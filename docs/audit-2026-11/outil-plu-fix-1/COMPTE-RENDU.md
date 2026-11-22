# OUTIL-PLU-FIX-1 — rendre l'outil PLU digne d'un promoteur

> Branche `fix/outil-plu-1` (worktree `~/Desktop/labuse-plu-fix`), API 7480 / front 10280. Réponse
> **point par point à la liste fermée** du contre-audit (`~/Desktop/audit-outils/01-PLU-ASTRA.md`).
> Base locale `labuse` (PostGIS, user OS `openclaw`). Aucune prod touchée, aucun merge dans `main`.
> Captures avant/après : `~/Desktop/outil-plu-fix-1/` (fichiers `00-*` avant relecteur, `01-04-apres-*`).

Interpréteur des rejeux : `PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python` ·
requêtes : `psql -h localhost -U openclaw -d labuse`.

---

## Étape 0 — environnement & périmètre

- `pwd` = `/Users/openclaw/Desktop/labuse-plu-fix` ; branche `fix/outil-plu-1` ; arbre propre au départ.
- Base locale lisible : 21 communes servies, 3414 extraits (état initial, = constat relecteur).
- **Périmètre : `plu_reglement_extrait` a D'AUTRES lecteurs que l'outil PLU** — l'audit §5 (« seul
  consommateur ») est FAUX. Le registre des lectures le prouve
  (`src/labuse/registre/lectures.py:674-680`) : **4 lecteurs** —
  `implantation/assiette.py` (lien PDF de la fiche parcelle à la bonne page : `article_ref, source_url,
  page_pdf` par zone), `implantation/service.py` (`max(millesime)`, `idurba`, compte par zone),
  `verite_terrain.py` (JOIN), `verite_terrain_plu_regles.py` (`texte_verbatim`). **Conséquence
  assumée** : réingérer la table change aussi le lien PDF de la fiche parcelle (assiette). Je n'ai PAS
  modifié `assiette.py`/`service.py` (hors périmètre « règles calibrées ») — seule la table et l'outil
  PLU ont bougé. Les prescriptions de Bras-Panon / Saint-Joseph (table `spatial_layers`, autre session)
  ne sont pas touchées.

---

## Point 1 — documents, dates, procédures

**Fait.** Dates DISTINCTES encodées par commune (`config/plu_dates_gpu.yaml`, source = tableau du
relecteur), fusionnées par l'API (`modules.py:_plu_dates_gpu` + `plu_annuaire_communes`) et affichées
en **format français**, l'écran disant laquelle il montre.

- **Saint-Paul corrigé** : l'écran affichait « édition 17/12/2025 » (FAUX — c'était l'approbation).
  Désormais : *« dépôt 97415_PLU_20251217 · version approuvée le **17/12/2025** · édition PDF **mars
  2026** · publiée au GPU le **09/03/2026** »* (capture `02-apres-saint-paul-dates-couverture-limites.png`).
- **Les Trois-Bassins corrigé** : la modification du **02/06/2022** n'est plus masquée — bloc ambre
  *« ⚠ modification du 02/06/2022 — l'en-tête ne doit pas masquer cette modification »*, en plus de
  l'approbation 21/02/2017 (API : `97423 … modifs:[{date:2022-06-02}]`, vérifié).
- **Procédures** : inventaire par commune avec **libellé distinct** et source — révisions **générales**
  (Saint-Denis, Saint-Paul, Saint-Louis ⟵ [note], Saint-Benoît, Le Tampon) et **allégées** (L'Étang-Salé,
  La Possession), chacune `(source : contre-audit)`. **L'absence de badge ne vaut plus « aucune
  procédure »** : note permanente sous la liste des 24 communes (*« …son absence ne garantit pas
  qu'aucune procédure n'est en cours — vérifiez au GPU / en mairie »*, capture `01`).
