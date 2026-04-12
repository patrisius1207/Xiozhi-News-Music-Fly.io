import asyncio
import websockets
import json
import urllib.request
import re
import subprocess
import os
from datetime import datetime

MCP_ENDPOINT = os.environ.get('MCP_ENDPOINT', '')

async def get_news(category="terkini"):
    urls = {
        "terkini":   "https://news.google.com/rss?hl=id-ID&gl=ID&ceid=ID:id",
        "nasional":  "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlRZU0FtVnVHZ0pWVXlnQVAB?hl=id-ID&gl=ID&ceid=ID:id",
        "dunia":     "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=id-ID&gl=ID&ceid=ID:id",
        "teknologi": "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB?hl=id-ID&gl=ID&ceid=ID:id",
        "olahraga":  "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdZU0FtVnVHZ0pWVXlnQVAB?hl=id-ID&gl=ID&ceid=ID:id",
        "hiburan":   "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y1RZU0FtVnVHZ0pWVXlnQVAB?hl=id-ID&gl=ID&ceid=ID:id",
        "bisnis":    "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=id-ID&gl=ID&ceid=ID:id",
    }
    url = urls.get(category.lower(), urls["terkini"])
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            xml = r.read().decode("utf-8", errors="ignore")
        items = []
        for block in re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)[:5]:
            title = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.DOTALL)
            source = re.search(r"<source>(.*?)</source>", block)
            if title:
                src = f" - {source.group(1)}" if source else ""
                items.append(f"{title.group(1).strip()}{src}")
        if not items:
            return "Tidak ada berita ditemukan."
        tanggal = datetime.now().strftime("%d %B %Y")
        return f"Berita {category.upper()} terbaru ({tanggal}):\n\n" + "\n\n".join(
            f"{i+1}. {t}" for i, t in enumerate(items)
        )
    except Exception as e:
        return f"Gagal ambil berita: {e}"

async def get_music_url(song_name):
    try:
        result = subprocess.run(
            ["yt-dlp", "-f", "bestaudio", "--get-url", f"ytsearch1:{song_name}"],
            capture_output=True, text=True, timeout=30
        )
        url = result.stdout.strip()
        if url:
            return {"success": True, "audio_url": url, "title": song_name, "source": "youtube", "result": f"Lagu ditemukan: {song_name}. Siap diputar di ESP32."}
    except Exception as e:
        print(f"[MUSIC] Error: {e}")
    return {"success": False, "result": "Lagu tidak ditemukan. Coba judul lebih spesifik."}

async def handle_mcp():
    print(f"Connecting to {MCP_ENDPOINT}")
    async with websockets.connect(MCP_ENDPOINT) as ws:
        print("Connected to XiaoZhi MCP!")
        async for message in ws:
            try:
                data = json.loads(message)
                method = data.get("method", "")
                msg_id = data.get("id")
                print(f"<- {method}")
                if method == "initialize":
                    await ws.send(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "XiaoZhiSTB", "version": "1.0.0"}}}))
                    print("-> Handshake OK!")
                elif method == "tools/list":
                    await ws.send(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": [{"name": "get_latest_news", "description": "Ambil berita terbaru dari Google News Indonesia. Category: terkini, nasional, dunia, teknologi, olahraga, hiburan, bisnis", "inputSchema": {"type": "object", "properties": {"category": {"type": "string"}, "jumlah": {"type": "integer"}}}}, {"name": "search_music_url", "description": "Cari dan stream lagu dari YouTube", "inputSchema": {"type": "object", "properties": {"song_name": {"type": "string"}}, "required": ["song_name"]}}, {"name": "get_current_time", "description": "Dapatkan waktu sekarang", "inputSchema": {"type": "object", "properties": {}}}]}}))
                    print("-> Tools list sent!")
                elif method == "tools/call":
                    tool = data["params"]["name"]
                    args = data["params"].get("arguments", {})
                    print(f"-> Tool: {tool} args: {args}")
                    if tool == "get_latest_news":
                        result = await get_news(args.get("category", "terkini"))
                    elif tool == "search_music_url":
                        music = await get_music_url(args.get("song_name", ""))
                        result = json.dumps(music, ensure_ascii=False)
                    elif tool == "get_current_time":
                        now = datetime.now()
                        result = f"Sekarang pukul {now.strftime('%H:%M')} WIB, tanggal {now.strftime('%d %B %Y')}."
                    else:
                        result = f"Tool tidak dikenal: {tool}"
                    await ws.send(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": result}]}}))
                    print(f"-> Response sent: {tool}")
                else:
                    if msg_id is not None:
                        await ws.send(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": {}}))
            except Exception as e:
                print(f"[ERROR] {e}")

async def main():
    while True:
        try:
            await handle_mcp()
        except Exception as e:
            print(f"[DISCONNECT] Reconnecting in 5s... ({e})")
            await asyncio.sleep(5)

if __name__ == "__main__":
    print("XiaoZhi MCP Server - STB Edition")
    asyncio.run(main())
