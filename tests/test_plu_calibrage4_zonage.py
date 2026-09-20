"""PLU-CALIBRAGE-4 lot 1 — la logique de ZoneRules PORTÉE dans le nouveau système
(`faisabilite/zonage.py`, lue de `regles` + `config/plu_zonage.yaml`). Un test par comportement
porté, AVANT toute bascule. Chacun dit OÙ le comportement vit désormais.
"""
from __future__ import annotations

from labuse.faisabilite.zonage import resolve_zone_v2, hypotheses_faisabilite_v2


# ── repli générique (_zone_generique) — vit dans zonage._resolve_v2_base (réutilise
#    plu_rules._zone_generique) ────────────────────────────────────────────────────────────────
def test_generique_progressif_zone_inconnue():
    """Commune progressive + zone U inconnue → estimation générique (calibree=False, constructible)."""
    r = resolve_zone_v2("Uzzz999", "97401")   # Les Avirons (progressif), code U hors calibrage
    assert r is not None and r.calibree is False and r.constructible_neuf is True


def test_generique_non_constructible_hors_prefixe():
    """Zone hors préfixe U/AU (ex. N) → générique NON constructible."""
    r = resolve_zone_v2("N", "97401")
    assert r is not None and r.calibree is False and r.constructible_neuf is False


# ── mode strict — vit dans _resolve_v2_base (zc['mode']=='strict') ──────────────────────────────
def test_mode_strict_zone_inconnue_renvoie_none():
    """Saint-Paul (mode strict) : une zone hors calibrage → None (jamais d'estimation)."""
    assert resolve_zone_v2("ZoneInconnueXX", "97415") is None


# ── zones AU*st non constructibles — vit dans _resolve_v2_base (zones_au_st) ─────────────────────
def test_au_st_non_constructible():
    """Une zone listée en `zones_au_st` (Les Avirons AUes) → constructible_neuf=False."""
    r = resolve_zone_v2("AUes", "97401")
    assert r is not None and r.constructible_neuf is False


def test_au_st_pattern():
    """Un code `AU\\w*st` non listé → non constructible par le motif."""
    r = resolve_zone_v2("AUxst", "97401")
    assert r is not None and r.constructible_neuf is False


# ── habitat: interdit — vit dans plu_zonage (métadonnée de zone) ────────────────────────────────
def test_habitat_interdit():
    """Les Avirons AUec : habitat interdit (vocation économique)."""
    r = resolve_zone_v2("AUec", "97401")
    assert r is not None and r.habitat == "interdit"


# ── mode prospect — vit dans plu_zonage (hauteur_mode) ──────────────────────────────────────────
def test_mode_prospect():
    """Saint-Denis Ud : hauteur bornée par prospect (hf calculé par parcelle)."""
    r = resolve_zone_v2("Ud", "97411")
    assert r is not None and r.hauteur_mode == "prospect"


# ── drapeau constructible_neuf explicite — vit dans plu_zonage ──────────────────────────────────
def test_constructible_neuf_flag():
    """Saint-Pierre Us : gelée (constructible_neuf=False) au règlement."""
    r = resolve_zone_v2("Us", "97416")
    assert r is not None and r.constructible_neuf is False


# ── renvoi AU→U — vit dans _resolve_v2_base ─────────────────────────────────────────────────────
def test_renvoi_au_vers_u():
    """AU<n><indice> reprend les règles de U<n><indice> (si la zone U existe), via_renvoi posé."""
    r = resolve_zone_v2("AU1a", "97415")             # Saint-Paul a U1a
    assert r is not None and r.via_renvoi and "U1a" in r.via_renvoi


# ── pleine_terre LUE (rubrique du schéma, câblée) — vit dans _zone_rules_from_regles ────────────
def test_pleine_terre_lue():
    """Les Avirons AUa : la pleine terre est lue des regles (avant, non lue)."""
    r = resolve_zone_v2("AUa", "97401")
    assert r is not None and r.pleine_terre_pct == 15.0


# ── hypothèses moteur migrées — vit dans plu_zonage (hypotheses_faisabilite_v2) ─────────────────
def test_hypotheses_migrees():
    """pct_lls=30 (Saint-Denis) survit à la migration hors plu_<slug>.yaml."""
    h = hypotheses_faisabilite_v2("97411")
    assert h.get("pct_lls") == 30


def test_hypotheses_commune_none_saint_paul():
    """commune=None → Saint-Paul (back-compat historique)."""
    assert hypotheses_faisabilite_v2(None).get("pct_lls") == 30   # Saint-Paul pct_lls=30


# ── drapeau via_renvoi / calibree portés — sanity ───────────────────────────────────────────────
def test_zone_calibree_a_ses_valeurs():
    """Une zone U calibrée (Saint-Denis Uh) porte ses valeurs des regles."""
    r = resolve_zone_v2("Uh", "97411")
    assert r is not None and r.calibree is True and r.hf_m == 7.0 and r.he_m == 4.5
