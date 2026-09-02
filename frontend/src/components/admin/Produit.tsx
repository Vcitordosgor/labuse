// DASHBOARD-V1 · D7 — PRODUIT : ce qui est utilisé · ce qui ne l'est jamais · ce que les clients demandent.
// ADMIN-1 (AD7) — période au choix 7/30/90 j, bloc « jamais ouverts » mis en avant, et « Retours clients »
// branché sur la file SIGNALEMENTS unifiée (CONNEXIONS-2) — plus une seconde liste (l'ancienne table
// `retours` n'alimente plus l'UI). Filtres par statut ET par compte.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { getAdminProduit, getAdminSignalements, postAdminSignalementStatut, type Signalement } from '../../lib/api'
import { MODULES } from '../outils/registry'
import { ActBtn, Chip, Panel, PHead } from './AdminView'

const fmtReu = (iso?: string | null) => {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat('fr-FR', { timeZone: 'Indian/Reunion', day: '2-digit', month: '2-digit' }).format(new Date(iso))
  } catch { return '—' }
}

// libellé d'un outil capté : registre des modules d'abord, puis les vues (`vue:*`), puis la clé nue.
const VUES: Record<string, string> = {
  'vue:cartes': 'Carte / fiches', 'vue:copilote': 'Copilote', 'vue:projets': 'Projets',
  'vue:crm': 'CRM', 'vue:sources': 'Sources (page)', 'vue:admin': 'Tour de contrôle',
}
const outilLabel = (k: string) => MODULES.find((m) => m.key === k)?.label ?? VUES[k] ?? k

const PERIODES = [7, 30, 90] as const

