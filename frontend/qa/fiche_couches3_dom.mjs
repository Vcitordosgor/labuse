// FICHE-COUCHES-3 — visibilité DOM + capture. Fiche = accordéon (.fiche-v6), tiroirs FERMÉS au
// départ. PAGE NEUVE par couche (évite la dégradation d'état sur une page longue). On attend que la
// fiche affiche le NOUVEL idu, on cherche le needle en ouvrant chaque tiroir. Capture par couche.
import { chromium } from 'playwright'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
const OUT = '/Users/openclaw/Desktop/labuse-couches-tuyau/captures/fiche-couches3/'
mkdirSync(OUT, { recursive: true })
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const CLIP = { x: 1010, y: 0, width: 430, height: 1000 }
const DRAWERS = ['Risques et protections', 'Urbanisme', 'Dispositifs et périmètres',
  'Dispositifs territoriaux', 'Réseaux et accès', 'Marché et secteur', 'Constructibilité',
  'Le bien', 'Réhabilitation', 'Autour de cette parcelle', 'Propriétaire', 'Données et méthode']
const cfg = JSON.parse(readFileSync('/tmp/fc3_audit.json', 'utf-8'))
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1000'] })
const out = []
for (const c of cfg) {
  const rec = { kind: c.kind, idu: c.idu, needle: c.needle, dom: false, onglet: '', libelle: '' }
  if (!c.idu) { out.push(rec); continue }
  const p = await br.newPage({ viewport: { width: 1440, height: 1000 } })
  p.on('console', () => {}); p.on('pageerror', () => {})
  try {
    await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
    await p.waitForFunction(() => !!window.__labuse_map && !!window.__labuse, { timeout: 60000 })
    const b = p.getByText('Explorer la carte', { exact: false }); if (await b.count().catch(() => 0)) await b.first().click().catch(() => {})
    await sleep(2500)
    await p.evaluate((idu) => window.__labuse.select(idu), c.idu)
    // attendre que la fiche affiche CE parcelle (idu dans .fiche-v6) + le compteur cascade
    await p.waitForFunction((idu) => { const bx = document.querySelector('.fiche-v6'); return bx && (bx.textContent || '').includes(idu) && /couches? évaluées?|Aucun/.test(bx.textContent || '') }, c.idu, { timeout: 25000 }).catch(() => {})
    await sleep(1000)
    const search = (needle) => p.evaluate((n) => {
      const box = document.querySelector('.fiche-v6'); if (!box) return null
      if (!(box.textContent || '').toLowerCase().includes(n.toLowerCase())) return null
      let el = null
      for (const e of box.querySelectorAll('*'))
        if ((e.textContent || '').toLowerCase().includes(n.toLowerCase()) && e.querySelectorAll('*').length < 6) el = e
      const t = el || box; t.scrollIntoView({ block: 'center' })
      return (t.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 150)
    }, needle)
    let hit = await search(c.needle)
    if (hit) { rec.dom = true; rec.onglet = 'toujours visible'; rec.libelle = hit }
    for (let i = 0; i < DRAWERS.length && !rec.dom; i++) {
      const loc = p.locator('.fiche-v6').getByText(DRAWERS[i], { exact: false }).first()
      if (!(await loc.count().catch(() => 0))) continue
      await loc.click({ timeout: 4000 }).catch(() => {}); await sleep(480)
      hit = await search(c.needle)
      if (hit) { rec.dom = true; rec.onglet = DRAWERS[i]; rec.libelle = hit }
    }
    if (!rec.dom) {
      const r = p.locator('.fiche-v6').getByText('Risques et protections', { exact: false }).first()
      if (await r.count().catch(() => 0)) { await r.click({ timeout: 4000 }).catch(() => {}); await sleep(350) }
    }
    await p.screenshot({ path: OUT + `${c.kind}_${c.idu}.png`, clip: CLIP })
  } catch (e) { rec.err = String(e).slice(0, 80) }
  await p.close().catch(() => {})
  console.log(`${c.kind}\t${c.idu}\tdom=${rec.dom}\t${rec.onglet}${rec.err ? '\tERR ' + rec.err : ''}`)
  out.push(rec)
}
writeFileSync('/tmp/fc3_dom.json', JSON.stringify(out, null, 1))
await br.close()
console.log('OK dom', out.length)
