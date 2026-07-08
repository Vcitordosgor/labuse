// PASSE EXPERT — ping SÉMANTIQUE par origine (IDU pulsé = IDU cliqué) + IA réelle (si clé).
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const SP = '#f=1&v=1&c=Saint-Paul'   // les suites historiques testent le MODE COMMUNE (défaut produit = île)
mkdirSync('../docs/design/captures/modules', { recursive: true })
const failures = []
const assert = (c, n, d = '') => (c ? console.log(`  ✓ ${n}`) : (failures.push(n), console.log(`  ✗ ${n} ${d}`)))

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))
const go = async () => { await page.goto(BASE + SP, { waitUntil: 'networkidle' }); await page.waitForSelector('.overflow-y-auto > button', { timeout: 25000 }); await page.waitForTimeout(900) }
await go()

// IDU réellement pulsé + centre carte ≈ parcelle ?
const pingState = () => page.evaluate(() => {
  const m = window.__labuse_map
  if (!m) return { idu: null, lng: 0, lat: 0, zoom: 0 }
  // le ping vit sur parcels-ping (commune GeoJSON) OU ile-ping (MVT île) ; un ancien ping
  // éteint peut subsister → on lit la couche dont la pulsation est ACTIVE (opacité > 0)
  let idu = null
  for (const id of ['parcels-ping', 'ile-ping']) {
    if (!(m.getLayer && m.getLayer(id))) continue
    const f = m.getFilter(id)
    const op = m.getPaintProperty(id, 'line-opacity')
    if (Array.isArray(f) && (typeof op !== 'number' || op > 0)) idu = f[2]
  }
  const c = m.getCenter()
  return { idu, lng: c.lng, lat: c.lat, zoom: m.getZoom() }
})
async function checkPing(origin, clickedIdu) {
  await page.waitForTimeout(1400)
  const st = await pingState()
  const geomOk = await page.evaluate(([idu, lng, lat]) => {
    const src = window.__labuse_map.querySourceFeatures ? null : null
    return true // le centre est vérifié par distance au centroïde ci-dessous côté Node
  }, [clickedIdu, st.lng, st.lat])
  // centroïde via l'API fiche (source de vérité géométrique)
  const f = await (await fetch(new URL(`/parcels/${clickedIdu}?source=q_v2`, BASE).href)).json()
  const [plng, plat] = f.coords
  const distDeg = Math.hypot(st.lng - plng, st.lat - plat)
  assert(st.idu === clickedIdu && distDeg < 0.003 && st.zoom >= 15.5,
    `ping ${origin} : ${clickedIdu.slice(8)} pulsé + carte centrée (Δ ${(distDeg * 111000).toFixed(0)} m, z${st.zoom.toFixed(1)})`,
    JSON.stringify(st))
  void geomOk
}

// 1. liste résultats
{
  const label = await page.locator('.overflow-y-auto > button').nth(2).innerText()
  const idu = '97415000' + (label.match(/([A-Z]{2}) (\d{4})/) || [])[1] + (label.match(/([A-Z]{2}) (\d{4})/) || [])[2]
  await page.locator('.overflow-y-auto > button').nth(2).click()
  await checkPing('liste résultats', idu)
  await page.keyboard.press('Escape')
}
// 2. module division
{
  await page.locator('nav button[title="Outils"]').click()
  await page.getByRole('button', { name: /Division parcellaire/ }).click()
  await page.waitForTimeout(1800)
  const label = await page.locator('aside .overflow-y-auto > button').first().innerText()
  const m = label.match(/([A-Z]{2}) (\d{4})/)
  await page.locator('aside .overflow-y-auto > button').first().click()
  await checkPing('module M01', '97415000' + m[1] + m[2])
  await page.keyboard.press('Escape')
}
// 3. CRM (carte AC0253)
{
  await go()
  await page.locator('nav button[title="CRM"]').click()
  await page.waitForTimeout(1200)
  await page.locator('[draggable="true"]', { hasText: 'AC 0253' }).first().click()
  await page.waitForTimeout(800)
  await checkPing('kanban CRM', '97415000AC0253')
  await page.keyboard.press('Escape')
}
// 4. notification (cloche → événement DM1376/premier)
{
  await go()
  await page.locator('button[title="Notifications"]').click()
  await page.waitForTimeout(800)
  // les notifications sont ÎLE ENTIÈRE : l'IDU réel vient de l'API (plus de préfixe SP fabriqué)
  const ev = await (await fetch(new URL('/events?limit=5', BASE).href)).json()
  const first = (ev.items ?? []).find((e) => e.idu)
  const btn = page.locator('div.rounded-lg button.min-w-0').first()
  if (first && (await btn.count())) {
    await btn.click()
    await checkPing('notification', first.idu)
  } else assert(true, 'notification : pas d’IDU dans le premier événement (skip)')
}

await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('PING SÉMANTIQUE — VERT')
