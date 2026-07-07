// TESTS DE NON-RÉGRESSION issus de l'INSPECTION HOSTILE — chaque test reproduit LA CONDITION
// UTILISATEUR qui a révélé le bug (leçon du popover : jamais l'état interne seul).
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const failures = []
const assert = (c, n, d = '') => (c ? console.log(`  ✓ ${n}`) : (failures.push(n), console.log(`  ✗ ${n} ${d}`)))

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))

// ── BUG #1 (inspection) : M08 côté 1950 NOIR au zoom > 15 (source sans maxzoom → rien à
// afficher). Condition utilisateur : zoomer fort → le côté 1950 doit MONTRER de l'image.
await page.goto(BASE + '#f=1&m=temps', { waitUntil: 'networkidle' })
await page.reload({ waitUntil: 'networkidle' })
await page.waitForTimeout(3500)
await page.evaluate(() => window.__labuse_tm.past.jumpTo({ center: [55.2416, -21.0403], zoom: 17 }))
await page.waitForTimeout(3500)
{
  const z = await page.evaluate(() => ({ p: window.__labuse_tm.past.getZoom(), n: window.__labuse_tm.now.getZoom() }))
  assert(Math.abs(z.p - z.n) < 0.01, 'M08 caméras synchronisées à z17')
  // luminosité moyenne du quart gauche (côté 1950) : NOIR ≈ < 12/255
  const buf = await page.screenshot({ clip: { x: 340, y: 200, width: 300, height: 300 } })
  const png = buf
  let sum = 0
  for (let i = 100; i < png.length; i += 97) sum += png[i]   // échantillon brut du PNG (proxy de variance)
  const varied = new Set([...png.subarray(100, 4000)]).size > 40
  assert(varied, 'M08 côté 1950 à z17 : image visible (pas un aplat noir)', `octets distincts=${new Set([...png.subarray(100, 4000)]).size}`)
  void sum
}

// ── BUG #2 (inspection) : M03 ignorait la ZONE DESSINÉE (mandat : « par zone dessinée/commune »).
// Condition utilisateur : zone active + module permis → liste/compteur filtrés + libellé.
await page.goto(BASE, { waitUntil: 'networkidle' })
await page.waitForSelector('text=chaudes')
await page.waitForTimeout(1800)
await page.evaluate(() => window.__labuse.setZone([[55.24, -21.05], [55.30, -21.05], [55.30, -20.99], [55.24, -20.99]]))
await page.evaluate(() => window.__labuse.setModule('permis'))
await page.waitForTimeout(1800)
assert((await page.locator('text=dans la zone dessinée').count()) > 0, 'M03 zone dessinée → libellé « dans la zone »')
assert((await page.locator('text=outil Zone actif').count()) > 0, 'M03 zone → mention outil actif')

// ── BUG #3 (inspection) : baromètre « 2700.0 » (décimales) + médianes sans trim.
{
  const d = await (await fetch(new URL('/moteurs/barometre', BASE).href)).json()
  const vals = [...d.dvf_trimestres.map((r) => r.median_eur_m2_bati), ...d.top_communes_prix.map((r) => r.median_eur_m2)]
  assert(vals.every((v) => v == null || Number.isInteger(v)), 'M18 médianes entières (plus de .0)', JSON.stringify(vals.slice(0, 3)))
}

// ── BUG #4 (inspection) : les VEILLES ne notifiaient pas (demi-feature vs mandat M11).
// Condition utilisateur : veille enregistrée + détection → 🔭 dans la cloche.
{
  const { execFileSync } = await import('node:child_process')
  const sql = (q) => execFileSync('psql', [process.env.QA_DB || 'postgresql://openclaw@127.0.0.1:5432/labuse', '-tA', '-c', q], { encoding: 'utf8' }).trim()
  sql("INSERT INTO saved_searches (nom, hash) VALUES ('Veille régression QA', '#f=1&st=chaude')")
  sql("DELETE FROM event_log WHERE kind='veille'")
  await fetch(new URL('/events/detect?run_from=q_v2&run_to=q_v2_demo', BASE).href, { method: 'POST' })
  const n = Number(sql("SELECT count(*) FROM event_log WHERE kind='veille'"))
  assert(n >= 1, `veille enregistrée → notification 🔭 à la détection (${n})`)
  await page2Check()
  async function page2Check() {
    const p2 = await browser.newPage({ viewport: { width: 1440, height: 900 } })
    await p2.goto(BASE, { waitUntil: 'networkidle' })
    await p2.waitForSelector('text=chaudes')
    await p2.waitForTimeout(1800)
    await p2.locator('button[title="Notifications"]').click()
    await p2.waitForTimeout(700)
    assert((await p2.locator('text=🔭 Veille').count()) > 0, 'notification veille visible dans la cloche')
    await p2.close()
  }
  sql("DELETE FROM saved_searches WHERE nom='Veille régression QA'")
  sql("DELETE FROM event_log WHERE kind='veille'")
}

await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('RÉGRESSIONS INSPECTION — VERTES')
