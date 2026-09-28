"""EXPORTS-FIX-1-BIS point 1 — la table d'USAGE du sol OCS GE (dimension US, IGN v2.0) est reprise
code par code de la nomenclature officielle. Garde contre l'inversion historique US1.1/US5."""
from labuse.exports.miroir import _OCS_GE_US, _ocs_ge_libelle


def test_ocsge_codes_temoins():
    # les deux témoins du mandat : un verger (US1.1) et une maison (US5).
    assert _ocs_ge_libelle("US1.1") == "Agriculture"
    assert _ocs_ge_libelle("US5") == "Usage résidentiel"


def test_ocsge_nomenclature_officielle():
    # quelques ancres de la nomenclature officielle (production secondaire/tertiaire, transition).
    attendu = {
        "US1.1": "Agriculture",
        "US1.2": "Sylviculture",
        "US2": "Production secondaire (industrie)",
        "US3": "Production tertiaire",
        "US5": "Usage résidentiel",
        "US6.1": "Zones en transition",
        "US6.2": "Zones abandonnées",
    }
    for code, lib in attendu.items():
        assert _OCS_GE_US.get(code) == lib, f"{code} : {_OCS_GE_US.get(code)!r} != {lib!r}"


def test_ocsge_jamais_inverse():
    # anti-régression : US1.1 n'est PAS résidentiel, US5 n'est PAS « sans usage ».
    assert "résidentiel" not in _OCS_GE_US["US1.1"].lower()
    assert "sans usage" not in _OCS_GE_US["US5"].lower()


def test_ocsge_code_inconnu_rendu_tel_quel():
    # un code hors catalogue est rendu tel quel, jamais inventé.
    assert _ocs_ge_libelle("US9.9") == "US9.9"
