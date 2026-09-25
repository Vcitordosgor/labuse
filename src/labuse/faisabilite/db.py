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
from dataclasses import dataclass, field, replace

from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import config
from .engine import Contraintes, Faisabilite, estimate_capacity
from .zonage import resolve_zone
from .zone_servie import FAMILLES_CONSTRUCTIBLES

_CTX = text("""
SELECT p.idu, p.commune,
       ST_Area(p.geom_2975)                               AS surface_m2,
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
    # ZONE-1 : zone DOMINANTE PAR SURFACE (la même que l'écran, cf. zone_servie.zone_dominante)
    # + drapeau « à cheval » quand aucune zone n'atteint 90 % — parts servies au bilan/fiche.
    zone_fam: str | None = None
    a_cheval: bool = False
    zone_parts: list = field(default_factory=list)


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
-- EXIGU-GRANDES : les zones AU NUMÉROTÉES (name '1AUb'/'2AUc'/'3AU5st'…) portent leur code GPU
-- normalisé dans `subtype` ('AUc'…) et commencent par un chiffre dans `name` — elles n'ont JAMAIS
-- matché `name ILIKE 'AU%'`, ce qui vidait leur assiette constructible (terrain_exigu à tort sur
-- de grandes parcelles à urbaniser). On les rattrape via `subtype` UNIQUEMENT quand `name` est
-- numérique (périmètre borné : les zones à `name` littéral — 8 communes — gardent leur
-- comportement, bug distinct plus large, hors de ce correctif).
uau AS (SELECT ST_Union(z.geom_2975) AS u
        FROM spatial_layers z, p
        WHERE z.kind = :zkind AND z.commune = p.commune
          AND (z.name ILIKE ANY(:uau_pats)
               OR (z.name ~ '^[0-9]' AND z.subtype ILIKE ANY(:uau_pats)))
          AND ST_Intersects(z.geom_2975, p.g)),
er AS (SELECT ST_Union(e.geom_2975) AS u
       FROM spatial_layers e, p
       WHERE e.kind = :pkind AND e.commune = p.commune
         AND e.subtype = ANY(:er_types) AND ST_Intersects(e.geom_2975, p.g)),
-- SOURCES-1 lot 1 : la part EBC est SOUSTRAITE de l'assiette (L113-1 CU — emprise boisée
-- inconstructible). Union ER+EBC pour la soustraction (jamais de double-compte au chevauchement).
ebc AS (SELECT ST_Union(e.geom_2975) AS u
        FROM spatial_layers e, p
        WHERE e.kind = :pkind AND e.commune = p.commune
          AND e.subtype = ANY(:ebc_types) AND ST_Intersects(e.geom_2975, p.g))
SELECT ST_Area(p.b) AS full_area,
       CASE WHEN uau.u IS NULL THEN NULL
            ELSE ST_Area(ST_Intersection(p.b, uau.u)) END AS uau_area,
       CASE WHEN er.u IS NULL THEN 0.0
            ELSE ST_Area(ST_Intersection(
                   CASE WHEN uau.u IS NULL THEN p.b ELSE ST_Intersection(p.b, uau.u) END,
                   er.u)) END AS er_area,
       CASE WHEN ebc.u IS NULL THEN 0.0
            ELSE ST_Area(ST_Intersection(
                   CASE WHEN uau.u IS NULL THEN p.b ELSE ST_Intersection(p.b, uau.u) END,
                   ebc.u)) END AS ebc_area,
       CASE WHEN er.u IS NULL AND ebc.u IS NULL THEN 0.0
            ELSE ST_Area(ST_Intersection(
                   CASE WHEN uau.u IS NULL THEN p.b ELSE ST_Intersection(p.b, uau.u) END,
                   ST_Union(COALESCE(er.u, ST_GeomFromText('GEOMETRYCOLLECTION EMPTY', 2975)),
                            COALESCE(ebc.u, ST_GeomFromText('GEOMETRYCOLLECTION EMPTY', 2975)))))
       END AS greve_area
FROM p LEFT JOIN uau ON TRUE LEFT JOIN er ON TRUE LEFT JOIN ebc ON TRUE
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

# GEOMETRIE-1 lot B — même listing ER, mesuré sur l'ASSIETTE GABARIT (jamais un m² d'un autre
# contour que celui réellement déduit).
_ER_DETAILS_ASSIETTE = text("""
WITH a AS (SELECT ST_MakeValid(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326), 2975)) AS g)
SELECT coalesce(e.attrs->>'txt', e.name)     AS txt,
       coalesce(e.attrs->>'libelle', e.name) AS libelle,
       ST_Area(ST_Intersection(a.g, ST_MakeValid(ST_ClipByBox2D(e.geom_2975, a.g)))) AS m2
