// ONBOARDING-1 (O4) — recette RÉELLE du tunnel d'invitation, DERRIÈRE LE RIDEAU (env pilot), captures de
// chaque étape + l'expiration/réutilisation du lien (refus propre avec /login).
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = 'http://127.0.0.1:8000'
const TOKEN = process.env.TOKEN
const OUT = '../docs/ONBOARDING-1/captures'
fs.mkdirSync(OUT, { recursive: true })
const errors = []
const browser = await chromium.launch({ executablePath: process.env.CHROME, headless: true })
const ctx = await browser.newContext({ viewport: { width: 900, height: 940 }, deviceScaleFactor: 2 })
const page = await ctx.newPage()
page.on('pageerror', (e) => errors.push('PAGEERROR: ' + String(e)))
page.on('console', (m) => { if (m.type() === 'error') errors.push('CONSOLE: ' + m.text()) })
const shot = async (n) => { await page.screenshot({ path: `${OUT}/${n}.png`, fullPage: false }); console.log('  shot', n) }
const report = {}

// 1. ouvrir le lien d'invitation (le mail mène ici)
await page.goto(`${BASE}/invitation?token=${TOKEN}`, { waitUntil: 'networkidle' })
await page.waitForTimeout(400)
await shot('1-invitation-formulaire')
report.h1_form = await page.locator('h1').first().innerText().catch(() => '?')

// 2. remplir le mot de passe + cocher les CGV → le bouton s'allume
await page.fill('#password', 'MotDePasse123!').catch((e) => errors.push('' + e))
await page.check('#cgv').catch((e) => errors.push('' + e))
await page.waitForTimeout(400)
await shot('2-mot-de-passe-cgv')
report.cta_actif = (await page.locator('#cta').getAttribute('aria-disabled').catch(() => '?')) === 'false'

// 3. créer le compte → écran « accès d'essai ouvert »
await page.click('#cta')
await page.waitForTimeout(1200)
await shot('3-acces-ouvert')
report.h1_ouvert = await page.locator('h1').first().innerText().catch(() => '?')

// 4. entrer dans LABUSE → page de login
await page.click('a.btn').catch(() => {})
await page.waitForTimeout(900)
await shot('4-login')
report.h1_login = await page.locator('h1').first().innerText().catch(() => '?')

// 5. premier login → arrivée dans l'app
await page.fill('#identifiant', 'recette@example.com').catch(() => {})
await page.fill('#password', 'MotDePasse123!').catch(() => {})
await page.click('button[type=submit]').catch(() => {})
await page.waitForTimeout(2500)
await shot('5-arrivee-app')
report.url_app = page.url()

// 6. l'expiration : réutiliser le MÊME lien (token consommé) → refus propre avec /login
const page2 = await ctx.newPage()
await page2.goto(`${BASE}/invitation?token=${TOKEN}`, { waitUntil: 'networkidle' })
await page2.waitForTimeout(400)
await page2.screenshot({ path: `${OUT}/6-lien-reutilise-refus.png` })
console.log('  shot 6-lien-reutilise-refus')
report.reuse_h1 = await page2.locator('h1').first().innerText().catch(() => '?')
report.reuse_a_login = await page2.locator('a[href="/login"]').count()

report.errors = errors.slice(0, 20)
fs.writeFileSync(`${OUT}/_report.json`, JSON.stringify(report, null, 2))
console.log('REPORT', JSON.stringify(report, null, 1))
await browser.close()
