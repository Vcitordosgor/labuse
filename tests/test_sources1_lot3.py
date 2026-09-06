"""SOURCES-1 lot 3 — gardes : les sols et le bruit (SIS, CASIAS, classement sonore, CBS)."""
from __future__ import annotations

from labuse.cascade.context import Intersection, ParcelRef
from labuse.cascade.layers.etage1 import SRC_CASIAS, SRC_SIS, SolPollueLayer
from labuse.enums import CascadeVerdict, Severity

P = ParcelRef(id=1, idu="97415000TT0001", commune="Test", surface_m2=1000.0)

PARAMS = {"spatial_kind": "sol_pollue", "proximite_m": 100, "severity": "faible",
          "severity_sis": "fort",
          "detail": ("Ancien site industriel recensé (CASIAS/instruction) à proximité — "
                     "inventaire historique, pas une pollution avérée ; étude de sol à prévoir "
                     "en cas de projet sensible.")}


class _Ctx:
    def __init__(self, by_kind: dict, nearest: dict | None = None):
        self.by = by_kind
        self._nearest = nearest

    def kind_present(self, kind):
        return kind in self.by

    def intersections(self, _pid, kind):
        return self.by.get(kind, [])

    def nearest_point(self, _pid, _kind):
        return self._nearest


def _i(subtype, coverage, nom=None):
    return Intersection(subtype, nom, coverage, {}, None)


def test_sis_vigilance_forte_et_obligations_dites():
    """Parcelle DANS un SIS → VIGILANCE FORTE ; les DEUX obligations sont dites (L556-2 étude
    de sols, L125-7 information écrite de l'acheteur/locataire) ; source = ligne SIS."""
    ctx = _Ctx({"sol_pollue": [_i("sis", 0.4, "Sucrerie de BEAUFONDS")]})
    v = SolPollueLayer().evaluate(P, ctx, PARAMS)
    assert v.result == CascadeVerdict.SOFT_FLAG and v.severity == Severity.FORT
    assert "L556-2" in v.detail and "L125-7" in v.detail
    assert "information" in v.detail.lower()
    assert v.data_source_name == SRC_SIS


def test_casias_inventaire_pas_pollution_averee():
    """Site CASIAS ≤ 100 m → VIGILANCE faible ; le motif dit « inventaire historique, pas une
    pollution avérée » ; source = ligne CASIAS."""
    ctx = _Ctx({"sol_pollue": []},
               nearest={"dist": 42.0, "id": 7, "name": "Ancienne station-service", "subtype": "casias",
                        "attrs": {}})
    v = SolPollueLayer().evaluate(P, ctx, PARAMS)
    assert v.result == CascadeVerdict.SOFT_FLAG and v.severity == Severity.FAIBLE
    assert "pas une pollution avérée" in v.detail
    assert v.data_source_name == SRC_CASIAS


def test_catalogue_lot3():
    from labuse.ingestion.seed_sources import SOURCES, verifier_catalogue
    noms = {r["name"] for r in SOURCES}
    for n in ("Géorisques — secteurs d'information sur les sols (SIS)",
              "Géorisques — CASIAS (anciens sites industriels)",
              "DEAL — cartes de bruit stratégiques (CBS)"):
        assert n in noms, n
    assert verifier_catalogue() == []


def test_filtres_lot3_enregistres():
    from labuse.filtres.sources import FILTRES_RICHES
    for cle in ("georisques_sis", "georisques_casias", "bruit_itt_cerema", "bruit_cartes"):
        assert cle in FILTRES_RICHES, cle
    # bruit : jamais de contrôle « 24 communes » sur les libellés du flux Cerema (majuscules)
    assert FILTRES_RICHES["bruit_itt_cerema"].commune_nom_col is None


def test_registre_lot3_servi():
    from labuse.registre.couverture import COUCHE_PAR_CLE_FRONT, FICHE_PARCELLE_CLES
    from labuse.registre.donnees import DONNEES
    for cid in ("sis_classe", "casias_statut", "sols_parcelle", "sis_couche",
                "casias_couche", "bruit_couche", "bruit_carte_couche"):
        assert cid in DONNEES, cid
        assert DONNEES[cid].en_attente is None
    for cle in ("sis", "casias", "bruit_route", "bruit_carte"):
        assert COUCHE_PAR_CLE_FRONT[cle] in DONNEES
    assert "sols" in FICHE_PARCELLE_CLES
    from labuse.registre import ROBINETS
    servies = {c for r in ROBINETS.values() for c in r.chiffres}
    assert {"sols_parcelle", "sis_classe", "casias_statut"} <= servies


def test_cascade_rules_lot3():
    from labuse import config
    lc = next(l for l in config.cascade_rules()["layers"] if l["name"] == "sol_pollue")
    assert lc["params"]["severity_sis"] == "fort"
    assert "pas une pollution avérée" in lc["params"]["detail"]


def test_vanne_et_reservoirs_lot3():
    import csv

    from labuse import filtres
    labels = {e.get("label") for e in filtres.sources_a_job()}
    assert "bruit_cartes" in labels
    with open("docs/CIRCUIT/inventaire/reservoirs.csv") as f:
        ids = {r[0] for r in csv.reader(f, delimiter=";")}
    for rid in ("georisques_sis", "georisques_casias", "deal_bruit_cartes"):
        assert rid in ids, rid


def test_fiche_regle_sis():
    import labuse.regles as regles
    fiches = regles.charger()
    f = fiches["sis_classe"]
    assert f.reference is not None and "L125-7" in f.reference.article
    assert "informer par écrit" in f.reference.extrait
