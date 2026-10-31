"""RETOURS-8 (R5) / RADAR-4 — la pige en onglets : les 4 chiffres de tête + la file « à rattacher ».

Vérifie côté backend ce qui NOURRIT l'UI en onglets :
  · /admin/radar/check expose annonces_en_vie · a_rattacher · reverif_dues (les chiffres de tête) ;
  · /admin/radar/a-rattacher liste les biens validés, en vente, NON rattachés — l'admin les rattache À LA
    MAIN (« C'est cette parcelle »). RADAR-4 : le rattachement AUTOMATIQUE (cascade, pistes, confiance)
    est RETIRÉ ; il n'y a plus de « forte/faible » ni de candidate proposée.
"""
from __future__ import annotations

import types

import pytest
from sqlalchemy import text

from labuse.db import session_scope  # noqa: F401 — parité avec les autres tests pige
from labuse.pige import api as radar_api

pytestmark = pytest.mark.db

COMMUNE = "RadarR8Ville"


def _req():
    return types.SimpleNamespace(state=types.SimpleNamespace(compte_id=None))


@pytest.fixture
def seed_non_rattaches(engine, monkeypatch):
    monkeypatch.setattr(radar_api, "exiger_admin", lambda req: None, raising=False)
    # la garde est importée dans les endpoints via `from ..api.auth import exiger_admin` → on patche là.
    from labuse.api import auth
    monkeypatch.setattr(auth, "exiger_admin", lambda req: None)
    with engine.begin() as c:
        # deux biens validés, en vente, NON rattachés (idu NULL) — l'admin les rattache à la main.
        b1 = c.execute(text(
            "INSERT INTO pige_biens (commune, type_bien, statut, idu, rattachement_niveau, "
            " rattachement_etat, rattachement_humain, a_qualifier) "
            "VALUES (:c,'maison','active',NULL,'absent','non_rattachee',false,false) RETURNING bien_id"),
            {"c": COMMUNE}).scalar()
        c.execute(text("INSERT INTO pige_faits (bien_id, prix, type_bien, valide_at) "
                       "VALUES (:b, 350000, 'maison', now())"), {"b": b1})
        b2 = c.execute(text(
            "INSERT INTO pige_biens (commune, type_bien, statut, idu, rattachement_niveau, "
            " rattachement_etat, rattachement_humain, a_qualifier) "
            "VALUES (:c,'terrain','active',NULL,'absent','non_rattachee',false,false) RETURNING bien_id"),
            {"c": COMMUNE}).scalar()
        c.execute(text("INSERT INTO pige_faits (bien_id, prix, type_bien, valide_at) "
                       "VALUES (:b, 190000, 'terrain', now())"), {"b": b2})
    yield {"b1": b1, "b2": b2}
    with engine.begin() as c:
        c.execute(text("DELETE FROM pige_faits WHERE bien_id IN (:a,:b)"), {"a": b1, "b": b2})
        c.execute(text("DELETE FROM pige_biens WHERE bien_id IN (:a,:b)"), {"a": b1, "b": b2})


def test_a_rattacher_liste_les_biens_non_rattaches(seed_non_rattaches):
    """RADAR-4 — la file « à rattacher » liste les biens NON rattachés (pas de pistes, pas de confiance) :
    l'admin saisit l'IDU lui-même. Aucune suggestion automatique n'est servie."""
    out = radar_api.radar_a_rattacher(_req())
    ids = {r["bien_id"] for r in out["file"]}
    assert seed_non_rattaches["b1"] in ids and seed_non_rattaches["b2"] in ids
    # plus aucun champ de rattachement automatique (confiance, piste, critères) n'est servi.
    for r in out["file"]:
        assert "confiance" not in r and "premiere_piste" not in r and "rattachement_criteres" not in r


def test_check_expose_les_chiffres_de_tete(seed_non_rattaches):
    d = radar_api.radar_check(_req())
    assert "annonces_en_vie" in d and "a_rattacher" in d and "reverif_dues" in d
    assert d["a_rattacher"] >= 2                                     # nos deux biens non rattachés
    assert d["annonces_en_vie"] >= 2                                 # validés + actifs
