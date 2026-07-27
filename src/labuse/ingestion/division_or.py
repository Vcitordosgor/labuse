"""O12 — DIVISION EN OR : parcelles où le bâti occupe un coin et laisse un résiduel DÉTACHABLE constructible.

FAUX POSITIF = PÉCHÉ MORTEL. Cet outil est livré **MASQUÉ** ; le livrable qui autorise l'exposition est un
**dossier de revue 20 cartes** validé VISUELLEMENT par Vic (pattern J3). Ici : le détecteur géométrique
conservateur + la table masquée `division_or_candidates`.

Géométrie (EPSG:2975, mètres) — seuils CONSERVATEURS :
  · parcelle ≥ 1000 m² (place pour DEUX lots viables) ;
  · bâti entre 8 % et 45 % de la parcelle (il y a un bâti, mais il ne remplit pas) ;
  · résiduel = plus grand polygone de (parcelle − bâti bufferisé 3 m) ;
  · résiduel entre 500 m² et (surface − 400) m² → le lot BÂTI conserve ≥ 400 m² (les deux lots restent viables) ;
  · **cercle inscrit du résiduel ≥ 9 m de rayon** (largeur ~18 m constructible, pas une lanière) ;
  · **façade voirie du résiduel ≥ 12 m** (accès INDÉPENDANT — le vrai discriminant) ;
  · **lot ≤ 50 % de la parcelle** (revue O12-ÎLE : un « lot » qui emporte presque toute la parcelle
    est un démembrement, pas une division — ex. 4 748 m² détachés de 5 433 m²) ;
  · **zonage du lot : U ou AU exigé** (revue O12-ÎLE : une division urbaine n'a pas de sens en zone
    A ou N). Zone dominante (plus grande intersection) du LOT dans `plu_gpu_zone` ; commune sans
    document (RNU) → lot gardé seulement si la parcelle est dans la PAU estimée (`parcel_pau`).
Deux TYPES de division (O12-ÎLE D — le bâti dans le lot est CLASSÉ, pas exclu) :
  · **libre** : lot nu (tout le bâti retiré du calcul du résiduel) — prioritaire au tri ;
  · **demolition** : seul le bâtiment PRINCIPAL (plus grande emprise au sol) est retiré — le lot
    peut contenir du bâti SECONDAIRE, chiffré (« dont N m² à démolir »). Garde anti-découpage
    inversé : le principal n'est JAMAIS dans le lot (par construction) ET le bâti à démolir pèse
    au plus la moitié du bâti conservé (`bati_lot × 3 ≤ bati_total`) — sinon rejet.
    Une parcelle qui passe en libre reste libre (la variante démolition ne la remplace pas).
L'accès restant du lot BÂTI est jugé VISUELLEMENT en revue : la métrique automatique tentée
(façade_parcelle − façade_lot) s'est révélée invalide (valeurs négatives, artefact de la frontière
découpée) — on ne filtre pas sur un chiffre faux (finding O12).
Score de clarté : la façade voirie y est PLAFONNÉE à 30 m (revue O12-ÎLE : une façade de 465 m
est une bande linéaire le long d'une route, pas un candidat plus clair).

Rien n'est affirmé sur la constructibilité réglementaire (recul, prospect, servitudes) : le détecteur repère un
POTENTIEL géométrique, la revue humaine tranche. Gain estimé branché sur le Score É V2 (Estimé). Zéro donnée nouvelle.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

EXPOSE = False   # MASQUÉ jusqu'à validation visuelle Vic (dossier 20 cartes)

DDL = """
CREATE TABLE IF NOT EXISTS division_or_candidates (
  idu           varchar(14) PRIMARY KEY,
  commune       varchar(64),
  surface_m2    int,
  bati_m2       int,
  bati_ratio    numeric(4,3),
  residuel_m2   int,
  residuel_rayon_m numeric(5,1),
  residuel_facade_m numeric(5,1),
  bati_facade_m numeric(5,1),
  zone          varchar(8),      -- zone dominante du lot (U/AU/AUc/AUs) ; NULL = commune RNU (PAU estimée)
  type_division varchar(12),     -- 'libre' (lot nu) | 'demolition' (bâti secondaire dans le lot)
  bati_lot_m2   int,             -- bâti contenu dans le lot (« dont N m² à démolir » ; 0 si libre)
  gain_estime_eur int,           -- via Score É V2 si dispo (Estimé), sinon NULL
  clarte        numeric(5,1),    -- score de clarté géométrique (tri du dossier de revue)
  computed_at   timestamptz DEFAULT now()
);
ALTER TABLE division_or_candidates ADD COLUMN IF NOT EXISTS zone varchar(8);
ALTER TABLE division_or_candidates ADD COLUMN IF NOT EXISTS type_division varchar(12);
ALTER TABLE division_or_candidates ADD COLUMN IF NOT EXISTS bati_lot_m2 int;
"""

# Détection pour UNE commune (batch raisonnable). Buffers/seuils = constantes ci-dessus.
_DETECT = """
WITH cand AS (
  SELECT p.id, p.idu, p.commune, p.geom_2975, p.surface_m2 FROM parcels p
  WHERE p.commune = :commune AND p.surface_m2 BETWEEN 1000 AND 6000
    AND EXISTS (SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975))),
