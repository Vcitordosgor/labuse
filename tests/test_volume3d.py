"""3.D — Volume constructible 3D (extrusion simple, v1).

Recette du brief : **le volume affiché correspond à l'emprise × hauteur de la capacité déjà
calculée.** On vérifie aussi que la géométrie sort en MÈTRES LOCAUX (prête pour l'axonométrie
front sans dépendance 3D) et qu'une parcelle non constructible ne produit pas de gabarit.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.faisabilite.db import volume3d_payload
from labuse.faisabilite.engine import estimate_capacity
from labuse.faisabilite.plu_rules import resolve_zone

# Parcelle ~30 m de côté, BIEN À L'INTÉRIEUR de la zone (lon 55.30→55.31, lat -21.00→-20.99).
_PARC = ("POLYGON((55.3050 -20.9953,55.3053 -20.9953,55.3053 -20.9950,"
         "55.3050 -20.9950,55.3050 -20.9953))")
_ZONE = "POLYGON((55.30 -21.00,55.31 -21.00,55.31 -20.99,55.30 -20.99,55.30 -21.00))"


def _seed(db, commune, zone_name, zone_subtype, idu):
    db.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, commune, geom) VALUES "
        "('plu_gpu_zone',:st,:zn,:c, ST_GeomFromText(:zw,4326))"),
        {"st": zone_subtype, "zn": zone_name, "c": commune, "zw": _ZONE})
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox) VALUES "
        "(:i,:c,'V','1', ST_GeomFromText(:w,4326), 900, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "c": commune, "w": _PARC}).scalar()


def test_engine_expose_une_hauteur_coherente():
    """La hauteur ajoutée à la capacité (3.D) = niveaux × hauteur d'étage."""
    fr = estimate_capacity(resolve_zone("U1c"), 1000, emprise_geo=(600.0, 3.0)).fourchette
    assert fr["hauteur_m"] == round(fr["niveaux_max"] * fr["hauteur_etage_m"], 1)
    assert fr["hauteur_m"] > 0 and fr["niveaux_max"] >= 1


@pytest.mark.db
def test_volume3d_payload_volume_egale_emprise_fois_hauteur(db_session):
    pid = _seed(db_session, "Volumeville", "U1c", "U", "VOL0000001")
    v = volume3d_payload(db_session, pid)
    assert v and v["constructible"] is True
    # Géométrie en MÈTRES LOCAUX (recentrée centroïde) : ni degrés ni 2975 brut.
    assert v["outline"] and len(v["outline"]) >= 3
    assert all(abs(x) < 1000 and abs(y) < 1000 for x, y in v["outline"])
    assert v["emprise"] and len(v["emprise"]) >= 3           # emprise insetée présente
    # RECETTE : volume = emprise constructible × hauteur (capacité déjà calculée).
    assert v["hauteur_m"] and v["emprise_constructible_m2"]
    assert v["volume_m3"] == round(v["emprise_constructible_m2"] * v["hauteur_m"])


@pytest.mark.db
def test_volume3d_non_constructible_pas_de_gabarit(db_session):
    """Zone agricole → aucune capacité → pas de gabarit (jamais de volume inventé)."""
    pid = _seed(db_session, "Volumeville2", "A", "A", "VOL0000002")
    v = volume3d_payload(db_session, pid)
    assert v is None or v.get("constructible") is False
    assert not (v or {}).get("outline")                      # rien à dessiner
