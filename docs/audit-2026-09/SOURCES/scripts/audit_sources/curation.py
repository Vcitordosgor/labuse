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

    # ══════════════ SOURCES-2 (13-14/09/2026) — verdicts recalculés après le mandat ══════════════
    30: {  # DEAL PPR / aléas
        "verdict": "PLEINE",
        "verdict_raison": "WFS Lizmap 01risque : PPR zonage + aléas inondation (76), mouvement de terrain (917) et — SOURCES-2 lot 3 — SUBMERSION MARINE (50 + 50 changement climatique) = 1 093 zones. + couche « état des PAC/PPR/PPRL » (24 communes, statuts et dates) qui sert le millésime PRODUCTEUR : PPR le plus récent approuvé le 16/04/2026.",
        "millesime_producteur": "PPR le plus récent approuvé le 16/04/2026 (couche état, lue chez le producteur)",
    },
    37: {  # DPE ADEME
        "verdict": "BRANCHÉE INVISIBLE (vide)",
        "verdict_raison": "SOURCES-2 lot 0 : les TROIS jeux ADEME moissonnés au CP brut (existants + neufs + tertiaire) = 93 lignes dont 16 RÉUNIONNAISES corroborées (75 « neufs ST LEU » = Saint-Leu-la-Forêt 95 — homonymie ; 2 = Montpellier/Lille). 16/16 rattachées parcelle, 8 avec ID-RNB, miroir producteur. Le vide est un TROU PRODUCTEUR (les DPE DROM ne remontent pas à l'observatoire — corollaire : DPEENERGIE vide sur les 87 553 logements RPLS 974) — pas un trou de filtre : il n'existe AUCUN champ INSEE brut au schéma, le filtre INSEE du rapport producteurs ne répare rien.",
        "millesime_producteur": "train mensuel commun aux 3 jeux (dataUpdatedAt 09/09/2026)",
        "n_objets_producteur": "93 lignes CP brut 974 (dont 16 authentiques corroborées)",
        "granularite": "logement (DPE déclaré)", "granularite_respectee": "oui (jamais généralisé à la parcelle)",
        "part_parcelles": "16 DPE corroborés (16/16 rattachés parcelle, 8 avec ID-RNB) — vide sur les 4 témoins",
        "manque_plein": "rien côté LABUSE — le producteur : les DPE DROM ne remontent pas à l'observatoire ADEME (sentinelle en veille sur le train mensuel)",
    },
    111: {  # Ravines DPF
        "verdict": "PLEINE",
        "verdict_raison": "SOURCES-2 lot 1 : migrée du WFS Carmen 29 (GML→ogr2ogr) au WFS LIZMAP de la DEAL (GeoJSON natif) — mêmes comptes (275 cours + 6 plans d'eau, vérifiés). Cascade marchepied 3,25 m intacte. Licence Lizmap : courrier DEAL (lot 5).",
    },
    113: {  # Espaces protégés complémentaires
        "verdict": "PLEINE",
        "verdict_raison": "SOURCES-2 lot 1 : migrée Carmen → Lizmap, PLUS RICHE — Lizmap sépare RNN Étang (2) et RNMR marine (150 zones réglementées vs 1 agrégat Carmen), et sert la couche ENS du DÉPARTEMENT (178 : gestionnaire, propriété, dateMAJ — la « ms:ENS » du rapport producteurs, jamais servie avant).",
    },
    114: {  # AZI / TRI
        "verdict": "PLEINE",
        "verdict_raison": "GASPAR par commune (fait documentaire) + SOURCES-2 lot 4 : les SCÉNARIOS de la Directive Inondation servis — 128 zones d'iso-hauteurs des 6 TRI (43 fréquent / 42 moyen / 43 extrême, codes producteur mesurés, hauteurs d'eau min/max, flag changement climatique), kind tri_zone en carte.",
    },
    145: {  # Systèmes d'endiguement (NOUVELLE)
        "verdict": "PLEINE",
        "emprise": "les systèmes d'endiguement du 974 (69 tronçons, 48 zones protégées)",
        "granularite": "ouvrage / zone protégée", "granularite_respectee": "oui",
        "champs_publies": "classe d'ouvrage A/B/C, niveau de protection (période de retour), niveaux/débits NGR danger-protection-sûreté, population protégée, gestionnaire, arrêté, source d'étude (EDD Hydrétudes déc. 2024)",
        "champs_ingeres": "tous les champs utiles (attrs complets)",
        "millesime_producteur": "EDD Hydrétudes décembre 2024 (porté par chaque zone)",
        "verdict_raison": "NOUVELLE (SOURCES-2 lot 3) : le risque inondation RÉSIDUEL derrière les digues — couche carte complète (aplat zones + trait digues, popup classe/niveau/population), statut « inondation résiduelle au-delà du niveau de protection » TOUJOURS porté. Licence Lizmap : courrier DEAL (lot 5).",
    },
    146: {  # Carte hypsométrique (CHANTIER)
        "verdict": "À DEMANDER / À BRANCHER",
        "verdict_raison": "SOURCES-2 lot 3 : la carte EXISTE (projet Lizmap 04tsunami) mais le producteur ne la sert qu'en WMS IMAGE — la couche des courbes de niveau est REFUSÉE en WFS (vérifié 13/09/2026). Vecteur demandé à la DEAL (courrier lot 5). La donnée de submersion est servie À LA PLACE par l'aléa PPRL vecteur (georisque_alea/submersion_marine + cc, 100 zones).",
    },
    147: {  # BAN PLUS (NOUVELLE)
        "verdict": "PLEINE",
        "emprise": "île entière", "communes_couvertes": "24/24",
        "part_parcelles": "745 874 liens adresse ↔ bâtiment ↔ parcelle ; 629 825 avec ID-RNB (84,4 %)",
        "granularite": "lien adresse ↔ bâtiment", "granularite_respectee": "oui",
        "champs_publies": "id_adr (BAN), id_bat (BD TOPO cleabs), idu, type_lien, nb_adr, nb_bat",
        "champs_ingeres": "tous + rnb_id résolu localement (rnb_batiments.ext_bdtopo)",
        "millesime_producteur": "BAN PLUS (data.gouv IGN, maj 27/08/2026), moisson 13/09/2026",
        "cadence_officielle": "continue (BAN quotidienne, BAN PLUS recalculée par l'IGN)",
        "verdict_raison": "NOUVELLE (SOURCES-2 lot 3) : l'ID-RNB devient la clé de jointure DPE ↔ RPLS ↔ BAN (mandat). Donnée ban_plus_adresses_bati servie au bloc « Le bien » (/parcels/{idu}), filtre (0 hors 974, part RNB), sonde data.gouv last_update.",
    },

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
    15: {  # data.regionreunion — Potentiel foncier : FAIT FOI (SOURCES-3 lot 0.5)
        "verdict": "PLEINE",
        "granularite": "îlot/zone (PAS parcelle)",
        "granularite_respectee": "oui — couche d'orientation, jamais servie comme une vérité parcellaire",
        "verdict_raison": "SOURCES-3 lot 0.5 (arbitrage Vic) : le producteur UNIQUE du potentiel foncier Région. Un seul chiffre servi, un seul producteur : id 9 (« Potentiel foncier Région (ODS) », famille urbanisme) devient son ALIAS. 4 906 objets en couche potentiel_foncier+sar.",
        "potentiel": "couche d'orientation ; peu de valeur ajoutée vs le potentiel calculé maison",
        "principes_ko": [P_PROV + " (licence à confirmer)"],
    },
    9: {  # Potentiel foncier Région (ODS) — ALIAS de 15 (SOURCES-3 lot 0.5)
        "verdict": "ALIAS (doublon)",
        "verdict_raison": "SOURCES-3 lot 0.5 (arbitrage Vic) : même jeu Région ODS « potentiel foncier » que id 15, qui fait foi. Devient son ALIAS (alias_de=15). Un seul chiffre servi, un seul producteur.",
        "potentiel": "aucun propre — redondant avec 15 (fait foi)",
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
        "verdict_raison": "SOURCES-2 lot 2 (balayage des 24 partitions, 13/09/2026) : publient au GPU — Saint-Denis 41, Saint-Paul 158 (délégations nommées), Sainte-Marie 1, Le Tampon 2 = 202 périmètres. « Jamais pas de DPU » est GRAVÉ dans la fiche : Saint-Pierre/Saint-Benoît = DPU institué, délégataire EPF documenté (hors GPU) ; Saint-Philippe = RNU ; les 17 autres = phrase EPF >80 % (Cour des comptes). TYPEINF 03 vérifié ≠ DPU (préemption ENS de L'Étang-Salé).",
        "champs_non_pris": "les DPU des 20 communes non publiées — à demander aux communes/EPCI.",
        "potentiel": "couverture 24/24 sur demande",
        "manque_plein": "récupérer les 20 DPU manquants (délibérations communales)",
    },
    108: {  # PEB
        "verdict": "PLEINE",
        "emprise": "les deux aérodromes du 974 (Roland-Garros + Pierrefonds)",
        "granularite": "zone A/B/C/D bruit aéroport", "granularite_respectee": "oui",
        "verdict_raison": "SOURCES-2 lot 2 : les DEUX PEB servis — Roland-Garros (annexes GPU) ET Pierrefonds (4 zones A/B/C/D en VECTEUR, DGAC/STAC via GetFeatureInfo dgac_peb_plan_wmsv Géoplateforme ; arrêté 29/03/2017, maj STAC 12/04/2022 ; zonage complet exigé à l'ingestion sinon échec franc). Le trou du sud est comblé — le géoréférencement du plan PDF était inutile.",
        "champs_non_pris": "aucun — Lden int/ext, dates, lien arrêté conservés en attrs.",
        "potentiel": "à plein (8 zones servies, carte + fiche + cascade)",
        "manque_plein": "rien de structurel",
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
    97: {  # CatNat — RATTACHÉE (SOURCES-3 lot 1)
        "verdict": "PLEINE",
        "emprise": "île entière (426 arrêtés, 24 communes)", "communes_couvertes": "24/24",
        "granularite": "arrêté CatNat par commune", "granularite_respectee": "oui",
        "verdict_raison": "SOURCES-3 lot 1 : RATTACHÉE au registre — le chiffre `catnat_n` (« Arrêtés CatNat », fiche commune / Pièges) déclare `reservoirs=(catnat_gaspar,)`, table `catnat_arretes` : la provenance est tracée (l'arête posée en CIRCUIT-6 lot 0, confirmée ici). SOURCES-2 lot 1 : recoupement de l'export CSV national GASPAR à chaque ingestion (CSV 426 = base 426, écart 0 — garde « l'API a perdu des arrêtés » en place).",
        "champs_non_pris": "l'objet précis de chaque arrêté (inondation/mvt/sécheresse) est en base mais pourrait mieux ressortir en fiche.",
        "potentiel": "chronologie CatNat par commune (fréquence d'arrêtés = signal de risque)",
    },
    98: {  # Taxe d'aménagement — RATTACHÉE (SOURCES-3 lot 1)
        "verdict": "PLEINE",
        "emprise": "24/24 communes en vigueur (08/09/2026)", "communes_couvertes": "24/24",
        "granularite": "taux communal", "granularite_respectee": "oui",
        "verdict_raison": "SOURCES-3 lot 1 : RATTACHÉE au registre — les chiffres `taxe_amenagement_eur` et `taxe_amenagement_estimee_eur` (outil Taxe + Financier) déclarent `reservoirs=(taxe_amenagement,)`, table `taxe_amenagement_taux` : le taux communal servi porte sa provenance (arête CIRCUIT-6 lot 0, confirmée ici).",
        "champs_non_pris": "part départementale/RAP éventuelle — non vérifié (lot 5).",
        "potentiel": "historique des délibérations de taux",
    },
    115: {  # SIS
        "verdict": "PARTIELLE — couverture incomplète",
        "emprise": "4 SIS sur l'île (secteurs d'information sur les sols)",
        "granularite": "secteur d'info sol (polygone)", "granularite_respectee": "oui",
        "verdict_raison": "Définitifs : Ouest seul arrêté (réalité producteur, canal SSP). SOURCES-2 lot 2 : + les 7 PROJETS Nord-Est/Sud du dossier préfecture (arrêtés 19/02/2026, consultation close 07/05/2026) servis sol_pollue/sis_projet « non opposable » (6 points posés, 1 CRS de PDF non identifié — dit) ; sentinelle octets sur le ZIP préfecture.",
    },
    116: {  # CASIAS
        "verdict": "PLEINE",
        "emprise": "453 sites (435 points, 18 emprises)",
        "verdict_raison": "453 anciens sites industriels servis (couche sol_pollue). Couverture conforme au producteur.",
    },
    112: {  # Zones humides
        "verdict": "PARTIELLE — couverture incomplète",
        "verdict_raison": "Inventaires DEAL 2003/2009/2011/2019 par secteurs — partiels par construction (le producteur n'a pas inventorié toute l'île). 3 122 objets. SOURCES-2 lot 1 : migrées du WFS Carmen au WFS LIZMAP de la DEAL (GeoJSON natif, mêmes comptes vérifiés).",
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
    28: {"verdict": "PLEINE", "verdict_raison": "Trait de côte / érosion côtière 2018 (24 168 objets). Couche carte. Millésime ancien (2018) à re-sonder. SOURCES-2 lot 6 : le fichier Réunion dédié existe bien chez le producteur (HTTP 200, Last-Modified 27/06/2018) — la couverture 974 est CONFIRMÉE, seul l'âge (8 ans) reste le point de vigilance (sentinelle octets en veille)."},
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
    119: {  # DVF Région — ALIAS de DVF Etalab (SOURCES-3 lot 0.4)
        "verdict": "ALIAS (doublon)",
        "verdict_raison": "SOURCES-3 lot 0.4 (arbitrage Vic) : DVF / valeurs foncières (Etalab, id 5) fait foi. DVF Réunion (Région) devient son ALIAS (alias_de=5). Le témoin de filtre qui lisait le jeu Région (figé 2014→mi-2021) pointe désormais sur Etalab. `region_dvf` = réservoir sans table.",
        "potentiel": "aucun propre — Etalab fait foi",
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
    130: {"verdict": "PARTIELLE — champs manquants", "verdict_raison": "Carte des loyers DHUP 2025, extrait 974 embarqué (offline, dépôt manuel). Repli de l'OLL. Fraîcheur à surveiller. SOURCES-2 lot 6 : couverture 974 CONFIRMÉE chez le producteur — le CSV national 2025 (publié 11/12/2025) porte les 24 communes (loypredm2 vérifié ligne à ligne)."},
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
    68: {  # Office de l'eau — RETIRÉE (SOURCES-3 lot 0.2)
        "verdict": "RETIRÉE",
        "emprise": "était 6 communes 100 % ANC (sur 24)", "communes_couvertes": "0/24 (retirée)",
        "granularite": "commune", "granularite_respectee": "oui",
        "verdict_raison": "SOURCES-3 lot 0.2 (arbitrage Vic) : RETIRÉE le 2026-09-13. `anc_service.py` a été rebranché sur l'INSEE RP2022 EGOUL (variable mode d'assainissement, taux non-raccordé, anc_maille_taux) : la branche source_commune (Office de l'eau) est supprimée. Prouvé sur les 12 témoins — l'assainissement non collectif s'affiche identique ou mieux (Salazie : « intégralement ANC » → « 100 % non raccordés (INSEE RP2022, IRIS) », sourcé et daté ; les 11 autres inchangés). La table anc_office_eau_commune est conservée (données non effacées), plus aucun lecteur.",
        "champs_non_pris": "les chroniques quantitatives (qualité/volume d'eau) — non exploitées, hors périmètre foncier.",
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
    45: {  # DINUM — RETRAIT DIFFÉRÉ (sort avec q_v15) — SOURCES-3 lot 0.1
        "verdict": "PLEINE",
        "emprise": "cache d'enrichissement (9 730 enrich., 2 650 dénominations) — Score V seul",
        "verdict_raison": "SOURCES-3 lot 0.1 (arbitrage Vic) : RETRAIT DIFFÉRÉ — reste servie jusqu'au prochain entraînement du modèle (sort avec q_v15). DINUM n'alimente PLUS que le Score V (owner_enrichment/owner_denom_lookup, `score_v.py:90,98`). Débranchée de l'affichage, de la facette et du scan : SIRENE fait foi pour tout affichage — l'APE des filtres/facette propriétaire vient de `sirene_etablissements.naf` (format pointé), l'état « cessée » est retiré (SIRENE n'ingère que les actifs, l'état administratif d'une unité légale n'y est pas lisible ; radiée/procédure BODACC restent). Verdict PLEINE, plus PARTIELLE.",
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
    74: {"verdict": "PLEINE", "verdict_raison": "GTFS 7 réseaux (PAN, maj 2026). Arrêts/lignes de transport en couche. SOURCES-2 lot 1 : les 7 réseaux VÉRIFIÉS un par un au PAN (13/09/2026), tous valides ≥ 31/12/2026 ; GTFS-RT disponible sur 3 réseaux (Car Jaune, Alternéo, Carsud) — documenté NON ingéré (donnée d'exploitation éphémère, arbitrage)."},
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
        "verdict_raison": "Couverture PRODUCTEUR complète (2 665 dalles 974, mission unique 23LHDREUNION — survol 11/08–11/10/2023, édition MNx 13/03/2025, levés SOURCES-2 lot 1, affichés au registre). Le reste-à-faire est LOCAL : la hauteur mesurée couvre ~70 % des parcelles (batch achevé ; solde = parcelles sans bâti rattachable).",
        "champs_non_pris": "le verdict de toiture (pente/forme) n'est calculé que sur 27 parcelles alors que la hauteur couvre 70 % : le calcul toiture est le vrai retard, pas la hauteur.",
        "potentiel": "étendre le verdict de toiture à la couverture hauteur (70 %)",
        "manque_plein": "étendre toiture_lidar (pente/forme) à la couverture hauteur (~70 %) — le vrai retard local.",
        "provenance_ok": "SOURCES-3 lot 1 — lidar_hd_mnh rattaché à marge_surelevation_m (surélévation mesurée) ET à hauteur_bati_m (extrusion 3D carte, robinet couche_batiments_3d) : la hauteur LiDAR servie à la carte est enfin créditée au LiDAR (fuite « 303k à la carte » close). Provenance tracée dans les deux sens (G6).",
    },
    6: {"verdict": "PLEINE", "verdict_raison": "RGE ALTI — pente 5 m (147 398 objets). Socle topographique (pente, viabilisation)."},
    65: {"verdict": "ALIAS (doublon)", "verdict_raison": "RGE ALTI 5 m = même réservoir que id 6 (alias_de=6). Alias correct."},
    61: {"verdict": "PLEINE", "verdict_raison": "BD ORTHO 20 cm 2025. Détection piscines (90,7 %), fond ortho. À plein usage."},
    69: {  # BD ORTHO IRC — CONSERVÉE (SOURCES-3 lot 0.3)
        "verdict": "PLEINE",
        "emprise": "île entière (dérivé végétation)",
        "part_parcelles": "parcel_vegetation : 431 663 (île entière)",
        "granularite": "parcelle (ombrage/canopée NDVI)", "granularite_respectee": "oui",
        "verdict_raison": "SOURCES-3 lot 0.3 (arbitrage Vic) : CONSERVÉE — la décision de retrait est ANNULÉE. L'infrarouge IRC alimente l'ombrage végétal du solaire et du scoring : `parcel_vegetation` (431 663 lignes) est lu par le solaire (`solaire.py:311` ombrage), le Flash (`flash/data.py:650`) et le scoring P (`p_model/sql.py:287`). Chiffre `prod_spec_kwh_kwc`, fiche Solaire. Verdict PLEINE, note de couverture retirée.",
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
    # (l'entrée 37 vit en tête de fichier — bloc SOURCES-2 : le « trou d'ingestion » supposé
    #  s'est révélé un TROU PRODUCTEUR, ingestion réparée et corroborée, 16 lignes réelles)

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
