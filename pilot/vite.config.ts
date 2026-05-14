import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "../engine/static/cockpit",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/health": "http://127.0.0.1:8000",
      "/backtest": "http://127.0.0.1:8000",
      "/market": "http://127.0.0.1:8000",
      "/live": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/ingest": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/nexus": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/auth": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/integrations": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
