# M124 — LA PROFONDEUR DVF 2014-2020 : QUALIFICATION (Phase 1, STOP)

*Branche `feat/m124-dvf-archives`. Donnée seulement : modèle, features, clamp 2021 et run servi
intouchés. Chaque chiffre mesuré en base ou sur le miroir.*

---

## LA DÉCOUVERTE QUI CHANGE LE MANDAT

**Les archives 2014-2020 sont DÉJÀ en base.** Le module `src/labuse/ingestion/dvf_histo.py`
(« M3.5 LOT A — profondeur historique DVF 2014-2020 ») a ingéré les 7 millésimes dans la table
dédiée **`dvf_mutations_histo`** : **110 463 lignes · 48 732 mutations · 24/24 communes**. Le dataset
d'entraînement (`p_model/ext_sql.py` → `p_model_ext_dataset`, années 2017-2026) la lit déjà — **le
train 2017-2024 du modèle servi a été bâti dessus**. Deux autres lecteurs : `dvf_prix_neuf.py`,
`defisc_fenetres.py`.

Ce qui RESTE réellement à faire en Phase 2 (après ton GO) :
1. **Catalogue + radar** : la ligne DVF dit « géo-DVF Etalab (millésimes 2021–2025) » — elle ne dit
   PAS la profondeur. À corriger : « 2014-2025 ».
2. **L'arbitrage éditions** (voir caveat n°1) : 4 millésimes rafraîchissables depuis une édition plus
   tardive — ton choix.
3. Le tableau de plausibilité définitif + Phase 3 (golden, doc).

---

## 1. LA SOURCE (URL exacte + licence)

