import { LEGEND_ORDER, STATUT_META } from '../../lib/status'
import { useApp } from '../../store/useApp'

export function Legend() {
  const mode = useApp((s) => s.mode)
  return (
    <div className="absolute bottom-4 right-4 rounded-[10px] border border-line-2 bg-surface-2 px-4 py-3">
      <p className="mb-2 font-mono text-[11px] tracking-widest text-txt-dim">
        {mode === 'verdict' ? 'VERDICT' : 'MUTABILITÉ'}
      </p>
      {mode === 'verdict' ? (
        <div className="flex flex-col gap-1.5">
          {LEGEND_ORDER.map((s) => (
            <div key={s} className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full" style={{ background: STATUT_META[s].color }} />
              <span className="text-[11px] text-txt">{STATUT_META[s].label}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-1.5">
          <div className="h-2 w-28 rounded-full" style={{ background: 'linear-gradient(90deg,#1E2A23,#2E6B4F,#46A88A,#5CE6A1)' }} />
          <div className="flex justify-between text-[10px] text-txt-dim">
            <span>0 m²</span>
            <span>SDP résiduelle</span>
            <span>5 000+</span>
          </div>
        </div>
      )}
    </div>
  )
}
