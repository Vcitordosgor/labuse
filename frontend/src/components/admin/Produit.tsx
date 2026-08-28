// DASHBOARD-V1 · D7 — PRODUIT : ce qui est utilisé (usage par outil 30 j, capteurs D1) ·
// ce que les clients demandent (retours du bouton « Signaler », statuts éditables).
// « Par client » = V2 (mandat) — le chip est là, grisé, honnête.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { getAdminProduit, postAdminRetourStatut } from '../../lib/api'
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

const TYPE_META: Record<string, { label: string; tone: 'ok' | 'warn' | 'ia' }> = {
  bug: { label: 'Bug', tone: 'warn' }, idee: { label: 'Idée', tone: 'ok' }, question: { label: 'Question', tone: 'ia' },
}

export function ProduitSection() {
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['admin-produit'], queryFn: getAdminProduit, refetchInterval: 120_000 })
  const [filtre, setFiltre] = useState<'tous' | 'bug' | 'idee' | 'question'>('tous')
  const statut = useMutation({
    mutationFn: ({ id, s }: { id: number; s: 'nouveau' | 'traite' | 'repondu' }) => postAdminRetourStatut(id, s),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-produit'] }),
  })
  const d = q.data
  if (!d) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>
  const max = Math.max(...d.usage.map((u) => u.n), 1)
  const retours = d.retours.filter((r) => filtre === 'tous' || r.type === filtre)
  return (
    <>
      <Panel>
        <PHead>
          Usage par outil · 30 jours
          <span className="ml-auto flex gap-1.5">
            <Chip tone="ok">Total</Chip>
            <Chip onClick={undefined}>Par client — V2</Chip>
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
          {!d.usage.length && <div className="py-4 text-center text-xs text-txt-mut">Aucune ouverture captée sur 30 jours (capteurs posés au lot D1 — la donnée arrive avec l'usage).</div>}
        </div>
        <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-xs text-txt-mut">
          Compte les <b className="text-txt">ouvertures d'outil</b> — événement léger, par licence. Dit où investir, et quel outil personne n'ouvre.
        </div>
      </Panel>

      <Panel>
        <PHead>
          Retours clients
          <span className="ml-auto flex gap-1.5">
            {(['tous', 'bug', 'idee', 'question'] as const).map((f) => (
              <Chip key={f} tone={filtre === f ? 'ok' : 'off'} onClick={() => setFiltre(f)}>
                {f === 'tous' ? 'Tous' : `${TYPE_META[f].label}s`}
              </Chip>
            ))}
          </span>
        </PHead>
        <table className="w-full text-[13px]">
          <thead>
            <tr>
              {['Date', 'Client', 'Type', 'Message', 'Statut'].map((h, i) => (
                <th key={h} className={`border-b border-line px-4 py-2.5 font-mono text-[9.5px] font-medium uppercase tracking-[0.12em] text-txt-dim ${i === 4 ? 'text-right' : 'text-left'}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {retours.map((r) => (
              <tr key={r.id} className="border-b border-line last:border-b-0 hover:bg-surface-3">
                <td className="px-4 py-2.5 font-mono text-xs text-txt-dim">{fmtReu(r.ts)}</td>
                <td className="px-4 py-2.5">{r.compte ?? <span className="text-txt-dim">interne</span>}</td>
                <td className="px-4 py-2.5"><Chip tone={TYPE_META[r.type]?.tone ?? 'off'}>{TYPE_META[r.type]?.label ?? r.type}</Chip></td>
                <td className="max-w-[420px] px-4 py-2.5 text-txt-mut">« {r.message} »</td>
                <td className="px-4 py-2.5 text-right">
                  {r.statut === 'nouveau' ? (
                    <span className="inline-flex gap-1.5">
                      <ActBtn tone="ghost" onClick={() => statut.mutate({ id: r.id, s: 'traite' })}>Marquer traité</ActBtn>
                      <ActBtn tone="ghost" onClick={() => statut.mutate({ id: r.id, s: 'repondu' })}>Répondu</ActBtn>
                    </span>
                  ) : (
                    <Chip tone="ok" onClick={() => statut.mutate({ id: r.id, s: 'nouveau' })}>
                      {r.statut === 'traite' ? 'Traité ✓' : 'Répondu ✓'}
                    </Chip>
                  )}
                </td>
              </tr>
            ))}
            {!retours.length && <tr><td colSpan={5} className="px-4 py-6 text-center text-xs text-txt-mut">Aucun retour {filtre !== 'tous' ? 'de ce type' : ''} — le bouton « Signaler » vit en haut à droite de l'app cliente.</td></tr>}
          </tbody>
        </table>
        <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-xs text-txt-mut">
          Chaque retour : qui, quand, quoi, statut. La boîte à idées produit — et la détection de bugs par les clients.
          Un clic sur un statut ✓ le repasse « nouveau ».
        </div>
      </Panel>
    </>
  )
}
