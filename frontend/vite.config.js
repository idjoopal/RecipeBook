import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/ui/',
  build: {
    outDir: 'dist',
  },
  server: {
    proxy: {
      '/mcp': 'http://localhost:9101',
      '/api': 'http://localhost:9101',
      '/health': 'http://localhost:9101',
    },
  },
})
