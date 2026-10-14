"""DASHBOARD-FIX-1 (point 3) — la bascule commite ses 3 pointeurs, ou dit « 3 fichiers à commiter ».

On teste la fonction pure `_commit_pointeurs` sur un dépôt git jetable : elle commite EXACTEMENT les
trois fichiers config/* (jamais `git add -A`) avec le message « bascule: <run> », est idempotente
(rien à committer → ok sans commit vide), et renvoie ok:False (→ bandeau rouge) quand git est absent.
"""
import os
import subprocess

import pytest

from labuse import bascule_flux

# CHASSE-CALCULS-FIX-1 — les variables d'environnement git PRIMENT sur `-C` ; on les retire pour que
# `git -C <repo>` vise TOUJOURS <repo> (sinon un GIT_DIR ambiant — hook pre-push — redirige vers le
# vrai dépôt). Même env que celui construit par bascule_flux._commit_pointeurs.
_GIT_ENV = {k: v for k, v in os.environ.items()
            if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
                         "GIT_OBJECT_DIRECTORY", "GIT_PREFIX", "GIT_NAMESPACE")}


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=_GIT_ENV)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "config").mkdir()
    for f in bascule_flux._POINTEURS_CONFIG:
        (tmp_path / f).write_text("init\n", encoding="utf-8")
    (tmp_path / "autre.txt").write_text("hors pointeurs\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def test_commite_les_trois_pointeurs(repo):
    for f in bascule_flux._POINTEURS_CONFIG:
        (repo / f).write_text("q_v16\n", encoding="utf-8")   # les 3 pointeurs changent (comme une vraie bascule)
    (repo / "autre.txt").write_text("CHANGÉ hors geste\n", encoding="utf-8")   # ne doit PAS être commité
    res = bascule_flux._commit_pointeurs(repo, "q_v16")
    assert res["ok"] is True and res.get("sha")
    # le dernier commit porte le bon message…
    msg = _git(repo, "log", "-1", "--format=%s").stdout.strip()
    assert msg == "bascule: q_v16"
    # …et ne touche QUE les 3 pointeurs (autre.txt reste modifié, non commité)
    noms = set(_git(repo, "show", "--name-only", "--format=", "HEAD").stdout.split())
    assert noms == set(bascule_flux._POINTEURS_CONFIG)
    assert "CHANGÉ" in (repo / "autre.txt").read_text(encoding="utf-8")
    assert _git(repo, "status", "--porcelain", "--", "autre.txt").stdout.strip()   # encore sale


def test_idempotent_rien_a_committer(repo):
    """Pointeurs déjà commités : ok, sans créer un commit vide."""
    avant = _git(repo, "rev-parse", "HEAD").stdout.strip()
    res = bascule_flux._commit_pointeurs(repo, "q_v16")
    assert res["ok"] is True and res.get("rien_a_committer") is True
    assert _git(repo, "rev-parse", "HEAD").stdout.strip() == avant   # aucun nouveau commit


def test_git_indisponible_rend_bandeau(tmp_path):
    """Pas un dépôt git → ok:False : le dashboard lèvera le bandeau rouge « 3 fichiers à commiter »."""
    (tmp_path / "config").mkdir()
    for f in bascule_flux._POINTEURS_CONFIG:
        (tmp_path / f).write_text("x\n", encoding="utf-8")
    res = bascule_flux._commit_pointeurs(tmp_path, "q_v16")
    assert res["ok"] is False
    assert res["fichiers"] == list(bascule_flux._POINTEURS_CONFIG)
    assert res.get("motif")


def test_git_dir_ambiant_ne_touche_jamais_le_vrai_depot(tmp_path, monkeypatch):
    """CHASSE-CALCULS-FIX-1 — un GIT_DIR ambiant (un hook pre-push exécute ses outils avec GIT_DIR
    défini) ne doit JAMAIS détourner les git de `_commit_pointeurs` vers le dépôt de l'appelant :
    `git -C <arbre>` reste sur <arbre>, le vrai dépôt n'est ni commité ni reconfiguré (core.bare).
    Ce test MORD si l'on retire le nettoyage d'environnement (le commit partirait dans `vrai`)."""
    # (a) un dépôt « réel » sentinelle, core.bare=false explicite.
    vrai = tmp_path / "vrai"; vrai.mkdir()
    _git(vrai, "init", "-q")
    _git(vrai, "config", "core.bare", "false")
    # (b) GIT_DIR pointe sur le dépôt réel — exactement comme pendant un push.
    monkeypatch.setenv("GIT_DIR", str(vrai / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(vrai))
    # (c) un arbre JETABLE, où la bascule doit committer ses 3 pointeurs.
    jetable = tmp_path / "jetable"; jetable.mkdir()
    _git(jetable, "init", "-q")
    _git(jetable, "config", "user.email", "t@t"); _git(jetable, "config", "user.name", "t")
    (jetable / "config").mkdir()
    for f in bascule_flux._POINTEURS_CONFIG:
        (jetable / f).write_text("init\n", encoding="utf-8")
    _git(jetable, "add", "-A"); _git(jetable, "commit", "-q", "-m", "base")
    for f in bascule_flux._POINTEURS_CONFIG:
        (jetable / f).write_text("q_v19\n", encoding="utf-8")

    res = bascule_flux._commit_pointeurs(jetable, "q_v19")

    # le commit DOIT viser `jetable` malgré GIT_DIR=vrai…
    assert res["ok"] is True and res.get("sha"), res
    assert _git(jetable, "log", "-1", "--format=%s").stdout.strip() == "bascule: q_v19"
    # …et le dépôt RÉEL (GIT_DIR) est INTACT : core.bare inchangé, aucun commit « bascule ».
    assert _git(vrai, "config", "--get", "core.bare").stdout.strip() == "false"
    assert "bascule" not in _git(vrai, "log", "--format=%s", "-n", "9").stdout
