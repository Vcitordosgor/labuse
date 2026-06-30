"""Intégration base : résout le contexte d'une parcelle (surface, zone PLU,
contraintes réunionnaises) et lance le moteur. Lecture seule ; aucune écriture,
aucune dépendance à la cascade/scoring (seuls les PARAMS de config/cascade_rules.yaml
sont relus pour partager les seuils — préfixes U/AU, typepsc ER/mixité/eaux).

Le code de sous-zone vient de spatial_layers.name (ex. 'U1c', 'Usdu') pour les
couches PLU ; la surface de ST_Area(geom_2975) (métrique) ; les contraintes des
couches pente / trait_de_cote / safer déjà ingérées.

DÉCISIONS 1 & 3 (directive post-1.A) appliquées ICI, sur la géométrie réelle :
- zonage mixte → l'emprise insetée est CLIPPÉE à la portion U/AU (ST_Intersection) ;
- emplacements réservés → leur surface est DÉDUITE de l'emprise constructible,
  avec la mention « ER {num} : {libellé} — {m²} déduits » dans la modulation ;
- mixité sociale / eaux pluviales → détectées et passées au bilan (Décisions 3.b/3.c).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import config
from .engine import Contraintes, Faisabilite, estimate_capacity
from .plu_rules import resolve_zone

_CTX = text("""
SELECT p.idu, p.commune,
       ST_Area(p.geom_2975)                               AS surface_m2,
       (SELECT COALESCE(z.attrs->>'libelle', z.subtype, z.name) FROM spatial_layers z
          WHERE z.commune = p.commune AND z.kind ILIKE '%plu%'
            AND z.kind NOT ILIKE '%prescription%'  -- les prescriptions (1.B) ne sont PAS des zones
            AND ST_Contains(z.geom, p.centroid)
          ORDER BY ST_Area(z.geom) ASC LIMIT 1)           AS zone,
       (SELECT max((pl.attrs->>'slope_pct')::float) FROM spatial_layers pl
          WHERE pl.commune = p.commune AND pl.kind = 'pente'
            AND ST_Intersects(pl.geom_2975, p.geom_2975))  AS pente_pct,
       EXISTS(SELECT 1 FROM spatial_layers t
          WHERE t.commune = p.commune AND t.kind = 'trait_de_cote'
            AND t.subtype IN ('bande_courte','bande_longue')
            AND ST_Intersects(t.geom_2975, p.geom_2975))    AS littoral,
       EXISTS(SELECT 1 FROM spatial_layers a
          WHERE a.commune = p.commune AND a.kind = 'safer'
            AND ST_Intersects(a.geom_2975, p.geom_2975))     AS safer
FROM parcels p
WHERE p.id = :pid
""")


@dataclass
class ParcelContext:
    parcel_id: int
    idu: str
    commune: str
    surface_m2: float
    zone: str | None
    contraintes: Contraintes
    # Prescriptions à effet économique (mixité sociale, eaux pluviales) + ER déduits,
    # renseignées par parcel_faisabilite() pour alimenter badges fiche et bilan.
    prescriptions_eco: dict = field(default_factory=dict)


def _layer_params(name: str) -> dict:
    """Params d'une couche de config/cascade_rules.yaml (source UNIQUE des seuils/typepsc)."""
    for lc in config.cascade_rules().get("layers", []):
        if lc.get("name") == name:
            return lc.get("params", {}) or {}
    return {}


# Emprise insetée (reculs), puis clippée à la portion U/AU (Décision 1 — zonage mixte),
# puis amputée de l'union des emplacements réservés (Décision 3.a). Tout en EPSG:2975.
_EMPRISE = text("""
WITH p AS (SELECT commune, geom_2975 AS g, ST_Buffer(geom_2975, -:d) AS b
           FROM parcels WHERE id = :pid),
uau AS (SELECT ST_Union(z.geom_2975) AS u
        FROM spatial_layers z, p
        WHERE z.kind = :zkind AND z.commune = p.commune
          AND z.name ILIKE ANY(:uau_pats) AND ST_Intersects(z.geom_2975, p.g)),
er AS (SELECT ST_Union(e.geom_2975) AS u
       FROM spatial_layers e, p
       WHERE e.kind = :pkind AND e.commune = p.commune
         AND e.subtype = ANY(:er_types) AND ST_Intersects(e.geom_2975, p.g))
SELECT ST_Area(p.b) AS full_area,
       CASE WHEN uau.u IS NULL THEN NULL
            ELSE ST_Area(ST_Intersection(p.b, uau.u)) END AS uau_area,
       CASE WHEN er.u IS NULL THEN 0.0
            ELSE ST_Area(ST_Intersection(
                   CASE WHEN uau.u IS NULL THEN p.b ELSE ST_Intersection(p.b, uau.u) END,
                   er.u)) END AS er_area
FROM p LEFT JOIN uau ON TRUE LEFT JOIN er ON TRUE
""")

