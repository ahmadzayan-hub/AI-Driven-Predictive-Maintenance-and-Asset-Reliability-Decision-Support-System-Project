import { expect, test } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { mkdir } from 'node:fs/promises'
import { viewLoaded } from './helpers'

// PROPOSALS ONLY: styles are injected into the browser fixture, never application code.
const variants = {
  'dubai-executive': { theme: 'light', bg: '#F5F4F0', surface: '#FFFFFF', text: '#24303B', muted: '#52616D', accent: '#334E68', soft: '#E9EEF1', on: '#FFFFFF', border: '#D7DDE1', strong: '#71808B' },
  'engineering-clarity': { theme: 'light', bg: '#F4F6F8', surface: '#FFFFFF', text: '#24303B', muted: '#52616D', accent: '#285A82', soft: '#E8EFF5', on: '#FFFFFF', border: '#D7DFE6', strong: '#71808B' },
  'calm-dark': { theme: 'dark', bg: '#20252B', surface: '#2A3038', text: '#EBEEF2', muted: '#B8C1CC', accent: '#9EBAD4', soft: '#36424E', on: '#20252B', border: '#47515C', strong: '#8A99A8' },
} as const

test.use({ baseURL: 'http://127.0.0.1:8125', contextOptions: { reducedMotion: 'reduce' } })
for (const [name, v] of Object.entries(variants)) for (const locale of ['en', 'ar']) for (const width of [390, 1440]) {
  test(`proposal ${name} ${locale} ${width}`, async ({ page }, info) => {
    test.skip(info.project.name !== 'desktop', 'One explicit comparison matrix')
    await page.setViewportSize({ width, height: 1000 })
    await page.addInitScript(({ lang, theme }) => { localStorage.setItem('aos-locale', lang); localStorage.setItem('aos-theme', theme) }, { lang: locale, theme: v.theme })
    await page.goto('/')
    await viewLoaded(page)
    await expect(page.locator('.command--pending')).toHaveCount(0)
    await expect(page.locator('html')).toHaveAttribute('data-theme', v.theme)
    const before = await page.locator('.panel:visible').innerText()
    await page.addStyleTag({ content: `
      :root { color-scheme: ${v.theme}; --bg:${v.bg}!important; --workspace-bg:${v.bg}!important; --surface:${v.surface}!important; --surface-raised:${v.surface}!important; --surface-sunken:${v.bg}!important; --surface-glass:${v.surface}!important; --text:${v.text}!important; --text-muted:${v.muted}!important; --text-faint:${v.muted}!important; --accent:${v.accent}!important; --accent-solid:${v.accent}!important; --accent-solid-hover:${v.accent}!important; --accent-soft:${v.soft}!important; --on-accent:${v.on}!important; --border:${v.border}!important; --border-strong:${v.strong}!important; --nav-surface:${v.surface}!important; --nav-text:${v.text}!important; --nav-muted:${v.muted}!important; --nav-active:${v.soft}!important; --nav-accent:${v.accent}!important; --nav-border:${v.border}!important; --panel-fill:${v.surface}!important; --hero-fill:${v.surface}!important; --hero-border:${v.border}!important; --radius-m:10px!important; --radius-l:12px!important; }
      body { color:${v.text}; background:${v.bg}; }
      .command__hero,.next-action,.overview__evidence { border-inline-start:1px solid var(--border)!important; box-shadow:none!important; }
      .command__headline { font-size:1.125rem!important; line-height:1.55!important; font-weight:500!important; }
      .next-action h3 { font-size:1.25rem!important; font-weight:500!important; }
      .card__title { font-weight:500!important; }
      .command__eyebrow,.next-action__eyebrow { color:var(--text-muted)!important; }
      .command__hero-body { flex-basis:420px!important; }
      .command__hero { background:var(--surface)!important; }
      .proposal-label { position:fixed; bottom:72px; inset-inline-end:12px; z-index:100; padding:6px 10px; border:1px solid var(--border-strong); border-radius:6px; background:var(--surface); color:var(--text); font:12px/1.4 sans-serif; pointer-events:none; }
    ` })
    const rgb = `rgb(${[1, 3, 5].map(i => parseInt(v.text.slice(i, i + 2), 16)).join(', ')})`
    await expect(page.locator('body')).toHaveCSS('color', rgb)
    expect(await page.locator('.panel:visible').innerText()).toBe(before)
    await page.evaluate((label) => { const n = document.createElement('div'); n.className = 'proposal-label'; n.textContent = label; document.body.append(n) }, `DESIGN PROPOSAL · ${name} · SYNTHETIC`)
    await expect(page.locator('.shell__mode')).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
    const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa']).analyze()
    expect(axe.violations).toEqual([])
    await page.locator('.panel:visible').evaluate(el => { el.scrollTop = 0 })
    await mkdir('../docs/screenshots', { recursive: true })
    await page.screenshot({ path: `../docs/screenshots/miyaar-design-proposal-${name}-${locale}-${width}.png` })
  })
}
