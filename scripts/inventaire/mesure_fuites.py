#!/usr/bin/env python3
"""CIRCUIT-0 Lot 5 — MESURE des fuites (5.2) et de l'eau ancienne (5.3). SELECT seuls.

Témoins : les 24 communes (parts de zonage, deux chemins) ; le global (n_sources, trois
chemins). La « part RNU » du mandat (fiche commune 18 % vs Communes › Comparaison 6 % à
Saint-Paul) correspond aux parts de zonage : le chemin « surface » (app.py:1908-1955,
fiche commune) contre le chemin « comptes de parcelles » (app.py:2436) — l'écran exact où
Vic a lu chaque valeur reste DOUTE, les DEUX chemins de calcul sont mesurés ici.
"""
from __future__ import annotations

import csv
import io
import subprocess
from pathlib import Path

INV = Path(__file__).resolve().parents[2] / "docs/CIRCUIT/inventaire"
OUT_MES = INV / "fuites_mesurees.csv"
OUT_EAU = INV / "eau_ancienne.csv"


def q(sql: str) -> list[list[str]]:
    out = subprocess.run(["psql", "-d", "labuse", "--csv", "-c", sql],
                         capture_output=True, text=True, check=True)
    return [r for r in csv.reader(io.StringIO(out.stdout))][1:]


SQL_ZONAGE = """
WITH z AS (
  SELECT p.commune, upper(z.zone_fam) fam, count(*) n, sum(p.surface_m2)::numeric m2
  FROM parcels p JOIN parcel_zone_plu z ON z.idu = p.idu
  WHERE z.zone_fam IS NOT NULL GROUP BY 1, 2),
b AS (SELECT commune, fam,
             round(100.0 * m2 / sum(m2) OVER (PARTITION BY commune), 1) AS pct_surface,
             round(100.0 * n / sum(n) OVER (PARTITION BY commune), 1) AS pct_parcelles
      FROM z)
SELECT commune, fam, pct_surface, pct_parcelles FROM b
WHERE fam IN ('A', 'N', 'U', 'AU') ORDER BY commune, fam
"""

MES_HEADER = ["chiffre_id", "cle", "robinet_a", "valeur_a", "robinet_b", "valeur_b",
              "ecart", "cause_probable", "preuve"]
EAU_HEADER = ["chiffre_id", "robinet", "millesime_table", "millesime_servi", "ecart",
              "mecanisme", "preuve"]


