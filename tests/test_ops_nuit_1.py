"""OPS-NUIT-1 — garde anti-rétrécissement du backup, mails ops ([URGENT]/[INFO], lien, plus de
« résolu »), résumé du matin, fenêtre reprenable du calcul de nuit."""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "deploy" / "scripts" / "backup_postgres.sh"


def _bash4() -> str | None:
    """Un bash >= 4 (le script prod utilise `mapfile`, absent du bash 3.2 de macOS). None → skip."""
    import shutil
    for cand in ("bash", "/opt/homebrew/bin/bash", "/usr/local/bin/bash", "/bin/bash"):
        exe = shutil.which(cand) or (cand if Path(cand).exists() else None)
        if not exe:
            continue
        out = subprocess.run([exe, "-c", "type mapfile"], capture_output=True, text=True)
        if out.returncode == 0:
            return exe
    return None


# ───────────────────────── 1. Backup : garde anti-rétrécissement (shell, sans base) ─────────────────────────

def _stub_bin(d: Path) -> None:
    """Pose des stubs pg_dump / pg_restore / psql dans `d` (ajouté en tête de PATH). pg_dump écrit un
    fichier de `STUB_DUMP_BYTES` octets ; pg_restore --list réussit ; psql ne liste aucune table illisible."""
    (d / "pg_dump").write_text(
        "#!/usr/bin/env bash\n"
        "out=''\n"
        "while [ $# -gt 0 ]; do [ \"$1\" = -f ] && { out=$2; shift; }; shift; done\n"
        "head -c \"${STUB_DUMP_BYTES:-1000000}\" /dev/zero > \"$out\"\n")
    (d / "pg_restore").write_text("#!/usr/bin/env bash\nexit 0\n")   # --list réussit toujours
    (d / "psql").write_text("#!/usr/bin/env bash\nexit 0\n")         # aucune table illisible
    for f in ("pg_dump", "pg_restore", "psql"):
        (d / f).chmod((d / f).stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def _run_backup(bash: str, backup_dir: Path, stub: Path, octets: int):
    env = dict(os.environ)
    env["PATH"] = f"{stub}:{env['PATH']}"
    env["LABUSE_BACKUP_DIR"] = str(backup_dir)
    env["LABUSE_BACKUP_KEEP"] = "2"
    env["STUB_DUMP_BYTES"] = str(octets)
    return subprocess.run([bash, str(SCRIPT)], env=env, capture_output=True, text=True)


def test_backup_garde_anti_retrecissement(tmp_path):
    """Un dump neuf < 70 % du dernier bon N'ÉVINCE PAS le bon : rotation annulée, suspect mis de côté,
    échec bruyant (exit 1). Le bon dump reste intact."""
    bash = _bash4()
    if not bash:
        pytest.skip("bash >= 4 (mapfile) absent — le script prod tourne sur Linux bash 4+")
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    stub = tmp_path / "bin"
    stub.mkdir()
    _stub_bin(stub)

    # 1) un gros dump « bon » (10 Mo) — passe, conservé.
    r1 = _run_backup(bash, backup_dir, stub, 10_000_000)
    assert r1.returncode == 0, r1.stderr
    bons = list(backup_dir.glob("labuse-labuse-*.dump"))
    assert len(bons) == 1 and bons[0].stat().st_size == 10_000_000
    bon_nom = bons[0].name

    # 2) un dump « rétréci » (0,1 Mo = 1 %) — la garde REFUSE la rotation.
    r2 = _run_backup(bash, backup_dir, stub, 100_000)
    assert r2.returncode == 1, "un dump 30 % plus petit doit échouer bruyamment"
    assert "ANTI-RÉTRÉCISSEMENT" in r2.stderr
    # le bon dump est toujours là (jamais évincé)…
    assert (backup_dir / bon_nom).exists() and (backup_dir / bon_nom).stat().st_size == 10_000_000
    # …le suspect est mis de côté HORS du glob de rotation (préfixe SUSPECT-)
    suspects = list(backup_dir.glob("SUSPECT-*.dump"))
    assert len(suspects) == 1
    # et aucun dump « normal » rétréci ne s'est substitué au bon
    assert all(f.stat().st_size == 10_000_000 for f in backup_dir.glob("labuse-labuse-*.dump"))


# ───────────────────────── 2. Mails ops : préfixes, lien, « résolu » supprimé (pur / base) ─────────────────────────

def test_prefixes_sujet_francais():
    from labuse import ops_alertes
    assert ops_alertes.URGENT == "[URGENT]" and ops_alertes.INFO == "[INFO]"
    assert ops_alertes._sans_prefixe("[URGENT] Sauvegarde HS") == "Sauvegarde HS"
    assert ops_alertes._sans_prefixe("[INFO] Résumé du matin") == "Résumé du matin"
    assert ops_alertes._sans_prefixe("[LABUSE] vieux") == "vieux"   # compat ancien préfixe


def test_lien_action_et_url_absolue():
    from labuse import ops_alertes
    from labuse.config import get_settings
    assert ops_alertes._lien_action("calcul-nuit:q_v21", None) == "/admin"
    assert ops_alertes._lien_action("x", "/admin/flux") == "/admin/flux"
    s = get_settings()
    url = ops_alertes._url_absolue(s, "/admin")
    assert url.endswith("/admin")
    assert ops_alertes._url_absolue(s, "https://x/y") == "https://x/y"


def test_seuil_retard_plancher_configurable():
    """OPS-NUIT-1 point 6(e) — le plancher de retard est réglable, 1 h par défaut (healthcheck)."""
    from labuse.config import get_settings
    assert float(getattr(get_settings(), "job_retard_seuil_min_h", 0)) == 1.0


@pytest.mark.db
def test_resoudre_nenvoie_plus_de_mail(db_session, monkeypatch):
    """OPS-NUIT-1 point 6(a) — ouvrir un incident envoie UN mail (URGENT) ; le résoudre n'en envoie
    AUCUN (la résolution part dans le résumé du matin)."""
    from labuse import ops_alertes
    envois = []
    monkeypatch.setattr(ops_alertes, "_sink",
                        lambda db, sujet, corps, *, dedup, lien="/admin": envois.append(sujet) or "ok")
    cle = "ops-nuit-test:x"
    ops_alertes.resoudre(db_session, cle)                 # rien d'ouvert → aucun mail
    assert envois == []
    assert ops_alertes.signaler(db_session, cle, "Bidule cassé", "détail", lien="/admin") == "ouvert"
    assert len(envois) == 1 and envois[0].startswith("[URGENT]")
    assert ops_alertes.resoudre(db_session, cle) is True  # résolu → AUCUN mail en plus
    assert len(envois) == 1
    # et il figure dans « résolus depuis » (pour le résumé)
    cles = [r["cle"] for r in ops_alertes.incidents_resolus_depuis(db_session, 26)]
    assert cle in cles


@pytest.mark.db
def test_resume_matin_part_toujours(db_session):
    """OPS-NUIT-1 point 6(b) — le résumé se construit TOUJOURS (best-effort), sujet préfixé, sections
    présentes. Un incident ouvert le rend [URGENT] avec un lien d'action ; sinon [INFO]."""
    from labuse import ops_alertes
    from labuse.config import get_settings
    from labuse.jobs_impl import _resume_matin_texte
    # état propre
    db_session.execute(__import__("sqlalchemy").text(
        "UPDATE ops_incidents SET resolu_at = now() WHERE cle = 'ops-nuit-resume:x' AND resolu_at IS NULL"))
    urgent, sujet, corps = _resume_matin_texte(db_session, get_settings())
    assert sujet.startswith("[URGENT]") or sujet.startswith("[INFO]")
    assert "Résumé du matin" in sujet
    for section in ("Calcul de nuit", "Sauvegarde", "Radar", "Verrous", "Cohérence", "Incidents ouverts"):
        assert section in corps, f"section « {section} » absente du résumé"
    # avec un incident ouvert → URGENT + lien d'action dans le corps
    ops_alertes.signaler(db_session, "ops-nuit-resume:x", "Geste attendu", "fais X", lien="/admin")
    urgent2, sujet2, corps2 = _resume_matin_texte(db_session, get_settings())
    assert urgent2 is True and sujet2.startswith("[URGENT]")
    assert "→ " in corps2   # un lien d'action est présent
    ops_alertes.resoudre(db_session, "ops-nuit-resume:x")


# ───────────────────────── 3. Calcul de nuit : fenêtre reprenable ─────────────────────────

def test_budget_borne_par_la_fin_de_fenetre():
    """OPS-NUIT-1 — le reste de fenêtre est positif avant fin_h, nul après ; sert à borner le budget."""
    from types import SimpleNamespace

    from labuse import jobs_impl
    s = SimpleNamespace(calcul_nuit_fin_h=5)
    reste = jobs_impl._secondes_avant_fin_fenetre(s)
    assert reste >= 0
    # fin_h déjà passée (fenêtre fermée) → 0 (pas de budget négatif).
    s_passe = SimpleNamespace(calcul_nuit_fin_h=0)
    assert jobs_impl._secondes_avant_fin_fenetre(s_passe) == 0.0
