"""OUTIL-ASSEMBLAGE-FIX-3 — filet (LOT 0) du mandat relecture-assemblage-2.

Ces tests FIGENT les cinq corrections de FIX-3 ; ils échouent (ROUGE) sur le code d'avant le correctif :
  · LOT 2 — la page de mixité AFFICHÉE vient de la ZONE de la parcelle (pas d'une page commune-wide) ;
  · LOT 3 — Saint-Denis Uavap.2 : obligation de ZONE armée au nombre de logements (≥ 30 → 15 %) ;
  · LOT 1 — la mention de mixité (+ borne haute) voyage à la MÊME source que l'écran dans
            la Calculette/le Comparatif (clé `mixite`), plus un chiffre sans sa réserve ;
  · LOT 5 — exclusion ZAC extraite du texte de la zone ET dite « non vérifiable » faute de périmètre ;
  · LOT 4 — (live) l'assemblage tout-introuvable NOMME les identifiants fautifs dans le 404.

Les tests PURS (sans base) sont le cœur du filet ; les tests LIVE se skippent proprement hors recette.
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.faisabilite.bilan import _clause_mixite, compute_bilan, compute_calculette
from labuse.faisabilite.engine import Hypotheses

# `_zone_mixite_regle` est NÉ avec FIX-3 : on l'importe DANS les tests LOT 5 (lazy) pour que, sur le code
# d'avant le correctif, ces tests échouent sur l'ABSENCE de la fonction — pas la collecte entière du module
# (les autres LOT échouent alors chacun sur SON comportement : page figée, régime/quota faux, clé absente).


# ───────────────────────── LOT 3 — obligation de ZONE Saint-Denis (Uavap.2) ─────────────────────────

def test_lot3_saint_denis_uavap_arme_a_30_logements():
    """Uavap.2 p.27 : « 30 logements collectif et plus → 15 % social ». Le bilan l'IGNORAIT (SMS-only)."""
    hyp = Hypotheses.charger("Saint-Denis")
    zm = {"seuil_logements": 30, "quota_pct": 15, "article": "Article Uavap.2", "page": "p. 27"}
    eco = {"zone_mixite": zm, "logements_estimes": 35, "sdp_programme_m2": 0.0,
           "sdp_max_m2": 0.0, "terrain_m2": 500.0}
    c = _clause_mixite(eco, hyp)
    assert c["declenchee"] is True
    assert c["regime"] == "intermediaire"          # borne haute (prix social non calibré)
    assert float(c["quota_pct"]) == 15.0
    assert c["article"] == "Article Uavap.2" and c["page"] == "p. 27"


def test_lot3_saint_denis_sous_le_seuil_pas_de_clause():
    hyp = Hypotheses.charger("Saint-Denis")
    zm = {"seuil_logements": 30, "quota_pct": 15, "article": "Article Uavap.2", "page": "p. 27"}
    eco = {"zone_mixite": zm, "logements_estimes": 20, "sdp_programme_m2": 0.0,
           "sdp_max_m2": 0.0, "terrain_m2": 500.0}
    assert _clause_mixite(eco, hyp)["declenchee"] is False


# ───────────────────────── LOT 2 — page de mixité PAR ZONE (pas commune-wide) ─────────────────────────

def test_lot2_page_vient_de_la_zone_pas_du_defaut_commune():
    """Trio CV (AU3c) : l'Art. 2 est en pp. 106-107 dans SON livret, pas « pp. 14-15 » (livret U1)."""
    hyp = Hypotheses.charger("Saint-Paul")
    assert hyp.mixite_sdp_seuil_haut_m2 >= 1800.0   # régime à bandes requis pour ce test
    eco = {"zone_mixite": {"article": "Art. 2 (zones U1 à U6)", "page": "pp. 106-107"},
           "sdp_programme_m2": 2000.0, "logements_estimes": 25, "terrain_m2": 500.0,
           "sdp_max_m2": 2000.0}
    c = _clause_mixite(eco, hyp)
    assert c["declenchee"] is True
    assert c["page"] == "pp. 106-107"
    assert c["page"] != "pp. 14-15"


