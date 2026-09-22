# RAPPORT VUES & POLISH — mandat du 12/07/2026

**Branche : `feat/vues-polish`** (depuis main `62ca295`, 6 commits + rapport — **aucun merge**).
E2E : `qa/vues/e2e.mjs` (**19 asserts verts**) + non-régression `qa/ux_v1/e2e.mjs` (toujours vert)
+ `tests/test_ux_v1.py` (13 verts, 1 skip documenté). Preuves : `audit_shots/vues_polish/`.
Décision produit appliquée : LABUSE = plateforme d'intelligence foncière, les segments = lentilles.

| # | Item | Commit |
|---|---|---|
| 1 | Renommage « Segments » → « Vues » + route `#pg=vues` (alias legacy `pg=segments`) | `2f95cfe` |
| 2 | Galerie : builder en héros, tuile Foncier, presets → Modèles | `66929cc` |
| 3 | Exemples copilote vérifiés en réel (mapping ci-dessous) | `95887e4` |
| 4 | Sources : fraîcheur prouvée, table `source_checks` | `dd8066c` |
| 5-6 | Loupe alignée · sélecteur communes | `6fdd7c7` |

## 1-2. Vues & galerie

Rail, titres, retours, wording : « Vues » partout (la clé d'état interne reste `segments`,
zéro refactor). La page devient adressable (`#pg=vues`) et l'ancien nom est accepté en alias.
Galerie réordonnée : **héros** « Composez votre ciblage sur 37 critères, ou décrivez-le en
français » (37 = compte DYNAMIQUE des filtres disponibles du registry) avec la recherche NL
intégrée + entrée « vue vierge » ; puis la **vue Foncier — parcelles chaudes & Brûlantes 🔥**
(compteurs SQL réels : 1 158 chaudes · 79 brûlantes au moment du test ; clic → carte, analyse
allumée, liste triée par V) ; puis les 5 presets en **« Modèles — des exemples à dupliquer,
pas des limites »**. Aucun preset supprimé.

## 3. Exemples copilote — mapping vérifié (exécution réelle, traduction Anthropic + comptage SQL)

| Exemple livré | Filtres traduits (vérifiés) | Résultats |
|---|---|---|
| les parcelles en procédure collective | `evenement: true` (+ statuts promues) | 40 |
| chaudes avec vue mer de plus de 1 000 m² | `statuts:[chaude], vueMer, surfaceMin:1000` | 287 |
| les chaudes de Saint-Paul en procédure collective | `statuts:[chaude], commune:Saint-Paul, evenement:true` | 1 |
| sol pollué de plus de 2 000 m² dans l'Ouest | `flags:[sol_pollue], surfaceMin:2000, communes:[Ouest]` | 39 |
| SDP d'au moins 800 m² hors zone à risque | `sdpMin:800, flagsExclus:[risques]` | 7 107 |
| à creuser près d'une usine ICPE | `statuts:[a_creuser], flags:[icpe]` | 1 754 |

**Reformulations (et pourquoi)** — le schéma NL du dashboard (`FILTER_SCHEMA`) ne traduit ni
l'âge du dirigeant, ni la détention/le siège hors île, ni la clôture piscine (réponses
`out_of_scope` VÉRIFIÉES — comportement correct du garde-fou) :
- « dirigeant de plus de 75 ans… » → remplacé par « sol pollué… dans l'Ouest » ;
- « propriétaire hors île, détention longue » → remplacé par « SDP ≥ 800 m² hors zone à risque » ;
- « piscine sans clôture déclarée » → 6ᵉ de mon choix : « à creuser près d'une usine ICPE » ;
- « les Brûlantes de Saint-Paul » traduisait **silencieusement** en simples chaudes (la nuance
  V se perdait — trompeur en démo) → remplacé par « chaudes de Saint-Paul en procédure
  collective » (n=1, honnête).

*Piste produit (hors mandat)* : exposer `brulantes` et les signaux V au schéma NL du copilote
rendrait les 4 exemples originaux traduisibles — petite extension d'`ia.py`, à mandater.

## 4. Sources — fraîcheur prouvée

Le compteur « N/51 sources datées » disparaît ; en-tête : « **Chaque source à sa fraîcheur
maximale, prouvée.** » Par ligne : « donnée du [date réelle — jobs/ingestion_runs, sinon
millésime] » ; la mention « **dernière version publiée — vérifié le [date]** » ne s'affiche
QUE si `source_checks` porte une vérification. Table créée (`data_source_id, verified_at,
note`), **vide — NULL partout** : le mandat d'audit data la remplira ; aucune date inventée
(vérifié : 0 mention affichée, 51/51 `verified_at: null`). Les anciennes mentions
heuristiques « dernière version publiée par la source » sont retirées (affirmation désormais
réservée aux lignes vérifiées).

## 5-6. Polish

Loupe : `pr-1.5` → `pr-[3px]` — le bouton 26 px retrouve des marges symétriques dans son
conteneur 32 px (mesuré 4/3 px, arrondi navigateur). Sélecteur communes : plus aucun
« N chaudes » par ligne ; le ⓘ devient « **voir la fiche commune →** » (même action : volet
contexte SRU/ANRU/PLH/marché ; vérifié E2E sur les 24 lignes).

## Confirmations

Aucun preset supprimé · aucun endpoint métier modifié hors lecture seule (`/sources` +
champ `verified_at` ; table `source_checks` créée par le `create_all` existant) · DA intacte ·
aucun travail mobile 375 (consigne actée pour les mandats suivants) · jamais de merge.
