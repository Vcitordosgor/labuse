// M120 — LE CADRAGE PROJET : les facettes de la carte RÉUTILISÉES telles quelles — mêmes contrôles
// (ChipGroup / ZoneSelector / SignalChip / NumField), jamais une copie — branchées sur le binding
// fourni (le cadrage projet local, via FiltreProvider).
// NU-F-003 (décision Vic « total partout, split visible ») — le cadrage rend EXACTEMENT les familles
// de la carte (terrain + Affiner la recherche + Propriétaire, étage 0 compris) et son compteur annonce
// le MÊME nombre que le panneau Filtre de la carte (`total`), avec le split qui l'explique
// (`figeable` triable · `ecartees` écartées). Plus de sous-ensemble codé en dur, plus de « rien
// d'autre » démenti par les faits.
import { useEffect, useState } from 'react'

import { getCadrageCompteur, type CadrageCompteur } from '../../lib/api'
import { countActiveFilters } from '../../lib/filters'
import {
  AffinerRecherche, ChipGroup, ETAT_SOL, NumField, SectionProprietaire, TitreSection, ZoneSelector,
} from './FiltreLabuse'
import { useFiltre } from './filtreContext'
import { type Filters } from '../../store/useApp'

const nf = new Intl.NumberFormat('fr-FR')

// PROJETS-FIX F1 — `compteurScope` : le PÉRIMÈTRE (communes) que le compteur vivant doit appliquer,
// mais qui vit HORS des facettes éditables (cas du wizard projet, où la commune est une étape à part).
// Sans lui, le compteur comptait l'ÎLE ENTIÈRE pendant qu'on cadrait une commune → le wizard annonçait
// un vivier île que le projet, commune-scopé, démentait. Le fournir aligne le compteur sur la création.
export function FiltreFacettes({ compteurScope }: { compteurScope?: Partial<Filters> } = {}) {
  const { filters } = useFiltre()
  const nActifs = countActiveFilters(filters)
  const [live, setLive] = useState<CadrageCompteur | null>(null)
  const [liveLoading, setLiveLoading] = useState(false)
  const scopeKey = JSON.stringify(compteurScope ?? {})
  useEffect(() => {
    const ctrl = new AbortController()
    setLiveLoading(true)
    const tmr = window.setTimeout(() => {
      // le compteur sort de la MÊME requête que « À trier » : facettes + périmètre, comme à la création.
      getCadrageCompteur({ ...filters, ...(compteurScope ?? {}) }, ctrl.signal)
        .then((r) => { setLive(r); setLiveLoading(false) })
        .catch(() => { /* abort/réseau : on garde le dernier nombre */ })
    }, 400)
    return () => { window.clearTimeout(tmr); ctrl.abort() }
  }, [filters, scopeKey])

  return (
    <div data-cadrage-facettes className="flex flex-col gap-4">
      {/* LE TERRAIN — faits objectifs (mêmes contrôles que « 2 · Le terrain » de la carte) */}
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
            {/* NU-B-002 / NU-F-003 — même partition que la carte (nu · bâti · non mesuré). */}
            <div className="mt-1"><ChipGroup field="etatSol" options={ETAT_SOL} partition /></div>
          </div>
        </div>
      </div>

      {/* NU-F-003 — les familles qui manquaient au cadrage, RÉUTILISÉES telles quelles depuis la carte :
          Affiner la recherche (copropriété, hauteur LiDAR, emprise/saturé, ZFANG, FRR, signaux de vie)
          et toute la section Propriétaire (dénomination, SIREN, forme juridique, APE, dirigeants, âge). */}
      <AffinerRecherche />
      <SectionProprietaire />

      {/* COMPTEUR — le MÊME nombre que la carte (`total`, étage 0 compris) + le split : combien seront
          réellement à trier (`figeable`), combien sont écartées. Le wizard annonce la carte, le split
          dit ce que le projet servira — plus de nombre démenti à l'ouverture. */}
      {nActifs > 0 && (
        <div data-cadrage-compteur aria-live="polite"
          className={`text-[11.5px] transition-opacity duration-quick ${liveLoading ? 'opacity-50' : 'opacity-100'}`}>
          {live == null ? <span className="text-txt-mut">…</span>
            : live.total === 0 ? <span className="text-st-creuser">Aucune parcelle — élargissez le cadrage.</span>
            : (
              <>
                <span className="text-txt-mut"><b className="tabular-nums text-txt">{nf.format(live.total)}</b> parcelle{live.total > 1 ? 's' : ''} correspondent à ce cadrage.</span>
                <p className="mt-0.5 text-[11px] text-txt-mut">
                  <b className="tabular-nums text-txt">{nf.format(live.figeable)}</b> à trier
                  {live.ecartees > 0 && <> · <span className="text-st-ecartee tabular-nums">{nf.format(live.ecartees)}</span> écartées</>}
                  {live.figeable > live.cap && <> · la shortlist figera les <b className="text-txt">{live.cap}</b> meilleures (par probabilité de mutation)</>}
                </p>
                <p className="mt-0.5 text-[10px] text-txt-dim">Écartées = terrains non constructibles et faux positifs (exclusions automatiques du moteur) — comptés par la carte, non triables.</p>
              </>
            )}
        </div>
      )}
    </div>
  )
}
