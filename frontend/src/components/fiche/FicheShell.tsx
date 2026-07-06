import { useQuery } from '@tanstack/react-query'
import { getResults } from '../../lib/api'
import { STATUT_META } from '../../lib/status'
import { useApp } from '../../store/useApp'

const TABS = ['Synthèse', 'Règles', 'Risques', 'Marché', 'Proprio', 'Bilan']

export function FicheShell({ idu }: { idu: string }) {
  const select = useApp((s) => s.select)
  // Coquille Brique 1 : en-tête réel (depuis le cache résultats), corps rempli en Brique 2.
  const results = useQuery({ queryKey: ['results'], queryFn: getResults })
  const p = results.data?.find((r) => r.idu === idu)
  const meta = p ? STATUT_META[p.status] : null

  return (
    <aside className="absolute right-0 top-0 z-10 flex h-full w-[380px] flex-col border-l border-line bg-surface-1 shadow-2xl">
      {p?.evenement === 'rouge' && (
        <div className="flex items-center gap-2 bg-[#3a1614] px-5 py-2 text-xs font-medium text-st-ecartee">
          ● Événement — procédure BODACC ouverte force « chaude »
        </div>
      )}
      <div className="flex items-start justify-between border-b border-line px-5 py-4">
        <div>
          <div className="font-mono text-sm font-medium text-txt-hi">{idu}</div>
          {meta && (
            <span className="mt-1 inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px]" style={{ background: `${meta.color}22`, color: meta.color }}>
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: meta.color }} />
              {meta.label}
            </span>
          )}
        </div>
        <button onClick={() => select(null)} className="text-txt-mut hover:text-txt-hi" title="Fermer">✕</button>
      </div>

      {p && (
        <div className="grid grid-cols-3 gap-px border-b border-line bg-line">
          {[
            { k: 'Qualité', v: p.q_score, c: '#5CE6A1' },
            { k: 'Accessibilité', v: p.a_score, c: '#4ADE96' },
            { k: 'Complétude', v: p.completeness_score, c: p.completeness_score >= 50 ? '#5CE6A1' : '#E8B44C' },
          ].map((x) => (
            <div key={x.k} className="bg-surface-1 px-4 py-3">
              <div className="font-display text-xl font-bold" style={{ color: x.c }}>{x.v}</div>
              <div className="text-[11px] text-txt-mut">{x.k}</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-4 border-b border-line px-5 py-2 text-xs">
        {TABS.map((t, i) => (
          <span key={t} className={i === 0 ? 'text-txt-hi' : 'text-txt-dim'}>{t}</span>
        ))}
      </div>

      <div className="flex flex-1 items-center justify-center px-6 text-center text-xs text-txt-dim">
        Fiche détaillée (barres Q/A dépliables, 6 onglets, faits datés, flags cliquables) —{' '}
        <span className="text-txt-mut">&nbsp;Brique 2</span>.
      </div>
    </aside>
  )
}
