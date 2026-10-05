// SECTION B (suite) — cycle de vie sur la fiche A (compte 90) : prolonger / suspendre / rétablir /
// renvoyer invitation, + file Courrier (échec simulé → rejouer). Captures seq 10+.
import { launchChromium, makeContext, attachPageErrors, loginVic, probe, capture, logStep, BASE, DESKTOP } from './lib.mjs'

const A_EMAIL = 'ct-parcours-a@cabinet-parcours.re'
const browser = await launchChromium()
const { ctx, errors } = await makeContext(browser, DESKTOP)
const page = await ctx.newPage()
attachPageErrors(page, errors)
let seq = 9
const cap = (slug, o) => capture(page, 'desktop', ++seq, slug, o)

async function toTour(sect) {
  if (!page.url().includes('8795')) await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(500)
  if (!(await page.getByText('TOUR DE CONTRÔLE').count().catch(() => 0))) {
    await page.getByRole('button', { name: 'Admin' }).first().click().catch(() => {})
    await page.waitForTimeout(700)
  }
  if (sect) { await page.getByRole('button', { name: new RegExp(sect) }).first().click().catch(() => {}); await page.waitForTimeout(700) }
}
async function openFicheA() {
  await toTour('Comptes')
  await page.getByRole('button', { name: /Essais/ }).first().click().catch(() => {})
  await page.waitForTimeout(500)
  const row = page.getByText(A_EMAIL).first()
  if (await row.count().catch(() => 0)) await row.click()
  else await page.getByText(/Téoulé/).first().click().catch(() => {})
  await page.waitForTimeout(800)
}

try {
  await loginVic(page, errors)
  await openFicheA()
  await cap('B-fiche-apercu', { fullPage: true })

  // Activité (file mail du compte)
  await page.getByRole('button', { name: /^Activité$/ }).first().click().catch(() => {})
  await page.waitForTimeout(700)
  await cap('B-fiche-activite', { fullPage: true })
  let p = await probe(page, errors)
  logStep({ device: 'desktop', name: 'fiche Activité (file mail du compte)', verdict: p.bodyText.match(/Brevo non configuré|a_rejouer|À rejouer|en attente|Reçu/i)?.[0] || 'voir capture' })

  // Prolonger l'essai → modale
  await page.getByRole('button', { name: /^Aperçu$/ }).first().click().catch(() => {})
  await page.waitForTimeout(300)
  await page.getByRole('button', { name: /Prolonger/ }).first().click().catch(() => {})
  await page.waitForTimeout(600)
  await cap('B-prolonger-modale', { fullPage: true })
  p = await probe(page, errors)
  logStep({ device: 'desktop', name: 'modale Prolonger', verdict: 'buttons: ' + p.buttons.slice(0, 20).join(' | ').slice(0, 200) })
  // confirmer (bouton de la modale contenant Prolonger/Confirmer/Valider)
  const confirm = page.getByRole('button', { name: /Prolonger l'essai|Prolonger de|Confirmer|Valider|Appliquer/ })
  await confirm.last().click().catch(() => {})
  await page.waitForTimeout(800)
  await cap('B-apres-prolonger', { fullPage: true })

  // Suspendre
  await page.getByRole('button', { name: /^Suspendre$/ }).first().click().catch(() => {})
  await page.waitForTimeout(600)
  await cap('B-suspendre-confirm', { fullPage: true })
  // confirmer la suspension si modale
  await page.getByRole('button', { name: /Suspendre|Confirmer|Oui/ }).last().click().catch(() => {})
  await page.waitForTimeout(800)
  await cap('B-apres-suspendre', { fullPage: true })
  p = await probe(page, errors)
  logStep({ device: 'desktop', name: 'après suspendre', verdict: p.bodyText.match(/Suspendu|suspendu|Rétablir/)?.[0] || 'voir capture' })

  // Rétablir
  await page.getByRole('button', { name: /Rétablir|Réactiver/ }).first().click().catch(() => {})
  await page.waitForTimeout(800)
  await cap('B-apres-retablir', { fullPage: true })

  // Renvoyer l'invitation
  await page.getByRole('button', { name: /Renvoyer l'invitation/ }).first().click().catch(() => {})
  await page.waitForTimeout(800)
  await cap('B-apres-renvoyer', { fullPage: true })
  p = await probe(page, errors)
  logStep({ device: 'desktop', name: 'renvoyer invitation', verdict: p.bodyText.match(/envoyée|renvoy|Brevo non configuré|dry/i)?.[0] || 'voir capture' })

  // Courrier → file globale
  await toTour('Courrier')
  await cap('B-courrier-file', { fullPage: true })
  p = await probe(page, errors)
  logStep({ device: 'desktop', name: 'Courrier (file mail)', verdict: 'buttons: ' + p.buttons.slice(0, 15).join(' | ').slice(0, 200) })

  await browser.close()
  logStep({ name: 'B-lifecycle terminé', verdict: 'OK' })
} catch (e) {
  logStep({ name: 'B-lifecycle exception', verdict: e.message })
  await cap('B-LIFECYCLE-EXCEPTION', { fullPage: true }).catch(() => {})
  await browser.close().catch(() => {})
}
