# MANIFESTE-SERVI — qui lit `config/served_manifest.json`, et ce qu'il doit dire

ROUGES-RESTANTS item 8 (19/10/2026, `fix/rouges-restants`). Constat corrigé : le scoring servi
`q_v19` a été re-scoré EN ENTIER le 18/10 12:53 sur l'étage 0 `q_v19_sources` (calculé le 18/10
10:12 — `p_score_v2_runs.params.etage0_run = 'q_v19_sources'`, 433 229 évaluations + 21,1 M lignes
de cascade en base), mais le manifeste épinglait encore `cascade_run = q_v18_sources` (bascule du
17/10) : la fiche, les 4 documents, la carte et les moteurs servaient une cascade PLUS VIEILLE que
celle dont le scoring servi est issu.

## Qui le lit

- **`src/labuse/manifeste.py`** — le POINT DE VÉRITÉ unique, relu à la requête (cache 3 s).
  Un seul écriveur : `bascule_flux.basculer()` (page Circuit / `labuse golden promote`), écrit
  ATOMIQUE (tmp + os.replace) puis auto-commit des pointeurs.
- **`runs.current()`** (scoring_run) — tout ce qui lit le score servi (fiche, carte, filtres,
  exports, Q_A_RUN_LABEL). `config/served_run.txt` n'est qu'une VUE DÉRIVÉE.
- **`runs.cascade()`** (cascade_run) — TOUS les lecteurs de cascade/étage 0 :
  `api/served_cascade.py` (fiche + 4 documents), `api/moteurs.py` (simulplu…), carte,
  renouvellement. C'est le champ qui était périmé.
- **`manifeste.division_run()`** — candidats division (`api/app.py:3226`, `sonde_circuit.py:865`).
- **`mvt_run`** — tuiles (affiché aussi au dashboard, `api/dashboard.py:3540`).
- **`residuel_run_seq`** — MIROIR d'affichage seulement : la vérité du résiduel est
  `residuel_runs.is_served` (ALGO-FIX-1), déplacée par `labuse residuel-serve` uniquement.
- **`fraicheur_caches.py`** (PRE-DEPLOY-1 lot C) — « le manifeste ne peut plus mentir » : périmé
  si le pointeur ne reflète pas la base ; `labuse rebuild --dry-run` échoue alors.
- **`circuit_verrous.py` (~896)** — verrou : le manifeste reflète le servi.
- **`exports/builder.py`** — `promoted_at` = la date « Données LABUSE au » des documents.

## Au déploiement / en prod

`deploy.sh` ne lit pas le fichier lui-même : il joue `circuit verrous` + `circuit suite` puis
`labuse rebuild` / `rebuild --dry-run` (fumée), qui eux comparent les caches AU manifeste. La prod
sert **le fichier COMMITÉ** : l'app relit `config/served_manifest.json` du dépôt déployé à la
requête. Un manifeste corrigé mais non commité ne change RIEN en prod (d'où le rappel
« ⚠ manifeste modifié : à commiter » de `golden promote`).

## Ce qu'il doit contenir pour servir q_v19 avec q_v19_sources

```json
scoring_run   = "q_v19"
cascade_run   = "q_v19_sources"   ← corrigé ici (était q_v18_sources du 11/10)
mvt_run       = "q_v19"
division_run  = "q_v19"
residuel_run_seq = 16             (miroir de residuel_runs.is_served — inchangé)
```

Correction appliquée dans ce commit (vérifiée : `resoudre_cascade_run(db, 'q_v19')` →
`q_v19_sources`, cascade complète en base ; les tests served_cascade/simulplu sèment sous
`runs.cascade()` et passent). La bascule normale n'offrait pas ce geste : `basculer()` refuse un
run déjà servi (« q_v19 est déjà le run servi ») — le ré-épinglage de cascade seul est donc un
édit direct du fichier, tracé par `par` et ce document. `precedent` est laissé intact (retour
arrière = l'état q_v18 complet).
