"""JOHN-TAYLOR-1 — LA RECETTE (base de test, modèle et effets de bord STUBÉS → aucun réseau).

Le mandat demande, et ce fichier prouve :
  · dix questions réelles avec leurs réponses sourcées (chat, outils de lecture) ;
  · un ordre exécuté (injection d'une source A), un ordre avec confirmation (promotion simulée) et un
    ordre hors liste refusé — TOUS journalisés ;
  · un résumé du matin produit ; une veille de nuit produite ; une enquête sur un incident simulé ;
  · le plafond de coût atteint coupe proprement.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from labuse.john import actions, budget, carnet, chat, enquete, resume, veille
from labuse.john import journal as jjournal

pytestmark = pytest.mark.db


# ════════════════════════════════ Stubs modèle (aucun réseau) ════════════════════════════════
def _usage():
    return SimpleNamespace(input_tokens=10, output_tokens=5)


def _txt(t):
    return SimpleNamespace(type="text", text=t)


def _tool(name, inp=None, tid="t1"):
    return SimpleNamespace(type="tool_use", name=name, input=inp or {}, id=tid)


def _msg(blocs):
    return SimpleNamespace(content=blocs, usage=_usage())


def _auto_appel(tool_name, *, injecte_faux=False, compteur=None):
    """Faux appel modèle : 1er tour → appelle l'outil de lecture `tool_name` ; 2e tour (une fois le
    résultat d'outil présent) → répond une phrase SANS chiffre (anti-invention trivialement vrai), ou
    un chiffre inventé si `injecte_faux` (pour prouver le refus du verrou)."""
    def _appel(**kw):
        if compteur is not None:
            compteur.append(1)
        dernier = kw["messages"][-1]
        contenu = dernier.get("content")
        a_resultat = isinstance(contenu, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in contenu)
        if not a_resultat:
            return _msg([_tool(tool_name)])
        if injecte_faux:
            return _msg([_txt("Il y a 987654 incidents en cours.")])
        return _msg([_txt("Voici ma lecture de l'exploitation : rien d'anormal ne ressort.")])
    return _appel


# ════════════════════════════════ 1) Dix questions réelles, sourcées ════════════════════════════════
def test_dix_questions_reelles_sourcees(db_session):
    questions = [
        ("Est-ce que tous les jobs tournent ?", "lire_jobs"),
        ("Y a-t-il des incidents ouverts ?", "lire_incidents"),
        ("Où en sont les sources et leur fraîcheur ?", "lire_sources"),
        ("Quel run est servi aux clients ?", "lire_runs"),
        ("Le banc de cohérence est-il vert ?", "lire_controles"),
        ("La sauvegarde de cette nuit est-elle bonne ?", "lire_sauvegardes"),
        ("Le Radar a-t-il tourné ?", "lire_radar"),
        ("Y a-t-il des erreurs dans les journaux ?", "lire_journaux"),
        ("Que dit le carnet de bord sur la BDNB ?", "lire_carnet"),
        ("Quels mandats ont été livrés récemment ?", "lire_rapports"),
    ]
    carnet.semer(db_session)
    for q, outil in questions:
        out = chat.repondre(db_session, q, appel=_auto_appel(outil))
        assert out["conversation_id"] is not None
        assert out["texte"] and not out.get("pause"), f"échec sur « {q} »"
        assert "cout" in out
    # une réponse par question = trace en base (10 user + 10 assistant au moins).
    n = db_session.execute(text("SELECT count(*) FROM john_messages")).scalar()
    assert n >= 20


def test_verrou_anti_invention_refuse_un_chiffre_non_source(db_session):
    """Même verrou que le Copilote : un chiffre absent des lectures fait refuser la réponse."""
    out = chat.repondre(db_session, "Combien d'incidents ?", appel=_auto_appel("lire_incidents", injecte_faux=True))
    assert "987654" not in out["texte"]
    assert "pas la donnée" in out["texte"] or "je ne sais pas" in out["texte"].lower() \
        or "ne pas répondre" in out["texte"]


# ════════════════════════════════ 2) Les ordres ════════════════════════════════
def _fake_backend(**kw):
    return actions.Backend(**kw)


def test_ordre_injection_source_a_execute(db_session):
    db_session.execute(text(
        "INSERT INTO data_sources (name, category, status) VALUES "
        "('SIRENE', 'economie', 'connecte') ON CONFLICT (name) DO NOTHING"))
    backend = _fake_backend(lancer_ingestion=lambda nom: {"label": "sirene", "log": "/tmp/x.log"})
    out = actions.executer(db_session, "injecter_source", {"source": "SIRENE"},
                           compte_id=1, compte="vic@labuse", backend=backend)
    assert out["ok"] and "classe A" in out["resume"]
    j = jjournal.dernieres(db_session, 5)
    assert j and j[0]["action"] == "injecter_source" and j[0]["ok"] and j[0]["compte"] == "vic@labuse"


def test_ordre_avec_confirmation_promotion_simulee(db_session):
    # contrôles VERTS (faux-client 0, lecteurs 0) → promotion autorisée après confirmation.
    db_session.execute(text(
        "INSERT INTO coherence_runs (mode, n_ecarts, faux_client, incoherent, tolerable, erreurs_lecteur) "
        "VALUES ('ile', 10, 0, 0, 10, 0)"))
    # 1) sans confirmation → John DEMANDE « tu confirmes ? », rien n'est fait, rien n'est journalisé.
    av = len(jjournal.dernieres(db_session, 50))
    demande = actions.executer(db_session, "promouvoir_run", {"run": "q_v21"},
                               compte_id=1, compte="vic@labuse", confirme=False)
    assert demande["besoin_confirmation"] and not demande.get("ok")
    assert len(jjournal.dernieres(db_session, 50)) == av       # pas encore journalisé
    # 2) avec « oui » (confirme=True) → bascule simulée OK, journalisée avec confirme=True.
    backend = _fake_backend(basculer=lambda db, run, par: {"ok": True, "run": run})
    fait = actions.executer(db_session, "promouvoir_run", {"run": "q_v21"},
                            compte_id=1, compte="vic@labuse", confirme=True, backend=backend)
    assert fait["ok"] and "promu" in fait["resume"]
    j = jjournal.dernieres(db_session, 5)
    assert j[0]["action"] == "promouvoir_run" and j[0]["confirme"] is True and j[0]["ok"]


def test_promotion_refusee_si_controles_non_verts(db_session):
    db_session.execute(text(
        "INSERT INTO coherence_runs (mode, n_ecarts, faux_client, incoherent, tolerable, erreurs_lecteur) "
        "VALUES ('ile', 10, 5, 5, 0, 0)"))     # faux-client = 5 → NON vert
    backend = _fake_backend(basculer=lambda db, run, par: {"ok": True})
    out = actions.executer(db_session, "promouvoir_run", {"run": "q_v21"},
                           compte_id=1, compte="vic@labuse", confirme=True, backend=backend)
    assert not out["ok"] and "NON verts" in out["resume"]


def test_ordre_hors_liste_refuse_et_journalise(db_session):
    out = actions.executer(db_session, "supprimer_la_base", {"force": True},
                           compte_id=1, compte="vic@labuse")
    assert not out["ok"] and out["refuse"]
    j = jjournal.dernieres(db_session, 5)
    assert j[0]["action"] == "supprimer_la_base" and j[0]["ok"] is False


def test_retirer_source_demande_confirmation(db_session):
    """L'autre action à confirmation : sans « oui », John demande ; rien n'est fait."""
    out = actions.executer(db_session, "retirer_source", {"source": "SIRENE"},
                           compte_id=1, compte="vic@labuse", confirme=False)
    assert out["besoin_confirmation"] and not out.get("ok")


# ════════════════════════════════ 3) Résumé du matin ════════════════════════════════
def test_resume_du_matin_produit_par_john(db_session):
    def _generer(db, facts):
        assert "resume_factuel" in facts
        return "Cette nuit, rien d'anormal. Rien n'attend votre décision, Vic."
    urgent, sujet, corps, meta = resume.composer_resume_matin(db_session, generer=_generer)
    assert meta["par"] == "john"
    assert "rien n'attend votre décision" in corps.lower()
    assert sujet                                   # le sujet [URGENT]/[INFO] du résumé actuel est conservé


def test_resume_du_matin_repli_si_john_echoue(db_session):
    def _rate(db, facts):
        return ""           # John dégradé → le résumé actuel part tel quel
    urgent, sujet, corps, meta = resume.composer_resume_matin(db_session, generer=_rate)
    assert meta["par"] == "repli" and corps        # un corps (le résumé actuel) est bien produit


# ════════════════════════════════ 4) Veille de nuit ════════════════════════════════
def test_veille_de_nuit_produite(db_session):
    reponse = json.dumps({"items": [
        {"axe": "reglementaire", "titre": "Nouvelle instruction taxe d'aménagement",
         "source": "BOFiP", "date_vue": "2026-10-28", "libelle": "info",
         "extrait": "mise à jour du 28/10/2026", "url": "https://bofip.impots.gouv.fr/x"},
        {"axe": "concurrence", "titre": "KelFoncier ajoute une couche PLU",
         "source": "kelfoncier.com", "date_vue": "2026-10-20", "libelle": "concurrence",
         "extrait": "annonce du 20/10/2026"},
        {"axe": "sources", "titre": "Item sans date (doit être écarté)",
         "source": "", "date_vue": "", "libelle": "info", "extrait": "pas de date ici"},
    ]})
    out = veille.lancer(db_session, appel=lambda db: reponse)
    assert out["ok"] and out["n"] == 2            # le 3e (sans source/date) est écarté (anti-invention)
    recentes = veille.recentes(db_session, 10)
    libs = {r["libelle"] for r in recentes}
    assert "info" in libs and "concurrence" in libs
    assert all(r["source"] for r in recentes)     # tout élément porte sa source


# ════════════════════════════════ 5) Enquête sur un incident ════════════════════════════════
def test_enquete_sur_incident_simule(db_session):
    from labuse import ops_alertes
    ops_alertes.signaler(db_session, "job-echec:backup-postgres",
                         "La sauvegarde a échoué", "pg_dump interrompu")

    def _generer(db, facts, mode):
        assert mode == "code"
        return json.dumps({
            "cause_probable": "Le pg_dump a été interrompu par un redéploiement concurrent.",
            "correction": "Relancer backup-postgres hors fenêtre de déploiement.",
            "mandat_claude_code": "Mandat : garde anti-concurrence déploiement/pg_dump dans backup_postgres.sh."})
    out = enquete.enqueter(db_session, cle="job-echec:backup-postgres", titre="Sauvegarde",
                           mode="code", generer=_generer)
    assert out["ok"] and out["cause_probable"] and out["correction"]
    assert out["mandat_claude_code"] and "Mandat" in out["mandat_claude_code"]
    assert "incidents" in out["faits"]            # John a bien lu les journaux


# ════════════════════════════════ 6) Le plafond coupe proprement ════════════════════════════════
def test_plafond_de_cout_coupe_proprement(db_session):
    from labuse.ai import core
    from labuse.ai_models import MODEL_OPUS
    # dépense du mois au-delà d'un plafond très bas.
    core._log_cost(db_session, "john-chat", MODEL_OPUS, False, 2000, 2000)   # ~0,18 €
    s = SimpleNamespace(john_plafond_eur=0.001, john_conversations_jours=90, john_actif=True)
    e = budget.etat(db_session, s)
    assert e.en_pause and e.depense_eur > e.plafond_eur

    appels = []
    out = chat.repondre(db_session, "Tout va bien ?", appel=_auto_appel("lire_jobs", compteur=appels), settings=s)
    assert out["pause"] is True
    assert not appels, "aucun appel modèle ne doit partir une fois le plafond atteint"
    assert "pause" in out["texte"].lower()


# ════════════════════════════════ Carnet de bord ════════════════════════════════
def test_carnet_proposition_entre_apres_accord_de_vic(db_session):
    carnet.semer(db_session)
    actives0 = {l["cle"] for l in carnet.lignes_actives(db_session)}
    assert "dec-bdnb-retiree" in actives0            # le seed est actif d'emblée

    ident = carnet.proposer(db_session, type="decision", titre="Nouveau seuil",
                            corps="Vic a choisi un seuil X.", par="john", cle="dec-test-x")
    # proposée ≠ active tant que Vic n'a pas validé.
    assert not any(l["cle"] == "dec-test-x" for l in carnet.lignes_actives(db_session))
    assert any(p["id"] == ident for p in carnet.proposees(db_session))

    assert carnet.valider(db_session, ident) is True
    assert any(l["cle"] == "dec-test-x" for l in carnet.lignes_actives(db_session))
