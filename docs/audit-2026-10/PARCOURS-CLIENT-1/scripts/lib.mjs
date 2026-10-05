// PARCOURS-CLIENT-1 — bibliothèque commune du harnais Playwright (rejouable).
// Import playwright via PW_PKG (chemin absolu du node_modules du dépôt principal) pour garder le
// script committable sans node_modules local. Lancer : voir run.sh.
import { writeFileSync, mkdirSync, appendFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const HERE = dirname(fileURLToPath(import.meta.url))
export const ROOT = resolve(HERE, '..')            // …/PARCOURS-CLIENT-1
// App servie single-origin par le dev vite (8795) qui proxifie l'API (5995). Le build prod
// (Rolldown, chunk vendor) rend blanc sous le chromium dispo — voir RAPPORT (finding BUILD).
export const BASE = process.env.PARCOURS_BASE || 'http://127.0.0.1:8795'
export const PILOTE_PW = process.env.LABUSE_AUTH_PASSWORD || 'parcours-vic-2026'

const PW = process.env.PW_PKG || 'playwright'
const _pwmod = await import(PW)
export const pw = _pwmod.chromium ? _pwmod : (_pwmod.default || _pwmod)

// macOS 13 : playwright 1.62 ne peut pas télécharger chromium — on pointe l'exécutable
// chromium-1217 déjà installé (celui du serveur MCP). Surchargaeable par CHROME_EXE.
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
  const { seq, device, name, url, verdict } = obj
  console.log(`  [${device || '-'}] ${seq != null ? '#' + seq + ' ' : ''}${name}  ${url || ''} ${verdict ? '→ ' + verdict : ''}`)
}

// Capture numérotée : captures/<device>/NN-slug.png
export async function capture(page, device, seq, slug, { fullPage = false } = {}) {
  const dir = resolve(ROOT, 'captures', device)
  mkdirSync(dir, { recursive: true })
  const nn = String(seq).padStart(2, '0')
  const file = resolve(dir, `${nn}-${slug}.png`)
  await page.screenshot({ path: file, fullPage })
  return file
}

// Capture d'un mail (HTML ou texte rendu) sous mails/NN-slug.png
export async function captureMail(page, seq, slug, { fullPage = true } = {}) {
  const dir = resolve(ROOT, 'mails')
  mkdirSync(dir, { recursive: true })
  const nn = String(seq).padStart(2, '0')
  const file = resolve(dir, `${nn}-${slug}.png`)
  await page.screenshot({ path: file, fullPage })
  return file
}

// Sonde l'état d'une page : url, titre, h1/h2, boutons visibles, 1res erreurs console.
export async function probe(page, errors) {
  const url = page.url()
  const title = await page.title().catch(() => '')
  const headings = await page.locator('h1,h2').allInnerTexts().catch(() => [])
  const buttons = await page.getByRole('button').allInnerTexts().catch(() => [])
  const bodyText = (await page.locator('body').innerText().catch(() => '')).slice(0, 2000)
  return { url, title, headings: headings.slice(0, 12), buttons: buttons.filter(Boolean).slice(0, 40), errors: (errors || []).slice(0, 20), bodyText }
}

// Contexte navigateur avec collecte d'erreurs console + requêtes échouées.
export async function makeContext(browser, viewport) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 2, locale: 'fr-FR', timezoneId: 'Indian/Reunion' })
  const errors = []
  ctx.on('weberror', (e) => errors.push('weberror: ' + e.error().message))
  return { ctx, errors }
}

export function attachPageErrors(page, errors) {
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text().slice(0, 300)) })
  page.on('pageerror', (e) => errors.push('pageerror: ' + e.message.slice(0, 300)))
  page.on('requestfailed', (r) => errors.push('reqfailed: ' + r.url().slice(0, 120) + ' ' + (r.failure()?.errorText || '')))
}

// Login pilote (= admin de fait, sans TOTP) : POST /login identifiant vide.
export async function loginVic(page, errors) {
  await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded' })
  await page.fill('input[name="password"]', PILOTE_PW)
  // identifiant laissé vide = voie pilote
  await Promise.all([page.waitForLoadState('networkidle').catch(() => {}), page.click('button[type="submit"]')])
  return probe(page, errors)
}

// Login client : identifiant + password.
export async function loginClient(page, email, password, errors) {
  await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded' })
  await page.fill('input[name="identifiant"]', email)
  await page.fill('input[name="password"]', password)
  await Promise.all([page.waitForLoadState('networkidle').catch(() => {}), page.click('button[type="submit"]')])
  return probe(page, errors)
}

export async function gotoAdmin(page) {
  await page.goto(BASE + '/socle/#admin=1', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(800)
}

export function now() { return Date.now() }
