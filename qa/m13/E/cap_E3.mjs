// M13 LOT E3 — bouton « Projet » de la fiche : ajout fiable + anti-doublon + projets grisés.
// Scénario mandat : 2 projets (E3-ALPHA, E3-BETA). On ajoute la parcelle à E3-ALPHA via l'UI, puis
// on rouvre le menu Projet → E3-ALPHA GRISÉ (déjà rattaché, non cliquable) et E3-BETA ACTIF.
import { chromium } from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.mjs'

const BASE = 'http://127.0.0.1:8034/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/.claude/worktrees/agent-af62c131e12fa9682/qa/m13/E'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } })
const page = await ctx.newPage()
page.on('console', (m) => { if (m.type() === 'error') console.log('PAGE ERR:', m.text()) })

// deep-link liste, ouvrir la 1re fiche
await page.goto(BASE + '#f=1&v=1', { waitUntil: 'networkidle' })
await sleep(1200)
await page.locator('[data-results-scroll] > button').first().evaluate((el) => el.click())
await sleep(1500)

const projetBtn = page.locator('[data-projet-fiche]').first()
await projetBtn.waitFor({ timeout: 10000 })
await projetBtn.scrollIntoViewIfNeeded()

// 1) ouvrir le menu, vérifier l'ajout FIABLE (E3-ALPHA passe à « À trier »)
await projetBtn.click()
await sleep(400)
const before = await page.locator('[data-projet-fiche-cible][data-deja="1"]').count()
console.log('E3 · grisés avant ajout (attendu 0):', before)
await page.locator('[data-projet-fiche-cible]', { hasText: 'E3-ALPHA' }).first().click()
await sleep(1000)   // invalidation projets-parcelle

// 2) rouvrir le menu → E3-ALPHA doit être grisé/désactivé, E3-BETA actif
// (le bouton rouvre toujours le menu, même déjà rattaché — E3.)
await projetBtn.click()
await sleep(600)
const menu = page.locator('[data-projet-fiche-menu]')
await menu.waitFor({ timeout: 5000 })

const alpha = page.locator('[data-projet-fiche-cible]', { hasText: 'E3-ALPHA' }).first()
const beta = page.locator('[data-projet-fiche-cible]', { hasText: 'E3-BETA' }).first()
const alphaDeja = await alpha.getAttribute('data-deja')
const alphaDisabled = await alpha.isDisabled()
const betaDeja = await beta.getAttribute('data-deja')
const betaDisabled = await beta.isDisabled()
console.log('E3 · ALPHA data-deja:', alphaDeja, 'disabled:', alphaDisabled, '(attendu 1 / true)')
console.log('E3 · BETA  data-deja:', betaDeja, 'disabled:', betaDisabled, '(attendu null / false)')

// preuve anti-doublon back : re-tenter l'ajout à ALPHA renverrait already=true (grisé le bloque en UI)
await menu.screenshot({ path: `${OUT}/e3_projets_grises.png` })

await browser.close()
console.log('DONE E3')
