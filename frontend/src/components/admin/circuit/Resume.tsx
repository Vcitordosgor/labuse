// CIRCUIT-P (lot 2.1) — LE RÉSUMÉ. Ne montre QUE ce qui cloche : titre, quatre repères, trois
// groupes (À faire / À corriger / À décider), une ligne de fin. Chaque ligne emmène vers sa cible
// (page de détail ou circuit déplié). Le bloc `resume` est calculé côté serveur — ici, on le REND.
import type { Cible, CircuitData } from './types'

export function Resume({ data, onCible }: { data: CircuitData; onCible: (c: Cible) => void }) {
  const r = data.resume
  const [k0, k1, k2, k3] = r.kpis
  return (
    <div className="res">
      <h1>{r.total > 0 ? <><b>{r.total}</b> chose{r.total > 1 ? 's' : ''} à regarder</> : 'Tout coule.'}</h1>
      <div className="sub">
        {r.total > 0
          ? "Tout le reste est branché sur le moteur, sert la dernière version et dit la même chose partout."
          : "Tout est branché sur le moteur, sert la dernière version et dit la même chose partout."}
        {data.dernier_controle
          ? ` Dernier contrôle ${new Date(data.dernier_controle.ts).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}.`
          : ''}
      </div>

      <div className="kpis">
        <div className="kpi"><div className="v">{k0.valeur}<small>/ {k0.sur}</small></div><div className="l">{k0.libelle}</div></div>
        <div className="kpi"><div className="v">{k1.valeur}<small>/ {k1.sur}</small></div><div className="l">{k1.libelle}</div></div>
        <div className="kpi"><div className="v">{k2.valeur}</div><div className="l">{k2.libelle}</div></div>
        <div className="kpi"><div className="v"><code>{k3.valeur}</code></div><div className="l">{k3.libelle} · candidat {k3.candidat || 'aucun'}</div></div>
      </div>

      {r.groupes.map((g) => (
        <div key={g.titre}>
          <div className="sect"><h2>{g.titre}</h2><span>{g.lignes.length}</span></div>
          {g.lignes.length === 0
            ? <div className="okline"><i /><b>Rien.</b></div>
            : g.lignes.map((li, i) => (
              <button key={i} className={`item ${li.couleur}`} onClick={() => onCible(li.cible)}>
                <span className="num">{li.n}</span>
                <span><span className="t">{li.titre}</span><span className="d">{li.phrase}</span></span>
                <span className="go">{li.verbe} →</span>
              </button>
            ))}
        </div>
      ))}

      <div className="okline" style={{ marginTop: 22 }}>
        <i />
        <span><b>{r.reste.reservoirs} réservoirs · {r.reste.robinets} robinets · {r.reste.chiffres} chiffres</b>
          {' '}— tout ce qui n'est pas listé ci-dessus va bien.</span>
      </div>
    </div>
  )
}
