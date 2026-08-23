/**
 * Outil « Prospection solaire » — sert la donnée solaire de `parcel_solar`, désormais RECONSTRUITE
 * depuis les sources par le builder (SOLAIRE M1, ingestion/solaire.py) : productible PVGIS (Sourcé
 * dérivé, mensuel + mois_optimal), pente RGE ALTI (Sourcé), azimut du bâti (Estimé), emprise toiture
 * (Estimé), piscine détectée (Estimé ortho 2025), proba propriétaire-occupant (Estimé statistique).
 * Le millésime vit dans le bandeau (servi par l'API). Horizon topographique intégré (PVGIS) ; ombrage
 * de proximité (bâti/arbres) non modélisé.
 * RGPD : aucune donnée nominative — des parcelles et des caractéristiques, jamais des personnes.
 * Outil de démarchage → export CSV. Vocabulaire M135/M137 (le verdict = verdictMeta).
 */
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { getProspectionSolaire, prospectionSolaireCsvUrl, type SolaireFiltres } from '../../lib/api'
import { verdictMeta } from '../../lib/status'
import { TOKENS } from '../../lib/tokens'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { ErrorState } from '../States'
import { Tip } from '../Tip'
import { CommuneScope } from './ModulePanel'

const SORTS = [
  { key: 'potentiel', label: 'Potentiel' },
  { key: 'toiture', label: 'Toiture' },
  { key: 'proba', label: 'Proba occupant' },
] as const
const POTENTIELS = [[0, 'Tous'], [1300, '≥ 1 300'], [1400, '≥ 1 400'], [1500, '≥ 1 500']] as const
const PROBAS = [[0, 'Toutes'], [50, '≥ 50 %'], [70, '≥ 70 %'], [80, '≥ 80 %']] as const
const PISCINES = [['tous', 'Peu importe'], ['oui', 'Piscine détectée'], ['non', 'Sans piscine détectée']] as const

// SOLAIRE M1 — la donnée est reconstruite depuis les sources (builder ingestion/solaire.py). Le
// millésime exact vit dans le bandeau (servi par l'API, source_millesime). Ici, la réserve de méthode :
// l'horizon topographique est intégré par PVGIS, seul l'ombrage de PROXIMITÉ (bâti/arbres) reste non modélisé.
const GEL = 'Millésime au bandeau ci-dessus ; horizon topographique intégré (PVGIS), ombrage de proximité (bâti, arbres) non modélisé.'
// une valeur absente s'affiche « — », jamais un zéro (mandat)
const num = (v: number | null | undefined, unit = '') => (v == null ? '—' : `${v.toLocaleString('fr-FR')}${unit}`)
// proba occupant : intervalle indicatif (± ~10 pts) autour de l'estimation statistique
const probaBand = (p: number | null | undefined) => {
  if (p == null) return '—'
  const lo = Math.max(0, Math.round(p / 10) * 10 - 10)
  const hi = Math.min(100, Math.round(p / 10) * 10 + 10)
  return `${lo}–${hi} %`
}

// en-tête de colonne avec « i » (méthode + millésime) — Estimé le DIT
function Th({ label, right, tip }: { label: string; right?: boolean; tip: string }) {
  return (
    <th className={`px-2 py-1.5 ${right ? 'text-right' : ''}`}>
      <span className="inline-flex items-center gap-1">{label}
        <Tip tip={tip}><span className="cursor-help rounded-full border border-line-2 px-1 text-[8px] text-txt-dim">i</span></Tip>
      </span>
    </th>
  )
}