FROM parcels p CROSS JOIN a
JOIN spatial_layers e ON e.kind = :pkind AND e.commune = p.commune
  AND e.subtype = ANY(:er_types) AND ST_Intersects(e.geom_2975, a.g)
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
        libelles.append("Parcelle déclarée agricole au RPG (usage agricole).")
    # ZONE-1 : la zone vient de LA résolution unique (dominante par surface, la même que
    # l'écran) — plus jamais de la zone du centroïde (deux vérités, verdicts en miroir sur
    # les parcelles à cheval — audit EXPORTS A3/transverse).
    from .zone_servie import zone_dominante
    zs = zone_dominante(session, parcel_id)
    return ParcelContext(parcel_id, r.idu, r.commune, float(r.surface_m2), zs.zone, c,
                         zone_fam=zs.zone_fam, a_cheval=zs.a_cheval, zone_parts=zs.parts)


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


# SCORING-6 lot A — assiette clippée. Union des CONTRAINTES GÉOMÉTRIQUES CERTAINES (au-delà des
# ER/EBC déjà soustraits par `_EMPRISE`) grevant la portion U/AU insetée : PPR zone rouge
# (INTERDICTION), PEB A/B (L112-10 interdit l'habitat neuf), marchepied DPF (3,25 m), abord de
# ravine (buffer), 50 pas géométriques. Les seuils viennent de la MÊME source que la cascade
# (cascade_rules.yaml) — jamais un nombre en double. La greve est intersectée avec la portion
# U/AU (assiette réelle) pour ne jamais soustraire hors de l'emprise constructible.
#
# RESIDUEL-VITESSE — ST_ClipByBox2D avant l'intersection fine. Les couches PPR (jusqu'à 320 k
# sommets), PEB, 50 pas et les zones PLU (jusqu'à 90 k sommets) sont d'énormes polygones : les
# intersecter tels quels avec chaque parcelle coûtait ~550 ms/appel (ST_Intersection parcourt
# TOUS les sommets, même pour ne garder qu'un ruban). ST_ClipByBox2D rogne d'abord le polygone à
# la bbox de l'assiette insetée p.b (opération O(bbox), pas O(sommets)), puis ST_MakeValid/ST_Union
# n'opèrent que sur le petit morceau restant. RÉSULTAT STRICTEMENT IDENTIQUE : la bbox de p.b
# contient p.b, l'assiette ⊆ p.b, donc greve ∩ assiette est inchangée (aire égale au bit près,
# écart max 5e-10 m² = bruit flottant, très en-dessous de l'arrondi entier de sdp). Toutes les
# géométries des couches sont VALIDES en base (0 invalide sur l'île) — ST_MakeValid reste par
# sécurité mais s'applique désormais au morceau clippé. dpf/ravine (petits, +buffer) inchangés.
_GREVE_CERTAINE = text("""
WITH p AS (SELECT commune, ST_Buffer(geom_2975, -:d) AS b FROM parcels WHERE id = :pid),
uau AS (SELECT ST_Union(ST_MakeValid(ST_ClipByBox2D(z.geom_2975, p.b))) AS u
        FROM spatial_layers z, p
        WHERE z.kind = :zkind AND z.commune = p.commune
          AND (z.name ILIKE ANY(:uau_pats)
               OR (z.name ~ '^[0-9]' AND z.subtype ILIKE ANY(:uau_pats)))
          AND ST_Intersects(z.geom_2975, p.b)),
assiette AS (SELECT CASE WHEN uau.u IS NULL THEN p.b
                         ELSE ST_Intersection(p.b, uau.u) END AS a
             FROM p LEFT JOIN uau ON TRUE),
greves AS (
    SELECT ST_MakeValid(ST_ClipByBox2D(g.geom_2975, p.b)) AS geom FROM spatial_layers g, p
      WHERE g.kind = 'ppr' AND g.commune = p.commune
        AND g.subtype = ANY(:ppr_red) AND ST_Intersects(g.geom_2975, p.b)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(g.geom_2975, p.b)) FROM spatial_layers g, p
      WHERE g.kind = 'peb' AND lower(g.subtype) = ANY(:peb_ab)
        AND ST_Intersects(g.geom_2975, p.b)
  UNION ALL
    SELECT ST_Buffer(ST_MakeValid(g.geom_2975), :dpf_m) FROM spatial_layers g, p
      WHERE g.kind = 'dpf' AND g.commune = p.commune AND ST_DWithin(g.geom_2975, p.b, :dpf_m)
  UNION ALL
    SELECT ST_Buffer(ST_MakeValid(g.geom_2975), :rav_m) FROM spatial_layers g, p
      WHERE g.kind = 'ravine' AND g.commune = p.commune AND ST_DWithin(g.geom_2975, p.b, :rav_m)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(g.geom_2975, p.b)) FROM spatial_layers g, p
      WHERE g.kind = 'cinquante_pas' AND g.commune = p.commune AND ST_Intersects(g.geom_2975, p.b)
)
SELECT COALESCE(ST_Area(ST_Intersection(a.a, gg.u)), 0.0) AS greve_m2
FROM assiette a LEFT JOIN (SELECT ST_Union(geom) AS u FROM greves) gg ON TRUE
""")


