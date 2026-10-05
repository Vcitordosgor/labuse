// SECTION C — côté client (steps 4,5,6 + sécurité 403 + gestes représentatifs + Mon compte/legal).
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { launchChromium, makeContext, attachPageErrors, loginClient, probe, capture, logStep, BASE, ROOT, DESKTOP, MOBILE } from './lib.mjs'

const ctx0 = JSON.parse(readFileSync(resolve(ROOT, 'run-logs/ctx.json'), 'utf-8'))
const TOKEN = ctx0.A_token, EMAIL = ctx0.A_email, PW = ctx0.A_pw

const browser = await launchChromium()
let seq = 0

async function run(device, viewport) {
  const { ctx, errors } = await makeContext(browser, viewport)
  const page = await ctx.newPage()
  attachPageErrors(page, errors)
  const cap = (slug, o) => capture(page, device, ++seq, slug, o)
  const L = (name, verdict, extra = {}) => logStep({ device, name, verdict, ...extra })

  // ——— STEP 4 : page de choix du mot de passe ———
  await page.goto(BASE + '/invitation?token=' + TOKEN, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(400)
  await cap('C4-invitation-page', { fullPage: true })
  let p = await probe(page, errors)
  L('invitation : page mot de passe', p.bodyText.match(/10 caractères[^\.]*/)?.[0] || 'règles ?', { url: p.url })
  // mot de passe faible
  await page.fill('#password', 'abc').catch(() => {})
  await page.check('#cgv').catch(() => {})
  await page.waitForTimeout(200)
  const cta = page.locator('#cta')
  L('mot de passe faible', (await cta.getAttribute('aria-disabled').catch(() => null)) === 'true' ? 'bouton reste désactivé (OK)' : 'bouton ACTIF (!)')
  await cap('C4-mdp-faible')
  // mot de passe valide, CGV non cochée
  await page.fill('#password', PW).catch(() => {})
  await page.uncheck('#cgv').catch(() => {})
  await page.waitForTimeout(200)
  L('CGV non cochée', (await cta.getAttribute('aria-disabled').catch(() => null)) === 'true' ? 'bouton désactivé sans CGV (OK)' : 'bouton actif sans CGV (!)')
  // succès
  await page.check('#cgv').catch(() => {})
  await page.waitForTimeout(200)
  await cap('C4-mdp-valide-cgv')
  await Promise.all([page.waitForLoadState('networkidle').catch(() => {}), page.locator('#cta').click().catch(() => {})])
  await page.waitForTimeout(800)
  p = await probe(page, errors)
  await cap('C4-apres-activation', { fullPage: true })
  L('activation (submit)', p.url.includes('login') ? 'redirige vers /login (OK)' : p.url, { url: p.url })

  // 2e usage du même lien
  await page.goto(BASE + '/invitation?token=' + TOKEN, { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(400)
  await cap('C4-lien-reutilise', { fullPage: true })
  p = await probe(page, errors)
  L('2e clic même lien', p.bodyText.match(/expiré|invalide|déjà|utilisé|connecter/i)?.[0] || 'voir capture')

  // lien invalide
  await page.goto(BASE + '/invitation?token=INVALIDE_xxx', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(300)
  await cap('C4-lien-invalide', { fullPage: true })
  p = await probe(page, errors)
  L('lien invalide/expiré', p.bodyText.match(/expiré|invalide|déjà|demander/i)?.[0] || 'voir capture')

  // ——— STEP 5 : connexion ———
  await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded' })
  await cap('C5-login-page')
  const remember = await page.getByText(/se souvenir|rester connecté/i).count().catch(() => 0)
  L('« se souvenir de moi »', remember ? 'présent' : 'ABSENT (pas de case)')
  // mauvais mot de passe
  await page.fill('input[name="identifiant"]', EMAIL)
  await page.fill('input[name="password"]', 'FauxMotDePasse!')
  await page.click('button[type="submit"]')
  await page.waitForTimeout(600)
  await cap('C5-mauvais-mdp', { fullPage: true })
  p = await probe(page, errors)
  L('mauvais mot de passe', p.bodyText.match(/incorrect|invalide|échou|réessay/i)?.[0] || 'voir capture')
  // bon login
  const ls = await loginClient(page, EMAIL, PW, errors)
  await page.waitForTimeout(1500)
  await cap('C5-apres-login', { fullPage: true })
  L('connexion réussie', ls.url.includes('socle') || ls.url.endsWith('/') ? 'entre dans l\'app' : ls.url, { url: ls.url })

  // ——— STEP 6 : première entrée (ce que voit un nouveau) ———
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(1800)
  await cap('C6-premiere-entree', { fullPage: true })
  p = await probe(page, errors)
  const voitAdmin = await page.getByRole('button', { name: 'Admin' }).count().catch(() => 0)
  L('première entrée', 'rail: ' + p.buttons.filter(Boolean).slice(0, 12).join(' | ').slice(0, 200))
  L('bouton Admin visible au client ?', voitAdmin ? '🔴 VISIBLE (fuite)' : 'absent (OK)')

  // ——— SÉCURITÉ : 5 URL admin → 403/refus ———
  for (const u of ['/admin/licences', '/admin/mails', '/admin/pilotage', '/usage/admin', '/retours']) {
    const r = await page.request.get(BASE + u).catch(() => null)
    L('URL admin ' + u, r ? ('HTTP ' + r.status() + (r.status() === 403 || r.status() === 401 ? ' (refus OK)' : ' (!)')) : 'no-resp')
  }

  // ——— gestes représentatifs (step 7 subset) ———
  // recherche adresse/commune via omnibox
  await page.getByRole('combobox').first().fill('Saint-Denis').catch(() => {})
  await page.waitForTimeout(1200)
  await cap('C7-recherche', { fullPage: true })
  // Outils
  await page.getByRole('button', { name: /^Outils$/ }).first().click().catch(() => {})
  await page.waitForTimeout(1000)
  await cap('C7-outils', { fullPage: true })
  // Copilote
  await page.getByRole('button', { name: /^Copilote$/ }).first().click().catch(() => {})
  await page.waitForTimeout(1000)
  await cap('C7-copilote', { fullPage: true })
  // Radar
  await page.getByRole('button', { name: /^Radar$/ }).first().click().catch(() => {})
  await page.waitForTimeout(1200)
  await cap('C7-radar', { fullPage: true })
  // Documents
  await page.getByRole('button', { name: /^Documents$/ }).first().click().catch(() => {})
  await page.waitForTimeout(1000)
  await cap('C7-documents', { fullPage: true })

  // ——— STEP 8 : Mon compte + légales ———
  await page.getByRole('button', { name: /Mon compte/ }).first().click().catch(() => {})
  await page.waitForTimeout(800)
  await cap('C8-mon-compte', { fullPage: true })
  p = await probe(page, errors)
  L('Mon compte', p.bodyText.slice(0, 160).replace(/\n/g, ' '))
  for (const [u, slug] of [['/cgv', 'cgv'], ['/mentions-legales', 'mentions'], ['/confidentialite', 'confidentialite']]) {
    await page.goto(BASE + u, { waitUntil: 'domcontentloaded' }).catch(() => {})
    await page.waitForTimeout(400)
    await cap('C8-legal-' + slug, { fullPage: true })
    const r = await page.request.get(BASE + u).catch(() => null)
    L('page légale ' + u, r ? 'HTTP ' + r.status() : 'no-resp')
  }

  await ctx.close()
}

try {
  await run('desktop', DESKTOP)
  logStep({ name: 'SECTION C desktop terminée', verdict: 'OK' })
} catch (e) {
  logStep({ name: 'SECTION C exception', verdict: e.message })
}
await browser.close().catch(() => {})
