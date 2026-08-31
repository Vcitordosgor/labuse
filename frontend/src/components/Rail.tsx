import { useQuery } from '@tanstack/react-query'
import { getMoi } from '../lib/api'
import { useApp, type View } from '../store/useApp'
import { MODULES } from './outils/registry'

// Icônes 20×20, trait 1.6, arrondi — redessinées pour être nettes à 20 px (les précédentes
// rendaient mal). Cohérence : contour simple, pas de remplissage sauf CRM (barres).
// RETOURS-3 R2 — le rail suit UN ordre imposé, unique, de haut en bas (Carte · Outils · Copilote ·
// Radar · Veille · Projets · CRM · Sources), puis Admin APRÈS Sources (hors liste du mandat, signalé).
// 'veille'/'sources' sont désormais DANS la liste (plus au pied) ; 'admin' reste gated à la fin.
type Zone = Exclude<View, 'admin'> | 'outils'

const ICONS: Record<Zone, JSX.Element> = {
  // M62-P1 (a/b) : l'entrée « IA » du rail = le Copilote (view 'copilote') → ÉTINCELLES.
  // M65 P4 : l'entrée « Recherche » (IAStub, view 'ia') est RETIRÉE — le Copilote absorbe le
  // montage de projet (entretienDirect) et la recherche NL reste dans l'omnibox du header.
  copilote: (
    <>
      <path d="M10 3.5 L11.6 8.4 L16.5 10 L11.6 11.6 L10 16.5 L8.4 11.6 L3.5 10 L8.4 8.4 Z"
        fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </>
  ),
  cartes: (
    <>
      <path d="M3.5 6.5 L8 4.5 L12 6.5 L16.5 4.5 V13.5 L12 15.5 L8 13.5 L3.5 15.5 Z"
        fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <line x1="8" y1="4.5" x2="8" y2="13.5" stroke="currentColor" strokeWidth="1.2" opacity="0.6" />
      <line x1="12" y1="6.5" x2="12" y2="15.5" stroke="currentColor" strokeWidth="1.2" opacity="0.6" />
    </>
  ),
  // RADAR-CATÉGORIE (T1) — icône radar de la maquette (cercles concentriques + point + balayage),
  // adaptée au viewBox 20 du rail.
  radar: (
    <>
      <circle cx="10" cy="10" r="7.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="10" cy="10" r="3.8" fill="none" stroke="currentColor" strokeWidth="1.3" />
      <circle cx="10" cy="10" r="1" fill="currentColor" />
      <path d="M10 2.5v2.4M17.5 10h-2.4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </>
  ),
  outils: (
    <>
      <circle cx="10" cy="10" r="6.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M12.6 7.4 L11 11 L7.4 12.6 L9 9 Z" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
    </>
  ),
  crm: (
    <>
      <rect x="3.5" y="9" width="3.6" height="7.5" rx="0.8" fill="currentColor" />
      <rect x="8.2" y="5" width="3.6" height="11.5" rx="0.8" fill="currentColor" />
      <rect x="12.9" y="11.5" width="3.6" height="5" rx="0.8" fill="currentColor" />
    </>
  ),
  // dossier + étoile : un projet formalisé, gardé (copilote-projet)
  projets: (
    <>
      <path d="M3.5 6 H8.2 L9.6 7.6 H16.5 V15 A0.8 0.8 0 0 1 15.7 15.8 H4.3 A0.8 0.8 0 0 1 3.5 15 Z"
        fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M10 9 L10.7 10.7 L12.5 10.9 L11.2 12.1 L11.6 13.9 L10 13 L8.4 13.9 L8.8 12.1 L7.5 10.9 L9.3 10.7 Z"
        fill="currentColor" stroke="none" />
    </>
  ),
  // RV2-V3 — Veille : cercles concentriques + repères cardinaux (radar de veille).
  veille: (
    <>
      <circle cx="10" cy="10" r="6.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="10" cy="10" r="2" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M10 1v2M10 17v2M1 10h2M17 10h2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </>
  ),
  // « base de données / fraîcheur » : stack de disques (remplace l'ancien badge « J-2 »)
  sources: (
    <>
      <ellipse cx="10" cy="5.5" rx="5.5" ry="2.2" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <path d="M4.5 5.5 V10 c0 1.2 2.5 2.2 5.5 2.2 s5.5 -1 5.5 -2.2 V5.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <path d="M4.5 10 v4.5 c0 1.2 2.5 2.2 5.5 2.2 s5.5 -1 5.5 -2.2 V10" fill="none" stroke="currentColor" strokeWidth="1.4" />
    </>
  ),
}

