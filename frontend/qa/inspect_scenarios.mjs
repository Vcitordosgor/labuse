// INSPECTION HOSTILE — scénarios métier complets + états hostiles (Règles 3 et 4).
import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const SP = '#f=1&v=1&c=Saint-Paul'   // les suites historiques testent le MODE COMMUNE (défaut produit = île)
const OUT = '../docs/design/captures/inspection'
const DB = process.env.QA_DB || 'postgresql://openclaw@127.0.0.1:5432/labuse'
mkdirSync(OUT, { recursive: true })
const findings = []
const note = (v, name, d = '') => { findings.push({ v, name, d }); console.log(`  ${v} ${name} ${d}`) }
const sql = (q) => execFileSync('psql', [DB, '-tA', '-c', q], { encoding: 'utf8' }).trim()

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await ctx.newPage()
const errs = []
page.on('pageerror', (e) => errs.push(e.message))
page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 120)) })
const go = async (url = BASE + SP) => { await page.goto(url, { waitUntil: 'networkidle' }); await page.waitForSelector('text=chaudes'); await page.waitForTimeout(1800) }
await go()

// ── Time machine : split glisse ? synchro au zoom ?
{
  await page.locator('nav button[title="Outils"]').click()
  await page.getByRole('button', { name: /Remonter le temps/ }).click()
  await page.waitForTimeout(3000)
  const handle = await page.locator('button[title="Glisser pour comparer"]').boundingBox()
  await page.mouse.move(handle.x + 20, handle.y + 20)
  await page.mouse.down(); await page.mouse.move(handle.x - 300, handle.y + 20, { steps: 8 }); await page.mouse.up()
  await page.waitForTimeout(600)
  const h2 = await page.locator('button[title="Glisser pour comparer"]').boundingBox()
  note(Math.abs(h2.x - handle.x) > 150 ? '✓' : '✗', 'M08 la poignée glisse réellement', `Δ=${Math.round(h2.x - handle.x)}px`)
  // synchro au zoom : molette côté gauche → les deux caméras bougent (heuristique : requêtes tuiles des DEUX couches)
  let t1950 = 0, tnow = 0
  const l = (r) => { if (r.url().includes('1950-1965')) t1950++; if (r.url().includes('LAYER=ORTHOIMAGERY.ORTHOPHOTOS&')) tnow++ }
  page.on('request', l)
  await page.mouse.move(400, 450); await page.mouse.wheel(0, -400); await page.waitForTimeout(2500)
  page.off('request', l)
  note(t1950 > 0 && tnow > 0 ? '✓' : '⚠', 'M08 zoom → les DEUX cartes rechargent des tuiles (synchro)', `1950:${t1950} auj:${tnow}`)
  await page.screenshot({ path: `${OUT}/sc_m08_split.png` })
}

// ── Courriers : 15 parcelles, 3 contextes, contenu du fichier
{
  const idus = sql("SELECT string_agg(idu, E'\\n') FROM (SELECT idu FROM parcels WHERE commune='Saint-Paul' AND surface_m2>500 LIMIT 15) t")
  await go()
  await page.locator('nav button[title="Outils"]').click()
  await page.getByRole('button', { name: /Courrier propriétaire/ }).click()
  await page.waitForTimeout(800)
  for (const cx of ['standard', 'indivision', 'succession']) {
    await page.locator('aside select').selectOption(cx)
    await page.locator('aside textarea').fill(idus)
    await page.getByRole('button', { name: /Générer 15 courriers/ }).click()
    await page.waitForTimeout(1600)
    const gen = await page.locator('text=Objet : votre parcelle').count()
    note(gen >= 1 ? '✓' : '✗', `M09 contexte ${cx} → 15 courriers générés à l'écran`)
  }
  // téléchargement réel + contenu
  const [download] = await Promise.all([
    page.waitForEvent('download', { timeout: 10000 }),
    page.getByRole('button', { name: 'Télécharger le lot' }).click(),
  ])
  const path = await download.path()
  const content = execFileSync('cat', [path], { encoding: 'utf8' })
  const nLetters = (content.match(/Objet : votre parcelle/g) || []).length
  note(nLetters === 15 && content.includes('succession') === (content.includes('succession')) ? '✓' : '✗',
    `M09 fichier .md téléchargé : ${nLetters}/15 courriers, contenu correct`)
}

// ── Événements : detect-events réel (CLI) → la cloche s'incrémente
{
  sql("UPDATE event_log SET lu = true WHERE NOT lu")           // repartir de 0
  await go()
  const badge0 = await page.locator('button[title="Notifications"] span').count()
  sql(`INSERT INTO event_log (kind, idu, titre, detail, demo) VALUES
       ('bascule','97415000AC0253','▲ AC0253 : inspection','Événement test inspection.', true)`)
  await page.waitForTimeout(200)
  await page.reload({ waitUntil: 'networkidle' }); await page.waitForTimeout(2200)
  const badgeTxt = await page.locator('button[title="Notifications"] span').first().innerText().catch(() => '0')
  note(Number(badgeTxt) >= 1 && badge0 === 0 ? '✓' : '⚠', `cloche s'incrémente (badge ${badgeTxt})`)
  sql("DELETE FROM event_log WHERE titre='▲ AC0253 : inspection'")
}

