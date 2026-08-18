"""M54-AB Famille 4 (C9) — le périmètre annoncé du PDF projet est RESPECTÉ.

Régression du décalage d'arguments de `_q_v2_where` (un « statuts » mort décalait tout d'un
cran → la valeur `communes` tombait dans `flags_exclus`, le filtre périmètre n'était jamais
appliqué : « Périmètre : Saint-Paul » mais top 5 sur toute l'île, « 19 300 correspondent »).

Interroge la base applicative (lecture seule), se skippe si absente (CI / base vide)."""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.api.projets import projet_apercu, ApercuIn

COMMUNE = "Saint-Paul"
APP_URL = os.environ.get("LABUSE_AUDIT_DATABASE_URL") \
    or os.environ.get("LABUSE_DATABASE_URL") \
    or "postgresql+psycopg://labuse:labuse@localhost:5432/labuse"


@pytest.fixture(scope="module")
def engine():
    try:
        eng = create_engine(APP_URL)
        with eng.connect() as c:
            n = c.execute(text("SELECT count(*) FROM parcels WHERE commune ILIKE :c"),
                          {"c": COMMUNE}).scalar()
    except Exception as exc:  # noqa: BLE001 - base indisponible → skip
        pytest.skip(f"base applicative indisponible ({type(exc).__name__})")
    if not n or n < 100:
        pytest.skip(f"données {COMMUNE} absentes ({n})")
    yield eng
    eng.dispose()


def test_top5_dans_le_perimetre_commune(engine):
    """M120 — le périmètre est une FACETTE du cadrage (`communes`) : top 5 ET compteur n
    restent dans cette commune."""
    with Session(engine) as db:
        commune = projet_apercu(ApercuIn(cadrage={"communes": [COMMUNE]}, limit=5), db)
        ile = projet_apercu(ApercuIn(cadrage={}, limit=5), db)   # aucune commune = toute l'île
    # top 5 ⊆ périmètre
    assert commune["top"], "aucune parcelle servie dans le périmètre"
    assert all(it["commune"] == COMMUNE for it in commune["top"]), \
        f"top hors commune : {[it['commune'] for it in commune['top']]}"
    # « N correspondent » compte le périmètre appliqué, pas l'île entière
    assert 0 < commune["n"] < ile["n"], f"n commune={commune['n']} vs île={ile['n']}"


def test_secteur_reste_dans_ses_communes(engine):
    """M120 — un « secteur » = ses communes, posées comme facette `communes` du cadrage : le top 5
    reste dans ces communes (jamais hors)."""
    from labuse.api.ia import SECTEURS
    communes_ouest = list(SECTEURS["Ouest"])
    with Session(engine) as db:
        ap = projet_apercu(ApercuIn(cadrage={"communes": communes_ouest}, limit=5), db)
    assert all(it["commune"] in set(communes_ouest) for it in ap["top"]), \
        f"top hors secteur : {[it['commune'] for it in ap['top']]}"
