"""CLASSEMENT-USAGE-1 — le gate « potentiel à bâtir » (règle unique), testé PUR (sans DB).

Verrouille : zone fermée (constructibilité / AU différé / cause résiduelle) → SDP bornée à 0 et
« rien à bâtir » ; zone ouverte + SDP > 0 → constructible ; le cas 97422000AX1253 (2AUe
declasse_zone_fermee, résiduel SANS cause) borné à 0 ; le fragment SQL du tri « À construire ».
"""
from labuse.faisabilite.potentiel_batir import (
    _assemble, sql_a_construire, where_a_construire, sql_gate_ferme,
)


def test_zone_ouverte_constructible_garde_sa_sdp():
    r = _assemble(sdp_raw=152, cause=None, constr_label=None, au_classe=None,
                  zone_fam="U", zone_lib="Uavap")
    assert r["sdp_restante_m2"] == 152
    assert r["zone_ouverte"] is True
    assert r["constructible"] is True
    assert r["rien_a_batir"] is False
    assert "152" in r["libelle"]


def test_zone_fermee_au_reglement_borne_a_zero():
    # cas 97422000AX1253 : résiduel 25 426 SANS cause, mais declasse_zone_fermee au cache.
    r = _assemble(sdp_raw=25426, cause=None, constr_label="declasse_zone_fermee",
                  au_classe="conditionnelle_operation", zone_fam="AU", zone_lib="2AUe")
    assert r["sdp_restante_m2"] == 0
    assert r["zone_ouverte"] is False
    assert r["constructible"] is False
    assert r["rien_a_batir"] is True
    assert "2AUe" in r["motif"]
    assert r["libelle"].startswith("Rien à bâtir")


def test_non_constructible_borne_a_zero():
    r = _assemble(sdp_raw=0, cause=None, constr_label="declasse_non_constructible",
                  au_classe=None, zone_fam="U", zone_lib="UA")
    assert r["sdp_restante_m2"] == 0 and r["rien_a_batir"] is True
    assert r["constructible"] is False


def test_au_non_ouverte_ferme():
    r = _assemble(sdp_raw=800, cause=None, constr_label=None,
                  au_classe="declasse_au_fermee", zone_fam="AU", zone_lib="2AU")
    assert r["sdp_restante_m2"] == 0 and r["zone_ouverte"] is False
    assert "AU non ouverte" in r["motif"]


def test_cause_residuelle_habitat_interdit_suffixe():
    # la cause porte un suffixe de zone (habitat_interdit:UEp) : le motif doit quand même matcher.
    r = _assemble(sdp_raw=0, cause="habitat_interdit:UEp", constr_label=None, au_classe=None,
                  zone_fam="U", zone_lib="UEp")
    assert r["rien_a_batir"] is True and r["constructible"] is False
    assert "Habitat interdit" in r["motif"]


def test_sdp_non_calculee_reste_distincte_de_zero():
    r = _assemble(sdp_raw=None, cause=None, constr_label=None, au_classe=None,
                  zone_fam="U", zone_lib="UB")
    assert r["sdp_restante_m2"] is None
    assert r["rien_a_batir"] is False   # inconnu ≠ nul
    assert "non calculé" in r["libelle"]


def test_fragments_sql_nul_safe_et_corrects():
    ac = sql_a_construire("r", "pc", "au")
    assert "sdp_residuelle_m2" in ac and "NOT (" in ac
    assert "COALESCE" in sql_gate_ferme("r", "pc", "au")
    w = where_a_construire("p")
    # autonome : il porte ses propres sous-requêtes (aucune jointure à ajouter par l'appelant).
    assert "EXISTS" in w and "parcel_residuel" in w and "parcel_constructibilite" in w
    assert "parcel_au_statut" in w