def _greve_certaine_m2(session: Session, parcel_id: int, recul: float, commune: str | None) -> float:
    """Surface (m²) des contraintes géométriques certaines grevant la portion U/AU insetée
    (SCORING-6 lot A). Seuils lus de cascade_rules.yaml (source unique)."""
    zonage = _layer_params("zonage_plu_gpu")
    risq = _layer_params("risques")
    dpfp = _layer_params("dpf")
    ravp = _layer_params("ravine")
    pebp = _layer_params("peb")
    row = session.execute(_GREVE_CERTAINE, {
        "pid": parcel_id, "d": recul,
        "zkind": zonage.get("spatial_kind", "plu_gpu_zone"),
        "uau_pats": [f"{p}%" for p in zonage.get("positive_prefixes", ["U", "AU"])],
        "ppr_red": [str(s) for s in risq.get("ppr_red_subtypes", ["INTERDICTION"])],
        "peb_ab": [str(z).lower() for z in pebp.get("hard_zones", ["a", "b"])],
        "dpf_m": float(dpfp.get("marchepied_m", 3.25)),
        "rav_m": float(ravp.get("buffer_m", 10)),
    }).scalar()
    return float(row or 0.0)


# GEOMETRIE-1 lot B — UN SEUL moteur de géométrie. L'assiette du calcul de capacité devient la
# ZONE D'IMPLANTATION du gabarit (reculs PAR CÔTÉ voie/séparative, PPR zone rouge DÉCOUPÉE,
# morceau constructible seul si à cheval) — la même fonction que l'outil Gabarit et le tiroir
# de fiche, aucune copie. Les contraintes restantes (ER/EBC, PEB A/B, marchepied DPF, ravine,
# 50 pas) sont soustraites de CETTE assiette — le PPR n'y figure plus (une contrainte, une fois :
# il est déjà découpé de l'assiette ; `_greve_certaine_m2` n'est plus appelée sur ce chemin).
# Seuils lus de cascade_rules.yaml (source unique), comme _GREVE_CERTAINE.
_GREVE_SUR_ASSIETTE = text("""
WITH a AS (SELECT ST_MakeValid(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:gj), 4326), 2975)) AS g),
p AS (SELECT commune FROM parcels WHERE id = :pid),
er AS (SELECT ST_Union(ST_MakeValid(ST_ClipByBox2D(e.geom_2975, a.g))) AS u
       FROM spatial_layers e, p, a
       WHERE e.kind = :pkind AND e.commune = p.commune
         AND e.subtype = ANY(:er_types) AND ST_Intersects(e.geom_2975, a.g)),
ebc AS (SELECT ST_Union(ST_MakeValid(ST_ClipByBox2D(e.geom_2975, a.g))) AS u
        FROM spatial_layers e, p, a
        WHERE e.kind = :pkind AND e.commune = p.commune
          AND e.subtype = ANY(:ebc_types) AND ST_Intersects(e.geom_2975, a.g)),
cert AS (SELECT ST_Union(geom) AS u FROM (
    SELECT ST_MakeValid(ST_ClipByBox2D(g2.geom_2975, a.g)) AS geom FROM spatial_layers g2, a
      WHERE g2.kind = 'peb' AND lower(g2.subtype) = ANY(:peb_ab)
        AND ST_Intersects(g2.geom_2975, a.g)
  UNION ALL
    SELECT ST_Buffer(ST_MakeValid(g2.geom_2975), :dpf_m) FROM spatial_layers g2, p, a
      WHERE g2.kind = 'dpf' AND g2.commune = p.commune AND ST_DWithin(g2.geom_2975, a.g, :dpf_m)
  UNION ALL
    SELECT ST_Buffer(ST_MakeValid(g2.geom_2975), :rav_m) FROM spatial_layers g2, p, a
      WHERE g2.kind = 'ravine' AND g2.commune = p.commune AND ST_DWithin(g2.geom_2975, a.g, :rav_m)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(g2.geom_2975, a.g)) FROM spatial_layers g2, p, a
      WHERE g2.kind = 'cinquante_pas' AND g2.commune = p.commune
        AND ST_Intersects(g2.geom_2975, a.g)
) s)
SELECT COALESCE(ST_Area(ST_Intersection(a.g, er.u)), 0.0)   AS er_area,
       COALESCE(ST_Area(ST_Intersection(a.g, ebc.u)), 0.0)  AS ebc_area,
       COALESCE(ST_Area(ST_Intersection(a.g, cert.u)), 0.0) AS cert_area,
       COALESCE(ST_Area(ST_Intersection(a.g, ST_Union(ST_Union(
           COALESCE(er.u,  ST_GeomFromText('GEOMETRYCOLLECTION EMPTY', 2975)),
           COALESCE(ebc.u, ST_GeomFromText('GEOMETRYCOLLECTION EMPTY', 2975))),
           COALESCE(cert.u, ST_GeomFromText('GEOMETRYCOLLECTION EMPTY', 2975))))), 0.0) AS greve_total
FROM a LEFT JOIN er ON TRUE LEFT JOIN ebc ON TRUE LEFT JOIN cert ON TRUE
""")


