import { useApp, type LayerToggles } from '../../store/useApp'
import { ResultsSection } from './ResultsSection'

const LAYERS: { key: keyof LayerToggles; label: string; hint?: string }[] = [
  { key: 'zonage', label: 'Zonage PLU', hint: 'U/AU en menthe, A/N en brun' },
  { key: 'parcelles', label: 'Parcelles', hint: 'colorées par statut' },
  { key: 'ppr', label: 'PPR multirisque' },
  { key: 'vue_mer', label: 'Vue mer', hint: 'liseré cyan (vue dégagée)' },
  { key: 'parc', label: 'Parc national' },
  { key: 'limites', label: 'Limites parcelles', hint: 'contours de toutes les parcelles' },
]

//: couches servies par commune (GeoJSON) — indisponibles en mode « Toute l'île » (payload)
const COMMUNE_ONLY: (keyof LayerToggles)[] = ['zonage', 'ppr', 'parc']

function LayersSection() {
  const { layers, toggleLayer, commune } = useApp()
  const ile = commune == null
  return (
    <div className="px-5 pt-4">
      <p className="mb-3 font-mono text-[11px] tracking-widest text-txt-dim">COUCHES</p>
      <div className="flex flex-col gap-2.5">
        {LAYERS.map(({ key, label, hint }) => {
          const off = ile && COMMUNE_ONLY.includes(key)
          const on = layers[key] && !off
          return (
            <button key={key} disabled={off} onClick={() => toggleLayer(key)}
              className={`flex items-center gap-3 text-left ${off ? 'cursor-not-allowed opacity-45' : ''}`}
              title={off ? `${label} — sélectionnez une commune (couche servie par commune)` : hint}>
              <span className={`flex h-[13px] w-[13px] shrink-0 items-center justify-center rounded-[3px] ${on ? 'bg-mint' : 'border border-line-2'}`}>
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
  const { panelOpen, togglePanel } = useApp()
  if (!panelOpen) {
    return (
      <button
        onClick={togglePanel}
        className="flex h-full w-8 shrink-0 items-start justify-center border-r border-line bg-surface-1 pt-5 text-txt-dim hover:text-txt"
        title="Déplier le panneau"
      >
        ›
      </button>
    )
  }
  return (
    <aside className="flex h-full w-[300px] shrink-0 flex-col border-r border-line bg-surface-1">
      <div className="flex shrink-0 items-center justify-between px-5 pt-4">
        <h2 className="text-sm font-medium text-txt-hi">Cartes</h2>
        <button onClick={togglePanel} className="text-txt-dim hover:text-txt" title="Replier le panneau">‹</button>
      </div>
      <LayersSection />
      <div className="mx-5 my-3 shrink-0 border-t border-line" />
      <ResultsSection />
    </aside>
  )
}
