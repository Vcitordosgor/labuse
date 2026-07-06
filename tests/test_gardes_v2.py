"""Phase 1 v2 — gardes G5 (socle SDP résiduelle), G1 (foncier public), G2 (emprise linéaire).

Tests unitaires via ctx factice (sans géométrie/pyproj), plus le mécanisme `weight_override`
(poids signé direct) dans compute_opportunity. Chaque garde tracée à sa source.
"""
from __future__ import annotations

from labuse.cascade.base import scored
from labuse.cascade.layers.etage1 import ResiduelSocleLayer
from labuse.cascade.layers.phase1 import EmpriseLineaireLayer, FoncierPublicLayer
from labuse.enums import CascadeVerdict, Severity
from labuse.scoring.opportunity import compute_opportunity


class _Ctx:
    def __init__(self, residuel=None, pm=None, forme=None):
        self._res, self._pm, self._forme = residuel, pm, forme

    def residuel(self, pid):
        return self._res

    def personne_morale(self, pid):
        return self._pm

    def forme(self, pid):
        return self._forme


class _P:
    id = 7
    idu = "97415000AB0001"


SOCLE = {"bandes": [
    {"max": 100, "points": -25, "lecture": "rien à construire"},
    {"max": 300, "points": -10, "lecture": "une maison"},
    {"max": 800, "points": 5, "lecture": "petit collectif"},
    {"max": 2000, "points": 15, "lecture": "opération viable"},
    {"max": 5000, "points": 25, "lecture": "belle opération"},
    {"max": None, "points": 30, "lecture": "opération majeure"},
]}


# ───────────────────────── G5 — socle SDP résiduelle ─────────────────────────

def test_socle_bandes():
    cas = [(5, -25), (99, -25), (100, -10), (272, -10), (300, 5),
           (787, 5), (800, 15), (1866, 15), (2000, 25), (4866, 25),
           (5000, 30), (34517, 30)]
    for sdp, attendu in cas:
        v = ResiduelSocleLayer().evaluate(_P(), _Ctx(residuel={"sdp": sdp}), SOCLE)
        assert v.weight_override == attendu, f"SDP {sdp} → {v.weight_override} (attendu {attendu})"
        assert v.extra == {"source_table": "parcel_residuel", "source_id": 7}


def test_socle_signe_du_resultat():
    # bande négative → SOFT_FLAG + severity INFO (×0 défensif) ; positive → POSITIVE
    neg = ResiduelSocleLayer().evaluate(_P(), _Ctx(residuel={"sdp": 50}), SOCLE)
    assert neg.result == CascadeVerdict.SOFT_FLAG and neg.severity == Severity.INFO
    pos = ResiduelSocleLayer().evaluate(_P(), _Ctx(residuel={"sdp": 9000}), SOCLE)
    assert pos.result == CascadeVerdict.POSITIVE


def test_socle_non_calcule_unknown():
    # ABSENCE (hors parcel_residuel) ET sdp=None → UNKNOWN, jamais −25.
    for res in (None, {"sdp": None}):
        v = ResiduelSocleLayer().evaluate(_P(), _Ctx(residuel=res), SOCLE)
        assert v.result == CascadeVerdict.UNKNOWN
        assert v.weight_override is None


# ───────────────────────── G1 — foncier public ─────────────────────────

G1 = {"groupes_exclus": [1, 2, 3, 4, 9]}


def test_g1_public_exclu():
    for groupe, label in [(1, "État"), (3, "Département"), (4, "Commune"), (9, "Établissements publics")]:
        pm = {"groupe": groupe, "groupe_label": label, "denomination": f"X {label}"}
        v = FoncierPublicLayer().evaluate(_P(), _Ctx(pm=pm), G1)
        assert v.result == CascadeVerdict.HARD_EXCLUDE and v.exclude_kind == "exclue"
        assert label in v.detail


def test_g1_hlm_et_sem_preserves():
    # 5 Office HLM, 6 SEM = MARCHANDS → PASS (jamais exclus).
    for groupe, label in [(5, "Office HLM"), (6, "sociétés d'économie mixte")]:
        v = FoncierPublicLayer().evaluate(_P(), _Ctx(pm={"groupe": groupe, "groupe_label": label}), G1)
        assert v.result == CascadeVerdict.PASS


def test_g1_prive_et_sans_pm_pass():
    assert FoncierPublicLayer().evaluate(_P(), _Ctx(pm={"groupe": 0, "groupe_label": "PM privée"}), G1).result == CascadeVerdict.PASS
    assert FoncierPublicLayer().evaluate(_P(), _Ctx(pm=None), G1).result == CascadeVerdict.PASS


# ───────────────────────── G2 — emprise linéaire ─────────────────────────

G2 = {"largeur_max_m": 8, "ratio_min": 8}


def test_g2_rue_fine_exclue():
    # lanière : largeur 2 m, ratio 90 → exclue
    v = EmpriseLineaireLayer().evaluate(_P(), _Ctx(forme={"larg": 2.0, "lng": 178.0, "ratio": 89.0}), G2)
    assert v.result == CascadeVerdict.HARD_EXCLUDE and v.exclude_kind == "faux_positif"


def test_g2_drapeau_survit():
    # drapeau allongé mais corps LARGE (51 m) → largeur≥8 → PASS malgré ratio 14,5
    v = EmpriseLineaireLayer().evaluate(_P(), _Ctx(forme={"larg": 51.0, "lng": 744.0, "ratio": 14.5}), G2)
    assert v.result == CascadeVerdict.PASS


def test_g2_parcelle_normale_survit():
    # étroite mais pas allongée (ratio 3) → PASS ; large et allongée → PASS
    assert EmpriseLineaireLayer().evaluate(_P(), _Ctx(forme={"larg": 6.0, "lng": 18.0, "ratio": 3.0}), G2).result == CascadeVerdict.PASS
    assert EmpriseLineaireLayer().evaluate(_P(), _Ctx(forme={"larg": 20.0, "lng": 200.0, "ratio": 10.0}), G2).result == CascadeVerdict.PASS


def test_g2_forme_degeneree_pass():
    assert EmpriseLineaireLayer().evaluate(_P(), _Ctx(forme=None), G2).result == CascadeVerdict.PASS


# ───────────────────────── weight_override (moteur d'opportunité) ─────────────────────────

def test_weight_override_applique_tel_quel():
    # socle −25 : court-circuite sévérité ; base 50 → 25, weight_applied = −25 exact
    res = compute_opportunity([scored("residuel_socle", "x", -25)])
    assert res.score == 25 and res.weights == [-25.0]
    # +30 : base 50 → 80
    res2 = compute_opportunity([scored("residuel_socle", "x", 30)])
    assert res2.score == 80 and res2.weights == [30.0]


def test_weight_override_naffecte_pas_les_couches_classiques():
    # une couche sans override garde le comportement sévérité (moyen → −10)
    from labuse.cascade.base import soft_flag
    res = compute_opportunity([soft_flag("risques", "x", Severity.MOYEN)])
    assert res.weights == [-10.0] and res.score == 40
