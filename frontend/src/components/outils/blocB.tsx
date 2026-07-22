/** BLOC B · Partie 2 — les outils O sans écran (verdict Vic sur maquettes docs/mockups/).
 *  Chaque module vit dans le shell violet du registre ; tokens seulement, wording boussole
 *  (Sourcé/Estimé, « non couvert » dit — jamais un faux RAS). */
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useApp } from '../../store/useApp'
import { Loading } from '../Loading'
import { ErrorState } from '../States'

const jfetch = async <T,>(url: string): Promise<T> => {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url} → ${r.status}`)
  return r.json() as Promise<T>
}

function Banner({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-violet/40 bg-violet/[0.07] px-3 py-2 text-[10.5px] leading-relaxed text-txt-mut">
      {children}
    </div>
  )
}

/* ───────────── O5 — SERVITUDES INVISIBLES (S46) ───────────── */

type Servitudes = {
  idu: string; n: number; synthese: string
  servitudes: { categorie: string; effet: string; source: string; date: string | null }[]
  non_couvert: string[]
}

export function O5Servitudes() {
  const { selectedIdu, select } = useApp()
  const [idu, setIdu] = useState(selectedIdu ?? '')
  useEffect(() => { if (selectedIdu) setIdu(selectedIdu) }, [selectedIdu])
  const q = useQuery({
    queryKey: ['o5', idu],
    queryFn: () => jfetch<Servitudes>(`/servitudes-invisibles/${idu.trim()}`),
    enabled: idu.trim().length === 14,
  })
  const d = q.data
  return (
    <>
      <Banner>Les contraintes <b>dormantes</b> qui ne se voient pas sur la carte — servitudes
        d'utilité publique, sols, bruit — ET ce que la base ne couvre pas (jamais un faux
        « RAS »). La due diligence notariale reste indispensable.</Banner>
      <input data-o5-idu value={idu} onChange={(e) => setIdu(e.target.value.trim())}
        placeholder="IDU (ou sélectionnez une parcelle sur la carte)"
        className="rounded-lg border border-line-2 bg-surface-3 px-2 py-1.5 font-mono text-[11px] text-txt focus:border-violet focus:outline-none" />
      {q.isLoading && <Loading accent="violet" label="Recherche des servitudes…" />}
      {q.isError && <ErrorState className="py-6" message="Servitudes indisponibles." retry={() => q.refetch()} />}
      {d && (
        <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2 text-[11px]">
            <span className="num-key text-base text-violet">{d.n}</span>{' '}
            <span className="text-txt-mut">servitude(s)/contrainte(s) sur</span>{' '}
            <button onClick={() => select(d.idu)} className="font-mono text-txt-hi hover:text-mint hover:underline">
              {d.idu.slice(8, 10)} {d.idu.slice(10)}</button>
          </div>
          {d.servitudes.map((s, i) => (
            <div key={i} className="rounded-lg bg-surface-3 px-3 py-2 shadow-elev-1">
              <div className="flex flex-wrap items-baseline gap-1.5">
                <b className="text-[11.5px] text-txt-hi">{s.categorie}</b>
                <span className="rounded-full border border-mint/40 bg-mint/10 px-1.5 text-[8.5px] font-medium text-mint">Sourcé</span>
                <span className="text-[9.5px] text-txt-dim">{s.source}{s.date ? ` · ${s.date}` : ''}</span>
              </div>
              <p className="mt-1 text-[11px] leading-snug text-txt">{s.effet}</p>
            </div>
          ))}
          {d.servitudes.length === 0 && (
            <p className="rounded-lg bg-surface-2/60 px-3 py-2 text-[11px] text-txt-mut">
              Aucune servitude détectée dans les couches ingérées — voir « non couvert » ci-dessous.</p>
          )}
          <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
            <p className="label-caps text-[9.5px]">Non couvert par la base — à vérifier ailleurs</p>
            <div className="mt-1 space-y-0.5">
              {d.non_couvert.map((n, i) => <p key={i} className="text-[10.5px] text-txt-mut">○ {n}</p>)}
            </div>
          </div>
        </div>
      )}
      {!d && !q.isLoading && !q.isError && (
        <p className="text-[11px] text-txt-dim">Saisissez un IDU complet (14 caractères) ou cliquez une parcelle.</p>
      )}
    </>
  )
}

/* ───────────── O6 — COMPARATEUR DE COMMUNES (S47) ───────────── */

type Comparateur = {
  communes: Record<string, string | number | null>[]
  indicateurs: Record<string, { libelle: string; direction: string; poids: number; source: string; nature: string }>
  methode: string; avertissement: string
}
const O6_COLS: { k: string; label: string; unite?: string }[] = [
  { k: 'score_composite', label: 'Composite' }, { k: 'stock', label: 'Stock opp.' },
  { k: 'velocite', label: 'Vélocité', unite: ' m' }, { k: 'permis', label: 'Permis 5 ans' },
  { k: 'deficit_sru', label: 'Déficit SRU', unite: ' %' }, { k: 'prix_neuf', label: '€/m² neuf' },
]

export function O6Comparateur() {
  const [poids, setPoids] = useState<Record<string, number>>({
    stock: 30, velocite: 15, permis: 15, deficit_sru: 15, pression_zan: 10, prix_neuf: 15,
  })
  const [tri, setTri] = useState('score_composite')
  const qs = Object.entries(poids).map(([k, v]) => `w_${k}=${(v / 100).toFixed(2)}`).join('&')
  const q = useQuery({ queryKey: ['o6', qs], queryFn: () => jfetch<Comparateur>(`/comparateur-communes?${qs}`) })
  const d = q.data
  const rows = [...(d?.communes ?? [])].sort((a, b) => Number(b[tri] ?? -1) - Number(a[tri] ?? -1))
  return (
    <>
      <Banner>Où investir : une ligne par commune, indicateurs <b>sourcés</b>, composite de
        commodité à pondération réglable. {d?.avertissement ?? 'Les valeurs brutes restent la référence.'}</Banner>
      <div className="rounded-lg border border-line-2 bg-surface-2 px-3 py-2">
        <p className="label-caps text-[9.5px]">Pondérations — renormalisées si une donnée manque</p>
        <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1">
          {Object.entries(poids).map(([k, v]) => (
            <label key={k} className="text-[10px] text-txt-mut">
              {d?.indicateurs?.[k]?.libelle ?? k} · <b className="tnum text-txt">{v} %</b>
              <input type="range" min={0} max={100} step={5} value={v} data-o6-poids={k}
                onChange={(e) => setPoids({ ...poids, [k]: Number(e.target.value) })}
                className="w-full accent-violet" />
            </label>
          ))}
        </div>
      </div>
      {q.isLoading && <Loading accent="violet" label="Calcul du comparatif…" />}
      {q.isError && <ErrorState className="py-6" message="Comparateur indisponible." retry={() => q.refetch()} />}
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="sticky top-0 grid grid-cols-[1fr_repeat(3,56px)] gap-1 bg-surface-1 py-1 sm:grid-cols-[1fr_repeat(6,56px)]">
          <span className="label-caps text-[9px]">Commune</span>
          {O6_COLS.map((c, i) => (
            <button key={c.k} data-o6-tri={c.k} onClick={() => setTri(c.k)}
              className={`text-right text-[9px] uppercase tracking-wide transition-colors duration-quick ${tri === c.k ? 'text-violet' : 'text-txt-dim hover:text-txt-mut'} ${i >= 3 ? 'hidden sm:block' : ''}`}>
              {c.label} {tri === c.k ? '↓' : ''}</button>
          ))}
        </div>
        {rows.map((c, i) => (
          <div key={String(c['insee'])} className="grid grid-cols-[1fr_repeat(3,56px)] items-baseline gap-1 border-b border-line py-1.5 text-[11px] sm:grid-cols-[1fr_repeat(6,56px)]">
            <span className="min-w-0 truncate text-txt">
              <span className="mr-1 font-mono text-[9px] text-txt-dim">#{i + 1}</span>{String(c['commune'])}</span>
            {O6_COLS.map((col, j) => (
              <span key={col.k} className={`tnum text-right font-mono ${col.k === 'score_composite' ? (i < 3 ? 'font-semibold text-violet' : 'text-txt') : 'text-txt-mut'} ${j >= 3 ? 'hidden sm:block' : ''}`}>
                {c[col.k] == null ? '—' : `${Number(c[col.k]).toLocaleString('fr-FR')}${col.unite ?? ''}`}</span>
            ))}
          </div>
        ))}
      </div>
      <p className="shrink-0 text-[9.5px] leading-snug text-txt-dim">
        Composite = aide de lecture (jamais un score de rendement) ; un axe manquant reste « — »,
        jamais un zéro inventé. Tri par colonne au clic.</p>
    </>
  )
}
