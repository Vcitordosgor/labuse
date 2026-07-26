import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Tip } from '../Tip'
import { useEffect, useState, useRef, type ReactNode } from 'react'
import { addToPipeline, ajouterParcelle, ApiError, createShare, faisabiliteExplain, getFaisabilite, getFiche, getOrthoEquipements, getPipelineForParcel, getProjets, getWatch, is429, pdfUrl, postChargeFonciere, postSignalement, projetsPourParcelle, toggleWatch } from '../../lib/api'
import { completudeColor, SCORE_TIP, STATUT_META, verdictMeta } from '../../lib/status'
import { fmtDateNum, fmtInt, fmtM2, fmtLibelleBrut } from '../../lib/format'
import { layerLabel } from '../../lib/layers'
import { CLIENT } from '../../lib/strings'
import { Loading } from '../Loading'
import { ErrorState } from '../States'
import { AskBar, renderRich } from './AskBar'
import { PourquoiPasTab } from './PourquoiPas'
import { ScoreV2Block } from './ScoreV2Block'
import { ViabilisationBlock } from './ViabilisationBlock'
import { PermitsProximityBlock } from './PermitsProximityBlock'
import { GestionnairesBlock } from './GestionnairesBlock'
import type { FicheLine, IcdBlock, Onglet, PotentielTransformation, ReglementPlu } from '../../lib/types'
import { useApp } from '../../store/useApp'

const SEV_COLOR: Record<string, string> = { fort: '#E8695A', moyen: '#E8B44C', faible: '#C9DCD1', info: '#8FA69A' }


// ═══════════════════════════════════════════════════════════════════════════
// M19 · RÉFÉRENCE VISUELLE (qa/m19/reference/REFERENCE_FICHE_PARCELLE.html) — hex/tailles/espacements
// repris À L'IDENTIQUE de la spec Vic. Ce sont les seules couleurs en dur autorisées (spec).
const REF = {
  bg: '#080b0a', shell: '#1d2521',
  card: '#0e1311', cardBorder: '#202b26', accent: '#120e1c', accentBorder: '#443563',
  name: '#eef7f2', mint: '#7de3ab', violet: '#c9b6f2', dim: '#5f7568', dim2: '#7d9488',
  chev: '#3f5249', chevAccent: '#564a75', barTrack: '#18211d', barFill: '#3aa06e', seg: '#26473a',
  pastilleTxt: '#8a7ab0', pastilleBg: '#1a1428',
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
}

function RefChevron({ open, accent }: { open: boolean; accent?: boolean }) {
  return <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke={accent ? REF.chevAccent : REF.chev} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"
    style={{ flexShrink: 0, transform: open ? 'rotate(90deg)' : 'none', transition: 'transform .15s' }}><path d="m9 6 6 6-6 6" /></svg>
}

/** M19 · tiroir de la référence : fermé = icône + nom + valeur clé + MICRO-PREUVE (jauge, segments,
 *  sparkline, pastilles, 3 données) ; ouvert = le détail (blocs existants). Une seule carte peut être
 *  `accent` (violet) = le signal chaud. Rien n'est supprimé : le détail vit dans le corps déplié. */
