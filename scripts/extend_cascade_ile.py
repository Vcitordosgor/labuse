#!/usr/bin/env python3
"""Extension cascade île (mandat 08/07/2026) — les 3 couches d'exclusion de Saint-Paul
appliquées aux 24 communes, en SET-BASED (équivalent à un re-run : couches indépendantes).

Étapes :
  prove-sp   Génère les verdicts de Saint-Paul avec le générateur SQL et les compare aux
             51 129 × 3 lignes STOCKÉES → ZÉRO écart exigé (c'est LA preuve de fidélité).
  extend     Backfill des 23 autres communes (idempotent par commune : DELETE des 3 couches
             puis INSERT) + nullification des poids des parcelles NOUVELLEMENT exclues
             (sémantique weights=[0]* du moteur : une parcelle exclue n'a aucun poids).
Ensuite (hors script) : labuse matrice-apply (matrice ×24 + MVT + tops + entonnoir).

Règles = celles de src/labuse/cascade/layers/etage0_ext.py (extraites des verdicts SP).
"""
from __future__ import annotations

import sys

import psycopg

DB = "postgresql://openclaw@127.0.0.1:5432/labuse"
RUN = "q_v2"
LAYERS = ("foncier_public", "emprise_lineaire", "residuel_socle")

#: générateur SQL des 3 couches pour UNE commune → lignes (parcel_id, layer, result, severity,
#: weight, detail, source_table, source_id). Formats IDENTIQUES à etage0_ext.py.
GEN_SQL = """
WITH parc AS (
  SELECT p.id, p.idu, p.geom_2975 FROM parcels p WHERE p.commune = %(c)s
),
own AS (
  SELECT parc.id, pm.groupe, pm.groupe_label, pm.denomination
  FROM parc LEFT JOIN parcelle_personne_morale pm ON pm.idu = parc.idu
),
fp AS (
  SELECT id AS parcel_id, 'foncier_public' AS layer_name,
    CASE WHEN groupe IN (1,2,3,4,9) THEN 'HARD_EXCLUDE' ELSE 'PASS' END AS result,
    NULL::text AS severity, NULL::float AS weight,
    CASE
      WHEN groupe IN (1,2,3,4,9) THEN
        'Propriété publique (' || denomination || ') — non acquérable [classification DGFiP groupe '
        || groupe || ' : ' || CASE groupe WHEN 1 THEN 'État' WHEN 2 THEN 'Région'
             WHEN 3 THEN 'Département' WHEN 4 THEN 'Commune'
             ELSE 'Établissements publics ou organismes associés' END || '].'
      WHEN groupe IS NOT NULL THEN
        'Propriétaire PM « ' || groupe_label || ' » (groupe ' || groupe || ') — acquérable.'
      ELSE 'Propriétaire non public (personne physique ou PM privée).'
    END AS detail,
    NULL::text AS source_table, NULL::text AS source_id
  FROM own
),
env AS (
  SELECT parc.id, c1, c2, LEAST(c1, c2) AS w,
         CASE WHEN LEAST(c1, c2) > 0 THEN GREATEST(c1, c2) / LEAST(c1, c2) END AS r
  FROM parc
  CROSS JOIN LATERAL (SELECT ST_OrientedEnvelope(parc.geom_2975) AS g) e
  CROSS JOIN LATERAL (
    SELECT CASE WHEN GeometryType(e.g) = 'POLYGON'
                THEN ST_Distance(ST_PointN(ST_ExteriorRing(e.g),1), ST_PointN(ST_ExteriorRing(e.g),2)) END AS c1,
           CASE WHEN GeometryType(e.g) = 'POLYGON'
                THEN ST_Distance(ST_PointN(ST_ExteriorRing(e.g),2), ST_PointN(ST_ExteriorRing(e.g),3)) END AS c2) d
),
el AS (
  SELECT id AS parcel_id, 'emprise_lineaire' AS layer_name,
    CASE WHEN w IS NULL OR r IS NULL THEN 'PASS'
         WHEN w < 8 AND r > 8 THEN 'HARD_EXCLUDE' ELSE 'PASS' END AS result,
    NULL::text AS severity, NULL::float AS weight,
    CASE WHEN w IS NULL OR r IS NULL THEN 'Forme non évaluable (géométrie dégénérée).'
         WHEN w < 8 AND r > 8 THEN
           'Emprise linéaire — voirie/délaissé probable (largeur ' || round(w)::int
           || ' m < 8 m ET allongement ' || round(r)::int || '× > 8×).'
         ELSE 'Forme non linéaire (largeur ' || round(w)::int || ' m, allongement '
              || round(r::numeric, 1) || '×).'
    END AS detail,
    NULL::text AS source_table, NULL::text AS source_id
  FROM env
),
res AS (
  SELECT parc.id AS parcel_id, 'residuel_socle' AS layer_name,
    CASE WHEN pr.sdp_residuelle_m2 IS NULL THEN 'UNKNOWN'
         WHEN pr.sdp_residuelle_m2 >= 300 THEN 'POSITIVE' ELSE 'SOFT_FLAG' END AS result,
    CASE WHEN pr.sdp_residuelle_m2 IS NOT NULL AND pr.sdp_residuelle_m2 < 300 THEN 'info' END AS severity,
    CASE WHEN pr.sdp_residuelle_m2 IS NULL THEN NULL
         WHEN pr.sdp_residuelle_m2 >= 5000 THEN 30 WHEN pr.sdp_residuelle_m2 >= 2000 THEN 25
         WHEN pr.sdp_residuelle_m2 >= 800 THEN 15 WHEN pr.sdp_residuelle_m2 >= 300 THEN 5
         WHEN pr.sdp_residuelle_m2 >= 100 THEN -10 ELSE -25 END::float AS weight,
    CASE WHEN pr.sdp_residuelle_m2 IS NULL THEN
      'SDP résiduelle non calculée — droits à construire inconnus (hors couverture parcel_residuel) ; à résoudre par extension du calcul, pas un signal d''absence de droits.'
    ELSE 'SDP résiduelle ' || round(pr.sdp_residuelle_m2)::int || ' m² — '
      || CASE WHEN pr.sdp_residuelle_m2 >= 5000 THEN 'opération majeure (socle +30).'
              WHEN pr.sdp_residuelle_m2 >= 2000 THEN 'belle opération (socle +25).'
              WHEN pr.sdp_residuelle_m2 >= 800 THEN 'opération viable (socle +15).'
              WHEN pr.sdp_residuelle_m2 >= 300 THEN 'petit collectif / 2–4 lots (socle +5).'
              WHEN pr.sdp_residuelle_m2 >= 100 THEN 'une maison — hors cible collectif (socle -10).'
              ELSE 'rien à construire (socle -25).' END
    END AS detail,
    CASE WHEN pr.sdp_residuelle_m2 IS NOT NULL THEN 'parcel_residuel' END AS source_table,
    CASE WHEN pr.sdp_residuelle_m2 IS NOT NULL THEN parc.id::text END AS source_id
  FROM parc LEFT JOIN parcel_residuel pr ON pr.parcel_id = parc.id
)
SELECT * FROM fp UNION ALL SELECT * FROM el UNION ALL SELECT * FROM res
"""


