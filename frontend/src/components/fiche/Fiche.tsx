import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Tip } from '../Tip'
import { createContext, isValidElement, useContext, useEffect, useMemo, useState, useRef, type ReactNode } from 'react'
import { addToPipeline, ajouterParcelle, ApiError, faisabiliteExplain, getCalculetteDefaults, getDossierStatut, getExplain, getFaisabilite, getFiche, getModeB, getMoi, getOrthoEquipements, getPipelineForParcel, getProjets, getWatch, is429, onePagerUrl, pdfUrl, postChargeFonciere, postSignalement, preDossierUrl, projetsPourParcelle, toggleWatch, type CalculetteDefaults } from '../../lib/api'
import { verdictMeta } from '../../lib/status'
import { fmtDateNum, fmtEurCompact, fmtInt, fmtM2, fmtLibelleBrut, iduComplet } from '../../lib/format'
import { layerLabel } from '../../lib/layers'
import { CLIENT } from '../../lib/strings'
import { Loading } from '../Loading'
import { ErrorState } from '../States'
import { AskBar, renderRich } from './AskBar'
import { AvisIA } from '../AvisIA'
import { PourquoiPasTab } from './PourquoiPas'
import { ScoreV2Block } from './ScoreV2Block'
import { ViabilisationBlock } from './ViabilisationBlock'
import { PermitsProximityBlock } from './PermitsProximityBlock'
import { DepotsBlock } from './DepotsBlock'
import { GestionnairesBlock } from './GestionnairesBlock'
import type { FicheLine, IcdBlock, Onglet, PotentielTransformation, ReglementPlu } from '../../lib/types'
import { useApp } from '../../store/useApp'

const SEV_COLOR: Record<string, string> = { fort: '#E8695A', moyen: '#E8B44C', faible: '#C9DCD1', info: '#8FA69A' }


// ═══════════════════════════════════════════════════════════════════════════
// M19 · RÉFÉRENCE VISUELLE (qa/m19/reference/REFERENCE_FICHE_PARCELLE.html) — hex/tailles/espacements
// repris À L'IDENTIQUE de la spec Vic. Ce sont les seules couleurs en dur autorisées (spec).
// M56-B — table repointée sur les tokens DA v3 (:root, styles/index.css). Les valeurs de
// CHROME (surfaces, filets, texte, iris) passent par var(--…) : une valeur = un endroit.
// Les valeurs de SÉMANTIQUE DE VALEUR (gris/ok/creuser/ecartee) restent les tokens de statut
// Tailwind — elles miroir la palette des tiers, LIÉE aux couches de la carte (intouchable).
const REF = {
  bg: 'var(--bg-0)', shell: 'var(--line-2)',
  card: 'var(--bg-2)', cardBorder: 'var(--line-card)', accent: 'var(--iris-bg)', accentBorder: 'var(--iris-line)',
  name: 'var(--txt-hi)', mint: 'var(--mint)', violet: 'var(--iris-2)', dim: 'var(--txt-off)', dim2: 'var(--lab)',
  chev: 'var(--txt-faint)', chevAccent: 'var(--txt-faint)', barTrack: 'var(--line)', barFill: 'var(--mint)', seg: 'var(--mint-bg)',
  pastilleTxt: 'var(--iris)', pastilleBg: 'var(--iris-bg)',
  // M55-O phase 3.5 — sémantique de valeur (le vert redevient un signal) : gris=factuel neutre,
  // ok=vert état positif confirmé, creuser=ambre attention, ecartee=rouge blocage. = tokens statut.
  gris: '#8FA69A', ok: '#5CE6A1', creuser: '#E8B44C', ecartee: '#E8695A',
} as const

// M-RENOUV : CUIVRE du segment Renouvellement (aligné TOKENS.renouv, lib/tokens.ts) — teinte
// propre, ni le vert des statuts ni le violet signal. Doctrine : « potentiel de renouvellement
// urbain », jamais « opportunité ».
const RENOUV = { txt: '#d99a63', bg: '#291d12', border: '#4a3520', bar: '#C9834E' } as const

const RENOUV_CODE_LABEL: Record<string, string> = {
  deja_bati: 'déjà bâtie',
  deja_bati_probable: 'déjà bâtie (probable)',
  ensemble_bati: 'ensemble bâti',
}

const drSvg = (path: ReactNode, size = 17) =>
  <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>{path}</svg>

// icônes de la référence (mêmes tracés)
const IC = {
  regles: drSvg(<><path d="M7 20h10" /><path d="M6 6l6-1l6 1" /><path d="M12 3v17" /><path d="M9 12 6 6l-3 6a3 3 0 0 0 6 0" /><path d="M21 12l-3-6l-3 6a3 3 0 0 0 6 0" /></>),
  risques: drSvg(<><path d="M12 3l7 4v5c0 4-3 7.5-7 9c-4-1.5-7-5-7-9V7z" /><path d="m9 12 2 2 4-4" /></>),
  proprio: drSvg(<><circle cx="12" cy="8" r="3.5" /><path d="M5 20a7 7 0 0 1 14 0" /></>),
  marche: drSvg(<><path d="m3 17 6-6 4 4 8-8" /><path d="M14 7h7v7" /></>),
  faisa: drSvg(<><path d="M3 21h18" /><path d="M5 21V8l7-5 7 5v13" /><path d="M9 21v-5h6v5" /></>),
  viab: drSvg(<><path d="M12 3v6" /><path d="M8 9h8l-1 5a3 3 0 0 1-6 0z" /><path d="M12 17v4" /></>),
  confiance: drSvg(<><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /><path d="M9 13h6" /><path d="M9 17h4" /></>),
  contexte: drSvg(<><circle cx="12" cy="10" r="3" /><path d="M12 21c-4-4-7-7.5-7-11a7 7 0 0 1 14 0c0 3.5-3 7-7 11z" /></>),
}

// M55-L point 6 : `TheatreCompteur` (« N parcelles analysées ») retiré de la fiche → 0-caller,
// fonction supprimée. Le champ back `parc_analysees` reste servi (autres usages / PDF).

// M55-L point 10 — ACCORDÉON EXCLUSIF des tiroirs de la fiche : un seul ouvert à la fois, zéro
// ouvert légal (initial). État à champ unique (store.ficheTiroir[idu]), exposé par contexte pour
// éviter le prop-drilling sur les 11 tiroirs. `openId` = id du tiroir ouvert (null = tout fermé).
const FicheAccordionCtx = createContext<{ openId: string | null; toggle: (id: string) => void }>({ openId: null, toggle: () => {} })

/** M56-B2 · tiroir de la fiche — GABARIT STRICT de la DA §4/4b (docs/DA-LABUSE.html) : la rangée
 *  fermée EST une `.gr` (colonne gauche `.gr-t` titre + `.gr-s` UNE ligne de contexte grise ;
 *  colonne droite `.gr-v` valeur neutre OU `.pill` de statut, puis `.chev`). Le filet --line entre
 *  rangées vient du wrapper (l'en-tête n'a de filet qu'à l'état OUVERT, pour séparer de son corps).
 *  Le `micro` riche (jauge, sparkline, segments) ne vit PLUS sur la rangée fermée : il descend EN
 *  TÊTE du tiroir ouvert (règle §4 : une seule ligne de contexte sur la rangée fermée).
 *  `value` : chaîne → enveloppée en `.gr-v` ; élément React (une `.pill`) → rendu tel quel.
 *  `icon` ignoré (gardé au type pour ne pas toucher les call-sites). */
function RefDrawer({ id, name, context, value, valueColor, accent, icon, micro, children }: {
  id?: string; icon?: ReactNode; name: string; context?: ReactNode; value?: ReactNode; valueColor?: string
  accent?: boolean; micro?: ReactNode; children?: ReactNode
}) {
  const acc = useContext(FicheAccordionCtx)
  const open = !!id && acc.openId === id
  const absent = valueColor === 'var(--txt-faint)'
  // M57-P1 (a) : à l'ouverture, l'en-tête du tiroir remonte en HAUT de la zone visible — après
  // l'animation d'ouverture (~200ms), en 'smooth' ; 'auto' (immédiat) si l'OS demande moins de
  // mouvement. Vaut pour les 7 tiroirs (comportement porté par RefDrawer). scrollMarginTop garde 8px.
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open || !ref.current) return
    const reduced = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    const t = setTimeout(() => ref.current?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' }), reduced ? 0 : 220)
    return () => clearTimeout(t)
  }, [open])
  return (
    <div ref={ref} data-drawer={id} style={{ scrollMarginTop: 8 }}>
      {/* M56-B6 · DA-FICHE-v6 — le tiroir est une CARTE AUTONOME : pastille d'icône 32×32 à
          gauche, corps (titre + sous-titre une ligne), valeur/pastille + chevron à droite.
          Ouvert : la carte s'ouvre (coins bas carrés) et .t-open prolonge la carte. */}
      <button className={`tiroir${open ? ' is-open' : ''}`} onClick={() => id && children && acc.toggle(id)} aria-expanded={open}
        style={children ? undefined : { cursor: 'default' }}>
        <div className="t-ico">{icon}</div>
        <div className="t-body">
          <div className="t-title" style={accent ? { color: 'var(--iris-2)' } : undefined}>{name}</div>
          {context != null && <div className="t-sub">{context}</div>}
        </div>
        <div className="t-right">
          {/* jamais une colonne droite VIDE : valeur, pastille, ou « — » (--txt-faint). */}
          {value != null
            ? (isValidElement(value)
              ? value
              : <span className={`t-val${absent ? ' absent' : ''}`} style={!absent && valueColor ? { color: valueColor } : undefined}>{value}</span>)
            : <span className="t-val absent">—</span>}
          {children && <span className="chev">{open ? '⌃' : '›'}</span>}
        </div>
      </button>
      {/* L'intérieur reste plat : paires libellé-valeur (children). Le micro riche (jauge/
          sparkline/segments) descend EN TÊTE du tiroir ouvert, jamais sur la carte fermée. */}
      {open && (children || micro) && (
        <div className="t-open">
          {micro && <div style={{ marginBottom: children ? 12 : 0, paddingTop: 12 }}>{micro}</div>}
          {children && <div style={micro ? undefined : { paddingTop: 12 }}>{children}</div>}
        </div>
      )}
    </div>
  )
}

// M56-B6 · DA-FICHE-v6 — libellé de groupe (LE TERRAIN / LE CONTEXTE) : plus de conteneur,
// juste un TEXTE + un FILET horizontal (.sec). `first` retiré (l'écart .sec est fixe : 20px avant).
const GroupLabel = ({ children }: { children: ReactNode; first?: boolean }) => (
  <div className="sec"><span>{children}</span><i /></div>
)

// micro-preuves (spec) ──────────────────────────────────────────────────────
// M55-N point 6 : `tip` optionnel — la jauge DIT ce qu'elle mesure (au survol). Sans tip, une
// barre nue (fill %) ne disait ni ce qu'elle mesure ni sur quelle échelle (constat Règles).
const MicroJauge = ({ pct, label, tip }: { pct: number; label: string; tip?: string }) => {
  const body = (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{ flex: 1, height: 4, background: REF.barTrack, borderRadius: 2, overflow: 'hidden' }}>
        <div style={{ width: `${Math.max(0, Math.min(100, pct))}%`, height: 4, background: REF.barFill }} />
      </div>
      <span style={{ fontSize: 11, color: REF.dim, whiteSpace: 'nowrap', ...(tip ? { cursor: 'help', borderBottom: '1px dotted #5f7568' } : {}) }}>{label}</span>
    </div>
  )
  return tip ? <Tip tip={tip}>{body}</Tip> : body
}
const MicroSegments = ({ n, label }: { n: number; label: string }) => (
  <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
    <span style={{ fontSize: 11, color: REF.dim, marginRight: 2, whiteSpace: 'nowrap' }}>{label}</span>
    {Array.from({ length: Math.max(1, Math.min(12, n)) }).map((_, i) => (
      <span key={i} style={{ flex: 1, height: 4, background: REF.seg, borderRadius: 2 }} />
    ))}
  </div>
)
const MicroSpark = ({ label }: { label: string }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
    <svg width="72" height="20" viewBox="0 0 72 20" style={{ flexShrink: 0 }}><polyline points="2,17 14,14 26,15 38,10 50,7 70,3" fill="none" stroke={REF.barFill} strokeWidth="1.6" /></svg>
    <span style={{ fontSize: 11, color: REF.dim }}>{label}</span>
  </div>
)
// M56-B2 · DA §3 — les signaux propriétaire sont des PASTILLES standard p-amber (attention),
// jamais des puces violettes locales.
const MicroPastilles = ({ items }: { items: string[] }) => (
  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
    {items.map((t, i) => <span key={i} className="pill-amber">{t}</span>)}
  </div>
)
const MicroTriple = ({ items }: { items: ReactNode[] }) => (
  <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap' }}>
    {items.map((it, i) => <span key={i} style={{ fontSize: 11, color: REF.dim }}>{it}</span>)}
  </div>
)

/** 429 (rate-limit / quota) : message dédié + nouvel essai automatique après la fenêtre.
 *  Ne JAMAIS afficher « serveur périmé » ici — le serveur va très bien, il protège. */
function RateLimit429({ error, refetch }: { error: unknown; refetch: () => void }) {
  useEffect(() => {
    const t = setTimeout(() => refetch(), 65_000)   // fenêtre de rate-limit = 60 s
    return () => clearTimeout(t)
  }, [refetch])
  const detail = error instanceof ApiError ? error.detail : undefined
  return (
    <div data-ratelimit-429 className="rounded-lg border border-line-2 bg-surface-2 p-4 text-xs">
      <p className="text-txt-hi">Trop de requêtes — réessayez dans une minute.</p>
      {detail && <p className="mt-1 text-txt-dim">{detail}</p>}
      <p className="mt-1 text-txt-dim">Nouvel essai automatique dans ~1 min.</p>
      <button onClick={() => refetch()} className="mt-2 min-h-7 rounded border border-line-2 px-2 py-1 text-txt transition-colors duration-quick hover:border-mint/60 hover:text-txt-hi">Réessayer maintenant</button>
    </div>
  )
}

function Weight({ w, result }: { w: number | null; result: string }) {
  if (w == null) {
    return <span className="w-10 shrink-0 text-right font-mono text-[11px] text-txt-dim">{result === 'UNKNOWN' ? '?' : '·'}</span>
  }
  const c = w > 0 ? 'text-st-chaude' : w < 0 ? 'text-st-ecartee' : 'text-txt-dim'
  return <span className={`w-10 shrink-0 text-right font-mono text-xs font-semibold ${c}`}>{w > 0 ? `+${w}` : w}</span>
}

// Source cliquable → DRAWER latéral (jamais un cul-de-sac : la fiche reste ouverte) + référence + date.
function SourceRef({ line }: { line: FicheLine }) {
  const openSourceDrawer = useApp((s) => s.openSourceDrawer)
  const trace = line.source_table && line.source_id != null ? `${line.source_table}#${line.source_id}` : null
  return (
    <div className="mt-0.5 flex items-center gap-2 text-[11px] text-txt-dim">
      {line.source && (
        <button onClick={() => openSourceDrawer(line)} className="truncate text-txt-dim transition-colors duration-quick hover:text-mint hover:underline"
          title="Voir la source (drawer)">
          {line.source}
        </button>
      )}
      {trace && <span className="shrink-0 font-mono text-txt-dim/70">{trace}</span>}
      {line.date && <span className="ml-auto shrink-0 font-mono tnum">{fmtDateNum(line.date)}</span>}
    </div>
  )
}

// M57-P1 (Q4) : `hideWeight` — masque les points signés (line.weight) de l'AFFICHAGE. Le fait,
// la source et la date restent. Utilisé dans le tiroir Urbanisme : les points dévoilaient le
// score avant la demande de verdict (doctrine M55-L) et faisaient doublon de rôle avec « Pourquoi
// ce score ». La donnée en base et le calcul sont intacts.
function Line({ line, hideWeight }: { line: FicheLine; hideWeight?: boolean }) {
  return (
    <div className="flex gap-3 border-b border-line/60 py-2 last:border-0">
      {!hideWeight && <Weight w={line.weight} result={line.result} />}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          {/* S03-S05 : libellé français à l'écran, clé technique de la couche au survol/tap (audit) */}
          <Tip tip={<span className="font-mono">couche {line.layer}</span>}>
            <span className="text-xs font-medium text-txt">{layerLabel(line.layer)}</span>
          </Tip>
          {line.severity && line.weight == null && (
            <span className="rounded-full px-1.5 text-[9px]" style={{ background: `${SEV_COLOR[line.severity]}22`, color: SEV_COLOR[line.severity] }}>
              {line.severity}
            </span>
          )}
          {line.result === 'UNKNOWN' && <span className="text-[9px] text-txt-dim">inconnu</span>}
        </div>
        <div className="text-[11px] leading-snug text-txt-mut">{fmtLibelleBrut(line.detail)}</div>
        <SourceRef line={line} />
      </div>
    </div>
  )
}

// Barre de sous-score dépliable (exigence #2 : DEUX barres, Q et A, vers leurs lignes tracées).
// Item 7 (UX V1) : `tip` = la définition du score au survol (Q et A ne restent jamais des sigles).
// M55-O phase 2.2 : composant ScoreBar retiré (0-caller après retrait des jauges Qualité/Accessibilité).

