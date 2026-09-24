# Harnais VITESSE-AUDIT-1 — rejouable tel quel

Mesure « avant/après » de chaque `VITESSE-FIX-n`. Ne touche **jamais** `src/` de l'app.

## Pièces

- **`sonde_app.py`** — enveloppe ASGI **jetable** autour de `labuse.api.app:app`. Mesure par requête
  HTTP : temps total | SQL | Python | n_requêtes SQL | octets, via un middleware ASGI + les events
  SQLAlchemy `before/after_cursor_execute`. Écrit `MESURES/sonde/sonde_requests.csv` et
  `sonde_sql.csv`. Pose aussi, **sur l'instance d'audit uniquement**, `lock_timeout=5s` +
  `statement_timeout=120s` (le heal DDL du démarrage échoue vite au lieu de bloquer la base partagée ;
  les lectures de service ne rencontrent jamais ce lock_timeout). **À NE PAS committer dans `src/`.**
- **`harness.mjs`** — 1) sweep des endpoints (55 couches tuiles île z9 + rue z14, endpoints fiche &
  outils, filtre, omnibox) en 1 froid + N chaud → `MESURES/sweep_endpoints.csv` ; 2) parcours
  navigateur (Playwright) boot + fiche → `MESURES/parcours_browser.csv` + `MESURES/har/*.har`.
- **`lonlat_to_tile.mjs`** — helper (lon,lat,zoom) → tuile XYZ + ancres La Réunion.

## Lancer l'API sondée (venv activé, worktree racine)

```bash
. ~/Desktop/labuse/.venv/bin/activate
export SONDE_DIR="$PWD/docs/audit-2026-09/VITESSE-AUDIT-1/MESURES/sonde"
export PYTHONPATH="$PWD/src"
# Vérifier le port 8305 LIBRE d'abord (un seul démarrage à la fois).
uvicorn sonde_app:sonde --app-dir docs/audit-2026-09/VITESSE-AUDIT-1/harnais \
  --host 127.0.0.1 --port 8305 --workers 1
```

Front de prod servi par FastAPI sous `http://127.0.0.1:8305/socle/` (faire `npm run build` dans
`frontend/` au préalable ; `config/served_run.txt` doit exister).

## Lancer les mesures

```bash
cd ~/Desktop/labuse-vitesse
export BASE=http://127.0.0.1:8305 SOURCE=q_v11_m137 WARM=2
export CHROME_BIN="$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-mac-arm64/chrome-headless-shell"
node docs/audit-2026-09/VITESSE-AUDIT-1/harnais/harness.mjs
# volet serveur seul (sans navigateur) : SKIP_PW=1
# volet navigateur seul (sweep déjà fait) : SKIP_SWEEP=1
```

Variables : `BASE`, `SOURCE` (run servi), `OUT`, `WARM`, `WITNESS` (défaut `97410000AN0347`),
`PM_SIREN` (défaut `452038805` = CBO Territoria), `CHROME_BIN`, `SKIP_PW`, `SKIP_SWEEP`.

## Corréler serveur ↔ client

Le **temps serveur** (Python | SQL | n_requêtes) de chaque requête est dans
`MESURES/sonde/sonde_requests.csv` (par chemin), la sonde captant TOUTES les requêtes quel que soit le
déclencheur (curl du sweep ou clic Playwright). Le CSV du sweep porte le temps **client** + le poids.

> Note : dans cette passe, `sweep_endpoints.csv` a été tronqué (bug de re-run corrigé depuis : le
> harnais n'écrase plus un CSV existant). Les données de couches ont été reconstruites depuis la sonde
> → `MESURES/couches_resume.csv`. Un simple relancement du sweep régénère `sweep_endpoints.csv`.
