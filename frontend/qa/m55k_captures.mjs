// M55-K — captures + non-régression (dev :5173). cd frontend && node qa/m55k_captures.mjs
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'
const OUT = '../reports/m55-k/captures'; const BASE = 'http://localhost:5173/socle/'
mkdirSync(OUT, { recursive: true })
const b = await chromium.launch({ channel: 'chrome' })
const errors = []
const np = async (w=1440,h=900) => { const p = await b.newPage({ viewport:{width:w,height:h} }); p.on('console',m=>{if(m.type()==='error')errors.push(m.text())}); return p }
const sect = p => p.evaluate(() => { const a=document.querySelector('aside'); return {c:!!a?.querySelector('[data-couches-drawer]'),f:!!a?.querySelector('[data-filtres-drawer]')} })

// K1 : jeu MIXTE (île) — ventilation juste, somme boucle, pas de ligne synthèse/filtres actifs
{ const p = await np(); await p.goto(BASE,{waitUntil:'networkidle',timeout:60000}); await p.waitForTimeout(2200)
  await p.locator('[data-filtres-toggle]').click(); await p.waitForTimeout(500)
  await p.locator('[data-analyser-btn]').click(); await p.waitForTimeout(3600)
  await p.locator('[data-voir-parcelles]').click(); await p.locator('[data-results-scroll] > button').first().waitFor({timeout:30000}); await p.waitForTimeout(4000)
  const panel = await p.locator('[data-results-panel]').innerText()
  const vent = await p.locator('[data-results-panel] p.mt-3').first().innerText()
  const N = s => parseInt(s.replace(/[^\d]/g,''))
  const p6 = [...vent.matchAll(/([\d  ]+) (?:brûlantes|chaudes|potentiel long terme|à creuser|potentiel épuisé|écartées)/g)].map(m=>N(m[1]))
  console.log('K1 ventilation:', vent.replace(/\n/g,' '))
  console.log('K1 somme boucle:', p6.reduce((a,c)=>a+c,0), '(attendu 431663) · synthèse absente:', !/opportunités détectées/.test(panel), '· filtres actifs absent:', !/filtres actifs/.test(panel))
  await p.close() }

// K2 : deux boutons une ligne au panneau le plus étroit
{ const p = await np(700,900); await p.goto(BASE,{waitUntil:'networkidle',timeout:60000}); await p.waitForTimeout(2200)
  await p.locator('[data-filtres-toggle]').click(); await p.waitForTimeout(500)
  await p.locator('[data-analyser-btn]').click(); await p.waitForTimeout(3600)
  await p.locator('[data-voir-parcelles]').click(); await p.waitForTimeout(1500)
  const c = await p.locator('[data-algo-open]'); const s = await p.locator('[data-scoring-open]')
  const uneLigne = await c.evaluate((el,sib)=>{ const lh=parseFloat(getComputedStyle(el).lineHeight)||14; return el.getBoundingClientRect().height<=lh*1.6 && Math.abs(el.getBoundingClientRect().top - document.querySelector('[data-scoring-open]').getBoundingClientRect().top)<2 }, null)
  console.log('K2 (panneau 240px) — classement:', JSON.stringify(await c.innerText()), '· scoring:', JSON.stringify(await s.innerText()), '· une ligne côte à côte:', uneLigne)
  await p.close() }

// accordéon invariant (K5 a touché les sections) : défaut A, analyse→B, page fraîche→A
{ const p = await np(); await p.goto(BASE,{waitUntil:'networkidle',timeout:60000}); await p.waitForTimeout(2200)
  const s0 = await sect(p); console.log('accordéon défaut (A couches):', s0.c && !s0.f)
  await p.locator('[data-filtres-toggle]').click(); await p.waitForTimeout(400)
  await p.locator('[data-analyser-btn]').click(); await p.waitForTimeout(3600)
  await p.locator('[data-voir-parcelles]').click(); await p.waitForTimeout(1200)
  const s1 = await sect(p); console.log('accordéon après analyse (B filtres):', s1.f && !s1.c, '· invariant 1 section:', (s1.c?1:0)+(s1.f?1:0)===1)
  await p.close() }
{ const p = await np(); await p.goto(BASE+'#f=1&smin=2000',{waitUntil:'networkidle',timeout:60000}); await p.waitForTimeout(2200)
  const s = await sect(p); console.log('accordéon page fraîche (A):', s.c && !s.f)
  await p.close() }

// persistance filtres après rechargement
{ const p = await np(); await p.goto(BASE,{waitUntil:'networkidle',timeout:60000}); await p.waitForTimeout(2200)
  await p.locator('[data-filtres-toggle]').click(); await p.waitForTimeout(400)
  await p.locator('button:has-text("97400")').first().click(); await p.waitForTimeout(600)
  await p.reload({waitUntil:'networkidle'}); await p.waitForTimeout(2200)
  console.log('persistance filtres (URL c=Saint-Denis):', /Saint-Denis|97400/.test(decodeURIComponent(p.url())))
  await p.close() }

console.log('console errors:', errors.length, errors.slice(0,4).join(' | '))
await b.close()
