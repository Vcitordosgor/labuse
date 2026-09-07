"""Fiche de règle — taux de taxe foncière REI. SOURCES-1 lot 5."""
from . import FicheRegle, Reference, declarer

declarer(FicheRegle(
    donnees=("tfpb_taux_pct",),
    formule_codee=(
        "Passe-plat des colonnes du fichier REI 2025 (DGFiP), identifiées via la TRACE "
        "officielle : E12 = taux TFPB appliqué sur la commune (servi en tête), E32 = taux "
        "TFPB intercommunal, F22 = taux TEOM net « taux plein ». Bornes de plausibilité "
        "[0 ; 100] % (hors bornes = écarté + listé). Impositions PRIMITIVES — dit au "
        "millésime. La taxe d'aménagement n'y est PAS (source CIRCUIT-3)."),
    entrees=("REI_2025.csv (data.economie.gouv.fr, ZIP annuel — colonnes E12/E12VOTE/E32/F22)",
             "commune_rei (table servie)"),
    classe="regle_externe",
    fonction="src/labuse/ingestion/rei.py:ingest_rei / rei_commune",
    verdict="conforme",
    reference=Reference(
        titre="TRACE du fichier REI 2025 (DGFiP)",
        article="variables E12 / E32 / F22",
        url=("https://data.economie.gouv.fr/api/v2/catalog/datasets/impots-locaux-fichier-"
             "de-recensement-des-elements-dimposition-a-la-fiscalite-dir/attachments/"
             "rei_2025_fichier_notice_tracezip"),
        version="REI 2025 (TRACE_REI_2025.xlsx du 02/06/2026)",
        extrait=("E12 : « Taux de taxe foncière sur les propriétés bâties (TFB) voté par la "
                 "commune ou taux moyen appliqué sur le territoire de la commune » ; F22/F23 : "
                 "« FB - TEOM / TAUX PLEIN - TAUX NET — Taux de taxe d'enlèvement des ordures "
                 "ménagères (TEOM) voté par la collectivité bénéficiaire, pour la zone taux "
                 "plein ». Mesuré 974 : E12 de 29,55 (Les Avirons) à 68,40 % (Saint-Louis)."),
        lu_le="2026-09-07"),
    exemple_temoin="tests/test_sources1_lot5.py::test_rei_taux_passe_plat",
    verifie_le="2026-09-07",
))
