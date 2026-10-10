// DASHBOARD-V1 · D5 — SECTION IA (mauve strictement réservé ici, comme dans l'app · M117).
// Conso lue du ledger ia_log (D1), quota/jour/licence ÉDITABLE (le /ask le lit), projection
// au rythme des 7 derniers jours, « Recharger le crédit ↗ » = console Anthropic (externe).
// Note honnête : le solde Anthropic n'est pas exposé par l'API — conso trackée localement.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { getAdminIa, postAdminLicenceQuota, type AdminIa, type IaBloc } from '../../lib/api'
import { ActBtn, Chip, Lbl, Panel, PHead } from './AdminView'
import { Chevron } from '../ui/Chevron'
import { Chargement } from '../Loading'

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

// CORRECTIFS-1 B2 — un bloc de coûts (interne OU clients) : mois · projection · coût moyen, jamais mélangés.
function BlocCard({ titre, sous, b, moisNom }: { titre: string; sous: string; b: IaBloc; moisNom: string }) {
  return (
    <div className="rounded-xl border border-line bg-surface-2 px-4 py-4">
      <div className="flex items-baseline justify-between gap-2">
        <Lbl>{titre}</Lbl>
        <span className="text-[11px] text-txt-dim">{b.appels.toLocaleString('fr-FR')} appels</span>
      </div>
      <div className="mt-2 grid grid-cols-3 gap-3">
        <div><div className="font-display text-xl font-semibold text-cp-ia">{eur(b.cout_eur)}</div><div className="mt-0.5 text-[10.5px] text-txt-mut">{moisNom}</div></div>
        <div><div className="font-display text-xl font-semibold text-cp-ia">≈ {eur(b.projection_fin_mois_eur, 0)}</div><div className="mt-0.5 text-[10.5px] text-txt-mut">projection</div></div>
        <div><div className="font-display text-xl font-semibold text-cp-ia">{eurUne(b.cout_moyen_eur)}</div><div className="mt-0.5 text-[10.5px] text-txt-mut">coût moyen</div></div>
      </div>
      <div className="mt-1.5 text-[11px] text-txt-dim">{sous}</div>
    </div>
  )
}

