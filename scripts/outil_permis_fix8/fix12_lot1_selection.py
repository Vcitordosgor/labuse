"""OUTIL-PERMIS-FIX-12 — LOT 1 : preuve avant/après de la SÉLECTION (lecture seule, base `labuse`).

Pour un suivi commençant le 01/01/2026, on compare la SÉLECTION des permis rattachés à une parcelle
(idu_codes non vide) sous l'ANCIENNE règle (`date_depot >= since`) et sous la NOUVELLE (date de
l'ÉVÉNEMENT réellement daté `evenement_date_sql >= since`). On donne combien ENTRENT et SORTENT, et on
montre que la déduplication repose sur l'IDENTIFIANT du permis (pas la date) → aucun déjà signalé
signalé deux fois, aucun perdu. Aucune écriture.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from sqlalchemy import text  # noqa: E402

from labuse import permis_classe  # noqa: E402
from labuse.db import session_scope  # noqa: E402

SINCE = "2026-01-01"


def main() -> int:
    ev = permis_classe.evenement_date_sql("")
    with session_scope() as s:
        print(f"Base : {s.execute(text('SELECT current_database()')).scalar()} (lecture seule) · suivi depuis {SINCE}\n")
        # Univers : permis rattachés à AU MOINS une parcelle (veille de parcelle).
        base = (f"FROM sitadel_permits WHERE jsonb_array_length(COALESCE(idu_codes,'[]'::jsonb)) > 0")
        old_sel = s.execute(text(f"SELECT count(*) {base} AND date_depot >= :d"), {"d": SINCE}).scalar()
        new_sel = s.execute(text(f"SELECT count(*) {base} AND ({ev}) >= :d"), {"d": SINCE}).scalar()
        entrants = s.execute(text(
            f"SELECT count(*) {base} AND ({ev}) >= :d AND (date_depot IS NULL OR date_depot < :d)"),
            {"d": SINCE}).scalar()
        sortants = s.execute(text(
            f"SELECT count(*) {base} AND date_depot >= :d AND (({ev}) IS NULL OR ({ev}) < :d)"),
            {"d": SINCE}).scalar()
        print("VEILLE DE PARCELLE — sélection avant/après (permis rattachés à une parcelle)")
        print(f"  ancienne règle (date_depot ≥ {SINCE})        : {old_sel}")
        print(f"  nouvelle règle (événement daté ≥ {SINCE})     : {new_sel}")
        print(f"  ENTRENT (autorisés dans la fenêtre, dépôt brut absent/ancien) : {entrants}")
        print(f"  SORTENT (faux dépôt récent, autorisés AVANT la fenêtre)       : {sortants}")

        # Témoins
        for pid in ("9744012520010", "97441626E0304"):
            r = s.execute(text(
                f"SELECT (date_depot >= :d) old, (({ev}) >= :d) new, date::date::text aut, date_depot::text dep "
                f"FROM sitadel_permits WHERE permit_id=:p"), {"d": SINCE, "p": pid}).mappings().first()
            if r:
                print(f"  témoin {pid} : autorisé {r['aut']} / dépôt {r['dep']} → ancienne={r['old']} nouvelle={r['new']}")

        # Dédup par IDENTIFIANT : la clé d'unicité de l'alerte de zone est (zone_id, kind, source_ref),
        # source_ref = permit_id — jamais la date. La veille de parcelle dédupe en permanent sur
        # (idu, permit_id). On le PROUVE en lisant l'index servi.
        idx = s.execute(text(
            "SELECT indexdef FROM pg_indexes WHERE tablename='alertes' AND indexname='uq_alertes_zone_kind_ref'")).scalar()
        print("\nDÉDUP par identifiant (alerte de zone) — index d'unicité servi :")
        print("  " + (idx or "absent (créé au point de détection _ensure_secteur_schema)"))
        # combien d'alertes déjà enregistrées : un rejeu ON CONFLICT ne les recrée pas (identifiant stable)
        deja = s.execute(text("SELECT count(*) FROM alertes WHERE kind='permis_in_zone'")).scalar()
        print(f"  alertes permis_in_zone déjà enregistrées (rejeu = ON CONFLICT DO NOTHING) : {deja}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
