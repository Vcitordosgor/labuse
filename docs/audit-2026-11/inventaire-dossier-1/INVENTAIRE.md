# INVENTAIRE-DOSSIER-1 — tout ce que LABUSE sait de **97411000BZ1065**, face au Dossier

**Parcelle** : 97411000BZ1065 — 3 Chemin de la Citerne, 97417 Saint-Denis — zone **Uh** (famille U), 1 567 m², 2 bâtiments.
**Mandat** : Opus, lecture seule, branche `audit/inventaire-dossier-1`, worktree `~/Desktop/labuse-inv`. Aucune correction, aucun accès prod.
**Méthode** : fiche réelle lue dans `fiche_cache` (base locale `labuse`, payload calculé le 09/11/2026, clé de fraîcheur `6b6007c7…`) ; Dossier **réellement rendu** par `exports.builder.construire(...)` + `render_pdf` → `DP-20261109-1065`, **10 pages**. Valeurs ci-dessous = valeurs servies, non recalculées.

**Carte des pages du Dossier** (pour la colonne « page ») :

| Page | Contenu |
|---|---|
| p1 | Page de garde : 5 tuiles (Surface · Zone · Pente · Risques · SDP restante) + sommaire |
| p2 | §1 Identité · début §2 Terrain |
| p3 | fin §2 Terrain · §3 Bâti · début §4 Urbanisme |
| p4 | §4 Urbanisme (règlement chiffré) |
| p5 | fin §4 (destinations) · début §5 Risques |
| p6 | fin §5 Risques · §6 Réseaux et desserte |
| p7 | §7 Fiscalité · début §8 Marché |
| p8 | fin §8 Marché · §9 Quartier · début §10 Potentiel |
| p9 | fin §10 Potentiel · §11 Simulation · début §12 Limites et sources |
| p10 | §12 Sources (suite) |

Légende proposition : **GARDER** = la ligne est juste et utile telle quelle · **RETIRER** = bruit, à sortir du Dossier · **AJOUTER** = LABUSE le **détient** mais ne l'imprime pas et devrait.

---

## TABLEAU 1 — un fait par ligne

> Colonne « Dossier (p.) » = page où le fait paraît ; « Absent » = ✓ si LABUSE le détient sans l'imprimer. « Source » = source amont servie dans la fiche.

### A. Identité / cadastre / propriété

| Fait (valeur réelle) | Source | Dossier (p.) | Absent | Proposition — raison (6 mots) |
|---|---|---|---|---|
| Adresse : 3 Chemin de la Citerne, 97417 | Base Adresse Nationale | p2 | — | GARDER — ancre le lecteur au lieu |
| Contenance cadastrale 1 567 m² | Cadastre API Carto PCI | p1, p2 | — | GARDER — chiffre socle du dossier |
| Filiation : issue de 97411000BZ0811, arpentage 05/07/1994 | DFI DGFiP | p2 | — | GARDER — division ancienne, contexte utile |
| Division récente = non | DFI DGFiP | p2 | — | GARDER — écarte le soupçon de redécoupage |
| Dernière mutation DVF sur la parcelle = aucune (2014-2025) | DVF Etalab | p2 | — | GARDER — jamais vendue, fait structurant |
| Permis sur la parcelle = aucun (Sitadel) | Sitadel/SDES | p2 | — | GARDER — honnête sur l'absence |
| Copropriété immatriculée = aucune | Registre copropriétés | p2 | — | GARDER — écarte un statut bloquant |
| Type de propriétaire = non déterminé (owner_type = `pp`) | DGFiP parcelles PM | p2 | — | GARDER — particulier non identifiable, dire pourquoi |
| Propriétaire PM non renseigné (flag) | DGFiP PM | — | ✓ | RETIRER — doublon du « non déterminé » |
| Âge dirigeant inconnu (flag axe A) | INPI RNE | — | ✓ | GARDER absent — signal interne de prospection |
| 2 acquéreurs PM voisins 36 mois : GERER IMMOBILIER REUNION (07/05/2025), LMA (08/10/2024) | DVF × DGFiP PM | — | ✓ | AJOUTER — promoteurs actifs juste à côté |
| Ancienneté de détention = indisponible | DGFiP PM / DVF | p2 | — | GARDER — dit franchement l'inconnu |
| 1 établissement à l'adresse : CLOSING CREST, NAF 7022Z conseil | INSEE SIRENE + BAN | — | ✓ | AJOUTER — occupation économique du bien |

