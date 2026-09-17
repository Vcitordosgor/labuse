// COUCHES-RECETTE-2 Lot B (B2) — LE composant de ligne de couche, PARTAGÉ entre l'ancienne liste
// (LeftPanel/LayerRow) et les couches du tuyau (CouchesTuyau/NouvellesCouches). Même case à cocher
// (13 px + coche), même libellé, même « i » (Tip au survol immédiat, sans curseur « ? »), même
// espacement → DA indiscernable, jamais une imitation.
import { Tip } from '../Tip'

// Le « i » : une pastille ronde ; le Tip s'affiche AU SURVOL immédiat (hoverDelayMs défaut 0),
// curseur normal (aucun « ? »). Clic sur la pastille ne bascule pas la couche (stopPropagation du Tip).
export function LayerInfoPill({ info }: { info: string }) {
  if (!info) return null
  return (
    <Tip garder side="top" tip={info} className="shrink-0">
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

// Une ligne de couche. `sub` : indentée (sous-option). `err` : échec de tuile signalé sur la ligne.
export function LayerRowUI({ on, label, info, onToggle, sub, dataKey, err }: {
  on: boolean
  label: string
  info?: string
  onToggle: () => void
  sub?: boolean
  dataKey?: string
  err?: boolean
}) {
  return (
    <div className={`flex items-center justify-between gap-2 px-3 py-2.5 ${sub ? 'pl-8' : ''}`}>
      <button
        data-layer={dataKey}
        data-layer-sub={sub ? true : undefined}
        onClick={onToggle}
        className="flex min-h-[24px] flex-1 items-center gap-3 text-left transition-colors duration-quick"
      >
        {sub && <span aria-hidden className="-ml-3 mr-0.5 text-[10px] leading-none text-txt-dim">↳</span>}
        <span className={`flex h-[13px] w-[13px] shrink-0 items-center justify-center rounded-[3px] ${on ? 'bg-mint' : 'border border-line-3'}`}>
          {on && (
            <svg viewBox="0 0 10 10" className="h-2.5 w-2.5">
              <polyline points="2,5.5 4,7.5 8,3" fill="none" stroke="#06301A" strokeWidth="1.8" />
            </svg>
          )}
        </span>
        <span className={`${sub ? 'text-[11px]' : 'text-xs'} ${on ? 'text-txt-hi' : 'text-[#97A39B]'}`}>
          {label}
          {err && <span className="ml-2 text-[10px] font-medium text-danger">tuile en échec</span>}
        </span>
      </button>
      <LayerInfoPill info={info ?? ''} />
    </div>
  )
}
