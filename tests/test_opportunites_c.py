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
    # bande littorale = cause RÉELLEMENT bloquante → rédhibitoire, même en zone U.
    assert not _cap(rules_u, bande_littorale=True).constructible
    # aléa PPR fort = cause réellement bloquante → rédhibitoire.
    assert not _cap(rules_u, alea_ppr="fort").constructible
