"""Blocs fonciers (OUTILS-MUSCLER-3) — regroupement de parcelles contiguës d'un même SIREN,
sur PostGIS réel. Un bloc connu vérifié à la main + les cas limites (isolée, propriétaires
différents, particulier) qui ne DOIVENT PAS se regrouper.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse import blocs
from labuse.faisabilite import residuel_runs as rr

pytestmark = pytest.mark.db

# Deux carrés ADJACENTS (côte à côte, contact cadastral) et un carré LOIN, à Blocville.
_A = "POLYGON((55.40 -21.00,55.4003 -21.00,55.4003 -20.9997,55.40 -20.9997,55.40 -21.00))"
_B = "POLYGON((55.4003 -21.00,55.4006 -21.00,55.4006 -20.9997,55.4003 -20.9997,55.4003 -21.00))"
_LOIN = "POLYGON((55.70 -21.30,55.7003 -21.30,55.7003 -21.2997,55.70 -21.2997,55.70 -21.30))"


def _p(db, idu, wkt, surf, commune="Blocville", zone=None):
    pid = db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox, geom_2975)"
        " VALUES (:i,:c,'S','1', ST_GeomFromText(:w,4326), :s,"
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)),"
        " ST_Transform(ST_GeomFromText(:w,4326),2975)) RETURNING id"),
        {"i": idu, "c": commune, "w": wkt, "s": surf}).scalar()
    if zone is not None:
        db.execute(text("INSERT INTO parcel_zone_plu (idu, zone_lib) VALUES (:i,:z)"),
                   {"i": idu, "z": zone})
    return pid


def _pm(db, idu, siren, denom="SCI TEST", groupe=None, forme=None):
    db.execute(text(
        "INSERT INTO parcelle_personne_morale (idu, siren, denomination, groupe, forme_juridique) "
        "VALUES (:i,:s,:d,:g,:f)"),
        {"i": idu, "s": siren, "d": denom, "g": groupe, "f": forme})


def _served_residuel(db, residuels: dict[int, int], seq: int = 1) -> None:
    """Installe un run résiduel SERVI et écrit les valeurs là où `compute_blocs` LIT.

    En prod `parcel_residuel` est une VUE sur le run servi ; en base de test c'est une table
    simple (créée par le schéma). On couvre les deux pour rester fidèle au chemin de lecture.
    """
    conn = db.connection()
    rr.ensure_runs_schema(conn)
    conn.execute(text("DELETE FROM residuel_runs"))
    conn.execute(text("INSERT INTO residuel_runs (run_seq, label, is_served) VALUES (:s,'test',true)"),
                 {"s": seq})
    kind = conn.execute(text("SELECT relkind FROM pg_class WHERE relname='parcel_residuel'")).scalar()
    if kind == "v" or kind is None:            # prod-like : versionné + vue
        for pid, sdp in residuels.items():
            conn.execute(text("INSERT INTO parcel_residuel_runs (run_seq, parcel_id, sdp_residuelle_m2, "
                              "capacite_estimee) VALUES (:r,:p,:v,true)"), {"r": seq, "p": pid, "v": sdp})
        if kind is None:
            conn.execute(text(rr._view_sql()))
    else:                                       # base de test : table simple
        conn.execute(text("DELETE FROM parcel_residuel"))
        for pid, sdp in residuels.items():
            conn.execute(text("INSERT INTO parcel_residuel (parcel_id, sdp_residuelle_m2, "
                              "capacite_estimee) VALUES (:p,:v,true)"), {"p": pid, "v": sdp})


def test_bloc_connu_verifie_a_la_main(db_session):
    """Deux parcelles contiguës du MÊME SIREN → UN bloc de 2. IDU, surface, résiduel, zonages vérifiés."""
    a = _p(db_session, "BLOC00001", _A, 600, zone="UA")
    b = _p(db_session, "BLOC00002", _B, 640, zone="UB")
    _pm(db_session, "BLOC00001", "S0001", "SCI ALPHA")
    _pm(db_session, "BLOC00002", "S0001", "SCI ALPHA")
    _served_residuel(db_session, {a: 300, b: 150})

    blocs.build_blocs(db_session)

    rows = db_session.execute(text(
        "SELECT bloc_key, siren, denomination, n_parcelles, surface_totale_m2, communes, "
        "sdp_residuelle_m2, sdp_couverture, zonages, residuel_run_seq FROM parcel_blocs")).mappings().all()
    assert len(rows) == 1
    r = rows[0]
    assert r["siren"] == "S0001" and r["denomination"] == "SCI ALPHA"
    assert r["bloc_key"] == "S0001:BLOC00001"          # clé déterministe = siren:min(idu)
    assert r["n_parcelles"] == 2
    assert r["surface_totale_m2"] == 1240             # 600 + 640, à la main
    assert r["communes"] == ["Blocville"]
    assert r["sdp_residuelle_m2"] == 450 and r["sdp_couverture"] == 2   # 300 + 150
    assert sorted(r["zonages"]) == ["UA", "UB"]
    assert r["residuel_run_seq"] == 1

    membres = db_session.execute(text(
        "SELECT idu, surface_m2, zone, sdp_residuelle_m2 FROM parcel_bloc_membres "
        "ORDER BY idu")).mappings().all()
    assert [m["idu"] for m in membres] == ["BLOC00001", "BLOC00002"]
    assert membres[0]["sdp_residuelle_m2"] == 300 and membres[0]["zone"] == "UA"


def test_parcelle_isolee_non_regroupee(db_session):
    """Un SIREN qui ne possède qu'UNE parcelle → aucun bloc (il faut 2 parcelles minimum)."""
    _p(db_session, "BLOC00010", _A, 600)
    _pm(db_session, "BLOC00010", "S0010")
    _served_residuel(db_session, {})
    blocs.build_blocs(db_session)
    assert db_session.execute(text("SELECT count(*) FROM parcel_blocs")).scalar() == 0