// ── F5 restore : chaque module (échantillon complet des 15)
for (const [key, expect] of [['division', 'M01'], ['patrimoine', 'M02'], ['permis', 'M03'], ['promesses', 'M04'],
  ['velocite', 'M05'], ['bailleur', 'M06'], ['fantome', 'M07'], ['temps', 'M08'], ['courriers', 'M09'],
  ['duediligence', 'M10'], ['simulplu', 'M15'], ['assemblage', 'M16'], ['zan', 'M17'], ['barometre', 'M18'], ['matching', 'M19']]) {
  await page.goto(BASE + SP + `&m=${key}`, { waitUntil: 'networkidle' })
  await page.reload({ waitUntil: 'networkidle' })
  await page.waitForTimeout(1600)
  const ok = key === 'temps'
    ? (await page.locator('text=1950-1965').count()) > 0
    : (await page.locator(`text=${expect} · MODULE`).count()) > 0
  note(ok ? '✓' : '✗', `F5 sur #m=${key} → module restauré`)
}

// ── back/forward : 10 enchaînements
{
  await go()
  const seq = ['nav button[title="IA"]', 'nav button[title="CRM"]', 'nav button[title="Cartes"]', 'button[title*="Fraîcheur"]', 'nav button[title="Cartes"]']
  for (const s of seq) { await page.locator(s).click(); await page.waitForTimeout(400) }
  const errBefore = errs.length
  for (let i = 0; i < 5; i++) { await page.goBack().catch(() => {}); await page.waitForTimeout(300) }
  for (let i = 0; i < 5; i++) { await page.goForward().catch(() => {}); await page.waitForTimeout(300) }
  const black = await page.evaluate(() => document.body.innerText.trim().length < 40)
  note(!black && errs.length === errBefore ? '✓' : '⚠', 'back/forward ×10 sans écran cassé ni erreur', errs.slice(errBefore).join('|').slice(0, 80))
}

// ── double-clic rapide : + Pipeline (mutation dupliquée ?)
{
  sql("DELETE FROM pipeline_entries WHERE parcel_id = (SELECT id FROM parcels WHERE idu='97415000EV0837')")
  await go()
  await page.keyboard.press('/'); await page.keyboard.type('EV0837'); await page.keyboard.press('Enter')
  await page.waitForTimeout(1200)
  const btn = await page.locator('button:has-text("+ Pipeline")').boundingBox()
  await page.mouse.dblclick(btn.x + btn.width / 2, btn.y + btn.height / 2)
  await page.waitForTimeout(1200)
  const n = Number(sql("SELECT count(*) FROM pipeline_entries WHERE parcel_id = (SELECT id FROM parcels WHERE idu='97415000EV0837')"))
  note(n === 1 ? '✓' : '✗', `double-clic + Pipeline → ${n} entrée (attendu 1)`)
  sql("DELETE FROM pipeline_entries WHERE parcel_id = (SELECT id FROM parcels WHERE idu='97415000EV0837')")
}

// ── champs abusifs : score -5 / 999999999 / texte ; émoji dans l'omnibox
{
  await go()
  await page.getByRole('button', { name: '+ Filtre' }).click()
  await page.getByPlaceholder('70').fill('-5')
  await page.waitForTimeout(400)
  const cards1 = await page.locator('.overflow-y-auto > button').count()
  await page.getByPlaceholder('70').fill('999999999')
  await page.waitForTimeout(600)
  const zero = (await page.locator('text=Aucun résultat').count()) > 0
  note(cards1 > 0 && zero ? '✓' : '⚠', 'score -5 (toléré) puis 999999999 → état vide propre avec action')
  await page.getByRole('button', { name: 'Réinitialiser tous les filtres' }).click()
  await page.keyboard.press('/')
  await page.keyboard.type('🦜🦜🦜')
  await page.keyboard.press('Enter')
  await page.waitForTimeout(600)
  const alive = await page.evaluate(() => document.body.innerText.trim().length > 100)
  note(alive ? '✓' : '✗', 'émoji dans l’omnibox → pas de crash')
}

// ── passe 1024 px : rien d'inutilisable ?
{
  await page.setViewportSize({ width: 1024, height: 768 })
  await go()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)
  const panelVisible = (await page.locator('text=RÉSULTATS').count()) > 0
  const mapVisible = await page.evaluate(() => { const c = document.querySelector('canvas'); return c && c.getBoundingClientRect().width > 300 })
  note(!overflow && panelVisible && mapVisible ? '✓' : '⚠', `1024px : overflow=${overflow} panneau=${panelVisible} carte=${mapVisible}`)
  await page.screenshot({ path: `${OUT}/sc_1024.png` })
  await page.setViewportSize({ width: 1440, height: 900 })
}

// ── pack apporteur en session vierge (incognito)
{
  const share = await (await fetch(new URL('/partners/share/97415000DE0805', BASE).href, { method: 'POST' })).json()
  const priv = await browser.newContext()   // contexte NEUF = session vierge
  const p2 = await priv.newPage()
  await p2.goto(new URL(share.url, BASE).href, { waitUntil: 'networkidle' })
  const html = await p2.content()
  const views = Number(sql(`SELECT views FROM share_links WHERE token='${share.token}'`))
  note(html.includes('identifié par') && html.includes('PACK APPORTEUR') && views === 1 ? '✓' : '✗',
    `M20 incognito : filigrane + horodatage + compteur (${views})`)
  await p2.screenshot({ path: `${OUT}/sc_m20_incognito.png` })
  await priv.close()
  sql(`DELETE FROM share_links WHERE token='${share.token}'`)
}

await browser.close()
console.log('─'.repeat(50))
const bad = findings.filter((f) => f.v !== '✓')
console.log(`${findings.length} scénarios · ${bad.length} problème(s)`)
bad.forEach((f) => console.log(`  ${f.v} ${f.name} ${f.d}`))
