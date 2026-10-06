#!/usr/bin/env bash
# =============================================================================
# LA BUSE — SYNC-RUN : le pont « le Mac CALCULE → le VPS SERT » (post-M7 · J5)
# -----------------------------------------------------------------------------
# Après une GRANDE PASSE locale (gel-cascade, retrain, nouveau run servi) :
#   1. dump ciblé des TABLES DE RUN + dérivés depuis la base LOCALE ;
#   2. transfert (rsync, checksum) ;
#   3. bascule sur le VPS (pg_restore --clean des tables ciblées) ;
#   4. build-mvt sur le VPS (tuiles au nouveau label) ;
#   5. VÉRIFICATION : comptages local vs VPS + GOLDEN DISTANT — le nouveau run
#      n'est « servi » qu'après ces deux verts.
#
# Usage :
#   deploy/scripts/sync-run.sh --dry-run                     # tout SAUF le restore (répétition)
#   deploy/scripts/sync-run.sh                               # bascule réelle (toutes les lignes)
#   deploy/scripts/sync-run.sh --run-label q_v15            # SCORING-6 lot F : dump FILTRÉ par run_label
#   deploy/scripts/sync-run.sh --dry-run --run-label q_v15  # répétition du dump filtré
#
# --run-label LABEL (SCORING-5-RETOUR §5.5) : ne transfère QUE les lignes de ce run pour les tables
#   versionnées (au lieu des ~80 M lignes tous labels de dryrun_cascade_results). Le restore MET À
#   JOUR ces seules lignes (DELETE WHERE label + COPY), les tables NON versionnées restent entières.
#
# Env requis pour l'étape 5 (golden) : LABUSE_QA_TARGET, LABUSE_QA_BASIC, LABUSE_QA_PASSWORD.
# ⚠ Ne JAMAIS lancer pendant le backup VPS de 3h (leçon M7 : verrous croisés).
# ⚠ Après une bascule de LABEL servi : maj du pointeur servi (config/served_run.txt, versionné —
#   l'override LABUSE_SERVED_RUN est RETIRÉ du VPS) + rebuild front (VITE_RUN_LABEL).
#
# SYNC-RUN-FIX (06/10) — DEUX CORRECTIFS :
#   (a) bash 3.2 (macOS) : plus de `declare -A` (bash 4+) ; les tables versionnées portent leur
#       (colonne, valeur) de filtre via les fonctions run_col()/run_lit() — compatible /bin/bash 3.2.
#   (b) le RÉSIDUEL SERVI est maintenant dans le périmètre : `parcel_residuel_runs` (données du run,
#       clé run_seq) + `residuel_runs` (manifeste du run), FILTRÉS sur le SEUL run_seq servi (défaut :
#       `residuel_run_seq` de config/served_manifest.json, surchargeable par --residuel-seq). La VUE
#       `parcel_residuel` n'est JAMAIS dumpée (elle dérive de parcel_residuel_runs). Au restore, le
#       résiduel est chargé SANS toucher le pointeur `is_served` (bascule = geste de Vic :
#       `labuse residuel-serve <seq>`) → aucun conflit avec l'index unique residuel_runs_one_served.
# =============================================================================
set -euo pipefail
HOST="${SYNC_HOST:-labuse-vps}"
DRY=0; RUN_LABEL=""; RESIDUEL_SEQ="${RESIDUEL_SEQ:-}"; CASCADE_LABEL="${CASCADE_LABEL:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --run-label) RUN_LABEL="${2:?--run-label attend un libellé}"; shift ;;
    --residuel-seq) RESIDUEL_SEQ="${2:?--residuel-seq attend un entier}"; shift ;;
    --cascade-label) CASCADE_LABEL="${2:?--cascade-label attend un libellé}"; shift ;;
    *) echo "argument inconnu : $1" >&2; exit 2 ;;
  esac; shift
