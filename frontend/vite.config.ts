import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The backend runs separately (default http://localhost:8000). Proxying "/api"
// to it keeps every request same-origin for the browser — no CORS, and no
// localhost vs 127.0.0.1 mismatch. Override the target with VITE_PROXY_TARGET
// if the backend is on another host or port.
const API_TARGET = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: API_TARGET, changeOrigin: true },
    },
  },
})
