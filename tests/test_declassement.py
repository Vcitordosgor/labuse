"""Déclassement — volet NON-franc (garde-fou faux positifs, flags qualité étage 1).

⚠ FUSION ÉTAGE 0 (refonte scoring, session 1) : les bloquants FRANCS (micro-parcelle,
pente non aménageable, équipement OSM dominant, déjà bâti franc) ont QUITTÉ ce module —
ils sont désormais des couches d'ÉLIMINATION de phase 1 (cf. test_etage0_filtre_dur.py).
`apply_declassement` ne conserve que les cas NON-francs, qui rétrogradent une opportunité en
« à creuser » SANS jamais l'éliminer (ni FAUX_POSITIF, ni EXCLUE) et sans jamais la remonter.
Ces tests reflètent ce contrat réduit.
"""
from labuse.enums import EvaluationStatus as ES
from labuse.scoring.declassement import apply_declassement

OPP = ES.OPPORTUNITE


# ───────────────────────── cas NON-francs → « à creuser » ─────────────────────────

def test_surface_reduite_passe_en_a_creuser():
    st, motif = apply_declassement(OPP, {"surface_m2": 180})
    assert st == ES.A_CREUSER and "180" in motif


def test_pente_forte_passe_en_a_creuser():
    st, _ = apply_declassement(OPP, {"pente_pct": 45})
    assert st == ES.A_CREUSER


def test_osm_recouvrement_partiel_passe_en_a_creuser():
    st, motif = apply_declassement(OPP, {"osm_subtype": "parking", "osm_coverage": 0.40})
    assert st == ES.A_CREUSER and "parking" in motif and "40" in motif


def test_cumul_de_signaux_non_francs_reste_a_creuser():
    # Plusieurs signaux NON-francs ne « cumulent » plus jamais vers une exclusion (fusion étage 0).
    st, motif = apply_declassement(OPP, {"surface_m2": 180, "pente_pct": 45})
    assert st == ES.A_CREUSER and ";" in motif


# ───────────────────────── ne déclasse PAS ─────────────────────────

def test_effleurement_de_bord_ne_declasse_pas():
    # une grande parcelle qui effleure un pitch à 7 % NE doit PAS être déclassée.
    st, motif = apply_declassement(OPP, {"surface_m2": 11420, "pente_pct": 6,
                                         "osm_subtype": "pitch", "osm_coverage": 0.07})
    assert st == OPP and motif is None


def test_aucun_signal_statut_inchange():
    st, motif = apply_declassement(OPP, {"surface_m2": 5000, "pente_pct": 5})
    assert st == OPP and motif is None


def test_ne_remonte_jamais_un_statut():
    # déjà exclue + signal non-franc → reste exclue (jamais re-promu vers « à creuser »).
    st, _ = apply_declassement(ES.EXCLUE, {"surface_m2": 180})
    assert st == ES.EXCLUE


# ───────────── les bloquants FRANCS ne sont plus classés ici (déplacés à l'étage 0) ─────────────

def test_bloquants_francs_ne_produisent_plus_faux_positif_ici():
    """Contrat de la fusion : un signal FRANC passé directement au déclassement ne renvoie
    JAMAIS FAUX_POSITIF/EXCLUE (au plus « à creuser ») — l'élimination franche est le monopole
    de l'étage 0 (cascade phase 1, cf. test_etage0_filtre_dur.py)."""
    for signals in (
        {"surface_m2": 28},                                   # micro-parcelle (franc)
        {"pente_pct": 94},                                    # pente non aménageable (franc)
        {"osm_subtype": "parking", "osm_coverage": 0.82},     # équipement dominant (franc)
        {"surface_m2": 40, "pente_pct": 80},                  # cumul franc
    ):
        st, _ = apply_declassement(OPP, signals)
        assert st in (OPP, ES.A_CREUSER)
        assert st not in (ES.FAUX_POSITIF_PROBABLE, ES.EXCLUE)
