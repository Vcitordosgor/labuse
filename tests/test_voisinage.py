"""Tests assemblage foncier / parcelles voisines (Phase 5). PostGIS réel (base de test)."""
import pytest
from sqlalchemy import text

from labuse.api.voisinage import compute_voisinage

pytestmark = pytest.mark.db


def _parcel(db, idu, x0, status=None, surface=1000.0):
    """Carré ~104 m de côté à l'abscisse x0 (4326) ; le trigger pose geom_2975."""
    wkt = (f"POLYGON(({x0:.5f} -21.0,{x0 + 0.001:.5f} -21.0,{x0 + 0.001:.5f} -20.999,"
           f"{x0:.5f} -20.999,{x0:.5f} -21.0))")
    pid = db.execute(text(
        "INSERT INTO parcels (idu, commune, geom, surface_m2, centroid) VALUES "
        "(:i,'Vz', ST_GeomFromText(:w,4326), :s, ST_Centroid(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": wkt, "s": surface}).scalar()
    if status:
        db.execute(text(
            "INSERT INTO parcel_evaluations (parcel_id, completeness_score, opportunity_score, status) "
            "VALUES (:p, 60, 70, :st)"), {"p": pid, "st": status})
    return pid


def test_voisines_adjacentes_et_assemblage(db_session):
    # Trois carrés ALIGNÉS et CONTIGUS (arêtes partagées) : A|B|C.
    a = _parcel(db_session, "VZ0000000000A1", 55.300, "opportunite", 1000)
    _parcel(db_session, "VZ0000000000B2", 55.301, "opportunite", 1500)   # contiguë à A
    _parcel(db_session, "VZ0000000000C3", 55.302, "a_creuser", 800)      # contiguë à B, pas à A
    db_session.flush()
    vz = compute_voisinage(db_session, a, 1000.0, "opportunite")
    idus = [v["idu"] for v in vz["voisines"]]
    assert "VZ0000000000B2" in idus and "VZ0000000000C3" not in idus     # seule B touche A
    assert vz["assemblage"]["possible"] is True
    assert vz["assemblage"]["n_interessantes"] >= 2
    assert "à vérifier" in vz["assemblage"]["note"]
    # wording prudent : jamais de promesse de propriété / faisabilité / constructibilité
    low = vz["assemblage"]["note"].lower()
    assert "même propriétaire" not in low and "constructible" not in low


def test_faux_positif_ne_propose_pas_d_assemblage(db_session):
    a = _parcel(db_session, "VZ0000000000D4", 55.310, "faux_positif_probable", 1000)
    _parcel(db_session, "VZ0000000000E5", 55.311, "opportunite", 1500)
    db_session.flush()
    vz = compute_voisinage(db_session, a, 1000.0, "faux_positif_probable")
    assert vz["voisines"]                                  # la voisine est listée…
    assert vz["assemblage"]["possible"] is False           # …mais aucun assemblage proposé
    assert vz["assemblage"]["note"] is None


def test_parcelle_isolee(db_session):
    a = _parcel(db_session, "VZ0000000000F6", 55.320, "opportunite", 1000)
    db_session.flush()
    vz = compute_voisinage(db_session, a, 1000.0, "opportunite")
    assert vz["voisines"] == [] and vz["assemblage"]["possible"] is False