**Source retenue (celle déjà ingérée)** : miroir **data.cquest.org/dgfip_dvf/** (Christian Quest) des
fichiers DGFiP « Demandes de valeurs foncières » — la donnée **brute nationale**, licence
**Licence Ouverte 2.0** (donnée publique DGFiP publiée sur data.gouv.fr avant le retrait des
millésimes ; le miroir republie à l'identique). URL exacte portée **par ligne** en base
(`source_archive`) :

| Millésime | URL ingérée | Édition |
|---|---|---|
| 2014 | `http://data.cquest.org/dgfip_dvf/201910/valeursfoncieres-2014.txt.gz` | 201910 |
| 2015 | `http://data.cquest.org/dgfip_dvf/201910/valeursfoncieres-2015.txt.gz` | 201910 |
| 2016 | `http://data.cquest.org/dgfip_dvf/202110/valeursfoncieres-2016.txt` | 202110 |
| 2017 | `http://data.cquest.org/dgfip_dvf/202204/valeursfoncieres-2017.txt` | 202204 |
| 2018 | `http://data.cquest.org/dgfip_dvf/202304/valeursfoncieres-2018.txt` | 202304 |
| 2019 | `http://data.cquest.org/dgfip_dvf/202404/valeursfoncieres-2019.txt` | 202404 |
| 2020 | `http://data.cquest.org/dgfip_dvf/202504/valeursfoncieres-2020.txt.zip` | 202504 |

**Vérifié le 18/08/2026** : le miroir est vivant (éditions 201904→202504 listées ; l'archive 2014
répond 200). **L'alternative geo-dvf est morte pour ≤ 2020** : `files.data.gouv.fr/geo-dvf/latest/csv/`
ne sert QUE 2021+ (2020 → 404, sondé) — cquest est le seul canal ouvert pour la profondeur.

## 2. LE SCHÉMA (différences vs prod)

La prod (`dvf_mutations_parcelle`, 2021-2025) vient du **geo-DVF Etalab géolocalisé** ; l'histo vient
du **brut DGFiP non géolocalisé**. Le choix **table dédiée** est celui de M3.5, justifié dans le module
(`dvf_histo.py:13`) — et le schéma a été **aligné colonne à colonne** :

| Point | Prod (geo-DVF) | Histo (brut DGFiP) |
|---|---|---|
| Colonnes | 14 | **les 14 mêmes + 2 provenance** (`source_archive`, `millesime_source`) |
| Géolocalisation | longitude/latitude remplies | **0 % remplies** (source non géolocalisée — sans impact : tenure joint par `id_parcelle`) |
| Identifiant parcelle | IDU geo-DVF | **IDU reconstruit** (dept+commune+section+plan zfill(4), même convention que pm_millesimes) |
| Id mutation | id geo-DVF | numéro de disposition DGFiP (formats différents, tables jamais jointes par id) |
| Natures | Vente, VEFA, VTB, Échange, Adjudication, Expropriation | **même taxonomie** (mesuré) |
| Encodage/entêtes | CSV UTF-8 | TXT « | »-séparé ; **tout écart d'entête est LEVÉ, jamais deviné** (`dvf_histo.py:28`) |
| Garde-fou | — | années ≥ 2021 **REFUSÉES** (`dvf_histo.py:190`) — la frontière est structurelle |

## 3. LES VOLUMES (complétude)

| Année | Lignes | Mutations | Bornes de dates |
|---|--:|--:|---|
| 2014 | 11 541 | 5 647 | 03/01 → 31/12 |
| 2015 | 12 017 | 5 953 | 02/01 → 31/12 |
| 2016 | 13 549 | 6 770 | 04/01 → 31/12 |
| 2017 | 15 597 | 7 475 | 02/01 → 31/12 |
| 2018 | 16 631 | 7 185 | 02/01 → 31/12 |
| 2019 | 19 171 | 7 969 | 02/01 → 31/12 |
| 2020 | 21 957 | 7 733 | 02/01 → 31/12 |
| *(prod 2021)* | *24 198* | *9 954* | |
| *(prod 2025)* | *14 523* | *7 184 (année en cours)* | |

**Plausibilité** : croissance régulière 5,6 k → 7,7 k mutations/an qui se raccorde à la prod
(9 954 en 2021 — le marché réunionnais a réellement accéléré post-Covid) ; chaque année couvre
janvier→décembre ; 24/24 communes. Aberrations mesurées, marginales : **355 lignes** valeur foncière
NULL/≤0 (0,3 %) et **70 mutations > 10 M€** (grands ensembles — plausible).

## 4. LA FRONTIÈRE 2020/2021 (dédup)

**Recouvrement = 0, par construction ET par mesure** : prod min = `2021-01-01`, histo max =
`2020-12-31` ; requête croisée (même parcelle + même date dans les deux tables) → **0 ligne** ;
et le garde-fou code refuse tout millésime ≥ 2021 dans l'histo. Une mutation n'existe qu'une fois.

## 5. LE GAIN (la raison du mandat, mesuré)

| | Parcelles du parc avec tenure connue |
|---|--:|
| Prod seule (2021-2025) | 37 314 (**8,6 %**) |
| + histo (2014-2020) | +36 583 nouvelles |
| **Total 2014-2025** | **73 897 (17,1 %)** |

**La profondeur double exactement la tenure connue** — c'était la prédiction du mandat, elle est
vérifiée. (Le bin « inconnu » de `tenure_bin` passera de ~91 % à ~83 % — le reste du parc n'a
réellement pas muté depuis 2014.) **Rien ne bouge avant M127** : le clamp 2021 de `features.py`
reste, le modèle servi est intouché.

## 6. LES CAVEATS (pour ton arbitrage)

1. **Éditions non finales sur 4 millésimes.** Chaque édition DGFiP couvre ~5 ans glissants ; la
   DERNIÈRE édition contenant une année est celle d'octobre N+5. Or : 2015 ingéré de l'éd. 201910
   (finale = 202010, disponible), 2017 de 202204 (finale = 202210), 2018 de 202304 (finale = 202310),
   2019 de 202404 (finale = 202410). L'écart = les transcriptions tardives (typiquement < 1-2 % d'une
   année). 2014 (201910) et 2016 (202110) sont aux éditions finales ; 2020 (202504) est à la dernière
   publiée. **Option A : rafraîchir les 4 depuis leur édition finale (ingestion idempotente,
   DELETE+réinsert par millésime — geste propre). Option B : assumer l'écart, le consigner.**
2. **`docs/DALLE-ALGO.md` n'existe nulle part dans le repo** (aucune branche, aucun commit). La
   Phase 3 demande d'y écrire trois lignes — je propose de le CRÉER avec ces trois lignes, sauf si
   tu me le fournis.
3. Phase 0 faite : BODACC réingéré (678 procédures, radar `a_jour`) ; BAN réingérée (339 915
   adresses, rattachement parcelles stable 416 365) avec un ⚠ dit en clair : **couverture bâti
   résidentiel 86,8 % < seuil 90 %** (le seuil n'est pas desserré) ; CLI `radar-sources` réparé
   (KeyError depuis le merge M123, le cron hebdo crashait).

---

*(STOP Phase 1 rendu — arbitrage Vic : (a) Option A ; (b) DALLE-ALGO.md fourni sur main ; (c) GO.)*

---

# PHASE 2-3 — EXÉCUTION (arbitrage rendu)

## Option A, corrigée par la vérification édition par édition

Les listings complets du miroir (201904→202504) invalident le caveat Phase 1 « 4 millésimes » : les
éditions d'**octobre ne portent l'année la plus ancienne qu'en `-s2`** (semestre 2 seul — ex. 202010 :
`valeursfoncieres-2015-s2.txt` ; 202410 : `2019-s2`) et **202210/202310 n'existent pas** sur le miroir.
La dernière édition **année-pleine** de chaque millésime :

| Millésime | Dernière éd. pleine | Ingérée | Verdict |
|---|---|---|---|
| 2014 | 201910 | 201910 | ✓ déjà finale |
| **2015** | **202004** | 201910 | **rafraîchi** |
| 2016 | 202110 | 202110 | ✓ |
| 2017 | 202204 | 202204 | ✓ (202210 n'existe pas) |
| 2018 | 202304 | 202304 | ✓ (202310 n'existe pas) |
| 2019 | 202404 | 202404 | ✓ (202410 = 2019-s2 seul) |
| 2020 | 202504 | 202504 | ✓ |

**2015 rafraîchi** (`ingest_millesime` idempotent, DELETE+réinsert, URL/édition par ligne) :
12 017 → **12 031 lignes (+14)**, 5 953 → **5 963 mutations (+10)** — les transcriptions tardives
attendues. Frontière 2020/2021 **re-prouvée après** : recouvrement 0.

## Catalogue + radar

La ligne DVF dit désormais : **« géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020 »** — appliqué
par le geste standard `persist_millesime` (chaîne versionnée dans `fraicheur.py`, le cron réécrit la
même) ; `seed_sources.py` dit le canal histo (cquest, Licence Ouverte, URL par ligne, frontière sans
recouvrement).

## Plausibilité (définitif)

24/24 communes **chaque** millésime 2014-2020 · part « Vente » stable 85,8 → 93,6 % · 355 lignes
VF NULL/≤0 (0,3 %) · 70 mutations > 10 M€ (grands ensembles).

## LE TABLEAU FINAL — mutations 2014-2025

| Année | Mutations | Lignes | Canal |
|---|--:|--:|---|
| 2014 | 5 647 | 11 541 | archives DGFiP (histo) |
| 2015 | 5 963 | 12 031 | archives DGFiP (histo) — *rafraîchie éd.202004* |
| 2016 | 6 770 | 13 549 | archives DGFiP (histo) |
| 2017 | 7 475 | 15 597 | archives DGFiP (histo) |
| 2018 | 7 185 | 16 631 | archives DGFiP (histo) |
| 2019 | 7 969 | 19 171 | archives DGFiP (histo) |
| 2020 | 7 733 | 21 957 | archives DGFiP (histo) |
| 2021 | 9 954 | 24 198 | géo-DVF (prod) |
| 2022 | 10 259 | 23 580 | géo-DVF (prod) |
| 2023 | 8 836 | 20 999 | géo-DVF (prod) |
| 2024 | 7 465 | 19 251 | géo-DVF (prod) |
| 2025 | 7 184 | 14 523 | géo-DVF (prod, année en cours) |
| **TOTAL 2014-2025** | **92 440** | **213 028** | **recouvrement dédupliqué : 0** |

## Vérification (rien de servi ne bouge)

- **Golden : 0 FAIL** (86 PASS, 33 INDÉTERMINÉ = quota env) — le run servi ne lit pas l'histo.
- **Suite : 1 618 passed, 1 failed** — le failed (`test_demo_51e_appel_429`) est un **flake de fuseau
  PRÉ-EXISTANT, sans lien M124** : `partners.py:458` compare `date.today()` (machine CEST, 18/08) au
  `jour` PostgreSQL (TZ Indian/Reunion, déjà 19/08) → entre 20 h et minuit CEST la porte quota se
  réinitialise au lieu de lever 429. Mesuré : PG `current_date`=2026-08-19 vs Python
  `date.today()`=2026-08-18 au moment du run. Repassera vert au matin ; **défaut TZ réel à corriger
  hors M124** (consigné, pas silencié — classe M90).
- **DALLE-ALGO.md** (fourni par Vic sur main, `6ed75755`) : les points 1 (« sous 1 an ») et 2 (les
  4 candidates M127) y étaient déjà ; point 3 mis à jour — **« profondeur DVF 2014-2025 ACQUISE
  (M124), clamp 2021 à lever au réentraînement »** + la vérité des éditions.

**Clamp 2021, modèle, features, run servi : INTOUCHÉS** (contrat du mandat tenu).
