import { useEffect, useState } from 'react'
import { useApp, type LayerToggles } from '../../store/useApp'
import { Legend } from '../map/Legend'
import { ResultsSection } from './ResultsSection'

const LAYERS: { key: keyof LayerToggles; label: string; hint?: string }[] = [
  // Point 12 : deux couches distinctes clarifiées — zones OFFICIELLES du GPU (polygones bruts)
  // vs zone rattachée PAR PARCELLE (parcel_zone_plu). Libellés + hints qui lèvent la confusion.
  { key: 'zonage', label: 'Zonage PLU (zones officielles)', hint: 'carte officielle des zones du GPU — polygones bruts (U/AU en menthe, A/N en brun)' },
  // M6.1 item 1 : recoloration des PARCELLES par famille de zone (palette dédiée) +
  // étiquette de la zone précise (U1e, 1AUc…) au zoom rapproché et au clic
  { key: 'zonage_parcelle', label: 'Zonage PLU (par parcelle)', hint: 'chaque parcelle colorée par sa zone rattachée (U/AU/A/N) — zone précise au zoom ≥ 16 et au clic' },
  { key: 'parcelles', label: 'Parcelles', hint: 'colorées par statut' },
  { key: 'ppr', label: 'PPR multirisque' },
  { key: 'parc', label: 'Parc national' },
  { key: 'limites', label: 'Limites parcelles', hint: 'contours de toutes les parcelles' },
  { key: 'communes', label: 'Limites communes', hint: 'contours communaux officiels (ligne verte)' },
  { key: 'anru', label: 'ANRU (NPNRU)', hint: 'périmètres de renouvellement urbain (8 quartiers d’intérêt national)' },
  // M6.1 item 2 : réserve domaniale littorale — libellé métier exact exigé par le mandat
  { key: 'cinquante_pas', label: '50 pas géométriques', hint: 'Réserve des 50 pas géométriques — bande de 81,20 m depuis le rivage (spécifique outre-mer)' },
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
      <p className="label-caps mb-3">Couches</p>
      <div className="flex flex-col gap-0.5">
        {LAYERS.map(({ key, label, hint }) => {
          const off = ile && COMMUNE_ONLY.includes(key)
          const on = layers[key] && !off
          return (
            <div key={key}>
              <button
                onClick={() => (off ? setHintKey(key) : (setHintKey(null), toggleLayer(key)))}
                className={`flex min-h-[28px] items-center gap-3 rounded-md py-1 text-left transition-colors duration-quick ${off ? 'opacity-45' : ''}`}
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
                <p data-hint-couche={key} className="ml-6 mt-0.5 text-[11px] text-st-creuser">
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
      <div className="mx-5 mb-1 flex shrink-0 items-center justify-between rounded-lg bg-mint/[0.08] px-3 py-2 shadow-elev-1">
        <span className="text-[11px] font-medium text-mint">✓ Analyse LABUSE affichée</span>
        <button data-verdict-off onClick={() => setVerdict(false)}
          className="text-[11px] text-txt-dim hover:text-txt" title="Masquer l'analyse — revenir au cadastre brut">
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
        className="mt-5 w-full rounded-xl bg-mint px-4 py-3.5 font-display text-sm font-bold text-mint-ink shadow-[0_0_24px_rgba(92,230,161,0.35)] transition-shadow duration-soft ease-cockpit hover:shadow-[0_0_36px_rgba(92,230,161,0.55)]">
        Afficher l'analyse LABUSE →
      </button>
      <p className="mt-3 text-[11px] leading-snug text-txt-dim">
        Rien n'est masqué : le cadastre reste entier, chaque parcelle garde son verdict —
        <br />cliquez-en une pour voir pourquoi. Vous gardez la main.
      </p>
    </div>
  )
}

export function LeftPanel() {
  const { panelOpen, togglePanel, verdict } = useApp()
  // Item 1 (UX V1, mobile) : sous 640 px le panneau occupait 100 % de l'écran — la carte
  // n'existait pas. Désormais la CARTE est l'écran d'accueil mobile ; COUCHES + légende
  // VERDICT vivent dans un tiroir escamotable (bouton « Couches » flottant).
  const [mobileOpen, setMobileOpen] = useState(false)
  return (
    <>
      {/* ── desktop ≥ 640 px : panneau latéral inchangé ── */}
      {!panelOpen ? (
        <button
          onClick={togglePanel}
          className="hidden h-full w-8 shrink-0 items-start justify-center border-r border-line bg-surface-1 pt-5 text-txt-dim hover:text-txt sm:flex"
          title="Déplier le panneau"
        >
          ›
        </button>
      ) : (
        <aside className="hidden h-full w-[300px] shrink-0 flex-col border-r border-line bg-surface-1 sm:flex">
          <div className="flex shrink-0 items-center justify-between px-5 pt-4">
            <h2 className="text-sm font-medium text-txt-hi">Cartes</h2>
            <button onClick={togglePanel} className="text-txt-dim hover:text-txt" title="Replier le panneau">‹</button>
          </div>
          <LayersSection />
          <div className="mx-5 my-3 shrink-0 border-t border-line" />
          <VerdictHero />
          {verdict && <ResultsSection />}
        </aside>
      )}

      {/* ── mobile < 640 px : carte plein écran, panneau en tiroir ── */}
      {!mobileOpen && (
        <button
          data-couches-mobile
          onClick={() => setMobileOpen(true)}
          className="absolute bottom-16 left-4 z-30 flex items-center gap-2 rounded-full border border-line-2 bg-surface-2 px-4 py-2 text-xs font-medium text-txt shadow-elev-2 sm:hidden"
          title="Couches, analyse et résultats"
        >
          <svg viewBox="0 0 20 20" className="h-4 w-4 text-mint">
            <path d="M10 3.5 L17 7 L10 10.5 L3 7 Z" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
            <path d="M3 10.5 L10 14 L17 10.5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
            <path d="M3 13.5 L10 17 L17 13.5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" opacity="0.55" />
          </svg>
          Couches
        </button>
      )}
      {mobileOpen && (
        <div data-couches-drawer className="absolute inset-0 z-40 flex sm:hidden">
          <div className="absolute inset-0 bg-black/55" onClick={() => setMobileOpen(false)} />
          <aside className="relative flex h-full w-[300px] max-w-[86%] flex-col border-r border-line bg-surface-1 shadow-elev-3">
            <div className="flex shrink-0 items-center justify-between px-5 pt-4">
              <h2 className="text-sm font-medium text-txt-hi">Cartes</h2>
              <button data-couches-fermer onClick={() => setMobileOpen(false)} className="text-txt-dim hover:text-txt" title="Revenir à la carte">✕</button>
            </div>
            <LayersSection />
            <div className="mx-5 my-3 shrink-0 border-t border-line" />
            <div className="shrink-0 px-5 pb-1"><Legend inline /></div>
            <VerdictHero />
            {verdict && <ResultsSection />}
          </aside>
        </div>
      )}
    </>
  )
}
