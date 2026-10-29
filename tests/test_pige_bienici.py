"""RADAR-SOURCES-2 — recette du traducteur Bien'ici (parseur du JSON realEstateAds).

Rejoue la fixture RÉELLE `qa/radar-bienici/ECH-BIENICI-1.json` (100 annonces de vente, La Réunion,
capturée via le navigateur comme le fera l'extension). Vérifie : le même schéma plat qu'`aplatir()`
Leboncoin, la commune résolue via l'INSEE (le champ `city` est une LOCALITÉ), les coordonnées, le
list_id stable et disjoint de Leboncoin, l'absence restée absente, l'échec bruyant, et que le dispatch
ne confond jamais un dépôt Leboncoin avec un dépôt Bien'ici.

Les tests de PARSING sont purs (aucune base). Les tests d'INGESTION / dédoublonnage portent le marqueur
`db` (base jetable `labuse_test`).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import html_ingest, html_next, portails

_ECH = Path(__file__).resolve().parents[1] / "qa" / "radar-bienici" / "ECH-BIENICI-1.json"


@pytest.fixture
def raw() -> str:
    return _ECH.read_text(encoding="utf-8")


@pytest.fixture
def recs(raw) -> list[dict]:
    return html_next.analyser(raw)["records"]


# ── parsing pur (aucune base) ───────────────────────────────────────────────

def test_dispatch_resultats_riche(raw):
    res = html_next.analyser(raw)
    assert res["mode"] == "resultats"
    assert res["provenance"] == html_next.PROV_RICHE
    assert len(res["records"]) == 100


def test_schema_identique_a_leboncoin(recs):
    # mêmes clés que la sortie d'`aplatir()` Leboncoin (le reste de la chaîne est portail-agnostique).
    lbc = html_next.aplatir({
        "list_id": 1, "url": "https://www.leboncoin.fr/x/1", "subject": "x",
        "attributes": [{"key": "real_estate_type", "value": "1"}, {"key": "square", "value": "80"}],
        "location": {"city": "Saint-Denis", "lat": -20.9, "lng": 55.4, "source": "city"},
    })
    assert set(recs[0]) >= set(lbc) - {"baisse_badge"}  # bienici ajoute baisse_badge (drapeau explicite)


def test_types_mappes(recs):
    types = {r["type"] for r in recs}
    assert types <= {"maison", "appartement", "terrain", "immeuble", None}
    # l'échantillon ne contient que maisons et appartements
    assert "maison" in types and "appartement" in types


def test_commune_resolue_via_insee(recs):
    # `city` = « Saint-Gilles les Bains » (localité) mais la commune servie est OFFICIELLE (Saint-Paul).
    r = next(r for r in recs if r["url"].endswith("immo-facile-61412190"))
    assert r["commune"] == "Saint-Paul"
    assert r["zipcode"] == "97434"
    # toutes les communes servies sont dans les 24 officielles (résolues par INSEE du quartier).
    from labuse.pige.intake import resoudre_commune
    assert all(resoudre_commune(r["commune"]) is not None for r in recs)


def test_coordonnees_presentes(recs):
    # le nerf du mandat : des coordonnées par annonce (floutage disque Bien'ici).
    assert all(r["lat"] is not None and r["lng"] is not None for r in recs)
    r = recs[0]
    assert -22 < r["lat"] < -20 and 55 < r["lng"] < 56   # La Réunion


def test_list_id_stable_et_disjoint_de_leboncoin(recs):
    ids = [r["list_id"] for r in recs]
    assert len(set(ids)) == len(ids)                      # unicité
    # espace Bien'ici au-dessus de tout list_id Leboncoin plausible (< ~10¹⁰) : jamais de fausse collision.
    assert all(i > 10 ** 11 for i in ids)
    # stable : re-parser donne les mêmes identités.
    again = html_next.analyser(_ECH.read_text(encoding="utf-8"))["records"]
    assert [r["list_id"] for r in again] == ids


def test_absence_reste_absente(recs):
    # Bien'ici ne porte ni global_condition, ni taxe foncière, ni chauffage, ni SIREN, ni nb d'étages.
    for r in recs:
        assert r["etat_bien"] is None
        assert r["taxe_fonciere"] is None
        assert r["chauffage"] is None
        assert r["owner_siren"] is None
        assert r["etages"] is None


def test_dpe_non_soumis_vierge_ignore(recs):
    # 'NS' (non soumis) / 'VI' (vierge) ne sont pas des lettres A–G → None (jamais devinés).
    assert all(r["dpe_classe"] in (None, *"ABCDEFG") for r in recs)
    assert all(r["dpe_ges"] in (None, *"ABCDEFG") for r in recs)


def test_baisse_badge_depuis_drapeau(recs):
    assert sum(1 for r in recs if r["baisse_badge"]) == 11   # priceHasDecreased mesuré sur la fixture


def test_piscine_booleen_dedie(recs):
    assert sum(1 for r in recs if r["piscine"]) == 25        # hasPool (jamais lu dans le titre)


def test_owner_pro_particulier(recs):
    assert all(r["owner_type"] in ("pro", "particulier", None) for r in recs)


def test_url_classee_bienici(recs):
    for r in recs:
        assert r["url"].startswith("https://www.bienici.com/")
        assert portails.slug_pour_url(r["url"]) == "bienici"


def test_echec_bruyant_zero_annonce():
    with pytest.raises(html_next.NextDataError):
        html_next.analyser('{"total": 0, "realEstateAds": []}')


def test_realestateads_pas_une_liste():
    with pytest.raises(html_next.NextDataError):
        html_next.analyser('{"realEstateAds": {"x": 1}}')


def test_dispatch_ne_confond_pas_leboncoin():
    # un dépôt Leboncoin (HTML __NEXT_DATA__) ne doit JAMAIS partir dans le chemin Bien'ici.
    lbc = ('<html><script id="__NEXT_DATA__">'
           '{"props":{"pageProps":{"searchData":{"ads":[{"list_id":42,'
           '"url":"https://www.leboncoin.fr/ad/ventes_immobilieres/42",'
           '"attributes":[{"key":"real_estate_type","value":"1"},{"key":"square","value":"90"}],'
           '"location":{"city":"Saint-Denis","source":"city"}}]}}}}</script></html>')
    res = html_next.analyser(lbc)
    assert res["mode"] == "resultats"
    assert res["records"][0]["list_id"] == 42
    assert portails.slug_pour_url(res["records"][0]["url"]) == "leboncoin"


def test_json_inconnu_non_bienici_echoue_bruyamment():
    # un JSON sans `realEstateAds` n'est pas Bien'ici → on retombe sur le chemin Next.js (échec bruyant).
    with pytest.raises(html_next.NextDataError):
        html_next.analyser('{"autre": 1}')


# ── ingestion / dédoublonnage (base jetable) ─────────────────────────────────

pytestmark_db = pytest.mark.db


@pytest.fixture
def depots_prive(tmp_path, monkeypatch):
    monkeypatch.setenv("LABUSE_PIGE_DEPOTS_DIR", str(tmp_path / "depots"))
    monkeypatch.setenv("LABUSE_PIGE_CAPTURES_DIR", str(tmp_path / "captures"))


@pytest.fixture
def nettoyer(recs):
    yield
    ids = [r["list_id"] for r in recs]
    with session_scope() as db:
        db.execute(text("DELETE FROM pige_biens WHERE bien_id IN "
                        "(SELECT bien_id FROM pige_annonces WHERE list_id = ANY(:i))"), {"i": ids})
        db.execute(text("DELETE FROM event_log WHERE dedup LIKE 'pige:%'"))
        db.commit()


@pytest.mark.db
def test_ingestion_idempotente(raw, recs, depots_prive, nettoyer):
    with session_scope() as db:
        r1 = html_ingest.ingester(db, raw, nom_fichier="bienici page 1", archiver=False)
    # toutes dans le périmètre des 24 communes (commune résolue via INSEE).
    assert r1["nb_hors_perimetre"] == 0
    assert r1["nb_annonces"] == 100
    with session_scope() as db:
        r2 = html_ingest.ingester(db, raw, nom_fichier="bienici page 1", archiver=False)
    # 2e dépôt du même contenu : aucune nouvelle (idempotence par list_id).
    assert r2["nb_nouvelles"] == 0


@pytest.mark.db
def test_fusion_avec_un_bien_leboncoin(recs, depots_prive):
    """Un bien déjà présent en base (côté Leboncoin) et la MÊME annonce Bien'ici (commune/type/surface/
    prix EXACTS) ne font qu'UN seul pige_biens : `_est_meme_bien` est portail-agnostique."""
    r = next(x for x in recs if x["type"] == "maison" and x["surface_hab"] and x["prix"])
    with session_scope() as db:
        # bien Leboncoin « jumeau » posé à la main, avec un list_id numérique Leboncoin.
        bien_id = db.execute(text(
            "INSERT INTO pige_biens (commune, statut, type_bien, source_position, district, last_seen_at) "
            "VALUES (:c, 'active', :t, :sp, :d, now()) RETURNING bien_id"),
            {"c": r["commune"], "t": r["type"], "sp": r["source_position"], "d": r["district"]}).scalar()
        db.execute(text(
            "INSERT INTO pige_faits (bien_id, prix, type_bien, surface_hab, surface_terrain) "
            "VALUES (:b, :p, :t, :sh, :st)"),
            {"b": bien_id, "p": r["prix"], "t": r["type"], "sh": r["surface_hab"], "st": r["surface_terrain"]})
        db.execute(text(
            "INSERT INTO pige_annonces (bien_id, portail, url_sortante, list_id) "
            "VALUES (:b, 'leboncoin', :u, :l)"),
            {"b": bien_id, "u": "https://www.leboncoin.fr/ad/ventes_immobilieres/999000111", "l": 999000111})
        db.commit()
        try:
            res = html_ingest._ingester_annonce(db, dict(r))
            assert res == "fusion"
            # une seule entité physique, deux occurrences portail.
            n_biens = db.execute(text(
                "SELECT count(*) FROM pige_annonces WHERE list_id IN (:l1, :l2)"),
                {"l1": 999000111, "l2": r["list_id"]}).scalar()
            assert n_biens == 2
            bid = db.execute(text("SELECT bien_id FROM pige_annonces WHERE list_id = :l"),
                             {"l": r["list_id"]}).scalar()
            assert bid == bien_id   # la nouvelle annonce a rejoint le bien Leboncoin le plus ancien
        finally:
            db.rollback()
            db.execute(text("DELETE FROM pige_biens WHERE bien_id = :b"), {"b": bien_id})
            db.commit()
