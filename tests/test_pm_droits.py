"""SCAN-FIX-1 (bloquant 1) — table COMPLÈTE des droits `parcelle_pm_droit` + titulaire principal.

Le loader historique jetait le code droit et gardait la 1re ligne par parcelle → un SIREN seulement
GESTIONNAIRE apparaissait « propriétaire ». Ici : la règle de priorité (propriétaire d'abord), la
ventilation par droit de l'onglet Possession, les autres titulaires de la fiche, et le compteur de
recherche cohérent avec le scan."""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

_WKT = [
    "POLYGON((55.50 -21.10,55.5003 -21.10,55.5003 -21.0997,55.50 -21.0997,55.50 -21.10))",
    "POLYGON((55.5003 -21.10,55.5006 -21.10,55.5006 -21.0997,55.5003 -21.0997,55.5003 -21.10))",
]


def test_rang_et_famille_droit():
    """La règle : propriétaire (P) l'emporte sur gestionnaire (G) ; familles propriété/gestion/autres."""
    from labuse.ingestion.pm_droits import rang_droit, famille_droit
    assert rang_droit("P") < rang_droit("G")          # propriétaire d'abord
    assert rang_droit("P") < rang_droit("B")          # propriété avant bailleur à construction
    assert rang_droit("G") == rang_droit("Z")         # Z (gestion d'un bien de l'État) = gestion
    assert famille_droit("P") == "propriete"
    assert famille_droit("N") == "propriete"
    assert famille_droit("G") == "gestion"
    assert famille_droit("S") == "gestion"            # syndic de copropriété = gestion
    assert famille_droit("B") == "autres"             # bailleur à construction = autres droits


def _ddl_droit(db):
    db.execute(text(
        "CREATE TABLE IF NOT EXISTS parcelle_pm_droit ("
        " id bigserial PRIMARY KEY, idu varchar(14) NOT NULL, siren varchar(20),"
        " denomination varchar(200), forme_juridique varchar(20), groupe smallint,"
        " groupe_label varchar(80), droit_code varchar(4), droit_label varchar(80),"
        " ordre_titulaire smallint, millesime varchar(8), source varchar(120), url_source text,"
        " date_import timestamptz NOT NULL DEFAULT now())"))


def _parcel(db, idu, wkt):
    db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'Droitville','S','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 900,"
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"), {"i": idu, "w": wkt})


def _droit(db, idu, siren, code, label, ordre, denom):
    db.execute(text(
        "INSERT INTO parcelle_pm_droit (idu, siren, denomination, groupe, droit_code, droit_label, "
        " ordre_titulaire, millesime) VALUES (:i,:s,:d,0,:c,:l,:o,'2026')"),
        {"i": idu, "s": siren, "d": denom, "c": code, "l": label, "o": ordre})


def test_possession_distingue_propriete_gestion_autres(db_session):
    """CBO est propriétaire (P) de 2 parcelles, seulement GESTIONNAIRE (G) d'une 3e (dont le vrai
    propriétaire est X) : l'onglet Possession compte 2 en propriété, 1 en gestion — PLUS « 3 possède »."""
    from labuse.api.modules import patrimoine, parcelle_titulaires
    s = db_session
    _ddl_droit(s)
    cbo, autre = "452038805", "310895172"
    _parcel(s, "97499000DR0001", _WKT[0])
    _parcel(s, "97499000DR0002", _WKT[1])
    _parcel(s, "97499000DR0003", _WKT[0])
    # 2 parcelles où CBO est propriétaire (principal)
    _droit(s, "97499000DR0001", cbo, "P", "Propriétaire", 1, "CBO TERRITORIA")
    _droit(s, "97499000DR0002", cbo, "P", "Propriétaire", 1, "CBO TERRITORIA")
    # 1 parcelle où CBO n'est que gestionnaire ; le propriétaire (principal) est X
    _droit(s, "97499000DR0003", autre, "P", "Propriétaire", 1, "SA HLM")
    _droit(s, "97499000DR0003", cbo, "G", "Gérant, mandataire, gestionnaire", 2, "CBO TERRITORIA")

    out = patrimoine(siren=cbo, limit=200, offset=0, request=None, db=s)
    pd = out["par_droit"]
    assert pd["propriete"]["recensees"] == 2        # CBO possède 2 (P)
    assert pd["gestion"]["recensees"] == 1          # CBO gère 1 (G)
    assert out["n_recensees"] == 3                  # 3 parcelles au total pour CBO
    assert out["perimetre"]["filiales_incluses"] is False
    # la liste porte le droit par parcelle (distinction DANS la liste)
    codes = {it["idu"]: it["droit_code"] for it in out["items"]}
    assert codes["97499000DR0003"] == "G"

    # fiche parcelle (écran) : la parcelle partagée a UN autre titulaire (CBO gestionnaire)
    tit = parcelle_titulaires("97499000DR0003", db=s)
    assert tit["n_autres"] == 1
    assert tit["titulaires"][0]["siren"] == cbo and tit["titulaires"][0]["droit_code"] == "G"