bldg AS (
  SELECT c.id, b.geom_2975 AS g, ST_Area(ST_Intersection(b.geom_2975, c.geom_2975)) AS a
  FROM cand c JOIN spatial_layers b ON b.kind='batiment' AND ST_Intersects(b.geom_2975, c.geom_2975)),
bat AS (SELECT id, ST_Union(g) AS bgeom, sum(a) AS bat_m2, count(*) AS nb_bat FROM bldg GROUP BY id),
-- bâtiment PRINCIPAL = plus grande emprise au sol sur la parcelle — JAMAIS dans le lot proposé
princ AS (SELECT DISTINCT ON (id) id, g AS pgeom FROM bldg ORDER BY id, a DESC),
-- deux variantes de lot : LIBRE (tout le bâti retiré — le lot est nu) ; DÉMOLITION (seul le
-- principal est retiré — le lot peut contenir du bâti SECONDAIRE, chiffré « à démolir »).
-- Parcelle mono-bâtiment : les variantes coïncident, la variante démolition est sautée.
freed AS (
  SELECT c.id, c.idu, c.commune, c.surface_m2, c.geom_2975, bat.bat_m2, v.variante,
         lg.geom AS free_geom, ST_Area(lg.geom) AS free_m2,
         (ST_MaximumInscribedCircle(lg.geom)).radius AS rad
  FROM cand c JOIN bat ON bat.id = c.id JOIN princ ON princ.id = c.id
  CROSS JOIN LATERAL (VALUES ('libre', bat.bgeom), ('demolition', princ.pgeom)) AS v(variante, sub)
  CROSS JOIN LATERAL (SELECT g.geom FROM ST_Dump(ST_Difference(c.geom_2975, ST_Buffer(v.sub, 3))) g
                      ORDER BY ST_Area(g.geom) DESC LIMIT 1) lg
  WHERE bat.bat_m2 / c.surface_m2 BETWEEN 0.08 AND 0.45
    AND NOT (v.variante = 'demolition' AND bat.nb_bat = 1)),
