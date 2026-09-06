/**
 * ÉTUDE DE ZONE · Z3 — « Autour de cette parcelle » (maquette, écran 1).
 *
 * Tiroir automatique de la fiche : la zone atteignable (isochrone IGN) depuis le centroïde, segmentée
 * « À pied · 15 min / Voiture · 5 min ». Qui vit dans la zone (Filosofi) + équipements les plus proches
 * AVEC leur temps. L'isochrone se dessine sur la carte EXISTANTE (module-extra, comme le Radar) et se
 * retire à la fermeture du tiroir (le composant ne se monte que quand le tiroir est ouvert).
 *
 * Honnêteté (mandat) : revenu = valeur au centroïde servie par la fiche (source unique, jamais deux
 * revenus divergents) ; « hors trafic » à chaque temps ; échec isochrone → message nommé, jamais un
 * cercle inventé ; zone inhabitée → dit dignement.
 */
import { useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'

import { getParcelleZone } from '../../lib/api'
import type { ParcelleZone } from '../../lib/types'
import { useApp } from '../../store/useApp'
import { GroupLabel, FactRow, FactNote, Rappel, StepProv } from './primitives'

const SEGMENTS = [
  { mode: 'pied' as const, minutes: 15, label: 'À pied · 15 min' },
  { mode: 'voiture' as const, minutes: 5, label: 'Voiture · 5 min' },
]

function nombre(n: number | null | undefined): string {
  return n == null ? '—' : n.toLocaleString('fr-FR')
}

function tempsLabel(min: number | null, mode: 'pied' | 'voiture'): string {
  if (min == null) return 'dans la zone'
  return `${min} min ${mode === 'pied' ? 'à pied' : 'en voiture'}`
}

export function AutourZoneBlock({ idu }: { idu: string }) {
  // segment courant (persisté dans le store d'app pour ne pas se réinitialiser au re-render du tiroir)
  const seg = useApp((s) => s.zoneSeg)
  const setZoneSeg = useApp((s) => s.setZoneSeg)
  const setModuleMap = useApp((s) => s.setModuleMap)
  const cur = SEGMENTS[seg] ?? SEGMENTS[0]

  const q = useQuery<ParcelleZone>({
    queryKey: ['parcelle-zone', idu, cur.mode, cur.minutes],
    queryFn: () => getParcelleZone(idu, cur.mode, cur.minutes),
    staleTime: 5 * 60_000,
  })
  const data = q.data

  // dessine l'isochrone sur la carte partagée (module-extra) ; retirée quand le tiroir se ferme.
  const feature = useMemo(() => {
    if (!data?.disponible || !data.geom) return null
    return { type: 'Feature' as const, geometry: data.geom, properties: { kind: 'zone-iso' } }
  }, [data])
  useEffect(() => {
    if (!feature) return
    setModuleMap({ idus: [idu], extra: { type: 'FeatureCollection', features: [feature] } })
    return () => setModuleMap({ idus: [], extra: null })
  }, [feature, idu, setModuleMap])

  return (
    <div data-autour-zone className="flex flex-col gap-3">
      {/* segment à pied / voiture — le contrôle segmenté (.seg) reste. */}
      <div className="flex gap-1 rounded-lg border border-line-2 bg-surface-2 p-0.5">
        {SEGMENTS.map((s, i) => (
          <button key={s.mode} onClick={() => setZoneSeg(i)}
            className={`flex-1 rounded-md px-2 py-1 text-[11px] font-medium transition-colors duration-quick ${
              i === seg ? 'bg-mint/15 text-txt-hi' : 'text-txt-mut hover:text-txt'}`}>
            {s.label}
          </button>
        ))}
      </div>

      {q.isLoading && <p className="text-xs text-txt-dim">Calcul de la zone atteignable…</p>}

      {/* échec isochrone → dégradé honnête et NOMMÉ (jamais un cercle substitué). Z3 la boîte → note. */}
      {data && !data.disponible && (
        <FactNote>
          <span data-zone-indisponible>
            Zone atteignable indisponible — {data.detail ?? 'le service d’isochrones IGN n’a pas répondu'}.
            <span className="text-txt-dim"> Aucun cercle approximatif n’est affiché à la place.</span>
          </span>
        </FactNote>
      )}

      {data?.disponible && (
        <>
          {/* QUI VIT DANS LA ZONE — Z1·02 sous-titre → kicker ; Z1·03 les stats numériques → FactRow. */}
          <div>
            <GroupLabel>Qui vit dans la zone</GroupLabel>
            {data.population?.inhabitee ? (
              <p className="text-[11px] text-txt-mut">Zone peu ou pas habitée — aucun carreau INSEE peuplé ici.</p>
            ) : (
              <div>
                <FactRow label="habitants" value={nombre(data.population?.habitants)} />
                <FactRow label="ménages" value={nombre(data.population?.menages)} />
                {/* RETOURS-11F4 F9 — le badge « estimé » ne s'affiche QUE si le revenu est IMPUTÉ ;
                    un carreau INSEE Filosofi réel est Sourcé, jamais « estimé ». */}
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

          {/* ÉQUIPEMENTS & COMMERCES — avec leur temps. Z1·02 sous-titre → kicker. */}
          {data.equipements && data.equipements.length > 0 && (
            <div>
              <GroupLabel>Équipements &amp; commerces</GroupLabel>
              <div className="mt-1 flex flex-col gap-1">
                {data.equipements.map((e, i) => (
                  <div key={i} className="flex items-center justify-between gap-2 text-[11.5px]">
                    <span className="truncate text-txt">
                      {e.domaine} <span className="text-txt-mut">— {e.nom}</span>
                    </span>
                    <span className="shrink-0 font-mono text-[11px] text-txt-hi">{tempsLabel(e.temps_min, data.mode)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* renvoi (zéro doublon) → Rappel + note de sources → FactNote. */}
          <Rappel>{data.renvoi}</Rappel>
          <FactNote>{data.note}</FactNote>
        </>
      )}
    </div>
  )
}
