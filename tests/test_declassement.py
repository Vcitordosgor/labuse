"""Garde-fou faux positifs — déclassement (cœur pur, sans DB)."""
from labuse.enums import EvaluationStatus as ES
from labuse.scoring.declassement import apply_declassement

OPP = ES.OPPORTUNITE


def test_parking_franc_ne_reste_pas_opportunite():
    st, motif = apply_declassement(OPP, {"osm_subtype": "parking", "osm_coverage": 0.82})
    assert st == ES.FAUX_POSITIF_PROBABLE
    assert "parking" in motif and "82" in motif


def test_equipement_sportif_ne_reste_pas_opportunite():
    st, motif = apply_declassement(OPP, {"osm_subtype": "pitch", "osm_coverage": 0.7})
    assert st == ES.FAUX_POSITIF_PROBABLE
    assert "sport" in motif.lower()


def test_micro_parcelle_est_faux_positif():
    st, motif = apply_declassement(OPP, {"surface_m2": 28})
    assert st == ES.FAUX_POSITIF_PROBABLE and "28" in motif


def test_petite_parcelle_passe_en_a_creuser():
    st, motif = apply_declassement(OPP, {"surface_m2": 180})
    assert st == ES.A_CREUSER and "180" in motif


def test_pente_extreme_declasse():
    st, motif = apply_declassement(OPP, {"pente_pct": 94})
    assert st == ES.FAUX_POSITIF_PROBABLE and "pente" in motif.lower()


def test_pente_forte_passe_en_a_creuser():
    st, _ = apply_declassement(OPP, {"pente_pct": 45})
    assert st == ES.A_CREUSER


def test_score_brut_eleve_ne_protege_pas():
    # le statut entre est "opportunité" (score brut élevé implicite) → quand même déclassé.
    st, motif = apply_declassement(OPP, {"surface_m2": 30, "pente_pct": 5})
    assert st == ES.FAUX_POSITIF_PROBABLE and motif


def test_plusieurs_signaux_forts_excluent():
    st, motif = apply_declassement(OPP, {"surface_m2": 40, "pente_pct": 80})
    assert st == ES.EXCLUE
    assert ";" in motif  # deux motifs cumulés


def test_chevauchement_de_bord_ne_declasse_pas():
    # une grande parcelle qui effleure un pitch à 7 % NE doit PAS être déclassée.
    st, motif = apply_declassement(OPP, {"surface_m2": 11420, "pente_pct": 6,
                                         "osm_subtype": "pitch", "osm_coverage": 0.07})
    assert st == ES.OPPORTUNITE and motif is None


def test_ne_remonte_jamais_un_statut():
    # déjà exclue + signal "faux positif" → reste exclue (jamais re-promu).
    st, _ = apply_declassement(ES.EXCLUE, {"surface_m2": 30})
    assert st == ES.EXCLUE
    # aucun signal → statut inchangé, pas de motif.
    st2, motif2 = apply_declassement(OPP, {"surface_m2": 5000, "pente_pct": 5})
    assert st2 == OPP and motif2 is None
