#!/usr/bin/env node
// Render the executive film (server/video/composition.html) frame by frame in
// Chromium and encode it with ffmpeg, with the narration and the subtitle track.
//
//   node server/video/render_film.mjs <job.json>
//
// job.json: { story, font, out, audio, subtitles, language, fps, width, height }
// Called by server/executive_video.py; nothing here invents content.
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'

const HERE = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(HERE, '..', '..')
const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'))

function ffmpeg(args, feed) {
  return new Promise((resolve, reject) => {
    const child = spawn('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-nostdin', ...args], { stdio: ['pipe', 'ignore', 'pipe'] })
    let errors = ''
    child.stderr.on('data', (chunk) => { errors += chunk })
    child.on('error', reject)
    child.on('close', (code) => (code === 0 ? resolve() : reject(new Error(`ffmpeg failed: ${errors.trim().slice(-600)}`))))
    feed(child.stdin).then(() => child.stdin.end(), (error) => { child.kill(); reject(error) })
  })
}

const require = createRequire(path.join(ROOT, 'frontend', 'package.json'))
const { chromium } = require('@playwright/test')
const executablePath = process.env.PLAYWRIGHT_EXECUTABLE_PATH ||
  ['/opt/pw-browsers/chromium-1194/chrome-linux/chrome', '/opt/pw-browsers/chromium'].find((p) => fs.existsSync(p))
const browser = await chromium.launch({ executablePath, args: ['--force-color-profile=srgb'] })
try {
  const scale = job.width / 1280
  const font = fs.readFileSync(job.font).toString('base64')
  const html = fs.readFileSync(path.join(HERE, 'composition.html'), 'utf8')
    .replace('/*FONT*/', `@font-face { font-family: Dubai; src: url(data:font/ttf;base64,${font}) format('truetype'); }`)
    .replace('/*STORY*/null', JSON.stringify(job.story).replace(/</g, '\\u003c'))
  const open = async () => {
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: scale })
    await page.setContent(html, { waitUntil: 'load' })
    await page.evaluate(() => document.fonts.ready)
    return page
  }
  const first = await open()
  const duration = await first.evaluate(() => window.film.duration)
  const frames = Math.round(duration * job.fps)
  // Contiguous slices rendered in parallel pages, each its own segment; every
  // frame is still a pure function of its time, so the slices join seamlessly.
  const workers = Math.max(1, Math.min(job.workers || os.cpus().length, 6, Math.ceil(frames / 250)))
  const size = Math.ceil(frames / workers)
  const pages = [first, ...(await Promise.all(Array.from({ length: workers - 1 }, open)))]
  const parts = pages.map((_, w) => `${job.out}.part${w}.mp4`)
  await Promise.all(pages.map((page, w) => ffmpeg(['-y', '-f', 'image2pipe', '-framerate', String(job.fps), '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', String(job.fps), parts[w]], async (stdin) => {
    for (let i = w * size; i < Math.min(frames, (w + 1) * size); i++) {
      await page.evaluate((t) => window.film.seek(t), i / job.fps)
      const shot = await page.screenshot({ type: 'jpeg', quality: 92 })
      if (!stdin.write(shot)) await new Promise((resolve) => stdin.once('drain', resolve))
    }
  })))
  const list = `${job.out}.parts.txt`
  fs.writeFileSync(list, parts.map((p) => `file '${p.replace(/'/g, "'\\''")}'`).join('\n'))
  const lang = job.language === 'ar' ? 'ara' : 'eng'
  await ffmpeg(['-y', '-f', 'concat', '-safe', '0', '-i', list, '-i', job.audio, '-i', job.subtitles,
    '-map', '0:v', '-map', '1:a', '-map', '2:s', '-c:v', 'copy',
    '-c:a', 'aac', '-ar', '48000', '-b:a', '160k', '-c:s', 'mov_text',
    '-metadata:s:a:0', `language=${lang}`, '-metadata:s:s:0', `language=${lang}`,
    '-t', duration.toFixed(3), '-movflags', '+faststart', job.out], async () => {})
  for (const p of [...parts, list]) fs.rmSync(p, { force: true })
  const page = first
  // Stills for review: one settled frame per scene.
  if (job.stills) {
    fs.mkdirSync(job.stills, { recursive: true })
    for (const [i, s] of job.story.scenes.entries()) {
      await page.evaluate((t) => window.film.seek(t), Math.min(s.end - 0.6, s.start + 4))
      await page.screenshot({ path: path.join(job.stills, `scene-${i + 1}-${s.id}.png`), type: 'png' })
    }
  }
  process.stdout.write(JSON.stringify({ frames, duration, workers }))
} finally {
  await browser.close()
}
