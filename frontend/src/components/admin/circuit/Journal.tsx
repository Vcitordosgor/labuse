// CIRCUIT-P (lot 5) / CIRCUIT-P2 (lot 4) — LE JOURNAL LISIBLE. Un tableau : quand, geste, cible,
// par, résultat. Les passages GROUPÉS (un job de filtres sur 39 sources, une volée d'agents) tiennent
// sur UNE ligne dépliable — « filtre · 39 sources · 28 ok, 10 avertissements, 1 quarantaine ·
// système » ; le clic déplie source par source. Un geste isolé reste une ligne. La cible porte son
// NOM affiché (jamais l'identifiant technique) et mène à sa page. Filtres = la liste complète des
// gestes, ordre fixe, présents même vides. « par » dit un nom. 50 lignes groupées par page.
import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'

import { getAdminCircuitJournal } from '../../../lib/api'
import { Chargement } from '../../Loading'

import type { CircuitData } from './types'

type Ouvrir = (type: 'reservoir' | 'robinet' | 'pompe', id: number | string) => void

// résultat → couleur (mint ça va, ambre à regarder, rouge échec/refus).
const couleurResultat = (r: string) =>
  r === 'echec' || r === 'refuse' ? 'rouge' : (r === 'dry-run' || r === 'lance') ? 'ambre' : 'mint'
// verdict d'un filtre → couleur.
const couleurVerdict = (v: string) =>
  v === 'quarantaine' ? 'rouge' : v === 'avertissements' ? 'ambre' : 'mint'

// la répartition d'un groupe : par verdict (filtre) si présent, sinon par résultat.
function repartition(e: any): { txt: string; couleur: string } {
  const v = e.verdicts || {}
  const ordreV = ['ok', 'avertissements', 'quarantaine']
  const clesV = Object.keys(v)
  if (clesV.length) {
    const parts = [...ordreV.filter((k) => v[k]), ...clesV.filter((k) => !ordreV.includes(k))]
      .map((k) => `${v[k]} ${k}`)
    const couleur = v.quarantaine ? 'rouge' : v.avertissements ? 'ambre' : 'mint'
    return { txt: parts.join(', '), couleur }
  }
  const r = e.resultats || {}
  const parts = Object.keys(r).map((k) => `${r[k]} ${k}`)
  const couleur = r.echec || r.refuse ? 'rouge' : (r['dry-run'] || r.lance) ? 'ambre' : 'mint'
  return { txt: parts.join(', '), couleur }
}

const quand = (ts: string) =>
  new Date(ts).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

