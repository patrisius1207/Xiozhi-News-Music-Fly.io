# 🎵📰 Xiozhi News Music

**MCP Server untuk XiaoZhi ESP32** — Kombinasi **Musik YouTube** + **Berita Google News**

Server ini berjalan di **Fly.io** dan terhubung dengan firmware XiaoZhi ESP32 via MCP (WebSocket).

---

## ✨ Fitur Utama

- **Streaming Musik YouTube**  
  - Menggunakan yt-dlp untuk mendapatkan direct audio URL  
  - Format: m4a/AAC (prioritas) & MP3 mono 64kbps (fallback)  
  - Support lagu Indonesia, Internasional, dan Mandarin

- **Berita Terkini via Google News**  
  - Lebih cepat dan lebih lengkap dibanding sumber lama  
  - Support berbagai kategori (Indonesia, Dunia, Teknologi, Olahraga, dll)

- **Lirik Lagu** (termasuk lirik Mandarin)
- Stabil di ESP32-S3 dengan RAM terbatas
- Deploy mudah ke Fly.io (gratis)

---

## 📁 Struktur Proyek
Xiozhi-News-Music-Fly.io/
├── music_news_server.py      # MCP Tools (Musik + Google News)
├── stream_server.py          # HTTP Streaming Server untuk YouTube
├── mcp_config.json
├── requirements.txt
├── Dockerfile
├── start.sh
├── fly.toml
└── README.md
text---

## 🚀 Cara Deploy ke Fly.io

### 1. Install Fly CLI
```bash
# Mac/Linux
curl -L https://fly.io/install.sh | sh

# Windows (PowerShell)
iwr https://fly.io/install.ps1 -useb | iex
2. Login
Bashfly auth login
3. Clone & Masuk ke Folder
Bashgit clone https://github.com/patrisius1207/Xiozhi-News-Music-Fly.io.git
cd Xiozhi-News-Music-Fly.io
4. Edit fly.toml
Ubah nama aplikasi menjadi unik:
tomlapp = "xiozhi-music-news-namakamu"   # ← GANTI INI
5. Set Secret (MCP Token)
Bashfly secrets set MCP_ENDPOINT="wss://api.xiaozhi.me/mcp/?token=TOKEN_KAMU"
6. Deploy
Bashfly deploy
7. Cek Log
Bashfly logs --tail

🗣️ Cara Menggunakan di XiaoZhi ESP32
Musik

"Putar lagu Seribu Kali Ghea Indrawari"
"Putar Popular The Weeknd"
"Nyalakan musik pop Indonesia"
"Putar 远方"

Berita (Google News)

"Ada berita apa hari ini?"
"Berita Indonesia terkini"
"Berita teknologi terbaru"
"Kabar olahraga sekarang"
"Berita dunia internasional"


📋 Kategori Berita yang Didukung

Indonesia
Dunia / Internasional
Teknologi
Bisnis / Ekonomi
Olahraga
Hiburan
Kesehatan


🛠️ Perintah Fly.io yang Berguna
Bashfly deploy              # Deploy ulang setelah update kode
fly logs --tail         # Lihat log real-time
fly status              # Status aplikasi
fly restart             # Restart server
fly secrets list        # Lihat secret yang tersimpan

⚠️ Catatan Penting

Gunakan query yang jelas untuk musik (contoh: "popular the weeknd" bukan hanya "populer")
Berita diambil langsung dari Google News (lebih cepat & up-to-date)
Musik di-stream langsung dari YouTube menggunakan yt-dlp
Firmware yang direkomendasikan: xiaozhi-esp32-music (Maggotxy fork)
Jika sering timeout, gunakan judul lagu + nama penyanyi secara lengkap


📌 Repository
https://github.com/patrisius1207/Xiozhi-News-Music-Fly.io

Dibuat untuk XiaoZhi ESP32
Musik + Berita dalam satu server yang ringan dan stabil.
Selamat mencoba! 🎵📰
text---

**Cara memasang:**

1. Buka file `README.md` di repo kamu.
2. Hapus semua isi lama.
3. Paste teks di atas.
4. Simpan, lalu commit:

```bash
git add README.md
git commit -m "Update README.md lengkap dengan Google News"
git push