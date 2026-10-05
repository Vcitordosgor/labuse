"""DASHBOARD-FIX-1 (point 3) — la bascule commite ses 3 pointeurs, ou dit « 3 fichiers à commiter ».

On teste la fonction pure `_commit_pointeurs` sur un dépôt git jetable : elle commite EXACTEMENT les
trois fichiers config/* (jamais `git add -A`) avec le message « bascule: <run> », est idempotente
(rien à committer → ok sans commit vide), et renvoie ok:False (→ bandeau rouge) quand git est absent.
"""
import subprocess

import pytest

from labuse import bascule_flux


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


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