def _assiette_gabarit(session: Session, idu: str):
    """GEOMETRIE-1 lot B — zone d'implantation du MOTEUR GABARIT (builder + compute_gabarit),
    servie comme assiette de la capacité. None quand le gabarit ne sert pas la parcelle
    (blocking, 5 causes — le lecteur garde alors son chemin legacy et l'écrit :
    `assiette_source='residuel_legacy'`). Renvoie (BuildResult, GabaritResult)."""
    from ..gabarit.builder import build_gabarit_input
    from ..gabarit.engine import compute_gabarit
    build = build_gabarit_input(session, idu)
    if build is None or build.blocking:
        return None
    res = compute_gabarit(build.input)
    if res.status != "ok":
        return None
    return build, res


def _sous_zone_constructible(ctx: ParcelContext):
    """SCORING-6 lot A — assiette clippée : quand la zone DOMINANTE n'est pas constructible
    (A/N, habitat interdit) mais qu'une portion U/AU subsiste, résout les règles de la plus
    grande sous-zone U/AU. Renvoie les ZoneRules de cette portion (capacité calculée sur la
    portion, au lieu du tout-ou-rien) ou None si aucune portion constructible ne se résout."""
    parts = [p for p in (ctx.zone_parts or []) if p.get("fam") in FAMILLES_CONSTRUCTIBLES]
    for p in sorted(parts, key=lambda x: -float(x.get("pct") or 0)):
        r = resolve_zone(p.get("zone"), ctx.commune)
        if r is not None and r.constructible_neuf and r.habitat != "interdit":
            return r
    return None


def _pct_constructible(ctx: ParcelContext) -> float | None:
    """Part U/AU (%) de la surface — None si la parcelle n'est pas à cheval (une seule zone)."""
    if not ctx.zone_parts:
        return None
    return sum(float(p.get("pct") or 0) for p in ctx.zone_parts
               if p.get("fam") in FAMILLES_CONSTRUCTIBLES)


