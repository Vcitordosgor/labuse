import { chromium } from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.mjs'

const BASE = 'http://127.0.0.1:8031/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/.claude/worktrees/agent-aac5ea7478102f189/qa/m13/B'

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function main() {
  const what = process.argv[2] || 'landing'
  const browser = await chromium.launch()
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
  const page = await ctx.newPage()
  page.on('console', (m) => { if (m.type() === 'error') console.log('PAGE ERR:', m.text()) })

  if (what === 'landing') {
    await page.goto(BASE, { waitUntil: 'networkidle' })
    await sleep(1500)
    await page.screenshot({ path: `${OUT}/landing.png` })
  }

  if (what === 'b1_omnibox') {
    await page.goto(BASE, { waitUntil: 'networkidle' })
    await sleep(1500)
    const box = page.locator('[data-omnibox]')
    await box.click()
    await box.fill('general bigeard')
    await sleep(900)
    await page.screenshot({ path: `${OUT}/b1_omnibox_suggestions.png` })
    // count suggestions
    const n = await page.locator('[role="option"]').count()
    console.log('omnibox suggestions:', n)
  }

  if (what === 'b1_scoreur') {
    await page.goto(BASE, { waitUntil: 'networkidle' })
    await sleep(1500)
    // open Outils drawer, then Scorer une adresse
    await page.screenshot({ path: `${OUT}/_debug_before_outils.png` })
    // Try clicking a button that opens Outils
    const outils = page.getByText(/Outils/i).first()
    if (await outils.count()) { await outils.click(); await sleep(600) }
    await page.screenshot({ path: `${OUT}/_debug_outils_open.png` })
  }

  await browser.close()
}
main().catch((e) => { console.error(e); process.exit(1) })
