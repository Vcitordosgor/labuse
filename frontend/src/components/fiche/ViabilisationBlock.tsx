/**
 * M-VIA lot 2 — Bloc « Viabilisation » (indicateur par FAISCEAU DE PREUVES).
 *
 * INDICATEUR de probabilité, JAMAIS une certitude ni un verrou de constructibilité.
 * Aucun tracé de réseau (donnée sensible). Contributions tracées « comme le bloc P v2 » :
 * la fiche dit POURQUOI (permis < 100 m, façade voie urbanisée, bâti mitoyen, zone).
 * Coût de raccordement QUALITATIF (Lot 3). Note PV S3REnR au niveau île (Lot 2.5).
 * Additif : rendu depuis la charge utile de la fiche (aucun fetch).
 */
import { TOKENS } from '../../lib/tokens'
import type { Viabilisation } from '../../lib/types'
import { Tip } from '../Tip'

const BAND_META: Record<Viabilisation['band'], { color: string; bg: string }> = {
  confirmee:  { color: TOKENS.viabConfirmee, bg: TOKENS.viabConfirmeeBg },
  probable:   { color: TOKENS.viabProbable, bg: TOKENS.viabProbableBg },
  incertaine: { color: TOKENS.viabIncertaine, bg: TOKENS.viabIncertaineBg },
  lourde:     { color: TOKENS.viabLourde, bg: TOKENS.viabLourdeBg },
}

export function ViabilisationBlock({ via }: { via: Viabilisation }) {
  const m = BAND_META[via.band] ?? BAND_META.incertaine
  return (
    <div data-viabilisation className="card-elev px-3 py-2.5">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-txt-hi">Viabilisation (eau · assainissement · élec)</span>
        <span className="ml-auto rounded-full px-2 py-0.5 text-[10.5px] font-semibold"
          style={{ backgroundColor: m.bg, color: m.color }}>{via.libelle}</span>
      </div>

      <div className="mt-2 flex items-baseline gap-3">
        <span className="font-mono text-xl font-semibold" style={{ color: m.color }}>{via.score}</span>
        <span className="text-[11px] text-txt-dim">/ 100 — probabilité de viabilisation (faisceau de preuves)</span>
      </div>

      {/* Barre du score */}
      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-line-2">
        <div className="h-full rounded-full" style={{ width: `${via.score}%`, background: m.color }} />
      </div>

      <p className="label-caps mt-2">Pourquoi cet indicateur</p>
      <ul className="mt-1 flex flex-col gap-0.5">
        {via.contributions.map((c, i) => (
          <li key={i} className="flex items-baseline gap-2 text-[11.5px]">
            <span className={`w-9 shrink-0 text-right font-mono font-semibold ${
              c.signe === '+' ? 'text-st-chaude' : c.signe === '−' ? 'text-st-ecartee' : 'text-txt-mut'}`}>
              {c.points > 0 ? `+${c.points}` : c.signe}
            </span>
            <span className="text-txt">
              <b className="font-medium text-txt-hi">{c.libelle}</b>
              <span className="text-txt-dim"> — {c.detail}</span>
            </span>
          </li>
        ))}
      </ul>

      {/* Lot 3 — coût de raccordement qualitatif */}
      <div className="mt-2.5 rounded-lg bg-surface-3 px-2.5 py-2">
        <p className="label-caps">Raccordement (qualitatif)</p>
        <p className="mt-1 text-[11.5px] leading-snug text-txt">{via.cout_raccordement.niveau}</p>
        <p className="mt-1 text-[11px] leading-snug text-txt-dim">{via.cout_raccordement.assainissement}</p>
      </div>

      {/* Lot 2.5 — note PV S3REnR (niveau île, volet photovoltaïque) */}
      {via.elec_pv && (
        <p className="mt-2 flex items-start gap-1.5 text-[11px] leading-snug text-txt-dim">
          <span aria-hidden className="text-st-creuser">↯</span>
          {via.elec_pv.source
            ? <Tip tip={via.elec_pv.source}><span>{via.elec_pv.note}</span></Tip>
            : <span>{via.elec_pv.note}</span>}
        </p>
      )}

      <p className="mt-2 text-[10.5px] leading-snug text-txt-dim">{via.disclaimer}</p>
    </div>
  )
}
