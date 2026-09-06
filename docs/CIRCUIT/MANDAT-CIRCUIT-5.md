# MANDAT CIRCUIT-5 — Les verrous

Branche : `feat/circuit-5`, worktree `~/Desktop/labuse-audit`, créée depuis `main` (CIRCUIT-0 à 4 et P y sont mergés).
Dossier : `docs/CIRCUIT/`. Compte-rendu : `docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-5.md`.
Objectif : qu'il ne reste plus de place au doute. Après ce mandat, chaque garantie que Vic attend est un **verrou** : une règle écrite en une phrase, un test qui la fait respecter, un endroit sur la page où elle se lit, et un déploiement qui refuse de partir si elle casse. Rien ne repose sur la vigilance de quelqu'un.

Ce que Vic veut pouvoir dire sans réserve, et que ce mandat rend vrai par construction :
- « Le PLU affiché sur Saint-Paul est celui de Saint-Paul ; le SRU de Saint-Benoît n'apparaît jamais sur Sainte-Marie. »
- « Si Sitadel 2026 est en base, tout l'app lit Sitadel 2026 ; personne ne lit 2025 dans un coin. »
- « Les outils, sections, couches et PDF n'écoutent que les 68 sources, pas 82 avec des doublons, des mortes et des essais. »
- « Une même donnée donne le même résultat partout où elle s'affiche. »
- « Tout le monde écoute le même moteur. »

---

## Autonomie

Mêmes règles que CIRCUIT-1 à 4 : aucune question à Vic, doutes tranchés par l'option la plus sûre et écrits dans « Décisions prises en autonomie », lots sautés plutôt qu'attendus, branche jamais rouge, un commit et un push par lot, reprise par « continue CIRCUIT-5 depuis docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-5.md ». **Aucune table n'est supprimée et aucune source n'est effacée en autonomie** : ce mandat liste, marque, verrouille ; la purge est un geste de Vic, outillé par une commande que le mandat fournit.

---

## Étape 0

1. `pwd` = `~/Desktop/labuse-audit`, arbre propre, sinon stop. `git fetch`, branche `feat/circuit-5` depuis `main` à jour. Suites vertes au départ, nombres notés.
2. Lire les comptes-rendus 0 à 4 et P : les dettes écrites y sont (la sonde qui écrit des libellés au lieu d'un `chiffre_id`, l'eau DPE non attribuable, les 14 lignes non servies de `data_sources`, les tables mortes relevées par CIRCUIT-0).

---

## Règles

