// M55-J — captures + non-régression (dev server :5173). cd frontend && node qa/m55j_captures.mjs
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const OUT = process.env.OUT || '../reports/m55-j/captures'
const BASE = process.env.BASE || 'http://localhost:5173/socle/'
mkdirSync(OUT, { recursive: true })
const b = await chromium.launch({ channel: 'chrome' })
const errors = []
const toN = s => s ? parseInt(s.replace(/[^\d]/g,'')) : null
const anaN = txt => { const m=txt.match(/analysé les ([\d  \s ]+) parcelles/); const r=txt.match(/([\d  \s ]+) retenues/); return { a:toN(m&&m[1]), ret:toN(r&&r[1]) } }
const newPage = async () => { const p = await b.newPage({ viewport: { width: 1440, height: 900 } }); p.on('console', m => { if (m.type()==='error') errors.push(m.text()) }); return p }
const sect = p => p.evaluate(() => { const a=document.querySelector('aside'); return { couches:!!a?.querySelector('[data-couches-drawer]'), filtres:!!a?.querySelector('[data-filtres-drawer]') } })

// ── POINT 1 : séquence bug + 3 chemins dérivés — aucun retenues>analysées ──
const bugTests = []
// (a) séquence exacte : lancer → ajouter filtre pendant revealed (bloqué : filtres masqués)
{ const p = await newPage(); await p.goto(BASE, { waitUntil:'networkidle', timeout:60000 }); await p.waitForTimeout(2200)
  await p.locator('[data-filtres-toggle]').click(); await p.waitForTimeout(500)
  await p.locator('button:has-text("97400")').first().click(); await p.waitForTimeout(400)
  await p.locator('[data-analyser-btn]').click(); await p.waitForTimeout(3600)
  const signalPresent = await p.locator('[data-signaux-vie]').count()   // 0 = masqué (gel)
  const { a, ret } = anaN(await p.locator('[data-phrase]').innerText())
  bugTests.push({ chemin:'(a) séquence bug (filtres masqués pendant analyse)', ok: ret<=a && signalPresent===0, detail:`ret=${ret} a=${a} signalMasqué=${signalPresent===0}` })
  await p.locator('[data-phrase]').locator('..').screenshot({ path:`${OUT}/p1_a_revealed.png` }).catch(()=>{})
  await p.close() }
// (b) chemin externe : header commune pendant revealed → invalidation
{ const p = await newPage(); await p.goto(BASE, { waitUntil:'networkidle', timeout:60000 }); await p.waitForTimeout(2200)
  await p.locator('[data-filtres-toggle]').click(); await p.waitForTimeout(500)
  await p.locator('button:has-text("97400")').first().click(); await p.waitForTimeout(400)
  await p.locator('[data-analyser-btn]').click(); await p.waitForTimeout(3600)
  await p.locator('[data-commune-select]').click(); await p.waitForTimeout(400)
  await p.locator('.floating').getByText('Saint-Pierre', { exact:false }).first().click(); await p.waitForTimeout(1000)
  const invalid = await p.locator('[data-analyse-perimee]').count(); const phrase = await p.locator('[data-phrase]').count()
  bugTests.push({ chemin:'(b) chemin externe (header) → invalidation', ok: invalid===1 && phrase===0, detail:`invalidée=${invalid} phraseVisible=${phrase}` })
  await p.close() }
// (c) rechargement page fraîche avec analyse active
{ const p = await newPage(); await p.goto(BASE+'#f=1&c=Saint-Denis&tv=chaude&al=1&v=1', { waitUntil:'networkidle', timeout:60000 }); await p.waitForTimeout(2500)
  await p.locator('[data-filtres-toggle]').click().catch(()=>{}); await p.waitForTimeout(800)
  const phrase = await p.locator('[data-phrase]').count(); const perimee = await p.locator('[data-analyse-perimee]').count()
  bugTests.push({ chemin:'(c) rechargement al=1 (page fraîche)', ok: phrase===0 && perimee===0, detail:`phrase=${phrase} périmée=${perimee}` })
  await p.close() }
