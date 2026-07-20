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


def test_restore_fichier_invalide_erreur_claire(engine, tmp_path):
    from labuse.cli import app as cli_app

    bogus = tmp_path / "pas-un-dump.dump"
    bogus.write_bytes(b"ceci n'est pas une archive pg_dump")
    res = runner.invoke(cli_app, ["restore-db", "--file", str(bogus), "--yes"])
    assert res.exit_code == 1
    assert "invalide" in res.output

    res = runner.invoke(cli_app, ["restore-db", "--file", str(tmp_path / "absent.dump"), "--yes"])
    assert res.exit_code == 1 and "introuvable" in res.output
