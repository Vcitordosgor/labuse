"""RADAR-DEPOT-2 — recette du dépôt double-variante (D1), de la page d'annonce (D2), du périmètre
admin de l'Instruire (D3), du badge « sous le marché » (D4) et de la collecte totale filtrée (D5).

Échantillons : `qa/radar-html/ECH-2-varianteB.html` (page de résultats servie en variante B, sans
searchData → DOM seul) et `qa/radar-terrains/T-*.html` (pages d'annonce individuelles). [RADAR-TEST]
purgés en fin de chaque test.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import html_ingest, html_next

pytestmark = pytest.mark.db

_QA = Path(__file__).resolve().parents[1] / "qa"
_ECH_A = _QA / "radar-html" / "ECH-1.html"
_ECH_B = _QA / "radar-html" / "ECH-2-varianteB.html"
_T_POSSESSION = _QA / "radar-terrains" / "T-possession.html"
_T_SAINTEMARIE = _QA / "radar-terrains" / "T-saintemarie.html"
_T_CAMELIAS = _QA / "radar-terrains" / "T-camelias.html"


@pytest.fixture
def depots_prive(tmp_path, monkeypatch):
    monkeypatch.setenv("LABUSE_PIGE_DEPOTS_DIR", str(tmp_path / "depots"))
    monkeypatch.setenv("LABUSE_PIGE_CAPTURES_DIR", str(tmp_path / "captures"))


def _ids(html: str) -> list[int]:
    return [r["list_id"] for r in html_next.analyser(html)["records"]]


def _purger(*htmls: str):
    ids: list[int] = []
    for h in htmls:
        ids += _ids(h)
    with session_scope() as db:
        db.execute(text("DELETE FROM pige_biens WHERE bien_id IN "
                        "(SELECT bien_id FROM pige_annonces WHERE list_id = ANY(:i))"), {"i": ids})
        db.execute(text("DELETE FROM event_log WHERE dedup LIKE 'pige:%'"))
        db.commit()


# ════════════════════════ D1 — parseur double variante ════════════════════════

def test_d1_variante_a_reconnue_sans_regression():
    """VARIANTE A (ECH-1) : le dispatcher rend 35 annonces RICHES — aucune régression du chemin historique."""
    r = html_next.analyser(_ECH_A.read_text(encoding="utf-8"))
    assert r["mode"] == "resultats" and r["provenance"] == html_next.PROV_RICHE
    assert len(r["records"]) == 35 and all(x["provenance"] == html_next.PROV_RICHE for x in r["records"])


def test_d1_variante_b_reconnue_degradee():
    """VARIANTE B (ECH-2) : searchData absent → 40 vignettes DOM, toutes DÉGRADÉES, sans position."""
    r = html_next.analyser(_ECH_B.read_text(encoding="utf-8"))
    assert r["mode"] == "resultats" and r["provenance"] == html_next.PROV_DEGRADE
    recs = r["records"]
    assert len(recs) == 40
    assert all(x["provenance"] == html_next.PROV_DEGRADE for x in recs)
    assert all(x["lat"] is None and x["lng"] is None for x in recs)          # pas de position
    assert all(x["first_publication_date"] is None for x in recs)            # date vignette = remontée, jetée
    assert all(x["list_id"] and x["commune"] and x["url"] for x in recs)     # le minimum récupérable est là


def test_d1_echec_bruyant_nomme_les_trois_chemins():
    """Aucune structure reconnue → NextDataError qui NOMME variante A, page d'annonce et variante B
    (jamais « réseau ou serveur »)."""
    with pytest.raises(html_next.NextDataError) as exc:
        html_next.analyser('<script id="__NEXT_DATA__">{"props":{"pageProps":{"messages":{}}}}</script>')
    m = str(exc.value).lower()
    assert "variante a" in m and "variante b" in m and "annonce" in m


def test_d1_ingestion_b_degradee_non_rattachee(depots_prive):
    """Dépôt B end-to-end : biens DÉGRADÉS, tous non_rattachés (aucune tentative), date_publication NULL
    (première vue = date du dépôt), aucun bien à qualifier inventé sur des champs absents."""
    html = _ECH_B.read_text(encoding="utf-8")
    _purger(html)
    with session_scope() as db:
        rep = html_ingest.ingester(db, html, "ECH-2-varianteB.html")
    assert rep["nb_annonces"] == 40 and rep["nb_nouvelles"] == 40
    assert rep["provenance"] == html_next.PROV_DEGRADE
    ids = _ids(html)
    with session_scope() as db:
        rows = db.execute(text(
            "SELECT b.rattachement_etat, b.date_publication, f.provenance "
            "FROM pige_biens b JOIN pige_annonces a ON a.bien_id = b.bien_id "
            "JOIN pige_faits f ON f.bien_id = b.bien_id WHERE a.list_id = ANY(:i)"),
            {"i": ids}).mappings().all()
    assert rows and all(r["rattachement_etat"] == "non_rattachee" for r in rows)
    assert all(r["date_publication"] is None for r in rows)
    assert all(r["provenance"] == html_next.PROV_DEGRADE for r in rows)
    _purger(html)


def test_d1_enrichissement_b_puis_a(depots_prive):
    """ENRICHISSEMENT B→A : un list_id vu d'abord en DÉGRADÉ, puis en RICHE, se remplit et passe riche ;
    un RE-passage en B ensuite n'efface AUCUNE donnée riche (combler seulement)."""
    a = html_next.analyser(_ECH_A.read_text(encoding="utf-8"))["records"]
    # on choisit un list_id présent dans les deux dépôts (mesuré : au moins un chevauchement A∩B).
    ids_b = set(_ids(_ECH_B.read_text(encoding="utf-8")))
    recA = next(r for r in a if r["list_id"] in ids_b)
    lid = recA["list_id"]
    # jumeau DÉGRADÉ du même list_id, avec un prix bidon et sans surfaces (le riche devra l'emporter).
    degr = {**{k: None for k in recA}, "provenance": html_next.PROV_DEGRADE, "list_id": lid,
            "url": recA["url"], "subject": recA["subject"], "type": recA["type"],
            "commune": recA["commune"], "prix": 999_999, "brut": {}, "piscine": False,
            "owner_type": "particulier", "baisse_badge": False}
    with session_scope() as db:
        db.execute(text("DELETE FROM pige_biens WHERE bien_id IN "
                        "(SELECT bien_id FROM pige_annonces WHERE list_id = :l)"), {"l": lid})
        db.commit()
    with session_scope() as db:                                  # 1) vu en B seul → dégradé
        html_ingest._ingester_annonce(db, degr); db.commit()
    with session_scope() as db:                                  # 2) dépôt A → enrichissement
        html_ingest._ingester_annonce(db, recA); db.commit()
    with session_scope() as db:
        r = db.execute(text("SELECT f.provenance, f.prix FROM pige_faits f "
                            "JOIN pige_annonces a ON a.bien_id = f.bien_id WHERE a.list_id = :l"),
                       {"l": lid}).mappings().first()
    assert r["provenance"] == html_next.PROV_RICHE and r["prix"] == recA["prix"]   # riche a rempli
    with session_scope() as db:                                  # 3) re-passage B → n'efface rien
        html_ingest._ingester_annonce(db, degr); db.commit()
    with session_scope() as db:
        r = db.execute(text("SELECT f.provenance, f.prix FROM pige_faits f "
                            "JOIN pige_annonces a ON a.bien_id = f.bien_id WHERE a.list_id = :l"),
                       {"l": lid}).mappings().first()
    assert r["provenance"] == html_next.PROV_RICHE and r["prix"] == recA["prix"]   # riche préservé (≠ 999999)
    with session_scope() as db:
        db.execute(text("DELETE FROM pige_biens WHERE bien_id IN "
                        "(SELECT bien_id FROM pige_annonces WHERE list_id = :l)"), {"l": lid})
        db.execute(text("DELETE FROM event_log WHERE dedup LIKE 'pige:%'"))
        db.commit()


