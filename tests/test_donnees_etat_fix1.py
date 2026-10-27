"""DONNEES-ETAT-FIX-1 — garde-fous des correctifs des écarts 1,2,3,4,6,7,9.

- Lot A : le déployeur `deploy_vps.sh` repose + vérifie le crontab à chaque passage (ou échoue).
- Lot B : la lecture du coût agent_source ne garde PAS `ia_log` verrouillé (cycle de verrous → échec du 28/10).
- Lot E : rotation des dumps VPS ramenée à 2 quotidiens + 1 hebdo.
(Lot C — sante-endpoints cède à la sauvegarde — est couvert dans test_cockpit_corrections_c.py ;
 Lot D — VACUUM réel — est couvert par ORF-03 dans test_fix_orfevre1_point2.py.)
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

RACINE = Path(__file__).resolve().parents[1]


# ─────────────── Lot A — le déploiement repose TOUJOURS le crontab ───────────────

def test_deploy_vps_repose_et_verifie_le_crontab():
    """Le bug ETAT-2 : un deploy changeait le binaire (registre) sans reposer /etc/cron.d/labuse.
    Désormais deploy_vps.sh régénère depuis le registre, sauvegarde l'ancien, pose, et VÉRIFIE —
    tout écart ARRÊTE le déploiement (exit 5)."""
    sh = (RACINE / "deploy/scripts/deploy_vps.sh").read_text()
    assert "jobs crontab --tz" in sh                              # régénère depuis le registre
    assert "--verifier /etc/cron.d/labuse" in sh                  # vérifie l'égalité au registre
    assert "labuse.bak-deploy-" in sh                             # sauvegarde l'ancien à côté
    assert "exit 5" in sh                                         # échoue bruyamment


# ─────────────── Lot B — la lecture du coût ne verrouille pas ia_log ───────────────

@pytest.fixture()
def _ia_log(tmp_path):
    """ia_log existe en local (créée paresseusement en prod par ai/core)."""
    from labuse.db import engine
    with engine().begin() as c:
        c.execute(text("CREATE TABLE IF NOT EXISTS ia_log "
                       "(id serial PRIMARY KEY, kind text, cout_eur double precision, "
                       "ts timestamptz DEFAULT now())"))
    return True


def test_le_cout_agent_source_libere_le_verrou(_ia_log):
    """FIX : après la lecture du coût, la session N'EST PLUS en transaction → aucun verrou sur ia_log →
    une session parallèle peut prendre l'ACCESS EXCLUSIVE (`ALTER … ADD COLUMN IF NOT EXISTS`) SANS
    attendre. C'est exactement ce qui a manqué le 28/10 (le passage réel a échoué en PendingRollbackError)."""
    from labuse import jobs_impl
    from labuse.db import session_factory
    Sess = session_factory()
    a, b = Sess(), Sess()
    try:
        jobs_impl._cout_agent_source_eur(a)            # lecture du coût (comme dans la boucle de l'agent)
        assert not a.in_transaction()                  # ← le FIX : transaction relâchée
        b.execute(text("SET lock_timeout = '3s'"))
        b.execute(text("ALTER TABLE ia_log ADD COLUMN IF NOT EXISTS compte_id integer"))
        b.commit()                                     # ne lève pas : le verrou était libre
    finally:
        a.rollback(); b.rollback(); a.close(); b.close()


def test_une_transaction_de_lecture_tenue_bloque_bien_l_alter(_ia_log):
    """Preuve du MÉCANISME que le fix évite : une transaction de lecture sur ia_log LAISSÉE OUVERTE
    (l'ancien comportement) bloque l'`ALTER … ADD COLUMN` d'une session parallèle (ACCESS EXCLUSIVE),
    jusqu'au lock_timeout. C'est le cycle de verrous observé en prod."""
    from labuse.db import session_factory
    Sess = session_factory()
    a, b = Sess(), Sess()
    try:
        a.execute(text("SELECT COALESCE(SUM(cout_eur), 0) FROM ia_log WHERE kind = 'agent_source'"))
        assert a.in_transaction()                      # a tient le verrou (pas de rollback : ancien état)
        b.execute(text("SET lock_timeout = '2s'"))
        with pytest.raises(Exception):                 # LockNotAvailable — l'ALTER ne passe pas
            b.execute(text("ALTER TABLE ia_log ADD COLUMN IF NOT EXISTS compte_id integer"))
    finally:
        a.rollback(); b.rollback(); a.close(); b.close()


# ─────────────── Lot E — rotation des dumps VPS (2 quotidiens + 1 hebdo) ───────────────

def test_rotation_dumps_reduite():
    from labuse.jobs_impl import BACKUP_ROTATION_N
    assert BACKUP_ROTATION_N == 2                                 # le job force 2 quotidiens
    sh = (RACINE / "deploy/scripts/backup_postgres.sh").read_text()
    assert "LABUSE_BACKUP_KEEP:-2" in sh                          # défaut script = 2
    assert "tail -n +2" in sh                                     # hebdo : 1 seul exemplaire
