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


# CONTENANCE-1 (garde-fou) — quand la contenance s'écarte d'un facteur > 2 du dessin (dans un sens
# OU l'autre : contenance < dessin/2 ou contenance > 2×dessin), le plan et le cadastre se contredisent
# trop : la surface est INDÉTERMINÉE. On ne calcule NI sur la contenance NI sur le dessin → « Analyse
# incomplète », les deux chiffres affichés, aucune capacité ni prix au m². Vérifié sur 40 parcelles
# (ECARTS.md) : l'incohérence est DANS le cadastre IGN. La borne HAUTE (contenance ≫ dessin) évite
# qu'une contenance aberrante (erreur d'unité) ne gonfle l'assiette via la ré-échelle C3.
MSG_SURFACE_INCERTAINE = "surface incertaine : le plan et le cadastre ne concordent pas"


def surface_incertaine(dessin_m2, contenance_m2) -> bool:
    """True si la contenance est présente ET s'écarte d'un facteur > 2 du dessin, dans UN SENS OU
    L'AUTRE : contenance < dessin/2 (plan énorme devant un petit acte) OU contenance > 2×dessin
    (contenance anormalement grande, p.ex. erreur d'unité ×10 000 : BP2028, dessin 813 m² ↔
    contenance 8 130 000). Garde-fou : la parcelle bascule en « Analyse incomplète ». Le garde-fou
    est désormais SYMÉTRIQUE — aucune ré-échelle C3 ne peut gonfler l'assiette à partir d'une
    contenance aberrante."""
    if not dessin_m2 or contenance_m2 is None or float(contenance_m2) <= 0:
        return False
    c, d = float(contenance_m2), float(dessin_m2)
    return c < d / 2.0 or c > 2.0 * d


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
