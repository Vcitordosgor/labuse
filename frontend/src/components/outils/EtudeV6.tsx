// ETUDE-V6 (Lot A) — L'ÉTUDE DE FAISABILITÉ EN 3 ÉTAPES EXACTEMENT : ① Choix des parcelles · ② Type de
// projet · ③ Votre programme, puis « Analyser mon projet ». Récapitulatif à droite. AUCUNE CARTE dans le
// formulaire, aucun bouton « bientôt », aucune présélection de type ni de typologie. Aucun calcul ici :
// l'étape 1 est validée par POST /modules/etude/parcelles (faits + contiguïté + sources), et l'analyse
// par POST /modules/etude. Remplace la config de M22 dans l'overlay EtudeEcran. Le RÉSULTAT détaillé
// (« ce que le terrain accueille », variantes, facteurs limitants) est repris au Lot B ; ici, base servie.
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { postEtude, postEtudeParcelles, postEtudeStationnement, postEtudeJauge, ETUDE_PDF_URL, etudePdfInit } from '../../lib/api'
import type { EtudeJaugeOut } from '../../lib/api'
import type { EtudeParcelle, EtudeParcellesOut, EtudePayload, EtudeVariante, EtudeGrandeur, EtudeStationnementRegimes, EtudeLotissement, EtudeIn, EtudeRegle } from '../../lib/api'
import { fmtInt, fmtDec } from '../../lib/format'
import { Bouton } from '../ui/Bouton'
import { Badge } from '../ui/Badge'
import { ParcelInput } from '../ParcelInput'
import { Chargement } from '../Loading'
import { PlanMasseSvg } from './PlanMasseSvg'
import { useOuvrirDocument } from '../../lib/ouvrirDocument'
import type { EtudeProgramme } from './M22Programme'

// Hypothèses de programme (mandat V6) : surface totale par logement, varangue incluse → intérieur indicatif.
// Jamais appelées SDP ni SHAB. Modifiables plus tard dans « Hypothèses » (Lot B).
const TYPES = ['T1', 'T2', 'T3', 'T4'] as const
type TypeKey = (typeof TYPES)[number]
const SURF: Record<TypeKey, { area: number; varangue: number }> = {
  T1: { area: 30, varangue: 6 }, T2: { area: 56, varangue: 9 },
  T3: { area: 70, varangue: 12 }, T4: { area: 80, varangue: 14 },
}

// ETUDE-V6-6 (item 5) — JAUGE EN LOGEMENTS (plus jamais en SDP) estimée avant calcul :
//   aérien   N ≈ zone × niveaux × coef ÷ (surf_moy + places/logt × 25 m² × niveaux × coef)
//   sous-sol N ≈ zone × niveaux × coef ÷ surf_moy          (le parking enterré ne consomme pas le sol)
// surf_moy / places par logement = moyennes pondérées de la demande. 25 m² = emprise d'une place (circ.).
const _M2_PLACE_JAUGE = 25
// ETUDE-V6-7 (item 6) — numérateur = BANDE de bâtiment (vraie forme, servie par le moteur), pas toute la
// zone ; en sous-sol, borné par la capacité des places au −1 (per-niveau servi) ÷ places par logement.
function enveloppeJauge(jd: EtudeJaugeOut | undefined, demande: Record<string, number>, surfaceDe: (t: string) => number,
                        stationnement: 'aerien' | 'sous_sol' = 'aerien') {
  if (!jd || !jd.estimable) return null
  const total = Object.values(demande).reduce((s, n) => s + n, 0)
  const bande = jd.bande_batiment_m2 ?? jd.zone_implantation_m2 ?? 0
  const niveaux = jd.niveaux ?? 0, coef = jd.coef_plancher ?? 0
  const surfMoy = total > 0 ? Object.entries(demande).reduce((s, [t, n]) => s + n * surfaceDe(t), 0) / total : 0
  const placesMoy = total > 0 ? Object.entries(demande).reduce((s, [t, n]) => s + n * (jd.places_par_type?.[t] ?? 1), 0) / total : 0
  const num = bande * niveaux * coef
  let estime: number
  if (stationnement === 'sous_sol') {
    const bati = surfMoy > 0 ? num / surfMoy : 0                                   // sol libéré : bâtiment plus grand
    const parking = placesMoy > 0 ? (jd.sous_sol_places_par_niveau ?? 0) / placesMoy : bati   // borné par le −1
    estime = Math.round(Math.min(bati, parking))
  } else {
    const denom = surfMoy + placesMoy * _M2_PLACE_JAUGE * niveaux * coef
    estime = denom > 0 ? Math.round(num / denom) : 0
  }
  return { estime, demande: total, surfMoy, placesMoy, mode: stationnement,
           niveaux_label: jd.niveaux_label ?? '', zone_m2: jd.zone_implantation_m2 ?? 0, coef }
}

// ETUDE-V6-3 (item 2) — préfixe NORMALISÉ de toute règle PLU affichée : « PLU de [commune] · zone [X] ·
// art. [n°] · millésime ». Chaque règle vient du PLU de la commune de l'assiette (regles.charger(insee)).
// ETUDE-V6-6 (item 10) — n° de document affiché = EF-<8> (les 8 premiers caractères du study_id), identique
// au cartouche du PDF (_numero_document côté serveur). Deux études différentes → deux numéros.
function numDoc(studyId?: string | null): string {
  return studyId && studyId.startsWith('EF-') && studyId.length >= 11 ? studyId.slice(0, 11) : (studyId ?? '')
}

function pluRef(commune?: string | null, zone?: string | null, article?: string | null, millesime?: string | null): string {
  return [commune ? `PLU de ${commune}` : 'PLU', zone ? `zone ${zone}` : null,
    article ? `art. ${article}` : null, millesime ? `millésime ${millesime}` : null].filter(Boolean).join(' · ')
}

type ProjetKey = 'etudiante' | 'senior' | 'social' | 'lotissement'
const PROJETS: { key: ProjetKey; label: string; desc: string }[] = [
  { key: 'etudiante', label: 'Résidence étudiante', desc: 'Studios et petits logements pour étudiants' },
  { key: 'senior', label: 'Résidence senior', desc: 'Logements adaptés pour personnes âgées' },
  { key: 'social', label: 'Logement social', desc: 'Programme locatif social ou assimilé' },
  { key: 'lotissement', label: 'Lotissement', desc: 'Division foncière en lots destinés à bâtir' },
]
// Lot C — le vrai type est transmis au moteur : l'implantation reste collective (le lotissement =
// division, Lot D), mais le STATIONNEMENT dépend de la destination (règle générale PLU + plafond L151-35).

const ETAPES = [
  { n: 1, titre: 'Choix des parcelles', sous: 'Assiette foncière' },
  { n: 2, titre: 'Type de projet', sous: 'Destination' },
  { n: 3, titre: 'Votre programme', sous: 'T1, T2, T3, T4' },
] as const

function verdictTon(v: string): 'vert' | 'ambre' | 'rouge' {
  if (v.startsWith('Exploitable')) return 'vert'
  if (v.startsWith('À compléter')) return 'ambre'
  return 'rouge'
}
function etatTon(r: string): 'vert' | 'ambre' | 'rouge' | 'neutre' {
  if (r === 'Réussi') return 'vert'
  if (r === 'Échoué') return 'rouge'
  if (r === 'À confirmer') return 'ambre'
  return 'neutre'  // Non effectué / Non applicable
}

