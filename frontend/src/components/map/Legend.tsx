import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { CINQUANTE_PAS_COLOR, EQUIP_META, LEGEND_ORDER, LEGEND_V2_ORDER, STATUT_META, TIER_V2_META, ZONE_FAM_META, ZONE_FAM_ORDER } from '../../lib/status'
import { useApp } from '../../store/useApp'
import { Tip } from '../Tip'

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
 *  légende flottante recouvrait le hero (item 1 UX V1) → elle vit dans le tiroir « Couches ».
 *
 *  M12 C6/C7 — UN SEUL panneau, plusieurs sections EMPILÉES (jamais superposées) :
 *   • Verdict (C7) : REPLIÉ PAR DÉFAUT, dépliable au clic (jamais supprimé — décision Vic) ;
 *   • Zonage PLU : visible dès qu'une des deux couches de colorisation est active ;
 *   • 50 pas géométriques ; Équipements (rapatriés de leur bloc flottant qui masquait le verdict).
 *  Le panneau est borné en hauteur et défile : les sections cohabitent sans déborder l'écran. */
export function Legend({ inline = false }: { inline?: boolean }) {
  const layers = useApp((s) => s.layers)
  const v2 = useV2Actif()
  // C7 : verdict REPLIÉ par défaut (libère la carte) — l'utilisateur le déplie s'il en a besoin.
  const [verdictOpen, setVerdictOpen] = useState(false)
  const zonageOn = layers.zonage_parcelle || layers.zonage_colorise

  return (
    <div className={`${inline
      ? 'rounded-xl bg-surface-2 px-4 py-3'
      : 'floating absolute bottom-4 right-4 hidden max-h-[60vh] overflow-y-auto px-4 py-3 sm:block'}`}>
      {/* ── Verdict (repliable, replié par défaut) ── */}
      <button
        data-legend-verdict-toggle
        onClick={() => setVerdictOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 text-left"
        aria-expanded={verdictOpen}
        title={verdictOpen ? 'Replier la légende du verdict' : 'Déplier la légende du verdict'}
      >
        {/* R3 (PJ5) : sans run v2 la légende est celle de la MATRICE Q×A (vocabulaire « dossier »,
            non thermique) — le thermique est réservé au scoring P servi. */}
        {v2 ? (
          <span className="label-caps">Verdict · Scoring v2</span>
        ) : (
          <Tip block side="top" tip="Classement matrice Q×A (historique) — vocabulaire « dossier », distinct de l'échelle thermique du scoring P servi.">
            <span className="label-caps">Verdict · Matrice Q×A</span>
          </Tip>
        )}
        <span className={`text-txt-dim transition-transform duration-quick ${verdictOpen ? 'rotate-180' : ''}`} aria-hidden="true">⌄</span>
      </button>
      {verdictOpen && (
        <div className="mt-2 flex flex-col gap-1.5">
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
      )}

      {/* ── Zonage PLU par famille (C5) — dès que « par parcelle » OU « colorisation » est active ── */}
      {zonageOn && (
        <div data-legend-zonage className="mt-3 border-t border-line pt-2.5">
          <p className="label-caps mb-2">Zonage PLU (par type)</p>
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

      {/* ── 50 pas géométriques ── */}
      {layers.cinquante_pas && (
        <div className="mt-3 border-t border-line pt-2.5">
          <Tip block side="top" tip="Réserve des 50 pas géométriques — bande de 81,20 m depuis le rivage (spécifique outre-mer)">
            <div data-legend-50pas className="flex items-center gap-2">
              <span className="h-0.5 w-4 rounded" style={{ background: CINQUANTE_PAS_COLOR }} />
              <span className="text-[11px] text-txt">50 pas géométriques</span>
            </div>
          </Tip>
        </div>
      )}

      {/* ── Équipements (C6 : rapatriée dans le panneau unique, ne recouvre plus le verdict) ── */}
      {layers.equipements && (
        <div data-legend-equip className="mt-3 border-t border-line pt-2.5">
          <p className="label-caps mb-2">Équipements</p>
          <div className="flex flex-col gap-0.5 text-[11px]">
            {EQUIP_META.map((e) => (
              <span key={e.key} className="flex items-center gap-1.5 text-txt-mut">
                <span className="text-[13px] leading-none">{e.emoji}</span>{e.label}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
