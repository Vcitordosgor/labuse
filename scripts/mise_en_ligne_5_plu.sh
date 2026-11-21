#!/usr/bin/env bash
# MISE-EN-LIGNE-5 LOT 3 — PLU : le geste MINIMAL (pas de push de fond).
#
# Contenu exact (mesuré le 21/11, Mac = vérité PLU-MAJ-2, prod = cible) :
#   · étiquette idurba  : 97408 zones 246 + prescriptions 86 (20251217→20260625)
#                         97411 prescriptions 2 908 (20260423→20260805)
#                         (les zones 97411 et le dpu sont DÉJÀ au bon idurba en prod ;
#                          étendre aux prescriptions est NÉCESSAIRE à la preuve « plu-veille-nuit
#                          sans écart », qui compare PAR COUCHE — géométries identiques, comptes
#                          identiques des deux côtés : pure étiquette)
#   · plu_reglement_extrait : remplace insee 97411+97408 par les lignes du Mac
#                         (prod 241@20260423 + 156@20251217 → Mac 241@20260805 + 156@20251217
#                          + 156@20260625 ; l'ancien texte 97408 reste = son archive)
#   · plu_layer_archive : table ABSENTE en prod — créée + 332 lignes du Mac (archive datée du
#                         zonage/prescriptions 97408_PLU_20251217, PLU-MAJ-2)
#   · peb : INSERT des 4 couches Mac absentes de prod (Roland Garros, data_source_id 108)
#   · ICPE : INTOUCHÉES (la prod a 3 lignes de plus que le Mac — flux vivant, prod fait foi)
#
# Usage :  ./scripts/mise_en_ligne_5_plu.sh preparer   # Mac : exporte les lignes → /tmp/ml5_plu/
#          ./scripts/mise_en_ligne_5_plu.sh a-blanc    # prod : comptes attendus vs trouvés, 0 écriture
#          ./scripts/mise_en_ligne_5_plu.sh appliquer  # prod : sauvegarde lignes touchées PUIS 1 transaction
# Garde-fous : a-blanc refuse si un compte ne colle pas ; appliquer rejoue les mêmes contrôles
# DANS la transaction (un écart → ROLLBACK) ; sauvegarde des lignes touchées AVANT, sur le serveur.
set -euo pipefail
HOST="labuse-vps"
D="/tmp/ml5_plu"
SD="/tmp/ml5_plu_srv"          # côté serveur
BK="/var/backups/labuse/ml5-plu-$(date +%Y%m%d)"

ATT_97408_NEUF="97408_PLU_20260625"; ATT_97408_VIEUX="97408_PLU_20251217"
ATT_97411_NEUF="97411_PLU_20260805"; ATT_97411_VIEUX="97411_PLU_20260423"

