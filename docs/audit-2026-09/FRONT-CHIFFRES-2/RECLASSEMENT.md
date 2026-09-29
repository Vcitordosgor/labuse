# FRONT-CHIFFRES-2 — reclassements « présentation pure »

Familles que FRONT-CHIFFRES-1 avait classées `remonter_back` (prudence) mais qui, à la lecture,
ne DÉCIDENT aucun chiffre / seuil / plafond / conversion / libellé : elles ne font que colorer ou
graduer une valeur DÉJÀ SERVIE. Une couleur ou un cran de jauge n'est pas un chiffre hors registre
(le verrou front FC-1 ne les vise pas). → reclassées `legitime` (règle « présentation pure : rien à
faire, listé comme tel »).

| famille | ligne(s) | ce que fait le front | pourquoi présentation |
|---|---|---|---|
| F11 | risques.tsx:22/24 | niveau d'aléa (catégoriel **servi**) → cran 0..3 de Jauge3 | le code le dit déjà : « présentation, aucun seuil inventé » ; `rédhibitoire` est un flag servi |
| F15 | RadarMarcheColonne.tsx:19/181 | couleur ambre/menthe selon le SIGNE de l'écart servi ; gris si `niveau === 'indicatif'` (**servi**) | couleur d'un signe, gris d'un niveau servi — aucun libellé décidé |
| F17 | Ia.tsx:165 | teinte rouge si `depense_eur >= budget_eur` (deux valeurs **servies**) | comparaison de deux servis → couleur seule (admin) |
| F22 | formes.tsx:99 | couleur des crans de Jauge3 selon le `niveau` (**prop servie**) | couleur d'un cran servi ; le nombre de crans vient de la donnée |

## ~~Arrêté pour décision~~ → REMONTÉ (décision Vic : servir la DA avec le tier)

| famille | ligne(s) | raison |
|---|---|---|
| F13 | ProjetKanban.tsx:37 | mapping `tier` (sortie du **scoring** brûlante/chaude/…) → couleur de pastille |
| F29 | TierBadge.tsx:9 | mapping hex→ton du badge de **verdict tier** (scoring) |

**Résolu (F13/F29 remontés).** Décision Vic : le back sert, à côté du tier, sa couleur (jeton DA)
et son libellé (`/vocabulaire/paliers`, source `scoring/tiers_client`). Pastille et badge lisent la
même carte ; à q_v15 (bandes A/B/C/D) un seul endroit change. La pastille F13 est corrigée au
passage (elle colorait `brulante` en « Priorité » alors que PRIORITE_SERVIE=false le résout en « À
suivre » — cf. CHANGEMENTS.csv).

## Lot P1 (suite) — reclassements présentation
| famille | ligne(s) | pourquoi présentation |
|---|---|---|
| F07 | ContextePanel:27/465/498 | SRU_META mappe le `statut` SERVI (carencée/déficitaire) → couleur+label+lecture ; :465/:498 = couleur selon le SIGNE d'une valeur servie (tendance/écart). Aucun chiffre décidé. |
| F20 | ProprietaireHistorique:25 | `n_millesimes < 2` : il faut AU MOINS deux millésimes pour tracer une frise / un changement — minimum inhérent, pas un seuil métier. `n_millesimes` est servi. |
| F24 | MapView:344 | `> 20 000` = plafond de RENDU (le front ne peut peindre 20k+ features à la parcelle) — contrainte technique d'affichage, pas une donnée que le client lit. *(Servable si Vic veut le rendre réglable.)* |
