"""QV22-1 (mandat Vic) — un candidat REFUSÉ ne bloque jamais la nuit suivante.

Jusqu'ici le calcul de nuit visait un label FIXE : un candidat déjà complet mais refusé (contrôles en
échec, ex. comptes divergents) était remesuré et re-refusé chaque nuit → blocage (constat 08/11). Ici :
le label est un POINTEUR (candidat_nuit) ; un candidat refusé est ARCHIVÉ et on avance au label suivant,
que le calcul recalcule FRAIS (socle reconstruit si le cadastre a bougé, étage 0 = le run lui-même).
"""
from __future__ import annotations

import contextlib
from types import SimpleNamespace

import pytest


# ─────────────────────────── jugements PURS (labuse.autonomie) ───────────────────────────

def test_label_suivant_incremente_le_dernier_nombre():
    from labuse.autonomie import label_suivant
    assert label_suivant("q_v21") == "q_v22"
    assert label_suivant("q_v22") == "q_v23"
    assert label_suivant("q_v9") == "q_v10"
    assert label_suivant("q_v21_sources") == "q_v22_sources"
    assert label_suivant("sans_chiffre") == "sans_chiffre_2"


def test_candidat_refuse_distingue_echec_dur_et_attente():
    from labuse.autonomie import Verdict, candidat_refuse
    assert candidat_refuse(Verdict(ok=False, echecs=["comptes divergents"])) is True
    # EN ATTENTE seul (banc de cohérence pas encore passé) n'est PAS un refus : run sain, on attend.
    assert candidat_refuse(Verdict(ok=False, en_attente=["cohérence : banc 03h45 pas passé"])) is False
    assert candidat_refuse(Verdict(ok=True)) is False


# ─────────────────────────── pointeur + archive (candidat_nuit) ───────────────────────────

def test_candidat_nuit_pointeur_et_archive(tmp_path, monkeypatch):
    from labuse import candidat_nuit
    monkeypatch.setattr(candidat_nuit, "_CONFIG", tmp_path)
    monkeypatch.setattr(candidat_nuit, "_FICHIER", tmp_path / "candidat_courant.json")
    monkeypatch.setattr(candidat_nuit, "_ARCHIVES", tmp_path / "candidats_archives")
    # pas de manifeste à copier dans ce test
    monkeypatch.setattr(candidat_nuit, "_archiver_manifeste", lambda label: None)

    # Pointeur absent → la GRAINE gouverne.
    assert candidat_nuit.label_courant("q_v21") == "q_v21"

    # On archive q_v21 (refusé) → avance à q_v22, trace le motif, reste en base (aucune table touchée).
    nouveau = candidat_nuit.archiver_et_avancer("q_v21", "REFUS — comptes divergents", le="2026-11-08T00:00:00+00:00")
    assert nouveau == "q_v22"
    assert candidat_nuit.label_courant("q_v21") == "q_v22"   # le pointeur gouverne désormais
    etat = candidat_nuit.lire()
    assert etat["archives"][-1] == {
        "label": "q_v21", "raison": "REFUS — comptes divergents", "le": "2026-11-08T00:00:00+00:00"}

    # Idempotent : ré-archiver q_v21 alors que le pointeur est déjà à q_v22 ne double pas l'archive.
    assert candidat_nuit.archiver_et_avancer("q_v21", "re-REFUS") == "q_v22"
    assert len(candidat_nuit.lire()["archives"]) == 1


# ─────────────────────────── socle : reconstruit SEULEMENT si périmé ───────────────────────────

def test_reconstruire_socle_a_jour_ne_relance_rien(monkeypatch):
    from labuse import jobs_impl
    from labuse import db as dbmod

    @contextlib.contextmanager
    def _scope():
        # frame = vivant → socle à jour
        yield SimpleNamespace(execute=lambda *a, **k: SimpleNamespace(scalar=lambda: 433229))
    monkeypatch.setattr(dbmod, "session_scope", _scope)

    def _interdit(*a, **k):
        raise AssertionError("socle à jour → aucune reconstruction (build_all) ne doit être lancée")
    monkeypatch.setattr(jobs_impl, "_run_sous_process_nice", _interdit)

    _log = SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None)
    res = jobs_impl._reconstruire_socle_si_perime(
        SimpleNamespace(calcul_nuit_fin_h=5, calcul_nuit_mem_mo=6000), _log)
    assert res == {"reconstruit": False, "n_frame": 433229}


# ─────────────────────────── intégration : refusé → archivé → run frais ───────────────────────────

