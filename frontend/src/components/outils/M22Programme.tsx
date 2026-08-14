import { useMutation } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { postProgramme } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { FaisabiliteTab } from '../fiche/Fiche'
import { CommuneScope } from './ModulePanel'
import { ParcelPicker } from './ParcelPicker'
import { TierBadge } from './TierBadge'

/** M22 · FAISABILITÉ — 2 entrées (M15-C) :
 *  · « Par critères » (SENS 2) : on décrit un programme, LABUSE propose les parcelles qui matchent.
 *    Le copilote pré-remplit le formulaire ; le moteur déterministe calcule. RG1 : le périmètre
 *    commune est SAISI ICI (plus hérité du filtre carte).
 *  · « Par parcelle » (SENS 1) : on désigne UNE parcelle (IDU / adresse / clic carte) et on voit sa
 *    faisabilité — exactement l'onglet Faisabilité des fiches, porté dans l'outil (aucune divergence). */
export function M22() {
  const { m22Prefill, setM22Prefill, parcelPrefill, setParcelPrefill, setModuleMap, select } = useApp()
  const [mode, setMode] = useState<'criteres' | 'parcelle'>('criteres')
  const [commune, setCommune] = useState<string | null>(null)   // RG1 : périmètre saisi dans l'outil
  const [picked, setPicked] = useState<string | null>(null)     // mode « par parcelle »
  const [form, setForm] = useState({ type: 'logements', batiments: 1, niveaux: 2, logements_par_batiment: 8, surface_unite_m2: 60, parking: true })
  const run = useMutation({ mutationFn: () => postProgramme({ ...form, commune }) })

  useEffect(() => {
    if (m22Prefill) {
      // le copilote pré-remplit le formulaire (mode critères) — on ne remplace QUE les champs fournis
      const fournis = Object.fromEntries(Object.entries(m22Prefill).filter(([, v]) => v != null))
      setForm((f) => ({ ...f, ...fournis }))
      setM22Prefill(null)
      setMode('criteres')
      setTimeout(() => run.mutate(), 150)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [m22Prefill])

  // M-ENTREE — porte fiche → Faisabilité : la parcelle amorce le mode « par parcelle » (motif
  // parcelPrefill partagé, consommation-puis-reset). Indépendant du m22Prefill critères (copilote).
  useEffect(() => {
    if (parcelPrefill) {
      setMode('parcelle')
      setPicked(parcelPrefill)
      setParcelPrefill(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parcelPrefill])

  const d = run.data
  // carte : résultats en mode critères, parcelle désignée en mode parcelle
  useEffect(() => {
    const idus = mode === 'criteres'
      ? ((d?.items ?? []) as Record<string, any>[]).map((i) => i.idu as string)
      : (picked ? [picked] : [])
    setModuleMap({ idus, extra: null })
    return () => setModuleMap({ idus: [], extra: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, d, picked])

  const F = (k: keyof typeof form, label: string, opts?: { min?: number }) => (
    <label className="min-w-0 flex-1 text-[11px] tracking-wide text-txt-dim">{label}
      <input type="number" min={opts?.min ?? 1} value={form[k] as number}
        onChange={(e) => setForm({ ...form, [k]: Number(e.target.value) })}
        className="mt-0.5 w-full rounded border border-line-2 bg-surface-3 px-2 py-1 text-xs text-txt focus:border-mint focus:outline-none" />
    </label>
  )

  return (
    <>
      {/* SÉLECTEUR DE MODE — deux façons d'entrer une parcelle */}
      <div className="flex gap-1 rounded-lg border border-line-2 bg-surface-2 p-1">
        {([['criteres', 'Par critères'], ['parcelle', 'Par parcelle']] as const).map(([m, l]) => (
          <button key={m} data-faisa-mode={m} onClick={() => setMode(m)}
            className={`flex-1 rounded-md py-1 text-[11px] font-medium transition-colors duration-quick ${mode === m ? 'bg-mint text-bg' : 'text-txt-mut hover:text-txt'}`}>
            {l}
          </button>
        ))}
      </div>

      {mode === 'criteres' && (
        <>
          <div className="rounded-lg border border-mint/40 bg-mint/[0.07] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
            Décrivez le programme — les critères sont <b>calculés et affichés</b> (SDP, hauteur PLU).
            Le copilote sait pré-remplir : « un terrain pour 3 immeubles R+3 avec parking ».
          </div>
          <CommuneScope commune={commune} onChange={setCommune} />
          <div className="flex gap-2">
            <label className="min-w-0 flex-1 text-[11px] tracking-wide text-txt-dim">TYPE
              <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}
                className="mt-0.5 w-full rounded border border-line-2 bg-surface-3 px-1 py-1 text-xs text-txt">
                <option value="logements">logements</option>
                <option value="etudiant">rés. étudiante</option>
                <option value="bureaux">bureaux</option>
              </select>
            </label>
            {F('batiments', 'BÂTIMENTS')}
            {F('niveaux', 'R+N', { min: 0 })}
          </div>
          <div className="flex gap-2">
            {F('logements_par_batiment', 'UNITÉS/BÂT')}
            {F('surface_unite_m2', 'M²/UNITÉ (hyp.)', { min: 15 })}
            <label className="flex min-w-0 flex-1 flex-col text-[11px] tracking-wide text-txt-dim">PARKING
              <button onClick={() => setForm({ ...form, parking: !form.parking })}
                className={`mt-0.5 w-full rounded border py-1 text-xs transition-colors duration-quick ${form.parking ? 'border-mint text-mint' : 'border-line-2 text-txt-mut'}`}>
                {form.parking ? 'oui' : 'non'}
              </button>
            </label>
          </div>
          <button onClick={() => run.mutate()} disabled={run.isPending}
            className="rounded-lg bg-mint py-1.5 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
            {run.isPending ? 'Calcul…' : 'Trouver les parcelles'}
          </button>
          {d && (
            <>
              <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[10.5px] text-txt-mut">
                <div><b className="text-txt">{d.criteres.unites}</b> unités → SDP ≥ <b className="tnum text-mint">{fmtInt(d.criteres.sdp_min_m2)} m²</b>
                  <span className="text-txt-dim"> ({d.criteres.calcul})</span></div>
                <div className="mt-0.5">{d.criteres.hauteur_regle}{form.parking ? ` · parking ~${fmtInt(d.criteres.parking_m2)} m²` : ''}</div>
                <div className="mt-1 text-[11px] leading-snug text-txt-dim">{d.bandeau}</div>
              </div>
              <div data-prog-count className="rounded-lg border border-mint/40 bg-mint/[0.07] px-3 py-2">
                <p className="text-[13px] leading-snug text-txt">
                  <b className="num-key text-lg text-mint">{fmtInt(d.n)}</b>{' '}
                  parcelle{d.n > 1 ? 's' : ''} correspond{d.n > 1 ? 'ent' : ''} à vos critères
                  <span className="text-txt-dim">{commune ? ` à ${commune}` : ' (toute l’île)'}</span>
                </p>
                <p className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">
                  {d.n > (d.items as unknown[]).length
                    ? `Total des correspondances (pas une limite) — les ${(d.items as unknown[]).length} premières, par marge de capacité décroissante, sont affichées.`
                    : 'Triées par marge de capacité décroissante.'}
                </p>
              </div>
              <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
                {(d.items as Record<string, any>[]).map((i) => (
                  <button key={i.idu} onClick={() => select(i.idu)}
                    className="flex w-full items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-left transition-colors duration-quick hover:border-mint/50">
                    <div className="min-w-0 flex-1">
                      <div className="font-mono text-xs text-txt-hi">{i.idu.slice(8, 10)} {i.idu.slice(10)}
                        {!commune && i.commune && <span className="ml-1.5 font-sans text-[11px] text-txt-dim">{i.commune}</span>}
                      </div>
                      <div className="truncate text-[10.5px] text-txt-mut">
                        SDP {fmtInt(i.sdp)} m² · zone {i.zone ?? '?'} {i.hauteur_verifiee ? `(h ${i.hauteur_plu_m} m ✓)` : '(hauteur à instruire)'}
                      </div>
                    </div>
                    <div className="shrink-0 text-right">
                      <div className="num-key text-sm text-mint">×{i.marge_capacite}</div>
                      <div>
                        <TierBadge tier={i.tier_v2 as string | null} etage0={i.etage0 as boolean | null} statut={i.statut as string | null} />
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </>
          )}
        </>
      )}

      {mode === 'parcelle' && (
        <>
          <div className="rounded-lg border border-mint/40 bg-mint/[0.07] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
            Désignez une parcelle : sa <b>faisabilité complète</b> (capacité, calcul tracé, explication IA,
            charge foncière) — le même calcul que l'onglet Faisabilité de la fiche.
          </div>
          {!picked ? (
            <ParcelPicker onPick={setPicked} picked={picked} />
          ) : (
            <>
              <div className="flex items-center gap-2 text-[11px] text-txt-mut">
                <span>Parcelle <b className="font-mono text-txt">{picked.slice(8, 10)} {picked.slice(10)}</b></span>
                <button data-faisa-changer onClick={() => setPicked(null)}
                  className="ml-auto rounded border border-line-2 px-2 py-0.5 text-[10.5px] text-txt-dim transition-colors duration-quick hover:text-txt">changer</button>
              </div>
              <div data-faisa-parcelle className="min-h-0 flex-1 overflow-y-auto pr-0.5">
                <FaisabiliteTab idu={picked} />
              </div>
            </>
          )}
        </>
      )}
    </>
  )
}
