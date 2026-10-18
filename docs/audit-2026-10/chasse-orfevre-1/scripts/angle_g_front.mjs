// CHASSE-ORFEVRE-1 — Angle G : « les petits riens du front ».
// Parcours Playwright rejouable : visite chaque écran (app SPA :6002/socle/ + pages serveur :8802),
// collecte console / réseau >=400 / texte rendu (typo, valeurs fuyantes, pluriels, séparateurs)
// + inventaire des champs de formulaire + sondes ciblées (double-clic, champ nombre, maxlength).
// Usage : node angle_g_front.mjs            (backend :8802 et vite :6002 déjà lancés)
// Sorties : /tmp/angleg_caps/*.png (une par écran) + /tmp/angleg_report.json
// Chrome SYSTÈME obligatoire (channel:'chrome') — Chromium bundlé ne tourne pas sur ce macOS 13.
import { chromium } from '../../../../frontend/node_modules/playwright/index.mjs'
import { mkdirSync, writeFileSync } from 'node:fs'

const BASE = process.env.BASE || 'http://localhost:6002/socle/'
const API = process.env.API || 'http://127.0.0.1:8802'
const OUT = '/tmp/angleg_caps'
mkdirSync(OUT, { recursive: true })

// ── écrans ─────────────────────────────────────────────────────────────────────
const MODULES = ['plu', 'permis', 'promesses', 'communes', 'barometre', 'calculette-fonciere',
  'mon-secteur', 'patrimoine', 'veille-promoteurs', 'assemblage', 'comparer', 'risques',
  'etude-zone', 'temps', 'programme', 'gabarit', 'taxe-amenagement', 'prospection-solaire',
  'blocs-fonciers', 'successions', 'courriers']
const SCREENS = [
  { id: 'carte', url: BASE, settle: 9000 },
  { id: 'fiche-AC0428', url: `${BASE}#idu=97401000AC0428`, settle: 6000, drawers: true },
  { id: 'fiche-CR0849', url: `${BASE}#idu=97415000CR0849`, settle: 6000, drawers: true },
  { id: 'commune-st-denis', url: `${BASE}#f=1&c=Saint-Denis`, settle: 7000 },
  ...MODULES.map((m) => ({ id: `outil-${m}`, url: `${BASE}#m=${m}`, settle: 4500 })),
  { id: 'radar', url: `${BASE}#radar=1`, settle: 5000 },
  { id: 'veille-parcelles', url: `${BASE}#surveillance=parcelles`, settle: 4000 },
  { id: 'veille-criteres', url: `${BASE}#surveillance=criteres`, settle: 4000 },
  { id: 'vue-documents', url: BASE, rail: 'documents', settle: 4000 },
  { id: 'vue-copilote', url: BASE, rail: 'copilote', settle: 4000 },
  { id: 'vue-projets', url: BASE, rail: 'projets', settle: 4000 },
  { id: 'vue-crm', url: BASE, rail: 'crm', settle: 4000 },
  { id: 'vue-sources', url: BASE, rail: 'sources', settle: 5000 },
  { id: 'admin-pilotage', url: `${BASE}#admin=1`, settle: 7000 },
  ...['licences', 'donnees', 'courrier', 'radar', 'produit', 'ia', 'contacts'].map((s) => ({
    id: `admin-${s}`, url: `${BASE}#admin=1`, adminSection: s, settle: 5000 })),
  // pages rendues côté serveur (hors proxy dev) — GET seulement, aucune soumission
  { id: 'srv-login', url: `${API}/login`, settle: 1500 },
  { id: 'srv-reset', url: `${API}/reset`, settle: 1500 },
  { id: 'srv-cgv', url: `${API}/cgv`, settle: 1500 },
  { id: 'srv-invitation-sans-token', url: `${API}/invitation`, settle: 1500 },
  { id: 'srv-onboarding-retour-ok', url: `${API}/onboarding/retour?ok=1`, settle: 1500 },
  { id: 'srv-onboarding-retour-ko', url: `${API}/onboarding/retour?ok=0`, settle: 1500 },
  { id: 'srv-flash', url: `${API}/flash?idu=97401000AC0428`, settle: 1500 },
]

// ── bruit console de dev à ignorer ─────────────────────────────────────────────
const NOISE = [/\[vite\]/, /React DevTools/, /Download the React/, /react-refresh/]

// ── analyses texte ─────────────────────────────────────────────────────────────
const PLURAL_WHITELIST = new Set(['mois', 'fois', 'pas', 'accès', 'cours', 'avis', 'repas',
  'plus', 'sans', 'vers', 'temps', 'corps', 'pays', 'procès', 'permis', 'bas', 'cas',
  'gros', 'dans', 'alors', 'ans']) // mots invariables/pièges — « 1 ans » resterait signalé via regle dédiée
