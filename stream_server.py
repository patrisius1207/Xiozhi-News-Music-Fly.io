# stream_server.py
# True YouTube Direct Streaming untuk ESP32-S3
# Format super ringan: m4a AAC ~48-64kbps (paling hemat RAM & stabil)

import subprocess
import json
import logging
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - YT-STREAM - %(levelname)s - %(message)s'
)
logger = logging.getLogger("yt_stream")

FLY_HOST = "xiaozhi-mcp.fly.dev"   # Ubah jika nama app Fly.io kamu berbeda

# Format audio PALING RINGAN untuk ESP32-S3
AUDIO_FORMAT = (
    "bestaudio[abr<=64][ext=m4a]"     # Prioritas utama: m4a ≤64kbps
    "/bestaudio[abr<=96][ext=m4a]"    # Cadangan ≤96kbps
    "/140"                             # m4a 128kbps (paling kompatibel)
    "/bestaudio[ext=m4a]"             # m4a apapun
    "/251/bestaudio/best"             # fallback
)

def get_direct_audio_url(query: str):
    """Cari lagu & kembalikan direct streaming URL (cepat, tidak download dulu)"""
    try:
        logger.info(f"Mencari: {query}")

        cmd = [
            "yt-dlp",
            f"ytsearch1:{query}",
            "--quiet", "--no-warnings",
            "-f", AUDIO_FORMAT,
            "--get-title",
            "--get-url",
            "--no-playlist"
        ]

        result = subprocess.check_output(cmd, text=True, timeout=25).strip().splitlines()

        if len(result) >= 2:
            title = result[0].strip()
            direct_url = result[1].strip()
            logger.info(f"✅ Berhasil: {title} → {direct_url[:80]}...")
            return {
                "status": "success",
                "title": title,
                "audio_url": direct_url,
                "format": "m4a"
            }
        else:
            return {"status": "error", "message": "Lagu tidak ditemukan"}

    except subprocess.TimeoutExpired:
        logger.error("Timeout yt-dlp")
        return {"status": "error", "message": "Timeout saat mencari lagu"}
    except Exception as e:
        logger.error(f"Error yt-dlp: {e}")
        return {"status": "error", "message": "Gagal mengambil musik"}


class StreamHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        # Health check
        if parsed.path in ("/", "/health"):
            self._json(200, {
                "status": "ok",
                "type": "youtube_direct_stream",
                "format": "m4a AAC low bitrate (~64kbps)"
            })
            return

        # Endpoint utama yang dipanggil ESP32
        if parsed.path == "/stream_pcm":
            params = parse_qs(parsed.query)
            song   = params.get("song", [""])[0].strip()
            artist = params.get("artist", [""])[0].strip()

            query = f"{artist} {song}".strip() if artist else song
            if not query:
                self._json(400, {"error": "song parameter wajib"})
                return

            result = get_direct_audio_url(query)

            if result["status"] == "success":
                self._json(200, {
                    "title": result["title"],
                    "audio_url": result["audio_url"],   # ← Langsung dipakai ESP32
                    "source": "youtube",
                    "format": "m4a"
                })
            else:
                self._json(404, result)
            return

        self._json(404, {"error": "Endpoint tidak ditemukan. Gunakan /stream_pcm?song=..." })

    def _json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(port: int = 8080):
    server = ThreadingHTTPServer(("0.0.0.0", port), StreamHandler)
    logger.info(f"🎵 YouTube Direct Stream Server started on port {port}")
    logger.info(f"Format: m4a AAC low bitrate (paling ringan untuk ESP32-S3)")
    server.serve_forever()


if __name__ == "__main__":
    run()