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
  · **façade voirie du résiduel ≥ 12 m** (accès INDÉPENDANT — le vrai discriminant).
L'accès restant du lot BÂTI est jugé VISUELLEMENT en revue : la métrique automatique tentée
(façade_parcelle − façade_lot) s'est révélée invalide (valeurs négatives, artefact de la frontière
découpée) — on ne filtre pas sur un chiffre faux (finding O12).

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
  gain_estime_eur int,           -- via Score É V2 si dispo (Estimé), sinon NULL
  clarte        numeric(5,1),    -- score de clarté géométrique (tri du dossier de revue)
  computed_at   timestamptz DEFAULT now()
);
"""

# Détection pour UNE commune (batch raisonnable). Buffers/seuils = constantes ci-dessus.
_DETECT = """
WITH cand AS (
  SELECT p.id, p.idu, p.commune, p.geom_2975, p.surface_m2 FROM parcels p
  WHERE p.commune = :commune AND p.surface_m2 BETWEEN 1000 AND 6000
    AND EXISTS (SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975))),
bat AS (
  SELECT c.id, ST_Union(b.geom_2975) AS bgeom,
         sum(ST_Area(ST_Intersection(b.geom_2975, c.geom_2975))) AS bat_m2
  FROM cand c JOIN spatial_layers b ON b.kind='batiment' AND ST_Intersects(b.geom_2975, c.geom_2975)
  GROUP BY c.id),
freed AS (
  SELECT c.id, c.idu, c.commune, c.surface_m2, c.geom_2975, bat.bgeom, bat.bat_m2,
         lg.geom AS free_geom, ST_Area(lg.geom) AS free_m2,
         (ST_MaximumInscribedCircle(lg.geom)).radius AS rad
  FROM cand c JOIN bat ON bat.id = c.id
  CROSS JOIN LATERAL (SELECT g.geom FROM ST_Dump(ST_Difference(c.geom_2975, ST_Buffer(bat.bgeom, 3))) g
                      ORDER BY ST_Area(g.geom) DESC LIMIT 1) lg
  WHERE bat.bat_m2 / c.surface_m2 BETWEEN 0.08 AND 0.45),
-- façade voirie du LOT détaché — le filtre d'accès (indépendant ≥ 12 m)
acces AS (
  SELECT *,
    (SELECT coalesce(sum(ST_Length(ST_Intersection(ST_Buffer(v.geom_2975,1.5), ST_Boundary(free_geom)))),0)
       FROM spatial_layers v WHERE v.kind='voirie' AND ST_DWithin(v.geom_2975, free_geom, 2)) AS facade_free
  FROM freed
  WHERE free_m2 >= 500 AND free_m2 <= surface_m2 - 400 AND rad >= 9)
SELECT idu, commune, round(surface_m2)::int surface_m2, round(bat_m2)::int bati_m2,
       round((bat_m2/surface_m2)::numeric,3) bati_ratio, round(free_m2)::int residuel_m2,
       round(rad::numeric,1) residuel_rayon_m, round(facade_free::numeric,1) residuel_facade_m,
       NULL::numeric AS bati_facade_m   -- accès du lot BÂTI : jugé VISUELLEMENT en revue (métrique
                                        -- façade_parcelle − façade_lot invalidée : négative, artefact
                                        -- de la frontière découpée — finding O12, pas de chiffre faux)
FROM acces
WHERE facade_free >= 12;
"""


# INSERT ... SELECT : détection + gain (Score É) + clarté en UNE passe SQL (pas de boucle Python par ligne).
_INSERT = """
INSERT INTO division_or_candidates (idu, commune, surface_m2, bati_m2, bati_ratio,
    residuel_m2, residuel_rayon_m, residuel_facade_m, bati_facade_m, gain_estime_eur, clarte)
SELECT d.idu, d.commune, d.surface_m2, d.bati_m2, d.bati_ratio, d.residuel_m2,
       d.residuel_rayon_m, d.residuel_facade_m, d.bati_facade_m,
       se.marge_estimee,
       round((d.residuel_rayon_m * 2 + d.residuel_facade_m)::numeric, 1) AS clarte
FROM ({detect}) d
LEFT JOIN score_e se ON se.idu = d.idu AND se.estimable
ON CONFLICT (idu) DO UPDATE SET commune=EXCLUDED.commune, surface_m2=EXCLUDED.surface_m2,
    bati_m2=EXCLUDED.bati_m2, bati_ratio=EXCLUDED.bati_ratio, residuel_m2=EXCLUDED.residuel_m2,
    residuel_rayon_m=EXCLUDED.residuel_rayon_m, residuel_facade_m=EXCLUDED.residuel_facade_m,
    bati_facade_m=EXCLUDED.bati_facade_m, gain_estime_eur=EXCLUDED.gain_estime_eur,
    clarte=EXCLUDED.clarte, computed_at=now()
"""


def build_divisions(session: Session, communes: list[str], *, commit: bool = True, log=lambda *_: None) -> dict:
    """Détecte les candidats division-en-or pour une liste de communes. Table MASQUÉE (flag EXPOSE=False).
    Une passe SQL par commune (détection + gain Score É + clarté), pas de boucle Python par ligne."""
    session.execute(text(DDL))
    has_score_e = session.execute(text("SELECT to_regclass('score_e')")).scalar() is not None
    detect = _DETECT.strip().rstrip(";")
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


def top_candidates(session: Session, *, limit: int = 20) -> list[dict]:
    """Les meilleurs candidats (clarté géométrique décroissante) pour le dossier de revue 20 cartes."""
    if session.execute(text("SELECT to_regclass('division_or_candidates')")).scalar() is None:
        return []
    rows = session.execute(text(
        "SELECT * FROM division_or_candidates ORDER BY clarte DESC, residuel_m2 DESC LIMIT :lim"),
        {"lim": limit}).mappings().all()
    return [dict(r) for r in rows]
