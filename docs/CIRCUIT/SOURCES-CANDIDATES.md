# SOURCES CANDIDATES — ce que LABUSE n'a pas encore et qui l'améliorerait

*Recherche du 06/09/2026 (Fable). Vérifié par recherche web sur les portails de l'État, de la Région, de la DEAL, de l'IGN, de Géorisques, de l'INPN, de l'Arcep, et par comparaison avec Géofoncier, Kelfoncier et les API SOGEFI. Les lignes « à vérifier » demandent un contrôle de la couverture réelle du 974 avant ingestion — c'est le rôle de la vanne et du filtre.*

Légende « forme » : **C** = couche carte · **F** = fiche parcelle/commune · **K** = cascade (vigilance/rédhibitoire) · **S** = candidat scoring (banc K0) · **O** = outil ou PDF.

---

## 1. Ce qui manque le plus : les contraintes qui bloquent ou renchérissent une opération

| # | Source | Ce que ça apporte | Forme | Producteur · accès | Effort |
|---|---|---|---|---|---|
| 1 | **Servitudes d'utilité publique (SUP) du Géoportail de l'urbanisme** — flux Atom par catégorie et par département | Les servitudes opposables qui ne sont ni dans le PLU ni dans le PPR : **AS1 périmètres de protection des captages d'eau**, **AC2 sites classés et inscrits**, AC4 sites patrimoniaux remarquables, **T5/T7 dégagement aéronautique** (Roland-Garros, Pierrefonds), PT1/PT2 radioélectriques, EL3 marchepied, A4/A5 canalisations, PM2 autour des ICPE. AC1 (monuments) et I4 (lignes) sont déjà partiellement couverts. | C F K O | État (GPU), licence ouverte, standard CNIG. **À vérifier : quelles catégories sont publiées pour le 974** (la publication se fait DDT par DDT). | M — une chaîne unique, une couche par catégorie |
| 2 | **Ravines : domaine public fluvial (1 800 km) et domaine privé de l'État (1 700 km)** | Le recul le plus réunionnais qui soit : servitude de marchepied 3,25 m, interdiction de défricher et d'exploiter sur 10 m de part et d'autre des ravines à pente > 27° (code forestier R.174-2), lit mineur inconstructible. Aujourd'hui aucune couche ne le dit. | C F K | DEAL Réunion : carte des cours d'eau DPF + tableur des affluents ; géométrie à croiser avec l'hydrographie BD TOPO. Ouvert. | M — le croisement hydrographie × liste DEAL demande soin |
| 3 | **SAR — Schéma d'aménagement régional** (zonages numérisés) | Espaces naturels remarquables du littoral, **coupures d'urbanisation**, espaces de continuité écologique, zones préférentielles d'urbanisation, espaces agricoles à protéger, zones à prescription. Le SAR s'impose aux PLU ; un terrain en coupure d'urbanisation ne s'ouvrira jamais. SAR 2050 en révision → sentinelle. | C F K S | DEAL (Carmen, numérisation au 1 : 25 000, non opposable) + Région (SAR en vigueur, PDF). **À demander à la Région : la couche SIG officielle.** | S — shapefiles existants |
| 4 | **Espaces naturels protégés (INPN, standard ENP)** | Cœur du Parc national (105 400 ha) et aire d'adhésion, réserves naturelles (Étang Saint-Paul, réserve marine), arrêtés de protection de biotope, terrains du Conservatoire du littoral, **espaces naturels sensibles du Département**, forêts de protection, site Ramsar. Une seule source, dix couches. | C F K | INPN / OFB, licence ouverte, jeu national filtré sur le 974. | S |
| 5 | **Secteurs d'information sur les sols (SIS)** + **CASIAS** (anciens sites industriels, ex-BASIAS) | Le SIS est une **obligation d'information de l'acheteur** à la parcelle (L125-7) : un terrain en SIS impose une étude de sols avant changement d'usage. CASIAS dit l'historique industriel. LABUSE a déjà SSP et ICPE ; il manque ces deux-là. | F K O | Géorisques, CSV quotidien (SIS) et export par région (CASIAS). Ouvert. | S |
| 6 | **Zonage d'assainissement** (collectif / non collectif) des communes et EPCI | Décisif pour la constructibilité : hors zone collective, l'ANC est obligatoire et impose une surface minimale et un sol filtrant. Aujourd'hui LABUSE ne sert que le taux de raccordement à l'égout. | C F K | Communes et EPCI (CINOR, TCO, CIVIS, CASUD, CIREST), souvent sur PEIGEO. **À demander à la Région / aux EPCI.** | M — 24 sources hétérogènes |
| 7 | **Zones humides** (inventaires DEAL) | Loi sur l'eau : compensation obligatoire, souvent rédhibitoire. Trois inventaires majeurs existent, flux WFS. | C K | DEAL Réunion, Carmen, WFS. Ouvert. | S |
| 8 | **Classement sonore des infrastructures de transport** | Secteurs affectés par le bruit (10 à 300 m des routes classées) : isolation acoustique obligatoire, coût de construction. Complète le PEB (SOURCES-1). | C F | DEAL, arrêtés préfectoraux + géométrie. **À vérifier** (souvent PDF seulement). | S à M |
| 9 | **Zones de présomption de prescription archéologique (ZPPA)** | Diagnostic archéologique obligatoire au-dessus de seuils de surface : délais et coûts. | C F K | Ministère de la Culture, Atlas des patrimoines, WFS. Ouvert. **À vérifier pour le 974.** | S |
| 10 | **Atlas des zones inondables / TRI** (Géorisques) | Là où le PPR n'existe pas encore ou est ancien, l'AZI donne l'emprise des crues connues. | C K | Géorisques, ouvert. | S |

