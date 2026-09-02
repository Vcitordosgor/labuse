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
// S0.1 — prix « à l'une » : on tolère 3 décimales UNIQUEMENT ici (une question coûte < 1 centime),
// jamais dans le reste de la page (fini « 0,79 centime »).
const eurUne = (v?: number | null) =>
  v == null ? '—' : `${v.toLocaleString('fr-FR', { minimumFractionDigits: 3, maximumFractionDigits: 3 })} €`

// RETOURS-8 (R3) — le plafond s'édite en EUROS/jour (0,50 · 1 · 2 · 5 ou libre). Le champ affiche
// l'unité « € » ; Enregistrer est immédiat (la question suivante du compte lit le nouveau budget).
function BudgetEdit({ id, budget, defaut }: { id: number; budget: number | null; defaut: number }) {
  const qc = useQueryClient()
  const [v, setV] = useState<string>(budget == null ? '' : String(budget))
  const parse = (s: string): number | null => { const t = s.trim().replace(',', '.'); return t === '' ? null : Number(t) }
  const save = useMutation({
    mutationFn: () => postAdminLicenceQuota(id, parse(v)),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-ia'] }); qc.invalidateQueries({ queryKey: ['admin-licences'] }) },
  })
  const val = parse(v)
  const dirty = val !== budget && !(v.trim() !== '' && Number.isNaN(val))
  return (
    <span className="flex items-center justify-end gap-1.5">
      <input value={v} onChange={(e) => setV(e.target.value.replace(/[^0-9.,]/g, ''))} placeholder={defaut.toFixed(2)}
        data-quota={id}
        className="w-16 rounded-md border border-line-2 bg-bg px-2 py-1 text-right font-mono text-xs text-txt outline-none focus:border-cp-ia" />
      <span className="text-xs text-txt-dim">€</span>
      {dirty && <ActBtn tone="ia" onClick={() => save.mutate()} disabled={save.isPending}>Enregistrer</ActBtn>}
    </span>
  )
}

export function IaSection() {
  const q = useQuery({ queryKey: ['admin-ia'], queryFn: getAdminIa, refetchInterval: 120_000 })
  const d = q.data
  if (!d) return <div className="py-10 text-center text-xs text-txt-mut">Chargement…</div>
  const maxJour = Math.max(...d.jours.map((x) => x.cout), 0.0001)
  const maxLic = Math.max(...d.par_licence.map((x) => x.cout), 0.0001)
  // ADMIN-1 AD6.2 — 30 jours (appels) + coût 30 j par compte, joints depuis par_licence.
  const lic30 = new Map(d.par_licence.map((x) => [x.compte_id, x] as const))
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
          <Lbl>Coût unitaire</Lbl>
          {/* RETOURS-8 (R3) — « 0,008 € / question » seulement (plus « pour 1 000 questions »). */}
          <div className="font-display text-2xl font-semibold text-cp-ia">
            {`${eurUne(d.cout_unitaire_question_eur)} / question`}
          </div>
          <div className="mt-1 text-[11.5px] text-txt-mut">coût moyen réel (ledger ia_log, mois courant)</div>
        </div>
        <div className="rounded-xl border border-line bg-surface-2 px-4 py-4">
          <Lbl>Plafond défaut / jour</Lbl>
          {/* RETOURS-8 (R3) — le plafond par défaut est en EUROS/jour. */}
          <div className="font-display text-2xl font-semibold text-txt-hi">{eur(d.budget_defaut_eur)}</div>
          <div className="mt-1 text-[11.5px] text-txt-mut">défaut — plafond € par compte modifiable ci-dessous</div>
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

      {/* ADMIN-1 AD6.2 — « Plafond quotidien par compte » : consommé/plafond aujourd'hui · 30 j · coût 30 j ·
          plafond éditable en ligne. C'est ça, allouer. Le budget € GLOBAL se gère côté console Anthropic. */}
      <Panel className="mt-3.5">
        <PHead>
          Plafond quotidien par compte <Chip tone="ia">recherche NL + Copilote /ask + missions</Chip>
        </PHead>
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-line font-mono text-[9.5px] uppercase tracking-[0.14em] text-txt-dim">
              <th className="px-4 py-2 text-left font-normal">Compte</th>
              <th className="px-4 py-2 text-right font-normal">Aujourd'hui</th>
              <th className="px-4 py-2 text-right font-normal">≈ questions</th>
              <th className="px-4 py-2 text-right font-normal">Coût 30 j</th>
              <th className="px-4 py-2 text-right font-normal">Plafond € / jour</th>
            </tr>
          </thead>
          <tbody>
            {d.quotas.map((k) => {
              const l = lic30.get(k.id)
              return (
                <tr key={k.id} className="border-b border-line last:border-b-0 hover:bg-surface-3">
                  <td className="px-4 py-2.5">{k.nom}</td>
                  {/* RETOURS-8 (R3) — dépense du jour / budget en EUROS + nb d'appels « en petit ». */}
                  <td className="px-4 py-2.5 text-right font-mono text-xs text-txt-mut">
                    <span className={k.depense_eur >= k.budget_eur ? 'text-cp-ia' : ''}>{eurUne(k.depense_eur)}</span>
                    <span className="text-txt-dim"> / {eur(k.budget_eur)}</span>
                    <span className="ml-1 text-[10px] text-txt-dim">({k.appels_aujourdhui} appels)</span>
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-xs text-txt-mut">{k.equiv_questions == null ? '—' : `≈ ${k.equiv_questions.toLocaleString('fr-FR')}`}</td>
                  <td className="px-4 py-2.5 text-right font-mono text-xs text-txt-mut">{eur(l?.cout ?? 0)}</td>
                  <td className="w-40 px-4 py-2.5 text-right"><BudgetEdit id={k.id} budget={k.copilote_budget_eur} defaut={d.budget_defaut_eur} /></td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-xs text-txt-mut">
          Vide = défaut ({eur(d.budget_defaut_eur)}/jour). Le plafond est en <b>euros</b> : une mission lourde (Sonnet) pèse
          à son coût réel, pas comme une question. Enregistrer est immédiat : la question suivante du compte lit le nouveau plafond.
        </div>
      </Panel>

      {/* RETOURS-7 Z7 — QUEL MODÈLE SERT CHAQUE SURFACE IA. Lu depuis la config (registre unique
          ai_models.SURFACES + override env), jamais un nom en dur : ce tableau EST la vérité servie. */}
      <Panel className="mt-3.5">
        <PHead>Modèle par surface IA <Chip tone="ia">config — ai_models.SURFACES</Chip></PHead>
        <table className="w-full text-[13px]">
          <tbody>
            {d.modeles_par_surface.map((s) => (
              <tr key={s.kind} data-ia-surface={s.kind} className="border-b border-line last:border-b-0 hover:bg-surface-3">
                <td className="px-4 py-2.5 text-txt">{s.label}</td>
                <td className="px-4 py-2.5 text-right font-mono text-xs text-cp-ia">{s.model}</td>
                <td className="px-4 py-2.5 text-right font-mono text-[10.5px] text-txt-dim">{s.kind}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-xs text-txt-mut">
          Un seul point de configuration du modèle par usage (défaut au registre, override
          <span className="font-mono"> LABUSE_IA_MODELE_&lt;KIND&gt;</span>). Aucun nom de modèle codé en dur ailleurs.
        </div>
      </Panel>
    </>
  )
}
