"""ETUDE-ASYNC-1 — le calcul d'étude tourne dans un PROCESSUS SÉPARÉ tuable, jamais dans un thread
in-process qui survivrait à la borne et affamerait la boucle de l'API.

Ces tests ne touchent PAS la base : ils exercent la MÉCANIQUE de `labuse.api.modules._dans_processus`
(processus « spawn », borne, mise à mort, remontée d'erreur) avec de faux workers. Ils tournent donc
dans le filet pre-push (famille « sans base »). La preuve « mêmes chiffres » sur l'assiette réelle est au
banc réel (test marqué `reel` plus bas) et à la recette ETUDE-ASYNC-1.
"""
from __future__ import annotations

import multiprocessing
import time

import pytest
from fastapi import HTTPException

from labuse.api import modules


# — faux workers de niveau module (picklables par « spawn ») —
def _fake_lent(secondes: float) -> str:
    time.sleep(secondes)
    return "jamais renvoyé si tué"


def _fake_ok(x: int) -> int:
    return x * x


def _fake_valueerror() -> None:
    raise ValueError("entrée refusée (ex. parcelles non contiguës)")


def _fake_runtime() -> None:
    raise RuntimeError("échec de rendu technique")


def _sans_fantome() -> None:
    """Aucun processus « etude » ne doit rester vivant."""
    time.sleep(0.2)  # laisse l'OS/mp reaper les enfants terminés
    restants = [p for p in multiprocessing.active_children() if p.name == "etude"]
    assert restants == [], f"processus fantôme après la borne : {restants}"


def test_borne_tue_le_processus_et_ne_laisse_pas_de_fantome(monkeypatch):
    # borne très basse → le worker lent (10 s) la dépasse à coup sûr
    monkeypatch.setattr(modules, "_etude_timeout_s", lambda: 0.3)
    t0 = time.time()
    with pytest.raises(HTTPException) as exc:
        modules._dans_processus(_fake_lent, (10.0,))
    assert exc.value.status_code == 503
    assert exc.value.detail["erreur"] == "etude_trop_lourde"
    # la borne doit couper PRÈS de 0,3 s (pas attendre les 10 s du worker)
    assert time.time() - t0 < 4.0
    _sans_fantome()


def test_resultat_traverse_le_processus(monkeypatch):
    monkeypatch.setattr(modules, "_etude_timeout_s", lambda: 30.0)
    assert modules._dans_processus(_fake_ok, (7,)) == 49
    _sans_fantome()


def test_valueerror_remonte_pour_un_400(monkeypatch):
    # une entrée refusée doit revenir en ValueError (la route la mappe en 400), pas en 503.
    monkeypatch.setattr(modules, "_etude_timeout_s", lambda: 30.0)
    with pytest.raises(ValueError):
        modules._dans_processus(_fake_valueerror, ())
    _sans_fantome()


def test_autre_erreur_remonte_pour_un_500(monkeypatch):
    monkeypatch.setattr(modules, "_etude_timeout_s", lambda: 30.0)
    with pytest.raises(RuntimeError):
        modules._dans_processus(_fake_runtime, ())
    _sans_fantome()


@pytest.mark.reel
def test_memes_chiffres_subprocess_vs_direct():
    """Banc réel : le payload servi par le processus séparé est IDENTIQUE au calcul direct (mêmes chiffres
    qu'avant sur l'assiette lourde de recette). JAMAIS en pre-push (base vide) — rejoué au banc réel.

    Le conftest redirige `session_scope` vers `labuse_test` (base de test, vide) ; comme les autres tests
    `reel` étude-v6, on pointe ici la base APPLICATIVE réelle (`LABUSE_APP_DATABASE_URL`) le temps du test
    — le processus enfant « spawn » hérite de cet environnement et calcule donc sur la même base."""
    import json
    import os

    from sqlalchemy import text

    from labuse import config, db

    app_url = os.environ.get("LABUSE_APP_DATABASE_URL")
    if not app_url:
        pytest.skip("LABUSE_APP_DATABASE_URL absent")

    idus = ["97404000AW0099", "97404000AW0451", "97404000AW0624", "97404000AW0625"]
    ancien = os.environ.get("LABUSE_DATABASE_URL")
    os.environ["LABUSE_DATABASE_URL"] = app_url
    config.get_settings.cache_clear()
    db._engine = None
    db._Session = None
    try:
        with db.session_scope() as s:
            n = s.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"), {"i": idus}).scalar()
        if n != 4:
            pytest.skip("parcelles témoins absentes de la base applicative")
        data = {"idus": idus, "type_projet": "collectif", "objectif": "equilibre"}
        direct = modules._worker_etude(dict(data), list(idus))      # calcul direct, dans CE process
        via_proc = modules._etudier_borne(dict(data))               # via processus séparé « spawn »
        a = json.dumps(direct, sort_keys=True, default=str)
        b = json.dumps(via_proc, sort_keys=True, default=str)
        assert a == b
    finally:
        if ancien is not None:
            os.environ["LABUSE_DATABASE_URL"] = ancien
        config.get_settings.cache_clear()
        db._engine = None
        db._Session = None