## 2. Ce qui change la valeur d'un bien ou d'une opération

| # | Source | Ce que ça apporte | Forme | Producteur · accès | Effort |
|---|---|---|---|---|---|
| 11 | **Action Cœur de Ville, Petites villes de demain, périmètres d'ORT** | Éligibilité **Denormandie** (rénovation de l'ancien avec avantage fiscal, prorogé jusqu'à fin 2027), priorité aux financements. Les périmètres ORT sont dans les conventions préfectorales. | F O S | ANCT (liste des communes, data.gouv) + préfecture de La Réunion (périmètres). | S (communes) à M (périmètres) |
| 12 | **OPAH / PIG** (périmètres d'amélioration de l'habitat) | Aides Anah à la rénovation : signal fort pour Densifier l'existant et pour le propriétaire occupant. | F S | Anah / EPCI. **À demander aux EPCI.** | M |
| 13 | **Inventaire des zones d'activité économique (ZAE)** | Obligatoire pour chaque EPCI depuis la loi Climat et résilience : vacance, occupation, gestionnaire. Le foncier économique n'est pas couvert par LABUSE aujourd'hui. | C F O | EPCI, publication obligatoire. Ouvert. | S |
| 14 | **Périmètres de ZAC et lotissements** (permis d'aménager Sitadel PA) | Là où le foncier est déjà aménagé ou en cours : lots à bâtir à venir, concurrence, prix de sortie. | C F S | Sitadel (PA) déjà en base côté permis ; ZAC : EPCI / Région / PEIGEO. | M |
| 15 | **Fibre à l'adresse — Arcep « Ma connexion internet »** | Raccordable ou non, opérateur par opérateur, à l'immeuble. Argument de vente pour un lot, critère pour un bureau. | F O | Arcep, data.gouv, licence ouverte, trimestriel, maille immeuble. | S |
| 16 | **Taux de taxe foncière votés (fichier REI, DGFiP)** | Charge fiscale du bien par commune, entrée du bilan promoteur et du Financier. Même fichier que les taux de taxe d'aménagement (chantier CIRCUIT-3). | F O | DGFiP, data.gouv, annuel. Ouvert. | S |
| 17 | **Demande de logement social (SNE) par commune** | Tension réelle du logement social : le promoteur LLS y lit sa demande. | F S | DHUP / SNE, open data commune. | S |
| 18 | **Observatoire local des loyers (ADIL Réunion)** | Loyers observés par secteur, plus fins que la carte DHUP. | F O | ADIL, publications ; **à vérifier** si données ouvertes. | S à M |

## 3. Propriété et généalogie du foncier

| # | Source | Ce que ça apporte | Forme | Producteur · accès | Effort |
|---|---|---|---|---|---|
| 19 | **Documents de filiation informatisés (DFI)** | La généalogie officielle des parcelles (mère → filles). C'est la réponse propre aux **permis orphelins** (10 799 rattachés à des parcelles disparues) : plus besoin d'intersecter des cadastres d'époque. Aussi : détecter les divisions récentes (signal de vente). | F S | DGFiP, open data. **À vérifier : disponibilité pour le 974.** | M — jointure avec la table des permis |
| 20 | **Fichiers fonciers complets, LOVAC, DV3F** | Propriétaires personnes physiques, vacance des logements, DVF enrichi. | F S | Cerema, **convention** (une seule demande pour les trois). | Démarche administrative, puis M |

## 4. Ce qui se demande à la Région, en une seule liste

- La couche SIG officielle du **SAR** en vigueur, et le calendrier du SAR 2050.
- Les **SIG communaux** rassemblés sur PEIGEO : emplacements réservés, EBC, DPU (SOURCES-1), **zonages d'assainissement**, périmètres de ZAC, OPAH.
- Le **cadastre solaire régional** (existe, jamais servi).
- Les données **TCSP** de PEIGEO / AGORAH (tracés en projet, Réunion Express).
- Les observatoires de l'**AGORAH** : foncier, habitat, ZAE — accès aux données brutes, pas aux PDF.
- Le **LiDAR régional** s'il diffère de celui de l'IGN.

## 5. Ce qui a été regardé et écarté

- Natura 2000 : ne s'applique pas à La Réunion.
- Zonage sismique : zone 2 uniforme sur l'île, une constante, pas une source.
- Retrait-gonflement des argiles, radon : peu discriminants à La Réunion, à revoir seulement si un client le demande.
- Réseaux d'eau potable et d'assainissement (canalisations) : gestionnaires privés ou régies, pas d'open data — convention au cas par cas, faible priorité.
- Meublés de tourisme déclarés : dispersés commune par commune, peu fiables.
- Foncier de l'État (cessions) et portefeuille de l'EPF Réunion : rapports, pas de données parcellaires ouvertes.

## 6. Ordre proposé

1. Un mandat **SOURCES-2 « Contraintes »** : SUP du GPU, ravines DPF/DPE, SAR, espaces protégés INPN, SIS + CASIAS, zones humides, AZI — sept sources ouvertes, toutes géographiques, toutes cascade. C'est le plus gros gain pour la justesse des verdicts.
2. Un mandat **SOURCES-3 « Valeur »** : ACV/PVD/ORT, fibre Arcep, taux REI, SNE, ZAE, DFI.
3. La demande à la Région (section 4) en parallèle, et la convention Cerema.
4. Assainissement, OPAH, ZAC, bruit, ZPPA au fil de ce que la Région et les EPCI fournissent.
