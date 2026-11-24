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

ADJ_BUFFER_M = 0.5          # contact cadastral (cf. voisinage) — distance MAX pour considérer un lien
# OUTIL-ASSEMBLAGE-FIX-1 (LOT 1) — longueur MINIMALE de bord cadastral PARTAGÉ pour qualifier une vraie
# mitoyenneté (« bord commun »). En deçà (contact par un seul point : bord mesuré ~0), l'assiette n'est
# PAS d'un seul tenant. Les vrais bords du relecteur mesurent 10–43 m, les contacts ponctuels 0 m : 0,5 m
# sépare proprement les deux (et absorbe les artefacts de précision d'une intersection ponctuelle).
SEUIL_BORD_M = 0.5
_INTERESSANT = ("opportunite", "a_creuser")


# OUTIL-ASSEMBLAGE-FIX-1 (LOT 1) — SQL de mesure d'un lien entre deux parcelles proches : distance
# (0 = elles se touchent) et LONGUEUR du bord cadastral commun (part LIGNE de l'intersection ;
# un contact ponctuel donne un ST_Point → longueur 0). Même seuil `ADJ_BUFFER_M` que la détection.
_LIENS_MESURE = text("""
    SELECT a.id AS a, b.id AS b,
           ST_Distance(a.geom_2975, b.geom_2975) AS dist,
           COALESCE(ST_Length(ST_CollectionExtract(
               ST_Intersection(a.geom_2975, b.geom_2975), 2)), 0.0) AS bord
    FROM parcels a JOIN parcels b
      ON a.id < b.id AND ST_DWithin(a.geom_2975, b.geom_2975, :buf)
    WHERE a.id = ANY(:ids) AND b.id = ANY(:ids)""")


def classer_lien(dist_m: float, bord_m: float) -> dict:
    """OUTIL-ASSEMBLAGE-FIX-1 (LOT 1) — les TROIS verdicts d'un lien entre deux parcelles proches
    (≤ `ADJ_BUFFER_M`), pour ne plus donner le même feu vert à une mitoyenneté vérifiée qu'à un
    contact ponctuel ou à un petit vide :
      · ``bord``  — bord cadastral commun MESURÉ (≥ `SEUIL_BORD_M`) : SEULE vraie mitoyenneté, la
                    seule qui autorise une opération « d'un seul tenant » (porte `longueur_bord_m`) ;
      · ``point`` — contact par un seul point (les polygones se touchent mais ne partagent aucun bord) ;
      · ``vide``  — petit vide cadastral (séparées de `vide_m` > 0, sous la tolérance) : la fusion des
                    géométries ne comble PAS ce vide.
    """
    dist_m, bord_m = float(dist_m or 0.0), float(bord_m or 0.0)
    if bord_m >= SEUIL_BORD_M:
        return {"type": "bord", "longueur_bord_m": round(bord_m, 2), "vide_m": None}
    if dist_m <= 0.01:
        return {"type": "point", "longueur_bord_m": round(bord_m, 2), "vide_m": None}
    return {"type": "vide", "longueur_bord_m": None, "vide_m": round(dist_m, 2)}


def liens_assiette(session: Session, ids: list[int]) -> list[dict]:
    """Les liens classés (bord/point/vide) entre les parcelles `ids`, du moteur de mesure PostGIS."""
    rows = session.execute(_LIENS_MESURE, {"ids": ids, "buf": ADJ_BUFFER_M}).mappings().all()
    return [{"a": r["a"], "b": r["b"], **classer_lien(r["dist"], r["bord"])} for r in rows]