// RETOURS-3 R2.1 — l'ORDRE IMPOSÉ, de haut en bas (référence unique, aucun autre tri). `ia` marque la
// seule surface IA (Copilote → survol/actif mauve). Admin n'est PAS dans cette liste : il est rendu
// APRÈS Sources (gated), cf. compte-rendu.
type RailKey = Zone
const RAIL: { key: RailKey; label: string; ia?: boolean }[] = [
  { key: 'cartes', label: 'Carte' },
  { key: 'outils', label: 'Outils' },
  { key: 'copilote', label: 'Copilote', ia: true },
  { key: 'radar', label: 'Radar' },
  { key: 'veille', label: 'Veille' },
  { key: 'projets', label: 'Projets' },
  { key: 'crm', label: 'CRM' },
  { key: 'sources', label: 'Sources' },
]
// titres NON redondants seulement (R2.3 : le tooltip qui répète le libellé sous l'icône est retiré).
const RAIL_TITLE: Partial<Record<RailKey, string>> = {
  veille: 'Veille — le foncier (parcelles, critères) et les annonces (Radar)',
  sources: 'Fraîcheur des données — sources et mises à jour',
}

// §2 (23/08/2026) — une carte OUTIL au GABARIT UNIQUE : plus de distinction « phare » (ni étoile,
// ni graisse renforcée). Chaque carte porte la BARRE VERTICALE GAUCHE (door-hot = border-left mint).
// Aucun code M à l'écran (gardé en interne seulement).
function OutilCard({ m, open }: { m: (typeof MODULES)[number]; open: (k: string) => void }) {
  return (
    <button
      key={m.key}
      data-outil={m.key}
      onClick={() => open(m.key)}
      className="door door-hot mb-0 w-full text-left transition-colors duration-quick hover:border-line-3"
    >
      <div className="text-xs font-medium text-txt">{m.label}</div>
      <div className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">{m.desc}</div>
    </button>
  )
}

// DASHBOARD-V1 — entrée « Tour de contrôle » au pied de rail : VISIBLE seulement pour l'admin
// (role 'admin' ou session locale dev). La visibilité est du confort d'UI — la vraie garde est
// côté backend (exiger_admin sur chaque /admin/*, 403 client).
function AdminRailEntry() {
  const { view, setView, outilsOpen } = useApp()
  const moi = useQuery({ queryKey: ['moi'], queryFn: getMoi, staleTime: 3_600_000 })
  const admin = (moi.data != null && moi.data.mode !== 'compte') || moi.data?.role === 'admin'
  if (!admin) return null
  const on = view === 'admin' && !outilsOpen
  return (
    <button data-rail-admin data-rail="admin" onClick={() => setView('admin')} aria-current={on ? 'page' : undefined}
      className={`rail-item ${on ? 'active' : ''}`} title="Tour de contrôle — pilotage de LABUSE (admin)">
      {/* jauge/compteur — le pilotage */}
      <svg viewBox="0 0 20 20" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M3.5 13.5 a6.5 6.5 0 1 1 13 0" strokeLinecap="round" />
        <path d="M10 13.5 L13.2 8.6" strokeLinecap="round" />
        <circle cx="10" cy="13.5" r="1.2" fill="currentColor" stroke="none" />
      </svg>
      <span className="rail-label">Admin</span>
    </button>
  )
}

