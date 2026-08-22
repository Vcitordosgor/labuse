"""PAU-CoSIA — la déduplication est DANS LE GESTE (jamais un bâtiment compté deux fois).

build_pau clusterise BD TOPO ∪ CoSIA. Les footprints CoSIA qui recouvrent un bâti BD TOPO
(les DOUBLONS = mêmes bâtiments vus par les deux sources) sont exclus AVANT le clustering.
Ce test le prouve end-to-end sur une commune fictive : 3 BD TOPO + 4 CoSIA dont 2 recouvrent
un BD TOPO → seuls 3 + 2 = 5 footprints entrent (les 2 partagés retirés), jamais 7.

Sur les données réelles (Saint-Philippe), la même règle retire 2 397 footprints CoSIA
partagés (mesuré) — cf. docs/mandats/PAU_COSIA_PHASE2.md.
"""
from __future__ import annotations

from sqlalchemy import text

from labuse import rnu

_COM = "TestCosiaVille"


def _carre(lon: float, lat: float, d: float = 0.00004) -> str:
    return (f"POLYGON(({lon} {lat}, {lon + d} {lat}, {lon + d} {lat + d}, "
            f"{lon} {lat + d}, {lon} {lat}))")


def _bati(session, kind: str, wkt: str) -> None:
    session.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, commune, geom) "
        "VALUES (:k, 'test', 'b', :c, ST_GeomFromText(:w, 4326))"),
        {"k": kind, "c": _COM, "w": wkt})


def test_dedup_dans_le_geste(db_session, monkeypatch):
    # commune fictive + params permissifs (le clustering n'est pas l'objet du test : la dédup l'est)
    monkeypatch.setattr(rnu, "_entries", lambda: {"97999": {"nom": _COM}})
    monkeypatch.setattr(rnu, "pau_params", lambda: {
        "eps_m": 1000.0, "min_batiments": 2, "buffer_m": 40.0, "critere": "centre"})
    db_session.execute(text("DELETE FROM spatial_layers WHERE commune = :c"), {"c": _COM})

    # 3 bâtiments BD TOPO, alignés (< 1 km → un noyau)
    b = [(55.5000, -21.0000), (55.5001, -21.0000), (55.5002, -21.0000)]
    for lon, lat in b:
        _bati(db_session, "batiment", _carre(lon, lat))
    # 4 CoSIA : 2 recouvrent B1/B2 (DOUBLONS), 2 nouveaux disjoints (dans l'eps)
    _bati(db_session, "batiment_cosia", _carre(55.5000, -21.0000))   # recouvre B1 → exclu
    _bati(db_session, "batiment_cosia", _carre(55.5001, -21.0000))   # recouvre B2 → exclu
    _bati(db_session, "batiment_cosia", _carre(55.5003, -21.0000))   # nouveau → gardé
    _bati(db_session, "batiment_cosia", _carre(55.5004, -21.0000))   # nouveau → gardé
    db_session.flush()

    r = rnu.build_pau(db_session, commit=False)
    com = r["communes"]["97999"]
    # 3 BD TOPO + 2 CoSIA nouveaux = 5 ; JAMAIS 7 (les 2 partagés ne comptent pas deux fois)
    assert com["calculee"] is True
    assert com["n_batiments"] == 5, f"attendu 5 (dédup), obtenu {com['n_batiments']}"

    # contrôle négatif : sans dédup, l'union brute compterait 7
    brut = db_session.execute(text(
        "SELECT count(*) FROM spatial_layers WHERE commune = :c "
        "AND kind IN ('batiment','batiment_cosia')"), {"c": _COM}).scalar()
    assert brut == 7, "le fixture doit contenir 7 footprints (3 BD TOPO + 4 CoSIA)"

    db_session.execute(text("DELETE FROM spatial_layers WHERE commune = :c"), {"c": _COM})


def test_sans_cosia_comportement_bd_topo_seul(db_session, monkeypatch):
    """Si la couche CoSIA est absente/vide, l'union se réduit à BD TOPO (aucune régression)."""
    monkeypatch.setattr(rnu, "_entries", lambda: {"97999": {"nom": _COM}})
    monkeypatch.setattr(rnu, "pau_params", lambda: {
        "eps_m": 1000.0, "min_batiments": 2, "buffer_m": 40.0, "critere": "centre"})
    db_session.execute(text("DELETE FROM spatial_layers WHERE commune = :c"), {"c": _COM})
    for lon in (55.5000, 55.5001, 55.5002):
        _bati(db_session, "batiment", _carre(lon, -21.0000))
    db_session.flush()
    r = rnu.build_pau(db_session, commit=False)
    assert r["communes"]["97999"]["n_batiments"] == 3   # BD TOPO seul, inchangé
    db_session.execute(text("DELETE FROM spatial_layers WHERE commune = :c"), {"c": _COM})


def test_avertissement_pau_reste_affiche():
    """La PAU gagne en qualité (CoSIA) mais reste ESTIMÉ — la nature ne change pas."""
    b = rnu.rnu_block("97417000AC0003")
    assert b is not None
    assert b["avertissement_pau"] == rnu.AVERTISSEMENT_PAU
    assert "estimée par LABUSE" in b["avertissement_pau"]
