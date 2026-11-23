# Outil PLU — compte-rendu OUTIL-PLU-FIX-4 (23/11/2026)

> Branche `fix/outil-plu-1`, worktree `~/Desktop/labuse-plu-fix`. Base `labuse` (PostGIS, user OS
> `openclaw`). API locale `http://127.0.0.1:7480`, route réelle `/modules/plu-annuaire/…`. PDF officiels
> dans `~/Desktop/labuse/data/plu_reglements`. Réingestion du jour : **3840 articles, 21 communes servies**.
> **Chaque chiffre est obtenu aujourd'hui par l'API** (ou base↔PDF), avec sa requête. Rejeu :
> `PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python`, `psql -h localhost -U openclaw -d labuse`.

Document d'un bloc (remplace FIX-1/2/3). Méthode suivie : chaque critère a été ATTAQUÉ par ses variantes
(pluriel, majuscules, en-têtes à point/tiret/chiffres romains) ; un critère n'est tenu que s'il y résiste.

## Le modèle

- **Unité de sens = l'ARTICLE ENTIER** (d'un en-tête au suivant), jamais coupé par page ni taille :
  l'exception reste avec sa règle. `src/labuse/ingestion/plu_ingest.py:_split_articles`.
- **La page est une donnée à part** : `page_map` (`[[offset, page], …]`). La recherche localise le mot
  **avec le MÊME stemmer que le FTS** (on teste chaque page de l'article :
  `to_tsvector('fr_unaccent', page) @@ websearch_to_tsquery('fr_unaccent', q)`), pas par `find()`
  littéral → les pluriels/fléchis sont correctement situés. `locate_match`.
- **Toutes les pages du mot sont citées** (`pages_match`), le passage montré est le premier.
- **Étiquette de zone** : l'en-tête de l'article d'abord (tolère le POINT : « Article N.1 » → N), sinon
  la bannière de page. Pas de « zone de chapitre » héritée du sommaire.
- **Gros blocs** (en-tête d'article suivant non détecté, PLU scannés) : re-découpés au NIVEAU EXISTANT
  (section / titre numéroté / intertitre) sans séparer les sous-points d'un article (pas de coupe au
  « 6.3 »). Ce qui reste > 10 pages est listé et SIGNALÉ (« règlement peu structuré »). La couverture
  dit séparément la part indexée à l'article et au chapitre.
- **Dispositions communes** servies à part sous filtre de zone (jamais celles qui nomment une autre zone).
- **Synonymes « recul »** = implantation / retrait.

## Les cinq critères d'arrêt — attaqués par leurs variantes, mesurés aujourd'hui

| # | Critère | Variantes attaquées | Résultat |
|---|---|---|---|
| 1 | 0 résultat citant une page sans le mot | **30 termes** (10 pluriels, 5 verbes conjugués, 5 expressions 2 mots, 10 simples) × 21 communes, page nettoyée ↔ FTS | **0 / 12 993 = 0 %** |
| 2 | 0 article coupé (U2e art.6 avec 6.3, art.13 avec 20 %) | — | art.6 **1 extrait p.91-92, 6.1+6.2+6.3** ; art.13 p.99-100, 20 % |
| 3 | gros blocs découpés / signalés | span ≥ 10 p | 34 → **14 blocs** ; le reste listé + mention écran + couverture article/chapitre |
| 4 | 0 étiquette contredisant l'en-tête | en-têtes **à point** « Article N.1 », à tiret, chiffres | **0** (requête tolérante au point) |
| 5 | aucun croisement entre zones | à l'étiquette ET au **contenu** | **0** à l'étiquette ; **0** en-tête d'article d'une autre classe dans un résultat (y c. communes peu structurées) |

