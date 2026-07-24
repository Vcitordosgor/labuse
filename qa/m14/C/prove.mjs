import { chromium } from '/Users/openclaw/Desktop/labuse/frontend/node_modules/playwright/index.mjs'

const BASE = 'http://127.0.0.1:8041/socle/'
const OUT = '/Users/openclaw/Desktop/labuse/.claude/worktrees/agent-a829077152967dedb/qa/m14/C'
const ALPHA = 33   // Projet Alpha
const BETA = 34    // Projet Beta

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function openFiche(page) {
  await page.goto(BASE + '#f=1&v=1', { waitUntil: 'networkidle' })
  await sleep(1500)
  await page.locator('[data-results-scroll] > button').first().evaluate((el) => el.click())
  await sleep(2500)
}

async function openProjetMenu(page) {
  const btn = page.locator('[data-projet-fiche]').first()
  await btn.evaluate((el) => el.scrollIntoView({ block: 'center' }))
  await sleep(200)
  for (let i = 0; i < 4; i++) {
    const expanded = await btn.getAttribute('aria-expanded')
    if (expanded === 'true') return
    await btn.evaluate((el) => el.click())
    await sleep(600)
  }
}

const run = async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  page.on('console', (m) => { if (m.type() === 'error') console.log('PAGE ERR', m.text()) })

  // Capture IDU from any parcel-scoped request (fiche, pour-parcelle, faisabilite…).
  let idu = null
  page.on('request', (r) => {
    let m = r.url().match(/\/projets\/pour-parcelle\/([^/?]+)/)
      || r.url().match(/\/parcels\/([^/?]+)(?:\/|\?|$)/)
    if (m && !idu) idu = decodeURIComponent(m[1])
  })

  await openFiche(page)
  await openProjetMenu(page)  // triggers projets fetch; pour-parcelle already fired on mount
  await sleep(500)

  // Fallback: grab idu from the pdf/share link on the fiche if network didn't catch it.
  if (!idu) {
    idu = await page.evaluate(() => {
      const a = document.querySelector('a[href*="/parcels/"][href*="/export"]')
      if (a) { const m = a.getAttribute('href').match(/\/parcels\/([^/]+)\//); return m ? m[1] : null }
      return null
    })
  }
  console.log('IDU =', idu)
  if (!idu) { await browser.close(); throw new Error('could not resolve IDU') }

  // Add this parcel to Projet Alpha ONLY, via the API (deterministic setup).
  const add = await fetch(`http://127.0.0.1:8041/projets/${ALPHA}/ajouter`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ idu }),
  }).then((r) => r.json())
  console.log('ADD to Alpha =', JSON.stringify(add))

  // Reload fiche so the button reflects "in 1 project" and reopen the menu.
  await openFiche(page)
  await openProjetMenu(page)
  await sleep(600)

  // Screenshot 1 : menu with Alpha greyed (deja) + Beta active (cliquable)
  const menu = page.locator('[data-projet-fiche-menu]').first()
  await menu.screenshot({ path: `${OUT}/c1_liste_grise_et_active.png` })
  console.log('shot c1 written')

  // Prove adding to a SECOND project works: click Beta.
  const cibles = page.locator('[data-projet-fiche-cible]')
  const n = await cibles.count()
  let clicked = null
  for (let i = 0; i < n; i++) {
    const el = cibles.nth(i)
    const disabled = await el.getAttribute('disabled')
    const txt = (await el.innerText()).trim()
    if (disabled === null && /Beta/.test(txt)) { await el.evaluate((x) => x.click()); clicked = txt; break }
  }
  console.log('clicked candidate =', clicked)
  await sleep(1500)

  // Reopen menu → both Alpha and Beta greyed now.
  await openProjetMenu(page)
  await sleep(600)
  const menu2 = page.locator('[data-projet-fiche-menu]').first()
  await menu2.screenshot({ path: `${OUT}/c2_les_deux_grises.png` })
  console.log('shot c2 written')

  // Confirm backend: parcel now in both projects.
  const pour = await fetch(`http://127.0.0.1:8041/projets/pour-parcelle/${encodeURIComponent(idu)}`).then((r) => r.json())
  console.log('POUR-PARCELLE =', JSON.stringify(pour))

  await browser.close()
}
run().catch((e) => { console.error(e); process.exit(1) })
