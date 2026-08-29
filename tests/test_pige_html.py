"""RADAR-HTML — recette du chemin d'entrée HTML (dépôt d'une page de résultats, remplace capture/vision).

Rejoue l'échantillon de référence `qa/radar-html/ECH-1.html` : 35 annonces, idempotence (2e dépôt =
0 doublon), échec BRUYANT si __NEXT_DATA__ absent/tronqué, l'annonce « terrain 1942 » part en À
QUALIFIER, une baisse de prix est historisée. [RADAR-TEST] purgés en fin.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import html_ingest, html_next

pytestmark = pytest.mark.db

_ECH = Path(__file__).resolve().parents[1] / "qa" / "radar-html" / "ECH-1.html"


@pytest.fixture
def html():
    return _ECH.read_text(encoding="utf-8")


@pytest.fixture
def depots_prive(tmp_path, monkeypatch):
    """Archive les dépôts dans un répertoire privé JETABLE (jamais le répertoire de prod)."""
    monkeypatch.setenv("LABUSE_PIGE_DEPOTS_DIR", str(tmp_path / "depots"))
    monkeypatch.setenv("LABUSE_PIGE_CAPTURES_DIR", str(tmp_path / "captures"))


def _list_ids(html: str) -> list[int]:
    return [a.get("list_id") for a in html_next.extraire_annonces(html)]


@pytest.fixture
def nettoyer(html):
    yield
    ids = _list_ids(html)
    with session_scope() as db:
        db.execute(text("DELETE FROM pige_biens WHERE bien_id IN "
                        "(SELECT bien_id FROM pige_annonces WHERE list_id = ANY(:i))"), {"i": ids})
        db.execute(text("DELETE FROM event_log WHERE dedup LIKE 'pige:depot:%' OR dedup LIKE 'pige:aq:%'"))
        db.commit()


# ── parsing pur ──

def test_parse_35_annonces(html):
    assert len(html_next.extraire_annonces(html)) == 35


def test_echec_bruyant_sans_next_data():
    with pytest.raises(html_next.NextDataError):
        html_next.extraire_annonces("<html><body>page tronquée</body></html>")


def test_echec_bruyant_structure_changee():
    # __NEXT_DATA__ présent mais chemin rompu → on refuse de deviner (jamais un zéro silencieux).
    with pytest.raises(html_next.NextDataError):
        html_next.extraire_annonces('<script id="__NEXT_DATA__">{"props":{"pageProps":{}}}</script>')


def test_echec_bruyant_zero_annonce():
    with pytest.raises(html_next.NextDataError):
        html_next.extraire_annonces(
            '<script id="__NEXT_DATA__">{"props":{"pageProps":{"searchData":{"ads":[]}}}}</script>')


def test_source_position_conservee(html):
    recs = [html_next.aplatir(a) for a in html_next.extraire_annonces(html)]
    sources = {r["source_position"] for r in recs}
    assert sources == {"address", "city"}                       # précision de position lisible
    assert sum(1 for r in recs if r["source_position"] == "address") == 3


# ── ingestion end-to-end ──

def test_ingestion_puis_idempotence(html, depots_prive, nettoyer):
    ids = _list_ids(html)
    with session_scope() as db:
        db.execute(text("DELETE FROM pige_biens WHERE bien_id IN "
                        "(SELECT bien_id FROM pige_annonces WHERE list_id = ANY(:i))"), {"i": ids})
        db.commit()
    with session_scope() as db:
        r1 = html_ingest.ingester(db, html, "ECH-1.html")
    assert r1["nb_annonces"] == 35 and r1["nb_nouvelles"] == 35 and r1["nb_maj"] == 0
    # 2e dépôt du MÊME fichier : aucun doublon, tout en MAJ.
    with session_scope() as db:
        r2 = html_ingest.ingester(db, html, "ECH-1.html")
    assert r2["nb_nouvelles"] == 0 and r2["nb_maj"] == 35
    with session_scope() as db:
        n = db.execute(text("SELECT count(*) FROM pige_annonces WHERE list_id = ANY(:i)"), {"i": ids}).scalar()
        nb = db.execute(text("SELECT count(DISTINCT bien_id) FROM pige_annonces WHERE list_id = ANY(:i)"),
                        {"i": ids}).scalar()
    assert n == 35 and nb == 35                                 # une annonce = un bien, jamais dédoublé


def test_terrain_incoherent_part_en_a_qualifier(html, depots_prive, nettoyer):
    """L'annonce « Terrain » de 1942 à 12 pièces (list_id 3241231179) part en À QUALIFIER."""
    with session_scope() as db:
        html_ingest.ingester(db, html, "ECH-1.html")
    with session_scope() as db:
        row = db.execute(text(
            "SELECT b.a_qualifier, b.a_qualifier_motifs FROM pige_biens b "
            "JOIN pige_annonces a ON a.bien_id = b.bien_id WHERE a.list_id = 3241231179"),
        ).mappings().first()
    assert row["a_qualifier"] is True
    assert any("terrain" in m.lower() for m in row["a_qualifier_motifs"])