def test_archive_principal_depuis_droits_meme_regle(db_session):
    """SCAN-FIX-2 (M3) — l'archive d'un millésime dans pm_proprietaires_millesimes est le TITULAIRE
    PRINCIPAL calculé par la MÊME RÈGLE (ordre_titulaire=1), pas la vieille « 1re ligne ». Sur une parcelle
    où le propriétaire (P) est X et le gestionnaire (G) est Y, l'archive retient X (comme le millésime servi)
    → la chronologie Communes ne verra pas de faux changement."""
    from labuse.ingestion.pm_droits import archive_principal_depuis_droits
    s = db_session
    s.commit = lambda: None   # neutralise le commit interne → la transaction du fixture roule en arrière
    _ddl_droit(s)
    # 2024 : parcelle à 2 titulaires — X propriétaire (principal), Y gestionnaire (ordre 2).
    s.execute(text("INSERT INTO parcelle_pm_droit (idu, siren, denomination, groupe, droit_code, "
                   "droit_label, ordre_titulaire, millesime) VALUES "
                   "('97499000AR0001','111111111','SCI X',0,'P','Propriétaire',1,'2024'),"
                   "('97499000AR0001','222222222','SCI Y',0,'G','Gérant',2,'2024')"))
    archive_principal_depuis_droits(s, "2024", log=lambda *_: None)
    row = s.execute(text("SELECT siren FROM pm_proprietaires_millesimes WHERE millesime=2024 AND idu='97499000AR0001'")).all()
    assert len(row) == 1 and row[0][0] == "111111111"   # le PROPRIÉTAIRE, pas le gestionnaire


def test_blocs_filtre_siren(db_session):
    """SCAN-FIX-2 (M4) — la route blocs honore enfin `?siren=` (il était ignoré) : elle ne rend que les
    blocs du propriétaire demandé, plus toute la liste."""
    from labuse.api.modules import blocs_liste
    s = db_session
    # labuse_test peut porter un parcel_blocs ancien sans `is_public` (schéma persistant) ; la colonne
    # existe en prod/scanfix. On la garantit dans la transaction (rollback-ée) pour exercer la route.
    s.execute(text("ALTER TABLE parcel_blocs ADD COLUMN IF NOT EXISTS is_public boolean NOT NULL DEFAULT false"))
    for key, siren, n in (("452038805:a", "452038805", 5), ("310863592:b", "310863592", 3)):
        s.execute(text(
            "INSERT INTO parcel_blocs (bloc_key, siren, denomination, n_parcelles, surface_totale_m2, "
            " communes, sdp_residuelle_m2, sdp_couverture, zonages, is_public, built_at) "
            "VALUES (:k,:s,:d,:n, 1000, ARRAY['Patville'], 0, 0, ARRAY['U'], false, now())"),
            {"k": key, "s": siren, "d": f"SCI {siren}", "n": n})
    kw = dict(commune=None, surface_min=0, sdp_min=0, n_min=2, inclure_publics=True, limit=200, offset=0, db=s)
    tout = blocs_liste(siren=None, **kw)
    cbo = blocs_liste(siren="452038805", **kw)
    assert tout["total"] == 2
    assert cbo["total"] == 1 and all(it["siren"] == "452038805" for it in cbo["items"])


def test_recherche_compte_recensees_et_annonce_masques(db_session):
    """Le compteur de la recherche = le scan (parcelles recensées via parcelle_pm_droit), U… qualifié."""
    from labuse.api.modules import patrimoine_search
    s = db_session
    _ddl_droit(s)
    _parcel(s, "97499000DR0101", _WKT[0])
    _droit(s, "97499000DR0101", "988888888", "P", "Propriétaire", 1, "SCI RECHERCHE ALPHA")
    _droit(s, "97499000DR0102", "U23725630", "P", "Propriétaire", 1, "ASS FONCIERE RECHERCHE")
    out = patrimoine_search("RECHERCHE", db=s)
    noms = {r["siren"]: r for r in out["resultats"]}
    assert noms["988888888"]["n"] == 1 and noms["988888888"]["siren_reel"] is True
    assert noms["U23725630"]["siren_reel"] is False      # identifiant fiscal, pas un SIREN
    assert out["total"] == len(out["resultats"]) and out["masques"] == 0
