// M78 · 2c — « COMPRIS : » les critères DÉDUITS, en chips éditables, adossés aux facettes RÉELLES.
// La traduction est VISIBLE (« 6 logements » → « SDP ≥ 420 m² »). Un critère non traduisible est DIT,
// jamais ignoré en silence (les 3 gaps : proximité, risque en recherche, déjà en vente — BACKLOG).
// Retirer une chip (✕) relance l'instruction avec les critères corrigés ; « + » rouvre la barre.
import { fmtEurCompact, fmtM2 } from '../../lib/format'

type Chip = { cle: string; label: string; traduction?: string }

/** Chips traduites depuis brief_json (payload de l'interpréteur, jamais inventé). */
function chipsDepuis(bj: Record<string, unknown>): Chip[] {
  const out: Chip[] = []
  const communes = (bj.communes as string[] | undefined) ?? []
  for (const c of communes) out.push({ cle: `commune:${c}`, label: c })
  const prog = bj.programme as { logements?: number; sdp_cible_m2?: number } | undefined
  if (prog?.logements != null)
    out.push({ cle: 'programme', label: `${prog.logements} logements`,
               traduction: prog.sdp_cible_m2 != null ? `SDP cible ≥ ${fmtM2(prog.sdp_cible_m2)}` : undefined })
  const smin = bj.surface_min_m2 as number | null | undefined
  if (smin != null) out.push({ cle: 'surface_min', label: `≥ ${fmtM2(smin)}` })
  const budget = bj.budget_max_eur as number | null | undefined
  if (budget != null) out.push({ cle: 'budget', label: `budget ≤ ${fmtEurCompact(budget)}` })
  const c = (bj.contraintes as Record<string, unknown> | undefined) ?? {}
  const zones = (c.zones as string[] | undefined) ?? []
  if (zones.length) out.push({ cle: 'zones', label: `zones ${zones.join(' · ')}` })
  if (c.exclure_ppr_rouge) out.push({ cle: 'ppr', label: 'hors PPR rouge' })
  if (c.exclure_abf) out.push({ cle: 'abf', label: 'hors ABF' })
  return out
}

/** Brief reconstruit depuis brief_json, en OMETTANT éventuellement une chip (pour la relance). */
export function briefDepuisJson(bj: Record<string, unknown>, sansCle?: string): string {
  const chips = chipsDepuis(bj).filter((ch) => ch.cle !== sansCle)
  const lieux = chips.filter((ch) => ch.cle.startsWith('commune:')).map((ch) => ch.label)
  const reste = chips.filter((ch) => !ch.cle.startsWith('commune:')).map((ch) => ch.label)
  return [reste.join(', '), lieux.length ? `à ${lieux.join(', ')}` : ''].filter(Boolean).join(' ')
}

export function ChipsCompris({ briefJson, onRelancer, onCorriger, enCours }: {
  briefJson: Record<string, unknown>
  onRelancer: (brief: string) => void      // ✕ sur une chip → relance avec les critères corrigés
  onCorriger: (brief: string) => void      // « + » / Corriger → rouvre la barre pré-remplie
  enCours?: boolean                         // instruction en cours → la modif annule + relance (§2d)
}) {
  const chips = chipsDepuis(briefJson)
  const nonAppliques = (briefJson.criteres_non_appliques as string[] | undefined) ?? []
  if (!chips.length && !nonAppliques.length) return null
  return (
    <div data-chips-compris className="mb-4 rounded-2xl border border-cp-line bg-cp-card px-5 py-3.5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-[10px] tracking-[.16em] text-cp-muted">COMPRIS
          {enCours && <span className="ml-1.5 text-cp-faint normal-case tracking-normal">· modifier relance l'instruction</span>} :</span>
        {chips.map((ch) => (
          <span key={ch.cle} data-chip={ch.cle}
            className="group inline-flex items-center gap-1.5 rounded-lg border border-cp-ia/25 bg-cp-ia/[0.07] px-2.5 py-1 text-[11.5px] text-cp-txt">
            {ch.label}
            {ch.traduction && <span data-chip-traduction className="text-cp-faint" title="Traduction appliquée par le moteur">→ {ch.traduction}</span>}
            <button data-chip-retirer aria-label={`Retirer ${ch.label}`}
              onClick={() => onRelancer(briefDepuisJson(briefJson, ch.cle))}
              className="ml-0.5 text-cp-faint opacity-60 hover:text-cp-txt hover:opacity-100">✕</button>
          </span>
        ))}
        {/* les 3 gaps (proximité, risque en recherche, déjà en vente) : DITS, jamais promis */}
        {nonAppliques.map((c) => (
          <span key={c} data-chip-non-applique
            className="inline-flex items-center gap-1.5 rounded-lg border border-cp-amber/30 bg-cp-amber/[0.08] px-2.5 py-1 text-[11.5px] text-cp-amber"
            title="Critère que le moteur ne sait pas appliquer — dit, jamais ignoré">
            « {c} » non applicable
          </span>
        ))}
        <button data-chip-ajouter onClick={() => onCorriger(briefDepuisJson(briefJson))}
          className="rounded-lg border border-dashed border-cp-line2 px-2.5 py-1 text-[11.5px] text-cp-muted hover:border-cp-ia/40 hover:text-cp-txt">
          + corriger
        </button>
      </div>
    </div>
  )
}
