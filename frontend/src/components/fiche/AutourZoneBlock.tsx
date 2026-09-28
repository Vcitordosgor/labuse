/**
 * ÉTUDE DE ZONE · Z3 — « Autour de cette parcelle » (maquette, écran 1).
 *
 * FICHE-FIX-5 (reste 1) — la fiche est ALIGNÉE sur l'outil Étude de zone : l'ampleur est un RAYON
 * en km (0,5 / 1 / 2 / 5 km, défaut 1 km), aux MÊMES valeurs, libellés et SOURCE que l'outil
 * (endpoint `/outils/etude-zone`, POST). Plus de « À pied 15 min / Voiture 5 min » : la fiche et
 * l'outil disent exactement la même chose. Le cercle se dessine sur la carte partagée (module-extra)
 * et se retire à la fermeture du tiroir.
 *
 * Honnêteté (mandat) : revenu = valeur servie (Filosofi) ; échec zone → message nommé, jamais un
 * cercle inventé ; zone inhabitée → dit dignement.
 */
import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { etudeZone } from '../../lib/api'
import type { EtudeZoneResult } from '../../lib/types'
import { useApp } from '../../store/useApp'
import { GroupLabel, FactRow, FactNote, StepProv } from './primitives'

// RETOURS-15 B9 — l'ampleur de l'outil : rayon en km. Même tableau, mêmes libellés que EtudeZone.
const RAYONS = [0.5, 1, 2, 5]

function nombre(n: number | null | undefined): string {
  return n == null ? '—' : n.toLocaleString('fr-FR')
}
const kmLabel = (r: number) => `${String(r).replace('.', ',')} km`

export function AutourZoneBlock({ idu }: { idu: string }) {
  const [seg, setSeg] = useState(1)   // défaut 1 km, comme l'outil
  const setModuleMap = useApp((s) => s.setModuleMap)
  const rayonKm = RAYONS[seg] ?? 1

  const q = useQuery<EtudeZoneResult>({
    queryKey: ['etude-zone-fiche', idu, rayonKm],
    queryFn: () => etudeZone({ idu, rayon_km: rayonKm, minutes: 10, mode: 'voiture' }),
    staleTime: 5 * 60_000,
  })
  const data = q.data

  // dessine le cercle de rayon sur la carte partagée (module-extra) ; retiré à la fermeture du tiroir.
  const feature = useMemo(() => {
    if (!data?.zone_disponible || !data.geom) return null
    return { type: 'Feature' as const, geometry: data.geom, properties: { kind: 'zone-iso' } }
  }, [data])
  useEffect(() => {
    if (!feature) return
    setModuleMap({ idus: [idu], extra: { type: 'FeatureCollection', features: [feature] } })
    return () => setModuleMap({ idus: [], extra: null })
  }, [feature, idu, setModuleMap])

  return (
    <div data-autour-zone className="flex flex-col gap-3">
      {/* AMPLEUR — rayon en km (mêmes valeurs et libellés que l'outil Étude de zone). */}
      <div data-zone-rayons className="flex gap-1 rounded-lg border border-line-2 bg-surface-2 p-0.5">
        {RAYONS.map((r, i) => (
          <button key={r} data-zone-rayon={r} onClick={() => setSeg(i)}
            className={`flex-1 rounded-md px-2 py-1 text-[11px] font-medium transition-colors duration-quick ${
              i === seg ? 'bg-mint/15 text-txt-hi' : 'text-txt-mut hover:text-txt'}`}>
            {kmLabel(r)}
          </button>
        ))}
      </div>

      {q.isLoading && <p className="text-xs text-txt-dim">Lecture de la zone…</p>}

      {/* échec → dégradé honnête et NOMMÉ (jamais un cercle substitué). */}
      {data && !data.zone_disponible && (
        <FactNote>
          <span data-zone-indisponible>
            Zone atteignable indisponible — {data.detail ?? 'le service n’a pas répondu'}.
          </span>
        </FactNote>
      )}

      {data?.zone_disponible && (
        <>
          {/* QUI VIT DANS LA ZONE — mêmes chiffres, même source (Filosofi) que l'outil. */}
          <div>
            <GroupLabel>Qui vit dans la zone</GroupLabel>
            {data.population?.inhabitee ? (
              <p className="text-[11px] text-txt-mut">Zone peu ou pas habitée — aucun carreau INSEE peuplé ici.</p>
            ) : (
              <div>
                <FactRow label="habitants" value={nombre(data.population?.habitants)} />
                <FactRow label="ménages" value={nombre(data.population?.menages)} />
                <FactRow
                  label={data.population?.revenu_majorite_imputee
                    ? `revenu médian / an · valeur approchée (${nombre(data.population.revenu_impute_n)}/${nombre(data.population.revenu_carreaux_n)} carreaux)`
                    : 'revenu médian / an'}
                  value={data.population?.revenu_median_eur != null ? <>{nombre(data.population.revenu_median_eur)} <small>€</small></> : '—'}
                  src={data.population?.revenu_majorite_imputee ? <StepProv prov="estimee" /> : <StepProv prov="sourcee" />} />
                <FactRow label="moins de 25 ans" value={data.population?.pct_moins_25 != null ? <>{data.population.pct_moins_25} <small>%</small></> : '—'} />
              </div>
            )}
          </div>

          {/* ÉQUIPEMENTS & COMMERCES dans le rayon (plus de temps à pied/voiture). */}
          {data.equipements && data.equipements.length > 0 && (
            <div>
              <GroupLabel>Équipements &amp; commerces</GroupLabel>
              <div className="mt-1 flex flex-col gap-1">
                {data.equipements.map((e, i) => (
                  <div key={i} className="flex items-center justify-between gap-2 text-[11.5px]">
                    <span className="truncate text-txt">
                      {e.domaine} <span className="text-txt-mut">— {e.nom}</span>
                    </span>
                    {e.temps_min != null && <span className="shrink-0 font-mono text-[11px] text-txt-hi">{e.temps_min} min</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          <FactNote>Zone atteignable dans un rayon de {kmLabel(rayonKm)} — même lecture que l'outil Étude de zone (Filosofi · BPE · isochrones IGN).</FactNote>
        </>
      )}
    </div>
  )
}
