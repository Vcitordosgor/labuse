"""Fiche de règle — sévérités des catégories de SUP. SOURCES-1 lot 1."""
from . import FicheRegle, declarer

declarer(FicheRegle(
    donnees=("sup_couche",),
    formule_codee=(
        "Parcelle ∩ assiette SUP (kind='sup', subtype=catégorie) → VIGILANCE graduée par "
        "catégorie (SUP_SEVERITES, etage1.py) : la plus sévère porte le verdict, toutes sont "
        "listées. t5/ac2/as1 → fort ; t4/t7/i1/i1bis/i3/i4/pt1/pt2 → moyen ; pm1/pm2/pm3/ac1/"
        "el10 → info ×0 (anti-double-compte : PPR via `risques`, MH via `abf`, parc national "
        "via `parc_national`) ; défaut → faible."),
    entrees=("spatial_layers (kind=sup : subtype=catégorie, attrs->nomsuplitt/geo)",
             "inventaire catégoriel 974 (sonde : api/document?documentType[]=SUP&grid=974)"),
    classe="choix_labuse",
    fonction="src/labuse/cascade/layers/etage1.py:SupLayer (SUP_SEVERITES)",
    verdict="choix_assume",
    choix=(
        "Mandat SOURCES-1 (06/09/2026) : « AS1 captages et T5 dégagement → RÉDHIBITOIRE selon la "
        "servitude, AC2 sites classés → VIGILANCE forte, PT1/PT2 → VIGILANCE ». État réel 974 au "
        "06/09/2026 (inventaire sondé) : AS1 NON publiée ; T5/PT1/PT2 publiées mais RESTREINTES "
        "au téléchargement (403 volontaire du gestionnaire) — aucune géométrie servable. Choix "
        "LABUSE : ac2 passe d'« info ×0 » à FORT (l'ancien anti-double-compte confondait "
        "Mérimée-MH (abf) et sites classés/inscrits — deux régimes distincts) ; pt1/pt2 déclarés "
        "MOYEN ; as1/t5 déclarés FORT en sévérité de flag, et le périmètre de protection "
        "IMMÉDIATE d'un captage AS1 deviendra RÉDHIBITOIRE à la première version réelle publiée "
        "(le niveau immédiat/rapproché/éloigné n'existe pas tant que la donnée n'est pas là — "
        "rien n'est inventé, la sonde catégorielle surveille la publication)."),
    exemple_temoin="tests/test_sources1_lot1.py::test_sup_severites",
    verifie_le="2026-09-07",
))
