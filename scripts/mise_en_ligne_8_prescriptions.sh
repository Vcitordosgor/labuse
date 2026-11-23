#!/usr/bin/env bash
# MISE-EN-LIGNE-8 — envoi PROD des prescriptions corrigées (4 communes), geste MINIMAL.
#
# Décision Vic : on envoie en prod les prescriptions des 4 communes que le contrôle indépendant
# (le ZIP officiel fait foi) a trouvées DIFFÉRENTES — les MÊMES qu'au Mac :
#   Bras-Panon (97402), Saint-Joseph (97412), Saint-Louis (97414), Sainte-Rose (97419).
#
# Méthode : on EXPÉDIE les lignes DÉJÀ CORRIGÉES du Mac (prouvées « identique » au ZIP), au lieu de
# relancer l'ingesteur sur la prod — la prod tourne un code DÉPLOYÉ ANTÉRIEUR (sans le correctif LOT 1
# « partition pas bbox ») : y relancer l'ingestion ré-introduirait la contamination. L'expédition de
# données est déterministe et indépendante de la version de code prod.
#   · geom expédiée en EWKB hex (SRID 4326) ; geom_2975 recalculée par le trigger trg_layers_geom_2975.
#   · data_source_id = 3 (« Urbanisme PLU/GPU (API Carto) », identique Mac/prod — vérifié).
#   · ZONES INTOUCHÉES (on ne purge/insère QUE kind='plu_gpu_prescription').
#   · sauvegarde des lignes AVANT (fichier $BK + archive datée plu_layer_archive) ; UNE transaction ;
#     contrôles d'ENTRÉE (comptes prod attendus) et de SORTIE (comptes = Mac, zones/icpe témoins) ;
#     un écart → ROLLBACK.
#
# Usage :  ./scripts/mise_en_ligne_8_prescriptions.sh preparer   # Mac : exporte les lignes → /tmp/ml8/
#          ./scripts/mise_en_ligne_8_prescriptions.sh a-blanc    # prod : comptes actuels + témoins, 0 écriture
#          ./scripts/mise_en_ligne_8_prescriptions.sh appliquer  # prod : sauvegarde PUIS 1 transaction
#          ./scripts/mise_en_ligne_8_prescriptions.sh affichage  # prod : rebuild geom_simple (après appliquer)
set -euo pipefail
HOST="${LABUSE_PROD_SSH:-labuse-vps}"
D="/tmp/ml8"
SD="/tmp/ml8_srv"
BK="/var/backups/labuse/ml8-presc-$(date +%Y%m%d-%H%M%S)"
COMMUNES="'Bras-Panon','Saint-Joseph','Saint-Louis','Sainte-Rose'"
# comptes ATTENDUS APRÈS = état Mac corrigé (prouvé identique au ZIP) :
ATT_BP=414; ATT_SJ=451; ATT_SL=505; ATT_SR=51; ATT_TOTAL=1421

prod() { ssh -o BatchMode=yes -o ConnectTimeout=30 "$HOST" "sudo -u postgres psql -At -F'|' -d labuse -c \"$1\""; }

preparer() {
  mkdir -p "$D"
  # lignes corrigées du Mac (geom en EWKB hex via COPY ; geom_2975/geom_simple/geom_ile NON exportées)
  psql -d labuse -c "\copy (SELECT kind, subtype, name, geom, attrs, data_source_id, commune FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune IN ($COMMUNES) ORDER BY commune, id) TO '$D/presc.copy'"
  local n; n=$(wc -l < "$D/presc.copy" | tr -d ' ')
  echo "lignes exportées : $n (attendu $ATT_TOTAL)"
  [ "$n" -eq "$ATT_TOTAL" ] || { echo "✗ compte export != $ATT_TOTAL — ARRÊT" >&2; exit 3; }
  ssh "$HOST" "mkdir -p $SD && chmod 777 $SD"
  scp -q "$D/presc.copy" "$HOST:$SD/"
  echo "✓ préparé ($D/presc.copy → $HOST:$SD/)"
}