export function ProspectionSolaire() {
  const select = useApp((s) => s.select)
  const setModuleMap = useApp((s) => s.setModuleMap)
  const [commune, setCommune] = useState<string | null>(null)
  const [potentielMin, setPotentielMin] = useState(0)
  const [probaOccMin, setProbaOccMin] = useState(0)
  const [piscine, setPiscine] = useState<'tous' | 'oui' | 'non'>('tous')
  const [sort, setSort] = useState<(typeof SORTS)[number]['key']>('potentiel')

  const filtres: SolaireFiltres = { commune, potentielMin, probaOccMin, piscine, sort }
  const { data, isLoading, error } = useQuery({
    queryKey: ['prospection-solaire', commune, potentielMin, probaOccMin, piscine, sort],
    queryFn: () => getProspectionSolaire(filtres),
    staleTime: 60_000,
  })

  // surligne les parcelles listées sur la carte (patron module-hl) ; nettoyage au démontage
  useEffect(() => {
    setModuleMap({ idus: (data?.items ?? []).map((i) => i.idu), extra: null })
    return () => setModuleMap({ idus: [], extra: null })
  }, [data, setModuleMap])

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-hidden">
      {/* bandeau — les limites de la V1, toujours visibles (mandat) */}
      <div className="rounded-lg border px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut"
        style={{ borderColor: `${TOKENS.mint}4d`, background: `${TOKENS.mint}0f` }}>
        Les parcelles au <b style={{ color: TOKENS.mint }}>meilleur potentiel solaire</b> — pour
        démarcher l'installation photovoltaïque. {data?.bandeau ?? GEL}
        {/* SOLAIRE M2 (renoncement) — le manque ASSUMÉ : pas de détection PV fiable, on le DIT plutôt
            que de servir un filtre faux (essai V0 : précision 0 %, qa/solaire/PV_PHASE1.md). */}
        <span className="mt-1 block text-[9.5px] text-txt-dim">
          <span className="cursor-help rounded-full border border-line-2 px-1 text-[8px]">i</span>{' '}
          Présence de panneaux existants <b>non détectée</b> — vérification sur photo aérienne à la charge du démarcheur.
        </span>
        {data && <span className="mt-1 block text-[9.5px] text-txt-dim">{data.source} · maj {data.maj}</span>}
      </div>

      {/* entrée + filtres */}
      <CommuneScope commune={commune} onChange={setCommune} />
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[10.5px] text-txt-mut">
        <label className="flex items-center gap-1">Potentiel
          <select data-solaire-potentiel value={potentielMin} onChange={(e) => setPotentielMin(Number(e.target.value))}
            className="rounded border border-line-2 bg-surface-3 px-1 py-0.5 text-txt">
            {POTENTIELS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1">Piscine
          <select data-solaire-piscine value={piscine} onChange={(e) => setPiscine(e.target.value as 'tous' | 'oui' | 'non')}
            className="rounded border border-line-2 bg-surface-3 px-1 py-0.5 text-txt">
            {PISCINES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1">Proba occupant
          <select data-solaire-proba value={probaOccMin} onChange={(e) => setProbaOccMin(Number(e.target.value))}
            className="rounded border border-line-2 bg-surface-3 px-1 py-0.5 text-txt">
            {PROBAS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
      </div>

      {isLoading && <Loading label="Prospection solaire…" />}
      {error && <ErrorState message="Données solaires momentanément indisponibles — réessayez." />}
      {data && (
        <>
          <div className="flex items-center gap-1">
            <span className="mr-1 text-[10px] text-txt-dim">Trier :</span>
            {SORTS.map((s) => (
              <button key={s.key} onClick={() => setSort(s.key)}
                className={`min-h-7 rounded px-2 py-1 text-[11px] transition-colors duration-quick ${sort === s.key
                  ? 'border bg-surface-3 font-medium' : 'text-txt-mut hover:text-txt'}`}
                style={sort === s.key ? { borderColor: `${TOKENS.mint}66`, color: TOKENS.mint } : undefined}>
                {s.label}
              </button>
            ))}
            <span className="ml-auto text-[10px] text-txt-dim">
              {data.tronquee
                ? `les ${data.n} premières sur ${data.total.toLocaleString('fr-FR')}`
                : `${data.n} sur ${data.total.toLocaleString('fr-FR')}`}{commune ? ` — ${commune}` : ' — île'}
            </span>
            {/* export CSV — outil de démarchage (mêmes colonnes que l'écran, mentions Sourcé/Estimé) */}
            <a data-solaire-csv href={prospectionSolaireCsvUrl(filtres)} download
              className="ml-2 rounded-md border px-2 py-1 text-[11px] font-medium transition-colors duration-quick hover:brightness-110"
              style={{ borderColor: `${TOKENS.mint}66`, color: TOKENS.mint, background: `${TOKENS.mint}12` }}>
              ↓ Exporter (CSV)
            </a>
          </div>
          <p className="-mt-1 text-[9.5px] text-txt-dim">
            Triées par <b className="text-txt-mut">{SORTS.find((s) => s.key === sort)?.label.toLowerCase()}</b> décroissant.
          </p>
          <div className="min-h-0 flex-1 overflow-y-auto">
            <table className="w-full text-[11px]">
              <thead className="sticky top-0 bg-surface-2 text-left text-[10px] uppercase tracking-wide text-txt-dim">
                <tr>
                  <th className="px-2 py-1.5">Parcelle</th>
                  <th className="px-2 py-1.5">Classement</th>
                  <Th label="Potentiel" right tip={`Productible PVGIS (modèle SARAH3, Commission européenne) — Sourcé dérivé, en kWh par kWc installé/an. ${GEL}`} />
                  <Th label="Azimut" tip={`Orientation du bâti (élongation de l'emprise) — Estimé (~63 % des parcelles). ${GEL}`} />
                  <Th label="Pente" right tip="Pente moyenne de la parcelle — Sourcé (RGE ALTI 5 m, IGN)." />
                  <Th label="Toiture" right tip={`Emprise au sol du bâti (BD TOPO/CoSIA) — Estimé, proxy de la surface de toiture ; pente et masques non déduits. ${GEL}`} />
                  <Th label="Piscine" tip="Détection sur ortho IGN BD ORTHO 20 cm (millésime 2025), fiabilité mesurée ~90,7 %. L'absence n'est pas vérifiée hors zones scannées (« — »)." />
                  <Th label="ABF" tip="Parcelle en périmètre Architectes des Bâtiments de France — installation solaire soumise à avis. Sourcé." />
                  <Th label="Proba occupant" tip={`Probabilité STATISTIQUE de propriétaire-occupant (Estimé) — non nominative, aucune donnée personnelle ; intervalle indicatif. ${GEL}`} />
                </tr>
              </thead>
              <tbody>
                {data.items.map((it) => (
                  <tr key={it.idu} data-solaire-row className="cursor-pointer border-t border-line hover:bg-surface-2"
                    onClick={() => select(it.idu)}>
                    <td className="px-2 py-1.5 font-mono text-txt">{it.idu}</td>
                    <td className="px-2 py-1.5">
                      {(() => { const v = verdictMeta(null, it.tier_v2, it.etage0); return (
                        <span className="rounded-full px-1.5 py-0.5 text-[10px] font-medium"
                          style={{ background: `${v.color}22`, color: v.color }}>{v.label}</span>
                      ) })()}
                    </td>
                    <td className="px-2 py-1.5 text-right font-medium" style={{ color: TOKENS.mint }}>{num(it.productible)}</td>
                    <td className="px-2 py-1.5 text-txt-mut">{it.azimut == null ? '—' : `${it.azimut}°`}</td>
                    <td className="px-2 py-1.5 text-right text-txt-mut">{it.pente == null ? '—' : `${it.pente}°`}</td>
                    <td className="px-2 py-1.5 text-right text-txt-mut">{num(it.toit_m2, ' m²')}</td>
                    <td className="px-2 py-1.5 text-txt-mut">{it.piscine ? 'oui' : '—'}</td>
                    <td className="px-2 py-1.5 text-txt-mut">{it.abf ? 'ABF' : '—'}</td>
                    <td className="px-2 py-1.5 text-txt-mut">{probaBand(it.proba_occ)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
