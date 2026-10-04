"""CHASSE-1 angle 8 — les parcelles qui ne devraient pas être là.

    python -m scripts.chasse.intruses   # → docs/audit-2026-10/CHASSE-1/INTRUSES.csv

Top 200 du classement servi (parcel_p_score_v2, run du manifeste, rang croissant hors
écartées/déclassées) : chaque parcelle est passée au crible — voirie, ravine, DPM/DPF,
cimetière, équipement public (BPE écoles/églises/mairies sur la parcelle), en mer / hors
référentiel, surface nulle, géométrie invalide, commune géom ≠ commune attribut, zone PLU
absente du catalogue. Lecture seule.
"""
from __future__ import annotations

import csv
import json
import pathlib

import psycopg

RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "CHASSE-1" / "INTRUSES.csv"
DSN = "postgresql://openclaw@localhost:5432/labuse"
MANIFESTE = json.loads((RACINE / "config" / "served_manifest.json").read_text())
V2RUN = MANIFESTE["scoring_run"]

# tiers servis comme « bons » (le top de la liste Analyse) — les déclassés/écartés sont exclus
TIERS_TOP = ("brulante", "chaude", "priorite", "a_suivre")

SQL_TOP = f"""
SELECT s.parcelle_id, s.tier, s.rang, p.id, p.commune, p.surface_m2
FROM parcel_p_score_v2 s
JOIN parcels p ON p.idu = s.parcelle_id
WHERE s.run_id = %(run)s AND s.tier = ANY(%(tiers)s) AND s.rang IS NOT NULL
ORDER BY s.rang ASC
LIMIT 200
"""

# chaque crible : (nom, SQL EXISTS/valeur pour UNE parcelle %(pid)s/%(idu)s)
CRIBLES = [
    ("voirie", """SELECT round((ST_Area(ST_Intersection(ST_Union(sl.geom_2975), p.geom_2975))
                        / NULLIF(ST_Area(p.geom_2975),0) * 100)::numeric, 1)
                  FROM parcels p
                  JOIN spatial_layers sl ON sl.kind='voirie'
                       AND sl.geom_2975 && p.geom_2975
                       AND ST_Intersects(sl.geom_2975, p.geom_2975)
                  WHERE p.id = %(pid)s GROUP BY p.geom_2975"""),
    ("ravine", """SELECT round((ST_Area(ST_Intersection(ST_Union(sl.geom_2975), p.geom_2975))
                        / NULLIF(ST_Area(p.geom_2975),0) * 100)::numeric, 1)
                  FROM parcels p
                  JOIN spatial_layers sl ON sl.kind='ravine'
                       AND sl.geom_2975 && p.geom_2975
                       AND ST_Intersects(sl.geom_2975, p.geom_2975)
                  WHERE p.id = %(pid)s GROUP BY p.geom_2975"""),
    ("dpf_dpm", """SELECT 'intersecte' FROM parcels p
                   JOIN spatial_layers sl ON sl.kind='dpf'
                        AND sl.geom_2975 && p.geom_2975
                        AND ST_Intersects(sl.geom_2975, p.geom_2975)
                   WHERE p.id = %(pid)s LIMIT 1"""),
    ("cimetiere", """SELECT 'intersecte' FROM parcels p
                     JOIN spatial_layers sl ON sl.kind='cimetiere'
                          AND sl.geom_2975 && p.geom_2975
                          AND ST_Intersects(sl.geom_2975, p.geom_2975)
                     WHERE p.id = %(pid)s LIMIT 1"""),
    ("equipement_public", """
        SELECT string_agg(DISTINCT sl.subtype, ',') FROM parcels p
        JOIN spatial_layers sl ON sl.kind IN ('amenite_bpe','amenite')
             AND sl.subtype ~* 'ecole|college|lycee|eglise|mairie|hopital|cimeti|culte'
             AND sl.geom_2975 && p.geom_2975
             AND ST_Intersects(sl.geom_2975, p.geom_2975)
        WHERE p.id = %(pid)s HAVING count(*) > 0"""),
    ("proprietaire_public", """
        SELECT groupe_label FROM parcelle_personne_morale
        WHERE idu = %(idu)s AND groupe_label IN ('Commune','État','Département','Région')"""),
    ("geom_invalide", """SELECT left(ST_IsValidReason(geom), 50) FROM parcels
                         WHERE id = %(pid)s AND NOT ST_IsValid(geom)"""),
    ("surface_nulle", """SELECT 'surface='||surface_m2 FROM parcels
                         WHERE id = %(pid)s AND (surface_m2 IS NULL OR surface_m2 < 1)"""),
    ("commune_geom_differente", """
        SELECT 'idu→'||left(idu,5)||' attr='||cr.insee FROM parcels p
        JOIN communes_referentiel cr ON cr.nom = p.commune
        WHERE p.id = %(pid)s AND left(p.idu,5) <> cr.insee"""),
    ("zone_hors_catalogue", """
        SELECT 'zone absente parcel_zone_plu' FROM parcels p
        WHERE p.id = %(pid)s
          AND NOT EXISTS (SELECT 1 FROM parcel_zone_plu z WHERE z.idu = p.idu)"""),
]


def main() -> None:
    conn = psycopg.connect(DSN, options="-c statement_timeout=120000")
    cur = conn.cursor()
    cur.execute(SQL_TOP, {"run": V2RUN, "tiers": list(TIERS_TOP)})
    top = cur.fetchall()
    print(f"top servi : {len(top)} parcelles (run {V2RUN}, tiers {TIERS_TOP})")

    lignes = []
    for idu, tier, rang, pid, commune, surf in top:
        for nom, sql in CRIBLES:
            try:
                cur.execute(sql, {"pid": pid, "idu": idu})
                row = cur.fetchone()
            except Exception as e:  # noqa: BLE001
                conn.rollback()
                row = (f"ERREUR {str(e)[:60]}",)
            if row and row[0] is not None:
                # voirie/ravine : ne garder que les recouvrements significatifs (> 30 %)
                if nom in ("voirie", "ravine"):
                    try:
                        if float(row[0]) <= 30:
                            continue
                        detail = f"{row[0]} % de la parcelle"
                    except (TypeError, ValueError):
                        detail = str(row[0])
                else:
                    detail = str(row[0])
                lignes.append({"idu": idu, "commune": commune, "tier": tier, "rang": rang,
                               "surface_m2": int(surf or 0), "crible": nom, "detail": detail})
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with open(SORTIE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["idu", "commune", "tier", "rang", "surface_m2",
                                          "crible", "detail"])
        w.writeheader()
        w.writerows(lignes)
    from collections import Counter
    print(f"{len(lignes)} signalements sur {len(top)} parcelles → {SORTIE}")
    for crible, n in Counter(l["crible"] for l in lignes).most_common():
        print(f"  {n:3d} {crible}")
    conn.close()


if __name__ == "__main__":
    main()