export function Journal({ data, onOpen, onAujourdhui }:
  { data: CircuitData; onOpen: Ouvrir; onAujourdhui?: (n: number) => void }) {
  // COCKPIT-1b (retour recette, point 2) — UNE seule rangée de filtres : '' = Tout · une famille ·
  // 'echecs' = Échecs seulement. Plus de rangée « Geste ».
  const [filtre, setFiltre] = useState('')
  const [page, setPage] = useState(1)
  const [ouverts, setOuverts] = useState<Record<string, boolean>>({})
  const taille = 50
  const q = useQuery({
    queryKey: ['circuit-journal', filtre, page],
    queryFn: () => getAdminCircuitJournal({
      famille: filtre && filtre !== 'echecs' ? filtre : undefined,
      echecs: filtre === 'echecs' ? true : undefined, page, taille }),
  })

  useEffect(() => { if (q.data && onAujourdhui) onAujourdhui(q.data.aujourdhui) }, [q.data, onAujourdhui])

  // résout une cible (nom/slug de réservoir, id/nom de robinet) vers sa page de détail.
  const resoudre = useMemo(() => {
    const res = new Map<string, number>(); const rob = new Map<string, string>()
    for (const r of data.reservoirs) { res.set(r.nom, r.id); if (r.slug) res.set(r.slug, r.id) }
    for (const r of data.robinets) { rob.set(r.id, r.id); rob.set(r.nom, r.id) }
    return (cible: string | null): { type: 'reservoir' | 'robinet'; id: number | string } | null =>
      !cible ? null
        : res.has(cible) ? { type: 'reservoir', id: res.get(cible)! }
          : rob.has(cible) ? { type: 'robinet', id: rob.get(cible)! } : null
  }, [data])

  const familles: { slug: string; label: string }[] = q.data?.familles || []
  const entrees = q.data?.entrees || []
  const total = q.data?.total || 0
  const pages = Math.max(1, Math.ceil(total / taille))

  // le nom affiché d'une cible (cliquable si elle mène quelque part).
  const Cible = ({ cible, nom }: { cible: string | null; nom: string | null }) => {
    const cbl = resoudre(cible)
    const txt = nom || cible || '—'
    return cbl
      ? <button className="lienc" onClick={(e) => { e.stopPropagation(); onOpen(cbl.type, cbl.id) }}>{txt}</button>
      : <span>{txt}</span>
  }

  return (
    <div>
      {/* COCKPIT-1b (point 2) — UNE seule rangée : Tout · les 4 familles · Échecs seulement. */}
      <div className="jf">
        <button className={filtre === '' ? 'on' : ''} onClick={() => { setFiltre(''); setPage(1) }}>Tout</button>
        {familles.map((f) => (
          <button key={f.slug} className={filtre === f.slug ? 'on' : ''}
            onClick={() => { setFiltre(f.slug); setPage(1) }}>{f.label}</button>
        ))}
        <button className={filtre === 'echecs' ? 'on' : ''} onClick={() => { setFiltre('echecs'); setPage(1) }}>Échecs seulement</button>
      </div>
      <div className="jl h"><span>quand</span><span>geste</span><span>cible</span><span>par</span><span>résultat</span></div>
      {q.isLoading ? <div className="muted" style={{ padding: 12 }}><Chargement variant="bloc" /></div>
        : entrees.length === 0 ? <div className="muted" style={{ padding: 12 }}>Aucune entrée.</div>
          : entrees.map((e: any) => {
            if (e.n > 1) {
              // ── ligne GROUPÉE, dépliable ──
              const rep = repartition(e)
              const open = !!ouverts[e.gk]
              return (
                <div key={e.gk}>
                  <button className="jl grp" onClick={() => setOuverts((o) => ({ ...o, [e.gk]: !o[e.gk] }))}>
                    <span className="muted">{quand(e.ts)}</span>
                    <span className="g"><i className={rep.couleur === 'mint' ? '' : rep.couleur} />{e.categorie_label}</span>
                    <span><b>{`${e.n} cibles`}</b> <span className="chev">{open ? '▼' : '‹'}</span></span>
                    <span className="muted">{e.par_nom}</span>
                    {/* CIRCUIT-P7 (lot 5) — coût du ledger sur les passages d'agents (hors web_search). */}
                    <span className={`r ${rep.couleur === 'mint' ? '' : rep.couleur}`}>{rep.txt}
                      {e.cout_eur != null && <span className="muted"> · {e.cout_eur.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €</span>}</span>
                  </button>
                  {open && e.membres.map((m: any, i: number) => {
                    const c = couleurResultat(m.resultat)
                    const v = (m.details || {}).verdict
                    return (
                      <div key={i} className="jl sub">
                        <span className="muted">{quand(m.ts)}</span>
                        <span />
                        <span><Cible cible={m.cible} nom={m.cible_nom} /></span>
                        <span className="muted">{m.par_nom}</span>
                        <span className={`r ${(v ? couleurVerdict(v) : c) === 'mint' ? '' : (v ? couleurVerdict(v) : c)}`}>{v || m.resultat}</span>
                      </div>
                    )
                  })}
                </div>
              )
            }
            // ── ligne ISOLÉE ──
            const c = couleurResultat(e.resultat)
            return (
              <div key={e.gk} className="jl">
                <span className="muted">{quand(e.ts)}</span>
                <span className="g"><i className={c === 'mint' ? '' : c} />{e.categorie_label}</span>
                <span><Cible cible={e.cible} nom={e.cible_nom} /></span>
                <span className="muted">{e.par_nom}</span>
                <span className={`r ${c === 'mint' ? '' : c}`}>{e.resultat}
                  {e.cout_eur != null && <span className="muted"> · {e.cout_eur.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €</span>}</span>
              </div>
            )
          })}
      <div className="jpage">
        <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>← Précédent</button>
        <span>page {page} / {pages} · {total} passage{total > 1 ? 's' : ''}</span>
        <button className="btn" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Suivant →</button>
      </div>
    </div>
  )
}
