"""OUTIL-ASSEMBLAGE-FIX-5 — filet (LOT 0) des deux compléments de la relecture-3.

Fige avant de coder (test-first). Sur le code d'avant le correctif, chacun échoue sur SON comportement :
  · LOT 1 — ZAC Marie Caze / Sans Souci : aucune n'a de zone/secteur dédié dans le zonage → les parcelles
            DÉCLENCHÉES de U4a/U4b/U4c portent un avertissement nommé ; aucun euro ne bouge ;
  · LOT 2 — Usdu (sans numéro de livret dans son nom) : la page vient du LIVRET rattaché par la géographie
            (page `None` par le seul nom) ; livret → page de mixité du livret ;
  · LOT 3 — ZAC Savane des Tamarins : l'écran dit que la ZAC a son PROPRE programme, « non chiffré ici ».
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.faisabilite.bilan import _clause_mixite, _zone_mixite_regle, compute_bilan
from labuse.faisabilite.engine import Hypotheses


def _prix_fiable():
    return {"q1": 4000.0, "median": 4500.0, "q3": 5000.0, "fiabilite": "fiable", "fiable": True,
            "type_prix": "prix observé", "n": 10, "n_exclus": 0, "n_doublons": 0,
            "periode": ("2022", "2026"), "radius_m": 500, "min": 3500.0, "max": 5500.0}


# ───────────────── LOT 1 — Marie Caze / Sans Souci : avert sur U4a/U4b/U4c déclenchées, pas ailleurs ─────────────────

def test_lot1_u4_zones_portent_lavert_marie_caze_sans_souci():
    from labuse.faisabilite.bilan import _zac_marie_caze_sans_souci
    for z in ("U4a", "U4b", "U4c"):
        assert _zac_marie_caze_sans_souci("Saint-Paul", z) is True
    for z in ("U3c", "U5a", "AU3st", "U4"):
        assert _zac_marie_caze_sans_souci("Saint-Paul", z) is False


def test_lot1_avert_present_et_nomme_les_deux_zac_sans_bouger_les_euros():
    hyp = Hypotheses.charger("Saint-Paul")
    eco = {"commune": "Saint-Paul", "mixite": True, "zac_avert_u4": True,
           "zone_mixite": {"article": None, "page": "p. 168"},
           "sdp_programme_m2": 2500.0, "logements_estimes": 30, "terrain_m2": 500.0, "sdp_max_m2": 2500.0}
    b = compute_bilan(1200.0, 500.0, _prix_fiable(), hyp, contexte_eco=eco)
    assert b.mixite["declenchee"] is True                        # la clause s'applique (pas d'exemption)
    assert any("Marie Caze" in a and "Sans Souci" in a for a in b.avertissements)
    assert any("périmètre de ces ZAC n'est pas disponible" in a for a in b.avertissements)
    # même bilan SANS le flag → CA identique (l'avert ne change aucun euro)
    eco2 = {k: v for k, v in eco.items() if k != "zac_avert_u4"}
    b2 = compute_bilan(1200.0, 500.0, _prix_fiable(), hyp, contexte_eco=eco2)
    assert b.ca["central"] == b2.ca["central"]
    assert not any("Marie Caze" in a for a in b2.avertissements)


# ───────────────── LOT 2 — Usdu : page du livret rattaché (le nom seul ne donne aucune page) ─────────────────

def test_lot2_usdu_par_le_nom_seul_na_pas_de_page():
    # « Usdu » n'a pas de numéro de livret → `_zone_mixite_regle` (basé sur le nom) ne résout aucune page.
    assert _zone_mixite_regle("Saint-Paul", "Usdu", None) is None


def test_lot2_usdu_page_du_livret_rattache_live():
    """Live : une parcelle Usdu réelle reçoit la page de mixité de SON livret (pp.106-107/168/214/274),
    ou None si à cheval. Skippe hors recette."""
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        pytest.skip("base APP injoignable")
    from labuse.faisabilite.bilan import _usdu_livret_page, _SP_LIVRET_PAGE
    eng = create_engine(url, future=True)
    pages_livret = set(_SP_LIVRET_PAGE[liv] for liv in (3, 4, 5, 6))
    with Session(eng) as db:
        db.execute(text("SET default_transaction_read_only = on"))
        rows = db.execute(text("""SELECT p.id FROM parcels p JOIN parcel_zone_plu z ON z.idu=p.idu
            WHERE p.commune='Saint-Paul' AND z.zone_lib='Usdu' LIMIT 15""")).all()
        if not rows:
            pytest.skip("pas de parcelle Usdu en base")
        got = [_usdu_livret_page(db, r[0]) for r in rows]
    assert all(g is None or g in pages_livret for g in got)
    assert any(g in pages_livret for g in got)      # au moins une rattachée


# ───────────────── LOT 3 — ZAC Savane : programme propre, « non chiffré ici » ─────────────────

def test_lot3_savane_dit_programme_propre_non_chiffre():
    hyp = Hypotheses.charger("Saint-Paul")
    eco = {"commune": "Saint-Paul", "mixite": True, "zac_mixite_exclue": True,
           "zone_mixite": {"article": None, "page": "pp. 106-107"},
           "sdp_programme_m2": 2500.0, "logements_estimes": 30, "terrain_m2": 5000.0, "sdp_max_m2": 2500.0}
    b = compute_bilan(1200.0, 5000.0, _prix_fiable(), hyp, contexte_eco=eco)
    d = b.mixite["detail"] or ""
    assert b.mixite["declenchee"] is False
    assert "PROPRE programme" in d or "propre programme" in d.lower()
    assert "non chiffré ici" in d
