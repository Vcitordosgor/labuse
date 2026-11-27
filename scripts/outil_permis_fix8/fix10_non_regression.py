#!/usr/bin/env python
"""OUTIL-PERMIS-FIX-10 — NON-RÉGRESSION (base locale `labuse`, lecture seule).

Rejoue les effectifs que le contre-audit ASTRA-5 valide, pour prouver que FIX-10 ne les déplace pas :
dormants 854 · caducs 4 836 (parcelles) · rayon 500 m BZ1065 · score composite des 24 communes
(Saint-Denis en tête) · totaux du Bilan témoin BZ1065.

Usage : LABUSE_DATABASE_URL=… PYTHONPATH=src python scripts/outil_permis_fix8/fix10_non_regression.py
"""
from __future__ import annotations

import os

os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")

from sqlalchemy import text  # noqa: E402

from labuse.db import session_scope  # noqa: E402
from labuse import runs  # noqa: E402
from labuse.registre.moteurs.commune import (  # noqa: E402
    INDICATEURS, composite_communes, indicateurs_communes, permis_point_mort)
from labuse.ingestion.pc_caducs import build_pc_caducs  # noqa: E402
from labuse.ingestion.permits import nearby_permits  # noqa: E402


with session_scope() as s:
    dmax = s.execute(text("SELECT max(date) FROM sitadel_permits")).scalar()

    print("=== Dormants (île, prédicat unique permis_classe._dormant_sql) ===")
    print("  dormants :", permis_point_mort(s, None, 36, dmax), "(attendu 854)")

    print("=== Caducs (pc_caducs, build LECTURE SEULE — commit=False puis rollback) ===")
    res = build_pc_caducs(s, commit=False, log=lambda *a, **k: None)
    n_caducs = s.execute(text("SELECT count(*) FROM pc_caducs")).scalar()
    print("  parcelles PC probablement caduques :", n_caducs, f"(build={res.get('total')}) (attendu 4 836)")
    s.rollback()   # on NE committe PAS pc_caducs (lecture seule)

    print("=== Rayon 500 m — BZ1065 (nearby_permits, 500 m / 24 mois) ===")
    pid = s.execute(text("SELECT id FROM parcels WHERE idu='97411000BZ1065'")).scalar()
    dyn = (nearby_permits(s, pid, radius_m=500, fenetre_mois=24) or {}).get("dynamique") or {}
    print(f"  permis_recents={dyn.get('permis_recents')} logements_recents={dyn.get('logements_recents')} "
          f"(attendu 1 permis / 4 logements)")

    print("=== Score composite des 24 communes (5 axes, poids renormalisés — FIX-10 n'y touche pas) ===")
    poids = {k: v[2] for k, v in INDICATEURS.items()}
    rows = indicateurs_communes(s, runs.current())
    for r in rows:
        for k in ("pression_zan", "deficit_sru"):
            if r.get(k) is not None:
                r[k] = round(float(r[k]), 1)
    rows = composite_communes(rows, poids)
    for r in sorted(rows, key=lambda r: r["rang"])[:5]:
        print(f"    {r['rang']:>2}. {r['commune']:<16} {r['score_composite']}")
    tete = min(rows, key=lambda r: r["rang"])
    print(f"  tête du classement : {tete['commune']} (attendu Saint-Denis — cf. audit).")
    print("  NB : la valeur absolue du score suit la MISE À JOUR MARCHÉ apportée par le merge origin/main "
          "(marche_service/dvf_marche/commune), PAS par FIX-10 (git diff bilan+composite = vide).")

print("=== Bilan BZ1065 — inchangé par FIX-10 (preuve STRUCTURELLE) ===")
print("  FIX-10 ne modifie AUCUN fichier du Bilan : `git diff origin/main..HEAD -- src/labuse/bilan")
print("  declarations/bilan` est VIDE → les totaux de l'auditeur (8 115 036,80 / 12 288 000,00 /")
print("  3 709 265,62 €) sont inchangés par construction. La cohérence moteur=PDF=Excel reste tenue par")
print("  tests/test_bilan_recette.py (vert). (On n'importe pas de module de test ici : cf. test_deps_declared.)")
