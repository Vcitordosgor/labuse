import { useState } from 'react'
import { useApp, type Basemap, type MapTool } from '../../store/useApp'
import { ORTHO_YEARS } from './basemaps'   // FIX-FONDS B5 — millésimes partagés avec l'outil TEMPS
import { Tip } from '../Tip'   // M62-P1 (c) : infobulles à 150 ms (survol) / immédiat (focus/clic)

// M105 P4.2 — SOMBRE EN PREMIER (défaut au boot : readBasemap = 'dark', vérifié).
// COUCHES-STYLE-6 : le fond « Clair » est RETIRÉ du sélecteur (bouton + option). Restent Sombre,
// Plan IGN et Ortho IGN, inchangés. (M63-P1 avait ajouté Clair au sélecteur ; on l'en retire.)
const BASEMAPS: { key: Basemap; label: string }[] = [
  { key: 'dark', label: 'Sombre' },
  { key: 'plan', label: 'Plan IGN' },
  { key: 'ortho', label: 'Ortho IGN' },
]
// Millésimes VÉRIFIÉS sur le 974 : ORTHO_YEARS (basemaps.ts) = Actuelle + les 6 de TEMPS_MILLESIMES.
// FINITIONS-1 (P1) — les 3 outils de mesure gardent leur infobulle AU SURVOL (seule exception de l'app),
// avec un libellé SIMPLIFIÉ (le verbe, pas la notice de saisie qui vit déjà dans le bandeau du bas).
const TOOLS: { key: MapTool; label: string; icon: JSX.Element; tip: string }[] = [
  {
    key: 'distance', label: 'Distance', tip: 'Calculer une distance',
    icon: <path d="M3 17 L17 3 M5.5 14.5 l1.6 1.6 M8.5 11.5 l1.6 1.6 M11.5 8.5 l1.6 1.6" stroke="currentColor" strokeWidth="1.4" fill="none" />,
  },
  {
    key: 'surface', label: 'Surface', tip: 'Calculer un périmètre',
    icon: <path d="M4 6 L14 3.5 L16.5 13 L7 16.5 Z" stroke="currentColor" strokeWidth="1.4" fill="none" strokeLinejoin="round" />,
  },
  {
    key: 'alti', label: 'Altitude', tip: 'Connaître l\'altitude',
    icon: <path d="M3 16 L8 7 L11 12 L13.5 8.5 L17 16 Z" stroke="currentColor" strokeWidth="1.4" fill="none" strokeLinejoin="round" />,
  },
  // RETOURS-1 R8 (Vic) : le bouton « Zone — Dessinez un polygone » quitte la barre. Le filtre de
  // zone reste dans le store/back (réversible) ; la pastille « Zone active × » reste le seul
  // affordance de sortie si un état zone existe encore en session.
]

