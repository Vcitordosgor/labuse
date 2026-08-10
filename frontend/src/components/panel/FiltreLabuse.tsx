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
import { DECLASSE_ORDER, TIER_DECLASSE_META, TIER_V2_META, type FilterTier, type TierV2 } from '../../lib/status'
import { CLIENT } from '../../lib/strings'
import { EMPTY_FILTERS, useApp, type Filters } from '../../store/useApp'
import { Tip } from '../Tip'

const CONSTRUCTIBILITE = [
  { k: 'constructible', l: 'Constructible' },
  { k: 'au_conditionnelle', l: 'AU conditionnelle' },
  { k: 'fermee', l: 'Zone fermée' },
  { k: 'inconstructible', l: 'Inconstructible' },
  { k: 'rnu', l: 'RNU / hors-PLU' },
]
const ETAT_SOL = [
  { k: 'nu', l: 'Nu' },
  { k: 'bati_marginal', l: 'Bâti marginal' },
  { k: 'bati_sature', l: 'Bâti saturé' },
  { k: 'bati_revele', l: 'Bâti révélé' },
]
const ZONE_FAM = [{ k: 'U', l: 'U' }, { k: 'AU', l: 'AU' }, { k: 'A', l: 'A' }, { k: 'N', l: 'N' }]
const PROPRIO_TYPE = [{ k: 'pm', l: 'PM identifiée (SIREN)' }, { k: 'bailleur', l: 'Bailleur (HLM/SEM)' }, { k: 'pp', l: 'Particulier / non déterminable' }]
const ETAT_SOCIETE = [{ k: 'procedure', l: 'Procédure collective' }, { k: 'cessee', l: 'Cessée' }, { k: 'radiee', l: 'Radiée' }]
const COPRO = [{ k: 'avec', l: 'En copropriété' }, { k: 'sans', l: 'Hors copropriété' }]
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
//: clés du groupe Signaux de vie (8 validés Vic) — libellés/« i » dans strings (CLIENT.signaux)
const SIGNAUX_KEYS = ['procedure', 'permis_actif', 'permis_caduc', 'defisc',
  'nu_pm', 'friche', 'cession', 'assemblage']


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

function BoolChip({ field, label }: { field: keyof Filters; label: string }) {
  const { filters, setFilter } = useApp()
  const on = !!filters[field]
  return <Chip on={on} onClick={() => setFilter(field, !on as never)}>{label}</Chip>
}

function Tiroir({ titre, sous, defaut = false, children }: { titre: string; sous?: string; defaut?: boolean; children: React.ReactNode }) {
  const [ouvert, setOuvert] = useState(defaut)
  return (
    <div className="border-t border-line-2/50">
      <button onClick={() => setOuvert((o) => !o)} className="flex w-full items-center justify-between py-1.5 text-left">
        <span className="text-xs font-medium text-txt-hi">{titre}{sous && <span className="text-txt-dim"> — {sous}</span>}</span>
        {/* M55-A point 4 : même patron que « Couches » — fermé → gauche (⌄ pivoté), ouvert → bas. */}
        <span className={`text-txt-dim transition-transform duration-quick ${ouvert ? '' : 'rotate-90'}`} aria-hidden="true">⌄</span>
      </button>
      {ouvert && <div className="pb-1">{children}</div>}
    </div>
  )
}