done
PG=${PG_BIN:-/Users/openclaw/miniforge3/envs/labusedb/bin}
LOCAL_DB="${LABUSE_LOCAL_DB:-postgresql://openclaw@localhost:5432/labuse}"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
STAMP=$(date +%Y%m%d-%H%M%S)
DUMP=/tmp/labuse_runsync_${STAMP}.dump
COPYDIR=/tmp/labuse_runsync_${STAMP}_filtered

# Tables NON versionnées (dérivés recalculés) — toujours transférées entières.
#   dvf_prix_sortie_neuf : prix de sortie du neuf (prefill Financier, cf. PRIX-SORTIE-1). PRIX-SORTIE-1
#   est code-seul (helper prix_sortie_neuf_servi, pas de table neuve) ; la couche VEFA (VEFA-1,
#   neuf_vefa_commune→spatial_layers) est RECONSTRUITE sur le VPS par `labuse vefa-neuf-build`
#   (post-déploiement) — donc rien d'autre à transférer pour le prix de sortie / la VEFA.
TABLES=(parcel_evaluations pc_caducs defisc_fenetres score_e dvf_prix_sortie_neuf surface_d_events)
# Tables de SCORING versionnées → filtrées par run_label/run_id (SCORING-6 : + score_labuse).
SCORE_RUN_TABLES=(parcel_p_score_v2 p_score_v2_runs dryrun_cascade_results
                  dryrun_parcel_evaluations score_labuse score_labuse_runs)
# Tables du RÉSIDUEL versionnées → filtrées par run_seq (entier). `parcel_residuel` est une VUE : jamais listée.
RESIDUEL_TABLES=(parcel_residuel_runs residuel_runs)
# Ensemble versionné du chemin FILTRÉ (scoring + résiduel) — export, comptages, vérif.
RUN_TABLES=("${SCORE_RUN_TABLES[@]}" "${RESIDUEL_TABLES[@]}")

run_col() {  # colonne de filtre d'une table versionnée (bash 3.2 : fonction, pas de tableau associatif)
  case "$1" in
    parcel_p_score_v2|p_score_v2_runs) echo run_id ;;
    dryrun_cascade_results|dryrun_parcel_evaluations|score_labuse|score_labuse_runs) echo run_label ;;
    parcel_residuel_runs|residuel_runs) echo run_seq ;;
    *) echo "" ;;
  esac
}
run_lit() {  # littéral SQL de la valeur de filtre (quotes incluses si texte ; entier nu pour run_seq)
  case "$1" in
    parcel_residuel_runs|residuel_runs) echo "$RESIDUEL_SEQ" ;;
    # La CASCADE servie a son PROPRE label (manifeste.cascade_run), distinct du scoring : q_v16 est
    # servi SUR la cascade q_v13_sources1 (QV16-VERIF-1, décision Vic). Filtrer dryrun_* sur q_v16
    # donnerait 0 ligne → fiche incohérente (étage 0 vide). On filtre donc sur CASCADE_LABEL.
    dryrun_cascade_results|dryrun_parcel_evaluations) echo "'$CASCADE_LABEL'" ;;
    *) echo "'$RUN_LABEL'" ;;
  esac
}

# Valeurs servies lues dans config/served_manifest.json (le run q_v16 servi EN LOCAL y est lié au
# résiduel run_seq=13 et à la cascade q_v13_sources1). Surchargeables par --residuel-seq/--cascade-label.
_manif() { python3 -c "import json;print(json.load(open('$REPO/config/served_manifest.json'))['$1'])" 2>/dev/null; }
if [ -n "$RUN_LABEL" ]; then
  [ -z "$RESIDUEL_SEQ" ] && RESIDUEL_SEQ="$(_manif residuel_run_seq)"
  [ -z "$CASCADE_LABEL" ] && CASCADE_LABEL="$(_manif cascade_run)"
  case "$RESIDUEL_SEQ" in
    ''|*[!0-9]*) echo "✗ residuel_run_seq introuvable/invalide ('$RESIDUEL_SEQ') — préciser --residuel-seq N" >&2; exit 2 ;;
  esac
  [ -n "$CASCADE_LABEL" ] || { echo "✗ cascade_run introuvable — préciser --cascade-label" >&2; exit 2; }
  echo "   servi ciblé : scoring '$RUN_LABEL' · résiduel run_seq=$RESIDUEL_SEQ · cascade '$CASCADE_LABEL'"
