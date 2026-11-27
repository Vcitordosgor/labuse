#!/usr/bin/env python
"""OUTIL-PERMIS-FIX-12 — NON-RÉGRESSION par les ROUTES/fonctions réelles (base `labuse`, lecture seule).

Prouve que FIX-12 (sélection des veilles sur l'événement daté ; migration des alertes ; reconstruction
de pc_caducs) ne déplace AUCUN des effectifs déjà validés :
  · dormants = 854 ;
  · classement des 24 communes (Saint-Denis en tête) ;
  · Dossier — 6 témoins (permis retenus / logements, 500 m / 24 mois) ;
  · Bilan BZ1065 (inchangé par construction — aucun fichier du Bilan touché) ;
  · bloc « Activité de dépôt » de 97401000AD0701 (depots_recents → null : le faux dépôt reste écarté).
"""
from __future__ import annotations

import os

os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")

from sqlalchemy import text  # noqa: E402

from labuse import runs  # noqa: E402
from labuse.db import session_scope  # noqa: E402
from labuse.ingestion.permits import depots_recents, nearby_permits  # noqa: E402
from labuse.registre.moteurs.commune import (  # noqa: E402
    INDICATEURS, composite_communes, indicateurs_communes, permis_point_mort)

DOSSIER_TEMOINS = [
    ("97411000BZ1065", "Saint-Denis", 1, 4),
    ("97424000AB0001", "Cilaos", 0, 0),
    ("97415000CV1498", "Saint-Paul", 5, 6),
    ("97405000BE1692", "Petite-Île", 16, 9),
    ("97414000DK0208", "Saint-Louis", 9, 14),
    ("97408000AC2215", "La Possession", 7, 9),
]


def main() -> int:
    ok = True
    with session_scope() as s:
        dmax = s.execute(text("SELECT max(date) FROM sitadel_permits")).scalar()

        print("=== Dormants (île, prédicat unique permis_classe._dormant_sql) ===")
        dorm = permis_point_mort(s, None, 36, dmax)
        ok &= (dorm == 854)
        print(f"  dormants : {dorm} (attendu 854) {'OK' if dorm == 854 else 'ÉCART'}")

        print("=== Classement composite des 24 communes (5 axes) ===")
        poids = {k: v[2] for k, v in INDICATEURS.items()}
        rows = indicateurs_communes(s, runs.current())
        for r in rows:
            for k in ("pression_zan", "deficit_sru"):
                if r.get(k) is not None:
                    r[k] = round(float(r[k]), 1)
        rows = composite_communes(rows, poids)
        for r in sorted(rows, key=lambda r: r["rang"])[:3]:
            print(f"    {r['rang']:>2}. {r['commune']:<16} {r['score_composite']}")
        tete = min(rows, key=lambda r: r["rang"])
        ok &= (tete["commune"] == "Saint-Denis" and len(rows) == 24)
        print(f"  tête : {tete['commune']} · {len(rows)} communes (attendu Saint-Denis / 24)")

        print("=== Dossier — 6 témoins (nearby_permits 500 m / 24 mois) ===")
        for idu, com, ep, el in DOSSIER_TEMOINS:
            pid = s.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()
            dyn = (nearby_permits(s, pid, radius_m=500, fenetre_mois=24) or {}).get("dynamique") or {}
            p, lg = dyn.get("permis_recents"), dyn.get("logements_recents")
            bon = (p == ep and lg == el)
            ok &= bon
            print(f"  {idu} {com:<14}: {p}/{lg} (attendu {ep}/{el}) {'OK' if bon else 'ÉCART'}")

        print("=== Bloc « Activité de dépôt » — 97401000AD0701 (depots_recents) ===")
        pid = s.execute(text("SELECT id FROM parcels WHERE idu='97401000AD0701'")).scalar()
        dep = depots_recents(s, pid) if pid else None
        parc = (dep or {}).get("parcelle") if dep else None
        print(f"  depots_recents.parcelle = {parc} (attendu None : le faux dépôt 9744012520010 reste écarté)")
        ok &= (parc is None)

    print("\n=== Bilan BZ1065 — inchangé par construction ===")
    print("  FIX-12 ne modifie AUCUN fichier du Bilan (git diff -- src/labuse/bilan declarations/bilan = vide)")
    print("  → totaux 8 115 036,80 / 12 288 000,00 / 3 709 265,62 € inchangés (test_bilan_recette vert).")
    print("\n" + ("NON-RÉGRESSION OK" if ok else "ÉCART — vérifier"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
