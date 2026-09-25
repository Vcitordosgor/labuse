"""PISCINES-2 — source UNIQUE fusionnée `piscines` : FLAIR ∪ CoSIA dédoublonnées (jointure spatiale
5 m). Remplace la lecture des deux couches historiques (`parcel_equipements` piscine servie par
l'outil, `tuyau_piscines` kind `piscine_cosia` de la carte) — qui restent en base, mais ne sont plus
lues ni par l'outil Piscines ni par la carte.

RÈGLE DE FUSION issue de la MESURE (échantillon aléatoire 30/classe, seed `p2seed7`, vérif ortho —
cf. docs/audit-2026-09/piscines-2/) : une classe est `servie` si précision mesurée ≥ 85 %,
`a_confirmer` entre 50 et 85 %, `ecartee` en dessous. Le plancher de surface 8 m² sépare le bruit
(CoSIA `probable` < 8 m² = 4 % de vraies) de l'ambigu (`probable` ≥ 8 m² = 60 %).

  classe                       précision mesurée   statut
  flair_haute (≥0,80)          100 %               servie
  flair_incertaine (<0,80)      90–96 %            servie
  cosia_confirmee (avec FLAIR) 100 %               servie   (concordance = confirmation)
  cosia_confirmee (sans FLAIR)  87–100 %           servie
  cosia_rare                    13–20 %            ecartee
  cosia_probable ≥ 8 m²         30–60 %            a_confirmer
  cosia_probable < 8 m²          3–4 %             ecartee

Les corrections « pas une piscine » (`piscine_corrections`, par idu) s'appliquent à cette table.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import load_yaml_config

# Plancher de surface (m²) qui sépare `probable` bruit (< 8) de `probable` ambigu (≥ 8) — justifié par
# la distribution mesurée, pas posé (cf. entête).
PROBABLE_FLOOR_M2 = 8.0
DEDUP_M = 5.0   # deux détections à ≤ 5 m = la même piscine (jointure spatiale)

MILL_FLAIR = "Ortho Express RVB 20 cm 2025 (IGN) · détection FLAIR"
MILL_COSIA = "CoSIA IA 20 cm 2025 (IGN)"

DDL = """
CREATE TABLE IF NOT EXISTS piscines (
  id               serial PRIMARY KEY,
  idu              varchar(14),                       -- parcelle (jointure spatiale ; NULL hors parcelle)
  commune          varchar,
  surface_m2       double precision,
  source           text NOT NULL,                     -- 'flair' | 'cosia' | 'flair+cosia'
  classe           text NOT NULL,                     -- flair_haute|flair_incertaine|cosia_confirmee|cosia_rare|cosia_probable
  statut           text NOT NULL,                     -- 'servie' | 'a_confirmer' | 'ecartee'
  confiance        double precision,                  -- FLAIR : confiance composite ; CoSIA : NULL
  geom             geometry(Point, 4326),
  geom_2975        geometry(Point, 2975),
  millesime_flair  text,
  millesime_cosia  text,
  built_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_piscines_geom2975 ON piscines USING gist (geom_2975);
CREATE INDEX IF NOT EXISTS ix_piscines_idu ON piscines (idu);
CREATE INDEX IF NOT EXISTS ix_piscines_statut ON piscines (statut, commune);
"""


def ensure(session: Session) -> None:
    session.execute(text(DDL))


def build(session: Session, log=print) -> dict[str, Any]:
    """Reconstruit `piscines` (idempotent : DELETE + rebuild). NE S'EXÉCUTE PAS tout seul — lancé par
    `labuse piscines-build` (doctrine d'injection sur clic humain)."""
    ensure(session)
    j = load_yaml_config("detection_ortho")["materialisation"]["juge"]
    fmin, pmin = j["flair_min"], j["probe_min"]
    session.execute(text("DELETE FROM piscines"))

    # FLAIR servi (même porte que la matérialisation parcel_equipements) : point de centroïde + confiance.
    session.execute(text("""
        CREATE TEMP TABLE _f AS
        SELECT d.id, d.idu, ST_Centroid(d.geom_2975) AS g2975, ST_Centroid(d.geom) AS g4326,
               d.surface_m2, d.confiance
        FROM ortho_detections d
        WHERE d.type = 'piscine'
          AND (d.validation = 'ok'
               OR (d.validation IS NULL AND d.juge_flair >= :fmin AND d.probe_score >= :pmin))
    """), {"fmin": fmin, "pmin": pmin})
    session.execute(text("CREATE INDEX ON _f USING gist (g2975)"))

    # 1) Les lignes FLAIR (une par détection retenue). source 'flair+cosia' si une CoSIA la double à ≤5 m.
    n_flair = session.execute(text("""
        INSERT INTO piscines (idu, commune, surface_m2, source, classe, statut, confiance,
                              geom, geom_2975, millesime_flair, millesime_cosia)
        SELECT f.idu, p.commune, f.surface_m2,
               CASE WHEN EXISTS (SELECT 1 FROM tuyau_piscines t
                                 WHERE ST_DWithin(t.geom_2975, f.g2975, :dedup))
                    THEN 'flair+cosia' ELSE 'flair' END AS source,
               CASE WHEN f.confiance >= 0.80 THEN 'flair_haute' ELSE 'flair_incertaine' END AS classe,
               'servie' AS statut, f.confiance,
               f.g4326, f.g2975, :mflair,
               CASE WHEN EXISTS (SELECT 1 FROM tuyau_piscines t
                                 WHERE ST_DWithin(t.geom_2975, f.g2975, :dedup))
                    THEN :mcosia ELSE NULL END
        FROM _f f LEFT JOIN parcels p ON p.idu = f.idu
    """), {"dedup": DEDUP_M, "mflair": MILL_FLAIR, "mcosia": MILL_COSIA}).rowcount
    log(f"  FLAIR servi : {n_flair} piscines")

    # 2) Les CoSIA SANS FLAIR à ≤5 m (les concordances sont déjà portées par les lignes FLAIR ci-dessus).
    #    idu par jointure spatiale au cadastre (centroïde ∈ parcelle) ; statut selon la règle mesurée.
    n_cosia = session.execute(text("""
        INSERT INTO piscines (idu, commune, surface_m2, source, classe, statut, confiance,
                              geom, geom_2975, millesime_flair, millesime_cosia)
        SELECT p.idu, t.commune, (t.attrs->>'surface_m2')::numeric,
               'cosia' AS source,
               CASE t.subtype WHEN 'confirmee' THEN 'cosia_confirmee'
                              WHEN 'rare' THEN 'cosia_rare'
                              ELSE 'cosia_probable' END AS classe,
               CASE
                 WHEN t.subtype = 'confirmee' THEN 'servie'
                 WHEN t.subtype = 'rare' THEN 'ecartee'
                 WHEN t.subtype = 'probable' AND (t.attrs->>'surface_m2')::numeric >= :floor THEN 'a_confirmer'
                 ELSE 'ecartee' END AS statut,
               NULL,
               ST_Transform(ST_Centroid(t.geom_2975), 4326), ST_Centroid(t.geom_2975),
               NULL, :mcosia
        FROM tuyau_piscines t
        LEFT JOIN parcels p ON ST_Intersects(p.geom_2975, ST_Centroid(t.geom_2975))
        WHERE NOT EXISTS (SELECT 1 FROM _f f WHERE ST_DWithin(f.g2975, t.geom_2975, :dedup))
    """), {"dedup": DEDUP_M, "floor": PROBABLE_FLOOR_M2, "mcosia": MILL_COSIA}).rowcount
    log(f"  CoSIA sans FLAIR : {n_cosia} piscines")

    session.execute(text("DROP TABLE IF EXISTS _f"))
    stats = dict(session.execute(text(
        "SELECT statut, count(*) FROM piscines GROUP BY statut")).all())
    total = int(session.execute(text("SELECT count(*) FROM piscines")).scalar() or 0)
    log(f"  total {total} · servie {stats.get('servie',0)} · a_confirmer {stats.get('a_confirmer',0)} · ecartee {stats.get('ecartee',0)}")
    return {"total": total, "flair": n_flair, "cosia": n_cosia, "par_statut": stats}
