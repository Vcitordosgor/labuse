"""RADAR-4 (E-040) — DÉDOUBLONNAGE des biens, recette.

Deux annonces du MÊME bien physique (même commune ∧ type ∧ surface EXACTE ∧ prix EXACT) ne font qu'UN
bien — AVANT la garde à-qualifier, et à travers les portails. Prouvé ici :
  · le même bien sur DEUX portails (Leboncoin ↔ Bien'ici) fusionne (une seule fiche, deux annonces) ;
  · deux annonces À QUALIFIER (champs contradictoires) du même bien fusionnent (l'ancien garde
    `not degrade and not motifs` les laissait filer en double — constat E-040) ;
  · la variante DÉGRADÉE (vignettes DOM, faits trop pauvres) reste ISOLÉE (pas de faux positif).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import html_ingest, html_next

pytestmark = pytest.mark.db

_COMMUNE = "Saint-Paul"


def _rec(list_id: str, url: str, **over) -> dict:
    base = dict(type="maison", commune=_COMMUNE, prix=350000, surface_hab=120.0,
                surface_terrain=500.0, list_id=list_id, url=url,
                provenance=html_next.PROV_RICHE, source_position="city", district="Saint-Gilles",
                first_publication_date=None, index_date=None, expiration_date=None, statut_portail=None)
    base.update(over)
    return base


def _nettoyer(db, list_ids):
    ids = tuple(list_ids)
    bids = [r[0] for r in db.execute(text(
        "SELECT DISTINCT bien_id FROM pige_annonces WHERE list_id = ANY(:i)"), {"i": list(ids)}).all()]
    if bids:
        db.execute(text("DELETE FROM pige_biens WHERE bien_id = ANY(:b)"), {"b": bids})
    db.commit()


def _n_biens(db, list_ids) -> int:
    return db.execute(text(
        "SELECT count(DISTINCT bien_id) FROM pige_annonces WHERE list_id = ANY(:i)"),
        {"i": list(list_ids)}).scalar() or 0


def test_meme_bien_deux_portails_fusionne():
    """Leboncoin + Bien'ici, même maison exacte (surf+prix) → UN seul bien, DEUX annonces."""
    lids = [940001, 940002]
    with session_scope() as db:
        _nettoyer(db, lids)
        r1 = html_ingest._ingester_annonce(db, _rec(940001, "https://www.leboncoin.fr/ad/r4-1"))
        r2 = html_ingest._ingester_annonce(db, _rec(940002, "https://www.bienici.com/annonce/r4-2"))
        db.commit()
        assert r1 == "nouvelle" and r2 == "fusion"
        assert _n_biens(db, lids) == 1                      # un seul bien physique
        n_ann = db.execute(text("SELECT count(*) FROM pige_annonces WHERE list_id = ANY(:i)"),
                           {"i": lids}).scalar()
        assert n_ann == 2                                   # les deux annonces le pointent
        _nettoyer(db, lids)


def test_deux_annonces_a_qualifier_fusionnent():
    """RADAR-4 (E-040) — deux annonces À QUALIFIER du même bien (terrain portant des pièces → motif
    d'incohérence), surf+prix exacts, fusionnent malgré le motif (l'ancien garde les séparait)."""
    lids = [940011, 940012]
    aq = dict(type="terrain", surface_hab=None, surface_terrain=800.0, prix=90000, pieces=5)
    with session_scope() as db:
        _nettoyer(db, lids)
        r1 = html_ingest._ingester_annonce(db, _rec(940011, "https://www.leboncoin.fr/ad/aq1", **aq))
        r2 = html_ingest._ingester_annonce(db, _rec(940012, "https://www.bienici.com/annonce/aq2", **aq))
        db.commit()
        assert r1 == "nouvelle" and r2 == "fusion"
        assert _n_biens(db, lids) == 1
        # le bien résultant est bien marqué à qualifier (le motif a été vu).
        aq_flag = db.execute(text(
            "SELECT bool_or(a_qualifier) FROM pige_biens b JOIN pige_annonces a ON a.bien_id = b.bien_id "
            "WHERE a.list_id = ANY(:i)"), {"i": lids}).scalar()
        assert aq_flag is True
        _nettoyer(db, lids)


def test_degrade_identique_reste_isole():
    """La variante DÉGRADÉE (faits pauvres) ne fusionne PAS sur l'identité exacte : deux dégradées
    identiques restent DEUX biens (garde anti-faux-positif, test_d1 end-to-end le confirme aussi)."""
    lids = [940021, 940022]
    dg = dict(provenance=html_next.PROV_DEGRADE, source_position="city")
    with session_scope() as db:
        _nettoyer(db, lids)
        r1 = html_ingest._ingester_annonce(db, _rec(940021, "https://www.leboncoin.fr/ad/dg1", **dg))
        r2 = html_ingest._ingester_annonce(db, _rec(940022, "https://www.leboncoin.fr/ad/dg2", **dg))
        db.commit()
        assert r1 == "nouvelle" and r2 == "nouvelle"        # dégradé → jamais fusionné sur l'exact
        assert _n_biens(db, lids) == 2
        _nettoyer(db, lids)
