// DASHBOARD-4b lot 2 — LE SENS INVERSE, accessible depuis la page Données (recherche), pas seulement
// par lien profond : on tape une couche / une section de fiche / une carte commune / un outil (…) et on
// voit la liste de ses SOURCES, chacune cliquable vers son détail réservoir. Les données viennent de
// /sources/par-element (registre inversé) ; le clic source → détail via l'id du réservoir (nom → id).
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getSourcesParElement } from '../../../lib/api'
import type { CircuitData } from './types'

const CAT_LABEL: Record<string, string> = {
  couche: 'Couche carte', fiche_parcelle: 'Section fiche parcelle', fiche_commune: 'Carte fiche commune',
  outils: 'Outil', documents: 'Document', copilote: 'Copilote', radar: 'Radar',
}

export function SensInverse({ data, onOpenSource }: { data: CircuitData; onOpenSource: (id: number) => void }) {
  const [q, setQ] = useState('')
  const elements = useQuery({ queryKey: ['sources-par-element'], queryFn: getSourcesParElement, staleTime: 5 * 60_000 }).data?.elements ?? []
  const nom2id = new Map(data.reservoirs.map((r) => [r.nom, r.id]))
  const req = q.trim().toLowerCase()
  const res = req.length >= 2 ? elements.filter((e) => e.nom.toLowerCase().includes(req)).slice(0, 25) : []
  return (
    <div className="card sens-inverse">
      <h3>Sens inverse — d'un élément à ses sources</h3>
      <input className="si-input" value={q} onChange={(e) => setQ(e.target.value)}
        placeholder="Une couche, une section de fiche, une carte commune, un outil…" aria-label="Chercher un élément" />
      {req.length >= 2 && (res.length ? (
        <ul className="si-list">
          {res.map((e) => (
            <li key={e.id}>
              <div className="si-el"><b>{e.nom}</b><span className="muted"> · {CAT_LABEL[e.categorie] ?? e.categorie}</span></div>
              <div className="si-src">
                {e.sources.length ? e.sources.map((s) => {
                  const id = nom2id.get(s)
                  return <span key={s} className="chip" title={id != null ? `Voir la source « ${s} »` : s}
                    onClick={id != null ? () => onOpenSource(id) : undefined}>{s}{id != null ? ' ↗' : ''}</span>
                }) : <span className="muted">aucune source</span>}
              </div>
            </li>
          ))}
        </ul>
      ) : <div className="muted" style={{ marginTop: 8 }}>aucun élément « {q} »</div>)}
      {req.length > 0 && req.length < 2 && <div className="muted" style={{ marginTop: 8 }}>tapez au moins deux lettres</div>}
    </div>
  )
}
