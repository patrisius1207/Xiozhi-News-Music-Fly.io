# music_news_server.py
# MCP Server Gabungan: Berita (Kompas/Antara) + Musik YouTube (yt-dlp)
# Deploy ke Railway
#
# Tools:
#   - get_latest_news   : ambil berita terbaru
#   - play_youtube_music: cari & stream musik dari YouTube

from mcp.server.fastmcp import FastMCP
import urllib.request
import subprocess
import json
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
#  TOOL 2 — MUSIK YOUTUBE
# ═══════════════════════════════════════════════════════

def search_youtube_audio_url(query: str) -> dict:
    """Cari lagu di YouTube dan ambil URL audio stream-nya via yt-dlp."""
    try:
        # Cari video YouTube
        search_cmd = [
            "yt-dlp",
            f"ytsearch1:{query}",   # ambil 1 hasil teratas
            "--get-id",
            "--get-title",
            "--no-playlist",
            "--quiet",
        ]
        result = subprocess.run(
            search_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        lines = result.stdout.strip().splitlines()
        if len(lines) < 2:
            return {"success": False, "error": "Lagu tidak ditemukan di YouTube"}

        # yt-dlp --get-title --get-id output: title dulu, lalu id
        title   = lines[0]
        video_id = lines[1]
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        # Ambil URL audio terbaik (format m4a/aac, langsung streamable)
        audio_cmd = [
            "yt-dlp",
            video_url,
            "--get-url",
            "-f", "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio",
            "--no-playlist",
            "--quiet",
        ]
        audio_result = subprocess.run(
            audio_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        audio_url = audio_result.stdout.strip()
        if not audio_url:
            return {"success": False, "error": "Gagal mengambil URL audio"}

        return {
            "success":   True,
            "title":     title,
            "video_id":  video_id,
            "audio_url": audio_url,
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout saat mencari lagu"}
    except FileNotFoundError:
        return {"success": False, "error": "yt-dlp tidak terinstall di server"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def play_youtube_music(song_name: str) -> dict:
    """
    Cari dan putar musik dari YouTube di speaker ESP32.
    Gunakan tool ini setiap kali pengguna meminta memutar lagu, musik, atau audio.
    Tool ini akan mencari lagu di YouTube dan mengirimkan URL audio ke perangkat.

    Parameter:
    - song_name: nama lagu atau artis yang ingin diputar.
      Contoh: "Bohemian Rhapsody Queen", "Sheila On 7 Dan", "lagu pop Indonesia terbaru"
    """
    logger.info(f"Mencari musik: {song_name}")

    info = search_youtube_audio_url(song_name)
    if not info["success"]:
        return {
            "success": False,
            "result":  f"Maaf, tidak bisa memutar '{song_name}'. {info.get('error', '')}"
        }

    title     = info["title"]
    audio_url = info["audio_url"]

    logger.info(f"Ditemukan: {title}")

    # Kembalikan URL audio ke firmware musik ESP32
    # Firmware xiaozhi-esp32-music akan otomatis stream URL ini
    return {
        "success":   True,
        "title":     title,
        "url":       audio_url,
        "result":    f"Memutar: {title}",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
