"""SILENCE-1 — « une carte = une vraie décision de Vic ; un mail = une vraie nouvelle ».

Tests de non-régression des silences du mandat :
  · point 2 — « jamais réussi » : le premier passage prévu se calcule EN UTC (le cron est UTC) même
    quand l'ancre arrive en heure locale Réunion (+04) ; resume-matin ne crie plus à 04h30 pour 07h30 ;
  · point 1 — après une injection réussie, l'acquittement remet la veille à « ok » (les cartes
    « nouvelle version » disparaissent) ;
  · point 3 — le résumé du matin est [INFO] quand rien ne casse, [URGENT] seulement sur incident ouvert,
    et sa liste « à traiter » ne contient ni escalades-doublons ni rien de déjà résolu ;
  · point 5 — G8 (avertissement) ne s'écrit plus « échec » dans le journal.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

REUNION = timezone(timedelta(hours=4))


# ─────────────── point 2 — le premier passage prévu se calcule en UTC ───────────────

def test_prochaine_apres_evalue_le_cron_en_utc_pas_en_local():
    """Le bug SILENCE-1 : `_prochaine_apres` recevait l'ancre `vue_at` en heure Réunion (+04, relue de
    Postgres dont le fuseau de session est Indian/Reunion) et comparait les champs cron à l'heure LOCALE.
    Pour resume-matin (`30 3 * * *` = 03:30 UTC = 07:30 Réunion), il rendait 03:30 RÉUNION (=23:30 UTC la
    veille) au lieu de 03:30 UTC → l'échéance « +1 h » tombait à 04:30 Réunion. On exige désormais 03:30
    UTC (= 07:30 Réunion)."""
    from labuse.ops_alertes import _prochaine_apres

    ancre = datetime(2026, 11, 3, 21, 0, 5, tzinfo=REUNION)   # exactement le vue_at de prod
    pp = _prochaine_apres("30 3 * * *", ancre)
    assert pp is not None
    assert pp.astimezone(timezone.utc) == datetime(2026, 11, 4, 3, 30, tzinfo=timezone.utc)
    assert pp.astimezone(REUNION).strftime("%H:%M") == "07:30"


def test_prochaine_apres_insensible_au_fuseau_de_l_ancre():
    """La même ancre, exprimée en UTC, en +04 ou naïve-UTC, doit donner le MÊME premier passage."""
    from labuse.ops_alertes import _prochaine_apres

    base_utc = datetime(2026, 11, 3, 17, 0, 5, tzinfo=timezone.utc)
    attendu = datetime(2026, 11, 4, 3, 30, tzinfo=timezone.utc)
    for ancre in (base_utc, base_utc.astimezone(REUNION), base_utc.replace(tzinfo=None)):
        pp = _prochaine_apres("30 3 * * *", ancre)
        assert pp.astimezone(timezone.utc) == attendu, ancre


def test_echeance_jamais_reussi_de_resume_matin_est_apres_0430_reunion():
    """Le symptôme exact du mandat, en arithmétique pure (sans DB) : pour l'ancre de prod (hier 21h00
    Réunion) et le cron de resume-matin, l'échéance « 1er passage prévu + marge 1 h » doit tomber à
    08h30 Réunion — donc STRICTEMENT APRÈS 04h30 Réunion, où l'alerte criait à tort."""
    from labuse.ops_alertes import _prochaine_apres

    ancre = datetime(2026, 11, 3, 21, 0, 5, tzinfo=REUNION)
    premier_passage = _prochaine_apres("30 3 * * *", ancre)
    echeance = premier_passage + timedelta(hours=1)   # marge plancher `job_retard_seuil_min_h` = 1 h
    maintenant_0430 = datetime(2026, 11, 4, 0, 30, tzinfo=timezone.utc)   # = 04h30 Réunion
    assert maintenant_0430 < echeance
    assert echeance.astimezone(REUNION).strftime("%H:%M") == "08:30"


# ─────────────── point 5 — la sonde BODACC ne « tombe » plus sur un hoquet serveur ───────────────

def test_sonde_api_non_json_est_injoignable_pas_illisible():
    """Un corps NON-JSON d'une API JSON (page d'erreur/maintenance rendue en 200) = hoquet serveur →
    « injoignable » (transitoire, couvert par la grâce), JAMAIS « illisible » (= notre lecteur cassé, en
    panne dès 3). C'est ce qui faisait tomber BODACC un matin sur 3 réponses HTML d'affilée."""
    from labuse import sentinelle

    def http_html(url, **k):
        return (200, {}, "<html><body>Service momentanément indisponible</body></html>")

    row = {"methode": "api", "url_version": "https://ex/api", "selecteur": "results.0.dateparution"}
    s = sentinelle.sonder_ligne(row, None, http=http_html)
    assert s.statut == "injoignable"