def prove_sp(cur) -> bool:
    """Générateur SQL vs lignes STOCKÉES de Saint-Paul — zéro écart exigé.
    NB poids : le générateur pose le poids « brut » ; les lignes stockées ont NULL quand la
    parcelle est exclue (weights=[0]*). La comparaison applique la même nullification."""
    cur.execute("DROP TABLE IF EXISTS _gen_sp")
    cur.execute("CREATE TEMP TABLE _gen_sp AS " + GEN_SQL, {"c": "Saint-Paul"})
    cur.execute("""
        WITH ex AS (SELECT DISTINCT parcel_id FROM dryrun_cascade_results
                    WHERE run_label = %(r)s AND result = 'HARD_EXCLUDE'),
        gen AS (
          SELECT g.parcel_id, g.layer_name, g.result, g.severity,
                 CASE WHEN ex.parcel_id IS NOT NULL THEN NULL
                      WHEN g.weight = 0 THEN NULL ELSE g.weight END AS weight,
                 g.detail, g.source_table, g.source_id
          FROM _gen_sp g LEFT JOIN ex ON ex.parcel_id = g.parcel_id),
        sto AS (
          SELECT c.parcel_id, c.layer_name, c.result, c.severity, c.weight_applied AS weight,
                 c.detail, c.source_table, c.source_id
          FROM dryrun_cascade_results c
          JOIN parcels p ON p.id = c.parcel_id AND p.commune = 'Saint-Paul'
          WHERE c.run_label = %(r)s AND c.layer_name IN ('foncier_public','emprise_lineaire','residuel_socle'))
        SELECT (SELECT count(*) FROM (SELECT * FROM gen EXCEPT ALL SELECT * FROM sto) a)
             + (SELECT count(*) FROM (SELECT * FROM sto EXCEPT ALL SELECT * FROM gen) b) AS d,
               (SELECT count(*) FROM gen) AS n_gen, (SELECT count(*) FROM sto) AS n_sto""",
                {"r": RUN})
    d, n_gen, n_sto = cur.fetchone()
    print(f"  Saint-Paul : {n_gen} lignes générées vs {n_sto} stockées → {d} écart(s)")
    if d:
        cur.execute("""
            WITH ex AS (SELECT DISTINCT parcel_id FROM dryrun_cascade_results
                        WHERE run_label = %(r)s AND result = 'HARD_EXCLUDE'),
            gen AS (SELECT g.parcel_id, g.layer_name, g.result,
                           CASE WHEN ex.parcel_id IS NOT NULL THEN NULL
                                WHEN g.weight = 0 THEN NULL ELSE g.weight END AS weight, g.detail
                    FROM _gen_sp g LEFT JOIN ex ON ex.parcel_id = g.parcel_id),
            sto AS (SELECT c.parcel_id, c.layer_name, c.result, c.weight_applied AS weight, c.detail
                    FROM dryrun_cascade_results c JOIN parcels p ON p.id = c.parcel_id AND p.commune='Saint-Paul'
                    WHERE c.run_label = %(r)s AND c.layer_name IN ('foncier_public','emprise_lineaire','residuel_socle'))
            SELECT * FROM ((SELECT 'gen' AS o, * FROM gen EXCEPT ALL SELECT 'gen', * FROM sto)
                UNION ALL (SELECT 'sto', * FROM sto EXCEPT ALL SELECT 'sto', * FROM gen)) x LIMIT 6""",
                    {"r": RUN})
        for row in cur.fetchall():
            print("   ", row)
    return d == 0