_ER_DETAILS = text("""
SELECT coalesce(e.attrs->>'txt', e.name)     AS txt,
       coalesce(e.attrs->>'libelle', e.name) AS libelle,
       ST_Area(ST_Intersection(ST_Buffer(p.geom_2975, -:d), e.geom_2975)) AS m2
FROM parcels p
JOIN spatial_layers e ON e.kind = :pkind AND e.commune = p.commune
  AND e.subtype = ANY(:er_types) AND ST_Intersects(e.geom_2975, p.geom_2975)
WHERE p.id = :pid ORDER BY m2 DESC
""")

_ECO = text("""
SELECT e.subtype, max(coalesce(e.attrs->>'libelle', e.name)) AS libelle
FROM parcels p
JOIN spatial_layers e ON e.kind = :pkind AND e.commune = p.commune
  AND e.subtype = ANY(:types) AND ST_Intersects(e.geom_2975, p.geom_2975)
WHERE p.id = :pid GROUP BY e.subtype
""")

_ER_LIB = re.compile(r"^ER\s*(\S+)\s*[-–—:]\s*(.+)$", re.IGNORECASE)


def parcel_context(session: Session, parcel_id: int) -> ParcelContext | None:
    r = session.execute(_CTX, {"pid": parcel_id}).one_or_none()
    if r is None:
        return None
    libelles = []
    c = Contraintes(
        pente_pct=float(r.pente_pct) if r.pente_pct is not None else None,
        bande_littorale=bool(r.littoral),
        agricole_sar=bool(r.safer),
        libelles=libelles,
    )
    if r.safer:
        libelles.append("Parcelle en périmètre SAFER (préemption agricole possible).")
    return ParcelContext(parcel_id, r.idu, r.commune, float(r.surface_m2), r.zone, c)


# ── Hauteur PROSPECT (Ud/Uu) : L≥H, L = largeur de la voie desservante (BD TOPO) ──
_FACADE_SEUIL_M = 25.0          # seuil de desserte (cohérent cascade_rules direct_access_m=25)
# Largeur par défaut quand la chaussée BD TOPO n'a pas de largeur exploitable (≈28 % des
# tronçons). Sentier/Escalier/Rond-point = pas une desserte habitée → None. Faible enjeu
# (le plancher 10 m de _prospect_hauteur écrase presque tout sauf les avenues larges).
_CLASSE_LARGEUR = {
    "Route à 2 chaussées": 14.0,
    "Route à 1 chaussée": 6.0,
    "Route empierrée": 4.0,
    "Chemin": 4.0,
}

_FACADE_SQL = text("""
    SELECT (s.attrs->>'largeur')::float AS largeur, s.subtype AS nature
    FROM parcels p JOIN spatial_layers s
      ON s.commune = :c AND s.kind = 'voirie'
         AND ST_DWithin(p.geom_2975, s.geom_2975, :seuil)
    WHERE p.id = :pid
""")


def _facade_largeur(session: Session, parcel_id: int, commune: str) -> tuple[float | None, str]:
    """Largeur de la voie DESSERVANT la parcelle, pour la hauteur prospect.

    Parmi les tronçons de voirie à ≤ 25 m (ST_DWithin), retient la LARGEUR LA PLUS GRANDE
    (favorise l'avenue desservante en cas de multi-façades). Largeur réelle BD TOPO si
    présente ET > 0 (« reel ») ; sinon défaut par classe de voie (« classe ») ; sinon, si
    aucune voie desservante exploitable, (None, « aucune »). NB : largeur ≤ 0 = dégénérée
    BD TOPO → traitée comme absente (fallback)."""
    best: tuple[float, str] | None = None
    for largeur, nature in session.execute(
            _FACADE_SQL, {"pid": parcel_id, "c": commune, "seuil": _FACADE_SEUIL_M}).all():
        if largeur is not None and largeur > 0:
            cand: tuple[float, str] | None = (float(largeur), "reel")
        else:
            d = _CLASSE_LARGEUR.get(nature)
            cand = (float(d), "classe") if d else None
        if cand and (best is None or cand[0] > best[0]):
            best = cand
    return best if best is not None else (None, "aucune")


