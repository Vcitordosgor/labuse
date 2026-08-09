import { chromium } from '../frontend/node_modules/playwright/index.mjs'
const BASE = (process.env.BASE || 'http://127.0.0.1:8000/socle/').replace(/\/?$/, '/')
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--ignore-gpu-blocklist', '--enable-gpu', '--use-angle=metal'] })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
await page.goto(BASE, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {})
await page.waitForTimeout(4000)
const chain = await page.evaluate(() => {
  let el = document.querySelector('.maplibregl-map')
  const out = []
  while (el && el !== document.documentElement) {
    const s = getComputedStyle(el)
    out.push({
      tag: el.tagName.toLowerCase(),
      cls: (el.className || '').toString().slice(0, 70),
      h: el.clientHeight, offH: el.offsetHeight,
      display: s.display, position: s.position,
      flex: s.flex, minH: s.minHeight, height: s.height, alignItems: s.alignItems,
    })
    el = el.parentElement
  }
  return out
})
console.log('=== chaîne d’ancêtres (.maplibregl-map → html), hauteurs ===')
for (const n of chain) console.log(`h=${String(n.h).padStart(4)} offH=${String(n.offH).padStart(4)} | ${n.display} ${n.position} flex="${n.flex}" minH=${n.minH} height=${n.height} align=${n.alignItems} | ${n.tag}.${n.cls}`)
await browser.close(); process.exit(0)
