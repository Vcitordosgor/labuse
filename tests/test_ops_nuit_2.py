"""OPS-NUIT-2 — RECETTE : faire taire les fausses alertes.

Chaque point du mandat, en test déterministe :
  · la vigie de sauvegarde ne juge QU'UN dump terminé (pas le fichier en cours d'écriture → « 1,2 Mo ») ;
  · « jamais réussi » n'est signalé qu'APRÈS le premier passage prévu du job + marge (plus au déploiement) ;
  · /readyz tolère une coupure courte (< 2 min) d'un redéploiement avant d'ouvrir l'incident ;
  · le contrôle de cohérence du calcul de nuit LIT le banc de 03h45 et reste « en attente » (pas « échec »)
    tant qu'un passage frais n'existe pas ;
  · le compteur Radar de la nuit est UNIQUE, par portail (pige_annonces) — même chiffre partout.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


# ───────────────────── 1. vigie sauvegarde : ne juger qu'un dump TERMINÉ ─────────────────────

def _ecrire_dump(d, nom, taille):
    p = d / nom
    p.write_bytes(b"0" * taille)
    return p


def test_dumps_termines_ecarte_le_dump_en_cours(tmp_path, monkeypatch):
    """Pendant l'écriture (backup en cours), le dump le plus récent (partiel) est ÉCARTÉ."""
    from labuse import ops_alertes
    bon = _ecrire_dump(tmp_path, "labuse-labuse-20261103-020000.dump", 6_000_000)
    import os
    os.utime(bon, (1, 1))                                   # le « bon » est le plus ancien
    partiel = _ecrire_dump(tmp_path, "labuse-labuse-20261104-020000.dump", 1_200_000)  # « 1,2 Mo » en cours
    os.utime(partiel, (2, 2))

    monkeypatch.setattr(ops_alertes, "_backup_en_cours", lambda: True)
    termines = ops_alertes._dumps_termines(str(tmp_path))
    assert [p.name for p in termines] == [bon.name]          # le partiel n'est pas jugé

    monkeypatch.setattr(ops_alertes, "_backup_en_cours", lambda: False)
    termines = ops_alertes._dumps_termines(str(tmp_path))
    assert termines[0].name == partiel.name                  # fini : on juge le plus récent


def test_vigie_ne_crie_pas_retrecie_pendant_ecriture(db_session, tmp_path, monkeypatch):
    """La vigie n'ouvre PAS « sauvegarde-retrecie » quand le petit dump est celui EN COURS d'écriture."""
    from labuse import config, ops_alertes
    import os
    bon = _ecrire_dump(tmp_path, "labuse-labuse-20261103-020000.dump", 6_000_000)
    os.utime(bon, (1, 1))
    partiel = _ecrire_dump(tmp_path, "labuse-labuse-20261104-020000.dump", 1_200_000)
    os.utime(partiel, (datetime.now().timestamp(), datetime.now().timestamp()))

    monkeypatch.setenv("LABUSE_BACKUP_DIR", str(tmp_path))
    config.get_settings.cache_clear()
    monkeypatch.setattr(ops_alertes, "_backup_en_cours", lambda: True)

    out = ops_alertes.verifier_declencheurs(db_session)
    config.get_settings.cache_clear()
    cles = {i["cle"] for i in ops_alertes.incidents_ouverts(db_session)}
    assert "sauvegarde-retrecie" not in cles                 # pas de fausse alerte sur le dump en cours
    assert out["sauvegarde"].get("backup_en_cours") is True
    # le dump JUGÉ est le bon (terminé), pas le partiel
    assert out["sauvegarde"]["dernier"] == bon.name


# ─────────────── 2. « jamais réussi » : après le premier passage prévu + marge ───────────────

def test_jamais_reussi_attend_le_premier_passage(db_session, monkeypatch, tmp_path):
    """Un job quotidien tout juste connu (aucun run) n'est PAS crié « jamais réussi » : il attend son
    premier passage prévu. Une fois ce passage + marge dépassé (job connu depuis la veille), il l'est."""
    from labuse import config, jobs_journal, ops_alertes

    monkeypatch.setenv("LABUSE_JOBS_STATE_DIR", str(tmp_path / "state"))
    config.get_settings.cache_clear()
    jobs_journal.ensure_table(db_session)
    from sqlalchemy import text as _text
    jobs_journal._ensure_premiere_vue(db_session)
    db_session.execute(_text("DELETE FROM job_premiere_vue"))      # base partagée : ardoise propre

    # 1er passage de la vigie : backup-postgres est VU pour la première fois (ancré à maintenant) → son
    # premier passage prévu est dans le futur → PAS « jamais réussi » (fin de la fausse alerte au déploiement).
    retards = {r["nom"]: r for r in ops_alertes._jobs_en_retard(db_session)}
    assert "backup-postgres" not in retards

    # on recule l'ancre de 2 jours (le job est connu depuis avant-hier, toujours aucun succès) → son
    # premier passage prévu est désormais loin derrière → « jamais réussi ».
    db_session.execute(
        __import__("sqlalchemy").text(
            "UPDATE job_premiere_vue SET vue_at = :v WHERE nom = 'backup-postgres'"),
        {"v": datetime.now(timezone.utc) - timedelta(days=2)})
    retards = {r["nom"]: r for r in ops_alertes._jobs_en_retard(db_session)}
    config.get_settings.cache_clear()
    assert "backup-postgres" in retards and retards["backup-postgres"]["motif"] == "jamais"


