import { fileURLToPath, URL } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: true,
    port: 3000,
    proxy: {
      '/api/v1/assessments': {
        target: process.env.VITE_ASSESSMENT_URL || process.env.VITE_GATEWAY_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
      '/api/v1/internal/simulations': {
        target: process.env.VITE_ASSESSMENT_URL || process.env.VITE_GATEWAY_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
      '/api': {
        target: process.env.VITE_GATEWAY_URL || 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: true,
    port: 3000,
  },
})