# ════════════════════════ D2 — page d'annonce = enrichissement ════════════════════════

def test_d2_page_annonce_zone_plu_et_drapeaux(depots_prive):
    """Page d'annonce T-possession : zone UBc DÉCLARÉE extraite, affichée « déclaré dans l'annonce » ;
    T-saintemarie : zone UD + drapeaux à rénover / à démolir. Aucun texte d'annonce stocké."""
    hp = _T_POSSESSION.read_text(encoding="utf-8")
    hs = _T_SAINTEMARIE.read_text(encoding="utf-8")
    _purger(hp, hs)
    with session_scope() as db:
        rp = html_ingest.ingester(db, hp, "T-possession.html")
        rs = html_ingest.ingester(db, hs, "T-saintemarie.html")
    assert rp["mode"] == "annonce" and rs["mode"] == "annonce"
    lid_p = _ids(hp)[0]
    lid_s = _ids(hs)[0]
    with session_scope() as db:
        dp = db.execute(text("SELECT f.declaratif FROM pige_faits f JOIN pige_annonces a "
                             "ON a.bien_id = f.bien_id WHERE a.list_id = :l"), {"l": lid_p}).scalar()
        ds = db.execute(text("SELECT f.declaratif FROM pige_faits f JOIN pige_annonces a "
                             "ON a.bien_id = f.bien_id WHERE a.list_id = :l"), {"l": lid_s}).scalar()
    assert dp["zone_plu"] == ["UBc"]
    assert ds["zone_plu"] == ["UD"]
    assert ds["drapeaux"]["a_renover"] is True and ds["drapeaux"]["a_demolir"] is True
    _purger(hp, hs)


