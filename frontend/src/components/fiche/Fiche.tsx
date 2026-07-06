import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getFiche } from '../../lib/api'
import { completudeColor, STATUT_META } from '../../lib/status'
import type { FicheLine, Onglet } from '../../lib/types'
import { useApp } from '../../store/useApp'

const SEV_COLOR: Record<string, string> = { fort: '#E8695A', moyen: '#E8B44C', faible: '#C9DCD1', info: '#8FA69A' }

function Weight({ w }: { w: number | null }) {
  if (w == null) return <span className="w-10 text-right font-mono text-[11px] text-txt-dim">?</span>
  const c = w > 0 ? 'text-st-chaude' : w < 0 ? 'text-st-ecartee' : 'text-txt-dim'
  return <span className={`w-10 shrink-0 text-right font-mono text-xs font-semibold ${c}`}>{w > 0 ? `+${w}` : w}</span>
}

// Source cliquable → page Sources (câblée en Brique 5). Exigence #5.
function SourceRef({ line }: { line: FicheLine }) {
  const trace = line.source_table && line.source_id != null ? `${line.source_table}#${line.source_id}` : null
  return (
    <div className="mt-0.5 flex items-center gap-2 text-[10px] text-txt-dim">
      {line.source && (
        <button className="text-[#5a7d6c] hover:text-mint" title="Voir la source (page Sources — Brique 5)">
          {line.source}
        </button>
      )}
      {trace && <span className="font-mono text-[#4a5a52]">{trace}</span>}
      {line.date && <span className="ml-auto font-mono">{line.date}</span>}
    </div>
  )
}

function Line({ line }: { line: FicheLine }) {
  return (
    <div className="flex gap-3 border-b border-[#141d17] py-2 last:border-0">
      <Weight w={line.weight} />
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

// Barre de sous-score dépliable (exigence #2 : Qualité /100 et Accessibilité /100 → lignes tracées).
function ScoreBar({ label, value, color, lines }: { label: string; value: number; color: string; lines: FicheLine[] }) {
  const [open, setOpen] = useState(label === 'Qualité')
  const weighted = lines.filter((l) => l.weight != null && l.weight !== 0).sort((a, b) => Math.abs(b.weight!) - Math.abs(a.weight!))
  return (
    <div className="rounded-lg border border-line-2 bg-surface-2">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-3 px-3 py-2.5">
        <span className="w-24 shrink-0 text-left text-xs text-txt">{label}</span>
        <span className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-line">
          <span className="absolute left-0 top-0 h-full rounded-full" style={{ width: `${value}%`, background: color }} />
        </span>
        <span className="w-8 text-right font-display text-sm font-bold" style={{ color }}>{value}</span>
        <span className="text-txt-dim">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div className="border-t border-line-2 px-3 py-1">
          {weighted.length ? weighted.map((l, i) => <Line key={i} line={l} />) : <p className="py-2 text-[11px] text-txt-dim">Aucun signal chiffré.</p>}
        </div>
      )}
    </div>
  )
}

const TABS: { k: 'synthese' | Onglet | 'bilan'; label: string }[] = [
  { k: 'synthese', label: 'Synthèse' }, { k: 'regles', label: 'Règles' }, { k: 'risques', label: 'Risques' },
  { k: 'marche', label: 'Marché' }, { k: 'proprio', label: 'Proprio' }, { k: 'bilan', label: 'Bilan' },
]

export function Fiche({ idu }: { idu: string }) {
  const select = useApp((s) => s.select)
  const [tab, setTab] = useState<'synthese' | Onglet | 'bilan'>('synthese')
  const { data: f, isLoading } = useQuery({ queryKey: ['fiche', idu], queryFn: () => getFiche(idu) })

  const meta = f ? STATUT_META[f.statut] : null
  const qLines = f?.lines.filter((l) => l.axis === 'q') ?? []
  const aLines = f?.lines.filter((l) => l.axis === 'a') ?? []
  const ongletLines = (o: Onglet) => f?.lines.filter((l) => l.onglet === o) ?? []

  return (
    <aside className="absolute right-0 top-0 z-10 flex h-full w-[400px] flex-col border-l border-line bg-surface-1 shadow-2xl">
      {/* Bandeau événement — héros (exigence #4) */}
      {f?.evenement === 'rouge' && (
        <div className="border-b border-[#5a2420] bg-[#3a1614] px-5 py-2.5">
          <div className="flex items-center gap-2 text-xs font-medium text-st-ecartee">● ÉVÉNEMENT — force « chaude »</div>
          {f.evenement_detail && <div className="mt-1 text-[11px] text-[#e8a99f]">{f.evenement_detail}</div>}
        </div>
      )}

      {/* En-tête : IDU + statut */}
      <div className="flex items-start justify-between border-b border-line px-5 py-4">
        <div>
          <div className="font-mono text-sm font-medium text-txt-hi">{idu}</div>
          <div className="mt-0.5 text-[11px] text-txt-mut">{f?.surface_m2 ? `${f.surface_m2.toLocaleString('fr-FR')} m²` : ''} · {f?.commune}</div>
          {meta && (
            <span className="mt-1.5 inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px]" style={{ background: `${meta.color}22`, color: meta.color }}>
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: meta.color }} />{meta.label}
            </span>
          )}
        </div>
        <button onClick={() => select(null)} className="text-txt-mut hover:text-txt-hi" title="Fermer">✕</button>
      </div>

      {/* Onglets */}
      <div className="flex gap-4 border-b border-line px-5 py-2 text-xs">
        {TABS.map((t) => (
          <button key={t.k} onClick={() => setTab(t.k)} className={tab === t.k ? 'font-medium text-txt-hi' : 'text-txt-dim hover:text-txt-mut'}>{t.label}</button>
        ))}
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-5">
        {isLoading && <p className="text-xs text-txt-dim">Chargement…</p>}
        {f && tab === 'synthese' && (
          <>
            <ScoreBar label="Qualité" value={f.q_score} color="#5CE6A1" lines={qLines} />
            <ScoreBar label="Accessibilité" value={f.a_score} color="#4ADE96" lines={aLines} />
            <div className="flex items-center gap-3 rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
              <svg viewBox="0 0 32 32" className="h-8 w-8 -rotate-90">
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
        {f && tab === 'bilan' && (
          <div className="flex flex-1 items-center justify-center text-center text-xs text-txt-dim">
            Bilan (charge foncière admissible : SDP × prix de sortie − coûts) — à paramétrer.
          </div>
        )}
      </div>

      {/* Actions + non-garantie (exigence #8) */}
      <div className="border-t border-line px-5 py-3">
        <div className="flex gap-2">
          <button className="flex-1 rounded-lg bg-mint py-1.5 text-xs font-medium text-mint-ink">+ Pipeline</button>
          <button className="rounded-lg border border-line-2 px-3 py-1.5 text-xs text-txt hover:text-txt-hi" title="Export PDF (Brique 3)">PDF</button>
          <button className="rounded-lg border border-line-2 px-3 py-1.5 text-xs text-txt hover:text-txt-hi" title="Analyse IA (V1.x)">IA</button>
        </div>
        <p className="mt-2.5 text-[10px] leading-tight text-txt-dim">
          Estimations indicatives issues de données publiques — ne valent ni conseil juridique/notarial ni
          garantie de constructibilité. À vérifier au règlement et auprès des services.
        </p>
      </div>
    </aside>
  )
}
