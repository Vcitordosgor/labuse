"""SOURCES-1 lot 2 — gardes : la nature et l'eau (INPN/ENP, DPF, zones humides, AZI/TRI, RPG).

Tests PURS (stubs, pas de PostGIS) sur les couches cascade + invariants du circuit."""
from __future__ import annotations

from labuse.cascade.context import Intersection, ParcelRef
from labuse.cascade.layers.phase1 import DpfLayer, EnsLayer, SaferLayer, ZoneHumideLayer
from labuse.enums import CascadeVerdict, Severity

P = ParcelRef(id=1, idu="97415000TT0001", commune="Test", surface_m2=1000.0)

ENS = {"spatial_kind": "ens", "severity": "moyen",
       "detail": "Espace protégé réglementaire (réserve / APB / conservatoire…) — restriction.",
       "hard_subtypes": ["réserve_naturelle_nationale", "reserve_naturelle",
                         "réserve_biologique", "apb"],
       "severites": {"conservatoire_du_littoral": "moyen", "ramsar": "faible",
                     "site_classe": "info", "site_inscrit": "info"}}

DPF = {"spatial_kind": "dpf", "marchepied_m": 3.25, "search_cap_m": 60}
ZH = {"spatial_kind": "zone_humide"}
SAFER = {"spatial_kind": "safer", "severity": "moyen",
         "detail": "Parcelle déclarée agricole au RPG (déclarations PAC) — usage agricole, à vérifier au PLU.",
         "plu_kind": "plu_gpu_zone", "zone_a_prefixes": ["A"],
         "canne_codes": ["CSA"], "canne_hard_pct": 50}


class _Ctx:
    def __init__(self, by_kind: dict, near: dict | None = None):
        self.by = by_kind
        self.near = near or {}

    def kind_present(self, kind):
        return kind in self.by

    def kind_present_commune(self, kind, commune):
        return kind in self.by

    def intersections(self, _pid, kind):
        return self.by.get(kind, [])

    def min_distance_m(self, _pid, kind):
        return self.near.get(kind)


def _i(subtype, coverage, name=None, attrs=None):
    return Intersection(subtype, name, coverage, attrs or {}, None)


def _one(out):
    return out if not isinstance(out, list) else out[0]


# ───────────────────────── ENP (réserves/APB rédhibitoires) ─────────────────────────

def test_enp_hard_reserves_apb():
    lay = EnsLayer()
    for st in ("réserve_naturelle_nationale", "reserve_naturelle", "réserve_biologique", "apb"):
        v = _one(lay.evaluate(P, _Ctx({"ens": [_i(st, 0.4, "Réserve X")]}), ENS))
        assert v.result == CascadeVerdict.HARD_EXCLUDE, st
    marine = _one(lay.evaluate(
        P, _Ctx({"ens": [_i("reserve_naturelle", 0.2, "Réserve Nationale Marine de la Réunion")]}), ENS))
    assert marine.result == CascadeVerdict.HARD_EXCLUDE
    assert "Marine" in marine.detail


def test_enp_vigilance_et_anti_double_compte():
    lay = EnsLayer()
    cons = _one(lay.evaluate(P, _Ctx({"ens": [_i("conservatoire_du_littoral", 0.3)]}), ENS))
    assert cons.result == CascadeVerdict.SOFT_FLAG and cons.severity == Severity.MOYEN
    ram = _one(lay.evaluate(P, _Ctx({"ens": [_i("ramsar", 0.3)]}), ENS))
    assert ram.severity == Severity.FAIBLE
    site = _one(lay.evaluate(P, _Ctx({"ens": [_i("site_classe", 0.3, "La Pointe au Sel")]}), ENS))
    assert site.severity == Severity.INFO and "AC2" in site.detail


# ───────────────────────── DPF (marchepied 3,25 m) ─────────────────────────

def test_dpf_marchepied():
    lay = DpfLayer()
    dans = lay.evaluate(P, _Ctx({"dpf": []}, near={"dpf": 2.0}), DPF)
    assert dans.result == CascadeVerdict.HARD_EXCLUDE
    assert "L2131-2" in dans.detail and "3,25" in dans.detail
    hors = lay.evaluate(P, _Ctx({"dpf": []}, near={"dpf": 8.0}), DPF)
    assert hors.result == CascadeVerdict.PASS
    loin = lay.evaluate(P, _Ctx({"dpf": []}, near={}), DPF)
    assert loin.result == CascadeVerdict.PASS
    absent = lay.evaluate(P, _Ctx({}), DPF)
    assert absent.result == CascadeVerdict.UNKNOWN


