"""OUTILS-S2 Lot C — verrou : toute couche carte WMTS (overlay proxy) a sa source DÉCLARÉE.

Les couches VECTEUR passent par `spatial_layers` et sont déjà couvertes par
`check_sources_declarees` (spatial_layers.data_source_id → data_sources). Les overlays WMTS servis
EN DIRECT par un proxy (courbes de niveau, orthos) NE PASSENT PAS par `spatial_layers` : ils
échappaient donc à toute garde. La couche « Courbes de niveau » (RETOURS-13 P5) a ainsi vécu sans
source cataloguée. Ce verrou ferme la brèche : chaque overlay WMTS déclaré doit avoir son entrée
dans le catalogue des sources (`seed_sources.SOURCES`), qui alimente `data_sources` au boot.

On vérifie le CATALOGUE (déclaration) — pas l'état d'une base — pour être déterministe.
"""
from __future__ import annotations

import pytest

from labuse.api import ortho_proxy
from labuse.ingestion.seed_sources import SOURCES

# Chaque overlay WMTS servi par un proxy → un fragment identifiant sa source dans le catalogue.
# Ajouter un overlay WMTS SANS l'inscrire ici (et sans déclarer sa source) fait échouer ce test.
WMTS_OVERLAYS = {
    ortho_proxy._CONTOUR_LAYER: "ELEVATION.CONTOUR.LINE",   # Courbes de niveau
}


@pytest.mark.parametrize("layer,fragment", list(WMTS_OVERLAYS.items()))
def test_chaque_overlay_wmts_a_sa_source_cataloguee(layer, fragment):
    trouve = any(
        fragment in (s.get("source_millesime") or "") or fragment in (s.get("name") or "")
        for s in SOURCES
    )
    assert trouve, f"couche WMTS {layer} servie sans source déclarée dans seed_sources.SOURCES"
