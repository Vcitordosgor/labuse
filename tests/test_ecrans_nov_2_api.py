"""ECRANS-NOV-2 — recette d'Astra côté API pour l'écran « Analyse LABUSE par scénario ».

Trois points : (1) codes AU PHASÉS (1AU, 2AU, 1AUc) reconnus ; (2) puces comptées qui NARROWENT
la liste sans toucher les effectifs + rangée de puces de prospection (fort/moyen/faible/non_evalue)
qui « font le total » ; (3) échec d'enrichissement remonté EXPLICITEMENT dans la réponse.

Les contrôles purs (regex AU, helpers de puce) tournent sans base ; les contrôles sur la sélection
réelle sont gardés par `LABUSE_REEL_DATABASE_URL` (comme test_algofix1_persist.py).
"""
from __future__ import annotations

import os

import pytest

from labuse.scoring import scenarios_v2_build as build
from labuse.scoring import scenarios_v2_persist as persist

pytestmark = pytest.mark.local


def _motif(zone: str) -> dict:
    return {"layer": "zonage_plu_gpu", "result": "POSITIVE",
            "detail": f"Zone PLU « {zone} » retenue, constructible"}


# ── (1) codes AU phasés reconnus ────────────────────────────────────────────
@pytest.mark.parametrize("zone,attendu", [
    ("AU", "AU"), ("AUc", "AU"),
    ("1AU", "AU"), ("2AU", "AU"), ("1AUc", "AU"), ("2AUm", "AU"),   # PHASÉS : le fix
    ("U", "U"), ("Ub", "U"), ("UA", "U"),
    ("A", None), ("N", None),                                        # ni U ni AU
])
def test_famille_portion_productive_reconnait_au_phasee(zone, attendu):
    assert build._famille_portion_productive([_motif(zone)]) == attendu


def test_au_phasee_prime_sur_u():
    # une portion AU (même phasée) commande l'horizon face à une portion U.
    assert build._famille_portion_productive([_motif("Ub"), _motif("1AU")]) == "AU"


# ── (2) puces : helpers purs ────────────────────────────────────────────────
def test_niveau_chip():
    assert persist._niveau_chip({"status": "AVAILABLE", "niveau": "fort"}) == "fort"
    assert persist._niveau_chip({"status": "AVAILABLE", "niveau": None}) == "non_evalue"
    assert persist._niveau_chip({"status": "NOT_AVAILABLE", "niveau": "fort"}) == "non_evalue"
    assert persist._niveau_chip({"status": "TO_VERIFY", "niveau": None}) == "non_evalue"


def test_passe_chip_potentiel_bande_et_statut():
    estime_A = {"statut": "ESTIMATED", "bande": "A", "signal": {}}
    estime_B = {"statut": "ESTIMATED", "bande": "B", "signal": {}}
    a_verifier = {"statut": "TO_VERIFY", "bande": None, "signal": {}}
    f = persist._passe_chip
    assert f(estime_A, "potential", band="A", statut=None, signal_niveau=None)
    assert not f(estime_B, "potential", band="A", statut=None, signal_niveau=None)
    # une parcelle NON estimée ne passe jamais une puce de bande (la bande = estimées)
    assert not f(a_verifier, "potential", band="A", statut=None, signal_niveau=None)
    assert f(a_verifier, "potential", band=None, statut="TO_VERIFY", signal_niveau=None)
    assert not f(estime_A, "potential", band=None, statut="TO_VERIFY", signal_niveau=None)


def test_passe_chip_prospection_niveau():
    fort = {"signal": {"status": "AVAILABLE", "niveau": "fort"}}
    faible = {"signal": {"status": "AVAILABLE", "niveau": "faible"}}
    f = persist._passe_chip
    assert f(fort, "sale", band=None, statut=None, signal_niveau="fort")
    assert not f(faible, "sale", band=None, statut=None, signal_niveau="fort")
    assert f(faible, "sale", band=None, statut=None, signal_niveau=None)   # « Tous »


# ── contrôles sur la sélection réelle (DB) ───────────────────────────────────
REEL = os.environ.get("LABUSE_REEL_DATABASE_URL")
_reel = pytest.mark.skipif(not REEL, reason="LABUSE_REEL_DATABASE_URL non défini")


@pytest.fixture()
def sess():
    from sqlalchemy.orm import Session
    from labuse.db import make_engine
    eng = make_engine(REEL)
    s = Session(eng)
    try:
        yield s
    finally:
        s.close()


