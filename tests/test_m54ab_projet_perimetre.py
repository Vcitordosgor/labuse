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
    """Périmètre = une commune → le top 5 ET le compteur n restent dans cette commune."""
    with Session(engine) as db:
        commune = projet_apercu(ApercuIn(
            fiche={"perimetre": {"mode": "communes", "communes": [COMMUNE]}}, limit=5), db)
        ile = projet_apercu(ApercuIn(fiche={"perimetre": {"mode": "ile"}}, limit=5), db)
    # top 5 ⊆ périmètre
    assert commune["top"], "aucune parcelle servie dans le périmètre"
    assert all(it["commune"] == COMMUNE for it in commune["top"]), \
        f"top hors commune : {[it['commune'] for it in commune['top']]}"
    # « N correspondent » compte le périmètre appliqué, pas l'île entière
    assert 0 < commune["n"] < ile["n"], f"n commune={commune['n']} vs île={ile['n']}"


def test_secteur_reste_dans_ses_communes(engine):
    """Périmètre = secteur → le top 5 reste dans les communes du secteur (jamais hors)."""
    from labuse.api.ia import SECTEURS
    with Session(engine) as db:
        ap = projet_apercu(ApercuIn(
            fiche={"perimetre": {"mode": "secteur", "secteur": "Ouest"}}, limit=5), db)
    communes_ouest = set(SECTEURS["Ouest"])
    assert all(it["commune"] in communes_ouest for it in ap["top"]), \
        f"top hors secteur : {[it['commune'] for it in ap['top']]}"
