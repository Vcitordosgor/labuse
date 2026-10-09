"""CONTENANCE-1 (Lot B) — LA source unique de « la surface du terrain » pour le client.

`parcels.surface_m2` = aire du DESSIN du plan cadastral (ST_Area). `parcels.contenance_m2` =
contenance cadastrale, le chiffre de l'acte notarié (champ Etalab). Décision de Vic : la surface
du terrain affichée au client, c'est la CONTENANCE si on l'a, sinon le dessin (mention « mesurée
sur le plan »). Le dessin ne sert plus qu'aux formes.

Tout le code — serializers, exports, Copilote, Flash, KMZ — passe par `surface_terrain(...)` (côté
Python) ou par `SURFACE_TERRAIN_SQL(...)` (dans le SQL). Plus personne ne lit `surface_m2` seul pour
AFFICHER une surface de terrain.
"""
from __future__ import annotations

from typing import NamedTuple

SOURCE_CADASTRE = "cadastre"   # contenance présente = chiffre de l'acte
SOURCE_PLAN = "plan"           # repli : aire mesurée sur le dessin


class SurfaceTerrain(NamedTuple):
    valeur: int | None          # m², arrondi entier (contenance si présente, sinon dessin arrondi)
    source: str                 # SOURCE_CADASTRE | SOURCE_PLAN
    dessin_m2: int | None       # l'aire du dessin, arrondie (pour la ligne discrète « Dessin du plan »)
    contenance_m2: int | None   # la contenance brute si présente


def surface_terrain(dessin_m2, contenance_m2) -> SurfaceTerrain:
    """Surface de terrain à afficher : contenance si présente, sinon dessin (repli, source='plan').

    `dessin_m2` = surface_m2 (float possible) ; `contenance_m2` = entier ou None. Jamais d'exception
    sur des entrées nulles — une parcelle sans aucune surface renvoie valeur=None (affiché « — »)."""
    des = round(dessin_m2) if dessin_m2 else None
    cont = int(contenance_m2) if contenance_m2 is not None else None
    if cont is not None:
        return SurfaceTerrain(cont, SOURCE_CADASTRE, des, cont)
    return SurfaceTerrain(des, SOURCE_PLAN, des, None)


def ecart_pct(dessin_m2, contenance_m2) -> float | None:
    """Écart relatif dessin↔contenance, en % de la contenance (None si l'une manque)."""
    if not dessin_m2 or not contenance_m2:
        return None
    return 100.0 * (float(dessin_m2) - float(contenance_m2)) / float(contenance_m2)


def SURFACE_TERRAIN_SQL(alias: str = "p") -> str:
    """Expression SQL de la surface de terrain (contenance si présente, sinon dessin). À utiliser
    dans les SELECT/WHERE/ORDER partout où le client FILTRE ou TRIE par surface de terrain."""
    return f"COALESCE({alias}.contenance_m2, {alias}.surface_m2)"


def champs_terrain(dessin_m2, contenance_m2) -> dict:
    """Les 3 champs additifs de surface de terrain, à `**`-spreader dans un dict de parcelle (SANS
    toucher `surface_m2`, qui reste le dessin). CONTENANCE-1."""
    st = surface_terrain(dessin_m2, contenance_m2)
    return {"surface_terrain_m2": st.valeur, "surface_source": st.source,
            "surface_dessin_m2": st.dessin_m2, "contenance_m2": st.contenance_m2}


def enrichir_payload(d: dict) -> dict:
    """Ajoute `surface_terrain_m2` + `surface_source` (+ expose `surface_dessin_m2`) à un dict de
    parcelle qui porte déjà `surface_m2` (dessin) et éventuellement `contenance_m2`. Mutation en
    place + renvoi, pour chaîner. Idempotent."""
    st = surface_terrain(d.get("surface_m2"), d.get("contenance_m2"))
    d["surface_terrain_m2"] = st.valeur
    d["surface_source"] = st.source
    d["surface_dessin_m2"] = st.dessin_m2
    return d
