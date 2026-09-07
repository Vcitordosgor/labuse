"""SOURCES-1 lot 1 — gardes : droit des sols (ER, EBC, DPU, PEB, ABC, SUP, ZPPA).

Tests PURS (stubs, pas de PostGIS) sur les couches cascade + invariants du circuit
(catalogue, filtres, registre, vanne). Les épinglages des fiches de règle vivent ici
(exemple_temoin des fiches regles/dispositifs_droit_sols, peb_zone, zonage_abc_commune,
sup_categories)."""
from __future__ import annotations

from labuse.cascade.context import Intersection, ParcelRef
from labuse.cascade.layers.etage1 import SUP_SEVERITES
from labuse.cascade.layers.phase1 import DpuLayer, PebLayer, PrescriptionPluLayer
from labuse.enums import CascadeVerdict, Severity

P = ParcelRef(id=1, idu="97415000TT0001", commune="Test", surface_m2=1000.0)

PRESC = {"spatial_kind": "plu_gpu_prescription", "emplacement_reserve_typepsc": ["05"],
         "boise_classe_typepsc": ["01"], "patrimoine_bati_typepsc": ["07"],
         "mixite_sociale_typepsc": ["16", "17"], "oap_typepsc": ["18"],
         "eaux_pluviales_typepsc": ["48"], "er_hard_exclude_pct": 50,
         "ebc_hard_exclude_pct": 80}

PEB = {"spatial_kind": "peb", "hard_zones": ["a", "b"],
       "flag_zones": {"c": "moyen", "d": "faible"}, "hard_min_pct": 2}

DPU = {"spatial_kind": "dpu", "severity": "faible", "severity_renforce": "moyen"}


class _Ctx:
    def __init__(self, by_kind: dict):
        self.by = by_kind

    def kind_present(self, kind):
        return kind in self.by

    def intersections(self, _pid, kind):
        return self.by.get(kind, [])


def _i(subtype, coverage, libelle=None):
    return Intersection(subtype, None, coverage, {"libelle": libelle} if libelle else {}, None)


def _as_list(out):
    return out if isinstance(out, list) else [out]


# ───────────────────────── ER / EBC (seuils du mandat) ─────────────────────────

def test_prescription_er_seuils():
    """ER < 50 % → VIGILANCE + déduction annoncée ; ≥ 50 % → RÉDHIBITOIRE, servitude levable dite."""
    lay = PrescriptionPluLayer()
    sous = _as_list(lay.evaluate(P, _Ctx({"plu_gpu_prescription": [_i("05", 0.30, "ER 3 - École")]}), PRESC))
    assert [v.result for v in sous] == [CascadeVerdict.SOFT_FLAG]
    assert "déduite de l'emprise constructible" in sous[0].detail
    sur = _as_list(lay.evaluate(P, _Ctx({"plu_gpu_prescription": [_i("05", 0.51, "ER 3 - École")]}), PRESC))
    assert [v.result for v in sur] == [CascadeVerdict.HARD_EXCLUDE]
    assert "levable" in sur[0].detail


def test_prescription_ebc_seuils():
    """EBC dès non nul → VIGILANCE FORTE + soustraction d'assiette dite ; ≥ 80 % → RÉDHIBITOIRE."""
    lay = PrescriptionPluLayer()
    sous = _as_list(lay.evaluate(P, _Ctx({"plu_gpu_prescription": [_i("01", 0.15, "EBC")]}), PRESC))
    assert [v.result for v in sous] == [CascadeVerdict.SOFT_FLAG]
    assert sous[0].severity == Severity.FORT
    assert "soustraite de l'assiette" in sous[0].detail and "L113-1" in sous[0].detail
    sur = _as_list(lay.evaluate(P, _Ctx({"plu_gpu_prescription": [_i("01", 0.85, "EBC")]}), PRESC))
    assert [v.result for v in sur] == [CascadeVerdict.HARD_EXCLUDE]
    assert "85 %" in sur[0].detail


