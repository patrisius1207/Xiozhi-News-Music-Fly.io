# music_news_server.py
# MCP Server Gabungan: Berita (Kompas/Antara) + Musik YouTube (yt-dlp)
# Deploy ke Fly.io
#
# Tools:
#   - get_latest_news    : ambil berita terbaru
#   - search_music_url   : cari URL audio dari YouTube, kembalikan ke LLM
#                          agar LLM teruskan ke self.music.play_song di ESP32

from mcp.server.fastmcp import FastMCP
import urllib.request
import subprocess
import re
import logging

logger = logging.getLogger("xiaozhi_mcp")
mcp = FastMCP("XiaoZhiTools")

# ═══════════════════════════════════════════════════════
#  TOOL 1 — BERITA
# ═══════════════════════════════════════════════════════

FEEDS = {
    "nasional":      "https://www.kompas.com/getrss/nasional",
    "internasional": "https://www.kompas.com/getrss/internasional",
    "bisnis":        "https://www.kompas.com/getrss/bisniskeuangan",
    "teknologi":     "https://www.kompas.com/getrss/tekno",
    "olahraga":      "https://www.kompas.com/getrss/olahraga",
    "terkini":       "https://www.antaranews.com/rss/terkini.xml",
}

def fetch_rss(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "XiaoZhiBot/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def parse_rss(xml: str, max_items: int = 5) -> list:
    items = []
    for block in re.findall(r"<item>(.*?)</item>", xml, re.DOTALL):
        if len(items) >= max_items:
            break
        title = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block)
        desc  = re.search(r"<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>", block, re.DOTALL)
        if title:
            desc_text = ""
            if desc:
                desc_text = re.sub(r"<[^>]+>", "", desc.group(1)).strip()[:180]
            items.append({"title": title.group(1).strip(), "description": desc_text})
    return items

@mcp.tool()
def get_latest_news(category: str = "nasional", jumlah: int = 5) -> dict:
    """
    Ambil berita terbaru dari Kompas.com atau Antara News.
    Gunakan saat pengguna bertanya tentang berita terkini, kabar hari ini,
    atau kejadian terbaru di Indonesia maupun dunia.

    Parameter:
    - category: nasional, internasional, bisnis, teknologi, olahraga, terkini
    - jumlah: berapa berita yang ditampilkan (1-10). Default: 5
    """
    cat = category.lower().strip()
    if cat not in FEEDS:
        cat = "nasional"
    count = max(1, min(int(jumlah), 10))
    try:
        xml   = fetch_rss(FEEDS[cat])
        items = parse_rss(xml, count)
        if not items:
            return {"success": False, "result": "Tidak ada berita ditemukan."}
        sumber = "Antara News" if cat == "terkini" else "Kompas.com"
        lines  = [f"Berita {cat.upper()} terbaru dari {sumber}:"]
        for i, item in enumerate(items, 1):
            lines.append(f"\n{i}. {item['title']}")
            if item["description"]:
                lines.append(f"   {item['description']}")
        return {"success": True, "result": "\n".join(lines)}
    except Exception as e:
        logger.error(f"News error: {e}")
        return {"success": False, "result": f"Gagal mengambil berita: {e}"}


# ═══════════════════════════════════════════════════════
#  TOOL 2 — CARI URL MUSIK DARI YOUTUBE
# ═══════════════════════════════════════════════════════

@mcp.tool()
def search_music_url(song_name: str) -> dict:
    """
    Cari lagu di YouTube dan kembalikan URL audio streamnya.
    Gunakan tool ini saat pengguna minta putar lagu atau musik.

    PENTING: Setelah mendapat URL dari tool ini, langsung panggil
    tool self.music.play_song dengan URL tersebut untuk memutar musik
    di speaker ESP32. Jangan tanya konfirmasi ke pengguna.

    Parameter:
    - song_name: nama lagu atau artis. Contoh: "Sheila On 7 Dan",
                 "Bohemian Rhapsody", "lagu pop Indonesia terbaru"
    """
    logger.info(f"Mencari URL musik: {song_name}")

    try:
        # Step 1: Cari video ID dan judul
        search_result = subprocess.run(
            ["yt-dlp", f"ytsearch1:{song_name}", "--get-id", "--get-title",
             "--no-playlist", "--quiet"],
            capture_output=True, text=True, timeout=30
        )
        lines = search_result.stdout.strip().splitlines()
        if len(lines) < 2:
            return {"success": False, "result": "Lagu tidak ditemukan di YouTube."}

        title    = lines[0]
        video_id = lines[1]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info(f"Ditemukan: {title} ({video_id})")

        # Step 2: Ambil direct URL audio — prioritas mp4a/m4a (kompatibel ESP32)
        audio_result = subprocess.run(
            ["yt-dlp", video_url,
             "--get-url",
             "-f", "140/bestaudio[ext=m4a]/bestaudio[acodec=mp4a]/bestaudio",
             "--no-playlist", "--quiet"],
            capture_output=True, text=True, timeout=60
        )
        audio_url = audio_result.stdout.strip().splitlines()[0] if audio_result.stdout.strip() else ""

        if not audio_url:
            return {"success": False, "result": f"Gagal mengambil URL audio untuk '{title}'."}

        logger.info(f"URL audio ditemukan, panjang: {len(audio_url)} chars")

        # Kembalikan dalam format yang jelas untuk LLM
        return {
            "success":   True,
            "song_title": title,
            "audio_url": audio_url,
            "result": (
                f"Lagu ditemukan: {title}\n"
                f"Sekarang panggil self.music.play_song dengan url: {audio_url}"
            )
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "result": "Timeout saat mencari lagu. Coba lagi."}
    except FileNotFoundError:
        return {"success": False, "result": "yt-dlp tidak tersedia di server."}
    except Exception as e:
        logger.error(f"Music error: {e}")
        return {"success": False, "result": f"Error: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
