# ETUDE-V6-4 — écran = PDF (mêmes mots, mêmes chiffres)

Branche `feat/etude-v6` (worktree `labuse-etude-v6`), **pas de merge**. Exigence : *l'écran et le PDF
disent exactement la même chose, avec les mêmes mots et les mêmes chiffres.* Recette : L'Étang-Salé
(AW 99/451/624/625), résidence étudiante — 41 T1 aérien puis sous-sol, puis 23 T2 + 6 T3 en sous-sol.

## Les 13 points

1. **Textes retirés** — « Pré-faisabilité foncière · La Réunion », « Votre projet. Les possibilités… »
   + sous-titre, « Aucune carte dans le formulaire… », « Géométrie & contenance : Cadastre… », le bas de
   page « Bilan surfacique clos… study_id… ». Plus affichés.
2. **Bloc PLU étape 1** = un BANDEAU vert distinct (bord mint, kicker « Règles du PLU », « de L'Étang-Salé ·
   zone UA »), typo propre. Les cartes de parcelles ne répètent plus les règles.
3. **« Lire l'article » partout** (étapes 1 et 2, stationnement, contrôles, annexe PDF) → extrait VERBATIM
   (texte cité, article, page, **millésime 2025-09-17**) + lien vers le document PLU officiel geopf quand il
   existe. Côté serveur : chaque règle porte `source_url` + `millesime` ; les contrôles sont rattachés à
   leur règle par mot-clé ; le PDF a une **annexe « extraits du règlement »** (8 articles cités mot pour mot).
4. **Stationnement en 3 lignes** (écran + PDF, mot pour mot) : « Le PLU de L'Étang-Salé (art. UA 2.7.3)
   exige 1 pl. T1–T2 · 1,5 pl. T3–T4 · 2 pl. T5+. » · « La loi nationale (Code de l'urbanisme, art.
   L151-35) plafonne à 0,5 place/logt si éligible — à confirmer. » · « LABUSE a dessiné N places… ».
5. **Mixité sociale** (UA 1.3, 20 % aidés > 1 000 m²) affichée dans le résultat ET dès l'étape 2, comme le PDF.
6. **« Surface du programme tenue »** = surface du programme (logements × surfaces T1–T4), jamais la SDP (la
   SDP reste en « SDP du scénario » et dans le détail des surfaces).
7. **« Recalculer »** sur une seule ligne, icône comprise (`whitespace-nowrap`).
8. **Recalcul** : changer Aérien/Sous-sol recalcule tout seul ; modifier une autre hypothèse **grise** « Générer
   le PDF » avec « Recalculez pour mettre à jour l'étude » jusqu'au recalcul — jamais de PDF d'un état non calculé.
9. **Plan du niveau −1 DESSINÉ sur la vraie géométrie** (écran + PDF) : contour de l'emprise enterrée dans
   l'assiette, allée centrale, places, rampe à leur vraie position — plus de grille générique. Objets
   `sous_sol_emprise`/`place_ss`/`allee_ss`/`rampe` au niveau −1, projetés comme le plan masse.
10. **Hauteur en sous-sol** : une phrase dit pourquoi. Notre modèle enterre le parking **sans surélever le
    RDC** ; quand la hauteur plafonne en sous-sol c'est le **relief** (le stationnement enterré a libéré le
    sol, c'est alors la pente qui borne les niveaux). Écrit à l'écran comme au PDF.
11. **PDF = écran** : même facteur limitant (« Ce qui limite : … »), même verdict, surfaces T1–T4 (30/56/70/80
    + varangues), type de projet, stationnement 3 lignes, mixité, mode aérien/sous-sol. Plus de « pas de
    sous-sol » / « non simulé ». En sous-sol, « N places au sous-sol (niveau −1) », jamais « aériennes ».
12. **PDF propre** : titre « Étude de faisabilité — L'Étang-Salé · parcelles AW 99, 451, 624, 625 », accents
    corrects (« aérien »), plus de noms techniques (IMPLANTATION-2, version conventions, « retenu (retenu) »),
    phrase « Projet saisi par le client » corrigée, règle de stationnement remplie.
13. **Garde de test** : `test_pdf_pas_de_nombre_ni_facteur_hors_ecran` — pour un même study_id, le PDF ne
    contient **aucun nombre ni facteur limitant absent du payload servi à l'écran** (aérien + sous-sol), ni
    nom technique. + `test_sous_sol_plan_dessine_sur_geometrie` (item 9).

## Source unique écran↔PDF

- `payload.facteur_limitant` (+ `facteur_limitant_detail`) : calculé **une seule fois** côté serveur
  (`service._facteur_limitant_phrase`/`_facteur_limitant_detail`), lu tel quel par l'écran ET le PDF.
- Règles : `source_url` + `millesime` portés par chaque ligne (`_decore_regles`), consommés par
  `LireArticle` (écran) et l'annexe (PDF).
- Niveau −1 : mêmes objets GeoJSON rendus par `PlanMasseSvg` (écran) et `_svg_plan` (PDF).
- Verrou `nombres_hors_payload` = **0** sur les 3 configs de la recette.

## Gardes (toutes vertes)

| Garde | Résultat |
|---|---|
| `tsc -b` (front) | 0 erreur |
| `vitest` | **298 / 298** |
| pytest implantation + etude_v6 | **161 passed** ; 2 `test_route_*` échecs **pré-existants** (env `labuse_test` vide, prouvé sur l'arbre propre) |
| `chasse_docs` | **20 OK · 0 ECART · 0 SKIP** |
| `chasse_donnees` | **23 OK · 0 ECART · 2 SKIP** |

## Captures (`captures/`)

- Écran : `ecran_1`…`ecran_7` (étape 1 bandeau PLU, Lire l'article, étape 2 mixité/stationnement, résultat
  41 T1 aérien, 41 T1 sous-sol, plan niveau −1, 23 T2 + 6 T3 sous-sol).
- PDF : `pdf_41T1_aerien.pdf`, `pdf_41T1_soussol.pdf`, `pdf_23T2_6T3_soussol.pdf` (+ PNG de pages clés :
  couverture, stationnement & mixité p3, plan niveau −1 p5, annexe règlement p12).

## Réserves honnêtes

- Un niveau de sous-sol enterré ne loge sur cette assiette que ~29 places ; loger 44 places demande
  **2 niveaux** — c'est écrit à l'écran et au PDF (plan de principe = niveau −1). Compte servi inchangé.
- Le lien PLU officiel pointe sur l'archive `.zip` geopf (pas d'ancre de page profonde) ; la page figure en
  clair (« p. 17 »).
- Services arrêtés en fin de session (8830/6060 libres). **Aucun merge.**
