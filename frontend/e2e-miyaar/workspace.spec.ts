import { expect, test, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import type { SessionState, TranscriptEntry } from '../src/shared/types'

// Explicitly synthetic browser fixtures, never shipped as application data.
async function boot(page: Page, locale: 'en' | 'ar' = 'en', theme = 'dark') {
  await page.addInitScript(({ locale, theme }) => {
    localStorage.setItem('aos-onboarded', '1')
    localStorage.setItem('aos-locale', locale)
    localStorage.setItem('aos-theme', theme)
  }, { locale, theme })
  const state: SessionState = {
    session_id: 'synthetic-ui-test', agent_name: 'Agentic OS', version: 'test',
    welcome: 'Synthetic test session', ended: false, created_at: '2026-10-19T08:00:00Z',
    transcript: [], preferences: { language: locale === 'ar' ? 'Arabic' : 'English' },
    memory: {}, memory_entries: [], history: [], memory_persisted: false,
    commands: [{ command: '/help', usage: '/help', description: 'Help' }],
  }
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    let body: unknown = {}
    if(path === '/api/auth/config') body = { mode: 'local', provider_url: '', publishable_key: '', flows: [] }
    else if(path === '/api/sessions' || path === '/api/sessions/synthetic-ui-test') body = state
    else if(path.endsWith('/preferences')) body = { reply_text: '', state }
    else if(path === '/api/runs') body = { runs: [] }
    else if(path === '/api/datasets') body = { datasets: [] }
    else if(path === '/api/usage') body = { datasets: { used: 0, limit: 10 }, runs_today: { used: 0, limit: 10 } }
    else if(path === '/api/pipelines') body = { profiles: [], stages: [] }
    await route.fulfill({ json: body })
  })
  // The app lands on the Command Centre (U12); the Miyaar workspace is the assistant.
  await page.goto('/#/assistant')
  await expect(page.locator('.miyaar-hero')).toBeVisible()
  return state
}
async function noOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
}
async function a11y(page: Page) {
  await page.evaluate(() => document.fonts.ready.then(() => undefined))
  const result = await new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze()
  expect(result.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => ({ target: n.target, reason: n.failureSummary })) }))).toEqual([])
}