def extend(cur, communes: list[str]) -> None:
    for c in communes:
        cur.execute("""
            DELETE FROM dryrun_cascade_results c USING parcels p
            WHERE p.id = c.parcel_id AND p.commune = %(c)s AND c.run_label = %(r)s
              AND c.layer_name IN ('foncier_public','emprise_lineaire','residuel_socle')""",
                    {"c": c, "r": RUN})
        cur.execute("DROP TABLE IF EXISTS _gen_c")
        cur.execute("CREATE TEMP TABLE _gen_c AS " + GEN_SQL, {"c": c})
        # poids NULL si la parcelle est exclue (anciennes exclusions OU nouvelles des 3 couches)
        cur.execute("""
            WITH ex AS (
              SELECT DISTINCT parcel_id FROM dryrun_cascade_results
              WHERE run_label = %(r)s AND result = 'HARD_EXCLUDE'
              UNION SELECT parcel_id FROM _gen_c WHERE result = 'HARD_EXCLUDE')
            INSERT INTO dryrun_cascade_results
              (run_label, parcel_id, layer_name, result, severity, weight_applied, detail,
               source_table, source_id, evenement)
            SELECT %(r)s, g.parcel_id, g.layer_name, g.result, g.severity,
                   CASE WHEN ex.parcel_id IS NOT NULL THEN NULL
                        WHEN g.weight = 0 THEN NULL ELSE g.weight END,
                   g.detail, g.source_table, g.source_id, NULL
            FROM _gen_c g LEFT JOIN ex ON ex.parcel_id = g.parcel_id""", {"r": RUN})
        # sémantique moteur : une parcelle NOUVELLEMENT exclue perd TOUS ses poids
        cur.execute("""
            WITH new_ex AS (SELECT DISTINCT parcel_id FROM _gen_c WHERE result = 'HARD_EXCLUDE')
            UPDATE dryrun_cascade_results c SET weight_applied = NULL
            FROM new_ex WHERE c.parcel_id = new_ex.parcel_id AND c.run_label = %(r)s
              AND c.weight_applied IS NOT NULL""", {"r": RUN})
        cur.execute("""SELECT count(*) FILTER (WHERE result='HARD_EXCLUDE' AND layer_name='foncier_public'),
                              count(*) FILTER (WHERE result='HARD_EXCLUDE' AND layer_name='emprise_lineaire')
                       FROM _gen_c""")
        fp, el = cur.fetchone()
        print(f"  {c}: +3 couches (public {fp} excl. · linéaire {el} excl.)", flush=True)
        cur.connection.commit()


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "prove-sp"
    with psycopg.connect(DB) as conn, conn.cursor() as cur:
        if action == "prove-sp":
            ok = prove_sp(cur)
            conn.rollback()
            print("PREUVE " + ("OK — le générateur reproduit Saint-Paul à l'identique" if ok else "EN ÉCHEC"))
            return 0 if ok else 1
        if action == "extend":
            cur.execute("""SELECT commune FROM parcels WHERE commune <> 'Saint-Paul'
                           GROUP BY commune ORDER BY count(*)""")
            communes = [r[0] for r in cur.fetchall()]
            extend(cur, communes)
            print(f"✓ extension faite : {len(communes)} communes")
            return 0
    print("action inconnue")
    return 1


if __name__ == "__main__":
    sys.exit(main())
