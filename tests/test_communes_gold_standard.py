"""LOT 6 — socle de généralisation : référentiel fiabilité + script générique (JAMAIS exécuté réel).

Verrouille : la config des 24 communes, le garde-fou de fiabilité (Saint-Paul = gold, le reste = non
fiable), et la sûreté du script générique (dry-run par défaut, confirmation spécifique à la commune,
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


def test_attendu_jamais_invente_hors_saint_paul():
    # Seul Saint-Paul a un attendu confirmé (51 129) ; les autres = 'a_verifier' (jamais un nombre inventé).
    c = communes.load_communes()
    assert c["Saint-Paul"]["attendu"] == 51129
    for nom, e in c.items():
        if nom != "Saint-Paul":
            assert e["attendu"] == "a_verifier"


# ── Garde-fou fiabilité ───────────────────────────────────────────────────────
def test_saint_paul_est_fiable_gold():
    assert communes.is_reliable("Saint-Paul") is True
    r = communes.reliability("Saint-Paul")
    assert r["reliable"] is True and r["etat"] == "gold"
    assert r["title"] is None and r["warnings"] == []


def test_communes_partielles_non_fiables():
    for nom in ("La Possession", "L'Étang-Salé", "Saint-Denis", "Le Tampon"):
        assert communes.is_reliable(nom) is False
        r = communes.reliability(nom)
        assert r["reliable"] is False
        assert "non encore validée" in r["title"].lower()
        assert any("commercialement" in w.lower() for w in r["warnings"])


def test_commune_absente_non_fiable():
    for nom in ("Sainte-Marie", "Cilaos", "Salazie"):
        assert communes.is_reliable(nom) is False


def test_commune_hors_referentiel_non_fiable():
    r = communes.reliability("Marseille")
    assert r["reliable"] is False and r["etat"] == "inconnu"


def test_status_list_24_un_seul_fiable():
    items = communes.status_list()
    assert len(items) == 24
    fiables = [x for x in items if x["reliable"]]
    assert [x["commune"] for x in fiables] == ["Saint-Paul"]      # un seul gold aujourd'hui


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


# ── Endpoint /communes/status ─────────────────────────────────────────────────
@pytest.mark.db
def test_communes_status_endpoint(engine):
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    with TestClient(app) as c:
        r = c.get("/communes/status").json()
    assert len(r["communes"]) == 24
    assert r["fiables"] == ["Saint-Paul"]
    assert r["gold_reference"] == "Saint-Paul"
