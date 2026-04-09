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
> Ambil token baru dari konsol xiaozhi.me — jangan pakai token lama yang sudah terekspos!

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

## ⚙️ Konfigurasi xiaozhi.me

Login ke **xiaozhi.me** → Agent → **Konfigurasi Karakter** → tambahkan di kolom pengenalan:

```
收到音乐相关的需求时，只使用 MPC tool play_youtube_music 工具。
收到新闻相关的需求时，只使用 MPC tool get_latest_news 工具。
```

Artinya:
- Untuk musik → pakai `play_youtube_music`
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

## 🔄 Update / Redeploy

Kalau ada perubahan file, cukup:
```bash
git add .
git commit -m "update"
git push

fly deploy
```

---

## 🛠️ Perintah Fly.io yang Berguna

```bash
fly logs          # lihat log real-time
fly status        # cek status app
fly restart       # restart app
fly secrets list  # lihat daftar secrets (token tidak ditampilkan)
```

---

## ⚠️ Catatan
- yt-dlp mengambil audio stream langsung dari YouTube (bukan download file)
- ffmpeg terinstall otomatis via Dockerfile
- Token WSS jangan pernah ditulis langsung di kode atau di-push ke GitHub
- Gunakan fly secrets set untuk menyimpan token dengan aman
