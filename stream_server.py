# stream_server.py - Versi Cepat Anti-Timeout (Fly.io Friendly)

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
    start_time = time.time()
    logger.info(f"Mulai mencari: {query}")

    # Beberapa strategi dengan timeout lebih ketat
    strategies = [
        {"fmt": "bestaudio[ext=m4a]/bestaudio/best", "desc": "m4a priority"},
        {"fmt": "bestaudio/best", "desc": "fallback audio"}
    ]

    for strat in strategies:
        try:
            cmd = [
                "yt-dlp",
                f"ytsearch3:{query} official audio",
                "--quiet", "--no-warnings",
                "-f", strat["fmt"],
                "--get-title", "--get-url",
                "--no-playlist",
                "--extractor-args", "youtube:player_client=web,android,ios",
                "--force-ipv4",
                "--socket-timeout", "15",           # batasi timeout per request
                "--retries", "2"
            ]

            result = subprocess.check_output(cmd, text=True, timeout=25).strip().splitlines()  # timeout total 25 detik

            if len(result) >= 2:
                title = result[0].strip()
                url = result[1].strip()
                duration = time.time() - start_time
                logger.info(f"✅ Berhasil ({strat['desc']}) dalam {duration:.1f}s: {title}")
                return {"status": "success", "title": title, "audio_url": url, "format": "m4a"}

        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout pada strategi {strat['desc']}")
        except Exception as e:
            logger.warning(f"Gagal strategi {strat['desc']}: {str(e)[:100]}")

        time.sleep(1)  # delay kecil antar strategi

    logger.error(f"Gagal total untuk: {query}")
    return {"status": "error", "message": "Lagu ditemukan tapi proses terlalu lambat. Coba judul lebih spesifik."}


class StreamHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/health"):
            self._json(200, {"status": "ok", "note": "Anti-timeout mode - max 25s"})
            return

        if parsed.path == "/stream_pcm":
            params = parse_qs(parsed.query)
            song = params.get("song", [""])[0].strip()
            artist = params.get("artist", [""])[0].strip()
            query = f"{song} {artist}".strip() if artist else song

            if not query or query.lower() in ["populer", "audio", "lagu"]:
                self._json(200, {
                    "status": "error",
                    "message": "Query terlalu umum. Sebutkan judul lagu + penyanyi lebih jelas (contoh: popular the weeknd)"
                })
                return

            result = get_audio_url(query)

            if result["status"] == "success":
                self._json(200, {
                    "title": result["title"],
                    "audio_url": result["audio_url"],
                    "source": "youtube",
                    "format": "m4a"
                })
            else:
                self._json(200, {
                    "status": "error",
                    "title": query,
                    "audio_url": "",
                    "message": result["message"]
                })
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
    logger.info("🎵 stream_server started - Anti Timeout + Fast Search (max ~25 detik)")
    server.serve_forever()


if __name__ == "__main__":
    run()