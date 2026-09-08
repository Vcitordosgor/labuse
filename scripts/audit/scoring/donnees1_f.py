"""SCORING-DONNEES-1 · Lot F — sources non ingérées : fiche seulement.

Une fiche par source (URL, millésime, volume 974, clé de jointure, licence,
coût d'ingestion estimé) — AUCUNE ingestion. Les faits externes ont été vérifiés
le 06/09/2026 (URLs testées, fichiers réellement téléchargés et comptés — RPG
GPKG lu, en-têtes CSV INSEE lus, sondes S3 BDNB dep95=200/dep974=403).
Le Radar est un état de la série EN BASE (faisabilité seulement).

Usage : .venv/bin/python scripts/audit/scoring/donnees1_f.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from donnees1_commun import OUT, log  # noqa: E402
from _common import engine  # noqa: E402

FICHES = [
    {
        "source": "INSEE RP 2022 à l'IRIS (bases infracommunales)",
        "url": "https://www.insee.fr/fr/statistiques/8647012 (Logement) ; "
               "https://www.insee.fr/fr/statistiques/8647008 (Couples-Familles-"
               "Ménages) ; https://www.insee.fr/fr/statistiques/8647014 "
               "(Évol-struct-pop) — CSV zippés 20-26 Mo",
        "millesime": "RP 2022, parution 16/10/2025, géographie au 01/01/2024 "
                     "(dernier millésime IRIS au 06/09/2026 ; RP 2023 communal "
                     "seulement)",
        "volume_974": "344 lignes IRIS (343 IRIS sur 23 communes irisées + "
                      "La Plaine-des-Palmistes servie en bloc)",
        "cle_jointure": "code IRIS 9 car. → parcelles par jointure SPATIALE "
                        "(spatial_layers kind='iris_insee' DÉJÀ en base + table "
                        "d'appartenance INSEE 7708995)",
        "licence": "Licence Ouverte / Etalab 2.0",
        "indicateurs_du_mandat": "vacance OUI (P22_LOGVAC) ; résidences "
            "secondaires OUI (P22_RSECOCC) ; emménagement 30 ans+ NON à l'IRIS "
            "(tranche max « 10 ans ou plus », P22_MEN_ANEM10P) ; ménages 75 ans+ "
            "NON à l'IRIS (proxys : P22_POPMEN80P, P22_POP75P)",
        "cout_ingestion": "FAIBLE : 3 CSV nationaux ~100 Mo, filtre 974, table "
                          "iris → parcelle par ST_Contains sur une couche déjà "
                          "servie ; 1 jour dont recette",
    },
    {
        "source": "RPG 2024 (Registre parcellaire graphique, éd. 3.0)",
        "url": "https://data.geopf.fr/telechargement/download/RPG/"
               "RPG_3-0__GPKG_RGR92UTM40S_R04_2024-01-01/"
               "RPG_3-0__GPKG_RGR92UTM40S_R04_2024-01-01.7z (7z 47 Mo, testé)",
        "millesime": "2024 (fichiers du 23/11/2025 ; pas d'édition 2025 au "
                     "06/09/2026 — flux ATOM vérifié)",
        "volume_974": "22 722 parcelles RPG / 15 227 îlots / 35 730 ha déclarés ; "
                      "canne à sucre (CSA) : 7 505 parcelles, 18 539 ha "
                      "(GPKG réellement compté)",
        "cle_jointure": "AUCUN identifiant cadastral (id_parcel interne) → "
                        "intersection géométrique avec le PCI, même projection "
                        "EPSG:2975 au 974",
        "licence": "Licence Ouverte / Etalab 2.0 (ASP-IGN-MASA)",
        "indicateurs_du_mandat": "parcelle déclarée / non déclarée + code culture "
                                 "(code_cultu, dont CSA = canne)",
        "cout_ingestion": "FAIBLE-MOYEN : 1 GPKG départemental, intersection "
                          "spatiale 22 722 × 431 663 (PostGIS, index GIST) ; "
                          "1-2 jours dont recette ; as-of PARTIEL (éditions "
                          "annuelles depuis 2015 disponibles à re-télécharger)",
    },
    {
        "source": "BDNB 2026-02.a (CSTB) — âge du bâti, absence DPE, vacance",
        "url": "https://www.data.gouv.fr/datasets/base-de-donnees-nationale-des-"
               "batiments/ ; https://bdnb.io/download/ ; extraits départementaux "
               "open-data.s3.fr-par.scw.cloud/bdnb_millesime_2026-02-a/",
        "millesime": "2026-02.a (modèle v0.7.11, MAJ data.gouv 22/05/2026)",
        "volume_974": "ZÉRO — LA RÉUNION ABSENTE : spatial=country-subset:fr:metro, "
                      "départements 01-95 + 2A/2B seulement ; sonde S3 dep95→200, "
                      "dep974/dep971→403 ; aucune extension DROM annoncée au "
                      "changelog (confirme le constat SCORING-3 L3)",
        "cle_jointure": "(si couverture un jour) rel_batiment_groupe_parcelle : "
                        "batiment_groupe_id ↔ parcelle_id = IDU cadastral "
                        "(vérifié au dictionnaire v0.7.11)",
        "licence": "Licence Ouverte 2.0",
        "indicateurs_du_mandat": "âge du bâti, absence de DPE, vacance — "
                                 "INDISPONIBLES au 974 ; alternatives locales : "
                                 "DPE ADEME (à ingérer réellement, 17 lignes en "
                                 "base) + fichiers fonciers CEREMA (licence à "
                                 "instruire)",
        "cout_ingestion": "SANS OBJET aujourd'hui (974 absent) ; la veille L3 "
                          "(catalogue 65e, CRON) détectera une éventuelle "
                          "extension",
    },
]


def fiches() -> None:
    eng = engine()
    log("[F] fiches sources non ingérées…")
    pd.DataFrame(FICHES).to_csv(OUT / "f1_fiches_sources.csv", index=False)

    log("[F4] Radar agrégé commune × type : état de la série en base…")
    etat = pd.read_sql("""
        SELECT (SELECT count(*) FROM radar_releves) AS releves_serie,
               (SELECT count(*) FROM pige_annonces) AS annonces,
               (SELECT min(date_saisie)::date FROM pige_annonces) AS premiere,
               (SELECT max(date_saisie)::date FROM pige_annonces) AS derniere,
               (SELECT count(DISTINCT date_saisie::date) FROM pige_annonces) AS jours_distincts""",
                       eng)
    par_type = pd.read_sql("""
        SELECT b.commune, b.type_bien, count(*) AS n
        FROM pige_biens b JOIN pige_annonces a USING (bien_id)
        GROUP BY 1, 2 ORDER BY 3 DESC""", eng)
    etat["verdict"] = (
        "INFAISABLE aujourd'hui : radar_releves (la série quotidienne) est VIDE, "
        "108 annonces saisies sur 2 jours (29-30/08/2026), 12 combinaisons "
        "commune × type, Saint-Denis = 62 % du volume — aucun agrégat commune × "
        "type × temps ne peut nourrir un score ; collecte manuelle (source_radar "
        "mode=manuel). À réévaluer quand la série aura des mois de profondeur.")
    etat.to_csv(OUT / "f4_radar_etat_serie.csv", index=False)
    par_type.to_csv(OUT / "f4_radar_commune_type.csv", index=False)
    print(pd.DataFrame(FICHES)[["source", "millesime", "volume_974"]]
          .to_string(index=False))
    print(etat.to_string(index=False))


if __name__ == "__main__":
    fiches()