### B. Terrain (sol, pente, couverture)

| Fait (valeur réelle) | Source | Dossier (p.) | Absent | Proposition — raison (6 mots) |
|---|---|---|---|---|
| Pente moyenne 13,8° (25 %) | RGE ALTI IGN | p1, p2 | — | GARDER — contrainte de chantier majeure |
| Pente **maximale** 31,1° | RGE ALTI IGN | — | ✓ | AJOUTER — le point dur du terrain |
| Flag terrassement lourd = vrai | RGE ALTI IGN | — | ✓ | AJOUTER — surcoût de fondation prévisible |
| Surface au sol libre 1 374 m² | BD TOPO IGN | p2 | — | GARDER — assiette réellement disponible |
| Part artificialisée OCS GE 24,9 % | OCS GE IGN | p3 | — | GARDER — artificialisation, utile ZAN |
| Usage du sol dominant = résidentiel (US5) | OCS GE IGN | p3 | — | GARDER — nature d'îlot claire |
| Part imperméabilisée CoSIA 12,2 % | CoSIA IGN | p3 | — | GARDER — chiffre d'emprise fiable |
| Part végétalisée/boisée CoSIA 87,6 % | CoSIA IGN | p3 | — | GARDER — potentiel d'espace libre |
| Part sol nu CoSIA 0,0 % | CoSIA IGN | p3 | — | RETIRER — zéro n'apprend rien ici |
| Piscine détectée = aucune | CoSIA IA | p3 | — | RETIRER — non pertinent pour l'investisseur |
| Bassin versant 100 % (code hydro, ruissellement amont/aval) | spatial_layers DEAL | — | ✓ | AJOUTER — contexte inondation complète le PPR |

### C. Bâti

| Fait (valeur réelle) | Source | Dossier (p.) | Absent | Proposition — raison (6 mots) |
|---|---|---|---|---|
| 2 bâtiments | BD TOPO + CoSIA | p3 | — | GARDER — état bâti de départ |
| Emprise bâtie 193 m² | BD TOPO IGN | p3 | — | GARDER — occupation au sol réelle |
| Hauteur du bâti 10,3 m (faîtage, LiDAR, survol 09/2023) | LiDAR HD IGN | p3 | — | GARDER — mesurée, date tracée |
| Hauteur à l'égout 3,6 m | LiDAR HD IGN | — | ✓ | AJOUTER — sert la marge de surélévation |
| Pente du toit 22,2° | LiDAR HD IGN | p3 | — | GARDER — forme du toit documentée |
| Forme du toit = simple pente (confiance 0,76) | LiDAR HD IGN | p3 | — | GARDER — honnête avec le niveau de confiance |
| 2 identifiants RNB | RNB IGN | p3 | — | RETIRER — référence technique sans valeur client |
| 2 adresses liées au bâti (BAN PLUS) | BAN PLUS IGN | p3 | — | RETIRER — doublon de l'adresse principale |
| État du bien = `bati_encore` / « bâti à vérifier » | dérivé LABUSE | p3 | — | GARDER — invite à la visite |

### D. Urbanisme / règlement

