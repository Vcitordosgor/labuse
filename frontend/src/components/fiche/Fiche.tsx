import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Tip } from '../Tip'
import { createContext, useContext, useEffect, useMemo, useState, useRef, type ReactNode } from 'react'
import { addToPipeline, ajouterParcelle, ApiError, faisabiliteExplain, getCalculetteDefaults, getDossierStatut, getExplain, getFaisabilite, getFiche, getModeB, getMoi, getOrthoEquipements, getPipelineForParcel, getProjets, getWatch, is429, onePagerUrl, pdfUrl, postChargeFonciere, postSignalement, preDossierUrl, projetsPourParcelle, toggleWatch, type CalculetteDefaults } from '../../lib/api'
import { verdictMeta } from '../../lib/status'
import { fmtDateNum, fmtEurCompact, fmtInt, fmtM2, fmtLibelleBrut, iduComplet, iduCourt } from '../../lib/format'
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
  contexte: drSvg(<><circle cx="12" cy="10" r="3" /><path d="M12 21c-4-4-7-7.5-7-11a7 7 0 0 1 14 0c0 3.5-3 7-7 11z" /></>),
}

// M55-L point 6 : `TheatreCompteur` (« N parcelles analysées ») retiré de la fiche → 0-caller,
// fonction supprimée. Le champ back `parc_analysees` reste servi (autres usages / PDF).

function RefChevron({ open, accent }: { open: boolean; accent?: boolean }) {
  return <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke={accent ? REF.chevAccent : REF.chev} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"
    style={{ flexShrink: 0, transform: open ? 'rotate(90deg)' : 'none', transition: 'transform .15s' }}><path d="m9 6 6 6-6 6" /></svg>
}

// M55-L point 10 — ACCORDÉON EXCLUSIF des tiroirs de la fiche : un seul ouvert à la fois, zéro
// ouvert légal (initial). État à champ unique (store.ficheTiroir[idu]), exposé par contexte pour
// éviter le prop-drilling sur les 11 tiroirs. `openId` = id du tiroir ouvert (null = tout fermé).
const FicheAccordionCtx = createContext<{ openId: string | null; toggle: (id: string) => void }>({ openId: null, toggle: () => {} })

/** M19 · tiroir de la référence : fermé = icône + nom + valeur clé + MICRO-PREUVE (jauge, segments,
 *  sparkline, pastilles, 3 données) ; ouvert = le détail (blocs existants). Une seule carte peut être
 *  `accent` (violet) = le signal chaud. Rien n'est supprimé : le détail vit dans le corps déplié.
 *  M55-L point 10 : l'état `open` est CONTRÔLÉ par l'accordéon (contexte), plus d'état local. */
