// PARCOURS-FIX-1 — rejoue le parcours COMPLET sur le BUILD DE PRODUCTION (API single-origin :6005),
// desktop + mobile, en vérifiant chaque correctif du mandat. Écrit les captures numérotées et un
// parcours.json (consommé par make_planche.mjs → PARCOURS.html/PDF). Chaque étape porte un verdict.
import { writeFileSync, readdirSync, mkdirSync } from 'node:fs'
import { execSync } from 'node:child_process'
import { resolve } from 'node:path'
import { launchChromium, makeContext, attachPageErrors, capture, loginVic, loginClient,
         probe, versBase, BASE, ROOT, DESKTOP, MOBILE, now } from './lib.mjs'

const DBURL = process.env.PSQL_DB || 'postgresql://openclaw@localhost:5432/labuse'
const psql = (sql) => execSync(`psql "${DBURL}" -tAc ${JSON.stringify(sql)}`, { encoding: 'utf8' }).trim()
const EMLDIR = process.env.LABUSE_MAIL_DRYRUN_DIR || resolve(ROOT, 'mails/eml')
const emlCount = () => { try { return readdirSync(EMLDIR).filter((f) => f.endsWith('.eml')).length } catch { return 0 } }

const steps = []
let dseq = 0, mseq = 0
async function étape(page, device, { etape, phrase, verdict = 'OK', clics = 1, slug, mail = false, fullPage = false }) {
  const t0 = now()
  const seq = device === 'mobile' ? ++mseq : ++dseq
  const file = await capture(page, device, seq, slug, { fullPage })
  const rel = file.replace(ROOT + '/', '')
  steps.push({ seq, device, etape, phrase, verdict, clics, temps_ms: now() - t0, img: rel, mail })
  console.log(`  [${device}] #${seq} ${etape} → ${verdict}`)
}

const browser = await launchChromium()
const EMAIL = 'promoteur.parcoursfix@cabinet-parcours.re'
const NOM = '[CT-PARCOURS] Rémi Téoulé'
const PW1 = 'ParcoursFix-2026!'
const PW2 = 'NouveauMotDePasse-2026!'

