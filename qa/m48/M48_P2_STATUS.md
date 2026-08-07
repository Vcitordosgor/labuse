# M48 — PHASE 2 · état d'avancement + DÉCOUVERTE hors cadre (STOP)

## Corrections faites / prêtes

| # | Correction | État | Golden |
|---|---|---|---|
| **F1** | IA : `statut_tier` = verdict servi (fin de la contradiction fiche↔IA) | ✅ **COMMITÉ** `[M48-P2-F1]` | neutre (l'IA n'est pas dans le golden) |
| **F4** | Retrait du champ mort `statut`/`status` (payload V2 + tuiles + front) | 🟡 **PRÊT** (stash + `F4_staged.patch`) | **bloqué** : le golden gèle `api.fiche.statut` (33 parcelles) → régénération requise |
| F2/F3 | Garde de péremption des tuiles + rejeu build-mvt (à toi) | ⏳ à faire | — |
| Backlog | 5 affirmations fausses | ⏳ à faire | neutre |
| Renouv. | Mention « 0 retenue » | ⏳ à faire | neutre |

F1 vérifié en live : AT2542 (brûlante) « écartée » → **« Brûlante… prioritaire… rang 14 »** ;
AP1610 (chaude) → « prioritaire… Chaude… rang 3 ». Test de non-régression vert
(`tests/test_fiche_ask_coherence.py`).

## ⚠️ DÉCOUVERTE HORS CADRE — le golden n'est PAS à 117/117 au départ

En posant le gate de vérification, constaté **sur pièces** :

- **Golden au base M48 (F1 seul) = 114/117** — 3 FAIL, tous `api.fiche.n_lignes_cascade`
  (`97405000AB0168`, `97421000AC0156`, `97423000AB1341`, ex. 37→36). **Rien à voir avec M48**
  (F1 est neutre pour le golden).
- **Chronologie** (dates constatées) :
  - tuiles `mvt_parcels` bâties : **2026-08-05 23:29**
  - golden régénéré : **2026-08-06 22:24**
  - **run servi `q_v8_calibre` re-scoré : 2026-08-07 00:17** ← APRÈS les deux
- Le re-score du 7 août a gardé les mêmes agrégats de tiers (118/1038/29978/2964) mais a **dérivé
  quelques parcelles** : 3 en nombre de lignes cascade (→ golden 114/117) et 4 tiers + 7 854 SDP
  (→ **c'est la cause EXACTE de F2/F3, les tuiles périmées**).

**Autrement dit** : le run servi a été re-matérialisé **hors du geste gardé** — ni régénération
golden, ni `build-mvt`. C'est la doctrine « toute table run-scopée entre dans le geste » (M47) et
« toute bascule régénère le golden » (garde M40/bascule_gardes) qui ont été contournées par ce
re-score. Je **n'ai pas** déclenché ce re-score (M47 était en rollback ; M48 est lecture seule
sauf F1/F4).

## Pourquoi je m'arrête ici

1. Le gate du mandat est **Golden 117/117**. Il est à **114/117 avant même M48** — je ne peux pas
   l'atteindre sans **régénérer le golden**, ce qui est un **geste gardé (à toi)**, et qui
   **absorberait les 3 dérives** (à valider comme légitimes, pas à masquer en silence).
2. **F4** exige la même régénération (retrait de `api.fiche.statut`).
3. Le re-score non gardé est une **découverte hors cadre** — je te la remonte avant d'aller plus loin.

## Ce que je propose (à ton arbitrage)

- **Confirmer** que le re-score du 7 août est légitime (nouvelle vérité servie) → alors :
  **régénérer le golden** (`qa/golden_check.py --dump > …/golden-parcelles.json`, ancres
  préservées) **+ rejeu `build-mvt`** (ta commande — voir §F2/F3 ci-dessous), ce qui met F2/F3,
  F4 et le golden au vert d'un coup.
- OU **investiguer d'abord** le re-score (qui/quoi l'a lancé le 7/08 00:17) avant tout geste servi.
- OU je continue les corrections **neutres pour le golden** (F2/F3 garde, backlog, renouvellement)
  maintenant, et on solde F4 + golden après ta décision.

**Commande build-mvt (F2/F3, quand la garde sera posée)** : `labuse build-mvt`
(rejoue `mvt_parcels` + overlays + `parcel_flags` + `parcel_renouvellement` sur le run servi).

**STOP.** J'attends ton arbitrage sur le golden / le re-score avant de committer F4.
