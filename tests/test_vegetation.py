"""Wave ANC & Végétation, Lot B — NDVI×MNH par tuile, agrégats, flags, signaux.

Aucun réseau : l'IRC est une image synthétique posée dans un cache temporaire, le MNH
est stubé (monkeypatch de `_fetch_mnh`). La géométrie de test est un carré de 512 m
aligné sur la grille, avec une parcelle dont la moitié EST est boisée (NIR fort +
hauteur 8 m) et la moitié OUEST en pelouse (NIR fort mais hauteur 0).
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest
from sqlalchemy import text

from labuse.ingestion import vegetation

TILE = "300032_7640000"          # xmin_ymin EPSG:2975 (grille 512 m)
XMIN, YMIN = 300032, 7640000


# ───────────────────────── pur : rasterisation ─────────────────────────

def test_rasterize_carre_et_trou():
    sq = {"type": "Polygon", "coordinates": [
        [[XMIN, YMIN], [XMIN + 100, YMIN], [XMIN + 100, YMIN + 100],
         [XMIN, YMIN + 100], [XMIN, YMIN]],
        [[XMIN + 40, YMIN + 40], [XMIN + 60, YMIN + 40], [XMIN + 60, YMIN + 60],
         [XMIN + 40, YMIN + 60], [XMIN + 40, YMIN + 40]],
    ]}
    m = vegetation._rasterize(sq, XMIN, YMIN, 512)
    surf = int(m.sum())
    assert 9200 < surf < 10100    # ~100×100 − trou 20×20 (bords de fillPoly ±)
    assert m[511 - 50, 50] == 0   # dans le trou
    assert m[511 - 10, 10] == 1   # dans le plein


def test_rasterize_geometrie_vide():
    assert vegetation._rasterize(None, XMIN, YMIN, 512) is None
    assert vegetation._rasterize({"type": "GeometryCollection", "geometries": []},
                                 XMIN, YMIN, 512) is None


# ───────────────────────── db : pipeline tuile → parcel_vegetation ─────────────────────────

def _setup_tile_env(s, tmp_path, monkeypatch):
    s.execute(text("""
        CREATE TABLE IF NOT EXISTS ortho_tiles (
          tile_id varchar(24) PRIMARY KEY, geom geometry(Polygon, 2975) NOT NULL,
          millesime varchar(8), acquise_at timestamptz, traite_at timestamptz,
          nb_detections integer, pv_traite_at timestamptz,
          irc_acquise_at timestamptz, veg_traite_at timestamptz)
    """))
    s.execute(text(vegetation.DDL))   # ALTER ortho_tiles + tables du lot (ordre : après la grille)
    s.execute(text("DELETE FROM vegetation_zonal_acc"))
    s.execute(text("DELETE FROM parcel_vegetation"))
    s.execute(text("DELETE FROM ortho_tiles WHERE tile_id = :t"), {"t": TILE})
    s.execute(text("""
        INSERT INTO ortho_tiles (tile_id, geom, millesime, irc_acquise_at)
        VALUES (:t, ST_SetSRID(ST_MakeEnvelope(:x, :y, :x2, :y2), 2975), '2025', now())
    """), {"t": TILE, "x": XMIN, "y": YMIN, "x2": XMIN + 512, "y2": YMIN + 512})
    # parcelle 100×100 m au cœur de la tuile ; bâtiment 20×20 au centre-ouest
    px0, py0 = XMIN + 200, YMIN + 200
    s.execute(text(
        "INSERT INTO parcels (idu, commune, surface_m2, geom) VALUES"
        " ('97415000VG0001', 'Saint-Paul', 10000,"
        "  ST_Transform(ST_SetSRID(ST_GeomFromText(:w), 2975), 4326))"
        " ON CONFLICT (idu) DO NOTHING"),
        {"w": f"POLYGON(({px0} {py0}, {px0 + 100} {py0}, {px0 + 100} {py0 + 100},"
              f" {px0} {py0 + 100}, {px0} {py0}))"})
    s.execute(text(
        "INSERT INTO spatial_layers (kind, geom, commune) VALUES ('batiment',"
        " ST_Transform(ST_SetSRID(ST_GeomFromText(:w), 2975), 4326), 'Saint-Paul')"),
        {"w": f"POLYGON(({px0 + 20} {py0 + 40}, {px0 + 40} {py0 + 40},"
              f" {px0 + 40} {py0 + 60}, {px0 + 20} {py0 + 60}, {px0 + 20} {py0 + 40}))"})
    # IRC synthétique 1280 px (0,4 m/px) : NIR fort partout, rouge faible → NDVI ~0,6
    irc = np.zeros((1280, 1280, 3), np.uint8)
    irc[:, :, 2] = 200   # canal PIR
    irc[:, :, 1] = 50    # canal rouge
    cache = tmp_path / "irc"
    cache.mkdir()
    cv2.imwrite(str(cache / f"{TILE}.jpg"), irc)
    monkeypatch.setattr(vegetation, "irc_tile_path", lambda t: cache / f"{t}.jpg")
    # MNH stub : moitié EST de la TUILE à 8 m, moitié OUEST à 0 m
    mnh = np.zeros((512, 512), np.float32)
    mnh[:, 256:] = 8.0
    monkeypatch.setattr(vegetation, "_fetch_mnh", lambda *_a, **_k: mnh)
    s.flush()


@pytest.mark.db
def test_process_finalize_et_signaux(db_session, tmp_path, monkeypatch):
    s = db_session
    _setup_tile_env(s, tmp_path, monkeypatch)
    res = vegetation.process_tiles(s, log=lambda *_: None)
    assert res["tuiles"] == 1 and res["mnh_echecs"] == 0
    out = vegetation.finalize(s, log=lambda *_: None)
    assert out["parcelles"] >= 1
    row = s.execute(text("""
        SELECT ndvi_moyen, canopee_pct, canopee_limite_pct, canopee_bati_pct,
               methode_hauteur, confiance
        FROM parcel_vegetation WHERE idu = '97415000VG0001'
    """)).one()
    # NDVI (200-50)/(200+50) = 0,6 partout (JPEG ± compression)
    assert 0.5 < row.ndvi_moyen < 0.7
    # parcelle à cheval sur la frontière MNH est/ouest : ~50 % sous canopée
    assert 40 < row.canopee_pct < 60
    assert row.methode_hauteur == "lidar" and row.confiance == "haute"
    # bande limite : moitié est végétalisée aussi → ~50 %
    assert 35 < row.canopee_limite_pct < 65
    # buffer bâti 8 m : bâtiment côté OUEST (MNH 0) → canopée bâti FAIBLE
    assert row.canopee_bati_pct is not None and row.canopee_bati_pct < 25
    # la tuile est checkpointée
    assert s.execute(text(
        "SELECT veg_traite_at IS NOT NULL FROM ortho_tiles WHERE tile_id = :t"),
        {"t": TILE}).scalar_one()


@pytest.mark.db
def test_signal_vegetation_haute_limite(db_session, tmp_path, monkeypatch):
    s = db_session
    _setup_tile_env(s, tmp_path, monkeypatch)
    s.execute(text("""
        INSERT INTO parcel_vegetation (idu, canopee_limite_pct, canopee_pct,
                                       methode_hauteur, confiance, bati_voisin_10m)
        VALUES ('97415000VG0001', 72, 40, 'lidar', 'haute', true)
        ON CONFLICT (idu) DO UPDATE SET canopee_limite_pct = 72, bati_voisin_10m = true
    """))
    n = vegetation.signal_vegetation(s)
    assert n == 1
    payload = s.execute(text("""
        SELECT sg.payload FROM parcel_signals sg JOIN parcels p ON p.id = sg.parcel_id
        WHERE sg.signal_type = 'vegetation_haute_limite' AND p.idu = '97415000VG0001'
    """)).scalar_one()
    assert payload["canopee_limite_pct"] == 72
    assert "IGN" in payload["source"]


def test_preset_elagage_valide():
    from labuse.config import load_yaml_config
    from labuse.segments.presets import validate_preset

    doc = load_yaml_config("segment_presets")
    presets = {p["slug"]: p for p in doc["presets"]}
    assert "elagage-limite" in presets
    assert validate_preset(presets["elagage-limite"]) == []
