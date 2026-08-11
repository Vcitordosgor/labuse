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

import { getFiltre, getFiltreCount, getV2Modele } from '../../lib/api'
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
const ZONE_FAM = [{ k: 'U', l: 'U' }, { k: 'AU', l: 'AU' }, { k: 'A', l: 'A' }, { k: 'N', l: 'N' }]
// M55-G point 7 : PROPRIO_TYPE / ETAT_SOCIETE / COPRO retirés avec les tiroirs pédagogiques
// (0-caller) — les champs de filtre restent dans le store + l'URL.
// M55-D stage 6 — les 24 communes par CODE POSTAL (CP dominant mesuré dans la BAN, table
// adresses). La chip affiche le CP, le « i » (title) nomme la commune. Rang 1 du panneau.
const CP_COMMUNES: [string, string][] = [
  ['97400', 'Saint-Denis'], ['97410', 'Saint-Pierre'], ['97412', 'Bras-Panon'],
  ['97413', 'Cilaos'], ['97414', 'Entre-Deux'], ['97419', 'La Possession'],
  ['97420', 'Le Port'], ['97424', 'Saint-Leu'], ['97425', 'Les Avirons'],
  ['97426', 'Les Trois-Bassins'], ['97427', "L'Étang-Salé"], ['97429', 'Petite-Île'],
  ['97430', 'Le Tampon'], ['97431', 'La Plaine-des-Palmistes'], ['97433', 'Salazie'],
  ['97438', 'Sainte-Marie'], ['97439', 'Sainte-Rose'], ['97440', 'Saint-André'],
  ['97441', 'Sainte-Suzanne'], ['97442', 'Saint-Philippe'], ['97450', 'Saint-Louis'],
  ['97460', 'Saint-Paul'], ['97470', 'Saint-Benoît'], ['97480', 'Saint-Joseph'],
]
// M55-G point 11 (décision Vic) — DEUX niveaux : les signaux LARGES devant (ceux qui parlent
// à tout le monde — dont le nouveau « Détenu par une société », 33 622 île / 7 460 servables,
// mesuré 12/08), les NICHES derrière « Plus de signaux ⌄ ». Libellés/« i » : CLIENT.signaux.
// Le OU de groupe et la persistance URL (sv=) sont inchangés — mêmes clés, même schéma.
const SIGNAUX_LARGES = ['pm_privee', 'procedure', 'permis_actif', 'permis_caduc', 'friche']
const SIGNAUX_NICHES = ['nu_pm', 'defisc', 'cession', 'assemblage']


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
  // Reset : les DEUX étages + éteint l'interrupteur (retour à l'état vierge).
  const resetTout = () => { setFilters(EMPTY_FILTERS); setVerdict(false) }
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
  // M55-G point 11 : niveau 2 des signaux — replié par défaut, mais OUVERT si une niche est
  // déjà active (restauration URL : jamais un filtre actif invisible).
  const [nichesOuvertes, setNichesOuvertes] = useState(
    () => filters.signaux.some((k) => SIGNAUX_NICHES.includes(k)))
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
  // réponse FRAÎCHE du rituel (appel DIRECT, sans retry) — la phrase révèle CES nombres-là
  const [fresh, setFresh] = useState<Awaited<ReturnType<typeof getFiltre>> | null>(null)
  const timerRef = useRef<number | null>(null)
  const rafRef = useRef<number | null>(null)
  // date du run servi (champ `gel` du modèle épinglé) — la ligne de contexte de l'appel
  const modele = useQuery({ queryKey: ['v2-modele'], queryFn: getV2Modele, staleTime: 3_600_000, retry: false })
  const runDate = (() => {
    const g = modele.data?.gel
    if (!g) return null
    const d = new Date(g.replace(' ', 'T'))
    return Number.isNaN(d.getTime()) ? null : d.toLocaleDateString('fr-FR')
  })()
  // prefers-reduced-motion : décompte remplacé par une transition simple (courte)
  const reduced = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  const RITUEL_MS = reduced ? 400 : 3000
  const lancer = () => {
    setPhase('counting'); setCountVal(0); setFresh(null)
    // la VRAIE requête part MAINTENANT (appel direct, SANS retry : un échec interrompt le rituel
    // au lieu d'être masqué par les retries react-query au-delà des 3 s)
    getFiltre({ ...filters, analyseLabuse: true }, 0)
      .then((r) => setFresh(r))
      .catch(() => {
        if (phaseRef.current !== 'counting') return
        if (timerRef.current) window.clearTimeout(timerRef.current)
        if (rafRef.current) cancelAnimationFrame(rafRef.current)
        setPhase('error')
      })
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
  const nCom = filters.communes.length
  const perimetre = nCom === 1 ? filters.communes[0] : nCom > 1 ? `${nCom} communes` : (commune ?? 'La Réunion')
  const recap = resumeCriteres(filters, CLIENT.signaux.labels)
  // la phrase révèle les nombres du RITUEL (réponse fraîche) ; hors rituel, la requête vivante
  const src = phase === 'revealed' && fresh ? fresh : on.data
  const phraseRetenues = src?.compte
  const t = src?.tiers
  const pl = (n: number, s: string) => `${nf.format(n)} ${s}${n > 1 ? 's' : ''}`
  // M55-F point 2 — l'arithmétique de la phrase (tout du point unique, mêmes critères) :
  //  · analysé (trame)     = trameQ.compte
  //  · retenues            = src.compte  (= ventilation 4 tiers + déclassées)
  //  · déclassées          = retenues − (brûlante+chaude+réserve+à creuser)   (motif, dans retenues)
  //  · écartées (étage 0)  = analysé − retenues                               (exclusions dures)
  const analyseTotal = trameQ.data?.compte
  const vent4 = t ? t.brulante + t.chaude + t.reserve_fonciere + t.a_creuser : 0
  const declassees = phraseRetenues != null ? phraseRetenues - vent4 : 0
  const ecartees = (analyseTotal != null && phraseRetenues != null) ? analyseTotal - phraseRetenues : null

  return (
    <div className="card-elev px-3 py-2">
      {/* ═══════ 1 · COMMUNES — rang 1, MAÎTRE du périmètre (M55-D stage 6). Multi par code
          postal ; le sélecteur du header n'est plus qu'un REFLET de CE filtre. ═══════ */}
      <div data-communes-filtre>
        <p className="label-caps text-txt-mut">1 · Communes
          <span className="ml-1.5 text-[9px] font-normal normal-case text-txt-dim">le périmètre — tout coché = toute l’île</span></p>
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
      <p className="mt-4 label-caps text-txt-mut">2 · Le terrain
        <span className="ml-1.5 text-[9px] font-normal normal-case text-txt-dim">faits, sans analyse</span></p>
      <div className="mt-1.5 flex flex-col gap-3">
        <div>
          <p className="label-caps text-txt-dim">Surface parcelle</p>
          <div className="mt-1 flex items-center gap-1.5"><NumField field="surfaceMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="surfaceMax" ph="max" suffix="m²" /></div>
        </div>
        <div>
          <p className="label-caps text-txt-dim">Zonage <span className="normal-case text-[8.5px] text-txt-dim">— famille U/AU/A/N + zone exacte</span></p>
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

      {/* ═══════ 3 · SIGNAUX DE VIE (M55-D stage 6 · M55-G point 11) — ÉVÉNEMENTS SOURCÉS,
          filtrables SANS analyse (pas des jugements). OU entre signaux du groupe, ET avec le
          reste. Deux niveaux : LARGES visibles, NICHES derrière « Plus de signaux ⌄ ». ═══════ */}
      <div data-signaux-vie className="mt-4">
        <p className="label-caps text-txt-mut">3 · Signaux de vie
          <span className="ml-1.5 text-[9px] font-normal normal-case text-txt-dim">événements sourcés — cumulables</span></p>
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {SIGNAUX_LARGES.map((k) => <SignalChip key={k} k={k} />)}
        </div>
        <button data-signaux-plus onClick={() => setNichesOuvertes((o) => !o)}
          aria-expanded={nichesOuvertes}
          className="mt-1.5 text-[10.5px] text-txt-dim underline decoration-txt-dim/40 underline-offset-2 hover:text-mint">
          {CLIENT.signaux.plus} <span className={`inline-block transition-transform duration-quick ${nichesOuvertes ? '' : 'rotate-90'}`} aria-hidden="true">⌄</span>
        </button>
        {nichesOuvertes && (
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {SIGNAUX_NICHES.map((k) => <SignalChip key={k} k={k} />)}
          </div>
        )}
      </div>

      {/* ═══════ COMPTEUR VIVANT (stage 7) — visible dès qu'un filtre est posé ═══════ */}
      {nActifs > 0 && (
        <p data-compteur-vivant aria-live="polite"
          className={`mt-3 text-[11.5px] tabular-nums transition-opacity duration-quick ${liveLoading ? 'opacity-50' : 'opacity-100'} ${live === 0 ? 'text-st-creuser' : 'text-txt-mut'}`}>
          {live == null ? '…' : live === 0 ? CLIENT.compteur.zero
            : <><b className="text-txt">{nf.format(live)}</b> parcelles correspondent à vos critères</>}
        </p>
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
        ) : phase === 'revealed' ? (
          /* ── 3. LA PHRASE — nombres RÉELS de /filtre (compte + ventilation par tier).
             M55-G point 7 : la phrase ne vit QU'AU moment du reveal — le panneau ré-ouvert
             après analyse ne la répète plus (le récit des nombres vit dans la zone résultats,
             un seul récit, M55-F point 1). ── */
          <div data-phrase>
            <p className="text-[11.5px] leading-relaxed text-txt-mut">
              {CLIENT.revelation.phraseIntro(analyseTotal ?? live ?? 0, perimetre)}{' '}
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
          /* ── 1. L'APPEL — contexte sobre + LE bouton chaud du panneau éteint ── */
          <div data-appel>
            {/* M55-D stage 8 : UN SEUL NOMBRE — bandeau, compteur et bouton dérivent tous de `live`
                (le compteur du stage 7). Pendant le fetch, l'opacité baisse PARTOUT en même temps
                (état de chargement partagé) — jamais un endroit à jour et l'autre en retard.
                La DATE du classement, elle, ne dépend pas des filtres. */}
            <p data-bandeau className={`text-[11.5px] leading-snug text-txt transition-opacity duration-quick ${liveLoading ? 'opacity-50' : 'opacity-100'}`}>
              {CLIENT.revelation.contexte(live ?? 431_663, runDate)}</p>
            <p className="mt-0.5 text-[10px] leading-snug text-txt-dim">{CLIENT.revelation.contexteSous}</p>
            {/* M55-F point 3 / M55-G point 2 — DEUX choix : « Voir les N parcelles » (sobre,
                « je cherche moi-même ») passe EN PREMIER ; le CTA d'analyse (mint dominant, le
                rituel du stage 5, inchangé) second, renommé « Révéler les opportunités → ».
                La carte ne bouge QU'AU geste (aucune repeinte pendant le réglage : verdict
                reste false tant qu'aucun bouton n'est cliqué). */}
            <button data-voir-factuel onClick={voirFactuel}
              className={`mt-2.5 w-full rounded-lg border border-line-2 py-1.5 text-[12px] text-txt-mut transition-colors duration-quick hover:border-mint/40 hover:text-txt ${liveLoading ? 'opacity-70' : 'opacity-100'}`}>
              {CLIENT.revelation.voirN(live ?? 431_663)}
            </button>
            <button data-analyser-btn onClick={lancer}
              className={`mt-2 w-full rounded-lg bg-mint py-2.5 font-display text-[13px] font-bold text-mint-ink shadow-[0_0_18px_rgba(92,230,161,0.3)] transition-[shadow,opacity] duration-soft hover:shadow-[0_0_28px_rgba(92,230,161,0.5)] ${liveLoading ? 'opacity-70' : 'opacity-100'}`}>
              {CLIENT.revelation.boutonFaire}
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

            {/* relance (re-décompte 3 s, décision Vic) + extinction DISCRÈTE (la cérémonie est à
                l'allumage, pas à l'extinction) */}
            <div className="flex items-center justify-between pt-1">
              <button data-relancer onClick={lancer}
                className="rounded-lg border border-mint/50 px-3 py-1 text-[11.5px] font-medium text-mint transition-colors duration-quick hover:bg-mint/10">
                {CLIENT.revelation.relancer}
              </button>
              <button data-desactiver onClick={() => setAnalyse(false)}
                className="text-[10.5px] text-txt-dim underline decoration-txt-dim/50 underline-offset-2 transition-colors duration-quick hover:text-txt">
                {CLIENT.revelation.desactiver}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* M55-D stage 7 (décision Vic) : plus AUCUNE section pédagogique dans le panneau —
          « Puis-je construire ? » retirée (les repères droit du sol vivent en fiche). */}

      {/* M55-G point 9 : libellé court, danger SOBRE — contour rouge discret, pas un pavé.
          Le geste reste inchangé (les deux étages + interrupteur), le title le dit. */}
      <button onClick={resetTout}
        title="Efface les DEUX étages et éteint l'interrupteur — retour à l'état vierge."
        className="mt-3 min-h-8 w-full rounded-lg border border-st-ecartee/40 py-1.5 text-[11px] text-st-ecartee/80 transition-colors duration-quick hover:border-st-ecartee/70 hover:bg-st-ecartee/10 hover:text-st-ecartee">
        Réinitialiser les filtres
      </button>
    </div>
  )
}
