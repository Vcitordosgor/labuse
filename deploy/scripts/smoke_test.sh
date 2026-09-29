#!/usr/bin/env bash
# =============================================================================
# LA BUSE — smoke test post-déploiement (lecture seule)
# -----------------------------------------------------------------------------
# Vérifie : app accessible · /healthz · /readyz · connexion DB · PostGIS actif ·
#           une requête parcelle simple · statut démo (si l'endpoint répond).
# N'écrit RIEN. Sort en code != 0 si un test critique échoue (utilisable en CI/cron).
#
# Usage :   deploy/scripts/smoke_test.sh
#           LABUSE_BASE_URL=https://app.labuse.immo deploy/scripts/smoke_test.sh
# =============================================================================
set -uo pipefail   # pas de -e : on veut exécuter TOUS les tests et tout rapporter

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
BASE="${LABUSE_BASE_URL:-http://127.0.0.1:8000}"
DB="${LABUSE_DB_NAME:-labuse}"
DB_USER="${LABUSE_DB_USER:-labuse}"
DB_HOST="${LABUSE_DB_HOST:-localhost}"
DB_PORT="${LABUSE_DB_PORT:-5432}"
PSQL=(psql -X -tA -q -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB")
MANIFEST="${LABUSE_SERVED_MANIFEST:-$REPO/config/served_manifest.json}"

fail=0
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
ko()   { printf '  \033[31m✗\033[0m %s\n' "$1"; fail=1; }

echo "== Smoke test LA BUSE — $BASE / base '$DB' =="

# 1) App accessible + /healthz (process vivant)
code=$(curl -s -o /dev/null -w '%{http_code}' -m 10 "$BASE/healthz" || echo 000)
[ "$code" = "200" ] && ok "app accessible · /healthz $code" || ko "/healthz a renvoyé $code (app down ?)"

# 2) /readyz (schéma + données critiques ; 200 = prêt, 503 = pas prêt)
code=$(curl -s -o /dev/null -w '%{http_code}' -m 15 "$BASE/readyz" || echo 000)
[ "$code" = "200" ] && ok "/readyz $code (schéma + données OK)" || ko "/readyz a renvoyé $code (DB injoignable ou non prête)"

# 3) Connexion DB
if [ "$("${PSQL[@]}" -c 'SELECT 1;' 2>/dev/null)" = "1" ]; then
    ok "connexion PostgreSQL OK"
else
    ko "connexion PostgreSQL impossible (vérifier .pgpass / LABUSE_DATABASE_URL)"
fi

# 4) PostGIS actif
pg=$("${PSQL[@]}" -c "SELECT postgis_lib_version();" 2>/dev/null || true)
[ -n "$pg" ] && ok "PostGIS actif (lib $pg)" || ko "PostGIS inactif (CREATE EXTENSION postgis ?)"

# 5) Requête parcelle simple
n=$("${PSQL[@]}" -c "SELECT count(*) FROM parcels;" 2>/dev/null || true)
if [[ "$n" =~ ^[0-9]+$ ]] && [ "$n" -gt 0 ]; then
    ok "table parcels interrogeable ($n parcelles)"
else
    ko "requête parcels échouée ou table vide (restauration du dump faite ?)"
fi

# 6) Statut démo (informatif — n'échoue pas le smoke test si l'endpoint diffère)
code=$(curl -s -o /tmp/labuse_smoke_demo.json -w '%{http_code}' -m 20 "$BASE/demo-status" || echo 000)
if [ "$code" = "200" ]; then
    ready=$(grep -o '"ready_for_demo":[^,]*' /tmp/labuse_smoke_demo.json 2>/dev/null | head -1)
    ok "/demo-status $code (${ready:-réponse OK})"
else
    printf '  · /demo-status %s (informatif, non bloquant)\n' "$code"
fi
rm -f /tmp/labuse_smoke_demo.json 2>/dev/null || true

# 7) PRE-DEPLOY-1 (lot C) — LE MANIFESTE COMMITÉ NE MENT PAS : config/served_manifest.json doit
#    refléter le résiduel RÉELLEMENT servi en base (residuel_runs.is_served). C'est le contrôle qui
#    aurait attrapé « manifeste run 8 ↔ is_served run 10 » (7ae2c2b7). BLOQUANT.
if [ ! -f "$MANIFEST" ]; then
    ko "served_manifest.json absent ($MANIFEST) — pointeur servi non traçable"
else
    man_seq=$(grep -o '"residuel_run_seq"[[:space:]]*:[[:space:]]*[0-9]*' "$MANIFEST" | head -1 | grep -o '[0-9]*$')
    db_seq=$("${PSQL[@]}" -c "SELECT run_seq FROM residuel_runs WHERE is_served LIMIT 1;" 2>/dev/null || true)
    if [ -z "$db_seq" ]; then
        printf '  · manifeste vs is_served (residuel_runs indéterminé, non bloquant)\n'
    elif [ "$man_seq" = "$db_seq" ]; then
        ok "manifeste = servi en base (résiduel seq $db_seq)"
    else
        ko "MANIFESTE MENTEUR : residuel_run_seq=$man_seq (commité) ≠ is_served=$db_seq (base) — corriger config/served_manifest.json avant de basculer le trafic"
    fi
fi

# 8) PRE-DEPLOY-1 (lot D) — INTERSECTIONS parcelle × couche (servitudes) : complète / partielle /
#    absente + date. INFORMATIF (les lecteurs repassent au calcul au vol, résultat identique) —
#    jamais bloquant, mais DIT pour qu'une table incomplète ne passe pas inaperçue.
if [ "$("${PSQL[@]}" -c "SELECT to_regclass('parcel_couche_intersection') IS NOT NULL;" 2>/dev/null)" = "t" ]; then
    ni=$("${PSQL[@]}" -c "SELECT count(*) FROM parcel_couche_intersection;" 2>/dev/null || echo 0)
    nc=$("${PSQL[@]}" -c "SELECT count(DISTINCT layer_id) FROM parcel_couche_intersection;" 2>/dev/null || echo 0)
    np=$("${PSQL[@]}" -c "SELECT count(DISTINCT parcel_id) FROM parcel_couche_intersection;" 2>/dev/null || echo 0)
    di=$("${PSQL[@]}" -c "SELECT to_char(max(updated_at),'YYYY-MM-DD') FROM parcel_couche_intersection_meta;" 2>/dev/null || echo '?')
    if [ "${ni:-0}" -gt 0 ]; then
        ok "intersections : $ni lignes · $nc couches · $np parcelles · le ${di:-?}"
    else
        printf '  · intersections : table présente mais VIDE (calcul au vol) — labuse build-intersections\n'
    fi
else
    printf '  · intersections : table absente (calcul au vol, correct mais lent) — labuse build-intersections\n'
fi

echo "=============================================="
if [ "$fail" -eq 0 ]; then
    echo "✓ Smoke test : tous les tests critiques PASSENT."
else
    echo "✗ Smoke test : au moins un test critique a ÉCHOUÉ (voir ci-dessus)."
fi
exit "$fail"
