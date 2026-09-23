// CIRCUIT-P4 (lot 2) — L'ONGLET « À FAIRE », onglet par défaut de la page Données.
// Une liste ORDONNÉE de gestes, calculée côté serveur (`/admin/circuit` → `a_faire`) ; le front ne
// recalcule rien. Cinq types de lignes seulement (Injecter · Déposer · Calculer · Basculer ·
// Décider), chacune avec un verbe et UN bouton d'action (plus, parfois, un lien discret « voir »/
// « lire »). Vide → « Rien à faire » + la phrase de contexte. Le bouton grisé porte SA raison.
import type { AFaireLigne, CircuitData } from './types'

export function AFaire({ data, onGeste }: {
  data: CircuitData
  onGeste: (l: AFaireLigne, quoi: 'bouton' | 'ghost') => void
}) {
  const af = data.a_faire
  if (!af) return <div className="muted">À faire — indisponible.</div>
  const n = af.total
  const c = af.calme
  return (
    <div className="res">
      <div className="af-head">
        <h1>{n > 0 ? <><b>{n}</b> {n > 1 ? 'choses' : 'chose'} à faire</> : 'Rien à faire'}</h1>
        {af.contexte && <span className="when">{af.contexte}</span>}
      </div>

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
          <div className="af-calm">
            Rien d'autre. <b>{c.nouvelles}</b> nouvelle version, <b>{c.pannes}</b> sonde en panne,{' '}
            <b>{c.vitrine}</b> sources en vitrine
            {c.derniere_bascule ? <>, dernière bascule le {c.derniere_bascule}</> : null}.
          </div>
        </>
      )}

      <p className="af-rules">
        Cinq gestes seulement peuvent apparaître ici : Injecter · Déposer · Calculer · Basculer ·
        Décider. Tout le reste est de l'information, dans Sources.
      </p>
    </div>
  )
}
