# SAWALA - Skenario B (Host Monitoring)

Implementasi dari `sistem-deteksi-meeting-skenario-b.md`. Host melakukan
screen capture pada gallery view meeting, sistem memotong tiap tile peserta
dan menganalisisnya secara real-time (OnCam/OffCam, avatar vs orang asli,
penggunaan HP, fatigue, dan ekspresi/senyum), lalu menampilkannya di
dashboard web live.

## Cara Tercepat: start.bat

Double-click `start.bat`. Script ini otomatis mengecek Python & Node,
membuat virtual environment, menginstall semua dependency, menjalankan
test, lalu menyalakan backend + dashboard dan membuka browser. Lihat
`PANDUAN-PENGGUNAAN.md` untuk panduan lengkap bergambar.

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
