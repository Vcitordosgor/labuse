#!/usr/bin/env bash
# VITESSE-CARTE-1 — banc tuiles SERVEUR (rejouable).
# Par (couche, z/x/y) : octets, temps mur froid (1er hit, LRU vide) + chaud (médiane de 3), code
# HTTP, ETag, Cache-Control. Le split serveur SQL/Python est dans mesures/sonde/sonde_requests.csv.
# Lancer API 8710 FRAÎCHEMENT démarrée → 1er hit de chaque overlay = vrai froid de génération.
#   BASE=http://127.0.0.1:8710 bash server_tiles.sh > ../mesures/server_tiles.csv
BASE="${BASE:-http://127.0.0.1:8710}"
Z9="9/334/286"; Z11="11/1339/1145"; Z14="14/10715/9164"   # St-Denis dense
echo "couche,route,z,x,y,froid_ms,chaud_ms,bytes,http,etag,cache_control"

ms() { curl -s -o /dev/null -w '%{time_total}' "$1" | awk '{printf "%.0f", $1*1000}'; }

mesure() {
  local label="$1" url="$2"
  local froid h1 h2 h3 chaud bytes http hdr etag cc zxy z x y
  froid=$(ms "$url")
  h1=$(ms "$url"); h2=$(ms "$url"); h3=$(ms "$url")
  chaud=$(printf '%s\n%s\n%s\n' "$h1" "$h2" "$h3" | sort -n | sed -n 2p)
  bytes=$(curl -s -o /dev/null -w '%{size_download}' "$url")
  http=$(curl -s -o /dev/null -w '%{http_code}' "$url")
  hdr=$(curl -s -D - -o /dev/null "$url")
  etag=$(printf '%s' "$hdr" | awk -F': ' 'tolower($1)=="etag"{gsub(/\r/,"");print $2}' | head -1)
  cc=$(printf '%s' "$hdr" | awk -F': ' 'tolower($1)=="cache-control"{gsub(/[\r,]/,";");print $2}' | head -1)
  zxy=$(printf '%s' "$url" | grep -oE '[0-9]+/[0-9]+/[0-9]+' | tail -1); IFS=/ read -r z x y <<<"$zxy"
  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
    "$label" "$(printf '%s' "$url" | sed "s#$BASE##")" "$z" "$x" "$y" \
    "$froid" "$chaud" "$bytes" "$http" "${etag:-none}" "${cc:-none}"
}

for t in "$Z9" "$Z11" "$Z14"; do mesure "parcels" "$BASE/map/tiles/$t.pbf"; done
for k in ppr alea_mvt alea_inondation plu_gpu_zone sup artificialisation dpu znieff ebc cinquante_pas \
         zonage_parcelle limites_parcelles limites_communes batiment icpe; do
  for t in "$Z9" "$Z11" "$Z14"; do mesure "$k" "$BASE/map/tiles/$k/$t.pbf"; done
done
