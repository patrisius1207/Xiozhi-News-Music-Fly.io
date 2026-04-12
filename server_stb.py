import asyncio
import websockets
import json
import urllib.request
import re
import subprocess
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

MCP_ENDPOINT = os.environ.get('MCP_ENDPOINT', '')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_ALLOWED_ID = os.environ.get('TELEGRAM_ALLOWED_USER_ID', '')

executor = ThreadPoolExecutor(max_workers=4)

def _http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=35) as r:
        return json.loads(r.read().decode())

def _http_post(url, data):
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())

async def tg_get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?timeout=10"
    if offset:
        url += f"&offset={offset}"
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, _http_get, url)
    except Exception as e:
        print(f"[TG] getUpdates error: {e}")
        return {"ok": False, "result": []}

async def tg_send(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": text}).encode()
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, _http_post, url, data)
    except Exception as e:
        print(f"[TG] sendMessage error: {e}")

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
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(executor, _http_get, url)
        return str(data)
    except Exception as e:
        pass
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
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            lambda: subprocess.run(
                ["yt-dlp", "-f", "bestaudio", "--get-url", f"ytsearch1:{song_name}"],
                capture_output=True, text=True, timeout=30
            )
        )
        url = result.stdout.strip()
        if url:
            return {"success": True, "audio_url": url, "title": song_name, "source": "youtube", "result": f"Lagu ditemukan: {song_name}. Siap diputar di ESP32."}
    except Exception as e:
        print(f"[MUSIC] Error: {e}")
    return {"success": False, "result": "Lagu tidak ditemukan."}

async def telegram_loop():
    if not TELEGRAM_BOT_TOKEN:
        print("[TG] Token tidak ada, dinonaktifkan.")
        return
    print("[TG] Telegram bot aktif!")
    offset = None
    while True:
        try:
            data = await tg_get_updates(offset)
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                user_id = str(msg.get("from", {}).get("id", ""))
                text = msg.get("text", "").strip()
                if not text or not chat_id:
                    continue
                if TELEGRAM_ALLOWED_ID and user_id != TELEGRAM_ALLOWED_ID:
                    await tg_send(chat_id, "Akses ditolak.")
                    continue
                print(f"[TG] Pesan: {text}")
                if text == "/start":
                    await tg_send(chat_id, "Halo! Saya XiaoZhi Controller.\n\nContoh:\n- Putar lagu Dewa 19\n- Berita hari ini\n- Berita teknologi\n- Jam berapa sekarang?")
                    continue
                text_lower = text.lower()
                if any(k in text_lower for k in ["berita", "news", "kabar"]):
                    cat = "terkini"
                    for k in ["teknologi", "olahraga", "hiburan", "bisnis", "nasional", "dunia"]:
                        if k in text_lower:
                            cat = k
                            break
                    await tg_send(chat_id, "Mengambil berita...")
                    result = await get_news(cat)
                    await tg_send(chat_id, result)
                elif any(k in text_lower for k in ["putar", "lagu", "musik", "play"]):
                    await tg_send(chat_id, f"Mencari: {text}...")
                    music = await get_music_url(text)
                    if music["success"]:
                        await tg_send(chat_id, f"Lagu ditemukan!\nJudul: {music['title']}\nDikirim ke ESP32...")
                    else:
                        await tg_send(chat_id, music["result"])
                elif any(k in text_lower for k in ["jam", "waktu", "time", "tanggal"]):
                    now = datetime.now()
                    await tg_send(chat_id, f"Sekarang pukul {now.strftime('%H:%M')} WIB, tanggal {now.strftime('%d %B %Y')}.")
                else:
                    await tg_send(chat_id, f"Perintah tidak dikenal.\n\nCoba:\n- Putar lagu ...\n- Berita teknologi\n- Jam berapa sekarang?")
        except Exception as e:
            print(f"[TG] Error: {e}")
            await asyncio.sleep(5)

async def handle_mcp():
    print("Connecting to MCP...")
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
                    print(f"-> Tool: {tool}")
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
                print(f"[MCP ERROR] {e}")

async def mcp_loop():
    while True:
        try:
            await handle_mcp()
        except Exception as e:
            print(f"[MCP] Reconnecting in 5s... ({e})")
            await asyncio.sleep(5)

async def main():
    print("XiaoZhi MCP + Telegram Server - STB Edition")
    await asyncio.gather(
        mcp_loop(),
        telegram_loop()
    )

if __name__ == "__main__":
    asyncio.run(main())
