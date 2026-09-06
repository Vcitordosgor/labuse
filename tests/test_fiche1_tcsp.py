"""FICHE-1 lot 4 — stationnement allégé (TCSP, L151-36) déclaré et servi sur la fiche.

Le bloc était servi/affiché (Réseaux) mais HORS registre : la donnée est désormais déclarée
(fiche_parcelle_reseaux). Même moteur que la couche TCSP : rayon 800 m STRICT depuis la station,
à vol d'oiseau.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.registre import ROBINETS
from labuse.registre.donnees import DONNEES


def test_registre_tcsp_declare():
    d = DONNEES["tcsp_stationnement_allege"]
    assert d.en_attente is None and d.type == "classe"
    assert d.domaine == ("sous_800m", "au_dela", "aucune_station")
    assert "tcsp_stationnement_allege" in ROBINETS["fiche_parcelle_reseaux"].chiffres


@pytest.mark.db
def test_tcsp_sous_800m_strict_et_nomme(db_session):
    """Une parcelle à ≤ 700 m d'une station est « sous_800m » avec station + distance + plafond."""
    from labuse.api.app import _proximites_block
    idu = db_session.execute(text(
        "SELECT p.idu FROM parcels p, spatial_layers st WHERE st.kind='tcsp_station' "
        "AND ST_DWithin(p.geom::geography, st.geom::geography, 700) LIMIT 1")).scalar()
    if not idu:
        pytest.skip("base de test sans parcelle proche d'une station TCSP")
    tcsp = (_proximites_block(db_session, idu) or {}).get("tcsp")
    assert tcsp and tcsp["sous_800m"] is True
    assert tcsp["station"] and tcsp["distance_m"] < 800
    assert "L151" in tcsp["libelle"] and "place de stationnement par logement" in tcsp["libelle"]
