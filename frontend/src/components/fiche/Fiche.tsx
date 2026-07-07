import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { addToPipeline, createShare, getFaisabilite, getFiche, getPipelineForParcel, getWatch, iaPourquoi, iaSynthese, pdfUrl, toggleWatch } from '../../lib/api'
import { completudeColor, STATUT_META } from '../../lib/status'
import type { FicheLine, Onglet } from '../../lib/types'
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

// M14 — suivi de cible : événements sur cette parcelle SANS l'entrer au pipeline.
function WatchButton({ idu }: { idu: string }) {
  const qc = useQueryClient()
  const w = useQuery({ queryKey: ['watch', idu], queryFn: () => getWatch(idu) })
  const t = useMutation({ mutationFn: () => toggleWatch(idu), onSuccess: () => qc.invalidateQueries({ queryKey: ['watch', idu] }) })
  const on = w.data?.watched
  return (
    <button onClick={() => t.mutate()}
      className={`rounded-lg border px-2.5 py-1.5 text-xs ${on ? 'border-mint text-mint' : 'border-line-2 text-txt hover:text-txt-hi'}`}
      title={on ? 'Suivie — les événements alimentent la cloche' : 'Suivre cette parcelle (alertes sans pipeline)'}>
      {on ? '👁 Suivie' : '👁'}
    </button>
  )
}