@_reel
def test_puce_bande_narrowe_liste_pas_effectifs(sess):
    base = persist.analyse_payload_persiste(sess, run_label="q_v20", mode="potential",
                                            scenario="keep", sort=None, commune="Entre-Deux",
                                            limit=1000)
    filt = persist.analyse_payload_persiste(sess, run_label="q_v20", mode="potential",
                                            scenario="keep", sort=None, commune="Entre-Deux",
                                            band="A", limit=1000)
    # effectifs INCHANGÉS (ils font le total), liste narrowée à la bande A.
    assert filt["effectifs"] == base["effectifs"]
    assert filt["n_selection"] == base["n_selection"]
    attendu = base["effectifs"]["par_bande"].get("A", 0)
    assert filt["n_filtre"] == attendu
    assert all(p["statut"] == "ESTIMATED" and p["bande"] == "A" for p in filt["parcelles"])


@_reel
def test_prospection_par_signal_fait_le_total(sess):
    d = persist.analyse_payload_persiste(sess, run_label="q_v20", mode="sale", scenario="keep",
                                         sort=None, commune="Entre-Deux", limit=1)
    ps = d["effectifs"]["par_signal"]
    assert set(ps) <= {"fort", "moyen", "faible", "non_evalue"}
    assert sum(ps.values()) == d["n_selection"]                     # « font le total »


# ── sélection par le JEU DE FILTRES COMPLET (ECRANS-NOV-2, placement) ────────
def test_order_by_potential():
    assert "project_total_m2 DESC" in persist._order_by_potential("rebuild", "capacity")
    assert "additional_m2 DESC" in persist._order_by_potential("keep", "capacity")
    assert "net_signed_m2 DESC" in persist._order_by_potential("rebuild", "gain")
    assert "surface_m2 DESC" in persist._order_by_potential("keep", "area")


def test_chip_where_potentiel_et_prospection():
    p = {}
    assert "ESTIMATED" in persist._chip_where("potential", "A", None, None, p) and p["chip_band"] == "A"
    p = {}
    assert persist._chip_where("potential", None, "TO_VERIFY", None, p).endswith(":chip_statut")
    assert p["chip_statut"] == "TO_VERIFY"
    p = {}
    assert persist._chip_where("sale", None, None, "fort", p) and p["chip_niv"] == "fort"
    assert persist._chip_where("sale", None, None, None, {}) == ""


_SEL = "SELECT idu FROM parcels WHERE commune = :selc"


@_reel
def test_payload_filtre_effectifs_font_le_total(sess):
    d = persist.analyse_payload_filtre(sess, scn_run="q_v20", mode="potential", scenario="keep",
                                       sort=None, sel_sql=_SEL, sel_params={"selc": "Entre-Deux"},
                                       limit=5)
    assert sum(d["effectifs"]["par_statut"].values()) == d["n_selection"]       # font le total
    assert d["n_filtre"] == d["n_selection"]                                    # pas de puce
    assert d["page"]["n"] <= 5


@_reel
def test_payload_filtre_puce_narrowe_la_liste_pas_les_effectifs(sess):
    base = persist.analyse_payload_filtre(sess, scn_run="q_v20", mode="potential", scenario="keep",
                                          sort=None, sel_sql=_SEL, sel_params={"selc": "Entre-Deux"},
                                          limit=5)
    filt = persist.analyse_payload_filtre(sess, scn_run="q_v20", mode="potential", scenario="keep",
                                          sort=None, sel_sql=_SEL, sel_params={"selc": "Entre-Deux"},
                                          band="A", limit=5)
    assert filt["effectifs"] == base["effectifs"]                              # effectifs intacts
    assert filt["n_filtre"] == base["effectifs"]["par_bande"].get("A", 0)      # liste narrowée
    assert all(p["statut"] == "ESTIMATED" and p["bande"] == "A" for p in filt["parcelles"])


@_reel
def test_payload_filtre_sale_par_signal_fait_le_total(sess):
    d = persist.analyse_payload_filtre(sess, scn_run="q_v20", mode="sale", scenario="keep",
                                       sort=None, sel_sql=_SEL, sel_params={"selc": "Entre-Deux"},
                                       limit=1)
    assert sum(d["effectifs"]["par_signal"].values()) == d["n_selection"]


@_reel
def test_enrichissement_remonte_dans_la_reponse(sess):
    d = build.analyse_scenarios_payload(sess, _ids(sess, "97403000AR1154"),
                                        mode="potential", scenario="rebuild", enrich=True,
                                        run_label="q_v20", limit=1)
    assert d["enrichissement"]["demande"] is True
    assert "echecs" in d["enrichissement"]
    assert d["parcelles"][0]["etat_calcul"] in ("ok", "failed", "fallback", "not_requested")


def _ids(sess, idu):
    from sqlalchemy import text
    return [r[0] for r in sess.execute(text("SELECT id FROM parcels WHERE idu=:i"), {"i": idu})]