for(const locale of ['en','ar'] as const) for(const size of ['desktop','phone','tablet','laptop'] as const) {
  test(`workspace ${locale} ${size}: RTL/LTR, controls and accessibility`, async ({ page }) => {
    await page.setViewportSize(size === 'desktop' ? { width: 1440, height: 1000 } : size === 'tablet' ? { width: 768, height: 1024 } : size === 'laptop' ? { width: 1024, height: 900 } : { width: 375, height: 812 })
    await boot(page,locale)
    await expect(page.locator('html')).toHaveAttribute('dir',locale === 'ar' ? 'rtl' : 'ltr')
    await expect(page.locator('.miyaar-toolbar strong')).toHaveText(locale === 'ar' ? 'معيار' : 'Miyaar')
    await expect(page.locator('.miyaar-actions button')).toHaveCount(5)
    expect(await page.locator('.chat__scroll').evaluate(el => el.scrollTop)).toBe(0)
    await noOverflow(page)
    await a11y(page)
    if(size === 'desktop' || size === 'phone') await page.screenshot({ path: `../docs/screenshots/miyaar-${locale}-${size}.png`, fullPage: true })
    await page.locator('.miyaar-action').last().click()
    await expect(page).toHaveURL(/#\/approvals/)
  })
}
test('light theme, command dialog and reduced motion remain usable', async ({ page }) => {
  await page.setViewportSize({width:1440,height:1000})
  await boot(page,'en','light')
  await a11y(page)
  await page.keyboard.press('ControlOrMeta+k')
  await expect(page.getByRole('dialog')).toBeVisible()
  await a11y(page)
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await page.screenshot({path:'../docs/screenshots/miyaar-en-light.png',fullPage:true})
})
test('pending message, two turns, source attribution and error recovery', async ({ page }) => {
  const state=await boot(page)
  let count=0
  await page.route('**/api/sessions/*/messages',async route=>{
    count++
    if(count===3){ await route.fulfill({status:503,json:{detail:'Synthetic provider outage'}}); return }
    const input=route.request().postDataJSON().text
    await new Promise(resolve=>setTimeout(resolve,300))
    const reply: TranscriptEntry={id:count*2,role:'agent',text:count===1?'Synthetic model response.':'Synthetic rules fallback.',time:state.created_at,source:count===1?'model':'rules',action:'chat',provider:count===1?'test-model':undefined}
    state.transcript.push({id:count*2-1,role:'user',text:input,time:state.created_at},reply)
    await route.fulfill({json:{state,reply}})
  })
  const input=page.getByRole('textbox',{name:'Message',exact:true})
  await input.fill('Inspect pump P-101')
  await input.press('Enter')
  await expect(page.getByRole('article',{name:'Sending your message'})).toContainText('Inspect pump P-101')
  await expect(page.locator('.msg--agent .msg__bubble')).toHaveText('Synthetic model response.')
  await input.fill('Explain the evidence')
  await input.press('Enter')
  await expect(page.locator('.miyaar-notice')).toBeVisible()
  await expect(page.locator('.msg--agent')).toHaveCount(2)
  await expect(page.locator('.msg__author').first()).toHaveText('Miyaar')
  await input.fill('Try again')
  await input.press('Enter')
  await expect(page.getByRole('alert')).toContainText('Synthetic provider outage')
  await expect(input).toHaveValue('Try again')
  await a11y(page)
  await page.screenshot({path:'../docs/screenshots/miyaar-conversation.png',fullPage:true})
})
test('voice consent, actual listening, interim preview and reviewed final draft',async({page})=>{
  await page.addInitScript(()=>{
    class Recognition {
      static instance: Recognition
      onstart?:()=>void; onresult?:(e:unknown)=>void; onend?:()=>void
      start(){Recognition.instance=this}
      stop(){}
    }
    Object.assign(window,{SpeechRecognition:Recognition, testRecognition:Recognition})
  })
  await boot(page)
  await page.getByRole('button',{name:'Dictate with microphone'}).click()
  await expect(page.getByText('Before using voice input',{exact:true})).toBeVisible()
  await page.getByRole('button',{name:'I understand, start recording'}).click()
  await expect(page.getByText('Requesting microphone access…')).toBeVisible()
  await page.evaluate(()=>{
    const w=window as unknown as {testRecognition:{instance:{onstart:()=>void;onresult:(e:unknown)=>void}}}
    w.testRecognition.instance.onstart()
    w.testRecognition.instance.onresult({resultIndex:0,results:[Object.assign([{transcript:'Review pump'}],{isFinal:false})]})
  })
  await expect(page.getByText('Listening · select the microphone to finish')).toBeVisible()
  await expect(page.locator('.voice-console__preview')).toContainText('Review pump')
  await expect(page.locator('.voice-wave i').first()).toHaveCSS('animation-name', 'none')
  await expect(page.getByRole('textbox',{name:'Message',exact:true})).toBeEmpty()
  await expect(page.getByRole('button',{name:'Send message'})).toBeDisabled()
  await a11y(page)
  await page.screenshot({path:'../docs/screenshots/miyaar-voice-preview.png',fullPage:true})
  await page.evaluate(()=>{
    const w=window as unknown as {testRecognition:{instance:{onresult:(e:unknown)=>void}}}
    w.testRecognition.instance.onresult({resultIndex:0,results:[Object.assign([{transcript:'Review pump P-101'}],{isFinal:true})]})
  })
  await expect(page.getByRole('textbox',{name:'Message',exact:true})).toHaveValue('Review pump P-101')
  await expect(page.locator('.msg--user')).toHaveCount(0)
})

test('a new session stays usable while an obsolete reply is still pending', async ({ page }) => {
  const previous = await boot(page)
  const next = { ...previous, session_id: 'new-ui-session', transcript: [] as TranscriptEntry[] }
  await page.route('**/api/sessions', route => route.fulfill({ json: next }))
  let release!: () => void
  const gate = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/sessions/*/messages', async route => {
    const old = route.request().url().includes('synthetic-ui-test')
    if (old) await gate
    const state = old ? previous : next
    const reply: TranscriptEntry = { id: 2, role: 'agent', text: old ? 'Obsolete reply' : 'Current session reply',
      time: state.created_at, source: 'model', action: 'chat', provider: 'synthetic' }
    await route.fulfill({ json: { reply, state: { ...state, transcript: [reply] } } })
  })
  try {
    const input = page.getByRole('textbox', { name: 'Message', exact: true })
    await input.fill('Old question')
    await input.press('Enter')
    await expect(page.getByRole('article', { name: 'Sending your message' })).toBeVisible()
    await page.getByRole('button', { name: 'New session', exact: true }).click()
    await expect(page.locator('.miyaar-hero')).toBeVisible()
    await expect(input).toBeEmpty()
    await input.fill('New question')
    await expect(page.getByRole('button', { name: 'Send message' })).toBeEnabled()
    await input.press('Enter')
    await expect(page.locator('.msg--agent .msg__bubble')).toHaveText('Current session reply')
    const obsolete = page.waitForResponse(response => response.url().includes('synthetic-ui-test/messages'))
    release()
    await obsolete
    await expect(page.locator('.msg--agent .msg__bubble')).toHaveText('Current session reply')
  } finally { release() }
})
