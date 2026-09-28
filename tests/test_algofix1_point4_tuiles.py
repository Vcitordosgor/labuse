"""ALGO-FIX-1 (point 4) — après une bascule, aucune tuile ni écran ne sert l'ancien run EN SILENCE.

- la bascule MESURE un rebuild sur une commune (table temp) et EXTRAPOLE l'île ; < 15 min → enchaîne
  le rebuild, sinon → ligne « À faire » BLOQUANTE + la carte signale qu'elle n'est pas à jour ;
- l'onglet « À faire » porte une ligne « Reconstruire les tuiles » quand mvt_parcels est périmé ;
- le front lit le run servi à l'exécution (/config/run), plus figé au build (testé côté endpoint).
"""
from __future__ import annotations

from labuse import circuit_resume
from labuse.api import tiles


# ── DÉCISION de la bascule : seuil 15 min (logique pure, mesure monkeypatchée) ──
def test_planifier_enchaine_sous_15min(monkeypatch):
    monkeypatch.setattr(tiles, "mesurer_rebuild_commune",
                        lambda db, run_label=None: {"mesure_ok": True, "estimation_ile_min": 2.0,
                                                    "tient_en_15min": True})
    p = tiles.planifier_reconstruction_tuiles(None, run_label="q_x")
    assert p["strategie"] == "enchainer"


def test_planifier_bloque_au_dela_15min(monkeypatch):
    monkeypatch.setattr(tiles, "mesurer_rebuild_commune",
                        lambda db, run_label=None: {"mesure_ok": True, "estimation_ile_min": 42.0,
                                                    "tient_en_15min": False})
    p = tiles.planifier_reconstruction_tuiles(None, run_label="q_x")
    assert p["strategie"] == "bloquer" and p["duree_estimee_min"] == 42.0


def test_planifier_enchaine_par_prudence_si_mesure_ko(monkeypatch):
    monkeypatch.setattr(tiles, "mesurer_rebuild_commune",
                        lambda db, run_label=None: {"mesure_ok": False, "motif": "run non scoré"})
    p = tiles.planifier_reconstruction_tuiles(None, run_label="q_x")
    assert p["strategie"] == "enchainer", "mesure impossible → jamais un oubli silencieux de rebuild"


# ── L'onglet « À faire » : ligne BLOQUANTE quand les tuiles sont périmées ──
def _lignes(**kw):
    r = circuit_resume.composer_a_faire([], residuel=None, candidat=None, run_servi="q_v11_m137", **kw)
    return r["lignes"]


def test_ligne_reconstruire_quand_tuiles_perimees_run_different():
    lignes = _lignes(tuiles={"perime": True, "run_carte": "q_v10", "run_servi": "q_v11_m137",
                             "motif": "run", "estimation_min": 3.0})
    rec = [l for l in lignes if l["type"] == "reconstruire"]
    assert len(rec) == 1
    assert rec[0]["couleur"] == "rouge", "ligne BLOQUANTE"
    assert "q_v10" in rec[0]["phrase"] and "q_v11_m137" in rec[0]["phrase"]


def test_ligne_reconstruire_quand_amont_plus_recent():
    lignes = _lignes(tuiles={"perime": True, "run_carte": "q_v11_m137", "run_servi": "q_v11_m137",
                             "motif": "amont", "carte_le": "2026-09-14T10:00:00+04:00"})
    rec = [l for l in lignes if l["type"] == "reconstruire"]
    assert len(rec) == 1 and "recalculé depuis" in rec[0]["phrase"]


def test_pas_de_ligne_quand_tuiles_a_jour():
    assert not [l for l in _lignes(tuiles=None) if l["type"] == "reconstruire"]
    assert not [l for l in _lignes(tuiles={"perime": False}) if l["type"] == "reconstruire"]


# ── Le front lit le run à l'exécution : l'endpoint /config/run existe et rend runs.current() ──
def test_config_run_rend_le_run_vivant(monkeypatch):
    from labuse.api import app as app_mod
    from labuse import runs
    monkeypatch.setattr(runs, "current", lambda: "q_vivant")
    assert app_mod.config_run() == {"run": "q_vivant"}
