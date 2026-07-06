"""Phase 2 v2 — Q économique : vue mer, assemblage, DVF quintiles-île + liquidité + écoulement,
pente graduée, OCS artificialisé (cumul plafonné avec la vue mer).

Tests unitaires via ctx factice (sans géométrie/pyproj).
"""
from __future__ import annotations

from labuse.cascade.context import Intersection
from labuse.cascade.layers.etage1 import AssemblageLayer, VueMerLayer
from labuse.cascade.layers.phase1 import OcsGeLayer, PenteLayer
from labuse.cascade.layers.phase2 import DvfLayer, _quintile_points
from labuse.enums import CascadeVerdict, Severity


class _P:
    id = 7
    idu = "97415000AB0001"
    commune = "Saint-Paul"


class _Ctx:
    def __init__(self, vue=None, assemblage=None, residuel=None, dvf=None, inter=None, present=True):
        self._vue, self._asm, self._res = vue, assemblage, residuel
        self._dvf, self._inter, self._present = dvf or {}, inter or [], present

    def vue_mer(self, pid):
        return self._vue

    def assemblage(self, pid):
        return self._asm

    def residuel(self, pid):
        return self._res

    def table_has_commune(self, table, commune):
        return True

    def dvf_stats(self, pid, radius, years):
        return self._dvf.get(radius, {"count": 0, "median_value": None, "median_eur_m2": None})

    def kind_present(self, kind):
        return self._present

    def intersections(self, pid, kind):
        return self._inter


# ───────────────────────── vue mer ─────────────────────────

def test_vue_mer_oui_partielle_non():
    oui = VueMerLayer().evaluate(_P(), _Ctx(vue={"vue": "oui", "distance_cote_m": 300}), {"bonus_key": "vue_mer"})
    assert oui.result == CascadeVerdict.POSITIVE and oui.magnitude == 1.0
    assert oui.extra == {"source_table": "parcel_vue_mer", "source_id": 7}
    part = VueMerLayer().evaluate(_P(), _Ctx(vue={"vue": "partielle"}), {"bonus_key": "vue_mer"})
    assert part.magnitude == 0.5
    non = VueMerLayer().evaluate(_P(), _Ctx(vue={"vue": "non"}), {"bonus_key": "vue_mer"})
    assert non.result == CascadeVerdict.PASS
    assert VueMerLayer().evaluate(_P(), _Ctx(vue=None), {"bonus_key": "vue_mer"}).result == CascadeVerdict.PASS


# ───────────────────────── assemblage ─────────────────────────

def test_assemblage_present_et_absent():
    v = AssemblageLayer().evaluate(_P(), _Ctx(assemblage={"siren": "123", "holding": 3, "voisins": 2}), {"bonus_key": "assemblage"})
    assert v.result == CascadeVerdict.POSITIVE and "2 parcelle" in v.detail and "123" in v.detail
    assert v.extra["source_table"] == "parcelle_personne_morale"
    assert AssemblageLayer().evaluate(_P(), _Ctx(assemblage=None), {"bonus_key": "assemblage"}).result == CascadeVerdict.PASS


# ───────────────────────── DVF quintiles île ─────────────────────────

def test_quintile_points():
    b = [976, 1553, 2249, 3407]
    p = [0, 2, 4, 7, 10]
    for em2, pt, q in [(500, 0, 1), (976, 2, 2), (1600, 4, 3), (2300, 7, 4), (3407, 10, 5), (9000, 10, 5)]:
        assert _quintile_points(em2, b, p) == (pt, q), em2


DVF_PARAMS = {"radii_m": [250, 500], "lookback_years": 5,
              "quintiles_ile_eur_m2": [976, 1553, 2249, 3407], "quintiles_points": [0, 2, 4, 7, 10],
              "liquidity_bonus_key": "liquidite_dvf", "liquidity_ref": 8,
              "ecoulement_sdp_min_m2": 2000, "ecoulement_liquidite_faible": 4}


def test_dvf_prix_et_liquidite():
    ctx = _Ctx(dvf={250: {"count": 4, "median_eur_m2": 2300}}, residuel={"sdp": 500})
    vs = DvfLayer().evaluate(_P(), ctx, DVF_PARAMS)
    prix = [v for v in vs if v.weight_override is not None][0]
    assert prix.weight_override == 7  # quintile Q4 (2249–3407)
    liq = [v for v in vs if v.bonus_key == "liquidite_dvf"][0]
    assert abs(liq.magnitude - 4 / 8) < 1e-9


def test_dvf_flag_ecoulement():
    # grosse SDP (>2000) + secteur peu liquide (count 2 < 4) → flag INFO
    ctx = _Ctx(dvf={250: {"count": 2, "median_eur_m2": 1600}}, residuel={"sdp": 8000})
    vs = DvfLayer().evaluate(_P(), ctx, DVF_PARAMS)
    flags = [v for v in vs if v.result == CascadeVerdict.SOFT_FLAG and v.severity == Severity.INFO]
    assert flags and "profondeur de marché" in flags[0].detail.lower()


# ───────────────────────── pente graduée ─────────────────────────

PENTE_PARAMS = {"seuil_faux_positif_pct": 60, "slope_labels": {"faible": 10, "modere": 20, "fort": 30, "tres_fort": 9999},
                "bandes": [{"max": 10, "points": 0}, {"max": 25, "points": -4}, {"max": 40, "points": -10}, {"max": 60, "points": -16}]}


def _pente(slope):
    return PenteLayer().evaluate(_P(), _Ctx(inter=[Intersection(None, None, 1.0, {"slope_pct": slope}, "ALTI")]), PENTE_PARAMS)


def test_pente_bandes():
    assert _pente(5).result == CascadeVerdict.PASS            # 0-10 → 0
    assert _pente(18).weight_override == -4                   # 10-25
    assert _pente(30).weight_override == -10                  # 25-40
    assert _pente(50).weight_override == -16                  # 40-60
    assert _pente(70).result == CascadeVerdict.HARD_EXCLUDE   # >60 exclue étage 0


# ───────────────────────── OCS artificialisé + cap vue mer ─────────────────────────

OCS_PARAMS = {"spatial_kind": "ocs_ge", "naturel_subtypes": ["naturel", "agricole"],
              "artificialise_subtypes": ["artificialise"], "artificialise_points": 4, "pair_cap_points": 10}


def _ocs(vue):
    inter = [Intersection("artificialise", None, 1.0, {}, "OCS")]
    return OcsGeLayer().evaluate(_P(), _Ctx(inter=inter, vue={"vue": vue} if vue else None), OCS_PARAMS)


def test_ocs_artificialise_cap_vue_mer():
    assert _ocs(None).weight_override == 4        # sans vue mer → +4 plein
    assert _ocs("partielle").weight_override == 4 # vue +4 → total 8 < 10, pas de cap
    assert _ocs("oui").weight_override == 2        # vue +8 → OCS plafonné à 2 (paire = 10)


def test_ocs_naturel_reste_flag():
    v = OcsGeLayer().evaluate(_P(), _Ctx(inter=[Intersection("naturel", None, 1.0, {}, "OCS")]), OCS_PARAMS)
    assert v.result == CascadeVerdict.SOFT_FLAG