def test_jamais_reussi_n_escalade_plus_immediatement(db_session, monkeypatch, tmp_path):
    """Un « jamais réussi » ouvre l'incident SANS escalade immédiate (plus de mail ESCALADE à l'instant)."""
    from labuse import config, jobs_journal, ops_alertes

    monkeypatch.setenv("LABUSE_JOBS_STATE_DIR", str(tmp_path / "state"))
    config.get_settings.cache_clear()
    jobs_journal.ensure_table(db_session)
    from sqlalchemy import text as _text
    jobs_journal._ensure_premiere_vue(db_session)
    db_session.execute(_text("DELETE FROM job_premiere_vue"))      # base partagée : ardoise propre
    # backup-postgres connu depuis 3 jours, jamais réussi (une tentative ratée l'ancre)
    jobs_journal.enregistrer(db_session, {"nom": "backup-postgres", "statut": "echec",
                                          "debut": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
                                          "fin": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()})
    ops_alertes.verifier_declencheurs(db_session)
    config.get_settings.cache_clear()
    cles = {i["cle"] for i in ops_alertes.incidents_ouverts(db_session)}
    assert "job-retard:backup-postgres" in cles                 # l'incident existe
    assert "escalade:job-jamais:backup-postgres" not in cles    # mais PAS d'escalade immédiate


# ─────────────────── 3. /readyz : tolérer la coupure courte d'un redéploiement ───────────────────

