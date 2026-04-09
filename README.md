# 🎵📰 XiaoZhi MCP Server — Musik + Berita
Deploy ke Railway — jalan 24/7 tanpa PC menyala.

---

## 📁 File yang Dibutuhkan
```
xiaozhi-railway/
├── music_news_server.py  ← MCP tools (berita + musik)
├── mcp_config.json       ← konfigurasi server
├── requirements.txt      ← Python dependencies
├── Dockerfile            ← untuk Railway
└── .env                  ← token kamu (jangan di-commit!)
```

---

## 🚀 Cara Deploy ke Railway

### 1. Push ke GitHub dulu
```bash
git init
git add .
git commit -m "xiaozhi mcp server"
git remote add origin https://github.com/USERNAME/xiaozhi-mcp.git
git push -u origin main
```
> ⚠️ Pastikan file `.env` masuk ke `.gitignore`!

### 2. Buat project baru di Railway
- Login ke https://railway.app
- Klik **New Project → Deploy from GitHub repo**
- Pilih repo yang baru kamu push

### 3. Set Environment Variable di Railway
Di Railway dashboard → **Variables** → tambahkan:
```
MCP_ENDPOINT = wss://api.xiaozhi.me/mcp/?token=TOKEN_BARU_KAMU
```
> Ganti dengan token baru dari xiaozhi.me (token lama sudah expired/terekspos)

### 4. Deploy!
Railway otomatis build dari Dockerfile dan jalankan server.

---

## ⚙️ Konfigurasi xiaozhi.me

Login ke **xiaozhi.me** → Agent → **Konfigurasi Karakter** → tambahkan di pengenalan:

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
- *"Putar lagu Sheila On 7"*
- *"Play Bohemian Rhapsody"*
- *"Nyalakan musik pop Indonesia"*

**Berita:**
- *"Ada berita apa hari ini?"*
- *"Berita teknologi terbaru?"*
- *"Kabar olahraga terkini?"*

---

## ⚠️ Catatan
- yt-dlp mengambil audio stream langsung dari YouTube (bukan download)
- ffmpeg diinstall otomatis via Dockerfile
- Token WSS lama sudah terekspos — **wajib regenerate** di xiaozhi.me
