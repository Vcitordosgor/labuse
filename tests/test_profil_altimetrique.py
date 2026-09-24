"""RETOURS-13 P6 — statistiques du profil altimétrique (fonction PURE, sans base ni réseau).

Le calcul de coupe (distance, dénivelés, pente moyenne, plus forte pente) est isolé dans
``stats_profil`` : on le vérifie ici sur des reliefs synthétiques, avec le vocabulaire cartes.gouv.
Le témoin BZ1065 (cartes.gouv : ~20 % de pente moyenne sur ~300 m) est reproduit comme une montée
monotone de 60 m sur 300 m → pente moyenne 20 %.
"""
from __future__ import annotations

from labuse.faisabilite.profil_altimetrique import stats_profil


def _pts(paires):
    return [{"dist_m": d, "alt_m": a} for d, a in paires]


def test_montee_monotone_20pct_sur_300m():
    # témoin BZ1065 (ordre de grandeur cartes.gouv) : +60 m sur 300 m = 20 %.
    p = _pts([(0, 0), (50, 10), (100, 20), (150, 30), (200, 40), (250, 50), (300, 60)])
    st = stats_profil(p)
    assert st is not None
    assert st["distance_m"] == 300.0
    assert st["denivele_positif_m"] == 60.0
    assert st["denivele_negatif_m"] == 0.0
    assert st["pente_moyenne_pct"] == 20.0
    assert st["pente_max_pct"] == 20.0          # pente constante → moyenne == max
    assert st["altitude_min_m"] == 0.0
    assert st["altitude_max_m"] == 60.0


def test_relief_avec_creux_denivele_des_deux_cotes():
    # 0 → 10 (montée) → 5 (descente) → 15 (montée) sur 30 m.
    p = _pts([(0, 0), (10, 10), (20, 5), (30, 15)])
    st = stats_profil(p)
    assert st["denivele_positif_m"] == 20.0     # +10 puis +10
    assert st["denivele_negatif_m"] == 5.0      # -5
    assert st["pente_max_pct"] == 100.0         # 10 m sur 10 m
    # grade absolu moyen = (20 + 5) / 30 = 83,3 %
    assert st["pente_moyenne_pct"] == 83.3


def test_moins_de_deux_points_valides_renvoie_none():
    assert stats_profil(_pts([(0, 12.0)])) is None
    assert stats_profil([{"dist_m": 0, "alt_m": None}, {"dist_m": 5, "alt_m": None}]) is None


def test_points_no_data_ignores_mais_distance_totale_conservee():
    # trous (None) au milieu : ignorés dans les pentes ; la distance reste celle des extrémités.
    p = _pts([(0, 10)]) + [{"dist_m": 25, "alt_m": None}] + _pts([(50, 20)])
    st = stats_profil(p)
    assert st is not None
    assert st["distance_m"] == 50.0
    assert st["denivele_positif_m"] == 10.0
    # grade moyen sur le segment valide 0→50 : 10 / 50 = 20 %
    assert st["pente_moyenne_pct"] == 20.0