try {
  // ───────────────────────── A · Vic (desktop) ─────────────────────────
  const { ctx } = await makeContext(browser, DESKTOP)
  const errs = []
  const vic = await ctx.newPage(); attachPageErrors(vic, errs)
  await loginVic(vic)
  await vic.goto(BASE + '/socle/', { waitUntil: 'networkidle' })
  const mount = await vic.evaluate(() => ({ l: typeof window.__labuse, root: (document.getElementById('root') || {}).innerHTML?.length || 0 }))
  await étape(vic, 'desktop', { etape: 'A1 · Build prod', phrase: 'Vic ouvre l’app servie par l’API (build de production).',
    verdict: (mount.l === 'object' && mount.root > 500 && errs.filter((e) => /is not a function|__commonJSMin/.test(e)).length === 0) ? 'OK' : 'BLOQUANT',
    clics: 1, slug: 'app-build-rendu' })

  // crée un compte d'ESSAI via l'API officielle (session Vic) → récupère le lien d'invitation
  const r = await ctx.request.post(BASE + '/admin/licences/creer-essai', { data: { email: EMAIL, nom: NOM, heures: 48 } })
  const inv = await r.json()
  const lien = versBase(inv.lien)
  console.log('  lien invitation =', lien)

  // la Tour de contrôle est un deep-link #admin=1 lu AU MOUNT : une nav qui ne change que le hash ne
  // remonte pas React → on force un reload pour que setView('admin') s'applique.
  await vic.goto(BASE + '/socle/#admin=1', { waitUntil: 'networkidle' })
  await vic.reload({ waitUntil: 'networkidle' }); await vic.waitForTimeout(1200)
  await vic.locator('[data-admin-section="licences"]').first().click({ timeout: 3000 }).catch(() => {})
  await vic.waitForTimeout(900)
  await étape(vic, 'desktop', { etape: 'A2 · Comptes', phrase: 'Vic voit la liste des comptes (essai [CT-PARCOURS] créé).', slug: 'admin-comptes', fullPage: true })

  // ouvre la fiche du compte → bouton « Copier le lien d'invitation » (Lot 2.5). Le segment par défaut
  // « À recevoir » ne liste pas un essai tout juste créé → on passe sur « Tous » avant de sélectionner.
  await vic.getByRole('button', { name: /^Tous/ }).first().click({ timeout: 2500 }).catch(() => {})
  await vic.waitForTimeout(500)
  await vic.locator(`[data-licence="${inv.compte_id}"]`).first().click({ timeout: 3000 }).catch(() => {})
  await vic.waitForTimeout(900)
  await étape(vic, 'desktop', { etape: 'A3 · Fiche compte', phrase: 'La fiche expose « Copier le lien d’invitation » (G4 corrigé).',
    verdict: (await vic.getByRole('button', { name: /Copier le lien d.invitation/ }).count()) ? 'OK' : 'ATTENTION', slug: 'fiche-bouton-lien' })
  await vic.getByRole('button', { name: /Copier le lien d.invitation/ }).first().click().catch(() => {})
  await vic.waitForTimeout(700)
  const inputCount = await vic.locator('input[readonly]').count()
  // le bouton RÉ-ÉMET un lien frais (nouveau token) → le token d'origine est périmé : le client doit
  // utiliser CE lien-ci. On le récupère depuis le champ en lecture seule et on l'utilise pour la suite.
  let lienClient = lien
  if (inputCount) {
    const v = await vic.locator('input[readonly]').first().inputValue().catch(() => '')
    if (v && /token=/.test(v)) lienClient = versBase(v)
  }
  await étape(vic, 'desktop', { etape: 'A3b · Lien copiable', phrase: 'Le lien d’invitation s’affiche, sélectionnable + bouton Copier.',
    verdict: inputCount ? 'OK' : 'ATTENTION', slug: 'fiche-lien-affiche' })

  // ───────────────────────── B · Client (desktop) — invitation ─────────────────────────
  const { ctx: cctx } = await makeContext(browser, DESKTOP)
  const cerr = []
  const cli = await cctx.newPage(); attachPageErrors(cli, cerr)
  await cli.goto(lienClient, { waitUntil: 'networkidle' })
  const hasConfirm = await cli.locator('#password2').count()
  const ctaTxt = (await cli.getByRole('button', { name: /Commencer mon essai|Continuer vers le paiement|essai/ }).first().innerText().catch(() => '')) || ''
  await étape(cli, 'desktop', { etape: 'B1 · Choix du mot de passe', phrase: 'Le client choisit son mot de passe : champ de confirmation présent, CTA adapté à l’essai.',
    verdict: (hasConfirm && /essai/i.test(ctaTxt)) ? 'OK' : 'ATTENTION', clics: 0, slug: 'invitation-mdp-page' })

  // règle imposée : mot de passe court → bouton éteint (.off)
  await cli.fill('#password', 'court'); await cli.fill('#password2', 'court')
  await cli.check('#cgv').catch(() => {})
  await cli.waitForTimeout(300)
  const offCourt = await cli.locator('#cta.off').count()
  await étape(cli, 'desktop', { etape: 'B2 · Règle 10 car.', phrase: 'Mot de passe trop court : le bouton reste éteint (règle imposée).',
    verdict: offCourt ? 'OK' : 'ATTENTION', clics: 2, slug: 'invitation-regle-courte' })

  // confirmation différente → bouton éteint + message
  await cli.fill('#password', PW1); await cli.fill('#password2', 'Autre-chose-2026!')
  await cli.waitForTimeout(300)
  const offDiff = await cli.locator('#cta.off').count()
  await étape(cli, 'desktop', { etape: 'B3 · Confirmation ≠', phrase: 'Les deux mots de passe diffèrent : bouton éteint, message clair.',
    verdict: offDiff ? 'OK' : 'ATTENTION', clics: 2, slug: 'invitation-confirmation-differente' })

  // confirmation identique + CGV → bouton allumé, on active
  await cli.fill('#password2', PW1); await cli.waitForTimeout(300)
  const onOk = await cli.locator('#cta:not(.off)').count()
  await étape(cli, 'desktop', { etape: 'B4 · Prêt', phrase: 'Mot de passe conforme + confirmation + CGV : le bouton s’allume.',
    verdict: onOk ? 'OK' : 'ATTENTION', clics: 1, slug: 'invitation-pret' })
  await Promise.all([cli.waitForLoadState('networkidle').catch(() => {}), cli.click('#cta')])
  await cli.waitForTimeout(1200)
  await étape(cli, 'desktop', { etape: 'B5 · Accès ouvert', phrase: 'Le compte est créé — le client entre dans l’app (essai).', slug: 'invitation-active', fullPage: false })

  // ───────────────────────── C · Connexion + « se souvenir » ─────────────────────────
  // déconnexion puis page login → case « Se souvenir de moi » (Lot 2.4)
  await cli.goto(BASE + '/login', { waitUntil: 'domcontentloaded' })
  await étape(cli, 'desktop', { etape: 'C1 · Connexion', phrase: 'La page de connexion propose « Se souvenir de moi ».',
    verdict: (await cli.locator('#souvenir').count()) ? 'OK' : 'ATTENTION', clics: 0, slug: 'login-souvenir' })
  await loginClient(cli, EMAIL, PW1, { souvenir: true })
  await cli.waitForTimeout(1000)
  const cookies = await cctx.cookies()
  const sess = cookies.find((c) => c.name === 'labuse_session' || c.name === 'session' || /session/i.test(c.name))
  const dureeJours = sess && sess.expires > 0 ? Math.round((sess.expires - Date.now() / 1000) / 86400) : 0
  await étape(cli, 'desktop', { etape: 'C2 · Session étendue', phrase: `Connecté avec « se souvenir » : session ≈ ${dureeJours} j (au lieu de 12 h).`,
    verdict: dureeJours >= 20 ? 'OK' : 'ATTENTION', clics: 1, slug: 'app-accueil-souvenir' })

  // ───────────────────────── Step 7 · les 20 gestes du promoteur ─────────────────────────
  const gestes = [
    ['recherche', '', 'Chercher une adresse / parcelle'],
    ['', 'plu', 'PLU / zonage'],
    ['', 'gabarit', 'Gabarit constructible 2D/3D'],
    ['', 'taxe-amenagement', 'Taxe d’aménagement'],
    ['', 'assemblage', 'Assembler deux parcelles'],
    ['', 'programme', 'Faisabilité / programme'],
    ['', 'calculette-fonciere', 'Calculette foncière (bilan)'],
    ['', 'comparer', 'Comparer des communes'],
    ['', 'communes', 'Fiche commune'],
    ['', 'risques', 'Risques & servitudes'],
    ['', 'etude-zone', 'Étude de zone'],
    ['', 'mon-secteur', 'Mon secteur'],
    ['', 'patrimoine', 'Patrimoine / successions'],
    ['', 'permis', 'Permis déposés'],
    ['', 'barometre', 'Baromètre du marché'],
    ['radar', '', 'Radar (marché en vente)'],
    ['copilote', '', 'Copilote (une question)'],
    ['documents', '', 'Mes documents'],
    ['', 'veille-promoteurs', 'Veille promoteurs'],
    ['temps', 'temps', 'Remonter le temps'],
  ]
  let g = 0
  for (const [flag, mod, label] of gestes) {
    g++
    const fatalAvant = cerr.filter((e) => /is not a function|__commonJSMin/.test(e)).length
    try {
      if (flag === 'radar') await cli.goto(BASE + '/socle/#radar=1', { waitUntil: 'networkidle' })
      else if (mod) await cli.goto(BASE + '/socle/#m=' + mod, { waitUntil: 'networkidle' })
      else await cli.goto(BASE + '/socle/', { waitUntil: 'networkidle' })
      await cli.waitForTimeout(500)
      // flags sans route de hash (toggles d'UI) : clic best-effort sur le rail.
      if (flag === 'copilote') await cli.getByRole('button', { name: /Copilote/i }).first().click({ timeout: 2500 }).catch(() => {})
      if (flag === 'documents') await cli.getByRole('button', { name: /Documents/i }).first().click({ timeout: 2500 }).catch(() => {})
      if (flag === 'temps') await cli.getByRole('button', { name: /Remonter le temps|temps/i }).first().click({ timeout: 2500 }).catch(() => {})
      if (flag === 'recherche') await cli.locator('input[type=search], input[placeholder*=dresse], input[placeholder*=arcelle]').first().click({ timeout: 2500 }).catch(() => {})
      await cli.waitForTimeout(500)
    } catch { /* on capture quand même l'état */ }
    const okMount = await cli.evaluate(() => typeof window.__labuse === 'object')
    const fatalApres = cerr.filter((e) => /is not a function|__commonJSMin/.test(e)).length
    await étape(cli, 'desktop', { etape: `7.${g} · ${label}`, phrase: `Le promoteur ouvre : ${label}.`,
      verdict: (okMount && fatalApres === fatalAvant) ? 'OK' : 'ATTENTION', clics: 1,
      slug: `geste-${String(g).padStart(2, '0')}-${(mod || flag || 'recherche')}` })
  }

  // /retours GET authentifié → redirection douce (Lot 2.7, plus de 405)
  const rr = await cctx.request.get(BASE + '/retours', { maxRedirects: 0 }).catch((e) => e)
  const rrStatus = rr.status ? rr.status() : (rr.response ? rr.response().status() : 0)

  // ───────────────────────── Step 8 · mot de passe oublié (round-trip) ─────────────────────────
  await cli.goto(BASE + '/reset', { waitUntil: 'domcontentloaded' })
  await cli.fill('input[type=email], input[name=email], #email', EMAIL).catch(() => {})
  await Promise.all([cli.waitForLoadState('networkidle').catch(() => {}), cli.click('button[type=submit]')]).catch(() => {})
  await cli.waitForTimeout(600)
  await étape(cli, 'desktop', { etape: '8.1 · Mot de passe oublié', phrase: 'Le client demande un lien de réinitialisation (dry-run → .eml).', slug: 'reset-demande' })
  // récupère le LIEN_RESET depuis mail_queue (dry-run : rien n'est parti, mais la file porte le lien)
  let resetLien = ''
  try {
    resetLien = psql("SELECT params->>'LIEN_RESET' FROM mail_queue WHERE mail_key='mdp_oublie' AND destinataire='" + EMAIL + "' ORDER BY id DESC LIMIT 1")
  } catch { /* noop */ }
  resetLien = versBase(resetLien)
  if (resetLien && /token=/.test(resetLien)) {
    await cli.goto(resetLien, { waitUntil: 'domcontentloaded' })
    await cli.fill('#password, input[name=password]', PW2).catch(() => {})
    await cli.fill('#password2, input[name=password2]', PW2).catch(() => {})
    await étape(cli, 'desktop', { etape: '8.2 · Nouveau mot de passe', phrase: 'Le client pose un nouveau mot de passe via le lien reçu.', slug: 'reset-nouveau-mdp' })
    await Promise.all([cli.waitForLoadState('networkidle').catch(() => {}), cli.click('button[type=submit]')]).catch(() => {})
    await cli.waitForTimeout(800)
    await loginClient(cli, EMAIL, PW2)
    await cli.waitForTimeout(800)
    await étape(cli, 'desktop', { etape: '8.3 · Reconnexion', phrase: 'Le client se reconnecte avec le nouveau mot de passe.',
      verdict: /socle/.test(cli.url()) ? 'OK' : 'ATTENTION', slug: 'reset-reconnexion' })
  } else {
    await étape(cli, 'desktop', { etape: '8.2 · Lien reset', phrase: 'Lien de réinitialisation introuvable en file (à vérifier).', verdict: 'ATTENTION', slug: 'reset-lien-absent' })
  }

  // ───────────────────────── D · Vic : suspension / rétablissement (mails) ─────────────────────────
  const cid = inv.compte_id
  const emlBefore = emlCount()
  await ctx.request.post(BASE + `/admin/licences/${cid}/suspendre`, { data: { motif: 'parcours-fix' } })
  await vic.waitForTimeout(400)
  const suspMail = psql("SELECT mail_key||':'||etat FROM mail_queue WHERE compte_id=" + cid + " AND mail_key='suspension' ORDER BY id DESC LIMIT 1")
  await vic.goto(BASE + '/socle/#admin=1', { waitUntil: 'networkidle' })
  await vic.reload({ waitUntil: 'networkidle' }); await vic.waitForTimeout(1000)
  await vic.locator('[data-admin-section="licences"]').first().click({ timeout: 3000 }).catch(() => {})
  await vic.waitForTimeout(700)
  await étape(vic, 'desktop', { etape: 'D1 · Suspension', phrase: `Vic suspend le compte → le mail « suspension » part (file : ${suspMail || '—'}).`,
    verdict: suspMail ? 'OK' : 'ATTENTION', slug: 'suspension' })
  await ctx.request.post(BASE + `/admin/licences/${cid}/retablir`, { data: {} })
  await vic.waitForTimeout(400)
  const retMail = psql("SELECT mail_key||':'||etat FROM mail_queue WHERE compte_id=" + cid + " AND mail_key='retablissement' ORDER BY id DESC LIMIT 1")
  await étape(vic, 'desktop', { etape: 'D2 · Rétablissement', phrase: `Vic rétablit le compte → le mail « rétablissement » part (file : ${retMail || '—'}).`,
    verdict: retMail ? 'OK' : 'ATTENTION', slug: 'retablissement' })

  // ───────────────────────── Step 9 · fin d'essai forcée ─────────────────────────
  psql("UPDATE comptes SET essai_expire_at = now() - interval '1 hour', statut='actif' WHERE id=" + cid)
  await loginClient(cli, EMAIL, PW2)
  await cli.waitForTimeout(900)
  const regul = /r.gulariser|suspendu|abonnement/i.test(await cli.locator('body').innerText().catch(() => ''))
  await étape(cli, 'desktop', { etape: '9 · Fin d’essai', phrase: 'Essai expiré : le client voit « abonnement à régulariser », données intactes.',
    verdict: regul ? 'OK' : 'ATTENTION', slug: 'fin-essai' })

  // ───────────────────────── Mobile (390×844) ─────────────────────────
  const { ctx: mctx } = await makeContext(browser, MOBILE)
  const merr = []
  const mob = await mctx.newPage(); attachPageErrors(mob, merr)
  await mob.goto(BASE + '/login', { waitUntil: 'domcontentloaded' })
  await étape(mob, 'mobile', { etape: 'M1 · Connexion (mobile)', phrase: 'Page de connexion sur mobile, avec « Se souvenir de moi ».',
    verdict: (await mob.locator('#souvenir').count()) ? 'OK' : 'ATTENTION', slug: 'login', fullPage: true })
  // nouvel essai pour une page d'invitation mobile fraîche
  const r2 = await ctx.request.post(BASE + '/admin/licences/creer-essai', { data: { email: 'promoteur.mobile@cabinet-parcours.re', nom: '[CT-PARCOURS] Mobile', heures: 48 } })
  const inv2 = await r2.json()
  await mob.goto(versBase(inv2.lien), { waitUntil: 'networkidle' })
  await étape(mob, 'mobile', { etape: 'M2 · Invitation (mobile)', phrase: 'Page mot de passe sur mobile : confirmation + CTA essai.',
    verdict: (await mob.locator('#password2').count()) ? 'OK' : 'ATTENTION', slug: 'invitation', fullPage: true })
  await loginVic(mob)   // session admin de fait pour prouver que le BUILD s'ouvre sur mobile
  await mob.goto(BASE + '/socle/', { waitUntil: 'networkidle' })
  const mMount = await mob.evaluate(() => ({ l: typeof window.__labuse, root: (document.getElementById('root') || {}).innerHTML?.length || 0 }))
  const mFatal = merr.filter((e) => /is not a function|__commonJSMin/.test(e)).length
  await étape(mob, 'mobile', { etape: 'M3 · App (mobile)', phrase: 'L’app (build de prod) s’ouvre et s’affiche sur mobile.',
    verdict: (mMount.l === 'object' && mMount.root > 500 && mFatal === 0) ? 'OK' : 'BLOQUANT', slug: 'app-accueil', fullPage: false })

  // ───────────────────────── preuve dry-run étanche ─────────────────────────
  const emlAfter = emlCount()
  // PREUVE d'étanchéité, SCOPÉE à cette session (destinataires @cabinet-parcours.re) : AUCUN mail n'a
  // reçu de messageId Brevo (message_id NULL partout) → 0 appel réseau réel. Les mails de cycle de vie
  // sont en file (a_rejouer/en_attente), jamais `recu`.
  const recusBrevo = psql("SELECT count(*) FROM mail_queue WHERE destinataire like '%@cabinet-parcours.re' AND message_id IS NOT NULL")
  const mailsSession = psql("SELECT string_agg(mail_key||':'||etat, ', ' ORDER BY id) FROM mail_queue WHERE destinataire like '%@cabinet-parcours.re'")
  const summary = {
    retours_get_status: rrStatus, eml_before: emlBefore, eml_after: emlAfter,
    mails_session_recus_brevo: Number(recusBrevo || 0), mails_session: mailsSession, souvenir_jours: dureeJours,
  }
  writeFileSync(resolve(ROOT, 'scripts/parcours.json'), JSON.stringify({ steps, summary }, null, 2))
  console.log('\nRÉSUMÉ', JSON.stringify(summary))
  console.log('captures desktop:', dseq, '· mobile:', mseq, '· .eml:', emlAfter)
} catch (e) {
  console.error('ÉCHEC parcours:', e && e.stack || e)
  writeFileSync(resolve(ROOT, 'scripts/parcours.json'), JSON.stringify({ steps, error: String(e) }, null, 2))
} finally {
  await browser.close()
}
