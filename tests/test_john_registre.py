"""JOHN-TAYLOR-1 — méta-tests du registre + invariants PURS (aucune base).

Couvre : le job de veille au registre, les surfaces/modèles IA de John, le catalogue d'actions (liste
fermée + les deux à confirmation), et le verrou anti-invention (pur)."""
from __future__ import annotations

from labuse.jobs import JOBS, _FAMILLE_LIBELLE_ROLE, prochaine


def test_john_veille_au_registre():
    j = JOBS["john-veille"]
    assert j.planifie and not j.gel
    assert j.cadence == "quotidien" and j.heure_reunion == "03:00"
    assert j.touche == "exploitation" and not j.envoie_mail
    assert prochaine(j.cron_utc) is not None
    assert _FAMILLE_LIBELLE_ROLE["john-veille"][0] == 1        # famille « Veille des sources »
    assert _FAMILLE_LIBELLE_ROLE["john-veille"][3] is False    # IA → pas « lançable » libre (coût/plafond)


def test_famille_couvre_tous_les_jobs():
    assert set(_FAMILLE_LIBELLE_ROLE) == set(JOBS)


def test_surfaces_ia_de_john():
    from labuse.ai_models import MODEL_OPUS, MODEL_FACTUAL, model_for, SURFACES, INTERNE_KINDS
    assert MODEL_OPUS == "claude-opus-4-8"
    # chat / résumé / enquête = Opus ; veille = Haiku (factuel, pas cher).
    assert model_for("john-chat") == MODEL_OPUS
    assert model_for("john-resume") == MODEL_OPUS
    assert model_for("john-enquete") == MODEL_OPUS
    assert model_for("john-veille") == MODEL_FACTUAL
    # tout le coût de John est « interne » (jamais facturé à un client).
    for k in ("john-chat", "john-resume", "john-enquete", "john-veille"):
        assert k in SURFACES and k in INTERNE_KINDS


def test_opus_ajoute_au_pricing_du_ledger():
    from labuse.ai.core import PRICE
    from labuse.ai_models import MODEL_OPUS
    assert MODEL_OPUS in PRICE          # sinon le coût d'Opus serait compté 0 au ledger


def test_catalogue_actions_liste_fermee():
    from labuse.john import actions
    cles = {a["cle"] for a in actions.catalogue()}
    assert cles == {"injecter_source", "relancer_job", "lancer_sauvegarde", "accepter_incident",
                    "accepter_ecart", "promouvoir_run", "retirer_source"}
    a_confirmer = {a["cle"] for a in actions.catalogue() if a["confirme"]}
    assert a_confirmer == {"promouvoir_run", "retirer_source"}   # seules celles qui touchent les clients


def test_outils_de_lecture_connus():
    from labuse.john import outils
    assert "lire_jobs" in outils.NOMS and "lire_incidents" in outils.NOMS
    assert "lire_sources" in outils.NOMS and "lire_carnet" in outils.NOMS
    assert len(outils.NOMS) == len(outils.TOOLS)


def test_anti_invention_pur():
    from labuse.john.chat import anti_invention
    # un chiffre présent dans les lectures passe ; un chiffre absent est refusé.
    ok, _ = anti_invention("Il y a 3 incidents ouverts.", [{"ouverts": [1, 2, 3], "n": 3}])
    assert ok
    ko, raison = anti_invention("Il y a 999 incidents ouverts.", [{"n": 3}])
    assert not ko and "999" in raison
    # une réponse sans chiffre passe toujours (rien à vérifier).
    ok2, _ = anti_invention("Rien d'anormal ne ressort des lectures.", [{"n": 0}])
    assert ok2


def test_message_pause_budget():
    from labuse.john.budget import EtatBudget, message_pause
    e = EtatBudget(plafond_eur=50.0, depense_eur=50.0, appels=10, en_pause=True)
    msg = message_pause(e)
    assert "pause" in msg.lower() and "50" in msg


def test_carnet_seed_contient_les_doctrines_et_decisions():
    from labuse.john.carnet import SEED
    cles = {e["cle"] for e in SEED}
    assert "dec-bdnb-retiree" in cles and "dec-7j-grace" in cles
    assert "doc-classes-ab" in cles and "doc-rien-invente" in cles and "doc-liste-fermee" in cles
