// RECETTE-12 C3 — checks parcelle en VRAI navigateur :
//  (1) EL0157 : 7,0 m faîtage · 3,0 m égout · survol sept 2023 (cf. C2)
//  (2) sans mesure : 97407000AK1074 → hauteur ESTIMÉ (BD TOPO), aucune mention LiDAR
//  (3) permis postérieur : 97411000BP0788 → « possiblement dépassé »
import pkg from '/Users/openclaw/Desktop/labuse-recette6/frontend/node_modules/playwright/index.js'
const { chromium } = pkg
const OUT='/Users/openclaw/Desktop/labuse-recette6/docs/audit-2026-09/captures-recette-12/'
const browser = await chromium.launch({ executablePath: '/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' })
const page = await browser.newPage({ viewport: { width: 1440, height: 960 }, deviceScaleFactor: 2 })
page.on('console',(m)=>{if(m.type()==='error')console.error('PAGE-ERR',m.text().slice(0,110))})
const wait=(ms)=>page.waitForTimeout(ms)
await page.goto('http://localhost:5199/socle/', { waitUntil: 'networkidle' })
await page.waitForFunction(() => window.__labuse != null, { timeout: 20000 })
const sel = async (idu) => { await page.evaluate((i)=>window.__labuse.select(i), idu); await page.waitForSelector('[data-bandeau-chiffres]',{timeout:20000}).catch(()=>{}); await wait(1500) }
const openDrawer = async (re) => { await page.locator(`text=${re}`).first().click().catch(()=>{}); await wait(700) }

// (2) SANS MESURE — AK1074 : hauteur estimé, aucun LiDAR
await sel('97407000AK1074')
await openDrawer('/^Le bien$/')
await page.waitForSelector('[data-le-bien]',{timeout:8000}).catch(()=>{})
await wait(500)
const ak = await page.evaluate(()=>{ const b=document.querySelector('[data-le-bien]'); if(!b) return null
  const m=b.innerText.match(/Hauteur du b[âa]ti[\s\S]{0,90}/i); return m?m[0].replace(/\s+/g,' ').trim():b.innerText.slice(0,120) })
console.log('AK1074 (sans mesure) :', ak, '| mention LiDAR?', /lidar|faîtage mesuré/i.test(ak||'')?'OUI(⚠)':'non')
try{ const el=await page.locator('[data-le-bien]').first().boundingBox(); await page.screenshot({path:OUT+'C3-sans-mesure-AK1074.png',clip:el?{x:Math.max(0,el.x-8),y:Math.max(0,el.y-48),width:el.width+16,height:Math.min(el.height+64,700)}:undefined}) }catch{ await page.screenshot({path:OUT+'C3-sans-mesure-AK1074.png'}) }

// (3) PERMIS POSTÉRIEUR — BP0788 : « possiblement dépassé » dans Constructibilité → Marge en hauteur
await sel('97411000BP0788')
await openDrawer('/Constructibilité/')
await wait(700)
const bp = await page.evaluate(()=>{ const m=document.body.innerText.match(/Marge en hauteur[\s\S]{0,180}/i); return m?m[0].replace(/\s+/g,' ').trim():null })
console.log('BP0788 (permis post.) :', bp, '| « possiblement dépassé »?', /possiblement dépass/i.test(bp||'')?'OUI':'non(⚠)')
await page.locator('text=/Marge en hauteur/i').first().scrollIntoViewIfNeeded().catch(()=>{})
await wait(400)
await page.screenshot({path:OUT+'C3-permis-posterieur-BP0788.png'})

// (1) EL0157 rappel (déjà en C2) — recapture le tiroir Le bien ouvert
await sel('97411000EL0157')
await openDrawer('/^Le bien$/')
await page.waitForSelector('[data-le-bien]',{timeout:8000}).catch(()=>{})
await wait(500)
const el = await page.evaluate(()=>{ const b=document.querySelector('[data-le-bien]'); const m=b.innerText.match(/Hauteur du b[âa]ti[\s\S]{0,90}/i); return m?m[0].replace(/\s+/g,' ').trim():null })
console.log('EL0157 :', el)
await browser.close(); console.log('DONE')
