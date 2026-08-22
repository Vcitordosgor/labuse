# M134 — Phase A : état des lieux `parcel_residuel` (lecture seule, aucun calcul lancé)

Branche `data/m134-refresh-residuel` @ `dfa402d3`. **Aucun calcul, aucune écriture,
aucun code touché.** Garde-fou conforme (origin/main portait bien `dfa402d3`).

## STOP — verdict à A.3 : le cache est ÉCRASABLE, pas versionné

`parcel_residuel` a pour **clé primaire `parcel_id` SEUL**, aucune colonne `run_id`
(`information_schema` vérifié ; `PRIMARY KEY (parcel_id)`). L'écriture est un UPSERT
`ON CONFLICT (parcel_id) DO UPDATE` (`residuel.py:152-160`). **Un nouveau calcul
ÉCRASE la donnée servie, parcelle par parcelle. Il n'existe aucun moyen de produire
un « run neuf » en parallèle sans toucher au service.**

C'est exactement le cas d'arrêt du mandat (A.3) : « Si l'écrasement est le seul mode
possible → STOP immédiat. On ne détruit pas la donnée servie pour en mesurer une
autre. » **Phase B (calcul dans un run neuf) est donc IMPOSSIBLE en l'état** — elle
exigerait un changement de schéma (versionnement) + tous les consommateurs, ce qui
est un mandat de code, hors périmètre. Je m'arrête et remonte.

Une **voie sûre existe néanmoins pour la mesure** (Phase C sans bascule ni
écrasement) — proposée en fin de rapport, à ton arbitrage.

---

## Les six points

### A.1 — Producteur et entrées

- **Commande** : `labuse compute-residuel` (`cli.py:1246`, `compute_residuel_cmd`)
  → `compute_residuel_batch` (`residuel.py:163`) → boucle `compute_residuel`
  (`residuel.py:80`) → `parcel_faisabilite` (`db.py:182`) → moteur
  `estimate_capacity` (`engine.py`).
- **Entrées consommées** (toutes en lecture) :
  - **PLU calibré** : `resolve_zone` (`plu_rules.py`) → `config/plu_<commune>.yaml`
    (hauteurs, reculs, emprise, `constructible_neuf`). C'est l'entrée qui a dérivé.
  - **Cadastre / géométrie** : `parcels.geom_2975` (surface, emprise insetée
    `_EMPRISE` `db.py:75`, centroïde `_CTX` `db.py:29`).
  - **Zonage fin** : `spatial_layers` kind `%plu%` (sous-zone par centroïde,
    `db.py:32-36`).
  - **Risques / servitudes** : `spatial_layers` kind `pente` (`db.py:37`),
    `trait_de_cote` (`db.py:40`), `safer` (`db.py:44`), voirie (prospect Ud/Uu,
    `db.py:145`), emplacements réservés / prescriptions éco (`_EMPRISE` / `_ECO`).
  - **Bâti existant** : BD TOPO `spatial_layers` kind `batiment` + CoSIA révélé
    `parcel_bati_revele` (`residuel.py:28,44`), via `bati.stats_batch`.
  - **Hypothèses** : `Hypotheses.charger(commune)` (`engine.py`) — coef occupation,
    étage, niveaux bâti par défaut.

### A.2 — Coût

- **Table** : 41 MB (431 663 lignes × 8 colonnes). Backup `parcel_residuel_pre_v8`
  déjà présent (17 MB, copie one-time, cf. A.4).
- **Par parcelle** : coûteux — chaque parcelle déclenche plusieurs requêtes
  spatiales (`_CTX`, `_EMPRISE` avec `ST_Buffer`/`ST_Intersection`/`ST_Union`, stats
  bâti). Pas un simple SELECT.
- **Durée** : non mesurée (aucun calcul lancé). Indice indirect : le cache actuel a
  été produit en **plusieurs lots sur des jours différents** (cf. A.3bis), signe
  d'un traitement long fractionné, pas d'un run unique de minutes.
- **Sous-ensemble** : OUI. `compute-residuel --commune <nom|INSEE>` (`cli.py:1247`)
  + `--chunk` (commit par lot). Un test **une commune** est possible et peu coûteux.
- **Garde disque** : un contrôle `DisqueInsuffisantError` existe côté bascule
  (`bascule_gardes.py:292`) — mais il vise les tables clé-run, pas ce cache léger.

### A.3 — Rattachement au run → **écrasement seul possible** (STOP, cf. ci-dessus)

Pas de `run_id`. UPSERT sur `parcel_id`. Un recalcul **écrase**. Aucun run parallèle.

**A.3bis — le cache n'est même pas un snapshot ATOMIQUE.** `computed_at` se répartit
en **trois lots** :

| Jour | Parcelles | État de code reflété |
|---|---|---|
| 2026-07-29 | **245 319** (57 %) | le plus ancien — pré M-N, M-PLU-REF, M94, M130-12, M131 |
| 2026-08-05 | 8 032 (2 %) | idem, +6 j |
| 2026-08-19 | **178 312** (41 %) | post M-N/M-PLU-REF/M94, **pré** M130-12/M131 |

Deux parcelles voisines peuvent donc refléter des règles PLU **différentes** selon le
jour de leur calcul. La « dérive » n'est pas uniforme.

### A.4 — Consommateurs (une bascule/écrasement les affecte TOUS)

`parcel_residuel` (le cache SDP ; distinct de `parcel_residuel_bati`) est lu par :

