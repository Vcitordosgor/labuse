// AUTO-QA VAGUE 3 — événements : job → notification démo → cloche → lu ; veille ; suivi ; digest ; badges CRM.
import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const BASE = process.env.BASE || 'http://127.0.0.1:8010/socle/'
const SP = '#f=1&c=Saint-Paul'   // les suites historiques testent le MODE COMMUNE (défaut produit = île)
const OUT = process.env.OUT || '../docs/design/captures/modules'
const DB = process.env.QA_DB || 'postgresql://openclaw@127.0.0.1:5432/labuse'
mkdirSync(OUT, { recursive: true })
const failures = []
const assert = (c, n, d = '') => (c ? console.log(`  ✓ ${n}`) : (failures.push(n), console.log(`  ✗ ${n} ${d}`)))
const sql = (q) => execFileSync('psql', [DB, '-tA', '-c', q], { encoding: 'utf8' }).trim()

// job (le système DOIT vivre) : re-seed démo → événements présents
const seed = await (await fetch(new URL('/events/demo', BASE).href, { method: 'POST' })).json()
assert(seed.events.bascule >= 0 && seed.run_demo === 'q_v2_demo', 'job démo tourne (run étiqueté)')
const evCount = Number(sql("SELECT count(*) FROM event_log WHERE demo"))
assert(evCount >= 8, `événements démo en base (${evCount})`)

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 })
page.on('pageerror', (e) => failures.push('PAGEERROR ' + e.message))
await page.goto(BASE + SP, { waitUntil: 'networkidle' })
await page.waitForSelector('text=chaudes')
await page.waitForTimeout(2200)

// M11 — cloche : badge + panneau + étiquette DÉMO + marquer lu
const unreadBefore = Number(sql('SELECT count(*) FROM event_log WHERE NOT lu'))
assert(unreadBefore > 0, `événements non lus (${unreadBefore})`)
await page.locator('button[title="Notifications"]').click()
await page.waitForTimeout(800)
assert((await page.locator('text=NOTIFICATIONS ·').count()) > 0, 'cloche → panneau notifications')
assert((await page.locator('span:has-text("DÉMO")').count()) > 0, 'événements étiquetés DÉMO')
await page.screenshot({ path: `${OUT}/m11_notifications.png` })
await page.locator('button[title="Marquer lu"]').first().click()
await page.waitForTimeout(700)
const unreadAfter = Number(sql('SELECT count(*) FROM event_log WHERE NOT lu'))
assert(unreadAfter === unreadBefore - 1, `marquer lu → SQL décrémenté (${unreadBefore}→${unreadAfter})`)

// M11 — veille : nommer la recherche courante
await page.locator('input[placeholder*="Nommer"]').fill('Chaudes vue mer (test QA)')
await page.getByRole('button', { name: '+ Veille' }).click()
await page.waitForTimeout(700)
assert(Number(sql("SELECT count(*) FROM saved_searches WHERE nom LIKE 'Chaudes vue mer%'")) >= 1, 'veille enregistrée (SQL)')
assert((await page.locator('text=Chaudes vue mer (test QA)').count()) > 0, 'veille listée dans le panneau')
await page.mouse.click(400, 500)

// M13 — digest HTML email-ready
const dig = await page.request.get(new URL('/events/digest.html', BASE).href)
const html = await dig.text()
assert(dig.status() === 200 && html.includes('chasse au trésor') && html.includes('TOP 5 CHAUDES'), 'digest HTML généré')

// M14 — suivi de cible depuis la fiche
await page.keyboard.press('/')
await page.keyboard.type('DE0805')
await page.keyboard.press('Enter')
await page.waitForTimeout(1200)
await page.locator('button[title*="Suivre cette parcelle"]').click()
await page.waitForTimeout(700)
assert(Number(sql("SELECT count(*) FROM watched_parcels WHERE idu='97415000DE0805'")) === 1, 'suivi de cible → SQL')
assert((await page.locator('text=👁 Suivie').count()) > 0, 'bouton passe à « Suivie »')
await page.locator('button[title*="Suivie"]').click()   // nettoyage (toggle off)
await page.keyboard.press('Escape')

// M12 — badge kanban « N nouveaux » (AC0253 est au pipeline ; lui forger un événement non lu)
sql(`INSERT INTO event_log (kind, idu, titre, detail, demo, lu)
     VALUES ('bascule','97415000AC0253','▲ AC0253 : test badge','Événement QA (démo).', true, false)`)
await page.locator('nav button[title="CRM"]').click()
await page.waitForTimeout(1200)
assert((await page.locator('span:has-text("nouveau")').count()) > 0, 'kanban : badge « N nouveaux » (M12)')
await page.screenshot({ path: `${OUT}/m12_kanban_badge.png` })
sql("DELETE FROM event_log WHERE titre='▲ AC0253 : test badge'")
sql("DELETE FROM saved_searches WHERE nom LIKE 'Chaudes vue mer%'")

await browser.close()
console.log('─'.repeat(50))
if (failures.length) { console.log(`ROUGE — ${failures.length}`); failures.forEach((f) => console.log('  ✗ ' + f)); process.exit(1) }
console.log('VAGUE 3 — AUTO-QA VERTE')
