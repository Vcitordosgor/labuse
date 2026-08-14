# AUDIT M88 — ANC : du signal Estimé au fait de secteur (Phase 1, mesure pure)

**Branche `feat/m88-anc-secteur`. Aucune écriture d'affichage. STOP après ce rapport, arbitrage Vic.**
Mesuré le 14/08/2026 sur la base `labuse` (run non concerné : mesure statique).

## TL;DR
- Le **taux brut de non-raccordement** existe déjà, propre, en base : `anc_maille_taux.taux_non_racc`
  (RP2022, variable EGOUL, agrégé IRIS + commune). **Sans** bonus rural, **sans** borne 5-95,
  **sans** seuil — ceux-ci ne vivent que dans `proba_anc`, en aval.
- **Couverture : 423 243 / 431 663 parcelles (98,0 %)** tombent dans un IRIS doté d'un taux.
  Seulement **8 420 (2,0 %)** sans IRIS — dont **6 450 = La Plaine-des-Palmistes** (commune entière,
  taux IRIS non diffusé par l'INSEE mais **taux commune disponible en repli**).
- **Vraisemblance : CONFIRMÉE et forte.** Sur les parcelles zonées, celles en **ANC** tombent dans
  des IRIS à taux médian **54,0 %**, celles en **collectif** à **16,7 %**. Le taux discrimine — il
  veut dire quelque chose. **On peut enchaîner la Phase 2.**
- Le taux **n'est pas** une précision à défendre : ce n'est pas une prédiction parcellaire, c'est un
  fait de secteur (% de logements). Rien à valider, tout à sourcer.

---

## 1 — Le taux brut (RP2022, aucune transformation)

Table `anc_maille_taux` (peuplée par `ingest_insee_egoul`, `src/labuse/ingestion/anc.py:89-146`) :

| colonne | sens |
|---|---|
| `maille` | `iris` \| `commune` |
| `code` | code IRIS (9) ou INSEE commune (5) |
| `insee` | code INSEE de la commune |
| `taux_non_racc` | **% de résidences principales NON raccordées au réseau collectif** |
| `n_logements` | somme des poids IPONDL |
| `millesime` | `RP2022` |

Origine du taux (`src/labuse/ingestion/anc.py:102-139`) : fichier détail INSEE **RP2022 Logements**
(`FD_LOGEMT_2022`), variable **EGOUL** (DOM only : 1=égout, 2=fosse, 3=puisard, 4=à même le sol),
pondérée **IPONDL**. Non-raccordés = **modalités 2, 3, 4**. `taux = 100 × poids(2,3,4) / poids_total`.
**C'est un pourcentage de logements, pas un score.** Le bonus rural (+15 pts si > 100 m de toute
zone U), la borne 5-95 et le seuil vivent en aval, dans `proba_anc` — jamais dans cette table.

350 lignes : **326 IRIS** + les communes. 148 307 résidences principales 974 diffusées.

## 2 — Couverture (jointure spatiale indexée centroïde → IRIS)

Rattachement = `ST_Contains(spatial_layers.geom_2975, ST_Centroid(parcelle))`, `kind='iris_insee'`
(pas de table de jointure : spatial pur).

| population | parcelles | % |
|---|---|---|
| **Dans un IRIS doté d'un taux** | **423 243** | **98,0 %** |
| Sans IRIS exploitable → Absent | 8 420 | 2,0 % |
| *Total* | *431 663* | *100 %* |

Les 8 420 « sans IRIS » se concentrent sur :

| commune | sans IRIS | note |
|---|---|---|
| **La Plaine-des-Palmistes** | **6 450** | commune ENTIÈRE : IRIS unique non diffusé (secret statistique). **Taux COMMUNE disponible** (repli). |
| Les Avirons | 703 | bords de polygone (centroïdes hors IRIS) |
| Saint-Paul | 342 | bords |
| Saint-Joseph / Sainte-Rose / Salazie / … | 108-222 | bords |

> À noter : la couche **servie aujourd'hui** ne couvre que **278 685** parcelles (les **bâties**,
> `emprise_batie_m2 > 20` — filtre du job). L'écran actuel dit donc « Absent » à ~144 000 parcelles
> non bâties qui sont pourtant dans un IRIS doté. Le fait de secteur, lui, existe pour 98 %.

## 3 — Distribution du taux

**Tous IRIS (326)** : min 0 · Q1 **18,1** · médiane **54,6** · Q3 **91,4** · max 100.

Ventilation demandée — les hauts se distinguent-ils de l'urbain ?

| groupe | n IRIS | Q1 | médiane | Q3 |
|---|---|---|---|---|
| **4 communes zonées** (urbain / littoral) | 124 | 8,5 | **17,4** | 63,6 |
| **20 autres** (hauts / rural) | 202 | 40,5 | **69,8** | 95,6 |

**Oui, nettement.** Médiane 17,4 % dans l'urbain zoné contre 69,8 % dans les hauts. C'est cet écart
qui donne sa valeur à l'information : dans les hauts, la majorité des logements ne sont pas raccordés.

