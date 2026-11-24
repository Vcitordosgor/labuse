"""SITADEL — historique des autorisations à proximité (Lot C4), sur PostGIS réel."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from labuse.ingestion.permits import nearby_permits

pytestmark = pytest.mark.db


def _parcel(db, idu, wkt):
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox) VALUES "
        "(:i,'Permia','S','1', ST_GeomFromText(:w,4326), 1000, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"),
        {"i": idu, "w": wkt}).scalar()


def _permit(db, pid, typ, idus, point_wkt=None):
    db.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, idu_codes, commune, geom, raw) VALUES "
        "(:pid,:t, now() - interval '1 year', CAST(:i AS jsonb),'Permia',"
        "  CASE WHEN CAST(:w AS text) IS NULL THEN NULL ELSE ST_GeomFromText(CAST(:w AS text),4326) END, '{}'::jsonb)"),
        {"pid": pid, "t": typ, "i": json.dumps(idus), "w": point_wkt})


def test_permit_rattache_par_idu(db_session):
    pid = _parcel(db_session, "PMT00001",
                  "POLYGON((55.40 -21.00,55.401 -21.00,55.401 -20.999,55.40 -20.999,55.40 -21.00))")
    _permit(db_session, "PC-RAT", "PC", ["PMT00001"], "POINT(55.4005 -20.9995)")
    pm = nearby_permits(db_session, pid)
    assert pm["count"] >= 1 and pm["rattaches"] == 1
    assert pm["items"][0]["rattache"] is True and pm["items"][0]["type"] == "PC"


def test_permit_proximite_distance(db_session):
    pid = _parcel(db_session, "PMT00002",
                  "POLYGON((55.50 -21.10,55.501 -21.10,55.501 -21.099,55.50 -21.099,55.50 -21.10))")
    _permit(db_session, "PC-NEAR", "DP", [], "POINT(55.5015 -21.0995)")   # ~150 m
    pm = nearby_permits(db_session, pid, radius_m=300)
    assert pm["count"] == 1 and pm["rattaches"] == 0
    it = pm["items"][0]
    assert it["rattache"] is False and it["distance_m"] is not None and it["distance_m"] <= 300


def test_permit_hors_rayon_absent(db_session):
    pid = _parcel(db_session, "PMT00003",
                  "POLYGON((55.60 -21.20,55.601 -21.20,55.601 -21.199,55.60 -21.199,55.60 -21.20))")
    _permit(db_session, "PC-FAR", "PC", [], "POINT(55.610 -21.205)")      # ~1 km
    pm = nearby_permits(db_session, pid, radius_m=300)
    assert pm["count"] == 0


def test_nature_et_dynamique(db_session):
    """1.B : nature (logements/surface) + statut + indicateur de dynamique de secteur."""
    import json as _j
    pid = _parcel(db_session, "PMT00100",
                  "POLYGON((55.40 -21.05,55.401 -21.05,55.401 -21.049,55.40 -21.049,55.40 -21.05))")
    # 3 permis géolocalisés à proximité, dont 2 récents avec logements
    permits = [("PCN0", "PC", 5, 420, "POINT(55.4003 -21.0497)"),
               ("PCN1", "PC", 3, 260, "POINT(55.4006 -21.0496)"),
               ("PCN2", "DP", 0, 0, "POINT(55.4004 -21.0498)")]
    for num, typ, lgt, surf, pt in permits:
        db_session.execute(text(
            "INSERT INTO sitadel_permits (permit_id,type,date,idu_codes,commune,geom,raw) VALUES "
            "(:p,:t, now()-interval '1 year', '[]'::jsonb,'Permia', ST_GeomFromText(:w,4326), CAST(:raw AS jsonb))"),
            {"p": num, "t": typ, "w": pt,
             "raw": _j.dumps({"nb_lgt": lgt, "surf_hab": surf, "daact": None})})
    from labuse.ingestion.permits import nearby_permits
    pm = nearby_permits(db_session, pid, radius_m=300)
    assert pm["dynamique"]["niveau"] == "modéré" or pm["dynamique"]["niveau"] == "actif"
    assert pm["dynamique"]["logements_recents"] == 8        # 5 + 3
    pc = next(i for i in pm["items"] if i["num"] == "PCN0")
    assert "5 logements" in pc["nature"] and "420 m²" in pc["nature"]
    assert pc["statut"].startswith("autorisé le")
    dp = next(i for i in pm["items"] if i["num"] == "PCN2")
    assert "non résidentiel" in dp["nature"]                # 0 logement → projet non résidentiel


def test_dynamique_respecte_le_rayon(db_session):
    """OUTIL-PERMIS-FIX-3 (Point 1) — ÉCHOUE si le RAYON disparaît du compte `dynamique` (régression du
    mandat 1 : le Dossier recevait le total de l'île). On sème un permis PROCHE (dans le rayon, 10 logts)
    ET un permis LOIN (~1 km, 999 logts) : le compte de dynamique ne doit voir QUE le proche."""
    import json as _j
    pid = _parcel(db_session, "PMT00200",
                  "POLYGON((55.30 -21.30,55.301 -21.30,55.301 -21.299,55.30 -21.299,55.30 -21.30))")
    for num, pt, lgt in (("PCDYN-NEAR", "POINT(55.3005 -21.2995)", 10),   # ~70 m
                         ("PCDYN-FAR", "POINT(55.320 -21.320)", 999)):     # ~3 km
        db_session.execute(text(
            "INSERT INTO sitadel_permits (permit_id,type,date,idu_codes,commune,geom,raw) VALUES "
            "(:p,'PC', now()-interval '6 months', '[]'::jsonb,'Permia', ST_GeomFromText(:w,4326), CAST(:raw AS jsonb))"),
            {"p": num, "w": pt, "raw": _j.dumps({"nb_lgt": lgt, "daact": None})})
    pm = nearby_permits(db_session, pid, radius_m=500, fenetre_mois=24)
    # SANS le rayon, le lointain (999 logts) gonflerait le compte : le test l'interdit.
    assert pm["dynamique"]["permis_recents"] == 1
    assert pm["dynamique"]["logements_recents"] == 10


def test_dynamique_exclut_les_annules(db_session):
    """OUTIL-PERMIS-FIX-7 (Point 3) — les permis ANNULÉS (ETAT_DAU=4) SORTENT du compte « à proximité »
    (n, logements, sans-nb) et sont comptés À PART (`permis_annules`), via la règle d'état unique
    (permis_classe.annule_sql). On sème 2 permis PROCHES : un normal (3 logts) + un ANNULÉ (5 logts)."""
    import json as _j
    pid = _parcel(db_session, "PMT00300",
                  "POLYGON((55.35 -21.35,55.351 -21.35,55.351 -21.349,55.35 -21.349,55.35 -21.35))")
    for num, pt, lgt, etat in (("PCANN-OK", "POINT(55.3505 -21.3495)", 3, "2"),      # autorisé
                               ("PCANN-NUL", "POINT(55.3506 -21.3494)", 5, "4")):    # ANNULÉ (code 4)
        db_session.execute(text(
            "INSERT INTO sitadel_permits (permit_id,type,date,idu_codes,commune,geom,raw) VALUES "
            "(:p,'PC', now()-interval '6 months', '[]'::jsonb,'Permia', ST_GeomFromText(:w,4326), CAST(:raw AS jsonb))"),
            {"p": num, "w": pt, "raw": _j.dumps({"nb_lgt": lgt, "etat": etat, "daact": None})})
    pm = nearby_permits(db_session, pid, radius_m=500, fenetre_mois=24)
    dyn = pm["dynamique"]
    assert dyn["permis_recents"] == 1          # l'annulé est HORS du compte
    assert dyn["logements_recents"] == 3       # les 5 logts de l'annulé ne sont pas sommés
    assert dyn["permis_annules"] == 1          # mais il est compté À PART
    db_session.execute(text("DELETE FROM sitadel_permits WHERE permit_id IN ('PCANN-OK','PCANN-NUL')"))


def test_delai_depuis_an_depot_et_fiche_masquee(db_session):
    """OUTIL-PERMIS-FIX-4 (Points 2-4) — la couche des délais dérive le dépôt de AN_DEPOT (année), PAS de
    DR_DEPOT (= date d'autorisation, corrompu) ; et la fiche masque dépôt+délai quand le dépôt n'est pas
    une date précise fiable (DR_DEPOT = autorisation)."""
    import json as _j
    from labuse.ingestion.permit_delais_m10 import ensure_delais_vivants
    # permit DP : AN_DEPOT 2023 (dépôt réel), autorisation 2026-01-15, DR_DEPOT = autorisation (corrompu)
    db_session.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, date_depot, idu_codes, commune, raw) VALUES "
        "('DELAI-AN','DP','2026-01-15','2026-01-15','[]'::jsonb,'Permia',CAST(:raw AS jsonb))"),
        {"raw": _j.dumps({"an_depot": "2023", "famille": "logements", "nb_lgt": "1"})})
    ensure_delais_vivants(db_session, resync=True)
    r = db_session.execute(text(
        "SELECT date_depot, delai_mois, valide FROM m10_permit_delais WHERE permit_id='DELAI-AN'")).mappings().first()
    # dépôt = AN_DEPOT-01-01 (2023-01-01), délai = 36 mois + 0 = 36 ; valide (autorisation ≥ dépôt).
    # (La couche a bien dérivé le dépôt de AN_DEPOT, PAS de date_depot=DR_DEPOT=autorisation=2026-01-15,
    #  qui aurait donné un délai 0 fallacieux.)
    assert str(r["date_depot"]) == "2023-01-01" and r["delai_mois"] == 36 and r["valide"] is True
    db_session.execute(text("DELETE FROM sitadel_permits WHERE permit_id='DELAI-AN'"))
    db_session.execute(text("DELETE FROM m10_permit_delais WHERE permit_id='DELAI-AN'"))
