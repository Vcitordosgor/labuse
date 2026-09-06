# MANDAT CIRCUIT-P2 — La page Circuit, retours de recette du 06/09

Branche : `feat/circuit-page` (la même que CIRCUIT-P), worktree `~/Desktop/labuse-audit`.
Compte-rendu : chapitre « P2 » ajouté à `docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-P.md`. Captures dans `docs/CIRCUIT/RECETTE-CIRCUIT-P/P2-*.png`.
Autonomie : mêmes règles (aucune question, doutes écrits, branche jamais rouge, push par lot, reprise par « continue CIRCUIT-P2 depuis le compte-rendu »).
Objectif : la page Données est le Circuit, rien d'autre ; chaque bouton fait quelque chose de visible ; un seul nombre de réservoirs partout ; un ambre veut dire quelque chose.

Décisions prises (Vic + Fable, 06/09/2026), à appliquer sans les rediscuter :
- **La page Données = le Circuit.** L'ancien enrobage disparaît : le bandeau « Mes données sont-elles à jour ? », sa ligne « run servi · calculé le · garde de cohérence 6/6 · 21 surfaces · 20 sur le run servi · 1 vivante », les onglets Circuit / Catalogue / CRON, et les deux paragraphes « Qui fait quoi » et « Les autres onglets sont des vues ». Le Catalogue n'existe plus : le Circuit avec « tout afficher » et les pages de détail le remplacent (la page Sources côté client reste). L'onglet CRON quitte Données : `/admin/cron` reste une page, son lien va dans Pilotage.
- **Un passe-plat n'est pas « hors moteur ».** `passe_plat` = une valeur brute d'un réservoir servie telle quelle, déclarée au registre : état neutre. « Hors moteur » ne désigne que `sql_propre` et `front` (qui doivent être à 0 depuis CIRCUIT-2 ; s'ils ne le sont pas, c'est la liste exacte qui remonte, pas 45).
- **Un seul nombre de réservoirs partout : 68**, les sources affichées (`WHERE_AFFICHEES` + les deux de SOURCES-1). Les 11 autres lignes de `data_sources` (retirées, doublons, hubs) ne sont pas des réservoirs ; elles apparaissent une fois, dans la page de détail du repère « réservoirs », sous « 11 lignes en base non servies ». Le même compteur nourrit le Résumé, l'en-tête de colonne du Circuit et la ligne de fin.

---

## Lot 1 — Le ménage

- 1.1 `Donnees.tsx` ne rend plus que le Circuit (trois onglets, deux boutons). Tout l'ancien enrobage listé ci-dessus est supprimé, composants et tests morts compris ; `grep` vide sur « Mes données sont-elles à jour », « fourmilière », « Qui fait quoi », « Catalogue ».
- 1.2 Le lien CRON déménage dans Pilotage ; la page `/admin/cron` est inchangée.
- 1.3 L'onglet s'appelle « Journal », sans « aujourd'hui · 78 » : le compteur du jour vit dans l'onglet lui-même, en petit, seulement s'il est > 0 (`Journal 78`).
- 1.4 Snapshot vitest de la page Données : un seul composant racine, le Circuit.

## Lot 2 — Les nombres

- 2.1 `circuit_etats.py` : `passe_plat` neutre ; « hors moteur » = `sql_propre` + `front` seulement ; test.
- 2.2 Une seule fonction `compteurs()` côté serveur : réservoirs (68), à jour et vérifiés, à regarder, vides ou manuels — avec l'égalité vérifiée par test (`a_jour + a_regarder + vides = 68`) — robinets, chiffres, run. Le Résumé, l'en-tête « Réservoirs 68, n à regarder », la ligne de fin, l'en-tête « Robinets » lisent cette fonction. Le repère « 31 / 68 » ouvre au clic la page de détail du compteur : la liste des 68 par état, et les 11 non servies en dessous.
- 2.3 « À jour et vérifiés » est défini une fois, en français, dans la page de détail du compteur : version chez le producteur = version dans le réservoir, contrôle plus récent que la cadence, filtre passé sans bloquant. Un réservoir sous sentinelle mais jamais contrôlé n'est pas « à jour ».
- 2.4 Toute ligne du Résumé dont le nombre est > 0 correspond à des éléments visibles quelque part dans le Circuit avec le même état (test : chaque ligne du Résumé → ses ids → tous « à regarder » dans le Circuit, et réciproquement : aucun élément « à regarder » sans ligne au Résumé).

