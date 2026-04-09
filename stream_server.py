# stream_server.py
# Fix "Sign in to confirm you're not a bot" + Pure Audio MP3 Mono 64kbps

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

        # Strategi anti-bot 2026
        cmd = [
            "yt-dlp",
            f"ytsearch3:{query}",
            "--quiet", "--no-warnings",
            "-f", "bestaudio/best",
            "-x", "--audio-format", "mp3",
            "--postprocessor-args", "ffmpeg:-ac 1 -ar 22050 -b:a 64k",   # Mono super ringan
            "--get-title",
            "--get-url",
            "--no-playlist",
            "--extractor-args", "youtube:player_client=android,web,ios,web_embedded",  # Multiple clients
            "--force-ipv4",
            "--sleep-interval", "2",          # Delay kecil antar request
            "--max-sleep-interval", "5",
            "--no-check-certificate"
        ]

        result = subprocess.check_output(cmd, text=True, timeout=45).strip().splitlines()

        if len(result) >= 2:
            title = result[0].strip()
            direct_url = result[1].strip()
            logger.info(f"✅ Berhasil (anti-bot): {title}")
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
        return {"status": "error", "message": "Timeout saat memproses lagu"}
    except Exception as e:
        error_str = str(e)
        if "Sign in to confirm" in error_str or "bot" in error_str.lower():
            logger.error("YouTube bot detection terdeteksi!")
            return {"status": "error", "message": "YouTube sedang membatasi akses (bot detection). Coba lagi 5-10 menit"}
        logger.error(f"Error yt-dlp: {error_str[:300]}")
        return {"status": "error", "message": "Gagal mengambil audio. Coba lagu lain"}


class StreamHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/health"):
            self._json(200, {"status": "ok", "note": "Anti-bot mode active"})
            return

        if parsed.path == "/stream_pcm":
            params = parse_qs(parsed.query)
            song   = params.get("song", [""])[0].strip()
            artist = params.get("artist", [""])[0].strip()

            query = f"{song} {artist}".strip() if artist else song
            if not query:
                self._json(400, {"error": "song wajib"})
                return

            # Tambah delay kecil jika terlalu banyak request berturut-turut
            time.sleep(0.8)

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
    logger.info("🎵 YouTube Stream Server - Anti Bot Detection Mode Active")
    server.serve_forever()


if __name__ == "__main__":
    run()