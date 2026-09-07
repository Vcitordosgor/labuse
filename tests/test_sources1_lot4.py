"""SOURCES-1 lot 4 — gardes : le cadre régional (SAR, DVF et potentiel foncier Région).

Le SAR officiel n'est diffusé nulle part en vecteur (07/09/2026) : la source entre en
`a_faire` avec réservoir LOGIQUE sur le proxy de vocations, rappel sentinelle 180 j (SAR
2050), et la doctrine D2 (jamais excluant) est verrouillée. Le DVF Région entre comme
ÉCHANTILLON PRODUCTEUR du filtre DVF (aucune donnée servie) ; le potentiel foncier Région
devient un contrôle de comparaison avec notre analyse."""
from __future__ import annotations

from labuse.cascade.context import Intersection, ParcelRef
from labuse.cascade.layers.phase1 import SarLayer
from labuse.enums import CascadeVerdict

P = ParcelRef(id=1, idu="97415000TT0001", commune="Test", surface_m2=1000.0)

SAR = {"spatial_kind": "sar", "plu_kind": "plu_gpu_zone", "uau_prefixes": ["U", "AU"],
       "divergent_subtypes": ["vocation_naturelle", "vocation_agricole", "vocation_continuite",
                              "vocation_coupure", "espace_naturel", "espace_agricole",
                              "coupure_urbanisation"],
       "info_subtypes": ["vocation_mixte", "vocation_rurale"]}


class _Ctx:
    def __init__(self, by_kind: dict):
        self.by = by_kind

    def kind_present(self, kind):
        return kind in self.by

    def intersections(self, _pid, kind):
        return self.by.get(kind, [])


def _i(subtype, coverage, name=None):
    return Intersection(subtype, name, coverage, {}, None)


def _as_list(out):
    return out if isinstance(out, list) else [out]


def test_sar_proxy_jamais_excluant():
    """Règle 5 du mandat verrouillée : le proxy SAR ne produit JAMAIS d'exclusion ni de
    malus, même en divergence totale U/AU ∩ vocation naturelle (doctrine D2)."""
    ctx = _Ctx({"sar": [_i("vocation_naturelle", 1.0)],
                "plu_gpu_zone": [_i(None, 1.0, "U")]})
    out = _as_list(SarLayer().evaluate(P, ctx, SAR))
    assert all(v.result not in (CascadeVerdict.HARD_EXCLUDE,) for v in out)
    assert all(v.result != CascadeVerdict.SOFT_FLAG or (v.severity and v.severity.value == "info")
               or "AU" in (v.detail or "") for v in out)


def test_catalogue_lot4():
    from labuse.ingestion.seed_sources import SOURCES, verifier_catalogue
    noms = {r["name"] for r in SOURCES}
    assert "SAR — schéma d'aménagement régional (Région/DEAL)" in noms
    assert "DVF Réunion (Région, data.regionreunion.com)" in noms
    assert verifier_catalogue() == []
    # le SAR est a_faire (couche officielle non diffusée), jamais « connecté » à tort
    sar = next(r for r in SOURCES if r["name"].startswith("SAR — schéma"))
    assert str(sar["status"].value if hasattr(sar["status"], "value") else sar["status"]) == "a_faire"
    assert "NON OPPOSABLE" in sar["legal_notes"]


def test_echantillon_producteur_dvf_rempli():
    """Le squelette CIRCUIT-3 est remplacé : 3 fenêtres agrégées, attendus lus chez le
    producteur régional, tolérance 5 % — et le contrôle sait les jouer (structure)."""
    from labuse.filtres import echantillon
    doc = echantillon.charger("dvf")
    assert doc and doc.get("lu_le") == "2026-09-07"
    assert not doc.get("a_valider")
    cles = {l["cle"] for l in doc["lignes"]}
    assert cles == {"ile-2019", "ile-2020", "97415-2020"}
    for l in doc["lignes"]:
        assert l["origine"]["url"].startswith("https://data.regionreunion.com/")
        assert l.get("tolerance_pct") == 5.0
    # fenêtres 2019/2020 seules (jeu Région figé à mi-2021 — jamais 2021+)
    assert not any("2021" in c or "2022" in c for c in cles)


def test_filtre_potentiel_foncier_region():
    from labuse.filtres.sources import FILTRES_RICHES
    f = FILTRES_RICHES["potentiel_foncier_region"]
    assert f.a_job is False and f.portee_run is False
    assert any(c.id == "d_potfoncier_convergence" for c in f.propres)
    # comparaison AVERTISSANTE (contrôle, jamais une quarantaine sur une divergence)
    ctrl = next(c for c in f.propres if c.id == "d_potfoncier_convergence")
    assert ctrl.severite == "avertissant"


def test_registre_lot4():
    from labuse.registre.donnees import DONNEES
    d = DONNEES["sar_divergence"]
    assert d.calcul == "moteur" and "sar_region" in d.reservoirs
    assert "non opposable" in d.definition
    import labuse.regles as regles
    fiches = regles.charger()
    assert "sar_divergence" in fiches
    assert "jamais rédhibitoires seuls" in (fiches["sar_divergence"].choix or "")


def test_reservoirs_et_pont_lot4():
    import csv
    with open("docs/CIRCUIT/inventaire/reservoirs.csv") as f:
        ids = {r[0] for r in csv.reader(f, delimiter=";")}
    assert {"sar_region", "region_dvf"} <= ids
    from labuse.circuit_etats import NOM_VERS_SLUG
    assert NOM_VERS_SLUG["SAR — schéma d'aménagement régional (Région/DEAL)"] == "sar_region"
    assert NOM_VERS_SLUG["DVF Réunion (Région, data.regionreunion.com)"] == "region_dvf"


def test_rappel_sar_2050_declare():
    from labuse.sentinelle import RAPPELS_MANUELS, RAISONS_NON_SURVEILLEES
    assert any(e["name"].startswith("SAR — schéma") and e["cadence_jours"] == 180
               for e in RAPPELS_MANUELS)
    assert "SAR 2050" in RAISONS_NON_SURVEILLEES["SAR — schéma d'aménagement régional (Région/DEAL)"]
