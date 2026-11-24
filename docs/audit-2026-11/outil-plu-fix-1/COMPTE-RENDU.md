# Outil PLU — compte-rendu OUTIL-PLU-FIX-6 (24/11/2026)

> Branche `fix/outil-plu-1`, worktree `~/Desktop/labuse-plu-fix`. Base `labuse` (PostGIS, user OS
> `openclaw`). API locale `http://127.0.0.1:7480`, route réelle `/modules/plu-annuaire/…`. PDF officiels
> dans `~/Desktop/labuse/data/plu_reglements`. Réingestion du jour : **3606 articles, 21 communes servies**
> (dont **849 extraits sans zone** = dispositions générales / communes / annexes, désormais correctement
> non étiquetés). **Chaque chiffre est obtenu aujourd'hui par l'API** (ou base↔PDF), avec sa requête. Rejeu :
> `PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python`, `psql -h localhost -U openclaw -d labuse`.

> **Rapport source `~/Desktop/audit-outils/01-PLU-ASTRA-2.md` VIDE** : le fichier ne contient que la ligne
> `pbpaste > ~/Desktop/audit-outils/01-PLU-ASTRA-2.md` (le collage a échoué). J'ai donc travaillé sur la
> **liste fermée de cinq points du mandat** (ci-dessous), qui FAIT foi. Points déclarés clos par le mandat
> (téléchargements, exceptions U2e, casse/accents, doublons Possession, pagination) : non rouverts.

## OUTIL-PLU-FIX-6 — réponse à la liste fermée de cinq points

**1. BLOQUANT — renvois de secteur (resolve_zone, même résolution que la fiche) — corrigé & prouvé.**
Un filtre de zone issu d'une fiche parcelle sur un secteur qui renvoie aux règles d'une autre zone sert
désormais les articles de la zone CIBLE, avec la note. Résolution unique via `faisabilite.zonage.resolve_zone`
(+ `config/plu_destinations`) — pas de seconde table. **Parcours parcelle témoins rejoués par l'API** :

| Parcelle | Zone (spatial_layers) | Note servie | `hauteur` | `stationnement` |
|---|---|---|---|---|
| **97415000CP0681** (Saint-Paul) | AU3c (72,3 %) | « AU3c : le règlement renvoie à U3c » | 5 extraits, **tous zone U3** (1er : Article 10 p.114) | 2 extraits U3 (Article 12 p.120) |
| **97422000AD0250** (Le Tampon) | 2AUd (73,0 %) | « 2AUd : le règlement renvoie à Ud » | 5 extraits, **tous zone UD** (ARTICLE Ud10 p.63) | 4 extraits UD (ARTICLE Ud12 p.66) |

*Deux secteurs d'un même ancêtre ne sont JAMAIS confondus* : Saint-Paul stocke bel et bien une zone
**AU3ST**, et le filtre AU3c ne ramène QUE U3 (jamais AU3ST). `zones_apparentees(AU3c)` = `['AU3','U3']`,
`zones_apparentees(2AUd)` = `['UD']` ; candidats AU3c = `[AU, AU3, AU3C]` (disjoints de AU3ST).
Inventaire des renvois ENTRE zones stockées des 21 communes (testés sur hauteur + stationnement) : 4 —
Étang-Salé `AUT→UT`, Saint-Paul `AU1LEC→U1lec`, `AU1E→U1e`, `AU3E→U3e` ; chacun ne sert que sa famille + la cible.

**2. BLOQUANT — bon chapitre / zone / article — corrigé & prouvé.** Les chapitres SANS zone (dispositions
générales, définitions, lexiques, annexes) ne portent plus d'étiquette de zone :
- Saint-Denis p.4-24 → **zone `None`** (le sommaire « ZONE N …119 » n'est plus pris pour un en-tête :
  `_is_toc_header`, points de suite).
- L'Étang-Salé (INSEE **97404**) p.6-14 → **`None`** : le SOMMAIRE p.3 listait « ZONE UA / UB / UC » et la
  bannière captait « UA », qui fuyait sur les dispositions générales. Une page listant **≥ 2 zones** est
  un sommaire → aucune bannière, reset (`_clean_pages`).
