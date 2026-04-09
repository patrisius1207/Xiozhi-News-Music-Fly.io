# stream_server.py
# YouTube Direct Streaming - Versi Stabil 2026 untuk ESP32-S3
# Prioritas: cepat, ukuran kecil, kompatibel AAC/m4a

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

FLY_HOST = "xiaozhi-mcp.fly.dev"   # Ganti kalau nama app Fly.io kamu berbeda

# Format audio yang lebih fleksibel & ringan (2026)
AUDIO_FORMAT = (
    "bestaudio[ext=m4a]/140/"           # m4a AAC (paling kompatibel)
    "bestaudio[abr<=128][ext=m4a]/"     # maks 128kbps
    "251/"                              # opus webm (ringan)
    "bestaudio/best"                    # fallback
)

def get_direct_audio_url(query: str):
    """Cari lagu dengan query lebih baik"""
    try:
        logger.info(f"Mencari musik: {query}")

        # Gunakan ytsearch dengan judul + artis yang lebih akurat
        cmd = [
            "yt-dlp",
            f"ytsearch5:{query}",           # cari 5 hasil, ambil yang terbaik
            "--quiet", "--no-warnings",
            "-f", AUDIO_FORMAT,
            "--get-title",
            "--get-url",
            "--no-playlist",
            "--extractor-args", "youtube:player_client=web,android"   # membantu bypass perubahan YouTube
        ]

        result = subprocess.check_output(cmd, text=True, timeout=30).strip().splitlines()

        if len(result) >= 2:
            title = result[0].strip()
            direct_url = result[1].strip()
            logger.info(f"✅ Ditemukan: {title}")
            return {
                "status": "success",
                "title": title,
                "audio_url": direct_url,
                "format": "m4a/aac"
            }
        else:
            logger.warning(f"Tidak menemukan hasil untuk: {query}")
            return {"status": "error", "message": "Lagu tidak ditemukan"}

    except subprocess.TimeoutExpired:
        logger.error("Timeout yt-dlp")
        return {"status": "error", "message": "Timeout saat mencari lagu"}
    except Exception as e:
        logger.error(f"Error yt-dlp: {str(e)[:200]}")
        return {"status": "error", "message": "Gagal mengambil sumber musik"}


class StreamHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/health"):
            self._json(200, {"status": "ok", "type": "youtube_direct_stream"})
            return

        if parsed.path == "/stream_pcm":
            params = parse_qs(parsed.query)
            song   = params.get("song", [""])[0].strip()
            artist = params.get("artist", [""])[0].strip()

            # Gabungkan query dengan baik
            query = f"{song} {artist}".strip() if artist else song
            if not query:
                self._json(400, {"error": "song wajib diisi"})
                return

            result = get_direct_audio_url(query)

            if result["status"] == "success":
                self._json(200, {
                    "title": result["title"],
                    "audio_url": result["audio_url"],
                    "source": "youtube",
                    "format": "m4a"
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
    logger.info(f"🎵 YouTube Streaming Server started (port {port}) - Format m4a low bitrate")
    server.serve_forever()


if __name__ == "__main__":
    run()