export function ProduitSection() {
  const qc = useQueryClient()
  const [jours, setJours] = useState<7 | 30 | 90>(30)
  const q = useQuery({ queryKey: ['admin-produit', jours], queryFn: () => getAdminProduit(jours), refetchInterval: 120_000 })
  // AD7.2 — retours clients = file signalements unifiée (fiche + annonce), filtrable statut + compte.
  const sig = useQuery({ queryKey: ['admin-signalements'], queryFn: () => getAdminSignalements(), refetchInterval: 120_000 })
  const [fStatut, setFStatut] = useState<'tous' | 'nouveau' | 'traite'>('tous')
  const [fCompte, setFCompte] = useState<string>('tous')
  const statut = useMutation({
    mutationFn: ({ id, s }: { id: number; s: 'nouveau' | 'traite' }) => postAdminSignalementStatut(id, s),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-signalements'] }),
  })

  const d = q.data
  // AD7.2 — « jamais ouverts sur la période » = catalogue front (registry MODULES, hors variantes cachées)
  // MOINS les outils captés sur la période. Aucun chiffre fabriqué : seulement une différence d'ensembles.
  const jamais = useMemo(() => {
    if (!d) return [] as string[]
    const vus = new Set(d.usage.map((u) => u.outil))
    return MODULES.filter((m) => !m.hidden && !vus.has(m.key)).map((m) => m.label)
  }, [d])
  const comptes = useMemo(() => {
    const s = new Set<string>()
    for (const x of sig.data?.signalements ?? []) if (x.compte_nom) s.add(x.compte_nom)
    return Array.from(s).sort()
  }, [sig.data])

  if (!d) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>
  const max = Math.max(...d.usage.map((u) => u.n), 1)
  const signalements = (sig.data?.signalements ?? []).filter((r) =>
    (fStatut === 'tous' || r.statut === fStatut) && (fCompte === 'tous' || r.compte_nom === fCompte))
  const typeMeta = (t: Signalement['type']) => t === 'fiche'
    ? { label: 'fiche', tone: 'warn' as const } : { label: 'annonce', tone: 'off' as const }

  return (
    <>
      <Panel>
        <PHead>
          Usage par outil
          <span className="ml-auto flex gap-1.5">
            {PERIODES.map((p) => (
              <Chip key={p} tone={jours === p ? 'ok' : 'off'} onClick={() => setJours(p)}>{p} j</Chip>
            ))}
          </span>
        </PHead>
        <div className="grid gap-2.5 p-4">
          {d.usage.map((u) => (
            <div key={u.outil} className="grid grid-cols-[150px_1fr_70px] items-center gap-3 text-xs">
              <b className="truncate font-medium text-txt-mut" title={u.outil}>{outilLabel(u.outil)}</b>
              <div className="h-3.5 overflow-hidden rounded border border-line bg-bg">
                <div className="h-full rounded-sm bg-gradient-to-r from-mint-sub to-mint" style={{ width: `${Math.max(2, (u.n / max) * 100)}%` }} />
              </div>
              <span className="text-right font-mono text-xs text-txt">{u.n.toLocaleString('fr-FR')}</span>
            </div>
          ))}
          {!d.usage.length && <div className="py-4 text-center text-xs text-txt-mut">Aucune ouverture captée sur {jours} jours (capteurs posés au lot D1 — la donnée arrive avec l'usage).</div>}
        </div>
        {/* AD7 — bloc « jamais ouverts » mis en avant (ambre) : c'est lui qui dit où investir. */}
        <div className="border-t border-amber/40 bg-amber/[0.06] px-4 py-3 text-[12.5px]">
          <b className="text-amber">Jamais ouverts sur {jours} j :</b>{' '}
          {jamais.length
            ? <span className="text-txt-mut">{jamais.join(' · ')} — à montrer en démo, ou à repenser.</span>
            : <span className="text-txt-mut">aucun — tous les outils du catalogue ont été ouverts.</span>}
        </div>
        <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-xs text-txt-mut">
          Compte les <b className="text-txt">ouvertures d'outil</b> — événement léger, par licence. « Jamais ouverts » = catalogue outils (registry) moins les outils captés sur la période.
        </div>
      </Panel>

      <Panel>
        <PHead>
          Retours clients
          <span className="text-txt-dim">— table signalements, la même que le compteur Pilotage</span>
          <span className="ml-auto flex flex-wrap items-center gap-1.5">
            {(['tous', 'nouveau', 'traite'] as const).map((f) => (
              <Chip key={f} tone={fStatut === f ? 'ok' : 'off'} onClick={() => setFStatut(f)}>
                {f === 'tous' ? 'Tous' : f === 'nouveau' ? 'Nouveaux' : 'Traités'}
              </Chip>
            ))}
            <select value={fCompte} onChange={(e) => setFCompte(e.target.value)}
              className="rounded-full border border-line-2 bg-surface-2 px-2.5 py-0.5 text-[10.5px] text-txt-mut">
              <option value="tous">Compte : tous</option>
              {comptes.map((cn) => <option key={cn} value={cn}>{cn}</option>)}
            </select>
          </span>
        </PHead>
        <table className="w-full text-[13px]">
          <thead>
            <tr>
              {['Date', 'Compte', 'Type', 'Message', 'Statut'].map((h, i) => (
                <th key={h} className={`border-b border-line px-4 py-2.5 font-mono text-[9.5px] font-medium uppercase tracking-[0.12em] text-txt-dim ${i === 4 ? 'text-right' : 'text-left'}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {signalements.map((r) => {
              const tm = typeMeta(r.type)
              return (
                <tr key={r.id} className="border-b border-line last:border-b-0 hover:bg-surface-3">
                  <td className="px-4 py-2.5 font-mono text-xs text-txt-dim">{fmtReu(r.created_at)}</td>
                  <td className="px-4 py-2.5">{r.compte_nom ?? <span className="text-txt-dim">interne</span>}</td>
                  <td className="px-4 py-2.5"><Chip tone={tm.tone}>{tm.label}</Chip></td>
                  <td className="max-w-[420px] px-4 py-2.5 text-txt-mut">« {r.commentaire ?? r.type_erreur} »</td>
                  <td className="px-4 py-2.5 text-right">
                    {r.statut === 'nouveau'
                      ? <ActBtn tone="ghost" onClick={() => statut.mutate({ id: r.id, s: 'traite' })}>Traiter</ActBtn>
                      : <Chip tone="ok" onClick={() => statut.mutate({ id: r.id, s: 'nouveau' })}>Traité ✓ — rouvrir</Chip>}
                  </td>
                </tr>
              )
            })}
            {!signalements.length && <tr><td colSpan={5} className="px-4 py-6 text-center text-xs text-txt-mut">Aucun signalement {fStatut !== 'tous' || fCompte !== 'tous' ? 'pour ce filtre' : ''} — le bouton « Signaler » vit dans la fiche et sur les annonces Radar.</td></tr>}
          </tbody>
        </table>
        <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-xs text-txt-mut">
          File UNIQUE des signalements (fiche + annonce), la même que la tuile « signalements ouverts » du Pilotage.
          Un clic sur « Traité ✓ » le repasse « nouveau ».
        </div>
      </Panel>
    </>
  )
}
