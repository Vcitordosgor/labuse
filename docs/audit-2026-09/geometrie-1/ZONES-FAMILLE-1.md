# ZONES-FAMILLE-1 — une seule source pour la famille de zone (U/AU/A/N)

Branche `fix/zones-famille-1` (base `fix/exigu-grandes` `e17583c0` ; fix `9cc54e69`).
Résiduel servi = **run 10** (patché sur les 8 communes), score servi = `q_v11_m137`
(**aucune bascule**). Généralise et remplace le correctif borné EXIGU-GRANDES.

---

## Le bug

Plusieurs requêtes SQL **devinaient la famille de zone depuis `spatial_layers.name`**
(`name ILIKE 'U%'/'AU%'`). Or `name` n'est PAS un code normalisé :
- code court dans la plupart des communes (`Ub`, `AUa`) ;
- **libellé littéral** dans 8 communes (`"Secteur de centralité"`, `"Zone urbaine mixte de
  faible densité"`…) → ne commence ni par `U` ni par `AU` → **jamais matché** ;
- forme **phasée** ailleurs (`1AUb`, `2AUc`) → commence par un chiffre → jamais matché.

La clé normalisée existe pourtant : **`subtype` = le typezone GPU** (`attrs->>'typezone'`),
valeurs `U / A / N / AU / AUc / AUs`. Le classement de famille (`zone_servie._FAM`, la cascade
`phase1`, `api/tiles`) l'utilise déjà. Seules les requêtes d'**assiette** lisaient `name` →
dans les 8 communes à libellé littéral, la portion U/AU n'était **jamais clippée** (assiette =
parcelle pleine, capacité **surestimée**) ; sur les zones AU phasées, l'assiette se **vidait**.

## La source unique

Fonction SQL **`labuse_zone_famille(subtype text) → text`** (`models.py`), même logique que
`zone_servie._FAM` et que la contrepartie Python `zone_norm.est_famille` :

```sql
CASE WHEN subtype ILIKE 'AU%' THEN 'AU' WHEN subtype ILIKE 'U%' THEN 'U'
     WHEN subtype = 'A' THEN 'A' WHEN subtype = 'N' THEN 'N' ELSE 'autre' END
```

IMMUTABLE (utilisable en WHERE), créée idempotemment par `create_all` (tests + `init_db`) et
`ensure_residuel_cache` (chemin résiduel/fiche) — `CREATE OR REPLACE` sans verrou de table.

## Chaque endroit corrigé

| fichier | requête / symbole | avant | après |
|---|---|---|---|
| `models.py` | `labuse_zone_famille` + `ensure_zone_famille_fn` | — | **source unique créée** + câblée dans `create_all`/`ensure_residuel_cache` |
| `faisabilite/zone_servie.py` | `_FAM` (feed `_N_ZONES`, `_PARTS`) | `CASE … z.subtype …` en dur | `labuse_zone_famille(z.subtype)` |
| `faisabilite/db.py` | `_EMPRISE` (assiette constructible) | `name ILIKE ANY(:uau_pats) OR (name ~ '^[0-9]' …)` | `labuse_zone_famille(z.subtype) = ANY(:uau_fams)` |
| `faisabilite/db.py` | `_GREVE_CERTAINE` (grève sur portion U/AU) | idem | idem |
| `faisabilite/db.py` | params `_EMPRISE` + `_greve_certaine_m2` | `uau_pats` (`'U%'`) | `uau_fams` (`'U'`) |
| `faisabilite/residuel.py` | `_BATI_ASSIETTE` (bâti sur portion U/AU) + param | `name ILIKE ANY(:uau_pats)` | `labuse_zone_famille(z.subtype) = ANY(:uau_fams)` |

**Déjà corrects (lisent `subtype`/code, non modifiés)** : `cascade/layers/phase1.py`
(`est_famille(i.subtype)`), `api/tiles.py` (`build_parcel_zone_plu`, `CASE … subtype`),
Python `zone_norm.est_famille` / `zonage._positive_prefixes` / `filtres/sources.py` /
`api/projets._zone_famille` (opèrent sur subtype/code résolu).

**Hors périmètre (filtres `name` NON liés à la famille de zone, laissés tels quels)** :
`data_sources.name` (bascule_flux, sources_catalog, sonde_circuit, fraicheur, ortho_tiles,
dispositifs, registre…), `type_local ILIKE` DVF (bilan, marché).

## Preuve