def parcel_faisabilite(session: Session, parcel_id: int,
                       assiette_clippee: bool = True,
                       hyp_overrides: dict | None = None) -> tuple[ParcelContext, Faisabilite] | None:
    """Contexte + pré-faisabilité d'une parcelle, EMPRISE SUR GÉOMÉTRIE RÉELLE
    (ST_Buffer du contour cadastral par le recul séparatif, EPSG:2975), clippée à la
    portion U/AU si zonage mixte (Décision 1) et amputée des emplacements réservés
    (Décision 3.a). None si parcelle/zone introuvable.

    FAISABILITE-clip (Vic 24/09/2026) — `assiette_clippee=True` PAR DÉFAUT : le moteur LIVE
    (fiche §capacité, outil Faisabilité, bilan, potentiel) calcule sur l'assiette CLIPPÉE, comme
    le RUN RÉSIDUEL SERVI (run 8, `--assiette-clippee`). Sur une parcelle A/N à cheval, la zone
    dominante non constructible n'annule plus la portion U/AU : la capacité est celle de la portion.
    (Le calcul d'un RUN reste piloté par le flag explicite de `compute_residuel_batch` — inchangé.)"""
    from .engine import Hypotheses

    ctx = parcel_context(session, parcel_id)
    if ctx is None or not ctx.zone:
        return None
    rules = resolve_zone(ctx.zone, ctx.commune)
    # SCORING-6 lot A — assiette clippée : si la zone DOMINANTE n'est pas constructible mais
    # qu'une portion U/AU subsiste, on résout la sous-zone U/AU et on calcule la capacité sur
    # cette portion (fini le tout-ou-rien). Chemin OPT-IN — servi inchangé quand désactivé.
    if assiette_clippee and (rules is None or not rules.constructible_neuf
                             or rules.habitat == "interdit"):
        alt = _sous_zone_constructible(ctx)
        if alt is not None:
            rules = alt
            ctx.contraintes.libelles.append(
                f"Zone dominante « {ctx.zone} » non constructible — capacité calculée sur la "
                f"portion U/AU (sous-zone « {alt.code} »), assiette clippée.")
    if rules is None:
        return None
    # PROSPECT (Ud/Uu) : hauteur PAR PARCELLE = L≥H, L = max(largeur voie desservante, 10 m).
    # Copie par-parcelle (dataclasses.replace) — la règle de zone partagée n'est JAMAIS mutée.
    if rules.hauteur_mode == 'prospect':
        largeur, src = _facade_largeur(session, parcel_id, ctx.commune)
        L = _prospect_hauteur(largeur)
        rules = replace(rules, hf_m=L, calibree=True,
                        notes=[*rules.notes,
                               f"Hauteur prospect L≥H = {L:.0f} m (largeur chaussée BD TOPO : {src})"])

    hyp = Hypotheses.charger(ctx.commune)   # M-N P1-13 : hypothèses de la commune
    # FAISABILITE-1 (lot D) — surcharges d'hypothèses (édition « et si… » de l'utilisateur, jamais
    # persistées en base : portées par le projet côté front). Seules les hypothèses Estimé/Dérivé
    # numériques et bornées sont acceptées ; toute autre clé est ignorée (jamais un calcul détourné).
    if hyp_overrides:
        from .engine import appliquer_overrides_hypotheses
        appliquer_overrides_hypotheses(hyp, hyp_overrides)
    recul = (float(rules.recul_limites_sep_m)
             if isinstance(rules.recul_limites_sep_m, (int, float))
             else hyp.recul_limites_defaut_m)

    zonage = _layer_params("zonage_plu_gpu")
    presc = _layer_params("prescription_plu")
    pkind = presc.get("spatial_kind", "plu_gpu_prescription")
    er_types = [str(t) for t in presc.get("emplacement_reserve_typepsc", ["05"])]
    ebc_types = [str(t) for t in presc.get("boise_classe_typepsc", ["01"])]
    args = {"pid": parcel_id, "d": recul,
            "zkind": zonage.get("spatial_kind", "plu_gpu_zone"),
            "uau_pats": [f"{p}%" for p in zonage.get("positive_prefixes", ["U", "AU"])],
            "pkind": pkind, "er_types": er_types, "ebc_types": ebc_types}
    # GEOMETRIE-1 lot B — UN SEUL moteur de géométrie (décision Vic 24/09) : l'assiette est la
    # ZONE D'IMPLANTATION du gabarit (reculs par côté, PPR rouge découpé, morceau constructible
    # si à cheval) quand le gabarit sert la parcelle ; sinon chemin legacy inchangé, et la
    # provenance est ÉCRITE (`assiette_source`) — pas de trou, pas de mensonge.
    gab = _assiette_gabarit(session, ctx.idu) if assiette_clippee else None
    assiette_source = "gabarit" if gab is not None else "residuel_legacy"
    if gab is not None:
        gbuild, gres = gab
        emprise_brute = float(gres.zoneImplantationM2 or 0.0)
        er_a = ebc_a = greve_cert = greve_tot = 0.0
        gj = gres.zoneImplantationGeoJSON
        if emprise_brute > 0 and gj:
            grow = session.execute(_GREVE_SUR_ASSIETTE, {
                "gj": json.dumps(gj), "pid": parcel_id,
                "pkind": pkind, "er_types": er_types, "ebc_types": ebc_types,
                "peb_ab": [str(z).lower() for z in _layer_params("peb").get("hard_zones", ["a", "b"])],
                "dpf_m": float(_layer_params("dpf").get("marchepied_m", 3.25)),
                "rav_m": float(_layer_params("ravine").get("buffer_m", 10)),
            }).one()
            er_a = float(grow.er_area or 0.0)
            ebc_a = float(grow.ebc_area or 0.0)
            greve_cert = float(grow.cert_area or 0.0)
            greve_tot = float(grow.greve_total or 0.0)
        emprise = max(0.0, emprise_brute - greve_tot)
        racc = gbuild.raccordement or {}
        ppr_rouge = bool((racc.get("ppr") or {}).get("rouge"))
        ctx.contraintes.libelles.append(
            "Assiette = zone d'implantation réglementaire (moteur gabarit) : reculs par côté "
            "voie/limites" + (", PPR zone rouge découpée" if ppr_rouge else "") + ".")
        servie_sur = (racc.get("multizone") or {}).get("servie_sur")
        if servie_sur:
            ctx.contraintes.libelles.append(
                f"Zonage mixte : assiette calculée sur le seul morceau constructible {servie_sur}.")
        if er_a >= 0.5 and gj:
            for r in session.execute(_ER_DETAILS_ASSIETTE, {
                    "gj": json.dumps(gj), "pid": parcel_id,
                    "pkind": pkind, "er_types": er_types}):
                m2 = float(r.m2 or 0.0)
                if m2 < 0.5:
                    continue
                m = _ER_LIB.match((r.libelle or "").strip())
                label = f"ER {m.group(1)} : {m.group(2).strip()}" if m else \
                    (f"{r.txt} : {r.libelle}" if r.txt and r.txt != r.libelle else (r.libelle or "ER"))
                ctx.contraintes.libelles.append(
                    f"{label} — {m2:.0f} m² déduits de l'emprise constructible.")
        if ebc_a >= 0.5:
            ctx.contraintes.libelles.append(
                f"Espace boisé classé — {ebc_a:.0f} m² soustraits de l'assiette constructible "
                "(Art. L113-1 CU, aucune construction sur l'emprise boisée).")
        if greve_cert > 0.5:
            ctx.contraintes.libelles.append(
                f"Contraintes géométriques certaines — {greve_cert:.0f} m² (PEB A/B, marchepied "
                "DPF, ravine, 50 pas) soustraits de l'assiette. Le PPR rouge est déjà découpé "
                "de l'assiette (jamais compté deux fois).")
        greve_a = greve_tot          # déduction NETTE réellement retranchée (extras)
    else:
        row = session.execute(_EMPRISE, args).one()
        full_a = float(row.full_area or 0.0)
        uau_a = float(row.uau_area) if row.uau_area is not None else None
        er_a = float(row.er_area or 0.0)
        ebc_a = float(row.ebc_area or 0.0)
        greve_a = float(row.greve_area or 0.0)

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
        # SOURCES-1 lot 1 : la part EBC est soustraite de l'assiette (L113-1 CU) — union ER+EBC
        # (greve_a) pour ne jamais soustraire deux fois un chevauchement.
        if ebc_a >= 0.5:
            ctx.contraintes.libelles.append(
                f"Espace boisé classé — {ebc_a:.0f} m² soustraits de l'assiette constructible "
                "(Art. L113-1 CU, aucune construction sur l'emprise boisée).")
        emprise = max(0.0, base - greve_a)

        # SCORING-6 lot A — assiette clippée : soustraire les contraintes géométriques certaines
        # (PPR rouge, PEB A/B, marchepied DPF, ravine, 50 pas) et ramener la surface au sol servant
        # aux plafonds CES/pleine terre à la seule portion U/AU. OPT-IN — servi inchangé sinon.
        greve_cert = 0.0
        if assiette_clippee:
            greve_cert = _greve_certaine_m2(session, parcel_id, recul, ctx.commune)
            if greve_cert > 0.5:
                emprise = max(0.0, emprise - greve_cert)
                ctx.contraintes.libelles.append(
                    f"Assiette clippée : {greve_cert:.0f} m² de contraintes géométriques certaines "
                    "(PPR rouge, PEB A/B, marchepied DPF, ravine, 50 pas) soustraits de l'emprise.")

    # Surface au sol servant aux plafonds CES/pleine terre : la seule portion U/AU (à cheval).
    surface_assiette = ctx.surface_m2
    if assiette_clippee:
        pct_c = _pct_constructible(ctx)
        if pct_c is not None and 0 < pct_c < 100:
            surface_assiette = ctx.surface_m2 * pct_c / 100.0

    # ZONE-1 : sur parcelle à cheval, le bilan LE DIT — parts servies (modulation + contexte éco).
    if ctx.a_cheval and ctx.zone_parts:
        from .zone_servie import libelle_a_cheval
        ctx.contraintes.libelles.append(libelle_a_cheval(ctx.zone_parts))

    eco_types = ([str(t) for t in presc.get("mixite_sociale_typepsc", [])]
                 + [str(t) for t in presc.get("eaux_pluviales_typepsc", [])])
    mixite_set = {str(t) for t in presc.get("mixite_sociale_typepsc", [])}
    eco: dict = {"er_deduit_m2": round(er_a), "ebc_deduit_m2": round(ebc_a)}
    if ctx.a_cheval and ctx.zone_parts:
        eco["zones_a_cheval"] = ctx.zone_parts
    if eco_types:
        for r in session.execute(_ECO, {"pid": parcel_id, "pkind": pkind, "types": eco_types}):
            if r.subtype in mixite_set:
                eco["mixite"], eco["mixite_libelle"] = True, r.libelle
            else:
                eco["pluvial"], eco["pluvial_libelle"] = True, r.libelle
    ctx.prescriptions_eco = eco

    # FAISABILITE-1 (lot D) — lignes manquantes : ER/EBC/greve déjà soustraits (dits en étape) +
    # mixité détectée (dite « non modélisée »). Informatif : aucune de ces valeurs ne change la fourchette.
    # total_deduit = déduction NETTE réellement retranchée de l'emprise. Chemin gabarit : greve_a
    # est déjà l'UNION ER∪EBC∪certaines ∩ assiette (_GREVE_SUR_ASSIETTE) — jamais re-sommer.
    # Chemin legacy : greve_a = union ER+EBC (dédupée par _EMPRISE) + greve_cert. er_m2/ebc_m2/
    # greve_cert ne sont que les CONTRIBUTIONS listées (elles peuvent se chevaucher).
    extras = {"er_m2": er_a, "ebc_m2": ebc_a, "greve_certaine_m2": greve_cert,
              "total_deduit_m2": greve_a if assiette_source == "gabarit" else greve_a + greve_cert,
              "mixite": bool(eco.get("mixite")),
              "assiette_source": assiette_source}
    return ctx, estimate_capacity(rules, surface_assiette, ctx.contraintes, hyp=hyp,
                                  emprise_geo=(emprise, recul), extras=extras)


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
    hyp = Hypotheses.charger(ctx.commune)   # M-N P1-13 : hypothèses de la commune
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


