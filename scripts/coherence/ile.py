"""COHERENCE-1 lot B (échelle île) — comparaisons SQL sur les 431 663 parcelles.

Dès que les DEUX côtés d'une notion sont des tables ou des vues, la comparaison ne se
fait pas sur l'échantillon mais sur TOUTE l'île : une requête par notion, qui rend le
nombre de parcelles divergentes (et 5 exemples). Le banc dit COMBIEN divergent, pas
seulement lesquelles.

    python -m scripts.coherence.ile        # ~ quelques minutes, lecture seule

Sortie : ECARTS-ILE.csv (notion · lecteur A · lecteur B · n_compare · n_divergent ·
exemples · cause présumée).
"""
from __future__ import annotations

import csv
import time

import psycopg

from .lib import DSN, RUN, SORTIE

#: (notion, lecteur_a, lecteur_b, cause_presumee, SQL) — le SQL rend (n_compare,
#: n_divergent, exemples text). %(run)s disponible.
COMPARAISONS: list[tuple] = [
    ("surface_parcelle_m2", "mvt_parcels.surface_m2", "parcels.surface_m2", "cache tuiles périmé", """
        SELECT count(*), count(*) FILTER (WHERE d), string_agg(idu, ' ') FILTER (WHERE d AND rn<=5)
        FROM (SELECT p.idu, abs(coalesce(m.surface_m2,0)-coalesce(p.surface_m2,0))
                     > 0.01*greatest(p.surface_m2,1) AS d,
                     row_number() OVER (PARTITION BY (abs(coalesce(m.surface_m2,0)-coalesce(p.surface_m2,0))
                     > 0.01*greatest(p.surface_m2,1)) ORDER BY p.idu) rn
              FROM mvt_parcels m JOIN parcels p ON p.id=m.id) t"""),

    ("surface_attribut_vs_geometrie", "parcels.surface_m2", "ST_Area(parcels.geom_2975)",
     "géométrie ou projection", """
        SELECT count(*), count(*) FILTER (WHERE d), string_agg(idu, ' ') FILTER (WHERE d AND rn<=5)
        FROM (SELECT idu, abs(surface_m2 - ST_Area(geom_2975)) > 0.02*greatest(surface_m2,1) AS d,
                     row_number() OVER (PARTITION BY (abs(surface_m2 - ST_Area(geom_2975))
                       > 0.02*greatest(surface_m2,1)) ORDER BY idu) rn
              FROM parcels) t"""),

    ("sdp_residuelle_m2", "mvt_parcels.sdp_residuelle_m2", "parcel_residuel.sdp_residuelle_m2",
     "cache tuiles périmé / run différent", """
        SELECT count(*), count(*) FILTER (WHERE d), string_agg(idu, ' ') FILTER (WHERE d AND rn<=5)
        FROM (SELECT p.idu,
                     (m.sdp_residuelle_m2 IS DISTINCT FROM r.sdp_residuelle_m2::int
                      AND abs(coalesce(m.sdp_residuelle_m2,0)-coalesce(r.sdp_residuelle_m2,0))
                          > 0.01*greatest(coalesce(r.sdp_residuelle_m2,0),1)) AS d,
                     row_number() OVER (PARTITION BY (m.sdp_residuelle_m2 IS DISTINCT FROM r.sdp_residuelle_m2::int
                      AND abs(coalesce(m.sdp_residuelle_m2,0)-coalesce(r.sdp_residuelle_m2,0))
                          > 0.01*greatest(coalesce(r.sdp_residuelle_m2,0),1)) ORDER BY p.idu) rn
              FROM mvt_parcels m JOIN parcels p ON p.id=m.id
              LEFT JOIN parcel_residuel r ON r.parcel_id=m.id) t"""),

    ("sous_densite", "mvt_parcels.sous_densite", "parcel_residuel.sous_densite",
     "cache tuiles périmé", """
        SELECT count(*), count(*) FILTER (WHERE d), string_agg(idu, ' ') FILTER (WHERE d AND rn<=5)
        FROM (SELECT p.idu, m.sous_densite IS DISTINCT FROM r.sous_densite AS d,
                     row_number() OVER (PARTITION BY (m.sous_densite IS DISTINCT FROM r.sous_densite)
                                        ORDER BY p.idu) rn
              FROM mvt_parcels m JOIN parcels p ON p.id=m.id
              LEFT JOIN parcel_residuel r ON r.parcel_id=m.id) t"""),

    ("tier_opportunite", "mvt_parcels.tier_v2", "parcel_p_score_v2.tier (run servi)",
     "run différent / tuiles pas rebasculées", """
        SELECT count(*), count(*) FILTER (WHERE d), string_agg(idu, ' ') FILTER (WHERE d AND rn<=5)
        FROM (SELECT p.idu, m.tier_v2 IS DISTINCT FROM s.tier AS d,
                     row_number() OVER (PARTITION BY (m.tier_v2 IS DISTINCT FROM s.tier)
                                        ORDER BY p.idu) rn
              FROM mvt_parcels m JOIN parcels p ON p.id=m.id
              LEFT JOIN parcel_p_score_v2 s ON s.parcelle_id=p.idu AND s.run_id=%(run)s) t"""),

    ("zone_plu_famille", "mvt_parcels.zone_fam", "parcel_zone_plu.zone_fam",
     "cache tuiles périmé", """
        SELECT count(*), count(*) FILTER (WHERE d), string_agg(idu, ' ') FILTER (WHERE d AND rn<=5)
        FROM (SELECT p.idu, m.zone_fam IS DISTINCT FROM z.zone_fam AS d,
                     row_number() OVER (PARTITION BY (m.zone_fam IS DISTINCT FROM z.zone_fam)
                                        ORDER BY p.idu) rn
              FROM mvt_parcels m JOIN parcels p ON p.id=m.id
              LEFT JOIN parcel_zone_plu z ON z.idu=p.idu) t"""),

    ("zone_plu_lib", "mvt_parcels.zone_lib", "parcel_zone_plu.zone_lib",
     "cache tuiles périmé", """
        SELECT count(*), count(*) FILTER (WHERE d), string_agg(idu, ' ') FILTER (WHERE d AND rn<=5)
        FROM (SELECT p.idu, m.zone_lib IS DISTINCT FROM z.zone_lib AS d,
                     row_number() OVER (PARTITION BY (m.zone_lib IS DISTINCT FROM z.zone_lib)
                                        ORDER BY p.idu) rn
              FROM mvt_parcels m JOIN parcels p ON p.id=m.id
              LEFT JOIN parcel_zone_plu z ON z.idu=p.idu) t"""),

    ("vigilances(flags)", "mvt_parcels.flags", "parcel_flags (run servi)",
     "tuiles pas rebasculées", """
        SELECT count(*), count(*) FILTER (WHERE d), string_agg(idu, ' ') FILTER (WHERE d AND rn<=5)
        FROM (SELECT p.idu,
                     coalesce(m.flags,'') IS DISTINCT FROM coalesce(f.flags,'') AS d,
                     row_number() OVER (PARTITION BY (coalesce(m.flags,'') IS DISTINCT FROM coalesce(f.flags,''))
                                        ORDER BY p.idu) rn
              FROM mvt_parcels m JOIN parcels p ON p.id=m.id
              LEFT JOIN (SELECT parcel_id, string_agg(layer_name, ',' ORDER BY layer_name) flags
                         FROM parcel_flags WHERE run_label=%(run)s GROUP BY parcel_id) f
                     ON f.parcel_id=m.id) t"""),
]


def main() -> None:
    lignes = []
    with psycopg.connect(DSN, options="-c statement_timeout=600000") as conn:
        for notion, la, lb, cause, sql in COMPARAISONS:
            t0 = time.time()
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, {"run": RUN})
                    n, div, ex = cur.fetchone()
            except Exception as e:  # noqa: BLE001
                conn.rollback()
                n, div, ex = None, None, f"ERREUR {str(e)[:120]}"
            lignes.append({"notion": notion, "lecteur_a": la, "lecteur_b": lb,
                           "n_compare": n, "n_divergent": div,
                           "exemples": (ex or "")[:200], "cause_presumee": cause,
                           "duree_s": round(time.time() - t0, 1)})
            print(f"{notion}: {div}/{n} divergent ({lignes[-1]['duree_s']}s)")
    SORTIE.mkdir(parents=True, exist_ok=True)
    with open(SORTIE / "ECARTS-ILE.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0].keys()))
        w.writeheader()
        w.writerows(lignes)
    print(f"→ {SORTIE/'ECARTS-ILE.csv'}")


if __name__ == "__main__":
    main()
