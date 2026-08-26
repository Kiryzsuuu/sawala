import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => ({
  // Production is served under /app (see src/api/main.py), but the dev
  // server should stay at the root so `npm run dev` matches the README.
  base: command === "build" ? "/app/" : "/",
  plugins: [react()],
  server: {
    port: 5173,
    host: true, // dengar di semua interface, supaya peserta lain di jaringan yang
                // sama bisa buka halaman monitor mereka sendiri
  },
}));
