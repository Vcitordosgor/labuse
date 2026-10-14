"""DISQUE-EXTERNE-1 (14/10) — la copie hors-VPS est passée du stockage objet chiffré au disque externe
du Mac. Côté VPS il ne reste qu'une VIGIE : lire le marqueur `.copie-externe.json` déposé par le Mac
après chaque copie vérifiée, et ALERTER « branche le disque » si la dernière copie a plus de 10 jours.
On prouve, sans VPS : le lecteur de marqueur, la fraîcheur, l'incident, et la ligne du récap."""
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from labuse import config, ops_alertes

RACINE = Path(__file__).resolve().parents[1]


def _ecrire_marqueur(dossier: Path, *, age_j: float, dump="labuse-labuse-20261014-133004.dump"):
    quand = datetime.now(timezone.utc) - timedelta(days=age_j)
    (dossier / ops_alertes.MARQUEUR_COPIE_EXTERNE).write_text(json.dumps({
        "copie_at": quand.isoformat(), "dump": dump, "sha256": "a" * 64,
        "taille_mo": 6909.2, "disque": "MUSIQUE-VIDEO"}), encoding="utf-8")
    return quand


def test_offsite_plus_de_job_vps():
    """La copie hors-VPS n'est plus pilotée par le VPS : ni job au registre, ni script d'envoi."""
    from labuse.jobs import JOBS
    assert "backup-offsite" not in JOBS
    assert not (RACINE / "deploy/scripts/backup_offsite.sh").exists()
    # Le relais est bien le Mac.
    assert (RACINE / "deploy/mac/backup_offsite_disque.sh").is_file()
    assert (RACINE / "deploy/mac/com.labuse.backup-offsite.plist").is_file()


def test_lire_marqueur_absent_ou_valide(tmp_path):
    assert ops_alertes.lire_copie_externe(str(tmp_path)) is None
    quand = _ecrire_marqueur(tmp_path, age_j=0)
    lu = ops_alertes.lire_copie_externe(str(tmp_path))
    assert lu is not None and lu["disque"] == "MUSIQUE-VIDEO"
    assert abs((lu["copie_at"] - quand).total_seconds()) < 2
    # marqueur illisible → None, jamais d'exception
    (tmp_path / ops_alertes.MARQUEUR_COPIE_EXTERNE).write_text("{pas du json", encoding="utf-8")
    assert ops_alertes.lire_copie_externe(str(tmp_path)) is None


def test_vigie_absente_recente_puis_ancienne(db_session, tmp_path, monkeypatch):
    """Pas de marqueur → incident « branche le disque » ; copie récente → résolu ; > seuil → ré-ouvert."""
    ops_alertes.ensure_table(db_session)
    s = config.get_settings()
    monkeypatch.setattr(s, "backup_dir", str(tmp_path))
    monkeypatch.setattr(s, "copie_externe_seuil_j", 10, raising=False)

    # 1) aucun marqueur → incident ouvert
    out = ops_alertes.verifier_declencheurs(db_session)
    assert out["copie_externe"]["present"] is False
    assert "copie-externe-ancienne" in {i["cle"] for i in ops_alertes.incidents_ouverts(db_session)}

    # 2) copie récente (2 j) → présent, à jour, incident résolu
    _ecrire_marqueur(tmp_path, age_j=2)
    out2 = ops_alertes.verifier_declencheurs(db_session)
    assert out2["copie_externe"]["present"] is True and out2["copie_externe"]["age_j"] == 2
    assert "copie-externe-ancienne" not in {i["cle"] for i in ops_alertes.incidents_ouverts(db_session)}

    # 3) copie ancienne (15 j > seuil 10) → incident ré-ouvert, sujet « branche le disque »
    _ecrire_marqueur(tmp_path, age_j=15)
    out3 = ops_alertes.verifier_declencheurs(db_session)
    assert out3["copie_externe"]["age_j"] == 15
    inc = {i["cle"]: i for i in ops_alertes.incidents_ouverts(db_session)}
    assert "copie-externe-ancienne" in inc
    assert "branche le disque" in inc["copie-externe-ancienne"]["sujet"].lower()


def test_recap_affiche_la_copie_externe(db_session, tmp_path, monkeypatch):
    """Le récap du matin porte la date de la dernière copie externe dans la ligne des vigies."""
    from labuse import jobs_impl
    ops_alertes.ensure_table(db_session)
    s = config.get_settings()
    monkeypatch.setattr(s, "backup_dir", str(tmp_path))
    quand = _ecrire_marqueur(tmp_path, age_j=1)

    capte = {}
    monkeypatch.setattr(jobs_impl, "_envoyer_alerte",
                        lambda corps, **kw: capte.update(corps=corps, sujet=kw.get("sujet", "")))

    class _Ctx:
        db = db_session
        dry_run = True
        def compte(self, **kw): capte.setdefault("compte", {}).update(kw)

    jobs_impl.recap_matin(_Ctx())
    attendu = quand.astimezone().strftime("%d/%m")
    assert f"copie externe {attendu}" in capte["corps"]
    assert capte["compte"]["copie_externe"] == attendu