a_blanc() {
  echo "── A-BLANC (prod, 0 écriture) : comptes prescriptions ACTUELS par commune ──"
  prod "SELECT commune, count(*) FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune IN ($COMMUNES) GROUP BY 1 ORDER BY 1"
  echo "── comptes ZONES par commune (TÉMOIN — doivent rester identiques après) ──"
  prod "SELECT commune, count(*) FROM spatial_layers WHERE kind='plu_gpu_zone' AND commune IN ($COMMUNES) GROUP BY 1 ORDER BY 1"
  echo "── empreinte parcelle→zone des 4 communes (doit rester IDENTIQUE après ; zones intouchées) ──"
  prod "SELECT left(idu,5), count(*), md5(string_agg(idu||'→'||coalesce(zone_lib,''),'|' ORDER BY idu)) FROM parcel_zone_plu WHERE left(idu,5) IN ('97402','97412','97414','97419') GROUP BY 1 ORDER BY 1"
  echo "── témoins globaux (icpe / peb) ──"
  prod "SELECT kind, count(*) FROM spatial_layers WHERE kind IN ('icpe','peb') GROUP BY 1 ORDER BY 1"
  echo "── fichier expédié présent sur le serveur ? ──"
  ssh "$HOST" "wc -l $SD/presc.copy 2>/dev/null || echo 'ABSENT — lancer preparer'"
  echo "── readyz ──"
  ssh "$HOST" "curl -s -o /dev/null -w 'readyz=%{http_code}\n' http://127.0.0.1:8000/readyz || true"
  echo "(attendu APRÈS : BP $ATT_BP · SJ $ATT_SJ · SL $ATT_SL · SR $ATT_SR · total $ATT_TOTAL)"
  echo ">>> reporte les comptes ACTUELS ci-dessus dans appliquer() (ENTRÉE) avant d'appliquer."
}

appliquer() {
  # Comptes d'ENTRÉE attendus (= état prod ACTUEL relevé par a-blanc) — passés en arguments :
  #   appliquer <OLD_BP> <OLD_SJ> <OLD_SL> <OLD_SR>
  local OLD_BP="${1:?usage: appliquer <OLD_BP> <OLD_SJ> <OLD_SL> <OLD_SR>}"
  local OLD_SJ="${2:?OLD_SJ manquant}"; local OLD_SL="${3:?OLD_SL manquant}"; local OLD_SR="${4:?OLD_SR manquant}"
  # SQL de transaction généré en LOCAL (fichier autonome → psql -f ; pas de heredoc imbriqué fragile).
  cat > "$D/apply.sql" <<SQL
\\set ON_ERROR_STOP on
BEGIN;
DO \$\$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune='Bras-Panon';  IF n<>$OLD_BP THEN RAISE EXCEPTION 'entree BP attendu $OLD_BP trouve %',n; END IF;
  SELECT count(*) INTO n FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune='Saint-Joseph'; IF n<>$OLD_SJ THEN RAISE EXCEPTION 'entree SJ attendu $OLD_SJ trouve %',n; END IF;
  SELECT count(*) INTO n FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune='Saint-Louis'; IF n<>$OLD_SL THEN RAISE EXCEPTION 'entree SL attendu $OLD_SL trouve %',n; END IF;
  SELECT count(*) INTO n FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune='Sainte-Rose'; IF n<>$OLD_SR THEN RAISE EXCEPTION 'entree SR attendu $OLD_SR trouve %',n; END IF;
END \$\$;
-- 0) ARCHIVE DATÉE des anciennes prescriptions (l'ancienne version reste archivée)
INSERT INTO plu_layer_archive (insee, commune, kind, subtype, name, idurba, geom, attrs, archive_le, motif)
  SELECT CASE commune WHEN 'Bras-Panon' THEN '97402' WHEN 'Saint-Joseph' THEN '97412'
                      WHEN 'Saint-Louis' THEN '97414' WHEN 'Sainte-Rose' THEN '97419' END,
         commune, kind, subtype, name, attrs->>'idurba', geom, attrs, now(),
         'MISE-EN-LIGNE-8 — prescriptions avant correction (envoi Mac corrige)'
  FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune IN ($COMMUNES);
-- 1) purge des prescriptions des 4 communes (ZONES INTOUCHEES)
DELETE FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune IN ($COMMUNES);
-- 2) insertion des lignes CORRIGEES du Mac (geom_2975 posee par trigger trg_layers_geom_2975)
CREATE TEMP TABLE _presc (kind varchar, subtype varchar, name varchar, geom geometry, attrs jsonb, data_source_id int, commune varchar);
\\copy _presc (kind,subtype,name,geom,attrs,data_source_id,commune) FROM '$SD/presc.copy'
INSERT INTO spatial_layers (kind, subtype, name, geom, attrs, data_source_id, commune)
  SELECT kind, subtype, name, geom, attrs, 3, commune FROM _presc;
