# stream_server.py
# HTTP Audio Streaming Server untuk ESP32
# Port 8080 — diakses via https://xiaozhi-mcp.fly.dev/stream_pcm?song=...
# Firmware ESP32 diupdate: base_url = "http://xiaozhi-mcp.fly.dev"

import subprocess
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - STREAM - %(levelname)s - %(message)s'
)
logger = logging.getLogger("stream_server")


def find_youtube(query: str) -> tuple:
    """Cari di YouTube, return (video_id, title) atau ('', '')."""
    try:
        result = subprocess.run(
            ["yt-dlp", f"ytsearch1:{query}",
             "--get-id", "--get-title", "--no-playlist", "--quiet"],
            capture_output=True, text=True, timeout=30
        )
        lines = result.stdout.strip().splitlines()
        if len(lines) >= 2:
            return lines[1], lines[0]  # (video_id, title)
    except Exception as e:
        logger.error(f"YouTube search error: {e}")
    return "", ""


class AudioStreamHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        logger.info(f"{self.address_string()} {fmt % args}")

    def do_GET(self):
        parsed = urlparse(self.path)

        # Health check untuk Fly.io
        if parsed.path in ("/", "/health"):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"XiaoZhi Stream OK")
            return

        # ── /stream_pcm?song=...&artist=... ──────────────────────────
        if parsed.path == "/stream_pcm":
            params = parse_qs(parsed.query)
            song   = params.get("song",   [""])[0].strip()
            artist = params.get("artist", [""])[0].strip()
            query  = f"{artist} {song}".strip() if artist else song

            if not query:
                self.send_error(400, "Parameter 'song' wajib diisi")
                return

            logger.info(f"Request: song='{song}' artist='{artist}'")

            video_id, title = find_youtube(query)
            if not video_id:
                self.send_error(404, "Lagu tidak ditemukan")
                return

            logger.info(f"Streaming: {title} ({video_id})")

            try:
                self.send_response(200)
                self.send_header("Content-Type", "audio/mp4")
                self.send_header("Connection", "close")
                self.send_header(
                    "X-Song-Title",
                    title.encode("ascii", "replace").decode()
                )
                self.end_headers()

                # Pipe audio langsung dari yt-dlp ke ESP32
                proc = subprocess.Popen(
                    ["yt-dlp",
                     f"https://www.youtube.com/watch?v={video_id}",
                     "-f", "140/bestaudio[ext=m4a]/bestaudio[acodec=mp4a]/bestaudio",
                     "-o", "-",
                     "--no-playlist", "--quiet"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL
                )

                sent = 0
                while True:
                    chunk = proc.stdout.read(4096)
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                        self.wfile.flush()
                        sent += len(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        logger.info(f"ESP32 tutup koneksi setelah {sent//1024}KB")
                        break

                proc.terminate()
                logger.info(f"Selesai: {title} ({sent//1024}KB)")

            except Exception as e:
                logger.error(f"Streaming error: {e}")
            return

        self.send_error(404, "Not found")


def run(port: int = 8080):
    server = HTTPServer(("0.0.0.0", port), AudioStreamHandler)
    logger.info(f"Stream server berjalan di :{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
