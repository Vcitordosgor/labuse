"""Stabilisation démo : healthcheck, seed pipeline (sans nom réel), parcelles documentées."""
from sqlalchemy import text

from labuse import demo


def _seed_parcels(db, commune="Testville", k=4):
    for i in range(k):
        x = 55.30 + i * 0.01
        wkt = f"POLYGON(({x:.3f} -21.000,{x + 0.005:.3f} -21.000,{x + 0.005:.3f} -20.995,{x:.3f} -20.995,{x:.3f} -21.000))"
        db.execute(text(
            "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox) VALUES "
            "(:i,:c,'T',:n, ST_GeomFromText(:w,4326), 1000, ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
            {"i": f"TEST{i:010d}", "c": commune, "n": str(i), "w": wkt})


# ── Pur ───────────────────────────────────────────────────────────
def test_parcelles_demo_documentees():
    assert len(demo.DEMO_PARCELS) >= 8
    for p in demo.DEMO_PARCELS:
        assert {"idu", "role", "montre", "vigilance"} <= set(p)
        assert p["idu"].startswith("97415") and len(p["idu"]) == 14


def test_seed_pipeline_aucun_nom_de_personne():
    # le seed n'emploie QUE des organisations « à confirmer », jamais un nom de personne physique.
    for s in demo._SEED_PIPELINE:
        assert "contact_nom" not in s["prospection"]


# ── DB ────────────────────────────────────────────────────────────
def test_seed_pipeline_idempotent(db_session):
    _seed_parcels(db_session)
    n1 = demo.seed_demo_pipeline(db_session, "Testville")
    n2 = demo.seed_demo_pipeline(db_session, "Testville")     # rejouable → pas de doublon
    assert n1 == n2 == len(demo._SEED_PIPELINE)
    rows = db_session.execute(text(
        "SELECT pe.prospection->>'statut_proprietaire', pe.prospection->>'contact_nom' "
        "FROM pipeline_entries pe JOIN parcels p ON p.id=pe.parcel_id WHERE p.commune='Testville'")).all()
    assert len(rows) == len(demo._SEED_PIPELINE)
    assert all(r[1] is None for r in rows)                    # aucun nom de personne stocké


def test_healthcheck_base_minimale_non_prete(db_session):
    _seed_parcels(db_session, "Testville", 2)
    res = demo.healthcheck(db_session, "Testville")
    assert res["ok"] is False                                 # PPR/SAR/DVF/OSM absents
    by = {c["name"]: c for c in res["checks"]}
    assert by["PPR"]["ok"] is False and by["PPR"]["critical"] is True
    assert by["SAR"]["ok"] is False and by["DVF geo-dvf"]["ok"] is False
    # ce qui est durable côté schéma est OK même sur base minimale :
    assert by["Module prospection"]["ok"] is True
    assert by["Exports HTML/Markdown"]["ok"] is True
    assert by["geom_2975 valide"]["ok"] is True               # trigger create_all → géom posée