def test_sonde_api_chemin_absent_reste_illisible():
    """Un corps JSON VALIDE mais dont le chemin attendu manque = vrai contrat cassé → « illisible »
    (on NE masque PAS une vraie panne de contrat sous la grâce)."""
    from labuse import sentinelle

    def http_json_sans_chemin(url, **k):
        return (200, {}, '{"results": []}')

    row = {"methode": "api", "url_version": "https://ex/api", "selecteur": "results.0.dateparution"}
    s = sentinelle.sonder_ligne(row, None, http=http_json_sans_chemin)
    assert s.statut == "illisible"


def test_bodacc_seed_lit_la_fraicheur_reelle():
    """Le semis BODACC pointe l'endpoint `records` (dernière parution) et non le `metas.default.modified`
    figé à 2021 : un chemin de liste `results.0.dateparution`."""
    from labuse import sentinelle

    e = [x for x in sentinelle.SEED if x["name"].startswith("BODACC")][0]
    assert "/records?" in e["url"] and "dateparution" in e["url"]
    assert e["selecteur"] == "results.0.dateparution"


# ─────────────── point 5 — « 3 pointeurs de run », corrigé À LA SOURCE (self-heal) ───────────────

def test_realigner_vue_depuis_manifeste_corrige_la_divergence(tmp_path, monkeypatch):
    """La vue dérivée `served_run.txt` en retard sur le MANIFESTE (point de vérité) est RÉÉCRITE depuis
    le manifeste — pas seulement signalée. C'est le « corrigé à la source » du mandat."""
    import json

    from labuse import golden_ops, manifeste, runs

    served = tmp_path / "served_run.txt"
    manif = tmp_path / "served_manifest.json"
    served.write_text("q_v20\n", encoding="utf-8")
    manif.write_text(json.dumps({"scoring_run": "q_v21"}), encoding="utf-8")
    monkeypatch.setattr(golden_ops, "_SERVED_FILE", served)
    monkeypatch.setattr(runs, "_SERVED_FILE", served)
    monkeypatch.setattr(manifeste, "_FICHIER", manif)
    monkeypatch.delenv("LABUSE_SERVED_RUN", raising=False)
    manifeste.invalidate()
    runs.invalidate()

    heal = golden_ops.realigner_vue_depuis_manifeste()
    assert heal["realigne"] is True and heal["vers"] == "q_v21"
    assert runs._lire_fichier() == "q_v21"          # la vue suit désormais le manifeste
    assert golden_ops.realigner_vue_depuis_manifeste()["realigne"] is False   # idempotent


# ─────────────── point 1 — l'acquittement fait disparaître les cartes « nouvelle version » ───────────────

def _poser_source(db, nom, methode, vu, servi):
    from sqlalchemy import text
    sid = db.execute(text(
        "INSERT INTO data_sources (name, status, source_millesime) VALUES (:n, 'active', :s) RETURNING id"),
        {"n": nom, "s": servi}).scalar()
    db.execute(text(
        "INSERT INTO source_veille (source_id, methode, dernier_vu, dernier_statut, dernier_entete, "
        "echecs_consecutifs, actif, cadence_heures) "
        "VALUES (:s, :m, CAST(:vu AS varchar), 'nouvelle_version', CAST(:vu AS varchar), 2, true, 24)"),
        {"s": sid, "m": methode, "vu": vu})
    return sid


def _statut(db, sid):
    from sqlalchemy import text
    return db.execute(text(
        "SELECT v.dernier_statut, v.dernier_notifie_vu, v.injection_vu, v.echecs_consecutifs, "
        "d.source_millesime FROM source_veille v JOIN data_sources d ON d.id=v.source_id "
        "WHERE v.source_id=:s"), {"s": sid}).mappings().first()


def test_acquittement_remet_la_veille_ok_et_avance_le_servi(db_session):
    """Les trois cartes du mandat : une par méthode. Après acquittement, `dernier_statut` repasse « ok »
    (la carte disparaît), l'injection est notée, les échecs remis à zéro ; pour une source À VERSION
    (api/page) la version SERVIE suit l'amont injecté."""
    from labuse import sentinelle

    s_api = _poser_source(db_session, "SRC population (agent-like api)", "api", "2024", "2023")
    s_temoin = _poser_source(db_session, "SRC annuaire (témoin)", "temoin", "94166", "desc annuaire")
    s_agent = _poser_source(db_session, "SRC INSEE (agent)", "agent", "2023", "2023")

    for sid, nom in ((s_api, "SRC population (agent-like api)"),
                     (s_temoin, "SRC annuaire (témoin)"),
                     (s_agent, "SRC INSEE (agent)")):
        r = sentinelle.acquitter_apres_injection(db_session, nom)
        assert r["trouve"] is True
        st = _statut(db_session, sid)
        assert st["dernier_statut"] == "ok", nom                 # la carte « nouvelle version » disparaît
        assert st["dernier_notifie_vu"] == st["injection_vu"]    # acquittée, plus ré-annoncée
        assert st["echecs_consecutifs"] == 0

    # la version SERVIE n'avance QUE pour la méthode à version (api), jamais pour un libellé (témoin/agent)
    assert _statut(db_session, s_api)["source_millesime"] == "2024"
    assert _statut(db_session, s_temoin)["source_millesime"] == "desc annuaire"
    assert _statut(db_session, s_agent)["source_millesime"] == "2023"