function analyseText(text) {
  const out = {}
  const grab = (re, cap = 8) => {
    const found = []
    let m; const r = new RegExp(re.source, re.flags.includes('g') ? re.flags : re.flags + 'g')
    while ((m = r.exec(text)) && found.length < cap) {
      const i = Math.max(0, m.index - 60)
      found.push(text.slice(i, m.index + m[0].length + 60).replace(/\s+/g, ' ').trim())
    }
    return found
  }
  out.fuyantes = grab(/\bundefined\b|\bNaN\b|\[object |Invalid Date|\bnull\b/)
  out.doubleEspace = grab(/[A-Za-zà-ü»,.] {2}[A-Za-zà-ü«]/)
  // pluriel après « 1 » : « 1 parcelles », « 1 ans »…
  const plur = []
  for (const m of text.matchAll(/(?<![\d,. ])\b1[   ]([a-zàâéèêëîïôöûüç]{2,}s)\b/gi)) {
    if (!PLURAL_WHITELIST.has(m[1].toLowerCase()) && plur.length < 10) {
      const i = Math.max(0, m.index - 50)
      plur.push(text.slice(i, m.index + m[0].length + 50).replace(/\s+/g, ' ').trim())
    }
  }
  out.plurielsFaux = plur
  out.unAnsEtc = grab(/\b1[   ](ans|parcelles|communes|zones|jours|euros)\b/)
  // apostrophe droite entre deux lettres (si la page utilise ailleurs l'apostrophe typographique)
  out.nbApostropheTypo = (text.match(/[a-zà-ü]’[a-zà-üA-Z]/g) || []).length
  out.apostropheDroite = grab(/[a-zà-üA-Z]'[a-zà-üA-Z]/)
  // espace NORMALE (sécable) avant ponctuation haute — devrait être insécable
  out.espaceSecablePonct = grab(/[a-zà-ü0-9)»%€] [;:!?](?![\/\d])/)
  // ponctuation haute COLLÉE (aucun espace) — hors URL/heures/ratios
  out.ponctCollee = grab(/[a-zà-ü][!?](?=[ \n]|$)/).filter((s) => !/https?:/.test(s))
  // nombres >= 10000 sans séparateur de milliers (hors IDU, années, codes)
  const nums = []
  for (const m of text.matchAll(/(?<![\dA-Z.,€\/-])\d{5,}(?![\d.,]|[A-Z])/g)) {
    const v = m[0]
    if (/^(19|20)\d{2}$/.test(v)) continue
    const ctx = text.slice(Math.max(0, m.index - 60), m.index + v.length + 40).replace(/\s+/g, ' ').trim()
    if (/97\d{3}|SIREN|siren|IDU|n°|id\b/.test(ctx)) continue
    if (nums.length < 10) nums.push(ctx)
  }
  out.nombresSansSeparateur = nums
  out.euros = { sym: (text.match(/€/g) || []).length, eur: (text.match(/\bEUR\b/g) || []).length, mot: (text.match(/\beuros?\b/gi) || []).length }
  out.tirets = { court: (text.match(/ - /g) || []).length, moyen: (text.match(/ – /g) || []).length, long: (text.match(/—/g) || []).length }
  return out
}

// ── boucle ─────────────────────────────────────────────────────────────────────
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const report = []
for (const sc of SCREENS) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  const consoleMsgs = new Map(), badReq = [], pageErrors = []
  page.on('console', (msg) => {
    const t = msg.type()
    if (t !== 'warning' && t !== 'error') return
    const txt = msg.text()
    if (NOISE.some((re) => re.test(txt))) return
    const k = `${t}|${txt.slice(0, 300)}`
    consoleMsgs.set(k, (consoleMsgs.get(k) || 0) + 1)
  })
  page.on('pageerror', (e) => pageErrors.push(String(e).slice(0, 300)))
  page.on('response', (r) => { if (r.status() >= 400) badReq.push(`${r.status()} ${r.url().slice(0, 160)}`) })
  page.on('requestfailed', (r) => badReq.push(`FAILED(${r.failure()?.errorText}) ${r.url().slice(0, 160)}`))
  try {
    await page.goto(sc.url, { waitUntil: 'networkidle', timeout: 45000 }).catch(() => {})
    if (sc.rail) { await page.click(`[data-rail="${sc.rail}"]`, { timeout: 8000 }).catch(() => {}) }
    if (sc.adminSection) { await page.click(`[data-admin-section="${sc.adminSection}"]`, { timeout: 10000 }).catch(() => {}) }
    await page.waitForTimeout(sc.settle)
    if (sc.drawers) { // fiche parcelle : ouvrir chaque tiroir de l'accordéon, un à un
      const ids = await page.$$eval('[data-drawer]', (els) => els.map((e) => e.getAttribute('data-drawer')))
      for (const id of ids) {
        await page.click(`[data-drawer="${id}"] button`, { timeout: 2000 }).catch(() => {})
        await page.waitForTimeout(1200)
        const txt = await page.evaluate(() => document.body.innerText)
        const a = analyseText(txt)
        if (a.fuyantes.length || a.plurielsFaux.length) {
          report.push({ screen: `${sc.id}/tiroir-${id}`, analyse: a, console: [], reseau: [] })
          await page.screenshot({ path: `${OUT}/${sc.id}-tiroir-${id}.png` }).catch(() => {})
        }
      }
    }
    const text = await page.evaluate(() => document.body.innerText)
    // inventaire formulaires (validation client)
    const champs = await page.evaluate(() => Array.from(document.querySelectorAll('input, textarea')).map((e) => ({
      tag: e.tagName.toLowerCase(), type: e.type || '', name: e.name || e.getAttribute('aria-label') || e.placeholder || '',
      maxlength: e.getAttribute('maxlength'), inputmode: e.getAttribute('inputmode'), required: e.required || false,
    })).slice(0, 60))
    await page.screenshot({ path: `${OUT}/${sc.id}.png` }).catch(() => {})
    report.push({
      screen: sc.id, url: sc.url + (sc.rail ? ` +rail:${sc.rail}` : '') + (sc.adminSection ? ` +section:${sc.adminSection}` : ''),
      console: [...consoleMsgs.entries()].map(([k, n]) => `${k}${n > 1 ? ` (×${n})` : ''}`),
      pageErrors, reseau: [...new Set(badReq)], analyse: analyseText(text), champs,
      textLen: text.length,
    })
    console.log(`✓ ${sc.id}  console:${consoleMsgs.size} http>=400:${new Set(badReq).size}`)
  } catch (e) {
    report.push({ screen: sc.id, erreur: String(e).slice(0, 300) })
    console.log(`✗ ${sc.id} ${e}`)
  }
  await page.close()
}