def verdicts_contiguite(session: Session, ids: list[int]) -> dict:
    """OUTIL-ASSEMBLAGE-FIX-1 (LOT 1) — les verdicts de contiguïté d'une sélection ORDONNÉE d'ids,
    partagés par l'écran (`/moteurs/assemblage`) et l'orphelin `/assemblage/study` :
      · ``contigu`` / ``tenant_unique`` — tous reliés par de VRAIS bords (seule « contiguë ») ;
      · ``relie``        — tous dans UN bloc via n'importe quel lien ≤ `ADJ_BUFFER_M` (gate du chiffrage) ;
      · ``lien_faible``  — relié mais via ≥ 1 contact ponctuel / petit vide ;
      · ``liens``        — liste brute `[{a, b, type, longueur_bord_m, vide_m}]` (ids internes) ;
      · ``isolees_ids``  — ids hors du bloc relié de `ids[0]` (séparés > tolérance cadastrale)."""
    liens = liens_assiette(session, ids)
    adj_all: dict[int, set[int]] = {i: set() for i in ids}
    adj_bord: dict[int, set[int]] = {i: set() for i in ids}
    for ln in liens:
        adj_all[ln["a"]].add(ln["b"]); adj_all[ln["b"]].add(ln["a"])
        if ln["type"] == "bord":
            adj_bord[ln["a"]].add(ln["b"]); adj_bord[ln["b"]].add(ln["a"])

    def _comp(adj: dict[int, set[int]]) -> set[int]:
        seen, stack = {ids[0]}, [ids[0]]
        while stack:
            for nb in adj[stack.pop()]:
                if nb not in seen:
                    seen.add(nb); stack.append(nb)
        return seen

    seen_all = _comp(adj_all)
    tenant = len(_comp(adj_bord)) == len(ids)
    relie = len(seen_all) == len(ids)
    return {"contigu": tenant, "tenant_unique": tenant, "relie": relie,
            "lien_faible": relie and not tenant, "liens": liens,
            "isolees_ids": [i for i in ids if i not in seen_all]}


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
        -- CONTENANCE-1 (Lot C) : le seuil de taille et les surfaces cumulées portent sur la surface
        -- de TERRAIN (contenance si présente, sinon dessin) — la même que la fiche.
        SELECT n.id, n.idu, COALESCE(n.contenance_m2, n.surface_m2) AS surface_m2,
               COALESCE(p.contenance_m2, p.surface_m2) AS surf_p,
               (COALESCE(p.contenance_m2, p.surface_m2) + COALESCE(n.contenance_m2, n.surface_m2)) AS cumul,
               s.tier AS status
        FROM parcels p
        JOIN parcels n ON n.id <> p.id AND ST_DWithin(p.geom_2975, n.geom_2975, :buf)
        LEFT JOIN parcel_p_score_v2 s ON s.parcelle_id = n.idu AND s.run_id = :run
        WHERE p.id = :pid AND COALESCE(p.contenance_m2, p.surface_m2) < :seuil   -- parcelle sous le seuil seule
          AND (COALESCE(p.contenance_m2, p.surface_m2) + COALESCE(n.contenance_m2, n.surface_m2)) >= :seuil
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


# OUTIL-ASSEMBLAGE-FIX-1 (LOT 2) — la capacité de l'union se calcule ZONE PAR ZONE : chaque portion
# de l'union reçoit les règles de SA propre zone (emprise, hauteur, recul), puis on additionne les SDP.
# Avant, la zone DOMINANTE régissait tout le calcul (audit ASTRA bloquant 2 : U2h recevait la hauteur
# U2b, Uh recevait l'emprise Uj). On conserve le CONTOUR de l'union (les limites INTERNES entre parcelles
# disparaissent dans ST_Union) : chaque zone insète l'union de SON recul (contour extérieur seulement —
# `ST_Buffer` sur l'union ne touche pas la limite interne entre zones), clippe à U/AU, intersecte SA
# zone, retranche les grèves. Reproduit à l'euro les contrôles du relecteur (DH 32 174, BZ 1 460, 1 007).

# 1er token du libellé = code court de zone (même extraction que api/tiles + zone_servie).
_TOK_ZONE = ("COALESCE(NULLIF(rtrim(split_part(btrim(z.attrs->>'libelle'), ' ', 1), ':'), ''), "
             "rtrim(split_part(btrim(z.name), ' ', 1), ':'))")

# Les zones U/AU (codes courts distincts) qui touchent l'union — une portion par zone.
_ZONES_UNION = text(f"""
WITH u AS (SELECT ST_Union(geom_2975) AS g FROM parcels WHERE id = ANY(:ids))
SELECT {_TOK_ZONE} AS zone, labuse_zone_famille(z.subtype) AS fam
FROM spatial_layers z, u
WHERE z.kind = :zkind AND z.commune = :commune
  AND labuse_zone_famille(z.subtype) = ANY(:uau_fams)
  AND ST_Intersects(z.geom_2975, u.g)
GROUP BY 1, 2
HAVING sum(ST_Area(ST_Intersection(ST_MakeValid(z.geom_2975), (SELECT g FROM u)))) > 0
ORDER BY sum(ST_Area(ST_Intersection(ST_MakeValid(z.geom_2975), (SELECT g FROM u)))) DESC
""")