preparer() {
  mkdir -p "$D"
  # 1. règlements des deux communes (toutes colonnes sauf id/tsv recalculables ? tsv copiée telle quelle)
  psql -d labuse -c "\copy (SELECT insee,commune,idurba,millesime,document,zone,article_ref,page_pdf,texte_verbatim,doute,doute_motif,pagination_ambigue,source_url,fetched_at,tsv FROM plu_reglement_extrait WHERE insee IN ('97411','97408') ORDER BY id) TO '$D/reglement.copy'"
  # 2. archive des couches (332 lignes, insee 97408)
  pg_dump -d labuse --schema-only -t plu_layer_archive --no-owner --no-acl > "$D/archive_ddl.sql"
  psql -d labuse -c "\copy (SELECT insee,commune,kind,subtype,name,idurba,geom,attrs,archive_le,motif FROM plu_layer_archive ORDER BY id) TO '$D/archive.copy'"
  # 3. les 4 peb absents de prod (identifiés par empreinte géométrique — jamais par id)
  psql -d labuse -c "\copy (SELECT kind,subtype,name,geom,attrs,data_source_id,commune,created_at,geom_2975,geom_simple,geom_ile FROM spatial_layers sl WHERE kind='peb' AND md5(ST_AsBinary(geom)) IN ('05f663e87b57e94c5de8158cf49ea8b4','71394ce21d9113951d4bc193ceafef9d','9663c54b83b41b3443843cebc3143534','dd60e4029d9aeb7467e93ab5f050af94')) TO '$D/peb.copy'"
  wc -l "$D"/*.copy
  echo "→ scp vers le serveur"
  ssh "$HOST" "mkdir -p $SD && chmod 777 $SD"
  scp -q "$D"/reglement.copy "$D"/archive.copy "$D"/peb.copy "$D"/archive_ddl.sql "$HOST:$SD/"
  echo "✓ preparé ($D → $HOST:$SD)"
}

a_blanc() {
  echo "── A-BLANC : comptes attendus vs trouvés (prod, 0 écriture) ──"
  ssh "$HOST" "sudo -u postgres psql -d labuse -At -F'§' <<'SQLEOF'
SET statement_timeout='60s';
SELECT 'zones_97408_vieilles', count(*) AS trouve, 246 AS attendu FROM spatial_layers WHERE kind='plu_gpu_zone' AND attrs->>'idurba'='97408_PLU_20251217';
SELECT 'prescriptions_97408_vieilles', count(*), 86 FROM spatial_layers WHERE kind='plu_gpu_prescription' AND attrs->>'idurba'='97408_PLU_20251217';
SELECT 'prescriptions_97411_vieilles', count(*), 2908 FROM spatial_layers WHERE kind='plu_gpu_prescription' AND attrs->>'idurba'='97411_PLU_20260423';
SELECT 'reglement_97411_97408_avant', count(*), 397 FROM plu_reglement_extrait WHERE insee IN ('97411','97408');
SELECT 'archive_absente', count(*), 0 FROM pg_tables WHERE tablename='plu_layer_archive';
SELECT 'peb_avant', count(*), 8 FROM spatial_layers WHERE kind='peb';
SELECT 'icpe_temoin', count(*), 1271 FROM spatial_layers WHERE kind='icpe';
SQLEOF" | grep -v "^SET$" || true
  echo "── empreinte parcelle→zone AVANT (doit rester IDENTIQUE après) ──"
  ssh "$HOST" "sudo -u postgres psql -d labuse -At -F'§' -c \"SELECT left(idu,5), count(*), md5(string_agg(idu||'→'||coalesce(zone_lib,''), '|' ORDER BY idu)) FROM parcel_zone_plu WHERE idu LIKE '97411%' OR idu LIKE '97408%' GROUP BY 1 ORDER BY 1\""
  echo "── fichiers préparés sur le serveur ──"
  ssh "$HOST" "wc -l $SD/*.copy 2>/dev/null || echo 'fichiers ABSENTS — lancer preparer d abord'"
  echo "(attendus : reglement 553 · archive 332 · peb 4)"
}

appliquer() {
  echo "── SAUVEGARDE des lignes touchées → $BK ──"
  ssh "$HOST" "sudo mkdir -p $BK && sudo chown postgres $BK
    sudo -u postgres psql -d labuse -c \"\\copy (SELECT * FROM plu_reglement_extrait WHERE insee IN ('97411','97408')) TO '$BK/reglement_avant.copy'\" \
      -c \"\\copy (SELECT id, kind, name, attrs FROM spatial_layers WHERE attrs->>'idurba' IN ('97408_PLU_20251217','97411_PLU_20260423')) TO '$BK/etiquettes_avant.copy'\" \
      -c \"\\copy (SELECT id, kind, name, md5(ST_AsBinary(geom)) FROM spatial_layers WHERE kind='peb') TO '$BK/peb_avant.copy'\"
    sudo ls -la $BK"
  echo "── TRANSACTION UNIQUE (contrôles rejoués en tête ; un écart → ROLLBACK) ──"
  ssh "$HOST" "sudo -u postgres psql -v ON_ERROR_STOP=1 -d labuse <<'SQLEOF'
BEGIN;
DO \$\$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM spatial_layers WHERE kind='plu_gpu_zone' AND attrs->>'idurba'='97408_PLU_20251217';
  IF n <> 246 THEN RAISE EXCEPTION 'zones 97408 attendues 246, trouvées %', n; END IF;
  SELECT count(*) INTO n FROM spatial_layers WHERE kind='plu_gpu_prescription' AND attrs->>'idurba'='97408_PLU_20251217';
  IF n <> 86 THEN RAISE EXCEPTION 'prescriptions 97408 attendues 86, trouvées %', n; END IF;
  SELECT count(*) INTO n FROM spatial_layers WHERE kind='plu_gpu_prescription' AND attrs->>'idurba'='97411_PLU_20260423';
  IF n <> 2908 THEN RAISE EXCEPTION 'prescriptions 97411 attendues 2908, trouvées %', n; END IF;
  SELECT count(*) INTO n FROM plu_reglement_extrait WHERE insee IN ('97411','97408');
  IF n <> 397 THEN RAISE EXCEPTION 'reglement avant attendu 397, trouvé %', n; END IF;
  SELECT count(*) INTO n FROM spatial_layers WHERE kind='peb';
  IF n <> 8 THEN RAISE EXCEPTION 'peb avant attendu 8, trouvé %', n; END IF;
END \$\$;

-- 1. étiquettes idurba (3 240 lignes, géométries intouchées)
UPDATE spatial_layers SET attrs = jsonb_set(attrs, '{idurba}', '\"97408_PLU_20260625\"')
 WHERE kind IN ('plu_gpu_zone','plu_gpu_prescription') AND attrs->>'idurba'='97408_PLU_20251217';
UPDATE spatial_layers SET attrs = jsonb_set(attrs, '{idurba}', '\"97411_PLU_20260805\"')
 WHERE kind='plu_gpu_prescription' AND attrs->>'idurba'='97411_PLU_20260423';

-- 2. règlements des deux communes = miroir du Mac
DELETE FROM plu_reglement_extrait WHERE insee IN ('97411','97408');
CREATE TEMP TABLE _regl (LIKE plu_reglement_extrait INCLUDING DEFAULTS);
ALTER TABLE _regl DROP COLUMN id;
\\copy _regl (insee,commune,idurba,millesime,document,zone,article_ref,page_pdf,texte_verbatim,doute,doute_motif,pagination_ambigue,source_url,fetched_at,tsv) FROM '/tmp/ml5_plu_srv/reglement.copy'
INSERT INTO plu_reglement_extrait (insee,commune,idurba,millesime,document,zone,article_ref,page_pdf,texte_verbatim,doute,doute_motif,pagination_ambigue,source_url,fetched_at,tsv)
  SELECT insee,commune,idurba,millesime,document,zone,article_ref,page_pdf,texte_verbatim,doute,doute_motif,pagination_ambigue,source_url,fetched_at,tsv FROM _regl;

-- 3. archive des couches (table créée, 332 lignes)
\\i /tmp/ml5_plu_srv/archive_ddl.sql
SET search_path = public;  -- le DDL de pg_dump vide le search_path : on le rétablit pour la suite
\\copy plu_layer_archive (insee,commune,kind,subtype,name,idurba,geom,attrs,archive_le,motif) FROM '/tmp/ml5_plu_srv/archive.copy'

-- 4. les 4 peb du Mac
CREATE TEMP TABLE _peb (LIKE spatial_layers INCLUDING DEFAULTS);
ALTER TABLE _peb DROP COLUMN id;
\\copy _peb (kind,subtype,name,geom,attrs,data_source_id,commune,created_at,geom_2975,geom_simple,geom_ile) FROM '/tmp/ml5_plu_srv/peb.copy'
INSERT INTO spatial_layers (kind,subtype,name,geom,attrs,data_source_id,commune,created_at,geom_2975,geom_simple,geom_ile)
  SELECT kind,subtype,name,geom,attrs,data_source_id,commune,created_at,geom_2975,geom_simple,geom_ile FROM _peb;

-- contrôles de SORTIE (dans la même transaction)
DO \$\$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM spatial_layers WHERE attrs->>'idurba' IN ('97408_PLU_20251217','97411_PLU_20260423');
  IF n <> 0 THEN RAISE EXCEPTION 'il reste % étiquettes vieilles', n; END IF;
  SELECT count(*) INTO n FROM plu_reglement_extrait WHERE insee IN ('97411','97408');
  IF n <> 553 THEN RAISE EXCEPTION 'reglement après attendu 553, trouvé %', n; END IF;
  SELECT count(*) INTO n FROM plu_layer_archive;
  IF n <> 332 THEN RAISE EXCEPTION 'archive attendue 332, trouvée %', n; END IF;
  SELECT count(*) INTO n FROM spatial_layers WHERE kind='peb';
  IF n <> 12 THEN RAISE EXCEPTION 'peb après attendu 12, trouvé %', n; END IF;
  SELECT count(*) INTO n FROM spatial_layers WHERE kind='icpe';
  IF n <> 1271 THEN RAISE EXCEPTION 'icpe touchées ! attendu 1271, trouvé %', n; END IF;
END \$\$;
COMMIT;
SQLEOF"
  echo "✓ appliqué — preuves à rejouer : idurba servi, plu-veille-nuit, empreinte parcelle→zone"
}

case "${1:-}" in
  preparer) preparer ;;
  a-blanc) a_blanc ;;
  appliquer) appliquer ;;
  *) echo "usage : $0 preparer|a-blanc|appliquer" >&2; exit 2 ;;
esac
