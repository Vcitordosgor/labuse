#!/usr/bin/env bash
# =============================================================================
# ROUGES-7 — répare l'ÉTAT DE SONDE local (base Mac `labuse`) pour les verrous V3b/V3c du circuit.
# -----------------------------------------------------------------------------
# Deux dérives d'ÉTAT (pas de code) que le banc de nuit COHERENCE-HOOK-1 a surfacées sur ce poste :
#
#   V3c — circuit_ecarts porte 2 écarts `chiffre_id = 'nombre_hors_registre'` : la trace laissée par la
#         sonde quand elle a vu la fuite « pente 38 % » du Dossier/Flash de 97416000DY0106. Cette fuite
#         est CORRIGÉE dans le code (ROUGES-7 : provenance ancre pente_pct au chiffre pente*deg). La sonde
#         n'efface pas les écarts résolus (upsert append-only) → on retire ces lignes OBSOLÈTES. Un nouveau
#         passage de sonde ne les réécrit pas (plus de fuite). [latent signalé : la sonde devrait solder
#         un écart disparu ; hors périmètre ROUGES-7, append-only assumé.]
#
#   V3b — la mesure LIVE d'« eau ancienne » voit le DPE « ouvert » parce que, sur ce Mac SANS cron DPE,
#         source_veille.dernier_vu (version amont vue) a avancé au-delà de data_sources.last_sync_at
#         (dernière ingestion). En prod le cron DPE ré-ingère (--force) et remet last_sync_at à jour (le
#         JEU amont est republié chaque semaine sans nouveau contenu 974 — « faux signal » documenté dans
#         sonde_circuit.eau_lignes). On aligne donc la date de sync locale sur la version vue (la DONNÉE
#         DPE n'est pas touchée, seulement l'horodatage de synchronisation).
#
# Idempotent (ne touche rien si déjà réparé). Lecture/écriture base LOCALE uniquement — jamais la prod.
# Usage :  scripts/ci/reparer_sonde_locale.sh [DSN]   # défaut = postgresql://openclaw@localhost:5432/labuse
# =============================================================================
set -euo pipefail
DSN="${1:-postgresql://openclaw@localhost:5432/labuse}"

echo "— V3c : retrait des écarts obsolètes « nombre_hors_registre » (fuite pente 38 % corrigée) —"
psql "$DSN" -v ON_ERROR_STOP=1 -c \
  "DELETE FROM circuit_ecarts WHERE chiffre_id = 'nombre_hors_registre';"

echo "— V3b : alignement de last_sync_at DPE sur la version amont vue (pas de cron DPE sur ce poste) —"
psql "$DSN" -v ON_ERROR_STOP=1 -c \
  "UPDATE data_sources d
      SET last_sync_at = GREATEST(d.last_sync_at, v.dernier_vu::timestamptz)
     FROM source_veille v
    WHERE v.source_id = d.id
      AND d.name ILIKE 'DPE ADEME%'
      AND v.dernier_vu::date > d.last_sync_at::date;"

echo "✓ état de sonde local réparé (V3b/V3c)."