def _prospect_hauteur(largeur_m: float | None) -> float:
    """Hauteur prospect L≥H : L = max(largeur de chaussée desservante, plancher 10 m)
    (« si l'emprise de la voie est inférieure à 10 m → ligne à 10 m », règlement Ud/Uu).
    Fonction PURE (sans base) — verrouillée par test."""
    return max(float(largeur_m or 0.0), 10.0)


def parcel_faisabilite(session: Session, parcel_id: int) -> tuple[ParcelContext, Faisabilite] | None:
    """Contexte + pré-faisabilité d'une parcelle, EMPRISE SUR GÉOMÉTRIE RÉELLE
    (ST_Buffer du contour cadastral par le recul séparatif, EPSG:2975), clippée à la
    portion U/AU si zonage mixte (Décision 1) et amputée des emplacements réservés
    (Décision 3.a). None si parcelle/zone introuvable."""
    from .engine import Hypotheses

    ctx = parcel_context(session, parcel_id)
    if ctx is None or not ctx.zone:
        return None
    rules = resolve_zone(ctx.zone, ctx.commune)
    if rules is None:
        return None

    hyp = Hypotheses.charger()
    recul = (float(rules.recul_limites_sep_m)
             if isinstance(rules.recul_limites_sep_m, (int, float))
             else hyp.recul_limites_defaut_m)

    zonage = _layer_params("zonage_plu_gpu")
    presc = _layer_params("prescription_plu")
    pkind = presc.get("spatial_kind", "plu_gpu_prescription")
    er_types = [str(t) for t in presc.get("emplacement_reserve_typepsc", ["05"])]
    args = {"pid": parcel_id, "d": recul,
            "zkind": zonage.get("spatial_kind", "plu_gpu_zone"),
            "uau_pats": [f"{p}%" for p in zonage.get("positive_prefixes", ["U", "AU"])],
            "pkind": pkind, "er_types": er_types}
    row = session.execute(_EMPRISE, args).one()
    full_a = float(row.full_area or 0.0)
    uau_a = float(row.uau_area) if row.uau_area is not None else None
    er_a = float(row.er_area or 0.0)

    base = full_a if uau_a is None else min(full_a, uau_a)
    plancher = float(zonage.get("an_mixte_min_pct", 5)) / 100.0
    if uau_a is not None and full_a > 0 and (full_a - base) / full_a >= plancher:
        ctx.contraintes.libelles.append(
            f"Zonage mixte : emprise constructible clippée à la portion U/AU "
            f"(~{base:.0f} m² retenus sur ~{full_a:.0f} m² insetés).")

    if er_a >= 0.5:
        for r in session.execute(_ER_DETAILS, {"pid": parcel_id, "d": recul,
                                               "pkind": pkind, "er_types": er_types}):
            m2 = float(r.m2 or 0.0)
            if m2 < 0.5:
                continue
            m = _ER_LIB.match((r.libelle or "").strip())
            label = f"ER {m.group(1)} : {m.group(2).strip()}" if m else \
                (f"{r.txt} : {r.libelle}" if r.txt and r.txt != r.libelle else (r.libelle or "ER"))
            ctx.contraintes.libelles.append(
                f"{label} — {m2:.0f} m² déduits de l'emprise constructible.")
    emprise = max(0.0, base - er_a)

    eco_types = ([str(t) for t in presc.get("mixite_sociale_typepsc", [])]
                 + [str(t) for t in presc.get("eaux_pluviales_typepsc", [])])
    mixite_set = {str(t) for t in presc.get("mixite_sociale_typepsc", [])}
    eco: dict = {"er_deduit_m2": round(er_a)}
    if eco_types:
        for r in session.execute(_ECO, {"pid": parcel_id, "pkind": pkind, "types": eco_types}):
            if r.subtype in mixite_set:
                eco["mixite"], eco["mixite_libelle"] = True, r.libelle
            else:
                eco["pluvial"], eco["pluvial_libelle"] = True, r.libelle
    ctx.prescriptions_eco = eco

    return ctx, estimate_capacity(rules, ctx.surface_m2, ctx.contraintes, hyp=hyp,
                                  emprise_geo=(emprise, recul))