# ───────────────────────── LOT 5 — exclusion ZAC extraite + « non vérifiable » ─────────────────────────

class _FakeRules:
    """`rules` minimal pour `_zone_mixite_regle` : porte un leaf `mixite` (forme plu_zonage)."""
    def __init__(self, mixite):
        self.mixite = mixite


def test_lot5_zone_mixite_extrait_les_zac_exclues():
    from labuse.faisabilite.bilan import _zone_mixite_regle
    # commune/zone à None → on reste sur le leaf `rules.mixite` (pas d'accès base), on teste l'extraction.
    leaf = {"article": "Art. 2", "page_pdf": 106,
            "condition": "programme ≥ 1 800 m² → 30 % aidés ; non applicable dans la ZAC Savane des Tamarins"}
    zm = _zone_mixite_regle(None, None, _FakeRules(leaf))
    assert zm is not None
    assert zm["zac_exclusions"] == ["Savane des Tamarins"]


def test_lot5_deux_zac_exclues_toutes_nommees():
    from labuse.faisabilite.bilan import _zone_mixite_regle
    leaf = {"article": "Art. 2", "page_pdf": 50,
            "condition": "mixité … ; ne s'applique pas dans la ZAC Marie Caze et la ZAC Sans Souci "
                         "(calcul à l'échelle de l'opération)"}
    zm = _zone_mixite_regle(None, None, _FakeRules(leaf))
    assert zm["zac_exclusions"] == ["Marie Caze", "Sans Souci"]


def _prix_fiable():
    return {"q1": 4000.0, "median": 4500.0, "q3": 5000.0, "fiabilite": "fiable", "fiable": True,
            "type_prix": "prix observé", "n": 10, "n_exclus": 0, "n_doublons": 0,
            "periode": ("2022", "2026"), "radius_m": 500, "secteur": "Saint-Paul",
            "min": 3500.0, "max": 5500.0}


def test_lot5_exclusion_non_verifiable_dite_quand_pas_de_perimetre():
    """Clause déclenchée + ZAC exclue dans le texte + AUCUN périmètre armé → avertissement explicite."""
    hyp = Hypotheses.charger("Saint-Paul")
    eco = {"mixite": True, "mixite_libelle": "logements aidés",
           "zone_mixite": {"article": "Art. 2", "page": "pp. 106-107",
                           "zac_exclusions": ["Savane des Tamarins"]},
           "sdp_programme_m2": 2000.0, "logements_estimes": 25, "terrain_m2": 500.0, "sdp_max_m2": 2000.0}
    b = compute_bilan(1000.0, 500.0, _prix_fiable(), hyp, contexte_eco=eco)
    assert any("Exclusion ZAC non vérifiable" in a for a in b.avertissements)
    assert any("Savane des Tamarins" in a for a in b.avertissements)


def test_lot5_perimetre_arme_exclut_la_clause_sans_avertissement():
    """Si un périmètre ZAC est armé (`zac_mixite_exclue`), la clause est écartée (pas d'avertissement « non vérifiable »)."""
    hyp = Hypotheses.charger("Saint-Paul")
    eco = {"mixite": True, "zac_mixite_exclue": True,
           "zone_mixite": {"article": "Art. 2", "page": "pp. 106-107",
                           "zac_exclusions": ["Savane des Tamarins"]},
           "sdp_programme_m2": 2000.0, "logements_estimes": 25, "terrain_m2": 500.0, "sdp_max_m2": 2000.0}
    b = compute_bilan(1000.0, 500.0, _prix_fiable(), hyp, contexte_eco=eco)
    assert not any("Exclusion ZAC non vérifiable" in a for a in b.avertissements)


