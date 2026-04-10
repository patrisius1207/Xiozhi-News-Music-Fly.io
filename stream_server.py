# stream_server.py
# SoundCloud → Direct MP3 (Bukan m3u8) - Fix untuk ESP32

import subprocess
import json
import logging
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - SC-STREAM - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sc_stream")


def get_soundcloud_direct_mp3(query: str):
    try:
        logger.info(f"Mencari di SoundCloud: {query}")

        cmd = [
            "yt-dlp",
            f"scsearch3:{query}",
            "--quiet", "--no-warnings",
            "-f", "bestaudio/best",                  # Ambil audio terbaik
            "--extract-audio",
            "--audio-format", "mp3",                 # Paksa konversi ke MP3
            "--postprocessor-args", "ffmpeg:-ac 1 -ar 22050 -b:a 64k -vn",  # Mono, rendah, no video
            "--get-title",
            "--get-url",
            "--no-playlist",
            "--force-ipv4",
            "--prefer-ffmpeg"
        ]

        result = subprocess.check_output(cmd, text=True, timeout=45).strip().splitlines()

        if len(result) >= 2:
            title = result[0].strip()
            direct_url = result[1].strip()
            logger.info(f"✅ Direct MP3 siap: {title}")
            return {
                "status": "success",
                "title": title,
                "audio_url": direct_url,
                "source": "soundcloud",
                "format": "mp3"
            }

    except Exception as e:
        logger.error(f"Error SoundCloud: {str(e)[:300]}")

    return {"status": "error", "message": "Gagal mendapatkan direct MP3 dari SoundCloud"}


class StreamHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/health"):
            self._json(200, {"status": "ok", "source": "SoundCloud Direct MP3"})
            return

        if parsed.path == "/stream_pcm":
            params = parse_qs(parsed.query)
            song   = params.get("song", [""])[0].strip()
            artist = params.get("artist", [""])[0].strip()

            query = f"{song} {artist}".strip() if artist else song
            if not query:
                self._json(400, {"error": "song wajib"})
                return

            result = get_soundcloud_direct_mp3(query)

            if result["status"] == "success":
                self._json(200, {
                    "title": result["title"],
                    "audio_url": result["audio_url"],
                    "source": "soundcloud",
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
    logger.info("🎵 SoundCloud Direct MP3 Server (Fix m3u8 issue)")
    server.serve_forever()


if __name__ == "__main__":
    run()