// M55-O phase 2.1b — « Vérifications d'éligibilité — ✓ N passées ». Les contrôles de cascade PASS
// (emprise, surface vs seuil de valorisation, bâti probable…) qui NOYAIENT le tiroir Urbanisme
// deviennent UNE ligne de synthèse dépliable dans le bloc Analyse. Repliés par défaut. Aucune
// donnée nouvelle : ce sont les mêmes lignes `result==='PASS'` (preuve de rigueur, pas un mur).
function EligibiliteReplie({ lines, color }: { lines: FicheLine[]; color: string }) {
  const passes = lines.filter((l) => l.result === 'PASS')
  if (passes.length === 0) return null
  return (
    <details data-eligibilite style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${color}33` }}>
      <summary style={{ cursor: 'pointer', fontSize: 12, fontWeight: 600, color: 'var(--lab)', listStyle: 'none' }}>
        Vérifications d'éligibilité — <span style={{ color: '#5CE6A1' }}>✓ {passes.length} passées</span>
      </summary>
      <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 2 }}>
        {passes.map((l, i) => <Line key={i} line={l} />)}
      </div>
    </details>
  )
}

// ALGO-1 item 2 — le bloc « Signaux vendeur » (Score V agrégé 0-100 + bandes) est RETIRÉ de l'affichage : le backtest M3.6 le mesure CONTRE-prédictif pour la mutation (RR@1158 = 0,51 < 1, SCORING_SPEC §7-D). Le CALCUL reste en base (parcel_v_score, backtest) ; les signaux propriétaires FACTUELS restent servis par le tiroir Propriétaire (lines cascade), les chips verdict et le filtre « signaux propriétaire » du Header.
const ICD_COLORS: Record<string, string> = { haute: '#4ADE96', partielle: '#9AA6A0', faible: '#F5A524', inconnu: '#9AA6A0' }
const icdColor = (b: string) => ICD_COLORS[b] ?? '#9AA6A0'

function IcdBlockView({ icd }: { icd: IcdBlock }) {
  const [open, setOpen] = useState(false)
  const color = icdColor(icd.bande)
  return (
    <div data-icd className="card-elev">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-3 px-3 py-2.5"
        title="Confiance données : déplier le détail">
        <Tip tip="Complétude des couches de données pour cette parcelle — n'entre pas dans le score d'opportunité (P, calculé indépendamment)." className="w-24 shrink-0">
          <span className="text-left text-xs text-txt underline decoration-dotted decoration-line-2 underline-offset-4">Confiance données</span>
        </Tip>
        <span className="relative h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-line">
          <span className="absolute left-0 top-0 h-full rounded-full" style={{ width: `${icd.score}%`, background: color }} />
        </span>
        <span data-icd-score className="w-8 shrink-0 text-right font-display text-sm font-bold tnum" style={{ color }}>{icd.score}</span>
        <span className="shrink-0 text-txt-dim">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="border-t border-line-2 px-3 py-2">
          <span className="rounded-full px-1.5 py-0.5 text-[9px] font-medium" style={{ background: `${color}1f`, color }}>{icd.libelle}</span>
          {icd.manquants.length > 0 ? (
            <>
              <p className="label-caps mt-2 pb-1">Ce qui manque</p>
              <ul data-icd-manquants className="flex flex-col gap-0.5">
                {icd.manquants.map((m, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-[11px] text-txt-mut"><span className="text-st-ecartee">•</span>{m}</li>
                ))}
              </ul>
            </>
          ) : <p className="mt-2 text-[11px] text-txt-dim">Toutes les couches de données sont présentes pour cette parcelle.</p>}
          <p className="mt-2 text-[10px] leading-snug text-txt-dim">{icd.cloisonnement}</p>
        </div>
      )}
    </div>
  )
}

// ── M9 lot 4 — Potentiel de transformation (fond de l'ancien outil Mutabilité) ──
const PT_COLORS: Record<string, string> = { fort: '#4ADE96', modere: '#F5C244', faible: '#9AA6A0', nul: '#6B7280', indetermine: '#6B7280' }
function PtRow({ k, v }: { k: string; v: string }) {
  return (<div className="flex justify-between gap-3"><span className="text-txt-dim">{k}</span><span className="text-right text-txt">{v}</span></div>)
}
function TransformationBlock({ pt }: { pt: PotentielTransformation }) {
  const color = PT_COLORS[pt.niveau] ?? '#9AA6A0'
  return (
    <div data-transformation className="card-elev px-3 py-2.5">
      <div className="flex items-center gap-2">
        <span className="text-xs text-txt">Potentiel de transformation</span>
        <span className="ml-auto rounded-full px-2 py-0.5 text-[10.5px] font-medium capitalize" style={{ background: `${color}22`, color }}>{pt.niveau}</span>
      </div>
      <p className="mt-1 text-[11px] leading-snug text-txt-mut">{pt.libelle}</p>
      <div className="mt-1.5 flex flex-col gap-0.5 text-[11px]">
        {pt.pct_consomme != null && <PtRow k="SDP consommée / autorisée" v={`${pt.pct_consomme} %`} />}
        {pt.sdp_residuelle_m2 != null && pt.sdp_residuelle_m2 > 0 && <PtRow k="SDP résiduelle estimée" v={`~${fmtInt(pt.sdp_residuelle_m2)} m²`} />}
        {pt.surelevation_possible != null && <PtRow k="Surélévation" v={pt.surelevation_possible ? `possible${pt.hauteur_marge_m != null ? ` (marge ~${pt.hauteur_marge_m} m)` : ''}` : 'non'} />}
      </div>
      <p className="mt-1.5 text-[10px] leading-snug text-txt-dim">{pt.source}</p>
    </div>
  )
}

// ── M9 lot 2 — Lien règlement PLU par zone ──────────────────────────────────
function ReglementPluBlock({ rp }: { rp: ReglementPlu }) {
  const setModule = useApp((s) => s.setModule)
  const setPluPrefill = useApp((s) => s.setPluPrefill)
  // M62-P1 (j) : la phrase d'explication (`note`) était répétée par zone alors qu'elle est
  // identique pour les deux → une seule fois, en gris, sous les lignes. Si les notes diffèrent,
  // on reste par zone (repli honnête).
  const notes = rp.zones.map((z) => z.note).filter(Boolean) as string[]
  const noteCommune = notes.length === rp.zones.length && notes.every((n) => n === notes[0]) ? notes[0] : null
  return (
    <div data-reglement-plu className="card-elev px-3 py-2.5">
      <p className="label-caps">Règlement PLU</p>
      {/* M62-P1 (j) : tout aligné à gauche, UNE ligne par zone — pastille + zone + liens
          (Voir l'article ↗ · Annuaire PLU →) sur la même ligne ; la phrase d'explication dessous,
          en gris, une seule fois si elle est identique pour les deux zones. */}
      <div className="mt-1.5 flex flex-col gap-1.5">
        {rp.zones.map((z, i) => (
          <div key={i}>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-left">
              <span className="rounded-md bg-surface-3 px-1.5 py-0.5 font-mono text-[11px] text-txt">{z.zone}</span>
              {z.url && <a data-plu-link href={z.url} target="_blank" rel="noreferrer" className="text-[11px] text-mint hover:underline">
                {z.calibree ? 'Voir l’article' : 'Voir le règlement'} ↗
              </a>}
              {z.annuaire?.insee && (
                <button data-plu-annuaire-link
                  onClick={() => { setPluPrefill({ insee: z.annuaire!.insee!, zone: z.annuaire!.zone ?? null }); setModule('plu-annuaire') }}
                  className="text-[11px] text-violet hover:underline">
                  Annuaire PLU →
                </button>
              )}
            </div>
            {z.articles.length > 0 && (
              <ul className="mt-1 flex flex-col gap-0.5">
                {z.articles.slice(0, 6).map((a, j) => (
                  <li key={j} className="text-[10.5px] text-txt-mut">
                    <a href={a.url ?? z.url ?? '#'} target="_blank" rel="noreferrer" className="hover:text-mint hover:underline" title={a.reference}>{a.reference}</a>
                  </li>
                ))}
              </ul>
            )}
            {/* note par zone UNIQUEMENT si elles diffèrent (sinon rendue une fois plus bas) */}
            {z.note && !noteCommune && <p className="mt-0.5 text-[10px] text-txt-dim">{z.note}</p>}
          </div>
        ))}
      </div>
      {noteCommune && <p className="mt-1.5 text-[10px] leading-snug text-txt-dim">{noteCommune}</p>}
      <p className="mt-1.5 text-[10px] leading-snug text-txt-dim">{rp.disclaimer}</p>
    </div>
  )
}

// ── M9 lot 3 — Signaler une erreur (file de QA humaine, aucune action automatique) ──
const SIGNALEMENT_TYPES: [string, string][] = [
  ['faux_positif', 'Faux positif (piscine, PV…)'], ['zonage', 'Zonage PLU'],
  ['bati', 'Bâti / occupation'], ['adresse', 'Adresse'], ['proprietaire', 'Propriétaire'],
  ['risque', 'Risque'], ['score', 'Score / verdict'], ['viabilisation', 'Viabilisation'], ['autre', 'Autre'],
]
function SignalerErreur({ idu }: { idu: string }) {
  const [open, setOpen] = useState(false)
  const [type, setType] = useState('faux_positif')
  const [champ, setChamp] = useState('')
  const [commentaire, setCommentaire] = useState('')
  const m = useMutation({ mutationFn: () => postSignalement({ idu, type_erreur: type, champ: champ || undefined, commentaire: commentaire || undefined }) })
  if (m.isSuccess) {
    return (
      <div data-signalement-ok className="card-elev px-3 py-2.5 text-[11px] text-txt-mut">
        ✓ Signalement enregistré (n°{m.data.id}) — merci. Il sera revu manuellement.
      </div>
    )
  }
  if (!open) {
    return (
      <button data-signaler-erreur onClick={() => setOpen(true)}
        className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] text-txt-mut hover:border-mint hover:text-mint">
        ⚑ Signaler une erreur
      </button>
    )
  }
  return (
    <div data-signalement-form className="card-elev px-3 py-2.5">
      <p className="label-caps">Signaler une erreur</p>
      <label className="mt-2 block text-[11px] text-txt-mut">Type d’erreur
        <select data-signalement-type value={type} onChange={(e) => setType(e.target.value)} className="mt-0.5 w-full rounded-md border border-line-2 bg-surface-3 px-2 py-1 text-xs text-txt">
          {SIGNALEMENT_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
      </label>
      <label className="mt-2 block text-[11px] text-txt-mut">Champ concerné (optionnel)
        <input value={champ} onChange={(e) => setChamp(e.target.value)} placeholder="ex. piscine, zonage, adresse"
          className="mt-0.5 w-full rounded-md border border-line-2 bg-surface-3 px-2 py-1 text-xs text-txt placeholder:text-txt-dim" />
      </label>
      <label className="mt-2 block text-[11px] text-txt-mut">Commentaire
        <textarea data-signalement-commentaire value={commentaire} onChange={(e) => setCommentaire(e.target.value)} rows={2} placeholder="Décrivez l’erreur constatée"
          className="mt-0.5 w-full rounded-md border border-line-2 bg-surface-3 px-2 py-1 text-xs text-txt placeholder:text-txt-dim" />
      </label>
      <div className="mt-2 flex items-center gap-2">
        <button data-signalement-submit onClick={() => m.mutate()} disabled={m.isPending}
          className="rounded-md bg-mint px-3 py-1 text-xs font-medium text-mint-ink disabled:opacity-50">
          {m.isPending ? 'Envoi…' : 'Envoyer'}
        </button>
        <button onClick={() => setOpen(false)} className="text-[11px] text-txt-mut hover:text-txt">Annuler</button>
        {m.isError && <span className="text-[11px] text-st-ecartee">Échec — réessayez.</span>}
      </div>
      <p className="mt-1.5 text-[10px] leading-snug text-txt-dim">Aucune modification automatique des données : votre signalement entre dans une file de vérification humaine.</p>
    </div>
  )
}


// M14 — suivi de cible : événements sur cette parcelle SANS l'entrer au pipeline.
function WatchButton({ idu }: { idu: string }) {
  const qc = useQueryClient()
  const w = useQuery({ queryKey: ['watch', idu], queryFn: () => getWatch(idu) })
  const t = useMutation({ mutationFn: () => toggleWatch(idu), onSuccess: () => qc.invalidateQueries({ queryKey: ['watch', idu] }) })
  const on = w.data?.watched
  // C4 · cloche = suivi ; style référence (31×31, vert actif quand suivie).
  return (
    <button onClick={() => t.mutate()} className="hbtn"
      style={on ? { background: 'var(--mint-bg)', borderColor: 'var(--mint)', color: 'var(--mint)' } : undefined}
      title={on ? CLIENT.fiche.suivreActif : CLIENT.fiche.suivre}>
      <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M10 5a2 2 0 1 1 4 0a7 7 0 0 1 4 6v3a4 4 0 0 0 2 3H4a4 4 0 0 0 2-3v-3a7 7 0 0 1 4-6" /><path d="M9 17v1a3 3 0 0 0 6 0v-1" /></svg>
    </button>
  )
}

// EXPRESS-01 · bouton « copier l'IDU » — copie la chaîne BRUTE 14 car. (sans espace),
// celle qu'on colle dans GPU/DVF/SIG. Style référence (bouton 31×31, retour visuel vert).
// M61 P5 — bouton « copier » discret, réutilisable (IDU + adresse). Libellés paramétrables.
function CopyIdu({ value, aria = 'Copier l’IDU', titre = 'Copier l’IDU (14 caractères, sans espace)', okTitre = 'IDU copié', dataAttr = 'idu' }: {
  value: string; aria?: string; titre?: string; okTitre?: string; dataAttr?: string
}) {
  const [ok, setOk] = useState(false)
  const copier = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setOk(true)
      setTimeout(() => setOk(false), 1400)
    } catch { /* presse-papier indisponible : on ne fait rien de destructeur */ }
  }
  return (
    <button onClick={copier} data-fiche-copy={dataAttr} aria-label={aria}
      style={{ border: 'none', background: 'none', padding: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', color: ok ? 'var(--mint)' : 'var(--txt-ghost)', cursor: 'pointer', flexShrink: 0 }}
      title={ok ? okTitre : titre}>
      {ok
        ? <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m5 12 5 5 9-11" /></svg>
        : <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V5a2 2 0 0 1 2-2h9" /></svg>}
    </button>
  )
}

// M55-L point 3 — l'icône « partager » (pack apporteur : lien public filigrané) a été RETIRÉE du
// header de la fiche (décision Vic). La fonction ShareButton et l'import createShare deviennent
// 0-caller côté front → retirés aussi (endpoint back /partners/share intact, revient au besoin).

function PipelineButton({ idu }: { idu: string }) {
  const qc = useQueryClient()
  const state = useQuery({ queryKey: ['pipeline-parcel', idu], queryFn: () => getPipelineForParcel(idu) })
  const add = useMutation({
    mutationFn: () => addToPipeline(idu),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pipeline-parcel', idu] })
      qc.invalidateQueries({ queryKey: ['pipeline'] })
    },
  })
  const inPipe = state.data?.in_pipeline
  return (
    <button
      onClick={() => !inPipe && add.mutate()}
      disabled={!!inPipe || add.isPending}
      aria-disabled={!!inPipe}
      className={`act whitespace-nowrap ${inPipe ? 'act-cmp cursor-default' : 'act-crm'}`}
      title={inPipe ? CLIENT.fiche.crmDedansTip : CLIENT.fiche.crmAjouterTip}
    >
      {add.isPending ? 'Ajout…' : inPipe ? CLIENT.fiche.crmDedans : CLIENT.fiche.crmAjouter}
    </button>
  )
}

/** F7 (M12) — rattacher la parcelle à un PROJET depuis la fiche. Voisin du « + Pipeline » mais
 *  distinct AU PREMIER COUP D'ŒIL : accent VIOLET (la couleur du copilote/projet dans toute l'app),
 *  quand Pipeline est en MENTHE (CRM prospection). La parcelle atterrit dans « À trier » (proposee).
 *  MULTI-PROJET AUTORISÉ : une parcelle peut nourrir plusieurs projets (dédup par projet côté
 *  serveur). Déjà rattachée → bouton actif (violet plein) + nom du/des projet(s) ; clic = ouvrir. */
function ProjetButton({ idu }: { idu: string }) {
  const qc = useQueryClient()
  const setOpenProjet = useApp((s) => s.setOpenProjet)
  const [open, setOpen] = useState(false)
  const attache = useQuery({ queryKey: ['projets-parcelle', idu], queryFn: () => projetsPourParcelle(idu) })
  const projetsQ = useQuery({ queryKey: ['projets'], queryFn: getProjets, enabled: open })
  const add = useMutation({
    mutationFn: (pid: number) => ajouterParcelle(pid, idu),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projets-parcelle', idu] })
      qc.invalidateQueries({ queryKey: ['projets'] })
      setOpen(false)
    },
  })
  const attaches = attache.data?.projets ?? []
  const dejaIds = new Set(attaches.map((p) => p.id))
  const inProjet = attaches.length > 0
  // liste des projets ACTIFS non archivés (candidats à l'ajout)
  const candidats = (projetsQ.data ?? []).filter((p) => p.statut === 'actif')
  // M15 C3 : le HAUT du menu ne montre QUE les projets où la parcelle PEUT être ajoutée
  // (elle n'y est pas encore) — tous cliquables, aucun grisé. Les projets où elle est déjà
  // rangée vivent UNIQUEMENT dans la section « Déjà dans » du bas (fin du doublon M14).
  const ajoutables = candidats.filter((p) => !dejaIds.has(p.id))

  return (
    <div className="relative flex-1">
      <button
        data-projet-fiche
        onClick={() => setOpen((o) => !o)}   // QA-59 : TOUJOURS le menu (multi-projet) — jamais de saut direct
        aria-expanded={open}
        className="act act-proj w-full whitespace-nowrap"
        style={inProjet ? { background: 'var(--iris)', color: 'var(--bg-0)', borderColor: 'transparent' } : undefined}
        title={inProjet
          ? `Dans ${attaches.length > 1 ? `${attaches.length} projets` : `le projet « ${attaches[0].nom} »`} — ouvrir / rattacher à un autre`
          : 'Rattacher cette parcelle à un projet (elle arrive dans « À trier »)'}
      >
        {inProjet
          ? (attaches.length > 1 ? `✓ ${attaches.length} projets` : `✓ ${attaches[0].nom}`)
          : '+ Projet'}
      </button>

      {open && (
        <div data-projet-fiche-menu className="floating absolute bottom-10 left-0 z-30 w-64 p-2 text-[11px]">
          {/* M-C/merge : le bloc « Ouvrir » de M13-E3 (en tête) est RETIRÉ — main (QA-59) sert déjà
              les projets rattachés en bas (« Déjà dans — ouvrir »), l'auto-merge les avait dupliqués. */}
          <p className="label-caps px-1 pb-1">Rattacher à un projet</p>
          {projetsQ.isLoading && <div className="px-1 py-2 text-txt-dim">Chargement…</div>}
          {!projetsQ.isLoading && ajoutables.length === 0 && (
            <p className="px-1 py-2 leading-snug text-txt-dim">
              {candidats.length === 0
                ? 'Aucun projet actif. Créez-en un depuis « Mes projets ».'
                : 'Cette parcelle est déjà dans tous vos projets actifs.'}
            </p>
          )}
          {/* M15 C3 : uniquement les projets où l'ajout est POSSIBLE — tous cliquables, aucun grisé
              (les projets déjà rattachés ne sont plus répétés ici, ils sont en bas). Le doublon
              interdit dans un même projet reste garanti côté backend (ON CONFLICT). */}
          <div className="max-h-56 space-y-0.5 overflow-y-auto">
            {ajoutables.map((p) => (
              <button key={p.id} data-projet-fiche-cible disabled={add.isPending}
                onClick={() => add.mutate(p.id)}
                className="flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-txt transition-colors duration-quick hover:bg-violet/10 hover:text-txt-hi"
                title={`Ajouter à « ${p.nom} » (→ À trier)`}>
                <span className="min-w-0 flex-1 truncate">{p.nom}</span>
                <span className="shrink-0 text-violet">+</span>
              </button>
            ))}
          </div>
          {/* Ouvrir un projet où la parcelle est déjà rangée (l'action « ouvrir » n'est plus sur le
              bouton principal, qui ouvre désormais toujours ce menu). */}
          {attaches.length > 0 && (
            <div className="mt-1 border-t border-line/40 pt-1">
              <p className="label-caps px-1 pb-0.5 text-txt-dim">Déjà dans — ouvrir</p>
              {attaches.map((p) => (
                <button key={`open-${p.id}`} data-projet-fiche-ouvrir
                  onClick={() => { setOpenProjet({ id: p.id, nom: p.nom }); setOpen(false) }}
                  className="flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-violet transition-colors duration-quick hover:bg-violet/10"
                  title={`Ouvrir « ${p.nom} »`}>
                  <span className="min-w-0 flex-1 truncate">{p.nom}</span>
                  <span className="shrink-0">→</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// M-Q P2-73 — un SEUL formateur de montants dans l'app (LOI-3). L'ancien `fmtEurCompact()` local (seuil
// k€ à 1 000) divergeait de `fmtEurCompact` (seuil k€ à 10 000) : 5 000 € s'affichait « 5 k€ »
// en fiche, « 5 000 € » au copilote. On bascule sur `fmtEurCompact` (format.ts) — même dessin
// partout. Le copilote l'utilisait déjà correctement.

/** Champ éditable d'hypothèse promoteur — valeur SAISIE (jamais estimée par LABUSE). */
function HypInput({ label, value, onChange, suffix, hint, placeholder }: {
  label: string; value: number | null; onChange: (v: number | null) => void
  suffix: string; hint?: boolean; placeholder?: string
}) {
  return (
    <div className="min-w-0 flex-1">
      <label className="flex items-center gap-1 text-[11px] text-txt-dim">
        {label}
        {hint && <span className="rounded bg-st-creuser/10 px-1 text-[8.5px] text-st-creuser" title="Hypothèse — à ajuster selon votre opération">hyp. — ajustez</span>}
      </label>
      <div className="mt-1 flex items-center rounded-lg border border-line-2 bg-surface-3 focus-within:border-mint">
        <input type="number" min={0} value={value ?? ''} placeholder={placeholder}
          onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
          className="min-w-0 flex-1 bg-transparent px-2 py-1.5 text-xs text-txt placeholder:text-txt-dim focus:outline-none" />
        <span className="shrink-0 px-2 text-[11px] text-txt-dim">{suffix}</span>
      </div>
    </div>
  )
}

/** LA CALCULETTE DE CHARGE FONCIÈRE (mandat bilan-calculette). LABUSE affiche le SOURCÉ (SDP,
 *  prix DVF) ; le promoteur saisit SES hypothèses (coût, marge) ; le résultat « selon vos
 *  hypothèses » se recalcule côté moteur (endpoint déterministe, aucune arithmétique dupliquée
 *  en JS). Cas limites honnêtes : capacité non résolue / prix insuffisant → pas de faux chiffre.
 *
 *  M-Q P1-16 — les défauts (coût, marge) viennent du SERVEUR (getCalculetteDefaults, dérivé du
 *  YAML), plus d'une constante 2500 gravée ici qui divergeait du 2550 serveur (donc du PDF « Note
 *  de financement »). On seed les champs une fois les défauts connus : calculette et PDF portent le
 *  même coût par défaut sur la même parcelle. */
export function Calculette({ idu }: { idu: string }) {
  // M58-P1 (Q5) : `staleTime:Infinity` SANS retry laissait la calculette en « Chargement »
  // DÉFINITIF si /bilan/calculette-defaults échouait une fois. On ajoute un retry et surtout un
  // ÉTAT D'ERREUR explicite avec « Réessayer » (règle DA « les états parlent » — jamais de zone muette).
  const defs = useQuery({ queryKey: ['calculette-defaults'], queryFn: getCalculetteDefaults, staleTime: Infinity, retry: 2 })
  if (defs.isError) {
    return (
      <div data-calculette>
        <p className="label-caps mb-1">Calculette de charge foncière</p>
        <div data-calc-erreur className="card-elev px-3 py-2.5 text-[11px] text-txt">
          <p className="text-st-creuser">Chargement de la calculette impossible.</p>
          <button onClick={() => defs.refetch()} className="mt-2 min-h-7 rounded border border-line-2 px-2 py-1 text-txt transition-colors duration-quick hover:border-mint/60 hover:text-txt-hi">Réessayer</button>
        </div>
      </div>
    )
  }
  if (!defs.data) {
    return (
      <div data-calculette>
        <p className="label-caps mb-1">Calculette de charge foncière</p>
        <div className="card-elev px-3 py-2.5 text-[11px] text-txt"><Loading label="Chargement" /></div>
      </div>
    )
  }
  return <CalculetteBody idu={idu} defauts={defs.data} />
}

function CalculetteBody({ idu, defauts }: { idu: string; defauts: CalculetteDefaults }) {
  const [cout, setCout] = useState<number | null>(defauts.cout_construction_m2)
  const [marge, setMarge] = useState<number | null>(defauts.marge_frais_pct)
  const [prixDemande, setPrixDemande] = useState<number | null>(null)
  // M22-A : la même équation, deux lectures — charge supportable (historique) ou prix d'achat
  // max admissible (inverse). Le moteur garantit l'identité des totaux (aucun calcul en JS).
  const [mode, setMode] = useState<'charge' | 'achat_max'>('charge')
  const [deb, setDeb] = useState({ cout: defauts.cout_construction_m2, marge: defauts.marge_frais_pct, prix: null as number | null })
  useEffect(() => {
    const t = setTimeout(() => setDeb({ cout: cout ?? defauts.cout_construction_m2, marge: marge ?? defauts.marge_frais_pct, prix: prixDemande }), 350)
    return () => clearTimeout(t)
  }, [cout, marge, prixDemande, defauts])
  const q = useQuery({
    queryKey: ['charge', idu, deb.cout, deb.marge, deb.prix, mode],
    queryFn: () => postChargeFonciere(idu, { cout_construction_m2: deb.cout, marge_frais_pct: deb.marge, prix_demande_eur: deb.prix, mode }),
    placeholderData: (prev) => prev,   // garde l'ancien résultat pendant le recalcul (pas de flash)
  })
  const d = q.data
  // A6 : partager les hypothèses courantes avec le bouton PDF (l'export les reflète)
  const setCalculette = useApp((s) => s.setCalculette)
  useEffect(() => {
    setCalculette(d?.calculable ? { cout_construction_m2: deb.cout, marge_frais_pct: deb.marge, prix_demande_eur: deb.prix } : null)
    return () => setCalculette(null)
  }, [d?.calculable, deb.cout, deb.marge, deb.prix, setCalculette])
  const cf = d?.charge_fonciere
  const achat = d?.achat
  return (
    <div data-calculette>
      <p className="label-caps mb-1 flex items-center gap-2">
        Calculette de charge foncière
        {q.isFetching && <span data-calc-recalc className="animate-pulse text-[9px] normal-case tracking-normal text-mint">recalcul…</span>}
      </p>
      <div className="card-elev px-3 py-2.5 text-[11px] leading-relaxed text-txt">
        {q.isLoading && <Loading label="Calcul en cours" />}
        {d && d.calculable === false && (
          <div data-calc-indispo>
            <p className="text-st-creuser">{d.message ?? 'Charge foncière non calculable.'}</p>
            {d.marche?.median != null && (
              <p className="mt-1 text-txt-mut">Au mieux — prix de sortie bâti secteur : <b className="tnum text-mint">{fmtInt(Number(d.marche.median))} €/m²</b> ({d.marche.fiabilite}).</p>
            )}
          </div>
        )}
        {d && d.calculable && cf && (
          <>
            {/* le SOURCÉ (lecture seule) — ce que LABUSE sait */}
            <p className="text-[11px] text-txt-dim">
              LABUSE (sourcé) : SDP vendable <b className="tnum text-txt">{fmtInt(Number(d.shab_vendable_m2))} m²</b> ·
              prix de sortie bâti <b className="tnum text-txt">{fmtInt(Number(d.prix_sortie_median))} €/m²</b> ·
              terrain <b className="tnum text-txt">{fmtInt(Number(d.terrain_m2))} m²</b>
            </p>
            {/* les HYPOTHÈSES — saisies par le promoteur */}
            <div className="mt-2 flex gap-2">
              <HypInput label="Coût construction" value={cout} onChange={setCout} suffix="€/m²" hint />
              <HypInput label="Marge & frais" value={marge} onChange={setMarge} suffix="%" hint />
            </div>
            {/* M22-A · BASCULE DE LECTURE — même équation, deux sens (discret, pas de refonte) */}
            <div className="mt-2 flex gap-1 rounded-lg border border-line-2 bg-surface-2 p-1">
              {([['charge', 'Charge supportable'], ['achat_max', "Prix d'achat max"]] as const).map(([m, l]) => (
                <button key={m} data-calc-mode={m} onClick={() => setMode(m)}
                  className={`flex-1 rounded-md py-1 text-[11px] font-medium transition-colors duration-quick ${mode === m ? 'bg-mint text-bg' : 'text-txt-mut hover:text-txt'}`}>
                  {l}
                </button>
              ))}
            </div>
            {/* le RÉSULTAT — calcul de VOS hypothèses (mêmes totaux dans les deux lectures) */}
            <div data-calc-resultat className="mt-2.5 rounded-lg border border-mint/40 bg-mint/[0.06] px-3 py-2">
              <p className="text-[11px] text-txt-dim">{mode === 'achat_max' ? "Prix d'achat maximal admissible" : 'Charge foncière supportable'} <span className="text-txt-mut">— selon vos hypothèses</span></p>
              <p className="mt-0.5">
                <b data-calc-cf className="num-key text-lg text-mint">{fmtEurCompact(cf.central)}</b>
                <span className="ml-1.5 text-[11px] text-txt-mut">≈ {fmtInt(Number(cf.par_m2_terrain))} €/m² de terrain</span>
              </p>
              {/* M36 Lot C (Q2) : bornes identiques à l'affichage → valeur unique « ~X » */}
              <p className="text-[11px] text-txt-dim">{fmtEurCompact(cf.bas) === fmtEurCompact(cf.haut) ? `~${fmtEurCompact(cf.bas)}` : `fourchette ${fmtEurCompact(cf.bas)} – ${fmtEurCompact(cf.haut)}`}{d.fiabilite === 'fragile' ? ' · prix de sortie fragile (ordre de grandeur)' : ''}</p>
              {mode === 'achat_max' && (
                <p className="mt-1 text-[9.5px] leading-snug text-txt-dim">
                  = ce que l'opération peut payer le terrain (CA × (1 − marge & frais) − construction − VRD le cas
                  échéant) — les trois scénarios suivent la fourchette de prix de sortie DVF (même équation que la
                  charge supportable, lue à l'envers).
                </p>
              )}
            </div>
            {/* aide à la DÉCISION D'ACHAT — prix demandé optionnel */}
            <div className="mt-2 flex items-end gap-2">
              <HypInput label="Prix demandé du terrain" value={prixDemande} onChange={setPrixDemande} suffix="€" placeholder="si connu" />
            </div>
            {mode === 'achat_max' && d.ecart_negociation && (
              <div data-calc-ecart className={`mt-2 rounded-lg px-3 py-2 text-[11px] font-medium ${d.ecart_negociation.sens === 'marge' ? 'bg-mint/10 text-mint' : 'bg-st-ecartee/10 text-st-ecartee'}`}>
                {d.ecart_negociation.sens === 'surcout'
                  ? <>Écart : prix demandé {fmtEurCompact(d.ecart_negociation.prix_demande_eur)} − prix d'achat max {fmtEurCompact(d.ecart_negociation.prix_achat_max_eur)} = <b>surcoût de {fmtEurCompact(d.ecart_negociation.demande_moins_max_eur)}</b> (+{Math.round(d.ecart_negociation.demande_moins_max_pct)} % au-dessus du max admissible).</>
                  : <>Écart : prix demandé {fmtEurCompact(d.ecart_negociation.prix_demande_eur)} est <b>sous votre prix d'achat max</b> ({fmtEurCompact(d.ecart_negociation.prix_achat_max_eur)}) — marge de {fmtEurCompact(Math.abs(d.ecart_negociation.demande_moins_max_eur))}.</>}
              </div>
            )}
            {/* M22-C : l'argumentaire PDF reprend LES MÊMES hypothèses que la calculette */}
            {mode === 'achat_max' && d.calculable && (
              <a data-argumentaire href={`/argumentaire/${idu}.pdf?cout_construction_m2=${deb.cout}&marge_frais_pct=${deb.marge}${deb.prix ? `&prix_demande_eur=${deb.prix}` : ''}`}
                target="_blank" rel="noreferrer"
                className="mt-1.5 inline-block text-[10.5px] text-txt-mut underline decoration-line-2 underline-offset-2 hover:text-mint">
                Éditer l'argumentaire de négociation (PDF)
              </a>
            )}
            {mode === 'charge' && achat && (
              <div data-calc-verdict className={`mt-2 rounded-lg px-3 py-2 text-[11px] font-medium ${achat.supportable ? 'bg-mint/10 text-mint' : 'bg-st-ecartee/10 text-st-ecartee'}`}>
                {achat.supportable
                  ? <>✓ Supportable — le terrain peut valoir {fmtEurCompact(achat.prix_demande_eur)} ; marge de {fmtEurCompact(achat.ecart_eur)} ({achat.ecart_pct > 0 ? '+' : ''}{Math.round(achat.ecart_pct)} %) sous votre charge foncière.</>
                  : <>✗ Trop cher — à {fmtEurCompact(achat.prix_demande_eur)}, l'opération dépasse de {fmtEurCompact(Math.abs(achat.ecart_eur))} ({Math.round(achat.ecart_pct)} %) ce que vos hypothèses supportent.</>}
              </div>
            )}
            {(d.avertissements ?? []).length > 0 && (
              <ul className="mt-1.5 list-inside list-disc text-[11px] text-st-creuser">
                {d.avertissements.map((a: string, i: number) => <li key={i}>{a}</li>)}
              </ul>
            )}
            <p className="mt-1.5 text-[9px] leading-snug text-txt-dim">
              Le coût de construction et la marge sont VOS hypothèses (LABUSE ne les estime pas). Le
              résultat empile 4 hypothèses (coût, marge, prix de sortie DVF, prix demandé) — les écarts
              sont arrondis au point de % (pas de fausse précision décimale). Estimation indicative, ne
              vaut pas conseil.
            </p>
          </>
        )}
      </div>
    </div>
  )
}

// Badges ÉQUIPEMENTS (mandat wave-ortho Lot 6) : piscine / PV / CES / pente — dans la
// synthèse, sourcés « ortho IGN 2025, fiabilité statistique, non contractuelle ».
function EquipementsBadges({ idu }: { idu: string }) {
  const { data: e } = useQuery({
    queryKey: ['equip', idu], queryFn: () => getOrthoEquipements(idu), retry: false,
  })
  if (!e) return null
  const b: [string, string, string][] = []
  if (e['piscine']) b.push([`Piscine ~${e['piscine_m2']} m²`, '#4fc3d9',
    `détection ortho — confiance ${e['piscine_confiance']}`])
  if (e['pv_detecte']) b.push([`PV détecté${e['pv_m2'] ? ` ~${e['pv_m2']} m²` : ''}`, '#5CE6A1', 'panneaux photovoltaïques (candidat scoré)'])
  if (e['pv_probable_ces']) b.push(['CES probable', '#e8b84d', 'chauffe-eau solaire probable (4-8 m²)'])
  if (e['pente_moy_deg'] != null) b.push([`Pente ${Math.round(Number(e['pente_non_batie_deg'] ?? e['pente_moy_deg']))}°`,
    e['flag_terrassement_lourd'] ? '#e8734d' : 'var(--lab)',
    `pente moyenne ${e['pente_non_batie_deg'] != null ? 'hors bâti ' : ''}(RGE ALTI 5 m)${e['flag_terrassement_lourd'] ? ' — terrassement lourd probable' : ''}`])
  if (!b.length) return null
  return (
    <div>
      <div className="flex flex-wrap gap-1.5">
        {b.map(([label, color, tip]) => (
          <Tip key={label} tip={tip}>
            <span className="rounded-full px-2 py-0.5 text-[11px] font-medium"
              style={{ background: `${color}22`, color }}>{label}</span>
          </Tip>
        ))}
      </div>
      <p className="mt-1 text-[9px] text-txt-dim">{String(e['source'] ?? '')}</p>
    </div>
  )
}

// EBC / ER (dette #10) — drapeaux d'INFORMATION dérivés des prescriptions PLU DÉJÀ calculées
// par la cascade (layer 'prescription_plu', libellés servis). Lecture seule : ne filtre, n'exclut
// ni ne pondère JAMAIS — le verdict et les scores restent ceux du run servi.
function prescriptionsInfo(lines: FicheLine[]): { ebc: { coverage: number | null } | null; ers: { num: string | null }[] } {
  let ebc: { coverage: number | null } | null = null
  const ers: { num: string | null }[] = []
  const vus = new Set<string>()
  for (const l of lines || []) {
    if (l.layer !== 'prescription_plu') continue
    const d = l.detail || ''
    if (d.startsWith('Espace boisé classé (EBC)')) {
      const m = d.match(/~\s*(\d+)\s*%/)
      const cov = m ? Number(m[1]) : null
      if (!ebc || (cov != null && (ebc.coverage == null || cov > ebc.coverage))) ebc = { coverage: cov }
    } else if (d.startsWith('Emplacement réservé')) {
      const m = d.match(/ER\s*n?°?\s*(\d+)/i) || d.match(/réservé\s*n?°?\s*(\d+)/i)
      const num = m ? m[1] : null
      const key = num ?? d.slice(0, 40)
      if (!vus.has(key)) { vus.add(key); ers.push({ num }) }
    }
  }
  return { ebc, ers }
}

function StepProv({ prov }: { prov?: string }) {
  const map: Record<string, [string, string]> = {
    sourcee: ['Sourcé', 'border-mint/40 bg-mint/10 text-mint'],
    estimee: ['Estimé', 'border-st-creuser/40 bg-st-creuser/10 text-st-creuser'],
    derive: ['Dérivé', 'border-line-2 bg-surface-2 text-txt-dim'],
  }
  const [label, cls] = map[prov ?? ''] ?? ['—', 'border-line-2 bg-surface-2 text-txt-dim']
  return <span className={`shrink-0 rounded-full border px-1.5 py-0.5 text-[9px] font-medium ${cls}`}>{label}</span>
}

/** M11 · SURFACE C — onglet FAISABILITÉ : le résultat, le calcul TRACÉ étape par étape (déterministe,
 *  exact, sourcé), l'explication IA À LA DEMANDE (violet premium, ancrée sur les steps), et la
 *  calculette de charge foncière rapatriée (financier au même endroit). L'IA explique, ne recalcule pas. */
export function FaisabiliteTab({ idu }: { idu: string }) {
  const { data: b, isLoading, isError, refetch } = useQuery({ queryKey: ['bilan', idu], queryFn: () => getFaisabilite(idu) })
  const [showSteps, setShowSteps] = useState(false)  // M58-P1 (h) : le calcul étape par étape est REPLIÉ par défaut
  const explain = useMutation({ mutationFn: () => faisabiliteExplain(idu) })
  if (isLoading) return <Loading label="Calcul de la pré-faisabilité" className="text-xs" />
  if (isError || !b) return <ErrorState message="Faisabilité indisponible." retry={() => refetch()} />

  const cap = b.capacite
  const fo = cap?.fourchette ?? {}
  const steps: { label: string; valeur: string; source: string; prov: string }[] = cap?.steps ?? []
  const ex = explain.data
  // M58-P1 (c) : « un zéro n'est pas une absence ». Capacité réelle = fourchette logements > 0.
  const logAuSol = Array.isArray(fo.logements_au_sol) ? fo.logements_au_sol : null
  const logMax = logAuSol ? Math.max(logAuSol[0] ?? 0, logAuSol[1] ?? 0) : null
  const capaciteReelle = logMax != null && logMax > 0
  return (
    <div className="flex flex-col gap-3">
      {/* ── LE RÉSULTAT (bloc capacité UNIQUE — M58-P1 b) ── */}
      {cap ? (
        <div className="rounded-lg border border-mint/40 bg-mint/[0.06] px-3 py-2.5">
          <p className="label-caps mb-1">Capacité constructible</p>
          <div className="text-sm font-medium text-txt-hi">{cap.verdict}</div>
          {/* M58-P1 (c) : jamais « 0–0 » / « ( m) » / « ~— » — on n'affiche la grille que si la
              capacité est réelle ; chaque champ retombe sur « — » plutôt qu'un zéro/vide trompeur. */}
          {capaciteReelle ? (
            <>
              <div className="mt-1.5 grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-txt-mut">
                <div>Gabarit : <b className="text-txt">{fo.niveaux && fo.hauteur_m != null ? `${fo.niveaux} (${fo.hauteur_m} m)` : '—'}</b></div>
                <div>SDP : <b className="text-txt">{fo.surface_plancher_m2 ? fmtM2(fo.surface_plancher_m2) : '—'}</b></div>
                <div>Logements : <b className="text-txt">{`${logAuSol![0]}–${logAuSol![1]}`}</b></div>
                <div>SHAB vendable : <b className="text-txt">{fo.shab_vendable_m2 ? `~${fmtM2(fo.shab_vendable_m2)}` : '—'}</b></div>
              </div>
              {/* M58-P1 (Q1) : lever l'apparente contradiction avant/après plafond. */}
              <div className="mt-1 text-[10.5px] text-txt-dim">La fourchette retenue est celle après plafond de densité.</div>
            </>
          ) : (
            <div className="mt-1.5 text-[11px] text-txt-faint">Capacité logements non calculable pour cette parcelle.</div>
          )}
          {!cap.calibree && <div className="mt-1 text-[11px] text-st-creuser">▲ estimation générique (zone non calibrée)</div>}
          <div className="mt-1.5 text-[10.5px] leading-snug text-txt-dim">{cap.bandeau}</div>
        </div>
      ) : (
        <div className="card-elev px-3 py-2 text-[11px] text-txt-mut">
          Zone PLU non résolue pour cette parcelle — capacité non calculable (honnête).
        </div>
      )}

      {/* ── LE CALCUL, ÉTAPE PAR ÉTAPE (déterministe) ── */}
      {steps.length > 0 && (
        <div>
          <button onClick={() => setShowSteps((s) => !s)} className="label-caps mb-1 flex w-full items-center justify-between transition-colors duration-quick hover:text-txt">
            <span>Le calcul, étape par étape ({steps.length})</span>
            <span>{showSteps ? '−' : '+'}</span>
          </button>
          {showSteps && (
            <ol data-faisa-steps className="card-elev overflow-hidden">
              {steps.map((s, i) => (
                <li key={i} className={`flex items-start gap-2 px-3 py-1.5 text-[11px] ${i % 2 ? 'bg-surface-2' : 'bg-surface-1'}`}>
                  <span className="shrink-0 font-mono text-[9px] text-txt-dim">{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-txt">{s.label}</span>
                      <b className="shrink-0 text-txt-hi">{s.valeur}</b>
                    </div>
                    <div className="mt-0.5 flex items-center gap-1.5">
                      <StepProv prov={s.prov} />
                      <span className="truncate text-[9.5px] text-txt-dim">{s.source}</span>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}

      {/* ── EXPLIQUER CE CALCUL EN CLAIR (IA, sur clic) — M58-P1 (e) : SEULEMENT s'il y a un
          calcul à expliquer (steps > 0). Sur une parcelle non calculable (0 step), pas de bouton. ── */}
      {cap && steps.length > 0 && (
        <div data-faisa-explain>
          {!ex && !explain.isPending && (
            <button onClick={() => explain.mutate()} data-faisa-explain-btn
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-violet/50 bg-violet/[0.07] py-2 text-[12px] font-medium text-violet hover:bg-violet/10">
              <svg viewBox="0 0 20 20" className="h-3.5 w-3.5"><path d="M10 3.5 L11.6 8.4 L16.5 10 L11.6 11.6 L10 16.5 L8.4 11.6 L3.5 10 L8.4 8.4 Z" fill="currentColor" /></svg>
              Expliquer ce calcul en clair
            </button>
          )}
          {explain.isPending && <p className="flex items-center gap-2 py-2 text-[11px] text-violet"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet" /> L'IA lit les étapes du calcul…</p>}
          {explain.isError && <p className="py-1 text-[11px] text-st-ecartee">Explication indisponible — réessayez.</p>}
          {ex && ex.disponible === false && <p className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] text-txt-mut">{ex.message}</p>}
          {ex && ex.disponible && ex.rejected && <p className="rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2 text-[11px] text-st-creuser">{ex.texte}</p>}
          {ex && ex.disponible && !ex.rejected && (
            <div className="rounded-lg border border-violet/40 bg-violet/[0.07] px-3 py-2.5">
              <AvisIA className="mb-2 border-violet/25 bg-violet/[0.05] text-txt-mut" />
              <p className="mb-1 font-mono text-[10px] tracking-widest text-violet">✦ EXPLICATION IA — À PARTIR DES ÉTAPES</p>
              <p className="whitespace-pre-wrap text-[12px] leading-relaxed text-txt">{renderRich(ex.texte ?? '')}</p>
              <p className="mt-1.5 text-[9px] leading-snug text-txt-dim">L'IA narre les étapes ci-dessus (elle ne recalcule rien) ; chaque chiffre est ancré sur une étape. Estimation indicative, ne vaut pas conseil.</p>
            </div>
          )}
        </div>
      )}

      {/* ── CHARGE FONCIÈRE rapatriée (le financier au même endroit) ── */}
      <Calculette idu={idu} />
    </div>
  )
}

function BilanTab({ idu }: { idu: string }) {
  const { data: b, isLoading, isError, refetch } = useQuery({ queryKey: ['bilan', idu], queryFn: () => getFaisabilite(idu) })
  if (isLoading) return <Loading label="Calcul de la pré-faisabilité" className="text-xs" />
  if (isError || !b) return <ErrorState message="Bilan indisponible." retry={() => refetch()} />
  const Sec = ({ t, children }: { t: string; children: React.ReactNode }) => (
    <div>
      <p className="label-caps mb-1">{t}</p>
      <div className="card-elev px-3 py-2 text-[11px] leading-relaxed text-txt">{children}</div>
    </div>
  )
  return (
    <div className="flex flex-col gap-3">
      {/* M58-P1 (b) : le bloc « Capacité » vivait ICI ET dans FaisabiliteTab (même b.capacite) —
          DOUBLON supprimé. La capacité est rendue UNE seule fois, en tête de FaisabiliteTab.
          BilanTab ne porte plus que Marché → Fiscal → RTAA (ordre M58-P1 h). */}
      {b.marche?.median != null && (
        /* CRED-2 : cette médiane est un prix BÂTI (par type de bien) — la nommer, pour qu'elle
           coexiste lisiblement avec la « médiane terrain » de l'onglet Marché. */
        <Sec t="Marché — prix de sortie bâti (secteur)">
          médiane bâti <b className="tnum text-mint">{fmtInt(Number(b.marche.median))} €/m²</b> ({b.marche.type_prix},
          {' '}{b.marche.n} ventes ≤ {Math.round(b.marche.radius_m)} m, rayon adaptatif) · fiabilité <b>{b.marche.fiabilite}</b>
          {b.marche.tendance ? <span className="text-txt-mut"> · tendance {b.marche.tendance}</span> : null}
          {/* P14 / M32 §2 : fraîcheur DVF — l'HORIZON (de quand datent les prix) + le millésime amont,
              servis structurés dans `marche.fraicheur` (point de vérité data_sources). Repli sur le
              libellé P14 `dvf_couverture` si l'objet structuré n'est pas encore servi. */}
          {(b.marche.fraicheur?.horizon_libelle || b.marche.dvf_couverture?.libelle) && (
            <div className="mt-1 text-[11px] text-txt-dim">
              DVF — {b.marche.fraicheur?.horizon_libelle ?? b.marche.dvf_couverture?.libelle}
              {b.marche.fraicheur?.millesime ? ` · ${b.marche.fraicheur.millesime}` : ' (dernière transaction en base · millésime en vigueur)'}
            </div>
          )}
        </Sec>
      )}
      {/* M58-P1 : note « la charge foncière est dans Faisabilité » RETIRÉE — elle pointait vers la
          calculette rendue juste au-dessus (FaisabiliteTab), dans le MÊME tiroir : redondante. */}
      <Sec t="Fiscal & leviers">
        <div>QPV : <b className={b.fiscal.qpv ? 'text-mint' : 'text-txt-mut'}>{b.fiscal.qpv ? 'OUI' : 'non'}</b> · TVA : {b.fiscal.tva}</div>
        <div className="mt-1 text-[11px] text-txt-dim">{b.fiscal.ta_note}</div>
      </Sec>
      {b.rtaa && <RtaaBlock rtaa={b.rtaa} />}
    </div>
  )
}

/** RTAA DOM (mandat 5bis) — rappel réglementaire de CONCEPTION, vérifié Légifrance
 *  (config/rtaa_dom.yaml). Les seuils d'altitude (400/600 m) sont énoncés dans chaque
 *  exigence — l'altitude de la parcelle n'est pas calculée ici (consigné). */
/** M33 — MODE B (réhabilitation) : lecture COMPLÉMENTAIRE, visuellement subordonnée au tier
 *  (M34 intact). TOUJOURS Estimé (le paramètre travaux l'est) — assumé au libellé. Le
 *  paramètre est un état d'UI : rien n'est persisté (recalcul via /parcels/{idu}/mode-b). */
function ModeBDrawer({ idu, initial }: { idu: string; initial: import('../../lib/types').ModeB }) {   // M55-L point 10 : defaultOpen retiré (accordéon contrôlé, initial fermé)
  // M45-B (L2) : le coût travaux est une VALEUR DE SESSION PARTAGÉE (fiche ↔ filtre) — le curseur
  // du tiroir Économie et cette fiche lisent/écrivent le même `modeB.travauxM2` (rien persisté).
  const travaux = useApp((s) => s.modeB.travauxM2)
  const setModeB = useApp((s) => s.setModeB)
  const q = useQuery({
    queryKey: ['mode-b', idu, travaux],
    queryFn: () => getModeB(idu, travaux),
    placeholderData: (prev) => prev,
  })
  const mb = q.data ?? initial
  if (!mb.disponible) return null
  // M59-P1 (Q4) — sous le seuil de SHAB : la section ne montre PAS le calcul, elle DIT pourquoi.
  if (mb.trop_petit) return (
    <RefDrawer id="mode-b" icon={IC.faisa} name="Réhabilitation" context="bâti trop petit"
      value={<span className="pill-amber">non pertinent</span>}>
      <p data-mode-b-trop-petit style={{ margin: 0, fontSize: 11.5, lineHeight: 1.5, color: '#8FA69A' }}>
        {mb.motif ?? `Bâti trop petit (SHAB ~${mb.shab_rehabilitable_m2 ?? '—'} m²) pour une thèse de réhabilitation.`}
      </p>
    </RefDrawer>
  )
  if (!mb.composantes) return null
  const c = mb.composantes
  const [bMin, bMax] = c.travaux.bornes
  const foncierM2 = mb.surface_parcelle_m2 ?? mb.terrain_nu?.surface_m2 ?? null
  return (
    <RefDrawer id="mode-b" icon={IC.faisa} name="Réhabilitation"
      context="Estimé — hypothèse travaux à ajuster"
      value={mb.negatif ? <span className="pill-amber">bilan négatif</span> : `~${mb.achat_max_libelle ?? ''}`}>
      <div data-mode-b style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {/* M59-P1 (Q1) — tête + comparaison terrain. La comparaison terrain nu ET la phrase
            « portée par le terrain » s'affichent dans LES DEUX cas (positif ou négatif) : c'est la
            vraie information sur ~50-64 % du stock, souvent des bilans bâti négatifs. */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {mb.negatif ? (
            /* résultat négatif : verdict en clair, JAMAIS un nombre négatif en tête. */
            <p style={{ margin: 0, fontSize: 11.5, lineHeight: 1.5, color: '#E8B44C' }}>{mb.message_negatif}</p>
          ) : (
            <>
              <p style={{ margin: 0, fontSize: 12.5, color: 'var(--txt-hi)' }}>
                Ce que la réhabilitation du bâti justifie : <b data-mode-b-achat>~{mb.achat_max_libelle ?? '—'}</b>
                <span style={{ marginLeft: 6, fontSize: 10.5, color: '#8FA69A' }}>(Estimé — l'hypothèse travaux l'est toujours)</span>
              </p>
              <p data-mode-b-hors-terrain style={{ margin: 0, fontSize: 10.5, color: '#8FA69A' }}>
                hors valeur du terrain — le foncier{foncierM2 != null ? ` (${fmtInt(foncierM2)} m²)` : ''} s'ajoute à ce montant
              </p>
            </>
          )}
          {mb.terrain_nu && (
            <p data-mode-b-terrain-nu style={{ margin: 0, fontSize: 10.5, color: '#8FA69A' }}>
              terrain nu au prix du secteur : <b style={{ color: 'var(--txt-hi)' }}>~{mb.terrain_nu.valeur_libelle}</b>{' '}
              <span style={{ fontSize: 10 }}>({fmtInt(mb.terrain_nu.prix_m2)} €/m² × {fmtInt(mb.terrain_nu.surface_m2)} m² · Estimé)</span>
            </p>
          )}
          {mb.porte_par_terrain && (
            <p data-mode-b-porte-terrain style={{ margin: '2px 0 0', fontSize: 11, lineHeight: 1.45, color: '#E8B44C' }}>
              À ces hypothèses, la valeur de cette parcelle est portée par le terrain, pas par le bâti.
            </p>
          )}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
            <span style={{ color: 'var(--txt-dim)' }}>Surface réhabilitable</span>
            <span style={{ color: 'var(--txt-hi)' }}>~{fmtInt(c.surface.shab_rehabilitable_m2)} m² hab.</span>
          </div>
          <p style={{ margin: 0, fontSize: 10, color: '#8FA69A' }}>
            emprise {fmtInt(c.surface.emprise_bati_m2)} m² <b style={{ color: '#5CE6A1' }}>Sourcé</b> ({c.surface.source_emprise}) × {c.surface.niveaux} niveau(x){' '}
            <b style={{ color: c.surface.niveaux_reels ? '#5CE6A1' : '#E8B44C' }}>{c.surface.niveaux_reels ? 'Sourcé' : 'Estimé'}</b>
            {' '}— {c.surface.niveaux_etiquette}
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
            <span style={{ color: 'var(--txt-dim)' }}>Prix de sortie (revente)</span>
            <span style={{ color: 'var(--txt-hi)' }}>{fmtInt(c.prix_sortie.prix_m2)} €/m² <b style={{ color: '#5CE6A1', fontSize: 10 }}>Sourcé DVF</b></span>
          </div>
          <p data-mode-b-perimetre style={{ margin: 0, fontSize: 10, color: '#8FA69A' }}>
            {c.prix_sortie.libelle}{c.prix_sortie.perimetre ? ` · ${c.prix_sortie.perimetre}` : ''}
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
            <span style={{ color: 'var(--txt-dim)', flex: 1 }}>Coût travaux <b style={{ color: '#E8B44C', fontSize: 10 }}>ESTIMÉ</b></span>
            <input data-mode-b-travaux type="number" min={bMin} max={bMax} step={50} value={travaux}
              onChange={(e) => setModeB({ travauxM2: Number(e.target.value) })}
              style={{ width: 80, background: '#0d1512', border: '1px solid #26302B', borderRadius: 6, color: 'var(--txt-hi)', padding: '3px 6px', fontSize: 11 }} />
            <span style={{ color: 'var(--txt-dim)' }}>€/m²</span>
          </div>
          <p style={{ margin: 0, fontSize: 10, color: '#8FA69A' }}>{c.travaux.libelle}</p>
          <p style={{ margin: 0, fontSize: 10, color: '#8FA69A' }}>{c.frais_marge.libelle}</p>
        </div>
        {/* M44 — SORTIE LOCATIVE : côte à côte avec la revente, jamais fusionnée. Loyer au plafond
            réglementaire Sourcé (ou marché Estimé) ; prix d'achat max à rendement cible. Mention fiscale. */}
        {mb.sortie_locative && (
          <div data-mode-b-locatif style={{ borderTop: '1px solid #24312b', paddingTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
            <p style={{ margin: 0, fontSize: 12, color: 'var(--txt-hi)', fontWeight: 600 }}>Sortie locative</p>
            {/* M59-P1 (Q2) — l'avertissement sur le loyer retenu passe AVANT le chiffre du prix
                d'achat locatif : le plafond réglementaire n'est pas un loyer de marché observé. */}
            <p data-mode-b-loyer-avert style={{ margin: 0, fontSize: 10, lineHeight: 1.4, color: '#E8B44C' }}>
              Loyer retenu : {mb.sortie_locative.loyer.etiquette}
              {mb.sortie_locative.loyer.source ? ` (réf. plafond ${mb.sortie_locative.loyer.source})` : ''}.
            </p>
            {mb.sortie_locative.negatif ? (
              <p style={{ margin: 0, fontSize: 11.5, color: '#E8B44C' }}>{mb.sortie_locative.message_negatif}</p>
            ) : (
              <p style={{ margin: 0, fontSize: 11.5, color: 'var(--txt-hi)' }}>
                Prix d'achat max : <b>~{mb.sortie_locative.achat_max_libelle}</b>
                <span style={{ marginLeft: 4, fontSize: 10, color: '#8FA69A' }}>(Estimé)</span> à rendement cible {mb.sortie_locative.rendement_cible_pct} %
                <span style={{ marginLeft: 4, fontSize: 10, color: '#8FA69A' }}>(paramètre client)</span>
              </p>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--txt-dim)' }}>Loyer</span>
              <span style={{ color: 'var(--txt-hi)' }}>~{fmtInt(mb.sortie_locative.loyer.annuel_eur)} €/an · {mb.sortie_locative.loyer.m2_mois_effectif} €/m²/mois</span>
            </div>
            {mb.sortie_locative.loyer.coef_surface != null && (
              <p style={{ margin: 0, fontSize: 10, color: '#8FA69A' }}>coefficient de surface {mb.sortie_locative.loyer.coef_surface}</p>
            )}
            <p style={{ margin: 0, fontSize: 9.5, lineHeight: 1.45, color: '#E8B44C' }}>{mb.sortie_locative.mention_fiscale}</p>
          </div>
        )}
        <p style={{ margin: 0, fontSize: 9.5, lineHeight: 1.45, color: '#6b7a72' }}>{mb.avertissement}</p>
      </div>
    </RefDrawer>
  )
}

function RtaaBlock({ rtaa }: { rtaa: { meta: Record<string, string>; exigences: { volet: string; exigence: string; reference: string; url: string; condition_altitude?: string }[] } }) {
  const [open, setOpen] = useState(false)
  const VOLET_COLOR: Record<string, string> = { cadre: '#8FA69A', thermique: '#E8B44C', acoustique: '#B497F0', aeration: '#7DE8E0', ecs: '#5CE6A1' }
  return (
    <div data-rtaa-block>
      <p className="label-caps mb-1">RTAA DOM — rappel réglementaire</p>
      <div className="card-elev px-3 py-2 text-[10.5px] leading-snug text-txt-mut">
        Construction neuve de logements : protection solaire, ventilation traversante,
        acoustique, aération et ECS renouvelable s'appliquent (seuils d'altitude 400/600 m).
        <button onClick={() => setOpen((o) => !o)} className="ml-1.5 text-mint hover:underline">
          {open ? 'replier' : `${rtaa.exigences.length} exigences →`}
        </button>
      </div>
      {open && (
        <div className="mt-1.5 flex flex-col gap-1.5">
          {rtaa.exigences.map((e, i) => (
            <div key={i} className="rounded-lg bg-surface-3 px-3 py-2">
              <span className="rounded-full px-1.5 py-0.5 font-mono text-[8.5px] font-semibold uppercase"
                style={{ color: VOLET_COLOR[e.volet] ?? '#8FA69A', background: `${VOLET_COLOR[e.volet] ?? '#8FA69A'}18` }}>
                {e.volet}
              </span>
              <p className="mt-1 text-[10.5px] leading-snug text-txt">{e.exigence}</p>
              {e.condition_altitude && <p className="mt-0.5 text-[11px] text-st-creuser">altitude : {e.condition_altitude}</p>}
              <a href={e.url} target="_blank" rel="noreferrer" className="mt-0.5 block text-[11px] text-mint hover:underline">
                {e.reference} ↗
              </a>
            </div>
          ))}
          <p className="text-[9px] leading-snug text-txt-dim">
            {rtaa.meta.champ} Vérifié le {rtaa.meta.verifie_le} — rappel de conception, ne
            remplace pas l'étude réglementaire du maître d'œuvre.
          </p>
        </div>
      )}
    </div>
  )
}

// M-B (passe directeur) : « qu'a-t-il d'autre ? » → scan patrimoine en un clic depuis la fiche.
function PatrimoineLink({ siren }: { siren: string }) {
  const { setModule, setM02Prefill } = useApp()
  return (
    <button
      onClick={() => { setM02Prefill(siren); setModule('patrimoine') }}
      className="mt-1.5 text-[11px] text-violet hover:underline"
      title="Scan patrimoine (M02) : tout le foncier de ce propriétaire sur l'île"
    >
      → tout son patrimoine (M02)
    </button>
  )
}

// M19 : la barre d'onglets a été retirée (fiche = pile de tiroirs) ; `tab` subsiste comme
// état interne toujours à 'synthese' (le contenu unique), gardé pour un diff minimal.

export function Fiche({ idu }: { idu: string }) {
  const select = useApp((s) => s.select)
  // M55-L point 5 — verdict à la demande : mémoire par parcelle pour la session (store).
  const verdictRevele = useApp((s) => !!s.verdictRevele[idu])
  const revelerVerdict = useApp((s) => s.revelerVerdict)
  // M61 P2 — bloc Analyse repliable : déplié par défaut (absent du map), état par parcelle/session.
  const analyseReplie = useApp((s) => !!s.analyseReplie[idu])
  const toggleAnalyseReplie = useApp((s) => s.toggleAnalyseReplie)
  const moduleFiche = useApp((s) => s.moduleFiche)
  const setModule = useApp((s) => s.setModule)
  const setFlyTo = useApp((s) => s.setFlyTo)        // Fix LOT 2 : « 1950 » recentre sur la parcelle
  const modBlock = moduleFiche[idu]
  const sourceLine = useApp((s) => s.sourceLine)
  const calculette = useApp((s) => s.calculette)   // A6 : hypothèses courantes → reflétées dans le PDF
  // Échap ferme la fiche — sauf si le drawer source est ouvert (il consomme Échap en premier)
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !useApp.getState().sourceLine && !useApp.getState().tool) select(null)
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [select])
  void sourceLine
  // M55-O phase 2.1c : `setTab` retiré (0-caller après retrait de goDrawer) — `tab` reste figé à
  // 'synthese' (le seul contenu), gardé pour le garde de rendu.
  const [tab] = useState<'synthese' | Onglet | 'bilan' | 'faisabilite' | 'pourquoi'>('synthese')
  // M19 · migration strangler onglets → tiroirs. MIGRATED = onglets déjà fondus dans la pile
  // Synthèse (leur contenu vit en FicheDrawer). Un clic d'onglet migré ouvre + scrolle le tiroir
  // (au lieu de basculer la vue) ; les onglets non migrés gardent l'ancienne bascule `tab`.
  // M55-L point 10 — accordéon EXCLUSIF des tiroirs (store, par parcelle). openId = tiroir ouvert
  // (null = tout fermé). La valeur du contexte est mémoïsée (identité stable tant que rien ne bouge).
  const tiroirOuvert = useApp((s) => s.ficheTiroir[idu] ?? null)
  const setFicheTiroir = useApp((s) => s.setFicheTiroir)
  const accValue = useMemo(
    () => ({ openId: tiroirOuvert, toggle: (id: string) => setFicheTiroir(idu, tiroirOuvert === id ? null : id) }),
    [tiroirOuvert, idu, setFicheTiroir],
  )
  // M55-O phase 2.1c : `goDrawer`/`pendingScroll` retirés — leurs seuls appelants (liens vers les
  // tiroirs « pourquoi »/« renouvellement ») ont disparu avec l'absorption de ces tiroirs dans le
  // bloc Analyse. Le lien « voir pourquoi » de l'écartée scrolle désormais vers les motifs inline.
  // A6 (post-revue) : recherche DANS la fiche (≠ barre du haut). La loupe de la fiche filtre le
  // CONTENU de la fiche (toutes les lignes tracées, tous onglets), pas le dashboard.
  const [ficheSearchOpen, setFicheSearchOpen] = useState(false)
  const [ficheQuery, setFicheQuery] = useState('')
  // M61 P1 — panneau IA unifié : 'aucun' = les deux boutons ; 'question' = AskBar pleine largeur ;
  // 'synthese' = panneau Synthèse pleine largeur. Le panneau actif REMPLACE la rangée de boutons
  // (ne se pose plus À CÔTÉ). Synthèse : la mutation vit ICI (persiste au repli) → replier puis
  // rouvrir ne relance AUCUN appel IA. Réinitialisée seulement au changement de parcelle.
  const [iaOuvert, setIaOuvert] = useState<'aucun' | 'question' | 'synthese'>('aucun')
  const syntheseM = useMutation({ mutationFn: () => getExplain(idu) })
  useEffect(() => { setIaOuvert('aucun'); syntheseM.reset() }, [idu])  // eslint-disable-line react-hooks/exhaustive-deps
  const { data: f, isLoading, isError, error, refetch } = useQuery({ queryKey: ['fiche', idu], queryFn: () => getFiche(idu) })
  const fq = ficheQuery.trim().toLowerCase()
  const ficheMatches = fq && f
    ? f.lines.filter((l) => `${l.layer} ${layerLabel(l.layer)} ${l.detail ?? ''} ${l.source ?? ''} ${l.result ?? ''}`.toLowerCase().includes(fq))
    : []

  // Correctif M5 (verdict d'en-tête) : étage 0 prime (bannière écartée + motifs, inchangé) ;
  // sinon un run v2 présent pilote bannière + badge (tier, rang, ×N) ; le statut matrice
  // legacy descend en « historique » dans la section Qualité — plus jamais verdict principal.
  const verdict = f ? verdictMeta(f.statut, f.score_v2?.tier, f.etage0) : null
  const v2Pilote = !!(f?.score_v2 && !f.etage0)
  const verdictEcartee = f ? (f.etage0 || (v2Pilote ? f.score_v2!.tier === 'ecartee' : f.statut === 'ecartee')) : false
  // C1 : motif principal d'écartement, affiché À CÔTÉ du badge (plus de bandeau rouge séparé).
  // Le détail complet reste dans l'onglet « Pourquoi pas » (rien n'est supprimé — R1).
  const hardLines = f?.lines.filter((l) => l.result === 'HARD_EXCLUDE') ?? []
  const ecarteeMotif = hardLines[0] ? layerLabel(hardLines[0].layer) : (f ? `qualité insuffisante (Q ${f.q_score})` : '')
  // M52 L2 (correction #1) : parcelle écartée/déclassée MAIS à signal ×N fort → cadrage « signal
  // brut ». Sans lui, « Déclassée » + « très forte probabilité relative » côte à côte forment une
  // contradiction (famille M48 : un statut mort à côté d'une promesse). Le ×N reste (réel), il
  // devient « signal brut » ; le mot passe en atténué ; un encadré dit que l'écartement PRIME et
  // pourquoi la fréquence est absente. Déclenché hors tiers servables (verdict.tier == null) et
  // seulement si le signal dépasse la moyenne (×N ≥ 2) — l'écartée simple ×1,3 reste sobre.
  const multBase = f?.score_v2?.mult_base ?? null
  const signalEcarte = !!(f?.score_v2 && verdict && verdict.tier == null && (multBase ?? 0) >= 2)
  const motifEcart = verdict?.label.includes(' — ') ? verdict.label.split(' — ').slice(1).join(' — ') : ecarteeMotif
  // M52 L2 — hiérarchie : l'essentiel (droit du sol + économie) s'ouvre à l'arrivée pour un tier
  // SERVABLE (verdict.tier ≠ null : brûlante/chaude/à-creuser/réserve). L'écartée simple n'ouvre
  // M55-L point 10 : `servable` (ex-pilote de defaultOpen des tiroirs Règles/Faisabilité) retiré —
  // l'accordéon est désormais tout fermé à l'ouverture (état initial légal), plus d'auto-ouverture.
  // M52 L3 — données ABSENTES, DITES (jamais approximées) : dérivées de nuls RÉELS du payload +
  // faits open-data connus. Chaque entrée est un fait vérifiable, pas une excuse vague.
  const donneesAbsentes: { quoi: string; pourquoi: string }[] = f ? [
    { quoi: 'Année de construction', pourquoi: 'non disponible en open data à la parcelle (ABSENTE)' },
    ...(!f.adresse ? [{ quoi: 'Adresse postale', pourquoi: 'parcelle non rattachée à une voie (BAN)' }] : []),
    ...(!f.proprietaire_moral ? [{ quoi: 'Identité du propriétaire', pourquoi: 'personne physique — non automatisée (workflow SPF/CERFA)' }] : []),
  ] : []
  const ongletLines = (o: Onglet) => f?.lines.filter((l) => l.onglet === o) ?? []
  // M19 · valeurs fermées des tiroirs d'onglets (P1.3) — dérivées des données DÉJÀ chargées,
  // aucun nouveau calcul ni requête. Risques : le NÉGATIF est AFFIRMÉ (« ✓ rien à signaler ·
  // N couches vérifiées ») — c'est le point capital de la refonte.
  const risquesLines = ongletLines('risques')
  const risquesFlags = risquesLines.filter((l) => l.result === 'SOFT_FLAG' || l.result === 'HARD_EXCLUDE')
  const risquesClean = risquesLines.filter((l) => l.result === 'PASS').length
  // Marché : médiane €/m² structurée (dvf_parcelle.secteur) + nb de ventes — donnée propre.
  const marcheLines = ongletLines('marche')
  const dvfSecteur = f?.dvf_parcelle?.secteur?.find((s) => s.type_bien === 'terrain') ?? f?.dvf_parcelle?.secteur?.[0]
  // Proprio : le signal dominant s'il existe (gérant âgé, procédure…), sinon le type de
  // propriétaire. Jamais d'identité de personne physique (boussole).
  const proprioLines = ongletLines('proprio')
  const proprioSignal = proprioLines.filter((l) => (l.weight ?? 0) > 0).sort((a, b) => (b.weight ?? 0) - (a.weight ?? 0))[0]
  const proprioType = f?.proprietaire_moral?.denomination ?? (f?.proprietaire_moral ? 'personne morale' : 'personne physique / non recensé')
  // Règles : zone PLU + SDP résiduelle (données déjà chargées).
  const reglesLines = ongletLines('regles')
  const reglesZone = f?.reglement_plu?.zones?.[0]?.zone
  const reglesSdp = f?.potentiel_transformation?.sdp_residuelle_m2
  // M19 réf. · faisabilité au niveau fiche pour la MICRO-PREUVE fermée (gabarit / logements /
  // charge). MÊME queryKey ['bilan', idu] que Faisabilité/Bilan → cache partagé, zéro requête en +.
  const faisa = useQuery({ queryKey: ['bilan', idu], queryFn: () => getFaisabilite(idu), enabled: !!f })
  const cap = faisa.data?.capacite
  const fo = cap?.fourchette
  // M30 item 5 (AI1886) : délaissé (< 50 m², seuil unique côté API) → le tiroir DIT
  // « délaissé (N m²) » au lieu d'une promesse de logements sur 9 m².
  const delaisse = faisa.data?.delaisse
  // M56-B3/B4 : zone A (agricole) et N (naturelle) = inconstructibles par principe. ATTENTION :
  // « AU » (à urbaniser) EST constructible → on exclut AU (« A » non suivi de « U »). Les zones
  // numérotées (1AU/2AU) commencent par un chiffre → non captées. U reste constructible.
  const nonConstructible = !!(reglesZone && /^(A(?!U)|N)/i.test(reglesZone))
  // M56-B4 point 3 (PRIORITÉ) — ne JAMAIS afficher un intervalle NUL (« 0–0 logts ») comme un
  // résultat : en non-constructible ou capacité nulle/absente, la colonne dit « non calculable »
  // (--txt-faint), pas un faux zéro. PRÉSENTATION seule — le calcul back n'est pas touché.
  const logMax = Array.isArray(fo?.logements_au_sol)
    ? Math.max(fo.logements_au_sol[0] ?? 0, fo.logements_au_sol[1] ?? 0)
    : (typeof fo?.logements_au_sol === 'number' ? fo.logements_au_sol : null)
  const capaciteNulle = logMax != null && logMax <= 0   // intervalle servi [0,0] / 0 = pas de résultat
  const logementsNonCalculable = nonConstructible || capaciteNulle  // pour le ton --txt-faint + contexte
  const logementsTxt = delaisse ? `délaissé (${delaisse.surface_m2} m²)`
    // Zone inconstructible → le calcul n'a pas d'objet : « non calculable ».
    : nonConstructible ? 'non calculable'
      // Zone constructible mais capacité servie nulle ([0,0]) → « — » (RefDrawer, --txt-faint) :
      // jamais « 0–0 logts » présenté comme un résultat.
      : capaciteNulle ? undefined
        : (logMax != null && logMax > 0)
          ? (Array.isArray(fo!.logements_au_sol) ? `${fo!.logements_au_sol[0]}–${fo!.logements_au_sol[1]} logts` : `${fo!.logements_au_sol} logts`)
          : (reglesSdp != null && reglesSdp > 0 ? `~${fmtInt(reglesSdp)} m² SDP` : 'à estimer')
  // micro-preuve Règles : jauge = part de SDP DÉJÀ consommée (le reste = potentiel).
  const pctConsomme = f?.potentiel_transformation?.pct_consomme
  const reglesArticle = f?.reglement_plu?.zones?.[0]?.articles?.[0]?.reference
  // M55-N point 8 : l'en-tête « Règles d'urbanisme » porte une CONTRAINTE de gabarit (hauteur max)
  // — plus la SDP résiduelle, qui vivait AUSSI dans l'en-tête « Faisabilité » (doublon M55-L P14).
  // Faisabilité garde la SDP ; la SDP reste accessible dans le corps du tiroir (potentiel/faisa).
  // Hauteur absente (faisabilité non calculée) → pas de valeur d'en-tête (le micro-jauge porte
  // déjà zone + article), jamais la SDP ni un doublon du zonage.
  // M56-B3 fix 6 : la colonne droite d'Urbanisme n'est JAMAIS vide. Hauteur connue → « N m max » ;
  // sinon l'ÉTAT de constructibilité de la zone (A/N = non constructible) ; à défaut, le RefDrawer
  // affiche « — » (--txt-faint). Zone A (agricole) et N (naturelle) = inconstructibles par principe.
  // M57-P1 (Q5) : « non constructible » affirmait plus que ce que le code sait (préfixe de zone
  // seul ; STECAL différé, extensions non traitées). Reformulé « constructibilité très limitée »
  // + « i » citant les exceptions non évaluées. Le CALCUL et la règle de zone sont inchangés.
  const reglesGabarit: ReactNode = fo?.hauteur_m != null
    ? `${fo.hauteur_m} m max`
    : nonConstructible
      ? <span className="t-val absent" style={{ maxWidth: 'none', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
          constructibilité très limitée
          <Tip side="top" tip="Les zones A et N interdisent la construction neuve à usage d'habitation, sauf exceptions non évaluées par LABUSE : STECAL, extension d'un bâtiment existant, construction agricole. À vérifier au règlement.">
            <span role="button" tabIndex={0} aria-label="Exceptions à la constructibilité" style={{ color: 'var(--txt-ghost)', fontSize: 11, cursor: 'help', flexShrink: 0 }}>ⓘ</span>
          </Tip>
        </span>
      : undefined
  // Dette #10 : drapeaux EBC / ER (information seule), dérivés des prescriptions PLU du run servi.
  const presc = f ? prescriptionsInfo(f.lines) : null

  // M56-B5 : conteneur fiche ramené de 440px (M55-L, +10 %) à 400px — sa largeur d'avant.
  // VALEUR UNIQUE ici (un critère, un seul endroit). `max-w-full` garde la fiche dans l'écran
  // aux petites largeurs (aucun débordement horizontal). Ne PAS toucher les tailles de texte
  // ni les paddings (calés en M56-B3 : panneau 14, .gr 10 vertical, .gr partagée).
  return (
    <FicheAccordionCtx.Provider value={accValue}>
    <aside className="fiche-v6 absolute right-0 top-0 z-10 flex h-full w-[400px] max-w-full flex-col border-l border-line shadow-2xl">
      {/* C1 : le bandeau « écartée » séparé est retiré — le motif s'affiche à côté du badge
          (en-tête, plus bas) et « voir pourquoi » ouvre l'onglet « Pourquoi pas ». Les motifs
          sourcés y restent intégralement (R1 : rien n'est supprimé). */}
      {f?.evenement === 'rouge' && (
        <div className="shrink-0 border-b border-st-ecartee/40 bg-st-ecartee/15 px-5 py-2.5">
          {/* R3 (PJ5) : vocabulaire matrice non thermique — « priorité dossier » (thermique = tier P servi) */}
          <div className="flex items-center gap-2 text-xs font-medium text-st-ecartee">● ÉVÉNEMENT — force « priorité dossier »</div>
          {f.evenement_detail && <div className="mt-1 text-[11px] leading-snug text-st-ecartee/90">{f.evenement_detail}</div>}
        </div>
      )}

      {/* bloc MODULE (doctrine : en tête de fiche, violet) */}
      {modBlock && (
        <div className="shrink-0 border-b border-violet/20 bg-violet/[0.07] px-5 py-3">
          <p className="label-caps text-violet">Module · {modBlock.module}</p>
          <div className="mt-1.5 flex flex-col gap-1">
            {modBlock.lines.map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3 text-[11px]">
                <span className="text-txt-dim">{k}</span>
                <span className="text-right text-txt">{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ═══ EN-TÊTE + CARTE VERDICT (DA §4). M56-B3 fix 3 : plus de filet ni de fond distinct
          sous l'en-tête — le panneau est un seul fond continu --bg-1 du haut au pied.
          M56-B3 fix 7 : padding panneau 16→14 (densité). ═══ */}
      {/* M56-B6 · DA-FICHE-v6 — EN-TÊTE en CARTE .head (identité + 4 chiffres) posée sur le fond
          de panneau plus sombre. Le CTA, le bandeau et les IA suivent SOUS la carte. */}
      <div style={{ padding: '14px 14px 0', flexShrink: 0 }}>
        <div className="head">
          <div className="head-top">
            <div style={{ minWidth: 0 }}>
              <div className="eyebrow">PARCELLE{f?.commune ? ` · ${f.commune.toUpperCase()}` : ''}</div>
              {/* IDU complet (mono) + copier sans cadre, collé à la référence. */}
              <div className="ref" data-fiche-idu>{iduComplet(idu) || 'Absent'}{iduComplet(idu) && <CopyIdu value={iduComplet(idu)} />}</div>
              {/* adresse ; absente → « i » explicatif. */}
              {/* M61 P5 — adresse COPIABLE : sélectionnable (aucun user-select:none) + icône copier
                  discrète (comme l'IDU). `.addr` passe en flex pour aligner texte + icône. */}
              <div className="addr" data-fiche-adresse>
                <span style={{ userSelect: 'text', minWidth: 0 }}>{f?.adresse ?? CLIENT.fiche.adresseAbsente}</span>
                {f?.adresse && <CopyIdu value={f.adresse} aria="Copier l’adresse" titre="Copier l’adresse" okTitre="Adresse copiée" dataAttr="adresse" />}
                {!f?.adresse && (
                  <Tip side="top" tip={CLIENT.fiche.adresseAbsenteInfo}>
                    <span data-adresse-absente-i role="button" tabIndex={0} aria-label="Pourquoi l’adresse manque"
                      style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 14, height: 14, borderRadius: 999, border: '1px solid var(--line-3)', color: 'var(--txt-ghost)', fontSize: 9, fontWeight: 700, lineHeight: 1, cursor: 'help', verticalAlign: 'middle' }}>i</span>
                  </Tip>
                )}
              </div>
              {f?.adresse && (
                <a className="addr-link" data-fiche-pj href={`https://www.pagesjaunes.fr/annuaire/chercherlespros?ou=${encodeURIComponent(`${f.adresse} ${f.commune ?? ''}`)}`}
                  target="_blank" rel="noreferrer noopener" title={CLIENT.fiche.pagesJaunesTip}>
                  {CLIENT.fiche.pagesJaunes} ↗
                </a>
              )}
            </div>
            <div className="hbtns">
              <WatchButton idu={idu} />
              <button className="hbtn" onClick={() => setFicheSearchOpen((o) => { if (o) setFicheQuery(''); return !o })}
                style={ficheSearchOpen ? { borderColor: 'var(--mint)', color: 'var(--mint)' } : undefined}
                title="Rechercher dans cette fiche">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><circle cx="11" cy="11" r="6" /><path d="m20 20-3.5-3.5" /></svg>
              </button>
              <button className="hbtn" onClick={() => select(null)} title="Fermer la fiche">
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg>
              </button>
            </div>
          </div>

        {/* M55-O phase 2.1 — BANDEAU DE 4 CHIFFRES (toujours visible, factuel, aucun avis) :
            Surface · Zone · SDP disponible · Prix secteur €/m². Valeurs SERVIES (jamais en dur) ;
            une valeur absente → « — » (jamais un zéro trompeur ni un blanc muet). Habillage affiné
            en phase 3. */}
        {f && (() => {
          const cells = [
            { l: 'Surface', v: fmtM2(f.surface_m2) },
            { l: 'Zone', v: reglesZone ?? '—' },
            // M56-B4 point 3 — un zéro n'est pas une absence : SDP nulle (non constructible) ou prix
            // nul = donnée sans objet → « — », jamais « 0 m² » / « 0 €/m² » présentés comme un résultat.
            { l: 'SDP dispo.', v: reglesSdp != null && reglesSdp > 0 ? `${fmtInt(reglesSdp)} m²` : '—' },
            // M56-B5 : « Secteur » (et non « Prix secteur ») — tient sur UNE ligne à 400px ; la DA §4 emploie déjà « SECTEUR ».
            { l: 'Secteur', v: dvfSecteur?.mediane_prix_m2 != null && dvfSecteur.mediane_prix_m2 > 0 ? `${fmtInt(dvfSecteur.mediane_prix_m2)} €/m²` : '—' },
          ]
          return (
            <div className="stats" data-bandeau-chiffres>
              {cells.map((c) => (
                <div className="stat" key={c.l}>
                  <div className="stat-l">{c.l.toUpperCase()}</div>
                  <div className={`stat-v${c.v === '—' ? ' vide' : ''}`}>{c.v}</div>
                </div>
              ))}
            </div>
          )
        })()}
        </div>{/* /.head — la carte d'en-tête (identité + 4 chiffres) est le SEUL bloc FIXE. */}
      </div>{/* M68 P1a — fin du wrapper FIXE (en-tête seul) : tout le reste défile. */}

      {/* M68 P1a — DÉFILEMENT UNIQUE : le bloc Analyse (CTA + carte verdict), la bannière RNU, les
          signaux, puis les tiroirs / actions / exports / mention légale vivent tous DANS ce conteneur
          `overflow-y-auto flex-1`. La fiche défile donc jusqu'au pied EN TOUTE circonstance (bloc
          Analyse absent / déplié / replié, synthèse ouverte, n'importe quel tiroir ouvert). Avant M68,
          le bloc Analyse était dans le wrapper flex-shrink:0 et affamait ce conteneur (cf. RAPPORT_M68). */}
      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto overflow-x-clip px-[14px] pb-4 pt-1">
        {/* wrapper NON-flex : conserve l'espacement interne d'origine du bloc Analyse (marges inline). */}
        <div>

        {/* M55-L point 5 — VERDICT À LA DEMANDE. À l'ouverture (verdict non encore demandé pour
            cette parcelle dans la session), un BOUTON vert remplace le bloc verdict — l'avis n'est
            jamais imposé à qui veut d'abord des informations. C'est le SEUL élément vert de ce
            niveau. Au clic, le bloc verdict complet se déploie (mémorisé par parcelle, session).
            Vaut aussi en mode factuel (le bouton apparaît pareillement : rien n'est imposé, tout
            est accessible). Les PDF gardent le verdict sans condition (rail back inchangé). */}
        {f && verdict && !verdictRevele && (
          // M56-B6 · DA-FICHE-v6 — bouton d'analyse pleine largeur (.cta, 40px) + légende dessous.
          <>
            <button data-demander-analyse className="cta" onClick={() => revelerVerdict(idu)}
              title="Déployer le verdict, le score et « pourquoi »">
              {CLIENT.fiche.demanderAnalyse} →
            </button>
            {/* M62-P1 (i) : sous-titre « Le verdict, le score et "pourquoi" — à la demande » RETIRÉ,
                le bouton se suffit (P2). `demanderAnalyseSous` (strings.ts) devient 0-caller. */}
          </>
        )}
        {/* CARTE VERDICT — teintée selon le tier (verdict.color) ; la référence montre le cas Chaude. */}
        {f && verdict && verdictRevele && (
          // M61 P2 — le bloc Analyse est un TIROIR : en-tête cliquable (Analyse LABUSE + verdict au
          // repli + chevron), corps repliable. État par parcelle (analyseReplie), déplié par défaut,
          // INDÉPENDANT de l'accordéon exclusif des 7 tiroirs (aucun autre tiroir ne se ferme).
          <div data-verdict-card style={{ marginTop: 8, background: `${verdict.color}12`, border: `1px solid ${verdict.color}59`, borderRadius: 13, overflow: 'hidden' }}>
            <button data-analyse-toggle onClick={() => toggleAnalyseReplie(idu)} aria-expanded={!analyseReplie}
              style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, background: 'none', border: 0, cursor: 'pointer', padding: '13px 16px', textAlign: 'left' }}>
              <span style={{ display: 'flex', alignItems: 'baseline', gap: 9, minWidth: 0, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 10, letterSpacing: 1.4, color: 'var(--lab)', textTransform: 'uppercase' }}>Analyse LABUSE</span>
                {analyseReplie && <span data-analyse-verdict style={{ fontSize: 14, fontWeight: 600, color: verdict.color }}>{verdict.label}</span>}
              </span>
              <span className="chev" style={{ color: 'var(--txt-faint)', flexShrink: 0, fontSize: 14, lineHeight: 1 }}>{analyseReplie ? '›' : '⌃'}</span>
            </button>
            {!analyseReplie && (
            <div data-analyse-corps style={{ padding: '0 16px 15px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
              <div style={{ minWidth: 0 }}>
                <p style={{ margin: 0, fontSize: 10, letterSpacing: 1.4, color: 'var(--lab)' }}>VERDICT LABUSE</p>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 9, marginTop: 5, flexWrap: 'wrap' }}>
                  <span data-badge-verdict style={{ fontSize: 23, fontWeight: 500, color: verdict.color, lineHeight: 1 }}>{verdict.label}</span>
                  {v2Pilote && f.score_v2?.rang != null && (verdict.tier === 'brulante' || verdict.tier === 'chaude') && (
                    <span style={{ fontSize: 12, color: 'var(--lab)' }}>rang {f.score_v2.rang}</span>
                  )}
                  {verdictEcartee && (
                    <span data-ecartee-motif style={{ fontSize: 12, color: 'var(--lab)' }}>
                      · {ecarteeMotif} <button onClick={() => document.querySelector('[data-analyse-motifs]')?.scrollIntoView({ behavior: 'smooth', block: 'center' })} style={{ background: 'none', border: 0, padding: 0, color: '#E8695A', textDecoration: 'underline', cursor: 'pointer', fontSize: 12 }} title={CLIENT.fiche.ecarteeVoirTip}>{CLIENT.fiche.ecarteeVoir}</button>
                    </span>
                  )}
                </div>
              </div>
              {f.score_v2?.mult_base != null && (
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <p style={{ margin: 0, fontSize: 19, fontWeight: 500, color: signalEcarte ? '#8C7468' : verdict.color, lineHeight: 1 }}>×{f.score_v2.mult_base.toFixed(1).replace('.', ',')}</p>
                  <p style={{ margin: '3px 0 0', fontSize: 11, color: 'var(--lab)' }}>
                    {signalEcarte ? 'signal brut' : 'plus probable d’être vendue'}
                    {f.score_v2.verbal?.info && (
                      <span title={f.score_v2.verbal.info} style={{ marginLeft: 4, cursor: 'help', borderBottom: '1px dotted #5f7568' }}>ⓘ</span>
                    )}
                  </p>
                  {/* mot d'échelle : en couleur du tier quand servable ; ATTÉNUÉ quand écartée à
                      signal fort (le mot ne doit pas faire promesse à côté d'un statut mort). */}
                  {f.score_v2.verbal?.mot && (
                    <p style={{ margin: '2px 0 0', fontSize: 11.5, fontWeight: 600, color: signalEcarte ? '#8C7468' : verdict.color }}>
                      {signalEcarte ? <>{f.score_v2.verbal.mot} <span style={{ fontWeight: 500, color: 'var(--lab)' }}>· écartée</span></> : f.score_v2.verbal.mot}
                    </p>
                  )}
                </div>
              )}
            </div>
            {/* M52 Lot 1 — réglette de position (×N, échelle LOG — arbitrage Vic L2, plus le
                percentile rang), fréquence mesurée par tier, « pourquoi ce score ». Présentation ;
                aucun calcul. Pas de note /100, pas d'étoiles (doctrine). */}
            {f.score_v2 && (
              <div style={{ margin: '12px 0 0' }}>
                {f.score_v2.verbal?.reglette_pct != null && (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: 'var(--txt-off)', marginBottom: 3 }}>
                      <span>moyenne</span><span>très forte</span>
                    </div>
                    <div style={{ position: 'relative', height: 7, borderRadius: 5, background: 'linear-gradient(90deg,#3a4d44,#6fb3d9 35%,#ffc266 70%,#ff7a59)' }}>
                      <i data-reglette style={{ position: 'absolute', top: -3, left: `${f.score_v2.verbal.reglette_pct}%`, width: 3, height: 13, background: '#fff', borderRadius: 2, boxShadow: '0 0 5px #000' }} />
                    </div>
                  </>
                )}
                {/* écartée/déclassée à signal fort : l'écartement PRIME — dit pourquoi la fréquence
                    est absente (doctrine étage 0 M5). Bordure « terre éteinte », pas de menthe. */}
                {signalEcarte && (
                  <p data-signal-ecarte style={{ margin: '9px 0 0', fontSize: 11, color: '#b9a898', borderLeft: '3px solid #8C7468', paddingLeft: 8 }}>
                    La parcelle porte {(multBase ?? 0) >= 4 ? 'un signal fort' : 'un signal au-dessus de la moyenne'} (×{f.score_v2.mult_base!.toFixed(1).replace('.', ',')}) <b>mais elle est écartée</b>{motifEcart ? <> : {motifEcart.toLowerCase()}</> : null} — l’écartement prime. La fréquence par tier ne s’affiche pas.
                    <span title="Le ×N est réel ; l’écartement (étage 0) prime sur le signal (doctrine M5). On montre le signal ET la raison de l’écart." style={{ marginLeft: 4, cursor: 'help', borderBottom: '1px dotted #5f7568' }}>ⓘ</span>
                  </p>
                )}
                {f.score_v2.verbal?.frequence && (
                  <p data-freq style={{ margin: '9px 0 0', fontSize: 11, color: 'var(--txt-dim)', borderLeft: '3px solid #5fd0a8', paddingLeft: 8 }}>
                    {f.score_v2.verbal.frequence.sous_moyenne
                      ? <>Fréquence de vente en dessous de la moyenne de l’île (potentiel de plus long terme).</>
                      : <>Parmi les parcelles de ce niveau, environ <b>{f.score_v2.verbal.frequence.sur_100} sur 100</b> ont été vendues en {f.score_v2.verbal.frequence.fenetre}, contre ~{f.score_v2.verbal.frequence.base_sur_100} sur 100 en moyenne.</>}
                    <span title={f.score_v2.verbal.frequence.source_dite} style={{ marginLeft: 4, cursor: 'help', borderBottom: '1px dotted #5f7568' }}>ⓘ</span>
                  </p>
                )}
                {(f.score_v2.pourquoi?.length ?? 0) > 0 && (
                  <details data-pourquoi style={{ marginTop: 8 }} open={verdict.tier === 'brulante' || verdict.tier === 'chaude' || signalEcarte}>
                    <summary style={{ cursor: 'pointer', fontSize: 11.5, color: '#a78bfa', fontWeight: 600 }}>{signalEcarte ? 'Pourquoi ce signal (avant l’écart)' : 'Pourquoi ce score'}</summary>
                    <ul style={{ margin: '6px 0 0', padding: 0, listStyle: 'none' }}>
                      {f.score_v2.pourquoi!.slice(0, 5).map((c, i) => (
                        <li key={i} style={{ padding: '3px 0', fontSize: 11.5, color: '#c9d6cf' }}>
                          <span style={{ color: c.signe === '-' ? '#8ba69a' : '#5fd0a8' }}>{c.signe === '-' ? '▽' : '▲'}</span>{' '}
                          {c.phrase || c.libelle}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            )}
            {/* chips d'arguments — M61 P3 : les pastilles « constructible {zone} » et « N vigilance(s) »
                sont RETIRÉES (doublon au mot près des tiroirs Urbanisme et Risques). Reste le seul
                signal qui n'existe nulle part ailleurs à ce niveau : le signal propriétaire (violet). */}
            {proprioSignal && (
              <div style={{ margin: '13px 0 0', paddingTop: 12, borderTop: `1px solid ${verdict.color}33`, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 11, background: '#1c1630', color: '#c9b6f2', border: '1px solid #3d3159', borderRadius: 6, padding: '3px 9px' }}>{fmtLibelleBrut(proprioSignal.detail).replace(/\s*—.*$/, '').slice(0, 34)}</span>
              </div>
            )}
            {/* M-RENOUV : badge segment Renouvellement (CUIVRE) — le verdict reste « Écartée » ;
                libellé doctrinal sous le badge, jamais « opportunité ». */}
            {f.renouvellement && (
              <div data-renouv-badge style={{ margin: '13px 0 0', paddingTop: 12, borderTop: `1px solid ${verdict.color}33` }}>
                <span style={{ fontSize: 11, fontWeight: 600, background: RENOUV.bg, color: RENOUV.txt, border: `1px solid ${RENOUV.border}`, borderRadius: 6, padding: '3px 9px', alignSelf: 'flex-start' }}>
                  Renouvellement — rang {fmtInt(f.renouvellement.rang_segment)}/{fmtInt(f.renouvellement.total_segment)}
                </span>
                <p data-renouv-libelle style={{ margin: '6px 0 0', fontSize: 11, color: 'var(--txt-dim)' }}>{f.renouvellement.libelle}</p>
                {/* M61 P4 — « Pourquoi ce rang » dépliable JUSTE À CÔTÉ du rang (comme « Pourquoi ce
                    score » sous le verdict) ; l'ancienne section basse « RENOUVELLEMENT — POURQUOI CE
                    RANG » est absorbée ici (aucune donnée nouvelle). */}
                <details data-renouv-pourquoi style={{ marginTop: 8 }}>
                  <summary style={{ cursor: 'pointer', fontSize: 11.5, color: RENOUV.txt, fontWeight: 600 }}>Pourquoi ce rang</summary>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
                    <p style={{ margin: 0, fontSize: 11.5, lineHeight: 1.5, color: 'var(--txt-dim)' }}>
                      {f.renouvellement.libelle} — écartée du classement principal ({RENOUV_CODE_LABEL[f.renouvellement.code_bati_origine] ?? f.renouvellement.code_bati_origine}),
                      mais en zone {f.renouvellement.zone_plu ?? '—'} avec une capacité restante réelle.
                    </p>
                    {f.renouvellement.composantes.map((c) => (
                      <div key={c.cle} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ flex: 1, fontSize: 11.5, color: REF.name, minWidth: 0 }}>{c.libelle}</span>
                        <div style={{ width: 90, height: 4, background: REF.barTrack, borderRadius: 2, overflow: 'hidden', flexShrink: 0 }}>
                          <div style={{ width: `${c.max > 0 ? Math.round(100 * c.points / c.max) : 0}%`, height: 4, background: RENOUV.bar }} />
                        </div>
                        <span style={{ fontSize: 11, color: RENOUV.txt, whiteSpace: 'nowrap', width: 42, textAlign: 'right' }}>{c.points}/{c.max}</span>
                      </div>
                    ))}
                    <MicroTriple items={[
                      f.renouvellement.sdp_residuelle_m2 != null && f.renouvellement.sdp_residuelle_m2 > 0 ? `SDP résiduelle ${fmtInt(f.renouvellement.sdp_residuelle_m2)} m²` : 'SDP résiduelle —',
                      f.renouvellement.surface_m2 != null ? `assiette ${fmtM2(f.renouvellement.surface_m2)}` : 'assiette —',
                      `rang île ${fmtInt(f.renouvellement.rang_segment)}/${fmtInt(f.renouvellement.total_segment)}`,
                    ]} />
                    <p style={{ margin: 0, fontSize: 10, color: REF.dim }}>{f.renouvellement.source}{f.renouvellement.maj ? ` · maj ${f.renouvellement.maj}` : ''}</p>
                  </div>
                </details>
              </div>
            )}

            {/* ═══ M55-O phase 2.1b — BLOC ANALYSE : TOUT l'avis LABUSE rassemblé (déployé au clic) ═══
                Aujourd'hui éparpillé (P dans « Les données », motifs dans « Pourquoi pas ? »,
                renouvellement et éligibilité en tiroirs) → réuni ici. Aucune donnée nouvelle. */}
            {/* P (probabilité de mutation) + « Pourquoi ce score » — déménagé du tiroir Les données. */}
            <div data-analyse-p style={{ marginTop: 13, paddingTop: 12, borderTop: `1px solid ${verdict.color}33` }}>
              <ScoreV2Block idu={idu} />
            </div>
            {/* M61 P4 — la section « RENOUVELLEMENT — POURQUOI CE RANG » a été REGROUPÉE dans le
                dépliant « Pourquoi ce rang » juste sous le rang (voir data-renouv-pourquoi ci-dessus). */}
            {/* Motifs rédhibitoires (« Pourquoi pas ? ») — tiroir entier absorbé. */}
            {(verdictEcartee || f.lines.some((l) => l.result === 'SOFT_FLAG')) && (
              <div data-analyse-motifs style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${verdict.color}33` }}>
                <p style={{ margin: '0 0 8px', fontSize: 10, letterSpacing: 0.8, color: 'var(--lab)', textTransform: 'uppercase' }}>Pourquoi pas ?</p>
                <PourquoiPasTab idu={idu} />
              </div>
            )}
            {/* Vérifications d'éligibilité — ✓ N passées (contrôles PASS du tiroir Urbanisme, repliés). */}
            <EligibiliteReplie lines={reglesLines} color={verdict.color} />
            </div>
            )}
          </div>
        )}

        {/* M65 P1 — le BANDEAU D'ATTENTION ambre « Marché peu actif à … » (ancien .band replié
            sur f.qualite_commune.degradee) est SUPPRIMÉ. La donnée n'est pas perdue : le tiroir
            « Qualité de la mesure · <commune> » (data-qualite-commune, plus bas) porte le détail
            complet (RR intra, échantillon, base %, libellé, source) dès que qualite_commune existe. */}

        {/* MANDAT RNU (B3) : bannière commune sans document local — étiquetage OBLIGATOIRE,
            flag général (config/rnu_communes.yaml). Jamais une affirmation de constructibilité ;
            la PAU est une ESTIMATION (wording validé Vic, servi par l'API — jamais reformulé ici). */}
        {f?.rnu && (
          <div data-rnu-banner style={{ marginTop: 10, background: '#2a2213', border: '1px solid #4a3c20', borderRadius: 10, padding: '9px 12px' }}>
            <p style={{ margin: 0, fontSize: 11.5, fontWeight: 600, color: '#e6b15c' }}>⚠ {f.rnu.libelle}</p>
            <p style={{ margin: '4px 0 0', fontSize: 10.5, lineHeight: 1.5, color: '#c9b98e' }}>
              {f.rnu.detail}{f.rnu.verifie_le ? ` Statut vérifié le ${f.rnu.verifie_le}.` : ''}
            </p>
            {f.rnu.dans_pau != null && (
              <p data-rnu-pau style={{ margin: '5px 0 0', fontSize: 10.5, lineHeight: 1.5, color: '#e6b15c' }}>
                {f.rnu.dans_pau ? 'Parcelle DANS l’enveloppe urbanisée estimée.' : 'Parcelle HORS de l’enveloppe urbanisée estimée.'}
                <span style={{ color: '#c9b98e' }}> {f.rnu.avertissement_pau}</span>
              </p>
            )}
          </div>
        )}

        {/* M29 (b)/(b) — signaux mérite/héritage (#9) et acquérabilité (#11) : information
            seule, libellés factuels arbitrés, AUCUN effet de classement. Champs absents = rien. */}
        {(f as any)?.entree_tete?.libelle && (
          <p data-entree-tete style={{ margin: '8px 0 0', fontSize: 11, color: '#8FA69A' }}>
            {(f as any).entree_tete.libelle} <span style={{ color: '#5a6b62' }}>({(f as any).entree_tete.etiquette})</span>
          </p>
        )}
        {(f as any)?.acquerabilite?.libelle && (
          <p data-acquerabilite style={{ margin: '4px 0 0', fontSize: 11, color: '#8FA69A' }}>
            assemblage : {(f as any).acquerabilite.libelle}
          </p>
        )}

        {/* M56-B4 point 2 — les drapeaux EBC / ER (prescriptions PLU, information seule) ne
            flottent plus dans le flux d'ACTIONS : ils descendent sous un micro-label « SIGNAUX »,
            juste avant LE TERRAIN (rendu plus bas). */}
        </div>{/* /wrapper non-flex du bloc Analyse (M68 P1a) — la suite défile aussi */}

      {ficheSearchOpen && (
        <div className="flex shrink-0 items-center gap-2 border-b border-line bg-surface-2 px-5 py-2">
          <input autoFocus data-fiche-search value={ficheQuery} onChange={(e) => setFicheQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Escape' && (setFicheQuery(''), setFicheSearchOpen(false))}
            placeholder="Chercher dans cette fiche (risque, réseau, ICPE…)"
            className="min-w-0 flex-1 rounded-md border border-line-2 bg-surface-3 px-2.5 py-1 text-xs text-txt placeholder:text-txt-dim focus:border-mint focus:outline-none" />
          {fq && <span className="shrink-0 text-[11px] text-txt-mut">{ficheMatches.length} résultat{ficheMatches.length > 1 ? 's' : ''}</span>}
        </div>
      )}

      {/* M19 (réf. ordre) : la barre d'onglets est RETIRÉE — la fiche est une pile de tiroirs
          empilés, navigable au scroll ; plus de navigation par onglets. */}

      {/* M68 P1a — l'ancien conteneur de défilement est FUSIONNÉ dans celui ouvert après l'en-tête
          (plus haut) : un seul conteneur `overflow-y-auto flex-1` pour tout le corps de la fiche. */}
        {/* A6 : recherche active → on remplace les onglets par les lignes de la fiche qui matchent */}
        {fq && f && (
          <div data-fiche-search-results>
            <p className="label-caps mb-2">Dans cette fiche · « {ficheQuery.trim()} »</p>
            {ficheMatches.length === 0
              ? <p className="text-xs text-txt-dim">Aucune donnée de la fiche ne correspond.</p>
              : <div className="flex flex-col gap-1">{ficheMatches.map((l, i) => <Line key={i} line={l} />)}</div>}
          </div>
        )}
        {isLoading && (
          <div className="flex flex-col gap-2">
            <Loading label="Chargement de la fiche" className="text-xs" />
            <div className="mt-1 h-16 animate-pulse rounded-lg bg-surface-2" />
            <div className="h-24 animate-pulse rounded-lg bg-surface-2" />
          </div>
        )}
        {isError && (is429(error) ? (
          <RateLimit429 error={error} refetch={refetch} />
        ) : error instanceof ApiError && error.status === 404 ? (
          /* G1 (M12) : une parcelle absente du run (copro non classée, hors périmètre, ou clic
             sur une trame sans idu) N'EST PAS une panne. Message NEUTRE, sans tonalité d'erreur —
             on invite simplement à re-sélectionner une parcelle. Aucun « serveur injoignable ». */
          <div data-fiche-hors-run className="rounded-lg border border-line-2 bg-surface-2 p-4 text-xs">
            <p className="text-txt">Cette parcelle n'est pas dans le périmètre analysé.</p>
            <p className="mt-1 text-txt-dim">Sélectionnez une parcelle sur la carte pour afficher sa fiche.</p>
            <button onClick={() => select(null)} className="mt-2 min-h-7 rounded border border-line-2 px-2 py-1 text-txt transition-colors duration-quick hover:border-mint/60 hover:text-txt-hi">Fermer</button>
          </div>
        ) : (
          <div data-fiche-erreur className="rounded-lg border border-st-ecartee/40 bg-st-ecartee/10 p-4 text-xs">
            {/* Item 3 (UX V1) : wording client — plus jamais « relancer labuse api » face à un
                utilisateur. Le détail technique reste lisible, en ligne discrète. */}
            <p className="text-st-ecartee">Connexion au serveur impossible — vérifiez votre réseau ou réessayez.</p>
            {error instanceof Error && error.message && (
              <p className="mt-1 break-all font-mono text-[10px] text-txt-dim">détail : {error.message}</p>
            )}
            <button onClick={() => refetch()} className="mt-2 min-h-7 rounded border border-line-2 px-2 py-1 text-txt transition-colors duration-quick hover:border-mint/60 hover:text-txt-hi">Réessayer</button>
          </div>
        ))}
        {!fq && f && tab === 'synthese' && (() => {
          // micro-preuves (spec) dérivées des données déjà chargées
          const shorten = (s: string) => fmtLibelleBrut(s).replace(/\s*[—(].*$/, '').trim()
          const proprioPastilles = proprioLines.filter((l) => (l.weight ?? 0) > 0).slice(0, 3).map((l) => shorten(l.detail).slice(0, 26))
          // ALGO-1 item 2 : l'accent proprio ne dépend plus du Score V (retiré de l'affichage)
          const proprioAccent = !!proprioSignal
          // M30 item 7 : la value dupliquait « Viabilisation » et écrasait le titre du tiroir en « V »
          const viabValue = f.viabilisation?.libelle?.replace(/^Viabilisation\s+/i, '') ?? (f.gestionnaires ? 'réseaux renseignés' : '—')
          // M55-O phase 3.5 : la valeur « Réseaux et accès » n'est VERTE que si l'état est confirmé
          // (band confirmee) ; sinon gris (factuel). Le vert redevient un signal.
          const viabColor = f.viabilisation?.band === 'confirmee' ? REF.ok : REF.gris
          const viabConfirmee = f.viabilisation?.band === 'confirmee'
          // M56-B2 · DA §4 — contexte Réseaux : les OPÉRATEURS (eau · assainissement · électricité).
          const viabContext = f.gestionnaires
            ? [f.gestionnaires.eau?.operateur, f.gestionnaires.assainissement?.operateur, f.gestionnaires.electricite?.gestionnaire].filter(Boolean).join(' · ') || null
            : null
          // M56-B6 · DA-FICHE-v6 « pas de % nu » : la couverture ICD vit dans le sous-titre du
          // tiroir « Données et méthode » (plus de valeur % nue à droite) — `confianceValue` retiré.
          return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {/* rien ne flotte : équipements, alerte accès, Q/A, statut, signaux → DANS les tiroirs (R1). */}

            {/* M55-L point 11 — BOUTONS IA EN TÊTE de fiche (mauve = couleur IA LABUSE, cf. « + Projet »
                / « Pourquoi ce score »), mis en valeur, visibles sans défilement dès l'ouverture.
                « Une question ? » (AskBar) + « Synthèse ». Même palette violette qu'avant (aucun
                nouveau composant), remontée + encadrée. */}
            {/* DA §4 — DEUX boutons .b-iris côte à côte, un libellé chacun. Les résultats
                (réponse AskBar, synthèse) se déploient en dessous. */}
            {/* M56-B3 fix 5 — DEUX .b-iris LÉGERS (moins que le bouton d'analyse) : hauteur réduite
                (padding 8px 11px), contenu aligné à GAUCHE, icône mauve 13px + libellé 12.5px. */}
            {/* M56-B6 · DA-FICHE-v6 — deux .ia-btn (34px) côte à côte ; icônes SVG conservées. */}
            {/* M61 P1 — le panneau actif (question ou synthèse) REMPLACE la rangée des deux boutons,
                pleine largeur ; « Replier » y ramène les boutons. Repli/réouverture de la synthèse
                ne relance aucun appel (mutation portée par la fiche, cf. syntheseM). */}
            <div data-ia-tete>
              {iaOuvert === 'aucun' && (
                <div className="ia">
                  <button onClick={() => setIaOuvert('question')} data-askbar-open className="ia-btn">
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M20 4H4v13h5l3 3 3-3h2z" /></svg>
                    Poser une question
                  </button>
                  <button onClick={() => { setIaOuvert('synthese'); if (!syntheseM.data && !syntheseM.isPending) syntheseM.mutate() }}
                    data-synthese-ia className="ia-btn" title={CLIENT.fiche.ia.syntheseTip}>
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" /></svg>
                    Synthèse IA
                  </button>
                </div>
              )}
              {iaOuvert === 'question' && <AskBar idu={idu} zone={null} startOpen onClose={() => setIaOuvert('aucun')} />}
              {iaOuvert === 'synthese' && <SyntheseIAPanel data={syntheseM.data} pending={syntheseM.isPending} error={syntheseM.isError} onReplier={() => setIaOuvert('aucun')} />}
            </div>

            {/* M55-O phase 2.1c : Mode B unifié et rattaché à la Constructibilité (rendu unique plus
                bas). L'ancien rendu « remonté » pour la déclassée à signal fort est retiré. */}

            {/* M56-B4 point 2 — SIGNAUX de la parcelle (drapeaux EBC / ER, information seule),
                regroupés ici juste avant LE TERRAIN, jamais au milieu des actions. Micro-label
                « SIGNAUX » ; si un seul signal, la pastille reste seule mais à cette place. */}
            {presc && (presc.ebc || presc.ers.length > 0) && (
              <div data-signaux-parcelle>
                <GroupLabel first>Signaux</GroupLabel>
                <div data-prescriptions-badges style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {presc.ebc && (
                    <Tip tip="Espace boisé classé — information. Toute construction est interdite sur l’emprise boisée (Art. L113-1 CU). N’exclut pas la parcelle.">
                      <span data-badge-ebc className="pill-mint">
                        partiellement en EBC{presc.ebc.coverage != null ? ` (~${presc.ebc.coverage} %)` : ''}
                      </span>
                    </Tip>
                  )}
                  {presc.ers.map((er, i) => (
                    <Tip key={i} tip="Emplacement réservé — information. Emprise grevée au profit d’un projet public (servitude levable si l’ER est abandonné). N’exclut pas la parcelle.">
                      <span data-badge-er className="pill-amber">
                        emplacement réservé{er.num ? ` n°${er.num}` : ''}
                      </span>
                    </Tip>
                  ))}
                </div>
              </div>
            )}

            {/* M55-O phase 3.4 — GROUPE SILENCIEUX « LE TERRAIN » : Urbanisme · Constructibilité
                (+ Mode B) · Risques et protections. */}
            <GroupLabel>Le terrain</GroupLabel>

            {/* M56-B6 · DA-FICHE-v6 — plus de conteneur .gcard : chaque tiroir est une carte autonome. */}
            {/* ① URBANISME — droit du sol (PLU, procédure, zonage, traducteur, règlement). */}
            <RefDrawer id="regles" icon={IC.regles} name="Urbanisme"
              value={reglesGabarit}
              context={[reglesZone ? `zone ${reglesZone}` : reglesArticle ? `art. ${reglesArticle}` : 'PLU', pctConsomme != null ? CLIENT.fiche.sdpConsommee(pctConsomme) : null].filter(Boolean).join(' · ')}
              micro={pctConsomme != null
                ? <MicroJauge pct={pctConsomme} label={CLIENT.fiche.sdpConsommee(pctConsomme)} tip={CLIENT.fiche.sdpConsommeeTip(reglesSdp ?? null)} />
                : <MicroJauge pct={0} label={[reglesZone ? `zone ${reglesZone}` : null, reglesArticle ? `art. ${reglesArticle}` : null].filter(Boolean).join(' · ') || 'PLU'} />}>
              <div className="flex flex-col gap-3">
                {/* M32 §2 + M40 : source qui fait foi. Les 3 choses distinctes, jamais mélangées :
                    (1) quel document LABUSE sert · (2) qu'il fait foi à ce jour · (3) ce qui est en
                    cours et non servi. + action « vérifier en mairie ». Couleur d'alerte hors « à jour ». */}
                {f.plu_fraicheur?.libelle && (
                  <div data-plu-fraicheur={f.plu_fraicheur.statut}
                    className={`rounded-lg border px-3 py-2 text-[11px] leading-snug ${
                      f.plu_fraicheur.statut === 'a_jour'
                        ? 'border-line-2 text-txt-mut'
                        : 'border-st-creuser/40 bg-st-creuser/10 text-txt'}`}>
                    <span className="mr-1">{f.plu_fraicheur.statut === 'a_jour' ? '🕓' : '▲'}</span>
                    {f.plu_fraicheur.document_servi ? (
                      <>
                        <span>{f.plu_fraicheur.document_servi}</span>
                        {f.plu_fraicheur.fait_foi && (
                          <span className="block text-[10px] text-txt-dim mt-0.5">✓ {f.plu_fraicheur.fait_foi}</span>
                        )}
                        {f.plu_fraicheur.en_cours && (
                          /* M57-P1 (d) : a_jour → avertissement NEUTRE (générique : assertion de config,
                             pas une procédure), sans sablier ni « En cours (non servi) ». Les autres
                             statuts (annule_partiel / opposabilite_en_attente) portent une procédure
                             RÉELLE → cadre « En cours (non servi) » conservé. */
                          f.plu_fraicheur.statut === 'a_jour'
                            ? <span className="block text-[10px] text-txt-dim mt-0.5">{f.plu_fraicheur.en_cours}</span>
                            : <span className="block text-[10px] text-st-creuser mt-0.5">⏳ En cours (non servi) : {f.plu_fraicheur.en_cours}</span>
                        )}
                        {f.plu_fraicheur.action && (
                          <span className="block text-[10px] text-txt-mut mt-0.5">→ {f.plu_fraicheur.action}</span>
                        )}
                      </>
                    ) : (
                      <>{f.plu_fraicheur.libelle}
                        {f.plu_fraicheur.note && f.plu_fraicheur.statut !== 'a_jour' && (
                          <span className="block text-[10px] text-txt-dim mt-0.5">{f.plu_fraicheur.note}</span>
                        )}
                      </>
                    )}
                  </div>
                )}
                {/* M41 — Radar procédures PLU : stade + conséquences parcellaires servables
                    (veille AU ; sursis si armé). Jamais l'issue de la procédure. */}
                {f.radar_procedure?.synthese?.etat && (
                  <div data-radar-procedure className="rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2 text-[11px] leading-snug text-txt">
                    <span className="mr-1">📡</span>{f.radar_procedure.synthese.etat}
                    {f.radar_procedure.veille_au && (
                      <span className="block text-[10px] text-mint mt-1">Veille AU — {f.radar_procedure.veille_au}</span>
                    )}
                    {f.radar_procedure.sursis ? (
                      <span className="block text-[10px] text-st-ecartee mt-1">
                        Sursis à statuer — {f.radar_procedure.sursis.texte}
                        <span className="block text-txt-dim">{f.radar_procedure.sursis.base_legale}</span>
                      </span>
                    ) : (
                      <span className="block text-[10px] text-txt-dim mt-1">Sursis à statuer : non servi (débat PADD non constaté à ce jour).</span>
                    )}
                  </div>
                )}
                {/* M55-O phase 2.2 — la jauge « Qualité » (q_score) est RETIRÉE de la fiche : mesurée
                    non discriminante en M55-N (82,5 % à la base neutre 50). Seule « Confiance données »
                    (ICD, tiroir Données) reste. Le champ back q_score n'est PAS touché (consommé
                    ailleurs : App, Kanban, MapView, filtres…) — seul l'affichage fiche disparaît. */}
                <TraducteurBloc idu={idu} />
                {f.reglement_plu && <ReglementPluBlock rp={f.reglement_plu} />}
                {/* M55-O phase 2.1c : le potentiel de transformation (SDP consommée/résiduelle/
                    surélévation) DÉMÉNAGE vers « Constructibilité » — il relève de la capacité, pas
                    du droit du sol pur. */}
                {/* M55-O phase 2.1b : les contrôles PASS (« sans objet ») partent dans
                    « Vérifications d'éligibilité » (bloc Analyse) ; ici, seules les lignes PLU
                    substantielles (non-PASS) restent — fini le mur de lignes « sans objet ». */}
                {/* M57-P1 (Q4) : points signés RETIRÉS ici (hideWeight) — le fait, la source et la
                    date restent. « Pourquoi ce score » (bloc Analyse) garde ses contributions. */}
                {(() => { const rl = reglesLines.filter((l) => l.result !== 'PASS'); return rl.length > 0
                  ? <div className="flex flex-col gap-1">{rl.map((l, i) => <Line key={i} line={l} hideWeight />)}</div> : null })()}
                {/* M22-B : lettre de vérification de zonage — bouton discret (la barre M20 reste à 7 tuiles) */}
                <a data-lettre-zonage href={`/lettre-zonage/${idu}.pdf`} target="_blank" rel="noreferrer"
                  className="self-start text-[10.5px] text-txt-mut underline decoration-line-2 underline-offset-2 hover:text-mint">
                  Éditer la lettre de vérification de zonage (PDF)
                </a>
              </div>
            </RefDrawer>

            {/* ③ ÉCONOMIE — capacité/bilan, marché, réseaux, mode B (M44). Ordre : capacité d'abord. */}
            {/* FAISABILITÉ ET BILAN — micro : 3 données sur une ligne. Ouvert si servable. */}
            <RefDrawer id="faisabilite" icon={IC.faisa} name="Constructibilité" value={logementsTxt}
              valueColor={logementsNonCalculable ? 'var(--txt-faint)' : undefined}
              context={delaisse
                ? `surface ${delaisse.surface_m2} m² · seuil ${delaisse.seuil_m2} m²`
                : logementsNonCalculable ? (reglesZone ? `zone ${reglesZone} · sans objet` : 'sans objet')
                  : [fo?.niveaux ?? null, 'calcul tracé'].filter(Boolean).join(' · ') || 'calcul tracé'}
              micro={<MicroTriple items={delaisse
                /* M30-revue A2 : le guard délaissé couvre la tuile ENTIÈRE — la sous-ligne ne
                   promet plus un gabarit/SDP sur une parcelle sous le seuil. */
                ? [`surface ${delaisse.surface_m2} m²`, `seuil délaissé ${delaisse.seuil_m2} m²`, 'bilan non servi']
                : [fo?.niveaux ?? 'gabarit', <>SDP <span style={{ color: 'var(--txt-dim)' }}>{fo?.surface_plancher_m2 ?? reglesSdp ?? '—'} m²</span></>, 'calcul tracé']} />}>
              <div className="flex flex-col gap-3">
                {delaisse && (
                  /* M30 item 5 : le bilan n'est pas servi sous 50 m² — on le DIT, on ne le masque pas */
                  <div data-delaisse className="flex items-start gap-2 rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2">
                    <span aria-hidden className="text-st-creuser">▲</span>
                    <p className="text-[11px] leading-snug text-txt">{delaisse.libelle}</p>
                  </div>
                )}
                {/* M55-O phase 2.1c : potentiel de transformation (SDP consommée/résiduelle/
                    surélévation) reçu depuis Urbanisme — la Constructibilité porte capacité + SDP. */}
                {f.potentiel_transformation && <TransformationBlock pt={f.potentiel_transformation} />}
                <FaisabiliteTab idu={idu} />
                {!delaisse && <BilanTab idu={idu} />}
              </div>
            </RefDrawer>
            {/* M55-O phase 2.1c : Mode B — Réhabilitation, rattaché à la Constructibilité (un seul
                rendu ; l'ancien dédoublement signalEcarte/servable est unifié). Reste un tiroir
                distinct (ModeBDrawer = RefDrawer autonome avec son propre fetch ; l'inliner dans
                Constructibilité casserait l'accordéon exclusif — signalé au rapport). */}
            {f.mode_b?.disponible && <ModeBDrawer idu={idu} initial={f.mode_b} />}

            {/* Risques et protections — clôt le groupe LE TERRAIN (M55-O phase 3.4). Valeur AMBRE
                quand il y a des vigilances (le vert redevient un signal — phase 3.5). */}
            <RefDrawer id="risques" icon={IC.risques} name="Risques et protections"
              context={`${risquesClean} couche${risquesClean > 1 ? 's' : ''} vérifiée${risquesClean > 1 ? 's' : ''}`}
              value={risquesFlags.length === 0
                ? <span className="pill-mint">rien à signaler</span>
                : <span className="pill-amber">{risquesFlags.length} vigilance{risquesFlags.length > 1 ? 's' : ''}</span>}
              micro={<MicroSegments n={risquesClean} label={`${risquesClean} couches`} />}>
              {risquesLines.length
                ? <div className="flex flex-col gap-1">{risquesLines.map((l, i) => <Line key={i} line={l} />)}</div>
                : <p className="text-xs text-txt-dim">Aucun signal sur cet onglet.</p>}
            </RefDrawer>

            {/* M55-O phase 3.4 — GROUPE SILENCIEUX « LE CONTEXTE » : Marché et secteur · Réseaux et
                accès · Propriétaire · Données et méthode. */}
            <GroupLabel>Le contexte</GroupLabel>

            {/* MARCHÉ — micro : sparkline + volume */}
            {/* M55-O phase 2.3 (incohérence 3) : le prix d'en-tête est étiqueté « terrain nu » — à
                distinguer du « prix de sortie bâti » (bilan) : deux métriques légitimes, jamais
                confondues (269-286 €/m² terrain vs ~2 000 €/m² bâti). */}
            <RefDrawer id="marche" icon={IC.marche} name="Marché et secteur"
              context={(dvfSecteur?.n_ventes ? `${dvfSecteur.n_ventes} vente${dvfSecteur.n_ventes > 1 ? 's' : ''} secteur` : 'comparables DVF') + ((faisa.data?.marche?.fraicheur?.horizon_libelle || faisa.data?.marche?.dvf_couverture?.libelle) ? ` · DVF — ${faisa.data.marche.fraicheur?.horizon_libelle ?? faisa.data.marche.dvf_couverture.libelle}` : '')}
              value={dvfSecteur?.mediane_prix_m2 != null ? `${fmtInt(dvfSecteur.mediane_prix_m2)} €/m²` : '—'}
              micro={<MicroSpark label={(dvfSecteur?.n_ventes ? `${dvfSecteur.n_ventes} ventes secteur` : 'comparables DVF') + ((faisa.data?.marche?.fraicheur?.horizon_libelle || faisa.data?.marche?.dvf_couverture?.libelle) ? ` · DVF — ${faisa.data.marche.fraicheur?.horizon_libelle ?? faisa.data.marche.dvf_couverture.libelle}` : '')} />}>
              {marcheLines.length
                ? <div className="flex flex-col gap-1">{marcheLines.map((l, i) => <Line key={i} line={l} />)}</div>
                : <p className="text-xs text-txt-dim">Aucun signal sur cet onglet.</p>}
              {/* M-U — signal de marché condensé (DVF actes + Sitadel), jamais un mot nu : les 2
                  composantes sont affichées ; l'outil « Marché » donne le bloc commune complet (9 lignes). */}
              {(() => { const sig = (f as unknown as { market_signal?: Record<string, any> }).market_signal
                return sig?.disponible ? (
                  <div data-fiche-market-signal className="mt-2 rounded-lg border border-line-2 bg-surface-2 px-2.5 py-1.5 text-[11px]">
                    <span className="font-medium text-txt">Signal de marché : {sig.label}</span>
                    {(sig.composantes as Record<string, any>[]).map((c, i) => (
                      <div key={i} className="mt-0.5 text-[10px] text-txt-mut">{c.sens} {c.cle} — {c.valeur}</div>
                    ))}
                    <p className="mt-0.5 text-[9px] text-txt-dim">{sig.source} · outil « Marché » pour le détail commune</p>
                  </div>
                ) : null })()}
              {/* M55-O phase 2.1c — HYPER-LOCAL absorbé depuis l'ancien tiroir « Contexte » :
                  historique permis sur la parcelle + voisinage proche (ventes DVF + permis 36 mois). */}
              {f.historique_site && (f.historique_site.permis.length > 0 || f.historique_site.caducite) && (
                <div data-historique-site className="mt-2 rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] leading-snug">
                  <div className="font-medium text-txt">🏗️ {f.historique_site.titre}</div>
                  <ul className="mt-1 list-disc pl-4 text-txt-mut">
                    {f.historique_site.permis.slice(0, 6).map((pm, i) => (
                      <li key={i}>{pm.type ?? 'permis'} — déposé {pm.date_depot ?? pm.date_autorisation ?? '?'}{pm.date_autorisation ? `, autorisé ${pm.date_autorisation}` : ''}</li>
                    ))}
                    {f.historique_site.caducite && (
                      <li className="text-st-ecartee">PC {f.historique_site.caducite.pc_annee ?? ''} — {f.historique_site.caducite.libelle_court ?? 'caduc'}</li>
                    )}
                  </ul>
                  <div className="mt-0.5 text-[10px] text-txt-dim">{f.historique_site.honnetete}</div>
                </div>
              )}
              {f.voisinage_proche && (
                <div data-voisinage-proche className="mt-2 rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] leading-snug">
                  <div className="font-medium text-txt">📍 {f.voisinage_proche.titre}</div>
                  <div className="mt-1 text-txt-mut">
                    {f.voisinage_proche.ventes_dvf} vente(s){f.voisinage_proche.prix_median_eur ? ` · prix médian ~${Math.round(f.voisinage_proche.prix_median_eur / 1000)} k€` : f.voisinage_proche.prix_note ? ` · ${f.voisinage_proche.prix_note}` : ''} · {f.voisinage_proche.permis} permis <span className="text-txt-dim">(&lt; 100 m, 36 mois)</span>
                  </div>
                  <div className="mt-0.5 text-[10px] text-txt-dim">{f.voisinage_proche.honnetete}</div>
                </div>
              )}
            </RefDrawer>

            {/* RÉSEAUX ET ACCÈS — accès, équipements, gestionnaires, permis */}
            <RefDrawer id="viabilisation" icon={IC.viab} name="Réseaux et accès" context={viabContext}
              value={viabConfirmee ? <span className="pill-mint">confirmée</span> : viabValue}
              valueColor={viabConfirmee ? undefined : viabColor}>
              <div className="flex flex-col gap-3">
                {/* M55-O phase 2.2 — la jauge « Accessibilité » (a_score) est RETIRÉE de la fiche
                    (même arbitrage que « Qualité » : une seule jauge de confiance, l'ICD). Champ back
                    a_score intact (consommé ailleurs). */}
                <EquipementsBadges idu={idu} />
                {f.lines.some((l) => l.layer === 'acces' && l.result === 'PASS') && (
                  <div data-acces-avertissement className="flex items-start gap-2 rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2">
                    <span aria-hidden className="text-st-creuser">▲</span>
                    <p className="text-[11px] leading-snug text-st-creuser"><b>Accès à vérifier</b> — aucun tronçon de voirie cartographié au contact.
                      <span className="text-txt-mut"> Signal informatif, non pondéré : la BD TOPO trace les voies publiques.</span></p>
                  </div>
                )}
                {f.viabilisation && <ViabilisationBlock via={f.viabilisation} />}
                {f.gestionnaires && <GestionnairesBlock g={f.gestionnaires} />}
                <PermitsProximityBlock idu={idu} />
                {f.depots && <DepotsBlock d={f.depots} />}
              </div>
            </RefDrawer>

            {/* M55-O phase 2.1c : Mode B rendu une seule fois, rattaché à la Constructibilité (plus haut). */}

            {/* M55-O phase 2.1c : le tiroir « Contexte » (historique + voisinage) est ABSORBÉ dans
                « Marché et secteur » (hyper-local). Il ne vit plus en tiroir séparé. */}

            {/* ⑤ PROPRIÉTÉ — société (M43) + signaux vendeur. CARTE ACCENTUÉE VIOLETTE = le signal chaud. */}
            <RefDrawer id="proprio" icon={IC.proprio} name="Propriétaire" accent={proprioAccent}
              context={proprioSignal ? (f.proprietaire_moral ? proprioType : 'personne physique') : undefined}
              value={proprioSignal ? shorten(proprioSignal.detail).slice(0, 20) : (f.proprietaire_moral ? proprioType.slice(0, 18) : 'privé')}
              micro={proprioPastilles.length ? <MicroPastilles items={proprioPastilles} /> : undefined}>
              <div className="flex flex-col gap-2">
                {f.proprietaire_moral ? (
                  <div className="card-elev px-3 py-2.5">
                    <p className="label-caps">Propriétaire (DGFiP)</p>
                    <div className="mt-1 text-xs font-medium text-txt-hi">{f.proprietaire_moral.denomination ?? '—'}</div>
                    <div className="mt-0.5 flex items-center gap-3 text-[10.5px] text-txt-mut">
                      {f.proprietaire_moral.siren && <span className="font-mono">SIREN {f.proprietaire_moral.siren}</span>}
                      {f.proprietaire_moral.groupe_label && <span>{f.proprietaire_moral.groupe_label}</span>}
                    </div>
                    {f.proprietaire_moral.etat_societe && (
                      // M43 — fait public d'entreprise (état société) : on le DIT, on n'en déduit RIEN
                      // (pas de vigilance, pas de badge, pas de filtre). PM only ; jamais la personne.
                      <div className="mt-2 border-t border-bd/60 pt-1.5 text-[10.5px] text-txt-mut">
                        <span className="text-txt-hi">{f.proprietaire_moral.etat_societe.libelle}</span>
                        <span className="ml-1 text-txt-dim">
                          (Sourcé {f.proprietaire_moral.etat_societe.etats.map((e) => e.source).filter((s, i, a) => a.indexOf(s) === i).join(' / ')})
                        </span>
                        <div className="mt-0.5 text-[9.5px] text-txt-dim italic">{f.proprietaire_moral.etat_societe.note}</div>
                      </div>
                    )}
                    {f.proprietaire_moral.siren && <PatrimoineLink siren={f.proprietaire_moral.siren} />}
                  </div>
                ) : (
                  <div className="card-elev px-3 py-2 text-[11px] text-txt-mut">
                    Propriétaire : personne physique ou non recensé au fichier des personnes morales
                    (identité nominative : workflow SPF/CERFA, jamais automatisée).
                    {/* M55-L point 12 — CONSTAT : le lien ouvrait `/parcels/{idu}/spf-letter` (lettre
                        TEXTE brute dans un onglet, 200 text/plain), pas un outil. Il OUVRE désormais
                        l'OUTIL courrier existant (M09, workflow SPF/CERFA) pré-rempli sur la parcelle
                        courante (M09 lit selectedIdu, préservé par setModule) — même mécanique que la
                        tuile Courrier. Le contexte parcelle passe (vérifié). Nuance rapportée : M09
                        n'a pas encore de motif « SPF » dédié (motifs : standard/indivision/succession)
                        ; l'endpoint /spf-letter reste servi (réactivable). */}
                    <button data-spf-letter onClick={() => setModule('courriers')}
                      className="mt-1.5 block text-left text-mint hover:underline" title={CLIENT.fiche.export.spfTip}>
                      → {CLIENT.fiche.export.spf} (courrier pré-rempli à envoyer au SPF)
                    </button>
                  </div>
                )}
                {proprioLines.length > 0 && <div className="flex flex-col gap-1">{proprioLines.map((l, i) => <Line key={i} line={l} />)}</div>}
              </div>
            </RefDrawer>

            {/* M55-O phase 3.4 : « Risques et protections » remonte dans le groupe LE TERRAIN
                (rendu plus haut, après la Constructibilité). */}

            {/* M55-O phase 2.1b : les tiroirs « Renouvellement — pourquoi ce rang » et « Pourquoi
                pas ? » sont ABSORBÉS dans le bloc Analyse (carte verdict, plus haut). Ils ne vivent
                plus en tiroirs séparés. */}

            {/* ⑧ LES DONNÉES — dernier bloc de contenu (M52 L3). Sources RÉELLEMENT utilisées sur
                cette fiche (data_sources) + données ABSENTES dites + confiance (ICD, score P), flags,
                signaler. Zéro nouvelle donnée : tout vient de tables existantes ou de nuls dits. */}
            <RefDrawer id="confiance" icon={IC.confiance} name="Données et méthode"
              context={[f.data_sources?.length ? `${f.data_sources.length} sources` : null, f.icd ? `couverture ${f.icd.score} %` : null].filter(Boolean).join(' · ') || undefined}
              value={<></>/* DA-FICHE-v6 « pas de % nu » : la couverture est dans le sous-titre ; à droite, juste le chevron. */}>
              <div className="flex flex-col gap-3">
                {/* Sources utilisées sur cette fiche — nom · fournisseur · millésime · fiabilité. */}
                {f.data_sources && f.data_sources.length > 0 && (
                  <div data-data-sources>
                    <p className="label-caps mb-1.5">Sources utilisées sur cette fiche</p>
                    <div className="flex flex-col gap-1">
                      {f.data_sources.map((s, i) => {
                        // millésime affiché seulement s'il est une date propre (AAAA / AAAA-MM) — les
                        // notes longues (« révisions par commune… ») cassent la ligne, le détail vit ailleurs.
                        const mill = s.millesime && /^\d{4}(-\d{2})?$/.test(s.millesime) ? s.millesime : null
                        return (
                        <div key={i} className="flex items-baseline justify-between gap-3 border-b border-line/60 py-1.5 last:border-0">
                          <div className="min-w-0">
                            <span className="text-xs text-txt">{s.nom}</span>
                            {s.fournisseur && <span className="ml-1 text-[10.5px] text-txt-dim">· {s.fournisseur}</span>}
                          </div>
                          <div className="flex shrink-0 items-baseline gap-2 whitespace-nowrap text-[10.5px] text-txt-mut">
                            {mill && <span className="tnum">{mill}</span>}
                            {s.fiabilite && <span className="rounded-full px-1.5" style={{ background: s.fiabilite === 'vérifiée' ? '#5CE6A122' : '#e8b84d22', color: s.fiabilite === 'vérifiée' ? '#5CE6A1' : '#e8b84d' }}>{s.fiabilite}</span>}
                          </div>
                        </div>
                      )})}
                    </div>
                  </div>
                )}
                {/* Données ABSENTES — dites, jamais approximées (doctrine M52). Dérivées de nuls RÉELS
                    du payload + faits open-data connus. Chaque absence est un fait, pas une excuse. */}
                {donneesAbsentes.length > 0 && (
                  <div data-donnees-absentes>
                    <p className="label-caps mb-1.5">Données absentes</p>
                    <ul className="flex flex-col gap-1">
                      {donneesAbsentes.map((a, i) => (
                        <li key={i} className="flex gap-2 text-[11px] leading-snug text-txt-mut">
                          <span aria-hidden className="text-txt-dim">○</span>
                          <span><span className="text-txt">{a.quoi}</span> — {a.pourquoi}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {/* M52 L4 — Qualité de la mesure PAR COMMUNE, DITE (audit RR fold 2025 OOS). RR intra
                    = pouvoir discriminant dans la commune ; « fragile » = <5 ventes en tête → fréquence
                    indicative. Mesure seule, aucun tier/seuil/modèle. */}
                {f.qualite_commune && (
                  <div data-qualite-commune className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
                    <div className="flex items-baseline justify-between gap-3">
                      <p className="label-caps">Qualité de la mesure · {f.qualite_commune.commune}</p>
                      <span className="shrink-0 rounded-full px-1.5 text-[10.5px]" style={{ background: f.qualite_commune.fragile ? '#e8b84d22' : '#5CE6A122', color: f.qualite_commune.fragile ? '#e8b84d' : '#5CE6A1' }}>
                        {f.qualite_commune.fragile ? 'échantillon limité' : 'robuste'}
                      </span>
                    </div>
                    <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] text-txt-mut">
                      {/* M-Q P2-74 : `rr_ile_dit` sert l'ordre de grandeur (« ~6,7 ») — jamais la
                          fausse précision 6.73. Sans lui, on N'affiche PAS le float brut : repli « — ». */}
                      <span>RR intra <b className="text-txt">{f.qualite_commune.rr_intra}</b>{f.qualite_commune.rr_ile != null ? <span className="text-txt-dim"> · île {f.qualite_commune.rr_ile_dit ?? '—'}</span> : null}</span>
                      <span>{f.qualite_commune.echantillon.toLocaleString('fr-FR')} parcelles</span>
                      {f.qualite_commune.taux_base_pct != null && <span>base {f.qualite_commune.taux_base_pct} %</span>}
                    </div>
                    <p className="mt-1.5 text-[11px] leading-snug text-txt-mut">{f.qualite_commune.libelle}</p>
                    <p className="mt-1 text-[10px] text-txt-dim">{f.qualite_commune.source}</p>
                  </div>
                )}
                {/* Confiance données (ICD) — jauge de confiance UNIQUE (M55-O 2.2). */}
                {f.icd && <IcdBlockView icd={f.icd} />}
                {/* M55-O phase 2.1b : ScoreV2Block (P + « pourquoi ce score ») DÉMÉNAGÉ dans le bloc
                    Analyse (carte verdict) — l'avis LABUSE est rassemblé, plus dans « Les données ». */}
                {/* M55-O phase 2.2 — le bloc « Signaux additionnels » (f.flags) est SUPPRIMÉ : ce sont
                    des redites des tiroirs dédiés (ABF → Risques, bâti/SDP → Constructibilité, PPR →
                    Risques). Chaque information n'apparaît qu'une fois. */}
                <SignalerErreur idu={idu} />
              </div>
            </RefDrawer>

            {/* M55-L point 11 : le bloc IA (« Une question ? » + « Synthèse ») est REMONTÉ en tête
                de fiche (voir plus haut, data-ia-tete). Il ne vit plus en bas de la pile. */}

            {/* ═══ BARRE D'ACTIONS · 2 niveaux (spec) — DANS le flux (fin du « double écran de vide ») ═══ */}
            <div>
              {/* M56-B6 · DA-FICHE-v6 — actions de pied en .actions (+ CRM · + Projet · Comparer),
                  sans filet séparateur (le relief vient du contraste fond/carte). */}
              <div className="actions">
                <PipelineButton idu={idu} />
                <ProjetButton idu={idu} />
                {/* M54-EXPO A8 — AJOUTER cette parcelle au comparateur (jusqu'à 3), puis ouvre le panneau. */}
                <button data-compare-add onClick={() => useApp.getState().addToCompare(idu)}
                  className="act act-cmp whitespace-nowrap"
                  title="Ajouter au comparateur (Outils → Comparer pour le rouvrir)">
                  ⇄ Comparer
                </button>
              </div>
              {/* M55-L point 8 — BARRE D'ACTIONS SUR DEUX LIGNES ÉQUILIBRÉES (décision Vic).
                  Ligne 1 : PDF · Dossier · Finance · Cadastre. Ligne 2 : 1950 · Maps · Courrier ·
                  One-pager · Pré-dossier PC. `gridAutoFlow:column + gridAutoColumns:1fr` → colonnes
                  ÉGALES quel que soit le nombre de tuiles réellement rendues (les tuiles Cadastre /
                  1950 / Maps sont conditionnées à f.coords → pas de trou). Mêmes hauteurs, mêmes
                  séparateurs qu'avant. */}
              {/* M56-B6 · DA-FICHE-v6 — EXPORTS ET OUTILS : label .sec + carte .exports (grille
                  4 colonnes .exp + bandeau large .exp-wide pour le Pré-dossier). Icônes 15px grises. */}
              <div className="sec"><span>EXPORTS ET OUTILS</span><i /></div>
              <div className="exports">
                <div className="exp-grid">
                  <a className="exp" href={pdfUrl(idu, calculette)} target="_blank" rel="noreferrer" title={calculette ? 'PDF (avec votre charge foncière)' : 'Exporter la fiche en PDF'}>
                    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /><path d="M12 12v5" /><path d="m9.5 14.5 2.5 2.5 2.5-2.5" /></svg>
                    <span>PDF</span>
                  </a>
                  <DossierTile idu={idu} />
                  <BanquierButton idu={idu} />
                  {f.coords && (
                    <a className="exp" data-cadastre-link href={`https://www.geoportail.gouv.fr/carte?c=${f.coords[0]},${f.coords[1]}&z=19&l0=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2::GEOPORTAIL:OGC:WMTS(1)&l1=CADASTRALPARCELS.PARCELLAIRE_EXPRESS::GEOPORTAIL:OGC:WMTS(1)&permalink=yes`} target="_blank" rel="noreferrer noopener" title={CLIENT.fiche.export.cadastreTip}>
                      <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="m9 4 6 2 6-2v14l-6 2-6-2-6 2V6z" /><path d="M9 4v14" /><path d="M15 6v14" /></svg>
                      <span>Cadastre</span>
                    </a>
                  )}
                  {f.coords && (
                    <button className="exp" onClick={() => { setFlyTo({ center: f.coords, zoom: 18 }); setModule('temps') }} title="Ce terrain en 1950 — comparateur temporel">
                      <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M12 8v4l3 2" /><path d="M3.05 11a9 9 0 1 1 .5 4" /><path d="M3 21v-5h5" /></svg>
                      <span>1950</span>
                    </button>
                  )}
                  {f.coords && (
                    <a className="exp" data-maps-link href={`https://www.google.com/maps/search/?api=1&query=${f.coords[1]},${f.coords[0]}`} target="_blank" rel="noreferrer" title="Ouvrir dans Google Maps (épingle sur la parcelle)">
                      <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0" /><circle cx="12" cy="10" r="3" /></svg>
                      <span>Maps</span>
                    </a>
                  )}
                  <button className="exp" data-courrier-tile onClick={() => setModule('courriers')} title={CLIENT.fiche.export.courrierTip}>
                    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" /></svg>
                    <span>{CLIENT.fiche.export.courrier}</span>
                  </button>
                  <a className="exp" data-onepager href={onePagerUrl(idu)} target="_blank" rel="noreferrer" title={CLIENT.fiche.export.onepagerTip}>
                    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /><path d="M8 13h8" /><path d="M8 17h5" /></svg>
                    <span>{CLIENT.fiche.export.onepager}</span>
                  </a>
                </div>
                <PreDossierTile idu={idu} />
              </div>
              {/* Mention légale conservée (présente aussi dans les PDF, back). */}
              <p data-disclaimer-legal className="legal">
                Estimations indicatives issues de données publiques — ni conseil juridique/notarial ni garantie de constructibilité. <span data-disclaimer-cu>Ces informations ne remplacent pas un certificat d'urbanisme.</span>
              </p>
            </div>
          </div>
          )
        })()}
      </div>


    </aside>
    </FicheAccordionCtx.Provider>
  )
}


