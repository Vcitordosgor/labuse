#!/usr/bin/env bash
# MISE-EN-LIGNE-5 LOT 2 — purge des runs morts (liste FIGÉE MENAGE-PROD-1 §A), prod.
#
# GARDÉS (jamais touchés, recomptés DANS la transaction — précision Vic 21/11 : un seul compte
# gardé différent d'avant → ROLLBACK et ARRÊT) : q_v20 (servi) · q_v19_sources (cascade servie) ·
# q_v19 (division) · q_v18 + q_v18_sources + seq 15 (retour arrière) · seq 17 (résiduel servi) ·
# snapshots de calibrage q_v8_calibre_*.
# SUPPRIMÉS (morts, re-vérifiés contre le manifeste au moment du geste) :
#   p_model_candidates + p_model_dataset (tables mortes, TRUNCATE)
#   parcel_residuel_runs seq 1,2,13 (+ en-têtes residuel_runs)
#   dryrun_parcel_evaluations q_v11_m137, q_v13_sources1, q_v21, q_v22, q_v24
#   score_labuse q_v16 (+ en-tête score_labuse_runs)
#   parcel_p_score_v2 q_v11_m137, q_v16, q_v21, q_v22 (+ en-têtes p_score_v2_runs)
#   dryrun_cascade_results q_v21, q_v22, q_v24
#
# Usage : ./scripts/mise_en_ligne_5_purge.sh verifier   # 0 écriture : manifeste, servis/épinglés,
#                                                        # liste finale avec comptes et TAILLES
#         ./scripts/mise_en_ligne_5_purge.sh appliquer  # UNE transaction (gardes), puis VACUUM
set -euo pipefail
HOST="labuse-vps"
MORTS_LABELS="'q_v11_m137','q_v13_sources1','q_v16','q_v21','q_v22','q_v24'"

verifier() {
  echo "── manifeste servi + runs épinglés (rien de la liste ne doit y figurer) ──"
  ssh "$HOST" "cat /opt/labuse/app/config/served_manifest.json | head -8
    sudo -u postgres psql -d labuse -At -F'§' -c \"SELECT run_seq, label, is_served, is_pinned FROM residuel_runs ORDER BY run_seq\""
  echo "── liste finale à supprimer : comptes + tailles ──"
  ssh "$HOST" "sudo -u postgres psql -d labuse -At -F'§' <<'SQLEOF'
SET statement_timeout='300s';
SELECT 'p_model_candidates (morte)', count(*), pg_size_pretty(pg_total_relation_size('p_model_candidates')) FROM p_model_candidates;
SELECT 'p_model_dataset (morte)', count(*), pg_size_pretty(pg_total_relation_size('p_model_dataset')) FROM p_model_dataset;
SELECT 'parcel_residuel_runs seq 1,2,13', count(*), pg_size_pretty(pg_total_relation_size('parcel_residuel_runs')) FROM parcel_residuel_runs WHERE run_seq IN (1,2,13);
SELECT 'dryrun_parcel_evaluations morts', count(*), pg_size_pretty(pg_total_relation_size('dryrun_parcel_evaluations')) FROM dryrun_parcel_evaluations WHERE run_label IN ('q_v11_m137','q_v13_sources1','q_v21','q_v22','q_v24');
SELECT 'score_labuse q_v16', count(*), pg_size_pretty(pg_total_relation_size('score_labuse')) FROM score_labuse WHERE run_label='q_v16';
SELECT 'parcel_p_score_v2 morts', count(*), pg_size_pretty(pg_total_relation_size('parcel_p_score_v2')) FROM parcel_p_score_v2 WHERE run_id IN ('q_v11_m137','q_v16','q_v21','q_v22');
SELECT 'dryrun_cascade_results morts', count(*), pg_size_pretty(pg_total_relation_size('dryrun_cascade_results')) FROM dryrun_cascade_results WHERE run_label IN ('q_v21','q_v22','q_v24');
SQLEOF" | grep -v '^SET$'
  echo "── comptes AVANT des gardés (référence pour la transaction) ──"
  ssh "$HOST" "sudo -u postgres psql -d labuse -At -F'§' <<'SQLEOF'
SET statement_timeout='300s';
SELECT 'score_labuse q_v20', count(*) FROM score_labuse WHERE run_label='q_v20';
SELECT 'score_labuse q_v18', count(*) FROM score_labuse WHERE run_label='q_v18';
SELECT 'p_score_v2 q_v20', count(*) FROM parcel_p_score_v2 WHERE run_id='q_v20';
SELECT 'p_score_v2 q_v18', count(*) FROM parcel_p_score_v2 WHERE run_id='q_v18';
SELECT 'p_score_v2 calibrage q_v8_*', count(*) FROM parcel_p_score_v2 WHERE run_id LIKE 'q_v8_calibre%';
SELECT 'cascade q_v19_sources', count(*) FROM dryrun_cascade_results WHERE run_label='q_v19_sources';
SELECT 'cascade q_v18_sources', count(*) FROM dryrun_cascade_results WHERE run_label='q_v18_sources';
SELECT 'evaluations q_v19', count(*) FROM dryrun_parcel_evaluations WHERE run_label='q_v19';
SELECT 'residuel seq 17', count(*) FROM parcel_residuel_runs WHERE run_seq=17;
SELECT 'residuel seq 15', count(*) FROM parcel_residuel_runs WHERE run_seq=15;
SQLEOF" | grep -v '^SET$'
  echo "── place disque avant ──"; ssh "$HOST" "df -h / | tail -1"
}

