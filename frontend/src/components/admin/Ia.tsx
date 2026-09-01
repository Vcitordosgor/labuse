// DASHBOARD-V1 · D5 — SECTION IA (mauve strictement réservé ici, comme dans l'app · M117).
// Conso lue du ledger ia_log (D1), quota/jour/licence ÉDITABLE (le /ask le lit), projection
// au rythme des 7 derniers jours, « Recharger le crédit ↗ » = console Anthropic (externe).
// Note honnête : le solde Anthropic n'est pas exposé par l'API — conso trackée localement.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { getAdminIa, postAdminLicenceQuota } from '../../lib/api'
import { ActBtn, Chip, Lbl, Panel, PHead } from './AdminView'

const eur = (v?: number | null, dec = 2) =>
  v == null ? '—' : `${v.toLocaleString('fr-FR', { minimumFractionDigits: dec, maximumFractionDigits: dec })} €`

function QuotaEdit({ id, quota, defaut }: { id: number; quota: number | null; defaut: number }) {
  const qc = useQueryClient()
  const [v, setV] = useState<string>(quota == null ? '' : String(quota))
  const save = useMutation({
    mutationFn: () => postAdminLicenceQuota(id, v.trim() === '' ? null : Number(v)),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-ia'] }); qc.invalidateQueries({ queryKey: ['admin-licences'] }) },
  })
  const dirty = (v.trim() === '' ? null : Number(v)) !== quota
  return (
    <span className="flex items-center gap-1.5">
      <input value={v} onChange={(e) => setV(e.target.value.replace(/[^0-9]/g, ''))} placeholder={String(defaut)}
        data-quota={id}
        className="w-16 rounded-md border border-line-2 bg-bg px-2 py-1 text-right font-mono text-xs text-txt outline-none focus:border-cp-ia" />
      {dirty && <ActBtn tone="ia" onClick={() => save.mutate()} disabled={save.isPending}>OK</ActBtn>}
    </span>
  )
}

