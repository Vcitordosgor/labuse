"""M82 (cas A) — l'outil Copilote `divisibilite` : le score GÉOMÉTRIQUE précalculé (module_division)
alimente la réponse « cette parcelle est-elle divisible ? » SANS trancher le réglementaire.

Doctrine gravée (réglementaire > géométrique) : jamais un « feu vert », toujours la réserve « le
règlement de zone fait foi » ; « non repérée » ≠ « non divisible ».
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.copilote_v2.outils import divisibilite


@pytest.mark.db
def test_divisibilite_candidate_reelle(db_session):
    idu = db_session.execute(text(
        "SELECT idu FROM module_division WHERE score >= 80 LIMIT 1")).scalar()
    if not idu:
        pytest.skip("aucune parcelle module_division en base")
    r = divisibilite(db_session, idu=idu)
    assert r.ok and r.data["candidate"] is True
    assert r.valeur >= 69                      # le +10 constant + gates → score plancher 69
    assert r.data["lot_estime_m2"] is not None
    # cadre réglementaire OBLIGATOIRE — jamais un verdict, jamais un feu vert
    assert "règlement de zone" in r.reserve and "PAS un verdict" in r.reserve


@pytest.mark.db
def test_divisibilite_non_repere_n_est_pas_non_divisible(db_session):
    # IDU valide (14 car.) absent de module_division → « non repérée », jamais « non divisible »
    r = divisibilite(db_session, idu="97401000ZZ9999")
    assert r.ok and r.data["candidate"] is False
    assert "non divisible" in r.reserve and "règlement de zone" in r.reserve


def test_divisibilite_idu_invalide():
    class _S:  # pas d'accès DB nécessaire : le garde longueur court-circuite
        pass
    r = divisibilite(_S(), idu="trop-court")
    assert not r.ok and r.refus