/** M54-EXPO-2 — « Synthèse IA » : prose IA de toute la fiche (GET /parcels/{idu}/explain). La
 *  couche 2 M-T garantit une sortie soit VALIDÉE (available) soit un repli STUB déterministe
 *  (available=false, stub=true) — on affiche le libellé de repli quand c'est un stub. Le quota IA
 *  existant s'applique au niveau du socle IA ; un 429 tombe dans le message d'erreur. */
// M61 P1 — PANNEAU synthèse (plus un bouton) : pleine largeur, markdown rendu (renderRich), bouton
// « Replier ». La mutation est portée par la fiche (SyntheseIAPanel ne fait AUCUN appel) → replier
// puis rouvrir n'exécute rien. Les états en cours / erreur s'affichent aussi pleine largeur.
function SyntheseIAPanel({ data: d, pending, error, onReplier }: {
  data?: Awaited<ReturnType<typeof getExplain>>; pending: boolean; error: boolean; onReplier: () => void
}) {
  const box = { marginTop: 8, background: '#110d1b', border: '1px solid #372c58', borderRadius: 12, padding: '11px 14px' } as const
  const stub = d && !d.available
  const rs = d?.rules_summary
  return (
    <div data-synthese-ia-result style={box}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
        <p style={{ margin: 0, fontSize: 11, fontWeight: 600, color: '#c9b6f2', display: 'flex', alignItems: 'center', gap: 6 }}>
          {CLIENT.fiche.ia.synthese}
          {stub && <span data-synthese-stub style={{ fontSize: 9.5, fontWeight: 500, color: '#b7a3e6', border: '1px solid #47386e', borderRadius: 5, padding: '1px 5px' }}>repli</span>}
        </p>
        <button data-synthese-replier onClick={onReplier} title="Replier — revenir aux boutons"
          style={{ background: 'none', border: '1px solid #372c58', borderRadius: 7, color: '#b7a3e6', fontSize: 11, padding: '2px 9px', cursor: 'pointer', flexShrink: 0 }}>Replier</button>
      </div>
      {pending ? (
        <p style={{ margin: '8px 0 0', color: '#c9b6f2', fontSize: 12 }}><span style={{ display: 'inline-block', width: 6, height: 6, marginRight: 8, borderRadius: 9, background: '#8a6ff0' }} className="animate-pulse" />{CLIENT.fiche.ia.syntheseEnCours}</p>
      ) : error ? (
        <p style={{ margin: '8px 0 0', color: '#E8695A', fontSize: 12 }}>{CLIENT.fiche.ia.syntheseErreur}</p>
      ) : (
        <>
          <div style={{ margin: '7px 0 0', fontSize: 12, lineHeight: 1.5, color: '#d8ccf5' }}>{renderRich((d?.available ? d.explanation : d?.message) ?? '')}</div>
          {stub && Array.isArray(rs) && rs.length > 0 && <ul style={{ margin: '6px 0 0', paddingLeft: 16, fontSize: 11.5, lineHeight: 1.5, color: '#c9b6f2' }}>{rs.map((r, i) => <li key={i}>{r}</li>)}</ul>}
          {stub && typeof rs === 'string' && rs && <div style={{ margin: '6px 0 0', fontSize: 11.5, lineHeight: 1.5, color: '#c9b6f2' }}>{renderRich(rs)}</div>}
          {stub && <p style={{ margin: '7px 0 0', fontSize: 10, color: '#8f80b8' }}>{CLIENT.fiche.ia.syntheseStub}</p>}
        </>
      )}
    </div>
  )
}