def test_proprietaires_differents_non_regroupes(db_session):
    """Deux parcelles CONTIGUËS mais de SIREN DIFFÉRENTS → jamais regroupées."""
    _p(db_session, "BLOC00020", _A, 600)
    _p(db_session, "BLOC00021", _B, 600)      # contiguë de la précédente
    _pm(db_session, "BLOC00020", "S0020")
    _pm(db_session, "BLOC00021", "S0021")     # propriétaire différent
    _served_residuel(db_session, {})
    blocs.build_blocs(db_session)
    assert db_session.execute(text("SELECT count(*) FROM parcel_blocs")).scalar() == 0


def test_particulier_hors_perimetre(db_session):
    """Deux parcelles contiguës SANS personne morale (particulier) → hors périmètre, aucun bloc."""
    _p(db_session, "BLOC00030", _A, 600)
    _p(db_session, "BLOC00031", _B, 600)      # contiguë, mais aucun lien PM
    _served_residuel(db_session, {})
    blocs.build_blocs(db_session)
    assert db_session.execute(text("SELECT count(*) FROM parcel_blocs")).scalar() == 0


def test_non_contigues_meme_siren_non_regroupees(db_session):
    """Même SIREN mais parcelles ÉLOIGNÉES (> 0,5 m) → deux singletons, aucun bloc."""
    _p(db_session, "BLOC00040", _A, 600)
    _p(db_session, "BLOC00041", _LOIN, 600)   # loin
    _pm(db_session, "BLOC00040", "S0040")
    _pm(db_session, "BLOC00041", "S0040")
    _served_residuel(db_session, {})
    blocs.build_blocs(db_session)
    assert db_session.execute(text("SELECT count(*) FROM parcel_blocs")).scalar() == 0


def test_endpoint_liste_et_detail(db_session):
    """L'endpoint /modules/blocs sert la liste (bandeau, filtres) et /modules/blocs/{id} le détail."""
    from fastapi import HTTPException

    from labuse.api import modules

    a = _p(db_session, "BLOC00060", _A, 700, commune="Blocville", zone="UA")
    b = _p(db_session, "BLOC00061", _B, 500, commune="Blocville", zone="UB")
    _pm(db_session, "BLOC00060", "S0060", "SCI OMEGA")
    _pm(db_session, "BLOC00061", "S0060", "SCI OMEGA")
    _served_residuel(db_session, {a: 400, b: 100})
    blocs.build_blocs(db_session)

    r = modules.blocs_liste(commune=None, surface_min=0, sdp_min=0, n_min=2,
                            limit=200, offset=0, db=db_session)
    assert r["total"] == 1 and r["n"] == 1
    it = r["items"][0]
    assert it["denomination"] == "SCI OMEGA" and it["siren"] == "S0060"
    assert it["n_parcelles"] == 2 and it["surface_totale_m2"] == 1200
    assert it["sdp_residuelle_m2"] == 500 and it["idu_repr"] == "BLOC00060"
    assert r["millesime"] is None or isinstance(r["millesime"], str)  # bandeau : source + millésime

    # filtre à paliers : un seuil résiduel trop haut écrème le bloc
    assert modules.blocs_liste(commune=None, surface_min=0, sdp_min=1000, n_min=2,
                               limit=200, offset=0, db=db_session)["total"] == 0
    # filtre nombre de parcelles
    assert modules.blocs_liste(commune=None, surface_min=0, sdp_min=0, n_min=3,
                               limit=200, offset=0, db=db_session)["total"] == 0

    d = modules.bloc_detail(bloc_id=it["bloc_id"], db=db_session)
    assert [m["idu"] for m in d["membres"]] == ["BLOC00060", "BLOC00061"]  # tri résiduel desc
    assert d["membres"][0]["sdp_residuelle_m2"] == 400
    with pytest.raises(HTTPException) as e:
        modules.bloc_detail(bloc_id=999999, db=db_session)
    assert e.value.status_code == 404


