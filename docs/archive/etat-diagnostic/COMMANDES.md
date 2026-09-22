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

## Validation post-merge — les 2 gates (à relancer à CHAQUE merge)

Après un merge dans `main`, le serveur API en mémoire sert encore l'ANCIEN code : il faut
le **redémarrer** sur le worktree `main`, puis passer les deux gates. Tout en LECTURE SEULE
(aucun re-score). Env commun : la base tourne en local, le rôle `labuse` n'existe pas → on
se connecte en `openclaw` ; `PROJ_DATA` évite l'erreur pyproj (cf. mémoire dette-pyproj).

```bash
# Env commun aux 3 commandes
export LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse"
export PROJ_DATA="$HOME/miniforge3/envs/labusedb/share/proj"
```

### 1. Redémarrer l'API sur le code mergé (port servi = 8010)

```bash
cd /Users/openclaw/Desktop/labuse
# tuer PROPREMENT (SIGTERM) le process qui sert le vieux code sur :8010
kill "$(lsof -tiTCP:8010 -sTCP:LISTEN)"
# attendre la libération du port, puis relancer depuis le worktree main
until ! lsof -iTCP:8010 -sTCP:LISTEN -n >/dev/null 2>&1; do sleep 0.5; done
nohup .venv/bin/labuse api --port 8010 > /tmp/labuse_api_8010.log 2>&1 &
# vérifier que le code mergé est bien servi (ex. M9 : le champ `icd` doit exister)
until curl -sf -m 3 http://127.0.0.1:8010/health >/dev/null; do sleep 0.5; done
curl -s "http://127.0.0.1:8010/parcels/97415000BE0027?source=q_v5_m6b" | python3 -c "import sys,json;print('icd:', 'icd' in json.load(sys.stdin))"
```

### 2. Golden dataset — 32 parcelles témoins, base ↔ API (attendu 32/32)

```bash
LABUSE_API_BASE="http://127.0.0.1:8010" python qa/golden_check.py
# 0 = 100 % PASS ; 1 = au moins un FAIL ; 2 = erreur d'exécution
```

### 3. Cohérence du run servi — 3 tests, AUCUN skip toléré (attendu 3/3)

```bash
# LABUSE_DATABASE_URL (openclaw) est INDISPENSABLE : le test #3 interroge la base
# APPLICATIVE (mvt_meta.run_label) ; sans URL valide il SKIPPE (≠ pass). -rs montre tout skip.
python -m pytest tests/test_run_serving_coherence.py -v -rs
# 1) front SOURCE == Q_A_RUN_LABEL   2) bundle dist contient le run   3) tuiles mvt sur le run servi
```

Règle : un gate non vert (golden < 32/32, cohérence < 3/3, ou un skip) = **stop et rapport**,
on ne répare rien à l'aveugle (une divergence = bascule de run incomplète, cf. docstring du test).

## Juger un challenger contre le run servi (arène — Phase 0)

**Une seule commande** produit le verdict (LECTURE SEULE sur les scores ; écrit un rapport dans
`reports/arene/`, ne bascule jamais le run servi) :

```bash
labuse arene --challenger <run_id>     # champion = dernier run servi par défaut
# → reports/arene/<date>_<run_id>.md + AVIS : CHALLENGER RETENU | REJETÉ | (REJETÉ éliminatoire boussole)
```

Options : `--champion <run_id>`, `--eval-year N`, `--churn-max 0.25`, `--n-boot 1000`. Le rapport
porte : contrôle d'univers, **gate golden/boussole (éliminatoire)**, RR@1158 (IC95 seed 974), lift,
ventilations commune/tier, ECE, churn top-1158, contrôle négatif par permutation, puis l'AVIS.
**L'avis est indicatif — la bascule du run servi reste une décision humaine.** Référence de comparaison :
`reports/arene/BASELINE_q_v6_m8.md` (champion contre lui-même).
