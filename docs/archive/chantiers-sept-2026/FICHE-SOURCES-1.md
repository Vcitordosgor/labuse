# FICHE-SOURCES-1 — quelles sources alimentent la fiche parcelle

**92 sources de la vitrine** (data_sources WHERE_AFFICHEES). Trace réelle, deux chemins croisés : (1) registre `NOM_VERS_SLUG → donnees.py → robinets.py` (catégorie+parent) ; (2) couches `spatial_layers.data_source_id`, kind thématique (`couches_carte`, les 53 qui remontent à la fiche). Priorité FICHE > COMMUNE > OUTIL > AUTRE > AUCUN. **Lecture seule.**

## Les chiffres
- **77** sources sur 92 alimentent la **fiche parcelle** (FICHE).
- **10** alimentent la **fiche commune** seulement (COMMUNE).
- **2** alimentent un **outil** seulement (OUTIL).
- **1** alimentent **autre chose** (carte seule / Radar / copilote / exports / page client).
- **2** n'alimentent **rien de visible** (AUCUN).

## Tableau des 92 sources

| Source | Verdict | Ligne(s) de la fiche | Section | Note |
|---|---|---|---|---|
| 50 pas géométriques — limite haute (DEAL) | FICHE | couche(s) : cinquante_pas | §5 Risques |  |
| ABF / Monuments historiques | FICHE | Vigilances; couche(s) : abf | Ce qui contraint · Risques et protections · §4 Urbanisme | aussi OUTIL: Pièges et risques |
| ACV / PVD / ORT (DGALN — liste des communes) | COMMUNE | ACV / PVD / ORT | ACV / PVD / ORT — Denormandie |  |
| AZI / TRI — inondation (Géorisques GASPAR) | FICHE | couche(s) : tri_zone | §5 Risques |  |
| Annuaire de l'administration (service-public.fr / DILA) | COMMUNE | Mairie & service urbanisme (coordonnées) | Mairie & service urbanisme |  |
| BAN PLUS — lien adresse ↔ bâtiment (IGN) | FICHE | Adresses liées au bâti (BAN PLUS) | Identifiants et références · Le bien |  |
| BD ORTHO 20 cm (IGN) | FICHE | Piscine ~m² | Réseaux et accès · Sur la parcelle | aussi OUTIL: Piscines, Remonter le temps |
| BD ORTHO IRC (IGN) | FICHE | Productible | Solaire · Solaire (rosace, productible) | aussi OUTIL: Prospection solaire, Toits bien exposés |
| BD TOPO IGN | FICHE | Capacité (logements); Emprise bâtie; Hauteur du bâti; Marge de surélévation (au faîtage); couche(s) : axe_structurant, bassin_versant, batiment, cimetiere … | Ce qu'il reste à bâtir · Ce qu'il y a dessus · Ce qui est constructible · Classement · Constructibilité | aussi OUTIL: Faisabilité, Prospection solaire |
| BODACC (procédures collectives) | FICHE | Événements propriétaire (BODACC); couche évaluée (cascade servie) | Propriétaire |  |
| BPE INSEE | FICHE | À proximité (équipements); couche(s) : amenite_bpe | Autour de cette parcelle · §9 Quartier · À proximité |  |
| Base Adresse Nationale | FICHE | Adresse | En-tête (adresse, géométrie) · Identité |  |
| Cadastre (API Carto PCI) | FICHE | Charge foncière; Division (candidate); Géométrie de la parcelle; Terrain nu secteur | Bilan indicatif · Ce qu'il reste à bâtir · Constaté — ventes actées (DVF) · Constructibilité · Division | aussi OUTIL: Assemblage, Faisabilité |
| Cartofriches (Cerema) | FICHE | couche(s) : friche | §4 Urbanisme |  |
| CatNat (arrêtés GASPAR / Géorisques) | COMMUNE | Arrêtés CatNat (détail); Arrêtés CatNat | Risques |  |
| Cerema / GéoLittoral — indicateur d'érosion côtière | FICHE | couche(s) : trait_de_cote | §5 Risques |  |
| Classement sonore ITT (Cerema) | FICHE | couche(s) : bruit_route | §5 Risques |  |
| CoSIA (couverture du sol IA, IGN) | FICHE | Capacité (logements); Bâti détecté CoSIA (hors BD TOPO); Division (candidate); Emprise bâtie; couche(s) : batiment_cosia, piscine_cosia | Ce qu'il reste à bâtir · Ce qu'il y a dessus · Ce qui est constructible · Classement · Constructibilité | aussi OUTIL: Communes, Comparaison communes |
| Communes La Réunion — contours (IGN ADMIN EXPRESS via geo.api.gouv, seed) | AUTRE |  |  | carte |
| Consommation d'espaces NAF (Cerema — portail de l'artificialisation) | COMMUNE | Enveloppe ZAN (reste) | Enveloppe ZAN | aussi OUTIL: Comparaison communes, Comparer des parcelles |
| Contours IRIS (IGN/INSEE) | FICHE | Quartier INSEE (IRIS); couche(s) : iris_insee | Le secteur · Quartier INSEE (Autour) · §9 Quartier | aussi OUTIL: Étude de zone |
| Coût de construction (EPTB SDES + choix LABUSE) | OUTIL |  |  | Coût de construction (bilan) |
| DEAL Réunion — PPR / aléas | FICHE | Aléas de la parcelle; Vigilances; couche(s) : georisque_alea, ppr, ppr_etat | Ce qui contraint · Risques et protections · §5 Risques | aussi OUTIL: Pièges et risques |
| DEAL — cartes de bruit stratégiques (CBS) | FICHE | couche(s) : bruit_carte | §5 Risques |  |
| DFI — documents de filiation informatisés (DGFiP) | FICHE | Historique cadastral (filiation DFI) | Historique cadastral · Historique cadastral (filiation DFI) |  |
| DGFiP — parcelles des personnes morales | FICHE | Historique propriétaire (millésimes PM); Propriétaire (type); couche évaluée (cascade servie) | Propriétaire · Qui détient | aussi OUTIL: Acquisitions récentes, Ce qu'ils construisent |
| DPE ADEME (logements existants) | FICHE | DPE connu (étiquette, année); couche évaluée (cascade servie) | Identifiants et références · Le bien |  |
| DVF / valeurs foncières | FICHE | Charge foncière; Mutations de la parcelle (DVF); Prix du neuf — observé (€/m²); Prix du neuf — VEFA à l'acte (€/m²); couche(s) : vefa_neuf | Affiché — neuf déclaré (VEFA) · Annoncé — en cours (Radar) · Autour de cette parcelle · Bilan indicatif · Classement | aussi OUTIL: Communes, Comparaison communes |
| EDF Réunion — lignes moyenne tension HTA (open data) | FICHE | couche(s) : ligne_mt | §6 Réseaux |  |
| Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen) | FICHE | couche(s) : ens | §5 Risques |  |
| FRR ex-ZRR — zone spéciale d'action rurale (Légifrance) | FICHE | Périmètres et dispositifs (parcelle); couche(s) : frr | Dispositifs et périmètres (QPV, ANRU, ZFANG, FRR) · Dispositifs fiscaux et urbains · §7 Fiscalité |  |
| Fibre Arcep — Ma connexion internet (immeuble) | FICHE | Fibre (raccordable FttH) | Fibre · Fibre (Réseaux et accès) |  |
| Filosofi INSEE (carreaux 200 m) | FICHE | Habitants (zone); Verdict · Classement servi | Autour de cette parcelle · Classement · Le secteur · Score d'opportunité (tier) | aussi OUTIL: Étude de zone, Étudier un bien |
| Forêts publiques (ONF) | FICHE | couche(s) : foret_publique | §4 Urbanisme |  |
| GPU — droit de préemption urbain (info-surf) | FICHE | Dispositifs et périmètres (parcelle); Droit de préemption urbain (DPU); couche(s) : dpu | Dispositifs et périmètres (droit des sols) · Droit des sols (ER · EBC · DPU · PEB) · §4 Urbanisme |  |
| GPU — emplacements réservés (prescriptions CNIG) | FICHE | Dispositifs et périmètres (parcelle); Emplacement réservé (ER); couche évaluée (cascade servie) | Dispositifs et périmètres (droit des sols) · Droit des sols (ER · EBC · DPU · PEB) |  |
| GPU — espaces boisés classés (prescriptions CNIG) | FICHE | Dispositifs et périmètres (parcelle); Espace boisé classé (EBC); couche évaluée (cascade servie) | Dispositifs et périmètres (droit des sols) · Droit des sols (ER · EBC · DPU · PEB) |  |
| GPU — zonages d'assainissement | FICHE | Logements raccordés à l'égout; couche(s) : zonage_assainissement | Réseaux et accès · Viabilisation · §6 Réseaux |  |
| Géorisques | FICHE | Aléas de la parcelle; Vigilances; couche évaluée (cascade servie) | Ce qui contraint · Risques et protections | aussi OUTIL: Pièges et risques |
| Géorisques — CASIAS (anciens sites industriels) | FICHE | Ancien site industriel (CASIAS); Sols (SIS/CASIAS, parcelle); couche évaluée (cascade servie) | Pour information · Sols (SIS / CASIAS) · Sols (SIS · CASIAS) |  |
| Géorisques — ICPE | FICHE | couche(s) : icpe | §5 Risques |  |
| Géorisques — cavités souterraines | FICHE | couche(s) : cavite | §5 Risques |  |
| Géorisques — mouvements de terrain | FICHE | couche(s) : mvt | §5 Risques |  |
| Géorisques — secteurs d'information sur les sols (SIS) | FICHE | Secteur d'information sur les sols (SIS); Sols (SIS/CASIAS, parcelle); couche évaluée (cascade servie) | Ce qui contraint · Sols (SIS / CASIAS) · Sols (SIS · CASIAS) |  |
| Géorisques — sites et sols pollués | FICHE | couche(s) : sol_pollue | §5 Risques |  |
| IGN BD CARTO V5 — occupation du sol | FICHE | couche(s) : ocs_ge | §4 Urbanisme |  |
| INPI RNE (dirigeants) | FICHE | couche évaluée (cascade servie) | carte/cascade | aussi OUTIL: Scan patrimoine |
| INPN / patrinat — espaces protégés | FICHE | couche(s) : ens | §5 Risques |  |
| INSEE RP Logement 2023 | COMMUNE | logés gratuitement; Habitants; Vacance | Population & logement |  |
| INSEE RP2022 — bases IRIS (logement, population) | FICHE | Quartier INSEE (IRIS) | Le secteur · Quartier INSEE (Autour) | aussi OUTIL: Étude de zone |
| INSEE RP2022 — fichier détail Logements (EGOUL) | FICHE | Logements raccordés à l'égout | Réseaux et accès · Viabilisation |  |
| Inventaire SRU (DHUP) | COMMUNE | Déficit SRU (objectif − taux LLS, points); Logements sociaux (inventaire SRU); Taux LLS | Logement social — SRU | aussi OUTIL: Communes, Comparaison communes |
| LiDAR HD — MNH 50 cm (IGN) | FICHE | Hauteur du bâti; Marge de surélévation (au faîtage); Nature du toit; Pente du toit | Ce qu'il y a dessus · Ce qui est constructible · Constructibilité · Couverture du sol · Le bien | aussi OUTIL: Prospection solaire, Toits bien exposés |
| Loyers DHUP — carte des loyers (annonces) | COMMUNE | Loyer médian | Loyers |  |
| Loyers OLL — ADIL Réunion / AGORAH (réseau des observatoires) | COMMUNE | Loyer médian | Loyers |  |
| NPNRU (DEAL Réunion / ANCT) | FICHE | Périmètres et dispositifs (parcelle); couche(s) : anru | Dispositifs et périmètres (QPV, ANRU, ZFANG, FRR) · Dispositifs fiscaux et urbains · §7 Fiscalité |  |
| OCS GE (IGN) — occupation du sol et artificialisation | FICHE | Part artificialisée (OCS GE); Usage du sol dominant (OCS GE); couche(s) : artificialisation | Couverture du sol · Le bien · §4 Urbanisme |  |
| OSM — transport (pôles d'échange & téléphérique) | FICHE | Transport public — au plus proche; Stationnement allégé (TCSP, L151-36); couche(s) : pole_echange, telepherique | Accès · Réseaux et accès · §6 Réseaux |  |
| OpenStreetMap / Overpass | FICHE | À proximité (équipements); couche(s) : amenite, osm_faux_positif | Autour de cette parcelle · §4 Urbanisme · §9 Quartier · À proximité |  |
| PEB — plans d'exposition au bruit (DGAC via annexes GPU) | FICHE | Dispositifs et périmètres (parcelle); Plan d'exposition au bruit (PEB); couche(s) : peb | Dispositifs et périmètres (droit des sols) · Droit des sols (ER · EBC · DPU · PEB) · §4 Urbanisme |  |
| PLH des 5 EPCI (extraction documentaire) | COMMUNE | Objectif logements/an | Programme local — PLH |  |
| PVGIS (Commission européenne) | FICHE | Productible | Solaire · Solaire (rosace, productible) | aussi OUTIL: Prospection solaire, Toits bien exposés |
| Parc National de La Réunion (INPN) | FICHE | couche(s) : parc_national | §5 Risques |  |
| Parkings OSM (loi APER) | FICHE | Viabilisation (faisceau) | Réseaux et accès · Viabilisation |  |
| QPV 2024 (ANCT) | FICHE | Périmètres et dispositifs (parcelle); couche(s) : qpv, tva_primo | Dispositifs et périmètres (QPV, ANRU, ZFANG, FRR) · Dispositifs fiscaux et urbains · §7 Fiscalité |  |
| RGE ALTI (altimétrie) | FICHE | Exposition (versant); Pente; Viabilisation (faisceau); couche(s) : pente | En-tête · En-tête (adresse, géométrie) · Réseaux et accès · Viabilisation · §2 Terrain |  |
| RNB — Référentiel National des Bâtiments | FICHE | Identifiants RNB des bâtiments | Identifiants et références · Le bien |  |
| RNIC — registre national des copropriétés (Anah) | FICHE | Copropriétés (RNIC) | Division · Division (copropriétés/lots) |  |
| RPG — déclarations agricoles (IGN/ASP) | FICHE | couche(s) : safer | §4 Urbanisme |  |
| RPLS — répertoire des logements locatifs sociaux (SDES) | FICHE | Parc social (logements RPLS) | Marché et secteur |  |
| RTAA DOM (textes réglementaires) | FICHE | Rappel RTAA DOM (exigences de conception) | Bilan indicatif · Constructibilité | aussi OUTIL: Faisabilité |
| Radar (pige d'annonces) | FICHE | Annonces Radar de la parcelle | Annoncé — en cours (Radar) · Marché et secteur | aussi OUTIL: Marché, Radar |
| Ravines — domaine public fluvial (DEAL Carmen) | FICHE | couche(s) : dpf | §5 Risques |  |
| Recherche d'entreprises (DINUM) | FICHE | Événements propriétaire (BODACC) | Propriétaire |  |
| SIRENE | AUCUN |  |  | slug sirene_recherche_entreprises — rien de visible |
| SIRENE établissements géolocalisés | FICHE | Événements propriétaire (BODACC) | Propriétaire | aussi OUTIL: Étude de zone |
| SITADEL (autorisations d'urbanisme) | FICHE | Déposés sur le secteur (36 mois); Sur cette parcelle (permis); Permis à 500 m sur 24 mois; Verdict · Classement servi; couche évaluée (cascade servie) | Autour de cette parcelle · Classement · Le secteur · Score d'opportunité (tier) · Sur la parcelle | aussi OUTIL: Ce qu'ils construisent, Communes |
| SUP — assiettes GPU (API Carto) | FICHE | Dispositifs et périmètres (parcelle); couche(s) : sup | Dispositifs et périmètres (droit des sols) · Droit des sols (ER · EBC · DPU · PEB) · §4 Urbanisme |  |
| Sudocuh (procédures d'urbanisme) | FICHE | Règlement de la zone (extraits) | Règlement · Règlement d'urbanisme (zones + extraits) | aussi OUTIL: PLU, Procédure & changement |
| Systèmes d'endiguement et zones protégées (DEAL Lizmap) | FICHE | Système d'endiguement; couche(s) : endiguement | Pour information · Risques et protections · §5 Risques |  |
| TCSP — voies bus en site propre (OSM) | FICHE | couche(s) : tcsp_station, tcsp_troncon, tcsp_zone | §6 Réseaux |  |
| Taux de taxe foncière — fichier REI (DGFiP) | FICHE | Taxe foncière (taux TFPB) | En-tête |  |
| Taxe d'aménagement — taux communaux (délibérations) | FICHE | Taxe d'aménagement — taux communal (référence) | Bilan indicatif · Constructibilité | aussi OUTIL: Taxe d'aménagement |
| Trafic RN (Région Réunion — SIR) | OUTIL |  |  | Étude de zone |
| Transport public — GTFS (PAN, 7 réseaux) | FICHE | Transport public — au plus proche; Stationnement allégé (TCSP, L151-36); couche(s) : transport_arret, transport_ligne | Accès · Réseaux et accès · §6 Réseaux |  |
| Urbanisme PLU/GPU (API Carto) | FICHE | Capacité (logements); Division (candidate); Marge de surélévation (au faîtage); Mixité sociale (clause); couche(s) : plu_gpu_prescription, plu_gpu_zone, plu_gpu_zone__archive_m40 | Ce qui est constructible · Constructibilité · Division · Division (copropriétés/lots) · En-tête | aussi OUTIL: Densifier l'existant, Faisabilité |
| VRD / assainissement (SPANC) | AUCUN |  |  | slug spanc_epci — rien de visible |
| ZFANG — zone franche d'activité nouvelle génération (Légifrance) | FICHE | Périmètres et dispositifs (parcelle); couche(s) : zfang | Dispositifs et périmètres (QPV, ANRU, ZFANG, FRR) · Dispositifs fiscaux et urbains · §7 Fiscalité |  |
| ZNIEFF (INPN/MNHN) | FICHE | Vigilances; couche(s) : znieff | Ce qui contraint · Risques et protections · §5 Risques | aussi OUTIL: Pièges et risques |
| Zonage ABC des communes (DHUP) | COMMUNE | Zonage A/B/C (logement) | Zonage A/B/C (logement) |  |
| Zones humides — inventaires DEAL (Carmen) | FICHE | couche(s) : zone_humide | §5 Risques |  |
| data.regionreunion.com — Potentiel foncier | FICHE | couche(s) : potentiel_foncier, sar | §10 Potentiel · §4 Urbanisme |  |

## Sources qui n'alimentent rien de visible (AUCUN)

- SIRENE
- VRD / assainissement (SPANC)

Réconciliation (vérifiée à la main) — les deux AUCUN sont RÉELS, pas des trous à combler :
- **SIRENE** (data_sources id 21) : les données SIRENE de la fiche (identité PM, événements
  propriétaire, concurrents) viennent de « **SIRENE établissements géolocalisés** » (id 86, verdict
  FICHE) et de « Recherche d'entreprises (DINUM) » (FICHE). L'entrée « SIRENE » nue est un doublon
  de catalogue qu'aucune donnée ni couche ne référence.
- **VRD / assainissement (SPANC)** : source manuelle du catalogue ; sur la fiche, le poste VRD est
  SAISI par le client (donnée `projet`, sans réservoir) — la source n'alimente aucune ligne servie.

## Notes de méthode
- **FICHE** = la source alimente ≥1 élément de la fiche parcelle, établi par l'un de : (a) donnée
  servie par un robinet `fiche_parcelle` ; (b) donnée DÉCLARÉE dans `declarations/fiche/` (surfaces
  parcelle, complètes depuis FICHE-RANGEMENT-2 lot 2) ; (c) couche `spatial_layers.data_source_id`
  (les 51/53 couches thématiques « remontent à la fiche ») ; (d) source de la cascade servie
  (`dryrun_cascade_results`). La « section » est au mieux : robinet/déclaration pour (a)(b), nature
  de la couche pour (c)(d).
- Les sous-sources Géorisques granulaires (mvt/ICPE/cavités/sites-sols) et les couches (OCS, forêt,
  EDF HTA, GéoLittoral, Potentiel foncier…) alimentent la fiche par leur COUCHE (chemin c/d) ; leurs
  DONNÉES cascade sont attribuées au réservoir agrégé `georisques_api` — attribution registre grossière
  mais visible côté fiche (à affiner si on veut la source granulaire au « i »).
- Rien n'a été corrigé ni rattaché (lecture seule).
