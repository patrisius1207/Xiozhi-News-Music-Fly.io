# stream_server.py - Anti Crash Total + Support Berita Tetap Hidup

import subprocess
import json
import logging
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - YT-STREAM - %(levelname)s - %(message)s'
)
logger = logging.getLogger("yt_stream")

def get_audio_url(query: str):
    try:
        logger.info(f"Mencari musik: {query}")

        cmd = [
            "yt-dlp",
            f"ytsearch4:{query} official audio",
            "--quiet", "--no-warnings",
            "-f", "bestaudio[ext=m4a]/bestaudio/best",
            "--get-title", "--get-url",
            "--no-playlist",
            "--extractor-args", "youtube:player_client=android,web,ios",
            "--force-ipv4",
            "--sleep-interval", "2"
        ]

        result = subprocess.check_output(cmd, text=True, timeout=40).strip().splitlines()

        if len(result) >= 2:
            title = result[0].strip()
            url = result[1].strip()
            logger.info(f"✅ Berhasil: {title}")
            return {"status": "success", "title": title, "audio_url": url}

    except Exception as e:
        logger.error(f"yt-dlp gagal: {str(e)[:200]}")
        time.sleep(2)

    # Fallback MP3 mono
    try:
        cmd = [
            "yt-dlp", f"ytsearch3:{query}",
            "--quiet", "--no-warnings", "-x", "--audio-format", "mp3",
            "--postprocessor-args", "ffmpeg:-ac 1 -ar 22050 -b:a 64k",
            "--get-title", "--get-url", "--no-playlist"
        ]
        result = subprocess.check_output(cmd, text=True, timeout=45).strip().splitlines()
        if len(result) >= 2:
            title = result[0].strip()
            url = result[1].strip()
            logger.info(f"✅ Fallback MP3: {title}")
            return {"status": "success", "title": title, "audio_url": url}
    except Exception as e:
        logger.error(f"Fallback gagal: {e}")

    return {"status": "error", "message": "Saat ini sulit mengambil lagu dari YouTube. Coba lagi nanti atau gunakan judul lebih lengkap."}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/health"):
            self._json(200, {"status": "ok", "service": "music + news ready"})
            return

        if parsed.path == "/stream_pcm":
            params = parse_qs(parsed.query)
            song = params.get("song", [""])[0].strip()
            artist = params.get("artist", [""])[0].strip()
            query = f"{song} {artist}".strip() if artist else song

            result = get_audio_url(query)

            if result.get("status") == "success":
                self._json(200, {
                    "title": result["title"],
                    "audio_url": result["audio_url"],
                    "source": "youtube",
                    "format": "m4a"
                })
            else:
                self._json(200, {   # Selalu 200 agar tidak crash ESP32
                    "status": "error",
                    "audio_url": "",
                    "message": result.get("message", "Gagal mengambil musik")
                })
            return

        # Endpoint dummy untuk berita (kalau dibutuhkan)
        if parsed.path == "/news":
            self._json(200, {"status": "news service ready (cek music_news_server.py)"})
            return

        self._json(404, {"error": "Endpoint tidak ditemukan"})

    def _json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(port: int = 8080):
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    logger.info("🎵 stream_server started - Anti Crash mode")
    server.serve_forever()


if __name__ == "__main__":
    run()