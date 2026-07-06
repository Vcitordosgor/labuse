import { useState } from 'react'

type Zone = 'ia' | 'cartes' | 'outils' | 'crm'

const ICON: Record<Zone, JSX.Element> = {
  ia: (
    <path d="M4 9 Q7 5 10 8 Q13 5 16 9" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
  ),
  cartes: (
    <>
      <polygon points="10,3 17,7 10,11 3,7" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <polygon points="10,9 17,13 10,17 3,13" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.55" />
    </>
  ),
  outils: (
    <>
      <circle cx="10" cy="6" r="2.4" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <line x1="7.5" y1="17" x2="9.2" y2="8.2" stroke="currentColor" strokeWidth="1.6" />
      <line x1="12.5" y1="17" x2="10.8" y2="8.2" stroke="currentColor" strokeWidth="1.6" />
    </>
  ),
  crm: (
    <>
      <rect x="3" y="9" width="3.4" height="8" fill="currentColor" />
      <rect x="8.3" y="5" width="3.4" height="12" fill="currentColor" />
      <rect x="13.6" y="11" width="3.4" height="6" fill="currentColor" />
    </>
  ),
}

const LABEL: Record<Zone, string> = { ia: 'IA', cartes: 'Cartes', outils: 'Outils', crm: 'CRM' }

export function Rail() {
  const [active, setActive] = useState<Zone>('cartes')
  return (
    <>
      <nav className="flex h-full w-16 shrink-0 flex-col items-center border-r border-line bg-surface-1 py-4">
        {(['ia', 'cartes', 'outils', 'crm'] as Zone[]).map((z) => {
          const on = active === z
          return (
            <button
              key={z}
              onClick={() => setActive(z)}
              className="group mb-5 flex w-full flex-col items-center gap-1"
              title={LABEL[z]}
            >
              <span
                className={`flex h-10 w-10 items-center justify-center rounded-[10px] border ${
                  on ? 'border-[#2E6B4F] bg-[#0F1A14] text-mint' : 'border-transparent text-txt-mut group-hover:text-txt'
                }`}
              >
                <svg viewBox="0 0 20 20" className="h-5 w-5">{ICON[z]}</svg>
              </span>
              <span className={`text-[11px] ${on ? 'text-mint' : 'text-txt-mut'}`}>{LABEL[z]}</span>
            </button>
          )
        })}
        <div className="mt-auto flex flex-col items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-mint" />
          <span className="font-mono text-[11px] text-txt-mut" title="Données à J-2">J-2</span>
          <span className="mt-3 flex h-7 w-7 items-center justify-center rounded-full border border-line-2 bg-surface-3 font-mono text-[11px] text-mint">
            VL
          </span>
        </div>
      </nav>
      {active === 'outils' && (
        <aside className="flex h-full w-[300px] shrink-0 flex-col border-r border-line bg-surface-1 p-5">
          <h2 className="text-sm font-medium text-txt-hi">Outils</h2>
          <p className="mt-1 font-mono text-[11px] tracking-widest text-txt-dim">MODULES</p>
          <div className="mt-6 flex flex-1 items-center justify-center rounded-xl border border-dashed border-line-2 text-center text-xs text-txt-dim">
            Aucun module actif.<br />Les outils d'analyse arriveront ici.
          </div>
        </aside>
      )}
    </>
  )
}