// ETUDE-V6-3 (item 6) — plus de pont « Bilan de ce scénario » : onBilan n'est plus consommé (prop gardée
// pour compat d'appel, ignorée). Un seul scénario affiché → plus d'état de variante active.
export function EtudeV6({ initialIdus, onClose }: {
  initialIdus?: string[]; onClose?: () => void; onBilan?: (prog: EtudeProgramme) => void
}) {
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [sel, setSel] = useState<string[]>(initialIdus ?? [])
  const [projet, setProjet] = useState<ProjetKey | null>(null)
  const [nb, setNb] = useState<Record<TypeKey, number>>({ T1: 0, T2: 0, T3: 0, T4: 0 })
  // Hypothèses modifiables (mandat) : surfaces T1–T4, varangues, et hypothèses MOTEUR (profondeur,
  // coef plancher). Vides = valeurs LABUSE par défaut. Édition dans le résultat → recalcul → même PDF.
  const [hyp, setHyp] = useState<{ surf: Record<TypeKey, string>; varangue: Record<TypeKey, string>; profondeur: string; coef: string; stationnement: 'aerien' | 'sous_sol'; niveauxSousSol: 1 | 2; lotCible: string; voirie: string }>(
    { surf: { T1: '', T2: '', T3: '', T4: '' }, varangue: { T1: '', T2: '', T3: '', T4: '' }, profondeur: '', coef: '', stationnement: 'aerien', niveauxSousSol: 1, lotCible: '', voirie: '' })
  const pdf = useOuvrirDocument()
  const surfOf = (t: TypeKey) => { const x = parseFloat(hyp.surf[t]); return isNaN(x) ? SURF[t].area : x }
  const varOf = (t: TypeKey) => { const x = parseFloat(hyp.varangue[t]); return isNaN(x) ? SURF[t].varangue : Math.max(0, Math.min(surfOf(t), x)) }
  const hypBody = (): EtudeIn['hypotheses'] => {
    const h: NonNullable<EtudeIn['hypotheses']> & { varangues?: Record<string, number> } = {}
    const prof = parseFloat(hyp.profondeur); const coef = parseFloat(hyp.coef)
    if (!isNaN(prof)) h.profondeur_m = prof
    if (!isNaN(coef)) h.coef_plancher_habitable = coef
    const varangues = Object.fromEntries(TYPES.filter((t) => hyp.varangue[t] !== '').map((t) => [t, varOf(t)]))
    if (Object.keys(varangues).length) h.varangues = varangues
    // ETUDE-V6-6 (item 3) — hypothèses du LOTISSEMENT : taille de lot visée + largeur de voirie.
    const lc = parseFloat(hyp.lotCible); const vl = parseFloat(hyp.voirie)
    if (!isNaN(lc) && lc > 0) h.lot_cible_m2 = lc
    if (!isNaN(vl) && vl > 0) h.voirie_largeur_m = vl
    return Object.keys(h).length ? h : undefined
  }
  // UNE seule config sert l'analyse ET le PDF (surfaces éditées via les lignes du programme → study_id).
  const corpsBody = (over?: Partial<EtudeIn>): EtudeIn => ({
    idus: sel, type_projet: projet ?? 'collectif',
    // ETUDE-V6-2 (Lot 3) — le mode de stationnement (aérien par défaut / sous-sol) pilote l'implantation.
    // ETUDE-V6-5 — en sous-sol, le NOMBRE DE NIVEAUX (1 ou 2) est explicite et borne la capacité.
    stationnement: hyp.stationnement,
    niveaux_sous_sol: hyp.stationnement === 'sous_sol' ? hyp.niveauxSousSol : undefined,
    programme: { mode: 'saisi', lignes: TYPES.filter((t) => nb[t] > 0).map((t) => ({ type: t, nombre: nb[t], surface_m2: surfOf(t) })) },
    hypotheses: hypBody(),
    ...over,
  })
  // ETUDE-V6-3 (item 4) — animation de chargement dans le bouton pendant la génération.
  // ETUDE-V6-4 (item 8) — jamais de PDF d'un état NON calculé : grisé tant qu'une hypothèse éditée n'est pas recalculée.
  const BoutonPdf = () => (
    <div className="flex flex-col gap-1">
      <Bouton niveau="secondaire" onClick={() => pdf.ouvrir(ETUDE_PDF_URL, 'etude-pdf', etudePdfInit(corpsBody()))} disabled={!!pdf.enCours || dirty}>
        {pdf.enCours ? <span className="inline-flex items-center gap-1.5">Génération<Chargement variant="inline" accent="courant" delai={0} /></span> : 'Générer le PDF ↓'}
      </Bouton>
      {dirty && <span data-pdf-perime className="text-[10px] text-amber">Recalculez pour mettre à jour l'étude.</span>}
      {/* ETUDE-V6-6 (item 10) — N° de document EF-<8> dérivé du study_id, identique au cartouche du PDF. */}
      {analyse.data?.study_id && <span data-num-doc className="text-[9px] text-txt-dim">N° de document {numDoc(analyse.data.study_id)} — le PDF part de la même étude.</span>}
    </div>
  )

  // Étape 1 : validation de l'assiette (faits + contiguïté + sources). Rejouée à chaque changement de sel.
  const valide = useQuery({
    queryKey: ['etude-parcelles', sel.join(',')],
    queryFn: () => postEtudeParcelles(sel),
    enabled: sel.length > 0,
    staleTime: 60_000,
  })
  const v: EtudeParcellesOut | undefined = valide.data

  // Étape 2 — la règle de stationnement applicable (règle PLU + plafond L151-35), dès le choix du type.
  const statio = useQuery({
    queryKey: ['etude-stationnement', sel.join(','), projet],
    queryFn: () => postEtudeStationnement(sel, projet!),
    enabled: step === 2 && !!projet && sel.length > 0,
    staleTime: 60_000,
  })

  // ETUDE-V6-2 (Lot 4) — enveloppe ESTIMÉE (jauge) : chargée dès l'étape 3 (rapide, sans moteur). Le
  // collectif seul (le lotissement ne dessine pas de bâtiment). Reste en cache pour le résultat (divergence).
  const jaugeQ = useQuery({
    queryKey: ['etude-jauge', sel.join(','), projet],
    queryFn: () => postEtudeJauge(sel, projet!),
    enabled: step === 3 && !!projet && projet !== 'lotissement' && !!v?.contiguite.ok,
    staleTime: 60_000,
  })

  // ETUDE-V6-4 (item 8) — une hypothèse éditée mais PAS recalculée rend l'étude affichée périmée : on
  // GRISE le PDF (« Recalculez pour mettre à jour l'étude ») tant que le recalcul n'est pas fait.
  const [dirty, setDirty] = useState(false)
  // Analyse (étape finale ET recalcul) : un seul appel moteur avec la config courante (hypothèses comprises).
  const analyse = useMutation({ mutationFn: (body?: EtudeIn) => postEtude(body ?? corpsBody()),
                                onSuccess: () => setDirty(false) })
  const recalculer = () => analyse.mutate(undefined)
  const marquerModifie = () => setDirty(true)
  // ETUDE-V6-7 (item 3) — stationnement CHOISI dès l'étape 3 : AÉRIEN ou SOUS-SOL (1 niveau ; plus de 2
  // niveaux). Met juste à jour l'hypothèse (pas de recalcul ; le choix part avec le programme, la jauge suit).
  const setStatioEtape3 = (choix: 'aerien' | 'sous_sol') => setHyp((h) => ({
    ...h, stationnement: choix, niveauxSousSol: 1 }))
  const resultat: EtudePayload | undefined = analyse.data
  // ETUDE-V6-3 (item 4) — animation de chargement de l'app (composant existant) pendant « Calcul en cours ».
  const loadingOverlay = analyse.isPending ? (
    <div data-etude-calcul className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-2 bg-surface-0/75 backdrop-blur-sm">
      <Chargement variant="bloc" label="Calcul en cours, jusqu'à une minute" />
    </div>
  ) : null

  // ETUDE-V6-2 (Lot 1) — l'étape 3 et le récap lisent TOUJOURS les surfaces par défaut (SURF), source
  // unique. Les hypothèses éditées (dans le résultat) n'affectent QUE le résultat, après « Recalculer ».
  const totalLogts = TYPES.reduce((s, t) => s + nb[t], 0)
  const surfaceProg = TYPES.reduce((s, t) => s + nb[t] * SURF[t].area, 0)
  const surfaceVar = TYPES.reduce((s, t) => s + nb[t] * SURF[t].varangue, 0)
  const surfaceInt = surfaceProg - surfaceVar

  // ETUDE-V6-2 (Lot 4) — enveloppe estimée vs programme saisi (surfaces par défaut, comme l'étape 3).
  const demandeNb: Record<string, number> = Object.fromEntries(TYPES.filter((t) => nb[t] > 0).map((t) => [t, nb[t]]))
  // ETUDE-V6-6 (items 4/5) — la jauge tient compte du stationnement CHOISI à l'étape 3 (aérien par défaut).
  const jauge = enveloppeJauge(jaugeQ.data, demandeNb, (t) => SURF[t as TypeKey]?.area ?? 0, hyp.stationnement)

  const contiguOk = sel.length > 0 && !!v?.contiguite.ok
  const peutContinuer1 = contiguOk && !valide.isFetching
  const peutAnalyser = contiguOk && !!projet && totalLogts > 0

  function reset() { setStep(1); setSel([]); setProjet(null); setNb({ T1: 0, T2: 0, T3: 0, T4: 0 }); resetHyp(); analyse.reset() }
  function resetHyp() { setHyp({ surf: { T1: '', T2: '', T3: '', T4: '' }, varangue: { T1: '', T2: '', T3: '', T4: '' }, profondeur: '', coef: '', stationnement: 'aerien', niveauxSousSol: 1, lotCible: '', voirie: '' }) }
  // « Modifier le programme » revient au formulaire ET réinitialise les hypothèses éditées (pas de fuite).
  function modifierProgramme() { resetHyp(); analyse.reset() }
  // ETUDE-V6-6 (item 3) — hypothèses du lotissement = taille de lot visée + largeur de voirie (pas T1–T4).
  const editeurLot = () => (
    <LotissementHypotheses hyp={hyp} setHyp={setHyp} onRecalculer={recalculer} enCours={analyse.isPending} onModifie={marquerModifie} />
  )
  function ajouter(idu: string) { setSel((xs) => (xs.includes(idu) || xs.length >= 8 ? xs : [...xs, idu])) }
  function retirer(idu: string) { setSel((xs) => xs.filter((x) => x !== idu)) }

  // ── RÉSULTAT LOTISSEMENT (Lot D) — plan de division, pas des scénarios d'implantation.
  if (resultat?.lotissement) {
    return (
      <div className="relative flex min-h-full flex-col">
        {loadingOverlay}
        <Entete onClose={onClose} onReset={modifierProgramme} resetLabel="← Modifier le programme" />
        <div className="flex items-center gap-3 border-b border-line-2 px-4 py-3">
          <span className="text-[12px] text-txt-dim">Verdict de l'étude</span>
          <Badge ton="ambre">{resultat.verdict}</Badge>
          <span className="text-[11px] text-txt-dim">{resultat.entrees.commune} · zone {resultat.entrees.zone} · lotissement</span>
        </div>
        <LotissementResultat lot={resultat.lotissement} hypothese={resultat.logements_hypothese} boutonPdf={<BoutonPdf />} pdfErreur={pdf.erreur ?? undefined} studyId={resultat.study_id} editeur={editeurLot()} />
        <p className="px-4 pb-4 text-[10px] leading-snug text-txt-dim">{resultat.lotissement.note}</p>
      </div>
    )
  }

  // ── RÉSULTAT (Lot B) — le résultat qui explique : Votre demande → Ce que le terrain accueille →
  //    L'écart → Ce qui limite → Alternative ; 4 grandeurs séparées ; 3 variantes ; 5 états ; verdict.
  if (resultat) {
    const variantes = resultat.variantes ?? []
    // ETUDE-V6-3 (item 6) — un SEUL scénario affiché : « votre programme » (plus d'onglets, plus d'alternative).
    const active = variantes.find((v) => v.role === 'votre_programme' && !v.absente) ?? variantes.find((v) => !v.absente) ?? variantes[0]
    const demMap: Record<string, number> = resultat.programme_saisi?.demande ?? Object.fromEntries(TYPES.filter((t) => nb[t] > 0).map((t) => [t, nb[t]]))
    const surfA = (t: string) => resultat.hypotheses?.surfaces?.[t] ?? SURF[t as TypeKey]?.area ?? 0
    const demTotal = Object.values(demMap).reduce((s, n) => s + n, 0)
    // ETUDE-V6-7 (item 2) — surface TENUE = Σ (logements DESSINÉS × surface), servie par le moteur : une seule
    // vérité (le plan), jamais la surface de la demande. Repli local si le champ n'est pas servi.
    const parPlan = active?.programme.par_type ?? {}
    const surfaceTenue = active?.programme.surface_tenue_m2 ?? Object.entries(parPlan).reduce((s, [t, n]) => s + n * surfA(t), 0)
    // ETUDE-V6-6 (item 5) — jauge EN LOGEMENTS confrontée au calcul EN LOGEMENTS (plus de SDP).
    const jaugeRes = enveloppeJauge(jaugeQ.data, demMap, surfA, active?.stationnement?.mode ?? 'aerien')
    const capLog = resultat.capacite_maximale?.logements ?? 0
    const divergence = (jaugeRes && capLog > 0 && Math.abs(jaugeRes.estime - capLog) / capLog > 0.2)
      ? { estime: jaugeRes.estime, calcule: capLog, pct: Math.round((Math.abs(jaugeRes.estime - capLog) / capLog) * 100) }
      : null
    // ETUDE-V6-3 (item 7) — UN SEUL facteur limitant, calculé une fois : bandeau, « Ce qui limite » n°1 et
    // message rouge disent la MÊME chose. En sous-sol, si c'est la pente, « hauteur sur la pente (relief X m) ».
    const facteurs = resultat.facteurs_limitants ?? []
    const sousSol = active?.stationnement?.mode === 'sous_sol'
    // ETUDE-V6-4 (items 10/11/13) — LA phrase « ce qui limite » vient du serveur (source unique) : l'écran et
    // le PDF disent exactement les mêmes mots. Repli local seulement si le serveur ne l'a pas renseignée.
    const limitePhrase: string | null = resultat.facteur_limitant ?? facteurs[0]?.facteur ?? active?.limite_capacite ?? null
    // ETUDE-V6-3 (item 8) — bloc fusionné « Votre programme : N demandés · M tiennent · max K » ; UNE réserve.
    const confr = resultat.confrontation
    const kMax = resultat.capacite_maximale?.logements ?? active?.resume.logements ?? 0
    const nDem = confr?.demande_logements ?? demTotal
    const mTiennent = confr?.tient ? nDem : (resultat.depassement?.total_tiennent ?? Math.min(nDem, kMax))
    const reserve = kMax - nDem
    const repLabel = resultat.capacite_maximale?.repartition ?? ''
    return (
      <div className="relative flex min-h-full flex-col">
        {loadingOverlay}
        <Entete onClose={onClose} onReset={modifierProgramme} resetLabel="← Modifier le programme" />
        {/* ETUDE-V6-3 (items 6/7) — bandeau : verdict + LE facteur limitant (même phrase partout). Plus d'onglets. */}
        <div className="flex flex-wrap items-center gap-2.5 border-b border-line-2 px-4 py-3">
          <span className="text-[12px] text-txt-dim">Verdict de l'étude</span>
          <Badge ton={verdictTon(resultat.verdict ?? '')}>{resultat.verdict}</Badge>
          {limitePhrase && <span className="text-[11px] text-txt-mut">· ce qui limite : <b className="text-txt">{limitePhrase}</b></span>}
        </div>

        {resultat.depassement && <Depassement d={resultat.depassement} limite={limitePhrase} />}

        {/* variante ABSENTE : l'onglet reste, il dit pourquoi (mandat §C). */}
        {active?.absente && (
          <div data-variante-absente={active.role} className="mx-4 my-6 rounded-lg border border-line-2 bg-surface-2 p-6 text-center">
            <b className="text-[13px] text-txt-hi">{active.role_label} — non proposée</b>
            <p className="mx-auto mt-1 max-w-[520px] text-[12px] text-txt-mut">{active.raison}</p>
          </div>
        )}

        {active && !active.absente && (
          <div className="grid flex-1 gap-4 p-4 lg:grid-cols-[1fr_360px]">
            <section className="flex flex-col gap-4">
              {/* ETUDE-V6-3 (item 9) — 2 grands chiffres : Logements tenus/demandés + Surface du programme tenue.
                  Sol restant / Emprise mobilisable / SDP autorisée passent dans le détail des surfaces. */}
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-line-2 bg-surface-2 p-3 transition-colors hover:border-mint/40">
                  <p className="text-[9px] uppercase tracking-wide text-txt-dim">Logements</p>
                  <div className="font-display text-[22px] font-bold leading-none text-txt-hi">{fmtInt(mTiennent)} <span className="text-[13px] text-txt-mut">/ {fmtInt(nDem)}</span></div>
                  <p className="mt-0.5 text-[9.5px] text-txt-dim">tenus / demandés</p>
                </div>
                <div className="rounded-lg border border-line-2 bg-surface-2 p-3 transition-colors hover:border-mint/40">
                  {/* ETUDE-V6-4 (item 6) — surface DU PROGRAMME (logements × surfaces T1–T4), JAMAIS la SDP. */}
                  <p className="text-[9px] uppercase tracking-wide text-txt-dim">Surface du programme tenue</p>
                  <div className="font-display text-[22px] font-bold leading-none text-txt-hi">{fmtDec(surfaceTenue)} <span className="text-[13px]">m²</span></div>
                  <p className="mt-0.5 text-[9.5px] text-txt-dim">logements × surfaces (varangue comprise)</p>
                </div>
              </div>
              {/* plan masse (item 10 : titre sans nom technique de variante) */}
              {active.geojson && (
                <div className="rounded-lg border border-line-2 bg-surface-2 p-3">
                  <p className="mb-2 text-[11px] font-semibold text-txt">Plan masse — {active.forme} · {active.niveaux_label}</p>
                  <PlanMasseSvg fc={active.geojson} svg={active.planche_svg} groupesCaches={[]} />
                </div>
              )}
              {/* ETUDE-V6-3 (item 10) — sous-sol : cartouche + plan de principe du niveau −1 (places + rampe). */}
              {sousSol && active.stationnement && <PlanSousSol st={active.stationnement} geojson={active.geojson} />}
              {/* ETUDE-V6-4 (items 4/5) — stationnement 3 lignes + mixité (identique au PDF). */}
              {resultat.stationnement_regimes && (
                <StationnementResultat regimes={resultat.stationnement_regimes}
                  placesActive={active.resume.places} commune={resultat.entrees.commune} zone={resultat.regles.zone}
                  mode={active.stationnement?.mode ?? 'aerien'} niveaux={active.stationnement?.niveaux_sous_sol ?? 1}
                  mixite={{ regle: resultat.regles.lignes.find((l) => /mixit/i.test(l.nom)) ?? null,
                            applicable: active.programme.mixite_applicable, aides: active.programme.logements_aides_imposes,
                            sdp_aidee: active.programme.sdp_aidee_imposee_m2 }} />
              )}
              {/* ETUDE-V6-3 (item 9) — détail des surfaces : sol restant, emprise mobilisable, SDP autorisée (+ rampe sous-sol). */}
              <DetailSurfaces v={active} />
              {/* contrôles — 5 états */}
              <Controles v={active} commune={resultat.entrees.commune} zone={resultat.regles.zone} millesime={resultat.regles.millesime} lignes={resultat.regles.lignes} />
            </section>

            <aside className="flex flex-col gap-3">
              {/* ETUDE-V6-3 (item 8) — bloc fusionné « Capacité maximale + Ce que le terrain accueille + L'écart » :
                  N demandés · M tiennent · maximum K. UNE seule réserve, cohérente partout. */}
              <Recit titre="Votre programme" ton={confr ? (confr.tient ? 'vert' : 'ambre') : verdictTon(active.verdict)}>
                <p className="text-[12px] text-txt-hi">{fmtInt(nDem)} demandés · <b className={confr?.tient !== false ? 'text-mint' : 'text-amber'}>{fmtInt(mTiennent)} tiennent</b> · le terrain accueille au maximum <b>{fmtInt(kMax)}</b></p>
                {/* ETUDE-V6-7 (item 2) — on DÉCRIT le plan dessiné (la typologie tenue) + la surface tenue : une
                    seule vérité, jamais la surface de la demande. */}
                <p className="mt-0.5 text-[10.5px] text-txt-dim">Dessiné : {Object.entries(parPlan).filter(([, n]) => n > 0).map(([t, n]) => `${n}×${t}`).join(' · ') || '—'} · {fmtDec(surfaceTenue)} m² de programme tenu</p>
                {reserve >= 0
                  ? <p className="mt-1 text-[11px] text-txt">Réserve de <b className="text-mint">{fmtInt(reserve)}</b> logement(s) jusqu'au maximum du terrain.</p>
                  : <p className="mt-1 text-[11px] text-txt">Dépassement de <b className="text-amber">{fmtInt(-reserve)}</b> logement(s) au-delà du maximum.</p>}
                <p className="mt-0.5 text-[9.5px] text-txt-dim">Maximum réglementaire du terrain (répartition {repLabel}) · {resultat.capacite_maximale?.niveaux_label} — indépendant du nombre demandé.</p>
                {divergence && (
                  <p data-divergence className="mt-1 text-[10.5px] text-amber">⚠ L'estimation de l'étape 3 (≈ {fmtInt(divergence.estime)} logements) et le calcul ({fmtInt(divergence.calcule)} logements) divergent de {divergence.pct} % : la jauge était {divergence.estime > divergence.calcule ? 'optimiste' : 'prudente'} — fiez-vous au calcul.</p>
                )}
              </Recit>
              {/* ETUDE-V6-3 (item 7) — ce qui limite : n°1 = LA phrase du bandeau/message (même facteur, une fois). */}
              <Recit titre="Ce qui limite">
                {facteurs.length > 0 ? (
                  <ol className="flex flex-col gap-1.5">
                    {facteurs.map((f, i) => (
                      <li key={f.facteur} className="text-[11px]">
                        <span className="text-txt">{i + 1}. {i === 0 && limitePhrase ? limitePhrase : f.facteur}</span>
                        {f.impact_logements > 0 ? (
                          <span className={`ml-1.5 font-semibold ${f.limitant ? 'text-coral' : 'text-txt-mut'}`}>−{f.impact_logements} logement(s)</span>
                        ) : (
                          <span className="ml-1.5 text-txt-mut">impact non chiffré</span>
                        )}
                        <p className="text-[9.5px] text-txt-dim">{f.detail} <span className="italic">({f.preuve})</span></p>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="text-[11.5px] text-txt">{limitePhrase ?? 'Aucun facteur limitant dominant identifié.'}</p>
                )}
                {/* ETUDE-V6-4 (item 10) — en sous-sol, pourquoi la hauteur plafonne (même phrase qu'au PDF). */}
                {resultat.facteur_limitant_detail && (
                  <p data-facteur-detail className="mt-1 text-[10.5px] text-txt-dim">{resultat.facteur_limitant_detail}</p>
                )}
                {active.controles.filter((c) => c.resultat === 'Échoué' || c.resultat === 'À confirmer').slice(0, 4).map((c) => (
                  <p key={c.nom} className="mt-0.5 text-[10px] text-txt-dim">• {c.nom} — <span className={c.resultat === 'Échoué' ? 'text-coral' : 'text-amber'}>{c.resultat}</span></p>
                ))}
                {/* ETUDE-V6-7 (item 7) — « Testez en sous-sol » retiré : on change le stationnement via « Modifier le programme ». */}
                {/* ETUDE-V6-7 (item 4) — en sous-sol, comment le sol libéré est utilisé (phrase chiffrée). */}
                {active.sol_libere_note && <p data-sol-libere className="mt-1 text-[10.5px] text-txt-dim">{active.sol_libere_note}</p>}
              </Recit>
              {/* ETUDE-V6-2 (Lot 3, correction §4) — règles d'aménagement NON modélisées par le PLU calibré
                  (ex. UA : espaces verts 20 %, marge plantée) : signalées « non vérifiées », jamais appliquées
                  en douce. Elles réduiraient la capacité servie. */}
              {resultat.regles_non_verifiees && resultat.regles_non_verifiees.length > 0 && (
                <Recit titre="Règles non vérifiées" ton="ambre">
                  {resultat.regles_non_verifiees.map((r) => (
                    <p key={r.nom} className="text-[10.5px] text-txt-dim">• <span className="text-txt">{r.nom}</span> — {r.exemple}. <span className="italic">{r.note}</span></p>
                  ))}
                </Recit>
              )}
              {/* ETUDE-V6-7 (item 7) — bloc « Hypothèses modifiables » retiré du résultat (change via « Modifier le programme »). */}
              {/* ETUDE-V6-3 (item 6) — plus de bouton « Bilan de ce scénario ». */}
              <div className="flex flex-wrap gap-2">
                <BoutonPdf />
              </div>
              {/* ETUDE-V6-4 (item 1) — ligne « Bilan surfacique clos… study_id… » retirée. */}
              {pdf.erreur && <p className="text-[10px] text-coral">{pdf.erreur}</p>}
            </aside>
          </div>
        )}

        {!active && (
          <div className="p-6 text-center">
            <Badge ton="rouge">{resultat.verdict}</Badge>
            <p className="mt-2 text-[12px] text-txt-mut">{resultat.message}</p>
          </div>
        )}

        <p className="px-4 pb-4 text-[10px] leading-snug text-txt-dim">Pré-faisabilité indicative, à faire confirmer par un architecte. Ni étude d'architecte, ni preuve de conformité. Une place annoncée = une place dessinée.</p>
      </div>
    )
  }

  // ── WIZARD (3 étapes) ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="relative flex min-h-full flex-col">
      {loadingOverlay}
      <Entete onClose={onClose} onReset={reset} resetLabel="↻ Recommencer" />
      {/* ETUDE-V6-4 (item 1) — hero « Votre projet… » retiré. */}
      <div className="grid grid-cols-1 gap-2 px-4 pt-4 sm:grid-cols-3">
        {ETAPES.map((e) => {
          const on = e.n === step
          const fait = e.n < step
          return (
            <button key={e.n} type="button" onClick={() => { if (e.n < step) setStep(e.n as 1 | 2 | 3) }}
              className={`flex items-center gap-2.5 rounded-lg border px-3 py-2.5 text-left transition-colors duration-quick ${
                on ? 'border-mint bg-mint text-mint-on' : fait ? 'border-line-2 hover:border-mint/50' : 'border-line-2 opacity-70'} ${e.n < step ? 'cursor-pointer' : 'cursor-default'}`}>
              {/* ETUDE-V6-6 (item 7) — étape sélectionnée = vert OPAQUE (fond plein, texte sombre), jamais translucide. */}
              <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded text-[12px] font-bold ${on ? 'bg-mint-on/15 text-mint-on' : fait ? 'bg-mint text-mint-on' : 'bg-surface-3 text-txt-dim'}`}>{e.n}</span>
              <span><b className={`block text-[12.5px] ${on ? 'text-mint-on' : 'text-txt-hi'}`}>{e.titre}</b><small className={`text-[10.5px] ${on ? 'text-mint-on/80' : 'text-txt-dim'}`}>{e.sous}</small></span>
            </button>
          )
        })}
      </div>

      <div className="grid flex-1 gap-4 p-4 lg:grid-cols-[1fr_340px]">
        <div className="rounded-lg border border-line-2 bg-surface-2 p-4">
          {step === 1 && <EtapeParcelles sel={sel} v={v} chargement={valide.isFetching} erreur={valide.error} onAjouter={ajouter} onRetirer={retirer} />}
          {step === 2 && <EtapeType projet={projet} onChoisir={setProjet} regimes={statio.data?.regimes} chargement={statio.isFetching} commune={statio.data?.commune} zone={statio.data?.zone} mixite={statio.data?.mixite} />}
          {step === 3 && <EtapeProgramme nb={nb} setNb={setNb} totalLogts={totalLogts} surfaceProg={surfaceProg} surfaceVar={surfaceVar} surfaceInt={surfaceInt} lotissement={projet === 'lotissement'}
            jauge={jauge} jaugeChargement={jaugeQ.isFetching} jaugeManquant={jaugeQ.data && !jaugeQ.data.estimable ? jaugeQ.data.manquant : null}
            statioChoix={hyp.stationnement} onStatioChoix={setStatioEtape3} sousSolDispo={jaugeQ.data?.sous_sol_dispo ?? null} />}
        </div>
        {/* ETUDE-V6-7 (item 8) — récap + boutons Retour/Continuer/Analyser dans la COLONNE DE DROITE, sous
            le récap, STICKY au défilement (sur les 3 étapes). */}
        <div className="flex flex-col gap-4 self-start lg:sticky lg:top-4">
          <Recap sel={sel} v={v} projet={projet} totalLogts={totalLogts} surfaceProg={surfaceProg} surfaceVar={surfaceVar}
            stationnement={projet && statio.data?.regimes?.general ? (statio.data.regimes.general.regle_courte ?? statio.data.regimes.general.etat ?? 'règle PLU') : null} />
          <PiedEtape
            step={step}
            peutContinuer1={peutContinuer1} peutAnalyser={peutAnalyser}
            enAnalyse={analyse.isPending} erreurAnalyse={analyse.error}
            onPrec={() => setStep((s) => (s > 1 ? ((s - 1) as 1 | 2 | 3) : s))}
            onSuiv={() => setStep((s) => (s < 3 ? ((s + 1) as 1 | 2 | 3) : s))}
            onAnalyser={() => analyse.mutate(undefined)}
            projetChoisi={!!projet}
          />
        </div>
      </div>
    </div>
  )
}

// ── En-tête (Fermer / Recommencer) ───────────────────────────────────────────────────────────────
function Entete({ onClose, onReset, resetLabel }: { onClose?: () => void; onReset: () => void; resetLabel: string }) {
  return (
    <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
      <div className="flex items-center gap-3">
        {onClose && <Bouton niveau="secondaire" onClick={onClose}>← Fermer</Bouton>}
        <div><b className="block text-[14px] text-txt-hi">Étude de faisabilité</b></div>
      </div>
      <Bouton niveau="secondaire" onClick={onReset}>{resetLabel}</Bouton>
    </header>
  )
}

function Chiffre({ v, l }: { v: string; l: string }) {
  return (
    <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
      <div className="font-display text-[22px] font-bold leading-none text-txt-hi">{v}</div>
      <div className="mt-1 text-[10.5px] text-txt-dim">{l}</div>
    </div>
  )
}

// ── Lot B — une des 4 grandeurs (valeur + statut mesuré/dérivé/non vérifié) ──────────────────────
// ETUDE-V6-3 (item 9) — détail des surfaces : les grandeurs déplacées (sol restant, emprise mobilisable,
// SDP autorisée) + les surfaces mesurées + la rampe en sous-sol. Repliable, ne vole pas la vedette aux 2 chiffres.
function DetailSurfaces({ v }: { v: EtudeVariante }) {
  const g = v.grandeurs
  const ligne = (l: string, gr: EtudeGrandeur) => (
    <div key={l} className="flex items-center justify-between border-t border-line-2 py-1" title={gr.detail}>
      <span className="text-[10.5px] text-txt-mut">{l}</span>
      <span className="flex items-center gap-1.5"><b className="text-[11px] text-txt-hi">{gr.valeur_m2 == null ? '—' : `${fmtDec(gr.valeur_m2)} m²`}</b>
        <Badge ton={gr.statut === 'mesuré' ? 'vert' : gr.statut === 'dérivé' ? 'neutre' : 'ambre'}>{gr.statut}</Badge></span>
    </div>
  )
  const st = v.stationnement
  return (
    <details data-detail-surfaces className="rounded-lg border border-line-2 bg-surface-2 p-3 transition-colors hover:border-mint/40">
      <summary className="cursor-pointer text-[11px] font-semibold text-txt">Détail des surfaces</summary>
      <div className="mt-1 flex flex-col">
        {ligne('Sol restant', g.sol_restant)}
        {ligne('Emprise mobilisable', g.emprise_mobilisable)}
        {ligne('SDP autorisée', g.sdp_autorisee)}
        {ligne('Programme (SDP dessinée)', g.programme_envisageable)}
        {Object.entries(v.surfaces_mesurees_m2 ?? {}).map(([k, m]) => (
          <div key={k} className="flex items-center justify-between border-t border-line-2 py-1">
            <span className="text-[10.5px] text-txt-mut">{k}</span><b className="text-[11px] text-txt">{fmtDec(m)} m²</b>
          </div>
        ))}
        {st?.mode === 'sous_sol' && (st.rampe_m2 ?? 0) > 0 && (
          <div className="flex items-center justify-between border-t border-line-2 py-1">
            <span className="text-[10.5px] text-txt-mut">Rampe de sous-sol</span><b className="text-[11px] text-txt">{fmtDec(st.rampe_m2 ?? 0)} m²</b>
          </div>
        )}
      </div>
    </details>
  )
}

// ETUDE-V6-4 (item 9) / V6-5 — plan du sous-sol DESSINÉ sur la vraie géométrie, UN plan PAR NIVEAU choisi
// (−1, et −2 si 2 niveaux). Chaque plan filtre le GeoJSON sur son niveau (places/allée/emprise tagués) +
// l'assiette pour le cadre. La capacité est bornée aux niveaux CHOISIS (jamais un 2ᵉ niveau supposé).
function PlanSousSol({ st, geojson }: { st: NonNullable<EtudeVariante['stationnement']>; geojson?: EtudeVariante['geojson'] | null }) {
  const n = st.places_sous_sol ?? 0
  const parNiveau = st.places_sous_sol_par_niveau ?? 0
  const niveaux = st.niveaux_sous_sol ?? 1
  const n1 = st.places_niveau_moins1 ?? n
  const n2 = st.places_niveau_moins2 ?? 0
  // un plan par niveau : objets tagués niveau=-1 / -2, + l'assiette (et la rampe au −1) pour le cadre.
  const planNiveau = (niv: -1 | -2, nPlaces: number) => {
    if (!geojson || nPlaces <= 0) return null
    const feats = geojson.features.filter((f: { properties?: { kind?: string; niveau?: number } | null }) => {
      const k = f.properties?.kind ?? ''
      if (k === 'assiette' || k === 'voie') return true
      if (['sous_sol_emprise', 'allee_ss', 'place_ss', 'rampe'].includes(k)) return f.properties?.niveau === niv
      return false
    })
    const fc = { type: 'FeatureCollection' as const, features: feats }
    if (!feats.some((f: { properties?: { kind?: string } | null }) => f.properties?.kind === 'place_ss')) return null
    return (
      <div className="mt-1">
        <p className="text-[10px] font-semibold text-mint">Niveau −{Math.abs(niv)} — {fmtInt(nPlaces)} places</p>
        <PlanMasseSvg fc={fc} groupesCaches={[]} className="block h-auto w-full max-w-[420px] rounded-md" />
      </div>
    )
  }
  return (
    <div className="rounded-lg border border-mint/40 bg-mint-bg p-3">
      <p className="mb-1 text-[11px] font-semibold text-mint">Stationnement en sous-sol · {fmtInt(niveaux)} niveau{niveaux > 1 ? 'x' : ''}</p>
      <p className="mb-2 text-[10px] text-txt-mut">{fmtInt(n)} places sur {fmtInt(niveaux)} niveau{niveaux > 1 ? 'x' : ''} ({fmtInt(parNiveau)} / niveau) · emprise {fmtDec(st.emprise_sous_sol_m2 ?? 0)} m² (≤ emprise réglementaire) · rampe {fmtDec(st.rampe_m2 ?? 0)} m²
        {st.rampe_detail && <> ({fmtDec(st.rampe_detail.rampe_profondeur_m)} m / {fmtDec(st.rampe_detail.rampe_pente_pct)} % = {fmtDec(st.rampe_detail.rampe_longueur_m)} m × {fmtDec(st.rampe_detail.rampe_largeur_m)} m)</>}
      </p>
      {planNiveau(-1, n1)}
      {niveaux >= 2 && planNiveau(-2, n2)}
      <p className="mt-1 text-[9px] text-txt-dim">Plan de principe dessiné sur la géométrie réelle — {fmtInt(parNiveau)} places / niveau sur cette emprise. L'implantation exacte relève de l'architecte.</p>
    </div>
  )
}

// ── Lot B — une étape du récit du résultat ──────────────────────────────────────────────────────
function Recit({ titre, ton, children }: { titre: string; ton?: 'vert' | 'ambre' | 'rouge'; children: React.ReactNode }) {
  const bord = ton === 'vert' ? 'border-l-mint' : ton === 'ambre' ? 'border-l-amber' : ton === 'rouge' ? 'border-l-coral' : 'border-l-line-2'
  return (
    <div data-recit={titre} className={`rounded-md border border-line-2 ${bord} border-l-2 bg-surface-2 px-3 py-2`}>
      <p className="text-[9px] font-semibold uppercase tracking-wide text-txt-dim">{titre}</p>
      <div className="mt-1">{children}</div>
    </div>
  )
}

// ── Lot B — la liste des contrôles (5 états) ────────────────────────────────────────────────────
// ETUDE-V6-4 (item 3) — rattache un contrôle à SA règle PLU (qui porte article/page/citation/lien/millésime)
// pour que « Lire l'article » apparaisse aussi sur les contrôles. Appariement par mot-clé du nom (stable).
function regleDuControle(nom: string, lignes: EtudeRegle[]): EtudeRegle | null {
  const n = nom.toLowerCase()
  const clefs: Array<[RegExp, RegExp]> = [
    [/emprise/, /emprise/],
    [/hauteur/, /hauteur|égout/],
    [/recul/, /recul/],
    [/perméab|pleine terre/, /pleine terre|perméab/],
    [/stationnement/, /stationnement/],
    [/mixité/, /mixité/],
  ]
  for (const [cn, cr] of clefs) {
    if (cn.test(n)) { const r = lignes.find((l) => cr.test((l.nom || '').toLowerCase())); if (r) return r }
  }
  return null
}

function Controles({ v, commune, zone, millesime, lignes }: { v: EtudeVariante; commune?: string | null; zone?: string | null; millesime?: string | null; lignes: EtudeRegle[] }) {
  const c = v.controles_compte
  // ETUDE-V6-3 (item 2) — citation normalisée : « PLU de [commune] · zone [X] · millésime · <citation sans "PLU "> ».
  const cite = (txt: string) => `${pluRef(commune, zone, null, millesime)} · ${txt.replace(/^PLU\s+/, '')}`
  return (
    <div className="rounded-lg border border-line-2 bg-surface-2 p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <b className="text-[11px] font-semibold text-txt">Contrôles réglementaires</b>
        <span className="text-[10px] text-mint">{c.reussi} réussis</span>
        {c.echoue > 0 && <span className="text-[10px] text-coral">{c.echoue} échoués</span>}
        {(c.a_confirmer ?? 0) > 0 && <span className="text-[10px] text-amber">{c.a_confirmer} à confirmer</span>}
        <span className="text-[10px] text-txt-dim">{c.non_effectue} non effectués · {c.non_applicable} sans objet</span>
      </div>
      <div className="flex flex-col gap-1">
        {v.controles.map((ct) => {
          const r = regleDuControle(ct.nom, lignes)
          return (
          <div key={ct.nom} className="flex items-start justify-between gap-2 border-t border-line-2 py-1">
            <div className="min-w-0">
              <span className="text-[11px] text-txt">{ct.nom}</span>
              <span className="ml-1.5 text-[10px] text-txt-dim">{ct.regle} · {ct.mesure}</span>
              {ct.citation && <span className="ml-1.5 text-[9.5px] text-txt-dim">— {cite(ct.citation)}</span>}
              {r && <LireArticle r={{ article: r.article, page_pdf: r.page_pdf, millesime: r.millesime ?? millesime, citation: r.citation, source_url: r.source_url, commune, zone }} />}
            </div>
            <Badge ton={etatTon(ct.resultat)}>{ct.resultat}</Badge>
          </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Lot D — résultat LOTISSEMENT : plan de division + tableau des lots + voirie/pleine terre/réseaux ──
function LotissementResultat({ lot, hypothese, boutonPdf, pdfErreur, studyId, editeur }: {
  lot: EtudeLotissement; hypothese?: { demande: Record<string, number> } | null
  boutonPdf?: React.ReactNode; pdfErreur?: string; studyId?: string; editeur?: React.ReactNode
}) {
  const tl = lot.tableau_lots
  const hyp = hypothese?.demande ?? {}
  return (
    <div className="grid flex-1 gap-4 p-4 lg:grid-cols-[1fr_360px]">
      <section className="flex flex-col gap-4">
        {/* ETUDE-V6-6 (item 2) — 0 lot n'est jamais muet : la raison + ce qui le permettrait. */}
        {tl.nombre === 0 && lot.raison && (
          <div data-lot-raison className="rounded-lg border border-amber/50 bg-amber-bg px-4 py-3">
            <b className="text-[12px] text-amber">Aucun lot dessinable</b>
            <p className="mt-1 text-[11.5px] text-txt">{lot.raison}</p>
            {lot.remede && <p className="mt-1 text-[11px] text-txt-dim"><b>Ce qui le permettrait :</b> {lot.remede}</p>}
          </div>
        )}
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Chiffre v={fmtInt(tl.nombre)} l="lots" />
          <Chiffre v={`${fmtDec(tl.surface_moyenne_m2 ?? 0)} m²`} l="surface moyenne" />
          <Chiffre v={`${fmtDec(tl.surface_min_m2 ?? 0)} m²`} l="surface mini" />
          <Chiffre v={`${fmtDec(lot.voirie_m2)} m²`} l="voirie" />
        </div>
        {/* ETUDE-V6-6 (item 1) — règles du PLU de la commune/zone, chacune sourcée (jamais Ud en dur). */}
        {(lot.regles_sourcees?.length ?? 0) > 0 && (
          <div data-lot-regles className="rounded-lg border-l-4 border-mint bg-mint-bg px-3.5 py-2.5">
            <p className="text-[9px] font-semibold uppercase tracking-[0.08em] text-mint">Règles du PLU · {lot.commune} · zone {lot.zone}</p>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {(lot.regles_sourcees ?? []).map((r) => (
                <span key={r.nom} className="inline-flex items-center gap-1 rounded border border-mint/40 bg-surface-1 px-1.5 py-0.5 text-[10px] text-txt-mut">
                  {r.nom} <b className="text-txt">{r.valeur}</b>
                  <span className="text-[9px] text-txt-dim">{r.servie ? `· ${r.article}` : '· non servie (hypothèse)'}</span>
                </span>
              ))}
            </div>
          </div>
        )}
        {lot.geojson && tl.nombre > 0 && (
          <div className="rounded-lg border border-line-2 bg-surface-2 p-3">
            <p className="mb-2 text-[11px] font-semibold text-txt">Plan de division — {tl.nombre} lots · {lot.voirie_config}</p>
            <PlanMasseSvg fc={lot.geojson} groupesCaches={[]} />
          </div>
        )}
        {/* contrôles (pleine terre : Réussi / Échoué avec chiffres) */}
        {(lot.controles?.length ?? 0) > 0 && (
          <div className="rounded-lg border border-line-2 bg-surface-2 p-3">
            <b className="text-[11px] font-semibold text-txt">Contrôles réglementaires</b>
            {(lot.controles ?? []).map((c) => (
              <div key={c.nom} className="mt-1.5 flex items-start justify-between gap-2 border-t border-line-2 py-1.5">
                <div className="min-w-0"><span className="text-[11px] text-txt">{c.nom}</span>
                  <span className="ml-1.5 text-[10px] text-txt-dim">{c.regle} · {c.mesure}{c.detail ? ` · ${c.detail}` : ''}</span></div>
                <Badge ton={etatTon(c.resultat)}>{c.resultat}</Badge>
              </div>
            ))}
          </div>
        )}
        {/* tableau des lots */}
        <div className="rounded-lg border border-line-2 bg-surface-2 p-3">
          <b className="text-[11px] font-semibold text-txt">Tableau des lots — accès {tl.acces}</b>
          <div className="mt-1.5 grid grid-cols-6 gap-1 text-[10.5px] sm:grid-cols-8">
            {tl.surfaces_m2.map((s, i) => (
              <span key={i} className="rounded border border-line-2 bg-surface-1 px-1.5 py-1 text-center"><b className="text-txt">#{i + 1}</b> <span className="text-txt-dim">{fmtInt(s)}</span></span>
            ))}
          </div>
        </div>
      </section>

      <aside className="flex flex-col gap-3">
        <Recit titre="Division foncière">
          <p className="text-[12px] text-txt-hi">{tl.nombre} lots · {fmtDec(tl.surface_moyenne_m2 ?? 0)} m² en moyenne ({fmtDec(tl.surface_min_m2 ?? 0)}–{fmtDec(tl.surface_max_m2 ?? 0)})</p>
          <p className="text-[10.5px] text-txt-dim">Assiette {fmtDec(lot.assiette_m2)} m² · net constructible {fmtDec(lot.net_constructible_m2)} m²{lot.ppr_rouge_m2 > 0 ? ` · PPR rouge ${fmtDec(lot.ppr_rouge_m2)} m² retiré` : ''}</p>
        </Recit>
        <LigneInfo l="Voirie" v={`${fmtDec(lot.voirie_m2)} m² · ${lot.voirie_config}`} sous={lot.voirie_largeur_source} />
        <Recit titre="Pleine terre" ton={lot.pleine_terre.resultat === 'Réussi' ? 'vert' : 'rouge'}>
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] text-txt">{fmtDec(lot.pleine_terre.estimee_m2)} m² vs {fmtDec(lot.pleine_terre.exigee_m2)} m² exigés ({lot.pleine_terre.exigee_pct} % · {lot.pleine_terre.article})</span>
            <Badge ton={lot.pleine_terre.resultat === 'Réussi' ? 'vert' : 'rouge'}>{lot.pleine_terre.resultat}</Badge>
          </div>
          <p className="mt-0.5 text-[9.5px] text-txt-dim">jardins privatifs {fmtDec(lot.pleine_terre.jardins_privatifs_m2)} m² (lot − emprise au CES {lot.pleine_terre.ces_pct} %) + espaces communs {fmtDec(lot.pleine_terre.communs_m2)} m²</p>
        </Recit>
        <LigneInfo l="Stationnement" v={`${lot.stationnement.total_lots} places (${lot.stationnement.par_lot}/lot · ${lot.stationnement.article ?? 'hypothèse'})`} sous={`+ ${lot.stationnement.visiteurs_estimes} visiteurs (estimé)`} />
        <Recit titre="EBC" ton={lot.ebc.m2 > 0 ? 'ambre' : undefined}>
          <p className="text-[11px] text-txt">{lot.ebc.m2 > 0 ? `${fmtDec(lot.ebc.m2)} m² d'EBC` : lot.ebc.statut}</p>
        </Recit>
        <Recit titre="Surface minimale de lot (PLU)">
          <p className="text-[11px] text-txt">{lot.min_lot_plu.existe ? 'règle présente' : 'aucune superficie minimale servie'}</p>
          <p className="mt-0.5 text-[9.5px] text-txt-dim">{lot.min_lot_plu.note}</p>
        </Recit>
        <Recit titre="Raccordements">
          {lot.raccordements.map((r) => (
            <p key={r.reseau} className="text-[10.5px] text-txt">{r.reseau} — <span className="text-txt-dim">{r.distance_m == null ? 'non vérifié' : `${fmtInt(r.distance_m)} m (${r.statut})`}</span></p>
          ))}
        </Recit>
        <Recit titre="Régime procédural" ton="ambre">
          <p className="text-[11px] text-txt">{lot.regime_procedural}</p>
        </Recit>
        <Recit titre="Bilan surfacique" ton={lot.bilan_surfacique.clos ? 'vert' : 'ambre'}>
          <div className="flex items-center justify-between gap-2">
            <span className="text-[11px] text-txt">assiette {fmtDec(lot.bilan_surfacique.assiette_m2)} m² = lots + voirie + communs + PPR + hors-zone</span>
            <Badge ton={lot.bilan_surfacique.clos ? 'vert' : 'ambre'}>{lot.bilan_surfacique.clos ? 'clos' : 'à ajuster'}</Badge>
          </div>
          <p className="mt-0.5 text-[9.5px] text-txt-dim">{fmtDec(lot.bilan_surfacique.lots_m2)} + {fmtDec(lot.bilan_surfacique.voirie_m2)} + {fmtDec(lot.bilan_surfacique.communs_m2)} + {fmtDec(lot.bilan_surfacique.ppr_rouge_m2)} + {fmtDec(lot.bilan_surfacique.hors_zone_m2)} = {fmtDec(lot.bilan_surfacique.somme_m2)} m² (écart {fmtDec(lot.bilan_surfacique.ecart_m2)}) — aucune double comptabilisation.</p>
        </Recit>
        {editeur}
        {boutonPdf}
        {pdfErreur && <p className="text-[10px] text-coral">{pdfErreur}</p>}
        {studyId && <p data-num-doc className="text-[9px] text-txt-dim">N° de document {numDoc(studyId)} — le PDF part de la même étude.</p>}
        {Object.keys(hyp).length > 0 && (
          <Recit titre="Logements futurs (hypothèse)">
            <p className="text-[11px] text-txt">{Object.entries(hyp).map(([t, n]) => `${n}×${t}`).join(' · ')}</p>
            <p className="mt-0.5 text-[9.5px] text-txt-dim">Hypothèse de constructions futures — jamais un nombre de lots garanti.</p>
          </Recit>
        )}
      </aside>
    </div>
  )
}
function LigneInfo({ l, v, sous }: { l: string; v: string; sous?: string }) {
  return (
    <div className="rounded-md border border-line-2 bg-surface-2 px-3 py-2">
      <p className="text-[9px] font-semibold uppercase tracking-wide text-txt-dim">{l}</p>
      <p className="text-[11px] text-txt">{v}</p>
      {sous && <p className="text-[9.5px] text-txt-dim">{sous}</p>}
    </div>
  )
}

// ── Hypothèses modifiables (mandat) : surfaces T1–T4, varangues, + hypothèses moteur (collectif) ──
type HypEtat = { surf: Record<TypeKey, string>; varangue: Record<TypeKey, string>; profondeur: string; coef: string; stationnement: 'aerien' | 'sous_sol'; niveauxSousSol: 1 | 2; lotCible: string; voirie: string }

// ETUDE-V6-6 (item 3) — hypothèses du LOTISSEMENT : taille de lot visée + largeur de voirie (jamais T1–T4).
function LotissementHypotheses({ hyp, setHyp, onRecalculer, enCours, onModifie }: {
  hyp: HypEtat; setHyp: (f: (h: HypEtat) => HypEtat) => void; onRecalculer: () => void; enCours: boolean; onModifie: () => void
}) {
  const champ = (val: string, ph: string, on: (v: string) => void) => (
    <input type="number" min={0} inputMode="decimal" value={val} placeholder={ph} onChange={(e) => { on(e.target.value); onModifie() }}
      className="w-20 rounded border border-line-2 bg-surface-2 px-1.5 py-0.5 text-center text-[11px] text-txt-hi" />
  )
  return (
    <details data-hypotheses-lot className="rounded-lg border border-line-2 bg-surface-2 p-3" open>
      <summary className="cursor-pointer text-[11px] font-semibold text-txt">Hypothèses du lotissement <small className="font-normal text-txt-dim">(Estimé — recalcule la division)</small></summary>
      <div className="mt-2 flex flex-col gap-2 text-[10.5px] text-txt-mut">
        <label className="flex items-center gap-2">Taille de lot visée {champ(hyp.lotCible, '450', (v) => setHyp((h) => ({ ...h, lotCible: v })))} m²</label>
        <label className="flex items-center gap-2">Largeur de voirie {champ(hyp.voirie, '5', (v) => setHyp((h) => ({ ...h, voirie: v })))} m</label>
        <div className="mt-1 flex items-center gap-2">
          <Bouton niveau="primaire" onClick={onRecalculer} disabled={enCours} className="whitespace-nowrap">{enCours ? 'Recalcul…' : 'Recalculer ↻'}</Bouton>
          <span className="text-[9.5px] text-txt-dim">Le recalcul met à jour la division ET le PDF (même study_id).</span>
        </div>
      </div>
    </details>
  )
}
// ── Lot C — stationnement dans le résultat : règle générale (appliquée) + plafond L151-35 (à confirmer)
//    + la capacité SOUS le régime réduit, jamais présentée comme acquise ───────────────────────────
// ETUDE-V6-4 (items 4/5) — stationnement en TROIS lignes sans ambiguïté (PLU exige · loi nationale plafonne ·
// LABUSE a dessiné) + MIXITÉ sociale affichée. Identique mot pour mot au PDF.
function StationnementResultat({ regimes, placesActive, commune, zone, mode, niveaux, mixite }: {
  regimes: EtudeStationnementRegimes
  placesActive: number; commune?: string | null; zone?: string | null
  mode: 'aerien' | 'sous_sol'; niveaux?: number
  mixite?: { regle: EtudeRegle | null; applicable: boolean | null; aides: number | null; sdp_aidee: number | null } | null
}) {
  const lieu = mode === 'sous_sol' ? `au sous-sol (${(niveaux ?? 1) >= 2 ? 'niveaux −1 et −2' : 'niveau −1'})` : 'en aérien (au sol)'
  const g = regimes.general, pf = regimes.plafond_national
  const regleG = g.regle_courte ?? (g.ratio_par_logement != null ? `${fmtDec(g.ratio_par_logement)} place/logt` : 'un barème par typologie')
  return (
    <div data-stationnement-resultat className="rounded-lg border border-line-2 bg-surface-2 p-3">
      <b className="text-[11px] font-semibold text-txt">Stationnement</b>
      <ol className="mt-2 flex flex-col gap-1.5 text-[11px] text-txt">
        <li className="flex items-start gap-1.5">
          <span>Le PLU de <b>{commune}</b> (art. {g.article ?? '—'}) exige <b>{regleG}</b>.</span>
          <LireArticle r={{ article: g.article, page_pdf: g.page_pdf, millesime: g.millesime, citation: g.citation, source_url: g.source_url, commune, zone }} />
        </li>
        {pf ? (
          <li className="text-txt">La loi nationale (Code de l'urbanisme, art. <b>{pf.reference}</b>) plafonne à <b>{fmtDec(pf.ratio_plafond)} place/logt</b> si le projet est éligible — <span className="text-amber">à confirmer</span>.</li>
        ) : (
          <li className="text-txt-dim">Aucun plafond national L151-35 applicable à cette destination.</li>
        )}
        <li className="text-txt">LABUSE a dessiné <b>{fmtInt(placesActive)} places</b> {lieu} selon la règle du PLU.</li>
      </ol>
      {mixite?.regle && (
        <div data-mixite className="mt-2 border-t border-line-2 pt-2 text-[10.5px] text-txt">
          <span><b>Mixité sociale</b> (art. {mixite.regle.article ?? '—'}) : {fmtDec(mixite.regle.valeur ?? 0)} % de logements aidés{mixite.regle.seuil_m2 != null ? ` au-delà de ${fmtDec(mixite.regle.seuil_m2)} m² de SDP` : ''}.</span>
          <LireArticle r={{ article: mixite.regle.article, page_pdf: mixite.regle.page_pdf, millesime: mixite.regle.millesime, citation: mixite.regle.citation, source_url: mixite.regle.source_url, commune, zone }} />
          <span className="ml-1 text-txt-dim">{mixite.applicable ? `Applicable : ${fmtInt(mixite.aides ?? 0)} logements aidés imposés.` : 'Non applicable (seuil non atteint).'}</span>
        </div>
      )}
    </div>
  )
}

// ── Lot B — dépassement : combien tiennent, lesquels manquent, par quoi commencer ───────────────
function Depassement({ d, limite }: { d: NonNullable<EtudePayload['depassement']>; limite?: string | null }) {
  const manquent = Object.entries(d.manquent)
  return (
    <div className="mx-4 mt-3 rounded-md border border-amber/50 bg-amber-bg px-4 py-3">
      <b className="text-[12px] text-amber">Votre programme dépasse les enveloppes testées — l'impossibilité n'est pas démontrée.</b>
      <p className="mt-1 text-[11.5px] text-txt">{d.total_tiennent} des {d.total_demande} logements demandés sont dessinables. Manquent : {manquent.map(([t, n]) => `${n}×${t}`).join(' · ')}.</p>
      {limite && <p className="mt-0.5 text-[10.5px] text-txt-mut">Par quoi commencer : {limite}. Réduisez la quantité ou changez l'implantation.</p>}
    </div>
  )
}

// ── Étape 1 — Parcelles ──────────────────────────────────────────────────────────────────────────
function EtapeParcelles({ sel, v, chargement, erreur, onAjouter, onRetirer }: {
  sel: string[]; v?: EtudeParcellesOut; chargement: boolean; erreur: unknown
  onAjouter: (idu: string) => void; onRetirer: (idu: string) => void
}) {
  return (
    <div>
      <EnTetePanneau n="01" titre="Choisissez votre terrain" sous="Une ou plusieurs parcelles (1 à 8). Elles doivent être contiguës pour constituer une même assiette foncière." />
      <label className="mb-1 block text-[9px] uppercase tracking-wide text-txt-dim">Référence de parcelle — adresse, IDU ou référence cadastrale</label>
      <div className="max-w-[560px]">
        {/* ETUDE-V6-2 (Lot 5) — le champ est VIDÉ après chaque ajout (remontage via la clé) : prêt pour la suivante. */}
        <ParcelInput key={sel.length} dataAttr="etude-v6-parcelle" withCarte={false} onPick={onAjouter} placeholder="Adresse, IDU ou référence (ex. 97404000AW0099)" />
      </div>

      <div className="mt-3 flex items-center justify-between">
        <b className="text-[12px] text-txt">Parcelles sélectionnées</b>
        <span className="text-[11px] text-txt-dim">{sel.length}/8</span>
      </div>
      {sel.length === 0 && <p className="mt-1.5 text-[11.5px] text-txt-dim">Ajoutez une référence pour commencer.</p>}

      {sel.length > 0 && chargement && !v && <div className="mt-2"><Chargement /></div>}
      {!!erreur && <p className="mt-2 text-[11.5px] text-coral">{(erreur as Error).message}</p>}

      {/* ETUDE-V6-3 (item 1) — règles PLU affichées UNE fois par ZONE pour l'assiette (« PLU de … · zone … ·
          N parcelles »), en plus d'une fois par parcelle (ci-dessous). */}
      {v?.parcelles && v.parcelles.length > 0 && <ReglesAssiette parcelles={v.parcelles} />}

      {v?.parcelles && (
        <div className="mt-2 flex flex-col gap-2">
          {v.parcelles.map((p) => (
            <div key={p.idu} data-etude-parcelle-row className="rounded-md border border-line-2 bg-surface-1 px-3 py-2">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <b className="font-mono text-[12px] text-txt-hi">{p.reference}</b>
                  <span className="text-[11px] text-txt-mut">{p.commune}</span>
                  {p.zone_plu && <Badge ton="neutre">{p.zone_plu}</Badge>}
                  {p.qualite_geometrique === 'irrégulière' && <Badge ton="ambre">géométrie irrégulière</Badge>}
                </div>
                <button type="button" onClick={() => onRetirer(p.idu)} className="text-[12px] text-txt-dim hover:text-coral" aria-label={`Retirer ${p.reference}`}>×</button>
              </div>
              <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-[10.5px] text-txt-dim">
                <span>Contenance <b className="text-txt">{p.contenance_cadastrale_m2 != null ? `${fmtDec(p.contenance_cadastrale_m2)} m²` : '—'}</b></span>
                <span>Surface réelle <b className="text-txt">{p.surface_reelle_m2 != null ? `${fmtDec(p.surface_reelle_m2)} m²` : '—'}</b></span>
                {p.ecart_m2 != null && <span>Écart {p.ecart_m2 > 0 ? '+' : ''}{fmtDec(p.ecart_m2)} m²</span>}
              </div>
              {/* ETUDE-V6-4 (item 2) — les cartes de parcelles NE répètent PLUS les règles PLU (bandeau unique en tête). */}
            </div>
          ))}

          {/* Union + contiguïté */}
          <div className={`rounded-md border px-3 py-2 ${v.contiguite.ok ? 'border-mint/40 bg-mint-bg' : 'border-coral/50 bg-coral/10'}`}>
            <b className="text-[12px] text-txt-hi">{v.union.nb_parcelles} parcelle{v.union.nb_parcelles > 1 ? 's' : ''} · {v.union.surface_reelle_m2 != null ? `${fmtDec(v.union.surface_reelle_m2)} m²` : '—'}</b>
            {v.contiguite.ok ? (
              <p className="mt-0.5 text-[10.5px] text-txt-mut">
                Contiguës, assiette fusionnée · périmètre {v.union.perimetre_m != null ? `${fmtDec(v.union.perimetre_m)} m` : '—'} · aire cadastrale {fmtDec(v.union.aire_cadastrale_m2)} m²{v.union.ecart_m2 != null ? ` (écart ${v.union.ecart_m2 > 0 ? '+' : ''}${fmtDec(v.union.ecart_m2)} m²)` : ''}
              </p>
            ) : (
              <p className="mt-0.5 text-[11px] font-medium text-coral">{v.contiguite.message}</p>
            )}
          </div>

          <Signaux v={v} />
          {/* ETUDE-V6-6 (item 8) — ligne « Zone PLU : Urbanisme PLU/GPU (API Carto). » retirée de l'étape 1. */}
        </div>
      )}
    </div>
  )
}

// ETUDE-V6-3 (item 1) — règles PLU regroupées par ZONE pour l'assiette : une entête « PLU de [commune] ·
// zone [X] · N parcelles » puis les règles de la zone (servies une fois). Seules les zones avec règles.
function ReglesAssiette({ parcelles }: { parcelles: EtudeParcellesOut['parcelles'] }) {
  const groupes = new Map<string, { commune: string | null; zone: string | null; n: number; regles: NonNullable<EtudeParcelle['regles_plu']> }>()
  for (const p of parcelles) {
    const cle = `${p.commune ?? ''}|${p.zone_plu ?? ''}`
    const g = groupes.get(cle)
    if (g) g.n += 1
    else groupes.set(cle, { commune: p.commune, zone: p.zone_plu, n: 1, regles: p.regles_plu ?? [] })
  }
  const items = [...groupes.values()].filter((g) => g.regles.length > 0)
  if (items.length === 0) return null
  // ETUDE-V6-4 (item 2) — BANDEAU PLU distinct (pas une carte de parcelle) : accent vert, typo propre,
  // « Règles du PLU de … · zone … ». Les cartes de parcelles ne répètent plus les règles.
  return (
    <div data-regles-assiette className="mt-3 flex flex-col gap-2">
      {items.map((g) => (
        <section key={`${g.commune}|${g.zone}`} className="rounded-lg border-l-4 border-mint bg-mint-bg px-3.5 py-2.5">
          <p className="text-[9px] font-semibold uppercase tracking-[0.08em] text-mint">Règles du PLU</p>
          <b className="font-display text-[13px] text-txt-hi">de {g.commune} · zone {g.zone}</b>
          <span className="ml-1.5 text-[10px] text-txt-mut">{g.n} parcelle{g.n > 1 ? 's' : ''}</span>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {g.regles.map((r) => (
              <span key={r.nom} className="inline-flex items-center gap-1 rounded border border-mint/40 bg-surface-1 px-1.5 py-0.5 text-[10px] text-txt-mut transition-colors hover:border-mint">
                {r.nom} <b className="text-txt">{fmtDec(r.valeur)}{r.unite === '%' ? ' %' : ` ${r.unite}`}</b>
                <LireArticle r={r} />
              </span>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

// ETUDE-V6-4 (item 3) — « Lire l'article » : extrait VERBATIM du règlement (texte cité, article, page,
// millésime) + lien vers le document PLU officiel à la bonne page quand il existe (source_url#page).
function LireArticle({ r }: { r: { article?: string | null; page_pdf?: number | null; millesime?: string | null; citation?: string | null; source_url?: string | null; commune?: string | null; zone?: string | null } }) {
  const [ouvert, setOuvert] = useState(false)
  if (!r.article && !r.citation) return null
  const lien = r.source_url ? (r.page_pdf != null ? `${r.source_url}#page=${r.page_pdf}` : r.source_url) : null
  return (
    <span className="relative inline-block">
      <button type="button" data-lire-article onClick={() => setOuvert((o) => !o)}
        className="text-[8.5px] text-mint underline decoration-dotted hover:decoration-solid">Lire l'article</button>
      {ouvert && (
        <span className="absolute left-0 top-[1.4em] z-30 block w-[280px] rounded-md border border-line-2 bg-surface-1 p-2.5 text-left shadow-lg">
          <span className="block text-[9px] font-semibold uppercase tracking-wide text-mint">{pluRef(r.commune, r.zone, r.article, r.millesime)}{r.page_pdf != null ? ` · p. ${r.page_pdf}` : ''}</span>
          {r.citation && <span className="mt-1 block text-[10px] italic text-txt">« {r.citation} »</span>}
          {lien
            ? <a href={lien} target="_blank" rel="noopener noreferrer" className="mt-1.5 block text-[9.5px] text-mint hover:underline">Ouvrir le règlement PLU officiel ↗</a>
            : <span className="mt-1.5 block text-[9px] text-txt-dim">Document PLU officiel non disponible en lien direct.</span>}
        </span>
      )}
    </span>
  )
}

function Signaux({ v }: { v: EtudeParcellesOut }) {
  const s = v.signaux
  const items: string[] = []
  if (s.communes_differentes) items.push(`Communes différentes : ${s.communes_differentes.join(', ')}.`)
  if (s.zones_differentes) items.push(`Zones PLU différentes : ${s.zones_differentes.join(', ')} — chaque sous-secteur a son règlement.`)
  if (s.ravine_traversante) items.push('Une ravine recoupe l\'assiette (à vérifier : emprise, recul, PPR).')
  if (s.proprietaires_presumes) items.push(`${s.proprietaires_presumes} propriétaire(s) présumé(s) (personnes morales en base) — la contiguïté ne prouve pas la maîtrise foncière.`)
  if (!items.length) return null
  return (
    <div className="rounded-md border border-amber/40 bg-amber-bg px-3 py-2">
      <b className="text-[11px] text-amber">À signaler (sans conclure sur la constructibilité)</b>
      <ul className="mt-1 list-disc pl-4 text-[10.5px] text-txt-mut">{items.map((t) => <li key={t}>{t}</li>)}</ul>
    </div>
  )
}


// ── Étape 2 — Type de projet ─────────────────────────────────────────────────────────────────────
function EtapeType({ projet, onChoisir, regimes, chargement, commune, zone, mixite }: {
  projet: ProjetKey | null; onChoisir: (k: ProjetKey) => void
  regimes?: EtudeStationnementRegimes; chargement: boolean; commune?: string | null; zone?: string | null
  mixite?: { quota_pct: number | null; seuil_m2: number | null; article: string | null; page_pdf: number | null; citation: string | null; source_url?: string | null; millesime?: string | null } | null
}) {
  return (
    <div>
      <EnTetePanneau n="02" titre="Quel type de projet ?" sous="Sélectionnez la destination de votre opération." />
      <div className="grid gap-2.5 sm:grid-cols-2">
        {PROJETS.map((pr) => {
          const on = pr.key === projet
          return (
            <button key={pr.key} type="button" data-etude-type={pr.key} onClick={() => onChoisir(pr.key)}
              className={`rounded-lg border px-3.5 py-3 text-left transition-colors duration-quick ${on ? 'border-mint bg-mint text-mint-on' : 'border-line-2 hover:border-mint/50'}`}>
              {/* ETUDE-V6-6 (item 7) — carte de type sélectionnée = vert OPAQUE (fond plein, texte sombre). */}
              <b className={`block text-[13px] ${on ? 'text-mint-on' : 'text-txt-hi'}`}>{pr.label}</b>
              <small className={`text-[11px] ${on ? 'text-mint-on/80' : 'text-txt-dim'}`}>{pr.desc}</small>
            </button>
          )
        })}
      </div>
      {projet && chargement && <div className="mt-3"><Chargement /></div>}
      {projet && regimes && <StationnementRegle regimes={regimes} lotissement={projet === 'lotissement'} commune={commune} zone={zone} />}
      {/* ETUDE-V6-4 (item 5) — mixité sociale dès l'étape 2 (comme résultat + PDF). */}
      {projet && mixite && (
        <div data-mixite-etape2 className="mt-2 rounded-md border border-line-2 bg-surface-1 px-3 py-2 text-[10.5px] text-txt">
          <b className="text-[11px] text-txt">Mixité sociale</b>
          <span className="ml-1.5">{fmtDec(mixite.quota_pct ?? 0)} % de logements aidés{mixite.seuil_m2 != null ? ` au-delà de ${fmtDec(mixite.seuil_m2)} m² de SDP` : ''}.</span>
          <LireArticle r={{ article: mixite.article, page_pdf: mixite.page_pdf, millesime: mixite.millesime, citation: mixite.citation, source_url: mixite.source_url, commune, zone }} />
        </div>
      )}
    </div>
  )
}

// ── Lot C — la règle de stationnement applicable (règle générale PLU + plafond L151-35 à confirmer) ──
function StationnementRegle({ regimes, lotissement, commune, zone }: { regimes: EtudeStationnementRegimes; lotissement?: boolean; commune?: string | null; zone?: string | null }) {
  const g = regimes.general, pf = regimes.plafond_national
  return (
    <div data-stationnement className="mt-3 flex flex-col gap-2">
      <div className="rounded-md border border-line-2 bg-surface-1 px-3 py-2">
        <div className="flex flex-wrap items-center gap-2">
          <b className="text-[11.5px] text-txt">Règle générale du PLU</b>
          <Badge ton={g.validee ? 'vert' : 'ambre'}>{g.etat}</Badge>
        </div>
        {/* ETUDE-V6-3 (item 2) — préfixe normalisé « PLU de [commune] · zone [X] · art. [n°] · millésime ». */}
        <p className="mt-1 text-[10px] text-txt-dim">{pluRef(commune, zone, g.article, g.millesime)}</p>
        <p className="mt-0.5 text-[11px] text-txt">{g.regle_courte ?? (g.ratio_par_logement != null ? `${fmtDec(g.ratio_par_logement)} place / logement` : 'barème par typologie')}</p>
        {g.citation && <p className="mt-0.5 text-[9.5px] text-txt-dim">« {g.citation} »</p>}
        {/* ETUDE-V6-4 (item 3) — « Lire l'article » dès l'étape 2 (stationnement). */}
        <LireArticle r={{ article: g.article, page_pdf: g.page_pdf, millesime: g.millesime, citation: g.citation, source_url: g.source_url, commune, zone }} />
      </div>
      {pf && (
        <div className="rounded-md border border-amber/40 bg-amber-bg px-3 py-2">
          <div className="flex flex-wrap items-center gap-2">
            <b className="text-[11.5px] text-amber">Plafond national {pf.reference} — sous condition d'éligibilité</b>
            <Badge ton="ambre">{pf.statut}</Badge>
          </div>
          <p className="mt-1 text-[11px] text-txt">
            Au plus <b>{fmtDec(pf.ratio_plafond)} place / logement</b> pour {pf.categorie}.
            {' '}Condition « à moins de 800 m d'un transport collectif » : {pf.condition_tcsp_sous_800m
              ? <span className="text-mint">vérifiée{pf.distance_tcsp_m != null ? ` (${fmtInt(pf.distance_tcsp_m)} m)` : ''}</span>
              : <span className="text-coral">non remplie</span>}. Éligibilité de catégorie : <b className="text-amber">{pf.eligibilite_categorie}</b>.
          </p>
          <p className="mt-0.5 text-[9.5px] text-txt-dim">{pf.note}</p>
        </div>
      )}
      {lotissement && (
        <p className="text-[10.5px] text-txt-mut">Lotissement : division foncière — les obligations de stationnement portent sur les futures constructions des lots.</p>
      )}
    </div>
  )
}

// ── Étape 3 — Programme ──────────────────────────────────────────────────────────────────────────
function EtapeProgramme({ nb, setNb, totalLogts, surfaceProg, surfaceVar, surfaceInt, lotissement, jauge, jaugeChargement, jaugeManquant, statioChoix, onStatioChoix, sousSolDispo }: {
  nb: Record<TypeKey, number>; setNb: (f: (n: Record<TypeKey, number>) => Record<TypeKey, number>) => void
  totalLogts: number; surfaceProg: number; surfaceVar: number; surfaceInt: number; lotissement: boolean
  jauge: ReturnType<typeof enveloppeJauge>; jaugeChargement: boolean; jaugeManquant: string[] | null
  statioChoix: 'aerien' | 'sous_sol'; onStatioChoix: (c: 'aerien' | 'sous_sol') => void
  sousSolDispo: { disponible: boolean; raison: string } | null
}) {
  const ssDispo = sousSolDispo?.disponible !== false   // disponible par défaut (tant que la jauge n'a pas répondu)
  const set = (t: TypeKey, val: number) => setNb((n) => ({ ...n, [t]: Math.max(0, Math.min(200, val)) }))
  return (
    <div>
      <EnTetePanneau n="03" titre="Combien de logements souhaitez-vous ?" sous="Indiquez simplement le nombre de T1, T2, T3 et T4." />
      {lotissement && (
        <div className="mb-3 rounded-md border border-amber/40 bg-amber-bg px-3 py-2 text-[10.5px] text-txt-mut">
          <b className="text-amber">Lotissement</b> — la composition des logements est informative : la faisabilité dépendra d'abord de la division en lots et des voiries à dessiner.
        </div>
      )}
      <div className="flex flex-col gap-2">
        {TYPES.map((t) => (
          <div key={t} className="flex items-center gap-3 rounded-md border border-line-2 bg-surface-1 px-3 py-2">
            <span className="w-8 font-mono text-[13px] font-bold text-txt-hi">{t}</span>
            <div className="flex-1">
              <b className="text-[12px] text-txt">{SURF[t].area} m²</b>
              <small className="ml-2 text-[10px] text-txt-dim">dont {SURF[t].varangue} m² de varangue · {SURF[t].area - SURF[t].varangue} m² intérieur indicatif</small>
            </div>
            <div className="flex items-center gap-1">
              <button type="button" onClick={() => set(t, nb[t] - 1)} aria-label={`Retirer un ${t}`} className="flex h-7 w-7 items-center justify-center rounded border border-line-2 text-txt hover:border-mint/60">−</button>
              <input type="number" min={0} max={200} inputMode="numeric" aria-label={`Nombre de ${t}`} data-etude-count={t}
                value={nb[t]} onChange={(e) => set(t, parseInt(e.target.value || '0', 10))}
                className="w-14 rounded border border-line-2 bg-surface-2 px-2 py-1 text-center text-[12px] text-txt-hi" />
              <button type="button" onClick={() => set(t, nb[t] + 1)} aria-label={`Ajouter un ${t}`} className="flex h-7 w-7 items-center justify-center rounded border border-line-2 text-txt hover:border-mint/60">+</button>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-3 flex items-center justify-between rounded-md border border-line-2 bg-surface-1 px-3 py-2">
        <div>
          <b className="text-[12.5px] text-txt-hi">{fmtInt(totalLogts)} logement{totalLogts > 1 ? 's' : ''} au programme</b>
          <p className="text-[10.5px] text-txt-dim">dont {fmtDec(surfaceVar)} m² de varangues · {fmtDec(surfaceInt)} m² d'intérieur indicatif</p>
        </div>
        <div className="text-right">
          <b className="font-display text-[20px] text-txt-hi">{fmtDec(surfaceProg)} m²</b>
          <p className="text-[10px] text-txt-dim">surface du programme</p>
        </div>
      </div>
      {/* ETUDE-V6-7 (items 3/4) — STATIONNEMENT choisi dès l'étape 3 : Aérien / Sous-sol 1 niveau (plus de
          2 niveaux). L'option Sous-sol est GRISÉE avec sa raison si le terrain touche un PPR ou si le
          règlement l'interdit ; sinon « à confirmer géotechnique/nappe ». */}
      {!lotissement && (
        <div className="mt-3 flex flex-wrap items-center gap-2 rounded-md border border-line-2 bg-surface-1 px-3 py-2 text-[10.5px] text-txt-mut">
          <span>Stationnement</span>
          <div className="inline-flex overflow-hidden rounded border border-line-2" role="group" aria-label="Mode de stationnement">
            {([['aerien', 'Aérien', true], ['sous_sol', 'Sous-sol 1 niveau', ssDispo]] as const).map(([c, lib, actif]) => (
              <button key={c} type="button" data-statio-etape3={c} disabled={!actif}
                onClick={() => actif && onStatioChoix(c)}
                className={`px-2 py-0.5 text-[10.5px] ${statioChoix === c && actif ? 'bg-mint font-semibold text-mint-on' : actif ? 'text-txt-mut hover:bg-surface-2' : 'cursor-not-allowed text-txt-dim/50 line-through'}`}>{lib}</button>
            ))}
          </div>
          {sousSolDispo && (
            <span data-sous-sol-raison className={`text-[9.5px] ${ssDispo ? 'text-txt-dim' : 'text-amber'}`}>{sousSolDispo.raison}</span>
          )}
        </div>
      )}
      {/* ETUDE-V6-6 (item 5) — JAUGE EN LOGEMENTS : ≈ N estimés vs demande. Grise si donnée manquante. */}
      {!lotissement && totalLogts > 0 && (
        <JaugeEnveloppe jauge={jauge} chargement={jaugeChargement} manquant={jaugeManquant} demande={totalLogts} />
      )}
      <p className="mt-2 text-[10px] text-txt-dim">Ces surfaces sont des hypothèses de programme (varangue comprise). La capacité ci-dessus est une estimation en logements, affinée par le calcul complet.</p>
    </div>
  )
}

// ── ETUDE-V6-6 (item 5) — jauge EN LOGEMENTS (étape 3, avant le calcul) : « ≈ N logements estimés »,
//    barre demande / estimation. Jamais le mot SDP. Tient compte du stationnement choisi (sous-sol = sol libre).
function JaugeEnveloppe({ jauge, chargement, manquant, demande }: {
  jauge: ReturnType<typeof enveloppeJauge>; chargement: boolean; manquant: string[] | null; demande: number
}) {
  if (manquant && manquant.length > 0) {
    return (
      <div data-jauge="non-estimable" className="mt-3 rounded-md border border-line-2 bg-surface-1 px-3 py-2.5">
        <div className="mb-1.5 flex items-center justify-between">
          <b className="text-[11.5px] text-txt">Capacité estimée <span className="text-[9px] font-normal uppercase tracking-wide text-txt-dim">· estimé</span></b>
          <span className="text-[10.5px] text-txt-mut">non estimable</span>
        </div>
        <div className="h-2 w-full rounded-full bg-line-2" />
        <p className="mt-1 text-[10px] text-txt-dim">Donnée manquante : {manquant.join(' · ')}. La capacité ne peut pas être estimée avant le calcul.</p>
      </div>
    )
  }
  if (!jauge) {
    return (
      <div data-jauge="chargement" className="mt-3 rounded-md border border-line-2 bg-surface-1 px-3 py-2.5">
        <b className="text-[11.5px] text-txt">Capacité estimée <span className="text-[9px] font-normal uppercase tracking-wide text-txt-dim">· estimé</span></b>
        <div className="mt-1.5 h-2 w-full animate-pulse rounded-full bg-line-2" />
        <p className="mt-1 text-[10px] text-txt-dim">{chargement ? 'Estimation en cours…' : 'Capacité estimée dès que l\'assiette est prête.'}</p>
      </div>
    )
  }
  // vert < 90 % · ORANGE 90–100 % (« à la limite, le calcul tranchera ») · rouge au-delà (demande > estimation).
  const estime = jauge.estime
  const ratio = estime > 0 ? demande / estime : (demande > 0 ? 2 : 0)
  const etat = demande > estime ? 'depassement' : ratio >= 0.9 ? 'limite' : 'ok'
  const pct = Math.min(100, Math.round(ratio * 100))
  const barre = etat === 'depassement' ? 'bg-coral' : etat === 'limite' ? 'bg-amber' : 'bg-mint'
  const cadre = etat === 'depassement' ? 'border-coral/50 bg-coral/5' : etat === 'limite' ? 'border-amber/50 bg-amber-bg' : 'border-line-2 bg-surface-1'
  const modeTxt = jauge.mode === 'sous_sol' ? 'sous-sol (sol libre)' : 'aérien'
  return (
    <div data-jauge={etat} className={`mt-3 rounded-md border px-3 py-2.5 ${cadre}`}>
      <div className="mb-1.5 flex items-center justify-between">
        <b className="text-[11.5px] text-txt">≈ {fmtInt(estime)} logements estimés <span className="text-[9px] font-normal uppercase tracking-wide text-txt-dim">· avant calcul · {modeTxt}</span></b>
        <span className="text-[10.5px] text-txt-mut">{fmtInt(demande)} demandés / ≈ {fmtInt(estime)} estimés</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-line-2">
        <div className={`h-full rounded-full ${barre}`} style={{ width: `${pct}%` }} />
      </div>
      {etat === 'depassement' ? (
        <p className="mt-1.5 text-[10.5px] text-coral">⚠ Vous demandez {fmtInt(demande)} logements pour ≈ {fmtInt(estime)} estimés sur ce terrain. Il n'en tiendra probablement pas autant — réduisez, ou passez en sous-sol (le parking libère le sol).</p>
      ) : etat === 'limite' ? (
        <p className="mt-1.5 text-[10.5px] text-amber">À la limite ({pct} % de la capacité estimée {jauge.niveaux_label}) — le calcul tranchera.</p>
      ) : (
        <p className="mt-1 text-[10px] text-txt-dim">Estimation {modeTxt} avant calcul (zone {fmtDec(jauge.zone_m2)} m² · {jauge.niveaux_label} · coef {jauge.coef}). Le calcul complet affine ce chiffre.</p>
      )}
    </div>
  )
}

function EnTetePanneau({ n, titre, sous }: { n: string; titre: string; sous: string }) {
  return (
    <div className="mb-3 flex items-start gap-2.5">
      <span className="flex h-7 shrink-0 items-center rounded bg-mint-bg px-2 font-mono text-[11px] font-bold text-mint">{n}</span>
      <div><h2 className="text-[16px] font-bold text-txt-hi">{titre}</h2><p className="text-[11px] text-txt-dim">{sous}</p></div>
    </div>
  )
}

// ── Récapitulatif ────────────────────────────────────────────────────────────────────────────────
// ETUDE-V6-2 (Lot 5) — le récap affiche « — » tant qu'une donnée n'est pas choisie/saisie (jamais 0,
// jamais « Non vérifié ») : un tiret dit « pas encore renseigné », pas « absent / problème ».
function Recap({ sel, v, projet, totalLogts, surfaceProg, surfaceVar, stationnement }: {
  sel: string[]; v?: EtudeParcellesOut; projet: ProjetKey | null
  totalLogts: number; surfaceProg: number; surfaceVar: number; stationnement: string | null
}) {
  const surfaceTerrain = v?.union.surface_reelle_m2
  const projetLabel = projet ? PROJETS.find((p) => p.key === projet)!.label : '—'
  return (
    <aside className="flex h-fit flex-col gap-0 rounded-lg border border-line-2 bg-surface-2 p-3">
      <p className="text-[9px] font-semibold uppercase tracking-wide text-mint">Récapitulatif</p>
      <div className="mt-2 rounded-md border border-line-2 bg-surface-1 px-3 py-2.5">
        <p className="text-[10.5px] text-txt-dim">Terrain sélectionné</p>
        <div className="font-display text-[26px] font-bold leading-none text-txt-hi">{surfaceTerrain != null ? fmtDec(surfaceTerrain) : '—'} {surfaceTerrain != null && <span className="text-[15px]">m²</span>}</div>
        <p className="mt-0.5 text-[10.5px] text-txt-dim">{sel.length > 0 ? `${sel.length} parcelle${sel.length > 1 ? 's' : ''}` : '—'}</p>
      </div>
      <Ligne l="Projet" v={projetLabel} />
      <Ligne l="Logements demandés" v={totalLogts > 0 ? fmtInt(totalLogts) : '—'} />
      <Ligne l="Surface du programme" v={totalLogts > 0 ? `${fmtDec(surfaceProg)} m²` : '—'} sous={totalLogts > 0 && surfaceVar > 0 ? `dont ${fmtDec(surfaceVar)} m² varangues` : undefined} />
      <Ligne l="Stationnement PLU" v={stationnement ?? '—'} />
    </aside>
  )
}
function Ligne({ l, v, sous, ton }: { l: string; v: string; sous?: string; ton?: 'ambre' }) {
  const vide = v === '—'
  return (
    <div className="flex items-center justify-between border-t border-line-2 py-2">
      <div><span className="text-[11.5px] text-txt-mut">{l}</span>{sous && <p className="text-[9.5px] text-txt-dim">{sous}</p>}</div>
      <b className={`text-[12px] ${vide ? 'text-txt-dim' : ton === 'ambre' ? 'text-amber' : 'text-txt-hi'}`}>{v}</b>
    </div>
  )
}

// ── Pied d'étape (navigation + action) ───────────────────────────────────────────────────────────
function PiedEtape({ step, peutContinuer1, peutAnalyser, enAnalyse, erreurAnalyse, onPrec, onSuiv, onAnalyser, projetChoisi }: {
  step: 1 | 2 | 3; peutContinuer1: boolean; peutAnalyser: boolean; enAnalyse: boolean; erreurAnalyse: unknown
  onPrec: () => void; onSuiv: () => void; onAnalyser: () => void; projetChoisi: boolean
}) {
  // ETUDE-V6-2 (Lot 5) — plus de bandeau descriptif au bas des 3 étapes : SEULEMENT Retour / Continuer /
  // Analyser. On garde le feedback FONCTIONNEL minimal (raison d'un blocage, « Calcul en cours », erreur).
  const suivBloque = step === 1 ? !peutContinuer1 : step === 2 ? !projetChoisi : false
  const raison = step === 1 && !peutContinuer1 ? 'Sélectionnez des parcelles contiguës pour continuer.'
    : step === 2 && !projetChoisi ? 'Choisissez un type de projet pour continuer.' : ''
  // ETUDE-V6-7 (item 8) — dans la colonne de droite (sous le récap, sticky) : feedback seulement s'il a du
  // contenu ; boutons en bas de carte, pleine largeur de la colonne.
  const feedback = raison || enAnalyse || !!erreurAnalyse
  return (
    <div className="flex flex-col gap-1.5 rounded-lg border border-line-2 bg-surface-2 p-3">
      {feedback && (
        <div className="text-[10.5px]">
          {raison && <span className="text-amber">{raison}</span>}
          {enAnalyse && <span className="text-txt-dim">Calcul en cours, jusqu'à une minute…</span>}
          {!!erreurAnalyse && <span className="text-coral">{(erreurAnalyse as Error).message}</span>}
        </div>
      )}
      <div className="flex items-center gap-2">
        {step > 1 && <Bouton niveau="secondaire" onClick={onPrec}>← Retour</Bouton>}
        {step < 3 && <Bouton niveau="primaire" onClick={onSuiv} disabled={suivBloque}>Continuer →</Bouton>}
        {step === 3 && <Bouton niveau="primaire" onClick={onAnalyser} disabled={!peutAnalyser || enAnalyse}>{enAnalyse ? 'Calcul en cours…' : 'Analyser mon projet →'}</Bouton>}
      </div>
    </div>
  )
}

export default EtudeV6
