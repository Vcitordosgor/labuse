"""SOURCES-AUDIT-1 — couche de curation (jugement humain adossé au code).

Clé = data_sources.id. Tout champ absent → l'automate décide (visibilité dérivée du registre,
comptes mesurés en base). Ce qui n'a pas pu être vérifié chez le producteur (aucun scraping)
est marqué « non vérifié » — jamais présenté comme un fait.

Sources des jugements : `registre/tables.py` (millésime/notes de couverture, vérité du code),
`data_sources.legal_notes` (licence en base), le graphe du registre (visibilité mesurée),
et la connaissance des jeux publics standard (marquée « non vérifié » quand incertaine).

Champs possibles : emprise, communes_couvertes, n_objets_producteur, ecart, part_parcelles,
champs_publies, champs_ingeres, champs_non_pris, geom_conservee, granularite,
granularite_respectee, millesime_producteur, cadence_officielle, test_client_clics, i_dit,
potentiel, manque_plein, principes_ok(list), principes_ko(list), verdict, verdict_raison.
"""
from __future__ import annotations

# ── les 7 principes du prompt tiers, repris pour les 116 (lot 5) — clés courtes ──
P_PROV = "provenance complète conservée"
P_974 = "filtrage 974 au plus tôt"
P_CRS = "CRS LABUSE respecté"
P_TESTS = "tests minimum par source"
P_ANTI = "anti-régression (volume→0 n'écrase pas)"

