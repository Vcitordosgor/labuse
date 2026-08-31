// RADAR-DEPOT-2 D2 — faits DÉCLARÉS dans l'annonce (zone PLU, COS/CES, drapeaux). Déclaratif VENDEUR,
// pas du calibré LABUSE — étiqueté « déclaré dans l'annonce », jamais confondu avec les faits sourcés.
// Aucun texte d'annonce n'est affiché, seulement des faits. Module PARTAGÉ (fiche client + instruction
// admin) — isolé ici pour ne pas rompre le lazy-load de RadarView (qui reste code-splitté par App).
import type { RadarDeclaratif } from '../../lib/api'

const DRAPEAUX_LBL: Record<string, string> = {
  a_renover: 'À rénover', a_demolir: 'Bâtisse à démolir', succession: 'Succession',
  lotissement: 'Lotissement', viabilise: 'Viabilisé',
}

export function Declaratif({ d }: { d: RadarDeclaratif }) {
  const flags = Object.entries(d.drapeaux).filter(([k, v]) => v === true && k in DRAPEAUX_LBL)
  const rien = !d.zone_plu.length && !d.cos_ces && d.emprise_sol_pct == null && !flags.length
  if (rien) return null
  return (
    <div data-radar-declaratif className="rounded-xl border border-line-2 bg-surface-2 px-3 py-2.5">
      <div className="mb-1.5 flex items-center gap-2">
        <span className="font-mono text-[10px] tracking-[0.2em] text-txt-mut">DÉCLARÉ DANS L’ANNONCE</span>
        <span className="rounded bg-surface-3 px-1.5 py-0.5 font-mono text-[9px] text-txt-dim">déclaratif vendeur</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {d.zone_plu.map((z) => (
          <span key={z} className="rounded-md border border-line-2 bg-surface-1 px-2 py-0.5 text-[11px] text-txt">Zone PLU {z}</span>
        ))}
        {d.cos_ces && <span className="rounded-md border border-line-2 bg-surface-1 px-2 py-0.5 text-[11px] text-txt">{d.cos_ces.type} {d.cos_ces.valeur}</span>}
        {d.emprise_sol_pct != null && <span className="rounded-md border border-line-2 bg-surface-1 px-2 py-0.5 text-[11px] text-txt">Emprise {d.emprise_sol_pct} %</span>}
        {flags.map(([k]) => (
          <span key={k} className="rounded-md border border-amber/30 bg-amber/[0.06] px-2 py-0.5 text-[11px] text-amber">
            {DRAPEAUX_LBL[k]}{k === 'lotissement' && d.drapeaux.lotissement_nom ? ` « ${d.drapeaux.lotissement_nom} »` : ''}
          </span>
        ))}
      </div>
    </div>
  )
}
