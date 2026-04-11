# stream_server.py - SoundCloud (Utama) + YouTube (Fallback)

import subprocess
import json
import logging
import re
import os
import tempfile
import requests
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - Xiozhi-Music - %(levelname)s - %(message)s'
)
logger = logging.getLogger("xiozhi_music")


def clean_title(title: str) -> str:
    """Bersihkan title dari noise seperti [abc123].mp3 atau filename mentah"""
    # Hapus ekstensi file di akhir
    title = re.sub(r'\.(mp3|m4a|flac|wav|ogg)$', '', title, flags=re.IGNORECASE)
    # Hapus YouTube/SoundCloud ID dalam kurung kotak: [a1xZrLE73Uc]
    title = re.sub(r'\[[a-zA-Z0-9_-]{6,}\]', '', title)
    # Hapus kurung kosong yang tersisa
    title = re.sub(r'\[\s*\]|\(\s*\)', '', title)
    # Rapikan spasi berlebih
    title = ' '.join(title.split())
    return title.strip()


def search_soundcloud(query: str):
    """Cari lagu di SoundCloud via yt-dlp (sumber utama)"""
    try:
        cmd = [
            "yt-dlp", f"scsearch3:{query}",
            "--quiet", "--no-warnings",
            "-f", "bestaudio/best",
            "--get-title", "--get-url",
            "--no-playlist",
            "--force-ipv4",
            "--socket-timeout", "15"
        ]
        result = subprocess.check_output(cmd, text=True, timeout=25).strip().splitlines()
        if len(result) >= 2:
            return {"title": clean_title(result[0].strip()), "audio_url": result[1].strip(), "source": "soundcloud"}
    except Exception as e:
        logger.warning(f"SoundCloud failed: {e}")
    return None


def search_youtube(query: str):
    """Fallback ke YouTube jika SoundCloud gagal"""
    try:
        cmd = [
            "yt-dlp", f"ytsearch3:{query} official audio",
            "--quiet", "--no-warnings",
            "-f", "bestaudio[ext=m4a]/bestaudio/best",
            "--get-title", "--get-url",
            "--no-playlist",
            "--extractor-args", "youtube:player_client=web,android",
            "--force-ipv4",
            "--socket-timeout", "15"
        ]
        result = subprocess.check_output(cmd, text=True, timeout=25).strip().splitlines()
        if len(result) >= 2:
            return {"title": clean_title(result[0].strip()), "audio_url": result[1].strip(), "source": "youtube"}
    except Exception as e:
        logger.warning(f"YouTube failed: {e}")
    return None


def get_audio_url(query: str):
    logger.info(f"Mencari lagu: {query}")

    # Prioritas 1: SoundCloud
    sc_result = search_soundcloud(query)
    if sc_result:
        logger.info(f"✅ Ditemukan di SoundCloud: {sc_result['title']}")
        return sc_result

    # Prioritas 2: YouTube (fallback)
    logger.info("SoundCloud tidak menemukan, mencoba YouTube...")
    yt_result = search_youtube(query)
    if yt_result:
        logger.info(f"✅ Ditemukan di YouTube: {yt_result['title']}")
        return yt_result

    return {"error": "Lagu tidak ditemukan di SoundCloud maupun YouTube. Coba judul lebih lengkap."}


class StreamHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/health"):
            self._json(200, {"status": "ok", "server": "Xiozhi Music - SoundCloud (Utama) + YouTube (Fallback)"})
            return

        if parsed.path == "/stream_pcm":
            params = parse_qs(parsed.query)
            song = params.get("song", [""])[0].strip()
            artist = params.get("artist", [""])[0].strip()
            query = f"{song} {artist}".strip() if artist else song

            if not query:
                self._json(400, {"error": "song wajib"})
                return

            result = get_audio_url(query)

            if "error" in result:
                self._json(200, {"status": "error", "message": result["error"]})
            else:
                # Buat proxy URL agar ESP32 tidak akses SoundCloud/YouTube langsung
                import urllib.parse
                encoded = urllib.parse.quote(result["audio_url"], safe="")
                host = self.headers.get("Host", "localhost")
                proxy_url = f"http://{host}/proxy?url={encoded}"
                self._json(200, {
                    "title": result["title"],
                    "audio_url": proxy_url,
                    "source": result.get("source", "soundcloud"),
                    "format": "mp3"
                })
            return

        if parsed.path == "/proxy":
            params = parse_qs(parsed.query)
            target_url = params.get("url", [""])[0].strip()
            if not target_url:
                self._json(400, {"error": "url wajib"})
                return
            try:
                is_hls = ".m3u8" in target_url or "playlist" in target_url

                if is_hls:
                    # Convert HLS → MP3 ke file temp dulu, baru kirim
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                        tmp_path = tmp.name

                    cmd = [
                        "ffmpeg", "-y",
                        "-i", target_url,
                        "-vn",
                        "-ar", "44100",
                        "-ac", "1",
                        "-b:a", "64k",
                        "-f", "mp3",
                        tmp_path
                    ]
                    ret = subprocess.run(cmd, timeout=60, stderr=subprocess.DEVNULL)

                    if ret.returncode != 0 or not os.path.exists(tmp_path):
                        self._json(502, {"error": "ffmpeg gagal convert audio"})
                        return

                    file_size = os.path.getsize(tmp_path)
                    self.send_response(200)
                    self.send_header("Content-Type", "audio/mpeg")
                    self.send_header("Content-Length", str(file_size))
                    self.send_header("Accept-Ranges", "bytes")
                    self.end_headers()
                    with open(tmp_path, "rb") as f:
                        while True:
                            chunk = f.read(8192)
                            if not chunk:
                                break
                            try:
                                self.wfile.write(chunk)
                            except BrokenPipeError:
                                break
                    os.unlink(tmp_path)
                else:
                    # Direct audio URL — download ke temp dulu, baru kirim
                    headers = {"User-Agent": "Mozilla/5.0"}
                    r = requests.get(target_url, headers=headers, timeout=30)
                    r.raise_for_status()

                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                        tmp.write(r.content)
                        tmp_path = tmp.name

                    file_size = os.path.getsize(tmp_path)
                    self.send_response(200)
                    self.send_header("Content-Type", "audio/mpeg")
                    self.send_header("Content-Length", str(file_size))
                    self.send_header("Accept-Ranges", "bytes")
                    self.end_headers()
                    with open(tmp_path, "rb") as f:
                        while True:
                            chunk = f.read(8192)
                            if not chunk:
                                break
                            try:
                                self.wfile.write(chunk)
                            except BrokenPipeError:
                                break
                    os.unlink(tmp_path)
            except Exception as e:
                logger.error(f"Proxy error: {e}")
                self._json(502, {"error": "Gagal proxy audio"})
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
    logger.info("🎵 Xiozhi Music Server started - SoundCloud (Utama) + YouTube (Fallback)")
    server.serve_forever()


if __name__ == "__main__":
    run()
