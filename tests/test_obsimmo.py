"""Marché Obsimmo VENTE (LOT 4-C) — dataset client statique, jamais inventé.

Vérifie l'intégrité du dataset (78 lignes, 26 secteurs × 3 typologies), la règle de fiabilité
NS≠0 (null jamais transformé en 0), les helpers de lecture/repli, le sous-score `market_signal`
(séparé et transparent) et le bloc fiche.
"""
from __future__ import annotations

from labuse import obsimmo


# ── Intégrité structurelle ──────────────────────────────────────────────────────────────────
def test_dataset_78_lignes():
    assert len(obsimmo.load()) == 78


def test_26_secteurs_x_3_typologies():
    rows = obsimmo.load()
    secteurs: dict[str, set[str]] = {}
    for r in rows:
        secteurs.setdefault(r["sector"], set()).add(r["property_type"])
    assert len(secteurs) == 26
    for sec, types in secteurs.items():
        assert types == set(obsimmo.PROPERTY_TYPES), sec


def test_validate_ok():
    v = obsimmo.validate()
    assert v == {"rows": 78, "secteurs": 26, "typologies": list(obsimmo.PROPERTY_TYPES)}


# ── Règle NS ≠ 0 : null jamais transformé en 0 ──────────────────────────────────────────────
def test_null_reste_null_le_port_terrains():
    """Le Port / terrains : indicateurs locaux NS (null), mais 1 terrain réellement en vente."""
    m = obsimmo.get_market("Le Port", "terrains_constructibles")
    assert m is not None
    assert m["local_avg_price_eur"] is None          # NS, surtout pas 0
    assert m["local_price_m2_min"] is None
    assert m["active_listings_count"] == 1            # vrai entier, vrai 1
    assert m.get("notes")                             # ligne à interpréter avec prudence
    assert obsimmo.local_disponible(m) is False


def test_vrai_zero_sainte_rose_terrains():
    """Sainte-Rose / terrains : prix local présent mais 0 terrain en vente (vrai zéro)."""
    m = obsimmo.get_market("Sainte-Rose", "terrains_constructibles")
    assert m["local_avg_price_eur"] == 85183
    assert m["active_listings_count"] == 0            # vrai zéro, pas un null


def test_saint_denis_terrains_valeurs_exactes():
    m = obsimmo.get_market("Saint-Denis", "terrains_constructibles")
    assert m["local_avg_price_eur"] == 125949
    assert m["active_listings_count"] == 16


def test_active_listings_toujours_entier():
    assert all(isinstance(r["active_listings_count"], int) for r in obsimmo.load())


# ── Secteurs Obsimmo rattachés à une commune administrative ─────────────────────────────────
def test_saint_gilles_rattaches_a_saint_paul():
    for sec in ("Saint-Gilles-les-Bains", "Saint-Gilles-les-Hauts"):
        for pt in obsimmo.PROPERTY_TYPES:
            m = obsimmo.get_market(sec, pt)
            assert m is not None and m["parent_commune"] == "Saint-Paul", (sec, pt)


# ── Helpers de lecture / repli ──────────────────────────────────────────────────────────────
def test_get_market_repli_sur_commune():
    """Un nom inconnu comme secteur mais connu comme parent_commune retombe sur la commune."""
    direct = obsimmo.get_market("Saint-Paul", "appartements")
    assert direct is not None and direct["sector"] == "Saint-Paul"


def test_get_market_tolerant_accents_casse():
    a = obsimmo.get_market("Étang-Salé", "maisons")
    b = obsimmo.get_market("etang sale", "maisons")
    assert a is not None and b is not None and a["sector"] == b["sector"] == "Étang-Salé"


def test_get_market_by_parent_commune_prefere_chef_lieu():
    """Saint-Paul a 3 secteurs Obsimmo (St-Paul, St-Gilles Bains/Hauts) → on privilégie St-Paul."""
    m = obsimmo.get_market_by_parent_commune("Saint-Paul", "terrains_constructibles")
    assert m is not None and m["sector"] == "Saint-Paul"


def test_get_regional_market_constant():
    reg = obsimmo.get_regional_market("Réunion Ouest", "terrains_constructibles")
    assert reg is not None
    assert reg["regional_avg_price_eur"] == 383167
    # le bloc régional est identique quel que soit le secteur de la région
    via_sector = obsimmo.get_market("Saint-Leu", "terrains_constructibles")
    assert via_sector["regional_avg_price_eur"] == reg["regional_avg_price_eur"]


def test_typologie_invalide_renvoie_none():
    assert obsimmo.get_market("Saint-Paul", "bureaux") is None
    assert obsimmo.get_regional_market("Réunion Ouest", "bureaux") is None


# ── Sous-score market_signal : séparé, transparent, NS-safe ─────────────────────────────────
def test_market_signal_ns_pas_de_score():
    """Marché local NS → aucun signal fabriqué."""
    m = obsimmo.get_market("Le Port", "terrains_constructibles")
    sig = obsimmo.market_signal(m)
    assert sig["disponible"] is False
    assert "score" not in sig


def test_market_signal_transparent():
    m = obsimmo.get_market("Saint-Paul", "terrains_constructibles")
    sig = obsimmo.market_signal(m)
    assert sig["disponible"] is True
    assert 0 <= sig["score"] <= 100
    assert sig["label"] in ("favorable", "neutre", "prudence")
    assert sig["fiabilite"] in ("bonne", "moyenne", "faible")
    assert sig["composantes"]                          # composantes affichées = transparence
    # opacité « Très forte » sur ce secteur → fiabilité faible (l'opacité ne change pas le sens)
    assert sig["fiabilite"] == "faible"


def test_market_signal_liquidite_vs_region():
    """La liquidité compare le délai LOCAL au délai RÉGIONAL — pur calcul sur le dataset."""
    m = obsimmo.get_market("Saint-André", "terrains_constructibles")  # 7,05 sem. vs 40,61 région
    sig = obsimmo.market_signal(m)
    liq = next(c for c in sig["composantes"] if c["cle"] == "Liquidité")
    assert liq["sens"] == "+"                          # vend bien plus vite que sa région
    assert sig["label"] == "favorable"


# ── Bloc fiche ──────────────────────────────────────────────────────────────────────────────
def test_fiche_block_saint_paul():
    b = obsimmo.fiche_block("Saint-Paul")
    assert b is not None
    assert b["principal"]["property_type"] == "terrains_constructibles"
    assert b["region"] == "Réunion Ouest"
    assert b["comparaison_regionale"]["regional_avg_price_eur"] == 383167
    assert "appartements" in b["autres"] and "maisons" in b["autres"]
    assert b["signal"]["disponible"] is True
    assert "extraction manuelle 2026-06-19" in b["source"]["mention"]
    assert b["source"]["provenance"] == "sourcee"


def test_fiche_block_secteur_fin_saint_gilles():
    """Cibler Saint-Gilles-les-Bains donne bien le secteur fin (≠ Saint-Paul administratif)."""
    b = obsimmo.fiche_block("Saint-Paul", sector="Saint-Gilles-les-Bains")
    assert b["secteur"] == "Saint-Gilles-les-Bains"
    assert b["parent_commune"] == "Saint-Paul"


def test_fiche_block_commune_hors_dataset():
    assert obsimmo.fiche_block("Paris") is None
