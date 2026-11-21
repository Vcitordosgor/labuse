"""FIX-OPPORTUNITES correction C — le RPG (déclaration agricole indicative) ne rend plus une parcelle
de zone U/AU « rédhibitoire ». En zone A/N, le comportement est INCHANGÉ (le RPG reste l'exclusion de
fait). Les causes réellement bloquantes (bande littorale, aléa PPR fort) restent, elles, rédhibitoires.

Tests purs sur le moteur (sans base) : on confronte la MÊME parcelle théorique selon sa famille de zone.
"""
from __future__ import annotations

import dataclasses

from labuse.faisabilite.engine import Contraintes, estimate_capacity
from labuse.faisabilite.zonage import resolve_zone

_EMPRISE = (1200.0, 3.0)   # assiette insetée généreuse (le terrain n'est pas le facteur limitant)


def _cap(rules, **contr):
    return estimate_capacity(rules, 2000.0, emprise_geo=_EMPRISE, contraintes=Contraintes(**contr))


def test_rpg_ne_bloque_plus_en_zone_u():
    rules_u = resolve_zone("U1c")
    sans = _cap(rules_u)
    avec = _cap(rules_u, agricole_sar=True)
    assert sans.constructible, "zone U sans RPG : constructible (référence)"
    # LA correction C : le RPG (indicatif) ne rend plus la parcelle U rédhibitoire.
    assert avec.constructible, "zone U + RPG : reste constructible (RPG indicatif, zonage U gouverne)"
    assert avec.cause != "redhibitoire"


def test_rpg_reste_bloquant_en_zone_a():
    # MÊMES règles, mais code de famille A → le RPG reste l'exclusion de fait (scope C = zone U).
    rules_a = dataclasses.replace(resolve_zone("U1c"), code="A")
    avec = _cap(rules_a, agricole_sar=True)
    assert not avec.constructible, "zone A + RPG : reste non constructible (comportement inchangé)"
    assert avec.cause == "redhibitoire"


def test_rpg_reste_bloquant_en_zone_n():
    rules_n = dataclasses.replace(resolve_zone("U1c"), code="N")
    assert not _cap(rules_n, agricole_sar=True).constructible


def test_causes_reellement_bloquantes_conservees_en_zone_u():
    rules_u = resolve_zone("U1c")
    # MOTEUR-VERITE-FIX-1 LOT 3 (V7) — le recul PROSPECTIF du trait de côte (bandes courte/longue)
    # est une PROJECTION d'érosion, pas une servitude d'interdiction : même entièrement couverte,
    # la parcelle reste constructible AVEC l'alerte « à vérifier auprès des services de l'État »
    # (preuve : 97410000BX0750, 100 % en bande, maison AUTORISÉE et ACHEVÉE — DAACT 17/07/2025).
    f_litt = _cap(rules_u, littoral_pct=1.0)
    assert f_litt.constructible
    assert any("trait de côte" in a.lower() for a in f_litt.avertissements)
    f_contact = _cap(rules_u, littoral_pct=0.15)
    assert f_contact.constructible
    assert any("trait de côte" in a.lower() for a in f_contact.avertissements)
    # aléa PPR fort = cause réellement bloquante → rédhibitoire (doctrine inchangée).
    assert not _cap(rules_u, alea_ppr="fort").constructible
