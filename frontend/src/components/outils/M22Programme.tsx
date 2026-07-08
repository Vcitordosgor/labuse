import { useMutation } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { postProgramme } from '../../lib/api'
import { STATUT_META } from '../../lib/status'
import { useApp } from '../../store/useApp'
import { VIOLET } from './registry'

const fmt = (n: number | null | undefined) => (n == null ? '—' : Math.round(Number(n)).toLocaleString('fr-FR'))

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
    <label className="min-w-0 flex-1 text-[10px] tracking-wide text-txt-dim">{label}
      <input type="number" min={opts?.min ?? 1} value={form[k] as number}
        onChange={(e) => setForm({ ...form, [k]: Number(e.target.value) })}
        className="mt-0.5 w-full rounded border border-line-2 bg-surface-3 px-2 py-1 text-xs text-txt focus:border-[#B497F0] focus:outline-none" />
    </label>
  )

  return (
    <>
      <div className="rounded-lg border border-[#4a3d6b] bg-[#1a1526] px-3 py-2 text-[10.5px] leading-relaxed text-[#b8a8de]">
        Décrivez le programme — les critères sont <b>calculés et affichés</b> (SDP, hauteur PLU).
        Le copilote sait pré-remplir : « un terrain pour 3 immeubles R+3 avec parking ».
      </div>
      <div className="flex gap-2">
        <label className="min-w-0 flex-1 text-[10px] tracking-wide text-txt-dim">TYPE
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
        <label className="flex flex-col text-[10px] tracking-wide text-txt-dim">PARKING
          <button onClick={() => setForm({ ...form, parking: !form.parking })}
            className={`mt-0.5 rounded border px-3 py-1 text-xs ${form.parking ? 'border-[#B497F0] text-[#B497F0]' : 'border-line-2 text-txt-mut'}`}>
            {form.parking ? 'oui' : 'non'}
          </button>
        </label>
      </div>
      <button onClick={() => run.mutate()} disabled={run.isPending}
        className="rounded-lg py-1.5 text-xs font-medium text-[#120d1d] disabled:opacity-40" style={{ background: VIOLET }}>
        {run.isPending ? 'Calcul…' : 'Trouver les parcelles'}
      </button>
      {d && (
        <>
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[10.5px] text-txt-mut">
            <div><b className="text-txt">{d.criteres.unites}</b> unités → SDP ≥ <b style={{ color: VIOLET }}>{fmt(d.criteres.sdp_min_m2)} m²</b>
              <span className="text-txt-dim"> ({d.criteres.calcul})</span></div>
            <div className="mt-0.5">{d.criteres.hauteur_regle}{form.parking ? ` · parking ~${fmt(d.criteres.parking_m2)} m²` : ''}</div>
            <div className="mt-1 text-[9.5px] leading-snug text-txt-dim">{d.bandeau}</div>
          </div>
          <p className="text-[11px] text-txt-dim">{fmt(d.n)} parcelles candidates (marge décroissante)</p>
          <div className="flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto">
            {(d.items as Record<string, any>[]).map((i) => (
              <button key={i.idu} onClick={() => select(i.idu)}
                className="flex w-full items-center gap-2 rounded-lg border border-line-2 bg-surface-3 px-3 py-2 text-left hover:border-[#6b5a96]">
                <div className="min-w-0 flex-1">
                  <div className="font-mono text-xs text-txt-hi">{i.idu.slice(8, 10)} {i.idu.slice(10)}
                    {!commune && i.commune && <span className="ml-1.5 font-sans text-[9.5px] text-txt-dim">{i.commune}</span>}
                  </div>
                  <div className="truncate text-[10.5px] text-txt-mut">
                    SDP {fmt(i.sdp)} m² · zone {i.zone ?? '?'} {i.hauteur_verifiee ? `(h ${i.hauteur_plu_m} m ✓)` : '(hauteur à instruire)'}
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  <div className="font-display text-sm font-bold" style={{ color: VIOLET }}>×{i.marge_capacite}</div>
                  <div className="text-[9px]" style={{ color: STATUT_META[i.statut as keyof typeof STATUT_META]?.color }}>
                    {STATUT_META[i.statut as keyof typeof STATUT_META]?.label}
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
