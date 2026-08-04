# AUDIT 2 — RENOUVELLEMENT (lecture seule, commit=False)

Mort depuis la bascule v8 (table restée sur q_v7_defisc, 68 445 lignes — le segment ne sert
plus RIEN). Rebuild mesuré à blanc sur le run servi (`renouvellement.build(commit=False)`,
rollback, zéro écriture) :
- **67 258 parcelles** (entonnoir : 195 209 bâties exclues → 182 330 U/AU → 71 899 capacité
  → 70 128 hors copro → 67 258 hors foncier public) — vs 68 445 sur q_v7 (Δ −1 187, effet
  calibrage v8, sain).
- Poids inchangés (résiduel 40, assiette 25, marché 20, divisibilité 15) ; seuils SDP ≥ 100,
  surface ≥ 600.
- Durée du rebuild réel : ~2 min. Risque : AUCUN sur les tiers (table indépendante du
  scoring, lue par la fiche seulement).
**Reco : rebuild réel = 1 commande, à faire au prochain geste servi (avec MAJ golden si des
ancres portent le badge). À intégrer au geste de bascule (doctrine « toute table run-scopée
entre dans le geste ou est déclarée cache »).**
