"""RETOURS-8 (R3) — plafond PAR COMPTE en EUROS, garde UNIQUE `etat_plafond_ia` sur /api/copilote-v2/ask.

Le plafond du Copilote est désormais exprimé en euros/jour (comptes.copilote_budget_eur, défaut config
2,00 €) : /ask, /ia (recherche NL) et les missions lourdes appliquent tous la MÊME garde
`dashboard.etat_plafond_ia` — un seul compteur, un seul plafond, une seule source. Une mission Sonnet
pèse à son COÛT RÉEL sur le budget du jour. Sans DB ni appel Anthropic : on éprouve la garde.
"""
from __future__ import annotations

import json
import types

from fastapi.responses import JSONResponse

from labuse.api import copilote_v2 as cv2
from labuse.api import dashboard as dash


def _req(compte_id):
    return types.SimpleNamespace(state=types.SimpleNamespace(compte_id=compte_id))


def _settings(dev_mode, nl_quota=30, ttl=10):
    return types.SimpleNamespace(dev_mode=dev_mode,
                                 nl_quota_jour=nl_quota, copilote_v2_contexte_ttl_minutes=ttl)


def test_ask_refuse_au_plafond_euros(monkeypatch):
    """Quand la garde unique signale un dépassement (dépense du jour ≥ budget €), /ask rend un 429
    portant le budget/dépense — et ne fait AUCUN appel modèle."""
    appels = {"answer": 0}
    detail = {"detail": "Plafond IA du jour atteint (2,00 €/jour). Reprend à minuit.",
              "budget_eur": 2.0, "depense_eur": 2.01, "gel_jusqua": "minuit"}
    monkeypatch.setattr(dash, "etat_plafond_ia", lambda *a, **k: detail)
    monkeypatch.setattr(cv2.config, "get_settings", lambda: _settings(dev_mode=False))
    monkeypatch.setattr(cv2, "answer", lambda *a, **k: appels.__setitem__("answer", appels["answer"] + 1))
    out = cv2.ask(cv2.AskIn(message="combien de parcelles ?"), _req(7), db=None)
    assert isinstance(out, JSONResponse) and out.status_code == 429
    body = json.loads(bytes(out.body))
    assert body["budget_eur"] == 2.0 and body["gel_jusqua"] == "minuit"
    assert appels["answer"] == 0                    # la garde court-circuite : zéro appel modèle


def test_ask_gate_recoit_compte_et_sujet(monkeypatch):
    """La garde reçoit le compte connecté et le sujet `c:<id>` (bucket compte, compteur unique)."""
    vus = {}
    def _gate(compte_id, sujet, jour, *, nl_defaut):
        vus.update(compte_id=compte_id, sujet=sujet, nl_defaut=nl_defaut)
        return None
    monkeypatch.setattr(dash, "etat_plafond_ia", _gate)
    monkeypatch.setattr(cv2.config, "get_settings", lambda: _settings(dev_mode=False))
    monkeypatch.setattr(cv2, "answer", lambda *a, **k: {"text": ""})
    monkeypatch.setattr(cv2.historique, "enregistrer", lambda *a, **k: 1)
    cv2.ask(cv2.AskIn(message="x"), _req(7), db=None)
    assert vus["compte_id"] == 7 and vus["sujet"] == "c:7"
    assert vus["nl_defaut"] == 30                         # repli appels pour un sujet sans compte


def test_ask_pilote_repli_nl(monkeypatch):
    """Sans compte (pilote/anonyme) : la garde applique le plafond historique en APPELS (nl_quota_jour)."""
    detail = {"detail": "Quota d'analyses IA atteint (30/jour). Reprend à minuit.",
              "quota": 30, "gel_jusqua": "minuit"}
    monkeypatch.setattr(dash, "etat_plafond_ia", lambda *a, **k: detail)
    monkeypatch.setattr(cv2.config, "get_settings", lambda: _settings(dev_mode=False, nl_quota=30))
    monkeypatch.setattr(cv2, "_sujet_quota", lambda req: "s:anon")
    out = cv2.ask(cv2.AskIn(message="x"), _req(None), db=None)
    assert isinstance(out, JSONResponse) and out.status_code == 429
    assert json.loads(bytes(out.body))["quota"] == 30


def test_ask_dev_mode_ne_compte_pas(monkeypatch):
    """LABUSE_DEV_MODE=1 → la garde n'est même pas appelée."""
    touche = {"n": 0}
    monkeypatch.setattr(dash, "etat_plafond_ia",
                        lambda *a, **k: touche.__setitem__("n", touche["n"] + 1) or {"detail": "x"})
    monkeypatch.setattr(cv2.config, "get_settings", lambda: _settings(dev_mode=True))
    monkeypatch.setattr(cv2, "answer", lambda *a, **k: {"text": "ok", "intent": None})
    monkeypatch.setattr(cv2.historique, "enregistrer", lambda *a, **k: 1)
    out = cv2.ask(cv2.AskIn(message="x"), _req(7), db=None)
    assert not isinstance(out, JSONResponse)         # pas de 429 : la garde est désactivée
    assert touche["n"] == 0                           # et la garde n'a même pas été appelée