## 4 — Cohérence de lecture (vraisemblance, PAS précision)

**Test IRIS-level** (le bon niveau) — parcelles zonées, rattachées au taux de LEUR IRIS :

| verdict du zonage | n parcelles | taux IRIS médian | taux IRIS moyen | Q1–Q3 |
|---|---|---|---|---|
| **ANC** | 9 909 | **54,0** | 57,5 | 44,5–77,1 |
| **collectif** | 47 798 | **16,7** | 30,4 | 8,5–49,3 |

Le taux brut est **3× plus élevé** là où le zonage officiel dit ANC. Signal monotone, franc : le taux
de secteur est vraisemblable. **Pas de STOP pour absence de corrélation.**

⚠ **Piège écarté — le niveau commune est CONFONDU** (à ne pas utiliser) :

| commune zonée | % ANC parmi zonées | taux COMMUNE RP2022 |
|---|---|---|
| Saint-Paul | 0,0 % | **49,3 %** |
| L'Étang-Salé | 22,5 % | 57,2 % |
| Saint-Denis | 36,4 % | 23,1 % |
| Le Port | 0,3 % | 6,8 % |

Saint-Paul affiche 49 % de non-raccordement au niveau commune mais 0 % d'ANC parmi ses parcelles
zonées : le polygone de zonage ne couvre que le cœur urbain collectif, le 49 % vient des hauts hors
zonage. La cohérence ne se lit qu'à l'IRIS — d'où le test ci-dessus.

## 5 — Millésime (ce qui sera affiché)

- Taux ANC : **`RP2022`** (stocké dans `anc_maille_taux.millesime` et `config/anc_vegetation.yaml`).
- **MAIS** : dans `data_sources`, `source_millesime` et `source_horizon_at` sont **NULL** pour
  « INSEE RP2022 — fichier détail Logements (EGOUL) » **et** pour « Contours IRIS (IGN/INSEE) ».
  → **La date de publication INSEE du RP2022 et le millésime des contours IRIS ne sont stockés nulle
  part.** Il faudra les **établir et enregistrer** (dataset INSEE 8647099) avant de les afficher —
  jamais inventer une date, jamais afficher la date d'ingestion. **Point bloquant pour la Phase 2.**

---

## Ce que sert l'écran aujourd'hui (à remplacer, Phase 2)

`src/labuse/anc_service.py:53-61` — état **Estimé** : `proba_anc >= 75` → libellé
**« Secteur à forte proportion d'ANC »**. C'est un quasi-verdict adossé à un score composite
(taux + bonus rural + borne) dont on ne peut plus nommer la source. Servi aux **bâties** seulement.
Callers uniques : fiche `api/app.py:_anc_block` (~2607) et PDF `flash/data.py:_bloc_anc` (~483).

## Sort de `proba_anc` / `parcel_anc` (usage interne)

`proba_anc` alimente le signal **`anc_mutation`** (`zone_anc='anc' OU proba_anc ≥ 70`,
`src/labuse/ingestion/anc.py:335-342`) écrit dans `parcel_signals`. **Mais** `anc_mutation`
n'apparaît dans **aucune config de scoring** (grep : présent seulement dans `anc_vegetation.yaml`) —
le signal est écrit, pas manifestement pondéré sur le score servi. → **`parcel_anc` tend vers
dormant.** Le mandat impose de **conserver table + job** quoi qu'il arrive ; reste à **confirmer**
si `parcel_signals(anc_mutation)` pèse réellement (sinon : conservée mais **déclarée dormante et
signalée** comme telle).

---

## Décisions demandées à Vic (STOP)

1. **Périmètre du fait de secteur** : le servir aux **98 %** (y compris parcelles non bâties, c'est un
   fait de secteur, pas une propriété de la parcelle) ou rester aux **bâties** comme aujourd'hui ?
   *Reco : les 98 % — le taux décrit le secteur, pas la parcelle.*
2. **Repli commune** quand l'IRIS n'est pas doté (récupère La Plaine-des-Palmistes = 6 450 + les bords) :
   servir le taux à la **maille commune**, maille DITE à l'écran ? *Reco : oui — même RP2022, maille
   plus grossière mais nommée ; sinon toute une commune reste « Absent » à tort.*
3. **Millésime** : où enregistre-t-on la date de publication RP2022 (INSEE) et le millésime IRIS,
   aujourd'hui absents ? Sans eux, la Phase 2 ne peut pas afficher honnêtement la date.
4. **`parcel_anc`** : confirmer usage réel (`anc_mutation` pesé ?) → conservée « active », sinon
   conservée **dormante** et signalée. Dans tous les cas : jamais supprimée.

Formulation pressentie du fait de secteur (Phase 2, pour mémoire, à valider) :
« **Dans ce secteur (IRIS *nom*), *X* % des logements ne sont pas raccordés au réseau collectif.**
Source : INSEE RP2022. À l'échelle du secteur, pas de la parcelle. » — **aucun seuil, aucune bascule,
aucun « probablement »**, un taux bas n'est jamais un feu vert. Renvoi SPANC maintenu.
