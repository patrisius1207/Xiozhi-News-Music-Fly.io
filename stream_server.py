# stream_server.py
# Fix Bot Detection 2026 + Pure Audio MP3 Mono 64kbps

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

def get_stable_mp3_url(query: str, max_retries=2):
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Mencari (attempt {attempt+1}): {query}")

            cmd = [
                "yt-dlp",
                f"ytsearch3:{query}",
                "--quiet", "--no-warnings",
                "-f", "bestaudio/best",
                "-x", "--audio-format", "mp3",
                "--postprocessor-args", "ffmpeg:-ac 1 -ar 22050 -b:a 64k",   # Mono 64kbps - paling ringan
                "--get-title",
                "--get-url",
                "--no-playlist",
                "--extractor-args", "youtube:player_client=web_safari,web,android,ios",  # Anti-bot utama
                "--force-ipv4",
                "--no-check-certificate",
                "--sleep-interval", "1"   # Hindari rate limit
            ]

            result = subprocess.check_output(cmd, text=True, timeout=45).strip().splitlines()

            if len(result) >= 2:
                title = result[0].strip()
                direct_url = result[1].strip()
                logger.info(f"✅ Berhasil: {title} (Pure MP3 mono)")
                return {
                    "status": "success",
                    "title": title,
                    "audio_url": direct_url,
                    "format": "mp3_mono_64kbps"
                }

        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout pada attempt {attempt+1}")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or str(e)
            if "Sign in to confirm you're not a bot" in stderr:
                logger.warning("YouTube bot detection terdeteksi. Mencoba lagi...")
                time.sleep(2)  # delay kecil
                continue
            else:
                logger.error(f"yt-dlp error: {stderr[:300]}")
        except Exception as e:
            logger.error(f"Error umum: {e}")

        if attempt < max_retries:
            time.sleep(1.5)

    return {"status": "error", "message": "Lagu tidak ditemukan atau diblokir YouTube"}


class StreamHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/health"):
            self._json(200, {"status": "ok", "format": "MP3 mono 64kbps - anti bot"})
            return

        if parsed.path == "/stream_pcm":
            params = parse_qs(parsed.query)
            song   = params.get("song", [""])[0].strip()
            artist = params.get("artist", [""])[0].strip()

            query = f"{song} {artist}".strip() if artist else song
            if not query:
                self._json(400, {"error": "song wajib"})
                return

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
    logger.info("🎵 Server MP3 Mono 64kbps dengan anti-bot (web_safari)")
    server.serve_forever()


if __name__ == "__main__":
    run()