// ── sondes ciblées (sans effet de bord : recherche/filtres seulement) ──────────
const probe = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const probeRes = {}
try {
  const reqs = []
  probe.on('request', (r) => { if (r.url().includes('/parcels/') || r.url().includes('/adresses/')) reqs.push(r.url()) })
  await probe.goto(BASE, { waitUntil: 'networkidle', timeout: 45000 }).catch(() => {})
  await probe.waitForSelector('[data-omnibox]', { timeout: 15000 })
  // 1) double-clic rapide sur « Lancer la recherche » : double requête ?
  await probe.fill('[data-omnibox]', '97401000AC0428')
  reqs.length = 0
  const btn = await probe.$('[aria-label="Lancer la recherche"]')
  if (btn) { await btn.click(); await btn.click().catch(() => {}) }
  await probe.waitForTimeout(4000)
  probeRes.doubleClicRecherche = { requetes: reqs.filter((u) => u.includes('/parcels/')).length, detail: reqs.slice(0, 6) }
  // 2) omnibox : coller 10 000 caractères — maxlength ? plantage ?
  const big = 'A'.repeat(10000)
  await probe.fill('[data-omnibox]', big)
  probeRes.omnibox10k = await probe.$eval('[data-omnibox]', (e) => ({ lenAccepte: e.value.length, maxlength: e.getAttribute('maxlength') }))
  await probe.fill('[data-omnibox]', '')
  // 3) champs Surface min/max du panneau FILTRES : acceptent-ils du texte ?
  await probe.click('text=FILTRES', { timeout: 4000 }).catch(() => {})
  await probe.waitForTimeout(1500)
  const surf = await probe.$$('input[placeholder*="min" i], input[inputmode], input[type="number"]')
  probeRes.champsSurface = []
  for (const el of surf.slice(0, 4)) {
    const info = await el.evaluate((e) => ({ type: e.type, inputmode: e.getAttribute('inputmode'), ph: e.placeholder }))
    await el.fill('abc!!').catch(async () => { info.refusTexte = true })
    info.valeurApresTexte = await el.evaluate((e) => e.value)
    await el.fill('').catch(() => {})
    probeRes.champsSurface.push(info)
  }
  await probe.screenshot({ path: `${OUT}/probe-formulaires.png` }).catch(() => {})
} catch (e) { probeRes.erreur = String(e).slice(0, 300) }
await probe.close()

writeFileSync('/tmp/angleg_report.json', JSON.stringify({ screens: report, probes: probeRes }, null, 1))
console.log('rapport → /tmp/angleg_report.json ; captures → ' + OUT)
await browser.close()
process.exit(0)
