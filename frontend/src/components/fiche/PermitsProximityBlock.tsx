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

export function PermitsProximityBlock({ idu }: { idu: string }) {
  const [open, setOpen] = useState<string | null>(null)
  const q = useQuery({ queryKey: ['parcelle-permis', idu], queryFn: () => modParcellePermis(idu) })
  const d = q.data as Record<string, any> | undefined
  const items = (d?.['items'] ?? []) as Record<string, any>[]
  if (!d || items.length === 0) return null
  return (
    <div data-permis-proximite className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2.5">
      <div className="mb-1 flex items-baseline justify-between">
        <span className="text-xs font-semibold text-txt">Permis à proximité</span>
        <span className="text-[11px] text-txt-dim">
          <b style={{ color: VIOLET }}>{d['c100']}</b> à &lt; 100 m · {d['c200']} à &lt; 200 m
        </span>
      </div>
      <p className="mb-2 text-[10.5px] leading-snug text-txt-dim">{d['note']} Cliquez pour la fiche.</p>
      <div className="flex flex-col gap-1">
        {items.slice(0, 12).map((i, k) => (
          <button key={k} onClick={() => setOpen(i['permit_id'] as string)}
            className="flex items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-2.5 py-1.5 text-left text-[11px] hover:border-[#6b5a96]">
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