// M45-B (L2) — curseur mode B : une valeur de SESSION unique (travaux + loyer + rendement),
// partagée fiche ↔ filtre, rien persisté. Pilote le filtre « Mode B rentable » ET le calcul de la fiche.
function ModeBCurseur() {
  const modeB = useApp((s) => s.modeB)
  const setModeB = useApp((s) => s.setModeB)
  const Champ = ({ k, label, suffix, step }: { k: 'travauxM2' | 'loyerM2' | 'rendementPct'; label: string; suffix: string; step?: number }) => (
    <label className="flex items-center gap-1 text-[11px] text-txt-mut">
      {label}
      <input type="number" step={step ?? 1} value={modeB[k]}
        onChange={(e) => setModeB({ [k]: Number(e.target.value) })}
        className="w-[62px] rounded-md border border-line-2 bg-transparent px-1.5 py-0.5 text-[11px] text-txt-hi focus:border-mint focus:outline-none" />
      <span className="text-[9.5px] text-txt-dim">{suffix}</span>
    </label>
  )
  return (
    <div className="mt-1 rounded-lg border border-line-2/60 bg-surface-2/40 px-2.5 py-2">
      <p className="label-caps">Curseur mode B <span className="text-[9px] font-normal normal-case text-txt-dim">— session partagée avec la fiche</span></p>
      <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1.5">
        <Champ k="travauxM2" label="Travaux" suffix="€/m²" step={50} />
        <Champ k="loyerM2" label="Loyer" suffix="€/m²/mois" step={0.5} />
        <Champ k="rendementPct" label="Rendement" suffix="%" step={0.5} />
      </div>
    </div>
  )
}


function Section({ title, tag, children }: { title: string; tag?: string; children: React.ReactNode }) {
  return (
    <div className="py-2">
      <p className="label-caps flex items-center gap-1.5">
        {title}
        {tag && <span className="rounded border border-line-2 px-1 py-px text-[8.5px] font-normal uppercase tracking-wide text-txt-dim">{tag}</span>}
      </p>
      {children}
    </div>
  )
}



