/**
 * fiche/primitives.tsx — RETOURS-11F4 (découpe de Fiche.tsx).
 * Primitives d'UI PARTAGÉES entre le shell de la fiche et les modules de section
 * (sections/*.tsx). Extrait TEL QUEL de Fiche.tsx : aucun changement de comportement,
 * seulement un point d'import unique (RefDrawer, Line, Micro*, PorteOutil, jetons REF/IC…).
 * Ne dépend d'AUCUN module de section → pas de cycle d'import.
 */
import { createContext, isValidElement, useContext, useEffect, useRef, type ReactNode } from 'react'
import { Tip } from '../Tip'
import { ApiError } from '../../lib/api'
import { fmtDateNum, fmtLibelleBrut } from '../../lib/format'
import { layerLabel } from '../../lib/layers'
import { useApp } from '../../store/useApp'
import type { FicheLine } from '../../lib/types'

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
      {/* RETOURS-4 S3 — `is-lien` marque un tiroir CLIQUABLE (id + children) → survol plein (index.css) ;
          un tiroir sans contenu (valeur seule) ne prend pas le survol. */}
      <button className={`tiroir${open ? ' is-open' : ''}${id && children ? ' is-lien' : ''}`} onClick={() => id && children && acc.toggle(id)} aria-expanded={open}
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
// M70 point 4 : `hideDate` retire la date de millésime en bout de ligne (bruit : toutes identiques ;
// le millésime reste en base, dans les exports PDF et l'écran Sources).
function SourceRef({ line, hideDate }: { line: FicheLine; hideDate?: boolean }) {
  const openSourceDrawer = useApp((s) => s.openSourceDrawer)
  // M70 décision 6 — la clé technique `source_table#source_id` (ex. « parcel_amenites#56909 ») ne
  // s'affiche PLUS au client (violation libellés_client). Le nom de source reste cliquable (drawer).
  return (
    <div className="mt-0.5 flex items-center gap-2 text-[11px] text-txt-dim">
      {line.source && (
        <button onClick={() => openSourceDrawer(line)} className="shrink-0 truncate text-txt-dim transition-colors duration-quick hover:text-mint hover:underline"
          title="Voir la source (drawer)">
          {line.source}
        </button>
      )}
      {/* FIX-FICHE F4 — le MILLÉSIME AMONT (vraie fraîcheur de la source, pas la date de run) est
          affiché INLINE, discret et tronqué : la traçabilité se lit sans ouvrir un tiroir. Le full
          au survol. La date de run (line.date) reste masquée (hideDate) car uniforme/trompeuse. */}
      {line.millesime_amont && (
        <span className="min-w-0 truncate text-[10px] text-txt-dim" title={line.millesime_amont}>· {line.millesime_amont}</span>
      )}
      {!hideDate && line.date && <span className="ml-auto shrink-0 font-mono tnum">{fmtDateNum(line.date)}</span>}
    </div>
  )
}

// M57-P1 (Q4) : `hideWeight` — masque les points signés (line.weight) de l'AFFICHAGE. Le fait,
// la source et la date restent. Utilisé dans le tiroir Urbanisme : les points dévoilaient le
// score avant la demande de verdict (doctrine M55-L) et faisaient doublon de rôle avec « Pourquoi
// ce score ». La donnée en base et le calcul sont intacts.
function Line({ line, hideWeight, hideDate }: { line: FicheLine; hideWeight?: boolean; hideDate?: boolean }) {
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
        <SourceRef line={line} hideDate={hideDate} />
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

function HypInput({ label, value, onChange, suffix, hint, placeholder }: {
  label: string; value: number | null; onChange: (v: number | null) => void
  suffix: string; hint?: boolean; placeholder?: string
}) {
  return (
    <div className="min-w-0 flex-1">
      {/* LOT1 — `flex-wrap` : le chip « hyp. » passe sous le libellé s'il n'y a pas la place, il ne
          CHEVAUCHE plus « Marge & frais » / « VRD & aménagements ». */}
      <label className="flex flex-wrap items-center gap-x-1 gap-y-0.5 text-[11px] text-txt-dim">
        {label}
        {hint && <span className="rounded bg-st-creuser/10 px-1 text-[8.5px] text-st-creuser" title="Hypothèse — à ajuster selon votre opération">hyp. — ajustez</span>}
      </label>
      {/* CIRCUIT-2 lot 1.7 — portée `projet` (DA v3) : une valeur SAISIE par le client s'affiche
          en AMBRE (bord + texte) — on voit d'un coup d'œil ce qui vient de lui, pas de LABUSE.
          Vide (placeholder = défaut serveur) : rendu neutre inchangé. */}
      <div className={`mt-1 flex items-center rounded-lg border bg-surface-3 ${
        value != null ? 'border-amber/60 focus-within:border-amber' : 'border-line-2 focus-within:border-mint'}`}>
        <input type="number" min={0} value={value ?? ''} placeholder={placeholder}
          onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
          data-saisie-client={value != null || undefined}
          className={`min-w-0 flex-1 bg-transparent px-2 py-1.5 text-xs placeholder:text-txt-dim focus:outline-none ${
            value != null ? 'text-amber' : 'text-txt'}`} />
        <span className="shrink-0 px-2 text-[11px] text-txt-dim">{suffix}</span>
      </div>
    </div>
  )
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

/** M60 P1c — LA PORTE D'OUTIL (gabarit .porte-outil de docs/DA-FICHE-v6.html, recopié TEL QUEL).
 *  En PIED de tiroir ouvert (après les données), pleine largeur ; accroche CONTEXTUALISÉE (jamais
 *  générique). Ouvre l'outil PRÉ-REMPLI via setModule (la fiche reste montée → retour intact). */
function PorteOutil({ ico, titre, sous, onClick, data, compacte }: {
  ico: ReactNode; titre: string; sous: string; onClick: () => void; data: string; compacte?: boolean
}) {
  return (
    <button type="button" data-porte={data} onClick={onClick} className={`porte-outil${compacte ? ' compacte' : ''}`}>
      <span className="po-ico">{ico}</span>
      <span style={{ minWidth: 0 }}>
        <span className="po-t block">{titre}</span>
        <span className="po-s block">{sous}</span>
      </span>
      <span className="po-arrow">→</span>
    </button>
  )
}

export { SEV_COLOR, REF, RENOUV, RENOUV_CODE_LABEL, drSvg, IC, FicheAccordionCtx, RefDrawer, GroupLabel, MicroJauge, MicroSegments, MicroSpark, MicroPastilles, MicroTriple, RateLimit429, Weight, SourceRef, Line, EligibiliteReplie, ICD_COLORS, icdColor, HypInput, StepProv, PorteOutil }