def test_proprietaires_publics_ecartes_par_defaut(db_session):
    """Un bloc de propriétaire PUBLIC (commune, groupe DGFiP 4) est écarté par défaut ; la case
    `inclure_publics` le rétablit ; le bandeau compte les écartés. Classé par catégorie juridique."""
    from labuse.api import modules

    # bloc PRIVÉ (SCI, groupe 0) et bloc PUBLIC (commune, groupe 4), chacun 2 parcelles contiguës.
    pa = _p(db_session, "BLOC00070", _A, 600); pb = _p(db_session, "BLOC00071", _B, 600)
    _pm(db_session, "BLOC00070", "S0070", "SCI PRIVEE"); _pm(db_session, "BLOC00071", "S0070", "SCI PRIVEE")
    pc = _p(db_session, "BLOC00080", _LOIN, 600)
    pd = _p(db_session, "BLOC00081", "POLYGON((55.7003 -21.30,55.7006 -21.30,55.7006 -21.2997,55.7003 -21.2997,55.7003 -21.30))", 600)
    _pm(db_session, "BLOC00080", "S0080", "COMMUNE DE TEST", groupe=4)
    _pm(db_session, "BLOC00081", "S0080", "COMMUNE DE TEST", groupe=4)
    _served_residuel(db_session, {pa: 100, pb: 100, pc: 50, pd: 50})
    blocs.build_blocs(db_session)

    # is_public bien posé : commune=public, SCI=privé.
    pub = dict(db_session.execute(text("SELECT siren, is_public FROM parcel_blocs")).all())
    assert pub == {"S0070": False, "S0080": True}

    kw = dict(commune=None, surface_min=0, sdp_min=0, n_min=2, limit=200, offset=0)
    # par défaut : le public est écarté, le bandeau le compte.
    d = modules.blocs_liste(inclure_publics=False, db=db_session, **kw)
    assert d["total"] == 1 and d["n_publics"] == 1 and d["inclure_publics"] is False
    assert [i["siren"] for i in d["items"]] == ["S0070"]
    # inclure_publics : les deux reviennent.
    d2 = modules.blocs_liste(inclure_publics=True, db=db_session, **kw)
    assert d2["total"] == 2 and {i["siren"] for i in d2["items"]} == {"S0070", "S0080"}


def test_idempotent(db_session):
    """Rejouer le batch produit le MÊME contenu (DELETE + rebuild, bloc_key déterministe)."""
    a = _p(db_session, "BLOC00050", _A, 600, zone="UA")
    b = _p(db_session, "BLOC00051", _B, 600, zone="UA")
    _pm(db_session, "BLOC00050", "S0050")
    _pm(db_session, "BLOC00051", "S0050")
    _served_residuel(db_session, {a: 100, b: 200})

    s1 = blocs.build_blocs(db_session)
    empreinte1 = db_session.execute(text(
        "SELECT bloc_key, sdp_residuelle_m2 FROM parcel_blocs ORDER BY bloc_key")).all()
    s2 = blocs.build_blocs(db_session)
    empreinte2 = db_session.execute(text(
        "SELECT bloc_key, sdp_residuelle_m2 FROM parcel_blocs ORDER BY bloc_key")).all()
    assert s1 == s2 and empreinte1 == empreinte2
    assert db_session.execute(text("SELECT count(*) FROM parcel_blocs")).scalar() == 1
