// M26-B — l'entonnoir : un étage par ligne du payload `entonnoir` (recap d'assemblage).
// Chaque n porte l'étiquette FOURNIE par le back (règle 1). Le badge de calibrage suit
// la formulation imposée du mandat ; la requalification (garde-fou) est TOUJOURS
// visible en clair, jamais repliée (règle 3).
import { fmtInt } from '../../lib/format'
import { CLIENT } from '../../lib/strings'
import type { RecapAssemblage } from '../../lib/copilote'
import { Badge } from './ui'

const S = CLIENT.copilote.entonnoir

export function Entonnoir({ recap, communes, dureeMs }: {
  recap: RecapAssemblage
  communes: string[] | null
  dureeMs: number | null
}) {
  const etages = recap.entonnoir
  const calibre = Object.keys(recap.calibrage).length > 0
    && Object.values(recap.calibrage).every((m) => m === 'article_plu')
  return (
    <div data-entonnoir className="rounded-2xl border border-cp-line bg-cp-card px-6 py-5">
      <div className="mb-4 flex flex-wrap items-center gap-2.5 font-display text-[9.5px] uppercase tracking-[.2em] text-cp-faint">
        {S.cap}
        {communes?.length ? <span>· {communes.join(', ')}</span> : null}
        {dureeMs != null && <span>· {Math.round(dureeMs / 1000)} s</span>}
        <Badge ton={recap.exhaustif ? 'mint' : 'ambre'} data="exhaustivite">
          {recap.exhaustif ? S.badgeExhaustif : S.badgePartiel}
        </Badge>
        <Badge ton={calibre ? 'mint' : 'ambre'} data="calibrage">
          {calibre ? S.badgeCalibre : S.badgeGenerique}
        </Badge>
      </div>
      {/* règle 3 : le garde-fou a mordu → requalification INTÉGRALE, jamais dans un repli */}
      {recap.requalification && (
        <p data-requalification
          className="mb-4 rounded-xl border border-cp-amber/30 bg-cp-amber/10 px-3.5 py-2.5 text-[11.5px] leading-relaxed text-cp-amber">
          {recap.requalification}
        </p>
      )}
      <div className="relative mx-[5%] mb-4 h-0.5 rounded bg-cp-line2">
        <div className="absolute inset-0 rounded bg-gradient-to-r from-cp-faint to-cp-mint" />
        {etages.map((e, i) => (
          <i key={e.etape}
            className={`absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full ${
              i === 0 ? 'h-2 w-2 bg-cp-faint'
              : i === etages.length - 1 ? 'h-[11px] w-[11px] bg-cp-mint shadow-[0_0_10px_rgba(99,242,184,.35)]'
              : 'h-2 w-2 bg-cp-mint shadow-[0_0_10px_rgba(99,242,184,.35)]'}`}
            style={{ left: `${(i / (etages.length - 1)) * 100}%` }} />
        ))}
      </div>
      <div className="grid gap-1.5 text-center"
        style={{ gridTemplateColumns: `repeat(${etages.length}, minmax(0, 1fr))` }}>
        {etages.map((e, i) => (
          <div key={e.etape} data-etage={e.etape}>
            <div className={`font-display text-[25px] font-bold tabular-nums tracking-tight ${
              i === etages.length - 1 ? 'text-cp-mint' : 'text-cp-txt'}`}>
              {fmtInt(e.n)}
            </div>
            <div className={`mt-0.5 text-[10px] leading-tight ${
              i === etages.length - 1 ? 'text-cp-mint/75' : 'text-cp-faint'}`}>
              {S.etages[e.etape] ?? e.etape}
            </div>
            {/* l'étiquette de l'étage, telle que fournie (règle 1 — chaîne libre du back) */}
            <div data-etage-etiquette className="mt-0.5 text-[8.5px] leading-tight text-cp-faint/80">
              {e.etiquette}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
