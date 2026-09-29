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
| F19 | PermitsProximityBlock:42 | `distance_m <= 100` ne décide QU'UNE couleur (violet) d'emphase pour les permis proches — tous les permis sont affichés, la distance est servie & affichée en clair. Aucune donnée ni libellé décidé. |
| F30 | TimeMachine:84 | `periodAn >= 2016` GÈRE la disponibilité d'une surcouche viewer (le cadastre d'époque n'existe qu'à partir de 2017 ; 2016-2020 le recouvre). Fait historique FIXE de couverture de données, pas un chiffre que le client lit — plomberie du comparateur d'orthos. *(Servable si la couverture cadastre devient dynamique.)* |
| F06 | moteurs:346/353/716 (+303) | glyphe de signe (« + », flèche ↑/↓/→) et couleur selon le SIGNE d'une valeur servie (pct, charge cumulée) = présentation ; le compte « N parcelles sans droits à bâtir » (moteurs:303) est une AGRÉGATION UI des items servis par `sdp_m2 > 0` (sens inhérent de la SDP), pour l'action « retirer les vides ». |
| F08 (part) | status.ts:229 + 298-303 | `completudeColor` (couleur selon ≥ 50 %) et `ageSignal` (couleur par bande d'âge + TEMPS RELATIF « il y a N mois » calculé au front, comme `ilYA` de format.ts) = présentation. |
| F16 | FiltreLabuse:820 | note descriptive « Terrain nu = aucune emprise bâtie ≥ 5 % » : le front ne DÉCIDE pas nu/bâti (la partition est une clause SQL back, seuil 5 % fixe et documenté) ; il la DÉCRIT. *(Servable si le seuil devient configurable.)* |

## Arrêté pour décision (touche le scoring)
| F08 (part) | status.ts:33 | `PRIORITE_SERVIE = false` est le DRAPEAU DE POLITIQUE du scoring (miroir de `tiers_client.PRIORITE_SERVIE`, égalité garantie par un test anti-dérive). Le repasser à True est une décision de scoring (Vic, réversible) ; le servir de façon asynchrone casserait les dérivations synchrones de `TIER_V2_META`. → arrêté. |
