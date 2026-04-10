# stream_server.py
# YouTube Streaming dengan OAuth2 (Fix Bot Detection 2026)

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

def get_mp3_url_with_oauth(query: str):
    try:
        logger.info(f"Mencari dengan OAuth2: {query}")

        cmd = [
            "yt-dlp",
            f"ytsearch3:{query}",
            "--quiet", "--no-warnings",
            "--username", "oauth2",          # ← Kunci utama
            "--password", "",                # password kosong
            "-f", "bestaudio/best",
            "-x", "--audio-format", "mp3",
            "--postprocessor-args", "ffmpeg:-ac 1 -ar 22050 -b:a 64k",  # Mono 64kbps
            "--get-title",
            "--get-url",
            "--no-playlist",
            "--extractor-args", "youtube:player_client=web,android,ios",
            "--force-ipv4",
            "--no-check-certificate",
            "--sleep-interval", "2"
        ]

        result = subprocess.check_output(cmd, text=True, timeout=50).strip().splitlines()

        if len(result) >= 2:
            title = result[0].strip()
            direct_url = result[1].strip()
            logger.info(f"✅ Sukses dengan OAuth2: {title}")
            return {
                "status": "success",
                "title": title,
                "audio_url": direct_url,
                "format": "mp3_mono_64kbps"
            }

    except subprocess.TimeoutExpired:
        logger.error("Timeout yt-dlp")
    except Exception as e:
        logger.error(f"Error yt-dlp: {str(e)[:300]}")

    return {"status": "error", "message": "Lagu tidak ditemukan atau diblokir sementara"}


class StreamHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/health"):
            self._json(200, {"status": "ok", "method": "OAuth2 + MP3 mono"})
            return

        if parsed.path == "/stream_pcm":
            params = parse_qs(parsed.query)
            song   = params.get("song", [""])[0].strip()
            artist = params.get("artist", [""])[0].strip()

            query = f"{song} {artist}".strip() if artist else song
            if not query:
                self._json(400, {"error": "song wajib"})
                return

            result = get_mp3_url_with_oauth(query)

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
    logger.info("🎵 YouTube MP3 Mono Server dengan OAuth2 (anti-bot 2026)")
    server.serve_forever()


if __name__ == "__main__":
    run()