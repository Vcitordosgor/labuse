"""Témoin CIRCUIT-4 — marché Radar : seuil 5 et médianes. ISOLATION : aucun DELETE global — on
FUSIONNE le corpus Saint-Denis existant avec nos lignes seedées (ids réservés 424301+), on
recalcule la médiane INDÉPENDAMMENT sur l'ensemble, et on nettoie nos lignes en sortie."""
from __future__ import annotations

import statistics

import pytest
from sqlalchemy import text

_IDS = list(range(424301, 424308))    # 6 validés + 1 à-qualifier (plage réservée au témoin)


@pytest.mark.db
def test_seuil5_et_medianes(engine):
    from labuse.db import session_scope
    from labuse.pige import marche
    from labuse.pige.tables import ensure_tables
    ensure_tables(engine)
    prix = [(100000, 500), (120000, 400), (150000, 500), (90000, 300),
            (200000, 800), (110000, 550)]
    try:
        with engine.begin() as c:
            for i in _IDS:
                c.execute(text("DELETE FROM pige_faits WHERE bien_id = :b"), {"b": i})
                c.execute(text("DELETE FROM pige_biens WHERE bien_id = :b"), {"b": i})
            for i, (p, st) in zip(_IDS[:6], prix):
                c.execute(text(
                    "INSERT INTO pige_biens (bien_id, commune, type_bien, statut, a_qualifier)"
                    " VALUES (:b, 'Saint-Denis', 'terrain', 'active', false)"), {"b": i})
                c.execute(text(
                    "INSERT INTO pige_faits (bien_id, prix, surface_terrain, valide_at)"
                    " VALUES (:b, :p, :st, now())"), {"b": i, "p": p, "st": st})
            c.execute(text("INSERT INTO pige_biens (bien_id, commune, type_bien, statut,"
                           " a_qualifier) VALUES (:b, 'Saint-Denis', 'terrain', 'active', true)"),
                      {"b": _IDS[6]})
            c.execute(text("INSERT INTO pige_faits (bien_id, prix, surface_terrain, valide_at)"
                           " VALUES (:b, 1, 1, now())"), {"b": _IDS[6]})
            # le corpus COMPLET des terrains validés de Saint-Denis (mêmes WHERE que le moteur),
            # relu pour le recalcul indépendant — nos lignes comprises, l'à-qualifier EXCLU.
            corpus = [(float(r[0]), float(r[1])) for r in c.execute(text(
                "SELECT f.prix, f.surface_terrain FROM pige_biens b"
                " JOIN pige_faits f ON f.bien_id = b.bien_id"
                " WHERE f.valide_at IS NOT NULL AND b.a_qualifier = false"
                " AND b.commune = 'Saint-Denis' AND b.type_bien = 'terrain'"
                " AND f.prix IS NOT NULL AND f.surface_terrain > 0")).all()]
        with session_scope() as s:
            out = marche.stats(s)
    finally:
        with engine.begin() as c:
            for i in _IDS:
                c.execute(text("DELETE FROM pige_faits WHERE bien_id = :b"), {"b": i})
                c.execute(text("DELETE FROM pige_biens WHERE bien_id = :b"), {"b": i})
    ligne = next(l for l in out["communes"] if l["commune"] == "Saint-Denis")
    # recalcul INDÉPENDANT : médiane des prix/m² du corpus fusionné (n ≥ 6 → servie)
    attendu = round(statistics.median([p / st for p, st in corpus]))
    assert ligne["prix_m2_terrain"]["n"] == len(corpus) >= 6
    assert ligne["prix_m2_terrain"]["insuffisant"] is False
    assert ligne["prix_m2_terrain"]["valeur"] == attendu