# ─────────────── point 3 — résumé du matin : [INFO]/[URGENT] + « à traiter » sans doublon ───────────────

def test_incidents_a_traiter_retire_les_escalades_doublons():
    """Une escalade d'ancienneté qui double un incident déjà listé ne compte pas comme un 2e geste."""
    from labuse.ops_alertes import incidents_a_traiter

    ouverts = [
        {"cle": "verite-sources", "sujet": "Vérité sources : 3 écarts"},
        {"cle": "escalade:ancien:verite-sources", "sujet": "ESCALADE — 20 j"},
        {"cle": "restore-test-ancien", "sujet": "Aucune restauration enregistrée"},
    ]
    cles = {i["cle"] for i in incidents_a_traiter(ouverts)}
    assert cles == {"verite-sources", "restore-test-ancien"}   # l'escalade-doublon est retirée


def test_incidents_a_traiter_garde_une_escalade_orpheline():
    """Une escalade dont la base n'est plus ouverte reste listée (vrai geste encore en attente)."""
    from labuse.ops_alertes import incidents_a_traiter

    ouverts = [{"cle": "escalade:ancien:copie-externe", "sujet": "ESCALADE — disque"}]
    assert [i["cle"] for i in incidents_a_traiter(ouverts)] == ["escalade:ancien:copie-externe"]


def test_resume_matin_info_quand_rien_ne_casse(db_session, monkeypatch, tmp_path):
    """Avec un dump frais, une copie externe fraîche, une restauration enregistrée et AUCUN incident
    ouvert, le résumé part en [INFO] « rien à signaler » — jamais [URGENT]."""
    import json as _json
    from datetime import datetime as _dt, timezone as _tz

    from sqlalchemy import text as _text

    from labuse import config, jobs_impl, ops_alertes

    s = config.get_settings()
    monkeypatch.setattr(s, "backup_dir", str(tmp_path), raising=False)
    # un dump TERMINÉ, frais et de bonne taille (pas de backup en cours)
    (tmp_path / "labuse-labuse-20261104-0300.dump").write_bytes(b"x" * 2_000_000)
    # copie externe fraîche + restauration de contrôle OK enregistrée (referme ses vigies)
    (tmp_path / ".copie-externe.json").write_text(_json.dumps(
        {"copie_at": _dt.now(_tz.utc).isoformat(), "dump": "labuse-labuse-20261104-0300.dump"}),
        encoding="utf-8")
    (tmp_path / ".restore-test.json").write_text(_json.dumps(
        {"test_at": _dt.now(_tz.utc).isoformat(), "statut": "ok", "message": "lisibilité OK"}),
        encoding="utf-8")
    # ardoise d'incidents propre (base de test partagée)
    ops_alertes.ensure_table(db_session)
    db_session.execute(_text("UPDATE ops_incidents SET resolu_at = now() WHERE resolu_at IS NULL"))

    urgent, sujet, corps = jobs_impl._resume_matin_texte(db_session, s)
    assert urgent is False, corps
    assert sujet.startswith(ops_alertes.INFO)
    assert "rien à signaler" in sujet
    assert "Incidents ouverts : aucun" in corps


# ─────────────── point 6 — vérité sources : Géorisques régional ≠ vigilance de parcelle ───────────────