**Non-régression.** 300 parcelles tirées HORS des 8 communes, recalculées avec le code parent
(EXIGU-GRANDES) vs ce correctif : **0 différence** (hors des zones à libellé/phasé, matcher
`subtype` donne exactement le même ensemble que `name` — 0 zone matche `name` U/AU sans que
`subtype` le fasse). Suite de tests : **314 passed**, 2 échecs **pré-existants** (vérifiés à
l'identique sur le parent : `test_vocabulaire_client_gravé` vocabulaire, `test_servitudes`
cascade). Verrou `tests/test_exigu_grandes.py` (3 tests) : la source unique est lue par les
deux requêtes d'assiette + témoins SQL numéroté & libellé-littéral (avant name → NULL, après
famille → portion clippée).

**Dix parcelles des 8 communes — assiette PLEINE → CLIPPÉE** (portion U/AU réelle, recul 3 m) :

| idu | commune | assiette avant (pleine) | portion U/AU après | clip |
|---|---|--:|--:|--:|
| 97403000AS0866 | Entre-Deux | 1 787 | 1 438 | 80 % |
| 97402000AB0684 | Bras-Panon | 4 788 | 3 623 | 76 % |
| 97418000BT0784 | Sainte-Marie | 1 267 | 253 | 20 % |
| 97418000AO0819 | Sainte-Marie | 9 027 | 3 102 | 34 % |
| 97418000AP3779 | Sainte-Marie | 4 604 | 167 | 4 % |
| 97416000EV1344 | Saint-Pierre | 1 999 | 1 744 | 87 % |
| 97421000AV0313 | Salazie | 1 552 | 1 413 | 91 % |
| 97418000AP0696 | Sainte-Marie | 12 162 | 476 | 4 % |
| 97416000EY0558 | Saint-Pierre | 2 227 | 420 | 19 % |
| 97418000AO0423 | Sainte-Marie | 2 385 | 455 | 19 % |

Avant, ces 10 renvoyaient **assiette = parcelle pleine** (aucune zone U/AU matchée par `name`,
`uau NULL → base = full`). Après, l'assiette est **clippée à la vraie portion U/AU** → la
capacité (et l'ER/EBC/grève déduits) portent enfin sur la seule surface constructible.

## Recalcul ciblé — les 8 communes seules

120 583 parcelles des 8 communes (Saint-Pierre, Petite-Île, Bras-Panon, Sainte-Marie,
Saint-André, Salazie, Sainte-Rose, Entre-Deux) recalculées `--into-run 10 --assiette-clippee`
(run 10 dé-servi → 8, patché, re-servi → 10 ; retour `residuel-serve 8`). Le reste de l'île
est inchangé (le fix ne touche que les parcelles touchant une zone U/AU à name littéral/phasé,
concentrées dans ces communes).

- SDP totale île : **80 999 450 → 79 543 072 m² (−1 456 378, −1,8 %)** — la capacité
  surestimée des 8 communes (assiette pleine) est retirée ; le reste de l'île est inchangé.
- parcelles à SDP > 0 : 147 978 → 147 503 (−475).

**Bande 0 par commune (avant → après), les 8 communes concentrent tout le mouvement :**

| commune | bande 0 avant | bande 0 après | Δ0 |
|---|--:|--:|--:|
| Saint-Pierre | 29 949 | 30 120 | +171 |
| Saint-André | 10 739 | 10 905 | +166 |
| Petite-Île | 11 069 | 11 156 | +87 |
| Sainte-Rose | 4 175 | 4 234 | +59 |
| Entre-Deux | 4 128 | 4 174 | +46 |
| Bras-Panon | 4 996 | 5 006 | +10 |
| Salazie | 5 349 | 5 358 | +9 |
| Sainte-Marie | 10 318 | 10 245 | −73 |
| **total 8** | | | **+475** |

Sens attendu : en retirant la capacité fictive (assiette pleine sur une parcelle en partie
A/N), des parcelles retombent en bande 0. Sainte-Marie contre-bouge (−73) : clipper à la
portion U/AU débloque aussi quelques parcelles dont le mélange U+A/N donnait 0 auparavant.
Le Δ des 8 communes (+475) = le Δ île exactement (reste de l'île inchangé).

## Distribution des bandes q_v15 — avant / après

| bande | avant (post-EXIGU) | après (ZONES-FAMILLE) | Δ |
|---|--:|--:|--:|
| 0 | 268 947 | **269 422** | **+475** |
| A | 5 321 | 5 124 | −197 |
| B | 27 495 | 27 293 | −202 |
| C | 39 679 | 39 661 | −18 |
| D | 75 483 | 75 425 | −58 |
| NC | 14 738 | 14 738 | 0 |
| total | 431 663 | 431 663 | 0 |

Correction nette : +475 en bande 0, −475 en constructible (A/B/C/D) — la capacité fictive des
8 communes à libellé littéral est retirée. NC inchangé (seuils inchangés).

**Aucune bascule** — `q_v11_m137` reste servi. `q_v15` = run candidat.
