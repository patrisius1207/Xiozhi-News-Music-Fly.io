# FIRMWARE_PATCH.md
# Cara mengarahkan firmware xiaozhi-esp32-music ke stream server kita sendiri

## File yang perlu diubah

Buka file:
```
main/boards/common/esp32_music.cc
```

## Cari baris ini (sekitar baris 50-80):
```cpp
// Kemungkinan bentuknya seperti ini:
std::string url = "http://110.42.59.54:2233/stream_pcm?song=" + encoded_song + "&artist=" + encoded_artist;

// Atau bisa juga:
#define MUSIC_API_HOST "110.42.59.54"
#define MUSIC_API_PORT 2233

// Atau:
const char* music_host = "110.42.59.54";
const int   music_port = 2233;
```

## Ganti dengan host Fly.io kamu:
```cpp
// Ganti IP lama:
// "110.42.59.54"  →  "xiaozhi-mcp.fly.dev"
// port 2233 tetap sama

// Contoh setelah diganti:
std::string url = "http://xiaozhi-mcp.fly.dev:2233/stream_pcm?song=" + encoded_song + "&artist=" + encoded_artist;

// Atau:
#define MUSIC_API_HOST "xiaozhi-mcp.fly.dev"
#define MUSIC_API_PORT 2233
```

## Setelah edit, compile & flash ulang:
```bash
idf.py build
idf.py -p COM3 flash monitor
```

## Cara cari baris yang tepat:
Jalankan di terminal dari folder firmware:
```bash
grep -r "110.42.59" main/
grep -r "stream_pcm" main/
grep -r "2233" main/
```
Salah satu dari ketiga command itu pasti ketemu baris yang perlu diganti.
