import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { EMPTY_FILTERS, useApp, type LayerToggles } from '../../store/useApp'
import { Legend } from '../map/Legend'
import { LAYER_INFO } from '../../lib/layers'
import { getFiltre } from '../../lib/api'
import { countActiveFilters } from '../../lib/filters'
import { TIER_V2_META, type FilterTier, type TierV2 } from '../../lib/status'
import { Tip } from '../Tip'
import { ResultsSection } from './ResultsSection'
import { FiltreLabuse } from './FiltreLabuse'
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
//  3. zonage_parcelle — couche PARCELLAIRE UNIQUE (M55-A fusion A) : colore toutes les parcelles
//                       par famille + code au zoom/clic — remplace « colorisation » + « par parcelle »
//  4. zonage          — zones officielles brutes du GPU (document opposable) — moins fréquent
//  5. ppr             — écran risques, filtre d'exclusion précoce fréquent
//  6. equipements     — contexte de proximité, courant en due diligence
//  7. communes        — repère communal (défaut ON, rarement basculé)
//  8. parc            — Parc national, situationnel (relief/mi-pentes)
//  9. anru            — périmètres de renouvellement, de niche
// 10. cinquante_pas   — bande littorale, la plus rare (communes côtières uniquement)
const LAYERS: { key: keyof LayerToggles; label: string }[] = [
  { key: 'parcelles', label: 'Parcelles' },
  { key: 'limites', label: 'Limites parcelles' },
  // M55-A (fusion A) : couche PARCELLAIRE UNIQUE — colore d'emblée toutes les parcelles par famille
  // ET révèle le code exact au zoom / au clic (l'ancienne case « Colorisation » est fusionnée ici).
  { key: 'zonage_parcelle', label: 'Zonage PLU par parcelle (calibré)' },
  // M55-A : zones OFFICIELLES du GPU (polygones bruts du document opposable) — distinctes du
  // rattachement calibré à la parcelle ; couvrent aussi l'espace non parcellaire (voirie, domaine public).
  { key: 'zonage', label: 'Zones du PLU officiel (brut)' },
  { key: 'ppr', label: 'PPR multirisque' },
  { key: 'equipements', label: 'Équipements' },
  { key: 'communes', label: 'Limites communes' },
  { key: 'parc', label: 'Parc national' },
  { key: 'anru', label: 'ANRU (NPNRU)' },
  // M6.1 item 2 : réserve domaniale littorale — libellé métier exact exigé par le mandat
  { key: 'cinquante_pas', label: '50 pas géométriques' },
  // M-RENOUV : segment Renouvellement (occupées, potentiel) — OFF par défaut, teinte cuivre
  { key: 'renouv', label: 'Renouvellement' },
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

// M12 C1 / M14 B3 (QA-64, reprise M13-D1/QA-47) — « Couches » est un TIROIR REPLIABLE, OUVERT
// PAR DÉFAUT tant que l'analyse LABUSE n'est pas affichée. Il se referme quand on clique
// « Afficher l'analyse LABUSE » (bascule `verdict`), pour libérer la place. Plus d'auto-fermeture
// 10 s. Ouvert, il POUSSE le contenu du dessous (flux flex : jamais de recouvrement).
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
        className="group flex w-full items-center justify-between gap-2 text-left"
        title={open ? 'Replier les couches' : 'Déplier les couches'}
      >
        <span className="label-caps">Couches</span>
        {/* M55-C point 3bis : le badge « N actives » respire (gap-3 = 12 px) — la zone de clic
            du chevron n'est plus ambiguë. */}
        <span className="flex items-center gap-3">
          {activeCount > 0 && (
            <span className="rounded-full bg-mint/15 px-1.5 py-0.5 text-[9.5px] font-medium text-mint">{activeCount} active{activeCount > 1 ? 's' : ''}</span>
          )}
          {/* M55-A item 5 : REPLIÉ → chevron vers la GAUCHE (⌄ pivoté 90°), DÉPLIÉ → vers le BAS.
              M55-C point 3 : harmonisé avec la croix du panneau — même boîte (h/w 7), même poids
              et même survol (group-hover → txt-hi), rotation douce (duration-soft, ease-cockpit). */}
          <span aria-hidden="true"
            className={`flex h-7 w-7 items-center justify-center text-base leading-none text-txt-dim transition-[transform,color] duration-soft ease-cockpit group-hover:text-txt-hi ${open ? '' : 'rotate-90'}`}>⌄</span>
        </span>
      </button>
      {open && (
        // plafonné + scrollable : sur un volet court, la liste des résultats garde sa hauteur.
        // QA-46 (M13-C) : overflow-x-clip — un `overflow-y-auto` calcule overflow-x=auto, si bien
        // que les tooltips absolus (Tip, `w-max`) débordant du volet étroit y déclenchaient une
        // BARRE HORIZONTALE fantôme. `clip` sur x supprime la barre sans créer de conteneur de
        // défilement, le tooltip reste peint. Défaut identique corrigé partout (fiche/CRM/tri).
        <div data-couches-drawer className="mt-3 max-h-[38vh] overflow-y-auto overflow-x-clip">
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

// M55-D stage 3 — « Filtres » = SECTION REPLIABLE du panneau gauche, MÊME carrosserie que « Couches »
// (titre + badge « N actifs » + chevron fermé→gauche/ouvert→bas). Ouverte : les 3 RAPIDES
// (Verdict / Surface / SDP, mêmes champs du store) + « Tous les filtres → » qui déplie le panneau
// EXPERT complet (FiltreLabuse, contenu du stage 2 inchangé). Accroche HONNÊTE : les filtres trient,
// ils ne recalculent pas (mesuré en phase 1). Le bouton header « Filtres (N) » a disparu.
function FiltresSection({ open, onToggle }: { open: boolean; onToggle: () => void }) {
  const { filters, setFilter, commune } = useApp()
  const [expertOpen, setExpertOpen] = useState(false)
  const n = countActiveFilters(filters)
  const TIERS: TierV2[] = ['brulante', 'chaude', 'reserve_fonciere', 'a_creuser', 'ecartee']
  const toggleTier = (t: FilterTier) =>
    setFilter('tiers', filters.tiers.includes(t) ? filters.tiers.filter((x) => x !== t) : [...filters.tiers, t])
  // N = parc du run servi dans le périmètre courant (dynamique) = la TRAME ENTIÈRE (analyse coupée →
  // toutes les parcelles analysées, retenues + écartées), pas un sous-ensemble. getFiltre lit la
  // commune active.
  const parc = useQuery({ queryKey: ['filtre-parc', commune], queryFn: () => getFiltre({ ...EMPTY_FILTERS, analyseLabuse: false }, 0) })
  const N = parc.data?.total
  const Num = ({ field, ph }: { field: 'surfaceMin' | 'surfaceMax' | 'sdpMin'; ph: string }) => (
    <input type="number" min={0} value={filters[field] ?? ''} placeholder={ph}
      onChange={(e) => setFilter(field, (e.target.value === '' ? null : Number(e.target.value)) as never)}
      className="w-[64px] rounded-md border border-line-2 bg-surface-3 px-1.5 py-0.5 text-[11px] text-txt focus:border-mint focus:outline-none" />
  )
  return (
    <div className="shrink-0 px-5 pt-4">
      <button data-filtres-toggle onClick={onToggle} aria-expanded={open}
        className="group flex w-full items-center justify-between gap-2 text-left"
        title={open ? 'Replier les filtres' : 'Déplier les filtres'}>
        <span className="label-caps">Filtres</span>
        <span className="flex items-center gap-3">
          {n > 0 && (
            <span className="rounded-full bg-mint/15 px-1.5 py-0.5 text-[9.5px] font-medium text-mint">{n} actif{n > 1 ? 's' : ''}</span>
          )}
          <span aria-hidden="true"
            className={`flex h-7 w-7 items-center justify-center text-base leading-none text-txt-dim transition-[transform,color] duration-soft ease-cockpit group-hover:text-txt-hi ${open ? '' : 'rotate-90'}`}>⌄</span>
        </span>
      </button>
      {open && (
        // plafonné + scrollable (comme le tiroir Couches) : le panneau EXPERT déplié est haut, il
        // scrolle DANS la section au lieu de casser la colonne flex de l'aside.
        <div data-filtres-drawer className="mt-3 max-h-[52vh] overflow-y-auto overflow-x-clip">
          {/* ── 3 RAPIDES ── */}
          <p className="label-caps text-txt-dim">Verdict</p>
          <div className="mt-1 flex flex-wrap gap-1.5">
            {TIERS.map((t) => (
              <button key={t} onClick={() => toggleTier(t)}
                className={`rounded-full border px-2 py-0.5 text-[11px] ${
                  filters.tiers.includes(t) ? 'border-mint text-txt-hi' : 'border-line-2 text-txt-mut'}`}>
                <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full align-middle" style={{ background: TIER_V2_META[t].color }} />
                {TIER_V2_META[t].label}
              </button>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap items-end gap-x-4 gap-y-2">
            <div><p className="label-caps text-txt-dim">Surface m²</p>
              <div className="mt-1 flex items-center gap-1"><Num field="surfaceMin" ph="min" /><span className="text-txt-dim">–</span><Num field="surfaceMax" ph="max" /></div></div>
            <div><p className="label-caps text-txt-dim">SDP résiduelle ≥</p>
              <div className="mt-1"><Num field="sdpMin" ph="m²" /></div></div>
          </div>
          {/* ── TOUS LES FILTRES → (déplie l'expert) + accroche honnête ── */}
          <button data-tous-les-filtres onClick={() => setExpertOpen((o) => !o)}
            className="mt-3 flex items-center gap-1.5 text-[12px] font-medium text-mint hover:underline">
            Tous les filtres
            <span className={`inline-block transition-transform duration-soft ${expertOpen ? 'rotate-90' : ''}`} aria-hidden="true">→</span>
          </button>
          <p className="mt-1 text-[10.5px] leading-snug text-txt-dim">
            {N != null ? CLIENT.filtres.accroche(N) : 'Filtres experts — affinez parmi les parcelles déjà analysées par LABUSE'}
          </p>
          {expertOpen && <div className="mt-2"><FiltreLabuse /></div>}
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
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center overflow-hidden px-6 pb-10 text-center">
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
  // M14 B3 (QA-64) : « Couches » OUVERT PAR DÉFAUT tant que l'analyse LABUSE n'est pas affichée.
  // État partagé desktop/mobile. Plus d'auto-fermeture 10 s : c'est la BASCULE vers l'analyse
  // (`verdict` false→true) qui replie les couches, une seule fois — l'utilisateur peut rouvrir.
  const [couchesOpen, setCouchesOpen] = useState(true)
  const prevVerdict = useRef(verdict)
  useEffect(() => {
    if (verdict && !prevVerdict.current) setCouchesOpen(false)
    prevVerdict.current = verdict
  }, [verdict])
  // M55-D stage 3 : la section « Filtres » (repliable, sous « Couches ») remplace le bouton header.
  // Fermée par défaut (le badge « N actifs » signale l'activité même repliée).
  const [filtresOpen, setFiltresOpen] = useState(false)
  // Accordéon : ouvrir une section replie l'autre — la colonne (hauteur fixe) ne déborde jamais,
  // même quand le panneau EXPERT est déplié dans « Filtres ».
  const toggleCouches = () => { setCouchesOpen((o) => !o); setFiltresOpen(false) }
  const toggleFiltres = () => { setFiltresOpen((o) => !o); setCouchesOpen(false) }
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
            {/* M55-B point 5 : une FERMETURE, pas un repli → croix (×), cohérent avec la fiche
                parcelle et le contexte commune (croix partout). Le ré-affichage se fait par la
                languette « › » quand le panneau est masqué. */}
            <button onClick={togglePanel} className="text-txt-dim hover:text-txt-hi" title="Fermer le panneau" aria-label="Fermer le panneau">✕</button>
          </div>
          <LayersSection open={couchesOpen} onToggle={toggleCouches} />
          <FiltresSection open={filtresOpen} onToggle={toggleFiltres} />
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
            <FiltresSection open={filtresOpen} onToggle={toggleFiltres} />
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
