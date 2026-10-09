"""CONTENANCE-1 (Lot B) — `surface_terrain` est LA fonction unique de surface de terrain.

Contenance si présente (chiffre de l'acte), sinon dessin du plan (repli, source='plan').
`champs_terrain`/`enrichir_payload` posent les champs servis ; `SURFACE_TERRAIN_SQL` est
l'expression SQL miroir (COALESCE) utilisée dans les filtres/tris.
"""
from __future__ import annotations

from sqlalchemy import text

from labuse import surface as S


def test_surface_terrain_contenance_prioritaire():
    st = S.surface_terrain(27156.4, 25633)
    assert st.valeur == 25633 and st.source == S.SOURCE_CADASTRE
    assert st.dessin_m2 == 27156 and st.contenance_m2 == 25633


def test_surface_terrain_repli_plan():
    st = S.surface_terrain(664.2, None)
    assert st.valeur == 664 and st.source == S.SOURCE_PLAN
    assert st.dessin_m2 == 664 and st.contenance_m2 is None


def test_surface_terrain_tout_nul():
    st = S.surface_terrain(None, None)
    assert st.valeur is None and st.source == S.SOURCE_PLAN


def test_champs_terrain_ne_porte_pas_surface_m2():
    # Le dict additif NE contient PAS surface_m2 (il ne doit pas écraser le dessin servi).
    c = S.champs_terrain(664.2, 694)
    assert "surface_m2" not in c
    assert c == {"surface_terrain_m2": 694, "surface_source": "cadastre",
                 "surface_dessin_m2": 664, "contenance_m2": 694}


def test_enrichir_payload_mute_et_renvoie():
    d = {"surface_m2": 27156.4, "contenance_m2": 25633}
    out = S.enrichir_payload(d)
    assert out is d
    assert out["surface_terrain_m2"] == 25633 and out["surface_source"] == "cadastre"
    assert out["surface_m2"] == 27156.4   # le dessin reste intact


def test_ecart_pct():
    assert round(S.ecart_pct(27156, 25633), 1) == 5.9
    assert round(S.ecart_pct(664, 694), 1) == -4.3
    assert S.ecart_pct(100, None) is None


def test_sql_coalesce_equivaut_a_la_fonction(db_session):
    # L'expression SQL (filtres/tris) et la fonction Python donnent la MÊME surface de terrain.
    s = db_session
    s.execute(text(
        "INSERT INTO parcels (idu, commune, surface_m2, contenance_m2, geom) VALUES "
        "('97415000ZZ0001','Saint-Paul', 27156.4, 25633, ST_SetSRID(ST_MakePoint(55.3,-21.0),4326)),"
        "('97415000ZZ0002','Saint-Paul', 664.2,  NULL,  ST_SetSRID(ST_MakePoint(55.3,-21.0),4326))"))
    rows = {r[0]: r[1] for r in s.execute(text(
        f"SELECT idu, {S.SURFACE_TERRAIN_SQL('p')} FROM parcels p "
        "WHERE idu IN ('97415000ZZ0001','97415000ZZ0002')")).all()}
    assert round(rows["97415000ZZ0001"]) == 25633    # contenance
    assert round(rows["97415000ZZ0002"]) == 664       # repli dessin
