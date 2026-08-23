// Dua skenario deployment:
//   - Dev server (Vite di :5173) memanggil backend terpisah di :8000 - butuh
//     host:port eksplisit karena beda origin.
//   - Semua skenario lain (app desktop yang backend-nya sendiri menyajikan
//     dashboard di :8000, atau production di belakang Nginx di :443/:80)
//     dashboard dan API selalu satu origin yang sama - request relatif
//     otomatis benar, dan otomatis ikut https/wss kalau halamannya https.
const isViteDevServer = window.location.port === "5173";

export const API_BASE = isViteDevServer ? `http://${window.location.hostname}:8000` : "";

const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
export const WS_URL = isViteDevServer
  ? `ws://${window.location.hostname}:8000/ws/live`
  : `${wsProtocol}//${window.location.host}/ws/live`;