fi

if [ -z "$RUN_LABEL" ]; then
  # ── chemin HISTORIQUE : tables entières (scoring versionné + dérivés). Le RÉSIDUEL n'y entre PAS
  #    (parcel_residuel est une VUE dépendante → pg_restore --clean la casserait ; le résiduel ne se
  #    synchronise que par le chemin FILTRÉ --run-label). ──
  ALL=("${SCORE_RUN_TABLES[@]}" "${TABLES[@]}")
  echo "── 1. dump ciblé (${#ALL[@]} tables, TOUS labels) depuis la base locale ──"
  ARGS=(); for t in "${ALL[@]}"; do ARGS+=(-t "$t"); done
  "$PG/pg_dump" -Fc "${ARGS[@]}" -d "$LOCAL_DB" -f "$DUMP"
  ls -lh "$DUMP" | awk '{print "   taille:", $5}'
  echo "── 2. comptages locaux (la référence) ──"
  : > /tmp/sync_counts_local.txt
  for t in "${ALL[@]}"; do
    printf "   %-28s %s\n" "$t" "$("$PG/psql" "$LOCAL_DB" -tAc "SELECT count(*) FROM $t")"
  done | tee /tmp/sync_counts_local.txt
else
  # ── chemin FILTRÉ (lot F) : dérivés entiers + scoring filtré par run_label + résiduel filtré par run_seq ──
  echo "── 1. dump FILTRÉ scoring='$RUN_LABEL' + cascade='$CASCADE_LABEL' + résiduel run_seq=$RESIDUEL_SEQ ──"
  mkdir -p "$COPYDIR"
  ARGS=(); for t in "${TABLES[@]}"; do ARGS+=(-t "$t"); done
  "$PG/pg_dump" -Fc "${ARGS[@]}" -d "$LOCAL_DB" -f "$DUMP"     # dérivés non versionnés = entiers
  : > /tmp/sync_counts_local.txt
  # Les CSV filtrés sont COMPRESSÉS EN FLUX (gzip) : le fichier non compressé n'existe jamais au repos
  # → pic disque local réduit à ~1 Go (la cascade q_v13_sources1 fait 2,6 Go en clair), /tmp du VPS
  # allégé d'autant, transfert plus court. `\copy … TO STDOUT` écrit le CSV sur stdout (le « COPY n »
  # part sur stderr) ; on canalise le seul stdout dans gzip. La décompression se fait sur le VPS.
  for t in "${RUN_TABLES[@]}"; do
    col="$(run_col "$t")"; lit="$(run_lit "$t")"
    "$PG/psql" "$LOCAL_DB" -c \
      "\copy (SELECT * FROM $t WHERE $col = $lit) TO STDOUT CSV" | gzip -1 > "$COPYDIR/$t.csv.gz"
    n=$("$PG/psql" "$LOCAL_DB" -tAc "SELECT count(*) FROM $t WHERE $col = $lit")
    printf "   %-28s %s (filtré)\n" "$t" "$n" | tee -a /tmp/sync_counts_local.txt
  done
  for t in "${TABLES[@]}"; do
    printf "   %-28s %s\n" "$t" "$("$PG/psql" "$LOCAL_DB" -tAc "SELECT count(*) FROM $t")" \
      | tee -a /tmp/sync_counts_local.txt
  done
fi

