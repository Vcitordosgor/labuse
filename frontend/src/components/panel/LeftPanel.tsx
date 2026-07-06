import { useApp, type LayerToggles } from '../../store/useApp'
import { ResultsSection } from './ResultsSection'

const LAYERS: { key: keyof LayerToggles; label: string }[] = [
  { key: 'zonage', label: 'Zonage PLU' },
  { key: 'parcelles', label: 'Parcelles' },
  { key: 'ppr', label: 'PPR multirisque' },
  { key: 'vue_mer', label: 'Vue mer' },
  { key: 'parc', label: 'Parc national' },
]

function LayersSection() {
  const { layers, toggleLayer } = useApp()
  return (
    <div className="px-5 pt-5">
      <p className="mb-3 font-mono text-[11px] tracking-widest text-txt-dim">COUCHES</p>
      <div className="flex flex-col gap-2.5">
        {LAYERS.map(({ key, label }) => {
          const on = layers[key]
          return (
            <button key={key} onClick={() => toggleLayer(key)} className="flex items-center gap-3 text-left">
              <span
                className={`flex h-[13px] w-[13px] items-center justify-center rounded-[3px] ${
                  on ? 'bg-mint' : 'border border-line-2'
                }`}
              >
                {on && (
                  <svg viewBox="0 0 10 10" className="h-2.5 w-2.5">
                    <polyline points="2,5.5 4,7.5 8,3" fill="none" stroke="#06130C" strokeWidth="1.8" />
                  </svg>
                )}
              </span>
              <span className={`text-xs ${on ? 'text-txt' : 'text-txt-mut'}`}>{label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export function LeftPanel() {
  return (
    <aside className="flex h-full w-[300px] shrink-0 flex-col border-r border-line bg-surface-1">
      <div className="flex items-center justify-between px-5 pt-5">
        <h2 className="text-sm font-medium text-txt-hi">Cartes</h2>
        <button className="text-txt-dim hover:text-txt" title="Replier">‹</button>
      </div>
      <LayersSection />
      <div className="mx-5 my-4 border-t border-line" />
      <ResultsSection />
    </aside>
  )
}
