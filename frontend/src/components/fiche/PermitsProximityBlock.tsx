/**
 * M10 lot 1.2/1.3 — Permis SUR ou À PROXIMITÉ de la parcelle, cliquables.
 *
 * La PREUVE derrière le signal « permis à proximité » du faisceau de viabilisation M-VIA :
 * lit exactement `via_permits_geo` (mêmes rayons 100/200 m que le score). Chaque permis ouvre
 * sa fiche (porteur, lots, surfaces, délai d'instruction) via le tiroir partagé du radar.
 */
import { actesParParcelle } from '../../lib/permisAffichage'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { modParcellePermis } from '../../lib/api'
import type { ReferencePermis } from '../../lib/types'
import { VIOLET } from '../outils/registry'
import { PermitDrawer } from '../outils/ModulePanel'
import { GroupLabel, FactNote } from './primitives'
import { fmtDateNum } from '../../lib/format'

export function PermitsProximityBlock({ idu }: { idu: string }) {
  const [open, setOpen] = useState<ReferencePermis | null>(null)
  // FICHE-FIX-5 (Lot I) — permis repliés après 5 (« + N »).
  const [tous, setTous] = useState(false)
  const q = useQuery({ queryKey: ['parcelle-permis', idu], queryFn: () => modParcellePermis(idu) })
  const d = q.data as Record<string, any> | undefined
  const { directs, voisins, tous: items } = actesParParcelle(d)
  if (!d || items.length === 0) return null
  const visibles = tous ? items : items.slice(0, 5)
  return (
    <div data-permis-proximite>
      {/* Z1·02 / Z3 — le titre encadré (card-elev) devient un KICKER avec le compte à droite ;
          plus de boîte dans la boîte. Le tableau des permis reste (mono, distances < 100 m en vert),
          la note de méthode passe en FactNote. Données identiques. */}
      <GroupLabel right={
        <span className="text-[11px] text-txt-dim">
          <b style={{ color: VIOLET }}>{directs.length}</b> sur la parcelle · {voisins.length} dans le voisinage
        </span>
      }>Permis sur la parcelle et à proximité</GroupLabel>
      <FactNote>Références cadastrales Sitadel, puis autres actes géolocalisés à 200 m ou moins.</FactNote>
      <div className="mt-2 flex flex-col gap-1">
        {visibles.map((i) => (
          <button key={`${i.nature}-${i.permit_id}`} onClick={() => setOpen({ id: i.permit_id, nature: i.nature })}
            className="flex items-center gap-2 px-0 py-1.5 text-left text-[11px] border-b border-line/60 last:border-0">
            <span className="font-mono text-txt">{i['nature'] as string}</span>
            <span className="text-txt-mut">{fmtDateNum(i['date'] as string)}</span>
            {i['nb_lgt'] != null && <span className="text-txt-dim">{String(i['nb_lgt'])} lgt</span>}
            <span className="ml-auto font-mono" style={{ color: i['distance_m'] <= 100 ? VIOLET : undefined }}>
              {i.sur_parcelle ? 'Sur la parcelle' : `${i.distance_m} m`}
            </span>
          </button>
        ))}
        {!tous && items.length > 5 && (
          <button type="button" onClick={() => setTous(true)}
            className="mt-0.5 self-start text-[11px] text-mint hover:underline">
            ◀ + {items.length - 5} autres permis
          </button>
        )}
      </div>
      {open && <PermitDrawer permitId={open.id} nature={open.nature} onClose={() => setOpen(null)} />}
    </div>
  )
}
