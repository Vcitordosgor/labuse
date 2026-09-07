"""Fiche de règle — zonage A/B/C des communes (DHUP). SOURCES-1 lot 1."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("zonage_abc_logement",),
    formule_codee=(
        "Passe-plat : classe = colonne « Zonage ABC en vigueur » du CSV national DHUP pour le "
        "CODGEO de la commune (DEP=974), upsert dans commune_zonage_abc — aucune transformation, "
        "domaine fermé {Abis, A, B1, B2, C}, une valeur hors domaine est écartée à l'ingestion "
        "et listée (jamais devinée)."),
    entrees=("CSV data.gouv « Liste ensemble des communes - Zonage ABC en vigueur 26 juin 2026 » "
             "(CODGEO;DEP;LIBGEO;Zonage)", "commune_zonage_abc (insee, zone, millesime)"),
    classe="regle_externe",
    fonction="src/labuse/ingestion/zonage_abc.py:ingest_zonage_abc / zonage_commune",
    verdict="conforme",
    reference=Reference(
        titre="Arrêté du 1er août 2014 modifié (zonage ABC, art. D. 304-1 CCH)",
        article="liste des communes annexée — version consolidée du 23/06/2026",
        url=("https://static.data.gouv.fr/resources/liste-des-communes-selon-le-zonage-abc/"
             "20260703-091314/liste-ensemble-des-communes-zonage-abc-en-vigueur-26-juin-2026.csv"),
        version="en vigueur depuis le 26/06/2026",
        extrait=("En-tête lu : « CODGEO;DEP;LIBGEO;Zonage ABC en vigueur depuis le 26 juin "
                 "2026 ». Lignes 974 lues (24/24) : 97401 Les Avirons=A ; 97404 L'Étang-Salé=A ; "
                 "97413 Saint-Leu=A ; 97415 Saint-Paul=A ; les 20 autres communes=B1."),
        lu_le="2026-09-06"),
    exemple_temoin="tests/test_sources1_lot1.py::test_zonage_abc_passe_plat",
    verifie_le="2026-09-07",
))
