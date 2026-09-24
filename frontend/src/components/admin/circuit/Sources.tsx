// CIRCUIT-P4 (lot 3) — L'ONGLET « SOURCES » : où en est chaque source servie.
// Un tableau, une ligne par source servie (vitrine) : nom + famille · millésime servi (+ date
// d'injection) · version chez le producteur · dernier contrôle (date + sonde/agent) · état · un
// bouton SEULEMENT si une action existe. ⟳ sur les automatiques. Recherche. Segment Vitrine / Hors
// vitrine : le hors-vitrine (alias, retirées, internes, hubs, à obtenir) avec statut, RAISON en
// français et date de décision — rien n'y est masqué. Clic sur une ligne vitrine → page de détail.
import { useMemo, useState } from 'react'

import type { Portee } from './Circuit'
import type { CircuitData, Reservoir } from './types'

const jour = (iso?: string | null) => (iso ? iso.slice(0, 10).split('-').reverse().join('/') : '—')
const quandCourt = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'
const eur = (n?: number | null) =>
  n == null ? '—' : `${n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`
const ETATS = ['à jour', 'nouvelle version', 'échue', 'jamais vérifiée', 'sonde en panne'] as const
const COUL: Record<string, string> = {
  'à jour': 'mint', 'nouvelle version': 'ambre', 'échue': 'ambre',
  'jamais vérifiée': 'gris', 'sonde en panne': 'rouge',
}
const estSonde = (m?: string) => ['api', 'page', 'entete', 'temoin'].includes(m || '')
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)
const action = (r: Reservoir): string | null =>
  r.etat[1] === 'nouvelle version' ? 'Injecter' : r.etat[1] === 'échue' ? 'Déposer' : null

// CIRCUIT-P7 (lot 1) — LES DEUX CARTES en tête de Sources : la Sonde de nuit (cadence, dernier
// passage, interrogées / en panne / nouvelles vues, bouton « Sonder maintenant ») et les Agents
// (dernier passage, coût du ledger, plafond, prochain dimanche, menu de portée). Tous les chiffres
// viennent du backend (`data.sonde` / `data.agents`) — le front ne recompte rien.
function Cartes({ data, tacheSonde, tacheAgents, onSonder, onAgents }: {
  data: CircuitData
  tacheSonde?: any; tacheAgents?: any
  onSonder: () => void; onAgents: (p: Portee) => void
}) {
  const [menu, setMenu] = useState(false)
  const s: any = data.sonde
  const a: any = data.agents
  const sondeEnCours = tacheSonde?.etat === 'en_cours'
  const agentsEnCours = tacheAgents?.etat === 'en_cours'
  const finiAgents = tacheAgents && (tacheAgents.etat === 'termine' || tacheAgents.etat === 'echec')
  const pct = agentsEnCours && tacheAgents.total ? Math.round((tacheAgents.fait / tacheAgents.total) * 100) : 0
  return (
    <div className="controles">
      <div className="carte controle">
        <div>
          <div className="titre"><i className="past ok" />Sonde de nuit</div>
          <div className="desc">
            {s ? <>À {s.cadence}, interroge les {s.interrogeables} sources qui ont un amont.{' '}
              {s.dernier_passage
                ? <>Dernier passage {quandCourt(s.dernier_passage)} : {s.interrogees} interrogées,{' '}
                  {s.en_panne} en panne, {s.nouvelles} nouvelle{s.nouvelles > 1 ? 's' : ''} version{s.nouvelles > 1 ? 's' : ''} vue{s.nouvelles > 1 ? 's' : ''}.</>
                : <>Jamais passée encore.</>}</>
              : 'Sonde indisponible.'}
          </div>
        </div>
        <button className="btn" disabled={sondeEnCours} onClick={onSonder}>
          {sondeEnCours ? 'Sonde en cours…' : 'Sonder maintenant'}
        </button>
      </div>

      <div className="carte controle agents">
        <div style={{ flex: 1 }}>
          <div className="titre"><i className="past mauve" />Agents</div>
          <div className="desc">
            {a ? <>Chaque dimanche, vont lire chez les {a.vitrine} producteurs.{' '}
              {a.dernier_passage
                ? <>Dernier passage {quandCourt(a.dernier_passage)} : {a.sources} sources,{' '}
                  {eur(a.cout_eur)}, {a.nouvelles} nouvelle{a.nouvelles > 1 ? 's' : ''} version{a.nouvelles > 1 ? 's' : ''} trouvée{a.nouvelles > 1 ? 's' : ''}.</>
                : <>Aucun passage encore.</>}{' '}
              {a.actif
                ? <>Plafond {eur(a.plafond_eur)} par passage{a.prochain_dimanche ? `, prochain passage dimanche ${jour(a.prochain_dimanche)}` : ''}.</>
                : <>Plafond à <b>0 €</b> — aucun agent ne tourne (fixer {a.cle_env} pour les activer).</>}</>
              : 'Agents indisponibles.'}
          </div>
          {agentsEnCours && (
            <div className="agents-cours">
              <span>{tacheAgents.message || 'Agents en cours…'}</span>
              <div className="barre"><i style={{ width: `${pct}%` }} /></div>
            </div>
          )}
          {!agentsEnCours && finiAgents && (
            <div className="agents-cours"><span>{tacheAgents.message} — écrit au journal</span></div>
          )}
        </div>
        <div className="menu">
          <button className="btn mauve" onClick={() => setMenu((m) => !m)}>Envoyer les agents ▾</button>
          {menu && (
            <div className="menu-liste">
              <button onClick={() => { setMenu(false); onAgents('jamais') }}>
                Sur les {a?.jamais ?? 0} jamais vérifiées</button>
              <button onClick={() => { setMenu(false); onAgents('g8') }}>
                Sur les {a?.g8 ?? 0} du verrou G8</button>
              <button onClick={() => { setMenu(false); onAgents('tous') }}>
                Sur les {a?.vitrine ?? 0} sources <span className="muted">(≈ {eur(a?.cout_estime_tous)})</span></button>
              <div className="sep" />
              <button disabled><span className="muted">Une source… (depuis sa fiche)</span></button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function Sources({ data, onOpen, tacheSonde, tacheAgents, onSonder, onAgents }: {
  data: CircuitData; onOpen: (id: number) => void
  tacheSonde?: any; tacheAgents?: any
  onSonder?: () => void; onAgents?: (p: Portee) => void
}) {
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
      {onSonder && onAgents && (
        <Cartes data={data} tacheSonde={tacheSonde} tacheAgents={tacheAgents}
          onSonder={onSonder} onAgents={onAgents} />
      )}
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
