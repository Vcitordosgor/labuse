"""SCORING-6 lot C — classification A/B/C/D de la cascade (tests PURS, sans base)."""
from labuse.scoring.cascade_v2 import (charger_classification, classer_verdict,
                                       pct_de_detail, reclasser)

CFG = charger_classification()


def _c(layer, result="HARD_EXCLUDE", detail=None, pct=None):
    return classer_verdict(layer, result, detail, pct, CFG)


def test_classe_a_exclusions_dures():
    for layer in ("eau", "parc_national", "foret_publique", "dpf", "ens", "surface",
                  "emprise_lineaire", "emprise_routiere", "pente", "osm_faux_positif",
                  "trait_de_cote"):
        v = _c(layer)
        assert v.classe == "A" and v.exclusion is True, layer


def test_ventilation_zonage_an():
    # A/N 100 % → A (exclusion) ; 90-99 % → B (portion U exploitable, aucune exclusion).
    plein = _c("zonage_plu_gpu", detail="Zone A (recouvrement 100 %)")
    partiel = _c("zonage_plu_gpu", detail="Zone A à 96 % de la parcelle")
    assert plein.classe == "A" and plein.exclusion is True
    assert partiel.classe == "B" and partiel.exclusion is False


def test_ventilation_ppr_er_ebc_peb():
    for layer in ("risques", "prescription_plu", "peb"):
        a = classer_verdict(layer, "HARD_EXCLUDE", None, 100.0, CFG)
        b = classer_verdict(layer, "HARD_EXCLUDE", None, 60.0, CFG)
        assert a.classe == "A" and a.exclusion, layer
        assert b.classe == "B" and not b.exclusion, layer


def test_classe_b_ne_produit_jamais_d_exclusion():
    # Invariant du mandat : une pénalité (B) n'exclut jamais.
    for layer, pct in (("risques", 60.0), ("prescription_plu", 55.0), ("peb", 3.0),
                       ("zonage_plu_gpu", 92.0)):
        assert classer_verdict(layer, "HARD_EXCLUDE", None, pct, CFG).exclusion is False
    assert _c("ravine", result="SOFT_FLAG").classe == "B"


def test_classe_c_informative():
    for layer in ("dpu", "zone_humide", "bati", "abf", "sup", "potentiel_foncier_region"):
        v = _c(layer, result="SOFT_FLAG")
        assert v.classe == "C" and v.exclusion is False, layer


def test_classe_d_supprimee_ou_deplacee():
    for layer in ("safer", "ocs_ge", "proprietaire", "dvf", "sitadel", "age_dirigeant", "bodacc"):
        v = _c(layer)
        assert v.classe == "D" and v.exclusion is False, layer


def test_reclasser_exclue_si_classe_a():
    r = reclasser([{"layer_name": "surface", "result": "HARD_EXCLUDE", "detail": None},
                   {"layer_name": "dpu", "result": "SOFT_FLAG", "detail": None}], CFG)
    assert r.exclue is True and len(r.exclusions) == 1 and len(r.infos) == 1


def test_reclasser_pas_exclue_si_seulement_b_partiel():
    r = reclasser([{"layer_name": "zonage_plu_gpu", "result": "HARD_EXCLUDE",
                    "detail": "Zone N à 96 %"},
                   {"layer_name": "safer", "result": "HARD_EXCLUDE", "detail": None}], CFG)
    assert r.exclue is False and len(r.penalites) == 1 and len(r.supprimes) == 1


def test_pct_de_detail():
    assert pct_de_detail("Zone A à 96 % de la parcelle") == 96.0
    assert pct_de_detail("PPR zone rouge — 100 % de la surface.") == 100.0
    assert pct_de_detail("aucun pourcentage ici") is None


def test_a_fixe_exclut_quel_que_soit_le_pct():
    # dpf/surface ne sont pas ventilées : HARD_EXCLUDE = exclusion, même avec un % dans le libellé.
    assert classer_verdict("dpf", "HARD_EXCLUDE", "DPF à ~2 m (12 %)", 12.0, CFG).exclusion is True
