import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // IPv4 explícito: en Windows + Node 17+ "localhost" resuelve primero a ::1
      // y Uvicorn escucha en 127.0.0.1, lo que produce un 502 en el proxy.
      "/api": "http://127.0.0.1:8000",
    },
  },
});
