import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { addToPipeline, createShare, getFaisabilite, getFiche, getOrthoEquipements, getPipelineForParcel, getSolaireFiche, getWatch, iaPourquoi, iaSynthese, pdfUrl, postChargeFonciere, toggleWatch } from '../../lib/api'
import { BRULANTE_COLOR, completudeColor, STATUT_META, vBandColor } from '../../lib/status'
import { Loading } from '../Loading'
import type { FicheLine, Onglet, ScoreV, VSignal } from '../../lib/types'
import { useApp } from '../../store/useApp'

const SEV_COLOR: Record<string, string> = { fort: '#E8695A', moyen: '#E8B44C', faible: '#C9DCD1', info: '#8FA69A' }

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
    <div className="mt-0.5 flex items-center gap-2 text-[10px] text-txt-dim">
      {line.source && (
        <button onClick={() => openSourceDrawer(line)} className="truncate text-[#5a7d6c] hover:text-mint hover:underline"
          title="Voir la source (drawer)">
          {line.source}
        </button>
      )}
      {trace && <span className="shrink-0 font-mono text-[#4a5a52]">{trace}</span>}
      {line.date && <span className="ml-auto shrink-0 font-mono">{line.date}</span>}
    </div>
  )
}

function Line({ line }: { line: FicheLine }) {
  return (
    <div className="flex gap-3 border-b border-[#141d17] py-2 last:border-0">
      <Weight w={line.weight} result={line.result} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-txt">{line.layer}</span>
          {line.severity && line.weight == null && (
            <span className="rounded-full px-1.5 text-[9px]" style={{ background: `${SEV_COLOR[line.severity]}22`, color: SEV_COLOR[line.severity] }}>
              {line.severity}
            </span>
          )}
          {line.result === 'UNKNOWN' && <span className="text-[9px] text-txt-dim">inconnu</span>}
        </div>
        <div className="text-[11px] leading-snug text-txt-mut">{line.detail}</div>
        <SourceRef line={line} />
      </div>
    </div>
  )
}

