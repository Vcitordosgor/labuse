#!/bin/zsh
# CHASSE-ORFEVRE-1 — Angle H (le code lui-même) : commandes REJOUABLES.
# LECTURE SEULE : rien n'est installé dans le venv du projet, rien n'est écrit en base.
# Outils tiers (vulture, pip-audit) : venv JETABLE dans /tmp. npm audit : lit package-lock, n'installe rien.
set -u
REPO=~/Desktop/labuse-orfevre
OUT=/tmp/angle_h
mkdir -p "$OUT"

# ───────────────────────── 0. venv jetable (vulture + pip-audit) ─────────────────────────
python3 -m venv /tmp/audit_venv
/tmp/audit_venv/bin/pip -q install pip-audit vulture

# ───────────────────────── 1. Fonctions mortes (backend) ─────────────────────────
# 1a. vulture brut (80 = quasi-certain pour variables/imports ; 60 = tout candidat)
/tmp/audit_venv/bin/vulture "$REPO/src/labuse" --min-confidence 80 > "$OUT/vulture_80.txt"
/tmp/audit_venv/bin/vulture "$REPO/src/labuse" --min-confidence 60 > "$OUT/vulture_60.txt"
# 1b. croisement anti-faux-positifs : /tmp/dead_check2.py (archivé en fin de ce script, section A)
#     - tokenise TOUT le repo (py/ts/tsx/yaml/sql/sh/html/toml/json/md) ;
#     - écarte TOUTE fonction décorée (routes FastAPI, @extracteur de robinet_fiche, @app.command…) ;
#     - écarte les noms dont la variante à tirets existe (dispatch jobs par nom : "pg-maintenance"
#       → getattr(jobs_impl, nom.replace("-","_")), cf. src/labuse/jobs.py:297-301) ;
#     - SURE = le nom n'apparaît NULLE PART ailleurs (même pas en chaîne) ; PROBABLE = refs
#       uniquement dans tests/ ou docs/*.md.
python3 /tmp/dead_check2.py > "$OUT/dead_results.txt"

# 1c. front : exports jamais importés (ts-prune via npx ; node_modules du worktree inutile)
cd "$REPO/frontend" && npx -y ts-prune -p tsconfig.json | grep -v "(used in module)" > "$OUT/tsprune.txt"

# ───────────────────────── 2. Index manquants ─────────────────────────
DSN=$(grep LABUSE_DATABASE_URL "$REPO/.env" | cut -d= -f2- | sed 's/^postgresql+psycopg/postgresql/')
# tables chaudes + stats de scan (base de dev : seq_scan élevé = indice, pas preuve)
psql "$DSN" -X -A -F'|' -c "
SELECT relname, n_live_tup, seq_scan, seq_tup_read, idx_scan, pg_size_pretty(pg_total_relation_size(relid)) sz
FROM pg_stat_user_tables WHERE seq_scan > 5000 AND n_live_tup > 20000
ORDER BY seq_tup_read DESC;" > "$OUT/pg_seqscan.txt"
# index existants des tables visées
psql "$DSN" -X -A -F'|' -c "
SELECT tablename, indexname, indexdef FROM pg_indexes WHERE schemaname='public'
AND tablename IN ('sirene_etablissements','dvf_mutations','parcelle_personne_morale','score_labuse',
                  'dryrun_parcel_evaluations','sitadel_permits','dvf_mutations_parcelle','parcels',
                  'spatial_layers','parcel_ocsge','arcep_immeubles','bodacc_procedures','watched_parcels',
                  'parcel_couche_intersection','event_log','pige_biens')
ORDER BY tablename;" > "$OUT/pg_indexes.txt"
# tables > 10k lignes SANS AUCUN index
psql "$DSN" -X -A -F'|' -c "
SELECT t.relname, n_live_tup FROM pg_stat_user_tables t
LEFT JOIN pg_indexes i ON i.tablename=t.relname AND i.schemaname='public'
WHERE i.indexname IS NULL AND n_live_tup > 10000 GROUP BY 1,2;" > "$OUT/pg_sans_index.txt"
# requêtes du code qui frappent les colonnes repérées
grep -rn --include="*.py" "FROM sirene_etablissements WHERE siren" "$REPO/src/labuse"
grep -rn --include="*.py" "ANCRE_DVF_SQL\|fenetre_dvf_sql" "$REPO/src/labuse"
grep -rn --include="*.py" "parcelle_personne_morale" "$REPO/src/labuse" | grep -i siren