export function MapToolbar() {
  const { basemap, setBasemap, orthoYear, setOrthoYear, terrain3d, toggleTerrain, tool, setTool, zone, setZone, selectedIdu, view, contexteCommune } = useApp()
  // M58-P1 (point carte) : quand la fiche (aside 400px, à droite) est ouverte, elle recouvrait ces
  // contrôles. On les décale vers la gauche de la largeur de la fiche (+16px de marge), transition
  // 180ms, retour à la fermeture. Aucun contrôle inaccessible.
  // RECETTE-10 T8 — la fiche COMMUNE (aside 420px, `ContextePanel`) recouvrait AUSSI ces contrôles
  // (le décalage ne regardait que la fiche parcelle) : même comportement, même animation, décalage à
  // la largeur de la fiche ouverte (420 + 16). Fini les contrôles de vue inaccessibles sous la fiche.
  const ficheParcelle = selectedIdu != null && view !== 'sources'
  const ficheCommune = contexteCommune != null
  const decalage = ficheParcelle ? 416 : ficheCommune ? 436 : 16
  const [bmOpen, setBmOpen] = useState(false)

  return (
    <div className="absolute top-4 flex flex-col items-end gap-2"
      style={{ right: decalage, transition: 'right 180ms cubic-bezier(.2,0,0,1)' }}>
      {/* DA §11 — « Sombre » (fond de plan) et « 3D » ALIGNÉS sur une même ligne. */}
      <div className="flex items-center gap-2">
      {/* fond de plan */}
      <div className="relative">
        <button
          onClick={() => setBmOpen((o) => !o)}
          /* RETOURS-19 Y1 — menu ouvert = ÉTAT ACTIF : vert opaque, contenu inversé sombre (avant : simple
             contour vert sur fond sombre). FINITIONS-1 (P3) — au SURVOL (état inactif), le bouton « Vue »
             (fond de plan) reçoit la MÊME animation verte que partout ailleurs (`hover-fill` : fond vert
             opaque, contenu inversé sombre) au lieu du simple éclaircissement du texte. */
          className={`flex h-9 items-center gap-2 rounded-lg border px-3 text-xs shadow-elev-1 transition-colors duration-quick ${
            bmOpen ? 'border-mint bg-mint text-mint-ink' : 'border-line-2 bg-surface-2 text-txt hover-fill'}`}
          aria-label="Fond de plan"
        >
          <svg viewBox="0 0 20 20" className="h-4 w-4">
            <polygon points="10,3 17,7 10,11 3,7" fill="none" stroke="currentColor" strokeWidth="1.4" />
            <polygon points="10,9.5 17,13.5 10,17.5 3,13.5" fill="none" stroke="currentColor" strokeWidth="1.4" opacity="0.5" />
          </svg>
          {BASEMAPS.find((b) => b.key === basemap)?.label}
          {basemap === 'ortho' && orthoYear !== 'now' && <span className={bmOpen ? 'text-mint-ink/80' : 'text-mint'}>· {ORTHO_YEARS.find((y) => y.an === orthoYear)?.label}</span>}
        </button>
        {bmOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setBmOpen(false)} />
            <div className="floating absolute right-0 top-11 z-20 w-64 p-3">
              <p className="label-caps">Fond de plan</p>
              <div className="mt-2 flex flex-col gap-1">
                {BASEMAPS.map((b) => (
                  <button key={b.key} onClick={() => setBasemap(b.key)}
                    /* RETOURS-19 Y1 — entrée ACTIVE = vert opaque, contenu inversé sombre. FINITIONS-2 (P2) —
                       au SURVOL d'une ligne non active, la même animation verte que partout (`hover-fill`). */
                    className={`rounded-md px-2 py-1.5 text-left text-xs transition-colors duration-quick ${basemap === b.key ? 'bg-mint font-medium text-mint-ink' : 'text-txt hover-fill'}`}>
                    {b.label}
                  </button>
                ))}
              </div>
              <p className="label-caps mt-3">Remonter le temps</p>
              {/* FIX-FONDS B5 (contrainte Vic) — les 7 millésimes en LISTE VERTICALE compacte (pas 6
                  boutons en ligne qui étireraient la cellule) : même gabarit que la liste des fonds
                  ci-dessus, visible seulement quand le menu est déplié. */}
              <div className="mt-1.5 flex flex-col gap-0.5">
                {ORTHO_YEARS.map((y) => (
                  <button key={y.an} onClick={() => setOrthoYear(y.an)}
                    /* FINITIONS-2 (P2) — tranches « Remonter le temps » : survol vert (`hover-fill`) hors ligne active. */
                    className={`rounded-md px-2 py-1 text-left text-[11px] transition-colors duration-quick ${
                      basemap === 'ortho' && orthoYear === y.an ? 'bg-mint font-medium text-mint-ink' : 'text-txt-mut hover-fill'}`}>
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
        /* FINITIONS-1 (P1) — infobulle au survol retirée (le libellé « 3D » du bouton porte le sens). */
        aria-label="Relief 3D"
      >
        3D
      </button>
      </div>

      {/* outils de mesure */}
      <div className="flex flex-col overflow-hidden rounded-lg border border-line-2 bg-surface-2 shadow-elev-1">
        {TOOLS.map((t) => (
          <div key={t.key} className="relative">
            {/* M62-P1 (c) / FINITIONS-1 (P1) : infobulle DA (Tip) à ~150 ms au survol — SEULE exception au
                retrait des infobulles au survol (`survol`). Libellé simplifié au verbe. */}
            <Tip garder survol side="top" hoverDelayMs={150} tip={t.tip}>
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
          aria-label="Retirer le filtre de zone"
        >
          Zone active <span className="text-txt-dim">×</span>
        </button>
      )}
    </div>
  )
}
