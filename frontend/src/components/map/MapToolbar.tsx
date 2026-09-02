import { useState } from 'react'
import { useApp, type Basemap, type MapTool } from '../../store/useApp'
import { ORTHO_YEARS } from './basemaps'   // FIX-FONDS B5 — millésimes partagés avec l'outil TEMPS
import { Tip } from '../Tip'   // M62-P1 (c) : infobulles à 150 ms (survol) / immédiat (focus/clic)

// M63-P1 (a) : le fond CLAIR rejoint le sélecteur existant (pas un nouveau bouton). Libellés simples.
// M105 P4.2 — SOMBRE EN PREMIER (défaut au boot : readBasemap = 'dark', vérifié).
const BASEMAPS: { key: Basemap; label: string }[] = [
  { key: 'dark', label: 'Sombre' },
  { key: 'clair', label: 'Clair' },
  { key: 'plan', label: 'Plan IGN' },
  { key: 'ortho', label: 'Ortho IGN' },
]
// Millésimes VÉRIFIÉS sur le 974 : ORTHO_YEARS (basemaps.ts) = Actuelle + les 6 de TEMPS_MILLESIMES.
const TOOLS: { key: MapTool; label: string; icon: JSX.Element; hint: string }[] = [
  {
    key: 'distance', label: 'Distance', hint: 'Clics = points · double-clic termine · Échap annule',
    icon: <path d="M3 17 L17 3 M5.5 14.5 l1.6 1.6 M8.5 11.5 l1.6 1.6 M11.5 8.5 l1.6 1.6" stroke="currentColor" strokeWidth="1.4" fill="none" />,
  },
  {
    key: 'surface', label: 'Surface', hint: 'Clics = sommets · double-clic ferme le polygone',
    icon: <path d="M4 6 L14 3.5 L16.5 13 L7 16.5 Z" stroke="currentColor" strokeWidth="1.4" fill="none" strokeLinejoin="round" />,
  },
  {
    key: 'alti', label: 'Altitude', hint: 'Clic = altitude au point (RGE ALTI)',
    icon: <path d="M3 16 L8 7 L11 12 L13.5 8.5 L17 16 Z" stroke="currentColor" strokeWidth="1.4" fill="none" strokeLinejoin="round" />,
  },
  // RETOURS-1 R8 (Vic) : le bouton « Zone — Dessinez un polygone » quitte la barre. Le filtre de
  // zone reste dans le store/back (réversible) ; la pastille « Zone active × » reste le seul
  // affordance de sortie si un état zone existe encore en session.
]

