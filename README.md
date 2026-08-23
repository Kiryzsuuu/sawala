# SAWALA - Skenario B (Host Monitoring)

Implementasi dari `sistem-deteksi-meeting-skenario-b.md`. Host melakukan
screen capture pada gallery view meeting, sistem memotong tiap tile peserta
dan menganalisisnya secara real-time (OnCam/OffCam, avatar vs orang asli,
penggunaan HP, fatigue, dan ekspresi/senyum), lalu menampilkannya di
dashboard web live.

## Cara Pakai (Windows, paling gampang): Installer

Download/build `Output/Sawala-Setup.exe` (lihat "Build Installer" di bawah),
lalu jalankan seperti installer biasa. Setelah terpasang, tinggal klik
shortcut **SAWALA** di Desktop atau Start Menu, ikon muncul di system tray,
browser otomatis kebuka ke dashboard. Tidak perlu Python/Node terpasang.

### Build Installer Sendiri

```bash
pip install pyinstaller
cd dashboard && npm install && npm run build && cd ..
pyinstaller meeting_monitor.spec --noconfirm
copy config.yaml dist\config.yaml
ISCC installer.iss
```

Hasilnya ada di `Output/Sawala-Setup.exe`. Butuh
[Inno Setup 6](https://jrsoftware.org/isinfo.php) terpasang (`winget install
JRSoftware.InnoSetup`).

## Cara Tercepat untuk Development: start.bat

Double-click `start.bat`. Script ini otomatis mengecek Python & Node,
membuat virtual environment, menginstall semua dependency, menjalankan
test, lalu menyalakan backend + dashboard dan membuka browser. Lihat
`docs/PANDUAN-PENGGUNAAN.pdf` untuk panduan lengkap bergambar.

## Instalasi Manual

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

cd dashboard && npm install && cd ..
```

Dependensi berat (`ultralytics`, `deepface`) bersifat opsional, jika tidak
terpasang, sistem otomatis jatuh ke mode fallback berbasis heuristik
(lihat komentar di `src/detection/phone_detector.py` dan
`src/detection/expression_detector.py`).

## Menjalankan Manual

```bash
# Terminal 1, backend
python -m src.api.main

# Terminal 2, dashboard
cd dashboard && npm run dev
```

Buka `http://localhost:5173`, klik **Mulai Sesi** untuk mengaktifkan
capture + analisis. Region layar default adalah monitor utama penuh; atur
`capture.region` di `config.yaml` untuk membatasi ke area gallery view.

## Dua Sumber Capture

| Sumber | Kapan dipakai | Cara aktif |
|---|---|---|
| Local screen capture (mss) | Aplikasi jalan di laptop host sendiri (installer/desktop) | Otomatis saat klik "Mulai Sesi", selama `capture.enable_local_capture: true` |
| Browser (`getDisplayMedia`) | Backend jalan di server/cloud tanpa layar lokal | Klik "Aktifkan Screen Capture" di dashboard, pilih jendela Zoom/Meet |

Jangan aktifkan keduanya bersamaan di mesin yang sama, akan bentrok
merebut index tile yang sama.

## Deploy ke Cloud (PM2 + Nginx, mis. Biznet Gio)

Server perlu Python 3.10+, Node 18+, PM2, dan Nginx. Sistem paket opencv
butuh `libgl1 libglib2.0-0 libsm6 libxext6 libxrender1` (apt).

```bash
git clone https://github.com/Kiryzsuuu/sawala.git && cd sawala

python3 -m venv venv
venv/bin/pip install -r requirements.txt

cd dashboard && npm ci && npm run build && cd ..

cp config.cloud.yaml config.yaml   # enable_local_capture: false - server tidak punya layar
cp .env.example .env               # lalu isi nilai asli, JANGAN commit

pm2 start deploy/ecosystem.config.js
pm2 save
```

`run.py` adalah entry point tipis (`python -m src.api.main` lewat
`runpy`) supaya PM2, yang butuh path file nyata, bisa menjalankannya -
`deploy/ecosystem.config.js` sudah mengarah ke situ.

Untuk Nginx, salin `deploy/nginx-sawala.conf` ke
`/etc/nginx/sites-available/`, sesuaikan `server_name`, symlink ke
`sites-enabled/`, lalu jalankan `certbot --nginx -d nama.domain.com` untuk
HTTPS otomatis.

Setelah jalan:

1. Buka `https://nama-domain-kamu.com`, login pakai akun super admin
   (`ADMIN_EMAIL`/`ADMIN_PASSWORD` di `.env`)
2. Klik **Mulai Sesi**
3. Klik **Aktifkan Screen Capture**, pilih jendela Zoom/Meet saat diminta
   browser

### Login & Keamanan

Sejak fitur login ditambahkan, semua endpoint sensitif (Mulai/Hentikan
Sesi, export data, ingest frame) butuh login. Akun super admin pertama
dibuat otomatis dari `.env` saat server pertama kali jalan. Super admin
bisa tambah/edit/hapus akun admin lain lewat tombol **Kelola User** di
dashboard. **Ganti password default segera setelah login pertama kali.**

## Menjalankan Tes

```bash
pytest tests/
```

## Struktur

Lihat bagian 6 pada `sistem-deteksi-meeting-skenario-b.md` untuk peta
struktur proyek lengkap.

## Privasi & Etika

Sistem ini memproses data wajah/perilaku peserta. Sebelum dipakai dalam
sesi nyata, penuhi persyaratan pada bagian 11 dokumen desain: pemberitahuan
dan persetujuan eksplisit peserta, penyimpanan hanya bentuk agregat, dan
kepatuhan terhadap UU PDP / GDPR sesuai yurisdiksi peserta.
