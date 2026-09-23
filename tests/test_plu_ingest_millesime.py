"""PLU-INGEST-DELETE — le bump de millésime PLU ne doit pas laisser d'ancien document orphelin.

Le nom du document de règlement est DATÉ (`..._YYYYMMDD.pdf`) : il change d'un millésime à l'autre.
`ingest_reglement` purge par (insee, document) → à un bump, l'ancien document survivait en base
(orphelin), la commune servant alors deux millésimes à la fois. Le correctif ajoute
`purge_commune_extraits` (DELETE par le seul INSEE, garde-fou 974) et `ingest_commune_reglements`
(purge par INSEE 1× puis insère tous les volumes en UNE transaction).

Commune témoin = 97499 (INSEE fictif, jamais servi, mais bien préfixé 974 → passe le garde-fou).
`db_session` est transactionnelle et rollback-ée : aucune pollution de la base de test.

FLIP attendu : les 4 tests qui exercent la nouvelle API échouent sur le code d'AVANT (fonctions
absentes) ; `test_ancien_chemin_par_document_laisse_orphelin` documente le défaut et passe des deux
côtés (il n'utilise que `ingest_reglement`, inchangé).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

import labuse.ingestion.plu_ingest as plu_ingest

pytestmark = pytest.mark.db

INSEE = "97499"                       # témoin fictif, préfixe 974 (garde-fou OK)
COMMUNE = "Commune Témoin"
IDURBA = "97499_PLU_TEMOIN"
URL = "https://example.invalid/97499_plu.zip"
DOC_V1 = "97499_reglement_20250101.pdf"   # millésime 1
DOC_V2 = "97499_reglement_20260101.pdf"   # millésime 2 (le NOM change au bump)


def _fake_split(path):
    """Remplace le parseur PDF : 1 extrait par document, texte marqué par le chemin (distingue
    les volumes). Évite tout PDF réel — le test porte sur la purge, pas sur le découpage."""
    return ([{"article_ref": "Article U 1", "zone": "U", "page_pdf": 1,
              "texte": f"Reglement volume {path}", "doute": False, "doute_motif": None}], False)


def _docs(session):
    return session.execute(
        text("SELECT DISTINCT document FROM plu_reglement_extrait WHERE insee=:i ORDER BY document"),
        {"i": INSEE}).scalars().all()


def _count(session):
    return session.execute(
        text("SELECT count(*) FROM plu_reglement_extrait WHERE insee=:i"), {"i": INSEE}).scalar()


def test_purge_commune_extraits_supprime_tout_par_insee(db_session, monkeypatch):
    """La purge par INSEE efface TOUS les documents de la commune, quel que soit leur nom."""
    monkeypatch.setattr(plu_ingest, "_split_articles", _fake_split)
    plu_ingest.ingest_reglement(db_session, insee=INSEE, commune=COMMUNE, idurba=IDURBA,
                                millesime="2025-01-01", document=DOC_V1, pdf_path="A",
                                source_url=URL, fetched_at=None, commit=False)
    plu_ingest.ingest_reglement(db_session, insee=INSEE, commune=COMMUNE, idurba=IDURBA,
                                millesime="2026-01-01", document=DOC_V2, pdf_path="B",
                                source_url=URL, fetched_at=None, commit=False)
    assert _count(db_session) == 2                      # deux documents en base
    n = plu_ingest.purge_commune_extraits(db_session, INSEE, commit=False)
    assert n == 2 and _count(db_session) == 0           # tout parti d'un coup


def test_purge_commune_extraits_garde_fou_974(db_session, monkeypatch):
    """Un INSEE hors 974 est REFUSÉ (garde-fou anti-DELETE-de-masse) et rien n'est supprimé."""
    monkeypatch.setattr(plu_ingest, "_split_articles", _fake_split)
    plu_ingest.ingest_reglement(db_session, insee=INSEE, commune=COMMUNE, idurba=IDURBA,
                                millesime="2025-01-01", document=DOC_V1, pdf_path="A",
                                source_url=URL, fetched_at=None, commit=False)
    for mauvais in ("75056", "", None):
        with pytest.raises(ValueError):
            plu_ingest.purge_commune_extraits(db_session, mauvais, commit=False)
    assert _count(db_session) == 1                       # la ligne 974 est intacte


def test_ingest_commune_reglements_multi_volume(db_session, monkeypatch):
    """Multi-volume conservé : deux volumes distincts → deux documents en base, une transaction."""
    monkeypatch.setattr(plu_ingest, "_split_articles", _fake_split)
    r = plu_ingest.ingest_commune_reglements(
        db_session, insee=INSEE, commune=COMMUNE, idurba=IDURBA, millesime="2026-01-01",
        documents=[{"name": DOC_V2, "path": "vol1"},
                   {"name": "97499_reglement_annexes_20260101.pdf", "path": "vol2"}],
        source_url=URL, fetched_at=None, commit=False)
    assert r["documents"] == 2 and r["extraits"] == 2
    assert len(_docs(db_session)) == 2


def test_bump_millesime_ne_laisse_pas_dorphelin(db_session, monkeypatch):
    """LE test de non-régression : au bump de millésime (nom de document changé), la commune ne
    sert QUE le nouveau document — l'ancien est purgé, pas d'orphelin."""
    monkeypatch.setattr(plu_ingest, "_split_articles", _fake_split)
    # millésime 1
    plu_ingest.ingest_commune_reglements(
        db_session, insee=INSEE, commune=COMMUNE, idurba=IDURBA, millesime="2025-01-01",
        documents=[{"name": DOC_V1, "path": "A"}], source_url=URL, fetched_at=None, commit=False)
    assert _docs(db_session) == [DOC_V1]
    # bump → millésime 2 (le nom du document change)
    plu_ingest.ingest_commune_reglements(
        db_session, insee=INSEE, commune=COMMUNE, idurba=IDURBA, millesime="2026-01-01",
        documents=[{"name": DOC_V2, "path": "B"}], source_url=URL, fetched_at=None, commit=False)
    assert _docs(db_session) == [DOC_V2]                  # SEUL le nouveau, 0 orphelin
    assert _count(db_session) == 1


def test_ancien_chemin_par_document_laisse_orphelin(db_session, monkeypatch):
    """Témoin du DÉFAUT (chemin `ingest_reglement` seul, inchangé) : purge par (insee, document) →
    au bump, l'ancien document DATÉ survit → la commune sert deux millésimes. C'est précisément ce
    que `ingest_commune_reglements` corrige (cf. test ci-dessus)."""
    monkeypatch.setattr(plu_ingest, "_split_articles", _fake_split)
    plu_ingest.ingest_reglement(db_session, insee=INSEE, commune=COMMUNE, idurba=IDURBA,
                                millesime="2025-01-01", document=DOC_V1, pdf_path="A",
                                source_url=URL, fetched_at=None, commit=False)
    plu_ingest.ingest_reglement(db_session, insee=INSEE, commune=COMMUNE, idurba=IDURBA,
                                millesime="2026-01-01", document=DOC_V2, pdf_path="B",
                                source_url=URL, fetched_at=None, commit=False)
    assert _docs(db_session) == [DOC_V1, DOC_V2]          # DEUX millésimes = orphelin non purgé
    assert _count(db_session) == 2
