#!/usr/bin/env python3
"""SCORING-5-RETOUR §4 — script JETABLE (hors pipeline, jamais destiné au merge).

Calcule le Score LABUSE V1 (spec corrigée : sans terme contexte) pour les 30
parcelles témoins de TEMOINS.csv, puis la distribution île entière.

Barème et facteurs = valeurs PROVISOIRES à caler sur ces témoins (décision Vic).
Caveats assumés :
- résiduel SERVI run_seq=2 (m135-run2-ile, 22-23/08) = PRÉ-calibrage PLU ;
- forme approximée par largeur w = 2·aire/périmètre et allongement aire/w² ;
- accès lu de la couche `acces` du dry-run q_v13_sources1 (PASS = non identifié) ;
- pente : pente_moy_deg RGE ALTI convertie en % (tan) ; absente -> neutre (1,0).
Lecture seule en base (SELECT uniquement).
"""
import csv
import subprocess
from pathlib import Path

OUT = Path(__file__).with_name("TEMOINS.csv")

# (idu, categorie, raison une phrase)
TEMOINS = [
    # --- 10 évidemment bonnes ---
    ("97402000AH1389", "bonne", "Grande parcelle U quasi nue (emprise 4 %), ~4 900 m² de SDP résiduelle, pente 6 %."),
    ("97404000AX0047", "bonne", "Parcelle U nue de L'Étang-Salé, ~2 700 m² de SDP résiduelle, pente 8 %."),
    ("97406000AM0928", "bonne", "Parcelle U quasi nue de la Plaine-des-Palmistes, ~4 450 m² de SDP, terrain plat (3 %)."),
    ("97408000BL0170", "bonne", "Parcelle U de La Possession, ~4 860 m² de SDP, emprise bâtie 10 %, plat."),
    ("97407000BC0579", "bonne", "Parcelle U nue du Port, ~5 000 m² de SDP résiduelle, pente 6 %."),
    ("97422000BW2390", "bonne", "Parcelle U nue du Tampon, ~5 000 m² de SDP résiduelle, pente 9 %."),
    ("97409000AY0786", "bonne", "Parcelle U de Saint-André, ~5 000 m² de SDP, emprise 12 %, terrain plat."),
    ("97410000AS1202", "bonne", "Parcelle U quasi nue de Saint-Benoît, ~5 000 m² de SDP, pente 6 %."),
    ("97411000AB0798", "bonne", "Parcelle U de Saint-Denis, ~5 000 m² de SDP, emprise 5 %, pente 6 %."),
    ("97423000AI0116", "bonne", "Parcelle U nue des Trois-Bassins, ~1 340 m² de SDP, pente 9 %."),
    # --- 10 évidemment mauvaises (non écartées par la cascade) ---
    ("97420000AD0103", "mauvaise", "Terrain exigu (SDP 0) en pente extrême (94 %) avec bâti haut : rien à construire."),
    ("97413000CU0703", "mauvaise", "Terrain exigu de Saint-Leu, SDP 0, pente 82 %."),
    ("97411000BN0496", "mauvaise", "Terrain exigu de Saint-Denis, SDP 0, pente 80 %."),
    ("97415000CX0664", "mauvaise", "SDP résiduelle famélique (36 m²) sur pente de 83 % à Saint-Paul."),
    ("97411000CP0427", "mauvaise", "SDP 82 m² sur pente de 80 % : un logement théorique sur une rampe."),
    ("97413000CR0421", "mauvaise", "SDP 102 m² sur pente de 76 % à Saint-Leu."),
    ("97401000AL0852", "mauvaise", "Parcelle en lame (largeur < 8 m, allongement > 8) déjà bâtie, SDP 40 m²."),
    ("97415000AD0389", "mauvaise", "Parcelle en lame de Saint-Paul, SDP 98 m² : géométrie inexploitable."),
    ("97401000AL0505", "mauvaise", "Bâtie saturée (emprise 167 %, faîtage 10,3 m), SDP résiduelle 0."),
    ("97401000AO0067", "mauvaise", "Bâtie saturée (emprise 192 %, faîtage 9,3 m), SDP résiduelle 0."),
    # --- 10 limites ---
    ("97402000AL0088", "limite", "Zone A à 96 % : écartée aujourd'hui, pénalité d'assiette demain (4 % restent U) — le résiduel servi lui donne SDP 0."),
    ("97402000AB1117", "limite", "Zone N à 96 % : même cas de reclassement B — portion U résiduelle non valorisée par le résiduel servi."),
    ("97406000AM0664", "limite", "PPR partiel (aléa fort en drapeau) sur parcelle bâtie (emprise 68 %) avec 376 m² de SDP restants."),
    ("97401000AI0166", "limite", "PPR partiel en drapeau fort mais 1 794 m² de SDP résiduelle : bonne capacité sous risque partiel."),
    ("97401000AM0140", "limite", "Bâtie sous-utilisée (emprise 14 %, sous-densité), 268 m² de SDP restants."),
    ("97401000AD0110", "limite", "Bâtie sous-utilisée (emprise 11 %), 434 m² de SDP restants."),
    ("97415000AC0070", "limite", "Zone PLU non résolue : analyse non calculable, dite telle quelle."),
    ("97415000AC0109", "limite", "Zone PLU non résolue : analyse non calculable, dite telle quelle."),
    ("97406000AV0888", "limite", "Zone AU fermée : 526 m² de SDP mais capacité différée (barème ×0,5)."),
    ("97411000IR0091", "limite", "Zone AU fermée de Saint-Denis : 4 720 m² de SDP différés (barème ×0,5)."),
]

