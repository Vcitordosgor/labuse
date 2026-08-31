// ONBOARDING-1 (O1) — reproduction navigateur du tunnel d'invitation, derrière le rideau.
import { chromium } from 'playwright'
import fs from 'node:fs'

const LINK = process.env.LINK
const OUT = '/tmp/onb'
fs.mkdirSync(OUT, { recursive: true })
const errors = []
const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const page = await (await browser.newContext({ viewport: { width: 900, height: 900 } })).newPage()
page.on('pageerror', (e) => errors.push('PAGEERROR: ' + String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push('CONSOLE: ' + m.text()) })
page.on('requestfailed', (r) => errors.push('REQFAIL: ' + r.url() + ' — ' + (r.failure()?.errorText || '')))
page.on('response', (r) => { if (r.status() >= 400) errors.push(`HTTP ${r.status()} ${r.url()}`) })

const log = (s) => console.log(s)
// 1. ouvrir le lien
await page.goto(LINK, { waitUntil: 'networkidle' })
await page.screenshot({ path: `${OUT}/1-form.png` })
log('H1: ' + await page.locator('h1').first().innerText().catch(() => '?'))
log('bouton CTA classe: ' + await page.locator('#cta').getAttribute('class').catch(() => 'pas de #cta'))
// 2. remplir password + cocher CGV
await page.fill('#password', 'MotDePasse123!').catch((e) => errors.push('fill pwd: ' + e))
await page.check('#cgv').catch((e) => errors.push('check cgv: ' + e))
await page.waitForTimeout(400)
log('après CGV, CTA classe: ' + await page.locator('#cta').getAttribute('class').catch(() => '?'))
log('CTA aria-disabled: ' + await page.locator('#cta').getAttribute('aria-disabled').catch(() => '?'))
await page.screenshot({ path: `${OUT}/2-rempli.png` })
// 3. cliquer le bouton
await page.click('#cta').catch((e) => errors.push('click cta: ' + e))
await page.waitForTimeout(1500)
await page.screenshot({ path: `${OUT}/3-apres-submit.png` })
log('après submit URL: ' + page.url())
log('après submit H1: ' + await page.locator('h1').first().innerText().catch(() => '?'))

console.log('=== ERREURS (' + errors.length + ') ===')
errors.forEach((e) => console.log('  ' + e))
await browser.close()
