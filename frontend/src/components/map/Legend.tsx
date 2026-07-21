import { useQuery } from '@tanstack/react-query'
import { CINQUANTE_PAS_COLOR, LEGEND_ORDER, LEGEND_V2_ORDER, STATUT_META, TIER_V2_META, ZONE_FAM_META, ZONE_FAM_ORDER } from '../../lib/status'
import { useApp } from '../../store/useApp'

// Correctif M5 : quand un run scoring v2 existe, la carte colore par le tier v2 — la légende
// suit (mêmes couleurs que le verdict d'en-tête). Sans run (404/503), légende matrice legacy.
export function useV2Actif(): boolean {
  const q = useQuery({
    queryKey: ['v2-actif'],
    queryFn: async () => (await fetch('/v2/modele')).ok,
    retry: false, staleTime: Infinity,
  })
  return q.data === true
}

/** `inline` : rendu dans un flux (tiroir mobile) au lieu du coin de carte. Sous 640 px la
 *  légende flottante recouvrait le hero (item 1 UX V1) → elle vit dans le tiroir « Couches ». */
export function Legend({ inline = false }: { inline?: boolean }) {
  const layers = useApp((s) => s.layers)
  const v2 = useV2Actif()
  return (
    <div className={`rounded-[10px] border border-line-2 bg-surface-2 px-4 py-3 ${
      inline ? '' : 'absolute bottom-4 right-4 hidden sm:block'}`}>
      {/* R3 (PJ5) : sans run v2 la légende est celle de la MATRICE Q×A (vocabulaire « dossier »,
          non thermique) — le thermique est réservé au scoring P servi. */}
      <p className="mb-2 font-mono text-[11px] tracking-widest text-txt-dim"
        title={v2 ? undefined : 'Classement matrice Q×A (historique) — vocabulaire « dossier », distinct de l\'échelle thermique du scoring P servi.'}>
        {v2 ? 'VERDICT · SCORING V2' : 'VERDICT · MATRICE Q×A'}
      </p>
      <div className="flex flex-col gap-1.5">
        {v2
          ? LEGEND_V2_ORDER.map((t) => (
              <div key={t} className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full" style={{ background: TIER_V2_META[t].color }} />
                <span className="text-[11px] text-txt">{TIER_V2_META[t].label}</span>
              </div>
            ))
          : LEGEND_ORDER.map((s) => (
              <div key={s} className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full" style={{ background: STATUT_META[s].color }} />
                <span className="text-[11px] text-txt">{STATUT_META[s].label}</span>
              </div>
            ))}
      </div>
      {/* M6.1 item 1 : légende DÉDIÉE quand la couche « Zonage PLU (parcelles) » est active —
          la vignette verdict reste intacte au-dessus (deux lectures simultanées assumées). */}
      {layers.zonage_parcelle && (
        <div data-legend-zonage>
          <p className="mb-2 mt-3 font-mono text-[11px] tracking-widest text-txt-dim">ZONAGE PLU (PARCELLES)</p>
          <div className="flex flex-col gap-1.5">
            {ZONE_FAM_ORDER.map((f) => (
              <div key={f} className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full" style={{ background: ZONE_FAM_META[f].color }} />
                <span className="text-[11px] text-txt">{ZONE_FAM_META[f].label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {/* M6.1 item 2 : rappel visuel de la bande littorale quand la couche est active */}
      {layers.cinquante_pas && (
        <div data-legend-50pas className="mt-3 flex items-center gap-2"
          title="Réserve des 50 pas géométriques — bande de 81,20 m depuis le rivage (spécifique outre-mer)">
          <span className="h-0.5 w-4 rounded" style={{ background: CINQUANTE_PAS_COLOR }} />
          <span className="text-[11px] text-txt">50 pas géométriques</span>
        </div>
      )}
    </div>
  )
}