def main() -> None:
    mes = []
    # ── 5.2a — parts de zonage, 24 communes × familles A et N (les deux du constat Vic) ──
    for commune, fam, pct_surface, pct_parcelles in q(SQL_ZONAGE):
        if fam not in ("A", "N"):
            continue
        ecart = round(abs(float(pct_surface) - float(pct_parcelles)), 1)
        mes.append({
            "chiffre_id": f"part_zone_{fam}_pct", "cle": commune,
            "robinet_a": "fiche_commune_zonage (surface)", "valeur_a": f"{pct_surface} %",
            "robinet_b": "comptes par famille app.py:2436 (parcelles)", "valeur_b": f"{pct_parcelles} %",
            "ecart": f"{ecart} pts", "cause_probable": "denominateur",
            "preuve": "SQL zonage surface vs parcelles (ce script) — chemin fidèle à l'intention : "
                      "SURFACE (commentaire OUTILS-6 C1, app.py:1908-1911 : « les parts de parcelles "
                      "ne représentent pas le territoire »)"})
    # ── 5.2b — n_sources : trois chemins ──
    n_vitrine = q("SELECT count(*) FROM data_sources WHERE lower(status) IN ('connecte','manuel') "
                  "AND COALESCE(technical_notes,'') NOT LIKE 'DOUBLON%' "
                  "AND COALESCE(technical_notes,'') NOT LIKE 'RETIRÉ%' "
                  "AND COALESCE(technical_notes,'') NOT LIKE 'DORMANT%' "
                  "AND COALESCE(affichage_desactive,false)=false")[0][0]
    n_brut = q("SELECT count(*) FROM data_sources")[0][0]
    mes.append({
        "chiffre_id": "n_sources", "cle": "global",
        "robinet_a": "page_sources_client + admin_catalogue (WHERE_AFFICHEES)", "valeur_a": n_vitrine,
        "robinet_b": "admin_flux_circuit (count(*) brut, flux.py:198)", "valeur_b": n_brut,
        "ecart": str(int(n_brut) - int(n_vitrine)), "cause_probable": "perimetre",
        "preuve": "SQL des deux chemins (ce script) — chemin fidèle : WHERE_AFFICHEES "
                  "(sources_catalog.py:36, « la vitrine ne montre que ce qui SERT »)"})
    # ── 5.2c — prix neuf VEFA : fuite HISTORIQUE corrigée (RETOURS-11F M1) — précalc encore lu ──
    mes.append({
        "chiffre_id": "prix_neuf_vefa_eur_m2", "cle": "Saint-Paul (97415)",
        "robinet_a": "comparateur/fiche/carte (moteur live neuf_vefa_commune)", "valeur_a": "5 003 €/m² (mesure du mandat RETOURS-11F)",
        "robinet_b": "précalcul dvf_prix_sortie_neuf (encore lu par score_e)", "valeur_b": "4 730 €/m² (idem)",
        "ecart": "273 €/m²", "cause_probable": "table",
        "preuve": "src/labuse/api/comparateur.py:57-60 (commentaire chiffré) ; score_e lit encore "
                  "dvf_prix_sortie_neuf (src/labuse/ingestion/score_e.py:59) — chemin fidèle : moteur live"})

    with OUT_MES.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MES_HEADER, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(mes)

    # ── 5.3 — eau ancienne ──
    eau = []
    dpe = q("SELECT coalesce(max(date_etablissement)::text,'aucune'), count(*) FROM dpe_records")[0]
    vu = q("SELECT coalesce(v.dernier_vu,'') FROM source_veille v WHERE v.source_id=37")[0][0]
    eau.append({"chiffre_id": "(tout chiffre DPE : classe, passoires)", "robinet": "fiche parcelle / filtres",
                "millesime_table": f"max(date_etablissement)={dpe[0]} (n={dpe[1]} en base LOCALE)",
                "millesime_servi": f"amont vu par la sonde : {vu[:10]}",
                "ecart": "≈ 6 semaines (local)",
                "mecanisme": "le cron ingest-dpe SAUTE toute commune déjà peuplée (cli.py, sans --force) "
                             "ET tamponne last_sync_at quand même (dpe.py:243) — volume prod ≠ local (DOUTE)",
                "preuve": "SELECT (ce script) ; src/labuse/ingestion/dpe.py:217-245"})
    dor = q("SELECT run_label, count(*) FROM division_or_candidates GROUP BY 1")[0]
    eau.append({"chiffre_id": "divisible_classe", "robinet": "fiche_parcelle_division",
                "millesime_table": f"run_label={dor[0]} (n={dor[1]})",
                "millesime_servi": "run servi q_v11_m137",
                "ecart": "1 run de retard",
                "mecanisme": "lignes lues SANS filtre de run (app.py:1573,2692-2696) ; toléré comme "
                             "workflow de revue par commune (bascule_gardes.py:663-665)",
                "preuve": "SELECT (ce script)"})
    sol = q("SELECT coalesce(max(millesime),'?'), count(*) FROM parcel_solar")[0] if \
        q("SELECT 1 FROM information_schema.columns WHERE table_name='parcel_solar' AND column_name='millesime'") else ("colonne absente", "?")
    eau.append({"chiffre_id": "prod_spec_kwh_kwc", "robinet": "outil_prospection_solaire / fiches",
                "millesime_table": f"parcel_solar gelé ({sol[0]}, n={sol[1]})",
                "millesime_servi": "PVGIS = API de calcul vivante (pas de millésime amont)",
                "ecart": "gel ASSUMÉ et étiqueté (bandeau lit le millésime en base)",
                "mecanisme": "recalcul uniquement par labuse solaire-build (geste)",
                "preuve": "SELECT (ce script) ; src/labuse/ingestion/solaire.py:43-45"})
    fc = q("SELECT coalesce(max(computed_at)::date::text,'aucun'), count(*) FROM commune_contexte_cache")[0]
    eau.append({"chiffre_id": "(les 15 cartes de la fiche commune)", "robinet": "fiche_commune_*",
                "millesime_table": f"cache computed_at max = {fc[0]} ({fc[1]} communes)",
                "millesime_servi": "sources live (DVF, Radar, Sitadel…)",
                "ecart": "jusqu'à 24 h (recalcul nocturne 03:00)",
                "mecanisme": "cache ASSUMÉ et tamponné (« compteurs précalculés le … » au front) ; "
                             "cache manquant → calcul direct honnête",
                "preuve": "SELECT (ce script) ; app.py (_CONTEXTE_CACHE_DDL et commentaire FICHE-COMMUNE-2 C1)"})
    iso = q("SELECT count(*), coalesce(min(created_at)::date::text,'-'), coalesce(max(created_at)::date::text,'-') FROM zone_isochrone_cache")[0]
    eau.append({"chiffre_id": "population_zone (et tout chiffre d'isochrone)", "robinet": "outil_etude_zone / pdf_flash",
                "millesime_table": f"zone_isochrone_cache : {iso[0]} entrées, {iso[1]} → {iso[2]}, SANS TTL",
                "millesime_servi": "isochrone IGN vivante",
                "ecart": "illimité (géométrie de voirie figée à la 1re demande)",
                "mecanisme": "cache par clé mode|minutes|lon|lat jamais purgé automatiquement",
                "preuve": "SELECT (ce script) ; src/labuse/zone.py:54-76"})
    eau.append({"chiffre_id": "score_e (marge promoteur)", "robinet": "couche/fiche (score E)",
                "millesime_table": "entrée dvf_prix_sortie_neuf = PRÉCALCUL divergent du moteur live "
                                   "(4 730 vs 5 003 à Saint-Paul, mesure RETOURS-11F)",
                "millesime_servi": "le neuf servi ailleurs est le moteur live",
                "ecart": "273 €/m² sur le témoin",
                "mecanisme": "le précalcul n'a pas suivi la bascule au moteur live (RETOURS-11F M1 n'a "
                             "corrigé que comparateur/fiche/carte)",
                "preuve": "src/labuse/api/comparateur.py:57-60 ; src/labuse/ingestion/score_e.py:59"})

    with OUT_EAU.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=EAU_HEADER, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(eau)

    ecarts_nz = sum(1 for m in mes if not str(m["ecart"]).startswith("0"))
    print(f"fuites_mesurees.csv : {len(mes)} lignes (écart ≠ 0 : {ecarts_nz})")
    print(f"eau_ancienne.csv : {len(eau)} lignes")
    sp = [m for m in mes if m["cle"] == "Saint-Paul"]
    for m in sp:
        print(f"  Saint-Paul {m['chiffre_id']}: {m['valeur_a']} vs {m['valeur_b']} ({m['ecart']})")


if __name__ == "__main__":
    main()