export function FiltreLabuse({ onRetract }: { onRetract?: () => void } = {}) {
  const { filters, setFilter, setFilters, setVerdict, commune, setCommunesFilter } = useApp()
  const analyseOn = filters.analyseLabuse
  const TIERS_V2: TierV2[] = ['brulante', 'chaude', 'reserve_fonciere', 'a_creuser', 'ecartee']
  const toggleTier = (t: FilterTier) =>
    setFilter('tiers', filters.tiers.includes(t) ? filters.tiers.filter((x) => x !== t) : [...filters.tiers, t])
  // M55-D stage 4 : interrupteur UNIFIÉ — analyseLabuse (persisté, URL) ⟺ verdict (carte). Éteint
  // par défaut : plus jamais « analyse active » quand l'utilisateur n'a rien allumé (bug mesuré).
  const setAnalyse = (v: boolean) => { setFilter('analyseLabuse', v); setVerdict(v) }
  // Reset : les DEUX étages + éteint l'interrupteur (retour à l'état vierge).
  const resetTout = () => { setFilters(EMPTY_FILTERS); setVerdict(false) }
  // Compteurs : parc FACTUEL (analyse coupée) et RETENUES (analyse). La transition raconte l'effet.
  const on = useQuery({ queryKey: ['filtre', filters, true], queryFn: () => getFiltre({ ...filters, analyseLabuse: true }, 0) })

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
  const nCom = filters.communes.length
  const perimetre = nCom === 1 ? filters.communes[0] : nCom > 1 ? `${nCom} communes` : (commune ?? 'La Réunion')
  const recap = resumeCriteres(filters, CLIENT.signaux.labels)
  // la phrase révèle les nombres du RITUEL (réponse fraîche) ; hors rituel, la requête vivante
  const src = phase === 'revealed' && fresh ? fresh : on.data
  const phraseRetenues = src?.compte
  const t = src?.tiers
  const pl = (n: number, s: string) => `${nf.format(n)} ${s}${n > 1 ? 's' : ''}`

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
          <button data-communes-toutes onClick={() => setCommunesFilter(CP_COMMUNES.map(([, n]) => n))}
            className="text-[10.5px] text-txt-dim underline decoration-txt-dim/40 underline-offset-2 hover:text-mint">tout</button>
          <button data-communes-aucune onClick={() => setCommunesFilter([])}
            className="text-[10.5px] text-txt-dim underline decoration-txt-dim/40 underline-offset-2 hover:text-mint">rien (toute l’île)</button>
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

      {/* ═══════ 3 · SIGNAUX DE VIE (M55-D stage 6) — 8 ÉVÉNEMENTS SOURCÉS, filtrables SANS
          analyse (pas des jugements). OU entre signaux du groupe, ET avec le reste. ═══════ */}
      <div data-signaux-vie className="mt-4">
        <p className="label-caps text-txt-mut">3 · Signaux de vie
          <span className="ml-1.5 text-[9px] font-normal normal-case text-txt-dim">événements sourcés — cumulables</span></p>
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {SIGNAUX_KEYS.map((k) => (
            <span key={k} className="flex items-center gap-1">
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
          ))}
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
        ) : phase === 'revealed' || analyseOn ? (
          /* ── 3. LA PHRASE — nombres RÉELS de /filtre (compte + ventilation par tier) ── */
          <div data-phrase>
            <p className="text-[11.5px] leading-relaxed text-txt-mut">
              {CLIENT.revelation.phraseIntro(live ?? 0, perimetre)}{' '}
              {CLIENT.revelation.phraseSelon(recap)}
            </p>
            {phraseRetenues === 0 ? (
              <p data-phrase-zero className="mt-1 text-[12.5px] font-medium leading-snug text-st-creuser">{CLIENT.revelation.phraseZero}</p>
            ) : (
              <p className="mt-1 text-[13px] leading-relaxed text-txt">
                <b className="text-[16px] text-mint tabular-nums">{phraseRetenues == null ? '…' : nf.format(phraseRetenues)}</b> retenues
                {t && phraseRetenues != null && (
                  <> — dont{' '}
                    <Tip side="top" tip={CLIENT.revelation.defTiers.brulante}>
                      <b className="cursor-help tabular-nums underline decoration-dotted decoration-txt-dim underline-offset-2">{pl(t.brulante, 'brûlante')}</b></Tip>,{' '}
                    <Tip side="top" tip={CLIENT.revelation.defTiers.chaude}>
                      <b className="cursor-help tabular-nums underline decoration-dotted decoration-txt-dim underline-offset-2">{pl(t.chaude, 'chaude')}</b></Tip>,{' '}
                    <Tip side="top" tip={CLIENT.revelation.defTiers.reserve_fonciere}>
                      <b className="cursor-help tabular-nums underline decoration-dotted decoration-txt-dim underline-offset-2">{nf.format(t.reserve_fonciere)} en potentiel long terme</b></Tip>
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
        ) : (
          /* ── 1. L'APPEL — contexte sobre + LE bouton chaud du panneau éteint ── */
          <div data-appel>
            {/* M55-D stage 8 : UN SEUL NOMBRE — bandeau, compteur et bouton dérivent tous de `live`
                (le compteur du stage 7). Pendant le fetch, l'opacité baisse PARTOUT en même temps
                (état de chargement partagé) — jamais un endroit à jour et l'autre en retard.
                La DATE du classement, elle, ne dépend pas des filtres. */}
            <p data-bandeau className={`text-[11.5px] leading-snug text-txt transition-opacity duration-quick ${liveLoading ? 'opacity-50' : 'opacity-100'}`}>
              {CLIENT.revelation.contexte(live ?? 431_663, runDate)}</p>
            <p className="mt-0.5 text-[10px] leading-snug text-txt-dim">{CLIENT.revelation.contexteSous}</p>
            <button data-analyser-btn onClick={lancer}
              className={`mt-2.5 w-full rounded-lg bg-mint py-2 font-display text-[13px] font-bold text-mint-ink shadow-[0_0_18px_rgba(92,230,161,0.3)] transition-[shadow,opacity] duration-soft hover:shadow-[0_0_28px_rgba(92,230,161,0.5)] ${liveLoading ? 'opacity-70' : 'opacity-100'}`}>
              {nActifs > 0 ? CLIENT.revelation.boutonFaire : CLIENT.revelation.boutonParc(live ?? 431_663)}
            </button>
          </div>
        )}
        {analyseOn && phase === 'idle' && (
          <div className="mt-3 flex flex-col gap-3">
            <div>
              <p className="label-caps text-txt-dim">Verdict · tiers</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {TIERS_V2.map((t) => (
                  <Chip key={t} on={filters.tiers.includes(t)} onClick={() => toggleTier(t)}>
                    <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full align-middle" style={{ background: TIER_V2_META[t].color }} />{TIER_V2_META[t].label}
                  </Chip>
                ))}
              </div>
            </div>
            <div>
              <p className="label-caps text-txt-dim">Déclassées · motif</p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {DECLASSE_ORDER.map((t) => (
                  <Chip key={t} on={filters.tiers.includes(t)} onClick={() => toggleTier(t)}>
                    <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full align-middle" style={{ background: TIER_DECLASSE_META[t].color }} />{TIER_DECLASSE_META[t].label.replace('Déclassée — ', '')}
                  </Chip>
                ))}
              </div>
              <p className="mt-1 text-[10px] leading-snug text-txt-dim">Les écartées ne sont jamais masquées — choisissez un motif pour les consulter, chacune garde son verdict.</p>
            </div>
            <Section title="Constructibilité calibrée" tag="Sourcé"><ChipGroup field="constructibilite" options={CONSTRUCTIBILITE} /></Section>
            <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
              <div><p className="label-caps text-txt-dim">Potentiel ≥ /100</p><div className="mt-1"><NumField field="scoreMin" ph="70" /></div></div>
              <div><p className="label-caps text-txt-dim">SDP résiduelle</p><div className="mt-1 flex items-center gap-1.5"><NumField field="sdpMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="sdpMax" ph="max" suffix="m²" /></div></div>
              <div><p className="label-caps flex items-center gap-1 text-txt-dim">Capacité <span className="rounded border border-line-2 px-1 text-[8px] uppercase">Est.</span></p><div className="mt-1 flex items-center gap-1"><span className="text-[11px] text-txt-dim">≥</span><NumField field="capaciteMin" ph="N" suffix="log." /></div></div>
            </div>
            {/* M55-D stage 6 : « Avec événement (BODACC) » REMPLACÉ par le groupe Signaux de vie. */}
            <div className="flex flex-wrap gap-1.5">
              <BoolChip field="veille" label="Veille succession" />
              <BoolChip field="horsCopro" label="Masquer copropriétés" />
            </div>

      {/* ── TIROIRS d'analyse (économie / mutation / propriété / niches) — dans l'étage ② ── */}
      <Tiroir titre="Combien ça coûte, ça rapporte ?" sous="économie">
        <div className="flex flex-wrap gap-x-6 gap-y-2 py-2">
          <div><p className="label-caps flex items-center gap-1.5">Prix d’achat max ≤ budget
            <span className="rounded border border-line-2 px-1 py-px text-[8.5px] uppercase text-txt-dim">Estimé</span></p>
            <div className="mt-1 flex items-center gap-1"><NumField field="budgetMax" ph="€" suffix="€" /></div></div>
          <div><p className="label-caps">Charge foncière (€)</p>
            <div className="mt-1 flex items-center gap-1.5"><NumField field="chargeMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="chargeMax" ph="max" /></div></div>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-2 py-2">
          <div><p className="label-caps flex items-center gap-1.5">Prix marché DVF (€/m²)
            <span className="rounded border border-line-2 px-1 py-px text-[8.5px] uppercase text-txt-dim">Sourcé</span></p>
            <div className="mt-1 flex items-center gap-1.5"><NumField field="prixMarcheMin" ph="min" /><span className="text-txt-dim">–</span><NumField field="prixMarcheMax" ph="max" suffix="€/m²" /></div></div>
          <div><p className="label-caps flex items-center gap-1.5">Bilan CA
            <span className="rounded border border-line-2 px-1 py-px text-[8.5px] uppercase text-txt-dim">Estimé</span></p>
            <div className="mt-1 flex items-center gap-1"><span className="text-[11px] text-txt-dim">≥</span><NumField field="caMin" ph="€" suffix="€" /></div></div>
        </div>
        <Section title="Repères">
          <div className="mt-1 flex flex-wrap gap-1.5">
            <BoolChip field="marcheFiable" label="Données marché fiables (n≥3)" />
            <BoolChip field="sousDensite" label="Bâti en sous-densité" />
            <BoolChip field="modeBRentable" label="Mode B rentable (au paramètre)" />
          </div>
        </Section>
        <ModeBCurseur />
      </Tiroir>

      <Tiroir titre="Ça va se vendre ?" sous="le cœur — voie analyse">
        <div className="flex flex-wrap gap-x-6 gap-y-2 py-2">
          <div><p className="label-caps">Probabilité ×N</p>
            <div className="mt-1 flex items-center gap-1"><span className="text-[11px] text-txt-dim">≥</span><NumField field="multMin" ph="N" suffix="×" /></div></div>
          <div><p className="label-caps">Têtes (rang P)</p>
            <div className="mt-1 flex items-center gap-1"><span className="text-[11px] text-txt-dim">≤</span><NumField field="rangMax" ph="N" /></div></div>
        </div>
        <Section title="Segments">
          <div className="mt-1 flex flex-wrap gap-1.5">
            <BoolChip field="renouvellement" label="Renouvellement" />
            <BoolChip field="divisionOr" label="Division en or (O12)" />
          </div>
          {/* M48 : le segment Renouvellement = des parcelles ÉCARTÉES par conception → 0 retenue par
              l'analyse. On le DIT quand le filtre est actif, pour lever le « 0 » déroutant du compteur. */}
          {filters.renouvellement && (
            <p className="mt-1.5 text-[10px] leading-snug text-txt-dim">
              Segment consultable via la <b className="text-txt-mut">voie manuelle</b> — coupez
              l’Analyse LABUSE pour l’explorer : ces parcelles occupées sont écartées du classement
              principal par conception (d’où 0 retenue par l’analyse).
            </p>
          )}
        </Section>
      </Tiroir>

      <Tiroir titre="À qui c’est, puis-je l’acheter ?" sous="propriété">
        <Section title="Type de propriétaire" tag="Sourcé"><ChipGroup field="proprietaireType" options={PROPRIO_TYPE} /></Section>
        <Section title="État de la société" tag="Sourcé (M43)"><ChipGroup field="etatSociete" options={ETAT_SOCIETE} /></Section>
        <Section title="Copropriété (RNIC)"><ChipGroup field="copro" options={COPRO} /></Section>
        <div className="pt-1 text-[10px] text-txt-dim">
          Dormance / succession : absent (attend avocat). Gérant âgé : jamais un critère (RGPD).
        </div>
      </Tiroir>

      <Tiroir titre="Veille & niches" sous="les différenciants">
        <Section title="Niches">
          <div className="mt-1 flex flex-wrap gap-1.5">
            <BoolChip field="npnru" label="Proximité NPNRU / QPV" />
            <BoolChip field="adresseAbsente" label="Adresse absente (BAN)" />
          </div>
        </Section>
        <div className="pt-1 text-[10px] text-txt-dim">
          Motif de déclassement : coupe l’Analyse LABUSE pour explorer les écartées (jamais masquées) ·
          potentiel solaire APER : M45 v1.1.
        </div>
      </Tiroir>

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

      <button onClick={resetTout}
        title="Efface les DEUX étages et éteint l'interrupteur — retour à l'état vierge."
        className="mt-3 min-h-8 w-full rounded-lg border border-line-2 py-1.5 text-[11px] text-txt-dim transition-colors duration-quick hover:border-st-ecartee/50 hover:text-txt">
        Réinitialiser — terrain, analyse &amp; interrupteur
      </button>
    </div>
  )
}
