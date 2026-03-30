import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/profil': 'http://localhost:8000',
      '/offres': 'http://localhost:8000',
      '/score': 'http://localhost:8000',
      '/tasks': 'http://localhost:8000',
      '/candidatures': 'http://localhost:8000',
      '/suivi': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
