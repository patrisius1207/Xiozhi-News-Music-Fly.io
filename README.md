# 🎵📰 Xiozhi News Music - STB Edition

MCP Server untuk XiaoZhi ESP32 — Musik YouTube + Berita Google News

Bisa dijalankan di **Fly.io (Docker)** atau **lokal di STB Android yang sudah di-root** (contoh: ZTE ZXV10 B866F Telkomsel).

---

## ✨ Fitur

- 🎵 Streaming Musik YouTube via yt-dlp (perintah suara ke ESP32)
- 📰 Berita Google News via Telegram (terkini, teknologi, olahraga, dll)
- 🕐 Waktu sekarang via Telegram
- 🖥️ Jalan lokal di STB Android tanpa biaya hosting (GRATIS!)
- 🔐 Remote STB via SSH dari desktop
- 🤖 Telegram Bot Controller

---

## 📁 Struktur File

- `music_news_server.py` — MCP server untuk Fly.io (Docker)
- `stream_server.py` — HTTP streaming server untuk Fly.io
- `server_stb.py` — MCP server ringan untuk STB/Termux (tanpa pydantic)
- `start.sh` — Start script untuk Fly.io
- `start_stb.sh` — Start script untuk STB
- `mcp_config.json` — Konfigurasi MCP
- `Dockerfile` — Docker config untuk Fly.io
- `fly.toml` — Fly.io config

---

## 🚀 Deploy ke Fly.io

```bash
fly auth login
git clone https://github.com/patrisius1207/Xiozhi-News-Music-Fly.io.git
cd Xiozhi-News-Music-Fly.io
fly secrets set MCP_ENDPOINT="wss://api.xiaozhi.me/mcp/?token=TOKEN_KAMU"
fly deploy
```

---

## 📺 Deploy Lokal di STB Android (GRATIS!)

Cocok untuk STB yang sudah di-root seperti **ZTE ZXV10 B866F** (Telkomsel IndiHome 2023).

### Spesifikasi STB yang Ditest
- Chipset: Amlogic S905Y4 ARM 32-bit
- RAM: 2GB
- OS: Android TV 11
- Konsumsi listrik: ~5-8 watt

### 1. Install Termux
Download dari F-Droid (bukan Play Store):
https://f-droid.org/packages/com.termux/

### 2. Install Dependencies
```bash
pkg update && pkg upgrade -y
pkg install python git openssh -y
pip install websockets yt-dlp
```

### 3. Clone & Setup
```bash
git clone https://github.com/patrisius1207/Xiozhi-News-Music-Fly.io.git
```

### 4. Set Environment Variables
```bash
echo 'export MCP_ENDPOINT="wss://api.xiaozhi.me/mcp/?token=TOKEN_KAMU"' >> ~/.bashrc
echo 'export TELEGRAM_BOT_TOKEN="TOKEN_BOT_TELEGRAM"' >> ~/.bashrc
source ~/.bashrc
```

### 5. Jalankan Server
```bash
# Start SSH dulu agar bisa remote dari PC
sshd

# Jalankan MCP + Telegram server di background
python -u ~/server_stb.py > ~/server.log 2>&1 &

# Cek log
tail -f ~/server.log
```

### 6. Autostart saat STB nyala
Install **Termux:Boot** dari F-Droid, lalu:
```bash
mkdir -p ~/.termux/boot
cp ~/Xiozhi-News-Music-Fly.io/start_stb.sh ~/.termux/boot/start_server.sh
chmod +x ~/.termux/boot/start_server.sh
```

---

## 🖥️ Remote STB dari Desktop

```bash
# Windows PowerShell / Linux / Mac
ssh -p 8022 u0_a96@192.168.1.3

# Cek log server
tail -f ~/server.log

# Restart server
pkill -f server_stb.py
python -u ~/server_stb.py > ~/server.log 2>&1 &
```

---

## 🤖 Telegram Bot

Buat bot via @BotFather di Telegram, lalu set token ke environment variable.

### Perintah yang Didukung

| Perintah | Hasil |
|---|---|
| `/start` | Info dan contoh perintah |
| `Berita hari ini` | Berita terkini |
| `Berita teknologi` | Berita teknologi |
| `Berita olahraga` | Berita olahraga |
| `Berita nasional` | Berita nasional |
| `Berita dunia` | Berita internasional |
| `Berita hiburan` | Berita hiburan |
| `Berita bisnis` | Berita bisnis |
| `Jam berapa sekarang?` | Waktu & tanggal |

### Catatan
- Putar musik ke ESP32 tetap via perintah suara langsung
- Telegram bot tidak bisa inject perintah ke ESP32 (MQTT credentials tersimpan di device)

---

## 🗣️ Perintah Suara ke XiaoZhi ESP32

- "Putar lagu Dewa 19 Kangen"
- "Putar Popular The Weeknd"
- "Ada berita apa hari ini?"
- "Berita teknologi terbaru"
- "Sekarang jam berapa?"

---

## ⚠️ Catatan Penting

- Token MCP didapat dari dashboard [xiaozhi.me](https://xiaozhi.me)
- `server_stb.py` tidak butuh pydantic/mcp library — cocok ARM 32-bit
- STB konsumsi listrik ~5-8 watt, sangat hemat
- Firmware ESP32 yang direkomendasikan: [xiaozhi-esp32-music](https://github.com/Maggotxy/xiaozhi-esp32-music)
- SSH server Termux berjalan di port **8022** (bukan 22)
