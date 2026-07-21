"""Moteur de segments Habitat — registry, évaluateur, presets, résilience.

Critère du mandat verrouillé ici : le moteur reste FONCTIONNEL sur une base SANS
parcel_solar / parcel_equipements (la base de test n'a naturellement aucune des
tables des mandats non mergés) — presets « partiels » sans erreur, jamais un crash.
"""
from __future__ import annotations

import pytest

from labuse import config
from labuse.segments import engine as seg
from labuse.segments import presets as presets_mod
from labuse.segments.registry import (EXPORT_COLS, FILTERS, JOINS, SORTS,
                                      compute_availability,
                                      reset_availability_cache)

# ───────────────────────── registry (pur, sans base) ─────────────────────────

def test_registry_integrite():
    """Chaque filtre/tri/colonne référence des jointures déclarées — le SQL ne vit
    QUE dans le registry."""
    for f in FILTERS.values():
        assert f.type in ("range", "bool", "enum"), f.cle
        for j in f.joins:
            assert j in JOINS, f"{f.cle} : jointure inconnue {j}"
    for s in SORTS.values():
        for j in s.joins:
            assert j in JOINS
    for k, (_h, _e, jkeys) in EXPORT_COLS.items():
        for j in jkeys:
            assert j in JOINS, f"export {k} : jointure inconnue {j}"


def test_seed_yaml_contrat():
    """Le seed versionné est valide : clés de filtres/tris/colonnes toutes connues,
    ≥ 11 métiers Habitat + les presets anticipés des autres mandats."""
    doc = config.load_yaml_config("segment_presets")
    presets = doc.get("presets") or []
    assert len(presets) >= 16   # M3 spin-off : presets solaire partis
    slugs = {p["slug"] for p in presets}
    for attendu in ("pergolas-terrasses", "paysagistes", "clotures-portails",
                    "artisans-renovation", "cuisinistes", "salles-de-bain",
                    "couvreurs-etancheite", "menuiseries-cyclonique", "termites-charpente",
                    "extensions-surelevations", "alarmes-telesurveillance",
                    "clim-pac",
                    "piscinistes-construction", "parc-piscines-entretien", "anc-travaux",
                    "elagage"):
        assert attendu in slugs, f"preset seedé manquant : {attendu}"
    for p in presets:
        assert presets_mod.validate_preset(p) == [], p["slug"]
        assert p.get("argumentaire"), f"{p['slug']} : argumentaire commercial requis"
    boosts = {p["slug"] for p in presets if p.get("boost_catnat")}
    assert {"couvreurs-etancheite", "menuiseries-cyclonique"} <= boosts


# ───────────────────────── évaluateur (base de test) ─────────────────────────

@pytest.mark.db
def test_disponibilite_detectee(db_session):
    """Les tables des mandats non mergés sont absentes → filtres grisés, avec le
    mandat qui les livrera ; les filtres sur tables présentes mais vides sont aussi
    indisponibles (une source vide n'a pas de sens produit)."""
    reset_availability_cache()
    avail = compute_availability(db_session, use_cache=False)
    for cle, mandat in [("piscine", "Détection Ortho"),
                        ("pv_detecte", "Détection Ortho"), ("zone_anc", "ANC & Végétation"),
                        ("ombrage_vegetal", "ANC & Végétation")]:
        assert avail[cle]["disponible"] is False, cle
        assert avail[cle]["mandat"] == mandat
    assert avail["communes"]["disponible"] is True   # aucune dépendance


@pytest.mark.db
def test_resilience_base_sans_tables_mandats(db_session):
    """CRITÈRE D'ACCEPTATION : base SANS parcel_solar/parcel_equipements — chaque
    preset seedé s'évalue sans erreur ; ses filtres orphelins sont listés inactifs."""
    reset_availability_cache()
    doc = config.load_yaml_config("segment_presets")
    avail = compute_availability(db_session, use_cache=False)
    for p in doc["presets"]:
        q = seg.build(db_session, p.get("filtres") or [], p.get("tri_defaut"),
                      colonnes_export=p.get("colonnes_export") or [], avail=avail)
        n = seg.run_count(db_session, q)          # exécute réellement le SQL
        assert n == 0                              # base de test vide
        assert seg.run_items(db_session, q, 10, 0) == []
    # un preset dépendant d'une source absente → badge « partiel » avec la liste
    # (M3 spin-off : l'exemple historique pv-residentiel est parti — même mécanique, preset piscines)
    pisc = next(p for p in doc["presets"] if p["slug"] == "parc-piscines-entretien")
    dispo, inactifs = presets_mod.preset_disponibilite(pisc, avail)
    assert dispo in ("partiel", "indisponible")
    assert inactifs                                   # au moins un filtre orphelin listé


