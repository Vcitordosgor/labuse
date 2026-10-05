// PARCOURS-FIX-1 — bibliothèque commune du harnais Playwright (rejouable), rejoué sur le BUILD DE PROD
// servi par l'API en single-origin (port 6005). Adapté de PARCOURS-CLIENT-1/scripts/lib.mjs.
import { mkdirSync, appendFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const HERE = dirname(fileURLToPath(import.meta.url))
export const ROOT = resolve(HERE, '..')                       // …/PARCOURS-FIX-1
export const BASE = process.env.PARCOURS_BASE || 'http://127.0.0.1:6005'
export const PILOTE_PW = process.env.LABUSE_AUTH_PASSWORD || 'parcours-vic-2026'

const PW = process.env.PW_PKG || (process.env.HOME + '/Desktop/labuse/frontend/node_modules/playwright/index.js')
const _pwmod = await import(PW)
export const pw = _pwmod.chromium ? _pwmod : (_pwmod.default || _pwmod)
export const CHROME_EXE = process.env.CHROME_EXE ||
  (process.env.HOME + '/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell')

export async function launchChromium() {
  return pw.chromium.launch({ headless: true, executablePath: CHROME_EXE })
}

export const DESKTOP = { width: 1440, height: 900 }
export const MOBILE = { width: 390, height: 844 }
const LOGS = resolve(ROOT, 'run-logs')
mkdirSync(LOGS, { recursive: true })

export function logStep(obj) {
  appendFileSync(resolve(LOGS, 'steps.jsonl'), JSON.stringify(obj) + '\n')
  const { seq, device, name, verdict } = obj
  console.log(`  [${device || '-'}] ${seq != null ? '#' + seq + ' ' : ''}${name} ${verdict ? '→ ' + verdict : ''}`)
}

export async function capture(page, device, seq, slug, { fullPage = false } = {}) {
  const dir = resolve(ROOT, 'captures', device)
  mkdirSync(dir, { recursive: true })
  const file = resolve(dir, `${String(seq).padStart(2, '0')}-${slug}.png`)
  await page.screenshot({ path: file, fullPage })
  return file
}

export async function makeContext(browser, viewport) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 2, locale: 'fr-FR', timezoneId: 'Indian/Reunion' })
  const errors = []
  return { ctx, errors }
}

export function attachPageErrors(page, errors) {
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text().slice(0, 300)) })
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message.slice(0, 300)))
}

export async function probe(page, errors) {
  const url = page.url()
  const title = await page.title().catch(() => '')
  const headings = await page.locator('h1,h2').allInnerTexts().catch(() => [])
  const bodyText = (await page.locator('body').innerText().catch(() => '')).slice(0, 1500)
  return { url, title, headings: headings.slice(0, 10), errors: (errors || []).slice(0, 20), bodyText }
}

export async function loginVic(page) {
  await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded' })
  await page.fill('input[name="password"]', PILOTE_PW)
  await Promise.all([page.waitForLoadState('networkidle').catch(() => {}), page.click('button[type="submit"]')])
}

export async function loginClient(page, email, password, { souvenir = false } = {}) {
  await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded' })
  await page.fill('input[name="identifiant"]', email)
  await page.fill('input[name="password"]', password)
  if (souvenir) await page.check('#souvenir').catch(() => {})
  await Promise.all([page.waitForLoadState('networkidle').catch(() => {}), page.click('button[type="submit"]')])
}

// réécrit l'hôte d'un lien (l'API forge public_base_url=:8000 par défaut) vers BASE (:6005).
export function versBase(lien) { return (lien || '').replace(/https?:\/\/127\.0\.0\.1:\d+/, BASE) }
export const now = () => Date.now()
