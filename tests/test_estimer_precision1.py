"""ESTIMER-PRECISION-1 — garde-fous UNITAIRES (aucun marqueur db/local/reel/network → filet pre-push) :

  · la SURFACE HABITABLE SAISIE prime sur toute estimation, avec le libellé « surface saisie » ;
  · les bandes de fiabilité recalibrées sont PAR SEGMENT (appartement vs maison) et « Élevée » ne sort
    pour la MAISON que dans le régime dense+homogène où le banc 2025 le tient (n≥40, dispersion ≤0,25) ;
  · la médiane PONDÉRÉE (quantile pondéré) se comporte comme attendu (poids égaux → médiane simple ;
    poids concentrés → tire la médiane vers les comparables qui pèsent).
"""
from __future__ import annotations

from labuse.pige.api import _fiabilite_bien, _surface_pour_total
from labuse.marche_service import _med_quantiles_pondere


# ── Surface habitable saisie (priorité 0, db NON touchée quand la surface est fournie) ──────────────
def test_surface_saisie_prime_et_libelle():
    s, src = _surface_pour_total(None, "97411000IE0241", 999, {"bati_m2": 63, "date": "2024-01-01"},
                                 "97411", surface_hab=90)
    assert s == 90
    assert src["source"] == "surface_saisie"
    assert "Surface habitable saisie (90 m²)" in src["ligne"]


def test_surface_saisie_ignoree_si_absente_ou_nulle():
    # surface_hab None → on retombe sur la dernière vente DVF (mut.bati_m2), db non requise ici non plus
    s, src = _surface_pour_total(None, "x", None, {"bati_m2": 63, "date": "2024-01-01"}, "97411",
                                 surface_hab=None)
    assert s == 63 and src["source"] == "dvf_vente"
    s0, src0 = _surface_pour_total(None, "x", None, {"bati_m2": 50}, "97411", surface_hab=0)
    assert src0["source"] == "dvf_vente"   # 0 ≤ 0 → ignoré


# ── Fiabilité recalibrée PAR SEGMENT ────────────────────────────────────────────────────────────────
def test_fiabilite_appartement_elevee_tient_15():
    niveau, ecart = _fiabilite_bien(20, 3000, 2500, 3300, False, type_bien="appartement")
    assert niveau == "fiable" and ecart == 15        # n≥15, disp=(3300-2500)/3000≈0,27 ≤0,40


def test_fiabilite_appartement_dispersion_moyenne():
    niveau, ecart = _fiabilite_bien(20, 3000, 2000, 3700, False, type_bien="appartement")
    assert niveau == "moyen" and ecart == 18          # disp≈0,57 (0,40–0,75)


def test_fiabilite_maison_elevee_reservee_dense_homogene():
    # maison dense + homogène : n≥40 ET disp≤0,25 → « Élevée » (±20), le seul régime où le banc tient <20 %
    niveau, ecart = _fiabilite_bien(50, 4000, 3600, 4300, False, type_bien="maison")
    assert niveau == "fiable" and ecart == 20
    # maison n<40 (même dispersion faible) → PAS « Élevée » : « Moyenne » ±26
    niveau2, ecart2 = _fiabilite_bien(20, 4000, 3600, 4300, False, type_bien="maison")
    assert niveau2 == "moyen" and ecart2 == 26


def test_fiabilite_limitee_et_repli_commune():
    assert _fiabilite_bien(5, 4000, 3900, 4100, False, type_bien="maison") == ("limitee", 36)
    assert _fiabilite_bien(50, 4000, 3600, 4300, True, type_bien="appartement") == ("limitee", 30)
    # type inconnu / bâti mixte → bandes MAISON (prudentes)
    assert _fiabilite_bien(20, 4000, 3900, 4100, False, type_bien="bati")[0] == "moyen"


# ── Médiane / quantiles pondérés ────────────────────────────────────────────────────────────────────
def test_med_pondere_poids_egaux_egale_mediane():
    q1, m, q3 = _med_quantiles_pondere([(100, 1), (200, 1), (300, 1)])
    assert m == 200


def test_med_pondere_poids_concentres_tire_la_mediane():
    # un comparable à 100 pèse 100× → la médiane pondérée bascule vers 100
    _q1, m, _q3 = _med_quantiles_pondere([(100, 100), (900, 1), (1000, 1)])
    assert m == 100


def test_med_pondere_vide():
    assert _med_quantiles_pondere([]) == (None, None, None)
