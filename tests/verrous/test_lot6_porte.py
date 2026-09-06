"""CIRCUIT-5 lot 6 — la commande, la porte, la page. Le Résumé REND la vérité des verrous
(dernier passage journalisé), le déploiement refuse au premier cassé."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import text

from labuse import circuit_resume, circuit_verrous as CV

pytestmark = pytest.mark.verrous

RACINE = Path(__file__).resolve().parents[2]


# ── le Résumé (lot 6.2) ─────────────────────────────────────────────────────────────────

def _composer(verrous):
    return circuit_resume.composer(
        [], [], compteurs={}, residuel=None, run_servi="run_x", candidat=None, verrous=verrous)


def test_resume_ligne_rouge_quand_un_verrou_casse():
    r = _composer({"casses": ["V2a", "V4b"], "orphelines": [], "muets": [], "rattachements": []})
    lignes = [li for g in r["groupes"] for li in g["lignes"]]
    rouge = next(li for li in lignes if li["titre"] == "verrous cassés")
    assert rouge["n"] == 2 and rouge["couleur"] == "rouge"
    assert "V2a" in rouge["phrase"] and "V4b" in rouge["phrase"]
    assert rouge["cible"]["type"] == "compteur"


def test_resume_lignes_a_decider_orphelines_et_muets():
    r = _composer({"casses": [], "orphelines": ["a", "b", "c"], "muets": ["mobpro"],
                   "rattachements": ["mairies"]})
    lignes = {li["titre"]: li for g in r["groupes"] for li in g["lignes"]}
    assert lignes["tables orphelines à purger"]["n"] == 3
    assert lignes["tables orphelines à purger"]["couleur"] == "gris"
    assert lignes["réservoirs sans lecteur, données sans réservoir"]["n"] == 2


def test_resume_sans_verrous_aucune_ligne_nouvelle():
    """Rétro-compatibilité : sans synthèse (verrous=None), le Résumé d'avant est inchangé."""
    r = _composer(None)
    titres = {li["titre"] for g in r["groupes"] for li in g["lignes"]}
    assert "verrous cassés" not in titres
    assert "tables orphelines à purger" not in titres


# ── la synthèse à coût page (lot 6.2) ───────────────────────────────────────────────────

@pytest.mark.db
def test_synthese_lit_le_dernier_passage_journalise(db_session):
    from labuse import circuit_journal
    circuit_journal.ensure(db_session)
    circuit_journal.journaliser(db_session, "controle", "verrous", "cron", "echec",
                                {"joues": 16, "casses": ["V3b"], "a_decider": ["V1c"]})
    s = CV.synthese_pour_page(db_session)
    assert s["casses"] == ["V3b"]
    assert s["jamais_joues"] is False
    assert s["phrases"]["V3b"] == CV.PHRASES["V3b"]
    # un passage PLUS RÉCENT et propre efface la ligne rouge
    circuit_journal.journaliser(db_session, "controle", "verrous", "cli", "ok",
                                {"joues": 16, "casses": [], "a_decider": []})
    assert CV.synthese_pour_page(db_session)["casses"] == []


# ── la porte (lot 6.1) ──────────────────────────────────────────────────────────────────

def test_deploy_sh_joue_les_verrous_avant_tout():
    """`deploy.sh` joue `labuse circuit verrous` AVANT toute pose, et refuse : binaire
    introuvable = refus, verrou cassé = refus — aucun contournement dans le script."""
    s = (RACINE / "deploy.sh").read_text(encoding="utf-8")
    porte = s.index("circuit verrous")
    pose = s.index("Pose du crontab")
    assert porte < pose, "la porte doit être jouée AVANT la pose"
    assert "exit 1" in s[s.index("REFUS : binaire labuse introuvable"):pose]
    assert "REFUS : un verrou est cassé" in s


def test_la_commande_couvre_tous_les_lots():
    """`labuse circuit verrous` joue chaque verrou des lots 1 à 5 (définition de fini)."""
    lots = {v.lot for v in CV.VERROUS}
    assert lots == {1, 2, 3, 4, 5}
    assert len(CV.VERROUS) == 16
    # un verrou = une phrase en français (règle 1 : sans phrase, pas un verrou)
    for v in CV.VERROUS:
        assert v.phrase and v.phrase == CV.PHRASES[v.id]


def test_le_marqueur_pytest_verrous_est_declare():
    s = (RACINE / "pyproject.toml").read_text(encoding="utf-8")
    assert "verrous:" in s


# ── la carte au détail du repère 68 (lot 6.2) ───────────────────────────────────────────

def test_verrous_md_se_lit_sans_le_code():
    """VERROUS.md : un verrou par ligne, la phrase de chacun y est (le document pour Vic)."""
    s = (RACINE / "docs" / "CIRCUIT" / "VERROUS.md").read_text(encoding="utf-8")
    for v in CV.VERROUS:
        assert f"**{v.id}**" in s, f"{v.id} absent de VERROUS.md"
    assert "labuse circuit verrous" in s and "labuse tables purger" in s
    assert "poubelle" in s and "DROP" in s
