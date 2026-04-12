# 🎵📰 Xiozhi News Music - STB Edition

MCP Server untuk XiaoZhi ESP32 — Musik YouTube + Berita Google News

Bisa dijalankan di **Fly.io (Docker)** atau **lokal di STB Android yang sudah di-root** (contoh: ZTE ZXV10 B866F Telkomsel).

---

## ✨ Fitur

- 🎵 Streaming Musik YouTube via yt-dlp
- 📰 Berita Google News (terkini, teknologi, olahraga, dll)
- 🕐 Waktu sekarang
- 🖥️ Bisa jalan lokal di STB Android tanpa biaya hosting
- 🔐 Remote via SSH dari desktop

---

## 📁 Struktur File

- `music_news_server.py` — MCP server untuk Fly.io
- `stream_server.py` — HTTP streaming server
- `server_stb.py` — MCP server ringan untuk STB/Termux (tanpa pydantic)
- `start.sh` — Start script untuk Fly.io
- `start_stb.sh` — Start script untuk STB

---

## 🚀 Deploy ke Fly.io

```bash
fly auth login
fly secrets set MCP_ENDPOINT="wss://api.xiaozhi.me/mcp/?token=TOKEN_KAMU"
fly deploy
```

---

## 📺 Deploy Lokal di STB Android (Gratis!)

Cocok untuk STB yang sudah di-root seperti ZTE ZXV10 B866F.

### 1. Install di Termux
```bash
pkg update && pkg upgrade -y
pkg install python git openssh -y
pip install websockets yt-dlp
```

### 2. Clone & Setup
```bash
git clone https://github.com/patrisius1207/Xiozhi-News-Music-Fly.io.git
echo 'export MCP_ENDPOINT="wss://api.xiaozhi.me/mcp/?token=TOKEN_KAMU"' >> ~/.bashrc
source ~/.bashrc
```

### 3. Jalankan Server
```bash
sshd
python -u ~/server_stb.py > ~/server.log 2>&1 &
```

### 4. Autostart (install Termux:Boot dari F-Droid)
```bash
mkdir -p ~/.termux/boot
cp start_stb.sh ~/.termux/boot/start_server.sh
chmod +x ~/.termux/boot/start_server.sh
```

---

## 🖥️ Remote dari Desktop via SSH

```bash
ssh -p 8022 u0_a96@192.168.1.3
tail -f ~/server.log
```

---

## 🗣️ Perintah XiaoZhi

- "Putar lagu Dewa 19 Kangen"
- "Ada berita apa hari ini?"
- "Berita teknologi terbaru"
- "Sekarang jam berapa?"

---

## ⚠️ Catatan

- Token MCP dari dashboard xiaozhi.me
- `server_stb.py` tidak butuh pydantic — cocok ARM 32-bit
- STB konsumsi listrik ~5-8 watt, sangat hemat
