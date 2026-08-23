// Backend selalu di port 8000, di host yang sama dengan yang dipakai untuk
// membuka dashboard ini, entah itu "localhost" (host sendiri) atau IP LAN
// (peserta lain yang membuka link yang dibagikan host).
export const API_HOST = window.location.hostname;
export const API_BASE = `http://${API_HOST}:8000`;
export const WS_URL = `ws://${API_HOST}:8000/ws/live`;
