"""COCKPIT-1 (Lot C) — les 3 corrections appliquées avant merge : A mail-queue à 14:10, C oracle
verite-sources (aléas zonaux, séisme/feu non discriminants + incident refermé), D recap-matin retiré
mais les ALERTES restent (site en panne / disque / sauvegarde ratée partent par leur propre chemin).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.cli import _crontab_du_registre
from labuse.jobs import JOBS


# ─────────────── Correction A — mail-queue à 14:10 ───────────────

def test_mail_queue_a_1410_dans_le_registre():
    j = JOBS["mail-queue-consommer"]
    assert j.cron_utc == "10 10 * * *"      # 10:10 UTC = 14:10 Réunion
    assert j.heure_reunion == "14:10" and j.cadence == "quotidien"


def test_mail_queue_a_1410_dans_le_crontab():
    for tz in ("utc", "reunion"):
        c = _crontab_du_registre(tz)
        ligne = [l for l in c.splitlines() if "mail-queue-consommer" in l and not l.strip().startswith("#")]
        assert len(ligne) == 1, "une seule ligne active pour mail-queue"
        assert ("10 10 " in ligne[0]) if tz == "utc" else ("10 14 " in ligne[0])
        assert "*/5" not in ligne[0]        # plus toutes les 5 min (fini la collision 13:35)


# ─────────────── Correction C — oracle risque zonal ───────────────

def test_aleas_zonaux_retire_seisme_et_feu():
    from scripts.coherence.oracles import aleas_zonaux
    entree = ["Inondation", "Séisme", "Mouvements de terrain", "Feu de forêt", "Recul du trait de côte"]
    assert aleas_zonaux(entree) == ["Inondation", "Mouvements de terrain", "Recul du trait de côte"]
    # une parcelle hors zone de risque mappée : Géorisques ne voit QUE séisme + feu → aucun aléa zonal
    assert aleas_zonaux(["Séisme", "Feu de forêt"]) == []


def test_comparaison_risque_nest_plus_fausse_hors_zone():
    """Le cœur du faux écart du 15/10 : LABUSE ne porte aucune vigilance (parcelle hors zone), Géorisques
    « au point » liste séisme+feu (île-wide). Après la correction : aucun aléa ZONAL → ok (pas d'écart)."""
    from scripts.coherence.oracles import aleas_zonaux
    risques_geo = ["Séisme", "Feu de forêt"]
    risque_labuse = False
    ok = bool(aleas_zonaux(risques_geo)) == risque_labuse
    assert ok is True, "séisme/feu seuls ne doivent plus produire un écart hors zone"
    # un VRAI risque zonal (Inondation) reste discriminant : il n'est PAS filtré.
    assert aleas_zonaux(["Inondation", "Séisme"]) == ["Inondation"]
    assert (bool(aleas_zonaux(["Inondation", "Séisme"])) == risque_labuse) is False  # labuse=False → écart


def test_incident_verite_sources_se_referme_sans_faux(db_session):
    """COCKPIT-1 (corr. C) — « incident fermé avec sa raison » : une fois l'oracle recalibré, un passage
    SANS faux referme l'incident « verite-sources » par la porte unique (resoudre). C'est ce qui éteint
    le rouge permanent du 15/10 au prochain passage."""
    from labuse import ops_alertes, verite_sources
    ops_alertes.ensure_table(db_session)
    # on simule l'incident ouvert du 15/10
    db_session.execute(text("DELETE FROM ops_incidents WHERE cle='verite-sources'"))
    ops_alertes.signaler(db_session, "verite-sources", "Vérité sources : 3 écart(s)", "risque séisme/feu")
    assert any(i["cle"] == "verite-sources" for i in ops_alertes.incidents_ouverts(db_session))
    # un passage recalibré : plus aucun « faux » (séisme/feu ne comptent plus)
    verite_sources.journaliser_passage(db_session, {"lignes": [
        {"notion": "risques_presence", "objet": "97411…AS0114", "valeur_labuse": "aucune vigilance risque zonale",
         "valeur_oracle": "aucun risque ZONAL · séisme/feu île-wide (non discriminants)",
         "source_oracle": "Géorisques", "verdict": "vrai"}],
        "bilan": {"vrai": 1, "non_verifiable": 0}, "echantillon": []})
    assert all(i["cle"] != "verite-sources" for i in ops_alertes.incidents_ouverts(db_session)), \
        "l'incident verite-sources doit être refermé après un passage sans faux"


# ─────────────── Correction D — recap-matin retiré, les ALERTES restent ───────────────

def test_recap_matin_retire_partout():
    assert "recap-matin" not in JOBS
    for tz in ("utc", "reunion"):
        assert "recap-matin" not in _crontab_du_registre(tz)


def test_alerte_sauvegarde_ratee_part_sans_recap(db_session, tmp_path, monkeypatch):
    """« sauvegarde ratée » — aucune sauvegarde présente → l'incident PART par verifier_declencheurs
    (appelé par healthcheck), sans le mail récap supprimé."""
    from labuse import config, ops_alertes
    ops_alertes.ensure_table(db_session)
    monkeypatch.setattr(config.get_settings(), "backup_dir", str(tmp_path))   # dossier VIDE = aucun dump
    db_session.execute(text("DELETE FROM ops_incidents WHERE cle='sauvegarde-absente'"))
    ops_alertes.verifier_declencheurs(db_session)
    assert any(i["cle"] == "sauvegarde-absente" for i in ops_alertes.incidents_ouverts(db_session))


def test_site_en_panne_leve_un_incident(monkeypatch):
    """« site en panne » — /health injoignable 2 fois → healthcheck LÈVE → le runner ouvre
    l'incident job-echec:healthcheck (porte unique). On prouve que la sonde lève (le reste est le
    chemin standard des jobs)."""
    import types
    import urllib.request

    from labuse import jobs_impl

    def _ko(*a, **k):
        raise OSError("connexion refusée")
    monkeypatch.setattr(urllib.request, "urlopen", _ko)
    # 1 échec précédent déjà en mémoire → ce passage fait le 2e → doit lever.
    ctx = types.SimpleNamespace(precedent={"compteurs": {"echecs_consecutifs": 1}},
                                dry_run=False, compte=lambda **k: None)
    with pytest.raises(RuntimeError, match="health"):
        jobs_impl.healthcheck(ctx)
