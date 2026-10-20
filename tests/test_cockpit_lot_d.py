"""COCKPIT-1 (Lot D) — tests de la PROPAGATION dans le Circuit.

Unitaire pur sur `cockpit_resume.propagation_reservoir` (la règle : un robinet est à jour quand son
run/cache a été produit après la dernière injection de son réservoir ; sinon en retard, avec le geste).
Le bloc `propagation` est attaché à chaque réservoir par /admin/circuit (couvert en `db`). La garde
« injection de test (base jetable) → robinets en retard → à jour après le geste » est jouée à la
recette (RAPPORT.md).
"""
from __future__ import annotations

import pytest

from labuse import cockpit_resume as ck

_CHIFFRES = {"c1": {"moteur": "cascade"}, "c2": {"moteur": "scoring"}, "c3": {"moteur": "cascade"}}


def _res(**over):
    base = {"id": 7, "nom": "Communes IGN", "etat": ["mint", "à jour"],
            "taps": ["couche:communes", "fiche:commune", "outil:permis"],
            "chiffres_ids": ["c1", "c2", "c3"]}
    base.update(over)
    return base


def test_nouvelle_version_met_tous_les_robinets_en_retard():
    r = _res(etat=["ambre", "nouvelle version"])
    p = ck.propagation_reservoir(r, eau_rob=set(), tuiles_perime=False, chiffres=_CHIFFRES)
    assert p["nouvelle"] is True
    assert p["en_retard"] == 3
    assert all(t["verdict"] == "en_retard" and t["geste"] == "injecter" for t in p["robinets"])


def test_eau_ancienne_demande_calculer():
    r = _res()   # injecté (à jour), mais un robinet sert de l'eau ancienne
    p = ck.propagation_reservoir(r, eau_rob={"fiche:commune"}, tuiles_perime=False, chiffres=_CHIFFRES)
    par = {t["id"]: t for t in p["robinets"]}
    assert par["fiche:commune"] == {"id": "fiche:commune", "verdict": "en_retard", "geste": "calculer"}
    assert par["couche:communes"]["verdict"] == "a_jour"
    assert p["en_retard"] == 1


def test_tout_a_jour():
    p = ck.propagation_reservoir(_res(), eau_rob=set(), tuiles_perime=False, chiffres=_CHIFFRES)
    assert p["en_retard"] == 0
    assert all(t["verdict"] == "a_jour" and t["geste"] is None for t in p["robinets"])


def test_moteurs_distincts():
    # c1/c3 = cascade, c2 = scoring → 2 moteurs distincts.
    p = ck.propagation_reservoir(_res(), eau_rob=set(), tuiles_perime=False, chiffres=_CHIFFRES)
    assert p["moteurs"] == 2


def test_tuiles_perime_signale_au_niveau_bandeau():
    p = ck.propagation_reservoir(_res(), eau_rob=set(), tuiles_perime=True, chiffres=_CHIFFRES)
    assert p["tuiles_perime"] is True


@pytest.mark.db
def test_circuit_attache_propagation_aux_reservoirs():
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    with TestClient(app) as c:
        r = c.get("/admin/circuit")
    assert r.status_code == 200
    reservoirs = r.json()["reservoirs"]
    assert reservoirs, "au moins un réservoir"
    for res in reservoirs:
        p = res.get("propagation")
        assert p is not None and set(p) >= {"nouvelle", "moteurs", "robinets", "en_retard"}


@pytest.mark.db
def test_garde_propagation_nouvelle_version_en_retard():
    """COCKPIT-1 (Lot D) — LA GARDE : sur le run servi, tout réservoir en « nouvelle version » (pas
    encore injecté) a TOUS ses robinets « en retard » avec le geste « injecter ». C'est la moitié LIVE
    de la garde du mandat (« robinets en retard → à jour après le geste ») ; la bascule en_retard→à_jour
    quand le réservoir n'est plus en nouvelle version est prouvée en unitaire (test_nouvelle_version_*
    + test_tout_a_jour). Une injection réelle sur base jetable (recette) la rejoue de bout en bout."""
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    with TestClient(app) as c:
        reservoirs = c.get("/admin/circuit").json()["reservoirs"]
    nouvelles = [r for r in reservoirs if (r.get("etat") or ["", ""])[1] == "nouvelle version"]
    for r in nouvelles:
        p = r["propagation"]
        assert p["nouvelle"] is True
        assert all(t["verdict"] == "en_retard" and t["geste"] == "injecter" for t in p["robinets"]), r["nom"]