function RefDrawer({ id, icon, name, value, valueColor, accent, micro, children, defaultOpen }: {
  id?: string; icon: ReactNode; name: string; value?: ReactNode; valueColor?: string
  accent?: boolean; micro?: ReactNode; children?: ReactNode; defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(!!defaultOpen)
  return (
    <div data-drawer={id} style={{ background: accent ? REF.accent : REF.card, border: `1px solid ${accent ? REF.accentBorder : REF.cardBorder}`, borderRadius: 12, padding: '13px 15px', scrollMarginTop: 8 }}>
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open}
        style={{ display: 'flex', alignItems: 'center', gap: 11, width: '100%', background: 'none', border: 0, padding: 0, cursor: children ? 'pointer' : 'default', textAlign: 'left', color: accent ? REF.violet : REF.mint }}>
        <span style={{ display: 'flex', flexShrink: 0 }}>{icon}</span>
        <span style={{ flex: 1, fontSize: 14, color: REF.name, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</span>
        {value != null && <span style={{ fontSize: 15, fontWeight: 500, color: valueColor ?? (accent ? REF.violet : REF.mint), whiteSpace: 'nowrap' }}>{value}</span>}
        {children && <RefChevron open={open} accent={accent} />}
      </button>
      {micro && <div style={{ marginTop: 10 }}>{micro}</div>}
      {open && children && <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${accent ? REF.accentBorder : '#1a231e'}` }}>{children}</div>}
    </div>
  )
}

// micro-preuves (spec) ──────────────────────────────────────────────────────
const MicroJauge = ({ pct, label }: { pct: number; label: string }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
    <div style={{ flex: 1, height: 4, background: REF.barTrack, borderRadius: 2, overflow: 'hidden' }}>
      <div style={{ width: `${Math.max(0, Math.min(100, pct))}%`, height: 4, background: REF.barFill }} />
    </div>
    <span style={{ fontSize: 11, color: REF.dim, whiteSpace: 'nowrap' }}>{label}</span>
  </div>
)
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
const MicroPastilles = ({ items }: { items: string[] }) => (
  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
    {items.map((t, i) => <span key={i} style={{ fontSize: 11, color: REF.pastilleTxt, background: REF.pastilleBg, borderRadius: 5, padding: '2px 8px' }}>{t}</span>)}
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

function Line({ line }: { line: FicheLine }) {
  return (
    <div className="flex gap-3 border-b border-line/60 py-2 last:border-0">
      <Weight w={line.weight} result={line.result} />
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
function ScoreBar({ label, value, color, lines, defaultOpen, tip }: {
  label: string; value: number; color: string; lines: FicheLine[]; defaultOpen?: boolean; tip?: string
}) {
  const [open, setOpen] = useState(!!defaultOpen)
  const weighted = lines.filter((l) => l.weight != null && l.weight !== 0).sort((a, b) => Math.abs(b.weight!) - Math.abs(a.weight!))
  return (
    <div className="card-elev">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-3 px-3 py-2.5"
        title={`${label} : déplier les signaux`}>
        {tip ? (
          <Tip tip={tip} className="w-24 shrink-0">
            <span className="text-left text-xs text-txt underline decoration-dotted decoration-line-2 underline-offset-4">{label}</span>
          </Tip>
        ) : (
          <span className="w-24 shrink-0 text-left text-xs text-txt">{label}</span>
        )}
        <span className="relative h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-line">
          <span className="absolute left-0 top-0 h-full rounded-full" style={{ width: `${value}%`, background: color }} />
        </span>
        <span className="w-8 shrink-0 text-right font-display text-sm font-bold tnum" style={{ color }}>{value}</span>
        <span className="shrink-0 text-txt-dim">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="border-t border-line-2 px-3 py-1">
          {weighted.length ? weighted.map((l, i) => <Line key={i} line={l} />) : <p className="py-2 text-[11px] text-txt-dim">Aucun signal chiffré — tout est neutre ou inconnu.</p>}
        </div>
      )}
    </div>
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
  return (
    <div data-reglement-plu className="card-elev px-3 py-2.5">
      <p className="label-caps">Règlement PLU</p>
      <div className="mt-1.5 flex flex-col gap-2">
        {rp.zones.map((z, i) => (
          <div key={i}>
            <div className="flex items-center gap-2">
              <span className="rounded-md bg-surface-3 px-1.5 py-0.5 font-mono text-[11px] text-txt">{z.zone}</span>
              {z.url && <a data-plu-link href={z.url} target="_blank" rel="noreferrer" className="text-[11px] text-mint hover:underline">
                {z.calibree ? 'Voir l’article' : 'Voir le règlement'} ↗
              </a>}
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
            {z.note && <p className="mt-0.5 text-[10px] text-txt-dim">{z.note}</p>}
          </div>
        ))}
      </div>
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
    <button onClick={() => t.mutate()}
      style={{ width: 31, height: 31, background: on ? '#101d16' : 'none', border: `1px solid ${on ? '#2f7a54' : '#232e29'}`, borderRadius: 9, display: 'flex', alignItems: 'center', justifyContent: 'center', color: on ? '#7de3ab' : '#7d9488', cursor: 'pointer', flexShrink: 0 }}
      title={on ? CLIENT.fiche.suivreActif : CLIENT.fiche.suivre}>
      <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M10 5a2 2 0 1 1 4 0a7 7 0 0 1 4 6v3a4 4 0 0 0 2 3H4a4 4 0 0 0 2-3v-3a7 7 0 0 1 4-6" /><path d="M9 17v1a3 3 0 0 0 6 0v-1" /></svg>
    </button>
  )
}

// M20 — pack apporteur : lien public lecture seule, filigrané + horodaté + compteur de vues.
function ShareButton({ idu }: { idu: string }) {
  const share = useMutation({ mutationFn: () => createShare(idu) })
  return (
    <div style={{ position: 'relative', flexShrink: 0 }}>
      <button onClick={() => share.mutate()}
        style={{ width: 31, height: 31, border: '1px solid #232e29', borderRadius: 9, background: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#7d9488', cursor: 'pointer' }}
        title="Pack apporteur : générer un lien public lecture seule (filigrané, compteur de vues)">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><path d="m8.6 13.5 6.8 4M15.4 6.5 8.6 10.5" /></svg>
      </button>
      {share.data && (
        <div className="floating absolute bottom-10 right-0 z-20 w-64 p-3 text-[11px]">
          <p className="label-caps">Lien apporteur</p>
          <a href={share.data.url} target="_blank" rel="noreferrer" className="mt-1 block truncate text-mint hover:underline">
            {window.location.origin}{share.data.url}
          </a>
          <p className="mt-1 text-[11px] text-txt-dim">Lecture seule · filigrané · consultations comptées.</p>
        </div>
      )}
    </div>
  )
}

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
      className={`flex h-8 flex-1 items-center justify-center whitespace-nowrap rounded-lg px-3 text-xs font-medium ${
        inPipe ? 'cursor-default border border-line-2 bg-surface-3 text-txt-mut' : 'bg-mint text-mint-ink hover:brightness-110'}`}
      title={inPipe ? 'Déjà suivie dans le pipeline (voir CRM)' : 'Ajouter au pipeline de prospection'}
    >
      {add.isPending ? 'Ajout…' : inPipe ? '✓ Dans le pipeline' : '+ Pipeline'}
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
        className={`flex h-8 w-full items-center justify-center gap-1 whitespace-nowrap rounded-lg px-3 text-xs font-medium ${
          inProjet ? 'bg-violet text-bg hover:brightness-110' : 'border border-violet/50 text-violet hover:bg-violet/10'}`}
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

function euros(x: number | null | undefined): string {
  if (x == null) return '—'
  const ax = Math.abs(x)
  if (ax >= 1_000_000) return `${(x / 1_000_000).toFixed(1)} M€`
  if (ax >= 1_000) return `${Math.round(x / 1_000).toLocaleString('fr-FR')} k€`
  return `${Math.round(x).toLocaleString('fr-FR')} €`
}

const CALC_COUT_DEFAUT = 2500
const CALC_MARGE_DEFAUT = 21

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
 *  en JS). Cas limites honnêtes : capacité non résolue / prix insuffisant → pas de faux chiffre. */
export function Calculette({ idu }: { idu: string }) {
  const [cout, setCout] = useState<number | null>(CALC_COUT_DEFAUT)
  const [marge, setMarge] = useState<number | null>(CALC_MARGE_DEFAUT)
  const [prixDemande, setPrixDemande] = useState<number | null>(null)
  // M22-A : la même équation, deux lectures — charge supportable (historique) ou prix d'achat
  // max admissible (inverse). Le moteur garantit l'identité des totaux (aucun calcul en JS).
  const [mode, setMode] = useState<'charge' | 'achat_max'>('charge')
  const [deb, setDeb] = useState({ cout: CALC_COUT_DEFAUT, marge: CALC_MARGE_DEFAUT, prix: null as number | null })
  useEffect(() => {
    const t = setTimeout(() => setDeb({ cout: cout ?? CALC_COUT_DEFAUT, marge: marge ?? CALC_MARGE_DEFAUT, prix: prixDemande }), 350)
    return () => clearTimeout(t)
  }, [cout, marge, prixDemande])
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
                <b data-calc-cf className="num-key text-lg text-mint">{euros(cf.central)}</b>
                <span className="ml-1.5 text-[11px] text-txt-mut">≈ {fmtInt(Number(cf.par_m2_terrain))} €/m² de terrain</span>
              </p>
              <p className="text-[11px] text-txt-dim">fourchette {euros(cf.bas)} – {euros(cf.haut)}{d.fiabilite === 'fragile' ? ' · prix de sortie fragile (ordre de grandeur)' : ''}</p>
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
                  ? <>Écart : prix demandé {euros(d.ecart_negociation.prix_demande_eur)} − prix d'achat max {euros(d.ecart_negociation.prix_achat_max_eur)} = <b>surcoût de {euros(d.ecart_negociation.demande_moins_max_eur)}</b> (+{d.ecart_negociation.demande_moins_max_pct} % au-dessus du max admissible).</>
                  : <>Écart : prix demandé {euros(d.ecart_negociation.prix_demande_eur)} est <b>sous votre prix d'achat max</b> ({euros(d.ecart_negociation.prix_achat_max_eur)}) — marge de {euros(Math.abs(d.ecart_negociation.demande_moins_max_eur))}.</>}
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
                  ? <>✓ Supportable — le terrain peut valoir {euros(achat.prix_demande_eur)} ; marge de {euros(achat.ecart_eur)} ({achat.ecart_pct > 0 ? '+' : ''}{achat.ecart_pct} %) sous votre charge foncière.</>
                  : <>✗ Trop cher — à {euros(achat.prix_demande_eur)}, l'opération dépasse de {euros(Math.abs(achat.ecart_eur))} ({achat.ecart_pct} %) ce que vos hypothèses supportent.</>}
              </div>
            )}
            {(d.avertissements ?? []).length > 0 && (
              <ul className="mt-1.5 list-inside list-disc text-[11px] text-st-creuser">
                {d.avertissements.map((a: string, i: number) => <li key={i}>{a}</li>)}
              </ul>
            )}
            <p className="mt-1.5 text-[9px] leading-snug text-txt-dim">
              Le coût de construction et la marge sont VOS hypothèses (LABUSE ne les estime pas). Le
              résultat est un calcul à partir de celles-ci — estimation indicative, ne vaut pas conseil.
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
    e['flag_terrassement_lourd'] ? '#e8734d' : '#7d9488',
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
  const [showSteps, setShowSteps] = useState(true)
  const explain = useMutation({ mutationFn: () => faisabiliteExplain(idu) })
  if (isLoading) return <Loading label="Calcul de la pré-faisabilité" className="text-xs" />
  if (isError || !b) return <ErrorState message="Faisabilité indisponible." retry={() => refetch()} />

  const cap = b.capacite
  const fo = cap?.fourchette ?? {}
  const steps: { label: string; valeur: string; source: string; prov: string }[] = cap?.steps ?? []
  const ex = explain.data
  return (
    <div className="flex flex-col gap-3">
      {/* ── LE RÉSULTAT ── */}
      {cap ? (
        <div className="rounded-lg border border-mint/40 bg-mint/[0.06] px-3 py-2.5">
          <p className="label-caps mb-1">Capacité constructible</p>
          <div className="text-sm font-medium text-txt-hi">{cap.verdict}</div>
          <div className="mt-1.5 grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-txt-mut">
            <div>Gabarit : <b className="text-txt">{fo.niveaux}</b> ({fo.hauteur_m} m)</div>
            <div>SDP : <b className="text-txt">{fmtM2(fo.surface_plancher_m2)}</b></div>
            <div>Logements : <b className="text-txt">{Array.isArray(fo.logements_au_sol) ? `${fo.logements_au_sol[0]}–${fo.logements_au_sol[1]}` : '—'}</b></div>
            <div>SHAB vendable : <b className="text-txt">~{fmtM2(fo.shab_vendable_m2)}</b></div>
          </div>
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

      {/* ── EXPLIQUER CE CALCUL EN CLAIR (IA, sur clic, premium violet) ── */}
      {cap && (
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
  const cap = b.capacite
  const fo = cap?.fourchette ?? {}
  const Sec = ({ t, children }: { t: string; children: React.ReactNode }) => (
    <div>
      <p className="label-caps mb-1">{t}</p>
      <div className="card-elev px-3 py-2 text-[11px] leading-relaxed text-txt">{children}</div>
    </div>
  )
  return (
    <div className="flex flex-col gap-3">
      {cap ? (
        <Sec t="Capacité (que peut accueillir ce terrain ?)">
          <div className="font-medium text-txt-hi">{cap.verdict}</div>
          <div className="mt-1 text-txt-mut">
            {fo.niveaux} · emprise bâtie max {fmtM2(fo.emprise_batie_max_m2)} · SDP {fmtM2(fo.surface_plancher_m2)} ·
            SHAB vendable ~{fmtM2(fo.shab_vendable_m2)} · stationnement : {String(fo.stationnement_regime ?? '—').replace(/_/g, ' ')}
          </div>
          {!cap.calibree && <div className="mt-1 text-[11px] text-st-creuser">▲ estimation générique (zone non calibrée)</div>}
          <div className="mt-1.5 text-[11px] leading-snug text-txt-dim">{cap.bandeau}</div>
        </Sec>
      ) : (
        <Sec t="Capacité">Zone PLU non résolue pour cette parcelle — capacité non calculable (honnête).</Sec>
      )}
      {b.marche?.median != null && (
        /* CRED-2 : cette médiane est un prix BÂTI (par type de bien) — la nommer, pour qu'elle
           coexiste lisiblement avec la « médiane terrain » de l'onglet Marché. */
        <Sec t="Marché — prix de sortie bâti (secteur)">
          médiane bâti <b className="tnum text-mint">{fmtInt(Number(b.marche.median))} €/m²</b> ({b.marche.type_prix},
          {' '}{b.marche.n} ventes ≤ {Math.round(b.marche.radius_m)} m) · fiabilité <b>{b.marche.fiabilite}</b>
          {b.marche.tendance ? <span className="text-txt-mut"> · tendance {b.marche.tendance}</span> : null}
          {/* P14 : fraîcheur DVF — de QUAND datent les prix (période réelle en base) */}
          {b.marche.dvf_couverture?.libelle && (
            <div className="mt-1 text-[11px] text-txt-dim">
              DVF — {b.marche.dvf_couverture.libelle} (dernière transaction en base · millésime en vigueur)
            </div>
          )}
        </Sec>
      )}
      {/* M11 Surface C : la calculette de charge foncière est RAPATRIÉE dans l'onglet Faisabilité
          (le financier au même endroit que la capacité et son explication). */}
      <div className="card-elev px-3 py-2 text-[11px] text-txt-mut">
        La <b className="text-txt">charge foncière</b> (« combien puis-je payer ce terrain ? ») est
        désormais dans l'onglet <b className="text-violet">Faisabilité</b>, avec le calcul détaillé.
      </div>
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
  const [tab, setTab] = useState<'synthese' | Onglet | 'bilan' | 'faisabilite' | 'pourquoi'>('synthese')
  // M19 · migration strangler onglets → tiroirs. MIGRATED = onglets déjà fondus dans la pile
  // Synthèse (leur contenu vit en FicheDrawer). Un clic d'onglet migré ouvre + scrolle le tiroir
  // (au lieu de basculer la vue) ; les onglets non migrés gardent l'ancienne bascule `tab`.
  const [pendingScroll, setPendingScroll] = useState<string | null>(null)
  useEffect(() => {
    if (!pendingScroll || tab !== 'synthese') return
    const t = window.setTimeout(() => {
      const root = document.querySelector(`[data-drawer="${pendingScroll}"]`) as HTMLElement | null
      if (root) {
        const btn = root.querySelector('button')
        if (btn && btn.getAttribute('aria-expanded') === 'false') btn.click()
        root.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
      setPendingScroll(null)
    }, 40)
    return () => window.clearTimeout(t)
  }, [pendingScroll, tab])
  const goDrawer = (key: string) => { setTab('synthese'); setPendingScroll(key) }
  // A6 (post-revue) : recherche DANS la fiche (≠ barre du haut). La loupe de la fiche filtre le
  // CONTENU de la fiche (toutes les lignes tracées, tous onglets), pas le dashboard.
  const [ficheSearchOpen, setFicheSearchOpen] = useState(false)
  const [ficheQuery, setFicheQuery] = useState('')
  const [askOpen, setAskOpen] = useState(false)   // M19 : la carte IA (bas de pile) ouvre l'AskBar
  useEffect(() => { setAskOpen(false) }, [idu])
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
  const meta = f ? STATUT_META[f.statut] : null
  const qLines = f?.lines.filter((l) => l.axis === 'q') ?? []
  const aLines = f?.lines.filter((l) => l.axis === 'a') ?? []
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
  const logementsTxt = fo?.logements_au_sol ? (Array.isArray(fo.logements_au_sol) ? `${fo.logements_au_sol[0]}–${fo.logements_au_sol[1]} logts` : `${fo.logements_au_sol} logts`) : (reglesSdp != null ? `~${fmtInt(reglesSdp)} m² SDP` : 'à estimer')
  // micro-preuve Règles : jauge = part de SDP DÉJÀ consommée (le reste = potentiel).
  const pctConsomme = f?.potentiel_transformation?.pct_consomme
  const reglesArticle = f?.reglement_plu?.zones?.[0]?.articles?.[0]?.reference

  return (
    <aside className="absolute right-0 top-0 z-10 flex h-full w-[400px] max-w-full flex-col border-l border-line bg-surface-1 shadow-2xl">
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

      {/* ═══ M19 · EN-TÊTE + CARTE VERDICT — spec qa/m19/reference (hex/tailles à l'identique) ═══ */}
      <div style={{ padding: '20px 16px 16px', flexShrink: 0, borderBottom: `1px solid ${REF.shell}` }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
          <div style={{ minWidth: 0 }}>
            <p style={{ margin: 0, fontSize: 10, letterSpacing: 1.6, color: '#4a5d53' }}>PARCELLE{f?.commune ? ` · ${f.commune.toUpperCase()}` : ''}</p>
            <p style={{ margin: '5px 0 0', fontFamily: 'ui-monospace,SFMono-Regular,Menlo,monospace', fontSize: 19, color: '#f5fbf8', letterSpacing: .4 }}>{idu.length >= 14 ? `${idu.slice(8, 10)} ${idu.slice(10)}` : idu}</p>
            {/* C3 : adresse jamais tronquée (2 lignes possibles) */}
            <p data-fiche-adresse style={{ margin: '5px 0 0', fontSize: 13, color: f?.adresse ? '#9db5a8' : '#5f7568', lineHeight: 1.45, overflowWrap: 'anywhere' }}>{f?.adresse ?? CLIENT.fiche.adresseAbsente}</p>
            <p style={{ margin: '4px 0 0', fontSize: 12, color: '#5f7568' }}>
              {f?.surface_m2 ? `${fmtM2(f.surface_m2)} · ` : ''}
              {f?.adresse && (
                <a data-fiche-pj href={`https://www.pagesjaunes.fr/annuaire/chercherlespros?ou=${encodeURIComponent(`${f.adresse} ${f.commune ?? ''}`)}`}
                  target="_blank" rel="noreferrer noopener" style={{ color: '#f4d35e', textDecoration: 'none' }} title={CLIENT.fiche.pagesJaunesTip}>
                  {CLIENT.fiche.pagesJaunes} ↗
                </a>
              )}
            </p>
          </div>
          <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
            {/* C4 : cloche = suivi (état réel via WatchButton, style référence) */}
            <WatchButton idu={idu} />
            <ShareButton idu={idu} />
            <button onClick={() => setFicheSearchOpen((o) => { if (o) setFicheQuery(''); return !o })}
              style={{ width: 31, height: 31, border: `1px solid ${ficheSearchOpen ? '#2f7a54' : '#232e29'}`, borderRadius: 9, background: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', color: ficheSearchOpen ? '#7de3ab' : '#7d9488', cursor: 'pointer' }}
              title="Rechercher dans cette fiche">
              <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><circle cx="11" cy="11" r="6" /><path d="m20 20-3.5-3.5" /></svg>
            </button>
            <button onClick={() => select(null)}
              style={{ width: 31, height: 31, border: '1px solid #232e29', borderRadius: 9, background: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#7d9488', cursor: 'pointer' }}
              title="Fermer la fiche">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg>
            </button>
          </div>
        </div>

        {/* CARTE VERDICT — teintée selon le tier (verdict.color) ; la référence montre le cas Chaude. */}
        {f && verdict && (
          <div data-verdict-card style={{ background: `${verdict.color}12`, border: `1px solid ${verdict.color}59`, borderRadius: 13, padding: '15px 16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
              <div style={{ minWidth: 0 }}>
                <p style={{ margin: 0, fontSize: 10, letterSpacing: 1.4, color: '#7d9488' }}>VERDICT LABUSE</p>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 9, marginTop: 5, flexWrap: 'wrap' }}>
                  <span data-badge-verdict style={{ fontSize: 23, fontWeight: 500, color: verdict.color, lineHeight: 1 }}>{verdict.label}</span>
                  {v2Pilote && f.score_v2?.rang != null && (verdict.tier === 'brulante' || verdict.tier === 'chaude') && (
                    <span style={{ fontSize: 12, color: '#7d9488' }}>rang {f.score_v2.rang}</span>
                  )}
                  {verdictEcartee && (
                    <span data-ecartee-motif style={{ fontSize: 12, color: '#7d9488' }}>
                      · {ecarteeMotif} <button onClick={() => goDrawer('pourquoi')} style={{ background: 'none', border: 0, padding: 0, color: '#E8695A', textDecoration: 'underline', cursor: 'pointer', fontSize: 12 }} title={CLIENT.fiche.ecarteeVoirTip}>{CLIENT.fiche.ecarteeVoir}</button>
                    </span>
                  )}
                </div>
              </div>
              {f.score_v2?.mult_base != null && (
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <p style={{ margin: 0, fontSize: 19, fontWeight: 500, color: verdict.color, lineHeight: 1 }}>×{f.score_v2.mult_base.toFixed(1).replace('.', ',')}</p>
                  <p style={{ margin: '3px 0 0', fontSize: 11, color: '#7d9488' }}>plus probable de muter</p>
                </div>
              )}
            </div>
            {/* chips d'arguments : 1 seul violet = le signal chaud (spec) ; le reste vert. */}
            {(proprioSignal || reglesZone || risquesLines.length > 0) && (
              <div style={{ margin: '13px 0 0', paddingTop: 12, borderTop: `1px solid ${verdict.color}33`, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {proprioSignal && (
                  <span style={{ fontSize: 11, background: '#1c1630', color: '#c9b6f2', border: '1px solid #3d3159', borderRadius: 6, padding: '3px 9px' }}>{fmtLibelleBrut(proprioSignal.detail).replace(/\s*—.*$/, '').slice(0, 34)}</span>
                )}
                {reglesZone && (
                  <span style={{ fontSize: 11, background: '#14251c', color: '#8fd8b4', border: '1px solid #26473a', borderRadius: 6, padding: '3px 9px' }}>constructible {reglesZone}</span>
                )}
                {risquesLines.length > 0 && (
                  <span style={{ fontSize: 11, background: '#14251c', color: '#8fd8b4', border: '1px solid #26473a', borderRadius: 6, padding: '3px 9px' }}>{risquesFlags.length === 0 ? '✓ rien à signaler' : `${risquesFlags.length} vigilance`}</span>
                )}
              </div>
            )}
            {/* M-RENOUV : badge segment Renouvellement (CUIVRE) — le verdict reste « Écartée » ;
                libellé doctrinal sous le badge, jamais « opportunité ». */}
            {f.renouvellement && (
              <div data-renouv-badge style={{ margin: '13px 0 0', paddingTop: 12, borderTop: `1px solid ${verdict.color}33` }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 11, fontWeight: 600, background: RENOUV.bg, color: RENOUV.txt, border: `1px solid ${RENOUV.border}`, borderRadius: 6, padding: '3px 9px' }}>
                    Renouvellement — rang {fmtInt(f.renouvellement.rang_segment)}/{fmtInt(f.renouvellement.total_segment)}
                  </span>
                  <button onClick={() => goDrawer('renouvellement')}
                    style={{ background: 'none', border: 0, padding: 0, color: RENOUV.txt, textDecoration: 'underline', cursor: 'pointer', fontSize: 11 }}
                    title="Voir les composantes du score de renouvellement">pourquoi ?</button>
                </div>
                <p data-renouv-libelle style={{ margin: '6px 0 0', fontSize: 11, color: '#9db5a8' }}>{f.renouvellement.libelle}</p>
              </div>
            )}
          </div>
        )}
      </div>

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

      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto overflow-x-clip p-5">
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
          const viabValue = f.viabilisation?.libelle ?? (f.gestionnaires ? 'réseaux renseignés' : '—')
          const confianceValue = f.icd ? `${f.icd.score} %` : `${f.completeness_score} %`
          return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
            {/* rien ne flotte : équipements, alerte accès, Q/A, statut, signaux → DANS les tiroirs (R1). */}

            {/* 1 · RÈGLES D'URBANISME — micro : jauge SDP + zone/article */}
            <RefDrawer id="regles" icon={IC.regles} name="Règles d'urbanisme"
              value={reglesSdp != null ? `${fmtInt(reglesSdp)} m² SDP` : reglesZone ? `zone ${reglesZone}` : 'voir'}
              micro={<MicroJauge pct={pctConsomme ?? 0} label={[reglesZone ? `zone ${reglesZone}` : null, reglesArticle ? `art. ${reglesArticle}` : null].filter(Boolean).join(' · ') || 'PLU'} />}>
              <div className="flex flex-col gap-3">
                <ScoreBar label="Qualité" value={f.q_score} color="#5CE6A1" lines={qLines} tip={SCORE_TIP.q} />
                <TraducteurBloc idu={idu} />
                {f.reglement_plu && <ReglementPluBlock rp={f.reglement_plu} />}
                {f.potentiel_transformation && <TransformationBlock pt={f.potentiel_transformation} />}
                {reglesLines.length > 0 && <div className="flex flex-col gap-1">{reglesLines.map((l, i) => <Line key={i} line={l} />)}</div>}
                {/* M22-B : lettre de vérification de zonage — bouton discret (la barre M20 reste à 7 tuiles) */}
                <a data-lettre-zonage href={`/lettre-zonage/${idu}.pdf`} target="_blank" rel="noreferrer"
                  className="self-start text-[10.5px] text-txt-mut underline decoration-line-2 underline-offset-2 hover:text-mint">
                  Éditer la lettre de vérification de zonage (PDF)
                </a>
              </div>
            </RefDrawer>

            {/* 2 · RISQUES — micro : N segments verts = N couches vérifiées (négatif AFFIRMÉ) */}
            <RefDrawer id="risques" icon={IC.risques} name="Risques"
              value={risquesFlags.length === 0 ? 'rien à signaler' : `${risquesFlags.length} vigilance`}
              micro={<MicroSegments n={risquesClean} label={`${risquesClean} couches`} />}>
              {risquesLines.length
                ? <div className="flex flex-col gap-1">{risquesLines.map((l, i) => <Line key={i} line={l} />)}</div>
                : <p className="text-xs text-txt-dim">Aucun signal sur cet onglet.</p>}
            </RefDrawer>

            {/* 3 · PROPRIÉTAIRE — CARTE ACCENTUÉE VIOLETTE (le signal chaud, une seule sur la fiche) */}
            <RefDrawer id="proprio" icon={IC.proprio} name="Propriétaire" accent={proprioAccent}
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
                    {f.proprietaire_moral.siren && <PatrimoineLink siren={f.proprietaire_moral.siren} />}
                  </div>
                ) : (
                  <div className="card-elev px-3 py-2 text-[11px] text-txt-mut">
                    Propriétaire : personne physique ou non recensé au fichier des personnes morales
                    (identité nominative : workflow SPF/CERFA, jamais automatisée).
                  </div>
                )}
                {proprioLines.length > 0 && <div className="flex flex-col gap-1">{proprioLines.map((l, i) => <Line key={i} line={l} />)}</div>}
              </div>
            </RefDrawer>

            {/* 4 · MARCHÉ — micro : sparkline + volume */}
            <RefDrawer id="marche" icon={IC.marche} name="Marché" valueColor={REF.name}
              value={dvfSecteur?.mediane_prix_m2 != null ? `${fmtInt(dvfSecteur.mediane_prix_m2)} €/m²` : '—'}
              micro={<MicroSpark label={dvfSecteur?.n_ventes ? `${dvfSecteur.n_ventes} ventes secteur` : 'comparables DVF'} />}>
              {marcheLines.length
                ? <div className="flex flex-col gap-1">{marcheLines.map((l, i) => <Line key={i} line={l} />)}</div>
                : <p className="text-xs text-txt-dim">Aucun signal sur cet onglet.</p>}
            </RefDrawer>

            {/* 5 · FAISABILITÉ ET BILAN — micro : 3 données sur une ligne */}
            <RefDrawer id="faisabilite" icon={IC.faisa} name="Faisabilité et bilan" value={logementsTxt}
              micro={<MicroTriple items={[fo?.niveaux ?? 'gabarit', <>SDP <span style={{ color: '#9db5a8' }}>{fo?.surface_plancher_m2 ?? reglesSdp ?? '—'} m²</span></>, 'calcul tracé']} />}>
              <div className="flex flex-col gap-3">
                <FaisabiliteTab idu={idu} />
                <BilanTab idu={idu} />
              </div>
            </RefDrawer>

            {/* 6 · VIABILISATION ET RÉSEAUX — accès, équipements, gestionnaires, permis */}
            <RefDrawer id="viabilisation" icon={IC.viab} name="Viabilisation et réseaux" value={viabValue}>
              <div className="flex flex-col gap-3">
                <ScoreBar label="Accessibilité" value={f.a_score} color="#4ADE96" lines={aLines} tip={SCORE_TIP.a} />
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
              </div>
            </RefDrawer>

            {/* 7 · CONFIANCE ET DONNÉES — score P (pourquoi), ICD, complétude, statut, flags, signaler */}
            <RefDrawer id="confiance" icon={IC.confiance} name="Confiance et données" value={confianceValue}>
              <div className="flex flex-col gap-3">
                <ScoreV2Block idu={idu} />
                {f.icd && <IcdBlockView icd={f.icd} />}
                {v2Pilote && meta && (
                  <div data-statut-matrice-historique className="card-elev flex items-center gap-2 px-3 py-2 text-[11px]">
                    <Tip tip="Classement de la matrice Q×A historique — remplacé par le scoring (P×C)"><span className="text-txt-dim underline decoration-dotted decoration-line-2 underline-offset-4">Statut matrice (historique)</span></Tip>
                    <span className="ml-auto inline-flex items-center gap-1.5" style={{ color: meta.color }}><span className="h-1.5 w-1.5 rounded-full" style={{ background: meta.color }} />{meta.label}</span>
                  </div>
                )}
                <div className="card-elev flex items-center gap-3 px-3 py-2.5">
                  <svg viewBox="0 0 36 36" className="h-11 w-11 shrink-0 -rotate-90">
                    <circle cx="18" cy="18" r="15" fill="none" stroke="#1E2A23" strokeWidth="3.5" />
                    <circle cx="18" cy="18" r="15" fill="none" stroke={completudeColor(f.completeness_score)} strokeWidth="3.5" strokeDasharray={2 * Math.PI * 15} strokeDashoffset={2 * Math.PI * 15 * (1 - f.completeness_score / 100)} strokeLinecap="round" />
                    <text x="18" y="18" transform="rotate(90 18 18)" textAnchor="middle" dominantBaseline="central" className="fill-txt-hi font-display text-[11px] font-bold" style={{ fontVariantNumeric: 'tabular-nums' }}>{f.completeness_score}</text>
                  </svg>
                  <div><div className="label-caps">Complétude · {f.completeness_score} %</div><div className="mt-0.5 text-[11px] text-txt-dim">{f.completeness_score >= 50 ? 'Dossier suffisant pour trancher' : 'Dossier incomplet — à creuser'}</div></div>
                </div>
                {f.flags.length > 0 && <div><p className="label-caps mb-1.5">Signaux additionnels</p><div className="flex flex-col gap-1">{f.flags.map((l, i) => <Line key={i} line={l} />)}</div></div>}
                <SignalerErreur idu={idu} />
              </div>
            </RefDrawer>

            {/* M-RENOUV : tiroir « pourquoi » du segment — les 4 composantes du score,
                sourcées ; wording doctrinal (géométrie favorable, jamais « division »). */}
            {f.renouvellement && (
              <RefDrawer id="renouvellement" icon={IC.faisa} name="Renouvellement — pourquoi ce rang"
                value={`${f.renouvellement.renouv_score}/100`} valueColor={RENOUV.txt}
                micro={<MicroJauge pct={f.renouvellement.renouv_score} label={`rang ${fmtInt(f.renouvellement.rang_commune)}/${fmtInt(f.renouvellement.total_commune)} commune`} />}>
                <div data-renouv-pourquoi style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <p style={{ margin: 0, fontSize: 11.5, lineHeight: 1.5, color: '#9db5a8' }}>
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
                    f.renouvellement.sdp_residuelle_m2 != null ? `SDP résiduelle ${fmtInt(f.renouvellement.sdp_residuelle_m2)} m²` : 'SDP résiduelle —',
                    f.renouvellement.surface_m2 != null ? `assiette ${fmtM2(f.renouvellement.surface_m2)}` : 'assiette —',
                    `rang île ${fmtInt(f.renouvellement.rang_segment)}/${fmtInt(f.renouvellement.total_segment)}`,
                  ]} />
                  <p style={{ margin: 0, fontSize: 10.5, lineHeight: 1.5, color: REF.dim }}>
                    Potentiel physique et réglementaire — ni une mise en vente prévisible, ni une garantie de constructibilité.
                  </p>
                </div>
              </RefDrawer>
            )}

            {/* Pourquoi pas — conditionnel (écartée / flaggée) */}
            {(verdictEcartee || f.lines.some((l) => l.result === 'SOFT_FLAG')) && (
              <RefDrawer id="pourquoi" icon={IC.risques} name="Pourquoi pas ?" value="motifs">
                <PourquoiPasTab idu={idu} />
              </RefDrawer>
            )}

            {/* CARTE IA — EN BAS de la pile (jamais en tête), une seule ligne (spec) */}
            <button onClick={() => setAskOpen(true)} data-askbar-open
              style={{ background: '#110d1b', border: '1px solid #372c58', borderRadius: 12, padding: '12px 15px', display: 'flex', alignItems: 'center', gap: 9, whiteSpace: 'nowrap', overflow: 'hidden', color: '#c9b6f2', cursor: 'pointer', width: '100%', textAlign: 'left' }}>
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" /><path d="M18 16l.7 1.9L21 18.6l-2.3.7L18 21l-.7-1.7L15 18.6l2.3-.7z" /></svg>
              <span style={{ flex: 1, fontSize: 13, color: '#d8ccf5', overflow: 'hidden', textOverflow: 'ellipsis' }}>{CLIENT.fiche.ia.accroche}</span>
              <span style={{ fontSize: 13, color: '#8a6ff0', flexShrink: 0 }}>{CLIENT.fiche.ia.demander}</span>
            </button>
            {askOpen && <AskBar idu={idu} zone={null} startOpen onClose={() => setAskOpen(false)} />}

            {/* ═══ BARRE D'ACTIONS · 2 niveaux (spec) — DANS le flux (fin du « double écran de vide ») ═══ */}
            <div style={{ marginTop: 7, paddingTop: 14, borderTop: '1px solid #1a2320' }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 11 }}>
                <PipelineButton idu={idu} />
                <ProjetButton idu={idu} />
              </div>
              {/* BLOC SEGMENTÉ UNIQUE — 6 tuiles (spec), plus 6 boutons séparés (C5 réglé structurellement). */}
              {/* M20-B1 : bloc segmenté UNIQUE, 6→7 colonnes (PDF·Dossier·Financier·1950·Cadastre·Maps·Courrier),
                  un seul rang, pas de menu ni de scroll horizontal (réf. M19 conservée). */}
              <div style={{ background: '#0e1311', border: '1px solid #1e2823', borderRadius: 11, display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', overflow: 'hidden' }}>
                <a href={pdfUrl(idu, calculette)} target="_blank" rel="noreferrer" style={{ padding: '10px 0 9px', textAlign: 'center', borderRight: '1px solid #16201c', color: '#8fd8b4', textDecoration: 'none', display: 'block' }} title={calculette ? 'PDF (avec votre charge foncière)' : 'Exporter la fiche en PDF'}>
                  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /><path d="M12 12v5" /><path d="m9.5 14.5 2.5 2.5 2.5-2.5" /></svg>
                  <p style={{ margin: '5px 0 0', fontSize: 10, color: '#7d9488' }}>PDF</p>
                </a>
                <a href={`/dossier/${idu}.pdf`} target="_blank" rel="noreferrer" style={{ padding: '10px 0 9px', textAlign: 'center', borderRight: '1px solid #16201c', color: '#8fd8b4', textDecoration: 'none', display: 'block' }} title="Dossier parcelle PDF brandé">
                  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /></svg>
                  <p style={{ margin: '5px 0 0', fontSize: 10, color: '#7d9488' }}>Dossier</p>
                </a>
                <BanquierButton idu={idu} />
                {f.coords && (
                  <button onClick={() => { setFlyTo({ center: f.coords, zoom: 18 }); setModule('temps') }} style={{ padding: '10px 0 9px', textAlign: 'center', borderRight: '1px solid #16201c', color: '#8fd8b4', background: 'none', border: 0, cursor: 'pointer' }} title="Ce terrain en 1950 — comparateur temporel">
                    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}><path d="M12 8v4l3 2" /><path d="M3.05 11a9 9 0 1 1 .5 4" /><path d="M3 21v-5h5" /></svg>
                    <p style={{ margin: '5px 0 0', fontSize: 10, color: '#7d9488' }}>1950</p>
                  </button>
                )}
                {f.coords && (
                  <a data-cadastre-link href={`https://www.geoportail.gouv.fr/carte?c=${f.coords[0]},${f.coords[1]}&z=19&l0=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2::GEOPORTAIL:OGC:WMTS(1)&l1=CADASTRALPARCELS.PARCELLAIRE_EXPRESS::GEOPORTAIL:OGC:WMTS(1)&permalink=yes`} target="_blank" rel="noreferrer noopener" style={{ padding: '10px 0 9px', textAlign: 'center', borderRight: '1px solid #16201c', color: '#8fd8b4', textDecoration: 'none', display: 'block' }} title={CLIENT.fiche.export.cadastreTip}>
                    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}><path d="m9 4 6 2 6-2v14l-6 2-6-2-6 2V6z" /><path d="M9 4v14" /><path d="M15 6v14" /></svg>
                    <p style={{ margin: '5px 0 0', fontSize: 10, color: '#7d9488' }}>Cadastre</p>
                  </a>
                )}
                {f.coords && (
                  <a data-maps-link href={`https://www.google.com/maps/search/?api=1&query=${f.coords[1]},${f.coords[0]}`} target="_blank" rel="noreferrer" style={{ padding: '10px 0 9px', textAlign: 'center', borderRight: '1px solid #16201c', color: '#8fd8b4', textDecoration: 'none', display: 'block' }} title="Ouvrir dans Google Maps (épingle sur la parcelle)">
                    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0" /><circle cx="12" cy="10" r="3" /></svg>
                    <p style={{ margin: '5px 0 0', fontSize: 10, color: '#7d9488' }}>Maps</p>
                  </a>
                )}
                {/* M20-A · 7e tuile : Courrier propriétaire → ouvre le module M09 (setModule) avec la
                    parcelle courante (selectedIdu) pré-remplie. Même moteur que l'entrée Outils, aucune
                    divergence. Boussole gérée par M09 (aucune identité de personne physique). */}
                <button data-courrier-tile onClick={() => setModule('courriers')}
                  style={{ padding: '10px 0 9px', textAlign: 'center', color: '#8fd8b4', background: 'none', border: 0, cursor: 'pointer' }}
                  title={CLIENT.fiche.export.courrierTip}>
                  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" /></svg>
                  <p style={{ margin: '5px 0 0', fontSize: 10, color: '#7d9488' }}>{CLIENT.fiche.export.courrier}</p>
                </button>
              </div>
              <p style={{ marginTop: 11, fontSize: 11, lineHeight: 1.45, color: '#5f7568' }}>
                Estimations indicatives issues de données publiques — ni conseil juridique/notarial ni garantie de constructibilité. <span data-disclaimer-cu style={{ color: '#7d9488' }}>Ces informations ne remplacent pas un certificat d'urbanisme.</span>
              </p>
            </div>
          </div>
          )
        })()}
      </div>


    </aside>
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
  // C6 · « Financier » (ex-Banquier) — rendu en CELLULE du bloc segmenté (spec référence).
  const cellStyle = { padding: '10px 0 9px', textAlign: 'center' as const, background: 'none', border: 0, borderRight: '1px solid #16201c', cursor: 'pointer', width: '100%' }
  const icon = <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}><rect x="3" y="6" width="18" height="12" rx="2" /><circle cx="12" cy="12" r="2.5" /></svg>
  if (etat === 'pret') return (
    <a href={url} target="_blank" rel="noreferrer" style={{ ...cellStyle, color: '#7de3ab', textDecoration: 'none', display: 'block' }} title="Note de financement prête — ouvrir le PDF">
      {icon}<p style={{ margin: '5px 0 0', fontSize: 10, color: '#7de3ab' }}>{CLIENT.fiche.export.banquierPret}</p>
    </a>
  )
  if (etat === 'encours') return (
    <span style={{ ...cellStyle, color: '#8fd8b4', display: 'block' }}>
      {icon}<p style={{ margin: '5px 0 0', fontSize: 10, color: '#7d9488' }}>{CLIENT.fiche.export.banquierEnCours}</p>
    </span>
  )
  return (
    <button onClick={lancer} data-banquier-btn style={{ ...cellStyle, color: '#8fd8b4' }}
      title={etat === 'erreur' ? 'Génération impossible — réessayer' : CLIENT.fiche.export.banquierTip}>
      {icon}<p style={{ margin: '5px 0 0', fontSize: 10, color: '#7d9488' }}>{etat === 'erreur' ? CLIENT.fiche.export.banquierErreur : CLIENT.fiche.export.finance}</p>
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
        <span className="label-caps text-[10px] text-violet">✦ Traduire ma zone en français courant</span>
        <span className="text-[11px] text-txt-dim">{open ? 'replier ▴' : 'déplier ▾'}</span>
      </button>
      {open && (
        <div className="mt-2">
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
