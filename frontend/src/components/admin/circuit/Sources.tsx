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

// CIRCUIT-P7 (lot 2) — l'ordre du tri : les problèmes d'abord (sonde en panne → nouvelle version →
// échue → jamais vérifiée → à jour), puis le nom. Une source non classée tombe en dernier.
const RANG: Record<string, number> = {
  'sonde en panne': 0, 'nouvelle version': 1, 'échue': 2, 'jamais vérifiée': 3, 'à jour': 4,
}
// CIRCUIT-P7 (lot 2) — le « mode d'entrée » lisible (comment la donnée entre), sous le nom.
const SONDE_LABEL: Record<string, string> = {
  api: 'sonde API', page: 'sonde page', entete: 'sonde en-tête', temoin: 'sonde témoin',
}
const modeEntree = (r: Reservoir): string => {
  const m = r.veille?.methode as string | undefined
  if (m && SONDE_LABEL[m]) return SONDE_LABEL[m]
  if (m === 'agent') return 'veille agent'
  if (m === 'rappel') return 'rappel manuel'
  return r.mode === 'depot_manuel' ? 'dépôt manuel'
    : r.mode === 'en_direct' ? 'flux continu'
      : r.mode === 'sans_millesime' ? 'sans millésime'
        : 'ingestion'
}
// CIRCUIT-P7 (lot 2) — la sous-ligne de « Dernier contrôle » : sonde / agent / échéance.
const controleLabel = (r: Reservoir): string => {
  if (r.veille && estSonde(r.veille.methode)) return 'sonde'
  if (r.veille?.methode === 'agent') return 'agent'
  if (r.mode === 'depot_manuel') return r.etat[1] === 'échue' ? 'échéance dépassée' : 'échéance'
  if (r.mode === 'sans_millesime') return 'sans objet'
  return '—'
}

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
  // CIRCUIT-P7 (suite) — « Envoyer les agents » lance l'agent LLM RÉEL (coût) : on confirme d'abord,
  // en affichant le coût estimé et le plafond par passage. La sonde sans coût reste sur son bouton.
  const [pending, setPending] = useState<{ portee: Portee; n: number; cout: number } | null>(null)
  const s: any = data.sonde
  const a: any = data.agents
  const per = a?.vitrine ? (a.cout_estime_tous || 0) / a.vitrine : 0
  const estime = (p: Portee): { n: number; cout: number } =>
    p === 'jamais' ? { n: a?.jamais ?? 0, cout: (a?.jamais ?? 0) * per }
      : p === 'g8' ? { n: a?.g8 ?? 0, cout: (a?.g8 ?? 0) * per }
        : { n: a?.vitrine ?? 0, cout: a?.cout_estime_tous ?? 0 }
  const choisir = (p: Portee) => { setMenu(false); setPending({ portee: p, ...estime(p) }) }
  const confirmer = () => { if (pending) onAgents(pending.portee); setPending(null) }
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
          <button className="btn mauve" disabled={agentsEnCours}
            onClick={() => { setPending(null); setMenu((m) => !m) }}>Envoyer les agents ▾</button>
          {menu && !pending && (
            <div className="menu-liste">
              <button onClick={() => choisir('tous')}>
                Sur les {a?.vitrine ?? 0} sources <span className="muted">(≈ {eur(a?.cout_estime_tous)})</span></button>
              <button onClick={() => choisir('jamais')}>
                Sur les {a?.jamais ?? 0} jamais vérifiées <span className="muted">(≈ {eur(estime('jamais').cout)})</span></button>
              <button onClick={() => choisir('g8')}>
                Sur les {a?.g8 ?? 0} du verrou G8 <span className="muted">(≈ {eur(estime('g8').cout)})</span></button>
              <div className="sep" />
              <button disabled><span className="muted">Une source… (depuis sa fiche)</span></button>
            </div>
          )}
          {pending && (
            <div className="menu-liste confirm">
              <div className="cf-txt">Agent LLM sur <b>{pending.n}</b> source{pending.n > 1 ? 's' : ''} —
                coût estimé <b>≈ {eur(pending.cout)}</b>. Plafond <b>{eur(a?.plafond_eur)}</b> par passage :
                l'envoi s'arrête dès qu'il est atteint.</div>
              <div className="cf-acts">
                <button className="btn" onClick={() => setPending(null)}>Annuler</button>
                <button className="btn mauve" onClick={confirmer}>Envoyer les agents</button>
              </div>
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
  // CIRCUIT-P7 (lot 2) — un seul état actif (« Toutes » par défaut) ; le filtre FILTRE (test).
  const [etatActif, setEtatActif] = useState<string>('tous')
  const comptes = data.etats_sources
  const hv = data.hors_vitrine ?? []

  const cherche = (s: string) => !q || s.toLowerCase().includes(q.toLowerCase())
  const vitrine = useMemo(
    () => data.reservoirs
      .filter((r) => (etatActif === 'tous' || r.etat[1] === etatActif) && cherche(`${r.nom} ${r.famille}`))
      .sort((a, b) => (RANG[a.etat[1]] ?? 9) - (RANG[b.etat[1]] ?? 9) || a.nom.localeCompare(b.nom, 'fr')),
    [data.reservoirs, etatActif, q],
  )

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
                <button key={e} className={`chip ${etatActif === e ? 'on' : ''}`} onClick={() => setEtatActif(e)}>
                  <i style={{ background: `var(--${COUL[e]})` }} />{cap(e)} {comptes[e] ?? 0}
                </button>
              ))}
              {/* « Toutes » EN DERNIER à droite (règle des filtres). */}
              <button className={`chip ${etatActif === 'tous' ? 'on' : ''}`} onClick={() => setEtatActif('tous')}>
                Toutes {comptes.total}
              </button>
            </div>
          )}
          <div className="svt">
            <div className="svt-h">
              <div>Source</div><div>Servi</div><div>Chez le producteur</div>
              <div>Dernier contrôle</div><div>État</div><div />
            </div>
            {vitrine.map((r) => {
              const v = r.veille
              const act = action(r)
              return (
                <div className="svt-r" key={r.id} onClick={() => onOpen(r.id)}>
                  <div className="svt-nm">
                    <i className={`dot ${r.etat[0]}`} />
                    <div>
                      <div className="nm">{r.nom}</div>
                      <div className="fam">{r.producteur} · {r.famille} · {modeEntree(r)}
                        {r.cadence_jours ? <span className="clock"> · ⟳ {r.cadence_jours} j</span> : null}</div>
                    </div>
                  </div>
                  <div className="cel">{r.millesime || '—'}
                    <small>{r.ingere_le ? `injecté le ${jour(r.ingere_le)}` : '—'}</small></div>
                  <div className={`cel ${v?.vu ? '' : 'vide'}`}>{v?.vu || '—'}
                    <small>{v?.passage ? `vu le ${jour(v.passage)}` : (r.sans_millesime ? 'sans millésime' : '—')}</small></div>
                  <div className={`cel ${r.dernier_controle ? '' : 'vide'}`}>{r.dernier_controle ? jour(r.dernier_controle) : 'jamais'}
                    <small>{controleLabel(r)}</small></div>
                  <div><span className={`stt ${r.etat[0]}`}><i />{r.etat[1]}</span></div>
                  <div className="act">
                    {act && <button className="btn" onClick={(e) => { e.stopPropagation(); onOpen(r.id) }}>{act}</button>}
                  </div>
                </div>
              )
            })}
            <div className="svt-foot">
              {vitrine.length} source{vitrine.length > 1 ? 's' : ''}
              {etatActif !== 'tous' ? ` · ${cap(etatActif)}` : ''}{q ? ` · « ${q} »` : ''}. Une ligne = une
              source servie ; clic = sa fiche (ce qu'elle alimente, ce qu'elle déclenche, son historique).
            </div>
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
