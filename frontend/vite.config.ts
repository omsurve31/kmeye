import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

const BACKEND_URL = 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    // In development the browser talks to Vite, which forwards /api calls to the backend.
    proxy: { '/api': BACKEND_URL },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
  },
})
