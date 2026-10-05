// SECTION B — côté Vic (dashboard) : création essai, validations, fiche, file mail, cycle de vie.
// Comptes [CT-PARCOURS] à domaine NON-test (visibles dans la liste ; le prefixe [CT-PARCOURS]
// ne déclenche PAS le masquage — seuls [CT-TEST]/@labuse.test le font). Purgés en fin de session.
import { writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { pw, launchChromium, makeContext, attachPageErrors, loginVic, probe, capture, logStep, BASE, ROOT, DESKTOP, MOBILE } from './lib.mjs'

const A = { email: 'ct-parcours-a@cabinet-parcours.re', prenom: 'Rémi', nom: 'Téoulé' }
const B = { email: 'ct-parcours-b@cabinet-parcours.re', prenom: 'Soazig', nom: 'Hoarau' }

const browser = await launchChromium()
const { ctx, errors } = await makeContext(browser, DESKTOP)
const page = await ctx.newPage()
attachPageErrors(page, errors)
let seq = 0
const cap = (slug, opts) => capture(page, 'desktop', ++seq, slug, opts)

async function gotoComptes() {
  // atterrir sur l'app cliente puis cliquer « Admin » (la nav par hash seule ne bascule pas la vue)
  if (!page.url().includes('8795')) await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(600)
  // si on n'est pas déjà dans la Tour de contrôle, cliquer Admin
  const dansTour = await page.getByText('TOUR DE CONTRÔLE').count().catch(() => 0)
  if (!dansTour) {
    await page.getByRole('button', { name: 'Admin' }).first().click().catch(() => {})
    await page.waitForTimeout(900)
  }
  await page.getByRole('button', { name: /Comptes/ }).first().click().catch(() => {})
  await page.waitForTimeout(900)
}

async function openEssaiForm() {
  await page.getByRole('button', { name: /Ouvrir un essai/ }).first().click()
  await page.waitForTimeout(500)
}

async function fillEssai({ email, prenom, nom }) {
  await page.getByPlaceholder('prenom@societe.re').fill(email)
  const boxes = page.locator('input[type="text"], input:not([type])')
  // Prénom + Nom = 2 derniers champs texte du panneau
  const tb = await page.getByRole('textbox').all()
  // email est le 1er textbox ; prénom = index 1, nom = index 2
  if (tb[1]) await tb[1].fill(prenom)
  if (tb[2]) await tb[2].fill(nom)
}

try {
  // — login + atterrissage —
  const lv = await loginVic(page, errors)
  logStep({ device: 'desktop', name: 'login Vic (pilote)', url: lv.url, verdict: lv.url.includes('socle') || lv.url.endsWith('/') ? 'OK' : 'VOIR' })

  await gotoComptes()
  let p = await probe(page, errors)
  logStep({ device: 'desktop', seq: seq + 1, name: 'admin Comptes (liste + bandeau localhost)', url: p.url })
  await cap('B-comptes-liste', { fullPage: true })
  // bandeau localhost présent ?
  const banner = await page.getByText(/liens des mails pointent sur http:\/\/127\.0\.0\.1/i).count()
  logStep({ device: 'desktop', name: 'bandeau liens non cliquables', verdict: banner ? 'OK présent' : 'ABSENT' })

  // — B1 formulaire vide —
  await openEssaiForm()
  await cap('B-essai-form-vide')
  const btnCreer = page.getByRole('button', { name: /Créer l'essai et envoyer/ })
  logStep({ device: 'desktop', name: 'form vide — boutons désactivés', verdict: (await btnCreer.isDisabled().catch(() => null)) ? 'OK désactivé' : 'ACTIF?!' })

  // — B1 validation e-mail invalide —
  await page.getByPlaceholder('prenom@societe.re').fill('pasunemail')
  const tb = await page.getByRole('textbox').all()
  if (tb[1]) await tb[1].fill('Rémi')
  await page.waitForTimeout(300)
  await cap('B-essai-email-invalide')
  logStep({ device: 'desktop', name: 'e-mail invalide', verdict: (await btnCreer.isDisabled().catch(() => null)) ? 'bouton reste désactivé' : 'bouton ACTIF (!)' })

  // — B1 création compte A (accents) —
  await page.getByPlaceholder('prenom@societe.re').fill(A.email)
  const tb2 = await page.getByRole('textbox').all()
  if (tb2[1]) await tb2[1].fill(A.prenom)
  if (tb2[2]) await tb2[2].fill(A.nom)
  await page.waitForTimeout(300)
  await cap('B-essai-rempli-A')
  const dis = await btnCreer.isDisabled().catch(() => null)
  logStep({ device: 'desktop', name: 'form A rempli (accents)', verdict: dis ? 'ENCORE désactivé (!)' : 'bouton actif' })
  await btnCreer.click().catch((e) => logStep({ name: 'click créer A', verdict: 'ERR ' + e.message }))
  await page.waitForTimeout(1200)
  p = await probe(page, errors)
  await cap('B-apres-creation-A', { fullPage: true })
  logStep({ device: 'desktop', name: 'après création A', url: p.url, verdict: 'voir capture — lien invitation affiché ?' })

  // — B1 doublon —
  await openEssaiForm().catch(() => {})
  await page.getByPlaceholder('prenom@societe.re').fill(A.email).catch(() => {})
  const tb3 = await page.getByRole('textbox').all()
  if (tb3[1]) await tb3[1].fill(A.prenom)
  await page.waitForTimeout(300)
  await btnCreer.click().catch(() => {})
  await page.waitForTimeout(1000)
  await cap('B-doublon-erreur', { fullPage: true })
  const dupTxt = (await page.locator('body').innerText()).match(/existe déjà[^\n]*/i)?.[0] || '(pas de message visible)'
  logStep({ device: 'desktop', name: 'doublon A', verdict: dupTxt })

  // — créer B (pour l'étape 10) —
  await gotoComptes()
  await openEssaiForm().catch(() => {})
  await page.getByPlaceholder('prenom@societe.re').fill(B.email)
  const tb4 = await page.getByRole('textbox').all()
  if (tb4[1]) await tb4[1].fill(B.prenom)
  if (tb4[2]) await tb4[2].fill(B.nom)
  await page.waitForTimeout(300)
  await btnCreer.click().catch(() => {})
  await page.waitForTimeout(1000)
  logStep({ device: 'desktop', name: 'création B', verdict: 'créé (étape 10)' })

  // — liste : filtre Essais —
  await gotoComptes()
  await page.getByRole('button', { name: /Essais/ }).first().click().catch(() => {})
  await page.waitForTimeout(700)
  await cap('B-liste-essais', { fullPage: true })
  p = await probe(page, errors)
  logStep({ device: 'desktop', name: 'liste filtre Essais', verdict: p.bodyText.includes(A.email) ? 'A visible' : (p.bodyText.includes('Rémi') || p.bodyText.includes('Téoulé') ? 'A visible (nom)' : 'A ABSENT') })

  // — fiche A —
  const rowA = page.getByText(A.email).first()
  if (await rowA.count().catch(() => 0)) {
    await rowA.click().catch(() => {})
  } else {
    await page.getByText(/Téoulé|Rémi/).first().click().catch(() => {})
  }
  await page.waitForTimeout(900)
  await cap('B-fiche-A', { fullPage: true })
  p = await probe(page, errors)
  logStep({ device: 'desktop', name: 'fiche A', url: p.url, verdict: 'buttons: ' + p.buttons.join(' | ').slice(0, 300) })

  await browser.close()
  logStep({ name: 'SECTION B terminée', verdict: 'OK' })
} catch (e) {
  logStep({ name: 'SECTION B exception', verdict: e.message })
  await cap('B-EXCEPTION', { fullPage: true }).catch(() => {})
  await browser.close().catch(() => {})
  process.exit(1)
}
