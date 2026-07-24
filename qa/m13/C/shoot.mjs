import { chromium } from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.mjs'

const BASE = 'http://127.0.0.1:8032/socle/'
const OUT = new URL('.', import.meta.url).pathname
const MODE = process.argv[2] || 'all'

// Measure horizontal overflow on document + a set of candidate containers.
async function measure(page, label) {
  return await page.evaluate((label) => {
    const res = { label, doc: {}, offenders: [] }
    const de = document.documentElement
    res.doc = { scrollWidth: de.scrollWidth, clientWidth: de.clientWidth, ok: de.scrollWidth <= de.clientWidth }
    // find every element whose own scrollWidth exceeds its clientWidth (real x-overflow)
    for (const el of document.querySelectorAll('*')) {
      const sw = el.scrollWidth, cw = el.clientWidth
      if (cw > 0 && sw - cw > 1) {
        const st = getComputedStyle(el)
        // only report elements that can actually scroll x OR clip (i.e. produce a bar / overflow)
        res.offenders.push({
          tag: el.tagName.toLowerCase(),
          cls: (el.className && el.className.toString().slice(0, 70)) || '',
          data: Object.keys(el.dataset).join(',') || '',
          sw, cw, overflowX: st.overflowX,
        })
      }
    }
    return res
  }, label)
}

function log(m) {
  console.log(`[${m.label}] doc.scrollWidth=${m.doc.scrollWidth} clientWidth=${m.doc.clientWidth} DOC_OK=${m.doc.ok}`)
  const bars = m.offenders.filter(o => o.overflowX === 'auto' || o.overflowX === 'scroll')
  console.log(`  x-overflow containers (auto/scroll) that overflow: ${bars.length}`)
  for (const o of bars) console.log(`   -> ${o.tag}.${o.cls} data[${o.data}] sw=${o.sw} cw=${o.cw} ox=${o.overflowX}`)
}

// Assert on a specific container: log scrollWidth<=clientWidth (true expected).
async function assertContainer(page, label, selector) {
  const r = await page.evaluate((sel) => {
    const el = document.querySelector(sel)
    if (!el) return { found: false }
    return { found: true, sw: el.scrollWidth, cw: el.clientWidth, ok: el.scrollWidth <= el.clientWidth }
  }, selector)
  if (!r.found) { console.log(`  [${label}] container "${selector}" NOT FOUND`); return }
  console.log(`  [${label}] container "${selector}" scrollWidth=${r.sw} clientWidth=${r.cw} scrollWidth<=clientWidth=${r.ok}`)
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
page.on('console', (msg) => { if (msg.type() === 'error') console.log('PAGE-ERR', msg.text()) })

async function shoot(name) {
  await page.screenshot({ path: `${OUT}${name}.png`, fullPage: false })
}

// ---- COUCHES (left panel drawer) ----
if (MODE === 'all' || MODE === 'couches') {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1500)
  // ensure couches drawer open
  const toggle = page.locator('[data-couches-toggle]')
  if (await toggle.count()) {
    const expanded = await toggle.getAttribute('aria-expanded')
    if (expanded !== 'true') await toggle.click()
  }
  await page.waitForTimeout(500)
  log(await measure(page, 'COUCHES'))
  await assertContainer(page, 'COUCHES', '[data-couches-drawer]')
  await shoot('couches')
}

// ---- RESULTS + TRI (verdict on) ----
if (MODE === 'all' || MODE === 'resultats') {
  await page.goto(BASE + '#f=1&v=1', { waitUntil: 'networkidle' })
  await page.waitForSelector('[data-results-scroll] > button', { timeout: 20000, state: 'attached' })
  await page.waitForTimeout(600)
  log(await measure(page, 'RESULTATS'))
  await assertContainer(page, 'RESULTATS', '[data-results-scroll]')
  await shoot('resultats')
  // tri bar lives at the top of the results panel; assert the panel (which holds the tri bar
  // + list) does not overflow horizontally.
  await assertContainer(page, 'TRI', '[data-tri-bar]')
  await assertContainer(page, 'TRI-panel', '[data-results-panel]')
  await shoot('tri')
}

// ---- FICHE (open first result) ----
if (MODE === 'all' || MODE === 'fiche') {
  await page.goto(BASE + '#f=1&v=1', { waitUntil: 'networkidle' })
  await page.waitForSelector('[data-results-scroll] > button', { timeout: 20000, state: 'attached' })
  const btn = page.locator('[data-results-scroll] > button').first()
  await btn.evaluate((el) => el.click())
  await page.waitForSelector('[data-fiche-tabs]', { timeout: 20000, state: 'attached' })
  await page.waitForTimeout(800)
  log(await measure(page, 'FICHE'))
  await assertContainer(page, 'FICHE', '[data-fiche-tabs]')
  await shoot('fiche')
}

// ---- CRM ----
if (MODE === 'all' || MODE === 'crm') {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1500)
  // click CRM in the rail
  const crm = page.getByText('CRM', { exact: true }).first()
  await crm.click()
  await page.waitForTimeout(2000)
  log(await measure(page, 'CRM'))
  await assertContainer(page, 'CRM', '[data-crm-cols]')
  // pager arrows present when >5 columns?
  const pager = await page.evaluate(() => !!document.querySelector('[aria-label="Colonnes suivantes"]'))
  console.log(`  [CRM] pager arrows present=${pager}`)
  await shoot('crm')
}

await browser.close()
console.log('DONE')
