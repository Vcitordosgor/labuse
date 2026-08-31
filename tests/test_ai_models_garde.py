"""SECTEUR-1 (S6) — GARDE des noms de modèles. Le 30/08/2026, la prod appelait encore
`claude-3-5-haiku-20241022` (retiré de l'API le 19/02/2026) → `not_found_error` échouant depuis
février EN SILENCE. Ces tests échouent si un modèle RETIRÉ réapparaît (dans le code OU dans l'env),
et vérifient que les noms actifs sont, eux, servis.
"""
from __future__ import annotations

import pytest

from labuse.ai_models import (
    ACTIVE_MODELS, DEFAULT_AGENT_MODEL, MODEL_FACTUAL, MODEL_REASONING, MODEL_VISION,
    RETIRED_MODELS, check_model,
)


def test_le_haiku_de_la_prod_est_bien_marque_retire():
    """Le fautif nommé par Anthropic (mail 30/08) DOIT être dans la liste des retirés."""
    assert "claude-3-5-haiku-20241022" in RETIRED_MODELS


def test_aucun_modele_actif_n_est_retire():
    """Aucune constante servie ne doit être un modèle retiré — le verrou du mandat."""
    for m in (MODEL_FACTUAL, MODEL_REASONING, MODEL_VISION, DEFAULT_AGENT_MODEL):
        assert m not in RETIRED_MODELS, f"modèle RETIRÉ servi : {m}"
    assert ACTIVE_MODELS.isdisjoint(RETIRED_MODELS)


def test_les_modeles_servis_sont_haiku45_ou_sonnet46():
    """Les noms actifs sont ceux de la migration (Haiku 4.5 / Sonnet 4.6), plus aucun 3.5."""
    assert MODEL_FACTUAL == "claude-haiku-4-5-20251001"
    assert MODEL_VISION == "claude-haiku-4-5-20251001"
    assert MODEL_REASONING == "claude-sonnet-4-6"
    assert all("claude-3-5" not in m and "claude-3-" not in m for m in ACTIVE_MODELS)


def test_check_model_leve_bruyamment_sur_un_retire():
    with pytest.raises(ValueError, match="RETIRÉ"):
        check_model("claude-3-5-haiku-20241022")
    assert check_model(MODEL_FACTUAL) == MODEL_FACTUAL   # un modèle servi passe


def test_un_echec_d_appel_modele_est_journalise(monkeypatch, caplog):
    """CAUSE PROFONDE — un échec d'appel (ex. not_found d'un modèle mort) DOIT être journalisé
    explicitement, plus jamais avalé dans un mode dégradé invisible."""
    import logging

    from labuse.ai import core

    monkeypatch.setattr(core, "has_key", lambda: True)

    class _FakeClient:
        def __init__(self, *a, **k): self.messages = self
        def create(self, **k):
            raise RuntimeError("not_found_error: model claude-3-5-haiku-20241022 not found")
    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", _FakeClient)

    with caplog.at_level(logging.ERROR, logger="labuse.ai"):
        res = core.complete(None, kind="test", system="s", context="ctx", model=MODEL_FACTUAL)
    assert res.degraded is True
    assert any("appel modèle" in r.message and "échoué" in r.message for r in caplog.records), \
        "l'échec d'appel modèle doit être journalisé (jamais silencieux)"
    # le bandeau nomme la piste « modèle inconnu ou retiré », pas un générique
    assert core.last_error() and "retiré" in core.last_error()


def test_aucun_nom_de_modele_retire_ne_reapparait_dans_le_code():
    """Le verrou demandé par le mandat : si un nom RETIRÉ réapparaît en dur dans le code source
    (hors la liste de garde elle-même), ce test échoue et nomme le fichier fautif. C'est ce qui aurait
    attrapé le `claude-3-5-haiku-20241022` de la prod avant qu'il n'échoue en silence."""
    import pathlib

    racine = pathlib.Path(__file__).resolve().parent.parent / "src" / "labuse"
    garde = racine / "ai_models.py"   # seule à avoir le DROIT de citer les retirés (dans RETIRED_MODELS)
    fautifs = []
    for py in racine.rglob("*.py"):
        if py == garde:
            continue
        txt = py.read_text(encoding="utf-8")
        for mort in RETIRED_MODELS:
            # un nom retiré cité en commentaire (ex. « ex-3-5-haiku ») n'est pas un appel : on ne
            # flague que le littéral chaîne complet.
            if f'"{mort}"' in txt or f"'{mort}'" in txt:
                fautifs.append(f"{py.relative_to(racine)} → {mort}")
    assert not fautifs, "nom(s) de modèle RETIRÉ en dur dans le code : " + "; ".join(fautifs)


def test_aucun_modele_en_dur_hors_source_unique():
    """Aucun littéral `claude-…` ne doit vivre hors `ai_models.py` : un nom de modèle est une
    constante de configuration, jamais dispersé (c'est ce qui a laissé traîner le juge VLM en dur)."""
    import pathlib
    import re

    racine = pathlib.Path(__file__).resolve().parent.parent / "src" / "labuse"
    garde = racine / "ai_models.py"
    motif = re.compile(r"""["']claude-[a-z0-9.\-]+["']""")
    fautifs = []
    for py in racine.rglob("*.py"):
        if py == garde:
            continue
        for m in motif.findall(py.read_text(encoding="utf-8")):
            fautifs.append(f"{py.relative_to(racine)} → {m}")
    assert not fautifs, "modèle en dur hors ai_models.py : " + "; ".join(fautifs)


def test_config_refuse_un_ai_model_retire_au_demarrage(monkeypatch):
    """fail-closed : LABUSE_AI_MODEL sur un modèle retiré fait échouer le boot (pas d'appel silencieux)."""
    from labuse.config import Settings
    monkeypatch.setenv("LABUSE_AI_MODEL", "claude-3-5-haiku-20241022")
    with pytest.raises(Exception, match="RETIRÉ"):
        Settings()
    # un modèle servi passe
    monkeypatch.setenv("LABUSE_AI_MODEL", MODEL_FACTUAL)
    assert Settings().ai_model == MODEL_FACTUAL
