"""Shortlist promoteur — logique de priorisation (pure, sans DB)."""
from __future__ import annotations

from labuse import shortlist as sl


def _row(**kw):
    base = {"idu": "97415000AA0001", "status": "opportunite", "opportunity_score": 70,
            "completeness_score": 80, "surface_m2": 2000, "sous_densite": False,
            "sdp_residuelle_m2": 0, "downgrade_reason": None, "owner_famille": "inconnu"}
    base.update(kw)
    return base


def test_priority_components_sum():
    score, comp = sl.priority_score(_row(sous_densite=True, owner_famille="public", surface_m2=5000))
    assert comp["verdict"] == 120                      # opportunité
    assert comp["opportunite"] == 70
    assert comp["fiabilite"] == 32.0                   # 80 * 0.4
    assert comp["densification"] == 25
    assert comp["economique"] == 30                    # min(5000/100, 30)
    assert comp["proprietaire"] == 18                  # public = actionnable
    assert comp["risque"] == 0
    assert score == round(sum(comp.values()), 1)


def test_opportunite_outranks_a_creuser_at_equal_score():
    opp, _ = sl.priority_score(_row(status="opportunite"))
    cre, _ = sl.priority_score(_row(status="a_creuser"))
    assert opp > cre


def test_risque_penalises():
    sans, _ = sl.priority_score(_row())
    avec, _ = sl.priority_score(_row(downgrade_reason="bande littorale"))
    assert sans - avec == 30


def test_rank_is_sorted_and_capped():
    rows = [_row(idu=f"x{i}", opportunity_score=s) for i, s in enumerate([10, 90, 50, 70, 30])]
    ranked = sl.rank_candidates(rows, pool=3)
    assert len(ranked) == 3
    scores = [r["opportunity_score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)      # priorité décroissante (verdict identique)
    assert all("_priority" in r and "_components" in r for r in ranked)


def test_rank_deterministic_tiebreak_on_idu():
    a = _row(idu="97415000BB0002", opportunity_score=50)
    b = _row(idu="97415000AA0009", opportunity_score=50)
    ranked = sl.rank_candidates([a, b])
    assert [r["idu"] for r in ranked] == ["97415000AA0009", "97415000BB0002"]


def test_assemblage_bonus_thresholds():
    assert sl.assemblage_bonus(False, 5000) == 0
    assert sl.assemblage_bonus(True, 400) == 30
    assert sl.assemblage_bonus(True, 1200) == 45        # franchit le seuil


def test_badges_actionnable_vs_pipeline():
    sujet = {"verdict_status": "opportunite",
             "potentiel_assemblage": {"possible": True},
             "proprietaire": {"famille": "public", "in_pipeline": False},
             "confiance": {"score": 80}, "ca": {"bas": 1, "central": 1, "haut": 1},
             "risque_principal": None}
    b = sl.badges(sujet)
    assert "Assemblage à vérifier" in b
    assert "À appeler" in b                             # propriétaire actionnable + pas au pipeline
    # une fois au pipeline, plus de « À appeler »
    sujet["proprietaire"]["in_pipeline"] = True
    assert "À appeler" not in sl.badges(sujet)


def test_badges_risque_et_a_consolider():
    sujet = {"verdict_status": "a_creuser",
             "potentiel_assemblage": {"possible": False},
             "proprietaire": {"famille": "inconnu", "in_pipeline": False},
             "confiance": {"score": 30}, "ca": None,
             "risque_principal": "déclassée"}
    b = sl.badges(sujet)
    assert "À surveiller" in b                          # à creuser
    assert "Risque fort" in b                           # downgrade
    assert "Données à consolider" in b                  # complétude faible + ca absent


def test_assemble_sujet_extracts_and_flags_priority():
    row = _row(idu="97415000CC0003", opportunity_score=74, completeness_score=92,
               surface_m2=9723, downgrade_reason=None, owner_famille="prive", _priority=300)
    fiche = {
        "parcel": {"commune": "Saint-Paul"},
        "verdict": {"status": "opportunite"},
        "faisabilite": {"constructible": True, "fourchette": {"niveaux": "R+2"},
                        "bilan": {"ca": {"bas": 1e6, "central": 1e6, "haut": 1e6},
                                  "charge_fonciere": {"central": 5e5, "par_m2_terrain": 250},
                                  "fiabilite": "fiable"}},
        "voisinage": {"assemblage": {"possible": True, "n_interessantes": 4, "surface_cumulee_m2": 35839}},
        "resume": {"prochaine_action": "Demander le relevé au SPF", "vigilance": ["bâti à vérifier"]},
        "prospection": {"statut_label": "Propriétaire à identifier", "in_pipeline": True},
    }
    s = sl.assemble_sujet(1, row, fiche)
    assert s["rang"] == 1
    assert s["idu"] == "97415000CC0003"
    assert s["potentiel_seul"] == "R+2"
    assert s["potentiel_assemblage"]["surface_cumulee_m2"] == 35839
    assert s["ca"]["central"] == 1e6
    assert s["charge_fonciere"]["par_m2_terrain"] == 250
    assert s["fiabilite_marche"] == "fiable"
    assert s["confiance"]["label"] == "élevée"
    assert s["badges"][0] == "Priorité du jour"        # rang 1
    assert "À appeler" not in s["badges"]               # in_pipeline


def test_assemble_sujet_missing_data_stays_null():
    """Données absentes → champs nuls, jamais inventés."""
    row = _row(idu="97415000DD0004", _priority=100)
    s = sl.assemble_sujet(2, row, None)                # aucune fiche enrichie
    assert s["ca"] is None
    assert s["charge_fonciere"] is None
    assert s["potentiel_assemblage"]["possible"] is False
    assert "Données à consolider" in s["badges"]
