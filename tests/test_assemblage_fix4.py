"""OUTIL-ASSEMBLAGE-FIX-4 — filet (LOT 0) du mandat relecture-assemblage-3.

Fige les quatre corrections avant de les coder (test-first). Sur le code d'avant le correctif, chacun
échoue sur SON comportement :
  · LOT 1 — toute zone de Saint-Paul cite la page de SON livret (vérifiée au PDF 97415), jamais le repli
            commune-wide « pp. 14-15 » hors livret 1 ; une zone sans page connue n'en cite aucune ;
  · LOT 2 — la ZAC Savane des Tamarins = la zone AU3st : ses parcelles (et elles seules) sont EXEMPTÉES
            et le disent ; une parcelle U3/AU3c hors ZAC ne porte plus l'avertissement « non vérifiable » ;
  · LOT 3 — une obligation de Saint-Denis cite le règlement de SA commune, jamais « (Saint-Paul) » ;
  · LOT 4 — les zones AUj/AUm/AUh de Saint-Denis portent la clause (Uma, maison d'arrêt, ne l'a PAS).
"""
from __future__ import annotations

import pytest

from labuse.faisabilite.bilan import _clause_mixite, _zone_mixite_regle, compute_bilan
from labuse.faisabilite.engine import Hypotheses


def _prix_fiable():
    return {"q1": 4000.0, "median": 4500.0, "q3": 5000.0, "fiabilite": "fiable", "fiable": True,
            "type_prix": "prix observé", "n": 10, "n_exclus": 0, "n_doublons": 0,
            "periode": ("2022", "2026"), "radius_m": 500, "min": 3500.0, "max": 5500.0}


# ───────────────── LOT 1 — page du LIVRET pour toute zone de Saint-Paul (jamais « pp. 14-15 » hors L1) ─────────────────

# zone → page attendue (vérifiée dans le PDF 97415 : livret 2 p.67, livret 3 pp.106-107, livret 5 p.214,
# livret 6 p.274). AU3st et AU3e = livret 3 ; AU5st et AU5e = livret 5 ; AU6st = livret 6 ; U2h/AU2h/U2e = livret 2.
_SP_ZONES_FILET = {
    "AU3st": "pp. 106-107", "AU3e": "pp. 106-107", "AU5st": "p. 214", "AU5e": "p. 214",
    "AU6st": "p. 274", "U2h": "p. 67", "AU2h": "p. 67", "U2e": "p. 67",
}


@pytest.mark.parametrize("zone,page", sorted(_SP_ZONES_FILET.items()))
def test_lot1_page_du_livret_jamais_14_15(zone, page):
    r = _zone_mixite_regle("Saint-Paul", zone, None)
    assert r is not None, f"{zone} : aucune règle de mixité résolue (pré-correctif : leaf absent)"
    assert r["page"] == page, f"{zone} : page {r['page']!r}, attendu {page!r}"
    assert r["page"] != "pp. 14-15"


def test_lot1_plus_de_repli_commune_wide_14_15():
    """Sans page de zone, la clause ne cite AUCUNE page (fin du repli `hyp.mixite_page` = « pp. 14-15 »)."""
    hyp = Hypotheses.charger("Saint-Paul")
    eco = {"zone_mixite": {"article": "Art. 2", "page": None}, "mixite": True,
           "sdp_programme_m2": 2000.0, "logements_estimes": 25, "terrain_m2": 500.0, "sdp_max_m2": 2000.0}
    c = _clause_mixite(eco, hyp)
    assert c["page"] is None
    assert c["page"] != "pp. 14-15"


# ───────────────── LOT 2 — ZAC Savane des Tamarins = AU3st : exemptée ; U3/AU3c hors ZAC : pas d'avert ─────────────────

def test_lot2_au3st_est_le_perimetre_de_la_zac():
    from labuse.faisabilite.bilan import _zac_savane_tamarins
    assert _zac_savane_tamarins("Saint-Paul", "AU3st") is True
    assert _zac_savane_tamarins("Saint-Paul", "U3c") is False
    assert _zac_savane_tamarins("Saint-Denis", "AU3st") is False


def test_lot2_au3st_exemptee_et_le_dit():
    hyp = Hypotheses.charger("Saint-Paul")
    eco = {"commune": "Saint-Paul", "mixite": True, "zac_mixite_exclue": True,
           "zone_mixite": {"article": None, "page": "pp. 106-107"},
           "sdp_programme_m2": 2500.0, "logements_estimes": 30, "terrain_m2": 5000.0, "sdp_max_m2": 2500.0}
    b = compute_bilan(1200.0, 5000.0, _prix_fiable(), hyp, contexte_eco=eco)
    assert b.mixite is not None and b.mixite["declenchee"] is False
    assert "ZAC Savane des Tamarins" in (b.mixite["detail"] or "")
    assert "non applicable" in (b.mixite["detail"] or "")


def test_lot2_u3_hors_zac_pas_davert_non_verifiable():
    hyp = Hypotheses.charger("Saint-Paul")
    eco = {"commune": "Saint-Paul", "mixite": True, "zone_mixite": {"article": None, "page": "pp. 106-107"},
           "sdp_programme_m2": 2500.0, "logements_estimes": 30, "terrain_m2": 500.0, "sdp_max_m2": 2500.0}
    b = compute_bilan(1200.0, 500.0, _prix_fiable(), hyp, contexte_eco=eco)
    assert not any("non vérifiable" in a for a in b.avertissements)
    assert b.mixite["declenchee"] is True          # la clause s'applique bien (hors ZAC)
    assert b.mixite["page"] == "pp. 106-107"


# ───────────────── LOT 3 — une obligation de Saint-Denis cite SA commune, jamais « (Saint-Paul) » ─────────────────

def test_lot3_source_saint_denis_jamais_saint_paul():
    hyp = Hypotheses.charger("Saint-Denis")
    eco = {"commune": "Saint-Denis",
           "zone_mixite": {"seuil_logements": 30, "quota_pct": 15, "article": "Article Uavap.2", "page": "p. 27"},
           "logements_estimes": 35, "sdp_programme_m2": 0.0, "sdp_max_m2": 0.0, "terrain_m2": 500.0}
    b = compute_bilan(1000.0, 500.0, _prix_fiable(), hyp, contexte_eco=eco)
    src = (b.mixite or {}).get("source") or ""
    assert "Saint-Paul" not in src
    assert "Saint-Denis" in src


# ───────────────── LOT 4 — AUj/AUm/AUh de Saint-Denis portent la clause ; Uma (maison d'arrêt) NON ─────────────────

@pytest.mark.parametrize("zone,page", [("AUj", "p. 91"), ("AUm", "p. 97"), ("AUh", "p. 101")])
def test_lot4_saint_denis_au_zones_armees(zone, page):
    r = _zone_mixite_regle("Saint-Denis", zone, None)
    assert r is not None and r["seuil_logements"] == 30 and r["quota_pct"] == 15
    assert r["page"] == page


def test_lot4_uma_non_armee():
    # Uma = « Zone urbaine de la maison d'arrêt » (PDF p.86, Article Uma.2) : AUCUNE clause de mixité.
    assert _zone_mixite_regle("Saint-Denis", "Uma", None) is None