appliquer() {
  echo "── TRANSACTION UNIQUE — gardes d'entrée (manifeste/épinglés) + RECOMPTE des gardés avant COMMIT ──"
  ssh "$HOST" "sudo -u postgres psql -v ON_ERROR_STOP=1 -d labuse <<'SQLEOF'
SET statement_timeout = 0;
BEGIN;
-- garde d'entrée : rien de la liste n'est servi ni épinglé
DO \$\$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM residuel_runs WHERE run_seq IN (1,2,13) AND (is_served OR is_pinned);
  IF n <> 0 THEN RAISE EXCEPTION 'seq de la liste servi/épinglé (%)', n; END IF;
END \$\$;
-- photo AVANT des gardés (précision Vic : recomptés avant COMMIT, un écart → ROLLBACK)
CREATE TEMP TABLE _gardes_avant AS
  SELECT 'score_labuse q_v20' k, count(*) n FROM score_labuse WHERE run_label='q_v20'
  UNION ALL SELECT 'score_labuse q_v18', count(*) FROM score_labuse WHERE run_label='q_v18'
  UNION ALL SELECT 'p_score_v2 q_v20', count(*) FROM parcel_p_score_v2 WHERE run_id='q_v20'
  UNION ALL SELECT 'p_score_v2 q_v18', count(*) FROM parcel_p_score_v2 WHERE run_id='q_v18'
  UNION ALL SELECT 'p_score_v2 calibrage', count(*) FROM parcel_p_score_v2 WHERE run_id LIKE 'q_v8_calibre%'
  UNION ALL SELECT 'cascade q_v19_sources', count(*) FROM dryrun_cascade_results WHERE run_label='q_v19_sources'
  UNION ALL SELECT 'cascade q_v18_sources', count(*) FROM dryrun_cascade_results WHERE run_label='q_v18_sources'
  UNION ALL SELECT 'evaluations q_v19', count(*) FROM dryrun_parcel_evaluations WHERE run_label='q_v19'
  UNION ALL SELECT 'residuel seq 17', count(*) FROM parcel_residuel_runs WHERE run_seq=17
  UNION ALL SELECT 'residuel seq 15', count(*) FROM parcel_residuel_runs WHERE run_seq=15;

TRUNCATE p_model_candidates;
TRUNCATE p_model_dataset;
DELETE FROM parcel_residuel_runs WHERE run_seq IN (1,2,13);
DELETE FROM residuel_runs WHERE run_seq IN (1,2,13);
DELETE FROM dryrun_parcel_evaluations WHERE run_label IN ('q_v11_m137','q_v13_sources1','q_v21','q_v22','q_v24');
DELETE FROM score_labuse WHERE run_label='q_v16';
DELETE FROM score_labuse_runs WHERE run_label='q_v16';
DELETE FROM parcel_p_score_v2 WHERE run_id IN ('q_v11_m137','q_v16','q_v21','q_v22');
DELETE FROM p_score_v2_runs WHERE run_id IN ('q_v11_m137','q_v16','q_v21','q_v22');
DELETE FROM dryrun_cascade_results WHERE run_label IN ('q_v21','q_v22','q_v24');

-- RECOMPTE des gardés avant COMMIT : un seul écart → EXCEPTION → ROLLBACK
DO \$\$
DECLARE r record; n bigint;
BEGIN
  FOR r IN SELECT k, n AS avant FROM _gardes_avant LOOP
    EXECUTE CASE r.k
      WHEN 'score_labuse q_v20' THEN 'SELECT count(*) FROM score_labuse WHERE run_label=''q_v20'''
      WHEN 'score_labuse q_v18' THEN 'SELECT count(*) FROM score_labuse WHERE run_label=''q_v18'''
      WHEN 'p_score_v2 q_v20' THEN 'SELECT count(*) FROM parcel_p_score_v2 WHERE run_id=''q_v20'''
      WHEN 'p_score_v2 q_v18' THEN 'SELECT count(*) FROM parcel_p_score_v2 WHERE run_id=''q_v18'''
      WHEN 'p_score_v2 calibrage' THEN 'SELECT count(*) FROM parcel_p_score_v2 WHERE run_id LIKE ''q_v8_calibre%'''
      WHEN 'cascade q_v19_sources' THEN 'SELECT count(*) FROM dryrun_cascade_results WHERE run_label=''q_v19_sources'''
      WHEN 'cascade q_v18_sources' THEN 'SELECT count(*) FROM dryrun_cascade_results WHERE run_label=''q_v18_sources'''
      WHEN 'evaluations q_v19' THEN 'SELECT count(*) FROM dryrun_parcel_evaluations WHERE run_label=''q_v19'''
      WHEN 'residuel seq 17' THEN 'SELECT count(*) FROM parcel_residuel_runs WHERE run_seq=17'
      WHEN 'residuel seq 15' THEN 'SELECT count(*) FROM parcel_residuel_runs WHERE run_seq=15'
    END INTO n;
    IF n IS DISTINCT FROM r.avant THEN
      RAISE EXCEPTION 'GARDÉ MODIFIÉ : % — avant %, après % → ROLLBACK', r.k, r.avant, n;
    END IF;
  END LOOP;
END \$\$;
COMMIT;
SQLEOF"
  echo "── VACUUM (hors transaction) ──"
  ssh "$HOST" "sudo -u postgres psql -d labuse -c \"SET statement_timeout=0\" -c 'VACUUM ANALYZE parcel_residuel_runs, dryrun_parcel_evaluations, score_labuse, parcel_p_score_v2, dryrun_cascade_results, p_model_candidates, p_model_dataset;'"
  echo "── preuves : q_v20 + readyz + place ──"
  ssh "$HOST" "sudo -u postgres psql -d labuse -At -c \"SELECT count(*) FROM score_labuse WHERE run_label='q_v20'\"
    curl -s -m 10 -o /dev/null -w 'readyz: %{http_code}\n' http://127.0.0.1:8000/readyz; df -h / | tail -1"
}

case "${1:-}" in
  verifier) verifier ;;
  appliquer) appliquer ;;
  *) echo "usage : $0 verifier|appliquer" >&2; exit 2 ;;
esac