// (d) retour arrière
{ const p = await newPage(); await p.goto(BASE, { waitUntil:'networkidle', timeout:60000 }); await p.waitForTimeout(2000)
  await p.locator('[data-filtres-toggle]').click(); await p.waitForTimeout(500)
  await p.locator('button:has-text("97400")').first().click(); await p.waitForTimeout(400)
  await p.locator('[data-analyser-btn]').click(); await p.waitForTimeout(3600)
  await p.locator('[data-voir-parcelles]').click(); await p.waitForTimeout(1200)
  await p.goBack({ waitUntil:'networkidle' }); await p.waitForTimeout(1500)
  await p.locator('[data-filtres-toggle]').click().catch(()=>{}); await p.waitForTimeout(600)
  const ph = await p.locator('[data-phrase]').count(); let ok = true
  if (ph) { const { a, ret } = anaN(await p.locator('[data-phrase]').innerText()); ok = ret==null||a==null||ret<=a }
  bugTests.push({ chemin:'(d) retour arrière', ok, detail:`phrase=${ph}` })
  await p.close() }
console.log('── POINT 1 : bug + chemins dérivés ──')
bugTests.forEach(t => console.log(`  ${t.ok?'✓':'⚠'} ${t.chemin} — ${t.detail}`))

// ── ACCORDÉON : chemins dont page fraîche ──
console.log('── ACCORDÉON ──')
{ const p = await newPage(); await p.goto(BASE, { waitUntil:'networkidle', timeout:60000 }); await p.waitForTimeout(2200)
  const s0 = await sect(p); console.log('  démarrage (défaut A couches):', s0.couches && !s0.filtres)
  await p.locator('[data-filtres-toggle]').click(); await p.waitForTimeout(400)
  await p.locator('button:has-text("97400")').first().click(); await p.waitForTimeout(400)
  await p.locator('[data-analyser-btn]').click(); await p.waitForTimeout(3600)
  await p.locator('[data-voir-parcelles]').click(); await p.waitForTimeout(1200)
  const s1 = await sect(p); console.log('  après analyse (J6 : B filtres):', s1.filtres && !s1.couches, '· invariant 1 section:', (s1.couches?1:0)+(s1.filtres?1:0)===1)
  await p.close() }
// page fraîche (pas hash-only)
{ const p = await newPage(); await p.goto(BASE+'#f=1&smin=2000', { waitUntil:'networkidle', timeout:60000 }); await p.waitForTimeout(2200)
  const s = await sect(p); console.log('  page fraîche lien partagé (A couches):', s.couches && !s.filtres, '· invariant:', (s.couches?1:0)+(s.filtres?1:0)===1)
  await p.close() }

// ── VENTILATION bouclée + persistance filtres ──
{ const p = await newPage(); await p.goto(BASE, { waitUntil:'networkidle', timeout:60000 }); await p.waitForTimeout(2200)
  await p.locator('[data-filtres-toggle]').click(); await p.waitForTimeout(500)
  await p.locator('button:has-text("97400")').first().click(); await p.waitForTimeout(400)
  await p.locator('[data-analyser-btn]').click(); await p.waitForTimeout(3600)
  await p.locator('[data-voir-parcelles]').click()
  await p.locator('[data-results-scroll] > button').first().waitFor({ timeout:30000 }); await p.waitForTimeout(4000)
  const vent = await p.locator('[data-results-panel] p.mt-3').first().innerText()
  const nums = (vent.match(/[\d  ]+/g)||[]).map(toN).filter(n=>n>0)
  console.log('── VENTILATION ──'); console.log('  ', vent.replace(/\n/g,' '))
  await p.locator('aside').first().screenshot({ path:`${OUT}/nr_analyse_complete.png` })
  // persistance : reload garde les filtres
  await p.reload({ waitUntil:'networkidle' }); await p.waitForTimeout(2500)
  await p.locator('[data-filtres-toggle]').click().catch(()=>{}); await p.waitForTimeout(800)
  const url = p.url(); console.log('  persistance filtres (URL porte c=Saint-Denis):', /Saint-Denis|97400/.test(decodeURIComponent(url)))
  await p.close() }

console.log('── console errors:', errors.length, errors.slice(0,4).join(' | '))
await b.close()
