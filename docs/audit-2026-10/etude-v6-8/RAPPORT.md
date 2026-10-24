# ETUDE-V6-8 — recette (chaque point prouvé par un test qui LIT le PDF, pas le payload)

Branche `feat/etude-v6`, **pas de merge**. Règle du mandat : chaque point est prouvé par un test qui lit le
PDF généré (`pdftotext`) et l'image du plan (cartouche de la planche embarquée), **jamais le payload**. Le
script de recette (item 5) génère les 2 PDF et lance toutes les vérifications d'un seul coup.

## Cas de recette — Étang-Salé AW 99/451/624/625, résidence étudiante
- **aérien** : 11 T1 + 5 T2 + 2 T3 + 5 T4 → **23 logements, 27 places**
- **sous-sol** : 39 T1 + 5 T2 + 9 T3 + 20 T4 (1 niveau)

## Tests (tous `@pytest.mark.reel`, `tests/test_etude_v6_8_pdf.py`, lecture `pdftotext`)

| Item | Test | Preuve lue dans le PDF |
|---|---|---|
| 1 — une seule implantation (plan = répartition = contrôles = page 1) ; annexe supprimée | `test_item1_une_seule_implantation` | logements **23** et places **27** identiques partout ; `« autre implantation »` absent |
| 2 — un seul n° de document partout | `test_item2_un_seul_numero_de_document` | un **unique** motif `EF-…` dans tout le PDF = celui de l'écran (aérien + sous-sol) |
| 3 — titre + règle de stationnement dans le tableau des règles | `test_item3_titre_et_regle_stationnement` | `Étude de faisabilité — L'Étang-Salé · parcelles AW 99, 451, 624, 625` ; `Stationnement` en section 2 |
| 4 — rampe comptée (≠ 0), sous-sol débordant tant que pleine terre ≥ 30 %, hauteur non citée sous plafond | `test_item4_sous_sol_rampe_hauteur_et_pleine_terre` | `rampe` imprimée, rampe_m2 > 0, pleine terre ≥ 30 % |
| 4 — nouveau maximum sous-sol | `test_item4_sous_sol_nouveau_maximum` | maximum **> 26** |

Le script de recette `scripts/etude_v6_8_recette.py` rejoue tout : `PASS` sur les 5 blocs.

## Ce qui a changé (par la racine)

- **Item 1 — `service._appliquer_programme_au_scenario`** : quand le plan couvre la demande, on rogne le
  **SCÉNARIO lui-même** (on retire les modules en trop en vidant les niveaux hauts, on rogne le
  stationnement au barème) PUIS on **recalcule capacité + contrôles** depuis le plan rogné. Plan masse,
  planche, répartition, coupe, SDP, places, contrôles et SHAB viennent donc TOUS du même plan (fini le patch
  de façade `_trim_variante_au_programme`, supprimé). L'annexe « autre implantation possible »
  (`_annexe`) n'est plus appelée.
- **Item 2 — n° unique** : la planche et la coupe reçoivent le **même** numéro que la page 1 (dérivé du
  `study_id`, `EF-<8>`), plus un numéro daté distinct ; le `.kicker` (CSS majuscules) ne transforme plus le
  numéro (span `text-transform:none`) → un seul motif `EF-…` dans tout le PDF.
- **Item 3 — titre** : la commune manquait dans `payload["terrain"]` ; le titre et la planche la prennent
  désormais de `entrees.commune`. Une ligne **Stationnement** (article + barème PLU) est ajoutée au tableau
  des règles (section 2).
- **Item 4 — sous-sol** :
  - rampe d'accès **comptée** dans le tableau des surfaces de la planche (jamais 0 m²).
  - `_footprint_sous_sol` = **zone d'implantation** (reculs déduits → hors marge plantée) − PPR rouge : le
    sous-sol peut **déborder du bâtiment** ; la pleine terre ≥ 30 % reste garantie par le contrôle
    « Perméabilité ».
  - `_pack_niveau` essaie **les deux orientations** de bandes et garde la meilleure → le −1 occupe
    efficacement l'empreinte.
  - « Ce qui limite » ne cite pas la hauteur quand le bâtiment est sous le plafond (déjà vrai, testé).
  - **Nouveau maximum (39/5/9/20) : 33 logements / 39 places (39 places au niveau −1), bâtiment R+2**
    (ancien plafond : 26 logements / 30 places, R+1).

## Note d'honnêteté (item 1)
Le plan « votre programme » du moteur contient parfois des types **non demandés** ou un bâtiment plus large
que nécessaire (ex. collectif 8 T2 + 4 T3 → le moteur dessine 20 logements avec du T4). Le rognage ramène
le plan à la **typologie exacte du client** (modules, places, répartition, contrôles, SHAB recalculés). Le
contour du bâtiment garde son RDC pleine largeur : le bilan surfacique certifie l'absence de **double
comptabilisation** (aucun recouvrement + somme des surfaces = assiette), ce que vérifie
`plan_sans_chevauchement` — redéfini pour porter sur ces deux garanties (et non la tidiness de l'allée).

## Gardes
| Garde | Résultat |
|---|---|
| `tsc -b` | **0** |
| `vitest` | **297 / 297** |
| pytest implantation + etude_v6 (`-m reel`) | (voir ci-dessous) ; 2 `test_route_*` échecs **pré-existants** (env `labuse_test` vide) |
| chasse_docs | **20 · 0 · 0** |
| chasse_donnees (`--api :8830`) | **23 · 0 · 2** |
| recette `scripts/etude_v6_8_recette.py` | **5 / 5 PASS** |