def test_readyz_debounce_tolere_coupure_courte(db_session, monkeypatch, tmp_path):
    from labuse import config, ops_alertes

    monkeypatch.setenv("LABUSE_JOBS_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("LABUSE_READYZ_TOLERANCE_S", "120")
    config.get_settings.cache_clear()
    monkeypatch.setattr(ops_alertes, "_readyz_local", lambda: (False, "boot en cours"))
    ops_alertes.resoudre(db_session, "readyz")          # base de test persistante : partir d'un readyz propre
    ops_alertes._effacer_readyz_depuis()

    # 1er « pas prêt » : sous la tolérance → aucun incident (c'est sans doute un restart de déploiement).
    r1 = ops_alertes.vigie_readyz(db_session)
    assert r1["ready"] is False and r1.get("incident") is False and r1.get("tolere") is True
    assert "readyz" not in {i["cle"] for i in ops_alertes.incidents_ouverts(db_session)}

    # on fait « vieillir » le premier pas-prêt au-delà de la tolérance → l'incident s'ouvre.
    ops_alertes._ecrire_readyz_depuis(datetime.now(timezone.utc) - timedelta(seconds=200))
    r2 = ops_alertes.vigie_readyz(db_session)
    assert r2.get("incident") is True
    assert "readyz" in {i["cle"] for i in ops_alertes.incidents_ouverts(db_session)}

    # service revenu prêt → incident refermé + état débounce effacé.
    monkeypatch.setattr(ops_alertes, "_readyz_local", lambda: (True, "prêt"))
    r3 = ops_alertes.vigie_readyz(db_session)
    config.get_settings.cache_clear()
    assert r3["ready"] is True
    assert "readyz" not in {i["cle"] for i in ops_alertes.incidents_ouverts(db_session)}
    assert not ops_alertes._readyz_etat_path().exists()


# ─────── 4. cohérence du calcul de nuit : lire le banc de 03h45, « en attente » si pas frais ───────

def test_coherence_banc_pas_frais_en_attente_pas_echec():
    """Un banc de cohérence pas encore passé pour la nuit → EN ATTENTE (pas promu) mais PAS un échec."""
    from labuse.autonomie import controler_run
    base = {"manifeste_present": True, "run_complet": True, "comptes_parcelles": 100,
            "comptes_precedent": 100, "copro_actionnables": 0, "rouge_actionnables": 0,
            "paliers_change": 0, "paliers_total": 100,
            "coherence_ecarts": 0, "coherence_erreurs": 0}

    v_pas_frais = controler_run({**base, "coherence_frais": False}, palier_delta_max_pct=3.0)
    assert v_pas_frais.ok is False
    assert v_pas_frais.echecs == []                      # PAS un échec (pas d'incident URGENT)
    assert any("banc" in e for e in v_pas_frais.en_attente)
    assert "EN ATTENTE" in v_pas_frais.resume()

    v_frais = controler_run({**base, "coherence_frais": True}, palier_delta_max_pct=3.0)
    assert v_frais.ok is True and "cohérence" in v_frais.reussis

    # banc frais mais NON vert → vrai échec de cohérence (incident légitime).
    v_rouge = controler_run({**base, "coherence_frais": True, "coherence_erreurs": 2},
                            palier_delta_max_pct=3.0)
    assert v_rouge.ok is False and v_rouge.echecs and not v_rouge.en_attente


def test_mesures_run_lit_le_banc_et_juge_la_fraicheur(db_session, monkeypatch):
    """_mesures_run lit coherence_runs mode='ile' (le banc) et marque coherence_frais selon l'âge."""
    from sqlalchemy import text
    from labuse import config, jobs_impl

    db_session.execute(text(
        "INSERT INTO coherence_runs (ts, mode, n_ecarts, faux_client, incoherent, tolerable, erreurs_lecteur) "
        "VALUES (:ts, 'ile', 0, 0, 0, 0, 0)"),
        {"ts": datetime.now(timezone.utc) - timedelta(hours=1)})        # banc d'il y a 1 h = frais
    config.get_settings.cache_clear()
    m = jobs_impl._mesures_run(db_session, "q_vTEST", "q_vPREC")
    assert m["coherence_ecarts"] == 0 and m["coherence_frais"] is True

    # une ligne banc vieille de 2 jours → PAS fraîche.
    db_session.execute(text("DELETE FROM coherence_runs"))
    db_session.execute(text(
        "INSERT INTO coherence_runs (ts, mode, n_ecarts, faux_client, incoherent, tolerable, erreurs_lecteur) "
        "VALUES (:ts, 'ile', 0, 0, 0, 0, 0)"),
        {"ts": datetime.now(timezone.utc) - timedelta(days=2)})
    m2 = jobs_impl._mesures_run(db_session, "q_vTEST", "q_vPREC")
    config.get_settings.cache_clear()
    assert m2["coherence_frais"] is False


# ─────────────── 5. Radar : un seul chiffre par nuit, par portail (pige_annonces) ───────────────

def test_comptage_nuit_par_portail(db_session):
    from sqlalchemy import text
    from labuse.pige.comptage_nuit import comptage_nuit, ligne_resume

    # jour UNIQUE (futur) : la base de test est persistante — on évite toute collision avec des annonces
    # d'autres tests créées à une vraie date. On passe `jour` explicitement (pas l'ancre capture).
    jour = "2099-03-07"
    sfx = "opsn2"
    db_session.execute(text("DELETE FROM pige_annonces WHERE url_sortante LIKE :u"), {"u": f"{sfx}%"})
    bid = db_session.execute(text(
        "INSERT INTO pige_biens (commune) VALUES ('Saint-Denis') RETURNING bien_id")).scalar()
    # une capture auto PROUVANT qu'on ne lit PAS pige_passes.n_nouvelles (999) pour le compte canonique.
    db_session.execute(text(
        "INSERT INTO pige_passes (passe, captured_at, source, n_pages, n_nouvelles, n_maj) "
        "VALUES ('nouvelles', :ca, 'auto', 5, 999, 0) "
        "ON CONFLICT (passe, captured_at) DO UPDATE SET n_nouvelles = 999, source = 'auto'"),
        {"ca": "2099-03-07 23:16:00+04"})
    # 3 annonces Bien'ici + 1 Leboncoin créées ce jour Réunion ; 1 annonce la VEILLE (ne doit pas compter).
    rows = [("bienici", "2099-03-07 23:16:00+04", 990001),
            ("bienici", "2099-03-07 23:17:00+04", 990002),
            ("bienici", "2099-03-07 10:00:00+04", 990003),
            ("leboncoin", "2099-03-07 23:18:00+04", 990004),
            ("bienici", "2099-03-06 23:00:00+04", 990005)]
    for i, (portail, ca, lid) in enumerate(rows):
        db_session.execute(text(
            "INSERT INTO pige_annonces (bien_id, portail, url_sortante, created_at, list_id, statut_portail) "
            "VALUES (:b, :p, :u, :c, :l, 'active')"),
            {"b": bid, "p": portail, "u": f"{sfx}{i}", "c": ca, "l": lid})

    cn = comptage_nuit(db_session, jour=jour)
    assert cn["jour"] == jour
    assert cn["nouvelles"] == 4                                   # 3 bienici + 1 leboncoin (veille exclue)
    pp = {p["portail"]: p["nouvelles"] for p in cn["par_portail"]}
    assert pp == {"bienici": 3, "leboncoin": 1}
    # le chiffre canonique NE vient PAS de pige_passes.n_nouvelles (999) : vérité par portail = pige_annonces.
    assert cn["nouvelles"] != 999
    # noms d'affichage via pige/portails.py (l'apostrophe de « Bien’ici » est typographique).
    from labuse.pige import portails
    r = ligne_resume(cn)
    assert f"{portails.nom('bienici')} 3" in r and f"{portails.nom('leboncoin')} 1" in r
