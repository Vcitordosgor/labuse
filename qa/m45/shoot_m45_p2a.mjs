// M45 (P2a) — captures du checkpoint : barre niveau 1 + interrupteur Analyse LABUSE (contraste)
// + tiroir « Puis-je construire ? ». Usage : cd frontend && node ../qa/m45/shoot_m45_p2a.mjs (API 8820).
import { chromium } from 'playwright'

const PORT = 8820
const b = await chromium.launch({ channel: 'chrome' })
const p = await b.newPage({ viewport: { width: 1280, height: 1500 } })
await p.goto(`http://127.0.0.1:${PORT}/socle`, { waitUntil: 'load', timeout: 90000 })
await p.waitForTimeout(2500)
// révéler le volet d'analyse (l'app ouvre sur la carte + intro)
try { await p.getByText(/Afficher l'analyse LABUSE/).first().click({ timeout: 8000 }) } catch (e) { console.log('reveal skip', e.message) }
await p.waitForFunction(() => document.body.innerText.includes('Réinitialiser les filtres'), { timeout: 30000 })
await p.waitForTimeout(2500)

const shot = (n) => p.screenshot({ path: `../qa/m45/screens/${n}.png`, fullPage: true }).then(() => console.log('png →', n))

// 1) état par défaut : barre niveau 1 + tiroir droit ouvert, Analyse LABUSE active
await shot('p2a_1_barre_defaut')

// 2) on pose « Constructible » + « Nu » → le compteur et le CONTRASTE bougent
for (const t of ['Constructible', 'Nu']) {
  try { await p.getByRole('button', { name: t, exact: true }).first().click({ timeout: 4000 }); await p.waitForTimeout(1500) } catch (e) { console.log('skip', t, e.message) }
}
await p.waitForTimeout(1500)
await shot('p2a_2_constructible_nu_contraste')

// 3) on COUPE l'analyse LABUSE → voie manuelle pure (le contraste disparaît, trame entière)
try { await p.getByRole('button', { name: /Analyse LABUSE/ }).first().click({ timeout: 4000 }); await p.waitForTimeout(1800) } catch (e) { console.log('skip toggle', e.message) }
await shot('p2a_3_voie_manuelle')

await b.close()