// M55-L point 7 : le widget feedback `FeedbackStrip` (« Ce lead vous est-il utile ? ») est retiré
// de la fiche → fonction 0-caller supprimée, imports `postFeedback`/`FeedbackVerdict` retirés.
// ⚠ BACKEND : le endpoint POST /feedback (M54-EXPO A4, models.ParcelFeedback) n'a plus AUCUN point
// d'entrée côté front — NON supprimé côté back (décision Vic requise ; peut revenir, p. ex. CRM).


/** M54-EXPO-2 Volet C — tuile « Dossier » enrichie du STATUT (GET /dossier/statut) : quota
 *  restant du mois affiché, ou grisée + raison si le générateur n'est pas déployé (501). La barre
 *  à 7 tuiles n'est PAS réordonnée : c'est la même cellule, avec l'état en plus. */
function DossierTile({ idu }: { idu: string }) {
  const st = useQuery({ queryKey: ['dossier-statut'], queryFn: getDossierStatut })
  const icon = <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /></svg>
  const d = st.data
  if (d && !d.disponible) return (
    <span className="exp" data-dossier-indispo aria-disabled style={{ opacity: 0.4, cursor: 'not-allowed' }} title={d.raison ?? 'Générateur de dossier indisponible'}>
      {icon}<span>Dossier</span>
    </span>
  )
  const compteur = d && !d.illimite && d.restants != null
  const tip = d ? (d.illimite ? 'Dossier parcelle PDF brandé (illimité — Intégral)' : `Dossier parcelle PDF brandé — ${d.restants}/${d.quota_mois} restants ce mois`) : 'Dossier parcelle PDF brandé'
  return (
    <a className="exp" data-dossier-tile href={`/dossier/${idu}.pdf`} target="_blank" rel="noreferrer" title={tip}>
      {/* M62-P1 (l) : vert d'action aligné sur le token unique `--mint` (#4ADE80), plus de `#7de3ab` en dur. */}
      {icon}<span>Dossier{compteur ? <span data-dossier-quota style={{ color: d!.restants === 0 ? '#E8695A' : 'var(--mint)' }}> · {d!.restants}</span> : ''}</span>
    </a>
  )
}


