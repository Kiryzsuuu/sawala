# Catatan lanjutan - 2026-08-30

## Status sekarang (live di sawala.inspiratekno.com)

- Dashboard: **https://sawala.inspiratekno.com/app/** (bukan `/`, itu landing page marketing terpisah)
- Server: `103.150.227.58`, user `Inspira`, repo di `/home/Inspira/sawala`, PM2 app `sawala`
- Login test: `maskiryz23@gmail.com` / `opet123`
- Deploy manual (belum ada CI/CD):
  ```
  cd /home/Inspira/sawala
  git pull
  venv/bin/pip install -q -r requirements.txt   # kalau requirements.txt berubah
  cd dashboard && npm run build && cd ..         # kalau ada perubahan dashboard/
  pm2 restart sawala
  ```

## Yang sudah dibenerin hari ini

- Preview Capture gak lagi flicker pas ada 1 request gagal ([LivePreview.jsx](dashboard/src/components/LivePreview.jsx))
- Peserta yang offcam dari awal sesi sekarang tetap ke-track (dulu hilang total kalau belum pernah kedeteksi wajah) ([analysis_engine.py](src/engine/analysis_engine.py))
- Screen-capture browser gak lagi pecah/distorsi kalau window di-resize ([BrowserScreenCapture.jsx](dashboard/src/components/BrowserScreenCapture.jsx))
- OCR auto-baca nama peserta dari label tile (butuh Tesseract-OCR binary terinstal di server - belum dicek apakah sudah ada) ([name_ocr.py](src/detection/name_ocr.py))
- Preview Capture sekarang juga jalan untuk sumber bot (mosaic per peserta), bukan cuma screen-capture ([preview.py](src/engine/preview.py))

## Zoom bot (bot/zoom_web_bot.py) - STATUS: DIBEKUKAN, jangan lanjut coba-coba

**Temuan penting**: Zoom mendeteksi Chromium headless kita sebagai automated bot ("Automated bots aren't allowed to join this meeting") dan memblokirnya - tidak konsisten (kadang lolos, kadang tidak), khas sistem anti-bot yang terus disempurnakan.

**Keputusan**: TIDAK mencoba stealth-patch/evasion untuk akalin deteksi ini - itu sengaja melanggar proteksi resmi platform, di luar batas yang mau dikerjakan.

Kode bot tetap ada di `bot/zoom_web_bot.py` + dashboard panel (`ZoomBotControl.jsx`) sebagai referensi, tapi jangan dijadikan andalan sampai ada keputusan lain.

## Rencana besok

1. **Cek apakah akun Zoom bisa upgrade ke plan yang support RTMS** (Real-Time Media Streams) - setahu saya minimal Pro/Business. Ini jalur RESMI yang direstui Zoom, gak akan pernah kena block.
2. Kalau bisa upgrade: lanjut setup app Zoom Marketplace tipe **General App** → tab **Features → Surface** → toggle "Allow auto-start for RTMS" (butuh scope RTMS dulu di tab **Scopes**, cari `rtms`, centang 5 scope non-phone/non-ZCC-voice: `rtms_started`, `rtms_stopped`, `rtms_interrupted`, `rtms_concurrency_near_limit`, `rtms_concurrency_limited`).
3. Kalau gak bisa upgrade: fallback permanen ke Screen Capture manual (sudah live & lumayan stabil sekarang) - opsional, host bisa isi nama peserta manual di dashboard kalau OCR gak akurat.

## App Zoom yang pernah dibuat (Marketplace)

- App pertama: tipe General/OAuth biasa, salah tipe, tidak dipakai - boleh dihapus dari Zoom Marketplace kalau mau beres-beres.
- App kedua: "General app 499" - ini yang dipakai coba-coba setup scope RTMS. Kredensialnya ada di halaman app itu sendiri (marketplace.zoom.us -> Develop -> Build App), tidak dicatat di sini karena sensitif - cek langsung di situ kalau mau lanjut besok.
