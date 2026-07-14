# SYNTHÈSE M10 — Radar permis cliquable + Vélocité administrative

Branche `feat/m10-permis` · seed 974 · additif · **aucun merge** · 14/07/2026.
Source : SITADEL (SDES/Dido, dispositif Sitadel3), autorisations d'urbanisme dép. 974,
2013 → 2026-08, déjà en base (`sitadel_permits`, 50 043 permis).

---

## Lot 0 — Constat de complétude des champs de dates (le préalable qui commande tout)

Le mandat impose de **vérifier la complétude des dates AVANT de promettre la vélocité**.
Verdict : **la date d'autorisation est en base, la date de dépôt n'y était PAS — mais elle
est récupérable à la source.** Détail :

| Champ | En base `sitadel_permits` | À la source SDES/Dido |
|---|---|---|
| Date d'autorisation (`DATE_REELLE_AUTORISATION`) | ✅ colonne `date`, 100 % | ✅ 100 % |
| Date d'achèvement (`DATE_REELLE_DAACT`) | ✅ `raw.daact`, ~41 % | ✅ |
| **Date de dépôt (`DR_DEPOT`, « Date réelle de dépôt de la DAU »)** | ❌ **jamais capturée** | ✅ **type date, 99,9 %** |

Le connecteur d'ingestion (`permits_sdes.py`) n'avait retenu que l'autorisation et la DAACT.
Le module « Vélocité » historique (M05) livrait donc un **proxy** autorisation→achèvement en
notant « dépôt→décision non porté par la source » — ce qui était **inexact** : `DR_DEPOT`
existe bel et bien au flux.