export function MapToolbar() {
  const { basemap, setBasemap, orthoYear, setOrthoYear, terrain3d, toggleTerrain, tool, setTool, zone, setZone, selectedIdu, view } = useApp()
  // M58-P1 (point carte) : quand la fiche (aside 400px, à droite) est ouverte, elle recouvrait ces
  // contrôles. On les décale vers la gauche de la largeur de la fiche (+16px de marge), transition
  // 180ms, retour à la fermeture. Aucun contrôle inaccessible.
  const ficheOuverte = selectedIdu != null && view !== 'sources'
  const [bmOpen, setBmOpen] = useState(false)

  return (
    <div className="absolute top-4 flex flex-col items-end gap-2"
      style={{ right: ficheOuverte ? 416 : 16, transition: 'right 180ms cubic-bezier(.2,0,0,1)' }}>
      {/* DA §11 — « Sombre » (fond de plan) et « 3D » ALIGNÉS sur une même ligne. */}
      <div className="flex items-center gap-2">
      {/* fond de plan */}
      <div className="relative">
        <button
          onClick={() => setBmOpen((o) => !o)}
          className={`flex h-9 items-center gap-2 rounded-lg border px-3 text-xs shadow-elev-1 transition-colors duration-quick ${
            bmOpen ? 'border-mint bg-surface-2 text-txt-hi' : 'border-line-2 bg-surface-2 text-txt hover:text-txt-hi'}`}
          title="Fond de plan"
        >
          <svg viewBox="0 0 20 20" className="h-4 w-4">
            <polygon points="10,3 17,7 10,11 3,7" fill="none" stroke="currentColor" strokeWidth="1.4" />
            <polygon points="10,9.5 17,13.5 10,17.5 3,13.5" fill="none" stroke="currentColor" strokeWidth="1.4" opacity="0.5" />
          </svg>
          {BASEMAPS.find((b) => b.key === basemap)?.label}
          {basemap === 'ortho' && orthoYear !== 'now' && <span className="text-mint">· {ORTHO_YEARS.find((y) => y.an === orthoYear)?.label}</span>}
        </button>
        {bmOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setBmOpen(false)} />
            <div className="floating absolute right-0 top-11 z-20 w-64 p-3">
              <p className="label-caps">Fond de plan</p>
              <div className="mt-2 flex flex-col gap-1">
                {BASEMAPS.map((b) => (
                  <button key={b.key} onClick={() => setBasemap(b.key)}
                    className={`rounded-md px-2 py-1.5 text-left text-xs transition-colors duration-quick ${basemap === b.key ? 'bg-mint/10 text-mint' : 'text-txt hover:bg-surface-3'}`}>
                    {b.label}
                  </button>
                ))}
              </div>
              <p className="label-caps mt-3" title="Orthophotos historiques IGN — données libres">Remonter le temps</p>
              {/* FIX-FONDS B5 (contrainte Vic) — les 7 millésimes en LISTE VERTICALE compacte (pas 6
                  boutons en ligne qui étireraient la cellule) : même gabarit que la liste des fonds
                  ci-dessus, visible seulement quand le menu est déplié. */}
              <div className="mt-1.5 flex flex-col gap-0.5">
                {ORTHO_YEARS.map((y) => (
                  <button key={y.an} onClick={() => setOrthoYear(y.an)}
                    className={`rounded-md px-2 py-1 text-left text-[11px] transition-colors duration-quick ${
                      basemap === 'ortho' && orthoYear === y.an ? 'bg-mint/10 text-mint' : 'text-txt-mut hover:bg-surface-3 hover:text-txt'}`}>
                    {y.label}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </div>

      {/* relief 3D — DA §11 : PAS d'icône sur « 3D » (aligné avec « Sombre »). */}
      <button
        onClick={toggleTerrain}
        /* RETOURS-9 (Q9) — contour 3D actif = plein vert, encre sombre (pas un liseré). */
        className={`flex h-9 items-center rounded-lg border px-3 text-xs shadow-elev-1 transition-colors duration-quick ${
          terrain3d ? 'border-mint bg-mint text-mint-ink font-medium' : 'border-line-2 bg-surface-2 text-txt hover:text-txt-hi'}`}
        title="Relief 3D (MNT) — maintenir Ctrl + glisser pour incliner la vue"
      >
        3D
      </button>
      </div>

      {/* outils de mesure */}
      <div className="flex flex-col overflow-hidden rounded-lg border border-line-2 bg-surface-2 shadow-elev-1">
        {TOOLS.map((t) => (
          <div key={t.key} className="relative">
            {/* M62-P1 (c) : infobulle DA (Tip) à ~150 ms au survol, IMMÉDIATE au focus/clic —
                remplace le `title` natif (délai navigateur ~500 ms, jugé trop long). */}
            <Tip side="top" hoverDelayMs={150} tip={`${t.label} — ${t.hint}`}>
              <button
                onClick={() => setTool(tool === t.key ? null : t.key)}
                /* RETOURS-9 (Q9) — outil de carte actif = plein vert, encre sombre. */
                className={`relative flex h-9 w-9 items-center justify-center border-b border-line-2 transition-colors duration-quick last:border-0 ${
                  tool === t.key ? 'bg-mint text-mint-ink' : 'text-txt-mut hover:text-txt'}`}
                aria-label={t.label}
              >
                <svg viewBox="0 0 20 20" className="h-[18px] w-[18px]" aria-hidden="true">{t.icon}</svg>
              </button>
            </Tip>
          </div>
        ))}
      </div>

      {zone && (
        <button
          onClick={() => setZone(null)}
          className="flex h-8 items-center gap-2 rounded-full border border-mint bg-surface-2 px-3 text-[11px] text-mint shadow-elev-1 transition-colors duration-quick hover:bg-mint/10"
          title="Retirer le filtre de zone"
        >
          Zone active <span className="text-txt-dim">×</span>
        </button>
      )}
    </div>
  )
}
