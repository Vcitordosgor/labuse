// CIRCUIT-P4 (lot 2) — L'ONGLET « À FAIRE », onglet par défaut de la page Données.
// Une liste ORDONNÉE de gestes, calculée côté serveur (`/admin/circuit` → `a_faire`) ; le front ne
// recalcule rien. Cinq types de lignes seulement (Injecter · Déposer · Calculer · Basculer ·
// Décider), chacune avec un verbe et UN bouton d'action (plus, parfois, un lien discret « voir »/
// « lire »). Vide → « Rien à faire » + la phrase de contexte. Le bouton grisé porte SA raison.
import type { AFaireLigne, CircuitData } from './types'

const jour = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'

export function AFaire({ data, onGeste, onOuvrirSources }: {
  data: CircuitData
  onGeste: (l: AFaireLigne, quoi: 'bouton' | 'ghost') => void
  onOuvrirSources?: () => void   // CIRCUIT-P7 (lot 4) — « Rien d'autre » renvoie aux Sources (jamais vérifiées → agents)
}) {
  const af = data.a_faire
  if (!af) return <div className="muted">À faire — indisponible.</div>
  const n = af.total
  const c = af.calme
  const d = af.dates
  return (
    <div className="res">
      <div className="af-head">
        <h1>{n > 0 ? <><b>{n}</b> {n > 1 ? 'choses' : 'chose'} à faire</> : 'Rien à faire'}</h1>
      </div>
      {/* CIRCUIT-P7 (lot 4) — trois dates sous le titre : sonde · contrôle du circuit · agents. */}
      {d && (
        <div className="af-dates">
          <span>sonde des sources : {jour(d.sonde)}</span>
          <span>contrôle du circuit : {jour(d.controle)}</span>
          <span>agents : {jour(d.agents)}</span>
        </div>
      )}

      {n === 0 ? (
        <div className="af-calm">
          Tout coule. <b>{c.nouvelles}</b> nouvelle version chez les producteurs,{' '}
          <b>{c.pannes}</b> sonde en panne, <b>{c.vitrine}</b> sources en vitrine.
        </div>
      ) : (
        <>
          <div className="af-list">
            {af.lignes.map((l, i) => (
              <div key={i} className={`af-item ${l.couleur}`}>
                <span className="dot" />
                <div>
                  <div className="t">{l.titre}</div>
                  <div className="d">{l.phrase}</div>
                </div>
                <div className="af-acts">
                  {l.ghost && (
                    <button className="btn ghost" onClick={() => onGeste(l, 'ghost')}>{l.ghost.label}</button>
                  )}
                  <button className="btn mint" disabled={l.bouton.disabled}
                    title={l.bouton.raison || undefined}
                    onClick={() => onGeste(l, 'bouton')}>{l.bouton.label}</button>
                </div>
              </div>
            ))}
          </div>
          {/* CIRCUIT-P7 (lot 4) — « jamais vérifiée » ne fait PAS de ligne : elle appelle l'agent
              depuis Sources, dit ici dans « Rien d'autre ». */}
          <div className="af-calm">
            Rien d'autre.{' '}
            {c.jamais ? <><b>{c.jamais}</b> source{c.jamais > 1 ? 's' : ''} jamais vérifiée{c.jamais > 1 ? 's' : ''} attend{c.jamais > 1 ? 'ent' : ''} les agents — ou tu {onOuvrirSources
              ? <button className="lienc" onClick={onOuvrirSources}>les envoies depuis Sources</button>
              : 'les envoies depuis Sources'}. </> : null}
            <b>{c.vitrine}</b> sources en vitrine, <b>{c.pannes}</b> sonde en panne
            {c.derniere_bascule ? <>, dernière bascule le {c.derniere_bascule}</> : null}.
          </div>
        </>
      )}

      <p className="af-rules">
        Cinq gestes seulement peuvent apparaître ici : Injecter · Déposer · Calculer · Basculer ·
        Décider. Chaque pastille non verte du Circuit et de Sources a sa ligne ici, et ce compteur
        est celui de la tuile « tâches à effectuer » du Pilotage.
      </p>
    </div>
  )
}
