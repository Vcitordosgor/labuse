// DASHBOARD-V1 · D6 — SOURCES : les 59, leur fraîcheur, leur cadence. Badge « À mettre à
// jour » = cadence dépassée (calcul auto backend) ; la cadence de CHAQUE source se règle ici ;
// « Relancer l'ingestion » n'apparaît QUE si une commande existe (config/sources_ingestion.yaml).
// Panneau CRON (verdicts /healthz/crons + dernières exécutions ingestion_runs) + panneau grisé
// « Agent de veille » (V2 — spec : docs/audit-2026-08/DASHBOARD/AGENT-VEILLE-SPEC.md).
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { getAdminSources, getHealthzCrons, postAdminSourceCadence, postAdminSourceRelancer, type AdminSource } from '../../lib/api'
import { ActBtn, Chip, Panel, PHead } from './AdminView'

const fmtReu = (iso?: string | null) => {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat('fr-FR', { timeZone: 'Indian/Reunion', day: '2-digit', month: '2-digit' }).format(new Date(iso))
  } catch { return '—' }
}

function SourceRow({ s, cadences }: { s: AdminSource; cadences: string[] }) {
  const qc = useQueryClient()
  const [msg, setMsg] = useState<string | null>(null)
  const cad = useMutation({
    mutationFn: (v: string | null) => postAdminSourceCadence(s.id, v),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-sources'] }),
  })
  const rel = useMutation({
    mutationFn: () => postAdminSourceRelancer(s.id),
    onSuccess: (r) => setMsg(`Relancée (${r.label}) — log ${r.log}`),
    onError: () => setMsg('Relance impossible.'),
  })
  return (
    <tr className="border-b border-line last:border-b-0 hover:bg-surface-3">
      <td className="px-4 py-2.5"><b className="text-txt">{s.name}</b>
        {msg && <div className="mt-1 text-[10.5px] text-mint">{msg}</div>}
      </td>
      <td className="px-4 py-2.5 font-mono text-xs text-txt-mut">{s.millesime ?? '—'}</td>
      <td className="px-4 py-2.5 font-mono text-xs text-txt-mut">{fmtReu(s.ingere_le)}</td>
      <td className="px-4 py-2.5">
        <select value={s.cadence ?? ''} onChange={(e) => cad.mutate(e.target.value || null)} data-cadence={s.id}
          className="rounded-md border border-line-2 bg-bg px-1.5 py-1 font-mono text-[11px] text-txt-mut outline-none focus:border-mint">
          <option value="">—</option>
          {cadences.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </td>
      <td className="px-4 py-2.5">
        {s.a_jour === false ? <Chip tone="warn">À mettre à jour</Chip>
          : s.a_jour === true ? <Chip tone="ok">OK</Chip>
            : <Chip>sans échéance</Chip>}
      </td>
      <td className="px-4 py-2.5 text-right">
        {s.relance && (
          <ActBtn tone="ghost" disabled={rel.isPending}
            onClick={() => { if (window.confirm(`Relancer l'ingestion « ${s.relance} » maintenant ?\n\nMême commande que le cron, détachée — peut durer plusieurs minutes.`)) rel.mutate() }}>
            {rel.isPending ? 'Lancement…' : "Relancer l'ingestion"}
          </ActBtn>
        )}
      </td>
    </tr>
  )
}

export function SourcesSection() {
  const q = useQuery({ queryKey: ['admin-sources'], queryFn: getAdminSources, refetchInterval: 300_000 })
  const crons = useQuery({ queryKey: ['healthz-crons'], queryFn: getHealthzCrons, refetchInterval: 300_000 })
  const [filtre, setFiltre] = useState('')
  const d = q.data
  if (!d) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>
  const visibles = d.sources.filter((s) => s.name.toLowerCase().includes(filtre.toLowerCase()))
  return (
    <>
      <div className="mb-3.5 flex flex-wrap items-center gap-2">
        {d.synthese.a_mettre_a_jour > 0 && <Chip tone="warn">{d.synthese.a_mettre_a_jour} à mettre à jour</Chip>}
        <Chip tone="ok">{d.synthese.ok} OK</Chip>
        {d.synthese.sans_echeance > 0 && <Chip>{d.synthese.sans_echeance} sans échéance (cadence à régler)</Chip>}
        <label className="ml-auto flex min-w-[210px] items-center gap-2 rounded-lg border border-line bg-surface-1 px-3 py-1.5 text-xs text-txt-dim">
          ⌕ <input value={filtre} onChange={(e) => setFiltre(e.target.value)} placeholder="Filtrer les sources…" data-sources-filtre
            className="w-full bg-transparent text-txt outline-none" />
        </label>
      </div>
      <Panel>
        <table className="w-full text-[13px]">
          <thead>
            <tr>
              {['Source', 'Millésime amont', 'Ingéré le', 'Cadence attendue', 'État', ''].map((h) => (
                <th key={h} className="border-b border-line px-4 py-2.5 text-left font-mono text-[9.5px] font-medium uppercase tracking-[0.12em] text-txt-dim">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibles.map((s) => <SourceRow key={s.id} s={s} cadences={d.cadences} />)}
            {!visibles.length && <tr><td colSpan={6} className="px-4 py-6 text-center text-xs text-txt-mut">Aucune source ne correspond au filtre.</td></tr>}
          </tbody>
        </table>
        <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-xs text-txt-mut">
          <b className="text-txt">« À mettre à jour »</b> = cadence dépassée, calculé automatiquement (date d'ingestion vs cadence).
          La cadence de chaque source se règle sur cette page. Les sources « à mettre à jour » sont triées d'abord.
        </div>
      </Panel>

      <div className="grid grid-cols-2 gap-3.5 max-[1100px]:grid-cols-1">
        <Panel className="mb-0">
          <PHead>CRON nocturne</PHead>
          <ul>
            {crons.data && Object.entries(crons.data.crons).map(([nom, c]) => (
              <li key={nom} className="flex items-center gap-3 border-b border-line px-4 py-2.5 text-[13px] last:border-b-0">
                <Chip tone={c.statut === 'ok' || c.statut === 'frais' ? 'ok' : c.statut === 'non_trace_db' ? 'off' : 'warn'}>{c.statut.replace(/_/g, ' ')}</Chip>
                <span className="min-w-0 flex-1 truncate"><b>{nom}</b>{c.note ? ` — ${c.note}` : ''}</span>
              </li>
            ))}
          </ul>
          <div className="border-t border-line px-4 py-2">
            <div className="mb-1 font-mono text-[9.5px] uppercase tracking-[0.14em] text-txt-dim">Dernières exécutions (ingestion_runs)</div>
            {d.runs.slice(0, 5).map((r, i) => (
              <div key={i} className="flex items-center gap-2 py-1 text-xs text-txt-mut">
                <span className="font-mono text-[10.5px] text-txt-dim">{fmtReu(r.started_at)}</span>
                <Chip tone={r.status === 'ok' || r.status === 'success' ? 'ok' : r.status ? 'warn' : 'off'}>{r.status ?? '—'}</Chip>
                <span className="truncate">{r.name ?? 'ingestion'}</span>
              </div>
            ))}
            {!d.runs.length && <div className="py-2 text-xs text-txt-dim">Aucune exécution tracée.</div>}
          </div>
        </Panel>
        <Panel className="mb-0 opacity-60">
          <PHead>Agent de veille des sources <Chip>V2</Chip></PHead>
          <div className="p-4 text-xs leading-relaxed text-txt-mut">
            Un job qui surveille chaque portail amont (data.gouv, IGN, GPU, Sudocuh…), détecte un
            nouveau millésime publié et notifie : « DVF S2 2026 disponible — lancer l'ingestion ? ».
            Il ne lance jamais l'ingestion lui-même. La table des cadences ci-dessus couvre le besoin
            en attendant. Spécification complète : <span className="font-mono text-[10.5px]">docs/audit-2026-08/DASHBOARD/AGENT-VEILLE-SPEC.md</span>.
          </div>
        </Panel>
      </div>
    </>
  )
}