def test_faisabilite_lit_les_types_ebc_du_yaml():
    """La pré-faisabilité lit boise_classe_typepsc de cascade_rules (source unique des seuils)."""
    from labuse.faisabilite.db import _layer_params
    presc = _layer_params("prescription_plu")
    assert presc.get("boise_classe_typepsc") == ["01"]
    assert float(presc.get("ebc_hard_exclude_pct", 0)) == 80.0


# ───────────────────────── PEB (L112-10) ─────────────────────────

def test_peb_zones_cascade():
    """Zone B ≥ 2 % → RÉDHIBITOIRE (L112-10 cité) ; C → VIGILANCE moyenne ; D → faible ;
    liseré B < 2 % → information (pas d'exclusion) ; hors zones → PASS."""
    lay = PebLayer()
    b = _as_list(lay.evaluate(P, _Ctx({"peb": [_i("b", 0.4, "PEB Roland Garros")]}), PEB))
    assert [v.result for v in b] == [CascadeVerdict.HARD_EXCLUDE]
    assert "L112-10" in b[0].detail
    c = _as_list(lay.evaluate(P, _Ctx({"peb": [_i("c", 0.9, "PEB Roland Garros")]}), PEB))
    assert [v.result for v in c] == [CascadeVerdict.SOFT_FLAG]
    assert c[0].severity == Severity.MOYEN and "isolement acoustique" in c[0].detail
    d = _as_list(lay.evaluate(P, _Ctx({"peb": [_i("d", 1.0, "PEB Roland Garros")]}), PEB))
    assert d[0].severity == Severity.FAIBLE
    lisere = _as_list(lay.evaluate(P, _Ctx({"peb": [_i("b", 0.01, "PEB Roland Garros")]}), PEB))
    assert [v.result for v in lisere] == [CascadeVerdict.SOFT_FLAG]
    hors = _as_list(lay.evaluate(P, _Ctx({"peb": []}), PEB))
    assert [v.result for v in hors] == [CascadeVerdict.PASS]
    absent = _as_list(lay.evaluate(P, _Ctx({}), PEB))
    assert [v.result for v in absent] == [CascadeVerdict.UNKNOWN]


# ───────────────────────── DPU (vigilance seulement) ─────────────────────────

def test_dpu_vigilance_jamais_redhibitoire():
    lay = DpuLayer()
    simple = lay.evaluate(P, _Ctx({"dpu": [_i("dpu", 1.0)]}), DPU)
    assert simple.result == CascadeVerdict.SOFT_FLAG and simple.severity == Severity.FAIBLE
    renf = lay.evaluate(P, _Ctx({"dpu": [_i("dpu_renforce", 1.0)]}), DPU)
    assert renf.result == CascadeVerdict.SOFT_FLAG and renf.severity == Severity.MOYEN
    assert "pas sur la constructibilité" in renf.detail
    hors = lay.evaluate(P, _Ctx({"dpu": []}), DPU)
    assert hors.result == CascadeVerdict.PASS


# ───────────────────────── SUP (sévérités du mandat) ─────────────────────────

def test_sup_severites():
    """AC2 → fort (plus jamais « info ») ; PT1/PT2 → moyen ; AS1 → fort (RÉDHIBITOIRE à la
    première version publiée — non publiée au 974 le 06/09/2026) ; anti-double-compte conservé
    (pm*/ac1/el10 = info)."""
    assert SUP_SEVERITES["ac2"] == "fort"
    assert SUP_SEVERITES["pt1"] == "moyen" and SUP_SEVERITES["pt2"] == "moyen"
    assert SUP_SEVERITES["as1"] == "fort" and SUP_SEVERITES["t5"] == "fort"
    for cat in ("pm1", "pm2", "pm3", "ac1", "el10"):
        assert SUP_SEVERITES[cat] == "info"


# ───────────────────────── zonage ABC (passe-plat) ─────────────────────────

def test_zonage_abc_passe_plat():
    """Le parseur ne sert QUE le domaine de l'arrêté et écarte le reste (jamais deviné)."""
    from labuse.ingestion.zonage_abc import ZONES_CONNUES
    assert ZONES_CONNUES == {"Abis", "A", "B1", "B2", "C"}
    # calcul refait à la main sur la ligne CSV lue le 06/09/2026 : « 97415;974;Saint-Paul;A »
    ligne = "97415;974;Saint-Paul;A".split(";")
    assert ligne[1] == "974" and ligne[3] in ZONES_CONNUES


