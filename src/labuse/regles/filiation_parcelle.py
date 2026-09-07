"""Fiche de règle — filiation officielle des parcelles (DFI) + rattachement des permis
orphelins. SOURCES-1 lot 6."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("filiation_parcelle",),
    formule_codee=(
        "Passe-plat : mères = lignes dfi_filiation où idu_fille = parcelle ; filles = lignes "
        "où idu_mere = parcelle ; tri par date_validation décroissante, nature servie telle "
        "quelle (6 natures DGFiP). IDU reconstruit = code_insee(5) + prefixe_section(3) + "
        "parcelle(6) ; deux codes AMONT servis étiquetés, jamais joints : fille 'PDP' = passage au domaine public (5 032), mère 'EDNC' = issue du non-cadastré (1 797). drapeau division_recente = ∃ fille avec date ≥ 2023 (simple lecture, "
        "pas un score). Rattachement des permis orphelins (choix LABUSE) : permis sans "
        "géométrie dont l'IDU référence une mère disparue → filles TERMINALES (descente "
        "récursive ≤ 8 niveaux) présentes au cadastre courant → geom = "
        "ST_PointOnSurface(ST_Union(filles)) ; raw.geoloc = « filiation DFI » ; ne touche "
        "jamais un permis déjà géolocalisé."),
    entrees=("dfi_filiation (idu_mere, idu_fille, nature, date_validation)",
             "sitadel_permits (idu_codes, geom)", "parcels (idu, geom_2975)"),
    classe="choix_labuse",
    fonction="src/labuse/ingestion/dfi.py:filiation_parcelle / rattacher_permis_par_filiation",
    verdict="choix_assume",
    choix=(
        "Mandat SOURCES-1 lot 6 : la filiation OFFICIELLE (DFI DGFiP) rattache les permis "
        "orphelins « proprement » — en complément du canal géométrique (cadastre d'époque, "
        "RETOURS-14/21) qui reste premier : la filiation ne se joue que sur les permis ENCORE "
        "sans géométrie après lui. L'écart entre les deux canaux est un CONTRÔLE croisé (la "
        "filiation dit l'événement officiel, l'époque dit la géométrie), jamais un conflit. "
        "Le point posé (PointOnSurface de l'union des filles) est marqué "
        "raw.origine_redecoupee=true dès que > 1 fille. Limites DITES : informatisation "
        "1980-90+ seulement, aménagements fonciers ruraux exclus (fiche 18 du rapport) — le "
        "reliquat d'orphelins est un état réel, mesuré au compte-rendu."),
    exemple_temoin="tests/test_sources1_lot6.py::test_filiation_idu_reconstruit",
    verifie_le="2026-09-07",
))
