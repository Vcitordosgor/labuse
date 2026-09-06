"""RETOURS-21 Lot B — les permis orphelins : le reliquat non localisable n'est jamais MUET.

Sur les 2 894 permis sans localisation, la BD PARCELLAIRE vecteur d'époque (édition 974 de 2008)
en récupère la majorité par la géométrie de la parcelle d'origine (même méthode que RETOURS-14).
Ce qui reste — parcelle absente de tout cadastre disponible, ou référence erronée — DOIT le dire
dans la liste : `marquer_reliquat_sans_localisation` pose une mention honnête, jamais un point.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.ingestion.cadastre_historique import marquer_reliquat_sans_localisation

pytestmark = pytest.mark.db


def test_reliquat_muet_recoit_une_mention(db_session):
    db_session.execute(text("DELETE FROM sitadel_permits WHERE permit_id LIKE '__R21_%'"))
    # un orphelin muet (geom NULL, geoloc NULL) + un permis localisé (geom présent)
    db_session.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, idu_codes, commune, geom, raw) VALUES "
        "('__R21_MUET__', 'PC', '[\"97401000AS9999\"]'::jsonb, 'Les Avirons', NULL, "
        " '{\"src\":\"test\"}'::jsonb), "
        "('__R21_LOC__', 'PC', '[\"97401000AS0001\"]'::jsonb, 'Les Avirons', "
        " ST_SetSRID(ST_MakePoint(55.5,-21.0),4326), '{\"src\":\"test\",\"geoloc\":\"parcelle d''origine\"}'::jsonb)"))
    n = marquer_reliquat_sans_localisation(db_session, log_fn=lambda *_: None)
    assert n >= 1
    muet = db_session.execute(text(
        "SELECT raw->>'geoloc' FROM sitadel_permits WHERE permit_id='__R21_MUET__'")).scalar()
    assert muet is not None and muet.startswith("sans localisation")
    loc = db_session.execute(text(
        "SELECT raw->>'geoloc' FROM sitadel_permits WHERE permit_id='__R21_LOC__'")).scalar()
    assert loc == "parcelle d'origine"   # un permis localisé n'est pas re-marqué
    db_session.execute(text("DELETE FROM sitadel_permits WHERE permit_id LIKE '__R21_%'"))