-- façade voirie du LOT détaché — le filtre d'accès (indépendant ≥ 12 m)
-- + borne lot/parcelle ≤ 50 % (au-delà c'est un démembrement, pas une division — revue O12-ÎLE)
acces AS (
  SELECT *,
    (SELECT coalesce(sum(ST_Length(ST_Intersection(ST_Buffer(v.geom_2975,1.5), ST_Boundary(free_geom)))),0)
       FROM spatial_layers v WHERE v.kind='voirie' AND ST_DWithin(v.geom_2975, free_geom, 2)) AS facade_free
  FROM freed
  WHERE free_m2 >= 500 AND free_m2 <= surface_m2 - 400 AND free_m2 <= surface_m2 * 0.5 AND rad >= 9),
-- bâti contenu dans le lot proposé (0 par construction en variante libre) → « dont N m² à démolir »
demol AS (
  SELECT a.*, CASE WHEN a.variante = 'libre' THEN 0 ELSE coalesce(
      (SELECT round(sum(ST_Area(ST_Intersection(b.g, a.free_geom))))::int
       FROM bldg b WHERE b.id = a.id), 0) END AS bati_lot_m2
  FROM acces a),
-- zone dominante du LOT (plus grande intersection avec plu_gpu_zone) — U/AU gardés, A/N exclus ;
-- NULL (commune RNU sans document) → gardé seulement si la parcelle est dans la PAU estimée
zon AS (
  SELECT d.*, z.subtype AS zone
  FROM demol d
  LEFT JOIN LATERAL (
    SELECT z2.subtype FROM spatial_layers z2
    WHERE z2.kind='plu_gpu_zone' AND ST_Intersects(z2.geom_2975, d.free_geom)
    ORDER BY ST_Area(ST_Intersection(z2.geom_2975, d.free_geom)) DESC LIMIT 1) z ON true)
SELECT DISTINCT ON (idu)
       idu, commune, round(surface_m2)::int surface_m2, round(bat_m2)::int bati_m2,
       round((bat_m2/surface_m2)::numeric,3) bati_ratio, round(free_m2)::int residuel_m2,
       round(rad::numeric,1) residuel_rayon_m, round(facade_free::numeric,1) residuel_facade_m,
       NULL::numeric AS bati_facade_m,  -- accès du lot BÂTI : jugé VISUELLEMENT en revue (métrique
                                        -- façade_parcelle − façade_lot invalidée : négative, artefact
                                        -- de la frontière découpée — finding O12, pas de chiffre faux)
       zone,
       CASE WHEN bati_lot_m2 < 1 THEN 'libre' ELSE 'demolition' END AS type_division,
       bati_lot_m2
FROM zon
WHERE facade_free >= 12
  AND (zone = 'U' OR zone LIKE 'AU%' OR (zone IS NULL AND ({pau_pred})))
  AND (variante = 'libre' OR bati_lot_m2 * 3 <= bat_m2)
ORDER BY idu, (variante = 'demolition'), free_m2 DESC;
"""


# INSERT ... SELECT : détection + gain (Score É) + clarté en UNE passe SQL (pas de boucle Python par ligne).
_INSERT = """
INSERT INTO division_or_candidates (idu, commune, surface_m2, bati_m2, bati_ratio,
    residuel_m2, residuel_rayon_m, residuel_facade_m, bati_facade_m, zone,
    type_division, bati_lot_m2, gain_estime_eur, clarte)
SELECT d.idu, d.commune, d.surface_m2, d.bati_m2, d.bati_ratio, d.residuel_m2,
       d.residuel_rayon_m, d.residuel_facade_m, d.bati_facade_m, d.zone,
       d.type_division, d.bati_lot_m2,
       se.marge_estimee,
       round((d.residuel_rayon_m * 2 + LEAST(d.residuel_facade_m, 30))::numeric, 1) AS clarte
FROM ({detect}) d
LEFT JOIN score_e se ON se.idu = d.idu AND se.estimable
ON CONFLICT (idu) DO UPDATE SET commune=EXCLUDED.commune, surface_m2=EXCLUDED.surface_m2,
    bati_m2=EXCLUDED.bati_m2, bati_ratio=EXCLUDED.bati_ratio, residuel_m2=EXCLUDED.residuel_m2,
    residuel_rayon_m=EXCLUDED.residuel_rayon_m, residuel_facade_m=EXCLUDED.residuel_facade_m,
    bati_facade_m=EXCLUDED.bati_facade_m, zone=EXCLUDED.zone,
    type_division=EXCLUDED.type_division, bati_lot_m2=EXCLUDED.bati_lot_m2,
    gain_estime_eur=EXCLUDED.gain_estime_eur, clarte=EXCLUDED.clarte, computed_at=now()
"""


def build_divisions(session: Session, communes: list[str], *, commit: bool = True, log=lambda *_: None) -> dict:
    """Détecte les candidats division-en-or pour une liste de communes. Table MASQUÉE (flag EXPOSE=False).
    Une passe SQL par commune (détection + gain Score É + clarté), pas de boucle Python par ligne."""
    session.execute(text(DDL))
    has_score_e = session.execute(text("SELECT to_regclass('score_e')")).scalar() is not None
    # PAU estimée (mandat RNU) : si la table existe, une commune SANS zonage garde ses candidats
    # dans la PAU ; sinon (base sans branche RNU) un lot sans zone est simplement exclu.
    has_pau = session.execute(text("SELECT to_regclass('parcel_pau')")).scalar() is not None
    pau_pred = "EXISTS (SELECT 1 FROM parcel_pau pp WHERE pp.idu = zon.idu)" if has_pau else "false"
    detect = _DETECT.format(pau_pred=pau_pred).strip().rstrip(";")
    if has_score_e:
        insert_sql = _INSERT.format(detect=detect)
    else:   # pas de Score É → gain NULL, sans jointure
        insert_sql = _INSERT.replace("se.marge_estimee,", "NULL::int,").replace(
            "LEFT JOIN score_e se ON se.idu = d.idu AND se.estimable", "").format(detect=detect)
    total = 0
    for commune in communes:
        session.execute(text(insert_sql), {"commune": commune})
        n = session.execute(text("SELECT count(*) FROM division_or_candidates WHERE commune = :c"),
                            {"c": commune}).scalar()
        total = session.execute(text("SELECT count(*) FROM division_or_candidates")).scalar()
        log(f"division-or {commune} : {n} candidats")
    if commit:
        session.commit()
    log(f"division_or_candidates : {total} candidats (MASQUÉ — attend le dossier de revue Vic)")
    return {"total": total, "expose": EXPOSE}


def top_candidates(session: Session, *, limit: int = 20, communes: list[str] | None = None,
                   type_division: str | None = None) -> list[dict]:
    """Les meilleurs candidats pour le dossier de revue 20 cartes — divisions LIBRES d'abord
    (le cas classique), puis clarté géométrique décroissante.
    `communes` : échantillonnage ÉQUILIBRÉ en tourniquet — le rang-1 de chaque commune, puis les
    rang-2, etc. ; une commune à court de candidats est compensée par les autres.
    `type_division` : restreint à 'libre' ou 'demolition' (dossier de revue dédié à un type)."""
    if session.execute(text("SELECT to_regclass('division_or_candidates')")).scalar() is None:
        return []
    where = "WHERE type_division = :type" if type_division else ""
    params: dict = {"lim": limit}
    if type_division:
        params["type"] = type_division
    tri = "(type_division = 'demolition'), clarte DESC, residuel_m2 DESC"
    if not communes:
        rows = session.execute(text(
            f"SELECT * FROM division_or_candidates {where} ORDER BY {tri} LIMIT :lim"),
            params).mappings().all()
        return [dict(r) for r in rows]
    where = (where + " AND" if where else "WHERE") + " commune = ANY(:communes)"
    params["communes"] = communes
    rows = session.execute(text(
        f"""
        SELECT * FROM (
          SELECT c.*, row_number() OVER (PARTITION BY commune ORDER BY {tri}) rn
          FROM division_or_candidates c {where}) t
        ORDER BY rn, {tri} LIMIT :lim
        """), params).mappings().all()
    return [{k: v for k, v in dict(r).items() if k != "rn"} for r in rows]