function RefDrawer({ id, icon, name, value, valueColor, accent, micro, children }: {
  id?: string; icon: ReactNode; name: string; value?: ReactNode; valueColor?: string
  accent?: boolean; micro?: ReactNode; children?: ReactNode
}) {
  const acc = useContext(FicheAccordionCtx)
  const open = !!id && acc.openId === id
  return (
    <div data-drawer={id} style={{ background: accent ? REF.accent : REF.card, border: `1px solid ${accent ? REF.accentBorder : REF.cardBorder}`, borderRadius: 12, padding: '13px 15px', scrollMarginTop: 8 }}>
      <button onClick={() => id && children && acc.toggle(id)} aria-expanded={open}
        style={{ display: 'flex', alignItems: 'center', gap: 11, width: '100%', background: 'none', border: 0, padding: 0, cursor: children ? 'pointer' : 'default', textAlign: 'left', color: accent ? REF.violet : REF.mint }}>
        <span style={{ display: 'flex', flexShrink: 0 }}>{icon}</span>
        {/* M30-revue A3 : le NOM passe à la ligne au lieu de s'écraser en « V » ou « … » —
            la valeur garde son ellipse, le titre reste toujours lisible en entier. */}
        <span style={{ flex: 1, fontSize: 14, color: REF.name, minWidth: 90, lineHeight: 1.25 }}>{name}</span>
        {value != null && <span style={{ fontSize: 15, fontWeight: 500, color: valueColor ?? (accent ? REF.violet : REF.mint), whiteSpace: 'nowrap', flexShrink: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis' }}>{value}</span>}
        {children && <RefChevron open={open} accent={accent} />}
      </button>
      {micro && <div style={{ marginTop: 10 }}>{micro}</div>}
      {open && children && <div style={{ marginTop: 12, paddingTop: 12, borderTop: `1px solid ${accent ? REF.accentBorder : '#1a231e'}` }}>{children}</div>}
    </div>
  )
}

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
// M55-O phase 2.2 : composant ScoreBar retiré (0-caller après retrait des jauges Qualité/Accessibilité).

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

// EXPRESS-01 · bouton « copier l'IDU » — copie la chaîne BRUTE 14 car. (sans espace),
// celle qu'on colle dans GPU/DVF/SIG. Style référence (bouton 31×31, retour visuel vert).
function CopyIdu({ value }: { value: string }) {
  const [ok, setOk] = useState(false)
  const copier = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setOk(true)
      setTimeout(() => setOk(false), 1400)
    } catch { /* presse-papier indisponible : on ne fait rien de destructeur */ }
  }
  return (
    <button onClick={copier} data-fiche-copy-idu aria-label="Copier l’IDU"
      style={{ width: 26, height: 26, border: `1px solid ${ok ? '#2f7a54' : '#232e29'}`, borderRadius: 8, background: ok ? '#101d16' : 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', color: ok ? '#7de3ab' : '#7d9488', cursor: 'pointer', flexShrink: 0 }}
      title={ok ? 'IDU copié' : 'Copier l’IDU (14 caractères, sans espace)'}>
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
      className={`flex h-8 flex-1 items-center justify-center whitespace-nowrap rounded-lg px-3 text-xs font-medium ${
        inPipe ? 'cursor-default border border-line-2 bg-surface-3 text-txt-mut' : 'bg-mint text-mint-ink hover:brightness-110'}`}
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
  const defs = useQuery({ queryKey: ['calculette-defaults'], queryFn: getCalculetteDefaults, staleTime: Infinity })
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
                  ? <>Écart : prix demandé {fmtEurCompact(d.ecart_negociation.prix_demande_eur)} − prix d'achat max {fmtEurCompact(d.ecart_negociation.prix_achat_max_eur)} = <b>surcoût de {fmtEurCompact(d.ecart_negociation.demande_moins_max_eur)}</b> (+{d.ecart_negociation.demande_moins_max_pct} % au-dessus du max admissible).</>
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
                  ? <>✓ Supportable — le terrain peut valoir {fmtEurCompact(achat.prix_demande_eur)} ; marge de {fmtEurCompact(achat.ecart_eur)} ({achat.ecart_pct > 0 ? '+' : ''}{achat.ecart_pct} %) sous votre charge foncière.</>
                  : <>✗ Trop cher — à {fmtEurCompact(achat.prix_demande_eur)}, l'opération dépasse de {fmtEurCompact(Math.abs(achat.ecart_eur))} ({achat.ecart_pct} %) ce que vos hypothèses supportent.</>}
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
  if (!mb.disponible || !mb.composantes) return null
  const c = mb.composantes
  const [bMin, bMax] = c.travaux.bornes
  return (
    <RefDrawer id="mode-b" icon={IC.faisa} name="Mode B — Réhabilitation"
      value={mb.negatif ? 'bilan négatif' : `~${mb.achat_max_libelle ?? ''}`}
      valueColor={mb.negatif ? '#E8B44C' : undefined}
      micro={<span style={{ fontSize: 10, color: '#8FA69A' }}>Estimé — hypothèse travaux à ajuster</span>}>
      <div data-mode-b style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {mb.negatif ? (
          <p style={{ margin: 0, fontSize: 11.5, lineHeight: 1.5, color: '#E8B44C' }}>{mb.message_negatif}</p>
        ) : (
          <p style={{ margin: 0, fontSize: 12.5, color: '#f5fbf8' }}>
            Prix d'achat max réhabilitation : <b data-mode-b-achat>~{mb.achat_max_libelle ?? '—'}</b>
            <span style={{ marginLeft: 6, fontSize: 10.5, color: '#8FA69A' }}>(Estimé — jamais un prix Sourcé : l'hypothèse travaux est toujours estimée)</span>
          </p>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
            <span style={{ color: '#9db5a8' }}>Surface réhabilitable</span>
            <span style={{ color: '#f5fbf8' }}>~{fmtInt(c.surface.shab_rehabilitable_m2)} m² hab.</span>
          </div>
          <p style={{ margin: 0, fontSize: 10, color: '#8FA69A' }}>
            emprise {fmtInt(c.surface.emprise_bati_m2)} m² <b style={{ color: '#5CE6A1' }}>Sourcé</b> ({c.surface.source_emprise}) × {c.surface.niveaux} niveau(x){' '}
            <b style={{ color: c.surface.niveaux_reels ? '#5CE6A1' : '#E8B44C' }}>{c.surface.niveaux_reels ? 'Sourcé' : 'Estimé'}</b>
            {' '}— {c.surface.niveaux_etiquette}
          </p>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
            <span style={{ color: '#9db5a8' }}>Prix de sortie (revente)</span>
            <span style={{ color: '#f5fbf8' }}>{fmtInt(c.prix_sortie.prix_m2)} €/m² <b style={{ color: '#5CE6A1', fontSize: 10 }}>Sourcé DVF</b></span>
          </div>
          <p style={{ margin: 0, fontSize: 10, color: '#8FA69A' }}>{c.prix_sortie.libelle}</p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
            <span style={{ color: '#9db5a8', flex: 1 }}>Coût travaux <b style={{ color: '#E8B44C', fontSize: 10 }}>ESTIMÉ</b></span>
            <input data-mode-b-travaux type="number" min={bMin} max={bMax} step={50} value={travaux}
              onChange={(e) => setModeB({ travauxM2: Number(e.target.value) })}
              style={{ width: 80, background: '#0d1512', border: '1px solid #26302B', borderRadius: 6, color: '#f5fbf8', padding: '3px 6px', fontSize: 11 }} />
            <span style={{ color: '#9db5a8' }}>€/m²</span>
          </div>
          <p style={{ margin: 0, fontSize: 10, color: '#8FA69A' }}>{c.travaux.libelle}</p>
          <p style={{ margin: 0, fontSize: 10, color: '#8FA69A' }}>{c.frais_marge.libelle}</p>
        </div>
        {/* M44 — SORTIE LOCATIVE : côte à côte avec la revente, jamais fusionnée. Loyer au plafond
            réglementaire Sourcé (ou marché Estimé) ; prix d'achat max à rendement cible. Mention fiscale. */}
        {mb.sortie_locative && (
          <div data-mode-b-locatif style={{ borderTop: '1px solid #24312b', paddingTop: 8, display: 'flex', flexDirection: 'column', gap: 4 }}>
            <p style={{ margin: 0, fontSize: 12, color: '#f5fbf8', fontWeight: 600 }}>Sortie locative</p>
            {mb.sortie_locative.negatif ? (
              <p style={{ margin: 0, fontSize: 11.5, color: '#E8B44C' }}>{mb.sortie_locative.message_negatif}</p>
            ) : (
              <p style={{ margin: 0, fontSize: 11.5, color: '#f5fbf8' }}>
                Prix d'achat max : <b>~{mb.sortie_locative.achat_max_libelle}</b>
                <span style={{ marginLeft: 4, fontSize: 10, color: '#8FA69A' }}>(Estimé)</span> à rendement cible {mb.sortie_locative.rendement_cible_pct} %
                <span style={{ marginLeft: 4, fontSize: 10, color: '#8FA69A' }}>(paramètre client)</span>
              </p>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: '#9db5a8' }}>Loyer retenu</span>
              <span style={{ color: '#f5fbf8' }}>~{fmtInt(mb.sortie_locative.loyer.annuel_eur)} €/an · {mb.sortie_locative.loyer.m2_mois_effectif} €/m²/mois</span>
            </div>
            <p style={{ margin: 0, fontSize: 10, color: '#8FA69A' }}>
              {mb.sortie_locative.loyer.etiquette}{mb.sortie_locative.loyer.coef_surface ? ` · coefficient de surface ${mb.sortie_locative.loyer.coef_surface}` : ''}
            </p>
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
  // M55-L point 10 — accordéon EXCLUSIF des tiroirs (store, par parcelle). openId = tiroir ouvert
  // (null = tout fermé). La valeur du contexte est mémoïsée (identité stable tant que rien ne bouge).
  const tiroirOuvert = useApp((s) => s.ficheTiroir[idu] ?? null)
  const setFicheTiroir = useApp((s) => s.setFicheTiroir)
  const accValue = useMemo(
    () => ({ openId: tiroirOuvert, toggle: (id: string) => setFicheTiroir(idu, tiroirOuvert === id ? null : id) }),
    [tiroirOuvert, idu, setFicheTiroir],
  )
  useEffect(() => {
    if (!pendingScroll || tab !== 'synthese') return
    const t = window.setTimeout(() => {
      // le tiroir est déjà ouvert par l'état (goDrawer l'a posé) → il ne reste qu'à le faire défiler.
      const root = document.querySelector(`[data-drawer="${pendingScroll}"]`) as HTMLElement | null
      if (root) root.scrollIntoView({ behavior: 'smooth', block: 'start' })
      setPendingScroll(null)
    }, 60)
    return () => window.clearTimeout(t)
  }, [pendingScroll, tab])
  // M55-L point 10 : goDrawer OUVRE le tiroir cible (accordéon exclusif → ferme les autres) puis
  // le fait défiler à l'écran (le scroll suit, l'utilisateur n'est jamais perdu).
  const goDrawer = (key: string) => { setTab('synthese'); setFicheTiroir(idu, key); setPendingScroll(key) }
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
  const logementsTxt = delaisse ? `délaissé (${delaisse.surface_m2} m²)`
    : fo?.logements_au_sol ? (Array.isArray(fo.logements_au_sol) ? `${fo.logements_au_sol[0]}–${fo.logements_au_sol[1]} logts` : `${fo.logements_au_sol} logts`) : (reglesSdp != null ? `~${fmtInt(reglesSdp)} m² SDP` : 'à estimer')
  // micro-preuve Règles : jauge = part de SDP DÉJÀ consommée (le reste = potentiel).
  const pctConsomme = f?.potentiel_transformation?.pct_consomme
  const reglesArticle = f?.reglement_plu?.zones?.[0]?.articles?.[0]?.reference
  // M55-N point 8 : l'en-tête « Règles d'urbanisme » porte une CONTRAINTE de gabarit (hauteur max)
  // — plus la SDP résiduelle, qui vivait AUSSI dans l'en-tête « Faisabilité » (doublon M55-L P14).
  // Faisabilité garde la SDP ; la SDP reste accessible dans le corps du tiroir (potentiel/faisa).
  // Hauteur absente (faisabilité non calculée) → pas de valeur d'en-tête (le micro-jauge porte
  // déjà zone + article), jamais la SDP ni un doublon du zonage.
  const reglesGabarit = fo?.hauteur_m != null ? `${fo.hauteur_m} m max` : undefined
  // Dette #10 : drapeaux EBC / ER (information seule), dérivés des prescriptions PLU du run servi.
  const presc = f ? prescriptionsInfo(f.lines) : null

  // M55-L point 4 : conteneur fiche élargi de 10 % — 400 → 440px (valeur unique ici). `max-w-full`
  // garde la fiche dans l'écran aux petites largeurs (aucun débordement horizontal).
  return (
    <FicheAccordionCtx.Provider value={accValue}>
    <aside className="absolute right-0 top-0 z-10 flex h-full w-[440px] max-w-full flex-col border-l border-line bg-surface-1 shadow-2xl">
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
            {/* EXPRESS-01 · IDU COMPLET 14 car. en position primaire (mono) + bouton copier.
                La forme courte (section+numéro) devient un rappel secondaire, jamais l'inverse. */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '5px 0 0' }}>
              <p data-fiche-idu style={{ margin: 0, fontFamily: 'ui-monospace,SFMono-Regular,Menlo,monospace', fontSize: 19, color: '#f5fbf8', letterSpacing: .4 }}>{iduComplet(idu) || 'Absent'}</p>
              {iduComplet(idu) && <CopyIdu value={iduComplet(idu)} />}
            </div>
            {iduComplet(idu) && iduCourt(idu) !== iduComplet(idu) && (
              <p data-fiche-idu-court style={{ margin: '3px 0 0', fontSize: 11, letterSpacing: .3, color: '#5f7568' }}>{iduCourt(idu)}</p>
            )}
            {/* C3 : adresse jamais tronquée (2 lignes possibles) */}
            {/* M55-L point 2 : adresse absente → « i » explicatif (absence réelle dans la source,
                pas un défaut de l'outil). Contenu depuis la source unique CLIENT.fiche. */}
            <p data-fiche-adresse style={{ margin: '5px 0 0', fontSize: 13, color: f?.adresse ? '#9db5a8' : '#5f7568', lineHeight: 1.45, overflowWrap: 'anywhere' }}>
              {f?.adresse ?? CLIENT.fiche.adresseAbsente}
              {!f?.adresse && (
                <Tip side="top" tip={CLIENT.fiche.adresseAbsenteInfo}>
                  <span data-adresse-absente-i role="button" tabIndex={0} aria-label="Pourquoi l’adresse manque"
                    style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 14, height: 14, marginLeft: 6, borderRadius: 999, border: '1px solid #2f7a54', color: '#7d9488', fontSize: 9, fontWeight: 700, lineHeight: 1, cursor: 'help', verticalAlign: 'middle' }}>i</span>
                </Tip>
              )}
            </p>
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

        {/* M55-O phase 2.1 — BANDEAU DE 4 CHIFFRES (toujours visible, factuel, aucun avis) :
            Surface · Zone · SDP disponible · Prix secteur €/m². Valeurs SERVIES (jamais en dur) ;
            une valeur absente → « — » (jamais un zéro trompeur ni un blanc muet). Habillage affiné
            en phase 3. */}
        {f && (() => {
          const cells = [
            { l: 'Surface', v: f.surface_m2 != null ? `${fmtInt(f.surface_m2)} m²` : '—' },
            { l: 'Zone', v: reglesZone ?? '—' },
            { l: 'SDP dispo.', v: reglesSdp != null ? `${fmtInt(reglesSdp)} m²` : '—' },
            { l: 'Prix secteur', v: dvfSecteur?.mediane_prix_m2 != null ? `${fmtInt(dvfSecteur.mediane_prix_m2)} €/m²` : '—' },
          ]
          return (
            <div data-bandeau-chiffres style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', border: '1px solid #1e2823', borderRadius: 11, overflow: 'hidden', background: '#0e1311' }}>
              {cells.map((c, i) => (
                <div key={c.l} style={{ padding: '8px 6px', textAlign: 'center', borderLeft: i ? '1px solid #16201c' : 'none' }}>
                  <p style={{ margin: 0, fontSize: 10, letterSpacing: 0.8, color: '#5f7568', textTransform: 'uppercase' }}>{c.l}</p>
                  <p style={{ margin: '3px 0 0', fontSize: 15, color: '#dfeee7', fontWeight: 500, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.v}</p>
                </div>
              ))}
            </div>
          )
        })()}

        {/* M55-L point 5 — VERDICT À LA DEMANDE. À l'ouverture (verdict non encore demandé pour
            cette parcelle dans la session), un BOUTON vert remplace le bloc verdict — l'avis n'est
            jamais imposé à qui veut d'abord des informations. C'est le SEUL élément vert de ce
            niveau. Au clic, le bloc verdict complet se déploie (mémorisé par parcelle, session).
            Vaut aussi en mode factuel (le bouton apparaît pareillement : rien n'est imposé, tout
            est accessible). Les PDF gardent le verdict sans condition (rail back inchangé). */}
        {f && verdict && !verdictRevele && (
          // M55-N point 4 : étoile retirée ; largeur AJUSTÉE AU CONTENU (alignSelf flex-start, plus
          // de width:100%) — le bouton n'occupe plus toute la largeur de la fiche. Libellé « Demander
          // à LABUSE d'analyser la parcelle » (strings) ; sous-titre conservé. Comportement inchangé.
          <button data-demander-analyse onClick={() => revelerVerdict(idu)}
            style={{ alignSelf: 'flex-start', maxWidth: '100%', display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 3, background: 'linear-gradient(180deg,#2FE0A0,#22c48b)', color: '#06130C', borderRadius: 13, border: 'none', padding: '13px 18px', cursor: 'pointer', textAlign: 'left', boxShadow: '0 0 22px rgba(47,224,160,0.28)' }}
            title="Déployer le verdict, le score et « pourquoi »">
            <span style={{ fontSize: 14.5, fontWeight: 700 }}>{CLIENT.fiche.demanderAnalyse}</span>
            <span style={{ fontSize: 11.5, fontWeight: 500, color: '#0a2419', opacity: .85 }}>{CLIENT.fiche.demanderAnalyseSous}</span>
          </button>
        )}
        {/* CARTE VERDICT — teintée selon le tier (verdict.color) ; la référence montre le cas Chaude. */}
        {f && verdict && verdictRevele && (
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
                  <p style={{ margin: 0, fontSize: 19, fontWeight: 500, color: signalEcarte ? '#8C7468' : verdict.color, lineHeight: 1 }}>×{f.score_v2.mult_base.toFixed(1).replace('.', ',')}</p>
                  <p style={{ margin: '3px 0 0', fontSize: 11, color: '#7d9488' }}>
                    {signalEcarte ? 'signal brut' : 'plus probable d’être vendue'}
                    {f.score_v2.verbal?.info && (
                      <span title={f.score_v2.verbal.info} style={{ marginLeft: 4, cursor: 'help', borderBottom: '1px dotted #5f7568' }}>ⓘ</span>
                    )}
                  </p>
                  {/* mot d'échelle : en couleur du tier quand servable ; ATTÉNUÉ quand écartée à
                      signal fort (le mot ne doit pas faire promesse à côté d'un statut mort). */}
                  {f.score_v2.verbal?.mot && (
                    <p style={{ margin: '2px 0 0', fontSize: 11.5, fontWeight: 600, color: signalEcarte ? '#8C7468' : verdict.color }}>
                      {signalEcarte ? <>{f.score_v2.verbal.mot} <span style={{ fontWeight: 500, color: '#7d9488' }}>· écartée</span></> : f.score_v2.verbal.mot}
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
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9.5, color: '#5f7568', marginBottom: 3 }}>
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
                  <p data-freq style={{ margin: '9px 0 0', fontSize: 11, color: '#9db5a8', borderLeft: '3px solid #5fd0a8', paddingLeft: 8 }}>
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

        {/* M52 L4 — rappel DISCRET quand la mesure de la commune est dégradée (échantillon limité) :
            le classement reste, la fréquence exacte est indicative. Jamais une excuse vague. */}
        {f?.qualite_commune?.degradee && (
          <p data-qualite-commune-rappel style={{ margin: '9px 0 0', fontSize: 10.5, lineHeight: 1.5, color: '#9db5a8' }}>
            <span style={{ color: '#e8b84d' }}>◐</span> {f.qualite_commune.libelle}
          </p>
        )}

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

        {/* Dette #10 — drapeaux EBC / ER : INFORMATION seule, jamais une exclusion. Dérivés des
            prescriptions PLU déjà servies par la cascade ; aucun impact sur le verdict ni le score. */}
        {presc && (presc.ebc || presc.ers.length > 0) && (
          <div data-prescriptions-badges style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {presc.ebc && (
              <Tip tip="Espace boisé classé — information. Toute construction est interdite sur l’emprise boisée (Art. L113-1 CU). N’exclut pas la parcelle.">
                <span data-badge-ebc className="rounded-full px-2 py-0.5 text-[11px] font-medium" style={{ background: '#5CE6A122', color: '#5CE6A1' }}>
                  partiellement en EBC{presc.ebc.coverage != null ? ` (~${presc.ebc.coverage} %)` : ''}
                </span>
              </Tip>
            )}
            {presc.ers.map((er, i) => (
              <Tip key={i} tip="Emplacement réservé — information. Emprise grevée au profit d’un projet public (servitude levable si l’ER est abandonné). N’exclut pas la parcelle.">
                <span data-badge-er className="rounded-full px-2 py-0.5 text-[11px] font-medium" style={{ background: '#e8b84d22', color: '#e8b84d' }}>
                  emplacement réservé{er.num ? ` n°${er.num}` : ''}
                </span>
              </Tip>
            ))}
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
          // M30 item 7 : la value dupliquait « Viabilisation » et écrasait le titre du tiroir en « V »
          const viabValue = f.viabilisation?.libelle?.replace(/^Viabilisation\s+/i, '') ?? (f.gestionnaires ? 'réseaux renseignés' : '—')
          // M36 Lot B : plus de repli sur la Complétude (quasi-constante) — ICD ou rien.
          const confianceValue = f.icd ? `${f.icd.score} %` : '—'
          return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
            {/* rien ne flotte : équipements, alerte accès, Q/A, statut, signaux → DANS les tiroirs (R1). */}

            {/* M55-L point 11 — BOUTONS IA EN TÊTE de fiche (mauve = couleur IA LABUSE, cf. « + Projet »
                / « Pourquoi ce score »), mis en valeur, visibles sans défilement dès l'ouverture.
                « Une question ? » (AskBar) + « Synthèse ». Même palette violette qu'avant (aucun
                nouveau composant), remontée + encadrée. */}
            <div data-ia-tete style={{ display: 'flex', flexDirection: 'column', gap: 8, border: '1px solid #2c2348', background: 'rgba(124,92,240,0.05)', borderRadius: 13, padding: 9 }}>
              <button onClick={() => setAskOpen(true)} data-askbar-open
                style={{ background: '#140f22', border: '1px solid #3d3163', borderRadius: 10, padding: '11px 13px', display: 'flex', alignItems: 'center', gap: 9, whiteSpace: 'nowrap', overflow: 'hidden', color: '#c9b6f2', cursor: 'pointer', width: '100%', textAlign: 'left' }}>
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" /><path d="M18 16l.7 1.9L21 18.6l-2.3.7L18 21l-.7-1.7L15 18.6l2.3-.7z" /></svg>
                <span style={{ flex: 1, fontSize: 13, color: '#d8ccf5', overflow: 'hidden', textOverflow: 'ellipsis' }}>{CLIENT.fiche.ia.accroche}</span>
                <span style={{ fontSize: 13, color: '#8a6ff0', flexShrink: 0 }}>{CLIENT.fiche.ia.demander}</span>
              </button>
              {askOpen && <AskBar idu={idu} zone={null} startOpen onClose={() => setAskOpen(false)} />}
              <SyntheseIA idu={idu} />
            </div>

            {/* M52 L2 — ADAPTATION déclassée à signal fort : le Mode B (le « et si ») remonte en 2,
                juste après le verdict, ouvert. Pour un tier servable il reste dans l'ÉCONOMIE (③). */}
            {signalEcarte && f.mode_b?.disponible && <ModeBDrawer idu={idu} initial={f.mode_b} />}

            {/* ② DROIT DU SOL — Règles d'urbanisme (zonage M40, procédure M41). Ouvert si servable. */}
            <RefDrawer id="regles" icon={IC.regles} name="Règles d'urbanisme"
              value={reglesGabarit}
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
                          <span className="block text-[10px] text-st-creuser mt-0.5">⏳ En cours (non servi) : {f.plu_fraicheur.en_cours}</span>
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
                {f.potentiel_transformation && <TransformationBlock pt={f.potentiel_transformation} />}
                {reglesLines.length > 0 && <div className="flex flex-col gap-1">{reglesLines.map((l, i) => <Line key={i} line={l} />)}</div>}
                {/* M22-B : lettre de vérification de zonage — bouton discret (la barre M20 reste à 7 tuiles) */}
                <a data-lettre-zonage href={`/lettre-zonage/${idu}.pdf`} target="_blank" rel="noreferrer"
                  className="self-start text-[10.5px] text-txt-mut underline decoration-line-2 underline-offset-2 hover:text-mint">
                  Éditer la lettre de vérification de zonage (PDF)
                </a>
              </div>
            </RefDrawer>

            {/* ③ ÉCONOMIE — capacité/bilan, marché, réseaux, mode B (M44). Ordre : capacité d'abord. */}
            {/* FAISABILITÉ ET BILAN — micro : 3 données sur une ligne. Ouvert si servable. */}
            <RefDrawer id="faisabilite" icon={IC.faisa} name="Faisabilité et bilan" value={logementsTxt}
              micro={<MicroTriple items={delaisse
                /* M30-revue A2 : le guard délaissé couvre la tuile ENTIÈRE — la sous-ligne ne
                   promet plus un gabarit/SDP sur une parcelle sous le seuil. */
                ? [`surface ${delaisse.surface_m2} m²`, `seuil délaissé ${delaisse.seuil_m2} m²`, 'bilan non servi']
                : [fo?.niveaux ?? 'gabarit', <>SDP <span style={{ color: '#9db5a8' }}>{fo?.surface_plancher_m2 ?? reglesSdp ?? '—'} m²</span></>, 'calcul tracé']} />}>
              <div className="flex flex-col gap-3">
                {delaisse && (
                  /* M30 item 5 : le bilan n'est pas servi sous 50 m² — on le DIT, on ne le masque pas */
                  <div data-delaisse className="flex items-start gap-2 rounded-lg border border-st-creuser/40 bg-st-creuser/10 px-3 py-2">
                    <span aria-hidden className="text-st-creuser">▲</span>
                    <p className="text-[11px] leading-snug text-txt">{delaisse.libelle}</p>
                  </div>
                )}
                <FaisabiliteTab idu={idu} />
                {!delaisse && <BilanTab idu={idu} />}
              </div>
            </RefDrawer>

            {/* MARCHÉ — micro : sparkline + volume */}
            <RefDrawer id="marche" icon={IC.marche} name="Marché" valueColor={REF.name}
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
            </RefDrawer>

            {/* VIABILISATION ET RÉSEAUX — accès, équipements, gestionnaires, permis */}
            <RefDrawer id="viabilisation" icon={IC.viab} name="Viabilisation et réseaux" value={viabValue}>
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

            {/* ③ ÉCONOMIE (suite) — Mode B (M44) pour un tier SERVABLE : reste dans l'économie
                (la déclassée l'a déjà remonté en 2). Lecture complémentaire, subordonnée au verdict. */}
            {!signalEcarte && f.mode_b?.disponible && <ModeBDrawer idu={idu} initial={f.mode_b} />}

            {/* ④ CONTEXTE — « Sur cette parcelle » (historique permis + caducité) et « Autour »
                (voisinage proche : ventes DVF + permis 36 mois). M42. Rien si les deux sont vides. */}
            {((f.historique_site && (f.historique_site.permis.length > 0 || f.historique_site.caducite)) || f.voisinage_proche) && (
              <RefDrawer id="contexte" icon={IC.contexte} name="Contexte"
                value={f.voisinage_proche ? `${f.voisinage_proche.ventes_dvf} vente(s) · ${f.voisinage_proche.permis} permis` : 'voir'}>
                <div className="flex flex-col gap-3">
                  {/* M42 — « Sur cette parcelle » : historique permis + caducité (un caduc DIT caduc). */}
                  {f.historique_site && (f.historique_site.permis.length > 0 || f.historique_site.caducite) && (
                    <div data-historique-site className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] leading-snug">
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
                  {/* M42 — « Autour, à moins de N m » : ventes DVF + permis (36 mois). Rien si vide. */}
                  {f.voisinage_proche && (
                    <div data-voisinage-proche className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] leading-snug">
                      <div className="font-medium text-txt">📍 {f.voisinage_proche.titre}</div>
                      <div className="mt-1 text-txt-mut">
                        {f.voisinage_proche.ventes_dvf} vente(s){f.voisinage_proche.prix_median_eur ? ` · prix médian ~${Math.round(f.voisinage_proche.prix_median_eur / 1000)} k€` : f.voisinage_proche.prix_note ? ` · ${f.voisinage_proche.prix_note}` : ''} · {f.voisinage_proche.permis} permis <span className="text-txt-dim">(36 mois)</span>
                      </div>
                      <div className="mt-0.5 text-[10px] text-txt-dim">{f.voisinage_proche.honnetete}</div>
                    </div>
                  )}
                </div>
              </RefDrawer>
            )}

            {/* ⑤ PROPRIÉTÉ — société (M43) + signaux vendeur. CARTE ACCENTUÉE VIOLETTE = le signal chaud. */}
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

            {/* ⑥ RISQUES — micro : N segments verts = N couches vérifiées (négatif AFFIRMÉ). */}
            <RefDrawer id="risques" icon={IC.risques} name="Risques"
              value={risquesFlags.length === 0 ? 'rien à signaler' : `${risquesFlags.length} vigilance`}
              micro={<MicroSegments n={risquesClean} label={`${risquesClean} couches`} />}>
              {risquesLines.length
                ? <div className="flex flex-col gap-1">{risquesLines.map((l, i) => <Line key={i} line={l} />)}</div>
                : <p className="text-xs text-txt-dim">Aucun signal sur cet onglet.</p>}
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
                  {/* M47 : étiquette source · millésime — comme toute couche servie. */}
                  <p style={{ margin: 0, fontSize: 10, color: REF.dim }}>
                    {f.renouvellement.source}
                    {f.renouvellement.maj ? ` · maj ${f.renouvellement.maj}` : ''}
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

            {/* ⑧ LES DONNÉES — dernier bloc de contenu (M52 L3). Sources RÉELLEMENT utilisées sur
                cette fiche (data_sources) + données ABSENTES dites + confiance (ICD, score P), flags,
                signaler. Zéro nouvelle donnée : tout vient de tables existantes ou de nuls dits. */}
            <RefDrawer id="confiance" icon={IC.confiance} name="Les données"
              value={f.data_sources?.length ? CLIENT.fiche.sourcesUtilisees(f.data_sources.length) : confianceValue}>
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
                {/* Confiance données (ICD) + score P « pourquoi ». */}
                {f.icd && <IcdBlockView icd={f.icd} />}
                <ScoreV2Block idu={idu} />
                {/* M55-O phase 2.2 — le bloc « Signaux additionnels » (f.flags) est SUPPRIMÉ : ce sont
                    des redites des tiroirs dédiés (ABF → Risques, bâti/SDP → Constructibilité, PPR →
                    Risques). Chaque information n'apparaît qu'une fois. */}
                <SignalerErreur idu={idu} />
              </div>
            </RefDrawer>

            {/* M55-L point 11 : le bloc IA (« Une question ? » + « Synthèse ») est REMONTÉ en tête
                de fiche (voir plus haut, data-ia-tete). Il ne vit plus en bas de la pile. */}

            {/* ═══ BARRE D'ACTIONS · 2 niveaux (spec) — DANS le flux (fin du « double écran de vide ») ═══ */}
            <div style={{ marginTop: 7, paddingTop: 14, borderTop: '1px solid #1a2320' }}>
              {/* M55-L point 9 : « + CRM » (ex-« + Pipeline ») et « + Projet ». Comparer a AUSSI une
                  entrée Outils (registry « comparer »), qui OUVRE le comparateur (la sélection persiste
                  en session). Le bouton fiche est CONSERVÉ car il porte l'AJOUT : mesuré, ouvrir le
                  tiroir Outils remet selectedIdu à null → un outil ne peut pas récupérer « la parcelle
                  regardée ». Le retirer laisserait le comparateur non peuplable (rapport, Vic tranche). */}
              <div style={{ display: 'flex', gap: 8, marginBottom: 11 }}>
                <PipelineButton idu={idu} />
                <ProjetButton idu={idu} />
                {/* M54-EXPO A8 — AJOUTER cette parcelle au comparateur (jusqu'à 3), puis ouvre le panneau. */}
                <button data-compare-add onClick={() => useApp.getState().addToCompare(idu)}
                  title="Ajouter au comparateur (Outils → Comparer pour le rouvrir)"
                  style={{ flexShrink: 0, padding: '0 12px', borderRadius: 9, border: '1px solid #2a3a33', background: '#0e1311', color: '#8fd8b4', fontSize: 12, cursor: 'pointer' }}>
                  ⇄ Comparer
                </button>
              </div>
              {/* M55-L point 8 — BARRE D'ACTIONS SUR DEUX LIGNES ÉQUILIBRÉES (décision Vic).
                  Ligne 1 : PDF · Dossier · Finance · Cadastre. Ligne 2 : 1950 · Maps · Courrier ·
                  One-pager · Pré-dossier PC. `gridAutoFlow:column + gridAutoColumns:1fr` → colonnes
                  ÉGALES quel que soit le nombre de tuiles réellement rendues (les tuiles Cadastre /
                  1950 / Maps sont conditionnées à f.coords → pas de trou). Mêmes hauteurs, mêmes
                  séparateurs qu'avant. */}
              <div style={{ background: '#0e1311', border: '1px solid #1e2823', borderRadius: 11, display: 'grid', gridAutoFlow: 'column', gridAutoColumns: '1fr', overflow: 'hidden' }}>
                <a href={pdfUrl(idu, calculette)} target="_blank" rel="noreferrer" style={{ padding: '10px 0 9px', textAlign: 'center', borderRight: '1px solid #16201c', color: '#8fd8b4', textDecoration: 'none', display: 'block' }} title={calculette ? 'PDF (avec votre charge foncière)' : 'Exporter la fiche en PDF'}>
                  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /><path d="M12 12v5" /><path d="m9.5 14.5 2.5 2.5 2.5-2.5" /></svg>
                  <p style={{ margin: '5px 0 0', fontSize: 10, color: '#7d9488' }}>PDF</p>
                </a>
                <DossierTile idu={idu} />
                <BanquierButton idu={idu} />
                {f.coords && (
                  <a data-cadastre-link href={`https://www.geoportail.gouv.fr/carte?c=${f.coords[0]},${f.coords[1]}&z=19&l0=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2::GEOPORTAIL:OGC:WMTS(1)&l1=CADASTRALPARCELS.PARCELLAIRE_EXPRESS::GEOPORTAIL:OGC:WMTS(1)&permalink=yes`} target="_blank" rel="noreferrer noopener" style={{ padding: '10px 0 9px', textAlign: 'center', color: '#8fd8b4', textDecoration: 'none', display: 'block' }} title={CLIENT.fiche.export.cadastreTip}>
                    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}><path d="m9 4 6 2 6-2v14l-6 2-6-2-6 2V6z" /><path d="M9 4v14" /><path d="M15 6v14" /></svg>
                    <p style={{ margin: '5px 0 0', fontSize: 10, color: '#7d9488' }}>Cadastre</p>
                  </a>
                )}
              </div>
              <div style={{ marginTop: 8, background: '#0e1311', border: '1px solid #1e2823', borderRadius: 11, display: 'grid', gridAutoFlow: 'column', gridAutoColumns: '1fr', overflow: 'hidden' }}>
                {f.coords && (
                  <button onClick={() => { setFlyTo({ center: f.coords, zoom: 18 }); setModule('temps') }} style={{ padding: '10px 0 9px', textAlign: 'center', borderRight: '1px solid #16201c', color: '#8fd8b4', background: 'none', border: 0, cursor: 'pointer' }} title="Ce terrain en 1950 — comparateur temporel">
                    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}><path d="M12 8v4l3 2" /><path d="M3.05 11a9 9 0 1 1 .5 4" /><path d="M3 21v-5h5" /></svg>
                    <p style={{ margin: '5px 0 0', fontSize: 10, color: '#7d9488' }}>1950</p>
                  </button>
                )}
                {f.coords && (
                  <a data-maps-link href={`https://www.google.com/maps/search/?api=1&query=${f.coords[1]},${f.coords[0]}`} target="_blank" rel="noreferrer" style={{ padding: '10px 0 9px', textAlign: 'center', borderRight: '1px solid #16201c', color: '#8fd8b4', textDecoration: 'none', display: 'block' }} title="Ouvrir dans Google Maps (épingle sur la parcelle)">
                    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0" /><circle cx="12" cy="10" r="3" /></svg>
                    <p style={{ margin: '5px 0 0', fontSize: 10, color: '#7d9488' }}>Maps</p>
                  </a>
                )}
                {/* Courrier propriétaire → module M09 (setModule) pré-rempli sur la parcelle courante. */}
                <button data-courrier-tile onClick={() => setModule('courriers')}
                  style={{ padding: '10px 0 9px', textAlign: 'center', borderRight: '1px solid #16201c', color: '#8fd8b4', background: 'none', border: 0, cursor: 'pointer' }}
                  title={CLIENT.fiche.export.courrierTip}>
                  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" /></svg>
                  <p style={{ margin: '5px 0 0', fontSize: 10, color: '#7d9488' }}>{CLIENT.fiche.export.courrier}</p>
                </button>
                <a data-onepager href={onePagerUrl(idu)} target="_blank" rel="noreferrer" style={{ padding: '10px 0 9px', textAlign: 'center', borderRight: '1px solid #16201c', color: '#8fd8b4', textDecoration: 'none', display: 'block' }} title={CLIENT.fiche.export.onepagerTip}>
                  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /><path d="M8 13h8" /><path d="M8 17h5" /></svg>
                  <p style={{ margin: '5px 0 0', fontSize: 10, color: '#7d9488' }}>{CLIENT.fiche.export.onepager}</p>
                </a>
                <PreDossierTile idu={idu} />
              </div>
              {/* M55-L point 7 : le widget feedback « Ce lead vous est-il utile ? » est RETIRÉ.
                  La mention légale est CONSERVÉE, relogée en pied de fiche au plus petit corps
                  lisible du DS (9px) et couleur discrète — elle reste présente dans les PDF (back). */}
              <p data-disclaimer-legal style={{ marginTop: 11, fontSize: 9, lineHeight: 1.5, color: '#4d5f57' }}>
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
function SyntheseIA({ idu }: { idu: string }) {
  const q = useMutation({ mutationFn: () => getExplain(idu) })
  useEffect(() => { q.reset() }, [idu])  // eslint-disable-line react-hooks/exhaustive-deps
  const d = q.data
  const box = { marginTop: 8, background: '#110d1b', border: '1px solid #372c58', borderRadius: 12, padding: '11px 14px' } as const
  if (!d && !q.isPending) return (
    <button onClick={() => q.mutate()} data-synthese-ia
      style={{ ...box, display: 'flex', alignItems: 'center', gap: 9, width: '100%', textAlign: 'left', color: '#c9b6f2', cursor: 'pointer' }} title={CLIENT.fiche.ia.syntheseTip}>
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" /></svg>
      <span style={{ flex: 1, fontSize: 13 }}>{CLIENT.fiche.ia.synthese}</span>
      <span style={{ fontSize: 12, color: '#8a6ff0' }}>rédiger →</span>
    </button>
  )
  if (q.isPending) return <p style={{ ...box, color: '#c9b6f2', fontSize: 12 }}><span style={{ display: 'inline-block', width: 6, height: 6, marginRight: 8, borderRadius: 9, background: '#8a6ff0' }} className="animate-pulse" />{CLIENT.fiche.ia.syntheseEnCours}</p>
  if (q.isError) return <p style={{ ...box, color: '#E8695A', fontSize: 12 }}>{CLIENT.fiche.ia.syntheseErreur}</p>
  const stub = d && !d.available
  const rs = d?.rules_summary
  return (
    <div data-synthese-ia-result style={box}>
      <p style={{ margin: 0, fontSize: 11, fontWeight: 600, color: '#c9b6f2', display: 'flex', alignItems: 'center', gap: 6 }}>
        {CLIENT.fiche.ia.synthese}
        {stub && <span data-synthese-stub style={{ fontSize: 9.5, fontWeight: 500, color: '#b7a3e6', border: '1px solid #47386e', borderRadius: 5, padding: '1px 5px' }}>repli</span>}
      </p>
      <p style={{ margin: '7px 0 0', fontSize: 12, lineHeight: 1.5, color: '#d8ccf5', whiteSpace: 'pre-wrap' }}>{d?.available ? d.explanation : d?.message}</p>
      {stub && Array.isArray(rs) && rs.length > 0 && <ul style={{ margin: '6px 0 0', paddingLeft: 16, fontSize: 11.5, lineHeight: 1.5, color: '#c9b6f2' }}>{rs.map((r, i) => <li key={i}>{r}</li>)}</ul>}
      {stub && typeof rs === 'string' && rs && <p style={{ margin: '6px 0 0', fontSize: 11.5, lineHeight: 1.5, color: '#c9b6f2', whiteSpace: 'pre-wrap' }}>{rs}</p>}
      {stub && <p style={{ margin: '7px 0 0', fontSize: 10, color: '#8f80b8' }}>{CLIENT.fiche.ia.syntheseStub}</p>}
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
  const cell = { padding: '10px 0 9px', textAlign: 'center' as const, borderRight: '1px solid #16201c', display: 'block' }
  const icon = <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /></svg>
  const d = st.data
  if (d && !d.disponible) return (
    <span data-dossier-indispo aria-disabled style={{ ...cell, color: '#8fd8b4', opacity: 0.4, cursor: 'not-allowed' }} title={d.raison ?? 'Générateur de dossier indisponible'}>
      {icon}<p style={{ margin: '5px 0 0', fontSize: 10, color: '#7d9488' }}>Dossier</p>
    </span>
  )
  const compteur = d && !d.illimite && d.restants != null
  const tip = d ? (d.illimite ? 'Dossier parcelle PDF brandé (illimité — Intégral)' : `Dossier parcelle PDF brandé — ${d.restants}/${d.quota_mois} restants ce mois`) : 'Dossier parcelle PDF brandé'
  return (
    <a data-dossier-tile href={`/dossier/${idu}.pdf`} target="_blank" rel="noreferrer" style={{ ...cell, color: '#8fd8b4', textDecoration: 'none' }} title={tip}>
      {icon}<p style={{ margin: '5px 0 0', fontSize: 10, color: '#7d9488' }}>Dossier{compteur ? <span data-dossier-quota style={{ color: d!.restants === 0 ? '#E8695A' : '#7de3ab' }}> · {d!.restants}</span> : ''}</p>
    </a>
  )
}


/** M54-EXPO — tuile « Pré-dossier PC » (ZIP CERFA). Réservée au plan Intégral (backend :
 *  pre_dossier.py → plans.acces('pre_dossier_pc') = 403 sinon + quota M-K). Le front lit le plan
 *  (getMoi) et grise la tuile hors Intégral (pas de téléchargement d'un 403). */
function PreDossierTile({ idu }: { idu: string }) {
  const moi = useQuery({ queryKey: ['moi'], queryFn: getMoi })
  const integral = moi.data?.plan === 'integral'
  const cell = { flex: 1, padding: '9px 0 8px', textAlign: 'center' as const, display: 'block', textDecoration: 'none' }
  const icon = <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ margin: '0 auto' }}><path d="M21 8v13H3V3h10" /><path d="M16 3h5v5" /><path d="M8 13h6M8 17h4" /></svg>
  if (!integral) return (
    <span data-predossier-gate aria-disabled style={{ ...cell, color: '#8fd8b4', opacity: 0.4, cursor: 'not-allowed' }} title={`${CLIENT.fiche.export.preDossierTip} — ${CLIENT.fiche.export.preDossierGate}`}>
      {icon}<p style={{ margin: '4px 0 0', fontSize: 10, color: '#7d9488' }}>{CLIENT.fiche.export.preDossier}</p>
    </span>
  )
  return (
    <a data-predossier href={preDossierUrl(idu)} target="_blank" rel="noreferrer" style={{ ...cell, color: '#8fd8b4' }} title={CLIENT.fiche.export.preDossierTip}>
      {icon}<p style={{ margin: '4px 0 0', fontSize: 10, color: '#7d9488' }}>{CLIENT.fiche.export.preDossier}</p>
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
