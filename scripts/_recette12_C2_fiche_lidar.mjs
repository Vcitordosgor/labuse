// RECETTE-12 C2 — PREUVE : la hauteur MESURÉE (LiDAR HD) visible dans la fiche, au résumé du tiroir
// « Le bien » (bâti existant) ET dans le tiroir ouvert, avec la date de survol. EL0157.
import pkg from '/Users/openclaw/Desktop/labuse-recette6/frontend/node_modules/playwright/index.js'
const { chromium } = pkg
const OUT='/Users/openclaw/Desktop/labuse-recette6/docs/audit-2026-09/captures-recette-12/'
const browser = await chromium.launch({ executablePath: '/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' })
const page = await browser.newPage({ viewport: { width: 1440, height: 960 }, deviceScaleFactor: 2 })
page.on('console',(m)=>{if(m.type()==='error')console.error('PAGE-ERR',m.text().slice(0,120))})
await page.goto('http://localhost:5199/socle/', { waitUntil: 'networkidle' })
await page.waitForFunction(() => window.__labuse != null, { timeout: 20000 })
await page.evaluate((i) => window.__labuse.select(i), '97411000EL0157')
await page.waitForSelector('[data-bandeau-chiffres]', { timeout: 20000 }).catch(()=>{})
await page.waitForTimeout(1500)
// le résumé REPLIÉ de « Le bien » doit déjà montrer la hauteur mesurée
await page.locator('text=/^Le bien$/').first().scrollIntoViewIfNeeded().catch(()=>{})
await page.waitForTimeout(400)
const resume = await page.evaluate(() => {
  const els=[...document.querySelectorAll('*')].filter(e=>/faîtage .* mesuré/i.test(e.textContent||'') && e.children.length<3)
  return els.length? els[0].textContent.replace(/\s+/g,' ').trim().slice(0,160):null
})
console.log('résumé replié « Le bien » :', resume)
await page.screenshot({ path: OUT+'C2-le-bien-resume.png' })
// ouvrir « Le bien »
await page.locator('text=/^Le bien$/').first().click().catch(()=>{})
await page.waitForSelector('[data-le-bien]', { timeout: 8000 }).catch(()=>{})
await page.waitForTimeout(700)
const detail = await page.evaluate(() => {
  const b=document.querySelector('[data-le-bien]'); if(!b) return null
  const m=b.innerText.match(/Hauteur du b[âa]ti[\s\S]{0,120}/i)
  return m? m[0].replace(/\s+/g,' ').trim():null
})
console.log('détail ouvert :', detail)
try{ const el=await page.locator('[data-le-bien]').first().boundingBox()
  await page.screenshot({ path: OUT+'C2-le-bien-ouvert.png', clip: el?{x:Math.max(0,el.x-8),y:Math.max(0,el.y-48),width:el.width+16,height:Math.min(el.height+64,900)}:undefined }) }
catch{ await page.screenshot({ path: OUT+'C2-le-bien-ouvert.png' }) }
console.log('CAPTURES C2 ok'); await browser.close()
