# -*- coding: utf-8 -*-
# VERIF[(commune, zone)] = (vocation_reglement, habitat_autorise, source)
# Rempli EXCLUSIVEMENT depuis les règlements écrits téléchargés (reports/m6-audit/reglements/)
# par les agents de vérification (résultats du 13/07/2026). AUCUNE valeur inventée.
VERIF = {
    # ── Saint-Denis (97411_reglement_20260423.pdf — contenu MS8 fév. 2024) ──
    ("Saint-Denis", "Ui"): (
        "Zone urbaine RÉSIDENTIELLE de densité intermédiaire (plaine littorale/piémont) — « L'habitation domine » ; PAS une zone industrielle (industrie interdite Art. Ui.1)",
        "oui (collectif >=30 lgts : min 15 % logements sociaux/intermédiaires)",
        "97411_reglement_20260423.pdf, caractère + Art. Ui.1/Ui.2 p.51-52, Art. Ui.10 p.56 (18 m)"),
    ("Saint-Denis", "Uicm"): (
        "Secteur de Ui (Canne Mapou) — vocation résidentielle affirmée",
        "oui (mêmes conditions que Ui)",
        "97411_reglement_20260423.pdf, p.51, Art. Ui.10 p.56 (12 m)"),
    ("Saint-Denis", "Uip"): (
        "Secteur de Ui, projet PRUNEL (QPV)",
        "conditionnel (logts neufs interdits en 1er front de certains axes — 2d front obligatoire ; pas de LLS neuf hors programme mixité)",
        "97411_reglement_20260423.pdf, Art. Ui.1 p.52, Art. Ui.10 p.56 (18 m / 12 m rue Marcadet)"),
    ("Saint-Denis", "Uj"): (
        "Zone urbaine « jardin » de centre de bourgs — habitat dominant",
        "oui (collectif >=30 lgts : min 15 % social/intermédiaire)",
        "97411_reglement_20260423.pdf, Art. Uj.1/Uj.2 p.59-60, Art. Uj.10 p.62 (13 m)"),
    ("Saint-Denis", "Um"): (
        "Zone urbaine de moyenne densité des pentes — habitat dominant",
        "oui (collectif >=30 lgts : min 15 % social/intermédiaire)",
        "97411_reglement_20260423.pdf, Art. Um.1/Um.2 p.65-66, Art. Um.10 p.68 (10 m)"),
    ("Saint-Denis", "Uh"): (
        "Zone urbaine des Hauts, vocation dominante habitat individuel, constructibilité limitée",
        "oui (conditions ANC ; collectif >=30 lgts : 15 % social)",
        "97411_reglement_20260423.pdf, Art. Uh.1/Uh.2 p.71, Art. Uh.10 p.73 (7 m)"),
    ("Saint-Denis", "AUx"): (
        "Zone À Urbaniser STRICTE (réserves Bellepierre, Domenjod) — ouverture subordonnée à modification/révision du PLU",
        "non (toutes constructions interdites sauf infra/ouvrages techniques et extension <=30 m2 existant)",
        "97411_reglement_20260423.pdf, Art. AUx.1/AUx.2 p.110"),
    ("Saint-Denis", "UEa"): (
        "ANOMALIE DONNÉE : zone inexistante au règlement de Saint-Denis (sommaire p.3-4) — polygone du PLU de Sainte-Marie (idurba 97418_plu_20251126) rattaché à Saint-Denis",
        "conditionnel (règlement Sainte-Marie UEa : gardiennage/fonctionnement uniquement)",
        "97411_reglement_20260423.pdf (absence) + 97418_reglement_20251126.pdf Art. U2 pt 4"),
    ("Saint-Denis", "UEc"): (
        "ANOMALIE DONNÉE : zone inexistante au règlement de Saint-Denis — polygone du PLU de Sainte-Marie (idurba 97418_plu_20251126)",
        "conditionnel (règlement Sainte-Marie UEc : gardiennage uniquement)",
        "97411 (absence) + 97418_reglement_20251126.pdf Art. U2 pt 4"),
    ("Saint-Denis", "UEp"): (
        "ANOMALIE DONNÉE : zone inexistante au règlement de Saint-Denis — polygone du PLU de Sainte-Marie (idurba 97418_plu_20251126)",
        "non (règlement Sainte-Marie UEp : habitat strictement interdit, gardiennage exclu)",
        "97411 (absence) + 97418_reglement_20251126.pdf Art. U2 pt 4 et 8 p.30"),

    # ── Sainte-Marie (97418_reglement_20251126.pdf) ──
    ("Sainte-Marie", "UEa"): (
        "Zone dédiée aux activités aéroportuaires (aéroport Roland Garros)",
        "conditionnel (uniquement logement des personnes indispensables au fonctionnement/gardiennage des activités)",
        "97418_reglement_20251126.pdf, p.29, Art. U2 « activités » pt 4-5 p.30, Art. U8 8.2 p.35 (24 m)"),
    ("Sainte-Marie", "UEc"): (
        "Zones de développement commercial, de services et/ou tertiaire",
        "conditionnel (logement de gardiennage/fonctionnement uniquement)",
        "97418_reglement_20251126.pdf, p.29, Art. U2 pt 4 et 6 p.30 (14 m)"),
    ("Sainte-Marie", "UEm"): (
        "Espaces d'activités mixtes (production, commerciales et services)",
        "conditionnel (logement de gardiennage/fonctionnement uniquement)",
        "97418_reglement_20251126.pdf, p.29, Art. U2 pt 4 et 7 p.30 (16 m)"),
    ("Sainte-Marie", "UEp"): (
        "Espaces d'activités économiques de production/transformation/réparation/conditionnement/distribution",
        "non (interdit strictement — l'exception gardiennage EXCLUT expressément UEp, Art. U2 pt 4)",
        "97418_reglement_20251126.pdf, p.29, Art. U2 pt 4 et 8 p.30 (16 m)"),
    ("Sainte-Marie", "1AUep"): (
        "Zone à urbaniser indicée « ep » — renvoi intégral au règlement UEp ; ouverte dès l'approbation",
        "non (par renvoi UEp : habitat interdit, y compris gardiennage)",
        "97418_reglement_20251126.pdf, chap. V p.41-42 (Art. AUindicée 1.2, 2 pt 1, 8)"),
    ("Sainte-Marie", "UAz"): (
        "Secteur de UA (centre-ville) — dispositions spécifiques quartier Beauséjour, zone résidentielle mixte",
        "oui (>2500 m2 SdP habitation : min 20 % logement social)",
        "97418_reglement_20251126.pdf, p.16, Art. U1/U2/U3 p.16-17, Art. U8 8.2 p.22 (30 m)"),
    ("Sainte-Marie", "UC"): (
        "Quartiers résidentiels (La Convenance, Les Cafés, La Grande-Montée, Bois-Rouge)",
        "oui (secteurs UC1/UC2 loi ELAN : très restreint — amélioration/réhabilitation sans extension du périmètre bâti)",
        "97418_reglement_20251126.pdf, p.16, Art. U1.2/U2 pt 6-7 p.16-17 (13 m)"),
    ("Sainte-Marie", "UD"): (
        "Écarts des hauts — poches d'habitat peu denses, résidentielle",
        "oui (secteur UD1 : restrictions ELAN)",
        "97418_reglement_20251126.pdf, p.16, Art. U1.2/U2 pt 6 p.16-17 (11 m)"),

    # ── Saint-Paul (97415_reglement_20251217.pdf, éd. mars 2026) ──
    ("Saint-Paul", "U1e"): (
        "Zones d'activités économiques… industrielles, artisanales et commerciales",
        "non (« Sont interdits… les constructions… à destination d'habitation » ; seules extensions de l'existant admises Art. 2.2)",
        "97415_reglement_20251217.pdf, Art. 1.2 p.37-38, Art. 10.2 p.44 (14 m)"),
    ("Saint-Paul", "U1ec"): (
        "Secteur de U1e — pôle d'activités Henri Cornu (EcoCité)",
        "non (règles U1e)",
        "97415_reglement_20251217.pdf, Art. 1.2 p.37, Art. 10.2 p.45 (18 m)"),
    ("Saint-Paul", "U1lec"): (
        "Secteur de U1l — extension des espaces de loisirs de la plaine de Cambaie",
        "conditionnel (constructions à usage d'habitation liées aux loisirs ; hébergement hôtelier admis)",
        "97415_reglement_20251217.pdf, Art. 1.2/2.2 p.38, Art. 10.2 p.44 (14 m)"),
    ("Saint-Paul", "U2e"): (
        "Occupation spécialisée (Carrosse, Bruniquel, STEP Ermitage)",
        "non (interdiction habitat Art. 1.2 — rédaction tronquée « à l'exception. » sans exception listée, fragilité rédactionnelle)",
        "97415_reglement_20251217.pdf, Art. 1.2 p.88, Art. 10.2 p.94 (14 m)"),
    ("Saint-Paul", "U3e"): (
        "Espaces à vocation d'activités économiques et artisanales de l'Eperon et de Plateau Caillou",
        "non (habitat interdit Art. 1.2 al. 2)",
        "97415_reglement_20251217.pdf, Art. 1.2 p.145, Art. 10.2 p.151 (14 m ; 19 m ZAC Savane des Tamarins)"),
    ("Saint-Paul", "AU1e"): (
        "Urbanisation future à vocation économique — renvoi intégral au règlement U1e",
        "non (renvoi U1e)",
        "97415_reglement_20251217.pdf, Art. 1-2 p.55-56"),
    ("Saint-Paul", "AU1ec"): (
        "Secteur de AU1e (Henri Cornu) — renvoi U1e/U1ec",
        "non",
        "97415_reglement_20251217.pdf, p.55"),
    ("Saint-Paul", "AU1est"): (
        "AU1e st — urbanisation future STRICTE « destinée à recevoir exclusivement de l'activité économique »",
        "non (économique exclusif + gel AU*st)",
        "97415_reglement_20251217.pdf, p.59"),
    ("Saint-Paul", "AU1lec"): (
        "Urbanisation future — renvoi intégral zone U1lec",
        "conditionnel (habitat lié aux loisirs, renvoi U1lec)",
        "97415_reglement_20251217.pdf, p.57-58"),
    ("Saint-Paul", "AU3e"): (
        "Urbanisation future — renvoi au règlement de la zone U3e",
        "non",
        "97415_reglement_20251217.pdf, Art. 1-2 p.160-161"),
    ("Saint-Paul", "AU5e"): (
        "Espace à vocation d'activités économiques et artisanales du bassin de vie (La Saline) — règlement propre",
        "non (habitat interdit Art. 1.2 al. 2)",
        "97415_reglement_20251217.pdf, Art. 1.2 p.254, Art. 10.2 p.260 (14 m)"),
    ("Saint-Paul", "AUse"): (
        "ANOMALIE DONNÉE : libellé INTROUVABLE au règlement Saint-Paul (0 occurrence) — polygone du PLU des Trois-Bassins (idurba 97423_PLU_20220602)",
        "",
        "97415_reglement_20251217.pdf (absence)"),
    ("Saint-Paul", "Usdu"): (
        "Secteurs Déjà Urbanisés loi littoral (L.121-8) — amélioration de l'offre de logement sans extension du périmètre bâti",
        "conditionnel (habitat admis si pas d'atteinte env./paysage + avis CDNPS, sans extension du périmètre bâti)",
        "97415_reglement_20251217.pdf, Art. 1.2-2.2 p.127-128, Art. 10.2 p.134 (6 m égout / 9 m faîtage)"),
    ("Saint-Paul", "UE"): (
        "ANOMALIE DONNÉE : libellé introuvable au règlement Saint-Paul — polygone du PLU de La Possession (idurba 97408_PLU_20251217)",
        "",
        "97415_reglement_20251217.pdf (absence)"),
    ("Saint-Paul", "UEm"): (
        "ANOMALIE DONNÉE : libellé introuvable au règlement Saint-Paul — polygone du PLU de La Possession (idurba 97408_PLU_20251217)",
        "",
        "97415_reglement_20251217.pdf (absence)"),
    ("Saint-Paul", "AUEm"): (
        "ANOMALIE DONNÉE : libellé introuvable au règlement Saint-Paul — polygone du PLU de La Possession (idurba 97408_PLU_20251217)",
        "",
        "97415_reglement_20251217.pdf (absence)"),
    ("Saint-Paul", "Ue"): (
        "ANOMALIE DONNÉE : libellé introuvable au règlement Saint-Paul — polygone du PLU des Trois-Bassins (idurba 97423_PLU_20220602)",
        "",
        "97415_reglement_20251217.pdf (absence)"),
    ("Saint-Paul", "U2c"): (
        "Zone résidentielle mixte, vocation touristique à conforter, développement résidentiel freiné (Boucan Canot-Saline)",
        "oui (habitat non interdit ; obligations de mixité sociale Art. 2.2)",
        "97415_reglement_20251217.pdf, caractère p.65, Art. 1.2 p.66, Art. 10.2 p.75 (hé 6 m / hf 9 m)"),
    ("Saint-Paul", "U6c"): (
        "Zone résidentielle mixte, tissu rural aéré (Tan Rouge, Bellemène, Bac Rouge)",
        "oui (interdits limités : entrepôt exclusif, agricole, camping)",
        "97415_reglement_20251217.pdf, caractère p.273, Art. 1.2 p.273, Art. 10.2 p.278 (hé 6 m / hf 9 m)"),

    # ── Le Port (97407_reglement_20241209.pdf) ──
    ("Le Port", "Ue"): (
        "Activités industrielles, artisanales et services liés (production, transformation, conditionnement, distribution)",
        "conditionnel (logement admis si utile au fonctionnement/surveillance, max 1 logement par unité foncière, non isolé ; hébergement interdit)",
        "97407_reglement_20241209.pdf, Art. Ue 1 p.79, Art. Ue 2 p.80, Art. Ue 8 p.84"),
    ("Le Port", "Uem"): (
        "Secteur de Ue, « zone tampon » en continuité de quartier résidentiel — industries interdites (maintien dans emprises existantes)",
        "conditionnel (mêmes conditions que Ue)",
        "97407_reglement_20241209.pdf, caractère p.79, Art. Ue 2 p.81, Art. Ue 8 p.84 (18 m)"),
    ("Le Port", "Umi"): (
        "Espaces destinés à accueillir des activités militaires",
        "conditionnel (Art. Umi 2 n'admet que les constructions destinées à la vocation militaire)",
        "97407_reglement_20241209.pdf, Art. Umi 1 p.91, Art. Umi 2 p.92, Art. Umi 8 p.94 (16 m)"),
    ("Le Port", "Us"): (
        "Espaces destinés à accueillir principalement des activités commerciales",
        "conditionnel (logement de fonctionnement/surveillance, max 1 par unité foncière ; hébergement interdit)",
        "97407_reglement_20241209.pdf, Art. Us 1 p.119, Art. Us 2 p.120, Art. Us 8 p.122 (18 m)"),
    ("Le Port", "Up"): (
        "Zones portuaires — seules constructions industrielles/artisanales/entrepôts/bureaux liées à l'activité portuaire",
        "conditionnel (logement utile au fonctionnement/surveillance sur l'unité foncière ; hébergement interdit)",
        "97407_reglement_20241209.pdf, Art. Up 1 p.107, Art. Up 2 p.109, Art. Up 8 p.110 (non réglementé)"),
    ("Le Port", "Uppp"): (
        "Secteur de Up « plaisance et pêche » — SECTEUR ANNULÉ par TA Réunion n°1900330 du 28/02/2022, définitif (CAA Bordeaux n°22BX01470 du 19/09/2023) ; texte toujours présent au règlement GPU",
        "non (sans objet — régime Up de droit commun applicable)",
        "97407_reglement_20241209.pdf p.107/109 + 97407_jugement_20241209.pdf Art. 1er"),
    ("Le Port", "Uoap"): (
        "Périmètre de l'OAP « Portes de l'océan » (OAP de secteur R.151-8, s'applique seule)",
        "indéterminé au règlement (renvoi intégral à l'OAP pièce n°4)",
        "97407_reglement_20241209.pdf, Art. Uoap 1-2 p.103, Art. Uoap 8 p.104"),
    ("Le Port", "1AUe"): (
        "Urbanisation future indicée (Haut du Triangle Agricole) — renvoi au règlement de la zone Ue",
        "conditionnel (règles Ue : logement de surveillance, 1 par unité foncière)",
        "97407_reglement_20241209.pdf, Art. 1AUindicée 1-2 p.142-144"),
    ("Le Port", "1AUem"): (
        "Libellé introuvable au règlement (0 occurrence) — par mécanisme d'indice suivrait Uem (inférence, pas une citation)",
        "conditionnel (inférence règles Uem)",
        "97407_reglement_20241209.pdf (absence du libellé)"),
    ("Le Port", "2AUem"): (
        "Espaces réservés à l'urbanisation future à vocation d'activités économiques mixtes — ouverture conditionnée à modification du PLU",
        "non (Art. 2AU 1 : toutes constructions interdites sauf réseaux/ouvrages techniques/extensions limitées)",
        "97407_reglement_20241209.pdf, caractère p.157, Art. 2AU 1-2 p.157-158"),
    ("Le Port", "Ua"): (
        "Quartiers/lotissements d'habitations individuelles — conserver la vocation résidentielle",
        "oui",
        "97407_reglement_20241209.pdf, caractère p.21, Art. Ua 1 p.21, Art. Ua 8 p.25 (9 m)"),
    ("Le Port", "Uc"): (
        "La plus grande partie du tissu urbain — mixité des fonctions et formes urbaines encouragée",
        "oui",
        "97407_reglement_20241209.pdf, caractère p.50, Art. Uc 1 p.50, Art. Uc 8 p.55 (16 m)"),

    # ── Saint-Pierre (97416_reglement_20240625.pdf — Eco-PLU approuvé juin 2024) ──
    # Zones Ua* : « Zone urbaine ou à urbaniser à vocation d'activités » — le tableau des
    # destinations (Art. Ua1) marque « Logement » INTERDIT dans TOUS les secteurs ; seules
    # extensions de l'existant admises « sauf pour les constructions à destination de
    # logement où aucune extension n'est autorisée » (Art. Ua1 p.173).
    ("Saint-Pierre", "Uazp"): (
        "Zone d'activités — ZAC Pierrefonds Aérodrome",
        "non (Logement marqué interdit au tableau Art. Ua1)",
        "97416_reglement_20240625.pdf, caractère p.171, Art. Ua1 p.172-175, Art. Ua3 p.178 (15,5 m égout / 20 m faîtage)"),
    ("Saint-Pierre", "Uazpc"): (
        "Zone d'activités — ZAC Pierrefonds Aérodrome (secteur c)",
        "non (Logement marqué interdit au tableau Art. Ua1)",
        "97416_reglement_20240625.pdf, caractère p.171, Art. Ua1 p.172-175, Art. Ua3 p.178"),
    ("Saint-Pierre", "Uaza"): (
        "Zone d'activités — ZA Cap Austral, Mon Caprice, Trois Cheminées, Mont Vert les Hauts, la Cafrine, ZI n°2 (artisanat autorisé)",
        "non (Logement interdit Art. Ua1 ; extension d'un logement existant : aucune autorisée)",
        "97416_reglement_20240625.pdf, caractère p.171, Art. Ua1 p.172-175 (interdiction p.173), Art. Ua3 p.178 (14 m faîtage)"),
    ("Saint-Pierre", "Uazc"): (
        "Zone d'activités — activités tertiaires, commerciales et industrie (ZAC Canabady…)",
        "non (Logement marqué interdit au tableau Art. Ua1)",
        "97416_reglement_20240625.pdf, caractère p.171, Art. Ua1 p.172-175, Art. Ua3 p.177-178 (13/18 m ; Canabady 7/12 m)"),
    ("Saint-Pierre", "AUazc"): (
        "Zone à urbaniser à vocation d'activités (tertiaire/commerce/industrie) — même régime que Uazc ; OAP, urbanisation après opérations d'aménagement",
        "non (même tableau Art. Ua1)",
        "97416_reglement_20240625.pdf, p.171, Art. Ua1 p.172-175, Art. Ua3 p.177-178"),
    ("Saint-Pierre", "Uazi"): (
        "Zone d'activités — accueil d'activités industrielles et artisanales (+ carrières possibles)",
        "non (Logement marqué interdit au tableau Art. Ua1)",
        "97416_reglement_20240625.pdf, caractère p.171, Art. Ua1 p.172-175, Art. Ua3 p.176-177 (16 m égout / 21 m faîtage)"),
    ("Saint-Pierre", "AUazi"): (
        "Zone à urbaniser à vocation d'activités industrielles/artisanales — même régime que Uazi ; OAP",
        "non (même tableau Art. Ua1)",
        "97416_reglement_20240625.pdf, p.171, Art. Ua1 p.172-175, Art. Ua3 p.176-177"),
    ("Saint-Pierre", "Uemi"): (
        "Secteur de Ue (équipements) dévolu aux activités militaires",
        "conditionnel (logements/hébergements uniquement si présence permanente sur site nécessaire au fonctionnement — logement de fonction)",
        "97416_reglement_20240625.pdf, caractère p.187, Art. Ue1 p.188-189, Art. Ue3 p.193 (16/21 m)"),
    ("Saint-Pierre", "Uep"): (
        "Secteur de Ue — parcs et espaces verts paysagers, activités de loisirs (sportives/culturelles)",
        "non (Logement marqué interdit au tableau Art. Ue1 ; seuls équipements de plein air et constructions légères)",
        "97416_reglement_20240625.pdf, caractère p.187, Art. Ue1 p.189-190, Art. Ue3 p.193"),
    ("Saint-Pierre", "AU01"): (
        "Zone à urbaniser insuffisamment équipée — NON ouverte à l'urbanisation dans l'Eco-PLU",
        "non (toute construction interdite ; seuls réseaux et extensions <=20 % SdP existante)",
        "97416_reglement_20240625.pdf, caractère + Art. AU0 1 p.200"),
    ("Saint-Pierre", "AU02"): (
        "Zone à urbaniser insuffisamment équipée — NON ouverte à l'urbanisation",
        "non (toute construction interdite ; extensions <=20 %)",
        "97416_reglement_20240625.pdf, Art. AU0 1 p.200"),
    ("Saint-Pierre", "AU03"): (
        "Zone à urbaniser insuffisamment équipée — NON ouverte à l'urbanisation",
        "non (toute construction interdite ; extensions <=20 %)",
        "97416_reglement_20240625.pdf, Art. AU0 1 p.200"),
    ("Saint-Pierre", "AU0c-1"): (
        "Zone à urbaniser insuffisamment équipée, secteur carrières (AU0c)",
        "non (toute construction interdite ; carrières sous conditions)",
        "97416_reglement_20240625.pdf, Art. AU0 1 p.200"),

    # ── Sainte-Suzanne (97420_reglement_20250929.pdf — PLU approuvé 29/09/2025) ──
    ("Sainte-Suzanne", "UE"): (
        "Zone économique : production, transformation, réparation, conditionnement, distribution, artisanat + recherche/formation valorisant le pôle économique",
        "non (Art. UE1.2 : interdites les constructions à usage d'habitation sauf exceptions Art. UE2 ; tableau des destinations : Logement interdit)",
        "97420_reglement_20250929.pdf, caractère p.20, Art. UE1.2 + tableau p.20-21, Art. UE8.2 p.24 (12 m faîtage)"),
    ("Sainte-Suzanne", "1AUe"): (
        "Zone à urbaniser indicée « e » — indice NON défini au règlement écrit (seuls indices a/b/c, 30/20/10 lgts/ha) ; mention unique p.30 (« l'ouverture de la zone 2AUe… une fois l'aménagement de l'ensemble des zones 1AUe entrepris ») — vocation économique probable, défaut de définition réglementaire",
        "indéterminé (indice « e » non réglementé au règlement écrit ; par analogie UE : habitat interdit)",
        "97420_reglement_20250929.pdf, Art. 3.2 p.6, chap. AU indicée p.29-31 (mention 1AUe/2AUe p.30)"),
}
