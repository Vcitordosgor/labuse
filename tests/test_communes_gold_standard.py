"""LOT 6 — socle de généralisation : référentiel fiabilité + script générique (JAMAIS exécuté réel).

Verrouille : la config des 24 communes, le garde-fou de fiabilité (communes gold = fiables, le reste =
non fiable), et la sûreté du script générique (dry-run par défaut, confirmation spécifique à la commune,
refus de commune inconnue, classification d'état). Aucune exécution réelle, aucun accès base muté.
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

from labuse import communes
from labuse.ingestion.run_all import REUNION_COMMUNES

_SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "import_commune_gold_standard.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("import_commune_gold_standard", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Config & référentiel ──────────────────────────────────────────────────────
def test_config_couvre_les_24_communes_officielles():
    c = communes.load_communes()
    assert len(c) == 24
    officiels = {nom for _, nom in REUNION_COMMUNES}
    assert set(c) == officiels                       # exactement les 24, ni plus ni moins
    # INSEE cohérent avec le référentiel officiel
    by_insee = {insee: nom for insee, nom in REUNION_COMMUNES}
    for nom, e in c.items():
        assert by_insee[e["insee"]] == nom


def test_attendu_jamais_invente_hors_gold():
    # Les communes GOLD ont un attendu CONFIRMÉ (compte Etalab vérifié au run) ; toutes les autres
    # restent 'a_verifier' — jamais un nombre inventé tant que la commune n'a pas été importée.
    c = communes.load_communes()
    assert c["Saint-Paul"]["attendu"] == 51129
    for nom, e in c.items():
        if e["etat"] == "gold":
            assert isinstance(e["attendu"], int)            # confirmé par l'import réel
        else:
            assert e["attendu"] == "a_verifier"             # jamais inventé avant import


# ── Garde-fou fiabilité ───────────────────────────────────────────────────────
def test_saint_paul_est_fiable_gold():
    assert communes.is_reliable("Saint-Paul") is True
    r = communes.reliability("Saint-Paul")
    assert r["reliable"] is True and r["etat"] == "gold"
    assert r["title"] is None and r["warnings"] == []


def test_communes_partielles_non_fiables():
    # La Possession, L'Étang-Salé, Saint-Pierre, Le Tampon ET Saint-Louis sont passées GOLD (runs réussis) → plus dans cette liste.
    for nom in ("Saint-Denis", "Saint-Leu"):
        assert communes.is_reliable(nom) is False
        r = communes.reliability(nom)
        assert r["reliable"] is False
        assert "non encore validée" in r["title"].lower()
        assert any("commercialement" in w.lower() for w in r["warnings"])


def test_communes_gold_apres_runs():
    # Verrouille l'état post-runs : Saint-Paul (étalon) + La Possession + L'Étang-Salé + Saint-Pierre + Le Tampon + Saint-Louis fiables.
    for nom in ("Saint-Paul", "La Possession", "L'Étang-Salé", "Saint-Pierre", "Le Tampon", "Saint-Louis"):
        assert communes.is_reliable(nom) is True
        r = communes.reliability(nom)
        assert r["reliable"] is True and r["etat"] == "gold" and r["title"] is None


def test_commune_absente_non_fiable():
    for nom in ("Sainte-Marie", "Cilaos", "Salazie"):
        assert communes.is_reliable(nom) is False


def test_commune_hors_referentiel_non_fiable():
    r = communes.reliability("Marseille")
    assert r["reliable"] is False and r["etat"] == "inconnu"


def test_status_list_fiables_gold():
    items = communes.status_list()
    assert len(items) == 24
    fiables = {x["commune"] for x in items if x["reliable"]}
    # Saint-Paul (étalon) + La Possession + L'Étang-Salé (vague 1) + Saint-Pierre + Le Tampon + Saint-Louis (vague 2 réussies).
    assert fiables == {"Saint-Paul", "La Possession", "L'Étang-Salé", "Saint-Pierre", "Le Tampon", "Saint-Louis"}


def test_commune_known_anti_erreur():
    assert communes.commune_known(insee="97408", nom="La Possession") is True
    assert communes.commune_known(insee="97408", nom="Saint-Paul") is False   # INSEE/nom incohérents
    assert communes.commune_known(insee="13055", nom="Marseille") is False


# ── Script générique : sûreté (PUR, aucune exécution réelle) ──────────────────
def test_script_slug_et_phrase_confirmation():
    s = _load_script()
    assert s.slug("La Possession") == "LA_POSSESSION"
    assert s.slug("L'Étang-Salé") == "L_ETANG_SALE"
    assert s.confirm_phrase("La Possession") == "IMPORT_LA_POSSESSION_COMPLET"
    # la phrase est SPÉCIFIQUE à la commune (anti-erreur de commune)
    assert s.confirm_phrase("La Possession") != s.confirm_phrase("Saint-Paul")


def test_script_real_mode_exige_execute_et_confirm_exact():
    s = _load_script()
    import argparse
    ns = argparse.Namespace
    assert s.real_mode(ns(commune="La Possession", execute=False, confirm="IMPORT_LA_POSSESSION_COMPLET")) is False
    assert s.real_mode(ns(commune="La Possession", execute=True, confirm="")) is False
    assert s.real_mode(ns(commune="La Possession", execute=True, confirm="IMPORT_SAINT_PAUL_COMPLET")) is False
    assert s.real_mode(ns(commune="La Possession", execute=True, confirm="IMPORT_LA_POSSESSION_COMPLET")) is True


def test_script_refuse_commune_inconnue():
    s = _load_script()
    ok, _ = s.validate_target("13055", "Marseille")
    assert ok is False
    ok2, _ = s.validate_target("97408", "La Possession")
    assert ok2 is True


def test_script_classification_etat():
    s = _load_script()
    assert s.classify_state(0, 0, 0.0) == "absent"
    assert s.classify_state(13338, 0, 100.0) == "partiel"      # cadastre + évalué mais SANS bâti
    assert s.classify_state(51129, 83981, 100.0) == "gold"     # bâti + 100 % → Saint-Paul
    assert s.classify_state(5000, 0, 0.0) == "partiel"


def test_script_missing_gold_layers():
    s = _load_script()
    # une commune partielle (sans bâti/ppr/sar…) → toutes les gold manquent
    miss = s.missing_gold_layers({"voirie": 5000, "pente": 4000, "plu_gpu_zone": 500})
    assert "batiment" in miss and "ppr" in miss and "sar" in miss
    # Saint-Paul complet → aucune manquante
    full = {k: 1 for k in s.GOLD_LAYERS}
    assert s.missing_gold_layers(full) == []


def test_script_dry_run_par_defaut_zero_acces_base():
    # Les étapes mutantes en dry-run ne touchent JAMAIS la base (zéro engine, zéro write).
    s = _load_script()
    assert s.step_import_parcels("La Possession", "97408", 13338, dry_run=True) == {"dry_run": True}
    assert s.step_layers("La Possession", "97408", dry_run=True) == {"dry_run": True}
    assert s.step_cascade("La Possession", dry_run=True) == {"dry_run": True}


# ── Post-checks [G] & décision (PURS — dict de métriques mocké, aucune base) ───
def _good_metrics(s):
    return {
        "parcels": 13338, "distinct": 13338, "sections": 30,
        "geom_invalid": 0, "geom2975_null": 0, "evaluated": 13338,
        "layers": {"batiment": 5000, "voirie": 8000, "pente": 4000, "plu_gpu_zone": 663,
                   "ppr": 4, "sar": 100, "ravine": 200, "plu_gpu_prescription": 300},
        "zonage_pct": 99.6, "dup_groups": 0,
        "verdicts": {"opportunite": 150, "a_creuser": 5000, "exclue": 1000, "faux_positif_probable": 7188},
        "opp_rate_pct": 1.1, "micro_opp": 30, "indexes": list(s.EXPECTED_INDEXES),
        "pipeline": 0, "feedback": 0, "alertes": 0,
    }


_BEFORE = {"pipeline": 0, "feedback": 0, "alertes": 0, "bati": 0, "parcels": 13338}


def _decide(s, m, crit_lf=None, noncrit_lf=None):
    checks = s.postcheck_results(m, _BEFORE, 13338, crit_lf or [])
    return s.final_decision(checks, crit_lf or [], noncrit_lf or [])


def test_postchecks_succes_exit0():
    s = _load_script()
    code, _ = _decide(s, _good_metrics(s))
    assert code == s.EXIT_OK


def test_postchecks_echec_couche_critique_rollback():
    s = _load_script()
    # bâti absent ET signalé en erreur critique → ROLLBACK (1)
    m = _good_metrics(s)
    m["layers"]["batiment"] = 0
    code, _ = _decide(s, m, crit_lf=["batiment"])
    assert code == s.EXIT_ROLLBACK


def test_postchecks_couche_non_critique_refetch():
    s = _load_script()
    code, _ = _decide(s, _good_metrics(s), noncrit_lf=["osm_faux_positif"])
    assert code == s.EXIT_REFETCH


def test_postchecks_opportunites_explosees_nogo_qa():
    s = _load_script()
    m = _good_metrics(s)
    m["opp_rate_pct"] = 11.2          # cascade SANS bâti → taux explosif
    code, _ = _decide(s, m)
    assert code == s.EXIT_NOGO_QA


def test_postchecks_doublons_idu_rollback():
    s = _load_script()
    m = _good_metrics(s)
    m["distinct"] = 13000             # doublons d'IDU
    code, _ = _decide(s, m)
    assert code == s.EXIT_ROLLBACK


def test_postchecks_geometrie_invalide_rollback():
    s = _load_script()
    m = _good_metrics(s)
    m["geom_invalid"] = 5
    code, _ = _decide(s, m)
    assert code == s.EXIT_ROLLBACK


def test_postchecks_index_manquant_rollback():
    s = _load_script()
    m = _good_metrics(s)
    m["indexes"] = []                 # index GIST absents
    code, _ = _decide(s, m)
    assert code == s.EXIT_ROLLBACK


def test_final_decision_precedence_rollback_avant_qa():
    s = _load_script()
    m = _good_metrics(s)
    m["opp_rate_pct"] = 12.0          # QA KO
    code, _ = _decide(s, m, crit_lf=["batiment"])   # + critique KO
    assert code == s.EXIT_ROLLBACK   # rollback (1) l'emporte sur no-go QA (4)


def test_expected_min_jamais_invente():
    s = _load_script()
    # commune présente : plancher = compte en base (jamais un nombre inventé)
    assert s.expected_min_parcels({"parcelles_en_base": 13338, "attendu": "a_verifier"}, None) == 13338
    # commune absente : plancher = compte RÉEL importé (Etalab), pas une constante
    assert s.expected_min_parcels({"parcelles_en_base": 0, "attendu": "a_verifier"}, 8200) == 8200
    # Saint-Paul : attendu confirmé pris en compte
    assert s.expected_min_parcels({"parcelles_en_base": 51129, "attendu": 51129}, None) == 51129


# ── Rapport [H] (mocké, sans base, sans écriture) ─────────────────────────────
def test_rapport_genere_avec_donnees_mockees():
    s = _load_script()
    m = _good_metrics(s)
    checks = s.postcheck_results(m, _BEFORE, 13338, [])
    code, verdict = s.final_decision(checks, [], [])
    lines = s.build_report("La Possession", "97408", "re_couches_re_cascade", verdict, code,
                           _BEFORE, m, checks, [], {"cascade": 1830.0})
    md = "\n".join(lines)
    assert "La Possession" in md and "97408" in md
    assert "re_couches_re_cascade" in md
    assert "## Verdicts & opportunités" in md and "Opportunité : **150**" in md
    assert "Micro-opportunités" in md and "Taux d'opportunité" in md
    assert "## Conclusion :" in md and "SUCCÈS" in md
    assert "batiment : 5000" in md            # statut des couches
    assert s.report_path("La Possession") == "docs/communes/la_possession_RESULTS.md"


def test_write_report_dry_run_n_ecrit_rien(tmp_path, monkeypatch):
    s = _load_script()
    monkeypatch.chdir(tmp_path)
    out = s.write_report("La Possession", dry_run=True, lines=["# test"])
    assert out is None
    assert not (tmp_path / "docs" / "communes").exists()    # aucune écriture en dry-run


def test_rapport_couche_bloquee_listee():
    s = _load_script()
    m = _good_metrics(s)
    m["layers"]["ppr"] = 0
    checks = s.postcheck_results(m, _BEFORE, 13338, ["ppr"])
    lines = s.build_report("La Possession", "97408", "re_couches_re_cascade", "x", s.EXIT_REFETCH,
                           _BEFORE, m, checks, ["ppr"], None)
    md = "\n".join(lines)
    assert "ppr : BLOQUÉ" in md and "BLOQUÉES" in md


# ── Endpoint /communes/status ─────────────────────────────────────────────────
@pytest.mark.db
def test_communes_status_endpoint(engine):
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    with TestClient(app) as c:
        r = c.get("/communes/status").json()
    assert len(r["communes"]) == 24
    assert set(r["fiables"]) == {"Saint-Paul", "La Possession", "L'Étang-Salé", "Saint-Pierre", "Le Tampon", "Saint-Louis"}
    assert r["gold_reference"] == "Saint-Paul"
