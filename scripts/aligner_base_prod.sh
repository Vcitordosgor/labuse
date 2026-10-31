#!/usr/bin/env bash
# =============================================================================
# COHERENCE-HOOK-1 (point 4) — ALIGNE LA BASE DU MAC SUR LA PROD (lecture seule côté prod).
# -----------------------------------------------------------------------------
# Importe depuis la prod (ssh labuse-vps, `sudo -u postgres psql -d labuse`), SANS JAMAIS y écrire :
#   1. `parcel_cadastre_remplacement`  (absente du Mac — pg_dump d'UNE table, remplacée localement)
#   2. les annonces Bien'ici           (slice ADDITIF par BIEN : tout bien portant ≥1 annonce bienici,
#                                        + ses annonces + ses faits ; IDs DÉCALÉS de +1 000 000 pour ne
#                                        JAMAIS entrer en collision avec les lignes Leboncoin du Mac —
#                                        la session RADAR-4 garde donc ses annonces intactes).
# Vérifie d'abord que le run servi est bien le 17 des DEUX côtés (sinon ABANDON : on n'aligne pas sur
# un run inattendu). Idempotent : si des annonces bienici sont déjà présentes localement, on NE RÉIMPORTE
# PAS (un second décalage collisionnerait). À la fin : compte avant/après + écart résiduel Mac vs prod.
#
# Usage :   scripts/aligner_base_prod.sh            # applique
#           scripts/aligner_base_prod.sh --verif     # vérifie seulement (run + comptes), n'écrit rien
# =============================================================================
set -uo pipefail

HOST="${LABUSE_PROD_SSH:-labuse-vps}"
MACDB="${LABUSE_DB_NAME:-labuse}"
OFFSET=1000000                       # décalage d'ID (≫ max local) : import bienici sans collision
VERIF_ONLY=0; [ "${1:-}" = "--verif" ] && VERIF_ONLY=1

MAC=(psql -X -tA -q -d "$MACDB")          # requêtes scalaires (tuples-only)
MACF=(psql -X -q -d "$MACDB")             # chargement de fichiers / heredoc SQL
prod() { ssh -o BatchMode=yes -o ConnectTimeout=20 "$HOST" "sudo -u postgres psql -At -d labuse -c \"$1\""; }
# \copy depuis la prod (lecture seule) : on exécute une méta-commande psql côté distant.
prod_copy() { ssh -o BatchMode=yes -o ConnectTimeout=60 "$HOST" "sudo -u postgres psql -d labuse -c \"\\copy ($1) TO STDOUT CSV\""; }

echo "== Alignement base Mac ← prod ($HOST) =="

# ── 0. Garde : le run servi doit être le 17 des deux côtés ───────────────────────────────────────
prod_seq="$(prod 'SELECT run_seq FROM residuel_runs WHERE is_served LIMIT 1')"
mac_seq="$("${MAC[@]}" -c 'SELECT run_seq FROM residuel_runs WHERE is_served LIMIT 1')"
echo "  run servi : prod=$prod_seq  mac=$mac_seq  (attendu 17)"
if [ "$prod_seq" != "17" ] || [ "$mac_seq" != "17" ]; then
  echo "  ✗ run servi ≠ 17 d'un côté → ABANDON (on n'aligne pas sur un run inattendu)."; exit 1
fi

# ── Comptes AVANT ────────────────────────────────────────────────────────────────────────────────
echo "  -- avant --"
echo "    cadastre_rempl (mac) : $("${MAC[@]}" -c "SELECT COALESCE((SELECT count(*) FROM parcel_cadastre_remplacement),-1)")"
echo "    annonces bienici (mac): $("${MAC[@]}" -c "SELECT count(*) FROM pige_annonces WHERE portail='bienici'")"

if [ "$VERIF_ONLY" = "1" ]; then
  echo "  -- prod (référence) --"
  echo "    cadastre_rempl (prod) : $(prod 'SELECT count(*) FROM parcel_cadastre_remplacement')"
  echo "    annonces bienici (prod): $(prod "SELECT count(*) FROM pige_annonces WHERE portail='bienici'")"
  echo "  (verif seule — rien écrit)"; exit 0
fi

# ── 1. parcel_cadastre_remplacement : pg_dump d'UNE table, remplacée localement ──────────────────
echo "  -- 1. parcel_cadastre_remplacement --"
tmp_cad="$(mktemp)"; trap 'rm -f "$tmp_cad"' EXIT
ssh -o BatchMode=yes -o ConnectTimeout=60 "$HOST" 'sudo -u postgres pg_dump --no-owner --no-privileges --clean --if-exists -t parcel_cadastre_remplacement labuse' > "$tmp_cad"
if [ ! -s "$tmp_cad" ]; then echo "  ✗ dump cadastre vide"; exit 1; fi
"${MACF[@]}" -v ON_ERROR_STOP=1 -f "$tmp_cad" >/dev/null
echo "    importée : $("${MAC[@]}" -c 'SELECT count(*) FROM parcel_cadastre_remplacement') lignes"

