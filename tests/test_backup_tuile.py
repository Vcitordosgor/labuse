"""RETOURS-8 (R10) — la tuile Backup du Pilotage lit le MÊME endroit/motif que les jobs.

Avant : `_age_backup` globait `*.dump` SEUL → les dumps du cron `backup-postgres` (`labuse-*.sql.gz`)
étaient invisibles, la tuile disait « aucun » alors qu'un backup existait. Elle lit désormais les deux
motifs, affiche taille + date, et distingue « répertoire non configuré » (dossier absent) d'« aucun ».
"""
from __future__ import annotations

import gzip
import types

from labuse import config
from labuse.api import dashboard


def _stub_settings(monkeypatch, rep):
    monkeypatch.setattr(config, "get_settings",
                        lambda: types.SimpleNamespace(backup_dir=rep))


def test_repertoire_absent_dit_non_configure(monkeypatch, tmp_path):
    _stub_settings(monkeypatch, str(tmp_path / "nexiste-pas"))
    assert dashboard._age_backup()["etat"] == "non_configure"


def test_repertoire_vide_dit_absent(monkeypatch, tmp_path):
    _stub_settings(monkeypatch, str(tmp_path))
    assert dashboard._age_backup()["etat"] == "absent"


def test_lit_le_dump_du_cron_sql_gz(monkeypatch, tmp_path):
    """Le dump du CRON (`labuse-*.sql.gz`) — que l'ancien glob `*.dump` ne voyait pas — est bien lu."""
    f = tmp_path / "labuse-labuse-20260902T030000Z.sql.gz"
    with gzip.open(f, "wb") as gz:
        gz.write(b"-- dump\n" * 1000)
    _stub_settings(monkeypatch, str(tmp_path))
    out = dashboard._age_backup()
    assert out["etat"] in ("ok", "ambre", "rouge")       # trouvé (plus « aucun »)
    assert out["fichier"] == f.name and out["taille_mo"] is not None
