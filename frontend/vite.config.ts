/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // During development the Vite dev server forwards API calls to the
      // FastAPI adapter so the app works without CORS configuration.
      '/api': 'http://127.0.0.1:8000',
    },
  },
  build: {
    target: 'es2022',
  },
  test: {
    environment: 'jsdom',
    // Bound concurrent jsdom memory on Windows. Assertions and deadlines
    // stay unchanged; CI retains its platform default.
    maxWorkers: process.platform === 'win32' ? 1 : undefined,
    setupFiles: ['./src/tests/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
