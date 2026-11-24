#!/usr/bin/env python
"""OUTIL-PERMIS-FIX-9 — les deux canaux de notification n'affichent plus une date de dépôt BRUTE.

Rejoue, sur la base locale `labuse`, l'EXPRESSION DE DÉTAIL exacte des deux canaux :
  - alerte de zone  (`alertes.py`, permis_in_zone) ;
  - veille parcelle (`api/events.py`, parcelle_suivie).
Chacune passe par LA fonction unique `permis_classe.depot_affichable_*` : si le dépôt est écarté
(année ≠ AN_DEPOT…), le détail dit « autorisé le … » (date d'autorisation), jamais la date rejetée.

Témoin 97441626E0304 + les 10 permis à année contradictoire de la relecture + un contrôle valide.

Usage : LABUSE_DATABASE_URL=… PYTHONPATH=src python scripts/outil_permis_fix8/verif_fix9_canaux.py
"""
from __future__ import annotations

import os

os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")

from sqlalchemy import text  # noqa: E402

from labuse import permis_classe  # noqa: E402
from labuse.db import session_scope  # noqa: E402

CONTRADICTOIRES = [
    "97440913A0154", "97440924A0017", "97441120A0159", "9744121230261", "97441419A0344",
    "97441617A0624", "97441624A0416", "97441626E0304", "97442215A0381", "97442222A0372",
]
CONTROLE_VALIDE = "97440226G0018"   # an_depot 2026 = année du dépôt → dépôt affichable

cond = permis_classe.depot_affichable_cond_sql("")      # bare (FROM sitadel_permits sans alias)
aff = permis_classe.depot_affichable_sql("")

# L'EXPRESSION exacte du détail de l'alerte de zone (alertes.py) et de la veille parcelle (events.py).
detail_sql = (
    "coalesce(type,'Permis')||' '||permit_id || "
    "CASE WHEN " + cond + " THEN ' déposé le '||date_depot::date::text "
    "WHEN date IS NOT NULL THEN ' autorisé le '||date::date::text ELSE '' END")

with session_scope() as s:
    print("=== Détail servi par les deux canaux (alerte de zone + veille parcelle) ===\n")
    rows = s.execute(text(
        f"SELECT permit_id, raw->>'an_depot' AS an, date_depot::date::text AS dr, date::date::text AS aut, "
        f"({aff})::text AS depot_affichable, ({detail_sql}) AS detail "
        f"FROM sitadel_permits WHERE permit_id = ANY(:ids) ORDER BY permit_id"),
        {"ids": CONTRADICTOIRES + [CONTROLE_VALIDE]}).mappings().all()
    faux = 0
    for r in rows:
        tag = "CONTRÔLE VALIDE" if r["permit_id"] == CONTROLE_VALIDE else "année contradictoire"
        print(f"  [{tag}] {r['permit_id']}  an_depot={r['an']}  DR_DEPOT={r['dr']}  autorisé={r['aut']}")
        print(f"      depot_affichable={r['depot_affichable']!r}")
        print(f"      détail : {r['detail']}")
        # un détail « contradictoire » afficherait la DR_DEPOT brute sous « déposé le »
        if r["permit_id"] != CONTROLE_VALIDE and r["dr"] and f"déposé le {r['dr']}" in (r["detail"] or ""):
            faux += 1
            print("      ⚠ DATE BRUTE SOUS « déposé le » — FAUX")
    print(f"\n→ témoins à année contradictoire affichant la date brute sous « déposé le » : {faux} (attendu 0)")
    print(f"→ contrôle {CONTROLE_VALIDE} : dépôt affiché = "
          f"{next(r['depot_affichable'] for r in rows if r['permit_id'] == CONTROLE_VALIDE)!r} (attendu 2026-02-15)")