export function Rail() {
  const { view, setView, outilsOpen, toggleOutils, openSources, setModule, toggleSurveillance } = useApp()
  // M104 — UNE seule entrée « Surveillance » (fusion Suivis + Secteurs + Critères, arbitrage
  // 17/08). Les notifications restent à la CLOCHE (chrome global) : la section configure et
  // liste ce qu'on surveille, la cloche affiche ce qui en sort.
  // M55-L point 9 — « Comparer » est un outil : son clic n'ouvre pas un ModulePanel mais l'overlay
  // comparateur (setCompareOpen). C'est l'OUVERTURE de la sélection courante (compareIdus persiste
  // en session) ; l'AJOUT reste sur la fiche (mesuré : ouvrir Outils remet selectedIdu à null, donc
  // un outil ne peut pas récupérer la parcelle regardée). Ferme le tiroir Outils.
  const openOutil = (k: string) => {
    // COMPARAISON (refonte) : « comparer » est un outil ANCRÉ dans Outils — openCompare ouvre son
    // panneau gauche (module='comparer', outilsOpen:false, picking ON, TTL 15 min), la carte reste
    // active à droite. Plus de bascule surprise vers « Cartes » ni de tiroir à refermer à la main.
    if (k === 'comparer') { useApp.getState().openCompare(); return }
    setModule(k)
  }

  return (
    <>
      <nav className="flex h-full w-16 shrink-0 flex-col items-center gap-1.5 overflow-y-auto border-r border-line bg-surface-1 py-5">
        {/* P4 (revue Vic n°3) — le rail est PUR icônes de navigation (l'oiseau + « LABUSE » vit au header).
            RETOURS-3 R2 — ordre imposé unique (RAIL), survol plein + sélection route-dérivée (classe .rail-item).
            L'entrée active dérive de `view`/`outilsOpen` : AUCUNE classe .active posée en JS en plus (source
            unique = la route), et le survol (@media hover) ne s'applique jamais à l'active → plus de double état. */}
        {RAIL.map(({ key, label, ia }) => {
          const on = key === 'outils' ? outilsOpen : view === key && !outilsOpen
          const act = () => {
            if (key === 'outils') return toggleOutils()
            if (key === 'veille') return toggleSurveillance()
            if (key === 'sources') return openSources()
            setView(key as View)
          }
          return (
            <button key={key} data-rail={key} {...(key === 'veille' ? { 'data-rail-surveillance': true } : {})}
              onClick={act} aria-current={on ? 'page' : undefined}
              className={`rail-item ${on ? 'active' : ''} ${ia ? 'ia' : ''}`}
              {...(RAIL_TITLE[key] ? { title: RAIL_TITLE[key] } : {})}>
              <svg viewBox="0 0 20 20" className="h-5 w-5">{ICONS[key]}</svg>
              <span className="rail-label">{label}</span>
            </button>
          )
        })}
        {/* R2.1 — Admin ne figure PAS dans l'ordre imposé : rendu APRÈS Sources, visible admin seulement (signalé). */}
        <AdminRailEntry />
      </nav>

      {/* §2 (23/08/2026) — Tiroir Outils EN LISTE PLATE : plus de catégories, plus d'étoile « phare ».
          Une seule colonne, gabarit unique, dans l'ORDRE d'usage probable fixé par registry.ts
          (instruire le bien → sourcer/approcher → lire le marché → analyse ponctuelle). */}
      {outilsOpen && (
        <aside className="flex h-full w-[320px] shrink-0 flex-col border-r border-line bg-surface-1">
          <div className="shrink-0 px-5 pb-2 pt-5">
            <h2 className="text-sm font-medium text-txt-hi">Outils</h2>
            {/* M82 : compte DYNAMIQUE (le nombre d'outils bouge) ; « métier » retiré (hors sujet). */}
            <p className="mt-0.5 text-[11px] leading-snug text-txt-dim">
              {MODULES.filter((m) => !m.hidden).length} outils fonciers, du repérage à l’action.
            </p>
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto px-5 pb-5">
            {MODULES.filter((m) => !m.hidden).map((m) => (   // clés aliasées (hidden) : pas de carte en double
              <OutilCard key={m.key} m={m} open={openOutil} />
            ))}
          </div>
        </aside>
      )}
    </>
  )
}
