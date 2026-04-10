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
import httpx

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
#  TOOL 2 — CARI URL MUSIK DARI SOUNDCLOUD (REKOMENDASI)
# ═══════════════════════════════════════════════════════


@mcp.tool()
async def search_music_url(song_name: str) -> dict:
    """
    Cari lagu di SoundCloud dan kembalikan URL audio stream langsung.
    Tool ini akan memanggil stream_server.py yang sudah diubah ke SoundCloud.
    
    Parameter:
    - song_name: nama lagu + artis (contoh: "Bintang di Surga Noah", "Ngga Dulu Akbar Chalay")
    """
    logger.info(f"Mencari URL musik di SoundCloud: {song_name}")

    try:
        # Panggil stream_server.py yang berjalan di port 8080
        async with httpx.AsyncClient(timeout=50.0) as client:
            response = await client.get(
                "http://127.0.0.1:8080/stream_pcm",   # Panggil lokal di Fly.io
                params={"song": song_name, "artist": ""}
            )

            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == "success":
                    logger.info(f"✅ Berhasil mendapatkan audio dari SoundCloud: {data.get('title')}")
                    return {
                        "success": True,
                        "song_title": data.get("title"),
                        "audio_url": data.get("audio_url"),
                        "source": "soundcloud",
                        "result": f"Lagu ditemukan: {data.get('title')}\nSiap diputar di ESP32."
                    }
                else:
                    return {
                        "success": False,
                        "result": data.get("error", "Lagu tidak ditemukan di SoundCloud.")
                    }
            else:
                logger.error(f"Stream server returned status: {response.status_code}")
                return {
                    "success": False,
                    "result": f"Music server error (status {response.status_code})"
                }

    except httpx.RequestError as e:
        logger.error(f"Connection error to stream_server: {e}")
        return {
            "success": False,
            "result": "Music streaming service sedang tidak tersedia. Coba lagi nanti."
        }
    except Exception as e:
        logger.error(f"Unexpected error in search_music_url: {e}")
        return {
            "success": False,
            "result": f"Terjadi kesalahan saat mencari lagu: {str(e)}"
        }