export function IaSection() {
  const q = useQuery({ queryKey: ['admin-ia'], queryFn: getAdminIa, refetchInterval: 120_000 })
  const d = q.data
  if (!d) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>
  const maxJour = Math.max(...d.jours.map((x) => x.cout), 0.0001)
  const maxLic = Math.max(...d.par_licence.map((x) => x.cout), 0.0001)
  return (
    <>
      <div className="mb-3.5 flex justify-end">
        <a href="https://console.anthropic.com/settings/billing" target="_blank" rel="noreferrer"
          className="rounded-lg border border-cp-ia-border bg-cp-ia-bg/50 px-3 py-1.5 text-xs font-medium text-cp-ia hover:brightness-125">
          Recharger le crédit ↗
        </a>
      </div>
      <div className="grid grid-cols-4 gap-3.5 max-[1100px]:grid-cols-2">
        <div className="rounded-xl border border-line bg-surface-2 px-4 py-4">
          <Lbl>Conso du mois</Lbl>
          <div className="font-display text-2xl font-semibold text-cp-ia">{eur(d.mois.cout_eur)}</div>
          <div className="mt-1 text-[11.5px] text-txt-mut">≈ {d.mois.appels.toLocaleString('fr-FR')} appels servis</div>
        </div>
        <div className="rounded-xl border border-line bg-surface-2 px-4 py-4">
          <Lbl>Coût moyen / question</Lbl>
          <div className="font-display text-2xl font-semibold text-cp-ia">
            {d.mois.cout_moyen_question == null ? '—' : `${(d.mois.cout_moyen_question * 100).toLocaleString('fr-FR', { maximumFractionDigits: 2 })} ct`}
          </div>
          <div className="mt-1 text-[11.5px] text-txt-mut">ledger ia_log, mois courant</div>
        </div>
        <div className="rounded-xl border border-line bg-surface-2 px-4 py-4">
          <Lbl>Quota / jour / licence</Lbl>
          <div className="font-display text-2xl font-semibold text-txt-hi">{d.quota_defaut}</div>
          <div className="mt-1 text-[11.5px] text-txt-mut">défaut — modifiable par licence ci-dessous</div>
        </div>
        <div className="rounded-xl border border-line bg-surface-2 px-4 py-4">
          <Lbl>Projection fin de mois</Lbl>
          <div className="font-display text-2xl font-semibold text-cp-ia">≈ {eur(d.projection_fin_mois_eur, 0)}</div>
          <div className="mt-1 text-[11.5px] text-txt-mut">au rythme des 7 derniers jours</div>
        </div>
      </div>

      <div className="mt-3.5 grid grid-cols-2 gap-3.5 max-[1100px]:grid-cols-1">
        <Panel className="mb-0">
          <PHead>Conso journalière · 30 jours</PHead>
          <div className="p-4">
            <div className="flex h-16 items-end gap-[3px]" aria-hidden="true">
              {d.jours.map((x) => (
                <i key={x.jour} title={`${x.jour} · ${eur(x.cout)} · ${x.appels} appels`}
                  className="min-w-[4px] flex-1 rounded-t-sm bg-gradient-to-b from-cp-ia to-cp-ia-border opacity-85"
                  style={{ height: `${Math.max(4, (x.cout / maxJour) * 100)}%` }} />
              ))}
            </div>
            <div className="mt-1.5 flex justify-between font-mono text-[9.5px] text-txt-dim">
              <span>{d.jours[0]?.jour.slice(5) ?? ''}</span><span>{d.jours.at(-1)?.jour.slice(5) ?? ''}</span>
            </div>
          </div>
          <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-xs text-txt-mut">
            Un pic isolé = un usage anormal à regarder. La conso suit le nombre de licences.
          </div>
        </Panel>
        <Panel className="mb-0">
          <PHead>Par licence · 30 jours</PHead>
          <div className="grid gap-2.5 p-4">
            {d.par_licence.map((x) => (
              <div key={x.compte_id ?? 'admin'} className="grid grid-cols-[150px_1fr_70px] items-center gap-3 text-xs">
                <b className="truncate font-medium text-txt-mut">{x.nom}</b>
                <div className="h-3.5 overflow-hidden rounded border border-line bg-bg">
                  <div className="h-full rounded-sm bg-gradient-to-r from-cp-ia-border to-cp-ia" style={{ width: `${Math.max(2, (x.cout / maxLic) * 100)}%` }} />
                </div>
                <span className="text-right font-mono text-xs text-txt">{eur(x.cout)}</span>
              </div>
            ))}
            {!d.par_licence.length && <div className="py-4 text-center text-xs text-txt-mut">Aucun appel IA sur 30 jours.</div>}
          </div>
          <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-xs text-txt-mut">
            Repère un client qui surconsomme (candidat à un forfait supérieur) — ou un usage anormal. {d.note}
          </div>
        </Panel>
      </div>

      <Panel className="mt-3.5">
        <PHead>Quota Copilote / jour — par licence <Chip tone="ia">recherche NL + Copilote /ask</Chip></PHead>
        <table className="w-full text-[13px]">
          <tbody>
            {d.quotas.map((k) => (
              <tr key={k.id} className="border-b border-line last:border-b-0 hover:bg-surface-3">
                <td className="px-4 py-2.5">{k.nom}</td>
                {/* CONNEXIONS-2 Lot 2 — consommé aujourd'hui / plafond effectif (compteur Copilote unique) */}
                <td className="px-4 py-2.5 text-right font-mono text-xs text-txt-mut">
                  <span className={k.consomme_aujourdhui >= k.plafond_effectif ? 'text-cp-ia' : ''}>{k.consomme_aujourdhui}</span>
                  <span className="text-txt-dim"> / {k.plafond_effectif} aujourd'hui</span>
                </td>
                <td className="px-4 py-2.5 text-right text-txt-mut">
                  {k.copilote_quota_jour == null ? `défaut (${d.quota_defaut}/j)` : `${k.copilote_quota_jour}/j`}
                </td>
                <td className="w-32 px-4 py-2.5"><QuotaEdit id={k.id} quota={k.copilote_quota_jour} defaut={d.quota_defaut} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-xs text-txt-mut">
          Vide = défaut ({d.quota_defaut}/jour). Un seul compteur pour la recherche NL et le Copilote : la modification prend effet à la prochaine question du client.
        </div>
      </Panel>
    </>
  )
}
