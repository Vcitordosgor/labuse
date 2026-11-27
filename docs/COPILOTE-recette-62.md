# COPILOTE · suite permanente des 62 cas

Les numéros reprennent l’ordre des cinq rapports du 26 novembre 2026. Un cas peut avoir plusieurs assertions, témoins, unités ou formulations. Les tests Python passent par les fonctions du serveur, avec des fiches déterministes et PostgreSQL de test pour les conversations. Les tests React exercent la navigation et les erreurs. Les deux programmes de recette complètent ces tests par des requêtes HTTPS et par le comportement réel de Chromium.

## Exécution

Depuis la racine du dépôt, dans l’environnement de développement configuré pour la base **de test** :

```sh
python -m pytest -q tests/test_copilote_audit_novembre.py tests/test_copilote_audit_2.py tests/test_copilote_audit_4.py tests/test_copilote_audits_3_a_5.py
npm --prefix frontend test -- --run src/components/copilote
```

Ces fichiers suivent la découverte normale de pytest et de Vitest dans la CI du dépôt. Pour tester la passerelle HTTP, les données parcellaires et le clavier sur une version publiée, fournir l’origine HTTPS en argument ainsi que les variables du compte de recette `LABUSE_RECETTE_EMAIL` et `LABUSE_RECETTE_PASSWORD`. La recette navigateur utilise Chromium de Playwright, ou le binaire spécifié par `PLAYWRIGHT_CHROMIUM_EXECUTABLE`. Les programmes suppriment les conversations qu’ils ont créées. Une assertion échouée renvoie un code de sortie non nul.

```sh
python -m scripts.recette_copilote_audits "$ORIGINE_RECETTE"
node frontend/qa/copilote-audits.mjs "$ORIGINE_RECETTE"
```

Les témoins cadastraux sont ceux des rapports. Une modification du cadastre ou d’une source peut légitimement changer une valeur attendue. Les références solaire, pente et zonage du cinquième audit sont relues depuis les services publiés à chaque passage.

## Correspondance avec les rapports

### Audit 1 · 15 cas

`tests/test_copilote_audit_novembre.py` et `frontend/src/components/copilote/__tests__/conversations.test.tsx`.

| Nº | Comportement vérifié |
|---|---|
| 01 | Écriture du fil réservée à sa session |
| 02 | Confirmation d’une adresse voisine, avec variantes bis et ter |
| 03 | Désaccord entre commune et code postal |
| 04 | Préemption et emplacement réservé |
| 05 | Bandeau après changement de parcelle |
| 06 | Réponse tardive après changement de conversation |
| 07 | Fibre, statut du bâtiment et distance |
| 08 | Échantillon de prix du terrain insuffisant |
| 09 | Dernière mutation parcellaire |
| 10 | Classe, date et bâtiment du DPE |
| 11 | Motif de faisabilité en l’absence de surface calculée |
| 12 | Conservation des sources et actions à la réouverture |
| 13 | Expiration annoncée pendant le fil et à la réouverture |
| 14 | Suppression refusée ou interrompue |
| 15 | Historique vide, erreur de liste ou erreur d’ouverture |

### Audit 2 · 13 cas

`tests/test_copilote_audit_2.py`, tests React de conversation et recette HTTPS pour le cas 08.

| Nº | Comportement vérifié |
|---|---|
| 01 | Copropriété et lots voisins |
| 02 | Total de surfaces dans les deux ordres |
| 03 | Surface bâtie |
| 04 | Pente de toiture indisponible |
| 05 | Hauteur estimée et source |
| 06 | Capacité en logements |
| 07 | Reprise après expiration sans réactivation des faits anciens |
| 08 | Six demandes passant par la passerelle, dont cumul, adresse et double question |
| 09 | Surface et zone PLU dans une même réponse |
| 10 | Sélection du deuxième candidat en relance |
| 11 | Identifiant de reprise identique et absence de tour en double |
| 12 | Brouillon conservé à la reprise et à la resélection |
| 13 | Pagination des conversations, y compris à dates identiques |

### Audits 3, 4 et 5 · 14 + 10 + 10 cas

`tests/test_copilote_audits_3_a_5.py` identifie les cas par leur numéro de rapport. `tests/test_copilote_audit_4.py` vérifie également le choix de la grandeur et le cas du zéro. La recette Chromium couvre 3.10, 4.10 et 5.10. Le dernier cas possède aussi un test React. La recette HTTPS rejoue les cas métier du cinquième audit.

| Nº | Audit 3 | Audit 4 | Audit 5 |
|---|---|---|---|
| 01 | Surface non bâtie | Parcelle explicite prioritaire sur le contexte | Millions et milliers en toutes lettres |
| 02 | Orientation des pans du toit | Surface de piscine et emprise de toiture | Taux négatif, signes ASCII et Unicode |
| 03 | Assainissement collectif | Part non bâtie | Montant final après remise, hausse et TVA |
| 04 | Conversion en hectares au tour suivant | Puissance, productible et production annuelle | Pourcentage avec conversion ha ↔ m² |
| 05 | CASIAS | Ménages, HLM et logements vacants | Pourcentage de parcelle, direct et en relance |
| 06 | Unité explicite en ha | SDP résiduelle, bâti conservé | Pente en pourcentage |
| 07 | Différence entre parcelles | Moyenne de surfaces et ordre des parcelles | Nombre théorique de panneaux en Wc ou kWc |
| 08 | Habitants et taux de vacance IRIS | Montant fiscal et données nécessaires | Moyenne mensuelle de production |
| 09 | Puissance photovoltaïque | Distance en kilomètres | Surface dans une zone PLU, y compris zone mixte et hectares |
| 10 | Largeur et visibilité du champ à 320 et 390 px | Clavier contenu dans le tiroir et restitution du focus | Saisie immédiate après Entrée à 320, 390 et 1 440 px |
| 11 | Parc de logements existants | | |
| 12 | Apostrophes droite et typographique dans le nom de la taxe | | |
| 13 | École du premier degré et distance | | |
| 14 | Part bâtie | | |
