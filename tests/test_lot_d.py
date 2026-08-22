"""Lot D — comparateur (D2), filtres sauvegardés (D3). M93 — D1 (one-pager) retiré avec le document."""
from __future__ import annotations

import pytest
from sqlalchemy import text

# ── Miroirs de la VRAIE source servie (formes RÉELLES de _q_v2_fiche + fiche_payload) ──
# Le comparateur lit désormais la fiche SERVIE `_q_v2_fiche` (verdict/rang/fraction/raison M135/M137)
# + la faisabilité `fiche_payload` — plus la fiche legacy `_build_fiche`. L'ANCIEN test passait un
# fiche fabriqué à la forme _build_fiche (verdict.status v1, SANS tier_v2) qui MASQUAIT le bug
# (tier_v2/rang_v2 toujours None → puce « Classement historique », rang muet). On teste les VRAIES clés.
_QV2 = {   # forme de _q_v2_fiche (score_v2 = verdict servi ; lines = cascade servie ; etage0)
    "idu": "97415000BV0912", "commune": "Saint-Paul", "surface_m2": 3948, "etage0": False,
    "score_v2": {"tier": "chaude", "rang": 15, "rang_total": 428239, "label": "À suivre",
                 "fraction": "1/4", "motif": None, "declasse": False,
                 "pourquoi": [{"signe": "+", "feature": "permis_recent", "bin": "oui",
                               "phrase": "permis récent à proximité"}]},
    "lines": [{"layer": "zonage_plu_gpu", "result": "POSITIVE", "detail": "Zone U", "weight": 3},
              {"layer": "ravine", "result": "SOFT_FLAG", "detail": "Proximité ravine", "weight": 0}],
}
_FAISAB = {   # forme de fiche_payload (faisabilité + bilan servi)
    "zone": "U6c", "constructible": True, "verdict": "R+1 · ~16-17 logts",
    "fourchette": {"surface_plancher_m2": 2555},
    "residuel": {"disponible": True, "taux_emprise_pct": 10, "sdp_residuelle_m2": 2259, "sous_densite": True},
    "bilan": {"fiable": True, "ca": {"bas": 2200000, "haut": 3400000},
              "charge_fonciere": {"central": 300000, "par_m2_terrain": 76}},
}


# ── D2 — _compare_row lit la source SERVIE (M135/M137), pas la fiche legacy ──

def test_compare_row_source_servie():
    from labuse.api.app import _compare_row
    from labuse.scoring.p_v2.libelles_client import raison_dominante
    r = _compare_row(_QV2, _FAISAB)
    # verdict SERVI : la puce dérive de tier_v2 + étage 0 ; rang + fraction + raison M135
    assert r["tier_v2"] == "chaude" and r["rang_v2"] == 15 and r["etage0"] is False
    assert r["label"] == "À suivre" and r["fraction"] == "1/4"
    assert r["raison"] == raison_dominante(_QV2["score_v2"]["pourquoi"])   # même calcul que la carte
    # faisabilité (fiche_payload) : SDP max/résiduelle + sous-densité + charge foncière
    assert r["sdp_max_m2"] == 2555 and r["sdp_residuelle_m2"] == 2259 and r["sous_densite"] is True
    assert r["charge_fonciere_m2"] == 76 and r["zone"] == "U6c" and r["constructible"] is True
    # contraintes depuis les lignes servies (le POSITIVE ne compte pas)
    assert r["n_contraintes"] == 1 and r["contraintes"] == ["Proximité ravine"]
    # charge morte RETIRÉE : plus de scores de matrice v1 dans le payload
    assert "opportunity_score" not in r and "completeness_score" not in r


@pytest.mark.db
def test_compare_endpoint_ne_leve_pas(db_session):
    """Il n'existait AUCUN test de l'endpoint /compare. Un IDU introuvable est ignoré (jamais une
    exception) et la structure {count, parcels} est toujours renvoyée."""
    from labuse.api.app import compare
    out = compare(idus="97499000ZZ9999,,  ", db=db_session)   # bogus + vides → 0 résultat, 0 crash
    assert isinstance(out, dict) and out["count"] == 0 and out["parcels"] == []


# ── D3 — filtres sauvegardés (DB) ──

