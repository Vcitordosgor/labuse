"""ETUDE-V6 (Lot A, étape 1) — validation de l'assiette : contiguïté par graphe + faits sourcés.

Deux familles :
  • la contiguïté est une fonction géométrique PURE (pas de base) → on couvre les 4 cas d'acceptation
    du mandat (segment commun = ok, non contiguë = refus, contact par un sommet = refus, retrait d'une
    parcelle de liaison qui scinde = refus) ;
  • la validation complète (`valider_parcelles`) est rejouée sur de vraies parcelles (marqueur `reel`).
"""
from __future__ import annotations

import os

import pytest
from shapely.geometry import Polygon

from labuse.implantation.assiette import (
    MSG_NON_CONTIGUES,
    contiguite_graphe,
    longueur_frontiere_partagee,
    qualite_geometrique,
    valider_parcelles,
)


def _carre(x0, y0, cote=10.0):
    return Polygon([(x0, y0), (x0 + cote, y0), (x0 + cote, y0 + cote), (x0, y0 + cote)])


# ---- Contiguïté : fonction pure, aucun accès base ------------------------------------------------

def test_frontiere_partagee_mesure_le_segment():
    a, b = _carre(0, 0), _carre(10, 0)   # côté commun x=10, longueur 10 m
    assert longueur_frontiere_partagee(a, b) == pytest.approx(10.0)


def test_acc1_segment_commun_accepte():
    # D-101 + D-102 : segment commun de longueur positive → une seule composante.
    g = {"A": _carre(0, 0), "B": _carre(10, 0)}
    r = contiguite_graphe(g)
    assert r["ok"] is True
    assert r["composantes"] == [["A", "B"]]


def test_acc2_non_contigue_refusee():
    # D-900 ajoutée loin → deux composantes, refus.
    g = {"A": _carre(0, 0), "B": _carre(100, 100)}
    r = contiguite_graphe(g)
    assert r["ok"] is False
    assert len(r["composantes"]) == 2


def test_acc3_contact_par_un_sommet_refuse():
    # Contact par le seul coin (10,10) : intersection ponctuelle, longueur nulle → NON contiguës.
    g = {"A": _carre(0, 0), "B": _carre(10, 10)}
    assert longueur_frontiere_partagee(g["A"], g["B"]) == pytest.approx(0.0)
    r = contiguite_graphe(g)
    assert r["ok"] is False


def test_acc4_retrait_parcelle_de_liaison_scinde():
    # Chaîne A–B–C (B au milieu touche A et C). Avec B : connexe. Sans B : deux composantes.
    chaine = {"A": _carre(0, 0), "B": _carre(10, 0), "C": _carre(20, 0)}
    assert contiguite_graphe(chaine)["ok"] is True
    sans_b = {k: v for k, v in chaine.items() if k != "B"}
    r = contiguite_graphe(sans_b)
    assert r["ok"] is False
    assert sorted(r["composantes"]) == [["A"], ["C"]]


def test_contact_sous_tolerance_refuse():
    # Chevauchement de frontière de 0,3 m seulement (< 0,5 m) → pas une vraie mitoyenneté.
    a = _carre(0, 0)
    b = Polygon([(10, 0), (20, 0), (20, 0.3), (10, 0.3)])
    assert 0 < longueur_frontiere_partagee(a, b) <= 0.5
    assert contiguite_graphe({"A": a, "B": b})["ok"] is False


def test_une_seule_parcelle_est_valide():
    assert contiguite_graphe({"A": _carre(0, 0)})["ok"] is True


def test_qualite_geometrique_etiquettes():
    assert qualite_geometrique(True, 0.80) == "régulière"
    assert qualite_geometrique(True, 0.26) == "irrégulière"
    assert qualite_geometrique(False, 0.80) == "invalide"
    assert qualite_geometrique(True, None) == "non mesurée"


# ---- Validation complète sur de vraies parcelles ------------------------------------------------

_ETANG = ["97404000AW0099", "97404000AW0451", "97404000AW0624", "97404000AW0625"]


@pytest.fixture(scope="module")
def session_reelle():
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from labuse.db import make_engine

    url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent (base applicative non définie)")
    eng = make_engine(url=url)
    s = sessionmaker(bind=eng, future=True)()
    n = s.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"), {"i": _ETANG}).scalar()
    if n != len(_ETANG):
        s.close()
        pytest.skip("parcelles témoins absentes de la base")
    yield s
    s.close()


@pytest.mark.reel
def test_etang_sale_contigu_et_sourcé(session_reelle):
    out = valider_parcelles(session_reelle, _ETANG)
    assert out["contiguite"]["ok"] is True
    assert out["union"]["nb_parcelles"] == 4
    # contenance cadastrale servie = 1746 m² (501+586+274+385), jamais recalculée depuis la géométrie
    assert out["union"]["aire_cadastrale_m2"] == pytest.approx(1746.0, abs=0.5)
    assert out["signaux"]["communes_differentes"] is None   # toutes à L'Étang-Salé
    # chaque parcelle porte sa référence, sa zone et sa qualité
    aw451 = next(p for p in out["parcelles"] if p["idu"].endswith("AW0451"))
    assert aw451["zone_plu"] == "UA"
    assert aw451["qualite_geometrique"] == "irrégulière"   # Polsby-Popper 0,26
    assert out["sources"]["cadastre"]["source"] == "Cadastre (API Carto PCI)"


@pytest.mark.reel
def test_parcelles_non_contigues_refusees(session_reelle):
    # Une parcelle d'Étang-Salé + une de Saint-Leu : éloignées → refus + signal communes différentes.
    out = valider_parcelles(session_reelle, ["97404000AW0099", "97413000AC0264"])
    assert out["contiguite"]["ok"] is False
    assert out["contiguite"]["message"] == MSG_NON_CONTIGUES
    assert out["signaux"]["communes_differentes"] == ["L'Étang-Salé", "Saint-Leu"]


@pytest.mark.reel
def test_reference_introuvable_leve(session_reelle):
    with pytest.raises(ValueError, match="introuvable"):
        valider_parcelles(session_reelle, ["97404000AW9999"])
