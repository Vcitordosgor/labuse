"""OUTIL-COMMUNES-FIX-1 (à corriger 5) — trimestre partiel par COUVERTURE DE DONNÉES (série par série).

Le défaut (relecteur) : Sitadel s'arrête en août, donc 2026T3 (juil-sept) ne porte que 2 mois ; le
drapeau « partiel » de la série PERMIS était faux pour l'île et Saint-Denis parce qu'il ne dépendait que
du volume. Le drapeau d'une série (DVF) ne doit pas non plus servir pour une autre (permis).

Test PUR (sans base) sur `_trimestre_fin` et `_marque_partiel_couverture`.
"""
from __future__ import annotations

import datetime as dt

from labuse.api.moteurs import _marque_partiel_couverture, _trimestre_fin


def test_trimestre_fin():
    assert _trimestre_fin("2026T3") == dt.date(2026, 9, 30)
    assert _trimestre_fin("2026T4") == dt.date(2026, 12, 31)
    assert _trimestre_fin("2025T1") == dt.date(2025, 3, 31)
    assert _trimestre_fin("nimporte") is None


def test_permis_t3_partiel_quand_donnees_sarretent_en_aout():
    serie = [{"trimestre": "2026T3", "partiel": False}, {"trimestre": "2026T2", "partiel": False}]
    _marque_partiel_couverture(serie, dt.date(2026, 8, 31))      # Sitadel s'arrête fin août
    assert serie[0]["partiel"] is True                           # T3 incomplet
    assert serie[1]["partiel"] is False                          # T2 inchangé


def test_trimestre_complet_non_partiel():
    serie = [{"trimestre": "2026T2", "partiel": False}]
    _marque_partiel_couverture(serie, dt.date(2026, 8, 31))      # données au-delà de la fin du T2
    assert serie[0]["partiel"] is False


def test_robustesse_serie_vide_ou_sans_date():
    _marque_partiel_couverture([], dt.date(2026, 8, 31))         # pas d'erreur
    serie = [{"trimestre": "2026T3", "partiel": False}]
    _marque_partiel_couverture(serie, None)                      # borne inconnue → inchangé
    assert serie[0]["partiel"] is False
