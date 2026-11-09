// ECRANS-NOV-2 — captures WebKit (Safari) de l'écran « Analyse LABUSE par scénario » + vérification
// des règles de focus/sélection (aucun contour au CLIC, vert opaque). WebKit car Safari marque les
// champs texte :focus-visible même au clic (cf. focusModality.ts) — on le vérifie sur l'écran réel.
//   node /tmp/pw-wk/node_modules/.bin/.. (webkit 2104)  →  on importe playwright-core de /tmp/pw-wk.
import { webkit } from '/tmp/pw-wk/node_modules/playwright-core/index.mjs'

const BASE = process.env.BASE || 'http://127.0.0.1:9990/socle/'
const OUT = 'captures/ecrans-nov-2'
const wait = (ms) => new Promise((r) => setTimeout(r, ms))

const b = await webkit.launch()
const page = await b.newPage({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 2 })
const shot = (name) => page.screenshot({ path: `${OUT}/${name}.png` })

await page.goto(BASE + '#analyse=1', { waitUntil: 'networkidle' })
// consentement cookies
await page.evaluate(() => { const b = [...document.querySelectorAll('button')].find((x) => /accepter|j'accepte|ok/i.test(x.textContent || '')); if (b) b.click() })
await page.waitForSelector('[data-ecran="analyse-scenario"] [data-voir-detail]', { timeout: 15000 })
await wait(400)
await shot('webkit-01-potentiel-keep')

// ── 2. Reconstruction ──
await page.click('button:has-text("Reconstruction")')
await page.waitForFunction(() => /existant/.test(document.querySelector('[data-ecran="analyse-scenario"]')?.innerText || ''), { timeout: 10000 })
await wait(400)
await shot('webkit-02-potentiel-rebuild')

// ── 3. Prospection vente ──
await page.click('button:has-text("Prospection vente")')
await page.waitForFunction(() => /Signal/.test(document.querySelector('[data-ecran="analyse-scenario"]')?.innerText || ''), { timeout: 10000 })
await wait(400)
await shot('webkit-03-prospection')

// ── vérif FOCUS au clic : cliquer une puce ne doit poser AUCUN contour (data-input=mouse) ──
const puce = page.locator('[data-ecran="analyse-scenario"] button:has-text("Fort")').first()
await puce.click()
await wait(200)
const focusAuClic = await page.evaluate(() => {
  const el = document.activeElement
  if (!el) return { ok: true, note: 'aucun focus' }
  const s = getComputedStyle(el)
  const outline = s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0
  return { input: document.documentElement.getAttribute('data-input'), tag: el.tagName,
    outlineWidth: s.outlineWidth, outlineStyle: s.outlineStyle, aContour: outline }
})
await shot('webkit-04-prospection-fort-selection')

// ── 4. Détail (potentiel) ──
await page.click('button:has-text("Potentiel foncier")')
await page.click('button:has-text("Reconstruction")')
await page.waitForSelector('[data-voir-detail]')
await page.locator('[data-voir-detail]').first().click()
await page.waitForFunction(() => /Ce qui explique|Gain net|Capacité/.test(document.body.innerText), { timeout: 10000 })
await wait(500)
await shot('webkit-05-detail')
await page.keyboard.press('Escape')
await wait(200)

// ── 5. Comprendre ──
await page.click('[data-comprendre]')
await page.waitForFunction(() => /Comprendre l'analyse/.test(document.body.innerText), { timeout: 5000 })
await wait(300)
await shot('webkit-06-comprendre')
await page.keyboard.press('Escape')
await wait(200)

// ── 6. Filtres repliés ──
await page.click('button:has-text("Replier les filtres")')
await wait(300)
await shot('webkit-07-filtres-replies')

console.log(JSON.stringify({ focusAuClic }, null, 2))
await b.close()
