# M47 — PHASE 0 · CONSTAT (lecture seule, STOP arbitrage Vic)

**Branche** `m47-rebuild-renouvellement`, base `main` `ebf78f0d`. **Tout vérifié sur pièces**
(code + base `labuse`, run servi `q_v8_calibre` lu depuis `config/served_run.txt`).
**Zéro écriture servie** : les rebuilds à blanc sont `commit=False` + `rollback` ; table servie
recomptée intacte (67 258) après coup. Aucun tier, poids, golden touché.

> ⚠️ **La prémisse centrale du mandat est périmée — exactement le piège pc_caducs/M31.**
> `parcel_renouvellement` **n'est PAS morte sur q_v7** : elle a déjà été **rejouée sur le run
> servi q_v8_calibre le 2026-08-05** (67 258 lignes). Le mandat reste utile, mais l'objet réel
> n'est **pas un rebuild** (déjà fait, reproductible bit-à-bit) — c'est le **câblage au geste**
> pour qu'elle ne remeure jamais, + une **garde de cohérence**, aujourd'hui absents.

---

## P0.1 — Sur quel run la table est-elle réellement bâtie ? (constaté, non présumé)

| Fait | Valeur constatée |
|---|---|
| Table existe | oui (`to_regclass` non nul) |
| Lignes | **67 258** |
| `run_label` (unique) | **`q_v8_calibre`** = le run servi |
| `computed_at` (unique batch) | **2026-08-05 01:34:17+04** |

**Le backlog disait « bâtie sur q_v7, jamais rejouée ». FAUX.** Mieux : le run `q_v7` n'existe
même pas — la cascade ne contient que `q_v7_defisc` et `q_v8_calibre` (`q_v7` = 0 ligne). La
table porte le run servi et un stamp du 5 août. Provenance : le code `renouvellement.py` n'a
qu'**un seul commit** (M-RENOUV A, jamais modifié) → le rebuild du 5 août est une **exécution
CLI `labuse renouv`** (opération DB, hors git), cohérente avec la reco de l'audit train5
`docs/mandats/train5/AUDIT2_RENOUVELLEMENT.md` (« rebuild réel = 1 commande »).

## P0.2 — Définition exacte du segment (documentée depuis la source)

`src/labuse/renouvellement.py`. Une parcelle entre **ssi les 5 conditions** :
1. **Exclue à l'étage 0 par BatiLayer** (`dryrun_cascade_results`, `layer_name='bati'`,
   `result='HARD_EXCLUDE'`), motif franc parmi `deja_bati_probable` / `deja_bati` /
   `ensemble_bati` (reconnu par préfixe — miroir Python/SQL testé).
2. **Zone PLU ∈ {U, AU}** (`p_model_ext_dataset`, `annee = max(annee)` = 2026).
3. **Capacité** : `sdp_residuelle_m2 > 100` **OU** `surface_m2 ≥ 600` (seuils config).
4. **NON copro** (`p_model_ext_copro` : rnic OU dvf).
5. **NON foncier public** (cascade `foncier_public` HARD_EXCLUDE).

**Score /100 = heuristique déterministe transparente** (percent_rank intra-segment,
`config/renouvellement.yaml`, Σ poids = 100 vérifié) : potentiel résiduel 40 · assiette 25 ·
marché 20 · divisibilité 15 (0|15). **Aucun modèle appris.** Seuls **cascade bati +
foncier_public** sont lus au `run_label` ; zone/capacité/copro/divisibilité lisent le **dataset
partagé** à l'as-of `max(annee)`.

## P0.3 — Rebuild à blanc sur `q_v8_calibre` + diff (rollback, zéro écriture)

Entonnoir mesuré : **195 209** bâties exclues → **182 330** U/AU → **71 899** capacité →
**70 128** hors copro → **67 258** hors foncier public.

**Diff servi vs rebuild à blanc (q_v8) : identité parfaite.**

| | entrées | sorties | stables |
|---|---|---|---|
| servi vs rebuild `q_v8_calibre` | **0** | **0** | **67 258** |

→ La table servie **est** un rebuild correct et courant, reproductible bit-à-bit.

