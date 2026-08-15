"""M79 — le €/m² marché DVF est un prix de TERRAIN NU du secteur cadastral, jamais un ratio
bâti/foncier. Test de non-régression : échoue si un prix est affiché sous le plancher de ventes,
ou si l'échelle recalée (150/325) n'est pas appliquée. ctx factice."""
from labuse.cascade.context import ParcelRef
from labuse.cascade.layers.phase2 import DvfLayer
from labuse.enums import CascadeVerdict

# params réels (miroir cascade_rules.yaml, M79)
P = {"bonus_key": "contexte_dvf_favorable", "liquidity_ref": 8,
     "price_lo_eur_m2": 150, "price_hi_eur_m2": 325, "w_liquidity": 0.5, "w_price": 0.5,
     "min_ventes_plancher": 3, "min_ventes_fiable": 5}


class _Ctx:
    def __init__(self, sector):
        self._s = sector

    def table_has_commune(self, table, commune):
        # M91 — ces tests exercent le CALCUL DE PRIX (plancher/échelle/fragilité), commune supposée
        # ingérée. Le garde « DVF non ingéré → UNKNOWN » (restauré M91) a son propre test dédié.
        return True

    def dvf_sector_terrain(self, idu):
        return self._s


def _p():
    return ParcelRef(id=1, idu="97415000AC0253", commune="Saint-Paul", surface_m2=1000.0)


def test_prix_terrain_du_secteur_pas_de_bati():
    # canari M79 : secteur 97415000AC → terrain 173 €/m², n=3 (le vrai « 173 », pas le « 379 » bâti-étalé)
    v = DvfLayer().evaluate(_p(), _Ctx({"median_eur_m2": 173, "n_ventes": 3, "fenetre": "2021-2025"}), P)
    assert "Prix médian terrain 173 €/m²" in v.detail
    assert "tous biens" not in v.detail and "rayon" not in v.detail       # plus de ratio bâti/rayon
    assert "3 ventes" in v.detail and "secteur cadastral" in v.detail


def test_plancher_dur_moins_de_3_ventes_pas_de_chiffre():
    v = DvfLayer().evaluate(_p(), _Ctx({"median_eur_m2": 500, "n_ventes": 2, "fenetre": "2021-2025"}), P)
    assert v.result == CascadeVerdict.PASS
    assert "échantillon insuffisant" in v.detail
    assert "500" not in v.detail                                          # AUCUN chiffre sous le plancher


def test_entre_3_et_5_prix_avec_mention_fragilite():
    v = DvfLayer().evaluate(_p(), _Ctx({"median_eur_m2": 300, "n_ventes": 4, "fenetre": "2021-2025"}), P)
    assert "Prix médian terrain 300 €/m²" in v.detail
    assert "fragile" in v.detail                                          # fragilité DITE, jamais cachée


def test_au_moins_5_ventes_fiable_sans_mention():
    v = DvfLayer().evaluate(_p(), _Ctx({"median_eur_m2": 300, "n_ventes": 10, "fenetre": "2021-2025"}), P)
    assert "Prix médian terrain 300 €/m²" in v.detail
    assert "fragile" not in v.detail


def test_echelle_recalee_150_325():
    # à em2=150 (plo) la composante prix = 0 ; à 325 (phi) elle = 1. Vérifie la magnitude bornée.
    bas = DvfLayer().evaluate(_p(), _Ctx({"median_eur_m2": 150, "n_ventes": 8, "fenetre": "x"}), P)
    haut = DvfLayer().evaluate(_p(), _Ctx({"median_eur_m2": 325, "n_ventes": 8, "fenetre": "x"}), P)
    # liq = 1 (n=8/8) → mag bas = 0.5*1 + 0.5*0 = 0.5 ; mag haut = 0.5*1 + 0.5*1 = 1.0
    assert abs(bas.magnitude - 0.5) < 1e-9
    assert abs(haut.magnitude - 1.0) < 1e-9


def test_secteur_sans_terrain_aucun_prix():
    v = DvfLayer().evaluate(_p(), _Ctx(None), P)
    assert v.result == CascadeVerdict.PASS and "aucune vente de terrain" in v.detail