| Consommateur | fichier:ligne | Usage |
|---|---|---|
| **Fiche** (potentiel résiduel) | `residuel.py:compute_residuel` via `db.fiche_payload` | bloc résiduel de la fiche |
| **Faisabilité « Par critères »** | `api/modules.py` (SQL sens2) | SDP + filtre du pré-tri |
| **Verdict servi** | `verdict_servi.py:113` | LEFT JOIN cause |
| **Cascade** | `cascade/context.py:603`, `cascade/layers/etage0_ext.py:175,187` | SDP + étage 0 |
| **Scoring P (statique)** | `scoring/p_model/features.py:110-117` | features `pct_potentiel`, `sous_densite`, `sdp_residuelle_m2` |
| **Scoring v2 (pipeline)** | `scoring/p_v2/pipeline.py:398` | JOIN sous-densité |
| **Score E** | `ingestion/score_e.py:98` | LEFT JOIN |
| **Flash / rapport** | `flash/data.py:224-227` | bloc résiduel |
| **Partners / apporteur** | `api/partners.py:106,133` | LEFT JOIN export |

**Point lourd** : ce cache n'alimente pas que l'affichage — il est **entrée du
scoring** (`p_model`, `p_v2`) et de la **cascade**. L'écraser change donc les
features du **prochain run de scoring**, pas seulement les 3 écrans cités par le
mandat.

**Backup existant** : `ensure_backups()` (`bascule_gardes.py:298`) crée
`parcel_residuel_pre_v8` (copie one-time, jamais écrasée). C'est une **sauvegarde de
table entière**, pas un run parallèle : le service lit toujours `parcel_residuel` en
direct.

### A.5 — Désignation du run servi (et pourquoi elle ne s'applique PAS ici)

`Q_A_RUN_LABEL` est lu de **`config/served_run.txt`** (fichier versionné, 1ʳᵉ ligne
non commentée — `score_v_constants.py:55`). Le geste de bascule = **éditer
`served_run.txt`** ; réversible (rééditer, ou `config/run_precedent.txt`, M80).
Override dev via `LABUSE_SERVED_RUN`.

**MAIS** : ce mécanisme gouverne les tables **versionnées par `run_id`**
(`parcel_p_score_v2`, `dryrun_*`). `parcel_residuel` **n'en fait pas partie** (pas de
`run_id`). **Éditer `served_run.txt` ne change RIEN à `parcel_residuel`.** Le
« rafraîchir » n'est pas une bascule de run — c'est un **recalcul + écrasement** d'une
table à-part. Le modèle mental « basculer d'un run à l'autre » ne s'applique pas.

### A.6 — Périmètre de la dérive (plus large que M130-12/M131)

Commits ayant touché les entrées du calcul **depuis le 29/07** (dates réelles) :

| Date | Commit | Effet sur le calcul |
|---|---|---|
| 22/08 | M131 (`9a33a200`) | grave Us + 2AUa-e (hauteur, gel conservé) |
| 22/08 | M130-12 (`19c41006`) | supprime le repli 4 m de `zones_au_st` |
| 22/08 | fix calculette (`5e7f28c3`) | VRD / coût-plancher (bilan, marginal résiduel) |
| 15/08 | M94 (`52bf312f`) | `place_m2`, marquage stationnement |
| 15/08 | M-PLU-REF-B (`ef02646f`) | marquage zone-aware (emprise/constructibilité) |
| 14/08 | M-PLU-REF (`090488cc`) | île-générique nommé + constructibilité |
| 08/08 | M-N (`e69da267`) | hypothèses **par commune** (coef, étage) |

Le lot 29/07 (245 k parcelles) précède **tout** ceci. Le lot 19/08 (178 k) reflète
M-N/M-PLU-REF/M94 mais **pas** M130-12/M131. **La dérive n'est donc pas « le cache ne
voit pas M131 » : c'est « le cache mélange trois états, dont le plus ancien ignore six
mandats ».**

---

## Ce que je propose (à ton arbitrage — je n'exécute rien)

Phase B telle qu'écrite (run neuf parallèle) est **impossible** sans code. Trois
voies, par ordre de sûreté :

1. **Mesure READ-ONLY par échantillon, SANS écrasement (recommandé).** La fonction
   `compute_residuel(session, parcel_id)` (`residuel.py:80`) est **pure/lecture
   seule** — elle renvoie un dict, n'écrit rien (toutes les écritures sont dans
   `compute_residuel_batch`). On peut donc, sur un **échantillon** (ancres + un
   tirage par commune + les zones M130-12/M131), **recalculer en direct** et
   **comparer** au `parcel_residuel` caché — livrant la mesure de dérive de Phase C
   **sans toucher un octet de la donnée servie**. C'est un calcul de lecture ; si tu
   le veux dans le cadre strict « aucun calcul en A », c'est le premier geste de la
   phase de mesure, sur ton go.
2. **Recompute vers une table de travail** (`parcel_residuel_m134`) au lieu de la
   table servie — nécessite **une ligne de code** (rediriger la cible de l'UPSERT) →
   sort du périmètre data. À arbitrer si tu veux un vrai run neuf comparable colonne
   à colonne sur l'île entière.
3. **Backup + recompute + overwrite** (le mode « bascule » historique) : sauver
   `parcel_residuel` → table datée, recalculer sur place (écrase le service **pendant**
   le run), puis servir. **Touche le service** et rejoue les features scoring — le
   plus intrusif, réservé à une vraie bascule décidée.

Mon avis : **(1)** pour mesurer la dérive maintenant, sans risque ; **(2)** si tu veux
la mesure exhaustive île entière (mais c'est un petit code). **(3)** est une bascule,
pas une mesure.

**Je m'arrête ici. Aucun calcul lancé, aucune écriture, service intact.**
CC ne bascule jamais, CC ne merge jamais.
