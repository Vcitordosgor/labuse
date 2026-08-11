/**
 * M45 (P2a) — Filtres LABUSE : les DEUX VOIES.
 *  · Barre NIVEAU 1 (toujours visible) : constructibilité calibrée · surface · SDP résiduelle ·
 *    état du sol · capacité logements (Estimé) · interrupteur « Analyse LABUSE ».
 *  · Interrupteur : ACTIF par défaut (le classement pilote). Le coupé = voie manuelle pure ;
 *    la bascule affiche le CONTRASTE (trame entière → têtes du classement).
 *  · Tiroir NIVEAU 2 témoin « Puis-je construire ? » (droit du sol).
 * Le compteur est SQL-exact (endpoint unifié /filtre) — jamais un calcul client. Chaque facette
 * porte son étiquette (Sourcé/Estimé) et sa limite. Aucune facette du cadrage ANTI-FILTRES ici.
 */
import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import { getFiltre, getFiltreCount } from '../../lib/api'
import { countActiveFilters, resumeCriteres } from '../../lib/filters'
import { CLIENT } from '../../lib/strings'
import { EMPTY_FILTERS, useApp, type Filters } from '../../store/useApp'
import { Tip } from '../Tip'

// M55-G suite point 3 : CONSTRUCTIBILITE et les chips de verdict/motif ont quitté l'état
// post-analyse (0-caller) — les champs de filtre restent dans le store + l'URL.
const ETAT_SOL = [
  { k: 'nu', l: 'Nu' },
  { k: 'bati_marginal', l: 'Bâti marginal' },
  { k: 'bati_sature', l: 'Bâti saturé' },
  { k: 'bati_revele', l: 'Bâti révélé' },
]
// M55-J point 1 : égalité de filtres pour le FILET d'invalidation — toute différence (y compris
// un simple réordonnancement) invalide la carte, ce qui est le comportement conservateur voulu
// (un vide honnête vaut mieux qu'un chiffre périmé).
const filtersEqual = (a: Filters, b: Filters): boolean => JSON.stringify(a) === JSON.stringify(b)

// M55-J point 2 : LE bouton d'action du panneau (un seul endroit pour la famille) — deux
// variantes hiérarchisées : `primary` (rempli mint, l'action dominante) et `secondary`
// (contour, l'action de retrait). Relancer/Désactiver s'y branchent, ils ne se distinguent
// plus par « bouton vs texte souligné » mais par le TRAITEMENT de la même famille.
function ActionBtn({ variant, onClick, children, dataAttr }:
  { variant: 'primary' | 'secondary'; onClick: () => void; children: React.ReactNode; dataAttr?: string }) {
  const extra = dataAttr ? { [dataAttr]: true } : {}
  const style = variant === 'primary'
    ? 'bg-mint font-semibold text-mint-ink hover:brightness-110'
    : 'border border-line-2 bg-surface-3/60 text-txt hover:border-txt-dim/50 hover:bg-surface-3 hover:text-txt-hi'
  return (
    <button {...extra} onClick={onClick}
      className={`flex-1 rounded-lg py-2 text-[12px] font-medium transition-colors duration-quick ${style}`}>
      {children}
    </button>
  )
}

const ZONE_FAM = [{ k: 'U', l: 'U' }, { k: 'AU', l: 'AU' }, { k: 'A', l: 'A' }, { k: 'N', l: 'N' }]
// M55-G point 7 : PROPRIO_TYPE / ETAT_SOCIETE / COPRO retirés avec les tiroirs pédagogiques
// (0-caller) — les champs de filtre restent dans le store + l'URL.
// M55-D stage 6 — les 24 communes par CODE POSTAL (CP dominant mesuré dans la BAN, table
// adresses). La chip affiche le CP, le « i » (title) nomme la commune. Rang 1 du panneau.
// M55-H point 7 : EXPORTÉE — le menu périmètre du header affiche le même CP (source unique).
export const CP_COMMUNES: [string, string][] = [
  ['97400', 'Saint-Denis'], ['97410', 'Saint-Pierre'], ['97412', 'Bras-Panon'],
  ['97413', 'Cilaos'], ['97414', 'Entre-Deux'], ['97419', 'La Possession'],
  ['97420', 'Le Port'], ['97424', 'Saint-Leu'], ['97425', 'Les Avirons'],
  ['97426', 'Les Trois-Bassins'], ['97427', "L'Étang-Salé"], ['97429', 'Petite-Île'],
  ['97430', 'Le Tampon'], ['97431', 'La Plaine-des-Palmistes'], ['97433', 'Salazie'],
  ['97438', 'Sainte-Marie'], ['97439', 'Sainte-Rose'], ['97440', 'Saint-André'],
  ['97441', 'Sainte-Suzanne'], ['97442', 'Saint-Philippe'], ['97450', 'Saint-Louis'],
  ['97460', 'Saint-Paul'], ['97470', 'Saint-Benoît'], ['97480', 'Saint-Joseph'],
]
// M55-G suite point 4 (décision Vic) — UN SEUL niveau, 7 signaux (les deux niveaux du
// point 11 n'auront vécu qu'une journée) : « Nu détenu par société » et « Cession de fonds »
// SUPPRIMÉS de l'UI (clés URL ignorées proprement dans filters.ts, backend intact).
// Libellés/« i » : CLIENT.signaux. OU de groupe et persistance URL (sv=) inchangés.
const SIGNAUX_KEYS = ['pm_privee', 'procedure', 'permis_actif', 'permis_caduc',
  'friche', 'assemblage', 'defisc']