# ── 2. annonces Bien'ici (slice ADDITIF par bien, IDs décalés +'"$OFFSET"') ──────────────────────
echo "  -- 2. annonces Bien'ici (slice par bien, décalage +$OFFSET) --"
deja="$("${MAC[@]}" -c "SELECT count(*) FROM pige_annonces WHERE portail='bienici'")"
if [ "${deja:-0}" -gt 0 ]; then
  echo "    déjà $deja annonces bienici en local → import SAUTÉ (idempotence : un 2ᵉ décalage collisionnerait)."
else
  d_b="$(mktemp)"; d_a="$(mktemp)"; d_f="$(mktemp)"; trap 'rm -f "$tmp_cad" "$d_b" "$d_a" "$d_f"' EXIT
  # L'ordre des colonnes de pige_biens DIFFÈRE entre Mac et prod (a_qualifier ↔ rattachement_criteres).
  # On SÉLECTIONNE donc les colonnes de prod DANS L'ORDRE DU MAC (le staging est LIKE pige_biens local)
  # → le \copy positionnel reste aligné quel que soit l'ordre distant.
  macols() { "${MAC[@]}" -c "SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position) FROM information_schema.columns WHERE table_name='$1';"; }
  CB="$(macols pige_biens)"; CA="$(macols pige_annonces)"; CF="$(macols pige_faits)"
  SEL_SUB="SELECT bien_id FROM pige_annonces WHERE portail='bienici'"
  SEL_B="SELECT $CB FROM pige_biens    WHERE bien_id IN ($SEL_SUB)"
  # Annonces : UNIQUEMENT les bienici. (Les ~4 annonces Leboncoin de biens fusionnés inter-portails
  # existent déjà sur le Mac sous leur propre bien → collision uq_pige_annonces_url ; on ne les
  # réimporte pas. Le Mac garde donc sa version LBC ; écart documenté au compte-rendu.)
  SEL_A="SELECT $CA FROM pige_annonces WHERE bien_id IN ($SEL_SUB) AND portail='bienici'"
  SEL_F="SELECT $CF FROM pige_faits    WHERE bien_id IN ($SEL_SUB)"
  prod_copy "$SEL_B" > "$d_b"; prod_copy "$SEL_A" > "$d_a"; prod_copy "$SEL_F" > "$d_f"
  echo "    tiré de la prod : biens=$(wc -l <"$d_b")  annonces=$(wc -l <"$d_a")  faits=$(wc -l <"$d_f")"
  "${MACF[@]}" -v ON_ERROR_STOP=1 <<SQL
BEGIN;
CREATE TEMP TABLE stg_biens    (LIKE pige_biens    INCLUDING DEFAULTS) ON COMMIT DROP;
CREATE TEMP TABLE stg_annonces (LIKE pige_annonces INCLUDING DEFAULTS) ON COMMIT DROP;
CREATE TEMP TABLE stg_faits    (LIKE pige_faits    INCLUDING DEFAULTS) ON COMMIT DROP;
\copy stg_biens    FROM '$d_b' CSV
\copy stg_annonces FROM '$d_a' CSV
\copy stg_faits    FROM '$d_f' CSV
-- décalage d'ID : bien_id / annonce_id (les PK propres des enfants vides ne nous concernent pas ici)
UPDATE stg_biens    SET bien_id    = bien_id    + $OFFSET;
UPDATE stg_annonces SET bien_id    = bien_id    + $OFFSET, annonce_id = annonce_id + $OFFSET;
UPDATE stg_faits    SET bien_id    = bien_id    + $OFFSET;
-- insertion dans l'ordre des FK : biens → annonces → faits
INSERT INTO pige_biens    SELECT * FROM stg_biens;
INSERT INTO pige_annonces SELECT * FROM stg_annonces;
INSERT INTO pige_faits    SELECT * FROM stg_faits;
-- séquences au-dessus du max (sécurité, même si les futurs inserts locaux restent < offset)
SELECT setval('pige_biens_bien_id_seq',       (SELECT max(bien_id)    FROM pige_biens));
SELECT setval('pige_annonces_annonce_id_seq', (SELECT max(annonce_id) FROM pige_annonces));
COMMIT;
SQL
  echo "    importées : $("${MAC[@]}" -c "SELECT count(*) FROM pige_annonces WHERE portail='bienici'") annonces bienici"
fi

# ── 3. Écart résiduel Mac vs prod ────────────────────────────────────────────────────────────────
echo "  -- écart résiduel Mac vs prod --"
for q in \
  "cadastre_rempl|SELECT count(*) FROM parcel_cadastre_remplacement" \
  "annonces_total|SELECT count(*) FROM pige_annonces" \
  "annonces_bienici|SELECT count(*) FROM pige_annonces WHERE portail='bienici'" \
  "annonces_leboncoin|SELECT count(*) FROM pige_annonces WHERE portail='leboncoin'" ; do
  lib="${q%%|*}"; sql="${q#*|}"
  echo "    $lib : mac=$("${MAC[@]}" -c "$sql")  prod=$(prod "$sql")"
done
echo "✓ alignement terminé."