// M20 — pack apporteur : lien public lecture seule, filigrané + horodaté + compteur de vues.
function ShareButton({ idu }: { idu: string }) {
  const share = useMutation({ mutationFn: () => createShare(idu) })
  return (
    <div className="relative">
      <button onClick={() => share.mutate()}
        className="rounded-lg border border-line-2 px-2.5 py-1.5 text-xs text-txt hover:text-txt-hi"
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
      className={`flex-1 rounded-lg py-1.5 text-xs font-medium ${
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

// Onglet BILAN — le moteur de faisabilité/bilan EXISTANT, enfin exposé (P0 revue Vic).
function BilanTab({ idu }: { idu: string }) {
  const { data: b, isLoading, isError, refetch } = useQuery({ queryKey: ['bilan', idu], queryFn: () => getFaisabilite(idu) })
  if (isLoading) return <p className="text-xs text-txt-dim">Calcul de la pré-faisabilité…</p>
  if (isError || !b) return (
    <div className="rounded-lg border border-[#5a2420] bg-[#2a1210] p-3 text-xs">
      <p className="text-st-ecartee">Bilan indisponible.</p>
      <button onClick={() => refetch()} className="mt-2 rounded border border-line-2 px-2 py-1 text-txt">Réessayer</button>
    </div>
  )
  const cap = b.capacite
  const fo = cap?.fourchette ?? {}
  const eur = (x: unknown) => (x == null ? '—' : `${Math.round(Number(x) / 1000).toLocaleString('fr-FR')} k€`)
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
        </Sec>
      )}
      {b.bilan && (
        <Sec t="BILAN INDICATIF (charge foncière)">
          <div>{b.bilan.verdict}</div>
          {b.bilan.charge_fonciere && (
            <div className="mt-1 text-txt-mut">
              CF médiane {eur(b.bilan.charge_fonciere.median ?? b.bilan.charge_fonciere.mediane)} —
              c'est ce qu'un opérateur peut payer CE terrain, hypothèses affichées ci-dessous.
            </div>
          )}
          <details className="mt-1.5">
            <summary className="cursor-pointer text-[10px] text-txt-dim">hypothèses ({(b.bilan.hypotheses ?? []).length})</summary>
            <ul className="mt-1 list-inside list-disc text-[10px] text-txt-dim">
              {(b.bilan.hypotheses ?? []).map((h: string, i: number) => <li key={i}>{h}</li>)}
            </ul>
          </details>
        </Sec>
      )}
      <Sec t="FISCAL & LEVIERS">
        <div>QPV : <b className={b.fiscal.qpv ? 'text-mint' : 'text-txt-mut'}>{b.fiscal.qpv ? 'OUI' : 'non'}</b> · TVA : {b.fiscal.tva}</div>
        {b.fiscal.prime_vue_mer && <div className="mt-0.5 text-[#7DE8E0]">Vue mer dégagée — {b.fiscal.prime_vue_mer}</div>}
        <div className="mt-1 text-[10px] text-txt-dim">{b.fiscal.ta_note}</div>
      </Sec>
    </div>
  )
}

const TABS: { k: 'synthese' | Onglet | 'bilan'; label: string }[] = [
  { k: 'synthese', label: 'Synthèse' }, { k: 'regles', label: 'Règles' }, { k: 'risques', label: 'Risques' },
  { k: 'marche', label: 'Marché' }, { k: 'proprio', label: 'Proprio' }, { k: 'bilan', label: 'Bilan' },
]

export function Fiche({ idu }: { idu: string }) {
  const select = useApp((s) => s.select)
  const moduleFiche = useApp((s) => s.moduleFiche)
  const setModule = useApp((s) => s.setModule)
  const modBlock = moduleFiche[idu]
  const sourceLine = useApp((s) => s.sourceLine)
  // Échap ferme la fiche — sauf si le drawer source est ouvert (il consomme Échap en premier)
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !useApp.getState().sourceLine && !useApp.getState().tool) select(null)
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [select])
  void sourceLine
  const [tab, setTab] = useState<'synthese' | Onglet | 'bilan'>('synthese')
  const [iaOpen, setIaOpen] = useState(false)
  const { data: f, isLoading, isError, refetch } = useQuery({ queryKey: ['fiche', idu], queryFn: () => getFiche(idu) })

  const meta = f ? STATUT_META[f.statut] : null
  const qLines = f?.lines.filter((l) => l.axis === 'q') ?? []
  const aLines = f?.lines.filter((l) => l.axis === 'a') ?? []
  const ongletLines = (o: Onglet) => f?.lines.filter((l) => l.onglet === o) ?? []

  return (
    <aside className="absolute right-0 top-0 z-10 flex h-full w-[400px] max-w-full flex-col border-l border-line bg-surface-1 shadow-2xl">
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
            </span>
          )}
        </div>
        <button onClick={() => select(null)} className="shrink-0 text-txt-mut hover:text-txt-hi" title="Fermer la fiche">✕</button>
      </div>

      <div className="flex shrink-0 gap-4 overflow-x-auto border-b border-line px-5 py-2 text-xs">
        {TABS.map((t) => (
          <button key={t.k} onClick={() => setTab(t.k)} className={`shrink-0 ${tab === t.k ? 'font-medium text-txt-hi' : 'text-txt-dim hover:text-txt-mut'}`}>
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-5">
        {isLoading && <p className="text-xs text-txt-dim">Chargement…</p>}
        {isError && (
          <div className="rounded-lg border border-[#5a2420] bg-[#2a1210] p-4 text-xs">
            <p className="text-st-ecartee">Impossible de charger la fiche.</p>
            <p className="mt-1 text-txt-dim">Le serveur est peut-être périmé — relancer `labuse api`.</p>
            <button onClick={() => refetch()} className="mt-2 rounded border border-line-2 px-2 py-1 text-txt hover:text-txt-hi">Réessayer</button>
          </div>
        )}
        {f && tab === 'synthese' && (
          <>
            <ScoreBar label="Qualité" value={f.q_score} color="#5CE6A1" lines={qLines} defaultOpen />
            <ScoreBar label="Accessibilité" value={f.a_score} color="#4ADE96" lines={aLines} />
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
        {f && (tab === 'regles' || tab === 'risques' || tab === 'marche' || tab === 'proprio') && (
          <div>
            {ongletLines(tab).length ? ongletLines(tab).map((l, i) => <Line key={i} line={l} />)
              : <p className="text-xs text-txt-dim">Aucun signal sur cet onglet.</p>}
          </div>
        )}
        {f && tab === 'bilan' && <BilanTab idu={idu} />}
      </div>

      <div className="shrink-0 border-t border-line px-5 py-3">
        <div className="flex gap-2">
          <PipelineButton idu={idu} />
          <WatchButton idu={idu} />
          <ShareButton idu={idu} />
          <a href={pdfUrl(idu)} target="_blank" rel="noreferrer"
            className="rounded-lg border border-line-2 px-3 py-1.5 text-xs text-txt hover:text-txt-hi" title="Exporter la fiche en PDF">
            PDF
          </a>
          {f && (
            <button onClick={() => setModule('temps')}
              className="rounded-lg border border-line-2 px-2.5 py-1.5 text-xs text-txt hover:text-txt-hi"
              title="Ce terrain en 1950 — comparateur temporel (M08)">
              1950
            </button>
          )}
          {f && (
            <a href={`https://www.google.com/maps/@${f.coords[1]},${f.coords[0]},19z/data=!3m1!1e3`}
              target="_blank" rel="noreferrer"
              className="rounded-lg border border-line-2 px-3 py-1.5 text-xs text-txt hover:text-txt-hi"
              title="Ouvrir la parcelle dans Google Maps (satellite) — deep-link, pas de tuiles intégrées (CGU)">
              G
            </a>
          )}
          <div className="relative">
            <button onClick={() => setIaOpen((o) => !o)}
              className="rounded-lg border border-line-2 px-3 py-1.5 text-xs text-txt hover:text-txt-hi" title="Analyse IA">
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
        <p className="mt-2.5 text-[10px] leading-tight text-txt-dim">
          Estimations indicatives issues de données publiques — ne valent ni conseil juridique/notarial ni
          garantie de constructibilité. À vérifier au règlement et auprès des services.
        </p>
      </div>
    </aside>
  )
}
