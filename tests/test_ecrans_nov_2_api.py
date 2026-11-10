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


def test_cohort_where_multi():
    # cases à cocher MULTIPLES : bandes (estimées) UNION statuts ; prospection : niveaux.
    p = {}
    w = persist._cohort_where("potential", ["A", "B"], [], [], p)
    assert "ESTIMATED" in w and ":c_bands" in w and p["c_bands"] == ["A", "B"]
    p = {}
    w = persist._cohort_where("potential", ["A"], ["TO_VERIFY"], [], p)
    assert " OR " in w and p["c_bands"] == ["A"] and p["c_statuts"] == ["TO_VERIFY"]
    p = {}
    assert ":c_niv" in persist._cohort_where("sale", [], [], ["fort", "moyen"], p)
    assert p["c_niv"] == ["fort", "moyen"]
    # rien de coché ⇒ liste vide (AND FALSE)
    assert "FALSE" in persist._cohort_where("potential", [], [], [], {})
    assert "FALSE" in persist._cohort_where("sale", [], [], [], {})


def test_n_coche_derive_des_effectifs():
    eff = {"par_bande": {"A": 10, "B": 20, "C": 5}, "par_statut": {"TO_VERIFY": 7},
           "par_signal": {"fort": 3, "faible": 9}}
    assert persist._n_coche(eff, "potential", ["A", "B"], [], []) == 30
    assert persist._n_coche(eff, "potential", ["A"], ["TO_VERIFY"], []) == 17
    assert persist._n_coche(eff, "sale", [], [], ["fort"]) == 3


_SEL = "SELECT idu FROM parcels WHERE commune = :selc"


@_reel
def test_payload_filtre_effectifs_font_le_total(sess):
    d = persist.analyse_payload_filtre(sess, scn_run="q_v20", mode="potential", scenario="keep",
                                       sort=None, sel_sql=_SEL, sel_params={"selc": "Entre-Deux"},
                                       bands=["A", "B", "C", "D"],
                                       statuts=["TO_VERIFY", "DEFERRED", "NO_MARGIN", "OUTSIDE_OBJECTIVE", "COMPUTE_PENDING"],
                                       limit=5)
    assert sum(d["effectifs"]["par_statut"].values()) == d["n_selection"]       # font le total
    # toutes les cohortes cochées → n_filtre = n_selection (hors PRESTUDY, absent du parc potentiel)
    assert d["n_filtre"] == d["n_selection"]
    assert d["page"]["n"] <= 5


@_reel
def test_payload_filtre_cohortes_narrowent_la_liste_pas_les_effectifs(sess):
    base = persist.analyse_payload_filtre(sess, scn_run="q_v20", mode="potential", scenario="keep",
                                          sort=None, sel_sql=_SEL, sel_params={"selc": "Entre-Deux"},
                                          limit=5)
    # Excellente + Bonne cochées (défaut maquette)
    filt = persist.analyse_payload_filtre(sess, scn_run="q_v20", mode="potential", scenario="keep",
                                          sort=None, sel_sql=_SEL, sel_params={"selc": "Entre-Deux"},
                                          bands=["A", "B"], limit=5)
    assert filt["effectifs"] == base["effectifs"]                              # effectifs intacts
    pb = base["effectifs"]["par_bande"]
    assert filt["n_filtre"] == pb.get("A", 0) + pb.get("B", 0)                 # N = somme cochée
    assert all(p["statut"] == "ESTIMATED" and p["bande"] in ("A", "B") for p in filt["parcelles"])
    # limit=0 (étape « Choisir ») : effectifs seuls, pas de liste
    choisir = persist.analyse_payload_filtre(sess, scn_run="q_v20", mode="potential", scenario="keep",
                                             sort=None, sel_sql=_SEL, sel_params={"selc": "Entre-Deux"},
                                             bands=["A"], limit=0)
    assert choisir["parcelles"] == [] and choisir["effectifs"] == base["effectifs"]


@_reel
def test_le_scenario_change_les_effectifs(sess):
    # BUG Vic (4) : la reconstruction NE DOIT PAS servir les effectifs du bâti conservé.
    keep = persist.effectifs_filtre(sess, scn_run="q_v20", mode="potential", scenario="keep",
                                    sel_sql="SELECT idu FROM parcels", sel_params={})
    reb = persist.effectifs_filtre(sess, scn_run="q_v20", mode="potential", scenario="rebuild",
                                   sel_sql="SELECT idu FROM parcels", sel_params={})
    # conservation : « Aucun ajout » existe, « Calcul à compléter » non
    assert keep["par_statut"].get("NO_MARGIN", 0) > 0
    assert keep["par_statut"].get("COMPUTE_PENDING", 0) == 0
    # reconstruction : l'INVERSE (la plupart « Calcul à compléter », aucun « Aucun ajout »)
    assert reb["par_statut"].get("COMPUTE_PENDING", 0) > 0
    assert reb["par_statut"].get("NO_MARGIN", 0) == 0
    assert keep["par_statut"] != reb["par_statut"]


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