# ───────────────────────── 3. Requêtes N+1 ─────────────────────────
# scan AST : boucles for/while contenant session/db/conn.execute|scalar|query
# (script archivé section B)
python3 /tmp/scan_n1.py "$REPO/src/labuse" > "$OUT/n1_all.txt"
# volumétrie réelle des boucles côté API
psql "$DSN" -X -A -c "SELECT 'watched_parcels', count(*) FROM watched_parcels
UNION ALL SELECT 'projets_actifs', count(*) FROM projets WHERE statut='actif'
UNION ALL SELECT 'comptes', count(*) FROM comptes
UNION ALL SELECT 'pipeline_entries', count(*) FROM pipeline_entries;"

# ───────────────────────── 4. Exceptions avalées ─────────────────────────
# scan AST : handlers dont le corps = pass/continue/return <const> sans raise/log/print
# (script archivé section C)
python3 /tmp/scan_except.py "$REPO/src/labuse" > "$OUT/except_swallow.txt"
# frères du bug G3 : attributs posés sur un proxy SQLAlchemy au lieu de la connexion DBAPI
grep -rn --include="*.py" -E "\.(autocommit|read_only|isolation_level)\s*=" "$REPO/src/labuse" "$REPO/scripts" "$REPO/qa"
grep -rn --include="*.py" "raw_connection()" "$REPO/src/labuse"

# ───────────────────────── 5. Valeurs en dur ─────────────────────────
grep -rn --include="*.py" -E "/Users/|/Volumes/" "$REPO/src/labuse"
grep -rn --include="*.py" "'/tmp\|\"/tmp" "$REPO/src/labuse"
grep -rn --include="*.py" -E "localhost:[0-9]+|127\.0\.0\.1:[0-9]+" "$REPO/src/labuse"
grep -rn --include="*.py" -E "[\"']q_v[0-9][0-9a-z_]*[\"']" "$REPO/src/labuse"
grep -rn --include="*.py" -iE "(api_key|apikey|token|secret|password)\s*[:=]\s*[\"'][A-Za-z0-9_-]{12,}[\"']" "$REPO/src/labuse"
grep -rniE "[a-z0-9._%+-]+@(gmail|labuse|outlook)[a-z.-]*\.[a-z]{2,}" "$REPO/src/labuse" --include="*.py"
grep -rn --include="*.py" -E "\"974[0-9]{2}\"|'974[0-9]{2}'" "$REPO/src/labuse" | grep -v test
grep -n "TRAIN_ANNEES" "$REPO/src/labuse/api/accueil.py"

# ───────────────────────── 6. TODO/FIXME/XXX/HACK ─────────────────────────
grep -rn --include="*.py" -iE "\b(TODO|FIXME|XXX|HACK)\b" "$REPO/src/labuse" | grep -v "\btodo\b.*=" > "$OUT/todos.txt"

# ───────────────────────── 7. Dépendances ─────────────────────────
# 7a. verrou prod (requirements.lock = CŒUR, versions exactes)
/tmp/audit_venv/bin/pip-audit -r "$REPO/requirements.lock" --no-deps --desc off -f json -o "$OUT/pip_audit_lock.json"
# 7b. venv RÉEL du Mac (inclut [ml]/torch) — freeze lecture seule puis requête OSV directe
#     (pip-audit -r sur le freeze échoue : backports.zstd absent de l'index py3.14 + conflit setuptools)
~/Desktop/labuse/.venv/bin/python -m pip freeze | grep -v "^-e\|^#\| @ \|^backports.zstd" > /tmp/venv_freeze2.txt
/tmp/audit_venv/bin/python /tmp/osv_check.py /tmp/venv_freeze2.txt   # script archivé section D
# 7c. front : le package-lock suffit, rien n'est installé
cd "$REPO/frontend" && npm audit --omit=dev --json > "$OUT/npm_audit_prod.json"
cd "$REPO/frontend" && npm audit --json > "$OUT/npm_audit_all.json"
# versions épinglées notables
grep -E "^(fastapi|sqlalchemy|starlette|uvicorn|pydantic|psycopg|stripe|jinja2)==" "$REPO/requirements.lock"
grep -E '"(react|vite|typescript)"' "$REPO/frontend/package.json"

# ══════════════ ANNEXE — scripts d'analyse (recopier dans /tmp avant de rejouer) ══════════════
# A. /tmp/dead_check2.py   : croisement vulture ↔ tokens du repo entier (+ filtre décorateurs,
#                            + variante à tirets pour le dispatch jobs). Lit $OUT/vulture_60.txt.
# B. /tmp/scan_n1.py       : AST — boucles contenant un execute/scalar/query.
# C. /tmp/scan_except.py   : AST — except dont le corps = pass/continue/return constante,
#                            sans raise ni appel log/print.
# D. /tmp/osv_check.py     : POST api.osv.dev/v1/querybatch sur un freeze pip (écosystème PyPI).
# Les quatre scripts sont reproduits in extenso dans ANGLE-H.md (annexe) si /tmp a été purgé.
