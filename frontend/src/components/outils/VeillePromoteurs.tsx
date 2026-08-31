// SECTEUR-1 (S3) + SECTEUR-2 (T2) — outil « Veille promoteurs » : ce que les promoteurs / bailleurs /
// SEM CONSTRUISENT (leurs OPÉRATIONS), pas leur patrimoine. Une opération = groupe de permis contigus,
// même propriétaire moral, même période (règle serveur). Chaque opération : un POINT sur la carte,
// promoteur, commune, logements, dates, état. Par promoteur : une frise par année + lien vers son Scan
// patrimoine (les deux se renvoient, ne se dupliquent pas). Chiffres = comptes SQL, millésime affiché.
import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getPromoteurFrise, getVeillePromoteurs, type OperationPromoteur } from '../../lib/api'
import { CP_COMMUNES } from '../panel/FiltreLabuse'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { iduComplet } from '../../lib/format'

const CAT_LABEL: Record<string, string> = { promoteur: 'Promoteur', bailleur: 'Bailleur social', sem: 'SEM' }

function Frise({ siren }: { siren: string }) {
  const q = useQuery({ queryKey: ['promoteur-frise', siren], queryFn: () => getPromoteurFrise(siren) })
  if (q.isLoading) return <Loading label="Frise…" className="text-[10px]" />
  const f = q.data
  if (!f) return null
  const maxLgt = Math.max(1, ...f.frise.map((a) => a.n_logements))
  return (
    <div className="mt-1.5 rounded-md border border-line-2 bg-surface-2 p-2 text-[11px]">
      <p className="text-txt-mut"><b className="text-txt">{f.n_operations}</b> opération{f.n_operations > 1 ? 's' : ''} · <b className="text-txt">{f.n_logements.toLocaleString('fr-FR')}</b> logements construits</p>
      {/* frise par année (opérations, logements) */}
      <div className="mt-1.5 flex flex-col gap-1">
        {f.frise.map((a) => (
          <div key={a.annee} className="flex items-center gap-2">
            <span className="w-9 shrink-0 tabular-nums text-txt-dim">{a.annee}</span>
            <span className="h-2.5 rounded-sm bg-mint/60" style={{ width: `${Math.round(100 * a.n_logements / maxLgt)}%`, minWidth: a.n_logements ? 6 : 0 }} />
            <span className="shrink-0 whitespace-nowrap text-[10px] text-txt-mut">{a.n_operations} op · {a.n_logements} lgt</span>
          </div>
        ))}
      </div>
      {/* renvoi vers Scan patrimoine (pas de duplication) */}
      <p className="mt-1.5 text-[10px] text-txt-dim">Patrimoine foncier détenu : <b className="text-txt-mut">{f.scan_patrimoine.n_parcelles.toLocaleString('fr-FR')}</b> parcelles (Scan patrimoine, même SIREN). {f.note}</p>
    </div>
  )
}

