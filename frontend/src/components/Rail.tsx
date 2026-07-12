import { useApp, type View } from '../store/useApp'
import { GROUPS, MODULES, VIOLET } from './outils/registry'

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
  // dossier + étoile : un projet formalisé, gardé (copilote-projet)
  projets: (
    <>
      <path d="M3.5 6 H8.2 L9.6 7.6 H16.5 V15 A0.8 0.8 0 0 1 15.7 15.8 H4.3 A0.8 0.8 0 0 1 3.5 15 Z"
        fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M10 9 L10.7 10.7 L12.5 10.9 L11.2 12.1 L11.6 13.9 L10 13 L8.4 13.9 L8.8 12.1 L7.5 10.9 L9.3 10.7 Z"
        fill="currentColor" stroke="none" />
    </>
  ),
  // cible à 3 anneaux : des SEGMENTS de prospects (moteur de segments Habitat)
  segments: (
    <>
      <circle cx="10" cy="10" r="6.5" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="10" cy="10" r="3.6" fill="none" stroke="currentColor" strokeWidth="1.4" opacity="0.7" />
      <circle cx="10" cy="10" r="1.1" fill="currentColor" stroke="none" />
    </>
  ),
}

const ZONES: { key: Zone; label: string }[] = [
  { key: 'ia', label: 'IA' },
  { key: 'cartes', label: 'Cartes' },
  { key: 'outils', label: 'Outils' },
  { key: 'segments', label: 'Segments' },
  { key: 'projets', label: 'Projets' },
  { key: 'crm', label: 'CRM' },
]

// ── icône « base de données / fraîcheur » : stack de disques (remplace l'ancien badge « J-2 »)
const SOURCES_ICON = (
  <>
    <ellipse cx="10" cy="5.5" rx="5.5" ry="2.2" fill="none" stroke="currentColor" strokeWidth="1.4" />
    <path d="M4.5 5.5 V10 c0 1.2 2.5 2.2 5.5 2.2 s5.5 -1 5.5 -2.2 V5.5" fill="none" stroke="currentColor" strokeWidth="1.4" />
    <path d="M4.5 10 v4.5 c0 1.2 2.5 2.2 5.5 2.2 s5.5 -1 5.5 -2.2 V10" fill="none" stroke="currentColor" strokeWidth="1.4" />
  </>
)

// P3 — une carte OUTIL : phare = mise en avant (bordure/point violet, bénéfice lisible) ;
// secondaire = ligne compacte. Aucun code M à l'écran (gardé en interne seulement).
function OutilCard({ m, phare, open }: { m: (typeof MODULES)[number]; phare: boolean; open: (k: string) => void }) {
  return (
    <button
      key={m.key}
      data-outil={m.key}
      data-outil-phare={phare ? '1' : undefined}
      onClick={() => open(m.key)}
      className={`w-full rounded-lg border px-3 text-left transition-colors ${
        phare
          ? 'border-[#4a3d6b] bg-[#171221] py-2.5 hover:border-[#B497F0]'
          : 'border-line-2 bg-surface-3 py-2 hover:border-[#6b5a96]'
      }`}
    >
      <div className="flex items-center gap-2">
        {phare && <span className="text-[10px]" style={{ color: VIOLET }} title="Outil phare">★</span>}
        <span className={`text-xs font-medium ${phare ? 'text-txt-hi' : 'text-txt'}`}>{m.label}</span>
      </div>
      <div className={`mt-0.5 leading-snug ${phare ? 'text-[11px] text-[#b8a8de]' : 'text-[10.5px] text-txt-dim'}`}>
        {m.desc}
      </div>
    </button>
  )
}

export function Rail() {
  const { view, setView, outilsOpen, toggleOutils, openSources, setModule } = useApp()

  return (
    <>
      <nav className="flex h-full w-16 shrink-0 flex-col items-center border-r border-line bg-surface-1 py-5">
        {/* P4 (revue Vic n°3) — UN SEUL oiseau : le combo oiseau + « LABUSE » vit dans le header.
            Le rail est PUR icônes de navigation, sans logomark redondant (l'oiseau du rail et
            celui du header se retrouvaient côte à côte en haut-gauche → doublon vu par Vic). */}
        {ZONES.map(({ key, label }) => {
          const on = key === 'outils' ? outilsOpen : view === key && !outilsOpen
          return (
            <button
              key={key}
              onClick={() => (key === 'outils' ? toggleOutils() : setView(key))}
              className="group mb-4 flex w-full flex-col items-center gap-1"
              title={label}
              aria-current={on ? 'page' : undefined}
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

        <div className="mt-auto flex flex-col items-center gap-2">
          {/* P5 (revue Vic n°3) — l'ancien badge cryptique « J-2 » devient une entrée « Sources »
              claire : même fonction (fraîcheur des données → page Sources), libellé explicite. */}
          <button
            onClick={() => openSources()}
            className="group flex w-full flex-col items-center gap-1"
            title="Fraîcheur des données — sources et mises à jour"
          >
            <span
              className={`flex h-10 w-10 items-center justify-center rounded-[10px] border transition-colors ${
                view === 'sources' ? 'border-[#2E6B4F] bg-[#0F1A14] text-mint' : 'border-transparent text-txt-mut group-hover:text-txt'
              }`}
            >
              <svg viewBox="0 0 20 20" className="h-5 w-5">{SOURCES_ICON}</svg>
            </span>
            <span className={`text-[10.5px] ${view === 'sources' ? 'text-mint' : 'text-txt-mut'}`}>Sources</span>
          </button>
          {/* B7 (mandat calculette) : la pastille « VL » du rail DOUBLAIT l'avatar déjà présent
              dans le header — retirée pour libérer de l'espace vertical (au profit des filtres).
              Aucune fonction unique n'y était attachée (statique) ; l'identité reste au header. */}
        </div>
      </nav>

      {/* P3 — Tiroir Outils CURÉ : regroupé par intention métier, les outils phares mis en avant.
          Un promoteur voit d'abord ce qui lui fait dire « je paie », pas 16 cases identiques. */}
      {outilsOpen && (
        <aside className="flex h-full w-[320px] shrink-0 flex-col border-r border-line bg-surface-1">
          <div className="shrink-0 px-5 pb-2 pt-5">
            <h2 className="text-sm font-medium text-txt-hi">Outils</h2>
            <p className="mt-0.5 text-[11px] leading-snug text-txt-dim">
              Les moteurs métier de LABUSE — <span style={{ color: VIOLET }}>★</span> = les plus utilisés.
            </p>
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-5 pb-5">
            {GROUPS.map((g) => {
              const outils = MODULES.filter((m) => m.group === g.key)
              if (!outils.length) return null
              return (
                <section key={g.key} data-outil-group={g.key}>
                  <div className="mb-2 flex items-baseline justify-between">
                    <p className="font-mono text-[10.5px] font-medium uppercase tracking-widest text-txt-mut">{g.label}</p>
                    <p className="text-[11px] text-txt-dim">{g.hint}</p>
                  </div>
                  <div className="flex flex-col gap-1.5">
                    {outils.map((m) => (
                      <OutilCard key={m.key} m={m} phare={!!m.phare} open={setModule} />
                    ))}
                  </div>
                </section>
              )
            })}
          </div>
        </aside>
      )}
    </>
  )
}
