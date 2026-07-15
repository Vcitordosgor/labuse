"""M11 · SURFACE A — tests de l'endpoint /parcels/{idu}/ask (barre de fiche).

L'appel modèle (core.complete) est MOCKÉ → tests déterministes, sans API Anthropic. On vérifie le
comportement de l'endpoint : anti-hallucination (amiante → Absent), liste blanche, quota, cache.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ai import core

IDU = "97423000AB1908"   # parcelle réelle servie (fiche premium disponible)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean(client):
    from labuse.db import session_scope
    with session_scope() as s:
        s.execute(text("CREATE TABLE IF NOT EXISTS ia_cache (idu varchar(14), run_label varchar(64),"
                       " question_hash varchar(64), kind varchar(24), question text, response jsonb,"
                       " computed_at timestamptz DEFAULT now(), PRIMARY KEY (idu, run_label, question_hash))"))
        s.execute(text("CREATE TABLE IF NOT EXISTS ia_ask_quota (sujet varchar(64), idu varchar(14),"
                       " jour date DEFAULT current_date, n integer DEFAULT 0, PRIMARY KEY (sujet, idu, jour))"))
        s.execute(text("DELETE FROM ia_cache WHERE kind='fiche_ask' AND idu=:i"), {"i": IDU})
        s.execute(text("DELETE FROM ia_ask_quota WHERE idu=:i"), {"i": IDU})
    yield


# catalogue synthétique (la base de test `labuse_test` n'a pas la fiche q_v6_m8 → on mocke _ask_context)
_CATALOGUE = {
    "zone_plu": core.Fact("1AUb", "SOURCE"),
    "surface_m2": core.Fact(313, "SOURCE"),
    "sdp_residuelle_m2": core.Fact(183, "ESTIME"),
    "viabilisation_assainissement": core.Fact(None, "ABSENT"),
}


def _mock_complete(monkeypatch, *, rejected=False, text_="Zone 1AUb ⟨src:zone_plu⟩.", sources=None):
    """Mocke core.complete (enregistre appels + contexte) ET _ask_context (catalogue synthétique)."""
    calls = []

    def fake(db, *, kind, system, context, model=core.MODEL_FACTUAL, **kw):
        calls.append({"kind": kind, "model": model, "context": context})
        if rejected:
            return core.IAResult(text="Je ne peux pas répondre de façon sourcée sur ce point.",
                                 model=model, rejected=True, reason="aucune source")
        return core.IAResult(text=text_, model=model, sources=sources or ["zone_plu"])
    monkeypatch.setattr("labuse.api.fiche_ask.core.complete", fake)
    monkeypatch.setattr("labuse.api.fiche_ask._ask_context",
                        lambda db, idu: (dict(_CATALOGUE), {"reglement_plu": "https://plu#p12"}))
    return calls


# ───────────────────── anti-hallucination (LE test qui compte) ─────────────────────
def test_amiante_hors_donnees_renvoie_absent(client, monkeypatch):
    # le modèle ne peut pas sourcer « amiante » → le socle rejette → l'endpoint dit « non disponible »
    _mock_complete(monkeypatch, rejected=True)
    r = client.post(f"/parcels/{IDU}/ask", json={"question": "Y a-t-il de l'amiante ?"})
    assert r.status_code == 200
    d = r.json()
    assert d["absent"] is True and d["rejected"] is True
    assert "n'est pas disponible" in d["texte"].lower()
    # JAMAIS l'affirmation douteuse
    assert "amiante" not in d["texte"].lower() or "disponible" in d["texte"].lower()


# ───────────────────── liste blanche : aucun champ hors catalogue envoyé ─────────────────────
def test_liste_blanche_contexte_dans_catalogue(client, monkeypatch):
    calls = _mock_complete(monkeypatch)
    catalogue = set(_CATALOGUE)
    client.post(f"/parcels/{IDU}/ask", json={"question": "Ça veut dire quoi la zone ?"})
    ctx = calls[0]["context"]["parcelle"]   # le contexte réellement passé au modèle
    assert set(ctx).issubset(catalogue), "un champ hors catalogue a fuité vers le modèle"
    # chaque champ porte une provenance étiquetée
    assert all(set(v) == {"valeur", "provenance"} for v in ctx.values())


# ───────────────────── routage modèle : haiku par défaut, sonnet sur faisabilité ─────────────────────
def test_routage_haiku_defaut_sonnet_faisabilite(client, monkeypatch):
    calls = _mock_complete(monkeypatch)
    client.post(f"/parcels/{IDU}/ask", json={"question": "Risque inondation ?"})
    client.post(f"/parcels/{IDU}/ask", json={"question": "Combien je peux construire ?"})
    assert calls[0]["model"] == core.MODEL_FACTUAL      # factuel → haiku
    assert calls[1]["model"] == core.MODEL_REASONING    # faisabilité → sonnet


# ───────────────────── quota 20/fiche/jour + le hit cache ne décompte pas ─────────────────────
def test_quota_21e_refusee_sans_appel(client, monkeypatch):
    from labuse.db import session_scope
    calls = _mock_complete(monkeypatch)
    with session_scope() as s:
        # place le sujet de test à 20 (le sujet dev = IP locale du TestClient)
        # on force le compteur pour TOUS les sujets possibles de ce test
        s.execute(text("INSERT INTO ia_ask_quota (sujet, idu, jour, n) "
                       "SELECT DISTINCT 'testclient', :i, current_date, 20"), {"i": IDU})
    # impossible de connaître le sujet exact → on teste la logique via une insertion ciblée :
    # on récupère le sujet réel en faisant 1 appel, puis on sature, puis on vérifie le refus.
    client.post(f"/parcels/{IDU}/ask", json={"question": "q0"})   # crée la ligne du vrai sujet
    with session_scope() as s:
        s.execute(text("UPDATE ia_ask_quota SET n=20 WHERE idu=:i"), {"i": IDU})
    n_avant = len(calls)
    r = client.post(f"/parcels/{IDU}/ask", json={"question": "question au-delà du quota"})
    assert r.json().get("quota_atteint") is True
    assert len(calls) == n_avant, "la question au-delà du quota ne doit PAS appeler le modèle"


def test_hit_cache_ne_decompte_pas_le_quota(client, monkeypatch):
    from labuse.db import session_scope
    calls = _mock_complete(monkeypatch)
    q = {"question": "Ça veut dire quoi 1AUb ?"}
    client.post(f"/parcels/{IDU}/ask", json=q)          # 1er appel → modèle + décompte
    with session_scope() as s:
        n1 = s.execute(text("SELECT n FROM ia_ask_quota WHERE idu=:i"), {"i": IDU}).scalar()
    client.post(f"/parcels/{IDU}/ask", json=q)          # même question → cache, pas de décompte
    with session_scope() as s:
        n2 = s.execute(text("SELECT n FROM ia_ask_quota WHERE idu=:i"), {"i": IDU}).scalar()
    assert n1 == n2, "un hit cache ne doit pas décompter le quota"
    assert len(calls) == 1, "la question répétée ne doit pas rappeler le modèle"


# ───────────────────── cache : question répétée = 0 appel modèle ─────────────────────
def test_cache_question_repetee_zero_appel(client, monkeypatch):
    calls = _mock_complete(monkeypatch)
    q = {"question": "Quelle est la surface ?"}
    r1 = client.post(f"/parcels/{IDU}/ask", json=q)
    r2 = client.post(f"/parcels/{IDU}/ask", json={"question": "  quelle est la SURFACE  "})  # normalisée
    assert r1.json()["cached"] is False and r2.json()["cached"] is True
    assert len(calls) == 1