-- contrôles de SORTIE (meme transaction)
DO \$\$ DECLARE n int; BEGIN
  SELECT count(*) INTO n FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune='Bras-Panon';  IF n<>$ATT_BP THEN RAISE EXCEPTION 'sortie BP attendu $ATT_BP trouve %',n; END IF;
  SELECT count(*) INTO n FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune='Saint-Joseph'; IF n<>$ATT_SJ THEN RAISE EXCEPTION 'sortie SJ attendu $ATT_SJ trouve %',n; END IF;
  SELECT count(*) INTO n FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune='Saint-Louis'; IF n<>$ATT_SL THEN RAISE EXCEPTION 'sortie SL attendu $ATT_SL trouve %',n; END IF;
  SELECT count(*) INTO n FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune='Sainte-Rose'; IF n<>$ATT_SR THEN RAISE EXCEPTION 'sortie SR attendu $ATT_SR trouve %',n; END IF;
  SELECT count(*) INTO n FROM spatial_layers WHERE kind='plu_gpu_prescription' AND geom_2975 IS NULL AND commune IN ($COMMUNES); IF n<>0 THEN RAISE EXCEPTION '% prescriptions sans geom_2975 (trigger ?)',n; END IF;
END \$\$;
COMMIT;
SQL
  echo "── SAUVEGARDE des lignes touchées → $BK (serveur) ──"
  scp -q "$D/apply.sql" "$HOST:$SD/"
  ssh "$HOST" "sudo mkdir -p $BK && sudo chown postgres $BK
    sudo -u postgres psql -d labuse -c \"\\copy (SELECT * FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune IN ($COMMUNES)) TO '$BK/presc_avant.copy'\"
    sudo cp $SD/presc.copy $SD/apply.sql $BK/ && sudo ls -la $BK"
  echo "── TRANSACTION UNIQUE (psql -f ; contrôles entrée/sortie dedans ; un écart → ROLLBACK) ──"
  ssh "$HOST" "sudo -u postgres psql -v ON_ERROR_STOP=1 -d labuse -f $SD/apply.sql"
  echo "✓ appliqué. Rejouer : contrôle prod identique, plu-veille-nuit, empreinte parcelle→zone, readyz, comptes q_v20."
  echo "  Puis l'affichage : ./scripts/mise_en_ligne_8_prescriptions.sh affichage"
}

affichage() {
  # Vic : reconstruire SEULEMENT ce qui sert l'affichage des couches. geom_simple est un CACHE de
  # simplification (l'API fait COALESCE(geom_simple, simplification à la volée)) : on le rebâtit pour
  # les lignes neuves des 4 communes (NULL après insertion). parcel_zone_plu = ZONES, intouché.
  echo "── rebuild geom_simple (prescriptions neuves des 4 communes) ──"
  prod "UPDATE spatial_layers SET geom_simple = ST_SimplifyPreserveTopology(geom, 0.0002) WHERE kind='plu_gpu_prescription' AND commune IN ($COMMUNES) AND geom_simple IS NULL"
  prod "SELECT count(*) FILTER (WHERE geom_simple IS NOT NULL) AS avec_simple, count(*) AS total FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune IN ($COMMUNES)"
  echo "── invalidation du cache de tuiles d'overlay (réplique _invalider_cache_persistant_overlays) ──"
  # Le tuyau sert les prescriptions EN DIRECT depuis geom_2975 ; sa version = run + max(created_at)
  # de spatial_layers + SEL tuyau_rev. L'INSERT a déjà bumpé max(created_at) → version changée. On
  # purge en plus le cache persistant (hors 'parcels') et on bumpe tuyau_rev (caches proxy amont).
  prod "DELETE FROM mvt_tile_cache WHERE layer <> 'parcels'"
  prod "INSERT INTO mvt_meta (key, value, updated_at) VALUES ('tuyau_rev', to_char(now(),'YYYYMMDDHH24MISSMS'), now()) ON CONFLICT (key) DO UPDATE SET value = to_char(now(),'YYYYMMDDHH24MISSMS'), updated_at = now()"
  echo "✓ geom_simple rebâtie + cache de tuiles overlay purgé + tuyau_rev bumpé."
  echo "  NON reconstruit (volontaire, décision Vic) : parcel_zone_plu (zones intouchées), résiduel servi"
  echo "  seq 17 et promotion (q_v20 gelé ; q_v25 recalculera la faisabilité des parcelles concernées)."
}

case "${1:-}" in
  preparer) preparer ;;
  a-blanc) a_blanc ;;
  appliquer) shift; appliquer "$@" ;;
  affichage) affichage ;;
  *) echo "usage : $0 preparer|a-blanc|appliquer|affichage" >&2; exit 2 ;;
esac