def test_d2_similaires_ignorees(depots_prive):
    """La page d'annonce ne traite QUE `pageProps.ad` — les annonces « similaires » du même JSON
    (présentes dans le DOM et le JSON) ne sont PAS ingérées (piège mesuré le 29/08)."""
    hp = _T_POSSESSION.read_text(encoding="utf-8")
    _purger(hp)
    with session_scope() as db:
        rep = html_ingest.ingester(db, hp, "T-possession.html")
    assert rep["nb_annonces"] == 1                              # UN seul bien, jamais les similaires
    _purger(hp)


def test_d2_enrichit_un_bien_deja_vu_en_liste(depots_prive):
    """Si le list_id de la page d'annonce est déjà connu (vu en liste), la page ENRICHIT le bien
    existant (ajoute le déclaratif) au lieu d'en créer un second."""
    hp = _T_POSSESSION.read_text(encoding="utf-8")
    lid = _ids(hp)[0]
    recA = html_next.analyser(hp)["records"][0]
    # on simule d'abord une vue « liste » (sans déclaratif), puis la page d'annonce.
    liste = {k: v for k, v in recA.items() if k != "declaratif"}
    _purger(hp)
    with session_scope() as db:
        html_ingest._ingester_annonce(db, liste); db.commit()
    with session_scope() as db:
        n1 = db.execute(text("SELECT count(*) FROM pige_annonces WHERE list_id = :l"), {"l": lid}).scalar()
        html_ingest.ingester(db, hp, "T-possession.html")
    with session_scope() as db:
        n2 = db.execute(text("SELECT count(*) FROM pige_annonces WHERE list_id = :l"), {"l": lid}).scalar()
        decl = db.execute(text("SELECT f.declaratif FROM pige_faits f JOIN pige_annonces a "
                               "ON a.bien_id = f.bien_id WHERE a.list_id = :l"), {"l": lid}).scalar()
    assert n1 == 1 and n2 == 1                                  # enrichi, jamais dédoublé
    assert decl and decl["zone_plu"] == ["UBc"]
    _purger(hp)


# ════════════════════════ D3 — Instruire : ADMIN seulement ════════════════════════

@pytest.fixture
def client_http(engine):
    from fastapi.testclient import TestClient
    from labuse.api.app import app
    return TestClient(app)


def test_d3_instruire_est_admin_only(client_http, monkeypatch):
    """D3 — l'Instruire, le rattachement humain et l'ortho sont sous la garde ADMIN (endpoints /admin/…) :
    si la garde refuse, ils refusent (un rattachement client erroné serait un faux fait servi à tous)."""
    from fastapi import HTTPException

    def _refuse(request):
        raise HTTPException(status_code=403, detail="admin requis")
    monkeypatch.setattr("labuse.api.auth.exiger_admin", _refuse)
    assert client_http.post("/admin/radar/instruire", json={"bien_id": 1}).status_code == 403
    assert client_http.post("/admin/radar/rattacher-humain",
                            json={"bien_id": 1, "idu": "X"}).status_code == 403
    assert client_http.get("/admin/radar/ortho/ABC").status_code == 403
    # l'ancien chemin CLIENT n'existe plus (le client ne rattache jamais).
    assert client_http.post("/radar/instruire", json={"bien_id": 1}).status_code == 404
    assert client_http.post("/radar/rattacher-humain", json={"bien_id": 1, "idu": "X"}).status_code == 404


# ════════════════════════ D4 — badge « sous le marché » ════════════════════════