def test_a_qualifier_hors_stats(html, depots_prive, nettoyer):
    """Une annonce À QUALIFIER n'entre pas dans les médianes de l'onglet Marché."""
    from labuse.pige import marche
    with session_scope() as db:
        html_ingest.ingester(db, html, "ECH-1.html")
        stats = marche.stats(db)
    sd = [l for l in stats["communes"] if l["commune"] == "Saint-Denis"][0]
    # les 2 terrains à-qualifier sont exclus → la médiane terrain reste insuffisante (n < 5), jamais
    # gonflée par un prix aberrant.
    assert sd["prix_m2_terrain"]["insuffisant"] is True


def test_baisse_de_prix_historisee(html, depots_prive, nettoyer):
    with session_scope() as db:
        html_ingest.ingester(db, html, "ECH-1.html")
    html_baisse = html.replace('"price":[655000]', '"price":[600000]')
    with session_scope() as db:
        html_ingest.ingester(db, html_baisse, "ECH-1-baisse.html")
    with session_scope() as db:
        ph = db.execute(text(
            "SELECT ancien_prix, nouveau_prix FROM pige_prix_historique ph "
            "JOIN pige_annonces a ON a.bien_id = ph.bien_id WHERE a.list_id = 3143092379 "
            "ORDER BY ph.id DESC LIMIT 1")).mappings().first()
    assert ph and ph["ancien_prix"] == 655000 and ph["nouveau_prix"] == 600000


def test_date_de_verite_est_first_publication(html, depots_prive, nettoyer):
    """« repéré le » suit first_publication_date, jamais index_date (majorité de republications)."""
    with session_scope() as db:
        html_ingest.ingester(db, html, "ECH-1.html")
    with session_scope() as db:
        row = db.execute(text(
            "SELECT b.date_publication, a.first_publication_date::date AS fpd "
            "FROM pige_biens b JOIN pige_annonces a ON a.bien_id = b.bien_id "
            "WHERE a.list_id = 3143092379")).mappings().first()
    assert row["date_publication"] == row["fpd"]


def test_rattachement_etats_valides_et_apparts_non_rattaches(html, depots_prive, nettoyer):
    """Tout bien porte un état de rattachement VALIDE, et les appartements (copro) sont TOUJOURS
    non rattachés (position = quartier). La coexistence des trois états dépend du parcellaire (présent
    en prod, absent de la base de test schéma-seul) : elle est mesurée au Lot 0 sur la vraie base."""
    with session_scope() as db:
        html_ingest.ingester(db, html, "ECH-1.html")
    ids = _list_ids(html)
    with session_scope() as db:
        rows = db.execute(text(
            "SELECT b.type_bien, b.rattachement_etat, b.est_copro FROM pige_biens b "
            "JOIN pige_annonces a ON a.bien_id = b.bien_id WHERE a.list_id = ANY(:i)"),
            {"i": ids}).mappings().all()
    assert rows and all(r["rattachement_etat"] in ("rattachee", "piste", "non_rattachee") for r in rows)
    apparts = [r for r in rows if r["type_bien"] == "appartement"]
    assert apparts and all(r["rattachement_etat"] == "non_rattachee" and r["est_copro"] for r in apparts)


# ════════ RADAR-RECETTE-1 — les 4 défauts de recette ════════

