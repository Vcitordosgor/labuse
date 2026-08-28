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
      {/* segment à pied / voiture */}
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

      {/* échec isochrone → dégradé honnête et NOMMÉ (jamais un cercle substitué) */}
      {data && !data.disponible && (
        <div data-zone-indisponible className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px] leading-snug text-txt-mut">
          Zone atteignable indisponible — {data.detail ?? 'le service d’isochrones IGN n’a pas répondu'}.
          <span className="text-txt-dim"> Aucun cercle approximatif n’est affiché à la place.</span>
        </div>
      )}

      {data?.disponible && (
        <>
          {/* QUI VIT DANS LA ZONE — 4 stats */}
          <div>
            <div className="mb-1.5 font-mono text-[9.5px] uppercase tracking-[0.18em] text-txt-dim">Qui vit dans la zone</div>
            {data.population?.inhabitee ? (
              <p className="text-[11px] text-txt-mut">Zone peu ou pas habitée — aucun carreau INSEE peuplé ici.</p>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <Stat v={nombre(data.population?.habitants)} k="habitants" />
                <Stat v={nombre(data.population?.menages)} k="ménages" />
                <Stat v={data.population?.revenu_median_eur != null ? `${nombre(data.population.revenu_median_eur)} €` : '—'}
                  k={data.population?.revenu_majorite_imputee
                    ? `revenu médian / an · valeur approchée (${nombre(data.population.revenu_impute_n)}/${nombre(data.population.revenu_carreaux_n)} carreaux)`
                    : 'revenu médian / an'} est />
                <Stat v={data.population?.pct_moins_25 != null ? `${data.population.pct_moins_25} %` : '—'} k="moins de 25 ans" />
              </div>
            )}
          </div>

          {/* ÉQUIPEMENTS & COMMERCES — avec leur temps */}
          {data.equipements && data.equipements.length > 0 && (
            <div>
              <div className="mb-1.5 font-mono text-[9.5px] uppercase tracking-[0.18em] text-txt-dim">Équipements &amp; commerces</div>
              <div className="flex flex-col gap-1">
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

          {/* renvoi (zéro doublon) + note de sources */}
          <p className="rounded-lg border border-line bg-surface-2 px-3 py-2 text-[10.5px] leading-snug text-txt-dim">{data.renvoi}</p>
          <p className="text-[10px] leading-snug text-txt-dim">{data.note}</p>
        </>
      )}
    </div>
  )
}

function Stat({ v, k, est }: { v: string; k: string; est?: boolean }) {
  return (
    <div className="rounded-lg border border-line-2 bg-surface-2 px-2.5 py-2">
      <div className="flex items-center gap-1.5 text-[13px] font-semibold text-txt-hi">
        <span>{v}</span>
        {est && <span className="rounded bg-mint/12 px-1 py-px font-mono text-[8px] uppercase tracking-wide text-mint">estimé</span>}
      </div>
      <div className="mt-0.5 text-[10px] text-txt-mut">{k}</div>
    </div>
  )
}
