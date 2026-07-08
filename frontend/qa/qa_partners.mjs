// AUTO-QA VAGUE 5 — M19 matching · M20 pack apporteur · M21 API partenaire.
import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const SP = '#f=1&v=1&c=Saint-Paul'   // les suites historiques testent le MODE COMMUNE (défaut produit = île)
const OUT = process.env.OUT || '../docs/design/captures/modules'
const DB = process.env.QA_DB || 'postgresql://openclaw@127.0.0.1:5432/labuse'
mkdirSync(OUT, { recursive: true })
const failures = []
const assert = (c, n, d = '') => (c ? console.log(`  ✓ ${n}`) : (failures.push(n), console.log(`  ✗ ${n} ${d}`)))
const sql = (q) => execFileSync('psql', [DB, '-tA', '-c', q], { encoding: 'utf8' }).trim()

// M21 — API partenaire (clé, quota, doc)
{
  const noKey = await fetch(new URL('/api/v1/parcels', BASE).href)
  assert(noKey.status === 401, 'M21 sans clé → 401')
  const ok = await (await fetch(new URL('/api/v1/parcels?key=demo-labuse-partner-key&statut=chaude&limit=5', BASE).href)).json()
  assert(ok.count === 5 && ok.items[0].q_score >= ok.items[4].q_score, 'M21 avec clé → parcelles triées')
  const docs = await fetch(new URL('/api/v1/docs', BASE).href)
  assert(docs.status === 200 && (await docs.text()).includes('demo-labuse-partner-key'), 'M21 doc une page')
  const badKey = await fetch(new URL('/api/v1/parcels?key=nimporte', BASE).href)
  assert(badKey.status === 401, 'M21 clé inconnue → 401')
}

// M20 — partage : création, page publique filigranée, compteur
{
  const share = await (await fetch(new URL('/partners/share/97415000DE0805', BASE).href, { method: 'POST' })).json()
  const pub = await fetch(new URL(share.url, BASE).href)
  const html = await pub.text()
  assert(pub.status === 200 && html.includes('PACK APPORTEUR') && html.includes('identifié par'),
    'M20 page publique filigranée + horodatée')
  assert(html.includes('QUALITÉ') && html.includes('noindex'), 'M20 scores + noindex')
  await fetch(new URL(share.url, BASE).href)
  const views = Number(sql(`SELECT views FROM share_links WHERE token='${share.token}'`))
  assert(views === 2, `M20 compteur de consultations (${views})`)
  sql(`DELETE FROM share_links WHERE token='${share.token}'`)
}

// M19 — profils démo + matching → cloche
{
  const profiles = await (await fetch(new URL('/partners/profiles', BASE).href)).json()
  assert(profiles.filter((p) => p.demo).length >= 2, 'M19 deux profils de démo étiquetés')
  const m = await (await fetch(new URL('/partners/match/run', BASE).href, { method: 'POST' })).json()
  const evMatch = Number(sql("SELECT count(*) FROM event_log WHERE kind='match'"))
  assert(evMatch >= 1, `M19 matching → événements en cloche (${evMatch})`)
  void m
}

// UI : module M19 + bouton partage fiche
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))
await page.goto(BASE + SP, { waitUntil: 'networkidle' })
await page.waitForSelector('text=chaudes')
await page.waitForTimeout(2000)
await page.locator('nav button[title="Outils"]').click()
await page.getByRole('button', { name: /Matching promoteurs/ }).click()
await page.waitForTimeout(1200)
assert((await page.locator('aside h2', { hasText: 'Matching promoteurs' }).count()) > 0, 'M19 module ouvert')
assert((await page.locator('span:has-text("DÉMO")').count()) >= 2, 'M19 profils étiquetés DÉMO à l’écran')
await page.getByRole('button', { name: 'Tester le matching maintenant' }).click()
await page.waitForTimeout(1200)
assert((await page.locator('text=match(s) émis').count()) > 0, 'M19 bouton matching → retour visible')
await page.screenshot({ path: `${OUT}/m19_matching.png` })

await page.keyboard.press('/')
await page.keyboard.type('DE0805')
await page.keyboard.press('Enter')
await page.waitForTimeout(1200)
await page.locator('button[title*="Pack apporteur"]').click()
await page.waitForTimeout(900)
assert((await page.locator('text=LIEN APPORTEUR').count()) > 0, 'M20 bouton fiche → lien généré')
await page.screenshot({ path: `${OUT}/m20_partage.png` })
const pubUrl = await page.locator('a:has-text("/p/")').getAttribute('href')
const pub2 = await page.request.get(new URL(pubUrl, BASE).href)
assert(pub2.status() === 200, 'M20 lien de la fiche → page publique 200')

await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('VAGUE 5 — AUTO-QA VERTE')