/** M54-EXPO — tuile « Pré-dossier PC » (ZIP CERFA). Réservée au plan Intégral (backend :
 *  pre_dossier.py → plans.acces('pre_dossier_pc') = 403 sinon + quota M-K). Le front lit le plan
 *  (getMoi) et grise la tuile hors Intégral (pas de téléchargement d'un 403). */
function PreDossierTile({ idu }: { idu: string }) {
  const moi = useQuery({ queryKey: ['moi'], queryFn: getMoi })
  const integral = moi.data?.plan === 'integral'
  const icon = <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M21 8v13H3V3h10" /><path d="M16 3h5v5" /><path d="M8 13h6M8 17h4" /></svg>
  if (!integral) return (
    <span className="exp-wide" data-predossier-gate aria-disabled style={{ opacity: 0.4, cursor: 'not-allowed', color: 'var(--txt)' }} title={`${CLIENT.fiche.export.preDossierTip} — ${CLIENT.fiche.export.preDossierGate}`}>
      {icon}<span>{CLIENT.fiche.export.preDossier}</span>
    </span>
  )
  return (
    <a className="exp-wide" data-predossier href={preDossierUrl(idu)} target="_blank" rel="noreferrer" title={CLIENT.fiche.export.preDossierTip}>
      {icon}<span>{CLIENT.fiche.export.preDossier}</span>
    </a>
  )
}