const nf = new Intl.NumberFormat('fr-FR')

// M55-D stage 4 : différenciation SÉLECTIONNÉ / disponible plus lisible que le tout-gris —
// disponible = fond léger + survol menthe (ça s'active) ; sélectionné = rempli menthe, texte franc.
function Chip({ on, onClick, children }: { on: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick}
      className={`rounded-full border px-2.5 py-0.5 text-[11px] transition-colors duration-quick ${
        on ? 'border-mint bg-mint/20 font-medium text-txt-hi'
          : 'border-line-2 bg-surface-3 text-txt-mut hover:border-mint/50 hover:text-txt'}`}>
      {children}
    </button>
  )
}

function ChipGroup({ field, options }: { field: keyof Filters; options: { k: string; l: string }[] }) {
  const { filters, setFilter } = useApp()
  const sel = (filters[field] as string[]) ?? []
  const toggle = (k: string) =>
    setFilter(field, (sel.includes(k) ? sel.filter((x) => x !== k) : [...sel, k]) as never)
  return (
    <div className="mt-1 flex flex-wrap gap-1.5">
      {options.map((o) => <Chip key={o.k} on={sel.includes(o.k)} onClick={() => toggle(o.k)}>{o.l}</Chip>)}
    </div>
  )
}

// M55-G point 11 : chip + « i » d'un signal de vie — partagé entre larges et niches
function SignalChip({ k }: { k: string }) {
  const { filters, setFilter } = useApp()
  return (
    <span className="flex items-center gap-1">
      <Chip on={filters.signaux.includes(k)}
        onClick={() => setFilter('signaux', (filters.signaux.includes(k)
          ? filters.signaux.filter((x) => x !== k) : [...filters.signaux, k]) as never)}>
        {CLIENT.signaux.labels[k]}
      </Chip>
      <Tip side="top" tip={CLIENT.signaux.infos[k]}>
        <span role="button" tabIndex={0} aria-label={`En savoir plus : ${CLIENT.signaux.labels[k]}`}
          className="flex h-[13px] w-[13px] items-center justify-center rounded-full border border-line-2 text-[8px] font-bold leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
      </Tip>
    </span>
  )
}

// M55-G suite point 7 : les titres de sections n'ont PLUS de sous-texte — l'explication vit
// dans un « i » (même patron que les signaux), au survol.
function TitreSection({ titre, info, cls = '' }: { titre: string; info: string; cls?: string }) {
  return (
    <p className={`label-caps flex items-center gap-1.5 text-txt-mut ${cls}`}>{titre}
      <Tip side="top" tip={info}>
        <span role="button" tabIndex={0} aria-label={`En savoir plus : ${titre}`}
          className="flex h-[13px] w-[13px] items-center justify-center rounded-full border border-line-2 text-[8px] font-bold normal-case leading-none text-txt-dim hover:border-mint hover:text-mint">i</span>
      </Tip>
    </p>
  )
}

function NumField({ field, ph, suffix }: { field: keyof Filters; ph: string; suffix?: string }) {
  const { filters, setFilter } = useApp()
  const v = filters[field] as number | null
  return (
    <div className="flex items-center gap-1">
      <input type="number" inputMode="numeric" placeholder={ph}
        value={v ?? ''} onChange={(e) => setFilter(field, (e.target.value === '' ? null : Number(e.target.value)) as never)}
        className="w-[68px] rounded-md border border-line-2 bg-transparent px-2 py-1 text-[11px] text-txt-hi placeholder:text-txt-dim focus:border-mint focus:outline-none" />
      {suffix && <span className="text-[10px] text-txt-dim">{suffix}</span>}
    </div>
  )
}

// M55-G point 7 / suite point 3 : Tiroir, ModeBCurseur, BoolChip, Section retirés avec le
// contenu de l'état allumé (0-caller ici ; le curseur mode B de SESSION reste porté par le
// store — la fiche continue de le lire).

