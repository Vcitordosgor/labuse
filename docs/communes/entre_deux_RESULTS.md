# Entre-Deux — re_couches_re_cascade + réparation ciblée pente : ✅ **réparation COMPLÈTE**

> `re_couches_re_cascade` d'Entre-Deux (97403) pour réparer une **évaluation périmée** (bâti=0, `fpp=0`).
> **1ᵉʳ run** : réparation majeure réussie (bâti 0→46 493, voirie déplafonnée, PPR/SAR/prescriptions/ravines/OSM
> apparus, géométrie invalide réparée) **mais la couche `pente` a échoué** (couche critique → exit 1,
> ROLLBACK recommandé). **Décision validée : PAS de rollback.** **2ᵉ étape** : diagnostic (échec transitoire
> RGE ALTI), **re-fetch ciblé `pente` seule** (sans purger les autres couches), puis **re-cascade Entre-Deux**.
> **Résultat final : toutes les couches gold présentes, cascade fiable, 0 géométrie invalide, 0 duplication.**
> **Aucun passage gold** (étape séparée).

## Verdict final : 🟢 **GO technique — Entre-Deux réparée et gold-ready** (NON marquée gold ; décision séparée)

## Contexte & backups

| Élément | Valeur |
|---|---|
| `main` (code) | **`e760cb4`** |
| Backup pré-commune (run 1) | `/var/backups/labuse/labuse-pre-entre-deux-20260625-140800.dump` — SHA `84b7d89e…9ea4a` |
| Backup pré-fix pente (run 2) | `/var/backups/labuse/labuse-pre-entre-deux-pente-fix-20260625-143536.dump` — SHA `309c87fc…408bd` (sidecar OK, `sha256sum -c` OK, 190 TOC, 6/6 tables critiques) |
| Commune / INSEE | **Entre-Deux / 97403** |
| Runs | (1) `import_commune_gold_standard.py` re_couches → **exit 1** (pente échouée) · (2) `ingest_pente` ciblé + `evaluate_commune` re-cascade → **exit 0** |

## Diagnostic de l'échec pente (run 1)

- Source : **IGN RGE ALTI** (`data.geopf.fr/altimetrie/…/elevation.json`), échantillonnage grille batché (100 pts, quota 5 req/s).
- Mécanique : `SAVEPOINT` par couche → une exception (timeout/5xx/parse transitoire sur un batch) a annulé **pente seule** ;
  les autres couches ont été **commitées**. Le purge `[D]` ayant supprimé l'ancienne pente **avant** l'échec → pente = 0.
- **Cause = transitoire** : sonde read-only ultérieure **HTTP 200**, élévations valides pour Entre-Deux (4 s/point — lent).
  **Pas** un bug code (16 communes gold OK), **pas** un filtre, **pas** une absence réelle, **pas** une erreur SQL.
- Fix : appel **direct** `ingest_pente(Entre-Deux)` (pas de purge des autres couches) → **4 140 cellules** (grille déterministe).

## Couches : périmé → run 1 → final

| Couche | Avant (périmé) | Run 1 (pente KO) | **Final** |
|---|---:|---:|---:|
| **bâti** | 0 | 46 493 | **46 493** ✅ |
| **voirie** | 5 000 (plafonné) | 8 802 | **8 802** ✅ |
| **pente** | 4 140 | **0** ❌ | **4 140** ✅ (couv. parcellaire 100 %) |
| PPR | 0 | 2 | **2** ✅ |
| SAR | 0 | 18 | **18** ✅ |
| prescriptions | 0 | 1 120 | **1 120** ✅ |
| ravines | 0 | 280 | **280** ✅ |
| OSM faux positifs | 0 | 230 | **230** ✅ |
| plu_gpu_zone | 506 (propre 182) | 506 | **506** (couv. 100 %) |
| géométrie invalide | 1 | 0 | **0** ✅ |
| DVF | 577 | 233 | **233** (re-fetch single-year — à vérifier ultérieurement, non bloquant) |

## Verdicts : périmé → run 1 → final (latest)

| Verdict | Avant (bâti=0) | Run 1 (pente=0) | **Final** |
|---|---:|---:|---:|
| Opportunité | 9 | 1 | **1** |
| À creuser | 5 542 | 1 711 | **1 642** |
| Écartée | 761 | 802 | **940** |
| Faux positif probable | 0 | 3 798 | **3 729** |

→ Le `fpp` **0 → 3 729** (cascade enfin **bâti-aware**) ; l'ajout de la **pente** déplace **+138** parcelles vers
« écartée » (contraintes de pente appliquées — Entre-Deux est en moyenne montagne). Verdicts **désormais fiables**
(bâti **et** pente pris en compte). **opp = 1** : potentiel structurellement faible (réalité foncière, pas un défaut data).

## Contrôles d'intégrité (final)

- ✅ **Toutes les couches gold présentes** ; **0 géométrie invalide** ; **0 duplication de couche** ; geom_2975 100 %.
- ✅ **6 312 / 6 312 évaluées** ; verdicts cohérents (Σ = 6 312).
- ✅ **DB globale 431 663 / 24 communes / gold 16** inchangée. Entre-Deux 6 312 (upsert id-préservant).
- ✅ **23 autres communes strictement conservées** ; fix `pente` + re-cascade **scopés Entre-Deux uniquement**.
- ✅ **Aucun rollback** · aucun passage gold · `config/communes_gold_standard.yaml` non modifié · scoring/seuil 65 inchangés ·
  pas d'Étape B · Étape A non généralisée · `parcel_evaluations` stale non nettoyées · aucun commit · aucun merge.

## Recommandation

- **🟢 GO technique** : Entre-Deux est désormais **réparée et gold-ready** (tous les post-checks critiques passeraient :
  bâti>0, pente>0, zonage 100 %, voirie, géométrie valide, 100 % évaluée, 0 duplication).
- **Passage gold = étape SÉPARÉE, sur validation** (édition `config/communes_gold_standard.yaml` 16→17 + tests + merge).
  À noter : Entre-Deux restera une commune à **faible opportunité** (1 opp, moyenne montagne) — gold « fiable » mais peu de leads.
- **Point mineur à vérifier** (non bloquant) : DVF 577→233 après re-fetch (probable passage à un flux mono-année plus propre).

---

### Provenance
- Mutations autorisées : (1) re_couches_re_cascade (run gold), (2) `ingest_pente` ciblé + `evaluate_commune` — toutes scopées Entre-Deux, backups validés avant chaque écriture.
- Mesures : `SELECT` lecture seule sur `parcels`, `parcel_evaluations` (latest), `spatial_layers`, `dvf_mutations`.
- Aucune autre commune touchée, aucun rollback, aucun passage gold, aucun commit, aucun merge.
