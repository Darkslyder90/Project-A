import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Dev-Proxy aufs lokale Backend (siehe Briefing: "npm run dev"/Vite-Dev-Server
    // mit Proxy aufs lokale Backend). In Prod laufen Frontend+Backend hinter
    // demselben Reverse Proxy, daher dieselben relativen Pfade im Code.
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