def test_oracle_risques_presence_ne_compte_plus_le_regional_comme_faux(monkeypatch):
    """Les 3 écarts « vérité sources » : Géorisques voit des risques AU PÉRIMÈTRE (Séisme, Feu,
    Inondation de secteur) alors que la parcelle n'a NI PPR NI aléa local. Sur la MÊME notion (le PPR/
    aléa de la PARCELLE), les deux s'accordent : le verdict n'est plus « faux », et le libellé servi
    devient « aucun PPR ni aléa local »."""
    import sys
    from pathlib import Path

    racine = Path(__file__).resolve().parents[1]
    if str(racine) not in sys.path:
        sys.path.insert(0, str(racine))
    from scripts.coherence import oracles

    def faux_json(url, **k):
        if "resultats_rapport_risque" in url:
            return {"risquesNaturels": {
                "inondation": {"present": True, "libelle": "Inondation"},
                "seisme": {"present": True, "libelle": "Séisme"},
                "feu": {"present": True, "libelle": "Feu de forêt"}}}
        return {}   # sismicité / radon : documentaires, sans donnée

    monkeypatch.setattr(oracles, "_json", faux_json)
    monkeypatch.setattr(oracles.time, "sleep", lambda *_: None)

    v = oracles.V()
    # parcelle sans PPR ni aléa LOCAL (fiche.aleas vide, aucune couche risque flaggée)
    temoin = {"idu": "97411000AS0114", "lon": 55.4568, "lat": -20.8884,
              "_fiche": {"aleas": [], "lines": []}}
    oracles.oracle_georisques(v, None, [temoin])

    rp = [l for l in v.lignes if l["notion"] == "risques_presence"]
    assert rp and rp[0]["verdict"] != "faux"                 # plus un écart « faux »
    assert rp[0]["valeur_labuse"] == "aucun PPR ni aléa local"   # le libellé servi exigé par le mandat


def test_oracle_risques_presence_detecte_encore_un_faux_positif_labuse(monkeypatch):
    """La sonde garde sa valeur : si LABUSE AFFIRME un risque local que Géorisques ne voit NULLE PART
    (ni au périmètre), c'est toujours « faux » (faux positif LABUSE)."""
    import sys
    from pathlib import Path

    racine = Path(__file__).resolve().parents[1]
    if str(racine) not in sys.path:
        sys.path.insert(0, str(racine))
    from scripts.coherence import oracles

    monkeypatch.setattr(oracles, "_json", lambda url, **k: {})   # Géorisques ne voit RIEN
    monkeypatch.setattr(oracles.time, "sleep", lambda *_: None)
    v = oracles.V()
    temoin = {"idu": "97411000AS0114", "lon": 55.4568, "lat": -20.8884,
              "_fiche": {"aleas": [{"nature": "inondation"}], "lines": []}}
    oracles.oracle_georisques(v, None, [temoin])
    rp = [l for l in v.lignes if l["notion"] == "risques_presence"]
    assert rp and rp[0]["verdict"] == "faux"


# ─────────────── point 7 — VRD/SPANC : manuelle « en attente de fichier », sans carte ───────────────

def test_manuelle_jamais_alimentee_sans_carte_deposer(monkeypatch):
    """Une source manuelle JAMAIS alimentée ne produit PAS de carte « Déposer » : le drapeau `a_verifier`
    (dashboard) exige un dépôt ANTÉRIEUR — sans fichier, elle reste « jamais vérifiée » (gris, benin),
    jamais « échue ». C'était le faux « à redéposer » de VRD/SPANC."""
    from datetime import datetime, timedelta, timezone

    from labuse.circuit_etats import etat_reservoir

    # reproduction de la règle `a_verifier` du dashboard (point 7) :
    def a_verifier(mode, cad, dernier_controle, now):
        return (bool(cad) and mode not in ("en_direct", "absente", "sans_millesime")
                and dernier_controle is not None and (now - dernier_controle).days > int(cad))

    now = datetime(2026, 11, 4, tzinfo=timezone.utc)
    # jamais alimentée : a_verifier False → « jamais vérifiée » (gris), PAS « échue » → aucune carte Déposer
    assert a_verifier("depot_manuel", 91, None, now) is False
    assert etat_reservoir({"mode": "depot_manuel", "a_verifier": False, "dernier_controle": None}) \
        == ("gris", "jamais vérifiée")
    # DÉJÀ alimentée puis cadence trimestrielle dépassée → a_verifier True → « échue » (à redéposer)
    vieux = now - timedelta(days=120)
    assert a_verifier("depot_manuel", 91, vieux, now) is True
    assert etat_reservoir({"mode": "depot_manuel", "a_verifier": True,
                           "dernier_controle": vieux.isoformat()}) == ("ambre", "échue")


def test_vrd_spanc_rappel_trimestriel():
    """Le rappel manuel VRD/SPANC est passé à une cadence TRIMESTRIELLE (91 j) — « un rappel trimestriel
    suffit » (point 7) — dans le semis des sources ET des rappels."""
    from labuse import sentinelle
    from labuse.ingestion import seed_sources

    assert seed_sources.MODE_ET_CADENCE["VRD / assainissement (SPANC)"][1] == 91
    rm = [x for x in sentinelle.RAPPELS_MANUELS if x["name"] == "VRD / assainissement (SPANC)"][0]
    assert rm["cadence_jours"] == 91
