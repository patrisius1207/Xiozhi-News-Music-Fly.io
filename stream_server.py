# stream_server.py
# Pure MP3 Mono 64kbps + Force Audio Only (Fix itag=18 & 302)

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

def get_pure_mp3_url(query: str):
    try:
        logger.info(f"Mencari: {query}")

        cmd = [
            "yt-dlp",
            f"ytsearch3:{query} official audio",
            "--quiet", "--no-warnings",
            "-f", "bestaudio/best",                  # Force audio only
            "-x", "--audio-format", "mp3",           # Extract + convert ke MP3
            "--postprocessor-args", "ffmpeg:-ac 1 -ar 22050 -b:a 64k -vn",  # Mono + no video
            "--get-title",
            "--get-url",
            "--no-playlist",
            "--extractor-args", "youtube:player_client=web,android,ios",
            "--force-ipv4",
            "--no-check-certificate",
            "--sleep-interval", "2",
            "--max-sleep-interval", "5"
        ]

        result = subprocess.check_output(cmd, text=True, timeout=50).strip().splitlines()

        if len(result) >= 2:
            title = result[0].strip()
            direct_url = result[1].strip()
            logger.info(f"✅ Pure MP3 mono: {title}")
            logger.info(f"URL length: {len(direct_url)} chars (should be direct mp3)")
            return {
                "status": "success",
                "title": title,
                "audio_url": direct_url,
                "format": "mp3"
            }
        else:
            return {"status": "error", "message": "Lagu tidak ditemukan"}

    except Exception as e:
        error_str = str(e).lower()
        if "sign in to confirm" in error_str or "bot" in error_str:
            return {"status": "error", "message": "YouTube bot detection. Coba lagi 10-15 menit"}
        logger.error(f"Error yt-dlp: {str(e)[:250]}")
        return {"status": "error", "message": "Gagal memproses lagu"}

class StreamHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/health"):
            self._json(200, {"status": "ok", "format": "Pure MP3 mono 64kbps"})
            return

        if parsed.path == "/stream_pcm":
            params = parse_qs(parsed.query)
            song   = params.get("song", [""])[0].strip()
            artist = params.get("artist", [""])[0].strip()

            query = f"{song} {artist}".strip() if artist else song
            if not query:
                self._json(400, {"error": "song wajib"})
                return

            time.sleep(1.2)   # hindari rate limit

            result = get_pure_mp3_url(query)

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
    logger.info("🎵 Pure MP3 Mono Server - Force audio only")
    server.serve_forever()


if __name__ == "__main__":
    run()