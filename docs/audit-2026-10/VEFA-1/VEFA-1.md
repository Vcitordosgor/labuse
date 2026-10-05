# VEFA-1 — Servir toutes les ventes VEFA que DVF contient

**Branche** `fix/vefa-1` (worktree `~/Desktop/labuse-vefa1`, depuis `origin/main`) · **Mesuré le** 2026-10-05 ·
**Base** `labuse` (lecture) · **Recompute borné** : `spatial_layers (kind='vefa_neuf')` uniquement.

Constat de départ (RECETTE-2 / D3) : **2 687 VEFA « brut »** dans DVF, **1 245 servies** (−1 442 ;
Saint-Denis −339, Saint-Paul −273, Le Tampon −237) → « — » en €/m² neuf dans l'outil Communes et
prix de sortie « calculé sur un échantillon amputé ».

---

## 1. Unité de comptage retenue — et ce que devient le −1 442

**Unité : la mutation distincte (`id_mutation`)**, nature `Vente en l'état futur d'achèvement`, 24 communes,
sur la fenêtre du moteur (`neuf_vefa` : 5 ans). DVF porte **6 641 lignes** VEFA (une ligne par lot/parcelle)
pour **2 686 mutations** : le « brut » et le « servi » doivent se compter dans la **même** unité.

Recomptage (psql, `timezone=Indian/Reunion`) :

| Grandeur | Valeur | Rapprochement D3 |
|---|---:|---|
| Lignes VEFA (tout le millésime 2021-2025) | 6 641 | — |
| **Mutations VEFA brut** (tout le millésime) | **2 686** | = D3 « 2 687 » ✔ |
| Mutations VEFA dans la fenêtre `now()−5 ans` (AVANT) | 2 350 | — |
| **Servi** (fenêtre `now()−5 ans`, dénominateur toutes surfaces) | **1 244** | = D3 « 1 245 » ✔ |

**Le « brut » était déjà des mutations, pas des lignes.** L'hypothèse « lignes vs mutations » du mandat
(point 1) est donc **écartée** : les deux comptent des mutations. Le −1 442 de D3 vient de **deux**
effets superposés, mesurés ici :

1. **Décalage de période** (le brut est pris sur *tout* le millésime, le servi sur la fenêtre glissante
   `now()−5 ans`) : 2 686 → 2 350 = **−336**, un pur artefact de comparaison + un **bug de fenêtre**
   (ci-dessous). À période égale, l'écart réel est 2 350 → 1 244 = **−1 106**.
2. **Absence de surface d'habitation** : l'essentiel du −1 106 restant.

L'écart ne « fond » donc pas entièrement — il reste une perte réelle — **mais sa plus grosse part est
légitime** (ventes sans surface, non calculables) et **une part est un vrai bug** (fenêtre). Les deux
correctifs ci-dessous re-servent **+172 mutations** (1 244 → 1 416, +13,8 %) sans jamais inventer un prix.

---

## 2. Où elles se perdent — pertes par étape

Universe = **2 686 mutations VEFA** (grain `id_mutation`, nature VEFA, 2021-2025, 24 communes).
Comptage à chaque étape du pipeline `neuf_vefa_commune` :

| # | Étape | Entrée → sortie | Perdues | Exemple `id_mutation` | Exclusion légitime | Raison |
|---|---|---|---:|---|:---:|---|
| 1 | Lecture + grain mutation (6 641 lignes → mutations) | 6 641 L → 2 686 M | — | `2021-1672907` (6 lignes = 1 mutation) | n/a | normalisation ligne→mutation |
| 2 | Filtre période | 2 686 → 2 686 | **−336** sous `now()−5 ans` → **0 après ancrage** | ventes de janv.–sept. 2021 | **NON — bug** | fenêtre glissante `now()` sur un millésime **figé** 2021-2025 ; corrigé par ancrage sur `max(date_mutation)` |
| 3 | Surface d'**habitation** présente (Σ surf. appart/maison > 0) | 2 686 → 1 429 | **−1 257** | `2024-1190924` (lignes `type_local` NULL, surface NULL) | **OUI** | à l'acte VEFA le bâti n'est pas construit → surface réelle vide ; Carrez absente dans `dvf_mutation_detail` (vérifié : ne récupère que ~6 cas) → €/m² non calculable, jamais inventé |
| 4 | Prix non symbolique (`valeur` > 1 000 €) | 1 429 → 1 429 | −0 | — | OUI | garde-fou ventes à 1 € |
| 5 | €/m² habitable ∈ [50 ; 20 000] | 1 429 → **1 416** | **−13** | `2022-1640940` (27 037 €/m²) | **OUI** | surface d'habitation captée minime vs valeur (lots non bâtis / commerciaux non captés) → ratio aberrant |
| | **SERVI (après correctifs)** | | **= 1 416** | | | |

