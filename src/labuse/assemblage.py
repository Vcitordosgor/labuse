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

from . import runs  # run servi (point de vérité unique) — lu à la requête
from .proprietaire_type import classify_owner_type

ADJ_BUFFER_M = 0.5          # contact cadastral (cf. voisinage)
_INTERESSANT = ("opportunite", "a_creuser")


def _params() -> dict:
    from .faisabilite.zonage import hypotheses_faisabilite
    h = hypotheses_faisabilite(None)     # défaut Saint-Paul (hypothèses migrées dans plu_zonage.yaml)
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
        -- M37 : le statut du voisin = TIER SERVI (parcel_p_score_v2), plus le rail legacy
        -- parcel_evaluations.status (éteint). Même source de vérité que voisinage.py (M34).
        SELECT n.id, n.idu, n.surface_m2, p.surface_m2 AS surf_p,
               (p.surface_m2 + n.surface_m2) AS cumul,
               s.tier AS status
        FROM parcels p
        JOIN parcels n ON n.id <> p.id AND ST_DWithin(p.geom_2975, n.geom_2975, :buf)
        LEFT JOIN parcel_p_score_v2 s ON s.parcelle_id = n.idu AND s.run_id = :run
        WHERE p.id = :pid AND p.surface_m2 < :seuil          -- la parcelle est sous le seuil seule
          AND (p.surface_m2 + n.surface_m2) >= :seuil        -- mais l'assemblage franchit le seuil
        ORDER BY cumul DESC LIMIT 5
        """
    ), {"pid": parcel_id, "buf": ADJ_BUFFER_M, "seuil": p["min_surface_m2"],
        "run": runs.current()}).mappings().all()
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


# ASSEMBLAGE-2 (RETOUCHES-1 lot B.4) — l'assiette d'un assemblage = l'UNION des géométries, jamais
# la somme des résiduels par parcelle (qui compte DEUX FOIS les reculs INTERNES entre parcelles et
# multiplie la VRD par le nombre de parcelles). On insète le CONTOUR EXTÉRIEUR de l'union du recul
# séparatif (les limites internes disparaissent dans ST_Union), on clippe à la portion U/AU, on
# retranche l'union des grèves (ER ∪ EBC ∪ PPR rouge ∪ PEB A/B ∪ marchepied DPF ∪ ravine ∪ 50 pas ∩
# assiette, jamais deux fois un chevauchement) — MÊME logique et MÊMES seuils que l'assiette clippée
# servie (faisabilite/db.py `_EMPRISE` + `_GREVE_CERTAINE`), appliquée à l'union.
_EMPRISE_UNION = text("""
WITH u AS (
    SELECT ST_Union(geom_2975) AS g, ST_Area(ST_Union(geom_2975)) AS surface,
           ST_Buffer(ST_Union(geom_2975), -:d) AS b
    FROM parcels WHERE id = ANY(:ids)),
uau AS (
    SELECT ST_Union(ST_MakeValid(ST_ClipByBox2D(z.geom_2975, u.b))) AS uu
    FROM spatial_layers z, u
    WHERE z.kind = :zkind AND z.commune = :commune
      AND labuse_zone_famille(z.subtype) = ANY(:uau_fams)
      AND ST_Intersects(z.geom_2975, u.b)),
assiette AS (
    SELECT CASE WHEN uau.uu IS NULL THEN u.b ELSE ST_Intersection(u.b, uau.uu) END AS a,
           ST_Area(u.b) AS full_area, u.surface AS surface, u.b AS b
    FROM u LEFT JOIN uau ON TRUE),
