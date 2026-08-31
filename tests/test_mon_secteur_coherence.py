"""SECTEUR-2 (T1) — Mon secteur = « Marché et secteur » de la fiche parcelle (identiques), et la
méthode « état de l'art » du moteur COMMUN : exclusion des 5 % extrêmes, rayon adaptatif jusqu'à n
minimum (constante), rayon effectif rendu, distribution avant/après. Un seul moteur, jamais un calcul
parallèle — ces tests le prouvent sur des parcelles réelles (skip si la base de test ne les porte pas).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.faisabilite.bilan import (
    MIN_N_SECTEUR, sector_price, trim_extremes_5pct, distribution_secteur,
)
from labuse.faisabilite.engine import Hypotheses

pytestmark = pytest.mark.db


def _quelques_parcelles(db, n=3):
    return [r[0] for r in db.execute(text(
        "SELECT idu FROM parcels WHERE commune IN ('Saint-Denis','Saint-Pierre','Le Tampon','Saint-Paul') "
        "ORDER BY idu LIMIT :n"), {"n": n}).all()]


def test_mon_secteur_identique_au_marche_secteur_de_la_fiche():
    """Le €/m² bâti de Mon secteur EST celui du moteur `sector_price` servi par la fiche — même appel,
    même nombre. Aucun calcul parallèle ne peut diverger."""
    from labuse.api.mon_secteur import mon_secteur
    with session_scope() as db:
        idus = _quelques_parcelles(db)
        if not idus:
            pytest.skip("base de test sans parcelle des communes témoins")
        verifs = 0
        for idu in idus:
            p = db.execute(text("SELECT id, commune FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
            fiche = sector_price(db, p["id"], Hypotheses.charger(p["commune"]))
            out = mon_secteur(idu=idu, db=db)
            sb = out["secteur_bati"]
            if sb is None:      # échantillon insuffisant sur cette parcelle → rien à comparer
                assert fiche.get("median") is None or not fiche.get("fiable")
                continue
            assert sb["median_eur_m2"] == fiche["median"], f"{idu}: Mon secteur ≠ fiche"
            assert sb["rayon_m"] == fiche["radius_m"]            # rayon EFFECTIF, identique
            verifs += 1
        if verifs == 0:
            pytest.skip("aucune parcelle témoin avec un secteur fiable dans la base de test")


def test_exclusion_des_5pct_extremes():
    """trim_extremes_5pct retire bien 2,5 % à chaque queue au-delà de ~20 valeurs, rien en deçà."""
    petit = [1000.0, 2000.0, 3000.0, 50000.0]        # 4 valeurs : floor(4·2,5 %) = 0 → intact
    kept, lo, hi = trim_extremes_5pct(petit)
    assert kept == sorted(petit) and lo is None and hi is None
    grand = [float(x) for x in range(1, 101)]         # 100 valeurs : 2 retirées de chaque côté
    kept, lo, hi = trim_extremes_5pct(grand)
    assert len(kept) == 96 and lo == 3.0 and hi == 98.0
    assert 1.0 not in kept and 100.0 not in kept


def test_distribution_avant_apres_rendue():
    """sector_price rend la distribution avant/après + la constante n minimum visée (transparence)."""
    with session_scope() as db:
        idus = _quelques_parcelles(db, 4)
        if not idus:
            pytest.skip("base de test sans parcelle témoin")
        vu = False
        for idu in idus:
            p = db.execute(text("SELECT id, commune FROM parcels WHERE idu = :i"), {"i": idu}).mappings().first()
            sp = sector_price(db, p["id"], Hypotheses.charger(p["commune"]))
            dist = sp.get("distribution")
            assert dist is not None
            assert dist["n_min_vise"] == MIN_N_SECTEUR
            assert dist["avant"]["n"] >= dist["apres"]["n"]        # le trim n'ajoute jamais
            if sp.get("fiable"):
                vu = True
        if not vu:
            pytest.skip("aucun secteur fiable dans la base de test")


def test_distribution_secteur_repere_vide():
    """Un échantillon vide rend des repères None (jamais un zéro trompeur)."""
    d = distribution_secteur([])
    assert d["n"] == 0 and d["median"] is None and d["max"] is None
