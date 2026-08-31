// CRON-2 (K7) — la page CRON de l'admin : un rang par job (description, planif heure Réunion, dernière
// exécution, statut, compteurs, prochaine exécution), bouton « Lancer maintenant » (via la CLI → même
// verrou : un job en cours refuse le double lancement), dernières lignes du log, mention dry-run.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { getAdminCron, getAdminCronLog, postAdminCronRun, type CronJob } from '../../lib/api'

const TON: Record<string, { c: string; l: string }> = {
  ok: { c: 'text-mint bg-mint/12', l: 'OK' },
  'dry-run': { c: 'text-viz-cyan bg-viz-cyan/12', l: 'DRY-RUN' },
  echec: { c: 'text-st-ecartee bg-st-ecartee/15', l: 'ÉCHEC' },
  timeout: { c: 'text-amber bg-amber/12', l: 'TIMEOUT' },
  en_cours: { c: 'text-amber bg-amber/12', l: 'EN COURS' },
}
const fmtDate = (s: string | null) => (s ? new Date(s).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—')
const compteursCourts = (c: Record<string, unknown> | null) => {
  if (!c || !Object.keys(c).length) return '—'
  return Object.entries(c).slice(0, 4).map(([k, v]) => `${k}=${typeof v === 'object' ? '…' : v}`).join(' · ')
}

function JobRow({ j, onRun, ouvrirLog }: { j: CronJob; onRun: () => void; ouvrirLog: () => void }) {
  const t = TON[j.dernier.statut ?? ''] ?? { c: 'text-txt-dim bg-surface-3', l: (j.dernier.statut ?? 'jamais').toUpperCase() }
  return (
    <div data-cron-row={j.nom} className="grid grid-cols-[1fr_auto] gap-2 border-b border-line-2 px-3 py-2.5">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <b className="text-[13px] font-semibold text-txt-hi">{j.nom}</b>
          <span className={`rounded px-1.5 py-0.5 font-mono text-[9.5px] ${t.c}`}>{t.l}</span>
          {j.envoie_mail && j.dernier.dry_run && <span className="rounded bg-viz-cyan/12 px-1.5 py-0.5 font-mono text-[9px] text-viz-cyan" title="SMTP non branché : le mail est calculé et logué, jamais envoyé">dry-run</span>}
        </div>
        <p className="mt-0.5 text-[11.5px] leading-snug text-txt-mut">{j.titre}</p>
        <p className="mt-1 flex flex-wrap gap-x-3 text-[10.5px] text-txt-dim">
          <span>⏱ {j.cadence} · <b className="text-txt-mut">{j.heure_reunion}</b> (Réunion)</span>
          <span>◀ dernière : {fmtDate(j.dernier.fin)}{j.dernier.duree_s != null ? ` · ${j.dernier.duree_s}s` : ''}</span>
          <span>▶ prochaine : {j.prochaine_reunion ?? '—'}</span>
        </p>
        <p className="mt-0.5 truncate font-mono text-[10px] text-txt-dim" title={compteursCourts(j.dernier.compteurs)}>
          {j.dernier.erreur ? <span className="text-st-ecartee">{j.dernier.erreur}</span> : compteursCourts(j.dernier.compteurs)}
        </p>
      </div>
      <div className="flex shrink-0 flex-col items-end gap-1">
        <button data-cron-run={j.nom} onClick={onRun}
          className="rounded-md border border-mint/50 bg-mint/12 px-2.5 py-1 text-[11px] font-medium text-mint hover:bg-mint/20">Lancer maintenant</button>
        <button data-cron-log={j.nom} onClick={ouvrirLog} className="text-[10.5px] text-txt-dim hover:text-txt">voir le log →</button>
      </div>
    </div>
  )
}

export function CronSection() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-cron'], queryFn: getAdminCron, refetchInterval: 5000 })
  const [logNom, setLogNom] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  const run = useMutation({
    mutationFn: postAdminCronRun,
    onSuccess: (r) => { setMsg(r.ok ? `${r.nom} : ${r.note}` : `Refusé : ${r.motif}`); setTimeout(() => qc.invalidateQueries({ queryKey: ['admin-cron'] }), 1500) },
  })
  const logQ = useQuery({ queryKey: ['admin-cron-log', logNom], queryFn: () => getAdminCronLog(logNom as string), enabled: !!logNom })
  const jobs = q.data?.jobs ?? []
  const dryRun = jobs.some((j) => j.envoie_mail && j.dernier.dry_run)

  return (
    <div className="flex flex-col gap-3">
      {dryRun && (
        <div data-cron-dryrun className="rounded-lg border border-viz-cyan/30 bg-viz-cyan/[0.06] px-3 py-2 text-[11.5px] text-txt">
          <b className="text-viz-cyan">Mode dry-run</b> — SMTP/Brevo n'est pas branché : les jobs qui enverraient un mail calculent, loguent et marquent « dry-run », mais n'envoient rien. Aucune erreur bloquante.
        </div>
      )}
      {msg && <p className="rounded-md bg-surface-2 px-3 py-1.5 text-[11.5px] text-txt-mut">{msg}</p>}
      <p className="text-[11px] text-txt-dim">{q.data?.note}</p>
      <div className="overflow-hidden rounded-xl border border-line-2">
        {q.isLoading && <p className="p-4 text-[12px] text-txt-dim">Chargement…</p>}
        {jobs.map((j) => (
          <JobRow key={j.nom} j={j} onRun={() => run.mutate(j.nom)} ouvrirLog={() => setLogNom(j.nom)} />
        ))}
      </div>

      {logNom && (
        <div data-cron-logview className="rounded-xl border border-line-2 bg-surface-2">
          <div className="flex items-center justify-between border-b border-line-2 px-3 py-2">
            <span className="font-mono text-[11px] text-txt-mut">LOG · {logNom}</span>
            <button onClick={() => setLogNom(null)} className="text-txt-dim hover:text-txt">✕</button>
          </div>
          <pre className="max-h-64 overflow-auto px-3 py-2 font-mono text-[10.5px] leading-snug text-txt">
            {logQ.isLoading ? 'Chargement…' : (logQ.data?.lignes?.length ? logQ.data.lignes.join('\n') : (logQ.data?.note ?? 'aucune ligne.'))}
          </pre>
        </div>
      )}
    </div>
  )
}
