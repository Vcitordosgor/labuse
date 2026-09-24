#!/bin/zsh
# RESIDUEL-VITESSE — worker de shard : calcule le résiduel des communes d'une liste
# dans un run EXISTANT (--into-run), pour paralléliser le recalcul île.
#
# Usage (2 shards de communes disjointes dans UN seul run_seq) :
#   psql "$LABUSE_DATABASE_URL" -tAc "SELECT DISTINCT commune FROM parcels ORDER BY commune" > /tmp/communes.txt
#   awk 'NR%2==1' /tmp/communes.txt > /tmp/shardA.txt ; awk 'NR%2==0' /tmp/communes.txt > /tmp/shardB.txt
#   RS=<run_seq créé via --new-run>       # jamais le run servi (garde-fou assert_writable)
#   caffeinate -i scripts/residuel_shard.sh $RS /tmp/shardA.txt &
#   caffeinate -i scripts/residuel_shard.sh $RS /tmp/shardB.txt &
#
# Communes disjointes => aucun conflit de clé (run_seq, parcel_id). Mesuré ~50 p/s à 2 shards
# sur machine chargée (mono = 33). Ne PAS sur-sharder si la machine swappe (memory-bound).
set -eu
: "${LABUSE_DATABASE_URL:?exporter LABUSE_DATABASE_URL}"
ROOT="${RESIDUEL_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
PY="${RESIDUEL_PY:-$ROOT/.venv/bin/python}"
RS="$1"; LIST="$2"
while IFS= read -r C; do
  [ -z "$C" ] && continue
  PYTHONPATH="$ROOT/src" "$PY" -m labuse.cli compute-residuel \
    --commune "$C" --into-run "$RS" --assiette-clippee
done < "$LIST"
echo "shard $LIST terminé (run $RS)"
