// CIRCUIT-P (lot 2.1) — LE RÉSUMÉ. Ne montre QUE ce qui cloche : titre, quatre repères, trois
// groupes (À faire / À corriger / À décider), une ligne de fin. Chaque ligne emmène vers sa cible
// (page de détail ou circuit déplié). Le bloc `resume` est calculé côté serveur — ici, on le REND.
// DASHBOARD-4 (D1) — les compteurs de la page = ceux des verrous ; (D2) — les verrous joués à la
// demande, résultat persistant (30 lignes phrase + état + preuve), un cassé = une ligne « à corriger ».
import type { Cible, CircuitData, VerrousTache } from './types'

export function Resume({ data, onCible, verrousTache, onRejouerVerrous, rejouerEnCours }: {
  data: CircuitData; onCible: (c: Cible) => void
  verrousTache?: VerrousTache; onRejouerVerrous?: () => void; rejouerEnCours?: boolean
}) {
  const r = data.resume
  const [k0, k1, k2, k3] = r.kpis
  const cc = data.compteurs_coherence
  // DASHBOARD-4 (D2) — le résultat persistant des verrous (30 lignes) ; sinon les 8 garanties servies
  // à chaque /admin/circuit servent d'aperçu en attendant un « Rejouer ».
  const vt = verrousTache
  const enCoursVerrous = vt?.etat === 'en_cours'
  const lignesVerrous = vt?.resultat?.lignes ?? null
  const garanties = data.garanties ?? null
  const picto = (v: string, avert?: boolean) => (v === 'ok' ? '✓' : v === 'casse' ? (avert ? '⚠' : '✗') : '…')
  const classeV = (v: string, avert?: boolean) => (v === 'ok' ? 'mint' : v === 'casse' ? (avert ? 'ambre' : 'rouge') : 'ambre')
  return (
    <div className="res">
      <h1>{r.total > 0 ? <><b>{r.total}</b> chose{r.total > 1 ? 's' : ''} à regarder</> : 'Tout coule.'}</h1>

      {/* DASHBOARD-4 (D1) — les compteurs, tels que les verrous les comptent (source unique). */}
      {cc && (
        <div className="cc-strip" title="Chaque nombre est lu de la fonction que les verrous lisent — jamais un compte propre à la page.">
          <span>Les compteurs, tels que les verrous les comptent :</span>
          <b>{cc.sources_vitrine ?? '—'}</b> sources vitrine <span className="cc-sep">·</span>
          <b>{cc.couches ?? '—'}</b> couches <span className="cc-sep">·</span>
          <b>{cc.donnees ?? '—'}</b> données <span className="cc-sep">·</span>
          <b>{cc.verrous}</b> verrous <span className="cc-plus">+</span> <b>{cc.garanties ?? '—'}</b> garanties
        </div>
      )}

      {/* DASHBOARD-4 (D2) — « labuse circuit verrous » jouable ici : progression + 30 lignes. */}
      <div className="verrous-bloc">
        <div className="verrous-tete">
          <h2>Verrous & garanties</h2>
          <button className="btn mint" disabled={enCoursVerrous || rejouerEnCours} onClick={onRejouerVerrous}>
            {enCoursVerrous ? `Verrous… ${vt?.fait ?? 0} / ${vt?.total ?? 30}` : 'Rejouer les verrous'}
          </button>
        </div>
        {vt?.resultat && (
          <div className="sub" style={{ margin: '0 0 8px' }}>
            {vt.resultat.bloquants.length === 0
              ? `Tout va bien — ${vt.resultat.joues} verrous joués, aucun bloquant.`
              : `À corriger : ${vt.resultat.bloquants.join(', ')} cassé(s).`}
            {vt.maj ? ` Dernier passage ${new Date(vt.maj).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}.` : ''}
          </div>
        )}
        {(lignesVerrous ?? garanties)?.map((g: any) => (
          <details key={g.id} className={`item ${classeV(g.verdict, g.avertissement)}`} style={{ cursor: 'default' }}>
            <summary style={{ display: 'flex', gap: 10, alignItems: 'baseline', listStyle: g.details?.length ? undefined : 'none' }}>
              <span className="num" style={{ minWidth: 30 }}>{g.id}</span>
              <span style={{ flex: 1 }}>
                <span className="t">{picto(g.verdict, g.avertissement)} {g.phrase}</span>
                <span className="d">{g.preuve}</span>
              </span>
            </summary>
            {g.details?.length > 0 && (
              <ul className="verrous-details">{g.details.map((x: string, i: number) => <li key={i}>{x}</li>)}</ul>
            )}
          </details>
        ))}
        {!lignesVerrous && (
          <div className="sub" style={{ marginTop: 4 }}>Aperçu des garanties ci-dessus — « Rejouer les verrous » joue aussi les {cc?.verrous ?? 22} verrous (30 lignes).</div>
        )}
      </div>

      <div className="sub">
        {r.total > 0
          ? "Tout le reste est branché sur le moteur, sert la dernière version et dit la même chose partout."
          : "Tout est branché sur le moteur, sert la dernière version et dit la même chose partout."}
        {data.dernier_controle
          ? ` Dernier contrôle ${new Date(data.dernier_controle.ts).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}.`
          : ''}
      </div>

      <div className="kpis">
        {/* CIRCUIT-P2 (lot 2.2) — le repère « N / 68 » ouvre au clic la page de détail du compteur. */}
        <button className="kpi lien" onClick={() => onCible({ type: 'compteur', ids: [] })}
          title="Voir les réservoirs par état, et les lignes en base non servies">
          <div className="v">{k0.valeur}<small>/ {k0.sur}</small></div><div className="l">{k0.libelle} →</div></button>
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