**Nuance sur les « 68 445 d'origine » (constaté, corrige le backlog ET l'audit train5).**
Rebuild à blanc sur `q_v7_defisc` **aujourd'hui = 67 258 aussi** (entrées 0, sorties 0 vs q_v8).
Le segment est **quasi run-indépendant** : ses seuls intrants run-scopés (cascade bati +
foncier_public) sont **identiques** entre `q_v7_defisc` et `q_v8_calibre`. Le « Δ −1 187 »
attribué au « calibrage v8 » par l'audit train5 est en réalité du **drift du dataset dans le
temps** (les 68 445/73 078 sont des mesures passées d'un `p_model_ext_dataset` différent),
**pas** l'effet de la bascule de run. Le diff run-à-run **live** est **0**.

## P0.4 — Tables sœurs run-scopées (balayage `information_schema` : colonne run_label)

7 tables portent `run_label`. Verdict de chacune (détail machine :
`sister_tables_inventaire.csv.gz`) :

| Table | Runs présents | Écrite par | Verdict M47 |
|---|---|---|---|
| **parcel_renouvellement** | q_v8_calibre | **CLI `renouv` (ISOLÉE)** | **ORPHELINE** — rebâtie q_v8 (5 août) mais **hors de tout geste** → à câbler + garde |
| dryrun_cascade_results | q_v7_defisc + q_v8_calibre | scoring (dryrun) | VIVANTE — c'est la sortie du run (EST le run) |
| dryrun_parcel_evaluations | q_v6/q_v7/q_v8_calibre | scoring (dryrun) | VIVANTE — sortie du run, lue run-scopée (`d.run_label=:run`) |
| entonnoir_motifs | q_v2 + q_v6_m8 + **q_v8_calibre** | scoring (`dryrun.py`) | VIVANTE — **prémisse « morte q_v2/q_v6 » STALE** : q_v8 présent, monte AVEC le scoring, lue run-scopée (`/stats/entonnoir`) |
| parcel_flags | q_v8_calibre | **geste build-mvt** (M45) | VIVANTE — déjà dans le geste de bascule |
| score_snapshots | q_v8_calibre + pre_pond/pre_m28/pre_m39/pre_regle | snapshots + archives M46 | ARCHIVE/JOURNAL — non concernée (par design ; `lignee_tete`) |
| ia_cache | q_v6_m8 + q_v7_defisc | ai/core.py | **CACHE** (déclarée) — miss → recalcul ; 0 ligne q_v8, ménage possible sans danger |

**Point doctrinal clé** : les 4 tables « VIVANTES » **rident automatiquement un geste**
(3 rident le scoring `dryrun`, `parcel_flags` ride `build-mvt`). `parcel_renouvellement` est
**la seule** montée par une **commande isolée** (`labuse renouv`) branchée sur **rien** → la
seule qui peut remourir en silence. C'est précisément le trou que M47 doit boucher.

## P0.5 — Où le segment est-il servi ? (aucune surface ne sert du q_v7 périmé)

| Surface | Code | Scope run |
|---|---|---|
| Filtre `/parcels?renouvellement=true` | app.py:960 | **run-scopé** (`rn.run_label = :runf`, runf = servi) ✅ |
| Bloc fiche `_renouvellement_block` | app.py:2197 | **non** scopé (lit la table telle quelle) |
| Carte `/map/renouvellement.geojson` | app.py:2746 | **non** scopé |
| Liste `/renouvellement/liste` | app.py:2770 | **non** scopé |
| Front : chip filtre « Renouvellement » | FiltreLabuse.tsx:297 (tiroir « Ça va muter ? ») | **LIVE** |
| Front : outil MR1, bloc fiche, tiroir « pourquoi », calque + légende carte | registry/Fiche/Legend/layers | **LIVE** |

**Deux prémisses de plus tombent** : (a) le mandat dit « M45 a délibérément exclu le filtre
Renouvellement de l'exposition » → **faux aujourd'hui** : le chip est rendu (posé M45-P2e/M46) ;
(b) aucune surface ne sert du q_v7 périmé — la table est stampée q_v8_calibre, donc **rien de
périmé n'est servi**. Le filtre `/parcels` est déjà run-scopé ; les 3 autres surfaces lisent la
table sans clause de run (**latent** : inoffensif tant qu'un seul run est présent, mais c'est
exactement ce qu'une garde de cohérence doit couvrir).

---

## SYNTHÈSE — ce qui reste réellement à faire (arbitrage Vic)

**Déjà acquis (sans action) :** table sur le run servi, reproductible bit-à-bit ; filtre +
fiche + carte + outil exposés et LIVE ; aucune donnée périmée servie.

**Trous réels, non couverts :**
1. **Câblage au geste de bascule (P1).** `renouvellement.build()` n'est dans **aucun** geste
   (ni scoring `dryrun`, ni `build-mvt`). Prochaine bascule sans exécution manuelle de
   `labuse renouv` → la table re-porte un run mort en silence. → l'ajouter au geste gardé
   `build-mvt` (comme `parcel_flags` en M45).
2. **Garde de cohérence absente.** Aucun code ne compare `run_label` de la table au run servi
   (grep vide dans `bascule_gardes.py`/`dryrun.py`/`tiles.py`). → garde bruyante :
   `run(parcel_renouvellement) ≠ run servi` ⇒ alerte.
3. **3 lectures non run-scopées** (fiche/carte/liste) — latent ; à couvrir par la garde (2) ou
   par un `WHERE run_label = run servi`, au choix.

**Question pour Vic (P0.6) :**
- **(a) Rebuild** : rien à refaire (déjà q_v8, reproductible) — **confirmer** qu'on ne rejoue
  pas, ou rejeu propre + MAJ golden si une ancre porte le badge ?
- **(b) Redéfinition** : la définition tient-elle telle quelle (seuils 100/600, poids
  40/25/20/15) ou on la révise ? → **ma reco : garder telle quelle**, elle est documentée et
  stable.
- **(c) Sœurs** : `entonnoir_motifs` / `dryrun_*` = VIVANTES (rien à faire) ; `ia_cache` =
  cache (ménage optionnel) ; `score_snapshots` = archive (ne pas toucher). → **ma reco :
  aucune action sœur**, sauf ménage `ia_cache` si souhaité.
- **(d) Portée P1** : je réduis M47 à **câblage geste + garde de cohérence + scope run sur les
  3 lectures** (pas de rebuild, pas de changement de classement). OK ?

**STOP.** Aucune Phase 1 avant arbitrage.

## Annexes (digests machine, .csv.gz — convention QA)
- `qa/m47/sister_tables_inventaire.csv.gz` — inventaire des 7 tables run-scopées.
- `qa/m47/rebuild_blanc_funnel_diff.csv.gz` — entonnoir + diffs (servi/q_v8/q_v7).
- Golden / re-mesures / SHA256 M37 : **intacts** (P0 = zéro écriture, rien à re-mesurer).
