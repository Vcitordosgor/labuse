"""SCORING-6 lot A — assiette clippée (résiduel sur la portion U/AU, pas le tout-ou-rien).

Tests PURS (sans base — comme test_faisabilite) : ils verrouillent la résolution de sous-zone
U/AU quand la zone dominante est A/N, et la monotonicité de la capacité en surface d'assiette.
La preuve BOUT-EN-BOUT (requête PostGIS `_greve_certaine_m2` + résolution sur zone_parts réels)
est reproductible via `captures/scoring6/lot_a_assiette.py` sur la base `labuse`.
"""
from labuse.faisabilite.db import (ParcelContext, _pct_constructible,
                                   _sous_zone_constructible)
from labuse.faisabilite.engine import Contraintes, estimate_capacity
from labuse.faisabilite.zonage import resolve_zone


def _ctx(parts, zone="A", commune="Bras-Panon"):
    return ParcelContext(1, "x", commune, 2000.0, zone, Contraintes(), zone_parts=list(parts))


def test_sous_zone_constructible_choisit_la_plus_grande_uau():
    # Zone dominante A à 96 %, portion Ud à 4 % → la capacité se calcule sur Ud (fini le 0).
    ctx = _ctx([{"zone": "A", "fam": "A", "pct": 96.0},
                {"zone": "Ud", "fam": "U", "pct": 4.0}])
    alt = _sous_zone_constructible(ctx)
    assert alt is not None and alt.code == "Ud" and alt.constructible_neuf


def test_sous_zone_prend_la_plus_grande_part_uau():
    # Deux portions constructibles → on retient la plus grande (Uc 8 % > Ud 4 %).
    ctx = _ctx([{"zone": "N", "fam": "N", "pct": 88.0},
                {"zone": "Ud", "fam": "U", "pct": 4.0},
                {"zone": "Uc", "fam": "U", "pct": 8.0}])
    alt = _sous_zone_constructible(ctx)
    assert alt is not None and alt.code == "Uc"


def test_sous_zone_aucune_portion_constructible():
    # 100 % A → aucune sous-zone U/AU : on ne devine pas une capacité.
    assert _sous_zone_constructible(_ctx([{"zone": "A", "fam": "A", "pct": 100.0}])) is None


def test_pct_constructible_somme_les_parts_uau():
    ctx = _ctx([{"zone": "A", "fam": "A", "pct": 90.0},
                {"zone": "Ud", "fam": "U", "pct": 6.0},
                {"zone": "AUb", "fam": "AU", "pct": 4.0}])
    assert _pct_constructible(ctx) == 10.0
    # parcelle mono-zone (zone_parts vide) → None (pas de clip de surface).
    assert _pct_constructible(_ctx([])) is None


def test_capacite_positive_sur_petite_assiette_clippee():
    # Cœur du lot A : sur la seule portion U (assiette réduite), la capacité reste > 0 —
    # le reclassement B de la cascade produit enfin quelque chose (SCORING-5-RETOUR §3).
    rules = resolve_zone("Ud", "Bras-Panon")
    assert rules is not None and rules.constructible_neuf
    # assiette clippée ~10 % d'une parcelle de 2 000 m² : surface 200 m², emprise geo 150 m².
    f = estimate_capacity(rules, 200.0, Contraintes(), emprise_geo=(150.0, 3.0))
    assert f.constructible
    assert (f.fourchette.get("surface_plancher_m2") or 0) > 0


def test_capacite_monotone_en_surface_dassiette():
    # Assiette plus grande ⇒ capacité ≥ (monotonicité — garde-fou du moteur résiduel).
    rules = resolve_zone("Ud", "Bras-Panon")
    petite = estimate_capacity(rules, 150.0, Contraintes(), emprise_geo=(110.0, 3.0))
    grande = estimate_capacity(rules, 1500.0, Contraintes(), emprise_geo=(1100.0, 3.0))
    sp_p = petite.fourchette.get("surface_plancher_m2") or 0
    sp_g = grande.fourchette.get("surface_plancher_m2") or 0
    assert 0 < sp_p <= sp_g
