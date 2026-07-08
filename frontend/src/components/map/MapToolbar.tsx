import { useEffect, useState } from 'react'
import { useApp, type Basemap, type MapTool, type OrthoYear } from '../../store/useApp'

const BASEMAPS: { key: Basemap; label: string }[] = [
  { key: 'dark', label: 'Sombre (Carto)' },
  { key: 'plan', label: 'Plan IGN' },
  { key: 'ortho', label: 'Ortho IGN' },
]
// Millésimes VÉRIFIÉS sur le 974 (WMTS Géoplateforme, tuiles testées) — « remonter le temps ».
const YEARS: { key: OrthoYear; label: string }[] = [
  { key: 'now', label: 'Actuelle' },
  { key: '2000', label: '2000-2005' },
  { key: '1950', label: '1950-1965' },
]
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
  {
    key: 'zone', label: 'Zone', hint: 'Dessinez un polygone : les résultats sont filtrés à la zone',
    icon: (
      <>
        <path d="M4.5 5.5 L15 4 L16 14.5 L6 16 Z" stroke="currentColor" strokeWidth="1.3" fill="none" strokeDasharray="2.6 2" strokeLinejoin="round" />
        <circle cx="10" cy="10" r="1.6" fill="currentColor" />
      </>
    ),
  },
]

export function MapToolbar() {
  const { basemap, setBasemap, orthoYear, setOrthoYear, terrain3d, toggleTerrain, tool, setTool, zone, setZone, commune } = useApp()
  const [bmOpen, setBmOpen] = useState(false)
  const ile = commune == null
  // R5 : hint ancré à l'outil (pas un toast lointain), auto-éteint
  const [zoneHint, setZoneHint] = useState(false)
  useEffect(() => {
    if (!zoneHint) return
    const t = setTimeout(() => setZoneHint(false), 2500)
    return () => clearTimeout(t)
  }, [zoneHint])

  return (
    <div className="absolute right-4 top-4 flex flex-col items-end gap-2">
      {/* fond de plan */}
      <div className="relative">
        <button
          onClick={() => setBmOpen((o) => !o)}
          className={`flex h-9 items-center gap-2 rounded-[10px] border px-3 text-xs ${
            bmOpen ? 'border-mint text-txt-hi' : 'border-line-2 bg-surface-2 text-txt hover:text-txt-hi'}`}
          title="Fond de plan"
        >
          <svg viewBox="0 0 20 20" className="h-4 w-4">
            <polygon points="10,3 17,7 10,11 3,7" fill="none" stroke="currentColor" strokeWidth="1.4" />
            <polygon points="10,9.5 17,13.5 10,17.5 3,13.5" fill="none" stroke="currentColor" strokeWidth="1.4" opacity="0.5" />
          </svg>
          {BASEMAPS.find((b) => b.key === basemap)?.label}
          {basemap === 'ortho' && orthoYear !== 'now' && <span className="text-mint">· {YEARS.find((y) => y.key === orthoYear)?.label}</span>}
        </button>
        {bmOpen && (
          <>
            <div className="fixed inset-0 z-10" onClick={() => setBmOpen(false)} />
            <div className="absolute right-0 top-11 z-20 w-56 rounded-xl border border-line-2 bg-surface-2 p-3 shadow-2xl">
              <p className="font-mono text-[10px] tracking-widest text-txt-dim">FOND DE PLAN</p>
              <div className="mt-2 flex flex-col gap-1">
                {BASEMAPS.map((b) => (
                  <button key={b.key} onClick={() => setBasemap(b.key)}
                    className={`rounded-md px-2 py-1.5 text-left text-xs ${basemap === b.key ? 'bg-[#0F1A14] text-mint' : 'text-txt hover:bg-surface-3'}`}>
                    {b.label}
                  </button>
                ))}
              </div>
              <p className="mt-3 font-mono text-[10px] tracking-widest text-txt-dim" title="Orthophotos historiques IGN — données libres">REMONTER LE TEMPS</p>
              <div className="mt-2 flex gap-1">
                {YEARS.map((y) => (
                  <button key={y.key} onClick={() => setOrthoYear(y.key)}
                    className={`flex-1 rounded-md border px-1 py-1 text-[11px] ${
                      basemap === 'ortho' && orthoYear === y.key ? 'border-mint text-mint' : 'border-line-2 text-txt-mut hover:text-txt'}`}>
                    {y.label}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </div>

      {/* relief 3D */}
      <button
        onClick={toggleTerrain}
        className={`flex h-9 items-center gap-2 rounded-[10px] border px-3 text-xs ${
          terrain3d ? 'border-mint bg-[#0F1A14] text-mint' : 'border-line-2 bg-surface-2 text-txt hover:text-txt-hi'}`}
        title="Relief 3D (MNT) — maintenir Ctrl + glisser pour incliner la vue"
      >
        <svg viewBox="0 0 20 20" className="h-4 w-4">
          <path d="M2.5 15.5 L8 6 L11.5 12 L14 8.5 L17.5 15.5 Z" stroke="currentColor" strokeWidth="1.4" fill="none" strokeLinejoin="round" />
        </svg>
        3D
      </button>

      {/* outils de mesure */}
      <div className="flex flex-col overflow-hidden rounded-[10px] border border-line-2 bg-surface-2">
        {TOOLS.map((t) => {
          // le filtre de zone compte côté client sur les features de la commune chargée —
          // en mode « Toute l'île » il serait menteur : désactivé avec la marche à suivre
          const off = t.key === 'zone' && ile
          return (
            <div key={t.key} className="relative">
              <button
                onClick={() => (off ? setZoneHint(true) : setTool(tool === t.key ? null : t.key))}
                className={`flex h-9 w-9 items-center justify-center border-b border-line-2 last:border-0 ${
                  off ? 'text-[#2E3A33]'
                    : tool === t.key ? 'bg-[#0F1A14] text-mint' : 'text-txt-mut hover:text-txt'}`}
                title={off ? undefined : `${t.label} — ${t.hint}`}
              >
                <svg viewBox="0 0 20 20" className="h-[18px] w-[18px]">{t.icon}</svg>
              </button>
              {off && zoneHint && (
                <span data-hint-zone className="absolute right-11 top-1/2 -translate-y-1/2 whitespace-nowrap rounded-md border border-st-creuser/40 bg-[#211a10] px-2 py-1 text-[10px] text-st-creuser">
                  Par commune — choisissez une commune
                </span>
              )}
            </div>
          )
        })}
      </div>

      {zone && (
        <button
          onClick={() => setZone(null)}
          className="flex h-8 items-center gap-2 rounded-full border border-mint bg-[#0F1A14] px-3 text-[11px] text-mint"
          title="Retirer le filtre de zone"
        >
          Zone active <span className="text-txt-dim">×</span>
        </button>
      )}
    </div>
  )
}
