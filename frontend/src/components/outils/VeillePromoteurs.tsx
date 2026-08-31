// SECTEUR-1 (S3) — outil « Veille promoteurs » : les permis déposés par promoteurs / bailleurs / SEM
// (le demandeur = propriétaire foncier PM, même SIREN que Scan patrimoine), filtrables, avec pour
// chaque promoteur ses acquisitions foncières récentes. Chiffres = comptes SQL (millésime affiché).
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getPromoteurAcquisitions, getVeillePromoteurs } from '../../lib/api'
import { CP_COMMUNES } from '../panel/FiltreLabuse'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { iduComplet } from '../../lib/format'

const CAT_LABEL: Record<string, string> = { promoteur: 'Promoteur', bailleur: 'Bailleur social', sem: 'SEM' }

function Acquisitions({ siren }: { siren: string }) {
  const q = useQuery({ queryKey: ['promoteur-acq', siren], queryFn: () => getPromoteurAcquisitions(siren) })
  if (q.isLoading) return <Loading label="Acquisitions…" className="text-[10px]" />
  const a = q.data
  if (!a) return null
  return (
    <div className="mt-1.5 rounded-md border border-line-2 bg-surface-2 p-2 text-[11px]">
      <p className="text-txt-mut"><b className="text-txt">{a.n_parcelles.toLocaleString('fr-FR')}</b> parcelles détenues (Scan patrimoine · SIREN {siren})</p>
      <div className="mt-1 flex flex-wrap gap-1.5">
        {a.par_commune.slice(0, 8).map((c) => (
          <span key={c.commune} className="rounded border border-line-2 px-1.5 py-px text-[10.5px] text-txt-mut">{c.commune} · {c.n}</span>
        ))}
      </div>
      <p className="mt-1 text-[10px] leading-snug text-txt-dim">{a.note}</p>
    </div>
  )
}

export function VeillePromoteurs() {
  const select = useApp((s) => s.select)
  const [commune, setCommune] = useState('')
  const [categorie, setCategorie] = useState('')
  const [depuis, setDepuis] = useState('')
  const [openSiren, setOpenSiren] = useState<string | null>(null)
  const q = useQuery({ queryKey: ['veille-promoteurs', commune, categorie, depuis], queryFn: () => getVeillePromoteurs({ commune: commune || undefined, categorie: categorie || undefined, depuis: depuis || undefined, limit: 100 }) })
  const d = q.data
  const sel = 'h-8 rounded-md border border-line-2 bg-surface-1 px-2 text-[11.5px] text-txt'

  return (
    <div data-veille-promoteurs className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-1 text-[12.5px]">
      <div>
        <h2 className="font-display text-base font-bold text-txt-hi">Veille promoteurs</h2>
        <p className="mt-0.5 text-[11.5px] text-txt-mut">Les permis déposés par des promoteurs, bailleurs sociaux et SEM (demandeur = propriétaire foncier PM, même SIREN que Scan patrimoine).{d?.millesime ? ` Données Sitadel au ${new Date(d.millesime).toLocaleDateString('fr-FR')}.` : ''}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        <select data-vp-commune value={commune} onChange={(e) => setCommune(e.target.value)} className={sel}>
          <option value="">Toutes les communes</option>
          {CP_COMMUNES.map(([, n]) => <option key={n} value={n}>{n}</option>)}
        </select>
        <select data-vp-categorie value={categorie} onChange={(e) => setCategorie(e.target.value)} className={sel}>
          <option value="">Toutes catégories</option>
          {(d?.categories ?? []).map((c) => <option key={c.cle} value={c.cle}>{c.label}</option>)}
        </select>
        <input data-vp-depuis type="date" value={depuis} onChange={(e) => setDepuis(e.target.value)} className={sel} title="Déposés depuis…" />
      </div>

      {q.isLoading && <Loading label="Chargement des permis…" className="mx-auto mt-4 text-xs" />}
      {d && (
        <>
          <p className="text-[11px] text-txt-dim"><b className="text-txt-mut">{d.n_total.toLocaleString('fr-FR')}</b> permis · {d.n_servi} affichés{d.tronquee ? ` (plafond ${d.plafond})` : ''}</p>
          <div className="flex flex-col gap-1.5">
            {d.permis.length === 0 && <p className="text-[11.5px] text-txt-dim">Aucun permis pour ce filtre.</p>}
            {d.permis.map((p, i) => (
              <div key={i} data-vp-permis className="rounded-lg border border-line-2 bg-surface-2 p-2.5">
                <div className="flex items-start gap-2">
                  <span className="flex-1 min-w-0">
                    <b className="block truncate text-[12.5px] text-txt-hi">{p.denomination ?? '(propriétaire non nommé)'}</b>
                    <span className="text-[11px] text-txt-mut">{CAT_LABEL[p.categorie] ?? p.categorie}{p.siren ? ` · SIREN ${p.siren}` : ''}</span>
                  </span>
                  <span className="shrink-0 text-right text-[11px] text-txt-mut">
                    <b className="text-txt">{p.nb_lgt ?? '—'}</b> logement{(p.nb_lgt ?? 0) > 1 ? 's' : ''}
                    <span className="block text-[10px] text-txt-dim">{p.date_depot ? new Date(p.date_depot).toLocaleDateString('fr-FR') : ''}{p.etat ? ` · ${p.etat}` : ''}</span>
                  </span>
                </div>
                <div className="mt-1.5 flex items-center gap-2 text-[10.5px]">
                  <span className="text-txt-dim">{p.commune}</span>
                  <button data-vp-parcelle onClick={() => select(iduComplet(p.idu))} className="font-mono text-mint hover:underline" title="Ouvrir la fiche parcelle">{p.idu} →</button>
                  {p.siren && <button data-vp-acquisitions onClick={() => setOpenSiren((s) => (s === p.siren ? null : p.siren))} className="ml-auto text-mint hover:underline">{openSiren === p.siren ? 'masquer' : 'ses acquisitions ▾'}</button>}
                </div>
                {openSiren === p.siren && p.siren && <Acquisitions siren={p.siren} />}
              </div>
            ))}
          </div>
          <p className="text-[10px] leading-snug text-txt-dim">{d.note}</p>
        </>
      )}
    </div>
  )
}