def test_d1a_a_verifier_ne_remplit_pas_tout_le_monde(html, depots_prive, nettoyer):
    """D1a — `a_verifier` (concept IA vision) reste NULL sur le chemin HTML : une donnée structurée n'a
    aucun champ « à vérifier ». `count(*) WHERE a_verifier IS NOT NULL` ne doit PLUS valoir 100 %."""
    with session_scope() as db:
        html_ingest.ingester(db, html, "ECH-1.html")
    ids = _list_ids(html)
    with session_scope() as db:
        non_null = db.execute(text(
            "SELECT count(*) FROM pige_faits f JOIN pige_annonces a ON a.bien_id = f.bien_id "
            "WHERE a.list_id = ANY(:i) AND f.a_verifier IS NOT NULL"), {"i": ids}).scalar()
    assert non_null == 0                                     # plus d'« initialisation qui remplit »


def test_d1c_bien_incoherent_non_rattache(html, depots_prive, nettoyer):
    """D1c — le « terrain » 1942 (list_id 3241231179) est incohérent → JAMAIS rattaché (la surface, base
    du rattachement, est la valeur suspecte) : à_qualifier, idu NULL, état non_rattachee."""
    with session_scope() as db:
        html_ingest.ingester(db, html, "ECH-1.html")
    with session_scope() as db:
        r = db.execute(text(
            "SELECT b.a_qualifier, b.idu, b.rattachement_etat, b.rattachement_niveau FROM pige_biens b "
            "JOIN pige_annonces a ON a.bien_id = b.bien_id WHERE a.list_id = 3241231179")).mappings().first()
    assert r["a_qualifier"] is True and r["idu"] is None
    assert r["rattachement_etat"] == "non_rattachee" and r["rattachement_niveau"] == "absent"


def test_d1c_a_qualifier_visible_mais_marque(html, depots_prive, nettoyer):
    """D1c — un bien à_qualifier reste VISIBLE dans le flux client, avec sa mention + motifs consultables."""
    from labuse.pige import client
    with session_scope() as db:
        html_ingest.ingester(db, html, "ECH-1.html")
        rep = client.lister(db, filtres={"a_qualifier": "oui"}, taille=200)
    assert rep["n_total"] >= 1
    b = next(x for x in rep["biens"] if x["a_qualifier"])
    assert b["a_qualifier"] is True and b["a_qualifier_motifs"] and b["rattachement"]["idu"] is None


def test_d2_pagination_et_troncature_explicite(html, depots_prive, nettoyer):
    """D2 — le plafond par page est explicite : taille=1 → tronquee=True + n_total > n_servi ; une
    grande taille sert tout, bornée au plafond."""
    from labuse.pige import client
    with session_scope() as db:
        html_ingest.ingester(db, html, "ECH-1.html")
        page1 = client.lister(db, filtres={}, taille=1)
        tout = client.lister(db, filtres={}, taille=1000)
    assert page1["tronquee"] is True and page1["n_servi"] == 1 and page1["n_total"] > 1
    assert tout["taille"] == client.PLAFOND_PAGE and tout["tronquee"] is False


def test_d2_filtre_statut_honore(html, depots_prive, nettoyer):
    """D2 — le filtre statut est HONORÉ (ne renvoie pas des biens d'un autre statut)."""
    from labuse.pige import client
    with session_scope() as db:
        html_ingest.ingester(db, html, "ECH-1.html")
        rep = client.lister(db, filtres={"statuts": ["a_reverifier"]}, taille=200)
    assert all(b["statut"] == "a_reverifier" for b in rep["biens"])


def test_d3_depots_dir_defaut_dev_local(monkeypatch):
    """D3 — en LABUSE_DEV_MODE=1 et sans LABUSE_PIGE_DEPOTS_DIR, depots_dir() est un chemin LOCAL
    (jamais /srv, lecture seule sur macOS)."""
    from labuse import config
    from labuse.pige.tables import depots_dir
    monkeypatch.delenv("LABUSE_PIGE_DEPOTS_DIR", raising=False)
    monkeypatch.setenv("LABUSE_DEV_MODE", "1")
    config.get_settings.cache_clear()
    d = str(depots_dir())
    config.get_settings.cache_clear()
    assert "/srv" not in d and ".local" in d


def test_d4_writable_nomme_le_chemin(monkeypatch):
    """D4 — un répertoire non inscriptible produit (False, detail) où `detail` NOMME le chemin fautif."""
    from labuse.pige.tables import depots_dir_writable
    monkeypatch.setenv("LABUSE_PIGE_DEPOTS_DIR", "/proc/nonexistent-radar/x")
    ok, detail = depots_dir_writable()
    assert ok is False and "/proc/nonexistent-radar/x" in detail
