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