**Décision (dans le périmètre des contraintes « tes nouvelles tables uniquement, lecture seule
sur l'existant ») :** ne PAS muter `sitadel_permits` ; rapatrier la date de dépôt dans une
table **additive** `m10_permit_delais`, joignable par `permit_id`. → pas de STOP : la vélocité
réelle dépôt→autorisation est livrée, la limite est documentée.

---

## Couverture des champs Sitadel après backfill (`m10_permit_delais`)

Table construite par `python -m labuse.ingestion.permit_delais_m10` (idempotent, upsert).

| Métrique | Valeur |
|---|---|
| Permis (permit_id uniques) | **50 290** |
| Avec dépôt **et** autorisation, causalité respectée → `valide` | **42 603 (84,7 %)** |
| Exclus « dépôt > autorisation » (erreur de saisie source) | **7 633 (15,2 %)** |
| Sans date de dépôt | 54 (0,1 %) |

**Précision réelle de `DR_DEPOT` : le MOIS** (85 % des dépôts au 1er du jour du mois). Le délai
n'a donc de sens **qu'en mois**, jamais en jours — ce qui colle au libellé du mandat (« X mois »).

---

## Lot 1 — Radar permis (fiches cliquables)

- **1.1 Fiche permis lisible** — `GET /modules/permis/{permit_id}` : référence, porteur (si
  personne morale ; « anonymisé à la source » sinon), nature (PC/DP/PA/PD + libellé), nombre de
  lots, surface habitable, **dates clés (dépôt / autorisation / achèvement)**, **délai
  d'instruction**, statut, parcelles liées. Tiroir cliquable côté front (radar **et** fiche).
- **1.2 Accès double** — (a) depuis la fiche parcelle : bloc « Permis à proximité » (rayons
  100/200 m, réutilise la logique M-VIA) ; (b) radar dédié filtrable **commune × période ×
  nature** (`GET /modules/permis?commune=&months=&nature=`).
- **1.3 Lien avec la viabilisation M-VIA** — `GET /modules/parcelle-permis?idu=` lit
  **exactement `via_permits_geo`** (la table même que lit le score de viabilisation) : les
  compteurs `c100`/`c200` de la fiche deviennent la **liste cliquable des permis** qui les
  produisent. Cohérence vérifiée : endpoint `c100=4/c200=10` == `parcel_viabilisation` pour la
  parcelle test ; `c100=14/c200=36` sur la parcelle de capture.

## Lot 2 — Vélocité administrative

`GET /modules/velocite?nature=` — **médiane** (jamais moyenne) du délai d'instruction
**dépôt → autorisation**, en mois, **par commune et par nature**, avec N, IQR (p25–p75) et
les trois limites d'honnêteté ci-dessous. Libellé type : *« délai médian d'instruction PC à
Saint-Paul : 9 mois, sur 4 796 dossiers 2013-2026 »*. Export CSV conservé.

### Distribution des délais — Permis de construire (PC), par commune

Cohortes de dépôt **mûres** (dépôt ≤ 2025-05 ; les 12 derniers mois exclus, cf. limite 2).

| Commune | N (mûrs) | Médiane (mois) | IQR (p25–p75) |
|---|--:|--:|--:|
| Saint-Denis | 2 478 | **10** | 6–13 |
| Saint-Leu | 2 034 | **10** | 7–13 |
| Bras-Panon | 579 | **10** | 6–12 |
| Cilaos | 294 | **10** | 6–12 |
| Saint-Paul | 4 796 | 9 | 6–12 |
| Le Tampon | 3 558 | 9 | 6–12 |
| Saint-Louis | 2 545 | 9 | 6–12 |
| Saint-Joseph | 2 273 | 9 | 6–12 |
| Saint-Benoît | 1 889 | 9 | 6–12 |
| Saint-André | 1 862 | 9 | 6–12 |
| Sainte-Marie | 1 780 | 9 | 6–12 |
| La Possession | 1 500 | 9 | 6–12 |
| Le Port | 825 | 9 | 6–13 |
| Les Avirons | 754 | 9 | 6–13 |
| Les Trois-Bassins | 605 | 9 | 5–12 |
| Salazie | 437 | 9 | 7–12 |
| Saint-Pierre | 4 897 | **8** | 6–11 |
| Sainte-Suzanne | 1 178 | 8 | 5–11 |
| Petite-Île | 883 | 8 | 5–11 |
| L'Étang-Salé | 876 | 8 | 5–11 |
| La Plaine-des-Palmistes | 785 | 8 | 5–11 |
| Entre-Deux | 569 | 8 | 5–11 |
| Sainte-Rose | 359 | 8 | 5–11 |
| Saint-Philippe | 320 | 8 | 5–11 |

Île entière (médianes, cohortes mûres) : **PC 9 mois · DP 8 · PD 7 · PA 10.** Lecture : le nord
(Saint-Denis, Saint-Leu) instruit un cran plus lentement que le sud (Saint-Pierre, Saint-Philippe) ;
l'écart inter-communes reste resserré (8–10 mois), stable sur toutes les cohortes 2020–2025.

### Les trois limites documentées (affichées telles quelles au client)

1. **Censure structurelle.** Le fichier Sitadel des autorisations ne contient **que des dossiers
   accordés** (0 ligne « déposé non tranché »). Le **taux de dossiers en cours** n'est donc
   **pas observable ici** ; la médiane est conditionnelle à « a fini par être autorisé »
   (refusés et pendants invisibles).
2. **Survie des cohortes récentes.** Un dépôt récent instruit lentement n'est pas encore visible
   → biais à la baisse. Preuve mesurée : cohorte de dépôt **2026** = médiane **1 mois** (n=260)
   contre 9 mois stable en 2020-2025. → la médiane de tête **exclut les 12 derniers mois de
   dépôts** (borne `maturite_cutoff`), comptés à part (`n_recent_exclu`).
3. **Qualité de la source.** `DR_DEPOT` est au mois (délai en mois) et **15,2 %** des lignes ont
   dépôt > autorisation (erreur de saisie, jusqu'à −157 mois) → `valide=false`, **exclues** de
   toute médiane et **comptées** (`n_exclus_qualite`), jamais silencieusement.

**Disclaimer produit :** indicateur **historique** (2013+), **pas une promesse** de délai futur.

## Lot 3 — Tests

| Contrôle | Résultat |
|---|---|
| **Golden dataset** (`qa/golden_check.py`) | **32/32 PASS** ✅ |
| **Cohérence run servi** (`tests/test_run_serving_coherence.py`) | **3/3 PASS** ✅ |
| **E2E M10** (`qa/e2e_m10.mjs`, 25 assertions) | **25/25 ✅** (radar filtrable, fiche permis cliquable, proximité cohérente M-VIA, vélocité médiane+N+censure, 0 erreur console) |
| Suite pytest (hors deps optionnelles) | 766 passent |

**Honnêteté suite :** 15 échecs pytest subsistent, **tous pré-existants et étrangers à M10**
(vérifié par `git stash` : ils échouent à l'identique sans mes changements). 8 sont des
`ModuleNotFoundError` (deps optionnelles absentes de l'env : `fpdf`…), 7 sont des échecs
pré-existants base/données (cascade, ortho, verdict) sans rapport avec les permis. **Aucune
régression introduite par M10.**

---

## Livrables & fichiers

**Données (additif, ma table uniquement) :** `m10_permit_delais` +
`src/labuse/ingestion/permit_delais_m10.py` (backfill date de dépôt).

**Backend (`src/labuse/api/modules.py`) :** `/modules/velocite` réécrit (dépôt→autorisation,
médiane, nature, N, censure) · `/modules/permis` enrichi (filtre nature + dépôt + délai) ·
`/modules/permis/{permit_id}` (fiche) · `/modules/parcelle-permis` (proximité cliquable).

**Frontend :** `ModulePanel.tsx` (M03 cartes cliquables + filtre nature + `PermitDrawer` ;
M05 médiane+N+censure) · `PermitsProximityBlock.tsx` (bloc fiche, marqueur `data-permis-proximite`) ·
`Fiche.tsx`, `lib/api.ts`. Build TS/vite vert.

**Captures** (`reports/m10-permis/captures/`) : `radar-permis.png`, `fiche-permis-drawer.png`,
`velocite.png`, `proximite-fiche-97414000ES1030.png`, `fiche-97414000ES1030.png`.

## Comment rejouer

```bash
# 1. backfill de la date de dépôt (idempotent)
PYTHONPATH=src python -m labuse.ingestion.permit_delais_m10
# 2. API de ce worktree (port libre, ex. 8012) + front buildé (frontend/dist)
PYTHONPATH=src python -m uvicorn labuse.api.app:app --port 8012
# 3. contrôles
LABUSE_API_BASE=http://127.0.0.1:8012 PYTHONPATH=src python qa/golden_check.py   # 32/32
PYTHONPATH=src python -m pytest tests/test_run_serving_coherence.py -q           # 3/3
BASE=http://127.0.0.1:8012 node qa/e2e_m10.mjs                                    # 25/25
```
