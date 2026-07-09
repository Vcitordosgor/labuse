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
  { key: 'communes', label: 'Limites communes', hint: 'contours communaux officiels (ligne verte)' },
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
    // FIX (rendu liste) : sur un volet court (laptop), COUCHES est PLAFONNÉ + scrollable pour
    // qu'il n'écrase plus la liste des résultats — il cède la place, la liste garde sa hauteur.
    <div className="shrink px-5 pt-4 max-h-[34vh] overflow-y-auto">
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

// P2 (revue Vic n°3) : le geste signature affirme un AVIS argumenté, pas une décision prise à
// votre place. « Afficher l'analyse LABUSE » — rien n'est masqué, le cadastre reste entier,
// chaque parcelle garde son verdict cliquable. L'utilisateur garde la main.
function VerdictHero() {
  const { verdict, setVerdict } = useApp()
  if (verdict) {
    return (
      <div className="mx-5 mb-1 flex shrink-0 items-center justify-between rounded-lg border border-[#2E6B4F] bg-[#0F1A14] px-3 py-1.5">
        <span className="text-[11px] font-medium text-mint">✓ Analyse LABUSE affichée</span>
        <button data-verdict-off onClick={() => setVerdict(false)}
          className="text-[10px] text-txt-dim hover:text-txt" title="Masquer l'analyse — revenir au cadastre brut">
          masquer
        </button>
      </div>
    )
  }
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-6 pb-10 text-center">
      <svg viewBox="0 0 240 82" className="h-7 w-20" fill="#2FE0A0" style={{ filter: 'drop-shadow(0 0 10px rgba(47,224,160,0.4))' }}>
        <path d="M2 15 C58 10 100 18 120 27 C140 18 182 10 238 15 C202 29 162 40 135 46 C127 49 122 53 120 60 C118 53 113 49 105 46 C78 40 38 29 2 15 Z" />
      </svg>
      <p className="mt-4 text-xs leading-relaxed text-txt-mut">
        Le cadastre entier est sous vos yeux — 431 663 parcelles, toutes cliquables.
        <br />LABUSE les a analysées et vous propose son avis.
      </p>
      <button data-verdict-on onClick={() => setVerdict(true)}
        className="mt-5 w-full rounded-xl bg-mint px-4 py-3.5 font-display text-sm font-bold text-mint-ink shadow-[0_0_24px_rgba(92,230,161,0.35)] transition hover:shadow-[0_0_36px_rgba(92,230,161,0.55)]">
        Afficher l'analyse LABUSE →
      </button>
      <p className="mt-3 text-[10px] leading-snug text-txt-dim">
        Rien n'est masqué : le cadastre reste entier, chaque parcelle garde son verdict —
        <br />cliquez-en une pour voir pourquoi. Vous gardez la main.
      </p>
    </div>
  )
}

export function LeftPanel() {
  const { panelOpen, togglePanel, verdict } = useApp()
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
      <VerdictHero />
      {verdict && <ResultsSection />}
    </aside>
  )
}
