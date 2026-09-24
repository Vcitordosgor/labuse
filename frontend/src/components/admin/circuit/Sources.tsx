// CIRCUIT-P4 (lot 3) — L'ONGLET « SOURCES » : où en est chaque source servie.
// Un tableau, une ligne par source servie (vitrine) : nom + famille · millésime servi (+ date
// d'injection) · version chez le producteur · dernier contrôle (date + sonde/agent) · état · un
// bouton SEULEMENT si une action existe. ⟳ sur les automatiques. Recherche. Segment Vitrine / Hors
// vitrine : le hors-vitrine (alias, retirées, internes, hubs, à obtenir) avec statut, RAISON en
// français et date de décision — rien n'y est masqué. Clic sur une ligne vitrine → page de détail.
import { useMemo, useState } from 'react'

import type { CircuitData, Reservoir } from './types'

const jour = (iso?: string | null) => (iso ? iso.slice(0, 10).split('-').reverse().join('/') : '—')
const ETATS = ['à jour', 'nouvelle version', 'échue', 'jamais vérifiée', 'sonde en panne'] as const
const COUL: Record<string, string> = {
  'à jour': 'mint', 'nouvelle version': 'ambre', 'échue': 'ambre',
  'jamais vérifiée': 'gris', 'sonde en panne': 'rouge',
}
const estSonde = (m?: string) => ['api', 'page', 'entete', 'temoin'].includes(m || '')
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
const action = (r: Reservoir): string | null =>
  r.etat[1] === 'nouvelle version' ? 'Injecter' : r.etat[1] === 'échue' ? 'Déposer' : null

export function Sources({ data, onOpen }: { data: CircuitData; onOpen: (id: number) => void }) {
  const [seg, setSeg] = useState<'vit' | 'hors'>('vit')
  const [q, setQ] = useState('')
  const [actifs, setActifs] = useState<Set<string>>(new Set(ETATS))
  const comptes = data.etats_sources
  const hv = data.hors_vitrine ?? []

  const cherche = (s: string) => !q || s.toLowerCase().includes(q.toLowerCase())
  const vitrine = useMemo(
    () => data.reservoirs.filter((r) => actifs.has(r.etat[1]) && cherche(`${r.nom} ${r.famille}`)),
    [data.reservoirs, actifs, q],
  )
  const toggle = (e: string) =>
    setActifs((s) => { const n = new Set(s); n.has(e) ? n.delete(e) : n.add(e); return n })

  return (
    <div>
      <div className="src-bar">
        <input className="search" value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="Chercher une source (cadastre, permis, PLU, LiDAR…)" />
        <div className="seg">
          <button className={seg === 'vit' ? 'on' : ''} onClick={() => setSeg('vit')}>
            Vitrine {comptes?.total ?? data.reservoirs.length}
          </button>
          <button className={seg === 'hors' ? 'on' : ''} onClick={() => setSeg('hors')}>
            Hors vitrine {hv.length}
          </button>
        </div>
      </div>

      {seg === 'vit' ? (
        <>
          {comptes && (
            <div className="src-chips">
              {ETATS.map((e) => (
                <button key={e} className={`chip ${actifs.has(e) ? 'on' : ''}`} onClick={() => toggle(e)}>
                  <i style={{ background: `var(--${COUL[e]})` }} />{cap(e)} {comptes[e] ?? 0}
                </button>
              ))}
            </div>
          )}
          <table className="src">
            <thead><tr>
              <th style={{ width: '32%' }}>Source</th><th>Millésime servi</th>
              <th>Chez le producteur</th><th>Dernier contrôle</th><th>État</th><th />
            </tr></thead>
            <tbody>
              {vitrine.map((r) => {
                const v = r.veille
                const act = action(r)
                return (
                  <tr className="row" key={r.id} onClick={() => onOpen(r.id)}>
                    <td>
                      <div className="nm">{r.nom}</div>
                      <div className="fam">{r.famille}
                        {estSonde(v?.methode) && <span className="clock">⟳ {r.cadence_jours ? `${r.cadence_jours} j` : 'auto'}</span>}
                      </div>
                    </td>
                    <td className="date">{r.millesime || '—'}
                      <small>{r.ingere_le ? `injectée le ${jour(r.ingere_le)}` : '—'}</small></td>
                    <td className="date">{v?.vu || '—'}
                      <small>{v?.vu ? 'vue par la sonde' : 'pas de sonde'}</small></td>
                    <td className="date">{v?.passage ? jour(v.passage) : 'jamais'}
                      <small>{estSonde(v?.methode) ? 'sonde' : 'agent'}</small></td>
                    <td><span className={`stt ${r.etat[0]}`}><i />{r.etat[1]}</span></td>
                    <td className="act">
                      {act && <button className="btn" onClick={(e) => { e.stopPropagation(); onOpen(r.id) }}>{act}</button>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <div className="src-foot">
            Une ligne = une source servie au client. Clic sur une ligne : ce qu'elle alimente,
            ce qu'elle déclenche, son historique.
          </div>
        </>
      ) : (
        <>
          <table className="src">
            <thead><tr>
              <th style={{ width: '32%' }}>Source</th><th>Statut</th>
              <th>Pourquoi elle n'est pas en vitrine</th><th>Depuis</th>
            </tr></thead>
            <tbody>
              {hv.filter((h) => cherche(`${h.nom} ${h.famille}`)).map((h) => (
                <tr key={h.id}>
                  <td><div className="nm">{h.nom}</div></td>
                  <td>{h.statut_label}</td>
                  <td className="src-why">{h.raison}</td>
                  <td className="date">{jour(h.depuis)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="src-foot">
            Rien ici n'est perdu : une source retirée garde ses données et sa raison, un alias
            empêche de réinjecter deux fois la même chose.
          </div>
        </>
      )}
    </div>
  )
}