Les **1 257** de l'étape 3 contiennent **1 170** mutations *sans aucune surface* (toutes lignes
`type_local` NULL) **et ~87** mutations ne portant qu'une surface **non-habitation** (local commercial
seul). Ces 87 étaient *servies à tort* avant le correctif (voir point 3).

> Note sur l'étape 3 (honnêteté de la hachure) : ces mutations sans surface ne sont **pas perdues du
> comptage** — elles restent dans `n_ventes_vefa_total` (le volume réel). Le moteur distingue le volume
> (`n_total`) du nombre à prix calculable (`n`) ; la hachure ne dit « peu de ventes » que lorsque le
> **volume** est faible, pas quand seule la surface manque.

---

## 3. Correctifs — à la source

Deux correctifs, dans **le** moteur VEFA unique (`neuf_vefa_commune`) et ses copies de fenêtre (pour que
« fiche = table = carte » gardent la même fenêtre). Aucune dépendance, aucun scoring, aucun front touché.

### 3.1 Fenêtre ancrée sur la dernière vente (plus de `now()` glissant)

Le millésime géo-DVF est **figé** (2021-2025). Un prédicat `date_mutation >= now() − 5 ans` érode
silencieusement le vieux bord de la fenêtre à mesure que l'horloge avance : au 2026-10-05 il jetait déjà
**336 mutations** de 2021 (−14 % de volume brut) pour rien. On ancre la fenêtre sur `max(date_mutation)`
des VEFA — **exactement** le principe que `detail_commune` appliquait déjà à son pivot 12 mois (« calé sur
la dernière vente observée, pas sur l'horloge système »).

- `src/labuse/ingestion/dvf_marche.py:165` — constante `VEFA_NATURE_SQL`.
- `src/labuse/ingestion/dvf_marche.py:175` — `vefa_fenetre_predicat()` : **le** prédicat de fenêtre, source unique.
- `src/labuse/ingestion/dvf_marche.py:217` — `neuf_vefa_commune` lit ce prédicat.
- `src/labuse/ingestion/vefa_neuf.py:87` — libellé millésime (dernière vente = ancre).
- `src/labuse/ingestion/vefa_neuf.py:155,164,184` — `detail_commune` (tendance, répartition) sur la même fenêtre ancrée.

Effet : servi **1 244 → 1 502** (+258) à dénominateur inchangé.

### 3.2 Dénominateur = surfaces des **lots d'habitation** seuls

Le €/m² d'un **logement** neuf ne doit sommer au dénominateur que les **lots d'habitation**
(`Appartement`, `Maison`). L'ancien `sum(surface_reelle_bati)` sommait aussi le **commercial/industriel**
(23 240 m² sur 115 lignes VEFA) et aurait sommé les parkings s'ils portaient une surface — ce qui **diluait**
le €/m² des mutations mixtes. C'est la mise en œuvre exacte du point de vigilance du mandat : *valeur
foncière totale / **somme des surfaces habitables des lots d'habitation**, jamais / un seul lot, jamais en
éliminant la mutation.*

- `src/labuse/ingestion/dvf_marche.py:170` — `VEFA_LOTS_HABITATION = ("Appartement","Maison")` (+ fragment SQL, source unique).
- `src/labuse/ingestion/dvf_marche.py:213` — `neuf_vefa_commune` : `sum(...) FILTER (WHERE type_local IN (...))`.
- `src/labuse/ingestion/vefa_neuf.py:160` — même filtre dans la tendance de `detail_commune`.
- `src/labuse/ingestion/vefa_neuf.py:124,201` — texte du « **i** » : exclusions légitimes écrites dans la colonne.

Effet (sur la fenêtre ancrée) : servi **1 502 → 1 416** (−86 mutations *pur non-logement* correctement
retirées) ; les **94 mutations mixtes** restantes obtiennent un €/m² **corrigé** (cf. témoin ci-dessous).

**Net des deux correctifs : 1 244 → 1 416 servies (+172, +13,8 %)** ; médiane île 4 789 → 4 749 €/m² (−0,8 %).

### 3.3 Tests unitaires — 3 mutations **réelles** (`tests/test_vefa_lots_habitation.py`)

| Cas | `id_mutation` | Composition | €/m² attendu | Ce que le test grave |
|---|---|---|---:|---|
| Lot simple | `2021-1673153` | 1 appart. 41 m², 176 200 € | **4 298** | `valeur / surface` |
| **Multi-lots + parking** | `2021-1672907` | 3 appart. (45+45+59=149 m²) **+ 3 dépendances** | **4 538** | valeur / **Σ** surfaces habitables ; **pas** / un seul lot (= 15 024) ; parkings exclus ; **jamais éliminée** |
| **Mixte habitation + commercial** | `2022-1639750` | 1 appart. 104 m² **+ 2 locaux comm. (177+137 m²)**, 630 360 € | **6 061** | locaux commerciaux **exclus** du dénominateur ; **pas** 1 508 €/m² (si tout sommé) |

Un 4ᵉ test grave l'**ancrage de fenêtre** (une vente ~4,8 ans avant la dernière reste servie, là où un
`now()−5 ans` la jetterait). **27 tests VEFA passent** (2 skips d'environnement), suite marché/comparateur
incluse (39 passed).

---

## 4. Re-servir et mesurer

Recompute **borné** et **journalisé** du cache marché, précédé d'un **dump** (voir `dumps/`).

- **Tables dumpées avant** : `spatial_layers (kind='vefa_neuf')` → `dumps/spatial_layers_vefa_neuf_AVANT.csv`
  (24 lignes, géométrie omise car régénérée à l'identique depuis `communes974.geojson`) ;
  `dvf_prix_sortie_neuf` → `dumps/dvf_prix_sortie_neuf_AVANT.csv` (12 lignes).
- **Recompute exécuté** : `build_vefa_neuf` uniquement (DELETE + 24 INSERT sur `kind='vefa_neuf'`).
  Journal : `vefa_neuf : 10 communes peintes, 14 hachurées (< 8 ventes)` ; millésime ancré `2025-12-31`.
- **Non recomputé, volontairement** : `dvf_prix_sortie_neuf` (voir § 4.3 — découplé du VEFA ; le recomputer
  n'aurait reflété qu'un rafraîchissement de données, pas le correctif).

### 4.1 Tableau 24 communes — brut · servi avant/après · €/m² neuf avant/après

`servi avant` = fenêtre `now()−5 ans` + dénominateur toutes surfaces ; `servi après` = fenêtre ancrée +
lots d'habitation. « — » = sous le seuil de 8 ventes (médiane absente, jamais extrapolée).

| Commune | INSEE | VEFA brut | Servi avant | Servi après | €/m² avant | €/m² après | Δ |
|---|---|---:|---:|---:|---:|---:|---:|
| Saint-Denis | 97411 | 606 | 267 | **355** | 5 000 | 4 878 | −2,4 % |
| Saint-Paul | 97415 | 570 | 297 | **326** | 4 760 | 4 745 | −0,3 % |
| Le Tampon | 97422 | 339 | 102 | **130** | 4 891 | 4 785 | −2,2 % |
| Saint-Pierre | 97416 | 283 | 149 | **158** | 4 958 | 4 931 | −0,5 % |
| Saint-Leu | 97413 | 269 | 146 | **155** | 4 789 | 4 958 | +3,5 % |
| La Possession | 97408 | 179 | 86 | **88** | 4 212 | 4 221 | +0,2 % |
| Sainte-Marie | 97418 | 149 | 75 | **83** | 4 159 | 4 190 | +0,7 % |
| L'Étang-Salé | 97404 | 146 | 63 | **66** | 4 778 | 4 796 | +0,4 % |
| Petite-Île | 97405 | 48 | 28 | 25 | 5 208 | 5 277 | +1,3 % |
| Les Trois-Bassins | 97423 | 39 | 15 | 15 | 6 370 | 6 370 | 0 % |
| Saint-Louis | 97414 | 24 | 6 | 5 | — | — | — |
| Saint-Benoît | 97410 | 8 | 6 | 6 | — | — | — |
| Saint-André | 97409 | 8 | 1 | 1 | — | — | — |
| Le Port | 97407 | 7 | 1 | 1 | — | — | — |
| Les Avirons | 97401 | 4 | 0 | 0 | — | — | — |
| Saint-Joseph | 97412 | 4 | 0 | 0 | — | — | — |
| Sainte-Suzanne | 97420 | 2 | 1 | 1 | — | — | — |
| Bras-Panon | 97402 | 1 | 1 | 1 | — | — | — |
| Salazie | 97421 | 1 | 1 | 1 | — | — | — |
| Entre-Deux · La Plaine-des-Palmistes · Saint-Philippe · Sainte-Rose · Cilaos | — | 0 | 0 | 0 | — | — | — |
| **ÎLE** | | **2 686** | **1 244** | **1 416** | 4 789 | 4 749 | −0,8 % |

Les trois communes citées par D3 sont **toutes re-servies davantage** : Saint-Denis +88, Saint-Paul +29,
Le Tampon +28. **Aucune** variation de médiane ne dépasse 10 % (§ 4.4).

### 4.2 Outil Communes — nombre de « — » en €/m² neuf, avant → après

Deux surfaces portent le €/m² neuf, **mesurées séparément** :

| Surface | « — » avant | « — » après | Détail |
|---|---:|---:|---|
| **Tableau comparateur** (live, `neuf_vefa_commune`) | 14 | **14** | 10 communes peintes avant comme après — le correctif **n'ajoute aucune** commune au-dessus du seuil (les 14 autres ont 0 à 6 ventes VEFA : sparsité **réelle** du marché, pas un trou de données). Il **fiabilise** l'effectif (servi +13,8 %). |
| **Couche carte** (cache `spatial_layers`) | 17 | **14** | le cache était **périmé** (ère 36 mois, 7 peintes) ; le rebuild le réaligne sur le moteur → **10 peintes**. |

Nouvellement peintes sur la carte après rebuild : **Les Trois-Bassins, Petite-Île, Sainte-Marie** (aucune
perdue). Captures `dumps/spatial_layers_vefa_neuf_{AVANT,APRES}.csv`.

> Lecture honnête : le correctif ne fait **pas disparaître** les « — » du comparateur. 14 des 24 communes
> ont < 8 ventes VEFA à prix calculable même sur 5 ans — c'est l'état **réel** du marché réunionnais du
> neuf (quasi uniquement du collectif, concentré sur 10 communes). Le gain est la **robustesse** (effectif)
> et la **justesse** (dénominateur), pas un peignage artificiel.

### 4.3 Prix de sortie des bilans — 3 témoins, avant → après

| Témoin | Parcelle | Prix de sortie avant | Prix de sortie après | Niveau |
|---|---|---:|---:|---|
| BZ1065 | `97411000BZ1065` (Saint-Denis) | 4 275 €/m² | **4 275 €/m²** | commune (n=77) |
| AM0097 | `97404000AM0097` (L'Étang-Salé) | 4 375 €/m² | **4 375 €/m²** | repli île |
| ES0266 | `97414000ES0266` (Saint-Louis) | 4 375 €/m² | **4 375 €/m²** | repli île |

**Inchangé — et c'est le résultat, pas une omission.** Le prix de sortie des bilans vient de
`dvf_prix_sortie_neuf`, construit par `build_prix_neuf` à partir d'un **proxy par permis** :
ventes (`nature = 'Vente'`) d'appartements réalisées ≤ 3 ans après l'achèvement d'un PC, hors bailleurs
sociaux — **jamais** la nature d'acte VEFA. Ce pipeline est **découplé** du moteur VEFA : le correctif de ce
mandat ne le touche pas. La prémisse D3 (« échantillon amputé » *de la VEFA*) ne s'applique donc pas au prix
de sortie ; son éventuelle amputation (filtre `surface >= 20`, exclusion sociale, fenêtre permis) relève
d'un autre pipeline et sort du périmètre VEFA-1. Le cache n'a **pas** été reconstruit pour ne pas confondre
un rafraîchissement de données avec l'effet du correctif.

### 4.4 Variations de prix neuf > 10 % — aucune

Sur les 10 communes servies, la plus forte variation de médiane est **Saint-Leu +3,5 %** (4 789 → 4 958).
Toutes les autres sont sous ±2,5 %. **Aucune commune > 10 %** : le correctif *stabilise* la médiane (il
retire la dilution commerciale et élargit l'effectif) au lieu de la faire bondir — ce qui est le
comportement attendu d'une correction honnête. Détail du mécanisme sur un cas mixte (Les Trois-Bassins,
mutation `2022-1639750`) : son €/m² passe de **1 508** (tout sommé) à **6 061** (habitable) ; mais comme la
médiane communale agrège 15+ ventes, l'effet net sur la médiane reste < 1 %.

---

## 5. Ce qui reste exclu — et pourquoi (écrit dans le « i »)

| Exclusion | Volume (millésime) | Statut | Écrit où |
|---|---:|---|---|
| Mutations **sans surface d'habitation** (bâti non construit à l'acte, Carrez absente au 974) | **1 170** | Légitime — €/m² non calculable, jamais inventé ; comptées au **volume** (`n_total`), pas au prix | « i » couche + `n_ventes_vefa_total` |
| Mutations **pur non-logement** (surface uniquement commerciale/industrielle) | **~87** | Légitime (correctif) — pas un logement, hors €/m² logement | `type_local IN ('Appartement','Maison')` |
| €/m² habitable **hors bornes** [50 ; 20 000] | **13** | Légitime — surface d'habitation captée minime vs valeur → ratio aberrant | borne documentée |
| Ventes à **≤ 1 000 €** (symbolique) | 0 | Légitime | garde-fou |
| Communes **sous le seuil** de 8 ventes à prix calculable | 14/24 | Légitime — sparsité réelle, hachure honnête (jamais extrapolée) | profil `neuf_vefa`, « i » |

Texte du « i » mis à jour (`vefa_neuf.py:124,201`) : *« €/m² = médiane sur les lots d'habitation
(commercial/parkings exclus du dénominateur) ; ventes sans surface d'habitation comptées au volume, pas au
prix — jamais extrapolé. »*

---

## Synthèse

- **Unité** : mutation (`id_mutation`). Le « brut » de D3 était déjà des mutations ; le −1 442 mélangeait
  deux périodes + une vraie perte (surface absente).
- **Deux correctifs à la source** : fenêtre ancrée (+258) et dénominateur lots d'habitation (−86, justesse).
  **Net +172 servies** (1 244 → 1 416, +13,8 %), **sans inventer un prix**.
- **Outil Communes** : la carte re-peint 3 communes (17 → 14 « — ») après rebuild ; le comparateur reste à
  14 « — » (sparsité réelle). **Prix de sortie découplé** du VEFA → témoins inchangés (résultat explicite).
- **Aucune** variation de médiane > 10 %. Cache recomputé **borné + journalisé + dumpé**.
