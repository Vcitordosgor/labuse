"""CHASSE-1 — tirage de l'échantillon (graine fixée, rejouable).

    python -m scripts.chasse.echantillon            # écrit ECHANTILLON.csv (ne régénère pas)
    python -m scripts.chasse.echantillon --regenerer

Trois blocs :
  · 200 parcelles stratifiées : 24 communes × {U,AU,A,N} × {nue,bâtie} (tirage aléatoire
    reproductible via setseed + hashtext, ~1 par cellule existante, complété au hasard) ;
  · ~300 parcelles pièges, ≤20 par classe (SQL ci-dessous) ;
  · les 20 témoins d'ORACLE-1 (docs/audit-2026-09/ORACLE-1/PARCELLES.csv).

Classes pièges VIDES par construction (documentées, pas passées sous silence) :
  · zac            — aucune couche ZAC en base (GEOPF-2 : absente réelle) ;
  · regle_non_modelisee — parcel_residuel.regles_non_modelisees est NULL partout
    (PLU-CALIBRAGE-5 pas mergé dans main au jour du tirage).
Classe adaptée :
  · contenance_ecart — la contenance cadastrale DGFiP n'est pas en base (oracle externe
    API Carto) ; on prend l'écart surface_m2 stockée vs ST_Area(geom_2975) > 15 %,
    même intention (aire annoncée ≠ aire géométrique).

Lecture seule sur la base dev (SELECT uniquement).
"""
from __future__ import annotations

import csv
import pathlib
import sys

import psycopg

RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "CHASSE-1" / "ECHANTILLON.csv"
ORACLE1 = RACINE / "docs" / "audit-2026-09" / "ORACLE-1" / "PARCELLES.csv"
DSN = "postgresql://openclaw@localhost:5432/labuse"
GRAINE = 0.42  # setseed PostgreSQL — fige le tirage

# ─────────────────────────── bloc 1 : 200 stratifiées
# une parcelle par cellule commune × famille × bâtie/nue (192 cellules théoriques),
# complétées à 200 par tirage global. Bâtie = présence dans parcel_filtre_bati.
SQL_STRATES = """
WITH base AS (
  SELECT p.idu, p.commune, z.zone_fam,
         (fb.parcel_id IS NOT NULL) AS batie,
         row_number() OVER (PARTITION BY p.commune, z.zone_fam, (fb.parcel_id IS NOT NULL)
                            ORDER BY hashtext(p.idu || %(sel)s)) AS rn
  FROM parcels p
  JOIN parcel_zone_plu z ON z.idu = p.idu
  LEFT JOIN parcel_filtre_bati fb ON fb.parcel_id = p.id
  WHERE z.zone_fam IN ('U','AU','A','N')
)
SELECT idu, commune, zone_fam, batie FROM base WHERE rn = 1
"""
SQL_COMPLEMENT = """
SELECT p.idu, p.commune, z.zone_fam, (fb.parcel_id IS NOT NULL) AS batie
FROM parcels p
JOIN parcel_zone_plu z ON z.idu = p.idu
LEFT JOIN parcel_filtre_bati fb ON fb.parcel_id = p.id
WHERE z.zone_fam IN ('U','AU','A','N') AND NOT (p.idu = ANY(%(deja)s))
ORDER BY hashtext(p.idu || %(sel)s) LIMIT %(n)s
"""

