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
import type { EtudeParcellesOut, EtudePayload, EtudeVariante, EtudeGrandeur, EtudeStationnementRegimes, EtudeLotissement, EtudeIn } from '../../lib/api'
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

// ETUDE-V6-2 (Lot 4) — enveloppe ESTIMÉE (jauge étape 3) : (zone d'implantation − sol du stationnement
// aérien) × niveaux (hauteur PLU) × coef plancher. `programme` = m² demandés. Renvoie null si non estimable.
function enveloppeJauge(jd: EtudeJaugeOut | undefined, demande: Record<string, number>, surfaceDe: (t: string) => number) {
  if (!jd || !jd.estimable) return null
  const placesEst = Object.entries(demande).reduce((s, [t, n]) => s + n * (jd.places_par_type?.[t] ?? 1), 0)
  const solStat = placesEst * (jd.m2_par_place_aerien ?? 18)
  const enveloppe = Math.max(0, ((jd.zone_implantation_m2 ?? 0) - solStat) * (jd.niveaux ?? 0) * (jd.coef_plancher ?? 0))
  const programme = Object.entries(demande).reduce((s, [t, n]) => s + n * surfaceDe(t), 0)
  return { placesEst, solStat, enveloppe, programme, niveaux_label: jd.niveaux_label ?? '', zone_m2: jd.zone_implantation_m2 ?? 0, coef: jd.coef_plancher ?? 0 }
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

export function EtudeV6({ initialIdus, onClose, onBilan }: {
  initialIdus?: string[]; onClose?: () => void; onBilan?: (prog: EtudeProgramme) => void
}) {
  const [step, setStep] = useState<1 | 2 | 3>(1)
  const [sel, setSel] = useState<string[]>(initialIdus ?? [])
  const [projet, setProjet] = useState<ProjetKey | null>(null)
  const [nb, setNb] = useState<Record<TypeKey, number>>({ T1: 0, T2: 0, T3: 0, T4: 0 })
  const [variantActive, setVariantActive] = useState<string>('votre_programme')
  // Hypothèses modifiables (mandat) : surfaces T1–T4, varangues, et hypothèses MOTEUR (profondeur,
  // coef plancher). Vides = valeurs LABUSE par défaut. Édition dans le résultat → recalcul → même PDF.
  const [hyp, setHyp] = useState<{ surf: Record<TypeKey, string>; varangue: Record<TypeKey, string>; profondeur: string; coef: string; stationnement: 'aerien' | 'sous_sol' }>(
    { surf: { T1: '', T2: '', T3: '', T4: '' }, varangue: { T1: '', T2: '', T3: '', T4: '' }, profondeur: '', coef: '', stationnement: 'aerien' })
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
    return Object.keys(h).length ? h : undefined
  }
  // UNE seule config sert l'analyse ET le PDF (surfaces éditées via les lignes du programme → study_id).
  const corpsBody = (over?: Partial<EtudeIn>): EtudeIn => ({
    idus: sel, type_projet: projet ?? 'collectif',
    // ETUDE-V6-2 (Lot 3) — le mode de stationnement (aérien par défaut / sous-sol) pilote l'implantation.
    stationnement: hyp.stationnement,
    programme: { mode: 'saisi', lignes: TYPES.filter((t) => nb[t] > 0).map((t) => ({ type: t, nombre: nb[t], surface_m2: surfOf(t) })) },
    hypotheses: hypBody(),
    ...over,
  })
  const BoutonPdf = () => (
    <Bouton niveau="secondaire" onClick={() => pdf.ouvrir(ETUDE_PDF_URL, 'etude-pdf', etudePdfInit(corpsBody()))} disabled={!!pdf.enCours}>
      {pdf.enCours ? 'Génération…' : 'Générer le PDF ↓'}
    </Bouton>
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

  // Analyse (étape finale ET recalcul) : un seul appel moteur avec la config courante (hypothèses comprises).
  const analyse = useMutation({ mutationFn: (body?: EtudeIn) => postEtude(body ?? corpsBody()) })
  const recalculer = () => analyse.mutate(undefined)
  // ETUDE-V6-2 (Lot 3) — « Testez en sous-sol » : bascule le mode ET relance en UN clic (on passe le corps
  // explicitement, car setHyp est asynchrone). Calculé seulement à la demande → l'étude aérienne reste rapide.
  const testerSousSol = () => {
    setHyp((h) => ({ ...h, stationnement: 'sous_sol' }))
    analyse.mutate(corpsBody({ stationnement: 'sous_sol' }))
  }
  const setModeStationnement = (m: 'aerien' | 'sous_sol') => setHyp((h) => ({ ...h, stationnement: m }))
  const resultat: EtudePayload | undefined = analyse.data

  // ETUDE-V6-2 (Lot 1) — l'étape 3 et le récap lisent TOUJOURS les surfaces par défaut (SURF), source
  // unique. Les hypothèses éditées (dans le résultat) n'affectent QUE le résultat, après « Recalculer ».
  const totalLogts = TYPES.reduce((s, t) => s + nb[t], 0)
  const surfaceProg = TYPES.reduce((s, t) => s + nb[t] * SURF[t].area, 0)
  const surfaceVar = TYPES.reduce((s, t) => s + nb[t] * SURF[t].varangue, 0)
  const surfaceInt = surfaceProg - surfaceVar

  // ETUDE-V6-2 (Lot 4) — enveloppe estimée vs programme saisi (surfaces par défaut, comme l'étape 3).
  const demandeNb: Record<string, number> = Object.fromEntries(TYPES.filter((t) => nb[t] > 0).map((t) => [t, nb[t]]))
  const jauge = enveloppeJauge(jaugeQ.data, demandeNb, (t) => SURF[t as TypeKey]?.area ?? 0)

  const contiguOk = sel.length > 0 && !!v?.contiguite.ok
  const peutContinuer1 = contiguOk && !valide.isFetching
  const peutAnalyser = contiguOk && !!projet && totalLogts > 0

  function reset() { setStep(1); setSel([]); setProjet(null); setNb({ T1: 0, T2: 0, T3: 0, T4: 0 }); resetHyp(); analyse.reset() }
  function resetHyp() { setHyp({ surf: { T1: '', T2: '', T3: '', T4: '' }, varangue: { T1: '', T2: '', T3: '', T4: '' }, profondeur: '', coef: '', stationnement: 'aerien' }) }
  // « Modifier le programme » revient au formulaire ET réinitialise les hypothèses éditées (pas de fuite).
  function modifierProgramme() { resetHyp(); analyse.reset() }
  const editeurHyp = (collectif: boolean) => (
    <HypothesesEditor hyp={hyp} setHyp={setHyp} surfOf={surfOf} varOf={varOf} types={TYPES.filter((t) => nb[t] > 0)}
      collectif={collectif} onRecalculer={recalculer} enCours={analyse.isPending}
      mode={hyp.stationnement} onMode={setModeStationnement} />
  )
  function ajouter(idu: string) { setSel((xs) => (xs.includes(idu) || xs.length >= 8 ? xs : [...xs, idu])) }
  function retirer(idu: string) { setSel((xs) => xs.filter((x) => x !== idu)) }

  // ── RÉSULTAT LOTISSEMENT (Lot D) — plan de division, pas des scénarios d'implantation.
  if (resultat?.lotissement) {
    return (
      <div className="flex min-h-full flex-col">
        <Entete onClose={onClose} onReset={modifierProgramme} resetLabel="← Modifier le programme" />
        <div className="flex items-center gap-3 border-b border-line-2 px-4 py-3">
          <span className="text-[12px] text-txt-dim">Verdict de l'étude</span>
          <Badge ton="ambre">{resultat.verdict}</Badge>
          <span className="text-[11px] text-txt-dim">{resultat.entrees.commune} · zone {resultat.entrees.zone} · lotissement</span>
        </div>
        <LotissementResultat lot={resultat.lotissement} hypothese={resultat.logements_hypothese} boutonPdf={<BoutonPdf />} pdfErreur={pdf.erreur ?? undefined} studyId={resultat.study_id} editeur={editeurHyp(false)} />
        <p className="px-4 pb-4 text-[10px] leading-snug text-txt-dim">{resultat.lotissement.note}</p>
      </div>
    )
  }

  // ── RÉSULTAT (Lot B) — le résultat qui explique : Votre demande → Ce que le terrain accueille →
  //    L'écart → Ce qui limite → Alternative ; 4 grandeurs séparées ; 3 variantes ; 5 états ; verdict.
  if (resultat) {
    const variantes = resultat.variantes ?? []
    const active = variantes.find((v) => v.role === variantActive) ?? variantes[0]
    const alternative = variantes.find((v) => v.role === 'alternative')
    // ETUDE-V6-2 (Lot 1) — « Votre demande » lit la config RÉELLEMENT ANALYSÉE (payload), source unique :
    // ni l'état live de l'éditeur ni des défauts recalculés → jamais de décalage avec le moteur/le PDF.
    const demMap: Record<string, number> = resultat.programme_saisi?.demande ?? Object.fromEntries(TYPES.filter((t) => nb[t] > 0).map((t) => [t, nb[t]]))
    const surfA = (t: string) => resultat.hypotheses?.surfaces?.[t] ?? SURF[t as TypeKey]?.area ?? 0
    const varA = (t: string) => resultat.hypotheses?.varangues?.[t] ?? SURF[t as TypeKey]?.varangue ?? 0
    const demProg = Object.entries(demMap).reduce((s, [t, n]) => s + n * surfA(t), 0)
    const demVar = Object.entries(demMap).reduce((s, [t, n]) => s + n * varA(t), 0)
    const demTotal = Object.values(demMap).reduce((s, n) => s + n, 0)
    // ETUDE-V6-2 (Lot 4) — DIVERGENCE : si l'estimation rapide (jauge étape 3) et le calcul (capacité
    // maximale SDP) s'écartent de plus de 20 %, le RÉSULTAT le dit (l'enveloppe estimée était optimiste/prudente).
    const jaugeRes = enveloppeJauge(jaugeQ.data, demMap, surfA)
    const capSdp = resultat.capacite_maximale?.sdp_m2 ?? 0
    const divergence = (jaugeRes && capSdp > 0 && Math.abs(jaugeRes.enveloppe - capSdp) / capSdp > 0.2)
      ? { estime: jaugeRes.enveloppe, calcule: capSdp, pct: Math.round((Math.abs(jaugeRes.enveloppe - capSdp) / capSdp) * 100) }
      : null
    const bilanDe = (v: EtudeVariante): EtudeProgramme =>
      ({ ref: v.role_label, logements: v.resume.logements, par_type: v.programme.par_type, sdp_m2: v.resume.sdp_m2, shab_m2: v.programme.shab_estimee_m2 })
    return (
      <div className="flex min-h-full flex-col">
        <Entete onClose={onClose} onReset={modifierProgramme} resetLabel="← Modifier le programme" />
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line-2 px-4 py-3">
          <div className="flex items-center gap-3">
            <span className="text-[12px] text-txt-dim">Verdict de l'étude</span>
            <Badge ton={verdictTon(resultat.verdict ?? '')}>{resultat.verdict}</Badge>
          </div>
          {variantes.length > 0 && (
            <div className="flex flex-wrap gap-1" role="tablist" aria-label="Variantes">
              {variantes.map((v) => {
                const on = v.role === active?.role
                return (
                  <button key={v.role} type="button" data-variante={v.role} onClick={() => setVariantActive(v.role)}
                    className={`rounded border px-2.5 py-1 text-[11px] transition-colors duration-quick ${on ? 'border-mint bg-mint font-semibold text-mint-on' : 'border-line-2 text-txt-mut hover:border-mint/60'}`}>
                    {v.role_label}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {resultat.depassement && <Depassement d={resultat.depassement} limite={variantes.find((v) => !v.absente)?.limite_capacite} />}

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
              {/* 4 grandeurs séparées */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <GrandeurCard l="Sol restant" g={active.grandeurs.sol_restant} />
                <GrandeurCard l="Emprise mobilisable" g={active.grandeurs.emprise_mobilisable} />
                <GrandeurCard l="SDP autorisée" g={active.grandeurs.sdp_autorisee} />
                <GrandeurCard l="Programme envisageable" g={active.grandeurs.programme_envisageable} />
              </div>
              {/* plan masse de la variante active */}
              {active.geojson && (
                <div className="rounded-lg border border-line-2 bg-surface-2 p-3">
                  <p className="mb-2 text-[11px] font-semibold text-txt">Plan masse — {active.role_label} · {active.forme} · {active.niveaux_label}</p>
                  <PlanMasseSvg fc={active.geojson} svg={active.planche_svg} groupesCaches={[]} />
                </div>
              )}
              {/* stationnement par destination : règle générale PLU + plafond L151-35 + capacité réduite */}
              {resultat.stationnement_regimes && (
                <StationnementResultat regimes={resultat.stationnement_regimes} reduite={resultat.capacite_reduite}
                  placesActive={active.resume.places} logtsActive={active.resume.logements} />
              )}
              {/* contrôles — 5 états */}
              <Controles v={active} />
            </section>

            {/* Récit : demande → accueil → écart → limite → alternative */}
            <aside className="flex flex-col gap-3">
              <Recit titre="Votre demande">
                <p className="text-[12px] text-txt">{fmtInt(demTotal)} logements · {fmtDec(demProg)} m² de programme</p>
                <p className="text-[10.5px] text-txt-dim">dont {fmtDec(demVar)} m² de varangues · {fmtDec(demProg - demVar)} m² d'intérieur indicatif</p>
                <p className="mt-1 text-[10.5px] text-txt-dim">{Object.entries(demMap).filter(([, n]) => n > 0).map(([t, n]) => `${n}×${t}`).join(' · ')}</p>
              </Recit>
              {/* ETUDE-V6-2 (Lot 2) — capacité MAXIMALE du terrain, calculée une fois et STABLE (indépendante
                  de la demande, répartition équilibrée) ; la demande y est ensuite confrontée. */}
              {resultat.capacite_maximale && (
                <Recit titre="Capacité maximale du terrain" ton={resultat.confrontation ? (resultat.confrontation.tient ? 'vert' : 'ambre') : undefined}>
                  <p className="text-[12px] text-txt-hi">{fmtInt(resultat.capacite_maximale.logements)} logements · {resultat.capacite_maximale.niveaux_label} · {resultat.capacite_maximale.forme}</p>
                  <p className="text-[10.5px] text-txt-dim">{Object.entries(resultat.capacite_maximale.par_type).map(([t, n]) => `${n}×${t}`).join(' · ')} · répartition {resultat.capacite_maximale.repartition}</p>
                  {resultat.confrontation && (
                    <p className="mt-1 text-[11px] text-txt">{resultat.confrontation.tient
                      ? <>Votre demande de {fmtInt(resultat.confrontation.demande_logements)} logements <b className="text-mint">tient</b> (réserve {fmtInt(resultat.confrontation.reserve_logements)}).</>
                      : <>Votre demande de {fmtInt(resultat.confrontation.demande_logements)} logements <b className="text-amber">dépasse</b> ce maximum de {fmtInt(-resultat.confrontation.reserve_logements)}.</>}</p>
                  )}
                  <p className="mt-0.5 text-[9.5px] text-txt-dim">Maximum du terrain sous {resultat.capacite_maximale.repartition} — indépendant du <b>nombre</b> demandé (deux demandes de même répartition donnent le même maximum).</p>
                  {/* ETUDE-V6-2 (Lot 4) — divergence estimation (jauge étape 3) ↔ calcul > 20 % : on le dit. */}
                  {divergence && (
                    <p data-divergence className="mt-1 text-[10.5px] text-amber">⚠ L'estimation rapide de l'étape 3 ({fmtDec(divergence.estime)} m² de SDP) et le calcul complet ({fmtDec(divergence.calcule)} m²) divergent de {divergence.pct} % : la jauge était {divergence.estime > divergence.calcule ? 'optimiste' : 'prudente'} — fiez-vous au calcul.</p>
                  )}
                </Recit>
              )}
              <Recit titre="Ce que le terrain accueille" ton={verdictTon(active.verdict)}>
                <p className="text-[12px] text-txt-hi">{fmtInt(active.resume.logements)} logements · {fmtInt(active.resume.places)} places · {active.niveaux_label}</p>
                <p className="text-[10.5px] text-txt-dim">{Object.entries(active.programme.par_type).map(([t, n]) => `${n}×${t}`).join(' · ')} · SDP {fmtDec(active.resume.sdp_m2)} m²</p>
                {/* ETUDE-V6-2 (Lot 3) — parking enterré : places au −1, emprise du sous-sol, rampe au sol. */}
                {active.stationnement?.mode === 'sous_sol' && (
                  <p className="mt-1 text-[10.5px] text-txt"><b className="text-mint">Stationnement en sous-sol</b> : {fmtInt(active.stationnement.places_sous_sol ?? 0)} places au niveau −1 · emprise {fmtDec(active.stationnement.emprise_sous_sol_m2 ?? 0)} m² (≤ emprise réglementaire)
                    {active.stationnement.rampe_detail && <> · rampe {fmtDec(active.stationnement.rampe_m2 ?? 0)} m² ({fmtDec(active.stationnement.rampe_detail.rampe_profondeur_m)} m / {fmtDec(active.stationnement.rampe_detail.rampe_pente_pct)} % = {fmtDec(active.stationnement.rampe_detail.rampe_longueur_m)} m × {fmtDec(active.stationnement.rampe_detail.rampe_largeur_m)} m)</>}
                    {(active.stationnement.sur_dalle_m2 ?? 0) > 0 && <> · {fmtDec(active.stationnement.sur_dalle_m2 ?? 0)} m² sur dalle retirés de la pleine terre</>}.</p>
                )}
                <div className="mt-1.5"><Badge ton={verdictTon(active.verdict)}>{active.verdict}</Badge></div>
              </Recit>
              {active.ecart && (
                <Recit titre="L'écart" ton={active.ecart.reserve_logements >= 0 ? 'vert' : 'ambre'}>
                  {active.ecart.reserve_logements >= 0 ? (
                    <p className="text-[11.5px] text-txt">Vos {active.ecart.demande_total} logements tiennent. Réserve de <b>{active.ecart.reserve_logements}</b> logement(s) sur cette variante dessinée.</p>
                  ) : (
                    <p className="text-[11.5px] text-txt">{active.ecart.variante_total} des {active.ecart.demande_total} demandés tiennent sur cette variante.</p>
                  )}
                  <p className="mt-0.5 text-[9.5px] text-txt-dim">Chiffré depuis une variante dessinée (prouvé), non une règle de trois.</p>
                </Recit>
              )}
              {/* ETUDE-V6-2 (Lot 2) — ce qui limite, CLASSÉ par impact (logements perdus), le stationnement
                  PROUVÉ par contrefactuel « sans places ». Repli sur l'ancienne ligne si le champ manque. */}
              <Recit titre="Ce qui limite">
                {resultat.facteurs_limitants && resultat.facteurs_limitants.length > 0 ? (
                  <ol className="flex flex-col gap-1.5">
                    {resultat.facteurs_limitants.map((f, i) => (
                      <li key={f.facteur} className="text-[11px]">
                        <span className="text-txt">{i + 1}. {f.facteur}</span>
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
                  <p className="text-[11.5px] text-txt">{active.limite_capacite ?? 'Aucun facteur limitant dominant identifié.'}</p>
                )}
                {active.controles.filter((c) => c.resultat === 'Échoué' || c.resultat === 'À confirmer').slice(0, 4).map((c) => (
                  <p key={c.nom} className="mt-0.5 text-[10px] text-txt-dim">• {c.nom} — <span className={c.resultat === 'Échoué' ? 'text-coral' : 'text-amber'}>{c.resultat}</span></p>
                ))}
                {/* ETUDE-V6-2 (Lot 3) — « Testez en sous-sol » quand le stationnement AÉRIEN plafonne : enterrer
                    les places libère le sol. Calculé SEULEMENT au clic (l'étude aérienne reste rapide). */}
                {(active.stationnement?.mode ?? 'aerien') === 'aerien'
                  && resultat.facteurs_limitants?.some((f) => f.facteur.startsWith('stationnement') && f.limitant) && (
                  <button type="button" data-tester-sous-sol onClick={testerSousSol} disabled={analyse.isPending}
                    className="mt-2 rounded border border-mint bg-mint/10 px-2.5 py-1 text-[11px] font-semibold text-mint hover:bg-mint/20 disabled:opacity-50">
                    {analyse.isPending ? 'Calcul en cours…' : 'Testez en sous-sol →'}
                  </button>
                )}
              </Recit>
              {alternative && alternative.role !== active.role && (
                <Recit titre="Une alternative concrète">
                  {alternative.absente ? (
                    <p className="text-[11.5px] text-txt-mut">{alternative.raison}</p>
                  ) : (
                    <>
                      <p className="text-[11.5px] text-txt">{alternative.forme} {alternative.niveaux_label} — {fmtInt(alternative.resume.logements)} logements.</p>
                      <button type="button" onClick={() => setVariantActive('alternative')} className="mt-1 text-[11px] text-mint hover:underline">Voir l'alternative →</button>
                    </>
                  )}
                </Recit>
              )}
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
              {editeurHyp(true)}
              <div className="flex flex-wrap gap-2">
                <BoutonPdf />
                {onBilan && <Bouton niveau="secondaire" onClick={() => onBilan(bilanDe(active))}>Bilan de ce scénario →</Bouton>}
              </div>
              {resultat.bilan_surfacique?.clos && (
                <p className="text-[9.5px] text-txt-dim">Bilan surfacique clos (contenance = zone constructible {fmtDec(resultat.bilan_surfacique.zone_constructible_m2 ?? 0)} m² + hors-zone {fmtDec(resultat.bilan_surfacique.hors_zone_m2 ?? 0)} m²) · plan sans chevauchement · study_id {resultat.study_id}.</p>
              )}
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
    <div className="flex min-h-full flex-col">
      <Entete onClose={onClose} onReset={reset} resetLabel="↻ Recommencer" />
      <div className="px-4 pt-4">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-mint">Outil de pré-faisabilité</p>
        <h1 className="mt-1 font-display text-[clamp(22px,3vw,34px)] font-bold leading-tight text-txt-hi">Votre projet. Les possibilités du terrain.</h1>
        <p className="mt-1 max-w-[640px] text-[12.5px] text-txt-mut">Trois étapes pour définir votre opération. LABUSE confronte ensuite votre programme aux capacités et contraintes à étudier.</p>
      </div>

      <div className="grid grid-cols-1 gap-2 px-4 pt-4 sm:grid-cols-3">
        {ETAPES.map((e) => {
          const on = e.n === step
          const fait = e.n < step
          return (
            <button key={e.n} type="button" onClick={() => { if (e.n < step) setStep(e.n as 1 | 2 | 3) }}
              className={`flex items-center gap-2.5 rounded-lg border px-3 py-2.5 text-left transition-colors duration-quick ${
                on ? 'border-mint bg-mint-bg' : fait ? 'border-line-2 hover:border-mint/50' : 'border-line-2 opacity-70'} ${e.n < step ? 'cursor-pointer' : 'cursor-default'}`}>
              <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded text-[12px] font-bold ${on || fait ? 'bg-mint text-mint-on' : 'bg-surface-3 text-txt-dim'}`}>{e.n}</span>
              <span><b className="block text-[12.5px] text-txt-hi">{e.titre}</b><small className="text-[10.5px] text-txt-dim">{e.sous}</small></span>
            </button>
          )
        })}
      </div>

      <div className="grid flex-1 gap-4 p-4 lg:grid-cols-[1fr_340px]">
        <div className="rounded-lg border border-line-2 bg-surface-2 p-4">
          {step === 1 && <EtapeParcelles sel={sel} v={v} chargement={valide.isFetching} erreur={valide.error} onAjouter={ajouter} onRetirer={retirer} />}
          {step === 2 && <EtapeType projet={projet} onChoisir={setProjet} regimes={statio.data?.regimes} chargement={statio.isFetching} />}
          {step === 3 && <EtapeProgramme nb={nb} setNb={setNb} totalLogts={totalLogts} surfaceProg={surfaceProg} surfaceVar={surfaceVar} surfaceInt={surfaceInt} lotissement={projet === 'lotissement'}
            jauge={jauge} jaugeChargement={jaugeQ.isFetching} jaugeManquant={jaugeQ.data && !jaugeQ.data.estimable ? jaugeQ.data.manquant : null} />}
        </div>
        <Recap sel={sel} v={v} projet={projet} totalLogts={totalLogts} surfaceProg={surfaceProg} surfaceVar={surfaceVar}
          stationnement={projet && statio.data?.regimes?.general ? (statio.data.regimes.general.etat ?? 'règle PLU') : null} />
      </div>

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
  )
}

// ── En-tête (Fermer / Recommencer) ───────────────────────────────────────────────────────────────
function Entete({ onClose, onReset, resetLabel }: { onClose?: () => void; onReset: () => void; resetLabel: string }) {
  return (
    <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
      <div className="flex items-center gap-3">
        {onClose && <Bouton niveau="secondaire" onClick={onClose}>← Fermer</Bouton>}
        <div><b className="block text-[14px] text-txt-hi">Étude de faisabilité</b><small className="text-[10.5px] text-txt-dim">Pré-faisabilité foncière · La Réunion</small></div>
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
function GrandeurCard({ l, g }: { l: string; g: EtudeGrandeur }) {
  const val = g.valeur_m2 == null ? '—' : `${fmtDec(g.valeur_m2)} m²`
  const ton = g.statut === 'mesuré' ? 'vert' : g.statut === 'dérivé' ? 'neutre' : 'ambre'
  return (
    <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5" title={g.detail}>
      <div className="font-display text-[20px] font-bold leading-none text-txt-hi">{val}</div>
      <div className="mt-1 text-[10.5px] text-txt-dim">{l}</div>
      <div className="mt-1"><Badge ton={ton}>{g.statut}</Badge></div>
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
function Controles({ v }: { v: EtudeVariante }) {
  const c = v.controles_compte
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
        {v.controles.map((ct) => (
          <div key={ct.nom} className="flex items-start justify-between gap-2 border-t border-line-2 py-1">
            <div className="min-w-0">
              <span className="text-[11px] text-txt">{ct.nom}</span>
              <span className="ml-1.5 text-[10px] text-txt-dim">{ct.regle} · {ct.mesure}</span>
              {ct.citation && <span className="ml-1.5 text-[9.5px] text-txt-dim">— {ct.citation}</span>}
            </div>
            <Badge ton={etatTon(ct.resultat)}>{ct.resultat}</Badge>
          </div>
        ))}
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
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Chiffre v={fmtInt(tl.nombre)} l="lots" />
          <Chiffre v={`${fmtDec(tl.surface_moyenne_m2 ?? 0)} m²`} l="surface moyenne" />
          <Chiffre v={`${fmtDec(tl.surface_min_m2 ?? 0)} m²`} l="surface mini" />
          <Chiffre v={`${fmtDec(lot.voirie_m2)} m²`} l="voirie" />
        </div>
        {lot.geojson && (
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
        <LigneInfo l="Stationnement" v={`${lot.stationnement.total_lots} places (${lot.stationnement.par_lot}/lot · ${lot.stationnement.article})`} sous={`+ ${lot.stationnement.visiteurs_estimes} visiteurs (estimé)`} />
        <Recit titre="EBC" ton={lot.ebc.m2 > 0 ? 'ambre' : undefined}>
          <p className="text-[11px] text-txt">{lot.ebc.m2 > 0 ? `${fmtDec(lot.ebc.m2)} m² d'EBC` : lot.ebc.statut}</p>
        </Recit>
        <Recit titre="Surface minimale de lot (PLU)">
          <p className="text-[11px] text-txt">{lot.min_lot_plu.existe ? 'règle présente' : 'aucune règle au PLU Ud'}</p>
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
        {studyId && <p className="text-[9px] text-txt-dim">study_id {studyId} — le PDF part de la même étude.</p>}
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
type HypEtat = { surf: Record<TypeKey, string>; varangue: Record<TypeKey, string>; profondeur: string; coef: string; stationnement: 'aerien' | 'sous_sol' }
function HypothesesEditor({ hyp, setHyp, surfOf, varOf, types, collectif, onRecalculer, enCours, mode, onMode }: {
  hyp: HypEtat; setHyp: (f: (h: HypEtat) => HypEtat) => void
  surfOf: (t: TypeKey) => number; varOf: (t: TypeKey) => number
  types: readonly TypeKey[]; collectif: boolean; onRecalculer: () => void; enCours: boolean
  mode: 'aerien' | 'sous_sol'; onMode: (m: 'aerien' | 'sous_sol') => void
}) {
  const champ = (val: string, ph: string, on: (v: string) => void) => (
    <input type="number" min={0} inputMode="decimal" value={val} placeholder={ph} onChange={(e) => on(e.target.value)}
      className="w-16 rounded border border-line-2 bg-surface-2 px-1.5 py-0.5 text-center text-[11px] text-txt-hi" />
  )
  return (
    <details data-hypotheses className="rounded-lg border border-line-2 bg-surface-2 p-3" open>
      <summary className="cursor-pointer text-[11px] font-semibold text-txt">Hypothèses modifiables <small className="font-normal text-txt-dim">(Estimé — recalcule l'étude)</small></summary>
      <div className="mt-2 flex flex-col gap-1.5">
        <div className="grid grid-cols-[2rem_1fr_1fr] items-center gap-2 text-[9px] uppercase tracking-wide text-txt-dim">
          <span>Type</span><span>Surface m²</span><span>dont varangue m²</span>
        </div>
        {types.map((t) => (
          <div key={t} className="grid grid-cols-[2rem_1fr_1fr] items-center gap-2">
            <span className="font-mono text-[12px] text-txt-hi">{t}</span>
            {champ(hyp.surf[t], `${surfOf(t)}`, (val) => setHyp((h) => ({ ...h, surf: { ...h.surf, [t]: val } })))}
            {champ(hyp.varangue[t], `${varOf(t)}`, (val) => setHyp((h) => ({ ...h, varangue: { ...h.varangue, [t]: val } })))}
          </div>
        ))}
        {collectif && (
          <div className="mt-1 flex flex-wrap items-center gap-3 border-t border-line-2 pt-2 text-[10.5px] text-txt-mut">
            <label className="flex items-center gap-1.5">Profondeur bâtiment {champ(hyp.profondeur, '13', (v) => setHyp((h) => ({ ...h, profondeur: v })))} m</label>
            <label className="flex items-center gap-1.5">Coef. plancher→habitable {champ(hyp.coef, '0.8', (v) => setHyp((h) => ({ ...h, coef: v })))}</label>
          </div>
        )}
        {/* ETUDE-V6-2 (Lot 3) — mode de stationnement : aérien (défaut) / sous-sol (places au −1, rampe au sol). */}
        {collectif && (
          <div className="mt-1 flex flex-wrap items-center gap-2 border-t border-line-2 pt-2 text-[10.5px] text-txt-mut">
            <span>Stationnement</span>
            <div className="inline-flex overflow-hidden rounded border border-line-2" role="group" aria-label="Mode de stationnement">
              {(['aerien', 'sous_sol'] as const).map((m) => (
                <button key={m} type="button" data-statio-mode={m} onClick={() => onMode(m)}
                  className={`px-2 py-0.5 text-[10.5px] ${mode === m ? 'bg-mint font-semibold text-mint-on' : 'text-txt-mut hover:bg-surface-1'}`}>
                  {m === 'aerien' ? 'Aérien' : 'Sous-sol'}
                </button>
              ))}
            </div>
            {mode === 'sous_sol' && <span className="text-[9.5px] text-txt-dim">Places au niveau −1, rampe au sol — l'emprise enterrée reste ≤ l'emprise réglementaire.</span>}
          </div>
        )}
        <div className="mt-1 flex items-center gap-2">
          <Bouton niveau="primaire" onClick={onRecalculer} disabled={enCours}>{enCours ? 'Recalcul…' : 'Recalculer ↻'}</Bouton>
          <span className="text-[9.5px] text-txt-dim">Le recalcul met à jour le résultat ET le PDF (même study_id).</span>
        </div>
      </div>
    </details>
  )
}

// ── Lot C — stationnement dans le résultat : règle générale (appliquée) + plafond L151-35 (à confirmer)
//    + la capacité SOUS le régime réduit, jamais présentée comme acquise ───────────────────────────
function StationnementResultat({ regimes, reduite, placesActive, logtsActive }: {
  regimes: EtudeStationnementRegimes
  reduite: EtudePayload['capacite_reduite']
  placesActive: number; logtsActive: number
}) {
  const g = regimes.general, pf = regimes.plafond_national
  return (
    <div data-stationnement-resultat className="rounded-lg border border-line-2 bg-surface-2 p-3">
      <b className="text-[11px] font-semibold text-txt">Stationnement</b>
      <div className="mt-2 flex items-start justify-between gap-2 border-t border-line-2 py-1.5">
        <div><span className="text-[11px] text-txt">Règle générale du PLU</span>
          <span className="ml-1.5 text-[10px] text-txt-dim">{g.ratio_par_logement != null ? `${fmtDec(g.ratio_par_logement)} pl./logt` : 'par typologie'}{g.millesime ? ` · ${g.millesime}` : ''} · {placesActive} places dessinées</span></div>
        <Badge ton="vert">appliquée</Badge>
      </div>
      {pf && (
        <div className="flex items-start justify-between gap-2 border-t border-line-2 py-1.5">
          <div><span className="text-[11px] text-txt">Plafond {pf.reference} ({pf.categorie})</span>
            <span className="ml-1.5 text-[10px] text-txt-dim">≤ {fmtDec(pf.ratio_plafond)} pl./logt · TCSP {pf.condition_tcsp_sous_800m ? `${fmtInt(pf.distance_tcsp_m ?? 0)} m ✓` : 'hors 800 m'} · catégorie à confirmer</span></div>
          <Badge ton="ambre">{pf.statut}</Badge>
        </div>
      )}
      {reduite && reduite.statut === 'À confirmer' && reduite.logements != null && (
        <div className="mt-1.5 rounded-md border border-amber/40 bg-amber-bg px-2.5 py-1.5">
          <p className="text-[10.5px] text-txt"><b className="text-amber">Sous le régime réduit (à confirmer)</b> : {reduite.logements} logements tiendraient (vs {logtsActive} à la règle générale) — le stationnement cesserait d'être le facteur limitant.</p>
          <p className="mt-0.5 text-[9.5px] text-txt-dim">{reduite.note}</p>
        </div>
      )}
      {reduite && reduite.statut === 'sans effet' && (
        <p className="mt-1.5 text-[9.5px] text-txt-dim">{reduite.note}</p>
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
      <p className="mt-1.5 text-[10.5px] text-txt-dim">Aucune carte dans le formulaire : la sélection se fait par recherche.</p>

      <div className="mt-3 flex items-center justify-between">
        <b className="text-[12px] text-txt">Parcelles sélectionnées</b>
        <span className="text-[11px] text-txt-dim">{sel.length}/8</span>
      </div>
      {sel.length === 0 && <p className="mt-1.5 text-[11.5px] text-txt-dim">Ajoutez une référence pour commencer.</p>}

      {sel.length > 0 && chargement && !v && <div className="mt-2"><Chargement /></div>}
      {!!erreur && <p className="mt-2 text-[11.5px] text-coral">{(erreur as Error).message}</p>}

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
              {/* ETUDE-V6-2 (Lot 5) — règles PLU SERVIES de la zone de cette parcelle, citées (article · page). */}
              {p.regles_plu && p.regles_plu.length > 0 && (
                <div data-regles-plu className="mt-1.5 flex flex-wrap gap-1.5">
                  {p.regles_plu.map((r) => (
                    <span key={r.nom} title={r.article ? `PLU art. ${r.article}${r.page_pdf != null ? ` · p. ${r.page_pdf}` : ''}` : undefined}
                      className="rounded border border-line-2 bg-surface-2 px-1.5 py-0.5 text-[10px] text-txt-mut">
                      {r.nom} <b className="text-txt">{fmtDec(r.valeur)}{r.unite === '%' ? ' %' : ` ${r.unite}`}</b>
                      {r.article && <span className="ml-1 text-[8.5px] text-txt-dim">{r.article}</span>}
                    </span>
                  ))}
                </div>
              )}
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
          <Sources v={v} />
        </div>
      )}
    </div>
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

function Sources({ v }: { v: EtudeParcellesOut }) {
  const c = v.sources.cadastre, p = v.sources.plu
  if (!c && !p) return null
  return (
    <p className="text-[9.5px] leading-snug text-txt-dim">
      {c && <>Géométrie &amp; contenance : {c.source}{c.derniere_synchro ? ` · maj ${c.derniere_synchro}` : ''}. </>}
      {p && <>Zone PLU : {p.source}.</>}
    </p>
  )
}

// ── Étape 2 — Type de projet ─────────────────────────────────────────────────────────────────────
function EtapeType({ projet, onChoisir, regimes, chargement }: {
  projet: ProjetKey | null; onChoisir: (k: ProjetKey) => void
  regimes?: EtudeStationnementRegimes; chargement: boolean
}) {
  return (
    <div>
      <EnTetePanneau n="02" titre="Quel type de projet ?" sous="Sélectionnez la destination de votre opération." />
      <div className="grid gap-2.5 sm:grid-cols-2">
        {PROJETS.map((pr) => {
          const on = pr.key === projet
          return (
            <button key={pr.key} type="button" data-etude-type={pr.key} onClick={() => onChoisir(pr.key)}
              className={`rounded-lg border px-3.5 py-3 text-left transition-colors duration-quick ${on ? 'border-mint bg-mint-bg' : 'border-line-2 hover:border-mint/50'}`}>
              <b className="block text-[13px] text-txt-hi">{pr.label}</b>
              <small className="text-[11px] text-txt-dim">{pr.desc}</small>
            </button>
          )
        })}
      </div>
      {projet && chargement && <div className="mt-3"><Chargement /></div>}
      {projet && regimes && <StationnementRegle regimes={regimes} lotissement={projet === 'lotissement'} />}
    </div>
  )
}

// ── Lot C — la règle de stationnement applicable (règle générale PLU + plafond L151-35 à confirmer) ──
function StationnementRegle({ regimes, lotissement }: { regimes: EtudeStationnementRegimes; lotissement?: boolean }) {
  const g = regimes.general, pf = regimes.plafond_national
  return (
    <div data-stationnement className="mt-3 flex flex-col gap-2">
      <div className="rounded-md border border-line-2 bg-surface-1 px-3 py-2">
        <div className="flex flex-wrap items-center gap-2">
          <b className="text-[11.5px] text-txt">Règle générale du PLU</b>
          <Badge ton={g.validee ? 'vert' : 'ambre'}>{g.etat}</Badge>
        </div>
        <p className="mt-1 text-[11px] text-txt">
          {g.ratio_par_logement != null ? `${fmtDec(g.ratio_par_logement)} place / logement` : 'barème par typologie'}
          {g.article && <span className="text-txt-dim"> · art. {g.article}</span>}
          {g.millesime && <span className="text-txt-dim"> · millésime {g.millesime}</span>}
        </p>
        {g.citation && <p className="mt-0.5 text-[9.5px] text-txt-dim">« {g.citation} »</p>}
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
        <p className="text-[10.5px] text-txt-mut">Lotissement : division foncière — les obligations de stationnement portent sur les futures constructions des lots (Lot D).</p>
      )}
    </div>
  )
}

// ── Étape 3 — Programme ──────────────────────────────────────────────────────────────────────────
function EtapeProgramme({ nb, setNb, totalLogts, surfaceProg, surfaceVar, surfaceInt, lotissement, jauge, jaugeChargement, jaugeManquant }: {
  nb: Record<TypeKey, number>; setNb: (f: (n: Record<TypeKey, number>) => Record<TypeKey, number>) => void
  totalLogts: number; surfaceProg: number; surfaceVar: number; surfaceInt: number; lotissement: boolean
  jauge: ReturnType<typeof enveloppeJauge>; jaugeChargement: boolean; jaugeManquant: string[] | null
}) {
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
      {/* ETUDE-V6-2 (Lot 4) — JAUGE : enveloppe estimée (avant calcul) vs programme saisi. Rouge si
          dépassement ; grise « non estimable » si une donnée manque. Étiquetée « estimé » (jamais un chiffre servi). */}
      {!lotissement && totalLogts > 0 && (
        <JaugeEnveloppe jauge={jauge} chargement={jaugeChargement} manquant={jaugeManquant} programme={surfaceProg} />
      )}
      <p className="mt-2 text-[10px] text-txt-dim">Ces surfaces sont des hypothèses de programme (varangue comprise). La surface de plancher réglementaire (SDP) sera calculée séparément par le moteur — jamais confondue avec ces m².</p>
    </div>
  )
}

// ── Lot 4 — jauge d'enveloppe estimée (étape 3, avant le calcul) ───────────────────────────────────
function JaugeEnveloppe({ jauge, chargement, manquant, programme }: {
  jauge: ReturnType<typeof enveloppeJauge>; chargement: boolean; manquant: string[] | null; programme: number
}) {
  if (manquant && manquant.length > 0) {
    return (
      <div data-jauge="non-estimable" className="mt-3 rounded-md border border-line-2 bg-surface-1 px-3 py-2.5">
        <div className="mb-1.5 flex items-center justify-between">
          <b className="text-[11.5px] text-txt">Enveloppe constructible <span className="text-[9px] font-normal uppercase tracking-wide text-txt-dim">· estimé</span></b>
          <span className="text-[10.5px] text-txt-mut">non estimable</span>
        </div>
        <div className="h-2 w-full rounded-full bg-line-2" />
        <p className="mt-1 text-[10px] text-txt-dim">Donnée manquante : {manquant.join(' · ')}. L'enveloppe ne peut pas être estimée avant le calcul.</p>
      </div>
    )
  }
  if (!jauge) {
    return (
      <div data-jauge="chargement" className="mt-3 rounded-md border border-line-2 bg-surface-1 px-3 py-2.5">
        <b className="text-[11.5px] text-txt">Enveloppe constructible <span className="text-[9px] font-normal uppercase tracking-wide text-txt-dim">· estimé</span></b>
        <div className="mt-1.5 h-2 w-full animate-pulse rounded-full bg-line-2" />
        <p className="mt-1 text-[10px] text-txt-dim">{chargement ? 'Estimation en cours…' : 'Enveloppe estimée dès que l\'assiette est prête.'}</p>
      </div>
    )
  }
  const depasse = programme > jauge.enveloppe
  const pct = jauge.enveloppe > 0 ? Math.min(100, Math.round((programme / jauge.enveloppe) * 100)) : 0
  return (
    <div data-jauge={depasse ? 'depassement' : 'ok'} className={`mt-3 rounded-md border px-3 py-2.5 ${depasse ? 'border-coral/50 bg-coral/5' : 'border-line-2 bg-surface-1'}`}>
      <div className="mb-1.5 flex items-center justify-between">
        <b className="text-[11.5px] text-txt">Enveloppe constructible <span className="text-[9px] font-normal uppercase tracking-wide text-txt-dim">· estimé</span></b>
        <span className="text-[10.5px] text-txt-mut">{fmtDec(programme)} / {fmtDec(jauge.enveloppe)} m² ({pct} %)</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-line-2">
        <div className={`h-full rounded-full ${depasse ? 'bg-coral' : 'bg-mint'}`} style={{ width: `${pct}%` }} />
      </div>
      {depasse ? (
        <p className="mt-1.5 text-[10.5px] text-coral">⚠ Votre programme ({fmtDec(programme)} m²) dépasse l'enveloppe estimée ({fmtDec(jauge.enveloppe)} m²) de {fmtDec(programme - jauge.enveloppe)} m². Le terrain ne tiendra probablement pas tout — réduisez ou testez le sous-sol.</p>
      ) : (
        <p className="mt-1 text-[10px] text-txt-dim">Estimé : (zone {fmtDec(jauge.zone_m2)} m² − stationnement {fmtDec(jauge.solStat)} m²) × {jauge.niveaux_label} × coef {jauge.coef} = {fmtDec(jauge.enveloppe)} m². Le calcul complet affine ce chiffre.</p>
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
  return (
    <div className="mx-4 mb-4 mt-2 flex items-center justify-between gap-3 border-t border-line-2 pt-3">
      <div className="min-h-[1em] text-[10.5px]">
        {raison && <span className="text-amber">{raison}</span>}
        {enAnalyse && <span className="text-txt-dim">Calcul en cours, jusqu'à une minute…</span>}
        {!!erreurAnalyse && <span className="text-coral">{(erreurAnalyse as Error).message}</span>}
      </div>
      <div className="flex items-center gap-2">
        {step > 1 && <Bouton niveau="secondaire" onClick={onPrec}>← Retour</Bouton>}
        {step < 3 && <Bouton niveau="primaire" onClick={onSuiv} disabled={suivBloque}>Continuer →</Bouton>}
        {step === 3 && <Bouton niveau="primaire" onClick={onAnalyser} disabled={!peutAnalyser || enAnalyse}>{enAnalyse ? 'Calcul en cours…' : 'Analyser mon projet →'}</Bouton>}
      </div>
    </div>
  )
}

export default EtudeV6
