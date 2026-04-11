# stream_server.py - Xiozhi Music
# SoundCloud (Utama) + YouTube (Fallback)
# Proxy: yt-dlp download → ffmpeg convert → kirim MP3 ke ESP32

import subprocess
import json
import logging
import re
import os
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - Xiozhi-Music - %(levelname)s - %(message)s'
)
logger = logging.getLogger("xiozhi_music")


def clean_title(title: str) -> str:
    title = re.sub(r'\.(mp3|m4a|flac|wav|ogg)$', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\[[a-zA-Z0-9_-]{6,}\]', '', title)
    title = re.sub(r'\[\s*\]|\(\s*\)', '', title)
    return ' '.join(title.split()).strip()


def find_song(query: str):
    """Cari lagu di SoundCloud dulu, fallback ke YouTube. Return dict atau None."""
    # SoundCloud
    try:
        cmd = [
            "yt-dlp", f"scsearch3:{query}",
            "--quiet", "--no-warnings",
            "-f", "bestaudio/best",
            "--get-title", "--get-url",
            "--no-playlist", "--force-ipv4", "--socket-timeout", "15"
        ]
        lines = subprocess.check_output(cmd, text=True, timeout=25).strip().splitlines()
        if len(lines) >= 2:
            logger.info(f"✅ Ditemukan di SoundCloud: {clean_title(lines[0])}")
            return {"title": clean_title(lines[0]), "source": "soundcloud", "yt_url": ""}
    except Exception as e:
        logger.warning(f"SoundCloud failed: {e}")

    # YouTube fallback
    try:
        cmd = [
            "yt-dlp", f"ytsearch3:{query} official audio",
            "--quiet", "--no-warnings",
            "-f", "bestaudio[ext=m4a]/bestaudio/best",
            "--get-title", "--get-url",
            "--no-playlist",
            "--extractor-args", "youtube:player_client=web,android",
            "--force-ipv4", "--socket-timeout", "15"
        ]
        lines = subprocess.check_output(cmd, text=True, timeout=25).strip().splitlines()
        if len(lines) >= 2:
            logger.info(f"✅ Ditemukan di YouTube: {clean_title(lines[0])}")
            return {"title": clean_title(lines[0]), "source": "youtube", "yt_url": lines[1].strip()}
    except Exception as e:
        logger.warning(f"YouTube failed: {e}")

    return None


def download_to_mp3(query: str, source: str, yt_url: str = None) -> str:
    """Download lagu dan convert ke MP3 mono 64k. Return path file MP3 atau None."""
    raw_path = "/tmp/xiozhi_raw"
    out_path = f"/tmp/xiozhi_{abs(hash(query)) % 999999}.mp3"

    # Bersihkan file lama
    for ext in ["m4a", "mp3", "webm", "opus", "ogg", "aac"]:
        p = f"{raw_path}.{ext}"
        if os.path.exists(p):
            os.unlink(p)
    if os.path.exists(out_path):
        os.unlink(out_path)

    try:
        if source == "soundcloud":
            dl_cmd = [
                "yt-dlp", f"scsearch1:{query}",
                "--quiet", "--no-warnings",
                "-f", "bestaudio/best",
                "--no-playlist", "--force-ipv4", "--socket-timeout", "15",
                "-o", f"{raw_path}.%(ext)s"
            ]
        else:
            dl_cmd = [
                "yt-dlp", yt_url,
                "--quiet", "--no-warnings",
                "-f", "bestaudio[ext=m4a]/bestaudio/best",
                "--no-playlist", "--force-ipv4", "--socket-timeout", "15",
                "-o", f"{raw_path}.%(ext)s"
            ]

        subprocess.run(dl_cmd, timeout=60, check=True, stderr=subprocess.DEVNULL)

        # Cari file hasil download
        raw_file = None
        for ext in ["m4a", "mp3", "webm", "opus", "ogg", "aac"]:
            candidate = f"{raw_path}.{ext}"
            if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
                raw_file = candidate
                break

        if not raw_file:
            logger.error("File hasil download tidak ditemukan")
            return None

        # Convert ke MP3 mono 64k
        ret = subprocess.run(
            ["ffmpeg", "-y", "-i", raw_file,
             "-vn", "-ar", "44100", "-ac", "1", "-b:a", "64k",
             "-f", "mp3", out_path],
            timeout=60, stderr=subprocess.DEVNULL
        )
        os.unlink(raw_file)

        if ret.returncode != 0 or not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
            logger.error("ffmpeg convert gagal")
            return None

        logger.info(f"✅ MP3 siap: {os.path.getsize(out_path)} bytes")
        return out_path

    except subprocess.TimeoutExpired:
        logger.error("Download timeout")
    except Exception as e:
        logger.error(f"Download error: {e}")

    return None


class StreamHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/health"):
            self._json(200, {"status": "ok", "server": "Xiozhi Music"})
            return

        if parsed.path == "/stream_pcm":
            params = parse_qs(parsed.query)
            song = params.get("song", [""])[0].strip()
            artist = params.get("artist", [""])[0].strip()
            query = f"{song} {artist}".strip() if artist else song

            if not query:
                self._json(400, {"error": "song wajib"})
                return

            logger.info(f"Mencari lagu: {query}")
            result = find_song(query)

            if not result:
                self._json(200, {"status": "error", "message": "Lagu tidak ditemukan. Coba judul lebih lengkap."})
                return

            encoded_query = urllib.parse.quote(query, safe="")
            encoded_source = urllib.parse.quote(result["source"], safe="")
            encoded_yt = urllib.parse.quote(result.get("yt_url", ""), safe="")
            host = self.headers.get("Host", "localhost")
            proxy_url = f"http://{host}/proxy?q={encoded_query}&src={encoded_source}&yt={encoded_yt}"

            self._json(200, {
                "title": result["title"],
                "audio_url": proxy_url,
                "source": result["source"],
                "format": "mp3"
            })
            return

        if parsed.path == "/proxy":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0].strip()
            source = params.get("src", ["soundcloud"])[0].strip()
            yt_url = params.get("yt", [""])[0].strip()

            if not query:
                self._json(400, {"error": "q wajib"})
                return

            logger.info(f"Proxy download: [{source}] {query[:50]}")
            mp3_path = download_to_mp3(query, source, yt_url or None)

            if not mp3_path:
                try:
                    self._json(502, {"error": "Gagal download audio"})
                except Exception:
                    pass
                return

            file_size = os.path.getsize(mp3_path)
            try:
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()
                with open(mp3_path, "rb") as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        try:
                            self.wfile.write(chunk)
                        except BrokenPipeError:
                            break
            except Exception as e:
                logger.error(f"Send error: {e}")
            finally:
                try:
                    os.unlink(mp3_path)
                except Exception:
                    pass
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
    server = ThreadingHTTPServer(("0.0.0.0", port), StreamHandler)
    logger.info("🎵 Xiozhi Music Server started - SoundCloud + YouTube + MP3 Proxy")
    server.serve_forever()


if __name__ == "__main__":
    run()
