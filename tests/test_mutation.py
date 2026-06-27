"""Score Mutation V1 (Radar Mutation) — moteur PUR, sans DB.

Vérifie la formule, les bornes, les niveaux, les garde-fous (bâti indisponible, confiance
faible) et la NON-régression du score d'opportunité.
"""
from dataclasses import replace

from labuse.mutation import (
    AVERTISSEMENT,
    SEUIL_FORTE,
    SEUIL_PRIORITAIRE,
    SEUIL_SURVEILLER,
    MutationFeatures,
    _niveau,
    compute_mutation_score,
)


def _f(**kw) -> MutationFeatures:
    base = dict(statut="a_creuser", opportunity_score=60, completeness_score=90, surface_m2=1000.0)
    base.update(kw)
    return MutationFeatures(**base)


def test_grande_parcelle_sous_exploitee_score_eleve():
    f = _f(surface_m2=24000, bati_ratio=0.0, opportunity_score=63, zone_u_au=True,
           marche_dvf=True, potentiel_regional=True, proprietaire={"public": True, "label": "Commune"})
    out = compute_mutation_score(f)
    assert out["score_mutation"] >= SEUIL_PRIORITAIRE
    assert out["niveau"] == "prioritaire"
    assert "Grand terrain sous-exploité" in out["badges"]
    assert "Foncier public stratégique" in out["badges"]


def test_near_threshold_score_moyen():
    f = _f(surface_m2=600, bati_ratio=0.1, opportunity_score=60, zone_u_au=True)
    out = compute_mutation_score(f)
    assert SEUIL_SURVEILLER <= out["score_mutation"] < SEUIL_PRIORITAIRE
    assert any(r["cle"] == "intensite_latente" for r in out["raisons"])


def test_malus_ppr_fort_baisse_le_score():
    base = _f(surface_m2=24000, bati_ratio=0.0, opportunity_score=63, zone_u_au=True, marche_dvf=True)
    sans = compute_mutation_score(base)["score_mutation"]
    avec = compute_mutation_score(replace(base, contrainte_forte=True))
    assert avec["score_mutation"] == max(0, sans - 15)
    assert "Vigilance contrainte forte" in avec["badges"]
    assert any(r["cle"] == "contrainte_forte" and r["points"] == -15 for r in avec["raisons"])


def test_niveaux_par_seuil():
    assert _niveau(70) == "prioritaire"
    assert _niveau(69) == "forte" and _niveau(55) == "forte"
    assert _niveau(54) == "surveiller" and _niveau(40) == "surveiller"
    assert _niveau(39) == "faible"


def test_sortie_explicable():
    out = compute_mutation_score(_f(surface_m2=6000, bati_ratio=0.02, zone_u_au=True))
    assert set(out) >= {"score_mutation", "niveau", "confiance", "badges", "raisons", "limites"}
    assert AVERTISSEMENT in out["limites"]
    assert all({"cle", "points"} <= set(r) for r in out["raisons"])


def test_bati_indisponible_jamais_faux_vacant():
    out = compute_mutation_score(_f(surface_m2=24000, bati_ratio=None, zone_u_au=True))
    assert not any(r["cle"] == "sous_exploitation" for r in out["raisons"])
    assert "Grand terrain sous-exploité" not in out["badges"]


def test_confiance_faible_plafonne_le_niveau():
    f = _f(surface_m2=24000, bati_ratio=0.0, opportunity_score=63, completeness_score=35,
           zone_u_au=True, marche_dvf=True, potentiel_regional=True)
    out = compute_mutation_score(f)
    assert out["score_mutation"] >= SEUIL_FORTE       # score reste élevé…
    assert out["niveau"] == "surveiller"              # …mais niveau plafonné (règle d'or)
    assert out["confiance_bande"] == "faible"


def test_score_borne_0_100():
    huge = compute_mutation_score(_f(surface_m2=99999, bati_ratio=0.0, opportunity_score=60,
                                     zone_u_au=True, marche_dvf=True, potentiel_regional=True,
                                     proprietaire={"public": True, "label": "État"}))
    assert 0 <= huge["score_mutation"] <= 100
    nul = compute_mutation_score(_f(statut="faux_positif_probable", surface_m2=50, bati_ratio=0.9,
                                    opportunity_score=10, contrainte_forte=True))
    assert nul["score_mutation"] == 0 and nul["niveau"] == "faible"


def test_aucun_impact_sur_score_opportunite():
    f = _f(opportunity_score=63, surface_m2=24000, bati_ratio=0.0, zone_u_au=True)
    out = compute_mutation_score(f)
    assert f.opportunity_score == 63                  # entrée non mutée (dataclass gelée)
    assert out["score_mutation"] != f.opportunity_score
    assert "opportunity_score" not in out             # score mutation DISTINCT, n'écrase pas l'opp
