"""CIRCUIT-3 lot 3 — L'ÉCHANTILLON VÉRIFIÉ CONTRE LE PRODUCTEUR.

Le contrôle `d_echantillon` compare NOTRE table à l'attendu PRODUCTEUR stocké dans
`filtres/echantillons/<source>.json`. Tests hors réseau : logique de comparaison, écart détecté,
squelette qui skip, et présence des échantillons genuine (cadastre, ban) avec l'origine producteur.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from labuse.filtres import cadre, echantillon
from labuse.filtres.cadre import Filtre

pytestmark = pytest.mark.db


def test_compare_numerique_et_texte():
    assert echantillon._compare(745, 745, None, None)
    assert echantillon._compare(742, 745, 2.0, None)        # 0,4 % < 2 %
    assert not echantillon._compare(114, 168, 10.0, None)    # 32 % > 10 %
    assert echantillon._compare(150, 168, None, 20)          # écart 18 ≤ tol_abs 20
    assert echantillon._compare("Saint-Denis", "saint-denis ", None, None)  # casse/espace
    assert not echantillon._compare(None, 5, None, None)


def test_echantillon_detecte_ecart(db_session, tmp_path, monkeypatch):
    # table témoin : une valeur conforme au producteur, une divergente
    db_session.execute(text("DROP TABLE IF EXISTS _c3_ech"))
    db_session.execute(text("CREATE TABLE _c3_ech (idu varchar, surface_m2 double precision)"))
    db_session.execute(text("INSERT INTO _c3_ech VALUES ('P1', 745), ('P2', 114)"))
    db_session.commit()
    # échantillon producteur : P1 attendu 745 (OK), P2 attendu 168 (ÉCART, notre 114)
    doc = {"source": "_c3_ech", "producteur": "TEST", "table": "_c3_ech", "cle_colonne": "idu",
           "lu_le": "2026-09-06", "lignes": [
               {"cle": "P1", "colonne": "surface_m2", "attendu": 745, "tolerance_pct": 2.0,
                "origine": {"url": "http://producteur/P1", "champ": "contenance"}},
               {"cle": "P2", "colonne": "surface_m2", "attendu": 168, "tolerance_pct": 10.0,
                "origine": {"url": "http://producteur/P2", "champ": "contenance"}}]}
    # rediriger le répertoire des échantillons vers tmp_path
    monkeypatch.setattr(echantillon, "_DIR", tmp_path)
    (tmp_path / "_c3_ech.json").write_text(json.dumps(doc))
    f = Filtre(source="_c3_ech", libelle="ech", table="_c3_ech", propres=[echantillon.controle()])
    v = cadre.jouer(db_session, f, version="t1")
    db_session.commit()
    r = {x["controle"]: x for x in v.resultats}["d_echantillon"]
    assert r["verdict"] == "ko"
    assert r["details"]["n_ecarts"] == 1
    ec = r["details"]["ecarts"][0]
    assert ec["cle"] == "P2" and ec["notre_valeur"] == "114.0" and ec["attendu_producteur"] == 168
    assert ec["origine"]["url"] == "http://producteur/P2"
    db_session.execute(text("DROP TABLE IF EXISTS _c3_ech"))
    db_session.commit()


def test_squelette_sans_lignes_skip(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(echantillon, "_DIR", tmp_path)
    (tmp_path / "_c3_vide.json").write_text(json.dumps(
        {"source": "_c3_vide", "table": "x", "cle_colonne": "y", "a_valider": True, "lignes": []}))
    f = Filtre(source="_c3_vide", libelle="v", propres=[echantillon.controle()])
    v = cadre.jouer(db_session, f, version="t1")
    db_session.commit()
    r = {x["controle"]: x for x in v.resultats}["d_echantillon"]
    assert r["verdict"] == "skip"


def test_echantillons_genuine_ont_origine_producteur():
    """Cadastre et BAN portent des lignes AVEC une origine producteur (URL + champ) — jamais nos tables."""
    for src, champ in (("cadastre_etalab", "contenance"), ("ban", "citycode")):
        doc = echantillon.charger(src)
        assert doc and doc["lignes"], f"{src} sans lignes"
        assert len(doc["lignes"]) >= 20
        for ligne in doc["lignes"]:
            o = ligne.get("origine") or {}
            assert o.get("url", "").startswith("http"), f"{src} : origine sans URL producteur"
            assert champ in (o.get("champ", "") + o.get("url", ""))


def test_tout_le_lot2_a_un_fichier_echantillon():
    """Les 20 sources qui pèsent ont un fichier échantillon (genuine ou squelette à valider)."""
    lot2 = ["dvf", "gpu_plu", "cadastre_etalab", "sitadel", "dgfip_parcelles_pm", "dpe",
            "georisques_mvt", "sirene_etablissements", "bodacc", "inpi_rne", "ban", "cosia",
            "flair", "lidar_hd", "edf", "osm_overpass", "osm_transport", "gtfs_pan", "bpe_insee",
            "filosofi", "trafic_rn"]
    manquants = [s for s in lot2 if not echantillon.chemin(s).exists()]
    assert manquants == [], f"sources sans fichier échantillon : {manquants}"
