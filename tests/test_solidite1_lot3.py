"""SOLIDITE-1 (Lot 3) — disque & sauvegardes. On prouve, sans VPS : le job de copie hors-VPS est au
registre, le contrôle de sauvegarde (absente / rétrécie) mord, les scripts ont une syntaxe saine et la
copie hors-VPS s'arrête PROPREMENT (code 3) quand elle n'est pas configurée (jamais d'envoi en clair)."""
import subprocess
from pathlib import Path

from labuse.jobs import JOBS

RACINE = Path(__file__).resolve().parents[1]


def test_backup_offsite_au_registre():
    j = JOBS.get("backup-offsite")
    assert j is not None and j.cadence.startswith("hebdo") and j.besoin_db is False


def test_restore_test_ne_restaure_plus_sur_le_vps():
    """L'impl VPS ne fait plus qu'un contrôle de lisibilité (.dump + pg_restore --list), pas une
    restauration complète (la vraie restauration = sur le Mac, deploy/mac/restore_test.sh)."""
    src = (RACINE / "src" / "labuse" / "jobs_impl.py").read_text(encoding="utf-8")
    deb = src.index("def restore_test(")
    corps = src[deb:deb + 1400]
    assert "pg_restore" in corps and "--list" in corps
    assert "labuse-*.dump" in corps and ".sql.gz" not in corps     # fini le glob .sql.gz obsolète
    assert "deploy/mac/restore_test.sh" in corps                   # pointe vers le test Mac


def test_scripts_syntaxe_bash():
    for rel in ("deploy/scripts/backup_offsite.sh", "deploy/scripts/menage_disque.sh",
                "deploy/mac/restore_test.sh"):
        r = subprocess.run(["bash", "-n", str(RACINE / rel)], capture_output=True, text=True)
        assert r.returncode == 0, f"{rel} : {r.stderr}"


def test_offsite_sarrete_proprement_si_non_configure():
    """Sans stockage objet (ni clé) configuré : code 3 (ni envoi, ni échec dur), message explicite."""
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin"}
    r = subprocess.run(["bash", str(RACINE / "deploy/scripts/backup_offsite.sh")],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 3 and "NON configur" in r.stdout


def test_menage_dry_run_par_defaut():
    """Le script de ménage n'exécute RIEN sans --execute (la ligne EXECUTE=0 par défaut)."""
    txt = (RACINE / "deploy/scripts/menage_disque.sh").read_text(encoding="utf-8")
    assert "EXECUTE=0" in txt and "--execute" in txt
    assert "p_model_ext_dataset" in txt   # explicitement GARDÉ (lu par l'API)


def test_controle_sauvegarde_absente_et_retrecie(db_session, tmp_path, monkeypatch):
    """La vigie sauvegarde (ops_alertes) : dossier vide → incident « absente » ; dump 2× plus petit que
    le précédent → incident « rétrécie »."""
    from labuse import ops_alertes, config
    ops_alertes.ensure_table(db_session)
    s = config.get_settings()
    monkeypatch.setattr(s, "backup_dir", str(tmp_path))
    # dossier vide → absente
    out = ops_alertes.verifier_declencheurs(db_session)
    assert out["sauvegarde"]["present"] is False
    assert "sauvegarde-absente" in {i["cle"] for i in ops_alertes.incidents_ouverts(db_session)}
    # deux dumps, le plus récent 2× plus petit → rétrécie
    (tmp_path / "labuse-labuse-20260101-000000.dump").write_bytes(b"x" * 1000)
    import os, time
    recent = tmp_path / "labuse-labuse-20260102-000000.dump"
    recent.write_bytes(b"x" * 300)
    os.utime(recent, (time.time() + 10, time.time() + 10))   # le plus récent
    out2 = ops_alertes.verifier_declencheurs(db_session)
    assert out2["sauvegarde"]["present"] is True
    cles = {i["cle"] for i in ops_alertes.incidents_ouverts(db_session)}
    assert "sauvegarde-absente" not in cles        # résolu (un dump est là)
    assert "sauvegarde-retrecie" in cles