CURATION: dict[int, dict] = {

    # ══════════════ PARCELLES ET PROPRIÉTÉ ══════════════
    1: {  # Cadastre API Carto PCI
        "emprise": "île entière (24/24 communes)", "communes_couvertes": "24/24",
        "part_parcelles": "100 % — c'est le socle parcellaire (431 663 parcelles)",
        "granularite": "parcelle", "granularite_respectee": "oui",
        "geom_conservee": "oui (géométrie parcellaire complète)",
        "champs_publies": "idu, numéro, section, feuille, contenance, commune, géométrie",
        "champs_ingeres": "idu, section, contenance, géométrie, commune",
        "champs_non_pris": "aucun d'utile laissé — le PCI Express est ingéré au complet (à voir : le lien feuille/section pour la reconstitution d'îlots, mineur)",
        "i_dit": "non vérifié (socle, rarement affiché comme une « donnée »)",
        "millesime_producteur": "PCI Express « latest » — non vérifié à la date du jour",
        "cadence_officielle": "mise à jour continue (DGFiP), publication trimestrielle Etalab",
        "potentiel": "socle déjà à plein usage",
        "manque_plein": "rien de structurel — millésime à re-sonder par la sentinelle",
        "principes_ok": [P_PROV, P_974, P_CRS, P_ANTI],
        "verdict": "PLEINE",
        "verdict_raison": "Socle parcellaire complet (431 663 parcelles, 24/24), lu par la quasi-totalité des moteurs. À plein potentiel.",
    },
    2: {  # Cadastre Etalab (alias)
        "verdict": "ALIAS (doublon)",
        "verdict_raison": "Canal bulk du MÊME réservoir que Cadastre API Carto (id 1). Alias correctement déclaré (alias_de=1). Rien à faire.",
    },
    132: {  # DFI filiation
        "emprise": "île entière", "communes_couvertes": "24/24",
        "part_parcelles": "409 623 liens de filiation (1989→2025) — non ramené à un % parcelle",
        "granularite": "mutation/lien de filiation", "granularite_respectee": "oui",
        "champs_non_pris": "non vérifié (schéma DFI DGFiP non consulté)",
        "millesime_producteur": "situation 19/06/2026 (en base)",
        "verdict": "PLEINE",
        "verdict_raison": "409 623 liens 974 ingérés (job_sur_clic). Sert la reconstitution de propriété. Coverage insulaire complète.",
    },
    71: {  # DGFiP parcelles PM
        "emprise": "île entière", "communes_couvertes": "24/24",
        "part_parcelles": "82 701 parcelles de personnes morales (sur 431 663)",
        "granularite": "parcelle × propriétaire moral × millésime",
        "granularite_respectee": "oui",
        "champs_non_pris": "non vérifié — le panel 2019→2025 permettrait des séries (entrée/sortie du patrimoine PM) : à voir pour une couche « mouvements PM ».",
        "potentiel": "séries temporelles d'acquisition/cession PM (déjà 7 millésimes en base)",
        "manque_plein": "une vue « mouvements » exploitant les millésimes empilés",
        "verdict": "PLEINE",
        "verdict_raison": "Cœur de Scan patrimoine / propriétaire. 7 millésimes empilés, sert le moteur propriétaire_historique.",
    },
    15: {  # Potentiel foncier Région (potentiel)
        "verdict": "PARTIELLE — couverture incomplète",
        "granularite": "îlot/zone (PAS parcelle)",
        "granularite_respectee": "à vérifier — le potentiel foncier Région est un dérivé d'îlots ; ne doit pas être servi comme une vérité parcellaire",
        "verdict_raison": "DOUBLON à trancher avec id 9 (même producteur Région ODS, familles `potentiel` vs `urbanisme`). Licence « à confirmer ». 4 906 objets en couche potentiel_foncier+sar. Voir S3.",
        "potentiel": "couche d'orientation ; peu de valeur ajoutée vs le potentiel calculé maison",
        "manque_plein": "clarifier la licence Région et fusionner avec id 9",
        "principes_ko": [P_PROV + " (licence à confirmer)"],
    },
    9: {  # Potentiel foncier Région (urbanisme) — doublon de 15
        "verdict": "SERVIE HORS REGISTRE",
        "verdict_raison": "DOUBLON de id 15 (même jeu Région ODS « potentiel foncier »), rangé en famille `urbanisme`. Aucun slug réservoir distinct servi. À fusionner avec 15 — voir S3.",
        "potentiel": "aucun propre — redondant avec 15",
        "manque_plein": "décision de fusion (garder 15 « potentiel », retirer 9)",
    },

    # ══════════════ URBANISME ET RÈGLES ══════════════
    3: {  # Urbanisme PLU/GPU API Carto
        "emprise": "île entière (24/24, par commune)", "communes_couvertes": "24/24",
        "part_parcelles": "zonage servi sur toute parcelle (16 338 objets zone+prescription)",
        "granularite": "zone/prescription PLU", "granularite_respectee": "oui",
        "champs_non_pris": "le règlement écrit complet (seul l'extrait plu_reglement_extrait est pris) : à voir — le texte intégral par zone serait exploitable par le Copilote.",
        "millesime_producteur": "GPU vivant, interrogé en direct — non pinné",
        "potentiel": "règlement écrit intégral indexé pour le Copilote ; historique des révisions",
        "manque_plein": "ingestion du règlement écrit complet (aujourd'hui : extrait)",
        "verdict": "PLEINE",
        "verdict_raison": "Zonage + prescriptions servis sur toute l'île, cœur de la faisabilité et du scoring. Interrogé en direct (GPU).",
    },
    44: {  # SUP GPU
        "verdict": "PARTIELLE — couverture incomplète",
        "emprise": "île entière mais catégories restreintes",
        "granularite": "assiette SUP", "granularite_respectee": "oui",
        "verdict_raison": "9 catégories SUP en vigueur ; T5/PT1/PT2 restreintes, AS1 (captages) NON publiée par le producteur. Couverture bornée par la publication GPU, pas par nous.",
        "champs_non_pris": "les SUP non publiées au GPU (AS1 captages) — à demander à l'ARS/DEAL (lot 7).",
        "potentiel": "AS1 (périmètres de captage) comblerait le plus gros trou réglementaire",
        "manque_plein": "obtenir AS1 hors GPU (source ARS)",
    },
    107: {  # DPU
        "verdict": "PARTIELLE — couverture incomplète",
        "emprise": "4/24 communes publiées au GPU", "communes_couvertes": "4/24",
        "granularite": "périmètre DPU", "granularite_respectee": "oui",
        "verdict_raison": "GPU typeinf 04 — seulement 4/24 communes ont publié leur DPU au GPU (06/09/2026). Là où c'est absent, ne pas affirmer « pas de DPU ». Les non-publiées sont listées.",
        "champs_non_pris": "les DPU des 20 communes non publiées — à demander aux communes/EPCI.",
        "potentiel": "couverture 24/24 sur demande",
        "manque_plein": "récupérer les 20 DPU manquants (délibérations communales)",
    },
    108: {  # PEB
        "verdict": "PARTIELLE — couverture incomplète",
        "emprise": "Roland-Garros seul (Pierrefonds non publié)",
        "granularite": "zone A/B/C/D bruit aéroport", "granularite_respectee": "oui",
        "verdict_raison": "PEB Roland-Garros B/C/D via annexes GPU ; PEB de Pierrefonds NON publié. Trou connu au sud.",
        "champs_non_pris": "PEB Pierrefonds — à demander à la DGAC/DEAL.",
        "potentiel": "ajouter Pierrefonds",
        "manque_plein": "PEB Pierrefonds",
    },
    105: {"verdict": "PLEINE", "verdict_raison": "Emplacements réservés (typepsc 05) servis par commune via GPU. Couche + cascade."},
    106: {"verdict": "PLEINE", "verdict_raison": "EBC (typepsc 01) servis par commune via GPU. Couche + cascade."},
    62: {  # Sudocuh
        "verdict": "PARTIELLE — champs manquants",
        "emprise": "île entière (procédures d'urbanisme)",
        "millesime_producteur": "état au 31/12/2024 (en base)",
        "verdict_raison": "État 31/12/2024 (dépôt manuel). Sert les procédures PLU. À voir : fraîcheur (dépôt manuel, cadence non tenue automatiquement).",
        "champs_non_pris": "non vérifié (schéma Sudocuh non consulté)",
    },
    102: {  # ENAF conso
        "verdict": "PLEINE",
        "emprise": "île entière par commune", "communes_couvertes": "24/24",
        "verdict_raison": "Conso ENAF 2021-2024 par commune (portail artificialisation). Sert le contexte ZAN commune.",
        "potentiel": "la trajectoire ZAN (objectif -50 % d'ici 2031) pourrait être calculée depuis la série",
        "manque_plein": "un indicateur trajectoire ZAN dérivé",
    },
    128: {  # ORT/ACV/PVD
        "verdict": "PARTIELLE — couverture incomplète",
        "emprise": "19/24 communes (13 ORT signées)", "communes_couvertes": "19/24",
        "granularite": "commune (éligibilité), PAS périmètre infra-communal",
        "granularite_respectee": "oui — servi comme éligibilité communale, pas comme périmètre",
        "verdict_raison": "Table DGALN vivante, 19 communes. C'est l'éligibilité COMMUNALE ; le périmètre ORT infra-communal (Denormandie) est une source à part (id 138, à demander).",
    },

    # ══════════════ RISQUES, NATURE, PATRIMOINE ══════════════
    4: {  # Géorisques (aléas)
        "emprise": "île entière", "communes_couvertes": "24/24",
        "granularite": "aléa (polygone)", "granularite_respectee": "oui",
        "champs_non_pris": "non vérifié — l'API Géorisques expose plus d'aléas que ceux ingérés ; couverts par les sources sœurs (SSP, cavités, ICPE, mvt, SIS, CASIAS, CatNat).",
        "verdict": "PLEINE",
        "verdict_raison": "Aléas Géorisques servis (couche + fiche Pièges + cascade). Complété par 8 sources Géorisques sœurs.",
    },
    97: {  # CatNat — HORS REGISTRE
        "verdict": "SERVIE HORS REGISTRE",
        "emprise": "île entière (426 arrêtés, 24 communes)", "communes_couvertes": "24/24",
        "granularite": "arrêté CatNat par commune", "granularite_respectee": "oui",
        "verdict_raison": "426 arrêtés servis (fiche commune / Pièges) MAIS aucun chiffre du registre ne déclare le réservoir `catnat_gaspar` (le chiffre `catnat_n` a `reservoirs={}`). La donnée coule, la provenance n'est pas tracée — trou de registre à combler.",
        "champs_non_pris": "l'objet précis de chaque arrêté (inondation/mvt/sécheresse) est en base mais pourrait mieux ressortir en fiche.",
        "potentiel": "chronologie CatNat par commune (fréquence d'arrêtés = signal de risque)",
        "manque_plein": "rattacher catnat_gaspar à un chiffre du registre (provenance)",
        "principes_ko": [P_PROV + " (chiffre sans réservoir déclaré)"],
    },
    98: {  # Taxe d'aménagement — HORS REGISTRE
        "verdict": "SERVIE HORS REGISTRE",
        "emprise": "24/24 communes en vigueur (08/09/2026)", "communes_couvertes": "24/24",
        "granularite": "taux communal", "granularite_respectee": "oui",
        "verdict_raison": "Taux 24/24 servis (outil Taxe d'aménagement + Financier) MAIS les chiffres `taxe_amenagement_eur`/`taxe_amenagement_estimee_eur` ont `reservoirs={}` — le taux communal saisi n'est pas rattaché comme réservoir. Provenance non tracée.",
        "champs_non_pris": "part départementale/RAP éventuelle — non vérifié.",
        "potentiel": "historique des délibérations de taux",
        "manque_plein": "rattacher `taxe_amenagement`/`taxe_amenagement_taux` aux chiffres taxe du registre",
        "principes_ko": [P_PROV + " (chiffres taxe sans réservoir déclaré)"],
    },
    115: {  # SIS
        "verdict": "PARTIELLE — couverture incomplète",
        "emprise": "4 SIS sur l'île (secteurs d'information sur les sols)",
        "granularite": "secteur d'info sol (polygone)", "granularite_respectee": "oui",
        "verdict_raison": "4 SIS 974 seulement (c'est la réalité du producteur, pas un manque LABUSE). Canal SSP partagé.",
    },
    116: {  # CASIAS
        "verdict": "PLEINE",
        "emprise": "453 sites (435 points, 18 emprises)",
        "verdict_raison": "453 anciens sites industriels servis (couche sol_pollue). Couverture conforme au producteur.",
    },
    112: {  # Zones humides
        "verdict": "PARTIELLE — couverture incomplète",
        "verdict_raison": "Inventaires DEAL 2003/2009/2011/2019 par secteurs — partiels par construction (le producteur n'a pas inventorié toute l'île). 3 122 objets.",
        "granularite": "zone humide (polygone)", "granularite_respectee": "oui",
    },
    110: {  # ZPPA a_faire
        "verdict": "À DEMANDER / À BRANCHER",
        "verdict_raison": "Atlas des patrimoines injoignable au 06/09/2026 — aucune donnée. Sentinelle de rappel 180 j posée. Pas d'accès officiel stable constaté.",
    },
    76: {  # ZNIEFF INPN — canonique
        "verdict": "PLEINE",
        "verdict_raison": "ZNIEFF servies (162 objets, maj 29/08/2025). Canonique face à id 80 (canal Région, retiré). Voir S3.",
    },
    28: {"verdict": "PLEINE", "verdict_raison": "Trait de côte / érosion côtière 2018 (24 168 objets). Couche carte. Millésime ancien (2018) à re-sonder."},
    7: {"verdict": "PARTIELLE — champs manquants", "verdict_raison": "Parc National servi (3 objets couche). Licence « à confirmer » (jeu pnrun_2021 via Région ODS) — provenance à clarifier.", "principes_ko": [P_PROV + " (licence à confirmer)"]},
    25: {"verdict": "PARTIELLE — champs manquants", "verdict_raison": "Espaces protégés INPN servis (couche ens). Licence « à confirmer ».", "principes_ko": [P_PROV + " (licence à confirmer)"]},

    # ══════════════ MARCHÉ, LOGEMENT, PERMIS ══════════════
    5: {  # DVF Etalab — canonique
        "emprise": "île entière", "communes_couvertes": "24/24",
        "granularite": "mutation (parcelle)", "granularite_respectee": "oui",
        "millesime_producteur": "géo-DVF 2021-2025 + archives DGFiP 2014-2020 (en base)",
        "champs_non_pris": "nature de culture, droits réels — non vérifié ; l'essentiel (prix, date, surface, type) est pris.",
        "potentiel": "déjà exploité en profondeur (médianes secteur, prix sortie neuf, VEFA)",
        "manque_plein": "rien de structurel",
        "verdict": "PLEINE",
        "verdict_raison": "DVF canonique (Etalab + archives DGFiP), cœur du marché. Contrainte L.112 A LPF (pas de réidentification) respectée. Face à id 119 (DVF Région), c'est la source de référence. Voir S3.",
        "principes_ok": [P_PROV, P_974, P_ANTI],
    },
    119: {  # DVF Région — doublon
        "verdict": "SERVIE HORS REGISTRE",
        "verdict_raison": "DOUBLON de DVF Etalab (id 5). Jeu Région figé 2014→mi-2021 (54 449 mutations), utilisé UNIQUEMENT comme échantillon du filtre DVF (contrôle producteur), non servi au client. `region_dvf` = réservoir sans table. Voir S3 : garder comme témoin de filtre ou retirer.",
        "potentiel": "témoin de contrôle qualité DVF, rien de plus",
        "manque_plein": "décider : témoin de filtre (garder discret) ou retrait",
    },
    16: {  # Sitadel
        "emprise": "île entière", "communes_couvertes": "24/24",
        "part_parcelles": "50 545 permis rattachés",
        "granularite": "permis (point/parcelle)", "granularite_respectee": "oui",
        "millesime_producteur": "2026-07 (en base) ; SDES publie au mois",
        "champs_non_pris": "non vérifié — le détail des surfaces créées par destination pourrait être mieux exploité.",
        "verdict": "PLEINE",
        "verdict_raison": "50 545 permis, cron mensuel. Sert marché, délais d'instruction, dynamique commune. À plein usage.",
    },
    84: {  # Radar pige — manuelle
        "verdict": "MANUELLE",
        "verdict_raison": "Pige d'annonces = collecte HUMAINE (dépôt manuel de pages HTML). Le client voit le Radar. Voir Lot 3 : dernière alimentation et procédure.",
        "champs_non_pris": "faits déclarés d'annonce (zone PLU, drapeaux) exploités ; le texte libre non.",
    },
    129: {"verdict": "PLEINE", "verdict_raison": "Loyers OLL 2024 (6 zones + agglo), servis par zone/IRIS. Granularité zone respectée."},
    130: {"verdict": "PARTIELLE — champs manquants", "verdict_raison": "Carte des loyers DHUP 2025, extrait 974 embarqué (offline, dépôt manuel). Repli de l'OLL. Fraîcheur à surveiller."},
    100: {"verdict": "PLEINE", "verdict_raison": "RNIC copropriétés (2 220 copros). Sert le signal copropriété. Millésime annuel Anah."},
    101: {"verdict": "PLEINE", "verdict_raison": "RPLS logements sociaux (01/01/2025). Sert SRU/contexte social par commune."},
    39: {"verdict": "PLEINE", "verdict_raison": "Inventaire SRU (LLS) par commune. Sert le contexte logement social. 24/24."},
    40: {"verdict": "PARTIELLE — champs manquants", "verdict_raison": "NPNRU quartiers (couche anru). Licence État LOv2 2022 — millésime à re-sonder.", "granularite": "quartier"},
    41: {"verdict": "PLEINE", "verdict_raison": "INSEE RP Logement 2023 par commune. Contexte logement."},
    42: {  # PLH — dépôt manuel
        "verdict": "PARTIELLE — champs manquants",
        "verdict_raison": "PLH des 5 EPCI par extraction documentaire (dépôt manuel, 07/07/2026). Chaque chiffre porte sa référence. Fraîcheur dépend d'un geste humain.",
    },
    133: {"verdict": "PLEINE", "verdict_raison": "RP2022 bases IRIS (logement/population), géographie 2024. Sert fiche commune quartiers."},
    109: {"verdict": "PLEINE", "verdict_raison": "Zonage ABC 24/24 (arrêté 23/06/2026 : 4 A, 20 B1). Sert défiscalisation/éligibilités."},

    # ══════════════ ÉNERGIE, RÉSEAUX, ASSAINISSEMENT ══════════════
    48: {  # PVGIS
        "emprise": "île entière (API de calcul)", "granularite": "parcelle (au run solaire)",
        "granularite_respectee": "oui", "millesime_producteur": "PVGIS v5.3 / SARAH3 (API)",
        "champs_non_pris": "PVGIS expose l'irradiation mensuelle et l'optimum d'inclinaison — vérifier qu'on exploite l'optimum (audit VERIF-1 : le pied « inclinés à 65° » était littéral).",
        "verdict": "PLEINE",
        "verdict_raison": "API de calcul solaire (CC BY 4.0). Alimente productible. À plein usage ; attention libellé inclinaison (dette VERIF-1).",
        "principes_ok": [P_PROV],
    },
    93: {"verdict": "PLEINE", "verdict_raison": "Lignes HTA EDF (19 480 objets, publié 16/10/2025). Couche réseau. Géométrie ~02/2020 (ancienne, mais publiée telle quelle par EDF)."},
    126: {"verdict": "PLEINE", "verdict_raison": "Fibre Arcep 330 051 immeubles (2026_T1). Sert l'éligibilité fibre à l'immeuble."},
    66: {"verdict": "PLEINE", "verdict_raison": "RP2022 fichier Logements (EGOUL) → maille ANC. Sert le taux d'assainissement collectif/non collectif."},
    68: {  # Office de l'eau — RETRAIT EN ATTENTE
        "verdict": "PARTIELLE — couverture incomplète",
        "emprise": "6 communes 100 % ANC (sur 24)", "communes_couvertes": "6/24",
        "granularite": "commune", "granularite_respectee": "oui",
        "verdict_raison": "⚠ RETRAIT EN ATTENTE (lot 0 S2). Vic avait décidé le retrait, mais `anc_service.py:57` lit encore `anc_office_eau_commune` EN DIRECT pour servir le statut ANC des 6 communes 100 % ANC (chiffre `part_logements_egout_pct`, moteur `anc`, fiche Réseaux). Retrait refusé tant que ce lecteur vit. Licence « à confirmer ».",
        "champs_non_pris": "les chroniques quantitatives (qualité/volume d'eau) — non exploitées, hors périmètre foncier.",
        "manque_plein": "d'abord débrancher anc_service du réservoir (mandat dédié), ensuite retirer.",
    },
    134: {"verdict": "À DEMANDER / À BRANCHER", "verdict_raison": "Zonages d'assainissement SIG complets — 4/24 via GPU aujourd'hui ; les 20 autres à demander aux 5 EPCI/régies (DEMANDE-REGION-EPCI). Voir Lot 2."},

    # ══════════════ ÉCONOMIE, ÉQUIPEMENTS, ACCÈS ══════════════
    21: {  # SIRENE (API directe) — servie via API
        "verdict": "PLEINE",
        "emprise": "île entière (API INSEE en direct)",
        "granularite": "établissement/unité légale", "granularite_respectee": "oui",
        "verdict_raison": "Servie via l'API recherche-entreprises EN DIRECT (Scan patrimoine, Copilote entreprise) — d'où 0 chiffre de registre attaché à `sirene_recherche_entreprises` (API à la requête, sans table). Ce n'est PAS invisible : le pro l'atteint par le Scan/Copilote. Le canal géolocalisé (id 86) est la variante à réservoir. Voir S3.",
        "champs_non_pris": "diffusion 'P' (non-diffusibles) masquée à dessein.",
    },
    45: {  # DINUM — RETRAIT EN ATTENTE
        "verdict": "PARTIELLE — couverture incomplète",
        "emprise": "cache d'enrichissement (9 730 enrich., 2 650 dénominations)",
        "verdict_raison": "⚠ RETRAIT EN ATTENTE (lot 0 S2). Vic avait décidé le retrait, mais `owner_enrichment`/`owner_denom_lookup` sont lus EN DIRECT par le Score V (`score_v.py:90,98`), les facettes propriétaire (`proprietaire_facettes.py:70`) et le Scan (`app.py:4695`) — chiffre `evenements_proprietaire_liste`, fiche Propriétaire. Retrait refusé tant que ces lecteurs vivent.",
        "manque_plein": "d'abord débrancher score_v/facettes/scan, ensuite retirer.",
    },
    86: {  # SIRENE établissements géoloc — doublon canal de 21
        "verdict": "PLEINE",
        "verdict_raison": "SIRENE géolocalisé (cron mensuel), variante à réservoir de la SIRENE API (id 21). Sert l'étude de zone (concurrents). Les deux coexistent par usage distinct (direct vs snapshot géo) — voir S3.",
        "granularite": "établissement géolocalisé",
    },
    88: {"verdict": "PLEINE", "verdict_raison": "Trafic RN Région (comptages par tronçon). Sert l'accessibilité/attractivité de zone."},
    20: {"verdict": "PLEINE", "verdict_raison": "BPE INSEE 2025 (équipements, 35 546 objets couche). Sert l'attractivité (commerces, écoles…)."},
    52: {"verdict": "PLEINE", "verdict_raison": "Filosofi 2021 (carreaux 200 m). Sert le revenu/population de zone. Millésime 2021 (le plus récent publié)."},
    64: {"verdict": "PLEINE", "verdict_raison": "Contours IRIS 2024. Socle géographique infra-communal (rattachements)."},
    18: {"verdict": "PLEINE", "verdict_raison": "BAN — géocodage d'adresses (job sur clic). Socle adresses↔parcelles."},
    99: {"verdict": "PLEINE", "verdict_raison": "Annuaire service-public (24 mairies, cron mensuel). Sert le bloc Mairie & urbanisme."},
    74: {"verdict": "PLEINE", "verdict_raison": "GTFS 7 réseaux (PAN, maj 2026). Arrêts/lignes de transport en couche."},
    75: {"verdict": "PLEINE", "verdict_raison": "OSM transport (pôles d'échange, téléphérique). Couche."},
    94: {"verdict": "PLEINE", "verdict_raison": "TCSP voies bus en site propre (OSM). Couche + valorisation L151-36."},
    19: {"verdict": "PLEINE", "verdict_raison": "OSM/Overpass — aménités (21 561 objets). Signal. ODbL (share-alike) respecté."},
    29: {"verdict": "PLEINE", "verdict_raison": "BODACC procédures collectives (job sur clic). Signal entreprise/propriétaire."},
    31: {"verdict": "PARTIELLE — champs manquants", "verdict_raison": "INPI RNE dirigeants. Licence SPÉCIFIQUE homologuée (pas Licence Ouverte) — usage encadré, à respecter.", "principes_ok": [P_PROV]},

    # ══════════════ TERRAIN, SOL, IMAGERIE ══════════════
    17: {  # BD TOPO
        "emprise": "île entière", "granularite": "bâtiment/voirie/eau/ravine",
        "granularite_respectee": "oui",
        "champs_non_pris": "BD TOPO expose bien plus de thèmes (hydro complète, végétation, équipements) que les 4 kinds ingérés (batiment, voirie, water, ravine) : à voir selon besoin.",
        "verdict": "PLEINE",
        "verdict_raison": "1,07 M d'objets (bâti, voirie, eau, ravine). Socle géométrique lu par potentiel/solaire/viabilisation. À plein usage sur les thèmes ingérés.",
        "potentiel": "thèmes BD TOPO non ingérés (végétation, équipements) selon besoin",
        "manque_plein": "rien de structurel pour l'usage actuel",
    },
    83: {  # CoSIA
        "emprise": "île entière", "part_parcelles": "445 190 bâtiments CoSIA",
        "granularite": "bâtiment (couverture du sol IA)", "granularite_respectee": "oui",
        "millesime_producteur": "CoSIA 2025 (PVA juil-août 2025, 20 cm)",
        "champs_non_pris": "CoSIA publie plusieurs classes d'occupation du sol (végétation, eau, route…) — seul le bâti est exploité ici. La NOUVELLE donnée « usage/artificialisation » relève d'OCS GE (candidate), pas de CoSIA.",
        "verdict": "PLEINE",
        "verdict_raison": "445 190 bâtis IA (2025), cœur du potentiel/scoring. Bâti à plein usage ; autres classes CoSIA non exploitées (par choix).",
        "potentiel": "classes CoSIA non-bâti (végétation, sols) si besoin",
    },
    70: {  # LiDAR HD — LOT 4 (mesuré sur la base servie, batch achevé)
        "verdict": "PARTIELLE — couverture incomplète",
        "coverage_tables": ["batiment_hauteur_lidar"],
        "emprise": "hauteur faîtage/égout sur 303 452 / 431 663 parcelles (~70 %) — batch de dalles ACHEVÉ (2 665/2 665)",
        "communes_couvertes": "24/24 (couverture parcellaire ~70 %)",
        "part_parcelles": "303 452 / 431 663 = 70,3 % (batiment_hauteur_lidar, mesuré) ; le verdict de TOITURE (toiture_lidar) ne couvre lui que 27 parcelles",
        "granularite": "parcelle (faîtage/égout) + bâtiment (toiture)", "granularite_respectee": "oui",
        "verdict_raison": "Correction (2ᵉ passe) : la hauteur LiDAR (faîtage/égout) couvre 303 452 parcelles (~70 %) dans `batiment_hauteur_lidar` — le batch de dalles a ACHEVÉ (les figures « 5 406 » de État-1 et « 80 905 » de RECETTE-11 sont périmées). Reste partielle car ~30 % des parcelles n'ont pas de bâti mesuré et le VERDICT de toiture (`toiture_lidar`) n'existe que sur 27 parcelles. **Provenance à corriger** : la hauteur LiDAR alimente `marge_surelevation_m`/`hauteur_bati_m` mais le registre crédite `bd_topo`, pas `lidar_hd_mnh` — la source LiDAR n'est pas tracée sur ce qu'elle sert.",
        "champs_non_pris": "le verdict de toiture (pente/forme) n'est calculé que sur 27 parcelles alors que la hauteur couvre 70 % : le calcul toiture est le vrai retard, pas la hauteur.",
        "potentiel": "étendre le verdict de toiture à la couverture hauteur (70 %) ; rattacher lidar_hd_mnh aux chiffres surélévation",
        "manque_plein": "1) rattacher lidar_hd_mnh à marge_surelevation_m/hauteur_bati_m (provenance) ; 2) étendre toiture_lidar",
        "principes_ko": ["provenance — hauteur LiDAR créditée à bd_topo, pas à lidar_hd_mnh"],
    },
    6: {"verdict": "PLEINE", "verdict_raison": "RGE ALTI — pente 5 m (147 398 objets). Socle topographique (pente, viabilisation)."},
    65: {"verdict": "ALIAS (doublon)", "verdict_raison": "RGE ALTI 5 m = même réservoir que id 6 (alias_de=6). Alias correct."},
    61: {"verdict": "PLEINE", "verdict_raison": "BD ORTHO 20 cm 2025. Détection piscines (90,7 %), fond ortho. À plein usage."},
    69: {  # BD ORTHO IRC — RETRAIT EN ATTENTE
        "verdict": "PARTIELLE — couverture incomplète",
        "emprise": "île entière (dérivé végétation)",
        "part_parcelles": "parcel_vegetation : 431 663 (île entière)",
        "granularite": "parcelle (ombrage/canopée NDVI)", "granularite_respectee": "oui",
        "verdict_raison": "⚠ RETRAIT EN ATTENTE (lot 0 S2). Vic avait décidé le retrait, mais l'infrarouge IRC est la source du NDVI/canopée : `parcel_vegetation` (431 663 lignes) est lu EN DIRECT par le solaire (`solaire.py:311` ombrage), le Flash (`flash/data.py:650`) et le scoring P (`p_model/sql.py:287`). Chiffre `prod_spec_kwh_kwc`, fiche Solaire. Retrait refusé tant que ces lecteurs vivent.",
        "manque_plein": "d'abord débrancher l'ombrage végétal du solaire/scoring, ensuite retirer.",
    },
    22: {"verdict": "PARTIELLE — champs manquants", "verdict_raison": "BD CARTO V5 occupation du sol (proxy OCS, 1 643 objets). Proxy grossier — l'OCS GE officielle est une candidate (lot 5)."},
    96: {"verdict": "PLEINE", "verdict_raison": "Cadastre d'époque (archives PCI 2017→2026). Sert le rattachement des permis anciens (RETOURS-14)."},
    10: {  # RPG proxy
        "verdict": "PARTIELLE — champs manquants",
        "verdict_raison": "RPG déclarations agricoles servi via un PROXY IGN (RPG.LATEST, année non pinnée) ; le vrai RPG DAAF n'est pas public. Licence « à confirmer ». Code culture servi (canne). Couche « cultures déclarées » + cascade zone A.",
        "principes_ko": [P_PROV + " (proxy, licence à confirmer, année non pinnée)"],
    },

    # ══════════════ HUBS ══════════════
    11: {"verdict": "HUB (catalogue)", "verdict_raison": "Portail Région ODS — hub de catalogue, jamais un réservoir. Licence par jeu à confirmer."},
    12: {"verdict": "HUB (catalogue)", "verdict_raison": "PEIGEO/AGORAH — hub régional, jamais un réservoir."},
    14: {"verdict": "HUB (catalogue)", "verdict_raison": "Géoplateforme IGN — hub, jamais un réservoir. Point d'accès de nombreuses sources IGN."},
    13: {"verdict": "PARTIELLE — champs manquants", "verdict_raison": "DEAL WMS/WFS — canal servi par proxys ; les tables sont portées par qpv/npnru. Peu autonome comme « source »."},

    # ══════════════ FISCAL / RÉGLEMENTAIRE ══════════════
    38: {"verdict": "PLEINE", "verdict_raison": "QPV 2024 (70 objets couche). Sert défiscalisation/TVA primo. À jour."},
    72: {"verdict": "PLEINE", "verdict_raison": "ZFANG (décret 2026-421). Zonage fiscal servi (couche + territoire fiscal). À jour."},
    73: {"verdict": "PLEINE", "verdict_raison": "FRR ex-ZRR (Légifrance). Zonage fiscal rural servi."},
    127: {"verdict": "PLEINE", "verdict_raison": "Taux taxe foncière REI 2025, 24/24. Sert l'estimation fiscale (fiche commune fiscalité)."},
    131: {"verdict": "PLEINE", "verdict_raison": "Coût de construction (EPTB 2024 + choix LABUSE 2300-2800 €/m²). Sert le bilan promoteur. Le « choix LABUSE » est délibéré et sourcé."},
    43: {  # RTAA DOM — servie via règles
        "verdict": "PLEINE",
        "verdict_raison": "RTAA DOM = règles portées PAR LE CODE (aucune table), servies dans la faisabilité (contraintes construction DOM). 0 chiffre attaché car ce sont des règles, pas une donnée mesurée — ce n'est pas « invisible ». Textes Légifrance vérifiés « en vigueur ».",
        "granularite": "règle nationale DOM", "granularite_respectee": "oui",
    },
    46: {"verdict": "PLEINE", "verdict_raison": "Classement sonore ITT (arrêtés déc. 2023, 1 004 objets). Couche bruit routier."},
    47: {"verdict": "PLEINE", "verdict_raison": "50 pas géométriques (cadastre 1877 géoréf.). Limite littorale servie. Couche."},

    # ══════════════ AUTRES RISQUES GÉORISQUES (concis) ══════════════
    32: {"verdict": "PLEINE", "verdict_raison": "Sites et sols pollués (513 objets). Couche + Pièges."},
    33: {"verdict": "PLEINE", "verdict_raison": "Cavités souterraines (151 objets). Couche + Pièges."},
    34: {"verdict": "PLEINE", "verdict_raison": "ICPE (1 261 objets). Couche + Pièges + cascade."},
    36: {"verdict": "PLEINE", "verdict_raison": "Mouvements de terrain (3 085 objets). Couche + Pièges + cascade (RETOURS-13)."},
    114: {"verdict": "PLEINE", "verdict_raison": "AZI/TRI inondation par commune (GASPAR). Fiche commune risques."},
    117: {"verdict": "PARTIELLE — couverture incomplète", "verdict_raison": "Cartes de bruit stratégiques CBS 2022 — 6 zones de dépassement seulement (échéance 4, RN/RD/VC). Partiel par construction."},
    111: {"verdict": "PLEINE", "verdict_raison": "Ravines DPF (arrêté 2006, 275 tronçons + 6 plans). Couche dpf. Le DPE (privé État) non diffusé."},
    113: {"verdict": "PLEINE", "verdict_raison": "Espaces protégés complémentaires (Ramsar 1, sites classés/inscrits 7, RN 3). Complète le kind ens INPN."},
    35: {"verdict": "PLEINE", "verdict_raison": "Cartofriches Cerema (372 friches). Couche + signal foncier."},
    24: {"verdict": "PLEINE", "verdict_raison": "ABF/Monuments historiques (Mérimée, 200 périmètres). Couche + contrainte patrimoine."},

    # ══════════════ ÉNERGIE / DPE ══════════════
    37: {"verdict": "PARTIELLE — couverture incomplète",
         "part_parcelles": "17 DPE, 1 passoire thermique — mesuré sur la base servie",
         "verdict_raison": "⚠ Coverage RÉELLE quasi-nulle sur la base servie : `dpe_records` = 17, `v_passoire_thermique` = 1. « Connecté » mais l'ingestion DPE (cron mensuel) n'a quasi rien chargé — ce n'est PAS un artefact de base de dev (la base porte 431 663 parcelles), c'est un vrai trou d'ingestion à investiguer (le cron tourne-t-il ? l'API ADEME répond-elle ?).",
         "granularite": "logement (DPE déclaré)", "granularite_respectee": "à vérifier — un DPE est un logement, pas une parcelle : ne pas généraliser à la parcelle.",
         "manque_plein": "relancer/réparer l'ingestion DPE (17 records ≈ vide)"},

    # ══════════════ RETIRÉES (déjà) ══════════════
    49: {"verdict": "RETIRÉE (déjà)", "verdict_raison": "EDF SEI open data — amont 410 Gone (jeu retiré par EDF ~2026). Retirée 06/09/2026. Rien à sonder. Le réseau HTA vit via id 93."},
    50: {"verdict": "RETIRÉE (déjà)", "verdict_raison": "Registre national installations (ODRÉ) — jamais branché, aucun usage. Retirée 06/09/2026."},
    80: {"verdict": "RETIRÉE (déjà)", "verdict_raison": "ZNIEFF canal Région — endpoint vivant mais 0 donnée. Retirée 06/09/2026. Canonique : id 76."},
    87: {"verdict": "RETIRÉE (déjà)", "verdict_raison": "MOBPRO — abandonnée par ZONE-DONNÉES ; lecteur zone.emplois_communes sans appelant (code mort). Retirée 06/09/2026. Précédent-clé : retirée car PLUS RIEN DE SERVI."},
    89: {"verdict": "RETIRÉE (déjà)", "verdict_raison": "BDNB — ne couvre pas le 974 (métropole seule, 0 ligne 974 vérifié). Retirée 06/09/2026 ; sentinelle+cron conservés pour un futur millésime 974. NB (lot 5) : LABUSE NE possède PAS BDNB."},

    # ══════════════ MANUELLES (Lot 3) ══════════════
    27: {"verdict": "MANUELLE", "verdict_raison": "Fichiers fonciers Cerema — SOUS CONVENTION, non instruite. Aucune donnée ingérée. En attendant : DVF ouvert. Voir Lot 3 + DEMANDE."},
    141: {"verdict": "MANUELLE", "verdict_raison": "LOVAC — détail RÉSERVÉ aux collectivités/État/Anah (fiche 19). Non ingéré. En attendant : vacance INSEE RP par IRIS. Voir Lot 3 : sur quelle base on la lirait (une collectivité mandante requise)."},
    142: {"verdict": "MANUELLE", "verdict_raison": "DV3F Cerema — même convention que les Fichiers fonciers. Non ingéré. En attendant : DVF + échantillon Région. Voir Lot 3."},
    26: {"verdict": "MANUELLE", "verdict_raison": "VRD/SPANC — saisie EPCI manuelle, aucune table dédiée. Collectif/non-collectif saisi. Licence « à confirmer ». Voir Lot 3."},

    # ══════════════ À FAIRE / À DEMANDER (Lot 2) ══════════════
    95: {"verdict": "À DEMANDER / À BRANCHER", "verdict_raison": "Réunion Express — hypothèses de tracé au débat public CNDP. Rien d'ingéré (ce ne sont pas des données arrêtées). À surveiller, pas à brancher."},
    118: {"verdict": "À DEMANDER / À BRANCHER", "verdict_raison": "SAR — couche SIG officielle NON diffusée par la Région (recherche 07/09/2026). Un proxy vocations existe (sar_region). À demander à la Région (lot 7). Non opposable directement."},
    135: {"verdict": "À DEMANDER / À BRANCHER", "verdict_raison": "Inventaires ZAE (L.318-8-2 CU) — à demander aux 5 EPCI. Demande prête (DEMANDE-REGION-EPCI)."},
    136: {"verdict": "À DEMANDER / À BRANCHER", "verdict_raison": "Périmètres de ZAC — pas d'open data 974 fiable. À demander (EPCI/communes/EPF). Standard CNIG ZAC."},
    137: {"verdict": "À DEMANDER / À BRANCHER", "verdict_raison": "OPAH/PIG — pas de périmètre polygone ouvert. À demander (Anah/EPCI)."},
    138: {"verdict": "À DEMANDER / À BRANCHER", "verdict_raison": "Périmètres ORT infra-communaux — à demander aux EPCI. L'éligibilité communale est déjà servie (id 128)."},
    139: {"verdict": "À DEMANDER / À BRANCHER", "verdict_raison": "ENS du Département — non diffusés en open data. À demander au Conseil départemental (droit de préemption ENS)."},
    140: {"verdict": "À DEMANDER / À BRANCHER", "verdict_raison": "Micro-données OLL — accès conventionné (ADIL/AGORAH). Agrégats par zone déjà servis (id 129). À conventionner pour le détail."},
    67: {"verdict": "ALIAS (doublon)", "verdict_raison": "GPU zonages assainissement (info-surf) = canal info-surf du même réservoir que id 63 (alias_de=63). Alias correct."},
    63: {"verdict": "PARTIELLE — couverture incomplète", "verdict_raison": "GPU zonages d'assainissement — SIG complet 4/24 communes seulement (11/07/2026). Les 20 autres à demander (id 134). Couche zonage_assainissement (258 objets)."},
}