- **Saint-André / Saint-Leu** : plus de « aucun document » — l'écran dit *« PLU 2019 (resp. 2007)
  opposable (mairie) »* (`note_doc`, servi par l'API ; vérifié `97409 … note: PLU 2019 opposable…`).
- **Saint-Benoît** : la modification du **30/06/2026** (Beauvallon, AUp→AUe ~3,5 ha), **absente du GPU**,
  est signalée à l'écran (bloc ambre, API : `97410 … modifs:[{date:2026-06-30, note:…ABSENTE du GPU…}]`).
- **La Possession** : dépôt actif `97408_PLU_20260625`, approuvé 25/06/2026, publié 29/10/2026
  (l'ancien `…20251217` n'est plus servi — voir point 5).

Identifiant du dépôt actif (idurba) confronté au GPU pour les 21 servies : **garde-fou OK, 0 écart**
(voir point 2).

---

## Point 2 — téléchargements

**Fait.** Deux liens DISTINCTS désormais :
- **« Télécharger le PLU intégral (.zip) »** = pack **actif** résolu **en direct** sur le GPU
  (EN_VIGUEUR), plus jamais un dépôt archivé. Ex. Saint-Paul pointe
  `…/api/document/0f717…/download/97415_PLU_20251217.zip` (capture snapshot). Les six ZIP archivés du
  relecteur (Les Avirons, L'Étang-Salé, Petite-Île, Le Port, Saint-Louis, Sainte-Marie) **et La
  Possession** pointent maintenant vers le pack actif.
- **Lien « règlement PDF ↗ (p. N) »** sur chaque extrait = **PDF du règlement écrit direct** (colonne
  nouvelle `pdf_url`, `config/plu_destinations/*.yaml meta.url`), **avec l'ancre `#page=N`**. *« Un lien
  .zip ouvre un zip, un lien PDF ouvre un PDF »* — l'inversion de La Possession est levée.

**Garde-fou (idurba, pas nom de fichier)** — `scripts/reingest_plu_outil_plu_fix_1.py:_active_pack` :
pour chaque commune, l'idurba servi par le GPU est comparé à l'idurba de `plu_millesimes` ; un écart
→ la commune n'est PAS servie. Rejeu : les 21 communes `pack=ok`, **0 écart** (La Possession GPU =
`97408_PLU_20260625` = config ✓ ; Petite-Île GPU = `97405_PLU_20230609` EN_VIGUEUR ✓).

**Pièces du pack** (preuve d'actif, via GPU `?grid=insee`) : Petite-Île pack EN_VIGUEUR `2 documents` ;
Le Port `7` (dépôt actif = annulation partielle + jugement, cf. note config `annule_partiel`).
**Saint-Joseph** : pack avec règlement + annexes + zonage, mais **31 pages en image** (plans) et aucun
PDF identifié « règlement graphique » distinct — signalé (`note` config + couverture, voir point 3).

> Réserve honnête : le garde-fou s'exécute **à la réingestion** (le `source_url` stocké est le pack
> actif résolu alors). Un garde-fou *au clic* (revalidation live à chaque téléchargement) serait plus
> fort ; non implémenté ici (il faudrait router le bouton intégral sur `/plu-annuaire/pack`).

---

## Point 3 — découpage & couverture

**Fait.** Deux bugs de découpage corrigés dans `src/labuse/ingestion/plu_ingest.py` :

1. **En-tête de page qui coupe l'article** (`_split_articles`) : les **en-têtes/pieds COURANTS** sont
   retirés avant le découpage (`_detect_chrome` + `_clean_pages`). Une bannière « Zone U2e » répétée en
   haut de chaque page ne crée plus de frontière d'article.
2. **Segment de titre de zone jeté avec son corps** : on n'abandonne plus le texte après un titre de
   zone (dispositions générales après le sommaire). Seuls les titres NUS (< 60 c.) sont sautés.

**Recontrôle Saint-Paul U2e** (exigé) :
- Article 6, §6.3 (saillies), page PDF 92 : **récupéré** — `zone=U2E, article 6, texte contient
  « 6.3 » ET « saillie »`.
- Article 13, seuil 20 % d'espaces libres perméables, page 100 : **récupéré** — texte contient
  « 20 », « perméabl », « espaces libres ».

**Réingestion** des 21 communes servies : `scripts/reingest_plu_outil_plu_fix_1.py` → **3428 extraits,
21 communes** (La Possession dédupliquée : 312 → 166). Réalignée sur `plu_millesimes` + PDF disque.

**Couverture mesurée** (`scripts/mesure_couverture_plu_outil_plu_fix_1.py` → table `plu_couverture`,
servie à l'écran). Métrique = **part des pages de TEXTE atteinte par un extrait indexé** (par span de
pages, comparable au relecteur), + **pages en IMAGE** détectées (scan/plan, « non indexé (image) »).
L'écran affiche désormais *« Indexé : ≈ X % des pages de texte · P pages en image (non indexées) »*.

| Commune (cible) | avant (relecteur) | après % texte | pages image | extraits |
|---|---|---|---|---|
| L'Étang-Salé | 14 % | **98 %** | 1 | 38 |
| Saint-Benoît | 44 % | **97 %** | 12 | 39 |
| Saint-Denis | 76 % | **99 %** | 7 | 280 |
| La Plaine-des-Palmistes | 91 % | **99 %** | 0 | 173 |
| Le Port | 97 % | **99 %** | 0 | 283 |
| Saint-Pierre | 90 % | **100 %** | 2 | 183 |
| Le Tampon (p.86-89) | 95 % | **99 %** | 0 | 222 |

Les pages « entièrement absentes » du relecteur (L'Étang-Salé 17-72, Saint-Benoît 52-124, Saint-Denis
1-23…) étaient pour l'essentiel du **texte perdu au découpage**, désormais réindexé. Reste surtout la
**page 1** (couverture) + les vraies **pages image**. Rejeu : `psql -c "SELECT * FROM plu_couverture
ORDER BY insee"`.

> Réserve : la granularité reste **inégale** sur les communes à longs blocs de dispositions
> (L'Étang-Salé : 98 % du texte couvert mais 38 extraits seulement → gros blocs ; la page citée d'un
> bloc fusionné est sa page de DÉBUT — ex. Saint-Denis « piscine » rendue p.2/p.19 au lieu de p.5/p.22).
> L'inventaire sémantique exhaustif par chapitre reste à affiner (le relecteur le notait déjà).

---

## Point 4 — étiquettes de zone

**Fait.** L'étiquette vient du **chapitre réellement régi** : l'en-tête d'article (« Article Ua 10 »)
sinon la **bannière de page** (« Zones U1a…U1pso » → famille `U1` ; préfixe « Règlement - ZONE UB »
toléré ; `forward-fill` quand le code n'apparaît qu'au titre de chapitre, ex. Saint-Denis « Zone
Uavap »). **Aucun héritage glissant** vers les dispositions générales (évite les faux « N »).
**Validation de forme** : un libellé qui n'a pas la forme d'un code réunionnais (`_ZONE_SHAPE`) devient
« sans étiquette » plutôt qu'une carte mensongère.

- **Zéro faux libellé** : `SELECT … WHERE zone !~ '^[0-9]{0,2}(AU|U|A|N)…'` → **AUCUN**. Les 53 cas
  plancher du relecteur (QUI, EST, DE, R, L, SONT, RURAL, et le « N » de l'art. 10 p.23) sont éliminés.
  Contrôle du cas nommé : Saint-Paul art. 10 p.23 → **`U1`** (était « N »).
- **Petite-Île et Saint-Benoît ne sont plus à 100 % sans étiquette** : Petite-Île **0 → 257/283**
  (zones UB, UC, UD, UE, 1AU, 2AU, A, N…) ; Saint-Benoît **0 → 37/39**.

**Décompte final (étiquetées / total), par commune** (reste = sans étiquette ; 0 fausse partout) :

| insee | commune | étiq./total | insee | commune | étiq./total |
|---|---|---|---|---|---|
| 97401 | Les Avirons | 109/117 | 97414 | Saint-Louis | 159/170 |
| 97402 | Bras-Panon | 131/142 | 97415 | Saint-Paul | 423/449 |
| 97403 | Entre-Deux | 96/99 | 97416 | Saint-Pierre | 127/183 |
| 97404 | L'Étang-Salé | 28/38 | 97418 | Sainte-Marie | 57/62 |
| 97405 | Petite-Île | 257/283 | 97419 | Sainte-Rose | 139/149 |
| 97406 | Plaine-des-Palmistes | 155/173 | 97420 | Sainte-Suzanne | 88/112 |
| 97407 | Le Port | 168/283 | 97421 | Salazie | 87/97 |
| 97408 | La Possession | 155/166 | 97422 | Le Tampon | 203/222 |
| 97410 | Saint-Benoît | 37/39 | 97423 | Les Trois-Bassins | 103/114 |
| 97411 | Saint-Denis | 262/267 | 97424 | Cilaos | 96/139 |
| 97412 | Saint-Joseph | 113/124 | | **TOTAL** | **2993/3428 (87 %)** |

> « Sans étiquette » = dispositions générales / lexique / annexes (pas de zone propre) + quelques
> secteurs multi-zones réduits à leur famille. « Ambiguës » : un article commun à plusieurs secteurs
> porte **la famille** (ex. « Ni et Ntol » → `N`, « U1a…U1pso » → `U1`) — choix assumé, filtrable (point 5).
> Communes encore basses (Le Port 168/283, Saint-Pierre 127/183, Cilaos 96/139) : format de bannière
> non encore capté — amélioration restante, mais **jamais de fausse étiquette**.

---

## Point 5 — recherche

**Fait**, vérifié ligne à ligne (toutes requêtes rejouables, config FTS `fr_unaccent`) :

- **Dédup version active** : La Possession `SELECT count(DISTINCT idurba) WHERE insee='97408'` → **1**
  (`97408_PLU_20260625`), 166 lignes. `hauteur` : **66 → 33** (plus de double comptage).
- **Casse & accents sans effet** : nouvelle config FTS `fr_unaccent` (français + `unaccent`). Cause
  trouvée : base en locale C → `to_tsvector('french','CLÔTURE')` = `clÔtur` (le Ô n'était PAS mis en
  minuscule) **et** `clôtur` ≠ `clotur` (accent). Résultat Saint-Paul : `clôture = clôtures = CLÔTURE =
  cloture = CLOTURE = 88` (était 82/82/**0/0/0**). Preuve live : recherche **CLÔTURE** →
  « Extraits 1–25 sur **88** » (capture `03`).
- **Codes de zone trouvés** : la colonne `zone` est désormais **dans le `tsv`**. `AU3st` à Saint-Paul :
  **0 → 14**.
- **« piscine » à Saint-Denis** : **0 → 2** (texte des dispositions générales réindexé). Page affichée
  p.2/p.19 (page de début du bloc) — voir réserve point 3 ; l'essentiel : la recherche ne rend plus zéro.
- **Pagination / offset** : `search_reglement(offset=…)` + param API `offset` + UI « ← Précédent /
  Suivant → ». `offset=0` et `offset=25` sur `hauteur` Saint-Paul : **0 chevauchement** (total 94) —
  `offset=25` ne renvoie plus les 25 premiers.
- **Filtre zone suit secteurs + renvois au règlement commun** : `zone_candidats` (UBc → {U, UB, UBC},
  AU3c → {AU, AU3}, 2AUd → {2AU}, Ud → {U, UD} ; jamais « A » tiré de « AU »). Contrôle exigé :
  **UBc à La Possession sur « hauteur » → renvoie `UB 10` page 31** ✓ (+ UB 7/8/11/13). Les mêmes
  familles couvrent Ud (Avirons), AU3c (Saint-Paul), 2AUd (Le Tampon).
- **Bloc d'exceptions** : rendu **hors du bloc résultats** (s'affiche même sans extrait trouvé — un
  filtre de zone erroné ne le masque plus) et **DIT sa provenance** : *« Exceptions issues du CALIBRAGE
  LABUSE (config/plu_destinations), pas du texte indexé »* (`exceptions_source`).

**Matrice 6 communes × 6 termes — avant / après** (compte d'extraits correspondants) :

| Commune | station. | hauteur | emprise | recul | clôture | piscine |
|---|---|---|---|---|---|---|
| Saint-Denis | 55→59 | 54→57 | 23→35 | 32→35 | 18→19 | **0→2** |
| La Possession | 40→**20** | 66→**33** | 54→**30** | 30→**15** | 16→**8** | 30→**15** |
| Saint-Paul | 48→52 | 86→94 | 48→61 | 57→61 | **82→88** | 46→46 |
| Le Tampon | 30→31 | 31→32 | 34→37 | 7→7 | 20→21 | 8→8 |
| Trois-Bassins | 24→24 | 31→31 | 9→10 | 18→18 | 15→15 | 11→11 |
| Entre-Deux | 20→21 | 16→17 | 11→18 | 5→5 | 5→5 | 6→6 |

(La Possession **baisse de moitié** = dédoublonnage ; les autres montent légèrement = texte récupéré ;
piscine Saint-Denis 0→2 = couverture récupérée. Les colonnes « Zone U / Zone AU » du relecteur
mesuraient un code exact précis ; non reproduites telles quelles — le filtre par famille les couvre.)

---

## Point 6 — ce que promet l'écran & preuve côté parcelle

**Fait (écran).**
- **Tuile** ajustée (fusion avec MINI-CORRECTIONS-2) : *« Le règlement d'urbanisme de chaque commune. »*
  — plus de « chaque zone » qui surpromettait une couverture exhaustive.
- **Mention VISIBLE des limites** sous la barre : *« ⚠ Recherche communale (texte du règlement). Elle ne
  vérifie pas, à la parcelle, les prescriptions graphiques, les servitudes d'utilité publique ni le PPR
  — à contrôler sur la fiche parcelle et au document graphique. »*

**Rapport (parcelle, lecture seule — aucun calibrage corrigé).** L'affirmation du relecteur (« la fiche
ne sert aucun chiffre de stationnement ») est **partiellement inexacte** : le stationnement **est
calibré et servi au moteur** (`validee=True`), conforme au PDF **3/3**, mais **asymétrie d'exposition** —
aucune des 3 zones n'est un champ de **fiche** (contrairement à hauteur/emprise), et le **gabarit** les
marque `not_integrated` (seul UA est chiffré, via `par_logement` ; Saint-Pierre `par_m2_sdp` et Le
Tampon `par_typologie` → « Règle connue, non chiffrée »).

| Parcelle | Zone | Article (PDF) | Règle PDF | Écart |
|---|---|---|---|---|
| 97414000DK0208 Saint-Louis | UA | UA 12.2 p.23 | 2 pl./logt (social 1, +0,5 visiteur >10 logts) | aucun écart de valeur ; **non servi en fiche** |
| 97416000HT0538 Saint-Pierre | Ud | Ud 6 p.93 | 1 pl./75 m² SDP (+vélo, social 1) | aucun écart ; gabarit « non chiffrée » |
| 97422000AD0887 Le Tampon | Ud | Ud 12.2 p.67 | 0,5/studio · 1/T2 · 1,5/T3+ ; indiv. 1/logt | aucun écart ; gabarit « non chiffrée » |

**Lecture seule — Saint-Benoît, Beauvallon (modif 30/06/2026, AUp→AUe ~3,5 ha).**
- Zone AUp de Beauvallon = `AUp1` (`spatial_layers` id 2166587, 16,10 ha). **23 parcelles** l'intersectent
  (`ST_Intersects(parcels, zone AUp1)`) — toutes à Saint-Benoît. La modif ne touche que ~3,5 ha des
  16,1 ha ; aucun sous-découpage « 3,5 ha » n'existe en base (approximation assumée : 23 couvre tout AUp1).
- Le moteur sert aujourd'hui ces parcelles en **AUp1 / famille AU non-résidentielle** (habitation
  interdite sauf gardiennage), `calibree=False` (« capacité estimée, PLU non calibré »).
- **Source officielle de la nouvelle délimitation AUe : NON exploitable.** GPU `?grid=97410` → un seul
  document `97410_PLU_20200206` EN_VIGUEUR (2020), **aucune entrée 2026**. La modif n'est pas au GPU,
  donc pas dans `spatial_layers`. Rien n'est ingéré (conforme au mandat « rapporte, n'ingère rien »).

---

## Tests / non-régression

- `tsc -b` du front : **vert** (0 erreur). Imports backend : OK.
- Cas du relecteur devenus des lignes de preuve rejouables (ci-dessus). Après réingestion :
  SP art.10 p.23 = `U1` ; Possession dédupliquée ; SD piscine = 2 ; clôture insensible = 88 ;
  AU3st = 14 ; UBc→UB10 p.31 ; offset disjoint ; 0 faux libellé.

## Commande d'envoi en PROD de la table réingérée (NON exécutée)

```bash
# Depuis le dépôt, sur la branche fusionnée, EN POINTANT LA PROD (DSN prod) :
LABUSE_DATABASE_URL="postgresql+psycopg://<user>@<host_prod>:5432/<db_prod>" \
LABUSE_PLU_PDF_DIR=<chemin PDF prod ou ~/Desktop/labuse/data/plu_reglements> \
PYTHONPATH=src python scripts/reingest_plu_outil_plu_fix_1.py        # réingère 21 communes + garde-fou idurba GPU

LABUSE_DATABASE_URL="postgresql+psycopg://<user>@<host_prod>:5432/<db_prod>" \
LABUSE_PLU_PDF_DIR=<chemin PDF prod> \
PYTHONPATH=src python scripts/mesure_couverture_plu_outil_plu_fix_1.py   # (re)peuple plu_couverture
```
`ensure_ddl` crée la config FTS `fr_unaccent`, la colonne `pdf_url` et la table `plu_couverture`
(idempotent). Prévoir un **re-déploiement du back** (nouveaux champs API) et du **front**.

## Restes honnêtes (non bloquants)

1. Granularité des gros blocs de dispositions (page = début du bloc) → sous-découpage fin à faire.
2. Étiquettes basses sur Le Port / Saint-Pierre / Cilaos (format de bannière non capté) — jamais faux.
3. Garde-fou dépôt archivé : à l'ingestion aujourd'hui ; version *au clic* souhaitable.
4. Secteurs multi-zones réduits à la famille (choix assumé, filtrable).
