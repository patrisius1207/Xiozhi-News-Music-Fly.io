# stream_server.py
# YouTube Streaming - Anti-Bot 2026 + Pure Audio MP3 Mono 64kbps

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

def get_stable_mp3_url(query: str):
    try:
        logger.info(f"Mencari: {query}")

        cmd = [
            "yt-dlp",
            f"ytsearch3:{query} official audio",     # tambah keyword "official audio" agar lebih akurat lagu
            "--quiet", "--no-warnings",
            "--impersonate", "chrome",               # ← Anti-bot utama (TLS fingerprint)
            "-f", "bestaudio/best",                  # Pure audio only (hindari itag video)
            "-x", "--audio-format", "mp3",
            "--postprocessor-args", "ffmpeg:-ac 1 -ar 22050 -b:a 64k",  # Mono 64kbps
            "--get-title",
            "--get-url",
            "--no-playlist",
            "--extractor-args", "youtube:player_client=web,android,ios,web_embedded",
            "--force-ipv4",
            "--no-check-certificate",
            "--sleep-interval", "1.5",
            "--max-sleep-interval", "4"
        ]

        result = subprocess.check_output(cmd, text=True, timeout=50).strip().splitlines()

        if len(result) >= 2:
            title = result[0].strip()
            direct_url = result[1].strip()
            logger.info(f"✅ Berhasil: {title}")
            logger.info(f"URL length: {len(direct_url)} chars")
            return {
                "status": "success",
                "title": title,
                "audio_url": direct_url,
                "format": "mp3_mono_64kbps"
            }
        else:
            return {"status": "error", "message": "Lagu tidak ditemukan"}

    except subprocess.TimeoutExpired:
        logger.error("Timeout yt-dlp")
        return {"status": "error", "message": "Timeout memproses lagu"}
    except Exception as e:
        error_str = str(e).lower()
        if "sign in to confirm" in error_str or "bot" in error_str:
            logger.error("YouTube bot detection kuat!")
            return {"status": "error", "message": "YouTube sedang membatasi. Coba lagi 10-15 menit"}
        logger.error(f"Error yt-dlp: {str(e)[:250]}")
        return {"status": "error", "message": "Gagal memproses. Coba lagu lain"}


class StreamHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/health"):
            self._json(200, {"status": "ok", "note": "Anti-bot + impersonate chrome active"})
            return

        if parsed.path == "/stream_pcm":
            params = parse_qs(parsed.query)
            song   = params.get("song", [""])[0].strip()
            artist = params.get("artist", [""])[0].strip()

            query = f"{song} {artist}".strip() if artist else song
            if not query:
                self._json(400, {"error": "song wajib"})
                return

            # Delay kecil untuk mengurangi rate limit
            time.sleep(1.0)

            result = get_stable_mp3_url(query)

            if result["status"] == "success":
                self._json(200, {
                    "title": result["title"],
                    "audio_url": result["audio_url"],
                    "source": "youtube",
                    "format": "mp3"
                })
            else:
                self._json(404, {"error": result["message"], "query": query})
            return

        self._json(404, {"error": "Gunakan /stream_pcm?song=..."})

    def _json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(port: int = 8080):
    server = ThreadingHTTPServer(("0.0.0.0", port), StreamHandler)
    logger.info("🎵 YouTube MP3 Server - impersonate chrome + pure audio")
    server.serve_forever()


if __name__ == "__main__":
    run()