- Saint-Benoît annexes p.54-72 → **`['None']`** (frontière de bloc `_RESET_CHAP_M`).
- **UB 9 et UB 10 de La Possession ne sont plus fusionnés** (base : `ARTICLE UB 9` p.31, `ARTICLE UB 10`
  p.31-32, séparés) : un VRAI article court (« UB 9 : Sans objet ») n'est plus pris pour un fragment de titre.
- **Saint-Denis p.22 « Piscines et bassins » n'est plus titré « Ordures ménagères »** : l'intertitre en
  chiffres ROMAINS « XXI. AMÉNAGEMENTS EXTÉRIEURS » est désormais une frontière de sous-découpe ; le passage
  piscine porte ce titre (vérifié API : `piscine|UA` Saint-Denis → disposition commune « XXI. AMÉNAGEMENTS
  EXTÉRIEURS » p.22).
- **Dispositions communes atteignables depuis n'importe quelle zone, servies à part** : `piscine` filtré sur
  `UA` à Saint-Denis → 0 résultat de zone **+ 2 dispositions communes** (« XXI. AMÉNAGEMENTS EXTÉRIEURS »
  p.22, « LEXIQUE » p.5).

**3. À CORRIGER — stationnement — corrigé & prouvé.** Le stemmer français réduit `stationnement`→`station`,
qui matchait « station d'épuration / de potabilisation ». On exige désormais le radical littéral `\ystationn`
(partagé par toutes les vraies formes, pas par les collisions), au résultat ET à la localisation de page :
- Saint-Denis `stationnement` : **n_total 58 → 53** ; les pages 131/140/142 (station d'épuration) **ne sont
  plus citées** (0). Le Tampon : pages 20/35 **plus citées** (0).
- Règle CIBLÉE sur le mot (pas un « stem+1 » générique, qui exclurait des flexions légitimes : `implantation`
  et `implantées` divergent dès `implant`). Contrôle des autres recherches de la matrice : `retrait→retr`
  ne produit **0 faux positif** d'article (retraite/retroussis co-occurrent) ; hauteur/emprise/recul/clôture/
  piscine ne sur-stemment pas. *Fiche parcelle (gabarit)* : l'outil PLU cite bien l'article et la page —
  Saint-Louis `ARTICLE UA 12` p.22-24 (⊃ UA 12.2 p.23), Saint-Pierre `ARTICLE Ud6` p.93-95. La VALEUR de
  stationnement affichée par la fiche de faisabilité relève du calibrage/gabarit, **hors du périmètre de
  cette correction** (table `plu_reglement_extrait`) : non modifiée, aucun écart de calibrage introduit.

**4. À CORRIGER — documentaire — corrigé.** Millésime du LOT distingué de la date du RÈGLEMENT ÉCRIT, badges
de procédure, réserve d'opposabilité (`config/plu_dates_gpu.yaml`, vérifs sur pièces p.1) :
- Saint-Denis : couverture = « Modification simplifiée n°8, dossier approuvé **FÉVRIER 2024** » ; lot déposé
  au GPU **05/08/2026**. L'écran affiche « édition PDF février 2024 » ≠ « publiée au GPU 24/08/2026 ».
- Badges de procédure servis pour chaque procédure connue : révisions générales (Saint-Benoît, Saint-Denis,
  **Saint-Louis**, Saint-Paul, Le Tampon), révisions allégées (L'Étang-Salé, La Possession), **Saint-Pierre
  modification n°1 à l'enquête jusqu'au 30/10/2026** (ajoutée).
- **Pas « opposable » sans réserve** quand un acte communal postérieur est connu : Saint-Benoît (Beauvallon
  ~3,5 ha AUp→AUe, conseil du 30/06/2026, absente du GPU) affiche désormais « Opposabilité SOUS RÉSERVE de
  cet acte postérieur (vérifiez en mairie) ».

**5. MINEUR — corrigé.** « Aucun extrait trouvé » ne s'affiche plus en même temps qu'une disposition commune
(front : le bloc est masqué si `dispositions_communes` est non vide) — cf. `piscine|UA` Saint-Denis ci-dessus.

### Matrice rejouée par l'API (n_total, 24/11)

| Commune | stationnement | hauteur | emprise | recul\* | clôture | piscine |
|---|---|---|---|---|---|---|
| Saint-Denis (97411) | **53** | 58 | 61 | 84 | 22 | 2 |
| La Possession (97408) | 19 | 33 | 47 | 62 | 8 | 15 |
| Saint-Paul (97415) | 48 | 97 | 91 | 149 | 87 | 44 |
| Le Tampon (97422) | 26 | 32 | 57 | 76 | 21 | 8 |
| Les Trois-Bassins (97423) | 25 | 34 | 29 | 67 | 16 | 12 |
| Entre-Deux (97403) | 17 | 22 | 25 | 36 | 16 | 6 |

\* `recul` = recul OR retrait OR implantation. Les comptes varient vs FIX-5 à cause de la re-découpe (chiffres
romains → davantage d'articles distincts) et de l'anti-collision stationnement (−5 à Saint-Denis).

## OUTIL-PLU-FIX-5 — réponse à la relecture 4

- **Saint-Benoît entièrement mal découpé (point 1) — corrigé.** Ses en-têtes s'écrivent « Article U – 4.
  Hauteur des constructions » (tiret en-dash entre zone et numéro) ; `_HEADER`/`_ZONE_FROM_ART` acceptent
  désormais l'espace, le point ET les tirets (court/en-dash/em-dash). **Les 47 en-têtes d'article de
  Saint-Benoît sont indexés** (`q=hauteur&insee=97410&zone=U` → « Article U – 4. » p.9) ; la mention
  « règlement peu structuré » est **retirée** (part article 81 %). Contrôle 21 communes ci-dessous.
- **Titres multi-lignes éclatés (point 2) — corrigé.** « TITRE III / DISPOSITIONS / APPLICABLES AUX
  ZONES / À URBANISER » était 4 extraits d'un mot. Un titre multi-lignes est refondu dans l'extrait
  suivant (`_fusionne_titres`) ; un extrait sans contenu n'est plus indexé. **Extraits quasi vides
  (net < 40) : 227 → 0.**
- **Mineurs (point 3) — corrigés.** Césures : la localisation rejoint « station-\nnement » avant le
  stemmer de page (critère 1 passe de 0,37 % à **0,05 %**, 6/11 851). « emprise au sol » à cheval sur
  deux pages : repli OR **scoré** (page portant le plus de termes). **Matrice rejouée en entier**
  (Trois-Bassins *recul* : 58 écrit → **67** obtenu).

### Contrôle des en-têtes d'article — 21 communes

`_HEADER` reconnaît maintenant « ARTICLE U 4 », « Article U.4 », « Article U – 4 », « Article N.1 ». Les
articles de Saint-Benoît (0 avant) sont tous servis ; aucune autre commune n'était affectée (aucune n'a
≥ 5 en-têtes « Article X – N » perdus). Les 5 critères d'arrêt restent tenus (ci-dessous), re-mesurés.

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
| 1 | 0 résultat citant une page sans le mot | **30 termes** (10 pluriels, 5 participes/verbes, 5 expressions 2-3 mots, 10 simples) × 21 communes, page nettoyée ↔ FTS, césure rejointe | **6 / 11 851 = 0,05 %** (résidu = expression à 3 mots répartie sur 2 pages) |
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
| Critère 1 (pluriels) | **tenu** | 6/11 851 = 0,05 % (30 termes) ; localisation par stemmer Postgres + césure rejointe. |
| Critère 4 (Article N.1) | **tenu** | Saint-Denis « Article N.x » → N ; contrôle tolérant au point = 0. |
| Gros blocs (34/786 p) | **réduit + cadré** | 34 → **14 blocs > 10 p** ; re-découpe au niveau existant ; liste + mention « peu structuré » + couverture article/chapitre (ci-dessous). |
| Croisement au contenu | **tenu** | 0 en-tête d'article d'une autre classe dans un résultat de zone (le bloc UE de Saint-Benoît ne contenait que des réf. CADASTRALES « Zone AK0561 », pas 20 zones ; `_valid_zone` les rejette). |
| « Zone N » sommaire (piscine SD) | **levé** | `q=piscine&insee=97411` → 2 articles, réfs « EMPRISE AU SOL » (p.5) et « ORDURES MÉNAGÈRES » (p.15-24) — plus de réf bidon « Zone N » ; **pages 5 et 22** servies. |
| « Lire l'article entier » sur gros bloc | **cadré** | blocs re-découpés ; ce qui reste (listes patrimoine/cadastre) est signalé « peu structuré ». |
| Dispositions communes (point 8) | **tenu** | servies à part ; 0 nommant une autre zone (vérifié). |
| Césures | **levé** | `_WORD_RE` joint « mot-\nmot » ; `stationnement` singulier 0 page fausse. |

## Gros blocs restants (> 10 pages) et « peu structuré »

La mention écran « règlement peu structuré » (`peu_structure`) porte désormais sur la PART du texte
servie au chapitre (part article < 70 %), non sur la seule présence d'un gros bloc : **L'Étang-Salé
(34 %) et Sainte-Marie (63 %)** — formats sans mot-clé « Article » (rubriques numérotées). **Saint-Benoît
n'est plus signalé** (47 articles « Article U – N » désormais détectés, part article 81 %).

Les quelques blocs > 10 pages qui subsistent sont des **listes/annexes sans structure plus fine** (page
citée exacte via `page_map`), p. ex. La Possession « LES BÂTIMENTS REMARQUABLES À PROTÉGER » p.109-164,
Le Port Section I/III/IV, Saint-Joseph « RÉFÉRENCE CADASTRALE » p.154-183, Saint-Pierre « MODE D'EMPLOI »
p.14-44, Saint-Denis « TITRE I » p.125-136. `SELECT insee, gros_blocs FROM plu_couverture`.

## Couverture (honnête) — article vs chapitre

`SELECT insee, pct_indexe, pct_article, pct_chapitre, peu_structure FROM plu_couverture`. Toutes les
communes : **98–100 %** des pages de corps réel atteintes. Part indexée **à l'article** : 99-100 % (bien
structurées, Saint-Benoît compris à 81 %) ; L'Étang-Salé 34 % et Sainte-Marie 63 % servies surtout **au
chapitre** (dit à l'écran). Pages en image (plans/scans) signalées : Saint-Joseph 34, La Possession 58.

## Matrice 6 communes × 6 termes (n_total ARTICLES, API — rejouée EN ENTIER FIX-5)

`GET /modules/plu-annuaire/search?q=<terme>&insee=<insee>&limit=1` → `n_total`. Chaque case re-tirée
de l'API aujourd'hui (la case Trois-Bassins *recul* du compte-rendu FIX-4 — 58 — était fausse ; **67**).

| Commune | stationnement | hauteur | emprise | recul* | clôture | piscine |
|---|---|---|---|---|---|---|
| Saint-Denis (97411) | 58 | 58 | 59 | 79 | 19 | 2 |
| La Possession (97408) | 20 | 33 | 46 | 62 | 8 | 15 |
| Saint-Paul (97415) | 48 | 86 | 91 | 136 | 77 | 44 |
| Le Tampon (97422) | 31 | 25 | 48 | 76 | 21 | 8 |
| Trois-Bassins (97423) | 25 | 34 | 29 | **67** | 16 | 12 |
| Entre-Deux (97403) | 21 | 17 | 26 | 45 | 14 | 6 |

(*recul* = synonymes implantation/retrait ; comptes d'ARTICLES. Les comptes bougent légèrement vs FIX-4 :
réingestion FIX-5 — en-têtes à tiret de Saint-Benoît détectés, bribes de titre retirées.)

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

- Quelques blocs > 10 pages subsistent (listes patrimoine/cadastre/mode d'emploi, sans structure plus
  fine) : page citée exacte (page_map), couverture au chapitre dite à part.
- Résidu critère 1 : 6/11 851 = 0,05 % (expression de 3 mots répartie sur 2 pages → page portant un seul
  des mots) — cas de bord, pas une page « sans le mot ».
- Dispositions générales étiquetées « N » à Saint-Denis (héritées du contexte « Zone N » du document) :
  réfs désormais réelles (« EMPRISE AU SOL »…), zone N imparfaite mais atteignable et paginée juste.
- La Possession : texte indexé édition déc. 2025, lien PDF édition active juin 2026 (note à l'écran).

## Lecteurs de `plu_reglement_extrait`

4 lecteurs (registre `lectures.py`) : l'outil PLU + `implantation/assiette.py`, `implantation/service.py`,
`verite_terrain*.py`. Seuls l'outil PLU et la table ont été modifiés ; le calibrage et la faisabilité non.