| Fait (valeur réelle) | Source | Dossier (p.) | Absent | Proposition — raison (6 mots) |
|---|---|---|---|---|
| Zone Uh (famille U), constructible, 100 % | API Carto GPU | p1, p3 | — | GARDER — fait qui commande tout |
| PLU opposable approuvé le 05/08/2026 | GPU | p4 | — | GARDER — millésime du document fait foi |
| Hauteur max 7 m faîtage / 4,5 m égout (Art. Uh.10 p.73) | Règlement PLU calibré | p4 | — | GARDER — règle chiffrée référencée |
| Emprise au sol max 30 % (Art. Uh.9 p.73) | Règlement PLU | p4 | — | GARDER — plafond d'emprise clair |
| Recul sur voie 3 m (Art. Uh.6 p.72) | Règlement PLU | p4 | — | GARDER — contrainte d'implantation nette |
| Recul limites séparatives (citation longue Art. Uh.7) | Règlement PLU | p4 | — | RETIRER — mur de texte illisible |
| Pleine terre min = non réglementé | Règlement PLU | p4 | — | GARDER — absence de règle utile à savoir |
| Stationnement 1 place/logement | Règlement PLU | p4 | — | GARDER — dimensionne le projet |
| Destinations autorisées (15) / sous conditions (5) / interdites (3) | Règlement PLU calibré | p5 | — | GARDER — programme possible en un coup d'œil |
| Mixité sociale : quota 15 % dès 30 logements (Art. Uh.2) | Règlement PLU | p4 | — | GARDER — seuil programme à connaître |
| RTAA DOM (conception réglementée logement neuf) | API Carto GPU | p4 | — | GARDER — obligation DOM spécifique |
| SCOT de la CINOR, approuvé 18/12/2013 | GPU WFS | p4 | — | GARDER — cadre supra-communal |
| DPU : parcelle dans le périmètre | GPU info-surf | p4 | — | GARDER — risque de préemption réel |
| Servitude PM1 — PPR (1 SUP, 100 %) | SUP API Carto | p4 | — | GARDER — servitude opposable majeure |
| Hors ER / hors EBC / hors PEB | GPU | p5 | — | GARDER — trois contraintes écartées d'un bloc |

### E. Risques et environnement

| Fait (valeur réelle) | Source | Dossier (p.) | Absent | Proposition — raison (6 mots) |
|---|---|---|---|---|
| 2 points de risque | dérivé LABUSE | p1, p5 | — | GARDER — compteur d'en-tête honnête |
| PPR zone bleue inondation + mouvement de terrain, 100 %, constructible sous prescriptions | DEAL PPR | p5 | — | GARDER — contrainte conditionnante centrale |
| Dates PPR : édition DEAL 16/04/2026 vs approbation commune 17/10/2012 | DEAL PPR | p5, p10 | — | RETIRER — deux dates sèment la confusion |
| 21 arrêtés CatNat commune (dont 5 détaillés : mvt terrain, vents cycloniques) | GASPAR Géorisques | — | ✓ | AJOUTER — historique sinistres parle au banquier |
| SIS / CASIAS / cavités / ICPE / ABF / endiguement / ZNIEFF = tous hors | Géorisques, INPN, Mérimée | p5 | — | GARDER — litanie rassurante mais à condenser |
| Mesure compensatoire GéoMCE = aucune | GéoMCE | p5 | — | RETIRER — donnée nationale rare, sur-détaillée |
| APER (EnR au sol exclues) = hors zone | OFB/INPN | p5 | — | RETIRER — hors sujet pour cette parcelle |

### F. Réseaux et desserte

