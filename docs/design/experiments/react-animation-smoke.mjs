// Desktop smoke check for the isolated study, not platform acceptance.
import { createServer } from 'node:http'
import { readFile, writeFile } from 'node:fs/promises'
import { resolve, join, sep } from 'node:path'
import { createRequire } from 'node:module'
import assert from 'node:assert/strict'

if (!process.argv[2] || !process.argv[3]) throw new Error('Supply the study directory and frontend directory.')
const root = resolve(process.argv[2])
const dist = join(root, 'dist')
const require = createRequire(join(resolve(process.argv[3]), 'package.json'))
const { chromium } = require('@playwright/test')
const mime = { '.js': 'text/javascript', '.css': 'text/css', '.html': 'text/html' }
const server = createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname)
    const file = resolve(dist, '.'+pathname+(pathname.endsWith('/') ? 'index.html' : ''))
    if (!file.startsWith(dist+sep)) { response.writeHead(403).end(); return }
    const extension = file.slice(file.lastIndexOf('.'))
    const content = await readFile(file)
    response.writeHead(200, { 'Content-Type': mime[extension] ?? 'application/octet-stream' })
    response.end(content)
  } catch { response.writeHead(404).end() }
})
await new Promise((done) => server.listen(0, '127.0.0.1', done))
let browser
const results = []
try {
  browser = await chromium.launch({ headless: true })
  for (const variant of ['native', 'react-flow', 'motion-mini', 'motion-lazy']) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'no-preference' })
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    await page.goto(`http://127.0.0.1:${server.address().port}/${variant}/`)
    await page.getByRole('heading', { level: 1 }).waitFor()
    if (variant === 'react-flow') await page.locator('.react-flow__node[data-id="2"]').click()
    else await page.getByRole('button', { name: 'Analytics / التحليلات', exact: true }).click()
    assert.equal(await page.locator('.details h2').innerText(), 'Analytics / التحليلات')
    await page.getByRole('button', { name: 'Simulate handoff / محاكاة انتقال', exact: true }).click()
    assert.match(await page.getByRole('status').innerText(), /Analytics/)
    await page.getByRole('button', { name: 'Pause demo / إيقاف العرض', exact: true }).click()
    assert(await page.getByRole('button', { name: 'Simulate handoff / محاكاة انتقال', exact: true }).isDisabled())
    await page.getByRole('button', { name: 'Resume demo / متابعة العرض', exact: true }).click()
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.getByRole('button', { name: 'Simulate handoff / محاكاة انتقال', exact: true }).click()
    const animations = await page.locator('.signal').evaluateAll(elements => elements.map(element => getComputedStyle(element).animationName))
    assert(animations.length && animations.every(name => name === 'none'))
    assert.deepEqual(errors, [])
    await page.screenshot({ path: join(root, variant+'.png'), fullPage: true })
    results.push({ variant, result: 'passed', checks: ['render', 'node selection', 'synthetic handoff', 'pause control', 'reduced-motion CSS', 'no page errors'], viewport: '1440x900', fixture: 'five synthetic nodes; bilingual labels' })
    await page.close()
  }
} finally {
  await browser?.close()
  await new Promise(done => server.close(done))
}
await writeFile(join(root, 'smoke-results.json'), JSON.stringify({ browser: 'Chromium', scope: 'desktop smoke only; not RTL, mobile, screen-reader or WCAG acceptance', results }, null, 2)+'\n')
console.log(JSON.stringify(results, null, 2))
