"""OUTIL-COMMUNES-FIX-1 bloquant 3 — le signal ZAN court porte sa DATE et le mot « scénario ».

Le défaut (relecteur) : « ZAN épuisé dans 1,1 an » — un futur relatif SANS date, trompeur lu en novembre
2026 (le calcul était juste au terme de la série Cerema, fin 2024). Et le budget = 50 % de la conso
2011-2021 est une HYPOTHÈSE comparative (scénario −50 %), pas une enveloppe réglementaire opposable. Le
signal doit : nommer le scénario, dater (année absolue + série), et parler de « solde simulé ».

Test PUR (sans base) sur `_zan_signal`.
"""
from __future__ import annotations

from labuse.api.app import ZAN_SEUIL_ANS, _zan_signal


def test_signal_porte_scenario_et_date():
    s = _zan_signal(1.1)                       # Saint-Denis : ~1,1 an au terme 2024
    assert s and s["code"] == "zan"
    lib = s["libelle"]
    assert "scénario" in lib                   # l'hypothèse est NOMMÉE
    assert "simulé" in lib                     # solde SIMULÉ, pas une enveloppe réglementaire
    assert "2025" in lib                       # DATE absolue (terme 2024 + 1 an), jamais « dans 1,1 an » nu
    assert "Cerema" in lib and "2021-2024" in lib   # série datée


def test_deja_depasse_reste_date_et_scenario():
    s = _zan_signal(0.0)
    assert s and "déjà dépassé" in s["libelle"]
    assert "scénario" in s["libelle"] and "2021-2024" in s["libelle"]


def test_annee_suit_le_terme_de_serie():
    # si une série plus récente est ingérée (terme 2025), l'épuisement se date à partir de ce terme
    assert "2027" in _zan_signal(2.0, fin=2025)["libelle"]


def test_au_dela_du_seuil_pas_de_signal():
    assert _zan_signal(float(ZAN_SEUIL_ANS)) is None
    assert _zan_signal(ZAN_SEUIL_ANS + 1.0) is None


def test_non_projetable_pas_de_signal():
    assert _zan_signal(None) is None
