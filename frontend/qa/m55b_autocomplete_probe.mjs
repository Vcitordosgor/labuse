// M55-B point 1 — sonde : la requête d'autocomplétion part-elle, et que renvoie-t-elle ?
import { chromium } from 'playwright'
const browser = await chromium.launch({ channel: 'chrome' })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const net = []
page.on('response', async (r) => {
  if (r.url().includes('/adresses/autocomplete')) {
    const ct = r.headers()['content-type'] || ''
    let n = null
    try { if (ct.includes('json')) n = (await r.json()).features?.length } catch {}
    net.push({ url: r.url().replace(/^https?:\/\/[^/]+/, ''), status: r.status(), ct: ct.slice(0, 30), features: n })
  }
})
await page.goto('http://localhost:5173/socle/', { waitUntil: 'networkidle', timeout: 60000 })
await page.waitForTimeout(1500)
const omni = page.locator('[data-omnibox]').first()
await omni.click()
await omni.type('3 chemin de la citerne', { delay: 40 })
await page.waitForTimeout(1500)
const suggestions = await page.locator('[role="listbox"] [role="option"]').count()
console.log('requêtes /adresses/autocomplete:', JSON.stringify(net, null, 0))
console.log('suggestions visibles:', suggestions)
await browser.close()
