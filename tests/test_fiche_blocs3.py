"""RETOUCHES-1 lot C (FICHE-3) — les six blocs sourcés de la fiche : chacun rend un dict avec
`disponible` + `source`, JAMAIS une exception (garde d'ingestion : une table absente = « sans objet »,
jamais un 500 qui poisonnerait la transaction de la fiche entière)."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import fiche_blocs3 as B

pytestmark = pytest.mark.db

_BLOCS = ["cartofriches", "loyers_oll", "trafic_rn", "catnat", "pm_voisines", "anciennete_detention"]


def test_blocs3_robustes_et_structures(db_session):
    """Chaque bloc rend un dict {disponible: bool, source: str, …} sans lever, même quand la source
    n'est pas ingérée (base de test) — c'est le contrat « sans objet, jamais une erreur »."""
    db_session.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "('97499000FB0001','Testville','FB','1', ST_GeomFromText(:w,4326),"
        " ST_Transform(ST_GeomFromText(:w,4326),2975), 500,"
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326))) ON CONFLICT (idu) DO NOTHING"),
        {"w": "POLYGON((55.4 -21.0,55.4003 -21.0,55.4003 -20.9997,55.4 -20.9997,55.4 -21.0))"})
    for nom in _BLOCS:
        r = getattr(B, nom)(db_session, "97499000FB0001")
        assert isinstance(r, dict), nom
        assert isinstance(r["disponible"], bool), nom
        assert r.get("source"), nom
    # la transaction n'est PAS poisonnée : une requête simple passe encore après les six blocs.
    assert db_session.execute(text("SELECT 1")).scalar() == 1
