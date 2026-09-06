/**
 * M10 lot 1.2/1.3 — Permis SUR ou À PROXIMITÉ de la parcelle, cliquables.
 *
 * La PREUVE derrière le signal « permis à proximité » du faisceau de viabilisation M-VIA :
 * lit exactement `via_permits_geo` (mêmes rayons 100/200 m que le score). Chaque permis ouvre
 * sa fiche (porteur, lots, surfaces, délai d'instruction) via le tiroir partagé du radar.
 */
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { modParcellePermis } from '../../lib/api'
import { VIOLET } from '../outils/registry'
import { PermitDrawer } from '../outils/ModulePanel'
import { GroupLabel, FactNote } from './primitives'

export function PermitsProximityBlock({ idu }: { idu: string }) {
  const [open, setOpen] = useState<string | null>(null)
  const q = useQuery({ queryKey: ['parcelle-permis', idu], queryFn: () => modParcellePermis(idu) })
  const d = q.data as Record<string, any> | undefined
  const items = (d?.['items'] ?? []) as Record<string, any>[]
  if (!d || items.length === 0) return null
  return (
    <div data-permis-proximite>
      {/* Z1·02 / Z3 — le titre encadré (card-elev) devient un KICKER avec le compte à droite ;
          plus de boîte dans la boîte. Le tableau des permis reste (mono, distances < 100 m en vert),
          la note de méthode passe en FactNote. Données identiques. */}
      <GroupLabel right={
        <span className="text-[11px] text-txt-dim">
          <b style={{ color: VIOLET }}>{d['c100']}</b> à &lt; 100 m · {d['c200']} à &lt; 200 m
        </span>
      }>Permis à proximité</GroupLabel>
      <FactNote>{d['note']} Cliquez pour la fiche.</FactNote>
      <div className="mt-2 flex flex-col gap-1">
        {items.slice(0, 12).map((i, k) => (
          <button key={k} onClick={() => setOpen(i['permit_id'] as string)}
            className="flex items-center gap-2 px-0 py-1.5 text-left text-[11px] border-b border-line/60 last:border-0">
            <span className="font-mono text-txt">{i['nature'] as string}</span>
            <span className="text-txt-mut">{i['date'] as string}</span>
            {i['nb_lgt'] != null && <span className="text-txt-dim">{String(i['nb_lgt'])} lgt</span>}
            <span className="ml-auto font-mono" style={{ color: i['distance_m'] <= 100 ? VIOLET : undefined }}>
              {String(i['distance_m'])} m
            </span>
          </button>
        ))}
      </div>
      {open && <PermitDrawer permitId={open} onClose={() => setOpen(null)} />}
    </div>
  )
}
