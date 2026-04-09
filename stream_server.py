# stream_server.py
# HTTP API Server untuk ESP32 musik
# Endpoint: GET /stream_pcm?song=...&artist=...
# Response: JSON { "audio_url": "...", "title": "...", "artist": "..." }

import subprocess
import json
import logging
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - STREAM - %(levelname)s - %(message)s'
)
logger = logging.getLogger("stream_server")


def resolve_final_url(url: str) -> str:
    """Follow semua redirect dan kembalikan URL final."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            method="HEAD"
        )
        # urllib otomatis follow redirect
        with urllib.request.urlopen(req, timeout=10) as resp:
            final = resp.url
            logger.info(f"Resolved URL: {final[:80]}...")
            return final
    except Exception as e:
        logger.warning(f"Tidak bisa resolve redirect: {e}, pakai URL asli")
        return url


def get_youtube_info(query: str) -> dict:
    """
    Cari lagu di YouTube, kembalikan direct audio URL yang sudah di-resolve.
    Pakai format 18 (mp4 360p dengan audio) sebagai fallback karena
    beberapa format m4a audio-only di-redirect oleh YouTube.
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
            logger.error("Tidak ada hasil pencarian")
            return {}

        title    = lines[0]
        video_id = lines[1]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info(f"Ditemukan: {title} ({video_id})")

        # Step 2: ambil direct URL audio dengan format yang paling kompatibel
        # Coba beberapa format secara berurutan
        format_priority = [
            "140",                              # m4a 128kbps (paling bagus)
            "bestaudio[ext=m4a]",               # m4a terbaik
            "bestaudio[acodec=mp4a]",           # AAC terbaik
            "bestaudio",                        # audio terbaik apapun
        ]

        audio_url = ""
        for fmt in format_priority:
            audio = subprocess.run(
                ["yt-dlp", video_url,
                 "--get-url",
                 "-f", fmt,
                 "--no-playlist",
                 "--quiet"],
                capture_output=True, text=True, timeout=30
            )
            url = audio.stdout.strip().splitlines()[0] \
                  if audio.stdout.strip() else ""
            if url:
                audio_url = url
                logger.info(f"Format '{fmt}' berhasil")
                break

        if not audio_url:
            logger.error("Tidak bisa dapat URL audio")
            return {}

        logger.info(f"Audio URL didapat ({len(audio_url)} chars)")

        # Step 3: resolve redirect — pastikan URL final tidak 302 lagi
        final_url = resolve_final_url(audio_url)

        return {
            "title":     title,
            "artist":    "",
            "audio_url": final_url,
            "lyric_url": "",
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

        # Health check
        if parsed.path in ("/", "/health"):
            self._json(200, {"status": "ok", "service": "XiaoZhi Stream"})
            return

        # /stream_pcm?song=...&artist=...
        if parsed.path == "/stream_pcm":
            params = parse_qs(parsed.query)
            song   = params.get("song",   [""])[0].strip()
            artist = params.get("artist", [""])[0].strip()
            query  = f"{artist} {song}".strip() if artist else song

            if not query:
                self._json(400, {"error": "Parameter 'song' wajib diisi"})
                return

            logger.info(f"Request: song='{song}' artist='{artist}'")

            result = get_youtube_info(query)
            if not result:
                self._json(404, {"error": "Lagu tidak ditemukan"})
                return

            logger.info(f"Mengembalikan JSON untuk: {result['title']}")
            self._json(200, result)
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
    server.serve_forever()


if __name__ == "__main__":
    run()