# Poids du transfert (dump Fc + CSV filtrés) — annoncé AVANT l'envoi.
dump_kb=$(du -k "$DUMP" | awk '{print $1}')
copy_kb=0; [ -n "$RUN_LABEL" ] && copy_kb=$(du -sk "$COPYDIR" | awk '{print $1}')
tot_kb=$(( dump_kb + copy_kb ))
printf "   charge utile : dump=%s Mo + csv=%s Mo = %s Mo\n" \
  "$(( dump_kb/1024 ))" "$(( copy_kb/1024 ))" "$(( tot_kb/1024 ))"

echo "── 3. transfert ──"
t0=$SECONDS
rsync -a --partial "$DUMP" "$HOST":/tmp/labuse_runsync.dump
[ "$(md5 -q "$DUMP")" = "$(ssh -o BatchMode=yes "$HOST" md5sum /tmp/labuse_runsync.dump | cut -d' ' -f1)" ] \
  && echo "   checksum OK" || { echo "✗ checksum transfert"; exit 1; }
[ -n "$RUN_LABEL" ] && rsync -a --partial "$COPYDIR"/ "$HOST":/tmp/labuse_runsync_filtered/
dt=$(( SECONDS - t0 )); [ "$dt" -lt 1 ] && dt=1
printf "   transféré : %s Mo en %s s (~%s Mo/s)\n" "$(( tot_kb/1024 ))" "$dt" "$(( tot_kb/1024/dt ))"

if [ "$DRY" = 1 ]; then
  echo "── DRY-RUN : arrêt avant restore. Dump(s) sur le VPS, rien n'a été touché côté base. ──"
  echo "   Bascule réelle (restore des données) : relancer sans --dry-run."
  echo "   Le POINTEUR servi reste le geste de Vic (ni ce script en dry-run ni le restore ne le changent)."
  exit 0
fi

echo "── 4. restore VPS (pg_restore des dérivés ; DELETE+COPY du scoring ; résiduel chargé SANS toucher is_served) ──"
ssh -o BatchMode=yes "$HOST" 'sudo -u postgres pg_restore --clean --if-exists --no-owner --role=labuse \
  -d labuse -j 2 /tmp/labuse_runsync.dump 2>&1 | tail -2'
if [ -n "$RUN_LABEL" ]; then
  # Décompression des CSV filtrés sur le VPS (42 Go libres) — les chargements ci-dessous lisent le .csv.
  echo "   … décompression des CSV filtrés sur le VPS"
  ssh -o BatchMode=yes "$HOST" 'cd /tmp/labuse_runsync_filtered && for f in *.csv.gz; do gunzip -f "$f"; done'
  # Scoring + cascade versionnés : DELETE de la valeur filtrée (run_lit : q_v16 pour le scoring,
  # cascade_run pour dryrun_*) + COPY. Idempotent (on supprime exactement ce que le CSV recharge).
  for t in "${SCORE_RUN_TABLES[@]}"; do
    col="$(run_col "$t")"; lit="$(run_lit "$t")"
    ssh -o BatchMode=yes "$HOST" "sudo -u postgres psql -v ON_ERROR_STOP=1 -d labuse -c \
      \"DELETE FROM $t WHERE $col = $lit\" -c \
      \"\\copy $t FROM '/tmp/labuse_runsync_filtered/$t.csv' CSV\""
  done
  # Résiduel — données du run : DELETE du SEUL run_seq + recharge, en une transaction (pas de fenêtre vide).
  ssh -o BatchMode=yes "$HOST" "sudo -u postgres psql -v ON_ERROR_STOP=1 -d labuse" <<SQL
BEGIN;
DELETE FROM parcel_residuel_runs WHERE run_seq = $RESIDUEL_SEQ;
\copy parcel_residuel_runs FROM '/tmp/labuse_runsync_filtered/parcel_residuel_runs.csv' CSV
COMMIT;
SQL
  # Résiduel — manifeste du run : UPSERT par run_seq SANS écrire is_served/is_pinned (le pointeur servi
  # reste intact → aucun conflit avec l'index unique residuel_runs_one_served). La bascule proprement
  # dite est `labuse residuel-serve $RESIDUEL_SEQ`, le geste de Vic.
  ssh -o BatchMode=yes "$HOST" "sudo -u postgres psql -v ON_ERROR_STOP=1 -d labuse" <<SQL
