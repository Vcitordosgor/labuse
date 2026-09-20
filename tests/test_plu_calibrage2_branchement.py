"""PLU-CALIBRAGE-2 lot 1 — le calcul de capacité branché sur les règles chiffrées VALIDÉES.

Une règle `valide` → sa valeur est utilisée ET l'étape passe SOURCÉ (article + page) ; une règle
`absent` (silence prouvé) → « pas de règle dans le PLU » ; pas de règle valide (autre commune,
ou `propose`) → rien ne change (ESTIMÉ). Les valeurs de BASE en plage/prospect (Ud/Up) ne
branchent aucune hauteur (l'étape reste ESTIMÉ)."""
from __future__ import annotations

from labuse.api.modules import _faisa_step_prov
from labuse.faisabilite import plu_rules as PR
from labuse.faisabilite.engine import Hypotheses, estimate_capacity


def _ov(zone, commune="Saint-Denis"):
    return PR._calibrage_overlay(zone, commune)


def test_valide_branche_valeur_et_source():
    """Zone Uh calibrée : hé/hf/emprise/reculs/stationnement pris des feuilles validées, avec
    leur source (article + page → SOURCÉ)."""
    champs, src = _ov("Uh")
    assert champs["he_m"] == 4.5 and champs["hf_m"] == 7.0 and champs["emprise_sol_pct"] == 30.0
    assert "calibrage validé" in src["hauteur"] and "Uh.10" in src["hauteur"]
    assert _faisa_step_prov(src["emprise"], "") == "sourcee"


def test_base_plage_prospect_ne_branche_pas_de_hauteur():
    """Base Ud = prospect (feuille plage, sans valeur unique) : AUCUNE hauteur branchée (l'étape
    niveaux reste ESTIMÉ) ; l'emprise 80 % (base-correcte) est bien branchée, elle."""
    champs, _ = _ov("Ud")
    assert "hf_m" not in champs and "he_m" not in champs and "niveaux_max" not in champs
    assert champs["emprise_sol_pct"] == 80.0


def test_secteur_porte_ses_valeurs():
    """Secteur Udop : R+5 (niveaux_max) + 18 m + emprise 70 % — ses propres valeurs, sourcées."""
    champs, src = _ov("Udop")
    assert champs["hf_m"] == 18.0 and champs["niveaux_max"] == 5 and champs["emprise_sol_pct"] == 70.0
    assert champs["hauteur_mode"] is None            # une hauteur absolue prime sur le prospect


def test_absent_dit_pas_de_regle():
    """Uv : emprise ABSENTE (silence prouvé) → source « pas de règle dans le PLU », prov=absent."""
    _champs, src = _ov("Uv")
    assert "pas de règle dans le PLU" in src["emprise"]
    assert _faisa_step_prov(src["emprise"], "") == "absent"


def test_autre_commune_identite():
    """Une commune sans règles validées dans plu_destinations → overlay None (rien ne change)."""
    assert _ov("Ud", "Saint-Pierre") is None
    assert PR._appliquer_calibrage(PR._resolve_zone_base("U1a", None), "U1a", None) is not None  # Saint-Paul intact


def test_niveaux_max_utilise_la_valeur_lue():
    """Le moteur : `niveaux_max` (R+n lu) est utilisé tel quel, pas dérivé d'une hauteur."""
    rules = PR.ZoneRules(code="Udop", niveaux_max=5, emprise_sol_pct=70.0,
                         sources={"hauteur": "Art. Ud.10 · p.44 (PLU, calibrage validé)"})
    f = estimate_capacity(rules, 2000.0, hyp=Hypotheses())
    niv = next(s for s in f.steps if s.label == "Niveaux constructibles")
    assert niv.valeur == "R+5" and "R+5 lu au règlement" in niv.formule
    assert _faisa_step_prov(niv.source, niv.prov) == "sourcee"


def test_prov_absent_reconnu():
    assert _faisa_step_prov("pas de règle dans le PLU (silence prouvé — Art. Uv.9 · p.84)", "") == "absent"
