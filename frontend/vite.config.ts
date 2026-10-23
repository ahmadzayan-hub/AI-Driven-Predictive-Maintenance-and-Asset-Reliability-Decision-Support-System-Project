/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { readFileSync } from 'node:fs'

// Preview the same enforced shell policy that Vercel serves, including Miyaar.
const deployment = JSON.parse(readFileSync(new URL('../vercel.json', import.meta.url), 'utf8')) as {
  headers: { headers: { key: string; value: string }[] }[]
}
const contentPolicy = deployment.headers.flatMap((rule) => rule.headers)
  .find((header) => header.key === 'Content-Security-Policy')?.value
if (!contentPolicy) throw new Error('The static shell content policy is missing')

export default defineConfig({
  plugins: [react()],
  preview: { headers: { 'Content-Security-Policy': contentPolicy } },
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
