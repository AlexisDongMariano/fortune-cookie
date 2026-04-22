import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite config. The `server.proxy` lets the React dev server forward
// any request starting with `/api` to the FastAPI backend on :8000,
// which avoids CORS headaches during local dev.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