# ───────────────────────── circuit : catalogue, filtres, registre ─────────────────────────

def test_catalogue_accepte_les_six_sources():
    from labuse.ingestion.seed_sources import SOURCES, verifier_catalogue
    noms = {r["name"] for r in SOURCES}
    for n in ("GPU — emplacements réservés (prescriptions CNIG)",
              "GPU — espaces boisés classés (prescriptions CNIG)",
              "GPU — droit de préemption urbain (info-surf)",
              "PEB — plans d'exposition au bruit (DGAC via annexes GPU)",
              "Zonage ABC des communes (DHUP)",
              "ZPPA — zones de présomption de prescription archéologique (Atlas des patrimoines)"):
        assert n in noms, n
    assert verifier_catalogue() == []


def test_filtres_lot1_enregistres():
    from labuse.filtres.sources import FILTRES_RICHES
    for cle in ("gpu_prescriptions_er", "gpu_prescriptions_ebc", "dpu", "peb",
                "zonage_abc", "sup_gpu"):
        assert cle in FILTRES_RICHES, cle
    # le PEB est une couche d'île : pas de contrôle « 24 communes » (commune = NULL)
    assert FILTRES_RICHES["peb"].commune_nom_col is None


def test_registre_lot1_servi():
    """Les 5 données FICHE-1 lot 7 ne sont PLUS en attente ; réservoirs réels rattachés ;
    les couches et la liste dispositifs existent ; la clé fiche `dispositifs` est rattachée."""
    from labuse.registre.couverture import COUCHE_PAR_CLE_FRONT, FICHE_PARCELLE_CLES
    from labuse.registre.donnees import DONNEES
    for cid, res in (("er_emplacement_reserve", "gpu_prescriptions_er"),
                     ("ebc_classe", "gpu_prescriptions_ebc"),
                     ("dpu_perimetre", "dpu_perimetres"),
                     ("peb_zone", "peb_dgac"),
                     ("zonage_abc_logement", "zonage_abc_dhup")):
        d = DONNEES[cid]
        assert d.en_attente is None, cid
        assert res in d.reservoirs, cid
    for cid in ("er_couche", "ebc_couche", "dpu_couche", "peb_couche", "sup_couche",
                "dispositifs_parcelle"):
        assert cid in DONNEES, cid
    for cle in ("er", "ebc", "dpu", "peb", "sup"):
        assert COUCHE_PAR_CLE_FRONT[cle] in DONNEES
    assert "dispositifs" in FICHE_PARCELLE_CLES
    for cid in FICHE_PARCELLE_CLES["dispositifs"]:
        assert cid in DONNEES, cid


def test_reservoirs_carte_lot1():
    import csv
    with open("docs/CIRCUIT/inventaire/reservoirs.csv") as f:
        ids = {r[0] for r in csv.reader(f, delimiter=";")}
    for rid in ("gpu_prescriptions_er", "gpu_prescriptions_ebc", "dpu_perimetres",
                "peb_dgac", "zonage_abc_dhup", "zppa_culture"):
        assert rid in ids, rid


def test_vanne_lot1():
    from labuse import filtres
    labels = {e.get("label") for e in filtres.sources_a_job()}
    assert {"dpu", "peb", "zonage_abc"} <= labels


def test_fiches_de_regle_lot1():
    import labuse.regles as regles
    fiches = regles.charger()
    for d in ("dispositifs_parcelle", "peb_zone", "zonage_abc_logement", "sup_couche"):
        assert d in fiches, d
    assert fiches["peb_zone"].reference is not None
    assert "L112-10" in fiches["peb_zone"].reference.article or \
        "L112-10" in fiches["peb_zone"].formule_codee


def test_peb_zone_jamais_devinee():
    from labuse.ingestion.gpu_infos import _peb_zone
    assert _peb_zone("C", None) == "c"
    assert _peb_zone(" b ", None) == "b"
    assert _peb_zone("", "Plan d'exposition au bruit") is None
    assert _peb_zone("X", None) is None
