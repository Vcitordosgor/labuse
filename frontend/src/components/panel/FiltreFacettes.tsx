// M120 — LE CADRAGE PROJET : les facettes de la carte (terrain + signaux) RÉUTILISÉES telles
// quelles — mêmes contrôles (ChipGroup / ZoneSelector / SignalChip / NumField), jamais une copie —
// branchées sur le binding fourni (le cadrage projet local, via FiltreProvider). Le compteur vivant
// est le MÊME endpoint que la carte (/filtre) : jamais un calcul client, jamais un faux positif.
import { useEffect, useState } from 'react'

import { getFiltreCount } from '../../lib/api'
import { countActiveFilters } from '../../lib/filters'
import { CLIENT } from '../../lib/strings'
import {
  ChipGroup, ETAT_SOL, NumField, SignalChip, SIGNAUX_KEYS, TitreSection, ZoneSelector,
} from './FiltreLabuse'
import { useFiltre } from './filtreContext'

const nf = new Intl.NumberFormat('fr-FR')

export function FiltreFacettes() {
  const { filters } = useFiltre()
  const nActifs = countActiveFilters(filters)
  const [live, setLive] = useState<number | null>(null)
  const [liveLoading, setLiveLoading] = useState(false)
  useEffect(() => {
    const ctrl = new AbortController()
    setLiveLoading(true)
    const tmr = window.setTimeout(() => {
      getFiltreCount(filters, ctrl.signal)
        .then((r) => { setLive(r.compte); setLiveLoading(false) })
        .catch(() => { /* abort/réseau : on garde le dernier nombre */ })
    }, 400)
    return () => { window.clearTimeout(tmr); ctrl.abort() }
  }, [filters])

  return (
    <div data-cadrage-facettes className="flex flex-col gap-4">
      {/* LE TERRAIN — faits objectifs */}
      <div>
        <TitreSection titre="Le terrain"
          info="Des faits objectifs (surface, zonage, état du sol) — valables sans aucune analyse." />
        <div className="gcard mt-2 flex flex-col gap-3 p-3">
          <div>
            <p className="label-caps text-txt-dim">Surface parcelle</p>
            <div className="mt-1 flex items-center gap-1.5">
              <NumField field="surfaceMin" ph="min" /><span className="text-txt-dim">–</span>
              <NumField field="surfaceMax" ph="max" suffix="m²" />
            </div>
          </div>
          <div>
            <p className="label-caps text-txt-dim">Zonage</p>
            <ZoneSelector />
          </div>
          <div>
            <p className="label-caps text-txt-dim">État du sol</p>
            <div className="mt-1"><ChipGroup field="etatSol" options={ETAT_SOL} /></div>
          </div>
        </div>
      </div>

      {/* SIGNAUX DE VIE — événements sourcés, cumulables (OU dans le groupe) */}
      <div>
        <div className="flex items-baseline justify-between gap-2">
          <TitreSection titre="Signaux de vie"
            info="Des événements sourcés, cumulables — une parcelle correspond si au moins un des signaux cochés est présent." />
          {filters.signaux.length > 0 && (
            <span className="shrink-0 text-[10.5px] text-txt-dim">
              {`${filters.signaux.length} actif${filters.signaux.length > 1 ? 's' : ''} sur ${SIGNAUX_KEYS.length}`}
            </span>
          )}
        </div>
        <div className="gcard mt-2 flex flex-wrap gap-1.5 p-3">
          {SIGNAUX_KEYS.map((k) => <SignalChip key={k} k={k} />)}
        </div>
      </div>

      {/* COMPTEUR VIVANT — même endpoint /filtre que la carte (SQL exact, jamais estimé) */}
      {nActifs > 0 && (
        <p data-cadrage-compteur aria-live="polite"
          className={`text-[11.5px] tabular-nums transition-opacity duration-quick ${liveLoading ? 'opacity-50' : 'opacity-100'} ${live === 0 ? 'text-st-creuser' : 'text-txt-mut'}`}>
          {live == null ? '…' : live === 0 ? CLIENT.compteur.zero
            : <><b className="text-txt">{nf.format(live)}</b> parcelles correspondent à ce cadrage</>}
        </p>
      )}
    </div>
  )
}