/** B1.5 — bouton Dossier banquier à ÉTATS : clic → préparation asynchrone côté serveur
 *  (le PDF pesait 9,3 s bloquants), sonde /statut toutes les 1,5 s, puis « prêt — ouvrir »
 *  (cache serveur : ouverture ~ms). Erreur : message court + réessai. Si le cache est déjà
 *  chaud, le premier clic ouvre directement (même geste utilisateur → pas de popup bloquée). */
function BanquierButton({ idu }: { idu: string }) {
  const [etat, setEtat] = useState<'idle' | 'encours' | 'pret' | 'erreur'>('idle')
  const timer = useRef<number | null>(null)
  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current) }, [])
  useEffect(() => { setEtat('idle'); if (timer.current) window.clearTimeout(timer.current) }, [idu])
  const url = `/dossier-banquier/${idu}.pdf`
  const poll = async () => {
    try {
      const r = await fetch(`/dossier-banquier/${idu}/statut`)
      const d = await r.json()
      if (d.etat === 'pret') { setEtat('pret'); return }
      if (d.etat === 'erreur') { setEtat('erreur'); return }
    } catch { setEtat('erreur'); return }
    timer.current = window.setTimeout(poll, 1500)
  }
  const lancer = async () => {
    try {
      const r = await fetch(`/dossier-banquier/${idu}/prepare`, { method: 'POST' })
      const d = await r.json()
      if (d.etat === 'pret') { window.open(url, '_blank', 'noreferrer'); setEtat('pret'); return }
      setEtat('encours'); timer.current = window.setTimeout(poll, 1500)
    } catch { setEtat('erreur') }
  }
  // C6 · « Financier » (ex-Banquier) — rendu en tuile .exp (DA-FICHE-v6).
  const icon = <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="6" width="18" height="12" rx="2" /><circle cx="12" cy="12" r="2.5" /></svg>
  if (etat === 'pret') return (
    <a className="exp" href={url} target="_blank" rel="noreferrer" style={{ color: 'var(--mint)' }} title="Note de financement prête — ouvrir le PDF">
      {icon}<span style={{ color: 'var(--mint)' }}>{CLIENT.fiche.export.banquierPret}</span>
    </a>
  )
  if (etat === 'encours') return (
    <span className="exp">
      {icon}<span>{CLIENT.fiche.export.banquierEnCours}</span>
    </span>
  )
  return (
    <button className="exp" onClick={lancer} data-banquier-btn
      title={etat === 'erreur' ? 'Génération impossible — réessayer' : CLIENT.fiche.export.banquierTip}>
      {icon}<span>{etat === 'erreur' ? CLIENT.fiche.export.banquierErreur : CLIENT.fiche.export.finance}</span>
    </button>
  )
}


