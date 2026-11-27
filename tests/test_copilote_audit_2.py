from uuid import uuid4
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from labuse.copilote_v2 import historique, registre_faits, resume_fiche
from labuse.copilote_v2.answering import answer
from labuse.config import get_settings


A = "97411000BZ1281"
B = "97415000BY0083"


@pytest.fixture
def fiches(monkeypatch):
    data = {"commune": "Saint-Denis", "score_v2": {"copro": True},
            "coproprietes": [{"rattachement": "proche_20m", "nb_lots_total": 65}],
            "le_bien": {"hauteur_bati_m": 8.9, "hauteur_nature": "estimé", "hauteur_source": "BD TOPO"}}
    monkeypatch.setattr(resume_fiche, "_fiche", lambda *_: data)
    def valeurs(db, idu, fiche, ids):
        brutes = {"surface_parcelle_m2": 599 if idu == A else 2458, "emprise_batie_m2": 900,
                  "capacite_logements": {"texte": "voir l’Étude de faisabilité"},
                  "zone_plu_famille": "U", "reglement_plu_bloc": {"zone": "Uh"}}
        return {k: SimpleNamespace(valeur=brutes[k]) for k in ids if k in brutes}
    monkeypatch.setattr(resume_fiche, "_valeurs", valeurs)
    return data


@pytest.mark.parametrize(("question", "champ", "attendu"), [
    ("Est-elle en copropriété ?", "copro", "non confirmé"),
    ("Quelle est la surface bâtie ?", "emprise_batie_m2", "900"),
    ("Quelle est la pente du toit ?", "pente_toit_deg", "non renseigné"),
    ("Quelle est la hauteur du bâti ?", "hauteur_bati_m", "estimée"),
    ("Quelle est la capacité en logements ?", "capacite_logements", "faisabilité"),
])
def test_mesures(fiches, question, champ, attendu):
    r = answer(None, f"{question} {A}")
    assert r["champ_id"] == champ and attendu in r["text"]


@pytest.mark.parametrize("ids", [(A, B), (B, A)])
def test_cumul(fiches, ids):
    r = answer(None, "Quelle est la surface totale des parcelles " + " et ".join(ids) + " ?")
    assert "3057" in "".join(r["text"].split()) and all(i in r["text"] for i in ids)


def test_deux_volets(fiches):
    r = answer(None, f"Quelle est la surface et quelle est la zone PLU de la parcelle {A} ?")
    assert "599" in r["text"] and "Zone Uh" in r["text"]


def test_deuxieme_suggestion(fiches):
    r = answer(None, "Je parlais de la deuxième suggestion. Quelle est sa surface ?",
               prior_params={"candidats": [A, B]})
    assert r["voie"]["idu"] == B and "2458" in "".join(r["text"].split())


@pytest.mark.db
def test_reprise_periode_et_relecture(db_session):
    db = db_session
    scope = dict(sujet="qa-audit2", compte_id=None)
    req = uuid4()
    first = dict(message="Ancien tour", reponse={"text": "Réponse", "intent": "QUESTION"})
    cid = historique.enregistrer(db, conversation_id=None, **first, **scope, request_id=req)
    assert historique.reponse_enregistree(db, req, None, scope["sujet"])["conversation_id"] == cid
    registre_faits.enregistrer(db, cid, [{"cle": "surface", "valeur": 321}])
    for table, col, key in [("copilote_conversations", "updated_at", "id"),
                            ("copilote_messages", "ts", "conversation_id"), ("copilote_faits", "ts", "conversation_id")]:
        db.execute(text(f"UPDATE {table} SET {col}=now()-interval '1 day' WHERE {key}=:i"), {"i": cid})
    historique.enregistrer(db, conversation_id=cid, message="Reprise", reponse={"text": "OK"}, **scope)
    ttl = get_settings().copilote_v2_contexte_ttl_minutes
    # Même une transaction où les deux écritures partagent now() doit exclure les anciennes dates.
    assert len(historique.fil(db, None, cid, ttl, sujet=scope["sujet"])[0]) == 2
    assert not registre_faits.du_fil(db, None, cid, ttl, sujet=scope["sujet"])
    assert len(historique.charger(db, None, cid, sujet=scope["sujet"])["messages"]) == 4


@pytest.mark.db
def test_pagination_dates_identiques(db_session):
    sujet = "qa-pages-" + uuid4().hex[:10]
    db_session.execute(text("INSERT INTO copilote_conversations(sujet,titre) "
                            "SELECT :s,'test' FROM generate_series(1,41)"), {"s": sujet})
    page = historique.lister(db_session, None, sujet=sujet)
    suite = historique.lister(db_session, None, sujet=sujet, avant=page[-1]["updated_at"], avant_id=page[-1]["id"])
    assert len(page) == 40 and len(suite) == 1 and suite[0]["id"] < page[-1]["id"]
