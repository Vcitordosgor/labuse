"""M70 décision 2 — ENS (couverture partielle 21/24 communes) ne produit jamais « Hors ENS »
(faux négatif, péché mortel) là où la commune n'a AUCUNE donnée → UNKNOWN. Fake ctx unitaire."""
from labuse.cascade.context import ParcelRef
from labuse.cascade.layers.phase1 import EnsLayer
from labuse.enums import CascadeVerdict

ENS_P = {"spatial_kind": "ens", "detail": "Espace protégé réglementaire à proximité.", "severity": "moyen"}


class _Ctx:
    """kind_present global True (ENS existe en base) ; kind_present_commune paramétrable ;
    intersections paramétrables (couverture de la parcelle)."""
    def __init__(self, commune_present: bool, inter_cov: float = 0.0):
        self._cp, self._cov = commune_present, inter_cov

    def kind_present(self, kind):
        return True

    def kind_present_commune(self, kind, commune):
        return self._cp

    def intersections(self, pid, kind):
        class _I:
            coverage = self._cov
        return [_I()] if self._cov > 0 else []


def _p(commune):
    return ParcelRef(id=1, idu="97407000AD0086", commune=commune, surface_m2=1000.0)


def test_ens_commune_vide_unknown_jamais_hors_ens():
    # Le Port : ENS existe en base mais AUCUNE donnée pour la commune → UNKNOWN, PAS « Hors ENS ».
    v = EnsLayer().evaluate(_p("Le Port"), _Ctx(commune_present=False), ENS_P)
    assert v.result == CascadeVerdict.UNKNOWN
    assert "non disponible sur cette commune" in v.detail
    assert "Hors ENS" not in v.detail


def test_ens_commune_couverte_sans_intersection_pass():
    # Saint-Paul (couverte) sans intersection → « Hors ENS » reste honnête (la commune EST mappée).
    v = EnsLayer().evaluate(_p("Saint-Paul"), _Ctx(commune_present=True, inter_cov=0.0), ENS_P)
    assert v.result == CascadeVerdict.PASS and "Hors ENS" in v.detail


def test_ens_intersection_soft_flag():
    v = EnsLayer().evaluate(_p("Saint-Denis"), _Ctx(commune_present=True, inter_cov=0.5), ENS_P)
    assert v.result == CascadeVerdict.SOFT_FLAG