greve AS (
    SELECT ST_MakeValid(ST_ClipByBox2D(e.geom_2975, a.b)) AS geom FROM spatial_layers e, assiette a
      WHERE e.kind = :pkind AND e.commune = :commune AND e.subtype = ANY(:er_types)
        AND ST_Intersects(e.geom_2975, a.b)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(e.geom_2975, a.b)) FROM spatial_layers e, assiette a
      WHERE e.kind = :pkind AND e.commune = :commune AND e.subtype = ANY(:ebc_types)
        AND ST_Intersects(e.geom_2975, a.b)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(g.geom_2975, a.b)) FROM spatial_layers g, assiette a
      WHERE g.kind = 'ppr' AND g.commune = :commune AND g.subtype = ANY(:ppr_red)
        AND ST_Intersects(g.geom_2975, a.b)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(g.geom_2975, a.b)) FROM spatial_layers g, assiette a
      WHERE g.kind = 'peb' AND lower(g.subtype) = ANY(:peb_ab) AND ST_Intersects(g.geom_2975, a.b)
  UNION ALL
    SELECT ST_Buffer(ST_MakeValid(g.geom_2975), :dpf_m) FROM spatial_layers g, assiette a
      WHERE g.kind = 'dpf' AND g.commune = :commune AND ST_DWithin(g.geom_2975, a.b, :dpf_m)
  UNION ALL
    SELECT ST_Buffer(ST_MakeValid(g.geom_2975), :rav_m) FROM spatial_layers g, assiette a
      WHERE g.kind = 'ravine' AND g.commune = :commune AND ST_DWithin(g.geom_2975, a.b, :rav_m)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(g.geom_2975, a.b)) FROM spatial_layers g, assiette a
      WHERE g.kind = 'cinquante_pas' AND g.commune = :commune AND ST_Intersects(g.geom_2975, a.b)
)
SELECT a.full_area, ST_Area(a.a) AS assiette_area, a.surface,
       COALESCE(ST_Area(ST_Intersection(a.a, gg.u)), 0.0) AS greve_area
FROM assiette a LEFT JOIN (SELECT ST_Union(geom) AS u FROM greve) gg ON TRUE
""")


def _capacite_union(session: Session, parcels: list) -> dict | None:
    """ASSEMBLAGE-2 — capacité + bilan de l'UNION des parcelles : UNE assiette (l'union insetée,
    clippée U/AU, moins les grèves), UN passage du moteur de capacité (`estimate_capacity`, le même
    que le résiduel/la fiche), UNE charge foncière (`compute_bilan_servi`, VRD sur l'emprise
    RÉELLEMENT aménagée — COMPARER-2 §2). None si aucune parcelle n'est constructible."""
    import dataclasses

    from .faisabilite.bilan import compute_bilan_servi
    from .faisabilite.db import _layer_params, parcel_faisabilite
    from .faisabilite.engine import Hypotheses, estimate_capacity
    from .faisabilite.zonage import resolve_zone

    # parcelle DOMINANTE constructible (plus grande surface) : porte la zone/commune de référence
    # (assemblage = parcelles contiguës, même secteur) + le prix de sortie du secteur pour le bilan.
    dom = None
    for p in sorted(parcels, key=lambda p: p.surface_m2 or 0, reverse=True):
        fz = parcel_faisabilite(session, p.id)
        if fz and fz[1].constructible:
            dom = (p, fz)
            break
    if dom is None:
        return None
    p_dom, (ctx_dom, _f_dom) = dom
    commune = ctx_dom.commune
    rules = resolve_zone(ctx_dom.zone, ctx_dom.commune) if ctx_dom.zone else None
    if rules is None:
        return None
    hyp = Hypotheses.charger(commune)
    recul = (float(rules.recul_limites_sep_m)
             if isinstance(rules.recul_limites_sep_m, (int, float))
             else hyp.recul_limites_defaut_m)
    zonage, presc = _layer_params("zonage_plu_gpu"), _layer_params("prescription_plu")
    risq, dpfp, ravp, pebp = (_layer_params("risques"), _layer_params("dpf"),
                              _layer_params("ravine"), _layer_params("peb"))
    row = session.execute(_EMPRISE_UNION, {
        "ids": [p.id for p in parcels], "d": recul, "commune": commune,
        "zkind": zonage.get("spatial_kind", "plu_gpu_zone"),
        "uau_fams": list(zonage.get("positive_prefixes", ["U", "AU"])),
        "pkind": presc.get("spatial_kind", "plu_gpu_prescription"),
        "er_types": [str(t) for t in presc.get("emplacement_reserve_typepsc", ["05"])],
        "ebc_types": [str(t) for t in presc.get("boise_classe_typepsc", ["01"])],
        "ppr_red": [str(s) for s in risq.get("ppr_red_subtypes", ["INTERDICTION"])],
        "peb_ab": [str(z).lower() for z in pebp.get("hard_zones", ["a", "b"])],
        "dpf_m": float(dpfp.get("marchepied_m", 3.25)),
        "rav_m": float(ravp.get("buffer_m", 10)),
    }).one()
    surface_union = float(row.surface or 0.0)
    emprise = max(0.0, float(row.assiette_area or 0.0) - float(row.greve_area or 0.0))
    if surface_union <= 0 or emprise <= 0:
        return None
    # capacité de l'union : MÊME moteur que le résiduel (assiette réelle = union insetée)
    f_union = estimate_capacity(rules, surface_union, ctx_dom.contraintes, hyp=hyp,
                                emprise_geo=(emprise, recul), extras={})
    if not f_union.constructible:
        return None
    ctx_union = dataclasses.replace(ctx_dom, surface_m2=surface_union, idu="ASSEMBLAGE",
                                    parcel_id=p_dom.id)
    # bilan de l'union : UNE charge foncière (VRD sur l'emprise aménagée de l'ENSEMBLE, une fois),
    # prix de sortie du secteur de la parcelle dominante (même secteur pour des parcelles contiguës).
    b, _ps = compute_bilan_servi(session, p_dom.id, fz=(ctx_union, f_union))
    fr = f_union.fourchette or {}
    log = fr.get("logements_sous_sol") or fr.get("logements_au_sol") or [0, 0]
    return {
        "surface_m2": round(surface_union),
        "emprise_m2": round(emprise),
        "sdp_m2": round(float(fr.get("surface_plancher_m2") or 0.0)),
        "logements": [log[0] or 0, log[1] or 0],
        "ca": (b.ca if (b and b.fiable) else None),
        "charge_fonciere": (b.charge_fonciere if (b and b.fiable) else None),
    }


