"""Pré-vol M7 · P1 — câblage ingest-permits : la commande CLI appelle la voie VIVANTE (SDES/Dido).

L'ancienne voie ODS Région est morte depuis 2023-09 (permits.py, legacy documenté) ; le cron.d
appelait déjà permits_sdes, mais la commande CLI appelait encore la morte. Preuve par appel mocké.
"""
from __future__ import annotations

from typer.testing import CliRunner

from labuse import cli
from labuse.ingestion import permits_sdes


def test_cli_ingest_permits_appelle_la_voie_vivante(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(permits_sdes, "run",
                        lambda refresh=False, geocode=True, log=print: calls.append(
                            {"refresh": refresh, "geocode": geocode}) or {"upserts": 0})
    r = CliRunner().invoke(cli.app, ["ingest-permits", "--refresh"])
    assert r.exit_code == 0, r.output
    assert calls == [{"refresh": True, "geocode": True}]   # la voie SDES, avec le delta demandé
    assert "SDES/Dido" in r.output


def test_cli_ingest_permits_defaut_backfill(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr(permits_sdes, "run",
                        lambda refresh=False, geocode=True, log=print: calls.append(
                            {"refresh": refresh}) or {"upserts": 0})
    r = CliRunner().invoke(cli.app, ["ingest-permits"])
    assert r.exit_code == 0 and calls == [{"refresh": False}]


def test_cron_d_appelle_la_voie_vivante():
    # le cron de prod pointe permits_sdes --refresh (jamais la voie ODS morte)
    from pathlib import Path
    cron = (Path(__file__).resolve().parents[1] / "deploy/cron.d/sitadel").read_text(encoding="utf-8")
    assert "labuse.ingestion.permits_sdes --refresh" in cron
    assert "ingestion.permits " not in cron              # pas la legacy


def test_voie_morte_reste_documentee_non_appelee():
    # permits.py garde ses helpers vivants (nearby_permits, géocodage) mais ingest_permits (ODS)
    # n'est plus appelé par personne dans le code actif
    import subprocess
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    out = subprocess.run(["grep", "-rn", "ingest_permits(", "--include=*.py", str(root / "src")],
                         capture_output=True, text=True).stdout
    callers = [l for l in out.splitlines() if "def ingest_permits" not in l]
    assert callers == [], f"la voie ODS morte est encore appelée : {callers}"
