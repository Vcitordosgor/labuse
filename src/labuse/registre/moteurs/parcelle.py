"""CIRCUIT-2 lot 1.6 — moteur `parcelle_proximites` : les distances et l'assemblage à la MAILLE
PARCELLE. `plus_proche` est le calcul extrait (l'endpoint appelle ici) ; l'assemblage reste chez
son producteur (bloc entier trop intriqué pour une coupe propre) — délégation, une seule vérité.
"""
from __future__ import annotations

from sqlalchemy import text


def plus_proche(db, idu: str, kind: str, subtype: str | None = None) -> dict | None:
    """distance_arret_m (et pôle/téléphérique/ligne HT/axe) — l'objet `kind` le plus proche de la
    parcelle (KNN geom_2975) + distance en mètres. M106 : PROXIMITÉ, jamais appartenance — on sert
    la distance, le lecteur juge. Extraction de api/app.py:_plus_proche."""
    row = db.execute(text(
        "SELECT sl.name, sl.subtype, sl.attrs, round(ST_Distance(sl.geom_2975, p.geom_2975))::int AS d "
        "FROM spatial_layers sl, parcels p WHERE p.idu = :idu AND sl.kind = :k "
        "AND sl.geom_2975 IS NOT NULL AND (CAST(:st AS text) IS NULL OR sl.subtype = :st) "
        "ORDER BY sl.geom_2975 <-> p.geom_2975 LIMIT 1"),
        {"idu": idu, "k": kind, "st": subtype}).mappings().first()
    if not row:
        return None
    return {"nom": row["name"], "subtype": row["subtype"],
            "attrs": row["attrs"] or {}, "distance_m": row["d"]}


def assemblage_assiette(db, idus: list[str]) -> dict:
    """assemblage_parcelles_n · assemblage_surface_m2 — DÉLÉGATION : le calcul vit dans
    api/moteurs.py:assemblage (contiguïté, agrégation fiche_payload, valorisation), une seule
    vérité — le bloc est trop intriqué (HTTP, plafonds config, privacy) pour une coupe propre."""
    from ...api.moteurs import AssemblageIn, assemblage
    return assemblage(AssemblageIn(idus=idus), db=db)