def aggregate_assiette(session: Session, parcels: list) -> dict:
    """CAPACITÉ + BILAN d'une assiette d'assemblage — calculés sur l'UNION des géométries (ASSEMBLAGE-2,
    RETOUCHES-1 lot B.4) : une seule assiette, un seul passage du moteur de capacité, une seule VRD
    (`_capacite_union`). Plus jamais la somme des résiduels par parcelle (qui doublait les reculs
    internes et multipliait la VRD). SOURCE unique de l'étude d'assemblage : /assemblage/study ET
    /moteurs/assemblage. `parcels` = objets Parcel (id, surface_m2, idu, commune). Renvoie aussi la
    SDP PAR PARCELLE (gain vs la meilleure seule) et les zones (valorisation)."""
    from .faisabilite.db import fiche_payload
    surface = round(sum(p.surface_m2 or 0 for p in parcels))
    par_parcelle: dict[int, float] = {}
    zones: list[tuple[str | None, str | None]] = []
    for p in parcels:
        try:
            fa = fiche_payload(session, p.id)
        except Exception:  # noqa: BLE001 — une parcelle illisible ne casse pas l'étude
            fa = None
        fr = (fa or {}).get("fourchette") or {}
        par_parcelle[p.id] = round(fr.get("surface_plancher_m2") or 0)
        zones.append((getattr(p, "commune", None), (fa or {}).get("zone")))
    u = _capacite_union(session, parcels)
    if not u:
        return {"surface_cumulee_m2": surface, "sdp_m2": 0, "logements": [0, 0], "ca": None,
                "charge_fonciere": None, "n_chiffrables": 0, "sdp_par_parcelle": par_parcelle,
                "zones": zones, "assiette": "aucune", "emprise_union_m2": None}
    cf = u["charge_fonciere"]
    cf_out = ({**cf, "par_m2_terrain": round(cf["central"] / surface)} if cf and surface else cf)
    return {
        "surface_cumulee_m2": surface,
        "sdp_m2": u["sdp_m2"],
        "logements": u["logements"],
        "ca": u["ca"],
        "charge_fonciere": cf_out,
        "n_chiffrables": 1 if u["ca"] else 0,
        "sdp_par_parcelle": par_parcelle,
        "zones": zones,
        "assiette": "union",
        "emprise_union_m2": u["emprise_m2"],
    }