| Fait (valeur réelle) | Source | Dossier (p.) | Absent | Proposition — raison (6 mots) |
|---|---|---|---|---|
| Fibre FTTH : immeuble raccordable (distance 0 m) | Arcep | p6 | — | GARDER — desserte numérique confirmée |
| 5 opérateurs fibre (FRTE, MIAS, MILK…) | Arcep | — | ✓ | RETIRER — détail opérateur sans enjeu foncier |
| Viabilisation = probable (score 90, « confirmée au voisinage ») | faisceau LABUSE | p6 | — | GARDER — verdict de desserte clair |
| Assainissement = non collectif (épandage + étude sol requise) | GPU zonage | p6 | — | GARDER — contrainte et surcoût majeur |
| Gestionnaires nommés : eau Dionéo (CINOR), assainissement Dionéo/STEP Grand Prado, élec EDF SEI, SPANC CINOR | annuaire LABUSE | — | ✓ | AJOUTER — à qui s'adresser, concret |
| Arrêt le plus proche : Vigie (Citalis) 206 m ; gare Ruisseau Blanc 1 971 m ; N6 996 m | GTFS + BD TOPO | p6 | — | GARDER — desserte transport chiffrée |
| Ligne 22a Citalis à 55 m | OSM/GTFS | — | ✓ | AJOUTER — desserte bus au contact |
| Hors rayon 800 m TCSP | BD TOPO | p6 | — | RETIRER — absence TCSP peu signifiante |
| **Productible solaire ≈ 1 548 kWh/kWc, « très favorable »** | Prospection solaire LABUSE | — | ✓ | AJOUTER — Dossier dit « non calculé » à tort |

### G. Fiscalité et dispositifs

| Fait (valeur réelle) | Source | Dossier (p.) | Absent | Proposition — raison (6 mots) |
|---|---|---|---|---|
| Taxe foncière bâti part communale 36,73 % · TEOM 15,80 % | REI DGFiP | p7 | — | GARDER — pression fiscale locale réelle |
| Taxe foncière non bâti part communale 13,03 % | REI DGFiP | — | ✓ | AJOUTER — pertinent tant que non bâti |
| Taxe d'aménagement — taux communal 3,0 % (depuis 01/01/2022) | barème DGFiP | p7 | — | GARDER — coût du projet à venir |
| Taux départemental taxe aménagement 2,5 % | barème DGFiP | — | ✓ | AJOUTER — complète le taux, calcul total |
| Zonage locatif B1 (DHUP) | arrêté zonage A/B/C | p7 | — | GARDER — commande l'éligibilité des dispositifs |
| TVA DOM 8,5 % / 2,1 % social | CGI 296/278 | p7 | — | GARDER — paramètre de montage financier |
| ZFANG régime standard (abattement ~50 %) | Légifrance | p7 | — | GARDER — avantage fiscal possible |
| FRR (ex-ZRR) commune classée en partie, position non vérifiée | Légifrance | p7 | — | RETIRER — non applicable fiscalement, Réunion |

### H. Marché / DVF / comparables

| Fait (valeur réelle) | Source | Dossier (p.) | Absent | Proposition — raison (6 mots) |
|---|---|---|---|---|
| Prix ancien médian 3 821 €/m² (maison, 29 ventes < 500 m, 2022-2025) | DVF Etalab | p1, p7 | — | GARDER — repère de valeur principal |
| Terrain nu secteur 369 €/m² (15 ventes) | DVF Etalab | p7 | — | GARDER — prix du foncier nu |
| Fourchette prix ancien : min 1 443 / Q1 2 810 / Q3 4 653 / max 5 256 €/m² | DVF Etalab | — | ✓ | AJOUTER — dispersion dit la fiabilité |
| Tendance −13 % (baisse), volatilité 48 % (modérée) | DVF Etalab | — | ✓ | AJOUTER — sens du marché, pas qu'un point |
| 29 points de prix comparables (liste détaillée) | DVF Etalab | — | ✓ | AJOUTER — les comparables sous la médiane |
| Médianes secteur cadastral : maison 3 494 / appart 2 381 €/m² | DVF Etalab | p8 | — | GARDER — comparaison par type |
| Ventes à < 100 m : 1 vente, 0 permis (36 mois) | DVF + Sitadel | p7 | — | GARDER — micro-secteur honnête |
| Valeur terrain estimée du secteur ≈ 578 223 € | DVF dérivé | — | ✓ | AJOUTER — ordre de grandeur d'acquisition |
| 11 permis déposés secteur cadastral (36 mois, dernier 2025) | Sitadel/SDES | — | ✓ | AJOUTER — dynamique de construction locale |
| Signal de marché = « prudence » (liquidité −13 %, 348 logts autorisés/12 mois) | DVF + Sitadel | — | ✓ | AJOUTER — lecture macro du secteur |
| VEFA commune = échantillon insuffisant | DVF | p8 | — | RETIRER — absence non informative |
| Radar — annonces actives = aucune | Radar LABUSE | p8 | — | GARDER — pas d'offre concurrente visible |
| Loyer médian OLL 13,7 €/m² (zone 1) | OLL ADIL/AGORAH | — | ✓ | AJOUTER — base du rendement locatif |

