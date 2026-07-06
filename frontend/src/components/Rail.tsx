import { useApp, type View } from '../store/useApp'
import { MODULES, VIOLET } from './outils/registry'

// Icônes 20×20, trait 1.6, arrondi — redessinées pour être nettes à 20 px (les précédentes
// rendaient mal). Cohérence : contour simple, pas de remplissage sauf CRM (barres).
type Zone = Exclude<View, 'sources'> | 'outils'

const ICONS: Record<Zone, JSX.Element> = {
  ia: (
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
}

const ZONES: { key: Zone; label: string }[] = [
  { key: 'ia', label: 'IA' },
  { key: 'cartes', label: 'Cartes' },
  { key: 'outils', label: 'Outils' },
  { key: 'crm', label: 'CRM' },
]

export function Rail() {
  const { view, setView, outilsOpen, toggleOutils, openSources, setModule } = useApp()

  return (
    <>
      <nav className="flex h-full w-16 shrink-0 flex-col items-center border-r border-line bg-surface-1 py-4">
        {/* logo — la buse */}
        <svg viewBox="-2 -2 36 14" className="mb-6 h-5 w-10 shrink-0">
          <path d="M0 10 Q8 0 16 8 Q24 0 32 10" stroke="#5CE6A1" strokeWidth="2.2" fill="none" strokeLinecap="round" />
        </svg>

        {ZONES.map(({ key, label }) => {
          const on = key === 'outils' ? outilsOpen : view === key && !outilsOpen
          return (
            <button
              key={key}
              onClick={() => (key === 'outils' ? toggleOutils() : setView(key))}
              className="group mb-4 flex w-full flex-col items-center gap-1"
              title={label}
            >
              <span
                className={`flex h-10 w-10 items-center justify-center rounded-[10px] border transition-colors ${
                  on ? 'border-[#2E6B4F] bg-[#0F1A14] text-mint' : 'border-transparent text-txt-mut group-hover:text-txt'
                }`}
              >
                <svg viewBox="0 0 20 20" className="h-5 w-5">{ICONS[key]}</svg>
              </span>
              <span className={`text-[10.5px] ${on ? 'text-mint' : 'text-txt-mut'}`}>{label}</span>
            </button>
          )
        })}

        <div className="mt-auto flex flex-col items-center gap-1.5">
          {/* Fraîcheur des données → page Sources (exigence #9) */}
          <button
            onClick={() => openSources()}
            className="flex flex-col items-center gap-1"
            title="Fraîcheur des données — voir les sources"
          >
            <span className="h-2 w-2 rounded-full bg-mint" />
            <span className={`font-mono text-[11px] ${view === 'sources' ? 'text-mint' : 'text-txt-mut'}`}>J-2</span>
          </button>
          <span
            className="mt-2 flex h-7 w-7 items-center justify-center rounded-full border border-line-2 bg-surface-3 font-mono text-[11px] text-mint"
            title="Vic — LABUSE"
          >
            VL
          </span>
        </div>
      </nav>

      {/* Tiroir Outils : mécanisme d'accueil VIDE (V1) — élégant, sans module */}
      {outilsOpen && (
        <aside className="flex h-full w-[300px] shrink-0 flex-col border-r border-line bg-surface-1 p-5">
          <h2 className="text-sm font-medium text-txt-hi">Outils</h2>
          <p className="mt-1 font-mono text-[11px] tracking-widest text-txt-dim">MODULES</p>
          <div className="mt-4 flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
            {MODULES.map((m) => (
              <button key={m.key} onClick={() => setModule(m.key)}
                className="rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-left hover:border-[#6b5a96]">
                <div className="flex items-baseline gap-2">
                  <span className="font-mono text-[10px]" style={{ color: VIOLET }}>{m.num}</span>
                  <span className="text-xs font-medium text-txt">{m.label}</span>
                </div>
                <div className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">{m.desc}</div>
              </button>
            ))}
          </div>
        </aside>
      )}
    </>
  )
}
