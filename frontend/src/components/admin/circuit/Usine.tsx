// COCKPIT-1 — « L'usine » : la page atteinte depuis « Voir l'usine » du Tableau de bord. Elle liste
// le registre des jobs (4 familles) avec dernier/prochain passage et les gestes possibles.
//
// ⚠ Lot A : SQUELETTE (en-tête + retour). Le détail des 4 colonnes de postes est posé au Lot B.
export function Usine({ onBack }: { onBack: () => void }) {
  return (
    <div className="ck">
      <div className="ck-head">
        <span className="right" />
        <button className="btn" onClick={onBack}>← Tableau de bord</button>
      </div>
      <div className="ck-sect">
        <div className="ck-head"><h2>L'usine</h2>
          <span className="sub">les postes, chacun à sa place</span></div>
        <div className="okline"><i /> La vue détaillée des postes (4 familles, dernier &amp; prochain
          passage, gestes) arrive au Lot&nbsp;B.</div>
      </div>
    </div>
  )
}