### I. Quartier / contexte social

| Fait (valeur réelle) | Source | Dossier (p.) | Absent | Proposition — raison (6 mots) |
|---|---|---|---|---|
| IRIS 7e Km-La Vigie-Les Brises : 3 113 habitants, 1 258 ménages | INSEE RP2022 | p8 | — | GARDER — poids démographique du quartier |
| 24,2 % de 60 ans et plus ; 24,9 % locataires | INSEE RP2022 | p8 | — | GARDER — profil de la demande |
| Parc : 1 371 logements, 7,7 % vacance | INSEE RP2022 | p8 | — | GARDER — tension/détente du parc |
| Part HLM 5,9 % ; bâti avant 1990 45,9 % | INSEE RP2022 | — | ✓ | RETIRER — détail secondaire, charge la page |
| Équipements proches : école 520 m, santé 290 m, commerce 311 m, bus 206 m | INSEE BPE + OSM | p8 | — | GARDER — qualité de vie concrète |
| Filosofi 200 m : niveau de vie 30 014 €, pauvreté 20 %, 72 % propriétaires | INSEE Filosofi | — | ✓ | AJOUTER — micro-pouvoir d'achat, plus fin qu'IRIS |
| RPLS commune : 25 185 logements sociaux, médiane constr. 1994 | RPLS | — | ✓ | RETIRER — échelle commune trop large |

### J. Potentiel / Gabarit (2D & 3D) / faisabilité

| Fait (valeur réelle) | Source | Dossier (p.) | Absent | Proposition — raison (6 mots) |
|---|---|---|---|---|
| Verdict : potentiel faible, proche de la densité autorisée | moteur densité LABUSE | p1, p8 | — | GARDER — réponse directe à l'investisseur |
| SDP résiduelle (bâti conservé) ≈ 35 m² | moteur densité | p1, p9 | — | GARDER — droits restants, chiffre clé |
| SDP maximale réglementaire, terrain libéré 212 m² | Gabarit réglementaire | p9 | — | GARDER — potentiel après démolition |
| Emprise constructible 470 m² (= 30 % de 1 567) | Gabarit réglementaire | — | ✓ | AJOUTER — surface de contact du gabarit |
| Niveaux max = 1 (plafond de hauteur) | Gabarit réglementaire | — | ✓ | AJOUTER — explique la SDP plafonnée |
| Marge de surélévation au faîtage −3,3 m | Gabarit / LiDAR | p9 | — | GARDER — surélévation impossible, dit crûment |
| Marge à l'égout +0,9 m (règle 4,5 / mesuré 3,6) | Gabarit / LiDAR | — | ✓ | AJOUTER — nuance la surélévation négative |
| Consommé 83 % / résiduel 17 % de la densité | moteur densité | — | ✓ | AJOUTER — taux de saturation parlant |
| SDP existante 177 m² / emprise bâtie calcul 186 m² | moteur densité | — | ✓ | GARDER absent — intermédiaire de calcul technique |
| Surélévation possible = non | Gabarit | p9 | — | GARDER — conclusion nette |
| Capacité en logements = non chiffrée ici | moteur | p9 | — | GARDER — refuse d'inventer un programme |

### K. Score d'opportunité (vente) — tenu hors Dossier