# Emprise constructible d'UNE zone : union insetée de SON recul (contour extérieur), ∩ U/AU, ∩ SA zone,
# − grèves (ER ∪ EBC ∪ PPR rouge ∪ PEB A/B ∪ marchepied DPF ∪ ravine ∪ 50 pas ∩ cette portion). Rend
# aussi la surface de TERRAIN de la zone (union ∩ zone, sans recul) pour le plafond CES/densité.
_EMPRISE_ZONE = text(f"""
WITH u AS (SELECT ST_Union(geom_2975) AS g FROM parcels WHERE id = ANY(:ids)),
ins AS (SELECT ST_Buffer(g, -:d) AS b, g FROM u),
zed AS (SELECT ST_Union(ST_MakeValid(z.geom_2975)) AS zz FROM spatial_layers z, ins
        WHERE z.kind = :zkind AND z.commune = :commune AND {_TOK_ZONE} = :zone
          AND ST_Intersects(z.geom_2975, ins.b)),
uau AS (SELECT ST_Union(ST_MakeValid(z.geom_2975)) AS uu FROM spatial_layers z, ins
        WHERE z.kind = :zkind AND z.commune = :commune
          AND labuse_zone_famille(z.subtype) = ANY(:uau_fams) AND ST_Intersects(z.geom_2975, ins.b)),
ass AS (SELECT ST_Intersection(ST_Intersection(ins.b, COALESCE(uau.uu, ins.b)),
                               (SELECT zz FROM zed)) AS a, ins.g AS g
        FROM ins LEFT JOIN uau ON TRUE),
greve AS (
    SELECT ST_MakeValid(ST_ClipByBox2D(e.geom_2975, ass.a)) AS geom FROM spatial_layers e, ass
      WHERE e.kind = :pkind AND e.commune = :commune AND e.subtype = ANY(:er_types) AND ST_Intersects(e.geom_2975, ass.a)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(e.geom_2975, ass.a)) FROM spatial_layers e, ass
      WHERE e.kind = :pkind AND e.commune = :commune AND e.subtype = ANY(:ebc_types) AND ST_Intersects(e.geom_2975, ass.a)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(g.geom_2975, ass.a)) FROM spatial_layers g, ass
      WHERE g.kind = 'ppr' AND g.commune = :commune AND g.subtype = ANY(:ppr_red) AND ST_Intersects(g.geom_2975, ass.a)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(g.geom_2975, ass.a)) FROM spatial_layers g, ass
      WHERE g.kind = 'peb' AND lower(g.subtype) = ANY(:peb_ab) AND ST_Intersects(g.geom_2975, ass.a)
  UNION ALL
    SELECT ST_Buffer(ST_MakeValid(g.geom_2975), :dpf_m) FROM spatial_layers g, ass
      WHERE g.kind = 'dpf' AND g.commune = :commune AND ST_DWithin(g.geom_2975, ass.a, :dpf_m)
  UNION ALL
    SELECT ST_Buffer(ST_MakeValid(g.geom_2975), :rav_m) FROM spatial_layers g, ass
      WHERE g.kind = 'ravine' AND g.commune = :commune AND ST_DWithin(g.geom_2975, ass.a, :rav_m)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(g.geom_2975, ass.a)) FROM spatial_layers g, ass
      WHERE g.kind = 'cinquante_pas' AND g.commune = :commune AND ST_Intersects(g.geom_2975, ass.a)
)
SELECT GREATEST(0.0, ST_Area(ass.a) - COALESCE(
         (SELECT ST_Area(ST_Intersection(ass.a, ST_Union(geom))) FROM greve), 0.0)) AS emprise_z,
       ST_Area(ST_Intersection(ass.g, (SELECT zz FROM zed))) AS surface_z
FROM ass
""")