1. **Un verrou = une phrase + un test + un endroit sur la page.** Un verrou sans test n'existe pas ; un test sans phrase en français n'est pas un verrou.
2. **Les verrous sont réunis dans une seule commande**, `labuse circuit verrous`, qui les joue tous et sort en erreur au premier qui casse. Cette commande est jouée par `pytest`, par la sonde de nuit, et par `deploy.sh` avant tout déploiement.
3. **Preuve avant affirmation** : chaque verrou est prouvé cassé sur un cas construit (une table orpheline posée exprès, une source en double, une jointure décalée d'une commune) puis vert une fois la garde en place. Les deux sorties vont au compte-rendu.
4. Rien de mergé ; captures avant/après pour la page.

---

## Lot 1 — Verrou des tables : chaque moteur ne lit que les tables des 68 réservoirs

- 1.1 **La carte table → réservoir** : `registre/tables.py` déclare, pour chacun des 68 réservoirs, la ou les tables servies (tables, vues, matérialisations, tuilages) et le millésime servi. Une table qui n'appartient à aucun réservoir n'est pas lisible par un moteur.
- 1.2 **Deux lectures qui doivent coïncider** : une analyse statique des fonctions de `registre/moteurs/` et des passe-plats (les noms de tables dans leurs requêtes), et une lecture à l'exécution (les tables réellement touchées pendant un passage de la sonde sur les témoins, via le journal des requêtes de la session). Test : aucune table lue, statiquement ou à l'exécution, hors de la carte. Le test est prouvé cassé sur une fonction témoin qui lit une table orpheline, puis vert.
- 1.3 **Les tables orphelines** : toutes les tables du schéma qui ne sont ni dans la carte, ni des tables d'exploitation déclarées (registre, journal, filtres, comptes, événements, sessions…), avec taille, dernière écriture, dernier lecteur connu, et l'action proposée (`purger` · `archiver` · `rattacher`) dans `docs/CIRCUIT/TABLES-ORPHELINES.md`. Une commande `labuse tables purger --apply` les déplace dans un schéma `poubelle` (jamais un `DROP`), sur le geste de Vic seulement.
- 1.4 **Réservoirs sans lecteur** : un réservoir des 68 qu'aucune donnée ne lit est listé avec la question « source à retirer, ou lecteur manquant ? » ; il apparaît au Résumé sous « à décider ».

## Lot 2 — Verrou des sources : 68, pas un de plus

- 2.1 Les 14 lignes de `data_sources` hors vitrine sont traitées une par une : doublon → fusionnée dans la ligne canonique (l'ancien id devient un alias, rien ne se perd) ; morte ou essai → `statut = retiree` avec la date et la raison ; hub ou catalogue → `statut = hub`, jamais compté comme réservoir. Résultat : la vitrine et `data_sources` servies coïncident, 68 = 68, et le repère de la page n'a plus de « lignes non servies » à montrer.
- 2.2 Test : `count(data_sources where statut = servie)` = `count(vitrine)` = nombre de réservoirs du registre = nombre affiché sur la page. Un `seed` qui ajouterait une source hors vitrine casse le test.
- 2.3 Une source ne peut plus entrer qu'avec un id, un producteur, un mode de remplissage, une cadence et une sonde (ou la raison de son absence) : le `seed` refuse le reste.

## Lot 3 — Verrou des versions : une seule version servie, partout

- 3.1 **Une version par réservoir** : test que chaque réservoir n'a qu'une version servie, que toute table d'un millésime antérieur est soit la `__precedente` de l'échange (CIRCUIT-3), soit orpheline (lot 1). Deux millésimes servis en même temps = verrou cassé.
- 3.2 **Après une bascule, zéro eau ancienne** : test joué sur la base locale — injecter une version (BODACC), calculer, basculer, puis `circuit_eau_ancienne` doit être vide hors « solaire gelé, étiqueté » ; s'il reste une ligne, le verrou nomme la donnée et le robinet.
- 3.3 **La sonde écrit des ids, plus des libellés** : `circuit_ecarts` et `circuit_eau_ancienne` portent `chiffre_id` et `robinet_id` (la dette de CIRCUIT-P3) ; l'eau DPE devient attribuable à ses robinets ; migration avec backfill ; test.

## Lot 4 — Verrou des communes : la bonne ligne pour la bonne commune

- 4.1 **Clé étrangère partout** : toute table à la maille commune porte un code INSEE contraint sur le référentiel des 24 ; un code absent ou hors référentiel ne peut plus entrer (les filtres de CIRCUIT-3 l'avertissaient, le verrou l'interdit).
- 4.2 **Test de permutation** : pour chaque donnée à la maille commune, la sonde calcule la valeur pour deux communes que le producteur distingue (Saint-Benoît et Sainte-Marie, choisies dans l'échantillon) et exige que les deux valeurs soient celles attendues, pas seulement différentes. Une jointure décalée d'une ligne ou un « première ligne » par défaut casse le verrou. Prouvé cassé sur une jointure volontairement décalée, puis vert.
- 4.3 **Test géographique** : pour trois parcelles témoins choisies à cheval ou à moins de 50 m d'une limite communale, la zone PLU, l'aléa et la commune de rattachement servis sont ceux de la commune où se trouve le centroïde ; une couche d'une commune voisine collée par erreur casse le verrou.
- 4.4 **Échantillon producteur pour toute la fiche commune** : pour chacune des 15 cartes de la fiche commune et pour chacune des 24 communes, la valeur attendue lue chez le producteur (INSEE, SRU/DHUP, DVF, Sitadel, GPU, DEAL…), stockée avec son origine dans `filtres/echantillons/communes/<carte>.json`, rejouée à chaque version comme contrôle avertissant ; ce que CC ne peut pas lire chez le producteur est listé dans `ECHANTILLONS-A-VALIDER.md` avec une proposition, sans bloquer.

## Lot 5 — Verrou des concepts et des moteurs

- 5.1 **Un concept = un id** : deux données dont le libellé normalisé ou la définition sont identiques ne peuvent pas coexister avec deux ids (test sur le registre) ; les synonymes assumés sont listés dans `CONCEPTS-CANONIQUES.md`, et c'est la seule exception admise. La revue de CIRCUIT-2 est rejouée sur l'intégralité des fiches parcelle et commune, des outils et des PDF.
- 5.2 **Une donnée = une fonction** : test que chaque id n'a qu'une fonction, que chaque robinet obtient chaque donnée par cette fonction (`sql_propre` = 0, `front` = 0, garde déjà posée en CIRCUIT-2 — ici réunie dans `verrous`), et que la sonde a bien comparé dans la nuit tous les couples (id, robinet) déclarés : un couple jamais sondé est un verrou cassé, pas un « non couvert ».
- 5.3 **Témoins** : les témoins parcelle passent de 54 à un échantillon tournant — 54 fixes plus 50 tirés chaque nuit parmi les parcelles consultées la veille (journal d'usage), pour qu'un écart hors témoins finisse par être vu.

## Lot 6 — La commande, la porte, la page

- 6.1 `labuse circuit verrous` : joue tous les verrous des lots 1 à 5, affiche une ligne par verrou (phrase, verdict, preuve), sort en erreur au premier cassé. Jouée dans `pytest` (marque `verrous`), dans le passage de nuit (résultat au Journal), et par `deploy.sh` qui refuse de déployer si un verrou est cassé.
- 6.2 Page Circuit : le Résumé reçoit les lignes « verrou cassé » (rouge, à corriger), « tables orphelines à purger » et « réservoirs sans lecteur » (à décider) ; la page de détail du repère « 68 » montre la carte table → réservoir ; un nouvel onglet n'est pas créé.
- 6.3 `docs/CIRCUIT/VERROUS.md` : **le document pour Vic** — une page, en français, un verrou par ligne : la phrase, ce qui le garantit, le test qui le tient, où ça se lit sur la page. C'est ce qu'il relira les jours de doute.

## Livrables

```
docs/CIRCUIT/MANDAT-CIRCUIT-5.md · COMPTE-RENDU-CIRCUIT-5.md · VERROUS.md · TABLES-ORPHELINES.md · ECHANTILLONS-A-VALIDER.md (complété)
src/labuse/registre/tables.py · src/labuse/circuit_verrous.py · CLI labuse circuit verrous · labuse tables purger
filtres/echantillons/communes/*.json (15 cartes × 24 communes)
migrations : statut des sources, chiffre_id/robinet_id dans la sonde, clés étrangères communes
tests/verrous/ : un test par verrou, chacun prouvé cassé puis vert
deploy.sh : porte sur labuse circuit verrous
```

## Définition de fini

- `labuse circuit verrous` existe, joue chaque verrou des lots 1 à 5, et passe sur la base locale ; `deploy.sh` le joue.
- Chaque verrou est prouvé cassé sur un cas construit, avec la sortie au compte-rendu, puis vert.
- 68 = 68 partout ; aucune table lue hors de la carte ; `TABLES-ORPHELINES.md` livré avec la commande de purge, rien de supprimé.
- Les 15 cartes × 24 communes ont leur attendu producteur, ou une ligne « à valider ».
- `VERROUS.md` se lit sans le code.
- Suites vertes, rien mergé.

## Ce qui reste à Vic, après

Lire `VERROUS.md`. Purger les tables orphelines avec la commande, quand il veut. Trancher les « réservoirs sans lecteur ». Merger, déployer — et à partir de là, un déploiement qui passe la porte est la preuve que tout tient.

## Interdits

Aucun `DROP`, aucune source effacée, aucun verrou sans test, aucun test ajusté pour passer, aucune valeur codée en dur, rien de mergé.