export function IaSection() {
  const q = useQuery({ queryKey: ['admin-ia'], queryFn: getAdminIa, refetchInterval: 120_000 })
  // DASHBOARD-2 (Lot 6) — filtre de la table plafond : clients / avec conso / tous (tests compris).
  const [fPlafond, setFPlafond] = useState<'clients' | 'conso' | 'tous'>('clients')
  // DASHBOARD-2 (Lot 6) — la liste « modèle par surface » est REPLIÉE par défaut (résumé + voir la liste).
  const [voirModeles, setVoirModeles] = useState(false)
  const d = q.data
  if (!d) return <div className="py-10 text-center"><Chargement variant="bloc" /></div>
  const maxLic = Math.max(...d.par_licence.map((x) => x.cout), 0.0001)
  // ADMIN-1 AD6.2 — 30 jours (appels) + coût 30 j par compte, joints depuis par_licence.
  const lic30 = new Map(d.par_licence.map((x) => [x.compte_id, x] as const))
  // DASHBOARD-2 (Lot 6) — fenêtres NOMMÉES : le mois courant en toutes lettres, « 30 j » partout.
  const moisNom = new Intl.DateTimeFormat('fr-FR', { month: 'long' }).format(new Date())
  // filtres de la table plafond (compteurs + liste filtrée).
  const estClient = (k: AdminIa['quotas'][number]) => k.plan !== 'interne'
  const aConso = (k: AdminIa['quotas'][number]) => ((lic30.get(k.id)?.cout ?? 0) > 0) || k.depense_eur > 0
  const cptClients = d.quotas.filter(estClient).length
  const cptConso = d.quotas.filter(aConso).length
  const quotasVus = fPlafond === 'clients' ? d.quotas.filter(estClient)
    : fPlafond === 'conso' ? d.quotas.filter(aConso) : d.quotas
  return (
    <>
      {/* CORRECTIFS-1 B2 — DEUX blocs DISJOINTS (jamais un total mélangé) : mois · projection · coût moyen par bloc. */}
      <div className="grid grid-cols-2 gap-3 max-[1100px]:grid-cols-1">
        <BlocCard titre="IA interne" sous="Agents de vérification des sources + ce que lance le dashboard." b={d.blocs.interne} moisNom={moisNom} />
        <BlocCard titre="IA clients" sous="Recherche NL + Copilote /ask + missions." b={d.blocs.clients} moisNom={moisNom} />
      </div>
      <div className="mt-3 rounded-xl border border-line bg-surface-2 px-4 py-4">
        <Lbl>Plafond défaut / jour</Lbl>
        <div className="font-display text-2xl font-semibold text-txt-hi">{eur(d.budget_defaut_eur)}</div>
        <div className="mt-1 text-[11.5px] text-txt-mut">par compte, modifiable ci-dessous</div>
      </div>

      <Panel className="mt-3.5">
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
            Repère un client qui surconsomme (candidat à un forfait supérieur) — ou un usage anormal.
          </div>
        </Panel>

      {/* ADMIN-1 AD6.2 — « Plafond quotidien par compte » : consommé/plafond aujourd'hui · 30 j · coût 30 j ·
          plafond éditable en ligne. C'est ça, allouer. Le budget € GLOBAL se gère côté console Anthropic. */}
      <Panel className="mt-3.5">
        <PHead>
          Plafond quotidien par compte <Chip tone="ia">recherche NL + Copilote /ask + missions</Chip>
          <span className="ml-auto flex flex-wrap items-center gap-1.5">
            <Chip tone={fPlafond === 'clients' ? 'ia' : 'off'} onClick={() => setFPlafond('clients')}>Clients {cptClients}</Chip>
            <Chip tone={fPlafond === 'conso' ? 'ia' : 'off'} onClick={() => setFPlafond('conso')}>Avec conso {cptConso}</Chip>
            <Chip tone={fPlafond === 'tous' ? 'ia' : 'off'} onClick={() => setFPlafond('tous')}>Tous, tests compris {d.quotas.length}</Chip>
          </span>
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
            {quotasVus.map((k) => {
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
          ai_models.SURFACES + override env), jamais un nom en dur : ce tableau EST la vérité servie.
          DASHBOARD-2 (Lot 6) — REPLIÉ par défaut : un résumé (N surfaces · modèle ×count) + voir la liste. */}
      <Panel className="mt-3.5">
        <PHead>Modèle par surface IA <Chip tone="ia">config — ai_models.py</Chip></PHead>
        <div className="flex items-center justify-between gap-3 px-4 py-3 text-[12.5px]">
          <div className="text-txt-mut">
            {d.modeles_par_surface.length} surface{d.modeles_par_surface.length > 1 ? 's' : ''}
            {Object.entries(d.modeles_par_surface.reduce<Record<string, number>>((acc, s) => { acc[s.model] = (acc[s.model] ?? 0) + 1; return acc }, {}))
              .sort((a, b) => b[1] - a[1])
              .map(([m, n]) => <span key={m}> · <span className="font-mono text-cp-ia">{m}</span> ×{n}</span>)}
            {' '}· source unique <span className="font-mono">ai_models.py</span>
          </div>
          <button onClick={() => setVoirModeles((v) => !v)} className="inline-flex items-center gap-1 whitespace-nowrap text-[12.5px] text-cp-ia hover:underline">
            <Chevron open={voirModeles} />{voirModeles ? 'replier' : 'voir la liste'}
          </button>
        </div>
        {voirModeles && (
          <table className="w-full border-t border-line text-[13px]">
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
        )}
        <div className="border-t border-line bg-surface-1 px-4 py-2.5 text-xs text-txt-mut">
          Un seul point de configuration du modèle par usage (défaut au registre, override
          <span className="font-mono"> LABUSE_IA_MODELE_&lt;KIND&gt;</span>). Aucun nom de modèle codé en dur ailleurs.
        </div>
      </Panel>
    </>
  )
}
