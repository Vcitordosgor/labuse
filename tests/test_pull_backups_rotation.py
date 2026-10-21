"""OPS-ROTATION-1 — rotation locale du rapatriement VPS (deploy/scripts/pull_backups.sh).

Tests de PURE LOGIQUE SHELL : on `source` le script (le garde `BASH_SOURCE == $0` empêche
le rapatriement de se lancer) et on appelle directement les fonctions `rotation`,
`disque_libre_go`, `alerter_disque` sur un répertoire jetable. Aucun accès réseau/DB.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from shutil import which

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "deploy" / "scripts" / "pull_backups.sh"

pytestmark = pytest.mark.skipif(which("bash") is None, reason="bash absent")


def _call(func_call: str) -> subprocess.CompletedProcess:
    """Source le script puis exécute `func_call` dans un bash isolé."""
    return subprocess.run(
        ["bash", "-c", f"source '{SCRIPT}'; {func_call}"],
        capture_output=True, text=True,
    )


def _fake_dumps(dir_: Path, n: int) -> list[str]:
    """Crée n dumps horodatés avec des mtimes CROISSANTS (le i-ème est plus récent)."""
    noms = []
    for i in range(n):
        f = dir_ / f"labuse-labuse-2026101{i}-130000.dump"
        f.write_text("x")
        ts = 1_700_000_000 + i * 86_400          # +1 jour par fichier
        os.utime(f, (ts, ts))
        noms.append(f.name)
    return noms


def test_rotation_ne_garde_que_les_2_plus_recents(tmp_path):
    noms = _fake_dumps(tmp_path, 5)              # 20261010 … 20261014
    r = _call(f"rotation '{tmp_path}' 2")
    assert r.returncode == 0, r.stderr
    restants = sorted(p.name for p in tmp_path.glob("labuse*.dump"))
    assert restants == sorted(noms[-2:]), f"attendu les 2 plus récents, obtenu {restants}"
    # les 3 plus anciens ont bien été annoncés supprimés
    assert r.stdout.count("rotation : supprimé") == 3


def test_rotation_noop_si_deja_sous_le_seuil(tmp_path):
    _fake_dumps(tmp_path, 2)                     # déjà 2 → rien à supprimer
    r = _call(f"rotation '{tmp_path}' 2")
    assert r.returncode == 0, r.stderr
    assert len(list(tmp_path.glob("labuse*.dump"))) == 2
    assert "supprimé" not in r.stdout


def test_rotation_robuste_repertoire_vide(tmp_path):
    # set -e / pipefail : aucun dump ne doit PAS faire échouer la fonction
    r = _call(f"rotation '{tmp_path}' 2")
    assert r.returncode == 0, r.stderr


def test_rotation_ne_touche_pas_les_fichiers_etrangers(tmp_path):
    _fake_dumps(tmp_path, 3)
    (tmp_path / "autre-chose.dump").write_text("x")      # ne matche pas labuse*.dump
    (tmp_path / "pull.log").write_text("x")
    _call(f"rotation '{tmp_path}' 2")
    assert (tmp_path / "autre-chose.dump").exists()
    assert (tmp_path / "pull.log").exists()


def test_alerte_disque_declenche_sous_le_seuil(tmp_path):
    # seuil absurde (999999 Go) → alerte à coup sûr, code retour 1
    r = _call(f"alerter_disque '{tmp_path}' 999999")
    assert r.returncode == 1
    assert "ALERTE DISQUE" in r.stderr


def test_alerte_disque_silencieuse_au_dessus_du_seuil(tmp_path):
    r = _call(f"alerter_disque '{tmp_path}' 0")
    assert r.returncode == 0
    assert r.stderr.strip() == ""


def test_disque_libre_go_renvoie_un_entier(tmp_path):
    r = _call(f"disque_libre_go '{tmp_path}'")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().isdigit()
