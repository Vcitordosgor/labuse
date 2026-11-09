# Dossier à transmettre à Claude — nouvelle Analyse LABUSE

**9 novembre 2026 — proposition ALGO-LABUSE-2, version 1.0.**

## Décision produit retenue

Les filtres restent tels quels. Le client choisit ensuite **Voir les parcelles** ou **Analyser avec LABUSE**. Aucune rubrique principale ni nouvel onglet de navigation n’est ajouté.

L’analyse distingue **Prospection vente** et **Potentiel foncier**, avec des scénarios de conservation, reconstruction et repérage d’une division pour logement.

Le changement de fond proposé est volontaire : **pas de nouvelle note globale 0–100 ni de poids inventés**. Le classement s’appuie sur le Signal existant dans son domaine validé, ou sur des capacités par scénario et des tris explicites. La qualité des données, les inconnues, les causes et les vérifications restent visibles.

## Fichiers

1. **01_SPECIFICATION_ALGORITHME.md** — document normatif : règles, quantités, statuts, tri, exclusions, incertitude, domaine du Signal, UX, validation et migration.
2. **02_MANDAT_CLAUDE.md** — instructions de travail prêtes à transmettre avec le dossier.
3. **03_MAQUETTE.html** — exemple interactif autonome, à ouvrir dans un navigateur. Les filtres de démonstration, la liste, les deux objectifs, les scénarios, les tris, les statuts, la pagination et les détails fonctionnent localement.
4. **04_MOTEUR_REFERENCE.cjs** — fonctions pures de référence pour les quantités, statuts et tris. Aucune prédiction ML ni opération SIG réelle.
5. **05_CAS_FICTIFS.json** — cas synthétiques utilisés par la maquette et les tests.
6. **06_TESTS_REFERENCE.cjs** — vérification du contrat de la référence.
7. **07_VERIFICATION.md** — vérifications effectuées sur ce dossier, leurs résultats et leurs limites.
8. **SOURCE_ALGO_LECTURE_1.txt** — copie du document initial fourni, pour comparaison ; ses règles ne prévalent pas sur la nouvelle spécification.

Le sous-dossier **captures/** fournit six vues de contrôle. **MANIFEST.sha256** permet de vérifier l’intégrité des fichiers. Ces compléments ne changent pas l’ordre de priorité documentaire ci-dessous.

La source de la maquette affichée dans la conversation est conservée séparément dans le dossier de visualisations. Le fichier HTML livré est autonome et ne nécessite ni compte ni installation.

## Lecture conseillée

Lire ce README, puis le mandat et la spécification. Ouvrir la maquette pour examiner les conséquences des règles. Le fichier de référence et ses tests servent à lever les ambiguïtés, pas à copier un backend de production.

En cas de différence : **spécification → moteur de référence/tests → maquette**. Toute divergence constatée doit être corrigée et rapportée, sans changer silencieusement une règle métier.

## Limites à conserver lors de la transmission

- Le dépôt et la production de LABUSE n’ont pas été audités dans ce travail.
- Les versions q_v15/q_v20 et chemins cités proviennent du document utilisateur et doivent être vérifiés.
- Les signaux de la maquette sont entièrement fictifs. Ils ne démontrent pas que le modèle L2-F couvre toutes les ventes de biens existants.
- La maquette ne valide ni constructibilité, ni rentabilité, ni divisibilité et ne reproduit pas tous les filtres de l’application.
- La recette de validation du produit réel demeure à exécuter dans le dépôt et sur les données adéquates.

## Exécuter la référence

Avec une version de Node compatible avec les scripts du dossier :

```sh
node 06_TESTS_REFERENCE.cjs
```

La maquette s’utilise par double-clic sur `03_MAQUETTE.html`. Toutes ses données sont embarquées ; elle ne consulte pas la production.
