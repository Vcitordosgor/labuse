// CIRCUIT-P (lot 5) — LE JOURNAL. Un tableau : quand, geste, cible, par, résultat. Filtres par type
// de geste, « tous » en premier À GAUCHE (c'est un filtre de journal, pas un groupe de tri : la règle
// « Tout à droite » vaut pour les filtres d'outils). Pagination simple. Une ligne dont la cible
// existe est un lien vers sa page de détail (5.1). Le compteur de l'onglet dit « aujourd'hui » et le
// nombre d'entrées du jour (5.2, remonté au conteneur).
import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'

import { getAdminCircuitJournal } from '../../../lib/api'

import type { CircuitData } from './types'

type Ouvrir = (type: 'reservoir' | 'robinet' | 'pompe', id: number | string) => void

// résultat → couleur (mint ça va, ambre à regarder, rouge échec/refus).
const couleurResultat = (r: string) =>
  r === 'echec' ? 'rouge' : r === 'refuse' ? 'rouge' : (r === 'dry-run' || r === 'lance') ? 'ambre' : 'mint'

export function Journal({ data, onOpen, onAujourdhui }:
  { data: CircuitData; onOpen: Ouvrir; onAujourdhui?: (n: number) => void }) {
  const [type, setType] = useState('')     // '' = tous
  const [page, setPage] = useState(1)
  const taille = 50
  const q = useQuery({
    queryKey: ['circuit-journal', type, page],
    queryFn: () => getAdminCircuitJournal({ type: type || undefined, page, taille }),
  })

  useEffect(() => { if (q.data && onAujourdhui) onAujourdhui(q.data.aujourdhui) }, [q.data, onAujourdhui])

  // résout la cible d'une entrée vers une page de détail (réservoir par nom/slug, robinet par id/nom).
  const resoudre = useMemo(() => {
    const res = new Map<string, number>(); const rob = new Map<string, string>()
    for (const r of data.reservoirs) { res.set(r.nom, r.id); if (r.slug) res.set(r.slug, r.id) }
    for (const r of data.robinets) { rob.set(r.id, r.id); rob.set(r.nom, r.id) }
    return (cible: string): { type: 'reservoir' | 'robinet'; id: number | string } | null =>
      res.has(cible) ? { type: 'reservoir', id: res.get(cible)! }
        : rob.has(cible) ? { type: 'robinet', id: rob.get(cible)! } : null
  }, [data])

  const gestes = ['tous', ...(q.data?.gestes || [])]
  const entrees = q.data?.entrees || []
  const total = q.data?.total || 0
  const pages = Math.max(1, Math.ceil(total / taille))

  return (
    <div>
      <div className="jf">
        {gestes.map((g) => (
          <button key={g} className={(type === '' && g === 'tous') || type === g ? 'on' : ''}
            onClick={() => { setType(g === 'tous' ? '' : g); setPage(1) }}>{g}</button>
        ))}
      </div>
      <div className="jl h"><span>quand</span><span>geste</span><span>cible</span><span>par</span><span>résultat</span></div>
      {q.isLoading ? <div className="muted" style={{ padding: 12 }}>Chargement…</div>
        : entrees.length === 0 ? <div className="muted" style={{ padding: 12 }}>Aucune entrée.</div>
          : entrees.map((e: any, i: number) => {
            const cible = resoudre(e.cible)
            const c = couleurResultat(e.resultat)
            const ligne = (
              <>
                <span className="muted">{new Date(e.ts).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>
                <span className="g"><i className={c === 'mint' ? '' : c} />{e.geste}</span>
                <span>{e.cible}</span>
                <span className="muted">{e.par}</span>
                <span className={`r ${c === 'mint' ? '' : c}`}>{e.resultat}</span>
              </>
            )
            return cible
              ? <button key={i} className="jl" onClick={() => onOpen(cible.type, cible.id)}>{ligne}</button>
              : <div key={i} className="jl">{ligne}</div>
          })}
      <div className="jpage">
        <button className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>← Précédent</button>
        <span>page {page} / {pages} · {total} entrée{total > 1 ? 's' : ''}</span>
        <button className="btn" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Suivant →</button>
      </div>
    </div>
  )
}