SCORE_SQL = """
WITH cible(idu) AS (VALUES {values}),
base AS (
  SELECT p.id, p.idu, p.commune,
         r.sdp_residuelle_m2 AS sdp, r.taux_emprise_pct AS emp, r.cause,
         tan(radians(coalesce(t.pente_moy_deg, 0)))*100 AS pente_pct,
         (t.pente_moy_deg IS NULL) AS pente_absente,
         ST_Area(p.geom_2975) AS a, ST_Perimeter(p.geom_2975) AS pe,
         h.faitage_m, au.classe AS au_classe, acc.result AS acces
  FROM cible c
  JOIN parcels p ON p.idu = c.idu
  JOIN parcel_residuel_runs r ON r.parcel_id = p.id AND r.run_seq = 2
  LEFT JOIN parcel_terrain t ON t.idu = p.idu
  LEFT JOIN batiment_hauteur_lidar h ON h.idu = p.idu
  LEFT JOIN parcel_au_statut au ON au.parcel_id = p.id
  LEFT JOIN LATERAL (
    SELECT d.result FROM dryrun_cascade_results d
    WHERE d.run_label = 'q_v13_sources1' AND d.parcel_id = p.id
      AND d.layer_name = 'acces' LIMIT 1) acc ON true
),
calc AS (
  SELECT *,
    (cause LIKE 'zone_non_resolue%' OR cause = 'hors_plu') AS non_calculable,
    (CASE WHEN coalesce(sdp, 0) <= 0 THEN 0
          WHEN sdp < 80 THEN 15 WHEN sdp < 200 THEN 35 WHEN sdp < 400 THEN 55
          WHEN sdp < 1000 THEN 75 WHEN sdp < 2000 THEN 90 ELSE 100 END
     * CASE WHEN au_classe IN ('declasse_au_fermee','declasse_au_statut_inconnu')
            THEN 0.5 ELSE 1.0 END) AS bareme,
    CASE WHEN pente_absente THEN 1.0
         WHEN pente_pct <= 15 THEN 1.0 WHEN pente_pct <= 30 THEN 0.85 ELSE 0.6 END AS f_pente,
    CASE WHEN pe > 0 AND (2*a/pe) < 8 AND (a / ((2*a/pe)^2)) > 8 THEN 0.8 ELSE 1.0 END AS f_forme,
    CASE WHEN acces = 'PASS' THEN 0.85 ELSE 1.0 END AS f_acces,
    CASE WHEN coalesce(emp, 0) = 0 THEN 1.0
         WHEN emp <= 20 THEN CASE WHEN coalesce(faitage_m,0) >= 9 THEN 0.8 ELSE 0.9 END
         WHEN emp <= 50 THEN CASE WHEN coalesce(faitage_m,0) >= 9 THEN 0.65 ELSE 0.8 END
         ELSE 0.65 END AS f_bati
  FROM base
)
SELECT idu, commune, sdp, coalesce(emp,0) emp, round(pente_pct) pente_pct,
       bareme, f_pente, f_forme, f_acces, f_bati,
       greatest(0.4, f_pente*f_forme*f_acces*f_bati) AS coef,
       CASE WHEN non_calculable THEN NULL
            ELSE least(100, round(bareme * greatest(0.4, f_pente*f_forme*f_acces*f_bati))) END AS score,
       non_calculable
FROM calc;
"""


def run_sql(sql: str) -> list[list[str]]:
    out = subprocess.run(
        ["psql", "-d", "labuse", "-X", "-A", "-t", "-F", "|", "-c", sql],
        capture_output=True, text=True, check=True)
    return [line.split("|") for line in out.stdout.strip().splitlines() if line]


def main() -> None:
    values = ", ".join(f"('{idu}')" for idu, _, _ in TEMOINS)
    rows = {r[0]: r for r in run_sql(SCORE_SQL.format(values=values))}
    header = ["idu", "commune", "categorie", "raison", "sdp_residuelle_m2",
              "bareme_capacite", "f_pente", "f_forme", "f_acces", "f_bati",
              "coef", "score", "non_calculable"]
    with OUT.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for idu, cat, raison in TEMOINS:
            r = rows[idu]
            w.writerow([idu, r[1], cat, raison, r[2], r[5], r[6], r[7], r[8],
                        r[9], r[10], r[11] or "", "oui" if r[12] == "t" else "non"])
    print(f"écrit : {OUT}")
    trie = sorted(
        ((idu, cat, rows[idu]) for idu, cat, _ in TEMOINS),
        key=lambda x: (x[2][11] == "", -float(x[2][11] or 0)))
    for idu, cat, r in trie:
        print(f"{r[11] or 'NC':>4}  {cat:<9} {idu} {r[1]:<24} sdp={r[2]:>6} coef={float(r[10]):.2f}")


if __name__ == "__main__":
    main()