def test_calcul_nuit_candidat_refuse_est_archive_et_relance(monkeypatch):
    """Candidat q_v21 déjà complet MAIS comptes divergents (431663 ≠ 433229) → il est ARCHIVÉ et le
    calcul relance un run FRAIS sous q_v22 (socle + flux-run), au lieu de re-mesurer q_v21 à l'infini."""
    from labuse import autonomie, bascule_flux, candidat_nuit, jobs_impl, ops_alertes, run_progress, runs
    from labuse import db as dbmod
    from labuse.jobs import JobContext

    monkeypatch.setenv("LABUSE_CALCUL_NUIT_PROMEUT", "0")
    monkeypatch.setenv("LABUSE_CALCUL_NUIT_FORCE", "1")   # pas de borne de fenêtre dans le test

    @contextlib.contextmanager
    def _fake_scope():
        yield SimpleNamespace(commit=lambda: None, execute=lambda *a, **k: None)
    monkeypatch.setattr(dbmod, "session_scope", _fake_scope)

    monkeypatch.setattr(jobs_impl, "_fenetre_calcul_ok", lambda s: (True, "ok"))
    monkeypatch.setattr(jobs_impl, "_declencheur_entree", lambda db, promu: (True, "test"))
    monkeypatch.setattr(autonomie, "doit_calculer", lambda *a, **k: (True, "test"))
    monkeypatch.setattr(run_progress, "en_cours", lambda: None)
    monkeypatch.setattr(runs, "promu_at", lambda: None)
    monkeypatch.setattr(runs, "current", lambda: "q_v20")
    monkeypatch.setattr(bascule_flux, "_run_complet", lambda db, run: (True, "complet (test)"))
    monkeypatch.setattr(jobs_impl, "_manifeste_candidat_present", lambda label: True)

    # q_v21 est REFUSÉ (comptes), q_v22 (le run frais) est OK (comptes alignés).
    def _mesures(db, cand, prec):
        if cand == "q_v21":
            return {"run_complet": True, "comptes_parcelles": 431663, "comptes_precedent": 433229,
                    "copro_actionnables": 0, "rouge_actionnables": 0, "paliers_total": 10, "paliers_change": 0,
                    "coherence_ecarts": 0, "coherence_erreurs": 0, "coherence_frais": True}
        return {"run_complet": True, "comptes_parcelles": 433229, "comptes_precedent": 433229,
                "copro_actionnables": 0, "rouge_actionnables": 0, "paliers_total": 10, "paliers_change": 0,
                "coherence_ecarts": 0, "coherence_erreurs": 0, "coherence_frais": True}
    monkeypatch.setattr(jobs_impl, "_mesures_run", _mesures)

    # on vise un pointeur VIERGE (graine q_v21) et on capture l'archivage.
    monkeypatch.setattr(candidat_nuit, "label_courant", lambda graine: "q_v21")
    archives: list = []
    def _arch(label, raison, **k):
        archives.append((label, raison))
        return autonomie.label_suivant(label)
    monkeypatch.setattr(candidat_nuit, "archiver_et_avancer", _arch)

    # le run frais : socle déjà à jour (pas de build_all) + flux-run capturé (on vérifie le label visé).
    monkeypatch.setattr(jobs_impl, "_reconstruire_socle_si_perime", lambda s, log: {"reconstruit": False})
    lances: list = []
    monkeypatch.setattr(jobs_impl, "_run_sous_process_nice",
                        lambda cmd, budget, preexec: (lances.append(cmd) or SimpleNamespace(returncode=0, stdout="", stderr="")))
    monkeypatch.setattr(ops_alertes, "resoudre", lambda db, cle: None)
    monkeypatch.setattr(ops_alertes, "signaler", lambda *a, **k: None)
    monkeypatch.setenv("LABUSE_ETAGE0_RUN", "")

    ctx = JobContext(db=None, dry_run=False, timeout_s=14400)
    jobs_impl.calcul_nuit(ctx)

    # q_v21 archivé pour cause de comptes ; un flux-run a été lancé pour q_v22.
    assert archives and archives[0][0] == "q_v21" and "compte" in archives[0][1]
    assert lances, "un run frais (flux-run) doit être lancé après archivage"
    cmd = lances[-1]
    assert "flux-run" in cmd and "q_v22" in cmd
    # le run frais est scoré sur SA cascade (étage 0 = lui-même), jamais sur le servi.
    import os
    assert os.environ.get("LABUSE_ETAGE0_RUN") == "q_v22"
    assert ctx.compteurs.get("label") == "q_v22"
    assert ctx.compteurs.get("promu") is False
