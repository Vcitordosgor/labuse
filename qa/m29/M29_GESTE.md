# M29 — GESTE (b)/(b) : signaux #9 + #11 servis — POINT D'ARRÊT (05/08/2026)

## Implémenté (fiche seulement, AUCUN effet de classement)
- **#9** : `parcel_entree_tete` (scoring/lignee_tete.py) — 514 entrées tracées via la chaîne
  d'archives (pre_pond → pre_regle → pre_m28 → servi), toutes « signal inchangé » (gestes à
  features constantes). Libellé factuel arbitré, étiquette Sourcé (archives contrib_d/rang).
  À recalculer au geste de chaque bascule.
- **#11** : `parcel_acquerabilite` — 3 états factuels arbitrés : même propriétaire (PM) 329 ·
  propriétaires distincts (PM) 46 · propriété non déterminable 685. Source DGFiP/Cerema ;
  `source_millesime` : champ prévu, NULL tant que la sync amont n'est pas tracée → étiquette
  **Estimé** affichée telle quelle (spec millésime en attente).
- API : champs `entree_tete` + `acquerabilite` sur la fiche q_v2 (même gate prod
  LABUSE_M28_BADGES=1) ; frontend : deux lignes sobres sous le verdict.

## Non-régression (mesuré)
- Diff servi avant/après : **vide hors fiches** — aucune ligne de parcel_p_score_v2 touchée
  (le geste n'écrit que 2 nouvelles tables + code API/front). Tiers 119/1033 inchangés,
  checksum des rangs de tête inchangé (3 023 784).
- **Golden : 117/117 PASS, 0 incohérence base↔API** (gate ON).

## Fiches témoins (capturées, qa/m29/)
- `temoin_9.png` — AR2714 (chaude 1737) : « entrée en tête à la bascule du 04/08/2026 —
  signal inchangé (Sourcé) ».
- `temoin_11.png` — CX2538 (chaude 112, gérant âgé 81 ans) : « assemblage : même propriétaire
  (PM) — source DGFiP/Cerema (millésime amont non tracé — Estimé) ».

## BACKLOG
#9 fermée (signal servi) · #11 fermée part PM · **#11-PP consignée en dette distincte**,
manquant nommé (source PP inexistante en open data — structurel).
