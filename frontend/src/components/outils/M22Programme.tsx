import { useMutation } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { postProgramme } from '../../lib/api'
import { fmtInt } from '../../lib/format'
import { useApp } from '../../store/useApp'
import { TierBadge } from './TierBadge'

/** M22 SENS 2 — programme → parcelles. Le formulaire est la vérité ; le copilote ne fait que le
 *  pré-remplir (doctrine : l'IA traduit, le moteur déterministe calcule). */
export function M22() {
  const { m22Prefill, setM22Prefill, setModuleMap, select, commune } = useApp()
  const [form, setForm] = useState({ type: 'logements', batiments: 1, niveaux: 2, logements_par_batiment: 8, surface_unite_m2: 60, parking: true })
  // périmètre = celui du sélecteur (commune active ou île entière)
  const run = useMutation({ mutationFn: () => postProgramme({ ...form, commune }) })

  useEffect(() => {
    if (m22Prefill) {
      // le copilote peut ne pas connaître toutes les valeurs (ex. « 3 immeubles R+3 » sans
      // nombre de logements → null) : on ne remplace QUE les champs fournis, les défauts tiennent
      const fournis = Object.fromEntries(Object.entries(m22Prefill).filter(([, v]) => v != null))
      setForm((f) => ({ ...f, ...fournis }))
      setM22Prefill(null)
      setTimeout(() => run.mutate(), 150)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [m22Prefill])

  const d = run.data
  useEffect(() => {
    const items = (d?.items ?? []) as Record<string, any>[]
    setModuleMap({ idus: items.map((i) => i.idu), extra: null })
    return () => setModuleMap({ idus: [], extra: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [d])

  const F = (k: keyof typeof form, label: string, opts?: { min?: number }) => (
    <label className="min-w-0 flex-1 text-[11px] tracking-wide text-txt-dim">{label}
      <input type="number" min={opts?.min ?? 1} value={form[k] as number}
        onChange={(e) => setForm({ ...form, [k]: Number(e.target.value) })}
        className="mt-0.5 w-full rounded border border-line-2 bg-surface-3 px-2 py-1 text-xs text-txt focus:border-violet focus:outline-none" />
    </label>
  )

  return (
    <>
      <div className="rounded-lg border border-violet/40 bg-violet/[0.07] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
        Décrivez le programme — les critères sont <b>calculés et affichés</b> (SDP, hauteur PLU).
        Le copilote sait pré-remplir : « un terrain pour 3 immeubles R+3 avec parking ».
      </div>
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
        {/* B4 : PARKING aligné en colonne flex-1 comme les autres champs (plus de largeur cassée) */}
        <label className="flex min-w-0 flex-1 flex-col text-[11px] tracking-wide text-txt-dim">PARKING
          <button onClick={() => setForm({ ...form, parking: !form.parking })}
            className={`mt-0.5 w-full rounded border py-1 text-xs transition-colors duration-quick ${form.parking ? 'border-violet text-violet' : 'border-line-2 text-txt-mut'}`}>
            {form.parking ? 'oui' : 'non'}
          </button>
        </label>
      </div>
      <button onClick={() => run.mutate()} disabled={run.isPending}
        className="rounded-lg bg-violet py-1.5 text-xs font-medium text-bg transition-[filter] duration-quick hover:brightness-110 disabled:opacity-40">
        {run.isPending ? 'Calcul…' : 'Trouver les parcelles'}
      </button>
      {d && (
        <>
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[10.5px] text-txt-mut">
            <div><b className="text-txt">{d.criteres.unites}</b> unités → SDP ≥ <b className="tnum text-violet">{fmtInt(d.criteres.sdp_min_m2)} m²</b>
              <span className="text-txt-dim"> ({d.criteres.calcul})</span></div>
            <div className="mt-0.5">{d.criteres.hauteur_regle}{form.parking ? ` · parking ~${fmtInt(d.criteres.parking_m2)} m²` : ''}</div>
            <div className="mt-1 text-[11px] leading-snug text-txt-dim">{d.bandeau}</div>
          </div>
          {/* Fix point 28 : compteur PROMINENT et RÉACTIF — l'utilisateur voit que sa saisie agit
              (le nombre change nettement quand le programme change), même si le haut de liste
              (marges fortes) reste stable. */}
          <div data-prog-count className="rounded-lg border border-violet/40 bg-violet/[0.07] px-3 py-2">
            <p className="text-[13px] leading-snug text-txt">
              <b className="num-key text-lg text-violet">{fmtInt(d.n)}</b>{' '}
              parcelle{d.n > 1 ? 's' : ''} correspond{d.n > 1 ? 'ent' : ''} à vos critères
              <span className="text-txt-dim">{commune ? ` à ${commune}` : ' (toute l’île)'}</span>
            </p>
            {/* Fix point 28 : lever la confusion « N = plafond ». N est le TOTAL des correspondances ;
                la liste n'en montre que les premières (triées par marge). */}
            <p className="mt-0.5 text-[10.5px] leading-snug text-txt-dim">
              {d.n > (d.items as unknown[]).length
                ? `Total des correspondances (pas une limite) — les ${(d.items as unknown[]).length} premières, par marge de capacité décroissante, sont affichées.`
                : 'Triées par marge de capacité décroissante.'}
            </p>
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
            {(d.items as Record<string, any>[]).map((i) => (
              <button key={i.idu} onClick={() => select(i.idu)}
                className="flex w-full items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-left transition-colors duration-quick hover:border-violet/50">
                <div className="min-w-0 flex-1">
                  <div className="font-mono text-xs text-txt-hi">{i.idu.slice(8, 10)} {i.idu.slice(10)}
                    {!commune && i.commune && <span className="ml-1.5 font-sans text-[11px] text-txt-dim">{i.commune}</span>}
                  </div>
                  <div className="truncate text-[10.5px] text-txt-mut">
                    SDP {fmtInt(i.sdp)} m² · zone {i.zone ?? '?'} {i.hauteur_verifiee ? `(h ${i.hauteur_plu_m} m ✓)` : '(hauteur à instruire)'}
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  <div className="num-key text-sm text-violet">×{i.marge_capacite}</div>
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
  )
}
