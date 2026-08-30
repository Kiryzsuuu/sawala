# SAWALA Zoom Web Bot

Bot headless-browser yang join meeting Zoom lewat Zoom Web Client (bukan
lewat screen-capture layar host), lalu kirim video + nama asli tiap
peserta ke backend SAWALA. Ini alternatif dari Skenario B (screen-capture)
yang tidak butuh Zoom Meeting SDK / RTMS berbayar - cukup akun Zoom gratis.

## Kenapa ini lebih akurat dari screen-capture

- **Nama peserta**: dibaca langsung dari HTML halaman Zoom, bukan tebakan
  OCR - selalu akurat selama Zoom tidak redesign DOM-nya.
- **Posisi video tiap peserta**: didapat dari bounding box elemen asli di
  halaman, bukan tebak potongan grid dari screenshot.
- **Tidak pernah distorsi/pecah**: resolusi browser dikontrol penuh oleh
  bot, tidak tergantung window siapa pun di-resize.

## Setup

```bash
pip install -r bot/requirements-bot.txt
playwright install chromium
```

Di `config.yaml` backend, pastikan `bot_ingest.token` diisi nilai acak asli
(bukan `"change-me"`) - itu yang dipakai bot ini untuk autentikasi ke
`/api/ingest/frame`.

## Menjalankan

1. Mulai sesi monitoring dulu dari dashboard SAWALA (tombol start session),
   atau `POST /api/session/start`. Endpoint ingest menolak frame kalau
   belum ada sesi aktif.
2. Dapatkan link **"Join from your Browser"** Zoom: buka link undangan
   meeting, saat halaman "Launching..." muncul, klik link kecil di bawah
   ("having issues, click here" -> "join from your browser"). Salin URL
   itu (biasanya `https://xxxx.zoom.us/wc/join/<meetingId>`).
3. Jalankan:

```bash
python bot/zoom_web_bot.py \
  --join-url "https://us02web.zoom.us/wc/join/1234567890" \
  --display-name "SAWALA Monitor" \
  --api-base "https://sawala.inspiratekno.com" \
  --ingest-token "<token yang sama dengan bot_ingest.token>" \
  --passcode "123456"        # kalau meeting pakai passcode
```

Bot akan join, otomatis skip audio (tidak perlu), pindah ke gallery view,
lalu tiap `--interval` detik (default 3) screenshot tiap tile peserta dan
kirim ke backend.

## Kalau bot gagal join / tidak nemu tile peserta

DOM Zoom Web Client berubah antar rilis tanpa pemberitahuan. Kalau bot
error "Tidak ada tile peserta ditemukan" atau macet di layar join:

1. Jalankan dengan `headless=False` sementara (ubah baris
   `p.chromium.launch(headless=True, ...)` di `zoom_web_bot.py`) supaya
   kelihatan browsernya macet di step mana.
2. Buka meeting yang sama manual di Chrome, klik kanan -> Inspect elemen
   nama peserta / video tile, cocokkan class-name-nya dengan
   `TILE_SELECTOR_CANDIDATES` / `NAME_SELECTOR_CANDIDATES` di
   `zoom_web_bot.py`, tambahkan selector baru kalau perlu.

## Menjalankan terus-menerus (production)

Untuk jalan otomatis tiap ada meeting, pakai PM2 seperti service backend:

```bash
pm2 start bot/zoom_web_bot.py --interpreter python3 --name sawala-zoom-bot -- \
  --join-url "..." --api-base "..." --ingest-token "..."
```

Perlu satu proses bot per meeting (bot ini cuma join satu meeting per
instance).
