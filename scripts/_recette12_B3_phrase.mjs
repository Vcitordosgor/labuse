// RECETTE-12 B3 — PREUVE : la phrase du modèle en français (13,3× · 1,2 % · au 10/08/2026).
import pkg from '/Users/openclaw/Desktop/labuse-recette6/frontend/node_modules/playwright/index.js'
const { chromium } = pkg
const OUT = new URL('../docs/audit-2026-09/captures-recette-12/', import.meta.url).pathname
const browser = await chromium.launch({ executablePath: '/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' })
const page = await browser.newPage({ viewport: { width: 1440, height: 960 }, deviceScaleFactor: 2 })
page.on('console', (m) => { if (m.type() === 'error') console.error('PAGE-ERR', m.text().slice(0,120)) })
await page.goto('http://localhost:5199/socle/', { waitUntil: 'networkidle' })
await page.waitForFunction(() => window.__labuse != null, { timeout: 20000 })
await page.evaluate(() => { window.__labuse.setVerdict(true); window.__labuse.setFilters({ ...window.__labuse.getFilters(), analyseLabuse: true }) })
await page.waitForSelector('[data-score-backtest]', { timeout: 20000 })
await page.waitForTimeout(800)
const txt = await page.locator('[data-score-backtest]').first().textContent()
console.log('PHRASE:', txt.trim())
const el = await page.locator('[data-score-backtest]').first().boundingBox()
await page.screenshot({ path: `${OUT}B3-phrase-fr.png`, clip: el ? { x: Math.max(0,el.x-8), y: Math.max(0,el.y-40), width: el.width+16, height: el.height+56 } : undefined })
console.log('CAPTURE B3-phrase-fr'); await browser.close()
