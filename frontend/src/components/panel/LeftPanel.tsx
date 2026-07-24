import { useEffect, useRef, useState } from 'react'
import { useApp, type LayerToggles } from '../../store/useApp'
import { Legend } from '../map/Legend'
import { LAYER_INFO } from '../../lib/layers'
import { Tip } from '../Tip'
import { ResultsSection } from './ResultsSection'
import { CLIENT } from '../../lib/strings'

// B8 (M12) : « Comprendre le classement » — explication du scoring ÉCRITE POUR UN CLIENT
// (contenu centralisé dans strings.ts, validé par Vic avant prod). Overlay léger, fermable.
function AlgoExplainer({ onClose }: { onClose: () => void }) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])
  return (
    <div data-algo-overlay className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}>
      <div className="max-h-[80vh] w-full max-w-md overflow-y-auto rounded-xl border border-line-2 bg-surface-2 p-5 shadow-elev-2"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3">
          <h3 className="font-display text-sm font-bold text-txt-hi">{CLIENT.algo.titre}</h3>
          <button onClick={onClose} className="shrink-0 rounded-md px-2 py-0.5 text-txt-dim hover:text-txt"
            aria-label="Fermer">✕</button>
        </div>
        <div className="mt-3 flex flex-col gap-3">
          {CLIENT.algo.corps.map((s) => (
            <div key={s.h}>
              <p className="label-caps text-[9.5px]">{s.h}</p>
              <p className="mt-0.5 text-[12px] leading-relaxed text-txt-mut">{s.p}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// M12 C4 — ORDRE des couches, du PLUS UTILISÉ au moins utilisé (justif. au rapport) :
//  1. parcelles       — la couche de travail (verdict coloré) — vue à chaque session
//  2. limites         — contour cadastral, référence constante posée sur le fond
//  3. zonage_colorise — lecture d'ensemble de la constructibilité (nouveau, C5) — geste rapide
//  4. zonage_parcelle — zone précise à la parcelle (étiquette + clic) — le détail
//  5. zonage          — zones officielles brutes du GPU — moins fréquent (déjà couvert par 3/4)
//  6. ppr             — écran risques, filtre d'exclusion précoce fréquent
//  7. equipements     — contexte de proximité, courant en due diligence
//  8. communes        — repère communal (défaut ON, rarement basculé)
//  9. parc            — Parc national, situationnel (relief/mi-pentes)
// 10. anru            — périmètres de renouvellement, de niche
// 11. cinquante_pas   — bande littorale, la plus rare (communes côtières uniquement)
const LAYERS: { key: keyof LayerToggles; label: string }[] = [
  { key: 'parcelles', label: 'Parcelles' },
  { key: 'limites', label: 'Limites parcelles' },
  // M12 C5 : colorise TOUTES les parcelles par type de zone, sans clic — à côté (pas à la place)
  { key: 'zonage_colorise', label: 'Colorisation par type de zonage' },
  // M6.1 item 1 : recoloration + étiquette de la zone précise au zoom et au clic
  { key: 'zonage_parcelle', label: 'Zonage PLU (par parcelle)' },
  // Point 12 : zones OFFICIELLES du GPU (polygones bruts), distinctes du rattachement à la parcelle
  { key: 'zonage', label: 'Zonage PLU (zones officielles)' },
  { key: 'ppr', label: 'PPR multirisque' },
  { key: 'equipements', label: 'Équipements' },
  { key: 'communes', label: 'Limites communes' },
  { key: 'parc', label: 'Parc national' },
  { key: 'anru', label: 'ANRU (NPNRU)' },
  // M6.1 item 2 : réserve domaniale littorale — libellé métier exact exigé par le mandat
  { key: 'cinquante_pas', label: '50 pas géométriques' },
]

// M12 C2 — pastille « i » d'une couche : au survol OU au clic, l'explication CLIENT (LAYER_INFO,
// centralisée) apparaît. Le clic sur la pastille NE bascule PAS la couche (stopPropagation dans Tip).
function LayerInfoPill({ info }: { info: string }) {
  if (!info) return null
  return (
    <Tip side="top" tip={info} className="shrink-0">
      <span
        role="button"
        tabIndex={0}
        aria-label="En savoir plus sur cette couche"
        className="flex h-[15px] w-[15px] items-center justify-center rounded-full border border-line-2 text-[9px] font-bold leading-none text-txt-dim transition-colors duration-quick hover:border-mint hover:text-mint"
      >
        i
      </span>
    </Tip>
  )
}

// M12 C1 / M13 D1 — « Couches » est un TIROIR REPLIABLE, OUVERT PAR DÉFAUT tant que
// l'analyse LABUSE n'est pas affichée (QA-47). Il se referme automatiquement quand on clique
// « Afficher l'analyse LABUSE » (voir LeftPanel : effet sur `verdict`), pour libérer la place.
// Plus d'auto-fermeture 10 s : c'est le passage à l'analyse qui replie les couches.
// Ouvert, il POUSSE le contenu du dessous (flux flex : jamais de recouvrement, la liste des
// résultats reste entière).
function LayersSection({ open, onToggle }: {
  open: boolean
  onToggle: () => void
}) {
  const { layers, toggleLayer } = useApp()
  const activeCount = LAYERS.reduce((n, { key }) => n + (layers[key] ? 1 : 0), 0)
  return (
    <div className="shrink-0 px-5 pt-4">
      <button
        data-couches-toggle
        onClick={onToggle}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 text-left"
        title={open ? 'Replier les couches' : 'Déplier les couches'}
      >
        <span className="label-caps">Couches</span>
        <span className="flex items-center gap-2">
          {activeCount > 0 && (
            <span className="rounded-full bg-mint/15 px-1.5 py-0.5 text-[9.5px] font-medium text-mint">{activeCount} active{activeCount > 1 ? 's' : ''}</span>
          )}
          <span className={`text-txt-dim transition-transform duration-quick ${open ? 'rotate-180' : ''}`} aria-hidden="true">⌄</span>
        </span>
      </button>
      {open && (
        // plafonné + scrollable : sur un volet court, la liste des résultats garde sa hauteur
        <div className="mt-3 max-h-[38vh] overflow-y-auto">
          <div className="flex flex-col gap-0.5">
            {LAYERS.map(({ key, label }) => {
              const on = layers[key]
              const info = LAYER_INFO[key] ?? ''
              return (
                <div key={key} className="flex items-center gap-2">
                  <button
                    onClick={() => toggleLayer(key)}
                    className="flex min-h-[28px] flex-1 items-center gap-3 rounded-md py-1 text-left transition-colors duration-quick"
                  >
                    <span className={`flex h-[13px] w-[13px] shrink-0 items-center justify-center rounded-[3px] ${on ? 'bg-mint' : 'border border-line-2'}`}>
                      {on && (
                        <svg viewBox="0 0 10 10" className="h-2.5 w-2.5">
                          <polyline points="2,5.5 4,7.5 8,3" fill="none" stroke="#06130C" strokeWidth="1.8" />
                        </svg>
                      )}
                    </span>
                    <span className={`text-xs ${on ? 'text-txt' : 'text-txt-mut'}`}>{label}</span>
                  </button>
                  <LayerInfoPill info={info} />
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// P2 (revue Vic n°3) : le geste signature affirme un AVIS argumenté, pas une décision prise à
// votre place. « Afficher l'analyse LABUSE » — rien n'est masqué, le cadastre reste entier,
// chaque parcelle garde son verdict cliquable. L'utilisateur garde la main.
function VerdictHero() {
  const { verdict, setVerdict } = useApp()
  const [algoOpen, setAlgoOpen] = useState(false)
  if (verdict) {
    return (
      <div className="mx-5 mb-1 flex shrink-0 items-center justify-between gap-2 rounded-lg bg-mint/[0.08] px-3 py-2 shadow-elev-1">
        {algoOpen && <AlgoExplainer onClose={() => setAlgoOpen(false)} />}
        <span className="min-w-0 truncate text-[11px] font-medium text-mint">✓ Analyse LABUSE affichée</span>
        <span className="flex shrink-0 items-center gap-1.5">
          {/* B8 : « Comprendre le classement » à côté de l'analyse affichée */}
          <button data-algo-open onClick={() => setAlgoOpen(true)}
            className="rounded-full border border-mint/40 px-2 py-0.5 text-[10.5px] font-medium text-mint hover:bg-mint/10"
            title="Ce que le classement mesure, sur quoi il est entraîné, ce qu'il ne dit pas">
            {CLIENT.algo.bouton}
          </button>
          {/* B9 : « masquer » est désormais un vrai bouton affirmé (plus un texte gris) */}
          <button data-verdict-off onClick={() => setVerdict(false)}
            className="rounded-full border border-line-2 px-2 py-0.5 text-[10.5px] text-txt-mut hover:border-txt-dim hover:text-txt"
            title="Masquer l'analyse — revenir au cadastre brut">
            Masquer
          </button>
        </span>
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
  // M13 D1 (QA-47) : « Couches » OUVERT PAR DÉFAUT tant que l'analyse LABUSE n'est pas affichée.
  // État partagé desktop/mobile.
  const [couchesOpen, setCouchesOpen] = useState(true)
  // M13 D1 : plus d'auto-fermeture 10 s ; c'est l'affichage de l'analyse LABUSE (`verdict` passe
  // à true) qui replie les couches pour libérer la place. On ne force la fermeture qu'à la
  // BASCULE (false→true), jamais ensuite : l'utilisateur peut rouvrir manuellement.
  const prevVerdict = useRef(verdict)
  useEffect(() => {
    if (verdict && !prevVerdict.current) setCouchesOpen(false)
    prevVerdict.current = verdict
  }, [verdict])
  const toggleCouches = () => setCouchesOpen((o) => !o)
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
            <button onClick={togglePanel} className="text-txt-dim hover:text-txt" title="Replier le panneau" aria-label="Replier le panneau">‹</button>
          </div>
          <LayersSection open={couchesOpen} onToggle={toggleCouches} />
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
              <button data-couches-fermer onClick={() => setMobileOpen(false)} aria-label="Fermer"
                className="flex h-7 w-7 items-center justify-center rounded-md text-txt-dim transition-colors duration-quick hover:bg-surface-3 hover:text-txt" title="Revenir à la carte">✕</button>
            </div>
            <LayersSection open={couchesOpen} onToggle={toggleCouches} />
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
