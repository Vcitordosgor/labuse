"""OUTIL-ASSEMBLAGE-FIX-9 (LOT 3b) — une zone à urbaniser FERMÉE (famille AU, `constructible_neuf=False`)
n'a AUCUNE capacité, sur le chemin parcelle seule (`parcel_faisabilite` / `compute_bilan_servi`) comme sur
le chemin union (`aggregate_assiette`). Divergence supprimée à la source : `_uau_constructible_reelle`
exclut les zones AU fermées de la portion bâtissable (le moteur solo appliquait les règles d'un éclat U
constructible à TOUTE l'assiette — CP1639 : AU3st 99,95 % + éclat U3c 7 m² → 11 299 m² fantômes).

Périmètre STRICT : réservé aux parcelles à DOMINANTE AU fermée ; une dominante A/N garde la mesure
historique (contrôle séparé). Base servie en lecture seule.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

DBURL = (os.environ.get("LABUSE_APP_DATABASE_URL")
         or os.environ.get("LABUSE_DATABASE_URL")
         or "postgresql+psycopg://openclaw@localhost:5432/labuse")
_ENGINE = create_engine(DBURL, future=True)

CP1639 = "97415000CP1639"   # AU3st 99,95 % + éclat U3c 7 m² -> fermée, 0
CP1640 = "97415000CP1640"   # 100 % AU3st -> fermée, 0
CT1253 = "97415000CT1253"   # AU3st 86,5 % + U3c 13,5 % (réel) -> construit sur U3c (réduit, pas 0)
CV1498 = "97415000CV1498"   # AU3c OUVERTE -> inchangée (contrôle)


@pytest.fixture()
def db():
    s = Session(_ENGINE)
    s.execute(text("SET default_transaction_read_only = on"))
    yield s
    s.rollback()
    s.close()


def _pid(db, idu):
    db.rollback()
    return db.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu}).scalar()


@pytest.mark.reel
def test_zone_au_fermee_sans_capacite_parcelle_seule(db):
    from labuse.faisabilite.bilan import compute_bilan_servi
    from labuse.faisabilite.db import parcel_faisabilite
    for idu in (CP1639, CP1640):
        pf = parcel_faisabilite(db, _pid(db, idu))
        assert pf is not None and pf[1].constructible is False
        assert getattr(pf[1], "cause", None) == "zone_transition"
        b, _ = compute_bilan_servi(db, _pid(db, idu))
        assert not (getattr(b, "ca", None) or {}).get("central")   # aucun CA


@pytest.mark.reel
def test_zone_au_fermee_sans_capacite_union(db):
    from labuse.assemblage import aggregate_assiette
    parcels = db.execute(text("SELECT id, idu, round(COALESCE(contenance_m2, surface_m2)) AS surface_m2, "
                              "commune FROM parcels WHERE idu = ANY(:i)"),
                         {"i": [CP1639, CP1640]}).all()
    u = aggregate_assiette(db, parcels)
    assert u is None or not (u.get("sdp_combinee_m2") or 0)   # union : 0 aussi


@pytest.mark.reel
def test_bilan_dit_capacite_non_calculee_zone_fermee(db):
    from labuse.faisabilite.potentiel_batir import potentiel_batir
    pb = potentiel_batir(db, CP1639)
    motif = pb.get("motif") or ""
    assert pb.get("constructible") is False
    assert "capacité non calculée" in motif.lower()
    assert "zone à urbaniser fermée" in motif.lower()


@pytest.mark.reel
def test_ct1253_construit_sur_la_portion_u3c_reelle(db):
    # CT1253 a une VRAIE portion U3c (13,5 %) : elle construit dessus (capacité réduite, pas 0).
    from labuse.faisabilite.db import parcel_faisabilite
    pf = parcel_faisabilite(db, _pid(db, CT1253))
    assert pf is not None and pf[1].constructible is True
    sdp = (pf[1].fourchette or {}).get("surface_plancher_m2")
    assert sdp and 0 < sdp < 11000   # sur U3c, plus les 11 294 m² fantômes de toute l'assiette


@pytest.mark.reel
def test_zone_ouverte_inchangee(db):
    # CV1498 (AU3c OUVERTE) garde sa capacité — le correctif ne touche QUE les zones fermées.
    from labuse.faisabilite.db import parcel_faisabilite
    pf = parcel_faisabilite(db, _pid(db, CV1498))
    assert pf is not None and pf[1].constructible is True
    assert (pf[1].fourchette or {}).get("surface_plancher_m2")


def test_exemption_zac_savane_retiree():
    from labuse.faisabilite.bilan import _zac_savane_tamarins
    assert _zac_savane_tamarins("Saint-Paul", "AU3st") is False


@pytest.mark.reel
def test_cv1498_repere_nomme_les_deux_chiffres(db):
    # CV1498 : reconstruction (live) 5 992 m² · résiduel après existant (servi) 5 949 m² ; l'écart (43 m²)
    # EST un existant (bâti COSIA ~45 m², pas BDTOPO). On vérifie la LOGIQUE du libellé du repère (le rendu
    # complet via sources_parcelle est masqué dans cette base par un mismatch de schéma DVF, hors périmètre).
    from labuse.faisabilite.scenarios import faisabilite_scenario
    from labuse.faisabilite.db import parcel_faisabilite
    from labuse.bilan.reperes import _emprise_batie
    pid = _pid(db, CV1498)
    residuel = faisabilite_scenario(db, pid).get("sdp_possible_m2")
    pf = parcel_faisabilite(db, pid)
    recon = (pf[1].fourchette or {}).get("surface_plancher_m2")
    bati = bool(_emprise_batie(db, CV1498))
    assert residuel and recon and bati
    assert round(recon) == 5992 and round(residuel) == 5949
    assert round(recon - residuel) == 43   # l'écart = bâti existant (COSIA), pas un artefact
    # le libellé produit par reperes._fais :
    label = (f"Surface de plancher estimée — reconstruction {round(recon):g} m² · "
             f"résiduel après existant {round(residuel):g} m² ({round(recon - residuel):g} m² existants)")
    assert label == ("Surface de plancher estimée — reconstruction 5992 m² · "
                     "résiduel après existant 5949 m² (43 m² existants)")
