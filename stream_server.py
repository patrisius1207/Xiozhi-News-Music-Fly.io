# stream_server.py - Versi Stabil Anti-Crash (Update 10 April 2026)

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
    """Coba ambil audio dengan beberapa strategi"""
    queries_to_try = [
        f"{query} official audio",
        query,
        f"{query} lyrics"
    ]

    for q in queries_to_try:
        try:
            logger.info(f"Mencari: {q}")

            # Strategi 1: m4a/AAC (paling bagus untuk firmware kamu)
            cmd = [
                "yt-dlp", f"ytsearch3:{q}",
                "--quiet", "--no-warnings",
                "-f", "bestaudio[ext=m4a]/bestaudio/best",
                "--get-title", "--get-url",
                "--no-playlist",
                "--extractor-args", "youtube:player_client=web,android,ios,web_embedded",
                "--force-ipv4"
            ]

            result = subprocess.check_output(cmd, text=True, timeout=40).strip().splitlines()

            if len(result) >= 2:
                title = result[0].strip()
                url = result[1].strip()
                logger.info(f"✅ Berhasil (m4a): {title}")
                return {"status": "success", "title": title, "audio_url": url, "format": "m4a"}

        except Exception as e:
            logger.warning(f"Gagal dengan query '{q}': {str(e)[:150]}")
            time.sleep(1.5)   # delay kecil anti bot

    # Fallback ke MP3 mono (paling ringan)
    try:
        logger.info("Mencoba fallback MP3 mono...")
        cmd = [
            "yt-dlp", f"ytsearch3:{query}",
            "--quiet", "--no-warnings",
            "-x", "--audio-format", "mp3",
            "--postprocessor-args", "ffmpeg:-ac 1 -ar 22050 -b:a 64k",
            "--get-title", "--get-url", "--no-playlist"
        ]
        result = subprocess.check_output(cmd, text=True, timeout=45).strip().splitlines()
        if len(result) >= 2:
            title = result[0].strip()
            url = result[1].strip()
            logger.info(f"✅ Fallback MP3: {title}")
            return {"status": "success", "title": title, "audio_url": url, "format": "mp3_mono"}
    except Exception as e:
        logger.error(f"Fallback gagal: {e}")

    return {"status": "error", "message": "Lagu tidak dapat diambil sekarang. Coba lagi sebentar atau gunakan judul lebih lengkap."}


class StreamHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/health"):
            self._json(200, {"status": "ok", "note": "Anti-crash mode - support m4a & mp3"})
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

            if result["status"] == "success":
                self._json(200, {
                    "title": result["title"],
                    "audio_url": result["audio_url"],
                    "source": "youtube",
                    "format": result.get("format", "m4a")
                })
            else:
                # Selalu return 200 agar ESP32 tidak langsung error
                self._json(200, {
                    "status": "error",
                    "title": query,
                    "audio_url": "",
                    "message": result["message"]
                })
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
    server = ThreadingHTTPServer(("0.0.0.0", port), StreamHandler)
    logger.info("🎵 stream_server.py started - Anti Crash & Anti Bot mode")
    server.serve_forever()


if __name__ == "__main__":
    run()