# ─────────────────────────── bloc 2 : classes pièges (≤20 chacune)
# Chaque requête rend (idu, commune[, detail]). random() est figé par setseed en amont.
PIEGES: list[tuple[str, str]] = [
    # classement réellement servi par l'écran Analyse = parcel_p_score_v2 du run v2 servi
    ("score_top50", """
        SELECT s.parcelle_id, p.commune FROM parcel_p_score_v2 s
        JOIN parcels p ON p.idu = s.parcelle_id
        WHERE s.run_id = %(v2run)s AND s.rang IS NOT NULL
        ORDER BY s.rang ASC LIMIT 50"""),
    ("score_flop50", """
        SELECT s.parcelle_id, p.commune FROM parcel_p_score_v2 s
        JOIN parcels p ON p.idu = s.parcelle_id
        WHERE s.run_id = %(v2run)s AND s.rang IS NOT NULL
        ORDER BY s.rang DESC LIMIT 50"""),
    ("signal_fort", """
        SELECT s.parcelle_id, p.commune FROM parcel_p_score_v2 s
        JOIN parcels p ON p.idu = s.parcelle_id
        WHERE s.run_id = %(v2run)s
        ORDER BY s.p_raw DESC LIMIT 20"""),
    ("plus_grandes", """
        SELECT idu, commune FROM parcels ORDER BY surface_m2 DESC NULLS LAST LIMIT 20"""),
    ("plus_petites_50m2", """
        SELECT idu, commune FROM parcels WHERE surface_m2 > 0 AND surface_m2 < 50
        ORDER BY random() LIMIT 20"""),
    ("multipolygone", """
        SELECT idu, commune FROM parcels WHERE ST_NumGeometries(geom) > 1 LIMIT 20"""),
    ("frontiere_commune", """
        SELECT DISTINCT ON (p.idu) p.idu, p.commune FROM parcels p
        WHERE EXISTS (SELECT 1 FROM parcels q
                      WHERE q.commune <> p.commune
                        AND q.geom_2975 && ST_Expand(p.geom_2975, 1)
                        AND ST_DWithin(q.geom_2975, p.geom_2975, 0.5))
        ORDER BY p.idu, random() LIMIT 20"""),
    ("cheval_zone_plu", """
        SELECT idu, commune FROM (
          SELECT p.idu, p.commune, count(DISTINCT sl.name) AS nz
          FROM parcels p
          JOIN spatial_layers sl ON sl.kind = 'plu_gpu_zone'
               AND sl.geom && p.geom AND ST_Intersects(sl.geom, p.geom)
               AND ST_Area(ST_Intersection(sl.geom, p.geom)::geography) > 5
          GROUP BY p.idu, p.commune HAVING count(DISTINCT sl.name) >= 2
          LIMIT 2000) t
        ORDER BY random() LIMIT 20"""),
    ("cinquante_pas", """
        SELECT p.idu, p.commune FROM parcels p
        WHERE EXISTS (SELECT 1 FROM spatial_layers sl WHERE sl.kind = 'cinquante_pas'
                      AND sl.geom && p.geom AND ST_Intersects(sl.geom, p.geom))
        ORDER BY random() LIMIT 20"""),
    ("sans_lidar", """
        SELECT p.idu, p.commune FROM parcels p
        JOIN parcel_filtre_bati fb ON fb.parcel_id = p.id
        WHERE NOT EXISTS (SELECT 1 FROM batiment_hauteur_lidar bh WHERE bh.idu = p.idu)
        ORDER BY random() LIMIT 20"""),
    ("pseudo_siren", """
        SELECT pm.idu, p.commune FROM parcelle_personne_morale pm
        JOIN parcels p ON p.idu = pm.idu
        WHERE pm.siren IS NULL OR upper(trim(pm.siren)) LIKE 'U%%'
        ORDER BY random() LIMIT 20"""),
    ("copropriete", """
        SELECT DISTINCT ON (rc.parcelle_idu) rc.parcelle_idu, p.commune
        FROM rnic_coproprietes rc JOIN parcels p ON p.idu = rc.parcelle_idu
        ORDER BY rc.parcelle_idu, random() LIMIT 20"""),
    ("indivision", """
        SELECT pm.idu, p.commune FROM parcelle_personne_morale pm
        JOIN parcels p ON p.idu = pm.idu
        WHERE pm.groupe_label IN ('Copropriétaires','Associés')
        ORDER BY random() LIMIT 20"""),
    ("permis_caduc", """
        SELECT pc.idu, p.commune FROM pc_caducs pc
        JOIN parcels p ON p.idu = pc.idu
        WHERE pc.statut_caducite = 'granted' OR pc.caduc_depuis IS NOT NULL
        ORDER BY random() LIMIT 20"""),
    ("sup_ac1", """
        SELECT DISTINCT ON (p.idu) p.idu, p.commune FROM parcels p
        JOIN spatial_layers sl ON sl.kind = 'sup' AND lower(sl.subtype) = 'ac1'
             AND sl.geom && p.geom AND ST_Intersects(sl.geom, p.geom)
        ORDER BY p.idu, random() LIMIT 20"""),
    # « partiel » = la LIMITE de la zone rouge traverse la parcelle (ni toute dedans, ni toute
    # dehors). Frontière subdivisée (morceaux ≤ 64 points) pour rester sous le timeout.
    ("ppr_rouge_partiel", """
        WITH bords AS (
          SELECT ST_Subdivide(ST_Boundary(geom), 64) AS g
          FROM spatial_layers WHERE kind = 'ppr' AND subtype = 'INTERDICTION')
        SELECT idu, commune FROM (
          SELECT DISTINCT p.idu, p.commune
          FROM bords b JOIN parcels p ON p.geom && b.g AND ST_Intersects(p.geom, b.g)
          LIMIT 2000) t
        ORDER BY random() LIMIT 20"""),
    ("plu_depublie", """
        SELECT idu, commune FROM parcels
        WHERE commune IN ('Saint-Leu','Saint-André')
        ORDER BY random() LIMIT 20"""),
    ("sans_adresse_ban", """
        SELECT p.idu, p.commune FROM parcels p
        WHERE NOT EXISTS (SELECT 1 FROM adresse_parcelles ap WHERE ap.idu = p.idu)
        ORDER BY random() LIMIT 20"""),
]
VIDES_DOCUMENTEES = {
    "zac": "aucune couche ZAC en base (GEOPF-2)",
    "regle_non_modelisee": "regles_non_modelisees NULL partout (PLU-CALIBRAGE-5 non mergé)",
    "contenance_ecart": "surface_m2 stockée = ST_Area(geom_2975) partout (écart max 0 mesuré) ; "
                        "la contenance DGFiP n'est pas en base (oracle externe API Carto)",
}


