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
       -- CONTENANCE-1 (Lot C) : la surface servant aux RATIOS (emprise CES, pleine terre, densité,
       -- seuils de taille) = CONTENANCE si présente (chiffre de l'acte), sinon dessin. Le DESSIN
       -- (ST_Area) reste disponible pour les formes et pour le facteur de ré-échelle C3.
       COALESCE(p.contenance_m2, ST_Area(p.geom_2975))    AS surface_m2,
       ST_Area(p.geom_2975)                               AS surface_dessin_m2,
       (SELECT max((pl.attrs->>'slope_pct')::float) FROM spatial_layers pl
          WHERE pl.commune = p.commune AND pl.kind = 'pente'
            AND ST_Intersects(pl.geom_2975, p.geom_2975))  AS pente_pct,
       -- PPR-UNIQUE-1 (E-006) — PART réellement dans la bande littorale (0..1), pas un booléen :
       -- un simple contact (12,7 % max observé) annulait toute la parcelle. On ne retire que la part.
       COALESCE((SELECT ST_Area(ST_Union(ST_Intersection(t.geom_2975, p.geom_2975)))
                 FROM spatial_layers t
                 WHERE t.commune = p.commune AND t.kind = 'trait_de_cote'
                   AND t.subtype IN ('bande_courte','bande_longue')
                   AND ST_Intersects(t.geom_2975, p.geom_2975))
                / NULLIF(ST_Area(p.geom_2975), 0), 0.0)        AS littoral_pct,
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
    surface_m2: float          # CONTENANCE-1 : surface de terrain (contenance si présente, sinon dessin)
    zone: str | None
    contraintes: Contraintes
    # CONTENANCE-1 (Lot C) : aire du DESSIN (ST_Area). Sert au facteur de ré-échelle C3 des aires
    # géométriques (zone d'implantation, déductions) : aire × surface_m2 / surface_dessin_m2.
    surface_dessin_m2: float = 0.0
    # Prescriptions à effet économique (mixité sociale, eaux pluviales) + ER déduits,
    # renseignées par parcel_faisabilite() pour alimenter badges fiche et bilan.
    prescriptions_eco: dict = field(default_factory=dict)
    # ZONE-1 : zone DOMINANTE PAR SURFACE (la même que l'écran, cf. zone_servie.zone_dominante)
    # + drapeau « à cheval » quand aucune zone n'atteint 90 % — parts servies au bilan/fiche.
    zone_fam: str | None = None
    a_cheval: bool = False
    zone_parts: list = field(default_factory=list)
    # DONNEES-FIX-1 point 4 — exceptions PLU `modifie_calcul=true` présentes sur la zone mais qu'on
    # ne sait pas modéliser (bandes/voies nommées/destination…) : la parcelle les PORTE plutôt que
    # de les approximer. Chaque item : {regle, porte, article, page_pdf}. Renseigné par parcel_faisabilite.
    regles_non_modelisees: list = field(default_factory=list)
    # EXIGU-FIX-1 — trace du ré-examen géométrique quand l'emprise tombait sous le seuil (sinon None) :
    # {decision: regain|exigu|verifier, net_m2, net_larg, pre_m2, parc_larg, has_net, valide}. Lecture
    # seule (transparence + tests), n'altère aucun calcul.
    reexamen_exigu: dict | None = None
    # EXPORTS-FIX-3 LOT 1 — quand la zone dominante est A/N mais qu'une sous-zone U/AU a été
    # envisagée : {m2, pct, sous_zone} de la portion U/AU RÉELLE mesurée. Renseigné par
    # parcel_faisabilite pour la garde d'aire réelle (transparence + tests). None sinon.
    uau_reelle: dict | None = None

    @property
    def terrain_sur_dessin(self) -> float:
        """Facteur de ré-échelle C3 : contenance/dessin (1.0 si pas de contenance ou dessin nul).
        Toute aire tirée du dessin et affichée/utilisée dans un ratio est multipliée par ce facteur
        → rien ne dépasse la surface du terrain et les proportions tiennent."""
        return (self.surface_m2 / self.surface_dessin_m2) if self.surface_dessin_m2 else 1.0

    @property
    def surface_incertaine(self) -> bool:
        """Garde-fou CONTENANCE-1 (SYMÉTRIQUE) : la contenance s'écarte d'un facteur > 2 du dessin,
        dans un sens OU l'autre (contenance < dessin/2 ou contenance > 2×dessin). `surface_m2` vaut
        la contenance quand elle est présente (COALESCE(contenance, ST_Area)), sinon le dessin — donc
        `surface_m2 != surface_dessin_m2` isole précisément « contenance présente et différente du
        dessin » (dans un sens comme dans l'autre). On passe alors cette contenance au prédicat."""
        from .. import surface as _s
        cont = self.surface_m2 if self.surface_m2 != self.surface_dessin_m2 else None
        return _s.surface_incertaine(self.surface_dessin_m2, cont)


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
-- ZONES-FAMILLE-1 : portion constructible via la SOURCE SQL UNIQUE `labuse_zone_famille(subtype)`
-- (typezone GPU) — jamais devinée depuis `name` (code « Ub », libellé « Secteur de centralité »
-- ou forme phasée « 1AUb » selon la commune). Couvre d'un coup les zones AU numérotées ET les
-- 8 communes à name littéral (bug EXIGU-GRANDES + son extension).
uau AS (SELECT ST_Union(z.geom_2975) AS u
        FROM spatial_layers z, p
        WHERE z.kind = :zkind AND z.commune = p.commune
          AND labuse_zone_famille(z.subtype) = ANY(:uau_fams)
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
    _litt_pct = float(r.littoral_pct or 0.0)
    c = Contraintes(
        pente_pct=float(r.pente_pct) if r.pente_pct is not None else None,
        littoral_pct=_litt_pct,
        bande_littorale=_litt_pct > 0.0,
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
                         surface_dessin_m2=float(r.surface_dessin_m2 or 0.0),
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
          AND labuse_zone_famille(z.subtype) = ANY(:uau_fams)
          AND ST_Intersects(z.geom_2975, p.b)),
assiette AS (SELECT CASE WHEN uau.u IS NULL THEN p.b
                         ELSE ST_Intersection(p.b, uau.u) END AS a
             FROM p LEFT JOIN uau ON TRUE),
greves AS (
    -- PPR-UNIQUE-1 — part INTERDITE (rouge ∪ code non classé) via la classification UNIQUE
    -- `labuse_ppr_couleur` (remplace l'ancien filtre `subtype = ANY(ppr_red)` qui ratait le code `i`).
    SELECT ST_MakeValid(ST_ClipByBox2D(g.geom_2975, p.b)) AS geom FROM spatial_layers g, p
      WHERE g.kind = 'ppr' AND g.commune = p.commune
        AND labuse_ppr_couleur(g.subtype, g.attrs) <> 'bleu' AND ST_Intersects(g.geom_2975, p.b)
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
    dpfp = _layer_params("dpf")
    ravp = _layer_params("ravine")
    pebp = _layer_params("peb")
    row = session.execute(_GREVE_CERTAINE, {
        "pid": parcel_id, "d": recul,
        "zkind": zonage.get("spatial_kind", "plu_gpu_zone"),
        "uau_fams": list(zonage.get("positive_prefixes", ["U", "AU"])),
        "peb_ab": [str(z).lower() for z in pebp.get("hard_zones", ["a", "b"])],
        "dpf_m": float(dpfp.get("marchepied_m", 3.25)),
        "rav_m": float(ravp.get("buffer_m", 10)),
    }).scalar()
    return float(row or 0.0)


# RESIDUEL-2 — UNION GLOBALE des contraintes certaines sur l'assiette legacy (p.b ∩ U/AU), fin du
# DOUBLE RETRAIT. L'ancien chemin legacy soustrayait SÉPARÉMENT union(ER,EBC) (greve_a, `_EMPRISE`)
# PUIS union(PPR rouge, PEB A/B, DPF, ravine, 50 pas) (greve_cert, `_GREVE_CERTAINE`) : là où ces
# deux ensembles se chevauchent, leur intersection était retranchée DEUX FOIS → emprise
# sous-estimée (faux zéros). Ici, une SEULE union de TOUTES les contraintes certaines, intersectée
# une seule fois avec l'assiette — exactement la mécanique du chemin gabarit (`_GREVE_SUR_ASSIETTE`,
# `greve_total`). er_area/ebc_area/cert_area restent retournés pour l'affichage (contributions
# individuelles, qui PEUVENT se chevaucher) ; seul `greve_total` (union) est réellement soustrait.
# Assiette identique à `_GREVE_CERTAINE` (inset p.b clippé à l'union U/AU) : résultat strictement
# comparable à `base` de `_EMPRISE`.
_GREVE_LEGACY_UNION = text("""
WITH p AS (SELECT commune, ST_Buffer(geom_2975, -:d) AS b FROM parcels WHERE id = :pid),
uau AS (SELECT ST_Union(ST_MakeValid(ST_ClipByBox2D(z.geom_2975, p.b))) AS u
        FROM spatial_layers z, p
        WHERE z.kind = :zkind AND z.commune = p.commune
          AND labuse_zone_famille(z.subtype) = ANY(:uau_fams)
          AND ST_Intersects(z.geom_2975, p.b)),
assiette AS (SELECT CASE WHEN uau.u IS NULL THEN p.b
                         ELSE ST_Intersection(p.b, uau.u) END AS a
             FROM p LEFT JOIN uau ON TRUE),
er AS (SELECT ST_Union(ST_MakeValid(ST_ClipByBox2D(e.geom_2975, p.b))) AS u
       FROM spatial_layers e, p
       WHERE e.kind = :pkind AND e.commune = p.commune
         AND e.subtype = ANY(:er_types) AND ST_Intersects(e.geom_2975, p.b)),
ebc AS (SELECT ST_Union(ST_MakeValid(ST_ClipByBox2D(e.geom_2975, p.b))) AS u
        FROM spatial_layers e, p
        WHERE e.kind = :pkind AND e.commune = p.commune
          AND e.subtype = ANY(:ebc_types) AND ST_Intersects(e.geom_2975, p.b)),
cert AS (SELECT ST_Union(geom) AS u FROM (
    SELECT ST_MakeValid(ST_ClipByBox2D(g.geom_2975, p.b)) AS geom FROM spatial_layers g, p
      WHERE g.kind = 'ppr' AND g.commune = p.commune
        AND labuse_ppr_couleur(g.subtype, g.attrs) <> 'bleu' AND ST_Intersects(g.geom_2975, p.b)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(g.geom_2975, p.b)) FROM spatial_layers g, p
      WHERE g.kind = 'peb' AND lower(g.subtype) = ANY(:peb_ab) AND ST_Intersects(g.geom_2975, p.b)
  UNION ALL
    SELECT ST_Buffer(ST_MakeValid(g.geom_2975), :dpf_m) FROM spatial_layers g, p
      WHERE g.kind = 'dpf' AND g.commune = p.commune AND ST_DWithin(g.geom_2975, p.b, :dpf_m)
  UNION ALL
    SELECT ST_Buffer(ST_MakeValid(g.geom_2975), :rav_m) FROM spatial_layers g, p
      WHERE g.kind = 'ravine' AND g.commune = p.commune AND ST_DWithin(g.geom_2975, p.b, :rav_m)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(g.geom_2975, p.b)) FROM spatial_layers g, p
      WHERE g.kind = 'cinquante_pas' AND g.commune = p.commune AND ST_Intersects(g.geom_2975, p.b)
) s)
SELECT COALESCE(ST_Area(ST_Intersection(a.a, er.u)), 0.0)   AS er_area,
       COALESCE(ST_Area(ST_Intersection(a.a, ebc.u)), 0.0)  AS ebc_area,
       COALESCE(ST_Area(ST_Intersection(a.a, cert.u)), 0.0) AS cert_area,
       COALESCE(ST_Area(ST_Intersection(a.a, ST_Union(ST_Union(
           COALESCE(er.u,  ST_GeomFromText('GEOMETRYCOLLECTION EMPTY', 2975)),
           COALESCE(ebc.u, ST_GeomFromText('GEOMETRYCOLLECTION EMPTY', 2975))),
           COALESCE(cert.u, ST_GeomFromText('GEOMETRYCOLLECTION EMPTY', 2975))))), 0.0) AS greve_total
FROM assiette a LEFT JOIN er ON TRUE LEFT JOIN ebc ON TRUE LEFT JOIN cert ON TRUE
""")


# ── EXIGU-FIX-1 — ré-examen géométrique AVANT de conclure « terrain exigu » ──────────────────────
# ALGO-LECTURE-1 §3.4-A + DEPLOY-GROUPE-3 §D : le moteur gabarit (reculs par côté) s'effondre à tort
# sur de grandes parcelles (zone d'implantation vidée) ; le code attribue alors une cause
# `terrain_exigu` (« trop étroit ») à des parcelles qui portent un gros morceau exploitable d'un seul
# tenant. Ce ré-examen est INDÉPENDANT du gabarit : il mesure, sur la GÉOMÉTRIE RÉPARÉE (ST_MakeValid),
# le PLUS GRAND MORCEAU D'UN SEUL TENANT de l'assiette nette = (parcelle ∩ U/AU) insetée des reculs,
# amputée de l'UNION des contraintes certaines (ER/EBC/PPR rouge/PEB A-B/DPF/ravine/50 pas) — même
# définition que `_GREVE_LEGACY_UNION`. Il renvoie, pour ce morceau : son aire nette, sa largeur utile
# (diamètre du cercle inscrit), ET l'aire de l'assiette AVANT contraintes + la largeur de la parcelle
# (pour distinguer un vrai terrain étroit d'une donnée douteuse). Tout sur le DESSIN (ré-échelle
# contenance appliquée côté Python). Lecture seule, isolé en SAVEPOINT par l'appelant.
LARGEUR_MIN_EXPLOITABLE_M = 3.0   # diamètre inscrit du plus grand morceau net en deçà duquel = vraiment trop étroit

_ASSIETTE_NETTE_ROBUSTE = text("""
WITH p AS (SELECT commune, ST_MakeValid(geom_2975) AS g0, ST_Buffer(ST_MakeValid(geom_2975), -:d) AS b
           FROM parcels WHERE id = :pid),
uau AS (SELECT ST_Union(ST_MakeValid(ST_ClipByBox2D(z.geom_2975, p.b))) AS u
        FROM spatial_layers z, p
        WHERE z.kind = :zkind AND z.commune = p.commune
          AND labuse_zone_famille(z.subtype) = ANY(:uau_fams) AND ST_Intersects(z.geom_2975, p.b)),
pre AS (SELECT CASE WHEN uau.u IS NULL THEN p.b ELSE ST_Intersection(p.b, uau.u) END AS a
        FROM p LEFT JOIN uau ON TRUE),
predump AS (SELECT (ST_Dump(ST_CollectionExtract(ST_MakeValid((SELECT a FROM pre)), 3))).geom AS part),
cert AS (SELECT ST_Union(geom) AS u FROM (
    SELECT ST_MakeValid(ST_ClipByBox2D(e.geom_2975, p.b)) AS geom FROM spatial_layers e, p
      WHERE e.kind = :pkind AND e.commune = p.commune AND e.subtype = ANY(:er_types) AND ST_Intersects(e.geom_2975, p.b)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(e.geom_2975, p.b)) FROM spatial_layers e, p
      WHERE e.kind = :pkind AND e.commune = p.commune AND e.subtype = ANY(:ebc_types) AND ST_Intersects(e.geom_2975, p.b)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(g.geom_2975, p.b)) FROM spatial_layers g, p
      WHERE g.kind = 'ppr' AND g.commune = p.commune
        AND labuse_ppr_couleur(g.subtype, g.attrs) <> 'bleu' AND ST_Intersects(g.geom_2975, p.b)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(g.geom_2975, p.b)) FROM spatial_layers g, p
      WHERE g.kind = 'peb' AND lower(g.subtype) = ANY(:peb_ab) AND ST_Intersects(g.geom_2975, p.b)
  UNION ALL
    SELECT ST_Buffer(ST_MakeValid(g.geom_2975), :dpf_m) FROM spatial_layers g, p
      WHERE g.kind = 'dpf' AND g.commune = p.commune AND ST_DWithin(g.geom_2975, p.b, :dpf_m)
  UNION ALL
    SELECT ST_Buffer(ST_MakeValid(g.geom_2975), :rav_m) FROM spatial_layers g, p
      WHERE g.kind = 'ravine' AND g.commune = p.commune AND ST_DWithin(g.geom_2975, p.b, :rav_m)
  UNION ALL
    SELECT ST_MakeValid(ST_ClipByBox2D(g.geom_2975, p.b)) FROM spatial_layers g, p
      WHERE g.kind = 'cinquante_pas' AND g.commune = p.commune AND ST_Intersects(g.geom_2975, p.b)
) s),
net AS (SELECT ST_Difference((SELECT a FROM pre),
                             COALESCE((SELECT u FROM cert), ST_GeomFromText('POLYGON EMPTY', 2975))) AS n),
netdump AS (SELECT (ST_Dump(ST_CollectionExtract(ST_MakeValid((SELECT n FROM net)), 3))).geom AS part),
nbig AS (SELECT part FROM netdump ORDER BY ST_Area(part) DESC LIMIT 1)
SELECT COALESCE((SELECT max(ST_Area(part)) FROM predump), 0.0)                         AS pre_area,
       COALESCE((SELECT ST_Area(part) FROM nbig), 0.0)                                 AS net_area,
       COALESCE((SELECT (ST_MaximumInscribedCircle(part)).radius * 2 FROM nbig), 0.0)  AS net_largeur,
       COALESCE((ST_MaximumInscribedCircle((SELECT g0 FROM p))).radius * 2, 0.0)       AS parc_largeur,
       (SELECT count(*) FROM nbig)                                                     AS has_net,
       ST_IsValid(ST_MakeValid((SELECT n FROM net)))                                   AS valide
""")


def _exigu_fix_actif() -> bool:
    """EXIGU-FIX-1 — seam de MESURE : le ré-examen géométrique est ACTIF par défaut ; mettre
    `LABUSE_EXIGU_FIX=0` le désactive (chemin d'ORIGINE, pour mesurer l'avant/après sur la MÊME
    population). N'influence AUCUNE parcelle hors de la branche terrain_exigu (il n'est appelé que
    lorsque l'emprise calculée tombe sous le seuil)."""
    import os
    return os.environ.get("LABUSE_EXIGU_FIX", "1") != "0"


def _reexamen_exigu(session: Session, parcel_id: int, recul: float, qargs: dict,
                    k_cont: float) -> tuple[str, dict]:
    """EXIGU-FIX-1 — décide, SUR PREUVE GÉOMÉTRIQUE, ce qu'est réellement une parcelle que le moteur
    s'apprête à classer `terrain_exigu`. Renvoie (decision, info) où decision ∈ :
      · 'regain'   — un morceau net exploitable existe (aire ≥ seuil ET largeur ≥ seuil) : la capacité
                     doit être calculée dessus (`info['net_m2']` = emprise à servir) ;
      · 'exigu'    — PROUVÉ inexploitable : morceau net mesuré trop petit/étroit, OU aucune assiette
                     nette sur une parcelle elle-même étroite (inset légitimement vidé) → on garde
                     `terrain_exigu` AVEC la preuve mesurée ;
      · 'verifier' — DOUTEUX : aucune assiette nette établie alors que la parcelle est large (contraintes
                     superposées / portion U/AU incohérente), ou géométrie non réparable → `assiette_a_verifier`.
    Isolé en SAVEPOINT : toute erreur géométrique → 'verifier' (jamais un faux « trop étroit », jamais un crash)."""
    from .engine import SEUIL_EXIGU_M2
    info = {"net_m2": 0.0, "net_larg": 0.0, "pre_m2": 0.0, "parc_larg": 0.0, "has_net": 0, "valide": None}
    try:
        with session.begin_nested():
            row = session.execute(_ASSIETTE_NETTE_ROBUSTE, {
                "pid": parcel_id, "d": recul,
                "zkind": qargs["zkind"], "uau_fams": qargs["uau_fams"],
                "pkind": qargs["pkind"], "er_types": qargs["er_types"], "ebc_types": qargs["ebc_types"],
                "peb_ab": qargs["peb_ab"], "dpf_m": qargs["dpf_m"], "rav_m": qargs["rav_m"],
            }).one()
    except Exception:  # noqa: BLE001 — géométrie pathologique : on ne tranche pas, on fait vérifier
        return "verifier", info
    info["net_m2"] = float(row.net_area or 0.0) * k_cont
    info["pre_m2"] = float(row.pre_area or 0.0) * k_cont
    info["net_larg"] = float(row.net_largeur or 0.0)
    info["parc_larg"] = float(row.parc_largeur or 0.0)
    info["has_net"] = int(row.has_net or 0)
    info["valide"] = bool(row.valide) if row.valide is not None else None
    if row.valide is False:
        return "verifier", info                       # géométrie nette non réparable → douteux
    # Un morceau net exploitable existe-t-il ? (aire ET largeur suffisantes)
    if info["has_net"] and info["net_m2"] >= SEUIL_EXIGU_M2 and info["net_larg"] >= LARGEUR_MIN_EXPLOITABLE_M:
        return "regain", info
    # Pas exploitable. Avons-nous MESURÉ un vrai petit morceau (preuve de l'exiguïté) ?
    if info["has_net"] and info["net_m2"] > 0:
        return "exigu", info                          # morceau net mesuré, trop petit ou trop étroit → prouvé
    # Aucune assiette nette (morceau net vide). Est-ce une parcelle réellement étroite, ou un doute ?
    largeur_ruban = 2.0 * recul + 1.0                 # en deçà, l'inset vide légitimement le contour (vrai ruban)
    if info["parc_larg"] and info["parc_larg"] < largeur_ruban:
        return "exigu", info                          # parcelle elle-même étroite → inset vidé pour de vrai
    return "verifier", info                           # parcelle large mais rien de net → données douteuses


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
    servie comme assiette de la capacité.

    RESIDUEL-2 — renvoie `(gab, blocages)` : `gab = (BuildResult, GabaritResult)` quand le gabarit
    SERT la parcelle (`blocages = []`) ; `(None, blocages)` sinon, où `blocages` liste les MOTIFS de
    non-service. Le lecteur garde alors son chemin legacy et QUALIFIE le repli selon ces motifs
    (`_repli_qualifiable`) : seule une non-qualification due à des arêtes naturelles non classables
    (ravine/littoral/DPF/micro-arête) prouve que l'inset uniforme + l'union des contraintes applique
    correctement les règles ; tout autre motif (recul voie deviné, PLU non calibré, CES/hauteur
    absents, multi-zones) laisse la capacité NON qualifiée (`assiette_source='residuel_legacy'`)."""
    from ..gabarit.builder import build_gabarit_input
    from ..gabarit.engine import compute_gabarit
    build = build_gabarit_input(session, idu)
    if build is None:
        return None, ["parcelle/zone introuvable ou géométrie de parcelle indisponible"]
    if build.blocking:
        return None, list(build.blocking)
    res = compute_gabarit(build.input)
    if res.status != "ok":
        return None, [f"gabarit:{res.status}"]
    return (build, res), []


# RESIDUEL-2 — un repli est QUALIFIÉ (il applique provablement les règles du cas) uniquement quand
# TOUS les motifs de non-service du gabarit sont « Limites de la parcelle non qualifiées » PORTANT
# une arête NATURELLE (ravine / littoral / domaine public non routier / micro-arête de numérisation).
# Le builder n'atteint l'étape limites/géométrie QUE si le PLU est complet et unique (`if not
# blocking`), donc zone constructible calibrée, CES et hauteur connus ; le seul point ouvert est alors
# cette arête, SANS voie dont le recul (souvent supérieur au séparatif) serait sous-appliqué →
# l'inset séparatif uniforme + l'union des contraintes est correct et CONSERVATEUR.
#
# PIÈGE (corrigé) : `non_classees` peut aussi contenir `MOTIF_VOIE_PRIVEE` (« desservie par une voie
# privée : le règlement ne précise pas le recul ») → le message commence AUSSI par « Limites… » mais
# c'est une RÈGLE DEVINÉE (recul sur voie privée), pas une arête naturelle → NON qualifiable. On
# exclut donc explicitement « voie privée » (les motifs bénins — « arête sans voie ni voisin »,
# « arête résiduelle < 1 m » — ne contiennent jamais cette sous-chaîne). Tout autre motif (recul voie,
# PLU non calibré, CES/hauteur absents, multi-zones) → NON qualifié.
_MOTIF_LEGACY_BENIN = "Limites de la parcelle non qualifiées"


def _repli_qualifiable(blocages: list[str]) -> bool:
    """RESIDUEL-2 — True si le repli applique provablement les règles du cas (arête naturelle seule ;
    jamais une voie privée au recul deviné)."""
    return bool(blocages) and all(
        b.startswith(_MOTIF_LEGACY_BENIN) and "voie privée" not in b for b in blocages)


def _sous_zone_constructible(ctx: ParcelContext):
    """SCORING-6 lot A — assiette clippée : quand la zone DOMINANTE n'est pas constructible
    (A/N, habitat interdit) mais qu'une portion U/AU subsiste, résout les règles de la plus
    grande sous-zone U/AU. Renvoie les ZoneRules de cette portion (capacité calculée sur la
    portion, au lieu du tout-ou-rien) ou None si aucune portion constructible ne se résout.

    EXPORTS-FIX-3 LOT 1 — ce choix de règle ne suffit PAS : il faut encore que la portion U/AU
    existe VRAIMENT (aire réelle), ce que ce `pct` (arrondi à 0,1 pt dans `zone_parts`) ne
    garantit pas — un éclat de 0,09 m² s'arrondit à 0,0 % et passait quand même. La GARDE d'aire
    réelle est posée au point d'appel DB-aware (`parcel_faisabilite`), qui mesure la surface U/AU
    sur la géométrie ; cette fonction reste pure (choix du secteur dominant U/AU)."""
    parts = [p for p in (ctx.zone_parts or []) if p.get("fam") in FAMILLES_CONSTRUCTIBLES]
    for p in sorted(parts, key=lambda x: -float(x.get("pct") or 0)):
        r = resolve_zone(p.get("zone"), ctx.commune)
        if r is not None and r.constructible_neuf and r.habitat != "interdit":
            return r
    return None


# EXPORTS-FIX-3 LOT 1 — SEUILS de « portion U/AU réelle ». Une parcelle dont la zone DOMINANTE
# n'est pas constructible (A/N) ne devient constructible « à cheval » que si sa part U/AU est une
# VRAIE surface : au-delà de ces deux seuils, qui sont exactement la frontière de la classe
# « infime » du mandat (moins de 1 % OU moins de 50 m²). En deçà (nulle ou infime), l'intersection
# U/AU est un éclat de numérisation / un contact de limite — aucune capacité n'est servie, la
# parcelle reste sa zone dominante. La famille U/AU est lue par `labuse_zone_famille(subtype)` (la
# source unique du code : tient sur 1AU/2AU et les libellés littéraux — Bras-Panon, Saint-Pierre),
# jamais par le préfixe du nom.
SEUIL_UAU_REELLE_M2 = 50.0
SEUIL_UAU_REELLE_PCT = 1.0

# Surface U/AU RÉELLE (m²) d'une parcelle + part (%) de sa surface dessinée. Intersection
# géométrique brute avec les zones de FAMILLE U/AU (même `positive_prefixes` que tout le moteur),
# sans inset : on mesure la portion U/AU telle qu'elle existe au plan, la « surface réelle en
# U/AU » du mandat. ST_ClipByBox2D avant l'intersection fine (grosses zones PLU) — résultat
# identique, O(bbox).
_UAU_REELLE = text("""
WITH p AS (SELECT commune, geom_2975 AS g, ST_Area(geom_2975) AS a FROM parcels WHERE id = :pid)
SELECT COALESCE(sum(ST_Area(ST_Intersection(
           ST_MakeValid(ST_ClipByBox2D(z.geom_2975, p.g)), p.g))), 0.0) AS uau_m2,
       (SELECT a FROM p) AS parc_m2
FROM spatial_layers z, p
WHERE z.kind = :zkind AND z.commune = p.commune
  AND labuse_zone_famille(z.subtype) = ANY(:uau_fams)
  AND ST_Intersects(z.geom_2975, p.g)
""")


def _uau_reelle(session: Session, parcel_id: int) -> tuple[float, float]:
    """EXPORTS-FIX-3 LOT 1 — (surface U/AU réelle en m², part en % de la parcelle). (0, 0) si
    aucune zone U/AU ne touche la parcelle. Lecture seule, bornée."""
    zonage = _layer_params("zonage_plu_gpu")
    row = session.execute(_UAU_REELLE, {
        "pid": parcel_id,
        "zkind": zonage.get("spatial_kind", "plu_gpu_zone"),
        "uau_fams": list(zonage.get("positive_prefixes", ["U", "AU"])),
    }).one()
    m2 = float(row.uau_m2 or 0.0)
    parc = float(row.parc_m2 or 0.0)
    pct = (100.0 * m2 / parc) if parc > 0 else 0.0
    return m2, pct


def _uau_portion_reelle(uau_m2: float, uau_pct: float) -> bool:
    """EXPORTS-FIX-3 LOT 1 — True si la portion U/AU est une VRAIE surface (classe « au-delà » du
    mandat : ≥ 50 m² ET ≥ 1 %). False pour « nulle » (0) et « infime » (< 1 % OU < 50 m²) : la
    parcelle ne porte alors aucune capacité à cheval (fonction pure, verrouillée par test)."""
    return uau_m2 >= SEUIL_UAU_REELLE_M2 and uau_pct >= SEUIL_UAU_REELLE_PCT


def _uau_gate_actif() -> bool:
    """EXPORTS-FIX-3 LOT 1 — seam de MESURE : la garde d'aire réelle U/AU est ACTIVE par défaut ;
    `LABUSE_UAU_PHANTOM_GATE=0` la désactive (comportement d'ORIGINE : une portion U/AU, même d'un
    éclat, rendait la parcelle constructible) pour mesurer l'avant/après sur la MÊME population.
    N'influence AUCUNE parcelle hors de la branche sous-zone (zone dominante déjà non constructible)."""
    import os
    return os.environ.get("LABUSE_UAU_PHANTOM_GATE", "1") != "0"


def _pct_constructible(ctx: ParcelContext) -> float | None:
    """Part U/AU (%) de la surface — None si la parcelle n'est pas à cheval (une seule zone)."""
    if not ctx.zone_parts:
        return None
    return sum(float(p.get("pct") or 0) for p in ctx.zone_parts
               if p.get("fam") in FAMILLES_CONSTRUCTIBLES)


def parcel_faisabilite(session: Session, parcel_id: int,
                       hyp_overrides: dict | None = None,
                       legacy_union: bool = True) -> tuple[ParcelContext, Faisabilite] | None:
    """Contexte + pré-faisabilité d'une parcelle, EMPRISE SUR GÉOMÉTRIE RÉELLE
    (ST_Buffer du contour cadastral par le recul séparatif, EPSG:2975), clippée à la
    portion U/AU si zonage mixte (Décision 1) et amputée des emplacements réservés
    (Décision 3.a). None si parcelle/zone introuvable.

    RESIDUEL-1 (décision Vic 08/11/2026) — UN SEUL CHEMIN, assiette CLIPPÉE pour TOUS les lecteurs.
    Le flag `assiette_clippee` a disparu : la fiche, l'outil Faisabilité, le bilan, le potentiel ET
    le run résiduel de nuit (`compute_residuel_batch`) calculent sur la MÊME assiette — zone
    d'implantation du gabarit, reculs par côté, **PPR zone rouge découpée**. Avant RESIDUEL-1, le
    batch appelait ce moteur avec `assiette_clippee=False` → branche héritée SANS découpe du rouge →
    toute parcelle touchée par une zone rouge fermée « rédhibitoire », alors que la fiche (clippée)
    la disait constructible sur la partie hors rouge. Deux chemins, deux verdicts : supprimés.

    Quand le moteur gabarit ne sert pas la parcelle (`_assiette_gabarit` → None : gabarit bloquant,
    zone non constructible), le calcul retombe sur la branche legacy ci-dessous — qui applique
    DÉSORMAIS inconditionnellement la découpe des contraintes certaines (PPR rouge compris) et le
    clip de surface à la portion U/AU. La provenance est écrite (`assiette_source`).

    RESIDUEL-2 — la branche legacy soustrait l'UNION GLOBALE des contraintes certaines (fin du double
    retrait). `legacy_union=False` est un seam de MESURE (hors service) qui rejoue l'ancien double
    retrait (ER∪EBC puis cert, chevauchement soustrait deux fois) pour chiffrer l'impact ; il ne
    change jamais le service (défaut True)."""
    from .engine import Hypotheses, SEUIL_EXIGU_M2

    ctx = parcel_context(session, parcel_id)
    if ctx is None or not ctx.zone:
        return None
    # CONTENANCE-1 (garde-fou) — contenance < moitié du dessin : surface indéterminée, on ne calcule
    # NI sur la contenance NI sur le dessin → « Analyse incomplète », aucune capacité. Court-circuit
    # AVANT toute géométrie (inutile ici). La fiche affiche quand même les deux chiffres (payload).
    if ctx.surface_incertaine:
        from .engine import faisabilite_surface_incertaine
        return ctx, faisabilite_surface_incertaine(ctx.zone)
    rules = resolve_zone(ctx.zone, ctx.commune)
    # SCORING-6 lot A — assiette clippée : si la zone DOMINANTE n'est pas constructible mais
    # qu'une portion U/AU subsiste, on résout la sous-zone U/AU et on calcule la capacité sur
    # cette portion (fini le tout-ou-rien). RESIDUEL-1 — toujours actif (chemin unique).
    alt = None
    phantom_ecarte = False
    if (rules is None or not rules.constructible_neuf
            or rules.habitat == "interdit"):
        alt = _sous_zone_constructible(ctx)
        if alt is not None:
            # EXPORTS-FIX-3 LOT 1 — GARDE D'AIRE RÉELLE : la sous-zone U/AU n'ouvre la
            # constructibilité QUE si la portion U/AU est une vraie surface (≥ 50 m² ET ≥ 1 %).
            # Une parcelle 100 % A/N peut toucher un éclat U/AU de quelques m² (contact de limite,
            # bruit de numérisation) : `_sous_zone_constructible` le choisissait et rendait TOUTE la
            # parcelle constructible (ex. 97408000BI0351 : éclat « UB » de 0,09 m² → 24 437 m² de
            # plancher fantôme). On mesure l'aire réelle ; en deçà des seuils, la parcelle reste sa
            # zone dominante (non constructible) — aucune capacité sans surface réelle en U/AU.
            uau_m2, uau_pct = _uau_reelle(session, parcel_id)
            ctx.uau_reelle = {"m2": uau_m2, "pct": uau_pct, "sous_zone": alt.code}
            if not _uau_gate_actif() or _uau_portion_reelle(uau_m2, uau_pct):
                rules = alt
                ctx.contraintes.libelles.append(
                    f"Zone dominante « {ctx.zone} » non constructible — capacité calculée sur la "
                    f"portion U/AU réelle (~{uau_m2:.0f} m², {uau_pct:.1f} % de la parcelle ; "
                    f"sous-zone « {alt.code} »), assiette clippée.")
            else:
                phantom_ecarte = True
            # sinon : portion U/AU infime/nulle → `rules` reste la zone dominante (A/N) non
            # constructible ; estimate_capacity rendra « non constructible en zone <dominante> »
            # (jamais un chiffre sur une portion qui n'existe pas réellement).
    if rules is None:
        # EXPORTS-FIX-3 LOT 1 — une sous-zone U/AU a été ÉCARTÉE par la garde d'aire réelle, mais la
        # zone dominante (A/N) n'est pas calibrée au PLU de la commune (resolve_zone → None). La
        # parcelle N'EST PAS « hors PLU » : elle est en zone non constructible. On sert un verdict
        # ferme (jamais None qui masquerait la zone, jamais la capacité fantôme qui l'ouvrait avant).
        if phantom_ecarte and ctx.zone_fam in ("A", "N"):
            from .engine import faisabilite_zone_non_constructible
            return ctx, faisabilite_zone_non_constructible(ctx.zone, ctx.zone_fam)
        return None
    # PROSPECT (Ud/Uu) : hauteur PAR PARCELLE = L≥H, L = max(largeur voie desservante, 10 m).
    # Copie par-parcelle (dataclasses.replace) — la règle de zone partagée n'est JAMAIS mutée.
    if rules.hauteur_mode == 'prospect':
        largeur, src = _facade_largeur(session, parcel_id, ctx.commune)
        L = _prospect_hauteur(largeur)
        rules = replace(rules, hf_m=L, calibree=True,
                        notes=[*rules.notes,
                               f"Hauteur prospect L≥H = {L:.0f} m (largeur chaussée BD TOPO : {src})"])

    # DONNEES-FIX-1 point 4 — les exceptions PLU `modifie_calcul=true` entrent au moteur par le même
    # système (zonage). Une majoration conditionnée à la surface (terrain ≥ seuil) relève la hauteur ;
    # les exceptions non modélisables (bandes, voies nommées, destination…) sont PORTÉES par la parcelle
    # (« règle non modélisée ») sans jamais être approximées. La condition de surface porte sur le
    # terrain d'assiette du projet = la superficie de la parcelle (ctx.surface_m2), pas la portion clippée.
    from .zonage import appliquer_exceptions_calcul
    rules, ctx.regles_non_modelisees = appliquer_exceptions_calcul(
        rules, ctx.commune, ctx.zone, ctx.surface_m2)

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
    # CHASSE-DONNEES-FIX-1 (suite 1, D-50) — recul limites séparatives EN FORMULE « H/2, minimum X » :
    # on NE couple PAS mécaniquement recul=H/2 au moteur. Mesuré (BW2262 503→131, AL1115 313→exigu,
    # AV1095 376→55) : inseter H/2 sur TOUTES les limites effondre la SDP de 74-85 %, car la géométrie
    # de l'enveloppe insète chaque limite, alors que les constructions sont souvent MITOYENNES (recul
    # réel par limite = inconnu). Le moteur garde donc le PLANCHER servi (3 m, affiché « minimum 3 m »)
    # comme borne HAUTE de capacité, et PORTE la formule en « règle non modélisée » : la fiche montre
    # « H/2, minimum 3 m » ET dit que le couplage H/2↔hauteur n'entre pas dans l'estimation (jamais une
    # valeur inventée dans un sens ni dans l'autre).
    _formule_recul = (getattr(rules, "recul_limites_formule", None) or "")
    if "H/2" in _formule_recul and isinstance(rules.hf_m, (int, float)):
        ctx.regles_non_modelisees = list(ctx.regles_non_modelisees or []) + [{
            "regle": "retraits.limites_separatives", "porte": "recul_formule",
            "article": None, "page_pdf": None,
            "texte": (f"Recul limites séparatives = H/2, minimum {recul:g} m (H = hauteur de façade). "
                      "La capacité est estimée au recul minimum (borne haute) : le couplage H/2↔hauteur "
                      "par limite n'est pas modélisé (mitoyenneté inconnue).")}]

    zonage = _layer_params("zonage_plu_gpu")
    presc = _layer_params("prescription_plu")
    pkind = presc.get("spatial_kind", "plu_gpu_prescription")
    er_types = [str(t) for t in presc.get("emplacement_reserve_typepsc", ["05"])]
    ebc_types = [str(t) for t in presc.get("boise_classe_typepsc", ["01"])]
    args = {"pid": parcel_id, "d": recul,
            "zkind": zonage.get("spatial_kind", "plu_gpu_zone"),
            "uau_fams": list(zonage.get("positive_prefixes", ["U", "AU"])),
            "pkind": pkind, "er_types": er_types, "ebc_types": ebc_types}
    # GEOMETRIE-1 lot B — UN SEUL moteur de géométrie (décision Vic 24/09) : l'assiette est la
    # ZONE D'IMPLANTATION du gabarit (reculs par côté, PPR rouge découpé, morceau constructible
    # si à cheval) quand le gabarit sert la parcelle ; sinon chemin legacy inchangé, et la
    # provenance est ÉCRITE (`assiette_source`) — pas de trou, pas de mensonge.
    gab, _blocages = _assiette_gabarit(session, ctx.idu)
    # RESIDUEL-2 — provenance EXACTE : gabarit, repli QUALIFIÉ (motifs purement « limites non
    # qualifiées » → règles provablement appliquées), ou repli NON qualifié (capacité provisoire).
    if gab is not None:
        assiette_source = "gabarit"
    elif _repli_qualifiable(_blocages):
        assiette_source = "residuel_legacy_qualifie"
    else:
        assiette_source = "residuel_legacy"
    # CONTENANCE-1 (Lot C3) — toute aire tirée du DESSIN (zone d'implantation, déductions ER/EBC/
    # greve) est ramenée à l'échelle de la CONTENANCE par ce facteur, pour que rien ne dépasse la
    # surface du terrain et que les proportions tiennent. Les FORMES (GeoJSON, reculs, intersections)
    # restent calculées sur le dessin ; seules leurs AIRES scalaires sont ré-échelonnées ici.
    k_cont = ctx.terrain_sur_dessin
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
        # C3 : aires géométriques → échelle contenance (emprise_brute = zone d'implantation).
        emprise_brute *= k_cont
        er_a *= k_cont; ebc_a *= k_cont; greve_cert *= k_cont; greve_tot *= k_cont
        emprise = max(0.0, emprise_brute - greve_tot)
        racc = gbuild.raccordement or {}
        ppr_rouge = bool((racc.get("ppr") or {}).get("rouge"))
        # PPR-PARTIEL-A lot 2 — garde-fous : la règle (lot 1) calcule désormais l'emprise sur la
        # partie hors zone rouge, mais on ne la SERT que si cette partie est exploitable. On vérifie
        # que le plus grand morceau d'un seul tenant hors rouge fait ≥ 200 m² ET touche une voie ;
        # sinon on ramène l'emprise à 0 AVEC MOTIF (jamais un 0 muet, traité au bloc vide_raison).
        # Ne s'applique qu'aux parcelles dont le 0 tiendrait au PPR rouge (ppr_rouge) : celles bloquées
        # par un ER / EBC / portion U/AU minuscule (FIX-1 §6) gardent leur propre motif plus bas.
        hors_rouge_vide = None
        if ppr_rouge and emprise >= SEUIL_EXIGU_M2:
            servable, hors_rouge_vide = _hors_rouge_fragment_servable(session, parcel_id, k_cont)
            if not servable:
                emprise = 0.0
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
        # RECETTE-1 A1 — raison réelle du vidage (message « trop exigu » ciblé, pas « reculs » partout).
        vide_raison = None
        if emprise < SEUIL_EXIGU_M2:
            if hors_rouge_vide:
                vide_raison = hors_rouge_vide     # garde-fou PPR-PARTIEL-A : partie hors rouge inexploitable
            elif ppr_rouge:
                vide_raison = "ppr_rouge"
            elif emprise_brute >= SEUIL_EXIGU_M2 and greve_tot >= 0.9 * emprise_brute:
                vide_raison = ("emplacement_reserve" if er_a >= max(ebc_a, greve_cert)
                               else "ebc" if ebc_a >= greve_cert else "contraintes")
            elif servie_sur:
                vide_raison = "portion_reduite"
            else:
                vide_raison = "reculs"
    else:
        row = session.execute(_EMPRISE, args).one()
        # C3 : aires géométriques (inset reculs, portion U/AU, ER/EBC) → échelle contenance.
        full_a = float(row.full_area or 0.0) * k_cont
        uau_a = (float(row.uau_area) * k_cont) if row.uau_area is not None else None
        er_a = float(row.er_area or 0.0) * k_cont
        ebc_a = float(row.ebc_area or 0.0) * k_cont
        greve_a_old = float(row.greve_area or 0.0) * k_cont  # union ER∪EBC (ancien 1er retrait)

        base = full_a if uau_a is None else min(full_a, uau_a)
        plancher = float(zonage.get("an_mixte_min_pct", 5)) / 100.0
        if uau_a is not None and full_a > 0 and (full_a - base) / full_a >= plancher:
            ctx.contraintes.libelles.append(
                f"Zonage mixte : emprise constructible clippée à la portion U/AU "
                f"(~{base:.0f} m² retenus sur ~{full_a:.0f} m² insetés).")

        if er_a >= 0.5:
            for r in session.execute(_ER_DETAILS, {"pid": parcel_id, "d": recul,
                                                   "pkind": pkind, "er_types": er_types}):
                m2 = float(r.m2 or 0.0) * k_cont   # C3 : aire ER affichée à l'échelle contenance
                if m2 < 0.5:
                    continue
                m = _ER_LIB.match((r.libelle or "").strip())
                label = f"ER {m.group(1)} : {m.group(2).strip()}" if m else \
                    (f"{r.txt} : {r.libelle}" if r.txt and r.txt != r.libelle else (r.libelle or "ER"))
                ctx.contraintes.libelles.append(
                    f"{label} — {m2:.0f} m² déduits de l'emprise constructible.")
        # SOURCES-1 lot 1 : la part EBC est soustraite de l'assiette (L113-1 CU).
        if ebc_a >= 0.5:
            ctx.contraintes.libelles.append(
                f"Espace boisé classé — {ebc_a:.0f} m² soustraits de l'assiette constructible "
                "(Art. L113-1 CU, aucune construction sur l'emprise boisée).")

        # RESIDUEL-2 — FIN DU DOUBLE RETRAIT. Avant : `base − greve_a` (union ER∪EBC) PUIS
        # `− greve_cert` (union PPR/PEB/DPF/ravine/50 pas) en DEUX soustractions → l'intersection
        # ER∪EBC ∩ PPR… était retranchée deux fois (emprise sous-estimée, faux zéros). Désormais UNE
        # SEULE union de TOUTES les contraintes certaines (`greve_total`), intersectée une fois avec
        # l'assiette — même mécanique que le chemin gabarit. er_a/ebc_a restent affichés comme
        # contributions (elles peuvent se chevaucher) ; seul `greve_total` est réellement soustrait.
        grow = session.execute(_GREVE_LEGACY_UNION, {
            "pid": parcel_id, "d": recul,
            "zkind": zonage.get("spatial_kind", "plu_gpu_zone"),
            "uau_fams": list(zonage.get("positive_prefixes", ["U", "AU"])),
            "pkind": pkind, "er_types": er_types, "ebc_types": ebc_types,
            "peb_ab": [str(z).lower() for z in _layer_params("peb").get("hard_zones", ["a", "b"])],
            "dpf_m": float(_layer_params("dpf").get("marchepied_m", 3.25)),
            "rav_m": float(_layer_params("ravine").get("buffer_m", 10)),
        }).one()
        greve_cert = float(grow.cert_area or 0.0) * k_cont   # part PPR/PEB/DPF/ravine/50 pas (affichage)
        greve_union = float(grow.greve_total or 0.0) * k_cont
        if legacy_union:
            greve_a = greve_union    # déduction NETTE réellement retranchée (union, jamais re-sommée)
            emprise = max(0.0, base - greve_union)
        else:
            # RESIDUEL-2 — seam de MESURE (hors service) : ANCIENNE mécanique du double retrait
            # (base − union(ER∪EBC) PUIS − union(cert), le chevauchement soustrait deux fois).
            greve_a = greve_a_old
            emprise = max(0.0, base - greve_a_old - greve_cert)
        if greve_cert > 0.5:
            ctx.contraintes.libelles.append(
                f"Assiette clippée : {greve_cert:.0f} m² de contraintes géométriques certaines "
                "(PPR rouge, PEB A/B, marchepied DPF, ravine, 50 pas) soustraits de l'emprise — "
                "union globale avec ER/EBC, aucun chevauchement compté deux fois.")
        # RECETTE-1 A1 — raison réelle du vidage (chemin legacy).
        vide_raison = None
        if emprise < SEUIL_EXIGU_M2:
            if full_a < SEUIL_EXIGU_M2:
                vide_raison = "reculs"            # parcelle réellement étroite (inset vide)
            elif base < SEUIL_EXIGU_M2:
                vide_raison = "portion_reduite"   # portion U/AU résiduelle minuscule
            elif er_a >= 0.9 * base:
                vide_raison = "emplacement_reserve"
            elif ebc_a >= 0.9 * base:
                vide_raison = "ebc"
            elif greve_cert >= 0.9 * base:
                vide_raison = "contraintes"
            else:
                vide_raison = "reculs"

    # ── EXIGU-FIX-1 — ré-examen géométrique AVANT de conclure « terrain exigu » ──────────────────
    # Les deux chemins (gabarit, legacy) ont fixé `emprise` et `vide_raison`. Si l'emprise tombe sous
    # le seuil, le code d'origine classait la parcelle `terrain_exigu` (« trop étroit ») — à tort sur
    # de grandes parcelles (effondrement du gabarit, cause mal attribuée : cf. DEPLOY-GROUPE-3 §D).
    # On ré-examine SUR PREUVE GÉOMÉTRIQUE (plus grand morceau d'un seul tenant de l'assiette nette,
    # géométrie réparée) : morceau exploitable → capacité calculée dessus ; prouvé inexploitable →
    # `terrain_exigu` AVEC preuve ; douteux → `assiette_a_verifier` (jamais « trop étroit »).
    # GARDE DE PÉRIMÈTRE : ce bloc ne s'exécute QUE lorsque l'emprise est déjà < seuil (donc une
    # parcelle qui n'aurait pas été `terrain_exigu` n'est jamais touchée → recalcul partiel valide).
    if emprise < SEUIL_EXIGU_M2 and _exigu_fix_actif():
        qargs = {"zkind": zonage.get("spatial_kind", "plu_gpu_zone"),
                 "uau_fams": list(zonage.get("positive_prefixes", ["U", "AU"])),
                 "pkind": pkind, "er_types": er_types, "ebc_types": ebc_types,
                 "peb_ab": [str(z).lower() for z in _layer_params("peb").get("hard_zones", ["a", "b"])],
                 "dpf_m": float(_layer_params("dpf").get("marchepied_m", 3.25)),
                 "rav_m": float(_layer_params("ravine").get("buffer_m", 10))}
        decision, rex = _reexamen_exigu(session, parcel_id, recul, qargs, k_cont)
        ctx.reexamen_exigu = {"decision": decision, **rex}
        if decision == "regain":
            emprise = rex["net_m2"]                     # capacité recalculée sur le morceau exploitable
            vide_raison = None
            assiette_source = "residuel_legacy"         # assiette = inset séparatif (plus la zone d'implant. gabarit)
            ctx.contraintes.libelles.append(
                f"Assiette ré-examinée (EXIGU-FIX-1) : le plus grand morceau d'un seul tenant "
                f"exploitable fait ~{rex['net_m2']:.0f} m² (largeur ~{rex['net_larg']:.0f} m) — "
                "capacité calculée sur ce morceau (le gabarit par côté s'effondrait à tort).")
        elif decision == "verifier":
            vide_raison = "a_verifier"
            ctx.contraintes.libelles.append(
                f"Assiette à vérifier (EXIGU-FIX-1) : aucune emprise nette fiable établie sur une "
                f"parcelle large (~{rex['parc_larg']:.0f} m) — contraintes superposées ou portion "
                "constructible à confirmer. Ni capacité ni « trop étroit » affirmés.")
        else:  # 'exigu' — prouvé inexploitable
            ctx.contraintes.libelles.append(
                f"Terrain exigu confirmé (EXIGU-FIX-1) : plus grand morceau net ~{rex['net_m2']:.0f} m², "
                f"largeur ~{rex['net_larg']:.1f} m — sous le seuil constructible (preuve géométrique).")

    # Surface au sol servant aux plafonds CES/pleine terre : la seule portion U/AU (à cheval).
    # RESIDUEL-1 — inconditionnel (chemin unique).
    surface_assiette = ctx.surface_m2
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
    # total_deduit = déduction NETTE réellement retranchée de l'emprise. RESIDUEL-2 : dans LES DEUX
    # chemins `greve_a` est désormais l'UNION ER∪EBC∪certaines ∩ assiette (gabarit :
    # `_GREVE_SUR_ASSIETTE` ; legacy : `_GREVE_LEGACY_UNION`) — jamais re-sommer avec greve_cert
    # (fin du double retrait). er_m2/ebc_m2/greve_cert ne sont que les CONTRIBUTIONS listées (elles
    # peuvent se chevaucher).
    extras = {"er_m2": er_a, "ebc_m2": ebc_a, "greve_certaine_m2": greve_cert,
              "total_deduit_m2": greve_a,
              "mixite": bool(eco.get("mixite")),
              "assiette_source": assiette_source,
              "assiette_vide": vide_raison}   # RECETTE-1 A1 — raison du vidage (message ciblé)
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
        # CHASSE-CALCULS-FIX-1 Lot 6 (E-C1) — le volume est une EXTRUSION À PLAT (emprise × hauteur) :
        # le terrain naturel (RGE ALTI) n'entre pas dans le volume. On le DIT (pas de mensonge), avec
        # la pente quand elle est connue (sur terrain pentu, le volume réel diffère du bloc affiché).
        "terrain_plat": True,
        "pente_pct": (round(ctx.pente_pct) if getattr(ctx, "pente_pct", None) is not None else None),
        "terrain_note": ("Volume indicatif — terrain supposé plat"
                         + (f" (pente ~{round(ctx.pente_pct)} % non reprise dans le volume)"
                            if getattr(ctx, "pente_pct", None) else "")
                         + "."),
        "note": "Gabarit-enveloppe indicatif : emprise constructible insetée du recul, extrudée à "
                "la hauteur PLU (niveaux × étage). Ni architecture ni implantation réelle ; "
                "terrain supposé plat (le relief n'entre pas dans le volume).",
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
    # RESIDUEL-1 — `res` est clippé (chemin unique) → le bâti retranché l'est sur la même portion
    # U/AU, sinon on soustrait le bâti de la portion A/N d'un plafond U/AU (résiduel faussement nul —
    # piège SCORING-6). Identique au run résiduel de nuit (même moteur, même assiette).
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


# ── PPR-PARTIEL-FIX-1 (lot 1) — la partie HORS zone rouge d'une parcelle partiellement rouge ─────
# PPR-PARTIEL-1 a établi que la règle « touche du rouge → 0 » déduit l'enveloppe réglementaire PPR
# ENTIÈRE (rouge + bleu), rayant à 0 des parcelles U/AU qui gardent des milliers de m² hors rouge
# (AY0786 : 145 m² de rouge sur 4 877 → servie à 0). Cette fonction RÉVÈLE ce reste, sans toucher au
# score ni à la SDP : elle est la SOURCE UNIQUE lue par la fiche, le Dossier et le Copilote (étape B).
#
# Au-dessous de ce seuil, on n'affiche RIEN : le `terrain_exigu` est alors CORRECT (rien à bâtir), et
# l'ancien libellé « trop étroit une fois retirée la zone rouge » reste vrai (PPR-PARTIEL-1 §2).
SEUIL_HORS_PPR_ROUGE_M2 = 200.0

# Mesure géométrique du ROUGE SEUL dans la parcelle — MÊME découpage que le gabarit (builder.py:348-365,
# exclusion `ppr-rouge`) : ST_ClipByBox2D → ST_MakeValid → ST_Union → ST_Intersection. On ne calcule
# PAS une enveloppe, PAS une SDP : l'aire du rouge réel, à retrancher de l'aire de la parcelle.
_HORS_PPR_ROUGE = text(
    "SELECT ST_Area(p.geom_2975) AS parcelle_m2, "
    "       ST_Area(ST_Intersection("
    "         ST_Union(ST_MakeValid(ST_ClipByBox2D(sl.geom_2975, p.geom_2975))), p.geom_2975)) AS rouge_m2 "
    "FROM spatial_layers sl, parcels p "
    "WHERE p.id = :pid AND sl.kind = 'ppr' AND labuse_ppr_couleur(sl.subtype, sl.attrs) <> 'bleu' "
    "  AND ST_Intersects(sl.geom_2975, p.geom_2975) GROUP BY p.geom_2975"
)


def surface_hors_ppr_rouge(session: Session, parcel_id: int, *,
                           faisa: tuple | None = None) -> dict | None:
    """Surface de foncier BRUT hors zone rouge PPR d'une parcelle partiellement rouge servie à 0.

    Rend `{"hors_rouge_m2": int, "pct": int}` (pct = part de la PARCELLE hors rouge) ou None.
    Calculée À LA DEMANDE (pas de run, pas de stockage), elle n'est servie QUE si :
      · la parcelle touche du rouge ET sa SDP servie est 0 POUR CE MOTIF — c.-à-d. le moteur
        conclut `cause == terrain_exigu` / `exigu_raison == ppr_rouge` (la chaîne builder:334-339 →
        db → engine → residuel:136 décrite par PPR-PARTIEL-1). Tout autre 0 (bâti saturé, zone A/N)
        n'est pas un gisement et ne reçoit rien ;
      · le reste hors rouge atteint SEUIL_HORS_PPR_ROUGE_M2 (200 m²) — en deçà, rien (le terrain est
        réellement exigu).
    C'est du FONCIER BRUT : les reculs ne sont PAS appliqués, ce n'est PAS une SDP ni un certificat de
    constructibilité (le libellé le dit). Si le découpage rouge-seul échoue (géométrie invalide, PPR
    superposés pathologiques), on rend None — jamais un chiffre douteux (le cas est compté au rapport).

    `faisa` = (ctx, Faisabilite) déjà calculé par l'appelant (la fiche) → évite de relancer le moteur.
    """
    res = faisa if faisa is not None else parcel_faisabilite(session, parcel_id)
    if res is None:
        return None
    _ctx, f = res
    # Éligibilité = le MOTIF exact du gisement (touche rouge + servi 0 pour terrain_exigu/ppr_rouge).
    if f.cause != "terrain_exigu" or f.exigu_raison != "ppr_rouge":
        return None
    # Découpage rouge-seul isolé dans un SAVEPOINT : une géométrie invalide ne doit JAMAIS casser la
    # transaction de la fiche — on rend None (rien affiché) et le rapport compte l'échec à part.
    try:
        with session.begin_nested():
            row = session.execute(_HORS_PPR_ROUGE, {"pid": parcel_id}).first()
    except Exception:  # noqa: BLE001 — ST_* sur géométrie pathologique : on n'affiche rien, pas un faux
        return None
    if row is None or row.parcelle_m2 is None or float(row.parcelle_m2) <= 0:
        return None
    parcelle_m2 = float(row.parcelle_m2)
    rouge_m2 = float(row.rouge_m2 or 0.0)
    hors_rouge_dessin = max(0.0, parcelle_m2 - rouge_m2)
    # CONTENANCE-1 (règle C3) — la surface hors rouge AFFICHÉE est tirée du dessin : on la ramène à
    # l'échelle de la contenance (× contenance/dessin), comme l'emprise et le seuil servable. Le `pct`
    # (part de la PARCELLE hors rouge) est un rapport de deux aires du dessin → invariant par l'échelle.
    # `getattr` : repli 1.0 (aucune ré-échelle) si le contexte n'expose pas le facteur (pas de contenance).
    k = getattr(_ctx, "terrain_sur_dessin", 1.0)
    hors_rouge_m2 = hors_rouge_dessin * k
    if hors_rouge_m2 < SEUIL_HORS_PPR_ROUGE_M2:
        return None                               # < 200 m² hors rouge : terrain_exigu correct, rien
    return {"hors_rouge_m2": round(hors_rouge_m2),
            "pct": round(100.0 * hors_rouge_dessin / parcelle_m2)}


def phrase_hors_ppr_rouge(hors: dict) -> str:
    """Le libellé CLIENT du gisement — SOURCE UNIQUE (fiche, Dossier §potentiel via verdict_potentiel,
    Copilote). Jamais le mot « constructible » pour cette partie : toujours « à étudier »."""
    m2 = f"{hors['hors_rouge_m2']:,}".replace(",", " ")      # séparateur de milliers en espace (FR)
    return (f"Parcelle touchée par une zone rouge PPR — droits servis à 0 par prudence ; "
            f"partie hors zone rouge : {m2} m², à étudier.")


#: part rouge AU-DELÀ de laquelle la parcelle est ~totalement rouge (vraiment rédhibitoire) : la doctrine
#: PPR-PARTIEL ne s'y applique plus (il ne reste rien d'utile hors rouge).
SEUIL_ROUGE_TOTAL_PCT = 95.0


def verdict_ppr_partiel(session: Session, parcel_id: int) -> dict | None:
    """DOCS-1 (décision Vic) — PPR-PARTIEL, SOURCE UNIQUE du verdict « la zone rouge ne retire QUE sa
    surface ; la partie hors rouge garde son potentiel ».

    Rend `{pct_rouge, pct_hors_rouge, hors_rouge_m2}` quand une parcelle est servie 0/rédhibitoire par le
    run PARCE QU'elle touche une zone rouge PPR PARTIELLE, alors que le reste hors rouge est EXPLOITABLE
    (≥ 200 m² d'un seul tenant touchant une voie — mêmes garde-fous PPR-PARTIEL-A que l'Étude). Rend None
    quand il n'y a pas de rouge, quand la parcelle est ~totalement rouge (≥ 95 %, vraiment rédhibitoire),
    ou quand la partie hors rouge est inexploitable (trop petite / enclavée).

    Lue par TOUS les lecteurs du verdict de potentiel (`potentiel_batir`, le bloc de transformation de la
    fiche, le Comparatif) pour qu'ils disent la MÊME chose que l'Étude de faisabilité, qui découpe déjà le
    rouge et bâtit sur le reste. Lecture seule, tolérante : toute erreur géométrique → None (jamais 500)."""
    try:
        with session.begin_nested():
            row = session.execute(_HORS_PPR_ROUGE, {"pid": parcel_id}).first()
    except Exception:  # noqa: BLE001 — géométrie pathologique : pas de correction, jamais un crash
        return None
    if row is None or row.parcelle_m2 is None or float(row.parcelle_m2) <= 0:
        return None                                   # ne touche AUCUNE zone rouge → rien à corriger
    parcelle = float(row.parcelle_m2)
    rouge = float(row.rouge_m2 or 0.0)
    if rouge <= 0:
        return None
    pct_rouge = 100.0 * rouge / parcelle
    if pct_rouge >= SEUIL_ROUGE_TOTAL_PCT:
        return None                                   # ~totalement rouge → rédhibitoire RÉEL, on n'y touche pas
    servable, _motif = _hors_rouge_fragment_servable(session, parcel_id)
    if not servable:
        return None                                   # partie hors rouge trop petite / enclavée : 0 correct
    # DERNIER GARDE-FOU — le moteur de faisabilité (qui applique TOUTES les contraintes : zonage, ER, EBC,
    # reculs, hauteur, PPR-PARTIEL-A) doit confirmer que la partie hors rouge est RÉELLEMENT constructible.
    # Il écarte les faux positifs : zone A/N, hors PLU, emplacement réservé couvrant tout, etc. (la seule
    # géométrie « il reste du hors-rouge » ne suffit pas). Le stored run, lui, peut être périmé/rédhibitoire.
    try:
        res = parcel_faisabilite(session, parcel_id)
    except Exception:  # noqa: BLE001 — moteur indisponible : prudence, on ne corrige pas
        return None
    if res is None or not res[1].constructible or res[1].cause is not None:
        return None
    return {"pct_rouge": max(1, round(pct_rouge)), "pct_hors_rouge": min(99, round(100.0 - pct_rouge)),
            "hors_rouge_m2": round(parcelle - rouge)}


# ── PPR-PARTIEL-A lot 2 — garde-fous de la partie hors zone rouge ────────────────────────────────
# La règle (lot 1) calcule la SDP sur la partie hors rouge ; mais les 588 ha de foncier BRUT ne sont
# pas tous exploitables. On ne sert QUE si la partie hors rouge forme UN SEUL TENANT (ST_Dump, plus
# grand fragment — les confettis sont ignorés) d'au moins SEUIL_HORS_PPR_ROUGE_M2 (200 m²) ET que ce
# fragment TOUCHE une voie (classification d'arêtes du Gabarit, limites.py). Une partie saine mais
# enclavée derrière le rouge reste à 0. L'emprise max PLU s'applique déjà à la portion hors rouge via
# le gabarit (pm1 n'est plus re-soustraite ; le rouge seul est découpé, builder.py:348-365).
# Le plus grand fragment hors rouge = parcelle − union(INTERDICTION) (PPR superposés déjà unionnés).
_HORS_ROUGE_FRAGMENT = text(
    "WITH rouge AS ("
    "  SELECT ST_Union(ST_MakeValid(ST_ClipByBox2D(sl.geom_2975, p.geom_2975))) AS g "
    "  FROM spatial_layers sl, parcels p WHERE p.id = :pid AND sl.kind='ppr' "
    "  AND labuse_ppr_couleur(sl.subtype, sl.attrs) <> 'bleu' AND ST_Intersects(sl.geom_2975, p.geom_2975)), "
    "hr AS (SELECT ST_Difference(p.geom_2975, COALESCE((SELECT g FROM rouge), "
    "       ST_GeomFromText('POLYGON EMPTY', 2975))) AS g FROM parcels p WHERE p.id = :pid), "
    "dump AS (SELECT (ST_Dump(ST_CollectionExtract(ST_MakeValid(g), 3))).geom AS part FROM hr) "
    "SELECT ST_AsText(part) AS wkt, ST_Area(part) AS m2 "
    "FROM dump ORDER BY ST_Area(part) DESC LIMIT 1"
)


def _hors_rouge_fragment_servable(session: Session, parcel_id: int,
                                  k_cont: float = 1.0) -> tuple[bool, str | None]:
    """Garde-fous PPR-PARTIEL-A lot 2 sur la partie hors zone rouge d'une parcelle partiellement rouge.

    Rend (True, None) si le plus grand morceau d'un seul tenant hors rouge est exploitable, sinon
    (False, motif) — où motif ∈ {hors_rouge_trop_petit, hors_rouge_sans_acces, hors_rouge_invalide},
    qui alimente `vide_raison` et donc le libellé client (jamais un 0 muet). Isolé dans un SAVEPOINT :
    une géométrie pathologique (ST_Difference invalide, PPR superposés) garde 0 et compte le cas.

    CONTENANCE-1 (règle C3) — `k_cont` = contenance/dessin : l'AIRE du fragment est tirée du dessin,
    on la ramène à l'échelle de la contenance (aire_dessin × contenance/dessin) AVANT de la comparer
    au seuil 200 m², comme l'emprise. L'ACCÈS (toucher une voie) reste un test de FORME, sur le dessin.
    """
    from ..gabarit.limites import classify_parcel_limits
    try:
        with session.begin_nested():
            row = session.execute(_HORS_ROUGE_FRAGMENT, {"pid": parcel_id}).first()
    except Exception:  # noqa: BLE001 — géométrie pathologique : 0 conservé, cas compté
        return False, "hors_rouge_invalide"
    if row is None or row.wkt is None or row.m2 is None:
        return False, "hors_rouge_trop_petit"   # hors rouge vide (parcelle ~100 % rouge) → rien à servir
    # 1+2. TENANT + SURFACE : le plus grand fragment d'un seul tenant atteint-il 200 m² (à l'échelle
    # de la contenance — règle C3) ?
    if float(row.m2) * k_cont < SEUIL_HORS_PPR_ROUGE_M2:
        return False, "hors_rouge_trop_petit"
    # 3. ACCÈS : ce fragment touche-t-il une voie (BD TOPO / emprise publique / voie privée) ?
    try:
        with session.begin_nested():
            lim = classify_parcel_limits(session, parcel_id, sub_geom_wkt=row.wkt,
                                         emprises_publiques=True, voies_privees=True)
    except Exception:  # noqa: BLE001
        return False, "hors_rouge_invalide"
    if lim is None or not lim.has_voie:
        return False, "hors_rouge_sans_acces"
    return True, None
