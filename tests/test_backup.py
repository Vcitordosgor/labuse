"""Tests backup / restore (pg_dump / pg_restore) — sur la base de TEST uniquement."""
from __future__ import annotations

from shutil import which

import pytest
from sqlalchemy import create_engine, text
from typer.testing import CliRunner

pytestmark = [pytest.mark.db,
              pytest.mark.skipif(not which("pg_dump"), reason="pg_dump absent")]

runner = CliRunner()


def _admin():
    from labuse.config import get_settings
    url = get_settings().database_url.rsplit("/", 1)[0] + "/postgres"
    return create_engine(url, isolation_level="AUTOCOMMIT")


def test_backup_puis_restore_sur_base_temporaire(engine, tmp_path):
    import re
    import subprocess

    from labuse.cli import app as cli_app
    from labuse.config import get_settings

    # F4 (Phase 0 J1) : pg_dump doit être ≥ à la version du SERVEUR, sinon « aborting … server
    # version mismatch ». Env local ici : pg_dump 16 vs serveur 18 → skip DOCUMENTÉ (jamais un rouge
    # permanent). Dans un env où les versions concordent, le test s'exécute normalement.
    with engine.connect() as _c:
        srv_major = int(str(_c.execute(text("SHOW server_version")).scalar()).split(".")[0])
    _out = subprocess.run(["pg_dump", "--version"], capture_output=True, text=True).stdout
    _m = re.search(r"(\d+)", _out)
    if _m and int(_m.group(1)) < srv_major:
        pytest.skip(f"pg_dump {_m.group(1)} < serveur PostgreSQL {srv_major} (incompatibilité de version, env local)")

    # 1. backup de la base de test → fichier horodaté non vide
    res = runner.invoke(cli_app, ["backup-db", "--dir", str(tmp_path)])
    assert res.exit_code == 0, res.output
    dumps = list(tmp_path.glob("labuse-*.dump"))
    assert len(dumps) == 1 and dumps[0].stat().st_size > 0
    assert "Sauvegarde" in res.output

    # 2. restore dans une base TEMPORAIRE (jamais la base courante) → tables présentes
    tmp_db = "labuse_restore_qa"
    admin = _admin()
    with admin.connect() as c:
        c.execute(text(f'DROP DATABASE IF EXISTS "{tmp_db}"'))
        c.execute(text(f'CREATE DATABASE "{tmp_db}"'))
    try:
        target = get_settings().database_url.rsplit("/", 1)[0] + f"/{tmp_db}"
        res = runner.invoke(cli_app, ["restore-db", "--file", str(dumps[0]),
                                      "--target-url", target, "--yes"])
        assert res.exit_code == 0, res.output
        e2 = create_engine(target)
        with e2.connect() as c:
            tables = {t for (t,) in c.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'")).all()}
            assert {"parcels", "spatial_layers", "pipeline_entries", "parcel_enrichment"} <= tables
        e2.dispose()
    finally:
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{tmp_db}"'))
        admin.dispose()


def test_vp001_pg_dump_plus_vieux_que_le_serveur_refuse(engine, tmp_path, monkeypatch):
    """VP-001 (mandat VPS) : un pg_dump d'une majeure plus vieille que le serveur est refusé
    AVANT d'écrire quoi que ce soit, avec la marche à suivre (LABUSE_PG_BIN_DIR) — au lieu du
    « server version mismatch » cryptique de pg_dump. Le faux binaire prouve aussi que
    LABUSE_PG_BIN_DIR est bien la source du binaire quand il est posé."""
    from labuse import config
    from labuse.cli import app as cli_app

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake = fake_bin / "pg_dump"
    fake.write_text("#!/bin/sh\necho 'pg_dump (PostgreSQL) 9.6.24'\n")
    fake.chmod(0o755)
    monkeypatch.setenv("LABUSE_PG_BIN_DIR", str(fake_bin))
    config.get_settings.cache_clear()
    try:
        res = runner.invoke(cli_app, ["backup-db", "--dir", str(tmp_path / "out")])
        assert res.exit_code == 2, res.output
        assert "pg_dump 9" in res.output and "LABUSE_PG_BIN_DIR" in res.output
        assert not list((tmp_path / "out").glob("*.dump"))  # rien d'écrit
    finally:
        monkeypatch.delenv("LABUSE_PG_BIN_DIR", raising=False)
        config.get_settings.cache_clear()


def test_vp001_pg_bin_dir_binaire_absent_erreur_claire(engine, tmp_path, monkeypatch):
    """LABUSE_PG_BIN_DIR posé sur un dossier SANS pg_dump → erreur claire, pas de repli PATH
    silencieux (le repli masquerait justement le problème de version que la variable corrige)."""
    from labuse import config
    from labuse.cli import app as cli_app

    vide = tmp_path / "vide"
    vide.mkdir()
    monkeypatch.setenv("LABUSE_PG_BIN_DIR", str(vide))
    config.get_settings.cache_clear()
    try:
        res = runner.invoke(cli_app, ["backup-db", "--dir", str(tmp_path / "out")])
        assert res.exit_code == 2, res.output
        assert "introuvable" in res.output
    finally:
        monkeypatch.delenv("LABUSE_PG_BIN_DIR", raising=False)
        config.get_settings.cache_clear()


def test_restore_fichier_invalide_erreur_claire(engine, tmp_path):
    from labuse.cli import app as cli_app

    bogus = tmp_path / "pas-un-dump.dump"
    bogus.write_bytes(b"ceci n'est pas une archive pg_dump")
    res = runner.invoke(cli_app, ["restore-db", "--file", str(bogus), "--yes"])
    assert res.exit_code == 1
    assert "invalide" in res.output

    res = runner.invoke(cli_app, ["restore-db", "--file", str(tmp_path / "absent.dump"), "--yes"])
    assert res.exit_code == 1 and "introuvable" in res.output