## Lot 3 — Les commandes qui ne répondent pas

- 3.1 **L'interrupteur « Ne montrer que ce qui cloche »** ne fait rien aujourd'hui : il doit filtrer les lignes à l'intérieur des blocs dépliés (allumé = seulement les éléments à regarder ; éteint = tous), et le titre de colonne doit dire « 68, 36 à regarder » dans les deux cas. Test vitest sur une fixture de trois réservoirs.
- 3.2 **« Vérifier que tout coule »** : au clic, le bouton passe en « Contrôle en cours… » (désactivé le temps du passage), une ligne de progression apparaît sous les onglets (« 42 / 130 robinets »), et à la fin le Résumé se rafraîchit seul, un message dit le résultat (« Contrôle terminé : 2 fuites, 1 eau ancienne, 0 nouvel écart ») et une ligne entre au Journal. Si le passage dure (les 24 PDF), on peut changer d'onglet, la progression reste visible.
- 3.3 **« Envoyer les agents sur tout »** ne doit jamais être un bouton grisé sans explication. Trois cas : crédit API absent ou épuisé → bouton actif, au clic un message clair (« Crédit API épuisé — recharge, puis relance ») et rien de lancé ; agents en cours → « 5 / 23 agents revenus », progression par réservoir dans le Circuit (état mauve « agent en route »), Résumé rafraîchi à chaque retour ; cas normal → lancement des agents sur les réservoirs jamais vérifiés ou à revérifier (pas les 68 : ceux dont le contrôle manque), journal alimenté. Même chose pour « Envoyer un agent » dans une page de détail.
- 3.4 Chaque geste de la page (vanne, agent, calculer, basculer, revenir, servir quand même, revenir à la précédente, vérifier) a un test qui prouve trois choses : l'endpoint est appelé, une ligne `circuit_journal` est écrite avec « qui », l'écran change (progression, message, rafraîchissement). Aucun bouton sans ces trois preuves.

## Lot 4 — Le journal lisible

- 4.1 Les passages groupés (un job de filtres sur 39 sources, une sonde sur 49) tiennent sur **une ligne** : « filtre · 39 sources · 28 ok, 10 avertissements, 1 quarantaine · système » ; le clic déplie le détail source par source. Une ligne isolée (une vanne, une bascule, un agent) reste une ligne.
- 4.2 La cible porte le **nom affiché** (« Géorisques — mouvements de terrain »), jamais l'identifiant technique ; un clic ouvre la page de détail.
- 4.3 Les filtres sont la liste complète des gestes, dans un ordre fixe, présents même vides : tous · vanne · calcul · bascule · agent · contrôle · filtre · sonde · cron. Les libellés sont en français (« vanne », pas « injecter » ; « contrôle », pas « job »).
- 4.4 « par » dit un nom (Vic, système, ingest-catnat), jamais « cli » ni « admin ».
- 4.5 Pagination : 50 lignes groupées par page, « Précédent / Suivant » en bas, comme aujourd'hui.

## Lot 5 — Vérification de bout en bout

- 5.1 Recette navigateur sur la base locale, captures P2-01 à P2-10 : la page Données s'ouvre sur le Résumé sans enrobage ; le repère 31 / 68 ouvre sa page ; le Circuit avec l'interrupteur dans les deux positions ; « Vérifier que tout coule » du clic jusqu'au message et à la ligne de journal ; « Envoyer les agents » dans le cas sans crédit et dans le cas normal (au moins un agent réel si le crédit le permet, sinon le cas sans crédit capturé) ; une page de détail réservoir, une robinet, la pompe ; Échap ; le journal groupé, un dépliage, un filtre vide.
- 5.2 Un test d'intégration parcourt tous les endpoints de la page (`/admin/circuit`, `/resume`, `/journal`, `/reservoir/{id}` pour les 68, `/robinet/{id}` pour les 130, `/pompe`) et échoue sur toute erreur ou tout temps > 1 s.
- 5.3 Suites vertes (backend, vitest, tsc), captures commitées, compte-rendu clos avec la liste des décisions prises en autonomie et de ce qui n'a pas pu être fait.

## Interdits

Pas de merge, pas de nouveau composant qui duplique un existant, aucun bouton grisé sans message, aucun compteur calculé au front, aucun identifiant technique affiché à l'écran.