@pytest.mark.db
def test_simulate_missing_force_indisponible(db_session):
    """La simulation d'absence (résilience) rend indisponible même une table présente."""
    reset_availability_cache()
    avail = compute_availability(db_session, use_cache=False,
                                 simulate_missing=frozenset({"dpe_records"}))
    assert avail["periode_construction"]["disponible"] is False
    q = seg.build(db_session, [{"cle": "periode_construction", "max": 1990}], None,
                  avail=avail)
    assert [f["cle"] for f in q.inactifs] == ["periode_construction"]
    assert seg.run_count(db_session, q) == 0       # s'exécute quand même


@pytest.mark.db
def test_injection_impossible(db_session):
    """Aucune chaîne cliente dans le SQL : clé inconnue → 422 ; valeur d'énum hors
    liste → 422 ; tri inconnu → 422 ; les valeurs passent en paramètres bindés."""
    reset_availability_cache()
    avail = compute_availability(db_session, use_cache=False)
    with pytest.raises(seg.FiltreInvalide):
        seg.build(db_session, [{"cle": "surface_m2; DROP TABLE parcels--"}], None, avail=avail)
    with pytest.raises(seg.FiltreInvalide):
        seg.build(db_session, [{"cle": "zonage_plu", "values": ["U'; DROP TABLE--"]}],
                  None, avail=avail)
    with pytest.raises(seg.FiltreInvalide):
        seg.build(db_session, [], "surface_desc; DELETE FROM parcels", avail=avail)
    with pytest.raises(seg.FiltreInvalide):
        seg.build(db_session, [{"cle": "pente_moy_deg", "max": "10; --"}], None,
                  avail=avail)
    # commune : valeur libre MAIS bindée — jamais concaténée dans le SQL
    payload = "Saint-Paul'; DROP TABLE parcels--"
    q = seg.build(db_session, [{"cle": "communes", "values": [payload]}], None, avail=avail)
    assert payload not in q.sql_count
    assert payload in q.params["f0_in"]
    assert seg.run_count(db_session, q) == 0


@pytest.mark.db
def test_groupe_ou(db_session):
    """{ou: [...]} compile en OR ; une branche indisponible est retirée sans erreur."""
    reset_availability_cache()
    avail = compute_availability(db_session, use_cache=False)
    q = seg.build(db_session, [{"ou": [{"cle": "surelevation_possible", "value": True},
                                       {"cle": "qpv", "value": True}]}], None, avail=avail)
    # surelevation dépend de parcel_residuel_bati (vide en test) → seule qpv survit
    assert " OR " not in q.sql_count or "qpv" in q.sql_count
    assert seg.run_count(db_session, q) == 0
    with pytest.raises(seg.FiltreInvalide):
        seg.build(db_session, [{"ou": [{"ou": [{"cle": "qpv"}]}]}], None, avail=avail)


@pytest.mark.db
def test_seed_et_crud_presets(db_session):
    """Seed idempotent (n'écrase jamais une édition admin) + upsert validé."""
    from sqlalchemy import text as _t
    for stmt in presets_mod.DDL.split(";"):     # dans LA transaction du test (rollback-ée)
        if stmt.strip():
            db_session.execute(_t(stmt))
    res1 = presets_mod.seed_presets(db_session)
    assert res1["erreurs"] == {}
    res2 = presets_mod.seed_presets(db_session)
    assert res2["inseres"] == []                    # déjà en base → aucun écrasement
    # édition admin conservée face au seed
    p = presets_mod.get_preset(db_session, "cuisinistes")
    p["argumentaire"] = "édité par Vic"
    presets_mod.upsert_preset(db_session, p)
    presets_mod.seed_presets(db_session)
    assert presets_mod.get_preset(db_session, "cuisinistes")["argumentaire"] == "édité par Vic"
    # contrat refusé : filtre inconnu
    with pytest.raises(seg.FiltreInvalide):
        presets_mod.upsert_preset(db_session, {
            "slug": "x-test", "nom": "X", "categorie": "renovation",
            "filtres": [{"cle": "nimporte_quoi"}]})


@pytest.mark.db
def test_export_csv_rgpd(db_session):
    """L'export « à l'occupant » n'expose AUCUNE colonne nominative : les en-têtes
    sont le français lisible du registry, où aucun nom de personne n'existe."""
    interdits = ("proprietaire", "denomination", "nom_usage", "siren", "dirigeant")
    for _cle, (header, expr, _j) in EXPORT_COLS.items():
        low = (header + " " + expr).lower()
        for mot in interdits:
            assert mot not in low, f"colonne d'export nominative : {header}"
