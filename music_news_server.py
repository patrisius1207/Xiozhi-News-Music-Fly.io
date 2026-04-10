# music_news_server.py
# MCP Server Gabungan: Berita Google News + Musik YouTube (Anti-Crash)

from mcp.server.fastmcp import FastMCP
import urllib.request
import re
import logging
import httpx
from datetime import datetime

logger = logging.getLogger("xiaozhi_mcp")
mcp = FastMCP("XiaoZhiTools")

# ═══════════════════════════════════════════════════════
#  TOOL 1 — BERITA GOOGLE NEWS (Baru!)
# ═══════════════════════════════════════════════════════

# Google News RSS untuk Indonesia (hl=id-ID, gl=ID, ceid=ID:id)
GOOGLE_NEWS_BASE = "https://news.google.com/rss"

CATEGORIES = {
    "terkini":     f"{GOOGLE_NEWS_BASE}?hl=id-ID&gl=ID&ceid=ID:id",           # Top stories Indonesia
    "nasional":    f"{GOOGLE_NEWS_BASE}/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlRZU0FtVnVHZ0pWVXlnQVAB?hl=id-ID&gl=ID&ceid=ID:id",  # Indonesia
    "dunia":       f"{GOOGLE_NEWS_BASE}/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=id-ID&gl=ID&ceid=ID:id", # Dunia
    "bisnis":      f"{GOOGLE_NEWS_BASE}/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=id-ID&gl=ID&ceid=ID:id", # Ekonomi/Bisnis
    "teknologi":   f"{GOOGLE_NEWS_BASE}/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB?hl=id-ID&gl=ID&ceid=ID:id", # Teknologi
    "olahraga":    f"{GOOGLE_NEWS_BASE}/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdZU0FtVnVHZ0pWVXlnQVAB?hl=id-ID&gl=ID&ceid=ID:id", # Olahraga
    "hiburan":     f"{GOOGLE_NEWS_BASE}/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y1RZU0FtVnVHZ0pWVXlnQVAB?hl=id-ID&gl=ID&ceid=ID:id", # Hiburan
}

def fetch_rss(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "XiaoZhiBot/1.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"Fetch Google News RSS error: {e}")
        return ""

def parse_google_news(xml: str, max_items: int = 6) -> list:
    items = []
    for block in re.findall(r"<item>(.*?)</item>", xml, re.DOTALL):
        if len(items) >= max_items:
            break
        title = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.DOTALL)
        desc = re.search(r"<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>", block, re.DOTALL)
        source = re.search(r"<source>(.*?)</source>", block)
        
        if title:
            desc_text = ""
            if desc:
                desc_text = re.sub(r"<[^>]+>", "", desc.group(1)).strip()[:220]
            src = source.group(1) if source else "Google News"
            items.append({
                "title": title.group(1).strip(),
                "description": desc_text,
                "source": src
            })
    return items

@mcp.tool()
def get_latest_news(category: str = "terkini", jumlah: int = 5) -> dict:
    """
    Ambil berita terbaru dari Google News Indonesia.
    Category: terkini, nasional, dunia, bisnis, teknologi, olahraga, hiburan
    """
    cat = category.lower().strip()
    if cat not in CATEGORIES:
        cat = "terkini"
    
    count = max(1, min(int(jumlah), 8))
    
    try:
        logger.info(f"[GOOGLE NEWS] Mengambil berita kategori: {cat}")
        url = CATEGORIES[cat]
        xml = fetch_rss(url)
        
        if not xml:
            return {"success": False, "result": "Gagal mengambil berita dari Google News. Coba lagi nanti."}
        
        items = parse_google_news(xml, count)
        
        if not items:
            return {"success": False, "result": "Tidak ada berita ditemukan untuk kategori ini."}
        
        lines = [f"📰 Berita {cat.upper()} terbaru dari Google News ({datetime.now().strftime('%d %B %Y')}) :"]
        
        for i, item in enumerate(items, 1):
            lines.append(f"\n{i}. {item['title']}")
            if item["description"]:
                lines.append(f"   {item['description']}")
            lines.append(f"   Sumber: {item['source']}")
        
        return {"success": True, "result": "\n".join(lines)}
        
    except Exception as e:
        logger.error(f"[GOOGLE NEWS] Error: {e}")
        return {"success": False, "result": "Maaf, saat ini sedang ada masalah saat mengambil berita dari Google News."}


# ═══════════════════════════════════════════════════════
#  TOOL 2 — MUSIK (Anti-Crash)
# ═══════════════════════════════════════════════════════

@mcp.tool()
async def search_music_url(song_name: str) -> dict:
    """
    Cari lagu di YouTube via stream_server.py
    """
    logger.info(f"[MUSIC] Mencari lagu: {song_name}")

    try:
        async with httpx.AsyncClient(timeout=50.0) as client:
            response = await client.get(
                "http://127.0.0.1:8080/stream_pcm",
                params={"song": song_name, "artist": ""},
                timeout=50.0
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("audio_url") or data.get("status") == "success":
                    title = data.get("title", song_name)
                    audio_url = data.get("audio_url")
                    logger.info(f"[MUSIC] ✅ Ditemukan: {title}")
                    return {
                        "success": True,
                        "song_title": title,
                        "audio_url": audio_url,
                        "source": "youtube",
                        "result": f"Lagu ditemukan: {title}\nSiap diputar di ESP32."
                    }
                else:
                    msg = data.get("message", "Lagu tidak ditemukan.")
                    return {"success": False, "result": msg}

            else:
                logger.error(f"[MUSIC] Stream server error: {response.status_code}")
                return {"success": False, "result": "Music server sedang bermasalah."}

    except httpx.TimeoutException:
        return {"success": False, "result": "Pencarian lagu terlalu lama. Coba judul lebih spesifik."}
    except httpx.RequestError as e:
        logger.error(f"[MUSIC] Connection error: {e}")
        return {"success": False, "result": "Music streaming service sedang tidak tersedia. Kamu masih bisa minta berita."}
    except Exception as e:
        logger.error(f"[MUSIC] Unexpected error: {e}")
        return {"success": False, "result": "Terjadi kesalahan saat mencari musik."}


# Tool tambahan
@mcp.tool()
def get_current_time() -> str:
    now = datetime.now()
    return f"Sekarang pukul {now.strftime('%H:%M')} WIB, tanggal {now.strftime('%d %B %Y')}."


if __name__ == "__main__":
    logger.info("XiaoZhi MCP Server started - Google News + Music (Anti-Crash)")
    mcp.run()