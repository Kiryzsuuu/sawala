import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true, // dengar di semua interface, supaya peserta lain di jaringan yang
                // sama bisa buka halaman monitor mereka sendiri
  },
});
