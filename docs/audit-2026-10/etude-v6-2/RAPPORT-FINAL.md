# ÉTUDE V6-2 — Rapport final

Recette V6-2 sur `feat/etude-v6` (worktree `labuse-etude-v6`, ports 8860/6060). 5 lots + 2 corrections
sur Étang-Salé. **Un lot = un commit. Branche NON mergée — en attente de recette.**

## Les lots

### Lot 1 — surfaces : défauts garantis, plus de fuite de l'éditeur (`87a2a6f38`)
La valeur bricolée dans « Hypothèses modifiables » (T1 = 9 m²) fuyait vers l'étape 3 / le récap. Désormais
l'étape 3 + le récap lisent TOUJOURS les défauts `SURF` (T1 30/6, T2 56/9, T3 70/12, T4 80/14) ;
« Modifier le programme » remet l'éditeur à zéro ; « Votre demande » (résultat) lit le PAYLOAD analysé =
même source que le PDF ; le back échoe les varangues. **10 T1 = 300 m² dont 60 varangues / 240 intérieur.**

### Lot 2 — capacité stable + facteur limitant juste (`1b3cb99df`)
Capacité maximale = meilleur candidat FAISABLE de la recherche (≥ toute variante dessinée, stable : deux
demandes de même répartition → même maximum). Facteurs limitants CLASSÉS par impact ; le stationnement
n'est dit limitant qu'après contrefactuel « sans places » (lu dans la même recherche). Confrontation
demande ↔ maximum servie.

### Lot 3 — stationnement en sous-sol + bornes 60/75 s + vitesse < 20 s (`a6e89ad48`)
Toggle aérien (défaut) / sous-sol ; places au −1, rampe au sol, emprise sous-sol ≤ emprise réglementaire ;
CTA « Testez en sous-sol » quand l'aérien plafonne ; même study_id → même PDF. Borne du moteur 30 → 60 s,
alignée ~75 s (nginx, Caddy, uvicorn, fetch front ; geste de prod pour Vic dans `docs/deploiement/`).
« Calcul en cours, jusqu'à une minute » pendant le calcul. Sous-sol calculé seulement au clic → < 20 s.
- **Correction 1 (`3174af8c1`)** : pleine terre au-dessus du sous-sol (jamais perméable) → 30 % appliqués
  sur la pleine terre réelle ; rampe réaliste ; hauteur sur pente signalée ; règles UA non vérifiées listées.
- **Correction 2 (`6fe96a1ba`)** : gradins **mesurés sur LiDAR** (R+3 en 3 gradins, relief 3,5–4,5 m) ;
  **espaces verts 20 % + marge plantée 2 m calibrées UA 2.6 et appliquées** ; rampe **58,3 m²** (calcul montré).

### Lot 4 — jauge d'enveloppe estimée à l'étape 3 (`b4a942d9c`)
Endpoint rapide `/modules/etude/jauge` (sans moteur, ~0,2 s). Enveloppe « estimé » = (zone d'implantation −
sol du stationnement aérien) × niveaux (hauteur PLU) × coef plancher, comparée au programme saisi. Bandeau
rouge au dépassement, jauge grise « non estimable » si donnée manque, divergence estimation ↔ calcul > 20 %
signalée au résultat.

### Lot 5 — écrans (HEAD de `feat/etude-v6`)
Champ de recherche vidé après chaque ajout (étape 1) ; règles PLU **par parcelle**, citées (étape 1) ;
récap « — » tant que non choisi (jamais 0 ni « Non vérifié ») ; bandeaux descriptifs bas de page supprimés
aux 3 étapes (seulement Retour / Continuer / Analyser).

## Recette Étang-Salé (AW 99/451/624/625, UA, 1 746 m²)
- **Lot 1** : 10 T1 = 300 m² (60 varangues / 240 intérieur), aucune fuite.
- **Capacité** : aérien **32 R+3** / sous-sol **44 R+3** (après corrections), stable entre deux demandes
  de même répartition.
- **Facteur limitant** (aérien) : stationnement prouvé (−12/−16 logts par contrefactuel), puis hauteur.
- **Sous-sol** : 44 places au −1, emprise 1 100 m², rampe 58,3 m², 365 m² sur dalle retirés de la pleine
  terre, gradins R+3 mesurés, EV 20 % + marge 2 m vérifiés.
- **Jauge étape 3** : 23 T2 + 6 T3 → 1 708 / 1 854 m² (92 %, vert) ; divergence calcul 5 % (< 20 %).
- **Écart à l'architecte (29)** expliqué chiffré : massing (bâti 735 vs ~547 m²), partie R+2 pente,
  programme (29) vs maximum (44). En aérien 32 vs 29 = +10 %.

## Recette Saint-Denis (DL 247/248, Ui, PPR)
Fonctionne toujours (pas de 503) sous la nouvelle borne ; capacité calculée < 20 s ; les champs Lot 2/4
servis. **Rien de cassé par V6-2.**

## Vérifications (à chaque lot)
tsc 0 · vitest **298/298** · pytest implantation **164 passed** (2 `test_route_*` pré-existants =
TestClient sur DB de test vide, sans rapport avec V6-2) · **chasse_docs 20·0·0** (garde E-04 alignée sur
la borne 60 s) · **chasse_donnees 23·0·2 SKIP**.

## Reste à faire (hors code)
- **Déploiement timeouts** (Vic) : `docs/deploiement/etude-v6-2-timeouts.md` (nginx/Caddy + uvicorn + rebuild front).
- **Merge** : en attente de la recette. Services arrêtés.

## Preuves
`docs/audit-2026-10/etude-v6-2/` : rapports lot1→lot5 + corrections + captures
(lot1 300 / lot2 capacité-facteurs / lot3 sous-sol + corrections / lot4 jauge / lot5 écrans).
