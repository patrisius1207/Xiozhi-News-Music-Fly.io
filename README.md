# 🎵📰 Xiozhi-Fly
MCP Server untuk XiaoZhi ESP32 — Musik YouTube + Berita Indonesia.
Deploy ke **Fly.io** — gratis permanen, jalan 24/7.

---

## 📁 Struktur File
```
Xiozhi-Fly/
├── music_news_server.py  ← MCP tools (berita + musik YouTube)
├── mcp_config.json       ← konfigurasi server
├── requirements.txt      ← Python dependencies
├── Dockerfile            ← build container
├── start.sh              ← jalankan MCP + HTTP keepalive
├── fly.toml              ← konfigurasi Fly.io
└── .gitignore            ← pastikan .env tidak ikut ke GitHub
```

---

## 🔧 Cara Kerja Musik (Alur Benar)

```
Kamu bicara → XiaoZhi (LLM)
    → search_music_url (Fly.io) → cari URL audio dari YouTube
    → self.music.play_song (ESP32 firmware) → stream ke speaker
```

MCP server di Fly.io hanya bertugas **mencari URL audio**.
Firmware ESP32 yang melakukan streaming-nya.

---

## 🚀 Cara Deploy ke Fly.io

### 1. Install flyctl
```bash
# Windows (PowerShell)
iwr https://fly.io/install.ps1 -useb | iex

# Mac/Linux
curl -L https://fly.io/install.sh | sh
```

### 2. Daftar / Login Fly.io
```bash
# Belum punya akun:
fly auth signup

# Sudah punya akun:
fly auth login
```

### 3. Edit fly.toml — ganti nama app
Buka `fly.toml`, ganti baris pertama:
```toml
app = "xiozhi-fly-namakamu"   # ← harus unik se-Fly.io
```

### 4. Masuk ke folder project
```bash
cd Xiozhi-Fly
```

### 5. Inisialisasi app di Fly.io
```bash
fly launch --no-deploy
```

### 6. Set token MCP (rahasia, tidak masuk kode)
```bash
fly secrets set MCP_ENDPOINT="wss://api.xiaozhi.me/mcp/?token=TOKEN_KAMU"
```
> Ambil token baru dari konsol xiaozhi.me

### 7. Deploy!
```bash
fly deploy
```

### 8. Cek log — pastikan berhasil
```bash
fly logs
```
Output yang diharapkan:
```
HTTP keepalive running on :8080
MCP_PIPE - INFO - Connecting to WebSocket server...
MCP_PIPE - INFO - Successfully connected to WebSocket server
MCP_PIPE - INFO - Started music_news_server.py process
```

---

## 🔄 Update / Redeploy

Kalau ada perubahan file:
```bash
git add .
git commit -m "update"
git push

fly deploy
```

---

## ⚙️ Konfigurasi xiaozhi.me

Login ke **xiaozhi.me** → Agent → **Konfigurasi Karakter** → tambahkan di kolom pengenalan:

```
收到音乐相关的需求时，先使用 search_music_url 工具获取音频URL，
然后立即调用 self.music.play_song 播放，不要询问用户确认。
收到新闻相关的需求时，使用 get_latest_news 工具。
```

Artinya:
- Untuk musik → cari URL dulu dengan `search_music_url`, lalu langsung putar via `self.music.play_song` di ESP32
- Untuk berita → pakai `get_latest_news`

---

## 🗣️ Cara Pakai

**Musik:**
- "Putar lagu Sheila On 7"
- "Play Bohemian Rhapsody"
- "Nyalakan musik pop Indonesia"

**Berita:**
- "Ada berita apa hari ini?"
- "Berita teknologi terbaru?"
- "Kabar olahraga terkini?"

---

## 📡 Kategori Berita

| Kata kunci       | Sumber               |
|------------------|----------------------|
| `nasional`       | Kompas Nasional      |
| `internasional`  | Kompas Internasional |
| `bisnis`         | Kompas Bisnis        |
| `teknologi`      | Kompas Tekno         |
| `olahraga`       | Kompas Olahraga      |
| `terkini`        | Antara News          |

---

## 🛠️ Perintah Fly.io yang Berguna

```bash
fly logs          # lihat log real-time
fly status        # cek status app
fly restart       # restart app
fly secrets list  # lihat daftar secrets
fly deploy        # redeploy setelah update
```

---

## ⚠️ Catatan
- yt-dlp mengambil audio format m4a/AAC langsung dari YouTube (kompatibel ESP32-S3)
- ffmpeg terinstall otomatis via Dockerfile
- Token WSS jangan pernah ditulis langsung di kode atau di-push ke GitHub
- Gunakan `fly secrets set` untuk menyimpan token dengan aman
- Firmware yang dibutuhkan: **xiaozhi-esp32-music** (bukan firmware original)