def test_d4_badge_seuil():
    """Le badge n'est vrai que SOUS le seuil ; l'écart exact est toujours porté ; surface manquante → pas
    de badge ; échantillon de référence < 5 → non calculable (jamais un badge sur une base fragile)."""
    from labuse.pige import signaux
    ref = {"eur_m2": 455.0, "n": 10, "perimetre": "terrain nu", "millesime": 2023}
    # RADAR-VEILLE-1 — nouvelle signature _badge(prix, type_bien, surface_hab, surface_terrain, ref,
    # terrain_ref). Ici un TERRAIN : la garde « biais terrain » (maisons) ne s'applique pas → seuil inchangé.
    def _b(prix, st, terrain_ref=None):
        return signaux._badge(prix, "terrain", None, st, ref, terrain_ref)
    # −20 % → sous le marché ; l'écart exact est présent quel que soit le verdict.
    sous = _b(364_000, 1000)   # 364 €/m² vs 455 → −20 %
    assert sous["calculable"] and sous["sous_le_marche"] is True and sous["ecart_pct"] == -20.0
    # −10 % → au-dessus du seuil (−15 %) : PAS le badge, mais l'écart reste affiché.
    limite = _b(410_000, 1000)  # 410 €/m² vs 455 → −9.9 %
    assert limite["calculable"] and limite["sous_le_marche"] is False and limite["ecart_pct"] < 0
    # surface manquante → pas de €/m² → pas de badge du tout.
    assert _b(364_000, None) is None
    # référentiel sous le seuil statistique → non calculable (jamais un badge sur < 5).
    faible = signaux._badge(364_000, "terrain", None, 1000, {"eur_m2": 455.0, "n": 3}, None)
    assert faible["calculable"] is False


def test_d4_distribution_ecarts_ne_leve_pas(depots_prive):
    """D4 — `distribution_ecarts` (justification / retune du seuil) tourne sans lever et rend les clés
    attendues (percentiles + seuil retenu + n sous le marché)."""
    from labuse.pige import signaux
    html = _ECH_A.read_text(encoding="utf-8")
    _purger(html)
    with session_scope() as db:
        html_ingest.ingester(db, html, "ECH-1.html")
        d = signaux.distribution_ecarts(db)
    assert set(d) >= {"n", "seuil_retenu_pct", "p10", "median", "p90", "n_sous_le_marche"}
    assert d["seuil_retenu_pct"] == signaux.SEUIL_SOUS_MARCHE_PCT
    _purger(html)


def test_d4_jamais_de_badge_sur_a_qualifier(depots_prive):
    """D4 — un bien À QUALIFIER (prix suspect par définition) ne porte JAMAIS de badge « sous le marché »."""
    from labuse.pige import client
    html = _ECH_A.read_text(encoding="utf-8")
    _purger(html)
    with session_scope() as db:
        html_ingest.ingester(db, html, "ECH-1.html")
        rep = client.lister(db, filtres={"a_qualifier": "oui"}, taille=200)
    assert rep["biens"]
    assert all(b["sous_le_marche"] is None for b in rep["biens"] if b["a_qualifier"])
    _purger(html)


# ════════════════════════ D5 — collecte totale, service filtré ════════════════════════

def test_d5_copros_embasees_mais_non_servies(depots_prive):
    """D5 — ECH-1 (35 annonces, 18 appartements) : le flux CLIENT montre 17 biens (copros exclues),
    la base en contient 35, et l'écart demandé/acté DIT son périmètre bâti (maisons + appartements)."""
    from labuse.pige import client, signaux
    html = _ECH_A.read_text(encoding="utf-8")
    _purger(html)
    ids = _ids(html)
    with session_scope() as db:
        html_ingest.ingester(db, html, "ECH-1.html")
        rep = client.lister(db, filtres={}, taille=200)
        n_base = db.execute(text("SELECT count(*) FROM pige_annonces WHERE list_id = ANY(:i)"),
                            {"i": ids}).scalar()
        n_copro = db.execute(text(
            "SELECT count(*) FROM pige_biens b JOIN pige_annonces a ON a.bien_id = b.bien_id "
            "WHERE a.list_id = ANY(:i) AND b.est_copro = true"), {"i": ids}).scalar()
        # l'écart demandé/acté retrouve son périmètre bâti complet (les copros comptent ici).
        eda = signaux.ecart_demande_acte(db, "Saint-Denis")
    assert n_base == 35 and n_copro == 18
    assert rep["n_total"] == 35 - 18                          # 17 servis au client (copros exclues)
    assert all(not b["est_copro"] for b in rep["biens"])      # aucune copro dans le flux
    assert eda["perimetre_bati"] == "maisons + appartements"  # le chiffre DIT son périmètre
    _purger(html)
