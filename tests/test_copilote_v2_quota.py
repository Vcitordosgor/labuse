"""FIX-COPILOTE F3 — plafond par compte sur /api/copilote-v2/ask.

Le chat n'avait NI quota NI rate-limit (le docstring l'affirmait à tort). On branche le MÊME
mécanisme que le run lourd (`compteur_incr_et_lire` sur `usage_compteurs`), scope `c:<compte_id>`,
kind distinct `copilote_v2_ask`. Dépassement → 429 honnête AVANT tout appel modèle. Sans DB, sans
appel Anthropic : on éprouve la garde, pas la couche métier.
"""
from __future__ import annotations

import json
import types

from fastapi.responses import JSONResponse

from labuse.api import copilote_v2 as cv2


def _req(compte_id):
    return types.SimpleNamespace(state=types.SimpleNamespace(compte_id=compte_id))


def _settings(dev_mode, plafond=40, ttl=10):
    return types.SimpleNamespace(dev_mode=dev_mode, copilote_v2_missions_jour=plafond,
                                 copilote_v2_contexte_ttl_minutes=ttl)


def test_ask_429_quand_plafond_depasse(monkeypatch):
    """Compteur au-dessus du plafond → 429 honnête, RENVOYÉ AVANT answer() (aucun modèle appelé)."""
    appels = {"answer": 0}
    monkeypatch.setattr(cv2, "compteur_incr_et_lire", lambda *a, **k: 41)   # 41 > 40
    monkeypatch.setattr(cv2.config, "get_settings", lambda: _settings(dev_mode=False))
    monkeypatch.setattr(cv2, "answer", lambda *a, **k: appels.__setitem__("answer", appels["answer"] + 1))
    out = cv2.ask(cv2.AskIn(message="combien de parcelles ?"), _req(7), db=None)
    assert isinstance(out, JSONResponse) and out.status_code == 429
    body = json.loads(bytes(out.body))
    assert body["quota"] == 40 and body["gel_jusqua"] == "minuit"
    assert "limite quotidienne" in body["detail"].lower()
    assert appels["answer"] == 0                    # la garde court-circuite : zéro appel modèle


def test_ask_compte_dans_le_bon_bucket(monkeypatch):
    """Même stockage que le run lourd, scope `c:<id>`, kind DISTINCT `copilote_v2_ask` (pas 'agent')."""
    vus = {}
    def _fake(jour, sujet, kind, n=1):
        vus.update(jour=jour, sujet=sujet, kind=kind)
        return 99
    monkeypatch.setattr(cv2, "compteur_incr_et_lire", _fake)
    monkeypatch.setattr(cv2.config, "get_settings", lambda: _settings(dev_mode=False))
    monkeypatch.setattr(cv2, "answer", lambda *a, **k: {"text": ""})
    cv2.ask(cv2.AskIn(message="x"), _req(7), db=None)
    assert vus["sujet"] == "c:7"                     # compte connecté → bucket compte
    assert vus["kind"] == "copilote_v2_ask"          # bucket propre, séparé du run lourd 'agent'


def test_ask_dev_mode_ne_compte_pas(monkeypatch):
    """LABUSE_DEV_MODE=1 → aucun comptage (comme partout) : le compteur n'est jamais touché."""
    touche = {"n": 0}
    monkeypatch.setattr(cv2, "compteur_incr_et_lire",
                        lambda *a, **k: touche.__setitem__("n", touche["n"] + 1) or 999)
    monkeypatch.setattr(cv2.config, "get_settings", lambda: _settings(dev_mode=True))
    monkeypatch.setattr(cv2, "answer", lambda *a, **k: {"text": "ok", "intent": None})
    monkeypatch.setattr(cv2.historique, "enregistrer", lambda *a, **k: 1)
    out = cv2.ask(cv2.AskIn(message="x"), _req(7), db=None)
    assert not isinstance(out, JSONResponse)         # pas de 429 : la garde est désactivée
    assert touche["n"] == 0                           # et le compteur n'a même pas été incrémenté
