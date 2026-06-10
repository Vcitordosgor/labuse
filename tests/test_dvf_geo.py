"""Tests de l'agrégation geo-dvf (import DVF récent). Fonction pure, sans DB ni réseau.

Vérifie le point critique : DVF éclate une vente en plusieurs lignes portant TOUTES la
valeur totale ; on doit agréger par id_mutation et sommer la surface, sinon le €/m² des
ventes multi-lots est surévalué. Et on ne garde que des comparables exploitables."""
from labuse.ingestion.layers_ingest import _geo_dvf_aggregate


def _row(mid, type_local="Appartement", surf="50", val="200000", lon="55.3", lat="-21.0",
         nature="Vente", terr="", commune="97415", date="2023-05-01"):
    return {"id_mutation": mid, "type_local": type_local, "surface_reelle_bati": surf,
            "valeur_fonciere": val, "longitude": lon, "latitude": lat, "nature_mutation": nature,
            "surface_terrain": terr, "code_commune": commune, "date_mutation": date}


def test_mutation_multilot_agrege_et_ne_surcompte_pas():
    # une mutation = 2 appartements (40 + 60 m²) vendus ensemble pour 500 000 € au TOTAL.
    rows = [_row("M1", surf="40", val="500000"), _row("M1", surf="60", val="500000")]
    out = _geo_dvf_aggregate(rows)
    assert len(out) == 1
    m = out[0]
    assert m["sb"] == 100.0                    # surface sommée
    assert m["val"] == 500000.0                 # valeur de la mutation (pas doublée)
    # €/m² correct = 500000/100 = 5000, et NON 500000/40 ou /60
    assert abs(m["val"] / m["sb"] - 5000) < 1e-6


def test_vefa_avec_surface_conservee_et_flaggee():
    out = _geo_dvf_aggregate([_row("V1", surf="59", val="272000",
                                    nature="Vente en l'état futur d'achèvement")])
    assert len(out) == 1 and out[0]["vefa"] is True
    assert abs(out[0]["val"] / out[0]["sb"] - 272000 / 59) < 1e-6


def test_mutation_sans_surface_residentielle_ecartee():
    # terrain seul (pas de local Maison/Appartement avec surface) → pas de prix fabriqué.
    assert _geo_dvf_aggregate([_row("T1", type_local="", surf="")]) == []
    assert _geo_dvf_aggregate([_row("T2", type_local="Local industriel. commercial", surf="120")]) == []


def test_mutation_type_mixte_ecartee():
    # appart + maison dans la même vente → €/m² ambigu, on n'invente pas.
    rows = [_row("X1", type_local="Appartement", surf="50"),
            _row("X1", type_local="Maison", surf="90")]
    assert _geo_dvf_aggregate(rows) == []


def test_mutation_sans_geoloc_ecartee():
    # sans coordonnées, le moteur de rayon ne peut pas l'utiliser → écartée.
    assert _geo_dvf_aggregate([_row("G1", lon="", lat="")]) == []


def test_maison_monotype_classee_maison():
    out = _geo_dvf_aggregate([_row("H1", type_local="Maison", surf="100", val="350000", terr="600")])
    assert len(out) == 1
    assert out[0]["tl"] == "Maison" and out[0]["st"] == 600.0 and out[0]["vefa"] is False
