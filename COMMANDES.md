# LA BUSE — Commandes de référence (scoring v2, M5)

> Créé au mandat M5 (les commandes historiques restent documentées dans
> DEMO_SETUP.md / DEPLOY_RUNBOOK.md). Env requis : `LABUSE_DATABASE_URL`,
> `PROJ_DATA` (cf. tests).

## Scoring v2 — production

```bash
labuse score-v2                       # run complet : features as-of + scoring + tiers + snapshot
labuse score-v2 --no-rebuild          # sans re-matérialiser les features (re-run rapide)
labuse score-v2 --run-id mon-run      # run_id explicite (REFUS si existant — versionné par run)
labuse score-v2 --no-snapshot         # sans gel snapshot
```

- Artifact : `reports/m36-foncier/artifacts-m36-scoring2026.joblib`, **sha256 vérifié
  au démarrage contre `FREEZE-scoring2026.json` — refus si mismatch**.
- Politique de recalibration (gravée dans `p_v2/pipeline.py`) : recalage d'INTERCEPT
  seul à chaque run (dernière année labellisée) ; **re-train complet = décision
  humaine annuelle**, jamais automatique.
- Écrit : `parcel_p_score_v2` (versionnée par run), `p_score_v2_runs`, snapshot
  `m5-AAAA-MM-JJ` (tables M1 `score_snapshots`, un label ne s'écrase jamais).
- Tiers : brûlante / chaude / à creuser / réserve foncière / écartée (étage 0).
  Hystérésis N_sortie ≈ 1,4 × N_entrée, bypass événement daté < 6 mois.

## Viabilisation & raccordement (M-VIA)

```bash
labuse viabilisation                  # construit parcel_viabilisation (les 24 communes)
labuse viabilisation --commune "Le Tampon"   # une seule commune
```

- Indicateur 0-100 par FAISCEAU DE PREUVES (permis < 100 m, façade voie urbanisée,
  adjacence bâti, zone PLU). **Aucun tracé réseau** (donnée sensible). Seuils calibrés,
  cf. `reports/m-via/SYNTHESE-M-VIA.md`. Bloc fiche + gestionnaires (`config/gestionnaires_via.yaml`).
- E2E : `IDU_CONF=97408000AM1255 IDU_LOURDE=97422000DY0010 node qa/e2e_m_via.mjs`
  (serveur `labuse api` + front buildé) → captures `reports/m-via/captures/`.

## Monitoring forward (mensuel, manuel)

```bash
labuse monitor-forward                          # dernier snapshot m5-*
labuse monitor-forward --snapshot-label m5-2026-07-12
```

Sortie : `reports/monitoring/AAAA-MM.md` + CSV faux négatifs. Protocole B0 :
le CLASSEMENT se suit en continu, les NIVEAUX ne se jugent qu'à l'édition N+2
(censure DVF 974 : ~40 % de complétude à 18 mois).

## Séquence démo (validation Vic)

```bash
labuse score-v2 --no-rebuild        # si un run du jour existe déjà : inutile
labuse api                          # puis suivre reports/m5-produit/CHECKLIST-DEMO.md
```

Endpoints v2 (lecture précalculée uniquement, P95 < 200 ms) :
`GET /v2/score/{idu}` · `GET /v2/liste?tier=&commune=&include_copro=` ·
`GET /v2/brulantes` · `GET /v2/reserve-fonciere` · `GET /v2/modele`.

## Scripts d'analyse M5

```bash
python scripts/m5-produit/churn_simulation.py   # churn chaude 2024→2025 par scénario d'hystérésis
python scripts/m5-produit/brulantes_delta.py    # brulantes-v2.csv + delta vs 120 v1.3 + sensibilité ±
```
