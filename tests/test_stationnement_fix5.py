"""ETUDE-STATIONNEMENT-FIX-5 — un passage ROULANT continu jusqu'à la voie pour chaque place comptée : les
jonctions allée–accès et accès–voie se mesurent en LARGEUR, pas en contact ponctuel."""
from __future__ import annotations

from shapely.geometry import LineString, Polygon

import labuse.implantation.controles as C


def _scene_base():
    """Une place (nez en haut, y=5) desservie par une allée au-dessus ; une voie en y=16."""
    place = Polygon([(0, 0), (2.5, 0), (2.5, 5), (0, 5)])
    allee = Polygon([(-4, 5), (6.5, 5), (6.5, 10), (-4, 10)])     # dégagement plein (5 m) devant le nez
    voie = LineString([(5, 16), (12, 16)])
    return place, allee, voie


def test_contact_ponctuel_allee_acces_refuse():
    """L'allée et l'accès ne se touchent qu'en UN POINT → aucune voiture ne passe → place NON comptée."""
    place, allee, voie = _scene_base()
    acces_point = Polygon([(6.5, 10), (12, 10), (12, 16), (6.5, 16)])   # touche l'allée au seul point (6.5,10)
    manque = C._pincement_allee([allee], [place], 5.0, [acces_point], voie)
    assert manque > C._DEGAGEMENT_SEUIL_M2, "un contact ponctuel ne dessert pas la place"


def test_jonction_large_desservie():
    """L'accès partage une ARÊTE avec l'allée (largeur) ET touche la voie sur une largeur de passage
    (x ∈ [5 ; 10], soit 5 m ≥ 2,40 m — cf. FIX-6 point 1) → la place est desservie."""
    place, allee, voie = _scene_base()
    acces_large = Polygon([(-4, 10), (10, 10), (10, 16), (-4, 16)])     # arête commune y=10 ; contact voie 5 m
    manque = C._pincement_allee([allee], [place], 5.0, [acces_large], voie)
    assert manque <= C._DEGAGEMENT_SEUIL_M2, "une jonction large dessert la place"


def test_allee_sur_acces_isole_refuse():
    """Deux allées : l'une desservie, l'autre reliée à un accès ISOLÉ de la voie. La place de la seconde
    n'est pas comptée, même si un AUTRE accès touche la voie."""
    place, allee, voie = _scene_base()
    acces_ok = Polygon([(-4, 10), (6.5, 10), (6.5, 16), (-4, 16)])      # touche la voie (largeur)
    place_a = Polygon([(20, 0), (22.5, 0), (22.5, 5), (20, 5)])
    allee_a = Polygon([(16, 5), (26.5, 5), (26.5, 10), (16, 10)])
    acces_isole = Polygon([(26.5, 10), (32, 10), (32, 13), (26.5, 13)])  # ne touche PAS la voie
    manque = C._pincement_allee([allee, allee_a], [place, place_a], 5.0, [acces_ok, acces_isole], voie)
    assert manque > C._DEGAGEMENT_SEUIL_M2, "la place reliée par un accès isolé n'est pas desservie"


# ── point 3 : un seul message quand aucun plan n'est trouvé ─────────────────────────────────────
def test_message_aucun_plan_coherent_avec_le_titre():
    """Quand la recherche ne trouve rien sur une zone constructible, le verdict dit « Aucun plan trouvé sous
    ces hypothèses » ET le message ne commence PLUS par « simulation impossible »."""
    import os
    import pytest
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker
    from labuse.db import make_engine
    from labuse.implantation.service import etudier_payload
    url = os.environ.get("LABUSE_APP_DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL")
    if not url:
        pytest.skip("base applicative absente")
    s = sessionmaker(bind=make_engine(url=url), future=True)()
    try:
        idus = ["97404000AM0759", "97404000AM0874"]
        if s.execute(text("SELECT count(*) FROM parcels WHERE idu = ANY(:i)"), {"i": idus}).scalar() != 2:
            pytest.skip("parcelles absentes")
        p = etudier_payload(s, {"idus": idus, "type_projet": "collectif", "objectif": "equilibre",
                                "stationnement": "aerien", "terrain": "libere"})
        assert p.get("verdict") == "Aucun plan trouvé sous ces hypothèses"
        msg = (p.get("message") or "").lower()
        assert not msg.startswith("simulation impossible"), f"message incohérent avec le titre : {p.get('message')!r}"
    finally:
        s.close()