# ───────────────────────── Zones humides (vigilance forte, secteurs dits) ─────────────────────────

def test_zone_humide_vigilance():
    lay = ZoneHumideLayer()
    v = _one(lay.evaluate(
        P, _Ctx({"zone_humide": [_i("habitats_2011", 0.42, "Étang du Gol")]}), ZH))
    assert v.result == CascadeVerdict.SOFT_FLAG and v.severity == Severity.FORT
    assert "2011" in v.detail and "42 %" in v.detail
    hors = _one(lay.evaluate(P, _Ctx({"zone_humide": []}), ZH))
    assert hors.result == CascadeVerdict.PASS
    assert "pas une preuve" in hors.detail


# ───────────────────────── RPG (canne en zone A, friche possible) ─────────────────────────

def test_rpg_canne_zone_a():
    lay = SaferLayer()
    zone_a = [_i(None, 0.95, "A")]
    canne = _one(lay.evaluate(P, _Ctx({
        "safer": [_i(None, 0.8, None, {"code_cultu": "CSA"})],
        "plu_gpu_zone": zone_a}), SAFER))
    assert canne.result == CascadeVerdict.HARD_EXCLUDE
    assert "canne" in canne.detail.lower()
    friche = _one(lay.evaluate(P, _Ctx({"safer": [], "plu_gpu_zone": zone_a}), SAFER))
    assert friche.result == CascadeVerdict.SOFT_FLAG
    assert "friche" in friche.detail.lower() and "pas une preuve" in friche.detail


def test_rpg_zone_au_jamais_happee():
    """AU commence par « A » mais est urbanisable — jamais traitée zone A."""
    lay = SaferLayer()
    v = _one(lay.evaluate(P, _Ctx({
        "safer": [_i(None, 0.8, None, {"code_cultu": "CSA"})],
        "plu_gpu_zone": [_i(None, 0.95, "AU2")]}), SAFER))
    assert v.result == CascadeVerdict.SOFT_FLAG
    autre = _one(lay.evaluate(P, _Ctx({
        "safer": [_i(None, 0.3, None, {"code_cultu": "VRG"})],
        "plu_gpu_zone": [_i(None, 0.95, "A")]}), SAFER))
    assert autre.result == CascadeVerdict.SOFT_FLAG and "VRG" in autre.detail


# ───────────────────────── circuit : catalogue, filtres, registre ─────────────────────────

def test_catalogue_lot2():
    from labuse.ingestion.seed_sources import SOURCES, verifier_catalogue
    noms = {r["name"] for r in SOURCES}
    for n in ("Ravines — domaine public fluvial (DEAL Carmen)",
              "Zones humides — inventaires DEAL (Carmen)",
              "Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen)",
              "AZI / TRI — inondation (Géorisques GASPAR)"):
        assert n in noms, n
    assert verifier_catalogue() == []


def test_filtres_lot2_enregistres():
    from labuse.filtres.sources import FILTRES_RICHES
    for cle in ("deal_dpf", "zones_humides", "enp_complements", "azi_tri", "rpg_ign"):
        assert cle in FILTRES_RICHES, cle


def test_registre_lot2():
    from labuse.registre.couverture import COUCHE_PAR_CLE_FRONT
    from labuse.registre.donnees import DONNEES
    for cid in ("dpf_couche", "zone_humide_couche", "enp_couche", "rpg_couche",
                "azi_tri_commune"):
        assert cid in DONNEES, cid
    for cle in ("dpf", "zone_humide", "enp", "rpg"):
        assert COUCHE_PAR_CLE_FRONT[cle] in DONNEES


def test_fiches_de_regle_lot2():
    import labuse.regles as regles
    fiches = regles.charger()
    for d in ("dpf_couche", "zone_humide_couche", "enp_couche", "rpg_couche"):
        assert d in fiches, d
    assert fiches["dpf_couche"].reference is not None
    assert "L2131-2" in fiches["dpf_couche"].reference.article \
        or "L2131-2" in fiches["dpf_couche"].formule_codee


def test_vanne_lot2():
    from labuse import filtres
    labels = {e.get("label") for e in filtres.sources_a_job()}
    assert {"deal_dpf", "zones_humides", "enp_complements", "azi_tri"} <= labels


def test_azi_geometrie_non_dupliquee():
    """Doctrine du lot : le fait AZI/TRI est une table, la géométrie d'aléa reste servie par
    georisque_alea (jamais deux couches pour la même emprise)."""
    from labuse.registre.donnees import DONNEES
    assert DONNEES["azi_tri_commune"].table == "azi_communes"
    assert DONNEES["azi_tri_commune"].type == "liste"
