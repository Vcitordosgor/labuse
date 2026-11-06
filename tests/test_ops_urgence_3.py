"""OPS-URGENCE-3 — recette des correctifs du mandat (famille UNITAIRE, sans base).

Couvre :
  · le calcul de nuit NE RELANCE PLUS un run déjà complet (passe droit aux contrôles/verdict) ;
  · le résumé du matin de John : texte propre SANS balise Markdown + repli si la sortie est COUPÉE ;
  · `IAResult.tronque` reflète bien l'arrêt au plafond de jetons.
"""
from __future__ import annotations

import contextlib
from types import SimpleNamespace

from labuse.ai.core import IAResult


# ───────────────────────── calcul de nuit : run déjà complet ─────────────────────────
def test_calcul_nuit_run_complet_ne_relance_pas_flux(monkeypatch):
    """Si `_run_complet` dit OUI, calcul_nuit ne spawn PAS flux-run : il va droit aux contrôles.
    (OPS-URGENCE-3 : un run fini ne doit plus être re-scoré ni tomber en « échec » sur un
    artefact absent — il passe au verdict.)"""
    from labuse import autonomie, bascule_flux, jobs_impl, ops_alertes, run_progress, runs
    from labuse import db as dbmod
    from labuse.jobs import JobContext

    monkeypatch.setenv("LABUSE_CALCUL_NUIT_PROMEUT", "0")   # chemin « calcule + contrôle, pas de bascule »

    @contextlib.contextmanager
    def _fake_scope():
        yield SimpleNamespace(commit=lambda: None, execute=lambda *a, **k: None)
    monkeypatch.setattr(dbmod, "session_scope", _fake_scope)

    monkeypatch.setattr(jobs_impl, "_fenetre_calcul_ok", lambda s: (True, "fenêtre ok"))
    monkeypatch.setattr(jobs_impl, "_declencheur_entree", lambda db, promu: (True, "test"))
    monkeypatch.setattr(autonomie, "doit_calculer", lambda *a, **k: (True, "test"))
    monkeypatch.setattr(run_progress, "en_cours", lambda: None)
    monkeypatch.setattr(runs, "promu_at", lambda: None)
    monkeypatch.setattr(runs, "current", lambda: "q_v20")
    # LE point du mandat : run DÉJÀ complet.
    monkeypatch.setattr(bascule_flux, "_run_complet", lambda db, run: (True, "complet (test)"))

    def _interdit(*a, **k):
        raise AssertionError("flux-run ne doit PAS être relancé sur un run déjà complet")
    monkeypatch.setattr(jobs_impl, "_run_sous_process_nice", _interdit)

    monkeypatch.setattr(jobs_impl, "_manifeste_candidat_present", lambda label: True)
    monkeypatch.setattr(jobs_impl, "_mesures_run", lambda db, cand, prec: {
        "run_complet": True, "comptes_parcelles": 10, "comptes_precedent": 10,
        "copro_actionnables": 0, "rouge_actionnables": 0,
        "paliers_total": 10, "paliers_change": 0,
        "coherence_ecarts": 0, "coherence_erreurs": 0, "coherence_frais": True,
    })
    monkeypatch.setattr(ops_alertes, "resoudre", lambda db, cle: None)
    monkeypatch.setattr(ops_alertes, "signaler", lambda *a, **k: None)

    ctx = JobContext(db=None, dry_run=False, timeout_s=14400)
    jobs_impl.calcul_nuit(ctx)   # ne doit PAS lever (flux-run interdit n'est jamais atteint)

    assert ctx.compteurs.get("calcul_saute") is True
    assert ctx.compteurs.get("controles_ok") is True
    assert ctx.compteurs.get("promu") is False


# ───────────────────────── John — texte propre + repli si coupé ─────────────────────────
def test_texte_propre_retire_le_markdown():
    from labuse.john.resume import _texte_propre
    brut = ("**URGENT** : le calcul est *fini*.\n"
            "# Radar\n"
            "- une puce\n"
            "* une autre\n"
            "Détail `technique` ici.")
    propre = _texte_propre(brut)
    assert "*" not in propre and "#" not in propre and "`" not in propre
    assert "URGENT" in propre and "fini" in propre and "technique" in propre
    assert "• une puce" in propre and "• une autre" in propre
    assert propre.splitlines()[1] == "Radar"       # le titre « # Radar » a perdu son dièse


def test_iaresult_tronque():
    assert IAResult(text="coupé au milieu", model="m", stop_reason="max_tokens").tronque is True
    assert IAResult(text="fini", model="m", stop_reason="end_turn").tronque is False
    assert IAResult(text="", model="m", degraded=True).tronque is False   # repli : pas de stop_reason


def test_generer_defaut_repli_si_degrade_ou_coupe(monkeypatch):
    """Le défaut rend '' (→ secours factuel) si le modèle est dégradé OU si la sortie est COUPÉE
    au plafond — jamais un mail tronqué « Radar du 05/ »."""
    from labuse.ai import core
    from labuse.john import resume

    monkeypatch.setattr(core, "complete",
                        lambda *a, **k: IAResult(text="…coupé", model="m", stop_reason="max_tokens"))
    assert resume._generer_defaut(None, {"resume_factuel": "x"}) == ""

    monkeypatch.setattr(core, "complete",
                        lambda *a, **k: IAResult(text="", model="m", degraded=True))
    assert resume._generer_defaut(None, {"resume_factuel": "x"}) == ""

    monkeypatch.setattr(core, "complete",
                        lambda *a, **k: IAResult(text="Tout va bien, Vic.", model="m", stop_reason="end_turn"))
    assert resume._generer_defaut(None, {"resume_factuel": "x"}) == "Tout va bien, Vic."