# 3.D — Empreintes pour le gabarit 3D : parcelle + emprise insetée du recul, RECENTRÉES sur le
# centroïde (mètres locaux EPSG:2975) → le front projette en axonométrie sans dépendance 3D.
_VOLUME_GEOM = text("""
WITH p AS (SELECT geom_2975 AS g, ST_Centroid(geom_2975) AS c FROM parcels WHERE id = :pid)
SELECT ST_AsGeoJSON(ST_Translate(p.g, -ST_X(p.c), -ST_Y(p.c)), 2) AS outline,
       ST_AsGeoJSON(ST_Translate(ST_Buffer(p.g, -:d), -ST_X(p.c), -ST_Y(p.c)), 2) AS emprise
FROM p
""")


def _ring_local(gj: str | None) -> list[list[float]] | None:
    """Anneau extérieur d'un polygone GeoJSON → liste [x,y] (sans le point de fermeture)."""
    if not gj:
        return None
    try:
        coords = (json.loads(gj).get("coordinates") or [])
    except (ValueError, AttributeError):
        return None
    if not coords or not coords[0]:
        return None
    ring = [[round(float(x), 2), round(float(y), 2)] for x, y in coords[0]]
    if len(ring) >= 2 and ring[0] == ring[-1]:
        ring = ring[:-1]
    return ring if len(ring) >= 3 else None


def volume3d_payload(session: Session, parcel_id: int,
                     fais: tuple[ParcelContext, Faisabilite] | None = None) -> dict | None:
    """3.D — Gabarit constructible 3D (v1 : extrusion simple). Empreinte = emprise constructible
    insetée du recul (mètres locaux) ; hauteur = niveaux × hauteur d'étage de la capacité DÉJÀ
    calculée. Volume = emprise × hauteur. Indicatif (ni architecture ni implantation réelle)."""
    res = fais or parcel_faisabilite(session, parcel_id)
    if res is None:
        return None
    ctx, f = res
    fr = f.fourchette or {}
    if not f.constructible:
        return {"constructible": False,
                "note": "Parcelle non constructible — aucun gabarit à extruder."}

    from .engine import Hypotheses
    rules = resolve_zone(ctx.zone, ctx.commune) if ctx.zone else None
    hyp = Hypotheses.charger()
    recul = (float(rules.recul_limites_sep_m)
             if rules is not None and isinstance(rules.recul_limites_sep_m, (int, float))
             else hyp.recul_limites_defaut_m)
    row = session.execute(_VOLUME_GEOM, {"pid": parcel_id, "d": recul}).one()
    outline = _ring_local(row.outline)
    if not outline:
        return None
    hauteur, emprise_m2 = fr.get("hauteur_m"), fr.get("emprise_constructible_m2")
    return {
        "constructible": True,
        "outline": outline,                       # parcelle (mètres locaux, centroïde = origine)
        "emprise": _ring_local(row.emprise),      # emprise constructible insetée (peut être None si exiguë)
        "hauteur_m": hauteur,
        "etage_m": fr.get("hauteur_etage_m"),
        "niveaux": fr.get("niveaux"),
        "niveaux_max": fr.get("niveaux_max"),
        "emprise_constructible_m2": emprise_m2,
        "emprise_batie_max_m2": fr.get("emprise_batie_max_m2"),
        "surface_plancher_m2": fr.get("surface_plancher_m2"),
        "volume_m3": round((emprise_m2 or 0) * (hauteur or 0)),   # ← recette : emprise × hauteur
        "recul_m": recul,
        "note": "Gabarit-enveloppe indicatif : emprise constructible insetée du recul, extrudée à "
                "la hauteur PLU (niveaux × étage). Ni architecture ni implantation réelle.",
    }


