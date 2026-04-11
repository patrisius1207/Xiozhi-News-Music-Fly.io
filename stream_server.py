# stream_server.py - Hybrid YouTube + QQ Music (Opsi Server QQ Music)

import subprocess
import json
import logging
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - WW-MUSIC - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ww_music")

def search_youtube(query: str):
    """Fallback ke YouTube (stabil)"""
    try:
        cmd = [
            "yt-dlp", f"ytsearch3:{query} official audio",
            "--quiet", "--no-warnings",
            "-f", "bestaudio[ext=m4a]/bestaudio/best",
            "--get-title", "--get-url",
            "--no-playlist",
            "--extractor-args", "youtube:player_client=web,android",
            "--force-ipv4",
            "--socket-timeout", "15"
        ]
        result = subprocess.check_output(cmd, text=True, timeout=25).strip().splitlines()
        if len(result) >= 2:
            return {"title": result[0].strip(), "audio_url": result[1].strip(), "source": "youtube"}
    except Exception as e:
        logger.warning(f"YouTube failed: {e}")
    return None

def search_qqmusic(query: str):
    """Coba ambil dari QQ Music (lebih baik untuk lagu Mandarin)"""
    try:
        # Menggunakan qqmusic search via yt-dlp atau direct (saat ini yt-dlp masih buggy, kita pakai simple search)
        cmd = [
            "yt-dlp", f"qqmusicsearch:{query}",
            "--quiet", "--no-warnings",
            "--get-title", "--get-url",
            "--no-playlist"
        ]
        result = subprocess.check_output(cmd, text=True, timeout=20).strip().splitlines()
        if len(result) >= 2:
            return {"title": result[0].strip(), "audio_url": result[1].strip(), "source": "qqmusic"}
    except:
        pass
    return None

def get_audio_url(query: str):
    logger.info(f"Mencari lagu: {query}")

    # Prioritas 1: QQ Music (jika terdeteksi lagu Mandarin)
    if any(kw in query.lower() for kw in ['远方', '晨风', 'teganya', 'sampaikan rindu', 'lyodra', 'ghea', 'noah']):
        qq_result = search_qqmusic(query)
        if qq_result:
            logger.info(f"✅ Ditemukan di QQ Music: {qq_result['title']}")
            return qq_result

    # Prioritas 2: YouTube
    yt_result = search_youtube(query)
    if yt_result:
        logger.info(f"✅ Ditemukan di YouTube: {yt_result['title']}")
        return yt_result

    return {"error": "Lagu tidak ditemukan di YouTube maupun QQ Music. Coba judul lebih lengkap."}

class StreamHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/health"):
            self._json(200, {"status": "ok", "server": "WW Music - YouTube + QQ Music Hybrid"})
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

            if "error" in result:
                self._json(200, {"status": "error", "message": result["error"]})
            else:
                self._json(200, {
                    "title": result["title"],
                    "audio_url": result["audio_url"],
                    "source": result.get("source", "youtube"),
                    "format": "m4a"
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
    logger.info("🎵 WW Music Server started - Hybrid YouTube + QQ Music")
    server.serve_forever()


if __name__ == "__main__":
    run()