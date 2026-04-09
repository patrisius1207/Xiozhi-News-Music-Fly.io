# stream_server.py
# HTTP Audio Server untuk ESP32 — Download dulu, baru serve
# Kualitas diturunkan untuk hemat memori ESP32-S3

import subprocess
import json
import logging
import os
import uuid
import threading
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - STREAM - %(levelname)s - %(message)s'
)
logger = logging.getLogger("stream_server")

FLY_HOST  = "xiaozhi-mcp.fly.dev"
CACHE_DIR = "/tmp/audio_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# ─── Konfigurasi Audio ────────────────────────────────────────────────────────
# Format prioritas — dari paling ringan ke paling berat
# ESP32-S3 RAM terbatas, pilih bitrate rendah
# Format 599 = audio only ~48kbps (paling ringan, cukup untuk suara)
# Format 140 = m4a 128kbps (standar)
# Format 250 = opus 70kbps di webm
AUDIO_FORMAT = (
    "bestaudio[abr<=64][ext=m4a]"      # m4a max 64kbps ← paling ringan
    "/bestaudio[abr<=96][ext=m4a]"     # m4a max 96kbps
    "/140"                              # m4a 128kbps standard
    "/bestaudio[ext=m4a]"              # m4a terbaik yang ada
    "/bestaudio"                        # fallback apapun
)

# Post-process: konversi ke mp3 mono 64kbps via ffmpeg
# Ini yang paling hemat memory di ESP32 (mono, bitrate rendah)
FFMPEG_ARGS = [
    "--postprocessor-args",
    "ffmpeg:-ac 1 -ar 22050 -b:a 64k",  # mono, 22050Hz, 64kbps
    "--audio-format", "mp3",
    "-x",  # extract audio only
]
# ─────────────────────────────────────────────────────────────────────────────

audio_cache = {}
cache_lock  = threading.Lock()


def cleanup_old_files():
    while True:
        time.sleep(300)
        now = time.time()
        with cache_lock:
            expired = [k for k, v in audio_cache.items()
                       if now - v[2] > 1800]
            for key in expired:
                path = audio_cache[key][0]
                try:
                    os.remove(path)
                    logger.info(f"Cache dihapus: {path}")
                except Exception:
                    pass
                del audio_cache[key]

threading.Thread(target=cleanup_old_files, daemon=True).start()


def download_audio(query: str) -> tuple:
    """Download audio dari YouTube, konversi ke MP3 mono 64kbps."""
    with cache_lock:
        if query in audio_cache:
            path, title, ts = audio_cache[query]
            if os.path.exists(path):
                logger.info(f"Cache hit: {title} ({os.path.getsize(path)//1024}KB)")
                audio_cache[query] = (path, title, time.time())
                return path, title

    logger.info(f"Mencari: {query}")

    try:
        # Cari video ID + judul
        search = subprocess.run(
            ["yt-dlp", f"ytsearch1:{query}",
             "--get-id", "--get-title",
             "--no-playlist", "--quiet"],
            capture_output=True, text=True, timeout=30
        )
        lines = search.stdout.strip().splitlines()
        if len(lines) < 2:
            return "", ""

        title    = lines[0]
        video_id = lines[1]
        logger.info(f"Ditemukan: {title} ({video_id})")

        # Download + konversi ke MP3 mono 64kbps
        file_id  = str(uuid.uuid4())[:8]
        out_tmpl = os.path.join(CACHE_DIR, f"{file_id}.%(ext)s")

        logger.info("Downloading + converting ke MP3 mono 64kbps...")
        dl = subprocess.run(
            ["yt-dlp",
             f"https://www.youtube.com/watch?v={video_id}",
             "-f", AUDIO_FORMAT,
             "-o", out_tmpl,
             "--no-playlist",
             "--quiet",
             "-x",                          # extract audio
             "--audio-format", "mp3",       # konversi ke mp3
             "--postprocessor-args",
             # mono (1 channel), 22050Hz sample rate, 64kbps
             "ffmpeg:-ac 1 -ar 22050 -b:a 64k",
             ],
            capture_output=True, text=True, timeout=180
        )

        # Cari file hasil konversi
        out_path = os.path.join(CACHE_DIR, f"{file_id}.mp3")
        if not os.path.exists(out_path):
            # Coba cari file apapun dengan file_id ini
            for f in os.listdir(CACHE_DIR):
                if f.startswith(file_id):
                    out_path = os.path.join(CACHE_DIR, f)
                    break

        if not os.path.exists(out_path):
            logger.error(f"File tidak terbuat. stderr: {dl.stderr[:200]}")
            return "", ""

        size = os.path.getsize(out_path)
        logger.info(f"Selesai: {title} ({size//1024}KB) → {out_path}")

        with cache_lock:
            audio_cache[query] = (out_path, title, time.time())

        return out_path, title

    except subprocess.TimeoutExpired:
        logger.error("Timeout download audio")
        return "", ""
    except Exception as e:
        logger.error(f"Error: {e}")
        return "", ""


class AudioHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/health"):
            self._json(200, {
                "status": "ok",
                "cache_count": len(audio_cache),
                "audio_format": "MP3 mono 22050Hz 64kbps"
            })
            return

        if parsed.path == "/stream_pcm":
            params = parse_qs(parsed.query)
            song   = params.get("song",   [""])[0].strip()
            artist = params.get("artist", [""])[0].strip()
            query  = f"{artist} {song}".strip() if artist else song

            if not query:
                self._json(400, {"error": "Parameter 'song' wajib diisi"})
                return

            logger.info(f"Request: '{query}'")

            file_path, title = download_audio(query)
            if not file_path:
                self._json(404, {"error": "Lagu tidak ditemukan"})
                return

            filename  = os.path.basename(file_path)
            audio_url = f"http://{FLY_HOST}/audio/{filename}"

            logger.info(f"→ {audio_url}")
            self._json(200, {
                "title":     title,
                "artist":    artist,
                "audio_url": audio_url,
                "lyric_url": "",
            })
            return

        if parsed.path.startswith("/audio/"):
            filename = parsed.path.split("/audio/")[1]
            if "/" in filename or ".." in filename:
                self.send_error(400, "Invalid filename")
                return

            file_path = os.path.join(CACHE_DIR, filename)
            if not os.path.exists(file_path):
                self.send_error(404, "File tidak ditemukan / expired")
                return

            file_size = os.path.getsize(file_path)
            logger.info(f"Serving: {filename} ({file_size//1024}KB)")

            # Tentukan content-type
            ctype = "audio/mpeg" if filename.endswith(".mp3") else "audio/mp4"

            try:
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Connection", "close")
                self.end_headers()

                with open(file_path, "rb") as f:
                    sent = 0
                    while True:
                        chunk = f.read(4096)
                        if not chunk:
                            break
                        try:
                            self.wfile.write(chunk)
                            sent += len(chunk)
                        except (BrokenPipeError, ConnectionResetError):
                            logger.info(f"ESP32 tutup ({sent//1024}/{file_size//1024}KB)")
                            break

                logger.info(f"Selesai serve: {filename} ({sent//1024}KB)")

            except Exception as e:
                logger.error(f"Serve error: {e}")
            return

        self._json(404, {"error": "Not found"})

    def _json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(port: int = 8080):
    server = ThreadingHTTPServer(("0.0.0.0", port), AudioHandler)
    logger.info(f"Audio server :{port} | Format: MP3 mono 22050Hz 64kbps")
    server.serve_forever()


if __name__ == "__main__":
    run()