# ───────────────────────── LOT 1 — source unique : Calculette & Comparatif portent la mixité ─────────────────────────

def test_lot1_calculette_expose_la_mixite():
    """Le PDF premium lit `calc["mixite"]` : la Calculette DOIT l'exposer (avant : absente → divergence)."""
    hyp = Hypotheses.charger("Saint-Denis")
    eco = {"zone_mixite": {"seuil_logements": 30, "quota_pct": 15, "article": "Article Uavap.2",
                           "page": "p. 27"}, "logements_estimes": 35,
           "sdp_programme_m2": 0.0, "sdp_max_m2": 0.0, "terrain_m2": 500.0}
    res = compute_calculette(1000.0, 500.0, _prix_fiable(), 2200.0, 18.0, contexte_eco=eco, hyp=hyp)
    assert res.get("calculable") is True
    assert "mixite" in res
    assert isinstance(res["mixite"], dict) and res["mixite"].get("servitude") is True
    assert res["mixite"].get("declenchee") is True


def test_lot1_comparatif_affiche_borne_haute():
    from labuse.exports.blocs.comparatif import _mixite_txt
    r = {"charge_fonciere_m2": 120.0, "bilan_hypotheses": ["…"],
         "mixite": {"servitude": True, "declenchee": True, "quota_pct": 15,
                    "produits": "logements sociaux et/ou intermédiaires",
                    "article": "Article Uavap.2", "page": "p. 27", "borne_haute": True}}
    txt = _mixite_txt(r)
    assert txt and "15" in txt
    assert "borne haute" in txt.lower()
    assert "Uavap.2" in txt and "p. 27" in txt


def test_lot1_comparatif_muet_sans_charge():
    from labuse.exports.blocs.comparatif import _mixite_txt
    # pas de charge présentable → pas de mention (on ne pose pas une réserve sur un bilan absent).
    assert _mixite_txt({"mixite": {"servitude": True, "declenchee": True}}) is None


def test_lot3_libelle_zone_pas_servitude_pour_saint_denis():
    """relecture-2 : une obligation de ZONE (Saint-Denis) ne se présente pas en « servitude/secteur »."""
    from labuse.exports.blocs.comparatif import _mixite_txt
    r = {"charge_fonciere_m2": 100.0, "bilan_hypotheses": ["…"],
         "mixite": {"servitude": True, "declenchee": False, "origine": "zone_reglement",
                    "article": "Article Uavap.2", "page": "p. 27"}}
    txt = _mixite_txt(r)
    assert "règlement de zone" in txt
    assert "Secteur de mixité sociale" not in txt
    # un secteur SMS (Saint-Paul) garde l'ancien libellé
    r2 = {**r, "mixite": {**r["mixite"], "origine": "secteur_sms"}}
    assert "Secteur de mixité sociale" in _mixite_txt(r2)


# ───────────────────────── LOT 4 — (live) assemblage tout-introuvable NOMME les ids ─────────────────────────

def _client():
    """TestClient sur l'app, base APP en lecture seule ; None si injoignable (skip hors recette)."""
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        return None
    try:
        from fastapi.testclient import TestClient
        from labuse.api.app import app
        eng = create_engine(url, future=True)
        with Session(eng) as s:
            s.execute(text("SELECT 1"))
        return TestClient(app)
    except Exception:
        return None


def test_lot4_assemblage_tout_introuvable_nomme_les_ids():
    client = _client()
    if client is None:
        pytest.skip("base APP injoignable")
    bogus = ["97999000ZZ9991", "97999000ZZ9992"]
    r = client.post("/moteurs/assemblage", json={"idus": bogus})
    assert r.status_code == 404
    detail = r.json().get("detail")
    assert isinstance(detail, dict), f"404 doit porter un détail structuré, reçu : {detail!r}"
    assert set(detail.get("introuvables") or []) == set(bogus)
    for i in bogus:
        assert i in detail.get("message", "")