# Retranchements AFFICHÉS (ce que les parcelles contiennent, mesuré SUR l'union DESSINÉE, non insetée) :
# part hors zone constructible, zone rouge PPR, emplacement réservé, espace boisé classé — en m², pour
# que l'utilisateur voie ce qui a été retiré et pourquoi (audit ASTRA bloquant 2).
_RETRANCH_UNION = text(f"""
WITH u AS (SELECT ST_Union(geom_2975) AS g, ST_Area(ST_Union(geom_2975)) AS surface
           FROM parcels WHERE id = ANY(:ids)),
uau AS (SELECT ST_Union(ST_MakeValid(z.geom_2975)) AS uu FROM spatial_layers z, u
        WHERE z.kind = :zkind AND z.commune = :commune
          AND labuse_zone_famille(z.subtype) = ANY(:uau_fams) AND ST_Intersects(z.geom_2975, u.g))
SELECT u.surface AS surface_union,
  COALESCE(ST_Area(ST_Intersection(u.g, uau.uu)), 0.0) AS surface_constructible,
  COALESCE((SELECT ST_Area(ST_Union(ST_Intersection(ST_MakeValid(g.geom_2975), u.g))) FROM spatial_layers g
            WHERE g.kind = 'ppr' AND g.commune = :commune AND g.subtype = ANY(:ppr_red)
              AND ST_Intersects(g.geom_2975, u.g)), 0.0) AS rouge,
  COALESCE((SELECT ST_Area(ST_Union(ST_Intersection(ST_MakeValid(e.geom_2975), u.g))) FROM spatial_layers e
            WHERE e.kind = :pkind AND e.commune = :commune AND e.subtype = ANY(:er_types)
              AND ST_Intersects(e.geom_2975, u.g)), 0.0) AS er,
  COALESCE((SELECT ST_Area(ST_Union(ST_Intersection(ST_MakeValid(e.geom_2975), u.g))) FROM spatial_layers e
            WHERE e.kind = :pkind AND e.commune = :commune AND e.subtype = ANY(:ebc_types)
              AND ST_Intersects(e.geom_2975, u.g)), 0.0) AS ebc
FROM u LEFT JOIN uau ON TRUE
""")


def _greve_params(presc: dict, risq: dict, pebp: dict, dpfp: dict, ravp: dict) -> dict:
    return {
        "pkind": presc.get("spatial_kind", "plu_gpu_prescription"),
        "er_types": [str(t) for t in presc.get("emplacement_reserve_typepsc", ["05"])],
        "ebc_types": [str(t) for t in presc.get("boise_classe_typepsc", ["01"])],
        "ppr_red": [str(s) for s in risq.get("ppr_red_subtypes", ["INTERDICTION"])],
        "peb_ab": [str(z).lower() for z in pebp.get("hard_zones", ["a", "b"])],
        "dpf_m": float(dpfp.get("marchepied_m", 3.25)),
        "rav_m": float(ravp.get("buffer_m", 10)),
    }


