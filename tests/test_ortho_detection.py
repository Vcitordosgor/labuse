"""Tests wave-ortho : détection piscines V0 (image synthétique) + géoréférencement."""
from __future__ import annotations

import numpy as np
import pytest
from sqlalchemy import text

from labuse.config import load_yaml_config


def _image_synthetique() -> np.ndarray:
    """Tuile 512×512 px « sol » avec : une piscine 8×5 m turquoise, un filament
    turquoise (ravine), un grand bassin 40×40 m (terrain de sport), un point sombre."""
    import cv2

    img = np.full((512, 512, 3), (60, 90, 100), np.uint8)  # BGR sol brunâtre
    # piscine : 40×25 px (8×5 m à 20 cm) turquoise clair (BGR)
    cv2.rectangle(img, (100, 100), (140, 125), (200, 190, 40), -1)
    # filament : 3 px de large, 200 px de long (aspect >> 6)
    cv2.rectangle(img, (300, 50), (303, 250), (200, 190, 40), -1)
    # trop grand : 200×200 px = 40×40 m = 1600 m² > 150 m²
    cv2.rectangle(img, (300, 300), (500, 500), (200, 190, 40), -1)
    # trampoline sombre (V faible)
    cv2.circle(img, (60, 400), 12, (80, 60, 10), -1)
    return img


def test_detect_in_image_filtres():
    from labuse.ingestion.ortho_piscines import _detect_in_image

    cfg = load_yaml_config("detection_ortho")["piscines"]
    cands = _detect_in_image(_image_synthetique(), cfg)
    assert len(cands) == 1  # seule la piscine passe les filtres
    c = cands[0]
    assert 30 <= c["surface_m2"] <= 50  # 8×5 m = 40 m²
    assert c["scores"]["couleur"] > 0.5
    assert c["scores"]["taille"] == 1.0  # dans la plage typique 15-50 m²


def test_px_to_wkt_georef():
    """(0,0) pixel = coin NW de la tuile ; y descend quand row monte."""
    from labuse.ingestion.ortho_piscines import _px_to_wkt_2975

    px = np.array([[0, 0], [10, 0], [10, 10]])
    wkt = _px_to_wkt_2975(px, xmin=338000, ymin=7661000, tile_px=2560)
    # coin NW = (338000, 7661512) pour une tuile de 512 m
    assert wkt.startswith("POLYGON((338000.00 7661512.00, 338002.00 7661512.00, "
                          "338002.00 7661510.00")


def test_detect_pv_ces_et_ombres():
    """PV ≥ 8 m² vs CES 4-8 m² ; les bandes fines (ombres de rive) sont rejetées."""
    import cv2

    from labuse.ingestion.ortho_pv import _detect_pv

    cfg = load_yaml_config("detection_ortho")["pv"]
    img = np.full((512, 512, 3), (140, 150, 160), np.uint8)  # toit clair
    zones = np.full((512, 512), 255, np.uint8)
    # panneau PV 6×4 m (30×20 px) anthracite bleuté
    cv2.rectangle(img, (100, 100), (130, 120), (60, 40, 30), -1)
    # CES 2,4×2 m (12×10 px)
    cv2.rectangle(img, (300, 300), (312, 310), (60, 40, 30), -1)
    # ombre de rive : bande de 0,6 m × 20 m (3×100 px)
    cv2.rectangle(img, (400, 50), (403, 150), (60, 40, 30), -1)
    cands = _detect_pv(img, zones, cfg)
    assert len(cands) == 2
    ces = {c["scores"]["ces"] for c in cands}
    assert ces == {True, False}  # un CES, un PV


def test_rings_parser():
    from labuse.ingestion.ortho_pv import _rings

    rings = _rings("MULTIPOLYGON(((0 0, 10 0, 10 10, 0 0)), ((20 20, 30 20, 30 30, 20 20)))")
    assert len(rings) == 2 and rings[0][1] == (10.0, 0.0)


pytestmark_db = pytest.mark.db


@pytest.mark.db
def test_post_traitement_rejets(db_session):
    """Rejets contextuels : hors cadastre supprimé, toit bleu supprimé, contexte scoré."""
    from labuse.ingestion.ortho_piscines import DDL, post_traitement
    from labuse.ingestion.ortho_tiles import DDL as DDL_TILES

    db_session.execute(text(DDL_TILES))
    db_session.execute(text(DDL))
    db_session.execute(text(
        """CREATE TABLE IF NOT EXISTS parcel_residuel_bati
             (idu varchar(14) PRIMARY KEY, emprise_batie_m2 double precision)"""))
    poly = ("POLYGON((55.4495 -21.3005, 55.4505 -21.3005, 55.4505 -21.2995, "
            "55.4495 -21.2995, 55.4495 -21.3005))")
    db_session.execute(text(
        f"""INSERT INTO parcels (idu, commune, section, numero, surface_m2, geom, geom_2975)
            VALUES ('97416000ZZ0001', 'Saint-Pierre', 'ZZ', '0001', 11000,
                    ST_GeomFromText('{poly}', 4326),
                    ST_Transform(ST_GeomFromText('{poly}', 4326), 2975))"""))
    db_session.execute(text(
        "INSERT INTO parcel_residuel_bati VALUES ('97416000ZZ0001', 120)"))
    crit = '{"couleur": 0.8, "forme": 0.8, "taille": 1.0}'

    def add(dx: float) -> None:
        p = (f"POLYGON(({55.4499 + dx} -21.3001, {55.4501 + dx} -21.3001, "
             f"{55.4501 + dx} -21.2999, {55.4499 + dx} -21.2999, {55.4499 + dx} -21.3001))")
        db_session.execute(text(
            """INSERT INTO ortho_detections (type, geom, geom_2975, surface_m2, criteres)
               VALUES ('piscine', ST_GeomFromText(:p, 4326),
                       ST_Transform(ST_GeomFromText(:p, 4326), 2975), 35,
                       CAST(:c AS jsonb))"""), {"p": p, "c": crit})

    add(0.0)     # dans la parcelle bâtie → gardée, contexte 1.0
    add(0.05)    # à ~5 km de tout cadastre → rejetée (hors cadastre)
    res = post_traitement(db_session, log=lambda *_: None)
    assert res["rejets"]["hors_cadastre"] == 1
    conf, idu = db_session.execute(text(
        "SELECT confiance, idu FROM ortho_detections WHERE type='piscine'")).one()
    assert idu == "97416000ZZ0001"
    # 0.35*0.8 + 0.25*0.8 + 0.20*1.0 + 0.20*1.0 = 0.88
    assert abs(float(conf) - 0.88) < 0.02