def main() -> None:
    if SORTIE.exists() and "--regenerer" not in sys.argv:
        print(f"déjà tiré (gelé) : {SORTIE} — --regenerer pour refaire")
        return
    conn = psycopg.connect(DSN, options="-c statement_timeout=600000")
    cur = conn.cursor()
    cur.execute("SELECT setseed(%s)", (GRAINE,))
    sel = str(GRAINE)

    # run v2 SERVI : même règle que app._score_v2_run_id — le run du manifeste
    # (config/served_run.txt via runs.current()), PAS le plus récent de la table.
    import json
    manifeste = json.loads((RACINE / "config" / "served_manifest.json").read_text())
    v2run = manifeste["scoring_run"]
    cur.execute("SELECT 1 FROM p_score_v2_runs WHERE run_id = %s", (v2run,))
    assert cur.fetchone(), f"run servi {v2run} absent de p_score_v2_runs"
    print(f"run v2 pris pour top/flop : {v2run}")

    vus: set[str] = set()
    lignes: list[dict] = []

    def ajouter(idu, commune, bloc, classe, detail=""):
        if idu in vus:
            return
        vus.add(idu)
        lignes.append({"idu": idu, "commune": commune, "bloc": bloc,
                       "classe": classe, "detail": detail})

    # bloc 3 d'abord (les 20 ORACLE-1, prioritaires, jamais dédoublonnés ailleurs)
    with open(ORACLE1, newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            ajouter(r["idu"], r["commune"], "oracle1", r["slot"], r["criteres"])

    # bloc 1 : stratifiées
    cur.execute(SQL_STRATES, {"sel": sel})
    strates = cur.fetchall()
    for idu, commune, fam, batie in strates:
        ajouter(idu, commune, "stratifie", f"{fam}_{'batie' if batie else 'nue'}")
    manque = 200 - sum(1 for l in lignes if l["bloc"] == "stratifie")
    if manque > 0:
        cur.execute(SQL_COMPLEMENT, {"deja": list(vus), "sel": sel, "n": manque})
        for idu, commune, fam, batie in cur.fetchall():
            ajouter(idu, commune, "stratifie", f"{fam}_{'batie' if batie else 'nue'}_cplt")

    # bloc 2 : pièges
    for classe, sql in PIEGES:
        cur.execute("SELECT setseed(%s)", (GRAINE,))  # chaque classe repart de la graine
        try:
            cur.execute(sql, {"v2run": v2run})
            rows = cur.fetchall()
        except Exception as e:  # noqa: BLE001 — une classe qui casse est un résultat
            conn.rollback()
            print(f"  ! classe {classe} : {e}")
            continue
        n = 0
        for row in rows:
            ajouter(row[0], row[1], "piege", classe)
            n += 1
        print(f"  {classe}: {n} tirées ({len(rows)} candidates)")
    for classe, motif in VIDES_DOCUMENTEES.items():
        lignes.append({"idu": "", "commune": "", "bloc": "piege",
                       "classe": classe, "detail": f"CLASSE VIDE — {motif}"})

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with open(SORTIE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["idu", "commune", "bloc", "classe", "detail"])
        w.writeheader()
        w.writerows(lignes)
    reels = [l for l in lignes if l["idu"]]
    print(f"\n{len(reels)} parcelles ({len(set(l['idu'] for l in reels))} uniques) → {SORTIE}")
    conn.close()


if __name__ == "__main__":
    main()
