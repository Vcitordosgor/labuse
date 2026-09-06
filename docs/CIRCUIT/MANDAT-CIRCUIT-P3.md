# MANDAT CIRCUIT-P3 — Deux lectures qui se contredisent

Branche : `feat/circuit-page`, worktree `~/Desktop/labuse-audit`. Chapitre « P3 » ajouté à `docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-P.md`, captures `RECETTE-CIRCUIT-P/P3-*.png`.
Autonomie : mêmes règles (aucune question, doutes écrits, branche jamais rouge, un commit et un push par lot, rien mergé).

## Le constat, recette Vic du 06/09 13h39, base locale

La base contient : `circuit_journal` 90 lignes · `circuit_ecarts` 1 · `circuit_eau_ancienne` 26 · `filtre_versions` 78 · `filtre_resultats` 195.

L'écran affiche pourtant :
- **Journal : « Aucune entrée. · page 1 / 1 · 0 passage »**, tous filtres confondus, alors que la veille au soir il affichait 78 entrées et que la table en a 90.
- **Colonne Robinets : « 130, 0 à regarder »** et « tout va bien » sur les douze catégories, pendant que le Résumé du même écran annonce « 2 fuites mesurées, 2 robinets » et « 1 robinet sert de l'eau ancienne ». Le repère dit « 130 / 130 robinets sans rien à signaler ».

Deux lectures du même état se contredisent sur la même page : c'est précisément ce que la règle 2.4 de CIRCUIT-P2 devait interdire, et son test n'a rien vu. Le test est donc faux aussi.

## Lot 1 — Le journal

- 1.1 Trouver pourquoi `GET /admin/circuit/journal` ne rend rien alors que la table est pleine : filtre de date implicite (« aujourd'hui » sur une horloge UTC contre des `ts` en heure Réunion, ou l'inverse), regroupement par lot qui écrase tout, jointure sur une cible devenue introuvable après le renommage en noms affichés, ou `type` par défaut qui ne correspond à aucune valeur en base. Écrire la cause exacte au compte-rendu.
- 1.2 Corriger, avec un test qui aurait attrapé : insérer trois lignes (une vanne, un lot de filtres sur 39 sources, une bascule) et vérifier que l'endpoint les rend, avec le regroupement attendu, sur chaque filtre et sur « tous ».
- 1.3 Aucun filtre de date par défaut : le journal montre les 50 dernières entrées, quelles que soient leurs dates. Le compteur de l'onglet, lui, compte celles du jour — jour de La Réunion.
- 1.4 Un test de non-régression : avec des lignes en base, `page 1 / 1 · 0 passage` est impossible.

## Lot 2 — L'état des robinets

- 2.1 Le calcul d'état d'un robinet doit lire les mêmes sources que le Résumé : `circuit_ecarts` ouvertes, `circuit_eau_ancienne`, `sql_propre`/`front` du registre, règles quand elles existent. Aujourd'hui il en manque au moins deux, puisque 0 robinet ressort à regarder alors que trois au moins le sont. Trouver et écrire pourquoi (jointure sur un id de robinet qui n'existe plus, écarts filtrés sur un statut, eau ancienne rattachée à un chiffre et jamais remontée au robinet).
- 2.2 **Le test d'égalité de la règle 2.4 est refait pour de bon** : il part des tables (`circuit_ecarts`, `circuit_eau_ancienne`, registre), construit l'ensemble des ids attendus « à regarder », et exige l'égalité stricte avec ce que rend `/admin/circuit` — des deux côtés, aucun en trop, aucun en moins. Le test précédent passait sur une page fausse : le remplacer, pas l'ajuster.
- 2.3 Même vérification pour les réservoirs : « 68, 35 à regarder » à gauche doit égaler la somme des lignes du Résumé qui portent sur des réservoirs, sans doublon (un réservoir compté dans deux lignes du Résumé n'est compté qu'une fois dans « à regarder »). Écrire la règle au compte-rendu.
- 2.4 Les pastilles d'un bloc reflètent l'état de chaque élément : un bloc « tout va bien » ne peut contenir aucune pastille ambre ou rouge, et réciproquement. Test.

## Lot 3 — Une seule source de vérité

- 3.1 Le Résumé et le Circuit lisent la même fonction d'état (`circuit_etats.py`) — vérifier qu'aucun des deux ne recalcule de son côté, ni au serveur ni au front ; si un chemin parallèle existe, le supprimer.
- 3.2 Ajouter un test de cohérence globale, joué sur la base réelle locale par `pytest -m local` : pour chaque ligne du Résumé, ses ids sont « à regarder » dans `/admin/circuit` ; pour chaque élément « à regarder », il existe une ligne du Résumé qui le contient. Ce test doit échouer sur l'état d'aujourd'hui avant correctif — le prouver au compte-rendu (sortie avant / après).

## Lot 4 — Recette

- 4.1 Captures P3-01 à P3-05 sur la base locale : Journal avec ses entrées et un lot déplié · Journal filtré sur « filtre » et sur « vanne » · Circuit avec « n à regarder » non nul à droite · un robinet en fuite ouvert depuis le Circuit · le Résumé et le Circuit côte à côte montrant les mêmes nombres.
- 4.2 Suites vertes (backend, vitest, tsc), compte-rendu clos avec les deux causes trouvées, en français, et ce qui a été supprimé.

## Interdits

Pas de merge. Aucun test ajusté pour passer : un test qui validait un écran faux est remplacé. Aucun compteur calculé au front. Aucune valeur codée en dur pour faire coïncider deux affichages.
