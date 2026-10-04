// ORACLE-1 Lot E — extraction du texte AFFICHÉ de la fiche (tous tiroirs ouverts un à un).
// node ecran_extract.mjs <IDU> <fichier_sortie>
// Lecture seule : ouvre http://localhost:5845/socle/#idu=<IDU>, attend la fiche (2e <aside>),
// clique chaque tiroir de l'accordéon (exclusif) et concatène le texte visible du panneau.
import { chromium } from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.mjs'
import { writeFileSync } from 'node:fs'

const [idu, out] = process.argv.slice(2)
if (!idu || !out) { console.error('usage: node ecran_extract.mjs IDU out.txt'); process.exit(1) }

const browser = await chromium.launch({ executablePath: '/Users/openclaw/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell' })
const page = await browser.newPage({ viewport: { width: 1600, height: 1200 } })
page.setDefaultTimeout(30000)
await page.goto(`http://localhost:5845/socle/#idu=${idu}`, { waitUntil: 'domcontentloaded' })
// attendre que la fiche soit chargée (tuile SURFACE dans le 2e aside)
for (let i = 0; i < 50; i++) {
  const ok = await page.evaluate(() => {
    const a = [...document.querySelectorAll('aside')][1]
    return !!a && /SURFACE|ZONE/.test(a.innerText || '')
  })
  if (ok) break
  await page.waitForTimeout(3000)
}

const seen = new Set()
const chunks = []
const grab = async (etape) => {
  const t = await page.evaluate(() => {
    const a = [...document.querySelectorAll('aside')][1]
    return a ? a.innerText : ''
  })
  if (etape) chunks.push(`\n### tiroir ouvert : ${etape}`)
  for (const line of t.split('\n')) {
    const l = line.trim()
    if (l && !seen.has(l)) { seen.add(l); chunks.push(l) }
  }
}
await grab('')

// tiroirs de l'accordéon : chaque rangée cliquable du panneau (marqueur '›')
const tiroirs = await page.evaluate(() => {
  const a = [...document.querySelectorAll('aside')][1]
  if (!a) return []
  const els = [...a.querySelectorAll('button, [role=button], div')]
  const rows = els.filter(e => {
    const t = (e.innerText || '').trim()
    return t.endsWith('›') && t.length < 160 && e.querySelectorAll('button').length <= 1
  })
  // dédoublonner : garder l'élément le plus petit par texte
  const byTxt = new Map()
  for (const r of rows) {
    const k = (r.innerText || '').trim().split('\n')[0]
    if (!byTxt.has(k) || r.innerText.length < byTxt.get(k).innerText.length) byTxt.set(k, r)
  }
  window.__tiroirs = [...byTxt.values()]
  return [...byTxt.keys()]
})
console.error('tiroirs:', tiroirs.join(' | '))
for (let i = 0; i < tiroirs.length; i++) {
  try {
    await page.evaluate((i) => {
      const el = window.__tiroirs[i]
      el.scrollIntoView({ block: 'center' })
      el.click()
    }, i)
    await page.waitForTimeout(1200)
    // sous-sections repliées (« … — déplier ») du tiroir courant
    await page.evaluate(() => {
      const a = [...document.querySelectorAll('aside')][1]
      if (!a) return
      for (const e of a.querySelectorAll('button, [role=button], summary, div')) {
        const t = (e.innerText || '').trim()
        if (/déplier/i.test(t) && t.length < 80) { try { e.click() } catch {} }
      }
    })
    await page.waitForTimeout(600)
    await grab(tiroirs[i])
  } catch { /* rerender — on continue */ }
}
await grab('final')

writeFileSync(out, chunks.join('\n'))
console.log(`${idu}: ${chunks.length} lignes uniques, ${tiroirs.length} tiroirs`)
await browser.close()
