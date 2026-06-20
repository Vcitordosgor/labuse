"""Assemblage foncier v1 (Lot C5) — paires de parcelles contiguës qui, RÉUNIES, franchissent
un seuil de taille qu'aucune n'atteint seule (l'assemblage débloque l'échelle d'une opération).

Pur PostGIS (ST_DWithin sur le contour cadastral) — aucune source externe. Croise avec le type
de propriétaire (C3) : deux parcelles du MÊME propriétaire morale identifié = priorité (un seul
interlocuteur). PRUDENCE héritée du voisinage : jamais d'affirmation de faisabilité ni d'accord.
Lecture seule ; ne touche ni la cascade ni le scoring.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import config
from .proprietaire_type import classify_owner_type

ADJ_BUFFER_M = 0.5          # contact cadastral (cf. voisinage)
_INTERESSANT = ("opportunite", "a_creuser")


def _params() -> dict:
    h = (config.load_yaml_config("plu_saint_paul").get("hypotheses_faisabilite") or {})
    return {
        "min_surface_m2": float(h.get("assemblage_min_surface_m2", 1000)),  # PLACEHOLDER
        "individuel_max_m2": float(h.get("assemblage_individuel_max_m2", 1000)),  # PLACEHOLDER
    }


def _owner_payload(session: Session, parcel_id: int) -> dict | None:
    return session.execute(text(
        """SELECT psr.raw_payload FROM parcel_source_results psr
           JOIN data_sources ds ON ds.id = psr.data_source_id
           WHERE psr.parcel_id = :p AND ds.name = 'Fichiers fonciers (Cerema)'
           ORDER BY psr.fetched_at DESC LIMIT 1"""), {"p": parcel_id}).scalar()


def _same_owner(a: dict | None, b: dict | None) -> bool:
    """Même propriétaire morale identifié (catégorie identique) — sinon « à vérifier »."""
    oa, ob = classify_owner_type(a), classify_owner_type(b)
    if not (oa["identifiable"] and ob["identifiable"]):
        return False
    return (a or {}).get("categorie") == (b or {}).get("categorie") and bool((a or {}).get("categorie"))


def parcel_assemblage(session: Session, parcel_id: int) -> dict:
    """Meilleure opportunité d'assemblage pour UNE parcelle (fiche) : un partenaire contigu avec
    qui la surface cumulée franchit le seuil. None-friendly."""
    p = _params()
    rows = session.execute(text(
        """
        SELECT n.id, n.idu, n.surface_m2, p.surface_m2 AS surf_p,
               (p.surface_m2 + n.surface_m2) AS cumul,
               e.status
        FROM parcels p
        JOIN parcels n ON n.id <> p.id AND ST_DWithin(p.geom_2975, n.geom_2975, :buf)
        LEFT JOIN LATERAL (SELECT status FROM parcel_evaluations e
            WHERE e.parcel_id = n.id ORDER BY evaluated_at DESC LIMIT 1) e ON true
        WHERE p.id = :pid AND p.surface_m2 < :seuil          -- la parcelle est sous le seuil seule
          AND (p.surface_m2 + n.surface_m2) >= :seuil        -- mais l'assemblage franchit le seuil
        ORDER BY cumul DESC LIMIT 5
        """
    ), {"pid": parcel_id, "buf": ADJ_BUFFER_M, "seuil": p["min_surface_m2"]}).mappings().all()
    if not rows:
        return {"possible": False}
    own_p = _owner_payload(session, parcel_id)
    partenaires = []
    for r in rows:
        same = _same_owner(own_p, _owner_payload(session, r["id"]))
        partenaires.append({"idu": r["idu"], "surface_m2": round(r["surface_m2"] or 0),
                            "surface_cumulee_m2": round(r["cumul"] or 0),
                            "status": r["status"], "meme_proprietaire": same})
    best = partenaires[0]
    prio = any(x["meme_proprietaire"] for x in partenaires)
    return {
        "possible": True, "seuil_m2": round(p["min_surface_m2"]),
        "meilleur_cumul_m2": best["surface_cumulee_m2"],
        "partenaires": partenaires, "priorite_meme_proprietaire": prio,
        "note": (f"Assemblage à étudier : avec une parcelle contiguë, ~{best['surface_cumulee_m2']} m² "
                 f"cumulés (seuil {round(p['min_surface_m2'])} m²)"
                 + (" — MÊME propriétaire morale (priorité, un interlocuteur)" if prio else "")
                 + ". Propriétaires, accords et faisabilité à vérifier."),
    }


def find_assemblages(session: Session, commune: str, limit: int = 100) -> list[dict]:
    """Liste dédiée : paires contiguës dont la somme franchit le seuil alors qu'AUCUNE ne
    l'atteint seule. Triées : même propriétaire d'abord, puis surface cumulée. v1 = paires
    (le triplet se lit en chaînant deux paires partageant une parcelle)."""
    p = _params()
    rows = session.execute(text(
        """
        SELECT a.idu AS idu_a, b.idu AS idu_b, a.id AS id_a, b.id AS id_b,
               round(a.surface_m2) AS s_a, round(b.surface_m2) AS s_b,
               round(a.surface_m2 + b.surface_m2) AS cumul
        FROM parcels a
        JOIN parcels b ON b.id > a.id AND ST_DWithin(a.geom_2975, b.geom_2975, :buf)
        WHERE a.commune = :c AND b.commune = :c
          AND a.surface_m2 < :indiv AND b.surface_m2 < :indiv
          AND (a.surface_m2 + b.surface_m2) >= :seuil
        ORDER BY cumul DESC
        LIMIT :lim
        """
    ), {"c": commune, "buf": ADJ_BUFFER_M, "indiv": p["individuel_max_m2"],
        "seuil": p["min_surface_m2"], "lim": limit}).mappings().all()
    out = []
    for r in rows:
        same = _same_owner(_owner_payload(session, r["id_a"]), _owner_payload(session, r["id_b"]))
        out.append({"parcelles": [r["idu_a"], r["idu_b"]],
                    "surfaces_m2": [int(r["s_a"]), int(r["s_b"])],
                    "surface_cumulee_m2": int(r["cumul"]),
                    "meme_proprietaire": same})
    out.sort(key=lambda x: (x["meme_proprietaire"], x["surface_cumulee_m2"]), reverse=True)
    return out