Critère 1 — la localisation utilise **exactement la même correspondance que la recherche** : on ne
`find()` plus la forme littérale (« hauteurs » ratait l'article qui dit « hauteur »), on teste chaque
page avec `to_tsvector/websearch_to_tsquery`. Mesure : `hauteurs` 84/86 pages fausses (relecture-3) →
**0** ; `clôtures` 35/77 → **0** ; `stationnements` 43/48 → **0**. Et **34 articles citent plusieurs
pages** (ex. « Article 10- » p.23-24-25), le passage montré étant le premier.

Critère 4 — `_ZONE_FROM_ART` tolère désormais le point : les **13 « Article N.1..N.13 » de Saint-Denis**
sont étiquetés **N** (étaient A). Requête de contrôle (tolérante au point, VRAIES zones d'en-tête) = **0**.

## Relecture 3 — point par point

| Réf | Verdict | Preuve (API / base) |
|---|---|---|
| Critère 1 (pluriels) | **tenu** | 0/12 993 (30 termes) ; localisation par stemmer Postgres + césure (« station-\nnement » rejoint). |
| Critère 4 (Article N.1) | **tenu** | Saint-Denis « Article N.x » → N ; contrôle tolérant au point = 0. |
| Gros blocs (34/786 p) | **réduit + cadré** | 34 → **14 blocs > 10 p** ; re-découpe au niveau existant ; liste + mention « peu structuré » + couverture article/chapitre (ci-dessous). |
| Croisement au contenu | **tenu** | 0 en-tête d'article d'une autre classe dans un résultat de zone (le bloc UE de Saint-Benoît ne contenait que des réf. CADASTRALES « Zone AK0561 », pas 20 zones ; `_valid_zone` les rejette). |
| « Zone N » sommaire (piscine SD) | **levé** | `q=piscine&insee=97411` → 2 articles, réfs « EMPRISE AU SOL » (p.5) et « ORDURES MÉNAGÈRES » (p.15-24) — plus de réf bidon « Zone N » ; **pages 5 et 22** servies. |
| « Lire l'article entier » sur gros bloc | **cadré** | blocs re-découpés ; ce qui reste (listes patrimoine/cadastre) est signalé « peu structuré ». |
| Dispositions communes (point 8) | **tenu** | servies à part ; 0 nommant une autre zone (vérifié). |
| Césures | **levé** | `_WORD_RE` joint « mot-\nmot » ; `stationnement` singulier 0 page fausse. |

## Gros blocs restants (> 10 pages) et raison — par commune

Communes signalées « règlement peu structuré » à l'écran (7) : La Plaine, Le Port, La Possession,
Saint-Benoît, Saint-Denis, Saint-Joseph, Saint-Pierre. `SELECT insee, gros_blocs FROM plu_couverture
WHERE peu_structure`. Les 14 blocs restants sont des **listes/annexes sans structure plus fine** :

| Commune | bloc (raison) |
|---|---|
| La Possession | « LES BÂTIMENTS REMARQUABLES À PROTÉGER » p.109-164 (liste patrimoine) |
| Le Port | Section III p.268-309, Section I p.178-210, Section IV p.309-319 (sections sans sous-niveau détecté) |
| Saint-Joseph | « RÉFÉRENCE CADASTRALE » p.154-183 (table cadastrale), énergétique p.135-145 |
| Saint-Pierre | « MODE D'EMPLOI » p.14-44 (préambule) |
| Saint-Benoît | patrimoine p.120-138, sous-sections p.9-21/23-34, annexes zones N p.72-82 (PLU 2020 scanné) |
| La Plaine | « OCCUPATIONS ET UTILISATIONS DU SOL » p.176-199 |
| Saint-Denis | « TITRE I » p.125-136 (dispositions générales) |

La page citée reste exacte dans ces blocs (page_map). La couverture le dit : part **à l'article** vs
**au chapitre** (ci-dessous).

## Couverture (honnête) — article vs chapitre

`SELECT insee, pct_indexe, pct_article, pct_chapitre, peu_structure FROM plu_couverture`. Toutes les
communes : **98–100 %** des pages de corps réel atteintes. Part indexée **à l'article** : 100 % (bien
structurées) à 66–71 % (Saint-Benoît, Le Port) ; le reste est servi **au chapitre** (dit à l'écran).
Pages en image (plans/scans) signalées : Saint-Joseph 34, La Possession 58, Saint-Benoît 13.

## Matrice 6 communes × 6 termes (n_total ARTICLES, API aujourd'hui)

`GET /modules/plu-annuaire/search?q=<terme>&insee=<insee>&limit=1` → `n_total`.

| Commune | stationnement | hauteur | emprise | recul* | clôture | piscine |
|---|---|---|---|---|---|---|
| Saint-Denis (97411) | 56 | 53 | 57 | 74 | 19 | 2 |
| La Possession (97408) | 20 | 33 | 47 | 62 | 8 | 15 |
| Saint-Paul (97415) | 48 | 86 | 91 | 136 | 77 | 44 |
| Le Tampon (97422) | 31 | 32 | 51 | 73 | 21 | 8 |
| Trois-Bassins (97423) | 24 | 31 | 27 | 58 | 15 | 11 |
| Entre-Deux (97403) | 21 | 17 | 24 | 43 | 5 | 6 |

(*recul* = synonymes implantation/retrait ; comptes d'ARTICLES.)

## Les quatre jeux de preuves rejoués par l'API

**Relecteur externe (01-PLU-ASTRA) :** casse/accents `clôture=CLÔTURE=cloture=77` ; `AU3st=13` (était 0) ;
`piscine` Saint-Denis **pages 5 et 22** ; UBc La Possession « hauteur » → **ARTICLE UB 10 p.31** ;
dates/procédures des 24 (Saint-Paul « approuvée 17/12/2025 · édition mars 2026 · publiée au GPU 09/03/2026 »,
Trois-Bassins modif 02/06/2022, Saint-Benoît modif 30/06/2026 absente du GPU, Saint-André/Saint-Leu
opposables 2019/2007).
**Relecture 1 :** B1 **tenu** (0 %, pluriels compris) ; B2 `A`↛`AU` (0 croisement) ; B3 (0 bidon) ; C1
`AU3c`=`AU3` ; C5 matrice reproductible ; C7 La Possession dédupliquée (1 idurba) ; M1 recul **136** (était 318).
**Relecture 2 :** D1 exception entière ; D2/D3/D4 (0 doublon strict, chrome≈0) ; **E2 levé = 0** (en-têtes
à point inclus) ; E1 dispositions communes à part.
**Relecture 3 :** critères 1 et 4 (ci-dessus) ; gros blocs réduits+signalés ; croisement contenu = 0.

Pagination : `offset=0` vs `offset=25` (`hauteur`, Saint-Paul) → **0 chevauchement**. Message 0-résultat +
`note_perimetre` au payload.

## Envoi en PROD (NON exécuté)

```bash
LABUSE_DATABASE_URL="postgresql+psycopg://<user>@<host_prod>:5432/<db_prod>" \
LABUSE_PLU_PDF_DIR=<chemin PDF prod> \
PYTHONPATH=src python scripts/reingest_plu_outil_plu_fix_1.py
LABUSE_DATABASE_URL="postgresql+psycopg://<user>@<host_prod>:5432/<db_prod>" \
LABUSE_PLU_PDF_DIR=<chemin PDF prod> \
PYTHONPATH=src python scripts/mesure_couverture_plu_outil_plu_fix_1.py
```
`ensure_ddl` crée la config FTS `fr_unaccent` et les colonnes `pdf_url, page_debut, page_fin, page_map`
(idempotent) ; `plu_couverture` porte `pct_article, pct_chapitre, peu_structure, gros_blocs`. Re-déploiement
back + front à prévoir.

## Réserves honnêtes

- 14 blocs > 10 pages subsistent (listes patrimoine/cadastre/mode d'emploi, PLU scannés sans structure
  plus fine) : **signalés** « peu structuré », page citée exacte, couverture au chapitre dite à part.
- Dispositions générales étiquetées « N » à Saint-Denis (héritées du contexte « Zone N » du document) :
  réfs désormais réelles (« EMPRISE AU SOL »…), zone N imparfaite mais atteignable et paginée juste.
- La Possession : texte indexé édition déc. 2025, lien PDF édition active juin 2026 (note à l'écran).

## Lecteurs de `plu_reglement_extrait`

4 lecteurs (registre `lectures.py`) : l'outil PLU + `implantation/assiette.py`, `implantation/service.py`,
`verite_terrain*.py`. Seuls l'outil PLU et la table ont été modifiés ; le calibrage et la faisabilité non.
