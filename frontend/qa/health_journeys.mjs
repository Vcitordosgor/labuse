import { chromium } from 'playwright'
const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const OUT = '../reports/health-check-post-m6/captures'
const b = await chromium.launch()
const pg = await b.newPage({ viewport: { width: 1440, height: 900 } })
const errs = []
pg.on('console', m => { if (m.type()==='error' && !/cartocdn|glyphs|fonts/i.test(m.text())) errs.push(m.text().slice(0,120)) })
pg.on('pageerror', e => errs.push('PAGEERROR '+String(e).slice(0,120)))
const R = { journeys: {}, console_errors: [] }

// §3b — carte : clic parcelle → popup = fiche (tier)
await pg.goto(BASE+'#f=1&v=1', { waitUntil:'networkidle', timeout:60000 }); await pg.waitForTimeout(3000)
// ouvrir la fiche AB1908 pour connaître son tier de référence
await pg.fill('input[title^="Recherche du dashboard"]','97423000AB1908'); await pg.keyboard.press('Enter'); await pg.waitForTimeout(4000)
const ficheTier = await pg.evaluate(()=> (document.querySelector('[data-badge-verdict]')?.innerText||'').replace(/\s+/g,' ').trim())
await pg.screenshot({ path:`${OUT}/hj-fiche-ref.png` })
// clic sur la parcelle au centre carte (elle est sélectionnée/centrée) → popup
await pg.waitForTimeout(1500)
await pg.mouse.click(720, 450); await pg.waitForTimeout(2500)
const popupTxt = await pg.evaluate(()=> (document.querySelector('.maplibregl-popup, .labuse-popup')?.innerText||'').replace(/\s+/g,' ').trim().slice(0,120))
await pg.screenshot({ path:`${OUT}/hj-popup.png` })
R.journeys.b = { fiche_verdict: ficheTier, popup: popupTxt }

// §3f — vue piscinistes : ouvrir Vues, activer piscinistes, compter
await pg.waitForTimeout(2000)
const vuesBtn = await pg.locator('button:has-text("Vues"), [title*="Vues"]').first()
if (await vuesBtn.count()) { await vuesBtn.click(); await pg.waitForTimeout(1500)
  const pisc = pg.locator('text=/Piscinistes/i').first()
  if (await pisc.count()) { await pisc.click(); await pg.waitForTimeout(3500) }
  await pg.screenshot({ path:`${OUT}/hj-piscinistes.png` })
  R.journeys.f = { ouvert:true, texte: (await pg.evaluate(()=>document.body.innerText.match(/Piscinistes[\s\S]{0,80}/)?.[0]||'')).replace(/\s+/g,' ').slice(0,100) }
} else R.journeys.f = { ouvert:false, note:'bouton Vues introuvable' }

R.console_errors = errs
console.log(JSON.stringify(R,null,1))
await b.close()
