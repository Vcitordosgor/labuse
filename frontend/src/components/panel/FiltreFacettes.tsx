// M120 — LE CADRAGE PROJET : les facettes de la carte (terrain + signaux) RÉUTILISÉES telles
// quelles — mêmes contrôles (ChipGroup / ZoneSelector / SignalChip / NumField), jamais une copie —
// branchées sur le binding fourni (le cadrage projet local, via FiltreProvider).
// M120-B — le compteur vivant compte le VIVIER FIGEABLE (hors exclusions dures), pas le total carte
// gonflé : le client voit l'univers réel qu'il triera, et qu'il figera un TOP-N (jamais l'ensemble).
import { useEffect, useState } from 'react'

import { getCadrageCompteur, type CadrageCompteur } from '../../lib/api'
import { countActiveFilters } from '../../lib/filters'
import {
  ChipGroup, ETAT_SOL, NumField, SignalChip, SIGNAUX_KEYS, TitreSection, ZoneSelector,
} from './FiltreLabuse'
import { useFiltre } from './filtreContext'

const nf = new Intl.NumberFormat('fr-FR')

export function FiltreFacettes() {
  const { filters } = useFiltre()
  const nActifs = countActiveFilters(filters)
  const [live, setLive] = useState<CadrageCompteur | null>(null)
  const [liveLoading, setLiveLoading] = useState(false)
  useEffect(() => {
    const ctrl = new AbortController()
    setLiveLoading(true)
    const tmr = window.setTimeout(() => {
      getCadrageCompteur(filters, ctrl.signal)
        .then((r) => { setLive(r); setLiveLoading(false) })
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

      {/* COMPTEUR VIVANT — le VIVIER FIGEABLE (SQL exact) : ce que le client triera réellement, et
          qu'il figera un TOP-N. Jamais le total gonflé par les exclusions dures. */}
      {nActifs > 0 && (
        <div data-cadrage-compteur aria-live="polite"
          className={`text-[11.5px] transition-opacity duration-quick ${liveLoading ? 'opacity-50' : 'opacity-100'}`}>
          {live == null ? <span className="text-txt-mut">…</span>
            : live.vivier === 0 ? <span className="text-st-creuser">Aucune parcelle figeable — élargissez le cadrage.</span>
            : live.vivier <= live.cap ? (
              <span className="text-txt-mut"><b className="tabular-nums text-txt">{nf.format(live.vivier)}</b> parcelle{live.vivier > 1 ? 's' : ''} figeable{live.vivier > 1 ? 's' : ''} — toutes seront à trier.</span>
            ) : (
              <span className="text-txt-mut"><b className="tabular-nums text-txt">{nf.format(live.vivier)}</b> parcelles figeables · la shortlist figera les <b className="text-txt">{live.cap}</b> meilleures (par probabilité de mutation) — <span className="text-st-creuser">resserrez le cadrage pour cibler</span>.</span>
            )}
          <p className="mt-0.5 text-[10px] text-txt-dim">Figeable = hors terrains non constructibles et faux positifs (exclusions automatiques du moteur).</p>
        </div>
      )}
    </div>
  )
}