/** BLOC B · S45 — Traducteur PLU (variante B, verdict Vic) : bloc dépliable de l'onglet
 *  Règles. Charge à l'ouverture seulement ; Sourcé = article calibré, Estimé = générique. */
function TraducteurBloc({ idu }: { idu: string }) {
  const [open, setOpen] = useState(false)
  const q = useQuery({
    queryKey: ['traducteur', idu],
    queryFn: async () => {
      const r = await fetch(`/traducteur-plu/${idu}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      if (!r.ok) throw new Error(`traducteur ${r.status}`)
      return r.json() as Promise<{
        ok: boolean; zone: string | null; zone_calibree: boolean
        regles_appliquees: { regle: string; valeur: string; source: string }[]
        reglement: { url: string | null; note: string | null }
      }>
    },
    enabled: open, staleTime: 300_000,
  })
  const d = q.data
  return (
    <div data-traducteur className="mb-3 rounded-lg border border-violet/30 bg-violet/[0.06] px-3 py-2">
      <button data-traducteur-toggle onClick={() => setOpen((o) => !o)}
        className="flex min-h-7 w-full items-center justify-between gap-2 text-left">
        {/* M62-P1 (j) : casse NORMALE (plus de capitales `label-caps`) — « Demander à l'IA de traduire le PLU ». */}
        <span className="text-[11px] font-medium tracking-normal normal-case text-violet">✦ Demander à l'IA de traduire le PLU</span>
        <span className="text-[11px] text-txt-dim">{open ? 'replier ▴' : 'déplier ▾'}</span>
      </button>
      {open && (
        <div className="mt-2">
          {/* M55-N point 9 (décision Vic) : <AvisIA/> RETIRÉ du traducteur — la traduction de règles
              PLU est une LECTURE FACTUELLE (rien à « juger »), la mise en garde IA y était hors-sujet.
              Les surfaces IA GÉNÉRATIVES la conservent (Synthèse/explication, « Une question ? »,
              recherche IA, entretien, copilote, restitution). */}
          {q.isLoading && <Loading accent="violet" label="Traduction des règles…" className="text-[11px]" />}
          {q.isError && (
            <p className="text-[11px] text-st-ecartee">
              Traduction indisponible — <button onClick={() => q.refetch()} className="underline">réessayer</button>
            </p>
          )}
          {d && (
            <>
              <div className="flex flex-wrap items-center gap-1.5">
                {d.zone && <span className="rounded-full border border-violet/50 px-2 py-0.5 text-[10px] font-semibold text-violet">zone {d.zone}</span>}
                {!d.zone_calibree && (
                  <span className="rounded-full border border-st-creuser/40 bg-st-creuser/10 px-2 py-0.5 text-[10px] text-st-creuser">
                    zone non calibrée — valeurs génériques (Estimé)</span>
                )}
              </div>
              <div className="mt-1.5 space-y-1">
                {d.regles_appliquees.map((r, i) => (
                  <div key={i} className="flex items-baseline gap-2 text-[11.5px]">
                    <span className="min-w-0 flex-1 text-txt">{r.regle}</span>
                    <b className="tnum text-txt-hi">{r.valeur}</b>
                    <span className="shrink-0 rounded-full border border-st-creuser/40 bg-st-creuser/10 px-1.5 text-[8.5px] font-medium text-st-creuser"
                      title={r.source}>{d.zone_calibree ? 'Sourcé' : 'Estimé'}</span>
                  </div>
                ))}
                {d.regles_appliquees.length === 0 && <p className="text-[11px] text-txt-dim">Aucune règle traduite pour cette zone.</p>}
              </div>
              <p className="mt-1.5 text-[10px] leading-snug text-txt-dim">
                La référence opposable reste le règlement écrit{d.reglement?.url ? <> — <a className="text-mint hover:underline" href={d.reglement.url} target="_blank" rel="noreferrer">l'ouvrir ↗</a></> : ''}.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  )
}