export function FiltreLabuse({ onRetract }: { onRetract?: () => void } = {}) {
  const { filters, setFilter, setFilters, setVerdict, commune, setCommunesFilter } = useApp()
  const analyseOn = filters.analyseLabuse
  // M55-D stage 4 : interrupteur UNIFIÉ — analyseLabuse (persisté, URL) ⟺ verdict (carte). Éteint
  // par défaut : plus jamais « analyse active » quand l'utilisateur n'a rien allumé (bug mesuré).
  const setAnalyse = (v: boolean) => { setFilter('analyseLabuse', v); setVerdict(v) }
  // Reset : les DEUX étages + éteint l'interrupteur (retour à l'état vierge). M55-J : coupe
  // aussi le rituel (phase/snapshot) — jamais une carte-phrase orpheline après un reset.
  const resetTout = () => { setFilters(EMPTY_FILTERS); setVerdict(false); setPhase('idle'); setSnapFilters(null) }
  // Compteurs : parc FACTUEL (analyse coupée) et RETENUES (analyse). La transition raconte l'effet.
  const on = useQuery({ queryKey: ['filtre', filters, true], queryFn: () => getFiltre({ ...filters, analyseLabuse: true }, 0) })
  // M55-F point 2 : la TRAME (analyse coupée) — total analysé du périmètre. écartées (étage 0) =
  // trame − retenues ; l'arithmétique de la phrase boucle (analysé = retenues + écartées).
  const trameQ = useQuery({ queryKey: ['filtre', filters, false], queryFn: () => getFiltre({ ...filters, analyseLabuse: false }, 0) })

  // ═══ M55-D stage 7 · COMPTEUR VIVANT — « N parcelles correspondent », mis à jour à chaque
  // changement de filtre : debounce 400 ms + AbortController (les appels obsolètes sont annulés).
  // TOUJOURS la réponse /filtre réelle (état courant de l'interrupteur), jamais une estimation.
  // Registre DISCRET — le rituel 3 s de la Révélation reste la cérémonie, intacte.
  const nActifs = countActiveFilters(filters)
  const [live, setLive] = useState<number | null>(null)
  const [liveLoading, setLiveLoading] = useState(false)
  useEffect(() => {
    const ctrl = new AbortController()
    setLiveLoading(true)
    const tmr = window.setTimeout(() => {
      getFiltreCount(filters, ctrl.signal)
        .then((r) => { setLive(r.compte); setLiveLoading(false) })
        .catch(() => { /* abort/réseau : on garde le dernier nombre, l'opacité signale le flottement */ })
    }, 400)
    return () => { window.clearTimeout(tmr); ctrl.abort() }
  }, [filters])

  // ═══ M55-D stage 5 · LA RÉVÉLATION — couche de PRÉSENTATION par-dessus l'état stage 4 (al/verdict
  // intouchés jusqu'au geste final). Décompte 3 s CONSTANT (rituel, décision Vic) ; pendant
  // l'animation la VRAIE requête /filtre part (refetch) — le résultat attend la fin pour se révéler.
  // Échec réseau pendant le décompte → interruption propre (jamais un faux succès). Le score est
  // PRÉ-CALCULÉ : le texte dit « application de vos critères », jamais « calcul du score ». ═══
  type Phase = 'idle' | 'counting' | 'revealed' | 'error'
  const [phase, setPhase] = useState<Phase>('idle')
  const phaseRef = useRef<Phase>('idle')
  phaseRef.current = phase
  const [countVal, setCountVal] = useState(0)
  // ═══ M55-J point 1 — INVARIANT : la carte d'analyse ne mélange JAMAIS deux runs. Tout ce
  // qu'elle affiche (effectif analysé, retenues, ventilation, récap des critères, périmètre)
  // provient du SNAPSHOT pris au lancement — pas des filtres live. Trois pièces figées à
  // `lancer()` : `fresh` (retenues + ventilation), `freshTrame` (effectif analysé = trame),
  // `snapFilters` (les critères du run, pour le récap/périmètre + le filet d'invalidation). ═══
  const [fresh, setFresh] = useState<Awaited<ReturnType<typeof getFiltre>> | null>(null)
  const [freshTrame, setFreshTrame] = useState<Awaited<ReturnType<typeof getFiltre>> | null>(null)
  const [snapFilters, setSnapFilters] = useState<Filters | null>(null)
  const timerRef = useRef<number | null>(null)
  const rafRef = useRef<number | null>(null)
  // M55-G suite point 5 : la requête v2-modele (date du run pour le bandeau) est partie avec
  // le bandeau — la date du classement vit dans la modale « comprendre le classement ».
  // prefers-reduced-motion : décompte remplacé par une transition simple (courte)
  const reduced = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  const RITUEL_MS = reduced ? 400 : 3000
  const lancer = () => {
    setPhase('counting'); setCountVal(0); setFresh(null); setFreshTrame(null)
    // M55-J point 1 : SNAPSHOT du run — on fige les critères et on tire LES DEUX effectifs
    // (retenues + trame analysée) sur CES critères-là. La carte ne lira plus jamais les filtres
    // live : elle décrit ce run, un point c'est tout.
    const snap = filters
    setSnapFilters(snap)
    // la VRAIE requête part MAINTENANT (appel direct, SANS retry : un échec interrompt le rituel
    // au lieu d'être masqué par les retries react-query au-delà des 3 s)
    getFiltre({ ...snap, analyseLabuse: true }, 0)
      .then((r) => setFresh(r))
      .catch(() => {
        if (phaseRef.current !== 'counting') return
        if (timerRef.current) window.clearTimeout(timerRef.current)
        if (rafRef.current) cancelAnimationFrame(rafRef.current)
        setPhase('error')
      })
    // la trame (effectif ANALYSÉ) du même run — le dénominateur de « retenues / analysées »
    getFiltre({ ...snap, analyseLabuse: false }, 0).then((r) => setFreshTrame(r)).catch(() => { /* filet plus bas */ })
    if (!reduced) {
      const t0 = performance.now()
      const cible = live ?? 431_663
      const tick = (now: number) => {
        const p = Math.min(1, (now - t0) / RITUEL_MS)
        setCountVal(Math.round(cible * p * p * p))   // easing cubique : les chiffres ACCÉLÈRENT
        if (p < 1) rafRef.current = requestAnimationFrame(tick)
      }
      rafRef.current = requestAnimationFrame(tick)
    }
    timerRef.current = window.setTimeout(() => setPhase((ph) => (ph === 'counting' ? 'revealed' : ph)), RITUEL_MS)
  }
  useEffect(() => {   // échec réseau pendant le décompte → état d'erreur honnête
    if (phase === 'counting' && on.isError) {
      if (timerRef.current) window.clearTimeout(timerRef.current)
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      setPhase('error')
    }
  }, [phase, on.isError])
  useEffect(() => () => {   // démontage : aucun timer orphelin
    if (timerRef.current) window.clearTimeout(timerRef.current)
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
  }, [])
  // geste final : l'analyse s'ALLUME (état stage 4, biunivoque) et la section se rétracte
  const voirParcelles = () => { setPhase('idle'); setAnalyse(true); onRetract?.() }
  // M55-F point 3 — le tri factuel : montrer la liste + la carte SANS l'opinion LABUSE. verdict
  // ON (les résultats s'affichent) mais analyseLabuse OFF (tri factuel, toutes les parcelles).
  // C'est le SEUL geste qui découple verdict de analyseLabuse (le bandeau des résultats le dit).
  const voirFactuel = () => { setPhase('idle'); setFilter('analyseLabuse', false); setVerdict(true); onRetract?.() }
  // M55-J point 1 : « analyse active » = le rituel est lancé (décompte/révélation) OU l'analyse
  // est allumée. Dans cet état les FILTRES SONT FIGÉS (fieldset désactivé plus bas) — un seul run
  // décrit, un seul effectif à l'écran.
  const analyseActive = analyseOn || phase === 'counting' || phase === 'revealed'
  // M55-J point 1 : la carte décrit le SNAPSHOT (snapFilters), pas les filtres live. Hors analyse
  // (état d'appel), il n'y a pas de carte-phrase → on retombe sur les filtres live sans effet.
  const cardFilters = snapFilters ?? filters
  const nCom = cardFilters.communes.length
  const perimetre = nCom === 1 ? cardFilters.communes[0] : nCom > 1 ? `${nCom} communes` : (commune ?? 'La Réunion')
  const recap = resumeCriteres(cardFilters, CLIENT.signaux.labels)
  // la phrase révèle les nombres du RITUEL (réponse fraîche du snapshot) ; hors rituel, le live
  const src = phase === 'revealed' && fresh ? fresh : on.data
  const phraseRetenues = src?.compte
  const t = src?.tiers
  const pl = (n: number, s: string) => `${nf.format(n)} ${s}${n > 1 ? 's' : ''}`
  // M55-J point 1 — l'arithmétique de la carte vient d'UN SEUL run (le snapshot) :
  //  · analysé (trame)     = freshTrame.compte  (snapshot, PAS trameQ live)
  //  · retenues            = fresh.compte  (snapshot ; = ventilation 4 tiers + potentiel épuisé)
  //  · potentiel épuisé    = retenues − (brûlante+chaude+réserve+à creuser)
  //  · écartées (étage 0)  = analysé − retenues                               (exclusions dures)
  // En phase revealed, on lit le snapshot (freshTrame) ; ailleurs (pas de phrase), le live.
  const analyseTotal = (phase === 'revealed' || phase === 'counting') ? freshTrame?.compte : trameQ.data?.compte
  const vent4 = t ? t.brulante + t.chaude + t.reserve_fonciere + t.a_creuser : 0
  const declassees = phraseRetenues != null ? phraseRetenues - vent4 : 0
  const ecartees = (analyseTotal != null && phraseRetenues != null) ? analyseTotal - phraseRetenues : null
  // M55-J point 1 · FILET DE SÉCURITÉ : si un chemin EXTERNE (sélecteur commune du header, URL,
  // retour arrière) déplace les filtres live pendant que le rituel décrit un run, la carte
  // s'INVALIDE (état neutre invitant à relancer) plutôt que d'afficher un chiffre périmé.
  const stale = phase === 'revealed' && snapFilters != null && !filtersEqual(filters, snapFilters)

  return (
    <div className="card-elev px-3 py-2">
      {/* ═══════ M55-J points 1 & 6 — LES FILTRES SONT FIGÉS PENDANT L'ANALYSE ═══════
          Arbitrage « faire DISPARAÎTRE » (et non « désactiver visiblement ») : pendant l'analyse,
          les contrôles de filtres sont retirés et remplacés par un RÉCAP COMPACT des critères du
          run (J1 l'autorise : « la liste des critères doit rester lisible dans la carte
          d'analyse »). Deux bénéfices : (1) impossible d'éditer un filtre → aucun run mixte ;
          (2) la section Filtres devient COMPACTE → le listing récupère la hauteur quand Couches
          se rétracte (J6). Pour changer de critères : Relancer / Désactiver l'analyse. */}
      {analyseActive ? (
        <div data-analyse-recap className="rounded-lg border border-mint/30 bg-mint/[0.05] px-3 py-2">
          <p className="label-caps text-[9px] text-txt-dim">Analyse en cours</p>
          <p className="mt-0.5 text-[11.5px] leading-snug text-txt">{recap ?? `toutes les parcelles de ${perimetre}`}</p>
          <p className="mt-1 text-[10px] leading-snug text-txt-dim">Filtres figés — Relancer ou Désactiver l’analyse pour les changer.</p>
        </div>
      ) : (
      <>
      {/* ═══════ 1 · COMMUNES — rang 1, MAÎTRE du périmètre (M55-D stage 6). Multi par code
          postal ; le sélecteur du header n'est plus qu'un REFLET de CE filtre. ═══════ */}
      <div data-communes-filtre>
        <TitreSection titre="1 · Communes"
          info="Le périmètre des résultats. Tout coché = toute l’île — rien coché aussi (aucune restriction)." />
        <div className="mt-1.5 flex flex-wrap gap-1">
          {CP_COMMUNES.map(([cp, nom]) => (
            <Tip key={cp} side="top" tip={`${cp} → ${nom}`}>
              <button onClick={() => setCommunesFilter(
                  filters.communes.includes(nom) ? filters.communes.filter((c) => c !== nom) : [...filters.communes, nom])}
                className={`rounded-full border px-2 py-0.5 font-mono text-[10.5px] tabular-nums transition-colors duration-quick ${
                  filters.communes.includes(nom) ? 'border-mint bg-mint/20 font-medium text-txt-hi'
                    : 'border-line-2 bg-surface-3 text-txt-mut hover:border-mint/50 hover:text-txt'}`}>
                {cp}
              </button>
            </Tip>
          ))}
        </div>
        <div className="mt-1.5 flex gap-3">
          {/* M55-G point 12 : libellés d'ACTION (« tout » / « rien (toute l'île) » ne disaient
              pas le geste) — le sous-titre de la section garde « tout coché = toute l'île ». */}
          <button data-communes-toutes onClick={() => setCommunesFilter(CP_COMMUNES.map(([, n]) => n))}
            className="text-[10.5px] text-txt-dim underline decoration-txt-dim/40 underline-offset-2 hover:text-mint">Ajouter tout</button>
          <button data-communes-aucune onClick={() => setCommunesFilter([])}
            className="text-[10.5px] text-txt-dim underline decoration-txt-dim/40 underline-offset-2 hover:text-mint">Retirer tout</button>
          {nCom > 0 && <span className="text-[10.5px] text-txt-dim">{nCom === 1 ? filters.communes[0] : `${nCom} communes`}</span>}
        </div>
      </div>

      {/* ═══════ 2 · LE TERRAIN (faits objectifs, toujours actifs — contraintes EN DERNIER) ═══════ */}
      <TitreSection cls="mt-4" titre="2 · Le terrain"
        info="Des faits objectifs (surface, zonage, état du sol) — valables sans aucune analyse." />
      <div className="mt-1.5 flex flex-col gap-3">
        <div>
          <p className="label-caps text-txt-dim">Surface parcelle</p>
          <div className="mt-1 flex items-center gap-1.5"><NumField field="surfaceMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="surfaceMax" ph="max" suffix="m²" /></div>
        </div>
        <div>
          <p className="label-caps text-txt-dim">Zonage</p>
          <div className="mt-1"><ChipGroup field="zonagePlu" options={ZONE_FAM} /></div>
          <input placeholder="zone exacte : UA, UB, 2AU (séparées par des virgules)"
            value={filters.zonePlu.join(', ')}
            onChange={(e) => setFilter('zonePlu', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
            className="mt-1.5 w-full rounded-md border border-line-2 bg-surface-3 px-2 py-1 text-[11px] text-txt-hi placeholder:text-txt-dim focus:border-mint focus:outline-none" />
        </div>
        <div>
          <p className="label-caps text-txt-dim">État du sol</p>
          <div className="mt-1"><ChipGroup field="etatSol" options={ETAT_SOL} /></div>
        </div>
      </div>
      {/* M55-D stage 7 (décision Vic) : « Contraintes de secteur » a QUITTÉ le panneau Filtres —
          les flags restent visibles en fiche et en couches. Les clés URL legacy (fl=) sont
          ignorées proprement à la lecture (filters.ts). */}

      {/* ═══════ 3 · SIGNAUX DE VIE (M55-D stage 6 · M55-G suite point 4) — ÉVÉNEMENTS
          SOURCÉS, filtrables SANS analyse (pas des jugements). OU entre signaux du groupe,
          ET avec le reste. UN SEUL niveau, 7 signaux (décision Vic). ═══════ */}
      <div data-signaux-vie className="mt-4">
        <TitreSection titre="3 · Signaux de vie"
          info="Des événements sourcés, cumulables — une parcelle correspond si au moins un des signaux cochés est présent. Chaque signal porte son propre « i » (source et date)." />
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {SIGNAUX_KEYS.map((k) => <SignalChip key={k} k={k} />)}
        </div>
      </div>

      {/* ═══════ COMPTEUR VIVANT (stage 7) — visible dès qu'un filtre est posé ═══════ */}
      {nActifs > 0 && (
        <p data-compteur-vivant aria-live="polite"
          className={`mt-3 text-[11.5px] tabular-nums transition-opacity duration-quick ${liveLoading ? 'opacity-50' : 'opacity-100'} ${live === 0 ? 'text-st-creuser' : 'text-txt-mut'}`}>
          {live == null ? '…' : live === 0 ? CLIENT.compteur.zero
            : <><b className="text-txt">{nf.format(live)}</b> parcelles correspondent à vos critères</>}
        </p>
      )}
      </>
      )}

      {/* ═══════ ÉTAGE ② — LE REGARD LABUSE (stage 5 : LA RÉVÉLATION — appel, décompte, phrase) ═══════ */}
      <div className={`mt-4 rounded-xl border p-3 transition-colors duration-soft ${
        analyseOn || phase === 'counting' || phase === 'revealed' ? 'border-mint/60 bg-mint/[0.07]' : 'border-line-2 bg-surface-2/40'}`}>
        {phase === 'counting' ? (
          /* ── 2. LE DÉCOMPTE — 3 s constantes ; texte honnête (on APPLIQUE des critères) ── */
          <div data-decompte className="py-2 text-center" aria-live="polite">
            <p className="font-display text-[24px] font-bold text-mint tabular-nums">
              {reduced ? '…' : nf.format(countVal)}
              {!reduced && live != null && countVal >= live && <span aria-hidden> ✓</span>}
            </p>
            <p className="mt-1 text-[11px] leading-snug text-txt-dim">
              {CLIENT.revelation.decompte(live ?? 431_663)}…
            </p>
          </div>
        ) : phase === 'error' ? (
          /* ── échec réseau : état d'erreur honnête, jamais un faux succès ── */
          <div data-analyse-erreur className="py-1">
            <p className="text-[12px] leading-snug text-st-ecartee">{CLIENT.revelation.erreur}</p>
            <button onClick={lancer}
              className="mt-2 rounded-lg border border-line-2 px-3 py-1 text-[11.5px] text-txt transition-colors duration-quick hover:border-mint hover:text-mint">
              {CLIENT.revelation.reessayer}
            </button>
          </div>
        ) : phase === 'revealed' && stale ? (
          /* ── FILET (M55-J point 1) : les filtres ont bougé par un chemin externe → carte
             invalidée, jamais un chiffre périmé. Un seul geste : relancer sur les nouveaux
             critères (le rituel repart proprement sur un snapshot frais). ── */
          <div data-analyse-perimee className="py-1">
            <p className="text-[12px] leading-snug text-st-creuser">{CLIENT.revelation.perime}</p>
            <button onClick={lancer}
              className="mt-2 w-full rounded-lg bg-mint py-2 font-display text-[12.5px] font-bold text-mint-ink transition-[filter] duration-quick hover:brightness-110">
              {CLIENT.revelation.relancerCta}
            </button>
          </div>
        ) : phase === 'revealed' ? (
          /* ── 3. LA PHRASE — nombres RÉELS de /filtre (compte + ventilation par tier).
             M55-G point 7 : la phrase ne vit QU'AU moment du reveal — le panneau ré-ouvert
             après analyse ne la répète plus (le récit des nombres vit dans la zone résultats,
             un seul récit, M55-F point 1). ── */
          <div data-phrase>
            <p className="text-[11.5px] leading-relaxed text-txt-mut">
              {/* M55-H point 10 : jamais « 0 parcelles » pendant que la trame charge — la phrase
                  d'intro attend un total connu (le reste s'affiche sans elle). M55-J point 1 :
                  l'effectif ANALYSÉ vient UNIQUEMENT du snapshot (freshTrame → analyseTotal),
                  JAMAIS du live — sinon on afficherait brièvement les retenues comme analysées. */}
              {analyseTotal != null && <>{CLIENT.revelation.phraseIntro(analyseTotal, perimetre)}{' '}</>}
              {CLIENT.revelation.phraseSelon(recap)}
            </p>
            {phraseRetenues === 0 ? (
              <p data-phrase-zero className="mt-1 text-[12.5px] font-medium leading-snug text-st-creuser">{CLIENT.revelation.phraseZero}</p>
            ) : (
              /* Ventilation COMPLÈTE (4 tiers + déclassées = retenues) puis écartées (étage 0) —
                 l'arithmétique boucle : retenues + écartées = analysé (point 2). */
              <p className="mt-1 text-[13px] leading-relaxed text-txt">
                <b className="text-[16px] text-mint tabular-nums">{phraseRetenues == null ? '…' : nf.format(phraseRetenues)}</b> retenues
                {t && phraseRetenues != null && (
                  <> — dont{' '}
                    <Tip side="top" tip={CLIENT.revelation.defTiers.brulante}>
                      <b className="cursor-help tabular-nums underline decoration-dotted decoration-txt-dim underline-offset-2">{pl(t.brulante, 'brûlante')}</b></Tip>,{' '}
                    <Tip side="top" tip={CLIENT.revelation.defTiers.chaude}>
                      <b className="cursor-help tabular-nums underline decoration-dotted decoration-txt-dim underline-offset-2">{pl(t.chaude, 'chaude')}</b></Tip>,{' '}
                    <Tip side="top" tip={CLIENT.revelation.defTiers.reserve_fonciere}>
                      <b className="cursor-help tabular-nums underline decoration-dotted decoration-txt-dim underline-offset-2">{nf.format(t.reserve_fonciere)} en potentiel long terme</b></Tip>,{' '}
                    <Tip side="top" tip={CLIENT.revelation.defTiers.a_creuser}>
                      <b className="cursor-help tabular-nums underline decoration-dotted decoration-txt-dim underline-offset-2">{nf.format(t.a_creuser)} à creuser</b></Tip>
                    {declassees > 0 && (
                      <>,{' '}
                        <Tip side="top" tip={CLIENT.revelation.defTiers.declassees}>
                          <b className="cursor-help tabular-nums underline decoration-dotted decoration-txt-dim underline-offset-2">{CLIENT.revelation.ventDeclassees(declassees)}</b></Tip>
                      </>
                    )}
                  </>
                )}
                {ecartees != null && ecartees > 0 && (
                  <> — et <b className="tabular-nums text-txt-mut">{CLIENT.revelation.ecarteesLbl(ecartees)}</b>{' '}
                    <span className="text-txt-dim">({CLIENT.revelation.ecarteesMotifs})</span>{' '}
                    <Tip side="top" tip={CLIENT.revelation.ecarteesTip}>
                      <span data-voir-pourquoi role="button" tabIndex={0}
                        className="cursor-help text-mint underline decoration-dotted underline-offset-2">{CLIENT.revelation.voirPourquoi}</span></Tip>
                  </>
                )}.
              </p>
            )}
            {phase === 'revealed' && (
              /* ── 4. LE GESTE FINAL — l'analyse s'allume, la section se rétracte ── */
              <button data-voir-parcelles onClick={voirParcelles}
                className="mt-3 w-full rounded-lg bg-mint py-2 font-display text-[13px] font-bold text-mint-ink transition-[filter] duration-quick hover:brightness-110">
                {CLIENT.revelation.voir}
              </button>
            )}
          </div>
        ) : !analyseOn ? (
          /* ── 1. L'APPEL — LES deux boutons, sans bandeau (M55-G suite point 5). M55-H
             point 3 : GROUPE net — marges constantes (gap-2), même largeur, secondaire
             franc (fond + bordure visibles) AU-DESSUS, primaire dominant (plus haut, flèche
             dessinée — même patron que « Commencer »). La carte ne bouge QU'AU geste. ── */
          <div data-appel className="flex flex-col gap-2">
            <button data-voir-factuel onClick={voirFactuel}
              className={`w-full rounded-lg border border-line-2 bg-surface-3/60 py-2.5 text-[12.5px] font-medium text-txt transition-colors duration-quick hover:border-txt-dim/50 hover:bg-surface-3 hover:text-txt-hi ${liveLoading ? 'opacity-70' : 'opacity-100'}`}>
              {CLIENT.revelation.voirN(live ?? 431_663)}
            </button>
            <button data-analyser-btn onClick={lancer}
              className={`group flex w-full items-center justify-center gap-2 rounded-lg bg-mint py-3 font-display text-[13.5px] font-bold text-mint-ink shadow-[0_0_18px_rgba(92,230,161,0.3)] transition-[box-shadow,filter,transform,opacity] duration-soft hover:shadow-[0_0_30px_rgba(92,230,161,0.5)] hover:brightness-105 active:translate-y-[1px] active:brightness-95 ${liveLoading ? 'opacity-70' : 'opacity-100'}`}>
              <span>{CLIENT.revelation.boutonFaire.replace(/\s*→\s*$/, '')}</span>
              <svg viewBox="0 0 16 16" aria-hidden="true"
                className="h-[13px] w-[13px] transition-transform duration-quick group-hover:translate-x-0.5">
                <path d="M2.5 8 H13 M9.5 3.5 L14 8 L9.5 12.5" fill="none" stroke="currentColor"
                  strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
          </div>
        ) : null}
        {analyseOn && phase === 'idle' && (
          <div className="mt-3 flex flex-col gap-3">
            {/* M55-G suite point 3 (décision Vic) : l'état post-analyse ne porte PLUS AUCUN
                contenu — chips verdict/tiers, motifs, constructibilité, potentiel, SDP,
                capacité, veille, copros et notes RETIRÉS (0-caller). Ne restent que les deux
                gestes : « Relancer l'analyse » et « désactiver l'analyse ». Conséquence actée :
                le filtrage par tier post-analyse quitte ce panneau (les champs gardent leur
                persistance URL — vieux liens compatibles). */}

            {/* M55-J point 2 : DEUX BOUTONS de même famille (ActionBtn), hiérarchisés —
                Relancer = action principale (primary, mint), Désactiver = action secondaire
                (contour). Plus de « lien souligné gris » qui ne se lit ni comme action ni
                comme état. Marges constantes (gap-2), même largeur (flex-1). */}
            <div className="flex gap-2 pt-1">
              <ActionBtn variant="primary" dataAttr="data-relancer" onClick={lancer}>
                {CLIENT.revelation.relancer}
              </ActionBtn>
              <ActionBtn variant="secondary" dataAttr="data-desactiver"
                onClick={() => { setAnalyse(false); setSnapFilters(null); setPhase('idle') }}>
                {CLIENT.revelation.desactiver}
              </ActionBtn>
            </div>
          </div>
        )}
      </div>

      {/* M55-D stage 7 (décision Vic) : plus AUCUNE section pédagogique dans le panneau —
          « Puis-je construire ? » retirée (les repères droit du sol vivent en fiche). */}

      {/* M55-G point 9 / M55-H point 3 : danger SOBRE, SÉPARÉ du groupe d'action (filet +
          respiration — jamais collé aux deux boutons). M55-J : masqué pendant l'analyse (les
          filtres sont figés — Désactiver l'analyse d'abord pour retrouver le reset). */}
      {!analyseActive && (
        <div className="mt-4 border-t border-line-2/50 pt-3">
          <button onClick={resetTout}
            title="Efface les DEUX étages et éteint l'interrupteur — retour à l'état vierge."
            className="min-h-8 w-full rounded-lg border border-st-ecartee/40 py-1.5 text-[11px] text-st-ecartee/80 transition-colors duration-quick hover:border-st-ecartee/70 hover:bg-st-ecartee/10 hover:text-st-ecartee">
            Réinitialiser les filtres
          </button>
        </div>
      )}
    </div>
  )
}
