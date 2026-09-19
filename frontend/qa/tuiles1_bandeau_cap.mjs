// FICHE-TUILES-OUTILS-1 Lot 1 — le bandeau de six chiffres. Capture de l'en-tête + lecture de la
// tuile Risques (compteur + niveau) sur : très contrainte, simple, quasi-bénigne (réelles), + un cas
// « rien à signaler » obtenu en MOCKANT le payload (aucune parcelle réelle n'a 0 vigilance à La Réunion).
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'
const BASE = 'http://localhost:5278/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/captures/fiche-tuiles-outils1/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
mkdirSync(OUT, { recursive: true })
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1460,1100'] })
const clipTop = async (p) => { const bb = await p.locator('.fiche-v6').boundingBox(); return { x: Math.max(0, bb.x), y: 0, width: bb.width, height: 430 } }
const readRisques = (p) => p.evaluate(() => {
  const stats = [...document.querySelectorAll('[data-bandeau-chiffres] .stat')]
  const s = stats.find((e) => (e.querySelector('.stat-l')?.textContent || '').toUpperCase().includes('RISQUES'))
  if (!s) return 'ABSENT'
  return `${s.querySelector('.stat-v')?.textContent?.trim()} · ${s.querySelector('.stat-s')?.textContent?.trim() || ''}`
})
async function load(p, idu) {
  await p.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 })
  await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
  const ex = p.getByText('Explorer la carte', { exact: false }); if (await ex.count().catch(() => 0)) await ex.first().click().catch(() => {})
  await sleep(1500); await p.evaluate((i) => window.__labuse.select(i), idu)
  await p.waitForFunction((i) => { const b = document.querySelector('.fiche-v6'); const t = b && b.innerText || ''; return b && t.includes(i) && !/Chargement de la fiche/.test(t) }, idu, { timeout: 90000 }).catch(() => {})
  await sleep(1800)   // laisse l'exposition (lazy) arriver
}
for (const [key, idu] of [['1_contrainte', '97410000AN0347'], ['2_simple', '97422000AK0924'], ['3_benigne', '97407000AK1345']]) {
  const ctx = await br.newContext({ viewport: { width: 1460, height: 1100 } }); const p = await ctx.newPage()
  p.on('pageerror', (e) => console.log('pageerror', String(e).slice(0, 120)))
  await load(p, idu)
  console.log(`${key} ${idu} :: Risques = ${await readRisques(p)}`)
  await p.screenshot({ path: `${OUT}${key}_${idu}.png`, clip: await clipTop(p) })
  await ctx.close()
}
// cas « rien à signaler » : on MOCK le payload (retire les vigilances risques + aléas) — aucune
// parcelle réelle n'atteint 0 vigilance (aléa/ICPE/bruit/côtier quasi-universels à La Réunion).
{
  const ctx = await br.newContext({ viewport: { width: 1460, height: 1100 } }); const p = await ctx.newPage()
  await p.route('**/parcels/97422000AK0924*', async (route) => {
    const resp = await route.fetch(); let body
    try { body = await resp.json() } catch { return route.fallback() }
    if (Array.isArray(body?.lines)) body.lines = body.lines.filter((l) => !(l.onglet === 'risques' && (l.result === 'SOFT_FLAG' || l.result === 'HARD_EXCLUDE')))
    body.aleas = null
    route.fulfill({ response: resp, body: JSON.stringify(body), contentType: 'application/json' })
  })
  await load(p, '97422000AK0924')
  console.log(`4_rien_mock 97422000AK0924 (MOCK 0 vig) :: Risques = ${await readRisques(p)}`)
  await p.screenshot({ path: `${OUT}4_rien_a_signaler_MOCK.png`, clip: await clipTop(p) })
  await ctx.close()
}
await br.close(); console.log('DONE')
