# stream_server.py
# HTTP API Server untuk ESP32 musik
# Endpoint: GET /stream_pcm?song=...&artist=...
# Response: JSON { "audio_url": "...", "title": "...", "artist": "..." }
# Firmware kemudian download audio dari audio_url secara langsung

import subprocess
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - STREAM - %(levelname)s - %(message)s'
)
logger = logging.getLogger("stream_server")


def get_youtube_direct_url(query: str) -> dict:
    """
    Cari lagu di YouTube, return direct audio URL.
    Format 140 = m4a 128kbps, kompatibel ESP32.
    """
    try:
        # Step 1: cari video ID + judul
        search = subprocess.run(
            ["yt-dlp", f"ytsearch1:{query}",
             "--get-id", "--get-title", "--no-playlist", "--quiet"],
            capture_output=True, text=True, timeout=30
        )
        lines = search.stdout.strip().splitlines()
        if len(lines) < 2:
            return {}

        title    = lines[0]
        video_id = lines[1]
        logger.info(f"Ditemukan: {title} ({video_id})")

        # Step 2: ambil direct URL audio
        audio = subprocess.run(
            ["yt-dlp",
             f"https://www.youtube.com/watch?v={video_id}",
             "--get-url",
             "-f", "140/bestaudio[ext=m4a]/bestaudio[acodec=mp4a]/bestaudio",
             "--no-playlist", "--quiet"],
            capture_output=True, text=True, timeout=30
        )
        audio_url = audio.stdout.strip().splitlines()[0] \
                    if audio.stdout.strip() else ""

        if not audio_url:
            return {}

        logger.info(f"Audio URL didapat ({len(audio_url)} chars)")
        return {
            "title":     title,
            "artist":    "",
            "audio_url": audio_url,
            "lyric_url": "",   # kosong — firmware handle gracefully
        }

    except subprocess.TimeoutExpired:
        logger.error("Timeout mencari lagu")
        return {}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {}


class MusicAPIHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        # ── Health check ──────────────────────────────────────────────
        if parsed.path in ("/", "/health"):
            self._json(200, {"status": "ok", "service": "XiaoZhi Stream"})
            return

        # ── /stream_pcm?song=...&artist=... ──────────────────────────
        # Firmware mengharapkan JSON response berisi audio_url
        if parsed.path == "/stream_pcm":
            params = parse_qs(parsed.query)
            song   = params.get("song",   [""])[0].strip()
            artist = params.get("artist", [""])[0].strip()
            query  = f"{artist} {song}".strip() if artist else song

            if not query:
                self._json(400, {"error": "Parameter 'song' wajib diisi"})
                return

            logger.info(f"Request: song='{song}' artist='{artist}'")

            result = get_youtube_direct_url(query)
            if not result:
                self._json(404, {"error": "Lagu tidak ditemukan"})
                return

            # Kembalikan JSON — persis format yang diharapkan firmware
            self._json(200, {
                "title":     result["title"],
                "artist":    result.get("artist", ""),
                "audio_url": result["audio_url"],
                "lyric_url": result.get("lyric_url", ""),
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
    server = HTTPServer(("0.0.0.0", port), MusicAPIHandler)
    logger.info(f"Music API server berjalan di :{port}")
    logger.info("Endpoint: GET /stream_pcm?song=JUDUL&artist=ARTIS")
    logger.info("Response: JSON { audio_url, title, artist, lyric_url }")
    server.serve_forever()


if __name__ == "__main__":
    run()
