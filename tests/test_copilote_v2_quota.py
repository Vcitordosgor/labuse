"""CONNEXIONS-2 Lot 2 (KO-3) — plafond PAR COMPTE unifié sur /api/copilote-v2/ask.

Avant : /ask plafonnait sur `copilote_v2_missions_jour` (config GLOBALE), donc l'override édité au
dashboard (`copilote_quota_jour`) était IGNORÉ par le Copilote réellement servi. Désormais /ask lit
`quota_du_compte` — la MÊME fonction et le MÊME compteur (`QUOTA_COPILOTE_KIND`) que la recherche NL
`/ia`. Un seul compteur, un seul plafond, une seule source. Sans DB ni appel Anthropic : on éprouve
la garde. Ce test échoue sur l'ancien code (qui bornait sur le plafond global).
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
    # copilote_v2_missions_jour reste dans la config (obsolète) mais /ask ne le lit PLUS.
    return types.SimpleNamespace(dev_mode=dev_mode, copilote_v2_missions_jour=999,
                                 nl_quota_jour=nl_quota, copilote_v2_contexte_ttl_minutes=ttl)


def test_ask_lit_le_quota_du_compte_edite(monkeypatch):
    """L'override dashboard (quota_du_compte) est ce que /ask applique — 429 au plafond ÉDITÉ (12),
    jamais le plafond global. Prouve KO-3 corrigé : éditer le quota au dashboard agit sur /ask."""
    appels = {"answer": 0}
    monkeypatch.setattr(dash, "quota_du_compte", lambda cid: 12)          # override licence édité
    monkeypatch.setattr(cv2, "compteur_incr_et_lire", lambda *a, **k: 13)  # 13 > 12
    monkeypatch.setattr(cv2.config, "get_settings", lambda: _settings(dev_mode=False))
    monkeypatch.setattr(cv2, "answer", lambda *a, **k: appels.__setitem__("answer", appels["answer"] + 1))
    out = cv2.ask(cv2.AskIn(message="combien de parcelles ?"), _req(7), db=None)
    assert isinstance(out, JSONResponse) and out.status_code == 429
    body = json.loads(bytes(out.body))
    assert body["quota"] == 12 and body["gel_jusqua"] == "minuit"        # le plafond ÉDITÉ, pas 40/999
    assert appels["answer"] == 0                    # la garde court-circuite : zéro appel modèle


def test_ask_compte_et_kind_unifie(monkeypatch):
    """Scope `c:<id>` et kind UNIQUE `QUOTA_COPILOTE_KIND` (le MÊME que /ia) — un seul compteur."""
    vus = {}
    def _fake(jour, sujet, kind, n=1):
        vus.update(jour=jour, sujet=sujet, kind=kind)
        return 1
    monkeypatch.setattr(dash, "quota_du_compte", lambda cid: 80)
    monkeypatch.setattr(cv2, "compteur_incr_et_lire", _fake)
    monkeypatch.setattr(cv2.config, "get_settings", lambda: _settings(dev_mode=False))
    monkeypatch.setattr(cv2, "answer", lambda *a, **k: {"text": ""})
    monkeypatch.setattr(cv2.historique, "enregistrer", lambda *a, **k: 1)
    cv2.ask(cv2.AskIn(message="x"), _req(7), db=None)
    assert vus["sujet"] == "c:7"                          # compte connecté → bucket compte
    assert vus["kind"] == dash.QUOTA_COPILOTE_KIND        # compteur UNIQUE partagé avec /ia


def test_ask_pilote_repli_nl_quota(monkeypatch):
    """Sans compte (pilote/anonyme) : quota_du_compte→None, repli sur nl_quota_jour (comme /ia)."""
    monkeypatch.setattr(dash, "quota_du_compte", lambda cid: None)
    monkeypatch.setattr(cv2, "compteur_incr_et_lire", lambda *a, **k: 31)   # 31 > 30
    monkeypatch.setattr(cv2.config, "get_settings", lambda: _settings(dev_mode=False, nl_quota=30))
    monkeypatch.setattr(cv2, "_sujet_quota", lambda req: "s:anon")
    out = cv2.ask(cv2.AskIn(message="x"), _req(None), db=None)
    assert isinstance(out, JSONResponse) and out.status_code == 429
    assert json.loads(bytes(out.body))["quota"] == 30


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
