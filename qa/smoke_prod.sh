#!/usr/bin/env bash
# =============================================================================
# LA BUSE — SMOKE DE PROD (M7, post-incident « vieille UI »)
# -----------------------------------------------------------------------------
# LEÇON OUTILLÉE : « une page répond » ≠ « la bonne app répond ». Ce smoke exige
# un MARQUEUR du build M2 dans le bundle JS servi à la racine (« Scorer une
# adresse » n'existe que dans l'UI M2+reliquats) — un 200 ne suffit jamais.
#
# Usage : LABUSE_QA_BASIC=labuse:<mdp> LABUSE_QA_PASSWORD=<mdp pilote> \
#         qa/smoke_prod.sh [https://app.labuse.immo]
# =============================================================================
set -euo pipefail
BASE="${1:-https://app.labuse.immo}"
: "${LABUSE_QA_BASIC:?}" ; : "${LABUSE_QA_PASSWORD:?}"
J=$(mktemp) ; trap 'rm -f "$J"' EXIT
fail=0

# 0. rideau fermé au monde
[ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/healthz")" = "401" ] || { echo "✗ rideau OUVERT ( != 401 sans creds)"; fail=1; }

# 1. flux navigation : / sans session → /login ; /app jamais exposée
r=$(curl -s -u "$LABUSE_QA_BASIC" -o /dev/null -w '%{http_code}:%{redirect_url}' "$BASE/")
case "$r" in 302*login*) echo "✓ / sans session → /login";; *) echo "✗ / sans session : $r"; fail=1;; esac
r=$(curl -s -u "$LABUSE_QA_BASIC" -o /dev/null -w '%{http_code}' "$BASE/app/")
[ "$r" = "301" ] && echo "✓ /app jamais exposée (301)" || { echo "✗ /app : $r"; fail=1; }

# 2. login applicatif → session
curl -s -u "$LABUSE_QA_BASIC" -c "$J" -X POST "$BASE/login" -H "Content-Type: application/json" \
  -d "{\"password\":\"$LABUSE_QA_PASSWORD\"}" -o /dev/null

# 3. LE MARQUEUR : la racine sert le shell M2 et son bundle contient l'UI M2
html=$(curl -s -u "$LABUSE_QA_BASIC" -b "$J" "$BASE/")
js=$(printf '%s' "$html" | grep -oE '/assets/[^"]*\.js' | head -1)
[ -n "$js" ] || { echo "✗ pas de bundle dans le shell racine"; exit 1; }
n=$(curl -s -u "$LABUSE_QA_BASIC" -b "$J" "$BASE$js" | grep -c "Scorer une adresse" || true)
[ "$n" -ge 1 ] && echo "✓ MARQUEUR M2 présent ($js)" || { echo "✗ MARQUEUR M2 ABSENT — mauvais front servi"; fail=1; }

# 4. endpoints représentatifs (avec session)
for e in "/healthz" "/map/tiles/meta" "/parcels?limit=1"; do
  c=$(curl -s -u "$LABUSE_QA_BASIC" -b "$J" -o /dev/null -w '%{http_code}' "$BASE$e")
  [ "$c" = "200" ] && echo "✓ $e" || { echo "✗ $e : $c"; fail=1; }
done

[ "$fail" = 0 ] && echo "SMOKE PROD : VERT" || { echo "SMOKE PROD : ROUGE"; exit 1; }
