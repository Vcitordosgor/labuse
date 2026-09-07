"""OUTILS-MUSCLER-2 — gardes de l'endpoint /moteurs/histoire/{idu} (la frise des faits).

Doctrine (mandat B) : des FAITS datés, jamais un récit ; chaque fait porte sa source et la
MAILLE RÉELLE de sa date (jour / année / millésime — une année seule s'affiche « 2024 »,
jamais « 01/01/2024 ») ; parcelle sans fait = réponse vide explicite, pas une erreur.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.db

_SQ = "POLYGON((55.70 -21.30,55.7003 -21.30,55.7003 -21.2997,55.70 -21.2997,55.70 -21.30))"


def _p(db, idu, commune="Frisville"):
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, surface_m2, centroid, bbox, geom_2975) VALUES "
        "(:i,:c,'S','1', ST_GeomFromText(:w,4326), 500, ST_Centroid(ST_GeomFromText(:w,4326)), "
        " ST_Envelope(ST_GeomFromText(:w,4326)), ST_Transform(ST_GeomFromText(:w,4326),2975)) RETURNING id"),
        {"i": idu, "c": commune, "w": _SQ}).scalar()


def _vente(db, idu, id_mut, date, val, bati=None, terrain=None, type_local=None):
    db.execute(text(
        "INSERT INTO dvf_mutations_parcelle (id_mutation, date_mutation, nature_mutation, valeur_fonciere, "
        "id_parcelle, type_local, surface_reelle_bati, surface_terrain, millesime) "
        "VALUES (:m, :d, 'Vente', :v, :i, :t, :b, :s, 2025)"),
        {"m": id_mut, "d": date, "v": val, "i": idu, "t": type_local, "b": bati, "s": terrain})


def _permis(db, idu, pid, d_auto, d_depot=None, daact=None, nb_lgt=None):
    db.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, date_depot, idu_codes, commune, raw) "
        "VALUES (:p, 'PC', :da, :dd, to_jsonb(ARRAY[CAST(:i AS text)]), 'Frisville', "
        "        jsonb_build_object('daact', CAST(:daact AS text), 'nb_lgt', CAST(:lgt AS text), "
        "                           'surf_hab', NULL, 'etat', '2', 'destination', NULL, 'src', 'test'))"),
        {"p": pid, "da": d_auto, "dd": d_depot, "i": idu, "daact": daact, "lgt": nb_lgt})


def _pm_millesime(db, idu, millesime, siren, denomination):
    db.execute(text(
        "INSERT INTO pm_proprietaires_millesimes (millesime, idu, siren, denomination) "
        "VALUES (:m, :i, :s, :d)"), {"m": millesime, "i": idu, "s": siren, "d": denomination})


def _dfi(db, mere, fille, date, nature="document d’arpentage"):
    # Table non-ORM (aucun lecteur avant la frise) : créée à blanc dans la transaction du test,
    # même schéma que la base réelle — rollback-ée par la fixture.
    db.execute(text(
        "CREATE TABLE IF NOT EXISTS dfi_filiation (id int GENERATED ALWAYS AS IDENTITY, "
        "insee varchar(5) NOT NULL, identifiant_dfi varchar(12) NOT NULL, nature varchar(64), "
        "date_validation date, idu_mere varchar(14) NOT NULL, idu_fille varchar(14) NOT NULL)"))
    db.execute(text(
        "INSERT INTO dfi_filiation (insee, identifiant_dfi, nature, date_validation, idu_mere, idu_fille) "
        "VALUES ('97499', 'DFI-TEST', :n, :d, :m, :f)"),
        {"n": nature, "d": date, "m": mere, "f": fille})


def test_histoire_familles_mailles_et_tri(db_session):
    """Les 4 familles servies, chacune à sa maille réelle, tri du plus récent au plus ancien ;
    chaque fait porte sa source nommée. Aucun tier/score (l'analyse n'a pas été demandée)."""
    from labuse.api.moteurs import histoire_parcelle
    _p(db_session, "HIST0001")
    _vente(db_session, "HIST0001", "M-1", "2023-05-12", 250000, bati=90, type_local="Maison")
    _permis(db_session, "HIST0001", "PC974TEST1", "2021-06-10", d_depot="2021-01-01", nb_lgt="3")
    _pm_millesime(db_session, "HIST0001", 2022, "111222333", "SCI AVANT")
    _pm_millesime(db_session, "HIST0001", 2023, "444555666", "SCI APRES")
    _dfi(db_session, "97499000ZZ0001", "HIST0001", "2019-03-04")
    out = histoire_parcelle("HIST0001", db_session)
    familles = [f["famille"] for f in out["faits"]]
    assert familles == ["vente", "proprietaire", "permis", "permis", "decoupe"]  # tri décroissant
    par_fam = {f["famille"]: f for f in out["faits"]}
    # maille jour (vente, découpe, autorisation) / année (dépôt 01/01) / millésime (propriétaire)
    assert par_fam["vente"]["maille"] == "jour" and par_fam["vente"]["date"] == "2023-05-12"
    assert par_fam["decoupe"]["maille"] == "jour" and par_fam["decoupe"]["annee"] == 2019
    depot = next(f for f in out["faits"] if f["famille"] == "permis" and "déposé" in f["libelle"])
    assert depot["maille"] == "annee" and depot["date"] == "2021"          # jamais « 01/01/2021 »
    auto = next(f for f in out["faits"] if f["famille"] == "permis" and "autorisé" in f["libelle"])
    assert auto["maille"] == "jour" and auto["date"] == "2021-06-10"
    prop = par_fam["proprietaire"]
    assert prop["maille"] == "millesime" and prop["date"] is None
    assert (prop["de_millesime"], prop["a_millesime"]) == (2022, 2023)
    assert prop["apres"]["denomination"] == "SCI APRES"                     # PM nommée (jamais un particulier)
    for f in out["faits"]:
        assert f["source"] and f["annee"]                                   # tout fait sourcé et posable
        assert "tier_v2" not in f and "score" not in f
    # B2 : des faits, pas un récit — aucune clé d'interprétation.
    assert not any("interpretation" in f or "recit" in f for f in out["faits"])


def test_histoire_vide_honnete(db_session):
    """Parcelle sans aucun fait : réponse vide EXPLICITE (n=0, faits=[]), les millésimes des
    sources voyagent quand même (bandeau C6) — jamais une erreur."""
    from labuse.api.moteurs import histoire_parcelle
    _p(db_session, "HIST0010")
    out = histoire_parcelle("HIST0010", db_session)
    assert out["n"] == 0 and out["faits"] == []
    assert {s["cle"] for s in out["sources"]} == {"dvf", "sitadel", "ff", "dfi"}


def test_histoire_dedup_mutation_multilignes(db_session):
    """Une vente multi-lignes DVF (Maison + Dépendance, même id_mutation) = UN SEUL fait,
    porté par le local principal (idiome FIX-4/B3)."""
    from labuse.api.moteurs import histoire_parcelle
    _p(db_session, "HIST0020")
    _vente(db_session, "HIST0020", "M-20", "2022-09-01", 300000, bati=120, type_local="Maison")
    _vente(db_session, "HIST0020", "M-20", "2022-09-01", 300000, bati=15, type_local="Dépendance")
    out = histoire_parcelle("HIST0020", db_session)
    ventes = [f for f in out["faits"] if f["famille"] == "vente"]
    assert len(ventes) == 1 and "Maison" in ventes[0]["libelle"]


def test_histoire_decoupe_groupee(db_session):
    """Un même acte (date + nature) liant plusieurs parcelles = UN fait, total dit
    (n_parcelles_liees), liste bornée au cap — rien de masqué en silence."""
    from labuse.api.moteurs import histoire_parcelle
    _p(db_session, "HIST0030")
    for k in range(3):
        _dfi(db_session, "HIST0030", f"97499000FL{k:04d}", "2020-11-20", nature="lotissement")
    out = histoire_parcelle("HIST0030", db_session)
    dec = [f for f in out["faits"] if f["famille"] == "decoupe"]
    assert len(dec) == 1
    assert dec[0]["n_parcelles_liees"] == 3 and len(dec[0]["parcelles_liees"]) == 3
    assert "origine" in dec[0]["libelle"]                                   # sens mère (elle a produit)
    assert out["cap_filiation"] >= 3


def test_histoire_parcelle_inconnue_404(db_session):
    from fastapi import HTTPException

    from labuse.api.moteurs import histoire_parcelle
    with pytest.raises(HTTPException) as e:
        histoire_parcelle("ZZ00000000", db_session)
    assert e.value.status_code == 404
