"""M106-B (arbitrage pôles) — la DÉFINITION cumulée des pôles d'échange, prouvée.

Un pôle d'échange EST un lieu où plusieurs réseaux se croisent : le dénombrement cumule
les lignes DISTINCTES (réseau:ligne) d'une GRAPPE spatiale (DBSCAN, rayon config) — jamais
un comptage par réseau (qui ratait structurellement les vrais nœuds), jamais une somme qui
double-compte une même ligne desservant plusieurs quais.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from labuse.ingestion.transport_reseaux import deriver_poles

pytestmark = pytest.mark.db


def _arret(db, nom, reseau, lignes, lon, lat):
    db.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, geom, attrs) VALUES "
        "('transport_arret', :r, :n, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), CAST(:a AS jsonb))"),
        {"r": reseau, "n": nom, "lon": lon, "lat": lat,
         "a": json.dumps({"reseau": reseau, "nb_lignes": len(lignes), "lignes": lignes})})


def test_cumul_inter_reseaux_dans_une_grappe(db_session):
    """Deux quais de RÉSEAUX DIFFÉRENTS à ~50 m : 8 + 8 lignes distinctes = 16 ≥ 14 → UN pôle
    (l'ancien comptage par réseau n'en voyait aucun). nb_reseaux = 2, critère servi complet."""
    db_session.execute(text("DELETE FROM spatial_layers WHERE kind IN ('transport_arret', 'pole_echange')"))
    lon, lat = 55.30, -21.05
    _arret(db_session, "Gare Test", "Citalis", [f"Citalis:{i}" for i in range(8)], lon, lat)
    _arret(db_session, "Gare Test Quai B", "Car Jaune", [f"Car Jaune:{i}" for i in range(8)], lon + 0.0005, lat)
    assert deriver_poles(db_session, None, None, seuil=14, rayon=150) == 1
    p = db_session.execute(text(
        "SELECT name, attrs FROM spatial_layers WHERE kind = 'pole_echange' AND subtype = 'gtfs'")).one()
    assert p[1]["nb_lignes"] == 16 and p[1]["nb_reseaux"] == 2
    assert "tous réseaux cumulés" in p[1]["critere"] and "150" in p[1]["critere"] and "14" in p[1]["critere"]


def test_union_jamais_une_somme(db_session):
    """Deux quais du MÊME réseau desservis par LES MÊMES 9 lignes (le cas Savanna mesuré) :
    l'union reste 9 < 14 → AUCUN pôle. Une somme naïve (9+9=18) en aurait fabriqué un faux."""
    db_session.execute(text("DELETE FROM spatial_layers WHERE kind IN ('transport_arret', 'pole_echange')"))
    lon, lat = 55.32, -21.06
    memes = [f"Kar'Ouest:{i}" for i in range(9)]
    _arret(db_session, "Savanna Test", "Kar'Ouest", memes, lon, lat)
    _arret(db_session, "Savanna Test Quai B", "Kar'Ouest", memes, lon + 0.0003, lat)
    assert deriver_poles(db_session, None, None, seuil=14, rayon=150) == 0


def test_hors_grappe_pas_de_cumul(db_session):
    """Deux quais à ~900 m (> rayon 150) : deux grappes distinctes, aucune ne passe le seuil —
    un rayon trop grand fabriquerait un faux pôle en fusionnant des nœuds distincts."""
    db_session.execute(text("DELETE FROM spatial_layers WHERE kind IN ('transport_arret', 'pole_echange')"))
    lon, lat = 55.34, -21.07
    _arret(db_session, "Nord", "Citalis", [f"Citalis:{i}" for i in range(8)], lon, lat)
    _arret(db_session, "Sud", "Car Jaune", [f"Car Jaune:{i}" for i in range(8)], lon, lat - 0.008)
    assert deriver_poles(db_session, None, None, seuil=14, rayon=150) == 0