// Barre de sous-score dépliable (exigence #2 : DEUX barres, Q et A, vers leurs lignes tracées).
function ScoreBar({ label, value, color, lines, defaultOpen }: {
  label: string; value: number; color: string; lines: FicheLine[]; defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(!!defaultOpen)
  const weighted = lines.filter((l) => l.weight != null && l.weight !== 0).sort((a, b) => Math.abs(b.weight!) - Math.abs(a.weight!))
  return (
    <div className="rounded-lg border border-line-2 bg-surface-2">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-3 px-3 py-2.5" title={`${label} : déplier les signaux`}>
        <span className="w-24 shrink-0 text-left text-xs text-txt">{label}</span>
        <span className="relative h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-line">
          <span className="absolute left-0 top-0 h-full rounded-full" style={{ width: `${value}%`, background: color }} />
        </span>
        <span className="w-8 shrink-0 text-right font-display text-sm font-bold" style={{ color }}>{value}</span>
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

// ── Score V (Vendabilité, Stage 3) ─────────────────────────────────────────────
// Le panneau « Pourquoi ce score » est le différenciateur crédibilité : chaque signal
// affiche son label, sa source, sa date et son LIEN VÉRIFIABLE (avis BODACC cliquable).
const FAMILLE_LABEL: Record<string, string> = {
  A: 'Détresse juridique', B: 'Cycle de vie du propriétaire', C: 'Détachement géographique',
  D: 'Dormance de l’actif', E: 'Pression réglementaire', malus: 'Malus',
}

function VSignalRow({ s }: { s: VSignal }) {
  const neg = s.points < 0
  return (
    <div className="flex gap-3 border-b border-[#141d17] py-2 last:border-0">
      <span className={`w-10 shrink-0 text-right font-mono text-xs font-semibold ${neg ? 'text-st-ecartee' : 'text-[#FF8A50]'}`}>
        {neg ? s.points : `+${s.points}`}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-txt">{s.label}</span>
          <span className="shrink-0 rounded-full bg-surface-3 px-1.5 text-[8.5px] text-txt-dim" title={`Famille ${s.famille}`}>
            {FAMILLE_LABEL[s.famille] ?? s.famille}
          </span>
        </div>
        {s.ref && <div className="text-[11px] leading-snug text-txt-mut">{s.ref}</div>}
        <div className="mt-0.5 flex items-center gap-2 text-[10px] text-txt-dim">
          {s.url
            ? <a href={s.url} target="_blank" rel="noreferrer" className="truncate text-[#5a7d6c] hover:text-mint hover:underline"
                title="Vérifier à la source (avis officiel)">{s.source} ↗</a>
            : <span className="truncate">{s.source}</span>}
          {s.match && s.match.confiance < 1 && (
            <span className="shrink-0 rounded bg-[#211a10] px-1 text-[8.5px] text-st-creuser"
              title="Propriétaire rapproché par dénomination (pas de SIREN au fichier DGFiP) — points réduits ×0.7">
              match {Math.round(s.match.confiance * 100)} %
            </span>
          )}
          {s.date_evenement && <span className="ml-auto shrink-0 font-mono">{s.date_evenement}</span>}
        </div>
      </div>
    </div>
  )
}

function VendabiliteBlock({ sv }: { sv: ScoreV }) {
  const [open, setOpen] = useState(false)
  const color = sv.brulante ? BRULANTE_COLOR : vBandColor(sv.v_band)
  if (sv.v_score == null) {
    // V non applicable (D4) : badge spécial à la place du score — jamais un « 0 » menteur.
    return (
      <div data-score-v className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
        <div className="flex items-center gap-3">
          <span className="w-24 shrink-0 text-xs text-txt">Vendabilité</span>
          <span className="rounded-full bg-surface-3 px-2 py-0.5 text-[10.5px] text-txt-mut">{sv.badge ?? 'N.A.'}</span>
        </div>
        <p className="mt-1 text-[10px] leading-snug text-txt-dim">
          Score V non calculé pour ce type de propriétaire — démarche d'acquisition spécifique.
        </p>
      </div>
    )
  }
  return (
    <div data-score-v className="rounded-lg border border-line-2 bg-surface-2">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-3 px-3 py-2.5"
        title="Vendabilité : signaux publics indiquant que le propriétaire a des raisons objectives de vendre — déplier « Pourquoi ce score »">
        <span className="w-24 shrink-0 text-left text-xs text-txt">Vendabilité</span>
        <span className="relative h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-line">
          <span className="absolute left-0 top-0 h-full rounded-full" style={{ width: `${sv.v_score}%`, background: color }} />
        </span>
        {sv.brulante && <span className="shrink-0 text-xs" title="🔥 BRÛLANTE — chaude Q×A + signaux vendeur forts (V ≥ 50)">🔥</span>}
        <span className="w-8 shrink-0 text-right font-display text-sm font-bold" style={{ color }}>{sv.v_score}</span>
        <span className="shrink-0 text-txt-dim">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="border-t border-line-2 px-3 py-1">
          <div className="flex items-center gap-2 py-1.5">
            <span className="rounded-full px-1.5 py-0.5 text-[9px] font-medium" style={{ background: `${color}1f`, color }}>
              {sv.v_band_label}{sv.brulante ? ' · 🔥 Brûlante' : ''}
            </span>
            {sv.badge && <span className="rounded-full border border-line-2 px-1.5 py-0.5 text-[9px] text-txt-dim">{sv.badge}</span>}
            {sv.v_coverage === 'partial' && !sv.badge && (
              <span className="rounded-full border border-line-2 px-1.5 py-0.5 text-[9px] text-txt-dim"
                title="Propriétaire non identifié (personne physique ou sans SIREN) : seuls les signaux de la parcelle (dormance, DPE) sont évalués">
                Signaux partiels
              </span>
            )}
          </div>
          <p className="pb-1 font-mono text-[9.5px] tracking-widest text-txt-dim">POURQUOI CE SCORE</p>
          {sv.signals.length
            ? sv.signals.map((s, i) => <VSignalRow key={i} s={s} />)
            : <p className="py-2 text-[11px] text-txt-dim">Aucun signal public de vente détecté — le propriétaire ne montre aucune raison objective de vendre.</p>}
          <p className="py-1.5 text-[9px] leading-snug text-txt-dim">
            V agrège des signaux PUBLICS (BODACC, RNE, DGFiP, DVF, Cartofriches, ADEME) — une
            propension, jamais une certitude ni une donnée nominative de personne physique.
          </p>
        </div>
      )}
    </div>
  )
}

// M14 — suivi de cible : événements sur cette parcelle SANS l'entrer au pipeline.
function WatchButton({ idu }: { idu: string }) {
  const qc = useQueryClient()
  const w = useQuery({ queryKey: ['watch', idu], queryFn: () => getWatch(idu) })
  const t = useMutation({ mutationFn: () => toggleWatch(idu), onSuccess: () => qc.invalidateQueries({ queryKey: ['watch', idu] }) })
  const on = w.data?.watched
  return (
    <button onClick={() => t.mutate()}
      className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border text-xs ${on ? 'border-mint text-mint' : 'border-line-2 text-txt hover:text-txt-hi'}`}
      title={on ? 'Suivie — les événements alimentent la cloche' : 'Suivre cette parcelle (alertes sans pipeline)'}>
      👁
    </button>
  )
}

// M20 — pack apporteur : lien public lecture seule, filigrané + horodaté + compteur de vues.
function ShareButton({ idu }: { idu: string }) {
  const share = useMutation({ mutationFn: () => createShare(idu) })
  return (
    <div className="relative shrink-0">
      <button onClick={() => share.mutate()}
        className="flex h-8 w-8 items-center justify-center rounded-lg border border-line-2 text-xs text-txt hover:text-txt-hi"
        title="Pack apporteur : générer un lien public lecture seule (filigrané, compteur de vues)">
        ↗
      </button>
      {share.data && (
        <div className="absolute bottom-10 right-0 z-20 w-64 rounded-lg border border-line-2 bg-surface-2 p-3 text-[11px] shadow-xl">
          <p className="font-mono text-[10px] tracking-widest text-txt-dim">LIEN APPORTEUR</p>
          <a href={share.data.url} target="_blank" rel="noreferrer" className="mt-1 block truncate text-mint hover:underline">
            {window.location.origin}{share.data.url}
          </a>
          <p className="mt-1 text-[10px] text-txt-dim">Lecture seule · filigrané · consultations comptées.</p>
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

// Panneau IA de la fiche : synthèse tracée + « pourquoi ce score ? » — mention systématique.
function IAPanel({ idu, onClose }: { idu: string; onClose: () => void }) {
  const [mode, setMode] = useState<'synthese' | 'pourquoi' | null>(null)
  const gen = useMutation({ mutationFn: (m: 'synthese' | 'pourquoi') => (m === 'synthese' ? iaSynthese(idu) : iaPourquoi(idu)) })
  const isStub = gen.data?.stub
  return (
    <div className="absolute bottom-10 right-0 z-20 w-[320px] rounded-lg border border-line-2 bg-surface-2 p-3 shadow-xl">
      <div className="flex items-center justify-between">
        <p className="font-mono text-[10px] tracking-widest text-txt-dim">ANALYSE IA</p>
        <button onClick={onClose} className="text-txt-dim hover:text-txt-hi">✕</button>
      </div>
      {isStub && (
        <p className="mt-1.5 rounded border border-st-creuser/40 bg-[#211a10] px-2 py-1 text-[9.5px] leading-snug text-st-creuser">
          Stub local (clé IA absente) — texte généré par règles depuis la fiche tracée.
          Activer : ANTHROPIC_API_KEY dans .env, puis relancer.
        </p>
      )}
      <div className="mt-2 flex gap-1.5">
        {([['synthese', 'Synthèse'], ['pourquoi', 'Pourquoi ce score ?']] as const).map(([k, l]) => (
          <button key={k} onClick={() => { setMode(k); gen.mutate(k) }}
            className={`rounded-full border px-2.5 py-1 text-[11px] ${mode === k ? 'border-mint text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>
            {l}
          </button>
        ))}
      </div>
      {gen.isPending && <p className="mt-3 text-[11px] text-txt-dim">Génération…</p>}
      {gen.isError && <p className="mt-3 text-[11px] text-st-ecartee">Erreur — réessayez.</p>}
      {gen.data && (
        <>
          <div className="mt-3 max-h-64 overflow-y-auto whitespace-pre-wrap text-[11px] leading-relaxed text-txt">{gen.data.texte}</div>
          <p className="mt-2 border-t border-line pt-2 text-[9.5px] text-txt-dim">{gen.data.mention}</p>
        </>
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
      <label className="flex items-center gap-1 text-[10px] text-txt-dim">
        {label}
        {hint && <span className="rounded bg-[#211a10] px-1 text-[8.5px] text-st-creuser" title="Hypothèse — à ajuster selon votre opération">hyp. — ajustez</span>}
      </label>
      <div className="mt-1 flex items-center rounded-lg border border-line-2 bg-surface-3 focus-within:border-mint">
        <input type="number" min={0} value={value ?? ''} placeholder={placeholder}
          onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
          className="min-w-0 flex-1 bg-transparent px-2 py-1.5 text-xs text-txt placeholder:text-txt-dim focus:outline-none" />
        <span className="shrink-0 px-2 text-[10px] text-txt-dim">{suffix}</span>
      </div>
    </div>
  )
}

/** LA CALCULETTE DE CHARGE FONCIÈRE (mandat bilan-calculette). LABUSE affiche le SOURCÉ (SDP,
 *  prix DVF) ; le promoteur saisit SES hypothèses (coût, marge) ; le résultat « selon vos
 *  hypothèses » se recalcule côté moteur (endpoint déterministe, aucune arithmétique dupliquée
 *  en JS). Cas limites honnêtes : capacité non résolue / prix insuffisant → pas de faux chiffre. */
function Calculette({ idu }: { idu: string }) {
  const [cout, setCout] = useState<number | null>(CALC_COUT_DEFAUT)
  const [marge, setMarge] = useState<number | null>(CALC_MARGE_DEFAUT)
  const [prixDemande, setPrixDemande] = useState<number | null>(null)
  const [deb, setDeb] = useState({ cout: CALC_COUT_DEFAUT, marge: CALC_MARGE_DEFAUT, prix: null as number | null })
  useEffect(() => {
    const t = setTimeout(() => setDeb({ cout: cout ?? CALC_COUT_DEFAUT, marge: marge ?? CALC_MARGE_DEFAUT, prix: prixDemande }), 350)
    return () => clearTimeout(t)
  }, [cout, marge, prixDemande])
  const q = useQuery({
    queryKey: ['charge', idu, deb.cout, deb.marge, deb.prix],
    queryFn: () => postChargeFonciere(idu, { cout_construction_m2: deb.cout, marge_frais_pct: deb.marge, prix_demande_eur: deb.prix }),
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
      <p className="mb-1 flex items-center gap-2 font-mono text-[10px] tracking-widest text-txt-dim">
        CALCULETTE DE CHARGE FONCIÈRE
        {q.isFetching && <span data-calc-recalc className="animate-pulse text-[9px] text-mint">recalcul…</span>}
      </p>
      <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5 text-[11px] leading-relaxed text-txt">
        {q.isLoading && <Loading label="Calcul en cours" />}
        {d && d.calculable === false && (
          <div data-calc-indispo>
            <p className="text-st-creuser">{d.message ?? 'Charge foncière non calculable.'}</p>
            {d.marche?.median != null && (
              <p className="mt-1 text-txt-mut">Au mieux — prix de sortie secteur : <b className="text-mint">{Number(d.marche.median).toLocaleString('fr-FR')} €/m²</b> ({d.marche.fiabilite}).</p>
            )}
          </div>
        )}
        {d && d.calculable && cf && (
          <>
            {/* le SOURCÉ (lecture seule) — ce que LABUSE sait */}
            <p className="text-[10px] text-txt-dim">
              LABUSE (sourcé) : SDP vendable <b className="text-txt">{Number(d.shab_vendable_m2).toLocaleString('fr-FR')} m²</b> ·
              prix de sortie <b className="text-txt">{Number(d.prix_sortie_median).toLocaleString('fr-FR')} €/m²</b> ·
              terrain <b className="text-txt">{Number(d.terrain_m2).toLocaleString('fr-FR')} m²</b>
            </p>
            {/* les HYPOTHÈSES — saisies par le promoteur */}
            <div className="mt-2 flex gap-2">
              <HypInput label="Coût construction" value={cout} onChange={setCout} suffix="€/m²" hint />
              <HypInput label="Marge & frais" value={marge} onChange={setMarge} suffix="%" hint />
            </div>
            {/* le RÉSULTAT — calcul de VOS hypothèses */}
            <div data-calc-resultat className="mt-2.5 rounded-lg border border-[#2E6B4F] bg-[#0F1A14] px-3 py-2">
              <p className="text-[10px] text-txt-dim">Charge foncière supportable <span className="text-txt-mut">— selon vos hypothèses</span></p>
              <p className="mt-0.5">
                <b data-calc-cf className="font-display text-lg font-bold text-mint">{euros(cf.central)}</b>
                <span className="ml-1.5 text-[10px] text-txt-mut">≈ {Number(cf.par_m2_terrain).toLocaleString('fr-FR')} €/m² de terrain</span>
              </p>
              <p className="text-[10px] text-txt-dim">fourchette {euros(cf.bas)} – {euros(cf.haut)}{d.fiabilite === 'fragile' ? ' · prix de sortie fragile (ordre de grandeur)' : ''}</p>
            </div>
            {/* aide à la DÉCISION D'ACHAT — prix demandé optionnel */}
            <div className="mt-2 flex items-end gap-2">
              <HypInput label="Prix demandé du terrain" value={prixDemande} onChange={setPrixDemande} suffix="€" placeholder="si connu" />
            </div>
            {achat && (
              <div data-calc-verdict className={`mt-2 rounded-lg px-3 py-2 text-[11px] font-medium ${achat.supportable ? 'bg-[#12241a] text-mint' : 'bg-[#2a1210] text-st-ecartee'}`}>
                {achat.supportable
                  ? <>✓ Supportable — le terrain peut valoir {euros(achat.prix_demande_eur)} ; marge de {euros(achat.ecart_eur)} ({achat.ecart_pct > 0 ? '+' : ''}{achat.ecart_pct} %) sous votre charge foncière.</>
                  : <>✗ Trop cher — à {euros(achat.prix_demande_eur)}, l'opération dépasse de {euros(Math.abs(achat.ecart_eur))} ({achat.ecart_pct} %) ce que vos hypothèses supportent.</>}
              </div>
            )}
            {(d.avertissements ?? []).length > 0 && (
              <ul className="mt-1.5 list-inside list-disc text-[9.5px] text-st-creuser">
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
        {b.map(([label, color, title]) => (
          <span key={label} title={title} className="rounded-full px-2 py-0.5 text-[10px] font-medium"
            style={{ background: `${color}22`, color }}>{label}</span>
        ))}
      </div>
      <p className="mt-1 text-[9px] text-txt-dim">{String(e['source'] ?? '')}</p>
    </div>
  )
}

// Onglet SOLAIRE — mandat Habitat Solaire (Lot 9.1) : chaque donnée est SOURCÉE, la
// facture est une ESTIMATION statistique, jamais une donnée réelle.
function SolaireTab({ idu }: { idu: string }) {
  const { data: sol, isLoading, isError } = useQuery({
    queryKey: ['solaire', idu], queryFn: () => getSolaireFiche(idu), retry: false,
  })
  if (isLoading) return <Loading label="Données solaires" className="text-xs" />
  if (isError || !sol) return (
    <p className="text-xs text-txt-dim">
      Pas de données solaires pour cette parcelle (parcelle non bâtie ou module en cours
      d'ingestion — mandat Habitat Solaire).
    </p>
  )
  const src = (sol['sources'] ?? {}) as Record<string, string>
  const score = sol['score_solaire'] as number | null
  const facture = sol['facture_est_eur_mois'] as number | null
  const azimut = sol['azimut_bati_deg'] as number | null
  const aper = (sol['aper_deadline'] ?? []) as Record<string, unknown>[]
  const badges: [string, string, string][] = []  // [label, couleur, titre]
  if (sol['flag_abf']) badges.push(['ABF', '#e8b84d', 'Périmètre ABF — déclaration préalable renforcée probable'])
  if (sol['flag_amiante']) badges.push(['Bâti pré-1997', '#e8734d', String(src['amiante'] ?? '')])
  if (sol['flag_topo_ombrage']) badges.push(['Ombrage topo', '#7d8fa8', 'Production < 80 % de la médiane communale (cirque/rempart)'])
  if (sol['pv_existant']) badges.push([sol['pv_existant'] === 'detecte' ? 'PV détecté' : 'Commune très équipée PV', '#5CE6A1', String(src['pv_existant'] ?? '')])
  if (sol['repowering']) badges.push(['Repowering', '#B497F0', 'Contrat d\'achat 2006-2013 en fin de vie'])
  return (
    <div className="flex flex-col gap-2">
      <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
        <p className="font-mono text-[10px] tracking-widest text-txt-dim">GISEMENT SOLAIRE</p>
        <div className="mt-1.5 flex items-center gap-3">
          <span className="flex-1 h-1.5 overflow-hidden rounded-full bg-line">
            <span style={{ width: `${score ?? 0}%` }} className="block h-full bg-[#f5c84b]" />
          </span>
          <span className="font-display text-sm font-bold text-[#f5c84b]">{score ?? '—'}<span className="text-[10px] text-txt-dim">/100</span></span>
        </div>
        <div className="mt-1 text-[11px] text-txt-mut">
          {sol['prod_spec_kwh_kwc'] ? `${Math.round(Number(sol['prod_spec_kwh_kwc']))} kWh/an par kWc installé` : 'Production spécifique en cours de calcul'}
        </div>
        <p className="mt-1 text-[9.5px] text-txt-dim">{src['gisement']}</p>
      </div>
      <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
        <p className="font-mono text-[10px] tracking-widest text-txt-dim">FACTURE ÉLECTRIQUE — ESTIMATION STATISTIQUE</p>
        <div className="mt-1 text-sm font-bold text-txt-hi">{facture != null ? `~${facture} €/mois` : '—'}</div>
        {sol['conso_est_kwh_an'] != null && <div className="text-[11px] text-txt-mut">{String(sol['conso_est_kwh_an'])} kWh/an estimés</div>}
        <p className="mt-1 text-[9.5px] text-txt-dim">{src['facture']}</p>
      </div>
      <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
        <p className="font-mono text-[10px] tracking-widest text-txt-dim">ORIENTATION DU BÂTI</p>
        <div className="mt-1 text-xs text-txt">
          {azimut != null ? <>Grand axe à <b>{Math.round(azimut)}°</b> (confiance {String(sol['azimut_confiance'] ?? '—')})</> : 'Bâti non significatif ou absent'}
        </div>
        <p className="mt-1 text-[9.5px] text-txt-dim">{src['azimut']}</p>
      </div>
      {badges.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {badges.map(([label, color, title]) => (
            <span key={label} title={title} className="rounded-full px-2 py-0.5 text-[10px] font-medium"
              style={{ background: `${color}22`, color }}>{label}</span>
          ))}
        </div>
      )}
      {sol['proba_proprio_occupant'] != null && (
        <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] text-txt-mut">
          Probabilité propriétaire-occupant : <b className="text-txt">{String(sol['proba_proprio_occupant'])}/100</b>
          <span className="text-txt-dim"> (statistique — carreau INSEE + mutation récente)</span>
        </div>
      )}
      {aper.length > 0 && aper.map((a, i) => (
        <div key={i} className="rounded-lg border border-[#5a2420] bg-[#2a1210] px-3 py-2 text-[11px] text-st-ecartee">
          ● Parking APER {String(a['surface_m2'])} m² — échéance {String(a['echeance'])}
          {a['statut'] === 'depassee' ? ' DÉPASSÉE' : ''} · sanction jusqu\'à {String(a['sanction_eur_an'])} €/an
        </div>
      ))}
      <p className="text-[9.5px] text-txt-dim">{src['aper']}</p>
    </div>
  )
}

// Onglet BILAN — le moteur de faisabilité/bilan EXISTANT, enfin exposé (P0 revue Vic).
function BilanTab({ idu }: { idu: string }) {
  const { data: b, isLoading, isError, refetch } = useQuery({ queryKey: ['bilan', idu], queryFn: () => getFaisabilite(idu) })
  if (isLoading) return <Loading label="Calcul de la pré-faisabilité" className="text-xs" />
  if (isError || !b) return (
    <div className="rounded-lg border border-[#5a2420] bg-[#2a1210] p-3 text-xs">
      <p className="text-st-ecartee">Bilan indisponible.</p>
      <button onClick={() => refetch()} className="mt-2 rounded border border-line-2 px-2 py-1 text-txt">Réessayer</button>
    </div>
  )
  const cap = b.capacite
  const fo = cap?.fourchette ?? {}
  const Sec = ({ t, children }: { t: string; children: React.ReactNode }) => (
    <div>
      <p className="mb-1 font-mono text-[10px] tracking-widest text-txt-dim">{t}</p>
      <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] leading-relaxed text-txt">{children}</div>
    </div>
  )
  return (
    <div className="flex flex-col gap-3">
      {cap ? (
        <Sec t="CAPACITÉ (que peut accueillir ce terrain ?)">
          <div className="font-medium text-txt-hi">{cap.verdict}</div>
          <div className="mt-1 text-txt-mut">
            {fo.niveaux} · emprise bâtie max {fo.emprise_batie_max_m2} m² · SDP {fo.surface_plancher_m2} m² ·
            SHAB vendable ~{fo.shab_vendable_m2} m² · stationnement : {fo.stationnement_regime}
          </div>
          {!cap.calibree && <div className="mt-1 text-[10px] text-st-creuser">⚠ estimation générique (zone non calibrée)</div>}
          <div className="mt-1.5 text-[9.5px] leading-snug text-txt-dim">{cap.bandeau}</div>
        </Sec>
      ) : (
        <Sec t="CAPACITÉ">Zone PLU non résolue pour cette parcelle — capacité non calculable (honnête).</Sec>
      )}
      {b.marche?.median != null && (
        <Sec t="MARCHÉ (prix de sortie secteur)">
          médiane <b className="text-mint">{Number(b.marche.median).toLocaleString('fr-FR')} €/m²</b> ({b.marche.type_prix},
          {' '}{b.marche.n} ventes ≤ {Math.round(b.marche.radius_m)} m) · fiabilité <b>{b.marche.fiabilite}</b>
          {b.marche.tendance ? <span className="text-txt-mut"> · tendance {b.marche.tendance}</span> : null}
          {/* P14 : fraîcheur DVF — de QUAND datent les prix (période réelle en base) */}
          {b.marche.dvf_couverture?.libelle && (
            <div className="mt-1 text-[10px] text-txt-dim">
              DVF — {b.marche.dvf_couverture.libelle} (dernière transaction en base · millésime en vigueur)
            </div>
          )}
        </Sec>
      )}
      {/* mandat bilan-calculette : le BILAN devient INTERACTIF — LABUSE assemble enfin ses
          ingrédients en LE chiffre que le promoteur attend (« combien puis-je payer ? »). */}
      <Calculette idu={idu} />
      <Sec t="FISCAL & LEVIERS">
        <div>QPV : <b className={b.fiscal.qpv ? 'text-mint' : 'text-txt-mut'}>{b.fiscal.qpv ? 'OUI' : 'non'}</b> · TVA : {b.fiscal.tva}</div>
        {b.fiscal.prime_vue_mer && <div className="mt-0.5 text-[#7DE8E0]">Vue mer dégagée — {b.fiscal.prime_vue_mer}</div>}
        <div className="mt-1 text-[10px] text-txt-dim">{b.fiscal.ta_note}</div>
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
      <p className="mb-1 font-mono text-[10px] tracking-widest text-txt-dim">RTAA DOM — RAPPEL RÉGLEMENTAIRE</p>
      <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[10.5px] leading-snug text-txt-mut">
        Construction neuve de logements : protection solaire, ventilation traversante,
        acoustique, aération et ECS renouvelable s'appliquent (seuils d'altitude 400/600 m).
        <button onClick={() => setOpen((o) => !o)} className="ml-1.5 text-mint hover:underline">
          {open ? 'replier' : `${rtaa.exigences.length} exigences →`}
        </button>
      </div>
      {open && (
        <div className="mt-1.5 flex flex-col gap-1.5">
          {rtaa.exigences.map((e, i) => (
            <div key={i} className="rounded-lg border border-line-2 bg-surface-3 px-3 py-2">
              <span className="rounded-full px-1.5 py-0.5 font-mono text-[8.5px] font-semibold uppercase"
                style={{ color: VOLET_COLOR[e.volet] ?? '#8FA69A', background: `${VOLET_COLOR[e.volet] ?? '#8FA69A'}18` }}>
                {e.volet}
              </span>
              <p className="mt-1 text-[10.5px] leading-snug text-txt">{e.exigence}</p>
              {e.condition_altitude && <p className="mt-0.5 text-[9.5px] text-st-creuser">altitude : {e.condition_altitude}</p>}
              <a href={e.url} target="_blank" rel="noreferrer" className="mt-0.5 block text-[9.5px] text-[#7DE8E0] hover:underline">
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
      className="mt-1.5 text-[11px] text-[#B497F0] hover:underline"
      title="Scan patrimoine (M02) : tout le foncier de ce propriétaire sur l'île"
    >
      → tout son patrimoine (M02)
    </button>
  )
}

const TABS: { k: 'synthese' | Onglet | 'bilan' | 'solaire'; label: string }[] = [
  { k: 'synthese', label: 'Synthèse' }, { k: 'regles', label: 'Règles' }, { k: 'risques', label: 'Risques' },
  { k: 'marche', label: 'Marché' }, { k: 'proprio', label: 'Proprio' }, { k: 'solaire', label: 'Solaire' },
  { k: 'bilan', label: 'Bilan' },
]

export function Fiche({ idu }: { idu: string }) {
  const select = useApp((s) => s.select)
  const moduleFiche = useApp((s) => s.moduleFiche)
  const setModule = useApp((s) => s.setModule)
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
  const [tab, setTab] = useState<'synthese' | Onglet | 'bilan' | 'solaire'>('synthese')
  const [iaOpen, setIaOpen] = useState(false)
  // A6 (post-revue) : recherche DANS la fiche (≠ barre du haut). La loupe de la fiche filtre le
  // CONTENU de la fiche (toutes les lignes tracées, tous onglets), pas le dashboard.
  const [ficheSearchOpen, setFicheSearchOpen] = useState(false)
  const [ficheQuery, setFicheQuery] = useState('')
  const { data: f, isLoading, isError, refetch } = useQuery({ queryKey: ['fiche', idu], queryFn: () => getFiche(idu) })
  const fq = ficheQuery.trim().toLowerCase()
  const ficheMatches = fq && f
    ? f.lines.filter((l) => `${l.layer} ${l.detail ?? ''} ${l.source ?? ''} ${l.result ?? ''}`.toLowerCase().includes(fq))
    : []

  const meta = f ? STATUT_META[f.statut] : null
  const qLines = f?.lines.filter((l) => l.axis === 'q') ?? []
  const aLines = f?.lines.filter((l) => l.axis === 'a') ?? []
  const ongletLines = (o: Onglet) => f?.lines.filter((l) => l.onglet === o) ?? []

  return (
    <aside className="absolute right-0 top-0 z-10 flex h-full w-[400px] max-w-full flex-col border-l border-line bg-surface-1 shadow-2xl">
      {f?.statut === 'ecartee' && (
        <div data-bandeau-ecartee className="shrink-0 border-b border-line-2 bg-surface-2 px-5 py-2.5">
          <div className="text-xs font-medium text-st-ecartee">LABUSE l'a écartée — voici pourquoi</div>
          <div className="mt-1 flex flex-col gap-0.5">
            {f.lines.filter((l) => l.result === 'HARD_EXCLUDE').slice(0, 4).map((l) => (
              <div key={l.layer} className="text-[10.5px] leading-snug text-txt-mut">✕ <b className="text-txt">{l.layer}</b> — {l.detail}</div>
            ))}
            {f.lines.filter((l) => l.result === 'HARD_EXCLUDE').length === 0 && (
              <div className="text-[10.5px] text-txt-mut">Aucune exclusion dure : qualité insuffisante (Q {f.q_score} &lt; 50) — détail dans les onglets.</div>
            )}
          </div>
          <div className="mt-1 text-[9.5px] text-txt-dim">Une écartée motivée = de la due diligence offerte — chaque motif est sourcé dans les onglets.</div>
        </div>
      )}
      {f?.evenement === 'rouge' && (
        <div className="shrink-0 border-b border-[#5a2420] bg-[#3a1614] px-5 py-2.5">
          <div className="flex items-center gap-2 text-xs font-medium text-st-ecartee">● ÉVÉNEMENT — force « chaude »</div>
          {f.evenement_detail && <div className="mt-1 text-[11px] leading-snug text-[#e8a99f]">{f.evenement_detail}</div>}
        </div>
      )}

      {/* bloc MODULE (doctrine : en tête de fiche, violet) */}
      {modBlock && (
        <div className="shrink-0 border-b border-[#2a2138] bg-[#171221] px-5 py-3">
          <p className="font-mono text-[10px] tracking-widest text-[#B497F0]">MODULE · {modBlock.module.toUpperCase()}</p>
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

      <div className="flex shrink-0 items-start justify-between border-b border-line px-5 py-4">
        <div className="min-w-0">
          <div className="truncate font-mono text-sm font-medium text-txt-hi">{idu}</div>
          <div className="mt-0.5 text-[11px] text-txt-mut">
            {f?.surface_m2 ? `${f.surface_m2.toLocaleString('fr-FR')} m² · ` : ''}{f?.commune ?? ''}
          </div>
          {meta && (
            <span className="mt-1.5 inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px]" style={{ background: `${meta.color}22`, color: meta.color }}>
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: meta.color }} />{meta.label}
              {f?.evenement === 'rouge' && f.statut === 'chaude' && (
                <span className="rounded-full bg-[#3a1614] px-1.5 text-[9px] font-semibold text-st-ecartee" title="Statut forcé par la bascule événementielle (BODACC) — pas par la matrice Q×A">· ÉVÉNEMENT</span>
              )}
            </span>
          )}
          {f?.score_v?.v_score != null && (
            <span data-badge-v className="ml-1.5 mt-1.5 inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-mono text-[10px] font-semibold"
              style={{
                background: `${f.score_v.brulante ? BRULANTE_COLOR : vBandColor(f.score_v.v_band)}22`,
                color: f.score_v.brulante ? BRULANTE_COLOR : vBandColor(f.score_v.v_band),
              }}
              title={`Vendabilité ${f.score_v.v_band_label} — détail dans la Synthèse`}>
              {f.score_v.brulante && <span aria-hidden>🔥</span>}V {f.score_v.v_score}
            </span>
          )}
          {f?.score_v?.badge && (
            <span className="ml-1.5 mt-1.5 inline-flex rounded-full border border-line-2 px-2 py-0.5 text-[9.5px] text-txt-mut">
              {f.score_v.badge}
            </span>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {/* A6 : la loupe de la fiche cherche DANS la fiche (son contenu), pas dans le dashboard */}
          <button
            onClick={() => setFicheSearchOpen((o) => { if (o) setFicheQuery(''); return !o })}
            className={`flex h-7 w-7 items-center justify-center rounded-md border text-txt-mut hover:border-mint hover:text-mint ${ficheSearchOpen ? 'border-mint text-mint' : 'border-line-2'}`}
            title="Rechercher dans cette fiche (ses données)">
            <svg viewBox="0 0 20 20" className="h-[15px] w-[15px]">
              <circle cx="9" cy="9" r="5.5" fill="none" stroke="currentColor" strokeWidth="1.7" />
              <line x1="13" y1="13" x2="17.5" y2="17.5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
            </svg>
          </button>
          <button onClick={() => select(null)} className="text-txt-mut hover:text-txt-hi" title="Fermer la fiche">✕</button>
        </div>
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

      {!fq && (
      <div className="flex shrink-0 gap-4 overflow-x-auto border-b border-line px-5 py-2 text-xs">
        {TABS.map((t) => (
          <button key={t.k} onClick={() => setTab(t.k)} className={`shrink-0 ${tab === t.k ? 'font-medium text-txt-hi' : 'text-txt-dim hover:text-txt-mut'}`}>
            {t.label}
          </button>
        ))}
      </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-5">
        {/* A6 : recherche active → on remplace les onglets par les lignes de la fiche qui matchent */}
        {fq && f && (
          <div data-fiche-search-results>
            <p className="mb-2 font-mono text-[10px] tracking-widest text-txt-dim">DANS CETTE FICHE · « {ficheQuery.trim()} »</p>
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
        {isError && (
          <div className="rounded-lg border border-[#5a2420] bg-[#2a1210] p-4 text-xs">
            <p className="text-st-ecartee">Impossible de charger la fiche.</p>
            <p className="mt-1 text-txt-dim">Le serveur est peut-être périmé — relancer `labuse api`.</p>
            <button onClick={() => refetch()} className="mt-2 rounded border border-line-2 px-2 py-1 text-txt hover:text-txt-hi">Réessayer</button>
          </div>
        )}
        {!fq && f && tab === 'synthese' && (
          <>
            {f.evenement === 'rouge' && f.statut === 'chaude' && (
              <div data-histoire-evenement className="rounded-lg border border-[#5a2420] bg-[#2a1210] px-3 py-2.5 text-[11.5px] leading-relaxed text-txt">
                Chaude par <b className="text-st-ecartee">ÉVÉNEMENT</b> : le propriétaire
                {f.proprietaire_moral?.denomination ? <> (<b>{f.proprietaire_moral.denomination}</b>)</> : ''} est en
                procédure collective{f.evenement_detail ? <> — {f.evenement_detail.replace(/^.*?:\s*/, '')}</> : ''}.
                Le score qualité ({f.q_score}) n'a pas déclenché ce statut : c'est l'urgence
                du dossier vendeur qui prime (doctrine bascule).
              </div>
            )}
            <EquipementsBadges idu={idu} />
            <ScoreBar label="Qualité" value={f.q_score} color="#5CE6A1" lines={qLines} defaultOpen />
            <ScoreBar label="Accessibilité" value={f.a_score} color="#4ADE96" lines={aLines} />
            {f.score_v && <VendabiliteBlock sv={f.score_v} />}
            <div className="flex items-center gap-3 rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
              <svg viewBox="0 0 32 32" className="h-8 w-8 shrink-0 -rotate-90">
                <circle cx="16" cy="16" r="13" fill="none" stroke="#1E2A23" strokeWidth="3" />
                <circle cx="16" cy="16" r="13" fill="none" stroke={completudeColor(f.completeness_score)} strokeWidth="3"
                  strokeDasharray={2 * Math.PI * 13} strokeDashoffset={2 * Math.PI * 13 * (1 - f.completeness_score / 100)} strokeLinecap="round" />
              </svg>
              <div>
                <div className="text-xs text-txt">Complétude {f.completeness_score}%</div>
                <div className="text-[11px] text-txt-dim">{f.completeness_score >= 50 ? 'Dossier suffisant pour trancher' : 'Dossier incomplet — à creuser'}</div>
              </div>
            </div>
            {f.flags.length > 0 && (
              <div>
                <p className="mb-1.5 font-mono text-[11px] tracking-widest text-txt-dim">FLAGS</p>
                <div className="flex flex-col gap-1">{f.flags.map((l, i) => <Line key={i} line={l} />)}</div>
              </div>
            )}
          </>
        )}
        {!fq && f && tab === 'proprio' && f.proprietaire_moral && (
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
            <p className="font-mono text-[10px] tracking-widest text-txt-dim">PROPRIÉTAIRE (DGFiP)</p>
            <div className="mt-1 text-xs font-medium text-txt-hi">{f.proprietaire_moral.denomination ?? '—'}</div>
            <div className="mt-0.5 flex items-center gap-3 text-[10.5px] text-txt-mut">
              {f.proprietaire_moral.siren && <span className="font-mono">SIREN {f.proprietaire_moral.siren}</span>}
              {f.proprietaire_moral.groupe_label && <span>{f.proprietaire_moral.groupe_label}</span>}
            </div>
            {f.proprietaire_moral.siren && <PatrimoineLink siren={f.proprietaire_moral.siren} />}
          </div>
        )}
        {!fq && f && tab === 'proprio' && !f.proprietaire_moral && (
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] text-txt-mut">
            Propriétaire : personne physique ou non recensé au fichier des personnes morales
            (identité nominative : workflow SPF/CERFA, jamais automatisée).
          </div>
        )}
        {!fq && f && (tab === 'regles' || tab === 'risques' || tab === 'marche' || tab === 'proprio') && (
          <div>
            {ongletLines(tab).length ? ongletLines(tab).map((l, i) => <Line key={i} line={l} />)
              : <p className="text-xs text-txt-dim">Aucun signal sur cet onglet.</p>}
          </div>
        )}
        {!fq && f && tab === 'solaire' && <SolaireTab idu={idu} />}
        {!fq && f && tab === 'bilan' && <BilanTab idu={idu} />}
      </div>

      <div className="shrink-0 border-t border-line px-5 py-3">
        {/* P6 (dernière passe) : barre d'actions REPRISE — deux rangées régulières, boutons de
            HAUTEUR UNIFORME (h-8). Rangée 1 = actions (pipeline/suivre/partager/IA), rangée 2 =
            exports & liens externes, tous à largeur égale. Fini le « bien vilain ». */}
        <div className="flex items-center gap-2">
          <PipelineButton idu={idu} />
          <WatchButton idu={idu} />
          <ShareButton idu={idu} />
          <div className="relative shrink-0">
            <button onClick={() => setIaOpen((o) => !o)}
              className="flex h-8 items-center justify-center rounded-lg border border-line-2 px-3 text-xs text-txt hover:text-txt-hi" title="Analyse IA">
              IA
            </button>
            {iaOpen && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setIaOpen(false)} />
                <IAPanel idu={idu} onClose={() => setIaOpen(false)} />
              </>
            )}
          </div>
        </div>
        <div className="mt-2 flex items-stretch gap-2">
          <a href={pdfUrl(idu, tab === 'bilan' ? calculette : null)} target="_blank" rel="noreferrer"
            className="flex h-8 flex-1 items-center justify-center rounded-lg border border-line-2 px-3 text-xs text-txt hover:text-txt-hi"
            title={calculette && tab === 'bilan' ? 'Exporter la fiche en PDF (avec votre charge foncière)' : 'Exporter la fiche en PDF'}>
            PDF
          </a>
          {/* Lot 4 (wave-adresses) : Dossier parcelle brandé — comité d'engagement, banque,
              client final. Quota mensuel selon plan ; 501 tant que le générateur (module
              Flash) n'est pas mergé — le serveur répond un message honnête. */}
          <a href={`/dossier/${idu}.pdf`} target="_blank" rel="noreferrer"
            className="flex h-8 flex-1 items-center justify-center rounded-lg border border-line-2 px-3 text-xs text-txt hover:text-txt-hi"
            title="Dossier parcelle PDF brandé (carte, zonage calibré, risques, DVF, permis) — usage interne">
            Dossier
          </a>
          {f && (
            <button onClick={() => setModule('temps')}
              className="flex h-8 flex-1 items-center justify-center rounded-lg border border-line-2 px-3 text-xs text-txt hover:text-txt-hi"
              title="Ce terrain en 1950 — comparateur temporel (M08)">
              1950
            </button>
          )}
          {f?.coords && (
            /* R8 (revue Vic n°2) : cadastre OFFICIEL (Géoportail IGN, PCI Express, permalien centré) */
            <a data-cadastre-link
              href={`https://www.geoportail.gouv.fr/carte?c=${f.coords[0]},${f.coords[1]}&z=18&l0=CADASTRALPARCELS.PARCELLAIRE_EXPRESS::GEOPORTAIL:OGC:WMTS(1)&permalink=yes`}
              target="_blank" rel="noreferrer"
              className="flex h-8 flex-1 items-center justify-center rounded-lg border border-line-2 px-3 text-xs text-txt hover:text-txt-hi"
              title="Vérifier la géométrie sur le cadastre OFFICIEL (Géoportail IGN — parcellaire PCI Express, centré sur la parcelle)">
              Cadastre
            </a>
          )}
          {f && (
            <a href={`https://www.google.com/maps/@${f.coords[1]},${f.coords[0]},19z/data=!3m1!1e3`}
              target="_blank" rel="noreferrer"
              className="flex h-8 w-9 shrink-0 items-center justify-center rounded-lg border border-line-2 text-xs text-txt hover:text-txt-hi"
              title="Ouvrir la parcelle dans Google Maps (satellite)">
              G
            </a>
          )}
        </div>
        <p className="mt-2.5 text-[10px] leading-tight text-txt-dim">
          Estimations indicatives issues de données publiques — ne valent ni conseil juridique/notarial ni
          garantie de constructibilité. À vérifier au règlement et auprès des services.
        </p>
      </div>
    </aside>
  )
}