def _capacite_union(session: Session, parcels: list) -> dict | None:
    """OUTIL-ASSEMBLAGE-FIX-1 (LOT 2) — capacité + bilan de l'UNION, calculés ZONE PAR ZONE : chaque
    portion de l'union reçoit les règles de SA zone (emprise/hauteur/recul), `estimate_capacity` par
    zone (le MÊME moteur que la fiche), puis on additionne les SDP. UNE charge foncière sur la fourchette
    AGRÉGÉE (`compute_bilan_servi`, VRD sur l'emprise réellement aménagée). None si aucune zone
    constructible. Reproduit les contrôles multizones du relecteur à l'euro près."""
    import dataclasses

    from .faisabilite.bilan import compute_bilan_servi
    from .faisabilite.db import _layer_params, parcel_faisabilite
    from .faisabilite.engine import Hypotheses, estimate_capacity
    from .faisabilite.zonage import resolve_zone

    # parcelle DOMINANTE constructible (plus grande surface) : porte la commune/contraintes de référence
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
    hyp = Hypotheses.charger(commune)
    zonage, presc = _layer_params("zonage_plu_gpu"), _layer_params("prescription_plu")
    risq, dpfp, ravp, pebp = (_layer_params("risques"), _layer_params("dpf"),
                              _layer_params("ravine"), _layer_params("peb"))
    ids = [p.id for p in parcels]
    zkind = zonage.get("spatial_kind", "plu_gpu_zone")
    uau_fams = list(zonage.get("positive_prefixes", ["U", "AU"]))
    gparams = _greve_params(presc, risq, pebp, dpfp, ravp)

    def _recul(rz) -> float:
        return (float(rz.recul_limites_sep_m) if isinstance(rz.recul_limites_sep_m, (int, float))
                else hyp.recul_limites_defaut_m)

    zones = session.execute(_ZONES_UNION, {
        "ids": ids, "commune": commune, "zkind": zkind, "uau_fams": uau_fams}).mappings().all()

    zones_detail: list[dict] = []
    sdp_tot = emprise_tot = shab_tot = silo_tot = 0.0
    surf_dom = -1.0
    f_rep = None                    # faisabilité représentative (zone de plus grande surface) pour le bilan
    for z in zones:
        rules_z = resolve_zone(z["zone"], commune)
        if rules_z is None:
            continue
        recul_z = _recul(rules_z)
        er = session.execute(_EMPRISE_ZONE, {
            "ids": ids, "commune": commune, "d": recul_z, "zone": z["zone"],
            "zkind": zkind, "uau_fams": uau_fams, **gparams}).one()
        emprise_z = max(0.0, float(er.emprise_z or 0.0))
        surface_z = float(er.surface_z or 0.0)
        detail = {"zone": z["zone"], "fam": z["fam"], "surface_m2": round(surface_z),
                  "emprise_m2": round(emprise_z), "recul_limites_m": recul_z,
                  "recul_voirie_m": (float(rules_z.recul_voirie_m)
                                     if isinstance(rules_z.recul_voirie_m, (int, float)) else None),
                  "sdp_m2": 0, "niveaux": None, "constructible": False}
        if emprise_z <= 0 or surface_z <= 0:
            zones_detail.append(detail)
            continue
        f_z = estimate_capacity(rules_z, surface_z, ctx_dom.contraintes, hyp=hyp,
                                emprise_geo=(emprise_z, recul_z), extras={})
        frz = f_z.fourchette or {}
        sdp_z = float(frz.get("surface_plancher_m2") or 0.0)
        if not f_z.constructible or sdp_z <= 0:
            zones_detail.append(detail)
            continue
        sdp_tot += sdp_z
        emprise_tot += emprise_z
        shab_tot += float(frz.get("shab_vendable_m2") or 0.0)
        silo_tot += float(frz.get("shab_vendable_silo_m2") or 0.0)
        # LOGEMENTS-SOURCE-UNIQUE — on NE lit PAS `logements_au_sol`/`logements_sous_sol` ici (doctrine :
        # le nombre de logements n'a qu'une source, l'Étude ; aucun nouveau lecteur). La fourchette agrégée
        # garde les logements de la zone REPRÉSENTATIVE (f_rep) — exacte en mono-zone (cas chiffrés CV/BZ).
        if surface_z > surf_dom:
            surf_dom, f_rep = surface_z, f_z
        detail.update({"sdp_m2": round(sdp_z), "niveaux": frz.get("niveaux_max"), "constructible": True})
        zones_detail.append(detail)
    if sdp_tot <= 0 or f_rep is None:
        return None

    rt = session.execute(_RETRANCH_UNION, {
        "ids": ids, "commune": commune, "zkind": zkind, "uau_fams": uau_fams, **gparams}).one()
    surface_union = float(rt.surface_union or 0.0)
    surface_constructible = float(rt.surface_constructible or 0.0)
    if surface_union <= 0:
        return None
    part_constructible = (surface_constructible / surface_union) if surface_union > 0 else 1.0
    pct_hors_zone = max(0, min(100, round(100.0 * (1.0 - part_constructible))))
    retranchements = {
        # mesurés SUR l'union dessinée (ce que les parcelles contiennent) — l'effet NET après recul est
        # déjà dans l'emprise par zone ; ici on montre la surface VISIBLE de chaque contrainte.
        "hors_zone_m2": round(max(0.0, surface_union - surface_constructible)),
        "ppr_rouge_m2": round(float(rt.rouge or 0.0)),
        "emplacement_reserve_m2": round(float(rt.er or 0.0)),
        "ebc_m2": round(float(rt.ebc or 0.0)),
    }

    # Fourchette AGRÉGÉE : somme PAR ZONE (chaque zone a subi SON plafond de densité et SON % d'emprise).
    # C'est elle qui nourrit le bilan (CA = surface vendable cumulée des zones, pas la zone dominante).
    fr_agg = dict(f_rep.fourchette or {})   # garde les logements de f_rep (LOGEMENTS-SOURCE-UNIQUE)
    fr_agg.update({
        "surface_plancher_m2": round(sdp_tot),
        "shab_vendable_m2": round(shab_tot),
        "shab_vendable_silo_m2": round(silo_tot),
    })
    f_union = dataclasses.replace(f_rep, fourchette=fr_agg, constructible=True)
    ctx_union = dataclasses.replace(ctx_dom, surface_m2=surface_constructible, idu="ASSEMBLAGE",
                                    parcel_id=p_dom.id)
    # bilan de l'union : UNE charge foncière (VRD sur l'emprise aménagée de l'ENSEMBLE, une fois),
    # prix de sortie du secteur de la parcelle dominante (même secteur pour des parcelles contiguës).
    b, _ps = compute_bilan_servi(session, p_dom.id, fz=(ctx_union, f_union))
    return {
        "surface_m2": round(surface_union),
        # NU-G-007 — surface d'assiette EN ZONE CONSTRUCTIBLE = intersection DIRECTE de l'union avec U/AU
        # (ASTRA : « l'intersection directe du dessin avec U/AU », pas une proportion après recul).
        "surface_constructible_m2": round(surface_constructible),
        "pct_hors_zone": pct_hors_zone,
        "part_constructible": part_constructible,
        "emprise_m2": round(emprise_tot),
        "sdp_m2": round(sdp_tot),
        # LOT 2 — décomposition par zone (règles de chaque portion) + contraintes retranchées visibles.
        "zones_detail": zones_detail,
        "retranchements": retranchements,
        "ca": (b.ca if (b and b.fiable) else None),
        "charge_fonciere": (b.charge_fonciere if (b and b.fiable) else None),
        # RETOURS-25 (pt 1) — prix de SORTIE neuf (€/m² habitable) résolu pour ce bilan.
        "prix_sortie_eur_m2": (round(float(_ps["prix"])) if (b and b.fiable and _ps and _ps.get("prix")) else None),
        # OUTIL-ASSEMBLAGE-FIX-2 (LOT 1) — obligation de mixité (règle/article/page/régime/borne haute),
        # pour que l'écran Assemblage la PORTE comme la fiche. None si la parcelle n'est pas en SMS.
        "mixite": (b.mixite if b else None),
    }