| Fait (valeur réelle) | Source | Dossier (p.) | Absent | Proposition — raison (6 mots) |
|---|---|---|---|---|
| Score de vente : tier « Sans signal », rang 276 094/429 799, percentile 35,8 %, « en dessous de la moyenne » | modèle P-score v2 | — | ✓ | GARDER absent — signal prospection, pas client |
| 3 motifs du score (taille moyenne −, SDP résiduelle +, rotation foncier −) | modèle P-score v2 | — | ✓ | GARDER absent — explicabilité interne LABUSE |
| Complétude des données 92 / ICD confiance haute 90 | agrégat LABUSE | — | ✓ | GARDER absent — métrique interne de qualité |
| 4 opportunités dans la section BZ | secteur LABUSE | — | ✓ | GARDER absent — accroche prospection, hors fiche |

### L. Couches consultées **sans trouvaille** (muettes sur cette parcelle)

> 36 sources interrogées ; ces couches ont répondu « rien ici » et ne sont pas des faits positifs. La plupart ne méritent PAS une ligne dans le Dossier.

| Couche (répond « rien ») | Source | Dossier (p.) | Absent | Proposition — raison (6 mots) |
|---|---|---|---|---|
| Cartofriches (friche) = aucune | Cerema | — | ✓ | GARDER absent — non-fait, inutile à imprimer |
| RPG agricole, forêts ONF, zones humides, parc national | IGN/ASP, ONF, DEAL | — | ✓ | GARDER absent — hors sujet zone urbaine |
| 50 pas géométriques, érosion côtière, littoral | DEAL, Cerema | — | ✓ | GARDER absent — parcelle non littorale |
| BODACC procédures collectives (propriétaire) | DILA | — | ✓ | GARDER absent — pas de PM identifiée |
| Classement sonore ITT, trafic RN (indisponible) | Cerema, Région | — | ✓ | GARDER absent — aucune donnée servie |
| Ravines / domaine public fluvial | DEAL Carmen | — | ✓ | GARDER absent — non recoupé ici |
| Potentiel foncier Région (îlots non urbanisés) | Région ODS | — | ✓ | GARDER absent — estimation régionale non fiable |

---

## TABLEAU 2 — lignes du Dossier qui n'apprennent **rien** au client

> Valeurs toujours nulles/absentes pour cette parcelle, répétitions d'un même chiffre, ou jargon non traduit.

