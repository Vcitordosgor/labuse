"""RADAR P3 · C1 — lecture côté CLIENT (liste filtrée, détail, clic sortant, signalement).

On sème un jeu [RADAR-TEST] représentatif (Sourcé rattaché, Estimé, non rattaché, baisse de prix,
brouillon non validé, retiré) et on gèle : le client ne voit QUE des VALIDÉS, la carte ne compte que
les rattachés, le clic est logué, le signalement ne change PAS le statut. [RADAR-TEST] purgés en fin.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import client

pytestmark = pytest.mark.db

INSEE = "97415"
WKT = "POLYGON((55.30 -21.00,55.302 -21.00,55.302 -21.002,55.30 -21.002,55.30 -21.00))"


@pytest.fixture
def cl(engine):
    from labuse.api.app import app
    return TestClient(app)


@pytest.fixture
def seed(engine):
    tag = uuid.uuid4().hex[:4].upper()
    ids: dict[str, int] = {}
    with session_scope() as s:
        idu = f"{INSEE}0{tag}0001"[:14].ljust(14, "0")
        s.execute(text(
            "INSERT INTO parcels (idu,commune,section,numero,geom,geom_2975,surface_m2,centroid,bbox) "
            "VALUES (:i,'Saint-Paul','ZZ','1',ST_GeomFromText(:w,4326),ST_Transform(ST_GeomFromText(:w,4326),2975),"
            "500,ST_Centroid(ST_GeomFromText(:w,4326)),ST_Envelope(ST_GeomFromText(:w,4326)))"),
            {"i": idu, "w": WKT})

        def bien(commune, typ, statut, niv, prix, idu_val, valide, sh=90, st=None):
            bid = s.execute(text(
                "INSERT INTO pige_biens (commune,type_bien,est_copro,idu,rattachement_niveau,rattachement_confiance,statut,date_publication) "
                "VALUES (:c,:t,false,:idu,:n,:cf,:s,current_date-10) RETURNING bien_id"),
                {"c": commune, "t": typ, "idu": idu_val, "n": niv,
                 "cf": 0.9 if niv == "source" else (0.55 if niv == "estime" else None), "s": statut}).scalar()
            s.execute(text("INSERT INTO pige_annonces (bien_id,portail,url_sortante) VALUES (:b,'leboncoin',:u)"),
                      {"b": bid, "u": f"https://www.leboncoin.fr/rt-{tag}-{bid}"})
            s.execute(text("INSERT INTO pige_faits (bien_id,prix,type_bien,surface_hab,surface_terrain,particulier_pro,fraicheur_source,etiquettes,valide_at) "
                           "VALUES (:b,:p,:t,:sh,:st,'particulier','publication','{}',:va)"),
                      {"b": bid, "p": prix, "t": typ, "sh": sh, "st": st, "va": "now()" if valide else None})
            if valide:
                s.execute(text("UPDATE pige_faits SET valide_at=now() WHERE bien_id=:b"), {"b": bid})
            return bid

        ids["source"] = bien("Saint-Paul", "maison", "active", "source", 349000, idu, True)
        ids["estime"] = bien("Saint-Paul", "terrain", "active", "estime", 180000, None, True, sh=None, st=1200)
        ids["non_ratt"] = bien("Saint-Pierre", "appartement", "active", "absent", 245000, None, True)
        ids["baisse"] = bien("Saint-Paul", "maison", "en_vente_longue", "source", 300000, idu, True)
        ids["brouillon"] = bien("Saint-Paul", "maison", "active", "absent", 400000, None, False)
        ids["retire"] = bien("Le Tampon", "maison", "retiree", "absent", 220000, None, True)
        # une baisse de prix sur le bien « baisse »
        s.execute(text("INSERT INTO pige_prix_historique (bien_id,ancien_prix,nouveau_prix) VALUES (:b,320000,300000)"),
                  {"b": ids["baisse"]})
    yield ids
    with session_scope() as s:
        s.execute(text("DELETE FROM pige_biens WHERE bien_id = ANY(:ids)"), {"ids": list(ids.values())})
        s.execute(text("DELETE FROM parcels WHERE commune='Saint-Paul' AND section='ZZ'"))
        s.execute(text("DELETE FROM event_log WHERE kind='pige.signalement_client'"))
        s.execute(text("DELETE FROM pige_clics WHERE bien_id = ANY(:ids)"), {"ids": list(ids.values())})


def test_client_ne_voit_que_les_valides_et_statuts_defaut(seed):
    with session_scope() as db:
        r = client.lister(db, filtres={})
    vus = {b["bien_id"] for b in r["biens"]}
    assert seed["source"] in vus and seed["estime"] in vus and seed["non_ratt"] in vus and seed["baisse"] in vus
    assert seed["brouillon"] not in vus       # non validé → invisible pour le client
    assert seed["retire"] not in vus          # statut hors défaut


def test_carte_ne_compte_que_les_rattaches(seed):
    with session_scope() as db:
        r = client.lister(db, filtres={})
    # sur nos 4 visibles : 2 rattachés (source + baisse), 2 non (estime idu null, non_ratt)
    assert r["n_rattaches"] == 2
    src = next(b for b in r["biens"] if b["bien_id"] == seed["source"])
    assert src["coords"] is not None and src["rattachement"]["niveau"] == "source"
    nr = next(b for b in r["biens"] if b["bien_id"] == seed["non_ratt"])
    assert nr["coords"] is None and nr["rattachement"]["idu"] is None


def test_filtres_et_compteur(seed):
    with session_scope() as db:
        assert client.lister(db, filtres={"commune": "Saint-Pierre"})["n_total"] == 1
        assert client.lister(db, filtres={"type_bien": "terrain"})["n_total"] == 1
        assert client.lister(db, filtres={"rattache": "non"})["n_total"] == 2
        assert client.lister(db, filtres={"prix_min": 300000})["n_total"] == 2  # 349k + 300k
        # statut hors défaut accessible en filtre explicite
        assert client.lister(db, filtres={"statuts": ["retiree"]})["n_total"] == 1


def test_detail_avec_historique_prix(seed):
    with session_scope() as db:
        d = client.detail(db, seed["baisse"])
        assert d["baisse"] is True and len(d["historique_prix"]) == 1
        assert d["historique_prix"][0]["nouveau"] == 300000
        assert client.detail(db, seed["brouillon"]) is None      # brouillon invisible même en direct


def test_clic_sortant_logue(cl, seed):
    r = cl.post("/radar/clic", json={"bien_id": seed["non_ratt"]}).json()
    assert r["ok"] and r["clic_id"] > 0
    with session_scope() as db:
        row = db.execute(text("SELECT portail FROM pige_clics WHERE id=:i"), {"i": r["clic_id"]}).mappings().first()
        assert row["portail"] == "leboncoin"


def test_signalement_ne_change_pas_le_statut(cl, seed):
    with session_scope() as db:
        avant = db.execute(text("SELECT statut FROM pige_biens WHERE bien_id=:b"), {"b": seed["source"]}).scalar()
    r = cl.post("/radar/signaler", json={"bien_id": seed["source"], "motif": "annonce retirée"}).json()
    assert r["ok"]
    with session_scope() as db:
        apres = db.execute(text("SELECT statut FROM pige_biens WHERE bien_id=:b"), {"b": seed["source"]}).scalar()
        assert apres == avant   # anti-abus : le signalement alerte, ne retire pas
        assert db.execute(text("SELECT count(*) FROM event_log WHERE kind='pige.signalement_client'")).scalar() >= 1
