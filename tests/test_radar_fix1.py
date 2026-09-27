"""RADAR-FIX-1 (1) — « MÊME BIEN, NOUVEAU NUMÉRO ».

Garde de la règle de fusion : unitaire sur `_est_meme_bien` (les 5 paires témoins de la base doivent
matcher, les 3 faux positifs mesurés ne doivent PAS) + intégration sur `_ingester_annonce` (un nouveau
numéro rejoint le bien existant au lieu de créer un doublon). Objets [RADAR-FIX-TEST] purgés en fin.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import html_ingest, html_next


# ════════════════════════ unitaire — la RÈGLE (sans DB) ════════════════════════

def _cand(type_bien="maison", prix=None, sh=None, st=None, sp=None, district=None):
    return {"type_bien": type_bien, "prix": prix, "surface_hab": sh, "surface_terrain": st,
            "source_position": sp, "district": district}


def test_regle_valeurs_exactes_meme_bien():
    # paire témoin {74,75} : maison 374 500 € / 200 m², même quartier — valeurs EXACTES → même bien.
    assert html_ingest._est_meme_bien(
        _cand("maison", 374500, 200, None, "city", "Le Butor"),
        type_bien="maison", prix=374500, surface_hab=200, surface_terrain=None,
        source_position="city", district="Le Butor") is True


def test_regle_exact_sans_district_meme_bien():
    # paire témoin {1,111} : maison 655 000 € / 202 m², district connu d'un seul côté — exact → même bien.
    assert html_ingest._est_meme_bien(
        _cand("maison", 655000, 202, 265, "address", "Montgaillard"),
        type_bien="maison", prix=655000, surface_hab=202, surface_terrain=265,
        source_position="address", district="") is True


def test_regle_terrain_exact_meme_bien():
    # paire témoin {77,101} : terrain 169 000 € / 310 m² (surface_hab NULL) — pertinente = terrain.
    assert html_ingest._est_meme_bien(
        _cand("terrain", 169000, None, 310, None, "Le Chaudron"),
        type_bien="terrain", prix=169000, surface_hab=None, surface_terrain=310,
        source_position=None, district="Le Chaudron") is True


def test_regle_tolerance_meme_quartier():
    # même quartier + prix a un peu bougé (±3 %) + surface ±2 % → même bien (re-publication).
    assert html_ingest._est_meme_bien(
        _cand("maison", 400000, 100, None, "city", "Bellepierre"),
        type_bien="maison", prix=410000, surface_hab=101, surface_terrain=None,
        source_position="city", district="Bellepierre") is True


def test_faux_positif_quartier_different_refuse():
    # {8,151} mesuré : deux F2 ~236-239 k€ / 59-60 m² dans des quartiers DIFFÉRENTS → PAS le même bien
    # (valeurs non exactes + quartiers connus distincts → la tolérance n'est pas accordée).
    assert html_ingest._est_meme_bien(
        _cand("appartement", 239500, 59, None, "city", "Petite-Île Bas de la Rivière"),
        type_bien="appartement", prix=236000, surface_hab=60, surface_terrain=None,
        source_position="city", district="Le Chaudron - Sainte-Clotilde") is False


def test_faux_positif_district_inconnu_refuse():
    # {15,26} mesuré : ~150 k€ / 52-53 m², un côté sans district → valeurs non exactes + quartier non
    # corroboré → refusé (sinon on fusionne des copros distinctes).
    assert html_ingest._est_meme_bien(
        _cand("appartement", 149900, 52, None, "address", ""),
        type_bien="appartement", prix=151200, surface_hab=53, surface_terrain=None,
        source_position="city", district="Le Chaudron - Sainte-Clotilde") is False


def test_type_different_jamais_meme_bien():
    assert html_ingest._est_meme_bien(
        _cand("terrain", 400000, None, 200, "city", "X"),
        type_bien="maison", prix=400000, surface_hab=200, surface_terrain=None,
        source_position="city", district="X") is False


# ════════════════════════ intégration — l'INGESTION fusionne (DB) ════════════════════════

pytestmark_db = pytest.mark.db

_L1, _L2, _L3 = 900000074, 900000075, 900000199   # list_ids [RADAR-FIX-TEST]


def _rec(list_id, prix, sh, *, district="Le Butor - Champ-Fleuri", sp="city"):
    return {
        "list_id": list_id, "url": f"https://www.leboncoin.fr/ad/ventes_immobilieres/{list_id}",
        "commune": "Saint-Denis", "type": "maison", "prix": prix,
        "surface_hab": sh, "surface_terrain": None, "pieces": 4,
        "provenance": html_next.PROV_RICHE, "source_position": sp, "district": district,
        "lat": -20.9, "lng": 55.45, "zipcode": "97400",
        "first_publication_date": "2026-09-01T10:00:00+04:00",
        "index_date": "2026-09-01T10:00:00+04:00",
        "expiration_date": "2026-11-01T10:00:00+04:00", "statut_portail": "active",
        "owner_type": "particulier", "brut": {},
    }


def _purger(db):
    db.execute(text("DELETE FROM pige_biens WHERE bien_id IN "
                    "(SELECT bien_id FROM pige_annonces WHERE list_id = ANY(:i))"),
               {"i": [_L1, _L2, _L3]})
    db.execute(text("DELETE FROM event_log WHERE dedup LIKE 'pige:%' AND detail LIKE '%900000%'"))


@pytest.mark.db
def test_ingestion_nouveau_numero_rejoint_le_bien():
    with session_scope() as db:
        _purger(db)
        db.commit()
    try:
        with session_scope() as db:
            r1 = html_ingest._ingester_annonce(db, _rec(_L1, 374500, 200))
            db.commit()
        with session_scope() as db:
            # même bien physique (exact), NOUVEAU numéro → fusion, pas de doublon
            r2 = html_ingest._ingester_annonce(db, _rec(_L2, 374500, 200))
            db.commit()
        assert r1 == "nouvelle"
        assert r2 == "fusion"
        with session_scope() as db:
            n_biens = db.execute(text(
                "SELECT count(DISTINCT bien_id) FROM pige_annonces WHERE list_id = ANY(:i)"),
                {"i": [_L1, _L2]}).scalar()
            n_numeros = db.execute(text(
                "SELECT count(*) FROM pige_annonces WHERE list_id = ANY(:i)"), {"i": [_L1, _L2]}).scalar()
        assert n_biens == 1          # UN seul bien
        assert n_numeros == 2        # DEUX numéros (l'historique des numéros est conservé)
    finally:
        with session_scope() as db:
            _purger(db)
            db.commit()


@pytest.mark.db
def test_ingestion_republication_conserve_prix_precedent():
    """Nouveau numéro à prix baissé (même quartier) → fusion + prix précédent conservé dans l'historique."""
    with session_scope() as db:
        _purger(db)
        db.commit()
    try:
        with session_scope() as db:
            html_ingest._ingester_annonce(db, _rec(_L1, 400000, 100))
            db.commit()
        with session_scope() as db:
            res = html_ingest._ingester_annonce(db, _rec(_L3, 390000, 100))   # −2,5 % (±3 %), même quartier
            db.commit()
        assert res == "fusion"
        with session_scope() as db:
            bien_id = db.execute(text("SELECT bien_id FROM pige_annonces WHERE list_id = :l"),
                                 {"l": _L1}).scalar()
            hist = db.execute(text(
                "SELECT ancien_prix, nouveau_prix FROM pige_prix_historique WHERE bien_id = :b "
                "ORDER BY date_constat DESC LIMIT 1"), {"b": bien_id}).mappings().first()
        assert hist is not None and hist["ancien_prix"] == 400000 and hist["nouveau_prix"] == 390000
    finally:
        with session_scope() as db:
            _purger(db)
            db.commit()