| Ligne du Dossier | p. | Défaut | Proposition |
|---|---|---|---|
| « **Vérifié : rien** » en tête de chaque bloc négatif (§2, §3, §4, §5, §6, §8) | p3-p8 | Répétition (6×) d'un libellé vide avant une liste de « aucun / hors » | Fusionner en un seul bandeau « Rien à signaler sur : … » |
| Litanie des négatifs §5 : SIS, endiguement, CASIAS, APER, GéoMCE, ABF, cavités, ICPE (8 lignes « aucun/hors ») | p5 | 8 lignes pour dire « rien » ; noie le seul fait réel (PPR) | Condenser en une ligne « 8 risques écartés » |
| « **Non disponible ici** : Productible solaire non calculé » | p6 | **Faux** : la fiche détient 1 548 kWh/kWc « très favorable » | Remplacer par la valeur réelle (voir F) |
| « Type de propriétaire : non déterminé » + flag « PM non renseigné » | p2 | Deux formulations du même vide | Garder une seule phrase |
| « Historique de détention : aucun millésime connu » | p2 | Valeur nulle structurelle (particulier) | Retirer quand owner_type = `pp` |
| « Capacité en logements : non chiffrée ici » + « Surface vendable non calculable » | p9 | Deux « non calculable » successifs sous §10 | Garder une mention, pas deux |
| §11 **Simulation** entière : « Renseignez votre opération pour obtenir le bilan » | p9 | Section sans aucun fait — renvoi vers le Bilan | Réduire à une phrase, pas une section |
| « Mixité sociale — quota de logements aidés **15** » | p4 | « 15 » sans unité (c'est 15 **%**) | Écrire « 15 % » |
| « Part sol nu (CoSIA) 0,0 % » | p3 | Zéro non informatif | Masquer les parts à 0,0 % |
| « hors part départementale et taxes spéciales » (taxe foncière) | p7 | Hedging réglementaire, pas un fait | Renvoyer en note de bas de page |
| Recul limites séparatives : citation brute « …4m ≤ L ≥ h/2… » | p4 | Jargon réglementaire non traduit | Résumer : « implantation possible sur limite » |
| Codes nus : RNB `QZ7HEVDG…`, NAF `7022Z`, US5/CS2.1.1.1, « PM1 » | p3-p4 | Références techniques opaques | Garder le libellé, cacher le code |
| PPR : « édition DEAL 16/04/2026 » (§5) vs « approuvé 17/10/2012 » (§12) | p5/p10 | Deux dates contradictoires en apparence | Unifier : « approuvé 2012, édition 2026 » |
| Contenance 1 567 m² (tuile p1) + Surface (tuile) + §2 + §10 ; SDP 35 m² (tuile p1 + §10) | p1-p9 | Mêmes chiffres répétés 3-4× | Tuiles = rappel ; éviter la redite en section |
| « VEFA commune : échantillon insuffisant » | p8 | Absence de donnée présentée comme ligne | Retirer quand n = 0 |
| Double sourçage : pied de source **sous chaque section** + grande section §12 Sources | p2-p10 | Les sources sont listées deux fois | Garder §12 ; alléger les pieds de section |

---

## ORDRE PROPOSÉ DES 11 SECTIONS

**Actuel** : 1 Identité · 2 Terrain · 3 Bâti · 4 Urbanisme · 5 Risques · 6 Réseaux · 7 Fiscalité · 8 Marché · 9 Quartier · 10 Potentiel · 11 Simulation.

L'ordre actuel décrit la parcelle « de la peau vers l'os » (sol → bâti → droit → valeur) et **garde la réponse — le potentiel — en 10ᵉ position**, après le marché et le quartier. Pour un opérateur foncier, la question est « puis-je bâtir, qu'est-ce qui bloque, combien ça vaut ». Je propose de **remonter Urbanisme et Potentiel** (ce qui est permis / ce qu'il reste) juste après l'Identité, puis les contraintes, puis le physique, et de **reléguer Quartier** (contexte) avant la Simulation :

| Rang | Section proposée | Pourquoi là |
|---|---|---|
| 1 | **Identité** | Ancre : où, quoi, à qui, d'où vient |
| 2 | **Urbanisme** | Le droit commande tout le reste |
| 3 | **Potentiel** | La réponse : ce qu'il reste à bâtir |
| 4 | **Risques et environnement** | Ce qui conditionne ou bloque le projet |
| 5 | **Terrain** | Physique : pente, sol libre, terrassement |
| 6 | **Bâti** | Existant à conserver ou démolir |
| 7 | **Réseaux et desserte** | Viabilité et surcoûts de raccordement |
| 8 | **Marché** | Prix et comparables pour chiffrer |
| 9 | **Fiscalité et dispositifs** | Charges et leviers du montage |
| 10 | **Quartier** | Contexte de la demande |
| 11 | **Simulation** | Bilan saisi par l'abonné (clôture logique) |

**Changements clés** : Urbanisme 4→2, Potentiel 10→3, Risques 5→4, Fiscalité 7→9, Marché 8→8, Quartier 9→10. Le lecteur obtient « constructible Uh / il reste ~35 m² / sous prescriptions PPR » dès la deuxième page, avant les détails. Si l'on ne change qu'**une** chose : faire passer **Potentiel juste après Urbanisme** — aujourd'hui la conclusion arrive sept sections trop tard.

---

*Fin de l'inventaire. Lecture seule — aucune donnée de production touchée, aucun fichier applicatif modifié.*