export function VeillePromoteurs() {
  const select = useApp((s) => s.select)
  const setModuleMap = useApp((s) => s.setModuleMap)
  const [commune, setCommune] = useState('')
  const [categorie, setCategorie] = useState('')
  const [depuis, setDepuis] = useState('')
  const [openSiren, setOpenSiren] = useState<string | null>(null)
  const q = useQuery({ queryKey: ['veille-promoteurs', commune, categorie, depuis], queryFn: () => getVeillePromoteurs({ commune: commune || undefined, categorie: categorie || undefined, depuis: depuis || undefined, limit: 200 }) })
  const d = q.data
  const sel = 'h-8 rounded-md border border-line-2 bg-surface-1 px-2 text-[11.5px] text-txt'

  // SECTEUR-2 (T2) — pousse les OPÉRATIONS localisées sur la carte (kind='operation', ambre / menthe si
  // citée par une annonce Radar). Nettoie au démontage (jamais un pin fantôme d'un autre outil).
  const extra = useMemo(() => ({
    type: 'FeatureCollection' as const,
    features: (d?.operations ?? []).filter((o) => o.lon != null && o.lat != null).map((o) => ({
      type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [o.lon, o.lat] },
      properties: { kind: 'operation', siren: o.siren, idu: o.idus[0] ?? null, radar_cite: o.radar_cite,
                    nb_logements: o.nb_logements },
    })),
  }), [d])
  useEffect(() => { setModuleMap({ idus: [], extra }); return () => setModuleMap({ idus: [], extra: null }) }, [extra, setModuleMap])

  return (
    <div data-veille-promoteurs className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto p-1 text-[12.5px]">
      <div>
        <h2 className="font-display text-base font-bold text-txt-hi">Veille promoteurs</h2>
        <p className="mt-0.5 text-[11.5px] text-txt-mut">Ce que les promoteurs, bailleurs sociaux et SEM CONSTRUISENT : leurs opérations (groupes de permis d'un même propriétaire moral, sur des parcelles contiguës et une même période).{d?.millesime ? ` Données Sitadel au ${new Date(d.millesime).toLocaleDateString('fr-FR')}.` : ''}</p>
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
        <input data-vp-depuis type="date" value={depuis} onChange={(e) => setDepuis(e.target.value)} className={sel} title="Déposées depuis…" />
      </div>

      {q.isLoading && <Loading label="Regroupement des opérations…" className="mx-auto mt-4 text-xs" />}
      {d && (
        <>
          <p className="text-[11px] text-txt-dim"><b className="text-txt-mut">{d.n_total.toLocaleString('fr-FR')}</b> opérations · <b className="text-txt-mut">{d.n_logements_total.toLocaleString('fr-FR')}</b> logements · {d.n_servi} affichées{d.tronquee ? ` (plafond ${d.plafond})` : ''}</p>
          <p className="text-[10px] leading-snug text-txt-dim">{d.regle.phrase}.</p>
          <div className="flex flex-col gap-1.5">
            {d.operations.length === 0 && <p className="text-[11.5px] text-txt-dim">Aucune opération pour ce filtre.</p>}
            {d.operations.map((o: OperationPromoteur, i) => (
              <div key={i} data-vp-operation className="rounded-lg border border-line-2 bg-surface-2 p-2.5">
                <div className="flex items-start gap-2">
                  <span className="flex-1 min-w-0">
                    <b className="block truncate text-[12.5px] text-txt-hi">{o.denomination ?? '(propriétaire non nommé)'}</b>
                    <span className="text-[11px] text-txt-mut">{CAT_LABEL[o.categorie] ?? o.categorie}{o.siren ? ` · SIREN ${o.siren}` : ''}</span>
                  </span>
                  <span className="shrink-0 text-right text-[11px] text-txt-mut">
                    <b className="text-txt">{o.nb_logements}</b> logement{o.nb_logements > 1 ? 's' : ''}
                    <span className="block text-[10px] text-txt-dim">{o.n_permis} permis{o.date_max ? ` · ${new Date(o.date_max).getFullYear()}` : ''}{o.etat ? ` · ${o.etat}` : ''}</span>
                  </span>
                </div>
                {/* libellé factuel de l'opération ; « nom » = citée par une annonce neuve du Radar */}
                <div className="mt-1 flex flex-wrap items-center gap-2 text-[10.5px]">
                  <span className="text-txt">{o.libelle}</span>
                  {o.radar_cite && <span data-vp-radar-cite className="rounded bg-mint/12 px-1.5 py-px text-[9.5px] font-medium text-mint">annonce neuve Radar rattachée</span>}
                </div>
                <div className="mt-1.5 flex items-center gap-2 text-[10.5px]">
                  <span className="text-txt-dim">{o.commune}{o.date_min && o.date_max && o.date_min !== o.date_max ? ` · ${new Date(o.date_min).toLocaleDateString('fr-FR')} → ${new Date(o.date_max).toLocaleDateString('fr-FR')}` : ''}</span>
                  {o.idus[0] && <button data-vp-parcelle onClick={() => select(iduComplet(o.idus[0]))} className="font-mono text-mint hover:underline" title="Ouvrir la fiche parcelle">{o.idus[0]} →</button>}
                  {o.siren && <button data-vp-frise onClick={() => setOpenSiren((s) => (s === o.siren ? null : o.siren))} className="ml-auto text-mint hover:underline">{openSiren === o.siren ? 'masquer' : 'sa frise ▾'}</button>}
                </div>
                {openSiren === o.siren && o.siren && <Frise siren={o.siren} />}
              </div>
            ))}
          </div>
          <p className="text-[10px] leading-snug text-txt-dim">{d.note}</p>
        </>
      )}
    </div>
  )
}
