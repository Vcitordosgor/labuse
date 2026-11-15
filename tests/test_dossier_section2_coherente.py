"""CHIRURGICAL-FIX-1 (LOT F, C-iii) — le §2 (verdict de zonage) ne proclame plus « constructible »
quand le §3 (verdict de potentiel) conclut que la parcelle n'est pas retenue (habitat interdit,
terrain exigu…). La SATURATION (zone constructible, SDP consommée, sans `cause`) garde « constructible »."""
from labuse.exports.verdicts import verdict_zonage
from labuse.registre.valeur import Valeur


def _v(x):
    return Valeur(valeur=x, chiffre_id="t", version_def="t", run=None)


def _vals(famille, pot):
    return {"zone_plu_famille": _v(famille), "potentiel_verdict": _v(pot)}


def test_section2_ne_dit_pas_constructible_si_parcelle_non_retenue():
    # habitat interdit en zone UE : §3 non retenu → §2 ne doit pas dire « constructible » sec.
    vz = verdict_zonage(_vals("U", {"cause": "habitat_interdit:UE", "libelle": "Non retenue"}))
    txt, ton, _ = vz
    assert "n'est pas retenue comme constructible" in txt
    assert ton == "warn"
    assert "— urbaine, constructible." not in txt   # plus l'affirmation générique de famille


def test_section2_garde_constructible_si_seulement_sature():
    # zone constructible, parcelle saturée (pas de `cause`) : §2 garde « constructible ».
    vz = verdict_zonage(_vals("U", {"cause": None, "niveau": "nul", "sdp_residuelle_m2": 0}))
    txt, ton, _ = vz
    assert "urbaine, constructible." in txt and ton == ""


def test_section2_garde_constructible_si_potentiel_ok():
    vz = verdict_zonage(_vals("U", {"cause": None, "libelle": "Fort potentiel"}))
    assert "urbaine, constructible." in vz[0]
