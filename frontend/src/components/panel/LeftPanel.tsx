import { useEffect, useState } from 'react'
import { useApp, type LayerToggles } from '../../store/useApp'
import { ResultsSection } from './ResultsSection'

const LAYERS: { key: keyof LayerToggles; label: string; hint?: string }[] = [
  { key: 'zonage', label: 'Zonage PLU', hint: 'U/AU en menthe, A/N en brun' },
  { key: 'parcelles', label: 'Parcelles', hint: 'colorées par statut' },
  { key: 'ppr', label: 'PPR multirisque' },
  { key: 'vue_mer', label: 'Vue mer', hint: 'liseré cyan (vue dégagée)' },
  { key: 'parc', label: 'Parc national' },
  { key: 'limites', label: 'Limites parcelles', hint: 'contours de toutes les parcelles' },
  { key: 'anru', label: 'ANRU (NPNRU)', hint: 'périmètres de renouvellement urbain (8 quartiers d’intérêt national)' },
  { key: 'equipements', label: 'Équipements', hint: 'mairie · écoles · santé · police/gendarmerie · sport (OSM, affichage seul)' },
]

//: couches servies par commune (GeoJSON) — indisponibles en mode « Toute l'île » (payload)
// R6 (revue Vic n°2) : TOUTES les couches sont servies île (zonage/PPR en MVT, parc en
// GeoJSON simplifié 8 Mo opt-in, ANRU/équipements en direct) — plus rien de commune-scopé.
const COMMUNE_ONLY: (keyof LayerToggles)[] = []

function LayersSection() {
  const { layers, toggleLayer, commune } = useApp()
  const ile = commune == null
  // R5 (revue Vic n°2) : le hint est ANCRÉ au contrôle cliqué — bref, contigu, auto-éteint
  const [hintKey, setHintKey] = useState<string | null>(null)
  useEffect(() => {
    if (!hintKey) return
    const t = setTimeout(() => setHintKey(null), 2500)
    return () => clearTimeout(t)
  }, [hintKey])
  return (
    <div className="px-5 pt-4">
      <p className="mb-3 font-mono text-[11px] tracking-widest text-txt-dim">COUCHES</p>
      <div className="flex flex-col gap-1.5">
        {LAYERS.map(({ key, label, hint }) => {
          const off = ile && COMMUNE_ONLY.includes(key)
          const on = layers[key] && !off
          return (
            <div key={key}>
              <button
                onClick={() => (off ? setHintKey(key) : (setHintKey(null), toggleLayer(key)))}
                className={`flex items-center gap-3 text-left ${off ? 'opacity-45' : ''}`}
                title={off ? undefined : hint}>
                <span className={`flex h-[13px] w-[13px] shrink-0 items-center justify-center rounded-[3px] ${on ? 'bg-mint' : 'border border-line-2'}`}>
                  {on && (
                    <svg viewBox="0 0 10 10" className="h-2.5 w-2.5">
                      <polyline points="2,5.5 4,7.5 8,3" fill="none" stroke="#06130C" strokeWidth="1.8" />
                    </svg>
                  )}
                </span>
                <span className={`text-xs ${on ? 'text-txt' : 'text-txt-mut'}`}>{label}</span>
              </button>
              {hintKey === key && (
                <p data-hint-couche={key} className="ml-6 mt-0.5 text-[10px] text-st-creuser">
                  Par commune — choisissez une commune ↑
                </p>
              )}
            </div>
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
