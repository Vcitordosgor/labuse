# MANDAT CIRCUIT-P — La page Circuit en trois onglets

Branche : `feat/circuit-page`, worktree `~/Desktop/labuse-audit`, créée depuis `main` si `feat/circuit-3` y est mergée, sinon depuis `feat/circuit-3`. À jouer **après CIRCUIT-3 et avant CIRCUIT-4** (le lot 5 de CIRCUIT-4 posera ses badges sur cette page).
Dossier : `docs/CIRCUIT/`. Compte-rendu : `docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-P.md`.
Référence exacte, validée par Vic le 06/09/2026 : `docs/CIRCUIT/maquette-circuit-v8.html` (à copier depuis `~/Downloads` si elle n'y est pas). Ce mandat ne discute pas le dessin, il le construit.
Objectif : la page où Vic ira le plus souvent doit se lire en dix secondes — ce qui cloche d'abord, le circuit entier derrière, le détail d'un élément sur une vraie page, et le journal de tout ce qui s'est passé.

---

## Autonomie

Mêmes règles que CIRCUIT-1 à 3 : aucune question à Vic, doutes tranchés par l'option la plus sûre et écrits, lots sautés plutôt qu'attendus, branche jamais rouge, push par lot, reprise par « continue CIRCUIT-P depuis docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-P.md ». La maquette est la vérité visuelle ; le registre, le manifeste, la sonde, les filtres et le journal de CIRCUIT-1 à 3 sont la vérité des données. Quand les deux divergent (un état que la maquette n'a pas prévu), CC ajoute l'état dans la même grammaire — une couleur, un libellé court, une phrase — et le note.

---

## Étape 0

1. `pwd` = `~/Desktop/labuse-audit`, arbre propre, sinon stop. Branche (voir en-tête). Suite verte et `vitest` vert au départ, nombres notés.
2. Lire `Circuit.tsx` tel qu'il existe (CIRCUIT-1 lot 5, étendu par CIRCUIT-2 lot 5 et CIRCUIT-3 lot 5) : tout ce qu'il sait afficher doit survivre, réorganisé.

---

## Règles

1. **Trois onglets, deux boutons, rien d'autre en haut** : Résumé (par défaut), Circuit, Journal ; à droite « Envoyer les agents sur tout » et « Vérifier que tout coule ». Les pastilles du bandeau disparaissent : elles deviennent les lignes du Résumé.
2. **Le Résumé ne montre que ce qui cloche.** Une ligne = un chiffre, un titre, une phrase en français, un verbe. Trois groupes dans cet ordre : « À faire, un geste de toi », « À corriger, un mandat pour CC », « À décider, quand tu veux ». En dessous, une seule ligne pour tout le reste. Zéro problème = « Tout coule. »
3. **Le Circuit se lit au niveau des familles et des catégories.** Neuf blocs de réservoirs à gauche (les familles de `reservoirs.csv`), douze blocs de robinets à droite (les catégories du registre), la pompe au milieu, un tuyau par bloc. Un bloc porte une pastille par élément (colorée seulement hors « ça coule ») et « n à regarder » ou « tout va bien ». Un clic déplie un bloc, un seul à la fois. Par défaut, seuls les éléments à regarder sont listés dans un bloc déplié ; l'interrupteur « Ne montrer que ce qui cloche » montre tout. Survoler une ligne allume son chemin (famille → pompe → catégories). Aucune ligne ne tronque un nom : deux lignes par élément (nom ; version · contrôle · cadence).
4. **Le détail est une page, pas un tiroir.** Cliquer une ligne ou la pompe remplace le dessin par la page de détail, avec « ← Retour au circuit » et Échap. Réservoir : versions (dans le réservoir, chez le producteur, dernier contrôle, horloge), gestes (agent, vanne, servir quand même, revenir), filtre à l'entrée, rapport de l'agent, ce qu'il alimente, les chiffres qu'il nourrit. Robinet : fuites et eau ancienne en tête, ce qu'il affiche avec ses badges (moteur / hors moteur, tampon, règle quand CIRCUIT-4 sera passé), la règle derrière ses calculs, alimenté par, dernier contrôle. Pompe : ce qui attend, gestes (calculer, basculer, revenir), note de version, moteurs et pointeurs, horloges.
5. **Le Journal est un tableau** : quand, geste, cible, par, résultat ; filtres par type de geste, « tous » en premier à gauche ici parce que c'est un filtre de journal, pas un groupe de tri (la règle « Tout à droite » vaut pour les filtres d'outils). Source : `circuit_journal`, plus les passages de sonde, filtres et contrôles.
6. **Les couleurs ne disent qu'une chose** : mint = ça coule, ambre = à regarder, rouge = bloqué ou fuite, gris = vide ou manuel, mauve = agent ou IA. Pas d'autre couleur sur cette page. Survol = vert opaque, contenu inversé (règle DA v3). Aucune barre de défilement horizontale. Aucune donnée affichée hors registre.
7. Un commit par lot, push, rien de mergé ; captures avant/après dans `docs/CIRCUIT/RECETTE-CIRCUIT-P/`.

---

## Lot 1 — Les données de la page

- 1.1 `GET /admin/circuit` (CIRCUIT-1) s'enrichit d'un bloc `resume` calculé côté serveur : la liste des lignes des trois groupes, chacune avec `n`, `couleur`, `titre`, `phrase`, `verbe`, `cible` (type et ids). La règle de composition vit dans `src/labuse/circuit_resume.py` avec un test par ligne possible (quarantaine, réservoir plein, eau nouvelle, eau ancienne, jamais vérifiés, fuites, écarts à la règle, horloge qui ment, filtres avec KO, hors moteur, choix LABUSE, cadences à valider). Le front ne recalcule rien.
- 1.2 `GET /admin/circuit/journal?type=&depuis=` : `circuit_journal` + passages de sonde, filtres, contrôles, agents, crons qui touchent l'eau ; pagination simple ; le « qui » toujours présent.
- 1.3 `GET /admin/circuit/reservoir/{id}`, `/robinet/{id}`, `/pompe` : les blocs de la page de détail, un appel chacun, < 500 ms sur la base réelle (test).
- 1.4 États : la fonction qui donne couleur + libellé court d'un réservoir et d'un robinet est unique, côté serveur, testée sur chaque cas de la maquette (`tankEtat` / `tapEtat` de la v8 sont la spécification).

## Lot 2 — Résumé et onglets

- 2.1 `Circuit.tsx` devient un conteneur à trois onglets ; `Resume.tsx` rend le bloc `resume` : titre, quatre repères (réservoirs à jour et vérifiés, robinets sans rien à signaler, chiffres, run servi et candidat), les trois groupes, la ligne de fin. Chaque ligne emmène vers sa cible : page de détail ou circuit déplié sur les ids concernés.
- 2.2 Les deux boutons du haut lancent les gestes existants et basculent sur l'onglet Circuit.
- 2.3 Test vitest : zéro problème → « Tout coule. » ; chaque type de ligne rend son verbe.

## Lot 3 — Le circuit par familles

- 3.1 `CircuitDiagram.tsx` : blocs famille / catégorie avec pastilles et compteur, accordéon, lignes à deux niveaux, interrupteur « que ce qui cloche », recherche (qui déplie les blocs contenant un résultat), tuyaux SVG au niveau des blocs (stubs, collecteur, distributeur, pompe), chemins allumés au survol, fuites en pointillé rouge entre bloc famille et bloc catégorie (agrégées, une par couple). Redessin sur redimensionnement, dépliage et défilement.
- 3.2 La pompe : bloc collant, run servi, ce qui attend, alerte sur les pointeurs tant que le manifeste n'est pas seul.
- 3.3 Test vitest : le nombre de tuyaux = familles + catégories + 2 ; un survol allume les bonnes catégories (fixture de deux réservoirs).

## Lot 4 — Les pages de détail

- 4.1 `Detail.tsx` (réservoir, robinet, pompe) conforme à la maquette, alimenté par 1.3 ; tous les gestes existants y vivent (agent, vanne, servir quand même, revenir, calculer, basculer, retour) avec leur journalisation. Retour par bouton et par Échap ; l'URL porte l'élément ouvert (`#reservoir/sitadel`) pour qu'un lien du journal ou d'un mail ouvre directement la bonne page.
- 4.2 Les chips « alimente » / « alimenté par » naviguent d'une page de détail à l'autre.

## Lot 5 — Le journal

- 5.1 `Journal.tsx` : tableau, filtres, pagination ; une ligne de journal dont la cible existe est un lien vers sa page de détail.
- 5.2 Le compteur de l'onglet dit « aujourd'hui » et le nombre d'entrées du jour.

## Lot 6 — Recette navigateur et retrait de l'ancien

- 6.1 Recette sur la base locale, avec le Chrome local : Résumé → clic sur chaque type de ligne → page de détail → retour → circuit déplié → survol → journal filtré ; captures numérotées dans `docs/CIRCUIT/RECETTE-CIRCUIT-P/`. Le parcours complet vanne → calcul → note → bascule → vérifier → revenir est rejoué sur la nouvelle page (comme au lot 5 de CIRCUIT-1), base restaurée après.
- 6.2 L'ancien rendu (bandeau à pastilles, tiroir du bas, colonnes exhaustives) est retiré ; aucun composant mort ne reste. Snapshot vitest de chaque onglet.
- 6.3 Le mandat CIRCUIT-4 pose ses badges de règle dans `Detail.tsx` (robinet) et sa ligne « écarts à la règle » dans le Résumé : le compte-rendu indique les points d'accroche.

## Livrables

```
docs/CIRCUIT/MANDAT-CIRCUIT-P.md · COMPTE-RENDU-CIRCUIT-P.md · maquette-circuit-v8.html · RECETTE-CIRCUIT-P/
src/labuse/circuit_resume.py · endpoints journal et détail · fonction d'état unique
frontend/src/components/admin/circuit/{Circuit,Resume,CircuitDiagram,Detail,Journal}.tsx
tests : circuit_resume, états, endpoints ; vitest : résumé, diagramme, détail, journal, snapshots
```

## Définition de fini

- Les trois onglets existent, le Résumé est calculé côté serveur, chaque ligne mène quelque part, le circuit se lit par familles, le détail est une page, le journal est filtrable.
- Aucune barre horizontale, aucune couleur hors les cinq, aucun nom tronqué.
- Recette jouée avec captures, ancien rendu retiré, suites vertes, rien mergé.

## Ce qui reste à Vic, après

Ouvrir la page, cliquer partout pendant cinq minutes, dire ce qui gêne. Merger.
