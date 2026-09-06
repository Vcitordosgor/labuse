"""Témoin CIRCUIT-4 — marché Radar : seuil 5 et médianes, sur lignes SEEDÉES (recompte à la main)."""
from __future__ import annotations

import statistics

import pytest
from sqlalchemy import text


@pytest.mark.db
def test_seuil5_et_medianes(engine):
    from labuse.db import session_scope
    from labuse.pige import marche
    from labuse.pige.tables import ensure_tables
    ensure_tables(engine)
    with session_scope() as s:
        s.execute(text("DELETE FROM pige_faits"))
        s.execute(text("DELETE FROM pige_biens"))
        # 6 terrains validés (≥ SEUIL_N) à Saint-Denis + 1 à-qualifier (exclu des stats)
        prix = [(100000, 500), (120000, 400), (150000, 500), (90000, 300),
                (200000, 800), (110000, 550)]
        for i, (p, st) in enumerate(prix, start=1):
            s.execute(text(
                "INSERT INTO pige_biens (bien_id, commune, type_bien, statut, a_qualifier)"
                " VALUES (:b, 'Saint-Denis', 'terrain', 'active', false)"), {"b": i})
            s.execute(text(
                "INSERT INTO pige_faits (bien_id, prix, surface_terrain, valide_at)"
                " VALUES (:b, :p, :st, now())"), {"b": i, "p": p, "st": st})
        s.execute(text("INSERT INTO pige_biens (bien_id, commune, type_bien, statut, a_qualifier)"
                       " VALUES (99, 'Saint-Denis', 'terrain', 'active', true)"))
        s.execute(text("INSERT INTO pige_faits (bien_id, prix, surface_terrain, valide_at)"
                       " VALUES (99, 1, 1, now())"))
        s.commit()
        out = marche.stats(s)
    ligne = next(l for l in out["communes"] if l["commune"] == "Saint-Denis")
    # recompte indépendant : médiane des prix/m² des 6 validés (l'à-qualifier N'Y EST PAS)
    attendu = round(statistics.median([p / st for p, st in prix]))
    assert ligne["prix_m2_terrain"]["valeur"] == attendu
    assert ligne["prix_m2_terrain"]["n"] == 6 and ligne["prix_m2_terrain"]["insuffisant"] is False
    assert ligne["actives"] == 6               # les comptes ignorent aussi l'à-qualifier
