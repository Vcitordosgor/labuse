import { chromium } from 'playwright'
const OUT = '/Users/openclaw/Desktop/labuse-sources-audit/captures/sources-audit/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const IDU = '97410000AN0347'
const br = await chromium.launch({ channel: 'chrome', headless: true, args: ['--window-size=1440,1200'] })
const p = await br.newPage({ viewport: { width: 1440, height: 1200 } })
p.on('pageerror', (e) => console.log('PAGEERROR', e.message))
await p.goto('http://localhost:5255/socle/', { waitUntil: 'domcontentloaded', timeout: 60000 })
await p.waitForFunction(() => !!window.__labuse, { timeout: 60000 })
await sleep(1200)
const ex = p.getByText('Explorer la carte', { exact: false })
if (await ex.count().catch(() => 0)) { await ex.first().click().catch(() => {}); await sleep(2500) }
await p.evaluate((idu) => window.__labuse.select(idu), IDU)
// attendre le contenu de la fiche (idu affiché + plus de "Chargement de la fiche")
await p.waitForFunction(() => {
  const a = document.querySelector('.fiche-v6'); if (!a) return false
  const loading = a.textContent.includes('Chargement de la fiche')
  const hasIdu = !!a.querySelector('[data-fiche-idu]')
  return hasIdu && !loading
}, { timeout: 25000 }).catch(()=>console.log('fiche pas prête (timeout)'))
await sleep(2500)
// déplier UNIQUEMENT les toggles d'accordéon (classe w-full) — jamais le × de fermeture
const btns = p.locator('.fiche-v6 button.w-full')
const n = await btns.count().catch(()=>0)
console.log('accordions', n)
for (let i=0;i<Math.min(n,40);i++){ await btns.nth(i).click({timeout:600}).catch(()=>{}); await sleep(120) }
await sleep(1500)
// scroll par la molette en survolant le panneau fiche (x=1240 dans les 400px de droite)
await p.mouse.move(1240, 600)
const parts = ['1_haut','2','3','4','5_bas']
for (let i=0;i<parts.length;i++){
  await p.screenshot({ path: OUT + `fiche_parcelle_${parts[i]}.png` })
  console.log('shot fiche_parcelle_'+parts[i])
  await p.mouse.wheel(0, 950); await sleep(900)
}
await br.close()
console.log('FICHE DONE')