def _hyp_modifiables_payload(commune: str | None) -> list[dict]:
    """FAISABILITE-1 (lot D) — hypothèses éditables servies (valeurs de la commune, avant tout
    override). Le front les rend en champs ; « Revenir aux hypothèses LABUSE » y revient."""
    from .engine import Hypotheses, hypotheses_modifiables
    return hypotheses_modifiables(Hypotheses.charger(commune))


def fiche_payload(session: Session, parcel_id: int) -> dict | None:
    """Payload JSON de la carte de faisabilité pour la fiche parcelle.
    None si la parcelle n'est pas couverte (zone hors PLU Saint-Paul outillé)."""
    res = parcel_faisabilite(session, parcel_id)
    if res is None:
        return None
    ctx, f = res
    c = ctx.contraintes

    # Potentiel résiduel (Lot B) — réutilise la faisabilité déjà calculée ; isolé/défensif.
    # FAISABILITE-clip — `res` est clippé (défaut) → le bâti retranché DOIT l'être sur la même
    # portion U/AU (assiette_clippee=True), sinon on soustrait le bâti de la portion A/N d'un plafond
    # U/AU (résiduel faussement nul — piège SCORING-6). Cohérent avec le run servi.
    residuel = None
    try:
        from .residuel import compute_residuel
        residuel = compute_residuel(session, parcel_id, faisa=res, assiette_clippee=True)
    except Exception:  # noqa: BLE001 - n'empêche jamais la fiche
        residuel = None

    # Bilan promoteur (PARTIE 1) — uniquement si constructible ; isolé/défensif.
    bilan = None
    try:
        from . import bilan_params as bpmod
        from .bilan import compute_bilan, sector_price
        from .engine import Hypotheses
        if f.constructible:
            # BILAN SERVI — SOURCE UNIQUE partagée (mandat prix sortie consommateurs, Vic 28/07/2026) :
            # cœur, Banquier, Argumentaire, Rapport de potentiel calculent LE MÊME bilan (charge
            # cohérente à l'euro entre tous les écrans). Prix de sortie NEUF par préséance ; les
            # overrides de bassin observatoire sont démotés (hors préséance) ; social-dominant → non
            # calculable servi. Cf. PRIX_SORTIE_CONSOMMATEURS_PHASE_A_RAPPORT.md.
            from .bilan import compute_bilan_servi
            secteur = None
            rules = resolve_zone(ctx.zone, ctx.commune) if ctx.zone else None
            secteur = (rules.bassin if rules else None) or "Saint-Paul"
            resolved = bpmod.resolve(session, secteur)
            _params_registre = [{**p, **resolved.get(p["key"], {})} for p in bpmod.registry()]
            b, _ps = compute_bilan_servi(session, ctx.parcel_id, res)
            if b is not None and not _ps["non_calculable"]:
                bilan = {
                    "fiable": b.fiable, "fiabilite": b.fiabilite, "verdict": b.verdict,
                    "prix_dvf": b.prix_dvf, "comparables": (b.prix_dvf or {}).get("comparables"),
                    "ca": b.ca, "charge_fonciere": b.charge_fonciere,
                    "steps": [{"label": s.label, "formule": s.formule, "valeur": s.valeur,
                               "source": s.source, "prov": s.prov} for s in b.steps],
                    "hypotheses": b.hypotheses, "avertissements": b.avertissements, "bandeau": b.bandeau,
                    "calc": b.calc, "niveau_prix_neuf": _ps["niveau"],
                    # Étiquette à 4 niveaux (couverture jamais payée par une fausse précision).
                    "prix_neuf_label": _ps["label"],
                    "prix_neuf_repli_ile": _ps["repli_ile"],
                    # 1.C — secteur + paramètres éditables (registre + valeurs résolues) + non calibrés.
                    "secteur": secteur,
                    "params": _params_registre,
                    "non_calibres_critiques": bpmod.uncalibrated_critical(resolved),
                    "estimes_a_affiner": bpmod.estimated_to_refine(resolved),
                }
            elif b is not None and _ps["non_calculable"]:
                # NON CALCULABLE — la parcelle est SERVIE avec la mention, JAMAIS écartée
                # (comportement M26-A « non estimable — non filtrée »). Un professionnel doit voir
                # la parcelle et savoir qu'on ne sait pas, pas la perdre.
                motif_nc = _ps["motif"]
                bilan = {
                    "fiable": False, "fiabilite": "non_calculable", "verdict": motif_nc,
                    "non_calculable": True, "motif_non_calculable": motif_nc,
                    "prix_dvf": None, "comparables": None, "ca": None, "charge_fonciere": None,
                    "steps": [], "hypotheses": [], "avertissements": [motif_nc], "bandeau": motif_nc,
                    "calc": None, "niveau_prix_neuf": None, "secteur": secteur,
                    "params": _params_registre,
                    "non_calibres_critiques": bpmod.uncalibrated_critical(resolved),
                    "estimes_a_affiner": bpmod.estimated_to_refine(resolved),
                }
            # b is None (capacité non résolue) → bilan reste None (non bloquant).
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
        # FAISABILITE-1 (lot D) — hypothèses ÉDITABLES (les seules lignes Estimé du calcul) : le front
        # rend un champ par entrée, les Sourcé restent verrouillés. Valeurs = celles servies (commune).
        "hypotheses_modifiables": _hyp_modifiables_payload(ctx.commune),
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