def fiche_payload(session: Session, parcel_id: int) -> dict | None:
    """Payload JSON de la carte de faisabilité pour la fiche parcelle.
    None si la parcelle n'est pas couverte (zone hors PLU Saint-Paul outillé)."""
    res = parcel_faisabilite(session, parcel_id)
    if res is None:
        return None
    ctx, f = res
    c = ctx.contraintes

    # Potentiel résiduel (Lot B) — réutilise la faisabilité déjà calculée ; isolé/défensif.
    residuel = None
    try:
        from .residuel import compute_residuel
        residuel = compute_residuel(session, parcel_id, faisa=res)
    except Exception:  # noqa: BLE001 - n'empêche jamais la fiche
        residuel = None

    # Bilan promoteur (PARTIE 1) — uniquement si constructible ; isolé/défensif.
    bilan = None
    try:
        from . import bilan_params as bpmod
        from .bilan import compute_bilan, sector_price
        from .engine import Hypotheses
        if f.constructible:
            hyp = Hypotheses.charger()
            # Programme estimé → déclenchement de la clause de mixité (seuils Art. 2).
            fr = f.fourchette
            logements_est = max((fr.get("logements_au_sol") or (0, 0))[1],
                                (fr.get("logements_sous_sol") or (0, 0))[1])
            vue_mer = session.execute(text(
                "SELECT vue FROM parcel_vue_mer WHERE parcel_id = :p"), {"p": parcel_id}).scalar()
            ctx.prescriptions_eco.update({
                "sdp_max_m2": fr.get("surface_plancher_m2"),
                "logements_estimes": logements_est,
                "terrain_m2": ctx.surface_m2,
                "pente_pct": ctx.contraintes.pente_pct,   # 2.A — alimente la majoration VRD pente
                "vue_mer": vue_mer,                        # 2.B — bonus prix si 'oui' (depuis le cache)
            })
            # 1.C — secteur = bassin PLU de la zone ; params résolus (défaut ← global ← secteur).
            secteur = None
            rules = resolve_zone(ctx.zone, ctx.commune) if ctx.zone else None
            secteur = (rules.bassin if rules else None) or "Saint-Paul"
            resolved = bpmod.resolve(session, secteur)
            bp_values = {k: r["value"] for k, r in resolved.items()}
            b = compute_bilan(fr.get("shab_vendable_m2", 0), ctx.surface_m2,
                              sector_price(session, ctx.parcel_id, hyp), hyp,
                              contexte_eco=ctx.prescriptions_eco, bilan_params=bp_values)
            bilan = {
                "fiable": b.fiable, "fiabilite": b.fiabilite, "verdict": b.verdict,
                "prix_dvf": b.prix_dvf, "comparables": (b.prix_dvf or {}).get("comparables"),
                "ca": b.ca, "charge_fonciere": b.charge_fonciere,
                "steps": [{"label": s.label, "formule": s.formule, "valeur": s.valeur,
                           "source": s.source, "prov": s.prov} for s in b.steps],
                "hypotheses": b.hypotheses, "avertissements": b.avertissements, "bandeau": b.bandeau,
                "calc": b.calc,
                # 1.C — secteur + paramètres éditables (registre + valeurs résolues) + non calibrés.
                "secteur": secteur,
                "params": [{**p, **resolved.get(p["key"], {})} for p in bpmod.registry()],
                "non_calibres_critiques": bpmod.uncalibrated_critical(resolved),
                "estimes_a_affiner": bpmod.estimated_to_refine(resolved),
            }
    except Exception:  # noqa: BLE001 - le bilan ne casse jamais la fiche
        bilan = None

    # 3.D — gabarit 3D (extrusion emprise × hauteur) ; isolé/défensif, jamais bloquant.
    volume3d = None
    try:
        volume3d = volume3d_payload(session, parcel_id, fais=res)
    except Exception:  # noqa: BLE001 - le 3D ne casse jamais la fiche
        volume3d = None

    return {
        "zone": f.zone,
        "zone_resolue": f.zone_resolue,
        "surface_m2": round(ctx.surface_m2),
        "constructible": f.constructible,
        "verdict": f.verdict,
        "fourchette": f.fourchette,
        "contexte": {
            "pente_pct": round(c.pente_pct) if c.pente_pct is not None else None,
            "littoral": c.bande_littorale,
            "safer": c.agricole_sar,
        },
        "steps": [{"label": s.label, "formule": s.formule, "valeur": s.valeur,
                   "source": s.source, "prov": s.prov} for s in f.steps],
        "hypotheses": f.hypotheses,
        "avertissements": f.avertissements,
        "modulation": f.modulation,
        "bandeau": f.bandeau,
        "bilan": bilan,
        "residuel": residuel,   # Lot B — potentiel résiduel (bâti existant × capacité max)
        "volume3d": volume3d,   # 3.D — gabarit constructible 3D (extrusion emprise × hauteur)
        # Badges fiche (Décisions 2/3) : mixité sociale, eaux pluviales, ER déduits.
        "prescriptions_eco": {
            "mixite_sociale": (ctx.prescriptions_eco.get("mixite_libelle") or "Clause logements aidés")
                              if ctx.prescriptions_eco.get("mixite") else None,
            "eaux_pluviales": (ctx.prescriptions_eco.get("pluvial_libelle") or "zonage eaux pluviales")
                              if ctx.prescriptions_eco.get("pluvial") else None,
            "er_deduit_m2": ctx.prescriptions_eco.get("er_deduit_m2") or 0,
        },
    }