BEGIN;
CREATE TEMP TABLE _rr_in (LIKE residuel_runs);
\copy _rr_in FROM '/tmp/labuse_runsync_filtered/residuel_runs.csv' CSV
INSERT INTO residuel_runs AS r
  (run_seq, label, is_served, is_pinned, code_commit, communes,
   computed_at_min, computed_at_max, duree_s, note, created_at)
  SELECT run_seq, label, false, false, code_commit, communes,
         computed_at_min, computed_at_max, duree_s, note, created_at FROM _rr_in
ON CONFLICT (run_seq) DO UPDATE SET
  label = excluded.label, code_commit = excluded.code_commit, communes = excluded.communes,
  computed_at_min = excluded.computed_at_min, computed_at_max = excluded.computed_at_max,
  duree_s = excluded.duree_s, note = excluded.note;
COMMIT;
SQL
fi
ssh -o BatchMode=yes "$HOST" 'sudo -u postgres psql -d labuse -c ANALYZE'

echo "── 5a. comptages VPS vs local (le moindre écart = arrêt) ──"
ok=1
while read -r line; do
  t=$(echo "$line" | awk '{print $1}'); n=$(echo "$line" | awk '{print $2}')
  col="$(run_col "$t")"
  if [ -n "$RUN_LABEL" ] && [ -n "$col" ]; then
    nv=$(ssh -o BatchMode=yes "$HOST" "sudo -u postgres psql -d labuse -tAc \"SELECT count(*) FROM $t WHERE $col = $(run_lit "$t")\"")
  else
    nv=$(ssh -o BatchMode=yes "$HOST" "sudo -u postgres psql -d labuse -tAc 'SELECT count(*) FROM $t'")
  fi
  [ "$n" = "$nv" ] && printf "   ✓ %-28s %s\n" "$t" "$n" || { printf "   ✗ %-28s local=%s vps=%s\n" "$t" "$n" "$nv"; ok=0; }
done < /tmp/sync_counts_local.txt
[ "$ok" = 1 ] || { echo "✗ ÉCART DE COMPTAGE — diagnostic requis"; exit 1; }

# NOTE SYNC-RUN-FIX : l'ancien étage « 5b » lançait ICI build-mvt + golden. Avec la séparation
# données/bascule, ces gestes dépendent du POINTEUR servi que SEUL Vic bascule ensuite — les jouer
# maintenant construirait les tuiles/golden sur l'ANCIEN run servi (q_v11_m137). On s'arrête donc
# après vérif des comptages et on rend la main : la bascule + le post-déploiement sont le geste de Vic.
echo "✓ SYNC-RUN terminé — DONNÉES posées sur le VPS, comptages VÉRIFIÉS, pointeurs INCHANGÉS."
echo "  Reste à Vic, DANS L'ORDRE (hors fenêtre de backup 3h) :"
echo "   1. bascule scoring   : labuse golden promote $RUN_LABEL"
echo "        (écrit config/served_run.txt, versionné — l'override LABUSE_SERVED_RUN est RETIRÉ du VPS)"
echo "   2. bascule résiduel  : labuse residuel-serve ${RESIDUEL_SEQ:-<seq>}   (is_served → run ${RESIDUEL_SEQ:-<seq>})"
echo "   3. front (VITE)      : VITE_RUN_LABEL=$RUN_LABEL deploy/scripts/deploy_app.sh $HOST"
echo "   4. tuiles parcels    : labuse build-mvt   (reconstruit mvt_parcels + purge/réchauffe le cache tuiles)"
echo "   5. intersections     : labuse build-intersections"
echo "   6. VEFA (prix neuf)  : labuse vefa-neuf-build"
echo "   7. golden distant    : python3 qa/golden_check.py --base-url \$LABUSE_QA_TARGET"
echo "   8. restart labuse."
