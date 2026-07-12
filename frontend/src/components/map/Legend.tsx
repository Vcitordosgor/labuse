import { useQuery } from '@tanstack/react-query'
import { LEGEND_ORDER, LEGEND_V2_ORDER, STATUT_META, TIER_V2_META } from '../../lib/status'
import { useApp } from '../../store/useApp'

// Correctif M5 : quand un run scoring v2 existe, la carte colore par le tier v2 — la légende
// suit (mêmes couleurs que le verdict d'en-tête). Sans run (404/503), légende matrice legacy.
export function useV2Actif(): boolean {
  const q = useQuery({
    queryKey: ['v2-actif'],
    queryFn: async () => (await fetch('/v2/modele')).ok,
    retry: false, staleTime: Infinity,
  })
  return q.data === true
}

/** `inline` : rendu dans un flux (tiroir mobile) au lieu du coin de carte. Sous 640 px la
 *  légende flottante recouvrait le hero (item 1 UX V1) → elle vit dans le tiroir « Couches ». */
export function Legend({ inline = false }: { inline?: boolean }) {
  const mode = useApp((s) => s.mode)
  const v2 = useV2Actif()
  return (
    <div className={`rounded-[10px] border border-line-2 bg-surface-2 px-4 py-3 ${
      inline ? '' : 'absolute bottom-4 right-4 hidden sm:block'}`}>
      <p className="mb-2 font-mono text-[11px] tracking-widest text-txt-dim">
        {mode === 'verdict' ? (v2 ? 'VERDICT · SCORING V2' : 'VERDICT') : 'MUTABILITÉ'}
      </p>
      {mode === 'verdict' ? (
        <div className="flex flex-col gap-1.5">
          {v2
            ? LEGEND_V2_ORDER.map((t) => (
                <div key={t} className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full" style={{ background: TIER_V2_META[t].color }} />
                  <span className="text-[11px] text-txt">{TIER_V2_META[t].label}</span>
                </div>
              ))
            : LEGEND_ORDER.map((s) => (
                <div key={s} className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full" style={{ background: STATUT_META[s].color }} />
                  <span className="text-[11px] text-txt">{STATUT_META[s].label}</span>
                </div>
              ))}
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          <div className="h-2 w-28 rounded-full" style={{ background: 'linear-gradient(90deg,#1E2A23,#2E6B4F,#46A88A,#5CE6A1)' }} />
          <div className="flex justify-between text-[11px] text-txt-dim">
            <span>0 m²</span>
            <span>SDP résiduelle</span>
            <span>5 000+</span>
          </div>
        </div>
      )}
    </div>
  )
}