@pytest.mark.db
def test_saved_filters_roundtrip(db_session):
    from labuse.api.app import SavedFilterIn, delete_filter, list_filters, save_filter
    db_session.execute(text("CREATE TABLE IF NOT EXISTS saved_filters ("
                            " id serial PRIMARY KEY, name varchar(80) NOT NULL, params jsonb NOT NULL,"
                            " created_at timestamptz NOT NULL DEFAULT now(), compte_id integer)"))
    # request=None → compte pilote (NULL) : current_compte() tolère l'appel direct hors HTTP.
    r = save_filter(SavedFilterIn(name="Mon filtre", params={"statuses": ["opportunite"], "taux": 40}), None, db=db_session)
    assert r["id"] and r["name"] == "Mon filtre"
    lst = list_filters(None, db=db_session)
    assert any(f["name"] == "Mon filtre" and f["params"]["taux"] == 40 for f in lst)
    delete_filter(r["id"], None, db=db_session)
    assert all(f["id"] != r["id"] for f in list_filters(None, db=db_session))


# ── 1.C — paramètres de bilan par secteur ──

def test_1c_compute_bilan_params_pilotent(monkeypatch):
    from labuse.faisabilite.bilan import compute_bilan
    from labuse.faisabilite.engine import Hypotheses
    h = Hypotheses()
    prix = {"fiable": True, "fiabilite": "fiable", "fiabilite_raisons": [], "type_prix": "appartement",
            "n": 40, "n_exclus": 0, "n_doublons": 0, "radius_m": 1500.0, "commune_fallback": False,
            "pct_appartement": 100, "periode": [2022, 2025], "q1": 2200, "median": 3000, "q3": 4300,
            "min": 2000, "max": 4700}
    base = compute_bilan(4600, 4500, prix, h)
    # override prix neuf + coût construction secteur → CA et coût changent
    bp = {"prix_m2_neuf": 3500, "cout_construction_m2_sdp": 3200, "cout_vrd_base": 50,
          "majoration_vrd_pente_pct": 20, "marge_cible_pct": 18, "honoraires_pct": 12, "frais_financiers_pct": 3}
    sect = compute_bilan(4600, 4500, prix, h, contexte_eco={"pente_pct": 35}, bilan_params=bp)
    assert sect.ca["central"] == round(4600 * 3500)              # prix override appliqué (flat)
    assert sect.calc["cout_vrd"] == round(50 * 1.20 * 4500)      # VRD base × (1+20% pente≥15) × terrain
    assert sect.charge_fonciere["central"] != base.charge_fonciere["central"]  # piloté par secteur


@pytest.mark.db
def test_1c_resolution_par_secteur(db_session):
    from sqlalchemy import text as _t

    from labuse.faisabilite import bilan_params as bp
    db_session.execute(_t("CREATE TABLE IF NOT EXISTS bilan_params (secteur varchar(64), param varchar(48),"
                          " value double precision, is_placeholder boolean DEFAULT false,"
                          " updated_at timestamptz DEFAULT now(), PRIMARY KEY (secteur, param))"))
    bp.save(db_session, "Le Guillaume", "cout_construction_m2_sdp", 3200.0)
    bp.save(db_session, "*", "prix_m2_lls", 2600.0)
    a = bp.resolve(db_session, "Saint-Paul Centre")
    b = bp.resolve(db_session, "Le Guillaume")
    # Le secteur « Guillaume » (3200) ne fuit PAS vers un autre secteur — qui retombe sur le
    # socle global/défaut (le socle web sourcé peut peupler '*', d'où source 'défaut' OU 'global').
    assert a["cout_construction_m2_sdp"]["value"] != 3200.0
    assert a["cout_construction_m2_sdp"]["source"] in ("défaut", "global")
    assert b["cout_construction_m2_sdp"]["value"] == 3200.0 and b["cout_construction_m2_sdp"]["source"] == "secteur"
    assert a["prix_m2_lls"]["source"] == "global" and a["prix_m2_lls"]["value"] == 2600.0
    assert "Coût de construction" in " ".join(bp.uncalibrated_critical({"cout_construction_m2_sdp": {"is_placeholder": True}}))
