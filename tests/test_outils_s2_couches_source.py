"""OUTILS-S2 Lot C — verrou : toute couche carte WMTS (overlay proxy) a sa source DÉCLARÉE.

Les couches VECTEUR passent par `spatial_layers` et sont déjà couvertes par
`check_sources_declarees` (spatial_layers.data_source_id → data_sources). Les overlays WMTS servis
EN DIRECT par un proxy (courbes de niveau, orthos) NE PASSENT PAS par `spatial_layers` : ils
échappaient donc à toute garde. Ce verrou ferme la brèche : chaque overlay WMTS déclaré doit avoir
sa source dans le catalogue (`seed_sources.SOURCES`), qui alimente `data_sources` au boot.

⚠ Cas « Courbes de niveau » (RETOURS-13 P5) : l'overlay `ELEVATION.CONTOUR.LINE` est un canal de
DIFFUSION (WMTS) de la donnée RGE ALTI® — les courbes sont dérivées du modèle altimétrique. Sa
SOURCE est donc « RGE ALTI (altimétrie) », déjà cataloguée (comme le profil altimétrique, qui en
dérive aussi). C'est pourquoi l'ajout de ces deux fonctions n'a PAS créé de nouvelle source (compte
inchangé) : ce n'est pas un oubli, c'est la bonne attribution. Un overlay WMTS n'est pas un réservoir
de données local (pas de table servie), donc pas une ligne de vitrine distincte.

On vérifie le CATALOGUE (déclaration) — pas l'état d'une base — pour être déterministe.
"""
from __future__ import annotations

import pytest

from labuse.api import ortho_proxy
from labuse.ingestion.seed_sources import SOURCES

# Chaque overlay WMTS servi par un proxy → un fragment identifiant SA SOURCE dans le catalogue.
# Ajouter un overlay WMTS SANS rattacher sa source (déclarée ici) fait échouer ce test.
WMTS_OVERLAYS = {
    ortho_proxy._CONTOUR_LAYER: "RGE ALTI",   # Courbes de niveau (ELEVATION.CONTOUR.LINE) ⟵ dérivé RGE ALTI
}


@pytest.mark.parametrize("layer,fragment", list(WMTS_OVERLAYS.items()))
def test_chaque_overlay_wmts_a_sa_source_cataloguee(layer, fragment):
    trouve = any(
        fragment in (s.get("name") or "") or fragment in (s.get("source_millesime") or "")
        for s in SOURCES
    )
    assert trouve, f"couche WMTS {layer} servie sans source rattachée dans seed_sources.SOURCES"