def aggregate_assiette(session: Session, parcels: list) -> dict:
    """CAPACITÉ + BILAN d'une assiette d'assemblage — calculés sur l'UNION des géométries (ASSEMBLAGE-2,
    RETOUCHES-1 lot B.4) : une seule assiette, un seul passage du moteur de capacité, une seule VRD
    (`_capacite_union`). Plus jamais la somme des résiduels par parcelle (qui doublait les reculs
    internes et multipliait la VRD). SOURCE unique de l'étude d'assemblage : /assemblage/study ET
    /moteurs/assemblage. `parcels` = objets Parcel (id, surface_m2, idu, commune). Renvoie aussi la
    SDP PAR PARCELLE (gain vs la meilleure seule) et les zones (valorisation)."""
    from .faisabilite.db import fiche_payload
    # OUT-ASSEMB-001/002 (CONTENANCE-1) — surface d'assiette cumulée = somme des CONTENANCES cadastrales
    # (acte) si présentes, sinon dessin : homogène avec la fiche / le prefill taxe, jamais le dessin seul.
    surface = round(sum((getattr(p, "contenance_m2", None) or p.surface_m2 or 0) for p in parcels))
    par_parcelle: dict[int, float] = {}
    # CHASSE-FIX-1 (B-2 / CH-B-M2) — règle SDP-UNIQUE : comme la fiche, l'assemblage part de la SDP
    # BÂTI CONSERVÉ (résiduelle = capacité max − bâti existant déjà debout), jamais la SDP brute (qui
    # suppose une table rase non dite). On collecte donc le bâti existant et la résiduelle PAR PARCELLE
    # (même source que la fiche : `residuel` de `fiche_payload`) pour dériver la conservation à l'union.
    existante_par: dict[int, float | None] = {}
    residuelle_par: dict[int, float | None] = {}
    conserve_estimation = False
    zones: list[tuple[str | None, str | None]] = []
    for p in parcels:
        try:
            fa = fiche_payload(session, p.id)
        except Exception:  # noqa: BLE001 — une parcelle illisible ne casse pas l'étude
            fa = None
        fr = (fa or {}).get("fourchette") or {}
        par_parcelle[p.id] = round(fr.get("surface_plancher_m2") or 0)
        res = (fa or {}).get("residuel") or {}
        if res.get("disponible") is not False and res.get("sdp_existante_m2") is not None:
            existante_par[p.id] = round(float(res.get("sdp_existante_m2") or 0))
            residuelle_par[p.id] = round(float(res.get("sdp_residuelle_m2") or 0))
            conserve_estimation = conserve_estimation or bool(res.get("estimation_sdp"))
        else:
            existante_par[p.id] = None     # bâti existant inconnu → conservation incertaine, on le dira
            residuelle_par[p.id] = None
            conserve_estimation = True
        zones.append((getattr(p, "commune", None), (fa or {}).get("zone")))
    sdp_existante_totale = round(sum(v for v in existante_par.values() if v))
    u = _capacite_union(session, parcels)
    if not u:
        return {"surface_cumulee_m2": surface, "sdp_m2": 0, "ca": None,
                "charge_fonciere": None, "n_chiffrables": 0, "sdp_par_parcelle": par_parcelle,
                "sdp_terrain_libere_m2": 0, "sdp_bati_conserve_m2": 0,
                "sdp_existante_totale_m2": sdp_existante_totale,
                "sdp_residuelle_par_parcelle": residuelle_par, "sdp_existante_par_parcelle": existante_par,
                "conserve_estimation": conserve_estimation,
                "zones": zones, "assiette": "aucune", "emprise_union_m2": None}
    # SDP terrain libéré = capacité BRUTE de l'union (table rase du bâti) ; SDP bâti conservé = ce qui
    # reste constructible en GARDANT le bâti existant (= brute − bâti existant total), comme la fiche.
    sdp_libere = u["sdp_m2"]
    sdp_conserve = max(0, sdp_libere - sdp_existante_totale)
    cf = u["charge_fonciere"]
    cf_out = ({**cf, "par_m2_terrain": round(cf["central"] / surface)} if cf and surface else cf)
    # OUTILS-P1-1 LOT3d (pt 1) — « dont N m² en zone constructible · X % hors zone » : les DEUX chiffres
    # décomposent le MÊME total affiché (surface cumulée) via la part constructible → ils s'additionnent à
    # 100 %. Avant, la surface constructible (union DESSINÉE × part) et le % (géométrie INSETÉE) sortaient
    # de deux bases ≠ de la surface cumulée (contenance) : 1 689 / 2 630 ≠ 1 − 31 %.
    part_c = u.get("part_constructible")
    if part_c is not None and surface:
        surf_constr_aff = round(surface * part_c)
        pct_hz_aff = max(0, min(100, round(100.0 * (1.0 - part_c))))
    else:
        surf_constr_aff = u.get("surface_constructible_m2")
        pct_hz_aff = u.get("pct_hors_zone")
    return {
        "surface_cumulee_m2": surface,
        # NU-G-007 — surface d'assiette EN ZONE CONSTRUCTIBLE + part hors zone (alignés sur l'Étude du
        # même assemblage) : la SDP cumulée est bornée à cette part, le % hors zone est DIT.
        "surface_constructible_m2": surf_constr_aff,
        "pct_hors_zone": pct_hz_aff,
        "sdp_m2": u["sdp_m2"],   # BRUTE de l'union (back-compat) = SDP terrain libéré
        # CHASSE-FIX-1 (B-2) — les deux grandeurs SDP-UNIQUE : conservé (défaut) et terrain libéré.
        "sdp_terrain_libere_m2": sdp_libere,
        "sdp_bati_conserve_m2": sdp_conserve,
        "sdp_existante_totale_m2": sdp_existante_totale,
        "sdp_residuelle_par_parcelle": residuelle_par,
        "sdp_existante_par_parcelle": existante_par,
        "conserve_estimation": conserve_estimation,
        "ca": u["ca"],
        "prix_sortie_eur_m2": u.get("prix_sortie_eur_m2"),   # RETOURS-25 (pt 1) — Bilan Assemblage
        "charge_fonciere": cf_out,
        "n_chiffrables": 1 if u["ca"] else 0,
        "sdp_par_parcelle": par_parcelle,
        "zones": zones,
        # LOT 2 — décomposition PAR ZONE (règles propres à chaque portion) + contraintes retranchées
        # visibles (hors zone, zone rouge, emplacement réservé, EBC — en m²).
        "zones_detail": u.get("zones_detail"),
        "retranchements": u.get("retranchements"),
        # OUTIL-ASSEMBLAGE-FIX-2 (LOT 1) — obligation de mixité portée par le bilan de l'union.
        "mixite": u.get("mixite"),
        "assiette": "union",
        "emprise_union_m2": u["emprise_m2"],
    }
