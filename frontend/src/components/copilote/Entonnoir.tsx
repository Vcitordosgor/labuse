// M26-B — l'entonnoir, dans ses deux vies : final (recap d'assemblage) et EN COURS
// (étages remplis au fil des step_completed, les suivants en attente — règle 5 : jamais
// un compteur inventé). Chaque n porte l'étiquette FOURNIE par le back (règle 1). Le
// badge de calibrage suit la formulation imposée du mandat ; la requalification
// (garde-fou) est TOUJOURS visible en clair, jamais repliée (règle 3).
import { fmtInt } from '../../lib/format'
import { CLIENT } from '../../lib/strings'
import { Badge } from './ui'

const S = CLIENT.copilote.entonnoir

export interface EtageAffiche { etape: string; n: number | null; etiquette?: string | null }

export function Entonnoir({ etages, communes, dureeMs, exhaustif, calibrage, requalification, enCours }: {
  etages: EtageAffiche[]
  communes: string[] | null
  dureeMs?: number | null
  /** null/undefined = badge non affichable (run en cours) */
  exhaustif?: boolean | null
  calibrage?: Record<string, string> | null
  requalification?: string | null
  enCours?: boolean
}) {
  const calibre = calibrage != null && Object.keys(calibrage).length > 0
    && Object.values(calibrage).every((m) => m === 'article_plu')
  return (
    <div data-entonnoir className="rounded-2xl border border-cp-line bg-cp-card px-6 py-5">
      <div className="mb-4 flex flex-wrap items-center gap-2.5 font-display text-[9.5px] uppercase tracking-[.2em] text-cp-faint">
        {enCours ? S.capEnCours : S.cap}
        {communes?.length ? <span>· {communes.join(', ')}</span> : null}
        {dureeMs != null && <span>· {Math.round(dureeMs / 1000)} s</span>}
        {exhaustif != null && (
          <Badge ton={exhaustif ? 'mint' : 'ambre'} data="exhaustivite">
            {exhaustif ? S.badgeExhaustif : S.badgePartiel}
          </Badge>
        )}
        {calibrage != null && (
          <Badge ton={calibre ? 'mint' : 'ambre'} data="calibrage">
            {calibre ? S.badgeCalibre : S.badgeGenerique}
          </Badge>
        )}
      </div>
      {/* règle 3 : le garde-fou a mordu → requalification INTÉGRALE, jamais dans un repli */}
      {requalification && (
        <p data-requalification
          className="mb-4 rounded-xl border border-cp-amber/30 bg-cp-amber/10 px-3.5 py-2.5 text-[11.5px] leading-relaxed text-cp-amber">
          {requalification}
        </p>
      )}
      <div className="relative mx-[5%] mb-4 h-0.5 rounded bg-cp-line2">
        <div className="absolute inset-0 rounded bg-gradient-to-r from-cp-faint to-cp-mint" />
        {etages.map((e, i) => (
          <i key={e.etape}
            className={`absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full ${
              e.n == null || i === 0 ? 'h-2 w-2 bg-cp-faint'
              : i === etages.length - 1 ? 'h-[11px] w-[11px] bg-cp-mint shadow-[0_0_10px_rgba(99,242,184,.35)]'
              : 'h-2 w-2 bg-cp-mint shadow-[0_0_10px_rgba(99,242,184,.35)]'}`}
            style={{ left: `${(i / (etages.length - 1)) * 100}%` }} />
        ))}
      </div>
      <div className="grid gap-1.5 text-center"
        style={{ gridTemplateColumns: `repeat(${etages.length}, minmax(0, 1fr))` }}>
        {etages.map((e, i) => (
          <div key={e.etape} data-etage={e.etape} data-etage-atteint={e.n != null ? '1' : undefined}
            className={e.n == null ? 'opacity-40' : ''}>
            <div className={`font-display text-[25px] font-bold tabular-nums tracking-tight ${
              e.n == null ? 'text-cp-faint'
              : i === etages.length - 1 ? 'text-cp-mint' : 'text-cp-txt'}`}>
              {e.n == null ? S.enAttenteEtage : fmtInt(e.n)}
            </div>
            <div className={`mt-0.5 text-[10px] leading-tight ${
              e.n != null && i === etages.length - 1 ? 'text-cp-mint/75' : 'text-cp-faint'}`}>
              {S.etages[e.etape] ?? e.etape}
            </div>
            {/* l'étiquette de l'étage, telle que fournie (règle 1 — chaîne libre du back) */}
            {e.etiquette && (
              <div data-etage-etiquette className="mt-0.5 text-[8.5px] leading-tight text-cp-faint/80">
                {e.etiquette}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
