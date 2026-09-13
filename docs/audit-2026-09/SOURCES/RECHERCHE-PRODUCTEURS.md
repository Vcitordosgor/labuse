# Audit des 92 sources LABUSE — Fiches producteurs, couverture 974 et verdicts d'exploitation

## TL;DR
- **La plupart des « trous » de LABUSE ne viennent pas des producteurs mais d'endpoints sous-exploités** : basculer des PDF/exports statiques vers les **flux WFS/WMS EPSG:2975 de la DEAL Réunion** (`deal974.lizmap.com`), vers l'**API Carto GPU** (`apicarto.ign.fr/api/gpu`) et vers les **téléchargements Géoplateforme IGN `latest`** débloque immédiatement des champs et des mises à jour manqués, sans convention et sans scraping.
- **Les vrais trous indépassables sont concentrés** sur le DPU (périmètre exploitable en ligne pour seulement ~2 à 4 communes sur 24, même si l'EPF Réunion en détient la délégation pour plus de 80 % des communes), les SIS (Nord-Est et Sud encore à l'état de projet, seul l'Ouest arrêté depuis 2023), le PEB Pierrefonds (uniquement PDF), les zonages d'assainissement (détenus par les 5 EPCI, non ouverts) et le DPE ADEME (filtrage géographique 974 défaillant).
- **Réutilisation commerciale** : l'écrasante majorité est en Licence Ouverte / Etalab 2.0 ou ODbL (commercial autorisé). À surveiller : **DVF** (interdiction de ré-identification et de réindexation), **OSM/BAN-BANO** (ODbL, partage à l'identique), et un bloc de **licences à faire confirmer par écrit** (couches DEAL Lizmap, Conservatoire du littoral, ONF, EDF Réunion, Parc national), plus les données **sous convention** (RPLS détaillé, CoproFF, OLL loyers).

## Key Findings

1. **Endpoint DEAL massivement sous-exploité.** La DEAL Réunion publie un serveur Lizmap complet en EPSG:2975 avec flux WMS/WMTS/WFS téléchargeables (`https://deal974.lizmap.com/cartes/`) couvrant aléas/PPR/TRI, systèmes d'endiguement et zones protégées, carte hypsométrique du littoral, cartes de bruit, ravines DPF, ENS, zones humides et 50 pas géométriques. Toute lecture de PDF ou d'export daté laisse des couches vectorielles à jour sur la table.

2. **L'API Carto GPU est la clé de tout l'urbanisme.** `https://apicarto.ign.fr/api/gpu/` (module Urbanisme v2.9.2) sert zonages, prescriptions (EBC, emplacements réservés), périmètres d'information (dont DPU en couche `info-surf`, `TYPEINF=04` au standard CNIG actuel — `03` pour les dépôts anciens) et servitudes d'utilité publique par géométrie, en licence ouverte et usage libre.

3. **DPU : le paradoxe à afficher honnêtement.** Le périmètre n'est exploitable en ligne que pour **Saint-Pierre** (DPU simple + renforcé, délégation à l'EPF Réunion par convention opérationnelle n°16 24 01, délibération n°35/1690 du conseil municipal du 21/10/2024) et **Saint-Benoît** (périmètre ajusté au PLU du 06/02/2020, portage EPF), plus Saint-Paul et Saint-Leu dont l'annexe DPU du PLU au GPU est présumée. **Pourtant, la Cour des comptes établit que « l'EPFR bénéficie de la délégation du droit de préemption de plus de 80 % des communes soit une surface de 10 000 ha sur les 26 000 ha d'espaces urbains existants ».** Autrement dit : le DPU existe presque partout, mais n'est presque nulle part cartographié dans le GPU.

4. **SIS : état mixte et communes précisément identifiées.** Secteur **Ouest arrêté (2023)** ; secteurs **Nord-Est et Sud à l'état de projet**, mis en consultation par l'arrêté préfectoral n°2026-218/SG/SCOPP/BCPE du 19/02/2026 (modifié par les arrêtés n°2026-405 et n°2026-406 du 02/04/2026), avec consultation électronique « du 7 avril au 7 mai 2026 inclus ». Les projets portent sur **Le Port, Saint-Paul, Saint-Louis, Saint-Pierre et La Plaine-des-Palmistes**. Géorisques ne publie que les SIS définitivement diffusés (CSV, mise à jour quotidienne).

5. **DPE ADEME : filtre géographique cassé pour le 974.** Les jeux officiels (`data.ademe.fr/datasets/dpe03existant`) sont nationaux, mensuels, en licence ouverte, mais le filtrage par département outre-mer est peu fiable (les lignes « 974 » remontent majoritairement un code postal métropolitain). Solution : filtrer sur le **code INSEE commune (974xx)**, pas le code postal, et fiabiliser via RNB/BAN.

6. **IGN Géoplateforme entièrement ouvert.** BD TOPO, BD ORTHO, RGE ALTI, OCS GE, LiDAR HD, CoSIA sont en **Licence Ouverte Etalab 2.0** (commercial autorisé), téléchargeables via l'API Atom (`geoservices.ign.fr/telechargement-api`) et servis en WMS/WFS via `data.geopf.fr`. **La Réunion est le premier DROM couvert par le LiDAR HD** ; les produits dérivés MNT/MNS/MNH y sont déjà disponibles.

7. **Millésimes très récents disponibles.** DVF mis à jour le **7 avril 2026** (transactions jusqu'au 31/12/2025, base portée à plus de 30 millions de transactions) ; BAN en mise à jour quotidienne (dernière modif 12/09/2026) ; cadastre PCI millésime juin 2026 ; INSEE Filosofi carreaux 200 m millésime 2021 (couvre explicitement La Réunion) ; BPE géolocalisée 2025 (mise à jour 09/07/2026).

---

## Details — Fiches par famille (10 points par source)

### FAMILLE RISQUES

**Géorisques (général) / API Géorisques.** 1. BRGM / DGPR. 2. `georisques.gouv.fr/donnees/bases-de-donnees` ; API v2 `georisques.gouv.fr/api/v1/`. 3. CSV, GeoJSON, API REST. 4. Fréquence variable selon base. 5. Licence Ouverte, commercial autorisé. 6. 974 entière. 7. Champs selon endpoint. 8. Commune/parcelle/adresse. 9. Page datée, API paginée. 10. **Verdict : rien de plus sur l'agrégat**, mais bug connu de complétude sur l'API CatNat.

**CatNat.** 1. DGPR/CCR via GASPAR. 2. `georisques.gouv.fr/api/v1/gaspar/catnat?code_insee=974xx`. 3. JSON/CSV. 4. Sous 30 j après parution au JO. 5. Licence Ouverte. 6. 974 entière. 7. Code arrêté, dates début/fin, date JO, libellé risque. 8. Commune. 9. Nouvelle procédure dès parution. 10. **Verdict : meilleur endpoint** (API GASPAR versionnée), mais **recouper avec l'export CSV national** car l'API renvoie parfois moins d'arrêtés que le site web (codes de risque non mappés).

**AZI/TRI inondation (GASPAR).** 1. DGPR. 2. GASPAR + jeux TRI Géorisques/data.gouv. 3. Shapefile/GeoJSON, standard Directive Inondation v2 (millésime 2020). 4. Cycle de rapportage européen. 5. Licence Ouverte. 6. Selon TRI désignés au 974. 7. Champs standardisés Directive Inondation. 8. Zonage. 9. Millésime dans le nom du jeu. 10. **Verdict : champs supplémentaires utiles** (scénarios fréquent/moyen/extrême).

**DEAL PPR/aléas.** 1. DEAL Réunion. 2. `deal974.lizmap.com/cartes/index.php/view/map?repository=02sprinr&project=01risque` (« Aléas littoraux et continentaux, PPR approuvés et TRI »), WMS/WMTS/WFS EPSG:2975. 3. Vecteur via WFS. 4. Selon approbations PPR. 5. **Licence non écrite sur Lizmap — à clarifier** (diffusion au titre de la politique de diffusion DEAL). 6. 974 entière. 7. Aléa, niveau, date d'approbation PPR. 8. Zonage/parcelle. 9. Extent et couches datées sur Lizmap. 10. **Verdict : meilleur endpoint** — consommer le WFS plutôt que les PDF ; la couche « état des PAC, PPR, PPRL et leur date d'approbation » sert la fraîcheur.

**DEAL cartes de bruit (CBS 4e échéance).** 1. DEAL/Préfet. 2. `reunion.developpement-durable.gouv.fr/4-les-cartes-de-bruit-strategiques-a55.html` ; arrêté n°2023-610/SG/SCOPP/BCPE du **28/03/2023** (routier non concédé > 3 M véh/an). 3. Cartes type A/B/C, PDF + WFS Lizmap possible. 4. Échéance quinquennale (4e = 2023). 5. Licence Ouverte présumée (données État). 6. Axes routiers > 3 M véh/an du 974 ; ferroviaire non concerné. 7. Lden, Ln, isophones 68/62 dB(A). 8. Courbes isophones. 9. Arrêté daté. 10. **Verdict : champs supplémentaires utiles** (isophones vectorielles) si servies en WFS ; sinon trou vectoriel (PDF).

**Classement sonore ITT (Cerema).** 1. Préfet/DEAL (méthodo Cerema). 2. Carte type B « secteurs affectés par le bruit » sur Lizmap DEAL. 3. Vecteur. 4. Révisé périodiquement. 5. Licence Ouverte présumée. 6. 974. 7. Catégorie (1-5), largeur secteur affecté. 8. Tronçon linéaire. 9. Arrêté préfectoral. 10. **Verdict : champs supplémentaires utiles** (catégorie sonore par voie).

**Géorisques CASIAS / sites et sols pollués (ex-BASOL).** 1. BRGM/DGPR. 2. bases CASIAS et « sites et sols pollués » Géorisques. 3. CSV. 4. CASIAS régulier. 5. Licence Ouverte. 6. 974 entière. 7. Identifiant, activité, état de connaissance. 8. Site/parcelle. 9. Base datée. 10. **Verdict : rien de plus** (déjà exhaustif côté producteur).

**ICPE.** 1. DGPR/inspection. 2. `georisques.gouv.fr` + `installationsclassees.developpement-durable.gouv.fr`. 3. CSV/API. 4. Régulière. 5. Licence Ouverte. 6. 974. 7. Régime, rubrique, statut Seveso. 8. Établissement. 9. Base datée. 10. **Verdict : rien de plus.**

**Cavités souterraines / mouvements de terrain.** 1. BRGM. 2. bases dédiées Géorisques. 3. CSV/GeoJSON. 4. Régulière. 5. Licence Ouverte. 6. 974. 7. Type, localisation, fiabilité. 8. Ponctuel/zone. 9. Base datée. 10. **Verdict : rien de plus.**

**SIS (secteurs d'information sur les sols)** — *approfondi.* 1. Préfecture/DEAL + Géorisques. 2. Projets : `reunion.gouv.fr/.../Projets-de-creation-de-secteurs-d-information-sur-les-sols-SIS-sur-les-secteurs-Nord-Est-Sud-Ouest` (dossiers ZIP + arrêtés PDF du 19/02/2026) ; définitifs : `georisques.gouv.fr/donnees/bases-de-donnees/secteurs-dinformations-sur-les-sols-sis` (CSV, MàJ quotidienne). 3. ZIP (projets), CSV (Géorisques). 4. Révision annuelle par le préfet. 5. Licence Ouverte (Géorisques). 6. **Ouest arrêté (2023) ; Nord-Est et Sud en projet** (arrêté n°2026-218 du 19/02/2026, modifié le 02/04/2026 ; consultation du 7 avril au 7 mai 2026), sur les communes du **Port, de Saint-Paul, Saint-Louis, Saint-Pierre et de La Plaine-des-Palmistes**. 7. Identifiant SSP, commune, emprise. 8. Parcelle/emprise. 9. Page consultation reunion.gouv.fr + base Géorisques quotidienne. 10. **Verdict : trou temporaire chez le producteur** pour Nord-Est/Sud. *Phrase app :* « Secteurs d'information sur les sols : arrêtés pour l'Ouest (2023) ; Nord-Est et Sud en projet, non opposables (consultation close le 7 mai 2026). »

**GéoLittoral érosion côtière.** 1. Cerema/DGALN. 2. `geolittoral.developpement-durable.gouv.fr` + indicateur national de l'érosion côtière sur data.gouv. 3. Shapefile/WMS. 4. Périodique. 5. Licence Ouverte. 6. Littoral 974 — **couverture précise non vérifiée**. 7. Taux d'évolution du trait de côte. 8. Linéaire côtier. 9. Millésime en métadonnées. 10. **Verdict : à confirmer** que l'indicateur national couvre les communes littorales du 974.

**RTAA DOM.** 1. DEAL/ministère (réglementation thermique-acoustique-aération DOM). 2. Documentation réglementaire reunion.developpement-durable.gouv.fr. 3. Texte réglementaire (pas un jeu géographique). 4. Selon évolutions. 5. Réglementation publique. 6. 974 (spécifique DOM). 7. N/A. 8. N/A. 9. Publication d'arrêtés. 10. **Verdict : trou de nature** — c'est une réglementation, pas une donnée ; rien de plus à tirer côté jeu de données.

### FAMILLE URBANISME

**Urbanisme PLU/GPU (API Carto)** — *pivot.* 1. IGN/DGALN (GPU). 2. `apicarto.ign.fr/api/gpu/` (v2.9.2) ; portail `geoportail-urbanisme.gouv.fr`. 3. JSON/GeoJSON, WGS84. 4. Flux continu (à chaque dépôt de document opposable). 5. Licence Ouverte, usage libre, commercial autorisé. 6. Selon documents déposés commune par commune. 7. Couches `document`, `zone-urba`, `prescription-surf/lin/pct`, `info-surf/lin/pct`, `assiette-sup`, `generateur-sup`, `acte-sup`. 8. Zonage/parcelle. 9. Flux ATOM `download-feed`, module `procedure`, date de publication par document. 10. **Verdict : meilleur endpoint** — remplace toute lecture manuelle du GPU.

**GPU DPU** — *approfondi, commune par commune.* 1. Communes / EPCI / EPF Réunion, exposition GPU via IGN. 2. API Carto `info-surf` filtrée `TYPEINF=04` (dépôts récents) ou `03` (anciens) ; DPU renforcé porté par le champ `LIBELLE`. 3. GeoJSON. 4. Selon dépôts. 5. Licence Ouverte (données GPU). 6. **Couverture très partielle en cartographie, mais quasi générale en droit** :
- **Confirmés en ligne** : **Saint-Pierre** (DPU simple + renforcé, délégation EPF Réunion, convention n°16 24 01, délib. 35/1689 et 35/1690 du CM du 21/10/2024, `saintpierre.re`) ; **Saint-Benoît** (périmètre ajusté au PLU du 06/02/2020, délib. DEL 079 09 2022, portage EPF, `saint-benoit.re`).
- **PLU au GPU, annexe DPU présumée** : **Saint-Paul** (`mairie-saintpaul.re/plu-en-vigueur`), **Saint-Leu**.
- **Non vérifiés individuellement (20 communes)** : Saint-Denis (recueils d'actes en ligne à dépouiller, `saintdenis.re/le-recueil-des-actes-administratifs`), Sainte-Marie, Sainte-Suzanne, Le Port, La Possession, Trois-Bassins, Saint-Louis, Cilaos, Étang-Salé, Les Avirons, Petite-Île, Entre-Deux, Le Tampon, Saint-Joseph, Saint-Philippe, Bras-Panon, Saint-André, Salazie, La Plaine-des-Palmistes, Sainte-Rose.
- **Fait structurant** : selon la Cour des comptes, « l'EPFR bénéficie de la délégation du droit de préemption de plus de 80 % des communes soit une surface de 10 000 ha sur les 26 000 ha d'espaces urbains existants » (rapport d'observations définitives sur l'EPF Réunion). Le DPU existe donc dans la grande majorité des communes, même non cartographié au GPU.
7. `TYPEINF`, `LIBELLE`, géométrie. 8. Périmètre (zones U/AU). 9. Recueils d'actes communaux + délibérations du conseil d'administration de l'EPF Réunion (`epf.re/pages/deliberations-des-conseils-dadministration`, source la plus efficace pour recenser les délégations). 10. **Verdict : trou structurel chez le producteur (dispersion communale)** ; l'absence au GPU ≠ absence de DPU. *Phrase app :* « Droit de préemption urbain : le périmètre exact n'est cartographié que pour Saint-Pierre et Saint-Benoît ; ailleurs, un DPU s'applique très probablement en zones U/AU (l'EPF Réunion en est délégataire pour plus de 80 % des communes) mais son périmètre n'est pas publié — vérifier en mairie ou auprès de l'EPF Réunion. »

**GPU emplacements réservés.** 1. Communes via GPU. 2. API Carto `prescription-surf/lin/pct`. 3. GeoJSON. 4. Selon dépôts. 5. Licence Ouverte. 6. Selon PLU déposés. 7. `TYPEPSC`, libellé, bénéficiaire. 8. Prescription. 9. Flux ATOM. 10. **Verdict : meilleur endpoint (API Carto)**, champ bénéficiaire utile.

**GPU EBC.** 1. Communes via GPU. 2. API Carto `prescription-surf` (EBC). 3. GeoJSON. 4. Selon dépôts. 5. Licence Ouverte. 6. Selon PLU déposés. 7. `TYPEPSC=EBC`, géométrie. 8. Prescription surfacique. 9. Flux ATOM. 10. **Verdict : rien de plus** (API Carto exhaustive sur les documents déposés).

**GPU zonages d'assainissement** — *approfondi.* 1. Les 5 EPCI (compétence assainissement depuis le 01/01/2020 : CINOR, TCO, CIVIS, CASUD, CIREST). 2. Théoriquement GPU (annexe PLU, `typeinf 19`)/API Carto ; sinon dossiers EPCI. 3. Vecteur si annexé. 4. Selon procédures. 5. Licence Ouverte si au GPU. 6. **Partielle/non vérifiée** : la CINOR a un zonage EU (examen au cas par cas, communes de Saint-Denis, Sainte-Marie, Sainte-Suzanne, réf. avis MRAe) mais **aucune publication open data EPCI confirmée** (ni Opendatasoft régional, ni PEIGEO). 7. Zone collectif/non collectif. 8. Zonage. 9. Annexion PLU. 10. **Verdict : trou chez le producteur** — non publié en open data par les EPCI. *Phrase app :* « Zonage d'assainissement : détenu par l'intercommunalité compétente depuis 2020, non disponible en open data — se référer à l'EPCI. »

**SUP assiettes GPU** — *approfondi.* 1. Gestionnaires de servitudes via GPU. 2. API Carto `assiette-sup-s/l/p`, `generateur-sup`, `acte-sup`. 3. GeoJSON. 4. Selon dépôts. 5. Licence Ouverte. 6. Selon catégories déposées (I4 électricité, PT télécoms, AC1 monuments, T5 aérodrome…). 7. Catégorie SUP, gestionnaire, acte. 8. Assiette. 9. Flux ATOM. 10. **Verdict : champs supplémentaires utiles** (acte + générateur) ; **trou** sur les catégories non encore déposées par les gestionnaires, à documenter catégorie par catégorie.

**ACV/PVD/ORT (DGALN).** 1. DGALN/ANCT. 2. data.gouv (Action Cœur de Ville, Petites Villes de Demain, ORT). 3. CSV. 4. Ponctuelle. 5. Licence Ouverte. 6. Communes conventionnées du 974. 7. Commune, dispositif, date convention. 8. Commune. 9. MàJ jeu data.gouv. 10. **Verdict : rien de plus.**

**Consommation d'espaces NAF (Cerema).** 1. Cerema. 2. `artificialisation.developpement-durable.gouv.fr`/data.gouv. 3. CSV. 4. Annuelle. 5. Licence Ouverte. 6. 974 (à la commune). 7. Flux NAF habitat/activité/mixte. 8. Commune. 9. Millésime annuel. 10. **Verdict : rien de plus.**

**Cartofriches (Cerema).** 1. Cerema. 2. `cartofriches.cerema.fr` + API/data.gouv. 3. CSV/GeoJSON. 4. Continue. 5. Licence Ouverte. 6. Friches recensées 974. 7. Identifiant, surface, statut. 8. Site. 9. Base datée. 10. **Verdict : champs supplémentaires utiles** (état d'avancement de la reconversion).

**Sudocuh.** 1. DGALN. 2. Suivi des documents d'urbanisme et d'habitat, data.gouv. 3. CSV. 4. Annuelle. 5. Licence Ouverte. 6. 974. 7. Type de document, état, EPCI compétent. 8. Commune/EPCI. 9. Millésime. 10. **Verdict : rien de plus.**

**NPNRU.** 1. ANRU. 2. data.gouv/anru.fr. 3. CSV. 4. Ponctuelle. 5. Licence Ouverte. 6. Quartiers conventionnés 974. 7. Quartier, protocole, financement. 8. Quartier. 9. MàJ jeu. 10. **Verdict : rien de plus.**

**PLH des 5 EPCI.** 1. Les 5 EPCI. 2. Sites EPCI/GPU (PLH annexé). 3. PDF majoritairement. 4. ~6 ans. 5. Variable. 6. Selon EPCI ayant PLH exécutoire. 7. N/A structuré. 8. EPCI. 9. Site EPCI. 10. **Verdict : trou vectoriel** — souvent PDF, pas de données structurées.

**PEB Pierrefonds** — *approfondi.* 1. DGAC/Préfet. 2. `reunion.gouv.fr/.../Plan-d-exposition-au-bruit-de-l-aerodrome-de-Saint-Pierre-Pierrefonds` — arrêté du **29/03/2017**, plan PDF au 1/25 000 + rapport de présentation ; visualisation `geoportail.gouv.fr/donnees/plan-dexposition-au-bruit`. 3. **PDF** ; version vectorielle Géoportail à confirmer. 4. Stable depuis 2017. 5. Document réglementaire opposable, réutilisation publique. 6. Commune de **Saint-Pierre** (zones A/B/C/D) ; **EPCI concernés : CIVIS et CASUD**. 7. Zones de bruit A/B/C/D (Lden). 8. Zonage. 9. Arrêté daté. 10. **Verdict : trou vectoriel probable chez le producteur** — vérifier si le PEB est servi en vectoriel via le Géoportail PEB ou l'annexe SUP T5 du PLU de Saint-Pierre au GPU (API Carto `assiette-sup`). *Phrase app :* « PEB de Pierrefonds : arrêté du 29/03/2017, disponible en plan PDF ; contour vectoriel à vérifier via l'annexe SUP du PLU de Saint-Pierre. »

**Révision PLU de Saint-Leu** — *source candidate.* 1. Commune de Saint-Leu (TCO). 2. `saintleu.re/plan-local-d-urbanisme-plu` + registre `registre-numerique.fr/revision-plu-stleu`. 3. PDF (dossier d'enquête). 4. **Enquête publique du 1er septembre au 9 octobre 2026** (arrêté municipal n°579/2026/DAD ; avis MRAe du 12/03/2026) ; approbation visée fin 2026/premier trimestre. 5. Document en cours (non opposable). 6. Saint-Leu. 7. N/A structuré. 8. Commune. 9. Suivi via module `procedure` de l'API GPU + site communal. 10. **Verdict : procédure en cours** — surveiller la publication du PLU révisé au GPU. Le PLU actuel (env. 17 ans) reste opposable jusqu'à approbation.

### FAMILLE MARCHÉ

**DVF (Etalab).** 1. DGFiP/Etalab (DINUM). 2. `data.gouv.fr/datasets/demandes-de-valeurs-foncieres` + app `app.dvf.etalab.gouv.fr`. 3. CSV. 4. Semestrielle ; **dernière MàJ 7 avril 2026** (transactions jusqu'au 31/12/2025 ; base à plus de 30 millions de transactions). 5. Licence Ouverte, **mais restrictions** : pas de ré-identification indirecte (R112 A-3 LPF), pas d'indexation par moteurs de recherche externes. 6. DOM inclus **sauf Alsace/Moselle/Mayotte** — La Réunion couverte. 7. Date mutation, valeur foncière, type de local, surface, parcelle, nature culture. 8. Parcelle. 9. Chaque MàJ peut ajouter des transactions dans tous les millésimes ; date affichée sur data.gouv. 10. **Verdict : réutilisation commerciale à surveiller** (restrictions ré-identification/indexation) ; rien de plus côté champs.

**DVF Réunion (Région).** 1. Région Réunion (Opendatasoft, `data.regionreunion.com`). 2. Portail ODS régional. 3. CSV/API ODS. 4. Selon reprise du millésime DVF. 5. Licence à vérifier (probablement Licence Ouverte). 6. 974. 7. Dérivés de DVF. 8. Parcelle/commune. 9. API ODS versionnée. 10. **Verdict : meilleure source amont = DVF Etalab/DGFiP** (plus frais) ; la version régionale n'ajoute pas de champ (redondance).

**Loyers DHUP (carte des loyers).** 1. DHUP/ANIL. 2. data.gouv « carte des loyers ». 3. CSV. 4. Annuelle. 5. Licence Ouverte. 6. Indicateurs à la commune, DOM inclus — **à confirmer pour le 974**. 7. Loyer médian €/m² maison/appartement. 8. Commune. 9. Millésime. 10. **Verdict : à confirmer** pour la couverture 974.

**Loyers OLL (ADIL/AGORAH).** 1. Observatoire local des loyers (ADIL/AGORAH). 2. Publications OLL Réunion. 3. PDF/tableaux. 4. Annuelle. 5. Variable/convention. 6. 974 par EPCI et zones. 7. Loyer par typologie et zone. 8. Zone infra-EPCI. 9. Publication annuelle. 10. **Verdict : accès sous convention/PDF** — trou vectoriel ; source la plus fine localement mais peu structurée.

**Coût de construction (EPTB SDES).** 1. SDES. 2. `statistiques.developpement-durable.gouv.fr`. 3. CSV. 4. Périodique. 5. Licence Ouverte. 6. National/régional. 7. Indices coût construction. 8. Région. 9. Millésime. 10. **Verdict : rien de plus.**

### FAMILLE LOGEMENT

**INSEE RP2022 détail Logements (EGOUL) / bases IRIS / RP Logement 2023.** 1. INSEE. 2. `insee.fr` (fichiers détail RP) + outil cartographie infracommunale `insee.fr/fr/outil-interactif/7737357`. 3. CSV/DBF. 4. Annuelle (millésimes glissants). 5. Licence Ouverte. 6. 974 entière. 7. Statut occupation, type logement, EGOUL, IRIS. 8. IRIS/logement. 9. Millésime RP annuel. 10. **Verdict : rien de plus** ; utiliser le dernier millésime.

**Contours IRIS.** 1. IGN/INSEE. 2. Géoplateforme/data.gouv CONTOURS-IRIS. 3. Shapefile/GeoPackage. 4. Annuelle. 5. Licence Ouverte. 6. 974. 7. Code IRIS, type, commune. 8. IRIS. 9. Millésime dans le nom. 10. **Verdict : rien de plus.**

**Filosofi carreaux 200 m.** 1. INSEE. 2. `insee.fr/fr/statistiques/8735162` (Revenus, pauvreté, niveau de vie 2021). 3. Shapefile/GeoPackage/CSV — chaque ZIP contient Métropole + Martinique + **La Réunion**. 4. Millésime **2021** (dernier). 5. Licence Ouverte. 6. 974 (La Réunion explicitement dans le champ). 7. 34 variables (âge, ménages, logements, revenus, imputation). 8. Carreau 200 m (id INSPIRE `idcar_200m`). 9. Nouveau millésime publié par l'INSEE. 10. **Verdict : rien de plus** ; vérifier le passage au millésime le plus récent.

**RPLS.** 1. SDES. 2. data.gouv « données détaillées au logement RPLS » ; version détaillée sur demande (`rpls.cgdd@developpement-durable.gouv.fr`). 3. CSV. 4. Annuelle (au 1er janvier). 5. **Version fine sous convention/ayants droit** ; version diffusable en Licence Ouverte. 6. 974. 7. Type construction, pièces, surface, année, financement, conventionnement, DPE ; **identité du bailleur non fournie**. 8. Logement. 9. Millésime annuel (RPLS2024 = collecte 2023, doté d'ID-RNB). 10. **Verdict : accès sous convention** pour la version fine ; champs DPE utiles.

**RNIC copropriétés (Anah) / CoproFF.** 1. Anah (RNIC) ; Cerema (CoproFF). 2. data.gouv RNIC (open data) + Datafoncier CoproFF. 3. CSV. 4. Trimestrielle (RNIC). 5. RNIC open data (Licence Ouverte) ; **CoproFF réservé aux ayants droit fichiers fonciers/LOVAC**. 6. 974. 7. Open data : nom, adresse, date création syndicat, nombre/nature de lots, syndic, procédures (29-1). 8. Copropriété/parcelle. 9. MàJ trimestrielle. 10. **Verdict : champs supplémentaires utiles via CoproFF sous convention** (copropriétés non immatriculées — env. un tiers du parc — et indicateurs de fragilité).

**Inventaire SRU (DHUP).** 1. DHUP (via RPLS). 2. data.gouv inventaire SRU. 3. CSV. 4. Annuelle. 5. Licence Ouverte. 6. Communes soumises SRU du 974. 7. Taux LLS, objectifs, prélèvement. 8. Commune. 9. Millésime. 10. **Verdict : rien de plus.**

**Zonage ABC (DHUP).** 1. DHUP. 2. data.gouv « zonage ABC » + `zonage-abc.din.developpement-durable.gouv.fr`. 3. CSV. 4. Selon arrêtés. 5. Licence Ouverte. 6. 974 (largement en zone B). 7. Commune, zone. 8. Commune. 9. Arrêté daté. 10. **Verdict : rien de plus.**

**QPV 2024.** 1. ANCT. 2. data.gouv / `sig.ville.gouv.fr`, contours QPV 2024. 3. Shapefile/GeoJSON. 4. Révision 2024. 5. Licence Ouverte. 6. QPV du 974. 7. Code QP, nom, commune. 8. Quartier. 9. Millésime 2024. 10. **Verdict : rien de plus.**

### FAMILLE ÉCONOMIE / PROPRIÉTAIRES

**SIRENE / SIRENE établissements géolocalisés.** 1. INSEE. 2. API Sirene (`api.insee.fr`) + base géolocalisée data.gouv/`data.insee.fr`. 3. CSV/API JSON. 4. Quotidienne. 5. Licence Ouverte ; **respect du statut de diffusion** (opposition possible des dirigeants, données anonymisées). 6. 974. 7. SIRET, APE, effectif, adresse, coordonnées X/Y. 8. Établissement. 9. Statut de diffusion daté (1er mai 2026 pour la base géoloc). 10. **Verdict : rien de plus** ; confirmer l'usage de la base géolocalisée pour X/Y.

**BODACC.** 1. DILA. 2. `bodacc.fr` + data.gouv/ODS DILA. 3. JSON/CSV/API. 4. Quotidienne. 5. Licence Ouverte. 6. 974. 7. Annonces (ventes, procédures collectives, radiations). 8. Établissement. 9. API ODS versionnée. 10. **Verdict : rien de plus.**

**INPI RNE.** 1. INPI. 2. API RNE/`data.inpi.fr`. 3. JSON/API. 4. Continue. 5. Conditions INPI (open data pour l'essentiel). 6. 974. 7. Dirigeants, bénéficiaires effectifs (accès restreint), comptes. 8. Entreprise. 9. API. 10. **Verdict : champs supplémentaires utiles** (dirigeants) selon droits d'accès.

**Recherche d'entreprises (DINUM).** 1. DINUM. 2. `recherche-entreprises.api.gouv.fr`. 3. API JSON. 4. Continue (agrège SIRENE/RNE/RNA). 5. Licence Ouverte, usage libre. 6. 974. 7. Agrégat SIRENE + dirigeants + finances. 8. Entreprise/établissement. 9. API. 10. **Verdict : meilleur endpoint d'agrégation** pour recouper.

**Annuaire de l'administration (DILA).** 1. DILA. 2. `api-lannuaire.service-public.fr`. 3. API/JSON. 4. Continue. 5. Licence Ouverte. 6. 974. 7. Services publics, coordonnées. 8. Organisme. 9. API. 10. **Verdict : rien de plus.**

**DGFiP parcelles des personnes morales.** 1. DGFiP (MAJIC personnes morales). 2. data.gouv « fichiers des parcelles des personnes morales ». 3. CSV. 4. Annuelle. 5. Open data (personnes morales uniquement ; personnes physiques exclues). 6. 974. 7. Parcelle, propriétaire personne morale, SIREN. 8. Parcelle. 9. Millésime annuel. 10. **Verdict : champs supplémentaires utiles** (lien parcelle↔SIREN).

**DFI filiation des parcelles (DGFiP).** 1. DGFiP. 2. data.gouv DFI. 3. CSV/format DGFiP. 4. Annuelle. 5. Open data. 6. 974. 7. Parcelle mère/fille, historique. 8. Parcelle. 9. Millésime. 10. **Verdict : champs supplémentaires utiles** (historique parcellaire).

**RPG déclarations agricoles.** 1. IGN/ASP. 2. Géoplateforme/data.gouv Registre Parcellaire Graphique. 3. Shapefile/GeoPackage. 4. Annuelle. 5. Licence Ouverte. 6. 974. 7. Îlot, culture principale (code). 8. Îlot/parcelle culturale. 9. Millésime annuel. 10. **Verdict : rien de plus.**

**Taux de taxe foncière REI (DGFiP).** 1. DGFiP. 2. data.gouv REI. 3. CSV. 4. Annuelle. 5. Open data. 6. 974. 7. Taux TFPB/TFPNB par commune/EPCI. 8. Commune. 9. Millésime. 10. **Verdict : rien de plus.**

**Taxe d'aménagement taux communaux.** 1. DGALN/DGFiP. 2. Publication annuelle des taux (data.gouv/bulletins). 3. CSV/PDF. 4. Annuelle. 5. Open data/publique. 6. 974. 7. Taux part communale, secteurs. 8. Commune/secteur. 9. Publication annuelle. 10. **Verdict : rien de plus** (LABUSE la lit déjà directement par un outil).

### FAMILLE CADASTRE / TOPOGRAPHIE

**Cadastre (API Carto PCI / PCI Express).** 1. DGFiP/IGN. 2. `apicarto.ign.fr/api/cadastre/` + `cadastre.data.gouv.fr` (Etalab). 3. GeoJSON/SHP/EDIGEO ; API WGS84. 4. **Millésime PCI juin 2026** (trimestriel). 5. Licence Ouverte. 6. 974. 7. Parcelle, section, feuille, contenance, bâti. 8. Parcelle/bâtiment. 9. `latest` dans l'URL, page millésimes. 10. **Verdict : rien de plus** (déjà optimal via API Carto).

**Cadastre d'époque (Etalab / PCI vecteur).** 1. Etalab/DGFiP. 2. `cadastre.data.gouv.fr/data/etalab-cadastre` (millésimes historisés). 3. GeoJSON/SHP. 4. Trimestrielle + archives. 5. Licence Ouverte. 6. 974. 7. Parcelle historique. 8. Parcelle. 9. Page des millésimes. 10. **Verdict : rien de plus.**

**RGE ALTI.** 1. IGN. 2. Géoplateforme (téléchargement + WMS/WFS `data.geopf.fr`). 3. Raster (MNT maillé). 4. Selon recampagne. 5. Licence Ouverte Etalab 2.0. 6. 974. 7. Altitude. 8. Maille (1 m/5 m). 9. API Atom. 10. **Verdict : rien de plus** (progressivement supplanté par les dérivés LiDAR HD).

**LiDAR HD MNH / LiDAR HD (IGN)** — *approfondi.* 1. IGN. 2. `cartes.gouv.fr/telechargement/IGNF_MNH-LIDAR-HD` (+ MNS/MNT) ; nuages `IGNF_NUAGES-DE-POINTS-LIDAR-HD` ; tableau d'assemblage WFS `IGNF_LIDAR-HD_TA:nuage-dalle` sur `data.geopf.fr/wfs/ows`. 3. Dalles 1 km², COPC.LAZ (nuage) et raster (MNT/MNS/MNH). 4. **La Réunion = premier DROM couvert** ; produits dérivés MNT/MNS/MNH déjà disponibles, nuages ajoutés ensuite ; couverture DROM (hors Guyane) visée d'ici 2026. 5. Licence Ouverte Etalab 2.0, commercial autorisé. 6. 974 (blocs classés). 7. Classification des points ; précision altimétrique ≤ 10 cm, planimétrique 30-50 cm (insuffisante pour le bornage). 8. Dalle/point. 9. Tableau d'assemblage WFS, nommage des dalles daté (ex. `NUALHD_1-0__LAZ_..._2025-03-14`). 10. **Verdict : meilleur endpoint** — passer par le WFS TA + téléchargement Géoplateforme ; le **MNH** est particulièrement utile (hauteur de végétation/bâti). *Date de survol exacte du 974 à confirmer* (nommage de dalles daté 2025).

**BD TOPO.** 1. IGN. 2. Géoplateforme (Atom + WMS/WFS). 3. Vecteur (GeoPackage/Shapefile). 4. Trimestrielle. 5. Licence Ouverte Etalab 2.0. 6. 974. 7. Bâtiments (hauteur, nature), routes, hydro, végétation. 8. Bâtiment/tronçon. 9. Archivage trimestriel. 10. **Verdict : rien de plus** ; champ hauteur bâtiment utile.

**RNB (référentiel national des bâtiments).** 1. IGN/CSTB/ANCT (beta.gouv). 2. `rnb.beta.gouv.fr` (API + téléchargement). 3. API/CSV/GeoJSON. 4. Continue. 5. Licence Ouverte. 6. 974 (complétude à confirmer). 7. ID-RNB, géométrie, liens adresses/parcelles. 8. Bâtiment. 9. API. 10. **Verdict : champs supplémentaires utiles** (ID-RNB comme clé de jointure DPE/RPLS/BAN).

### FAMILLE TERRAIN / IMAGERIE

**BD ORTHO 20 cm / BD ORTHO IRC.** 1. IGN. 2. Géoplateforme (Atom + WMS/WMTS `data.geopf.fr`). 3. Raster (RVB 20 cm ; IRC infrarouge). 4. Selon campagne départementale. 5. Licence Ouverte Etalab 2.0. 6. 974. 7. N/A (imagerie). 8. Pixel 20 cm. 9. Millésime dans le nom. 10. **Verdict : rien de plus.**

**CoSIA.** 1. IGN. 2. Géoplateforme CoSIA (couverture du sol par IA). 3. Raster/vecteur. 4. En cours de déploiement. 5. Licence Ouverte Etalab 2.0. 6. **Disponibilité 974 à confirmer.** 7. Classes d'occupation IA. 8. Pixel/objet. 9. Géoplateforme. 10. **Verdict : à confirmer** pour la disponibilité 974.

### FAMILLE OCCUPATION DU SOL

**OCS GE.** 1. IGN. 2. Géoplateforme OCS GE (Atom + WFS). 3. Vecteur. 4. Par département, recampagne pluriannuelle. 5. Licence Ouverte Etalab 2.0. 6. **Disponibilité/millésime 974 à confirmer.** 7. Couverture (CS) + usage (US). 8. Objet. 9. Géoplateforme. 10. **Verdict : à confirmer** pour la disponibilité 974.

**IGN BD CARTO V5 occupation du sol.** 1. IGN. 2. Géoplateforme BD CARTO. 3. Vecteur. 4. Périodique. 5. Licence Ouverte Etalab 2.0. 6. 974. 7. Occupation du sol généralisée. 8. Objet (moyenne échelle). 9. Géoplateforme. 10. **Verdict : rien de plus** (OCS GE plus fin si disponible).

### FAMILLE ACCÈS / TRANSPORTS

**Transport public GTFS (PAN, 7 réseaux).** 1. AOM/exploitants via Point d'Accès National. 2. `transport.data.gouv.fr/datasets/region/04` ; Car Jaune `pysae.com/api/v2/groups/car-jaune/gtfs/pub` (+ GTFS-RT) ; Citalis GTFS + PAPANG (téléphérique). 3. GTFS + GTFS-RT. 4. À chaque mise à jour de l'offre (validation quotidienne PAN). 5. Licence Ouverte. 6. Réseaux 974 (Car Jaune interurbain, Citalis/CINOR, etc.). 7. Lignes, arrêts, horaires, temps réel. 8. Arrêt/ligne. 9. Validation PAN datée. 10. **Verdict : meilleur endpoint** — consommer les flux PAN + temps réel ; vérifier que les 7 réseaux sont tous branchés.

**OSM transport (pôles d'échange) / TCSP voies bus / Parkings OSM (loi APER) / OpenStreetMap-Overpass.** 1. OpenStreetMap. 2. API Overpass (`overpass-api.de`) + exports Geofabrik. 3. OSM XML/GeoJSON. 4. Continue. 5. **ODbL** (attribution + partage à l'identique) — commercial autorisé sous conditions ODbL. 6. 974. 7. Tags OSM (`highway`, `amenity=parking`, `public_transport`…). 8. Objet. 9. Overpass en temps réel. 10. **Verdict : rien de plus, mais ODbL impose le partage à l'identique** — attention à la contamination de licence.

**Trafic RN (Région Réunion SIR).** 1. Région Réunion (Système d'Information Routier). 2. `data.regionreunion.com` (ODS). 3. CSV/API ODS. 4. Périodique. 5. Licence à confirmer. 6. Réseau routier national 974. 7. Comptages, TMJA. 8. Tronçon. 9. API ODS. 10. **Verdict : champs supplémentaires utiles** (TMJA par tronçon).

**Fibre Arcep.** 1. Arcep. 2. `cartefibre.arcep.fr` + data.gouv (« Ma connexion internet »). 3. CSV/API. 4. Trimestrielle. 5. Licence Ouverte. 6. 974. 7. Éligibilité fibre par local/adresse. 8. Adresse/bâtiment. 9. Millésime trimestriel. 10. **Verdict : rien de plus.**

### FAMILLE ENVIRONNEMENT

**Zones humides DEAL** — *point d'attention.* 1. DEAL Réunion. 2. Lizmap DEAL (`deal974.lizmap.com`) WFS EPSG:2975. 3. Vecteur. 4. Selon inventaires. 5. **Licence non écrite — à clarifier.** 6. 974. 7. Type de zone humide, source d'inventaire. 8. Zone. 9. Couches datées Lizmap. 10. **Verdict : meilleur endpoint (WFS)** ; couverture inventaire potentiellement incomplète.

**Espaces protégés complémentaires / ENS Département (DEAL Carmen)** — *point d'attention.* 1. DEAL Réunion (WFS) / Département (ENS). 2. Lizmap/Carmen DEAL, couche `ms:ENS` signalée. 3. Vecteur WFS. 4. Selon désignations. 5. Licence à clarifier. 6. 974. 7. Type d'espace, gestionnaire. 8. Zone. 9. WFS GetCapabilities. 10. **Verdict : champ/couche supplémentaire utile** (ENS non exploités) — confirmer la présence de `ms:ENS` dans le GetCapabilities WFS.

**INPN espaces protégés / ZNIEFF (INPN/MNHN).** 1. MNHN (INPN). 2. `inpn.mnhn.fr` + Géoplateforme (WFS ZNIEFF). 3. Shapefile/WFS. 4. Selon actualisation. 5. Licence Ouverte/Etalab. 6. 974. 7. Type ZNIEFF I/II, code, espèces déterminantes. 8. Zone. 9. INPN daté. 10. **Verdict : rien de plus.**

**Parc National de La Réunion.** 1. Parc national/OFB. 2. `lizmap.ofb.fr/pnrun/` (cartothèque). 3. Vecteur/WMS. 4. Selon actualisation. 5. Licence à confirmer. 6. Cœur + aire d'adhésion 974. 7. Zonage réglementaire. 8. Zone. 9. Lizmap OFB. 10. **Verdict : rien de plus** ; confirmer le flux WFS.

**Forêts publiques (ONF).** 1. ONF. 2. data.gouv/Géoplateforme (BD Forêt IGN complémentaire). 3. Vecteur. 4. Périodique. 5. **Licence à confirmer (ONF parfois restrictive).** 6. 974. 7. Régime forestier, série. 8. Parcelle forestière. 9. Jeu daté. 10. **Verdict : licence à clarifier.**

**50 pas géométriques (DEAL).** 1. DEAL Réunion. 2. Lizmap DEAL WFS EPSG:2975. 3. Vecteur. 4. Selon délimitation. 5. Licence à clarifier. 6. Zone littorale 974. 7. Zone des 50 pas, régime. 8. Zone. 9. Lizmap. 10. **Verdict : meilleur endpoint (WFS).**

**Ravines DPF (DEAL Carmen).** 1. DEAL Réunion (Domaine Public Fluvial). 2. Lizmap/Carmen DEAL WFS. 3. Vecteur. 4. Selon actualisation. 5. Licence à clarifier. 6. 974. 7. Ravine, statut DPF. 8. Linéaire. 9. WFS. 10. **Verdict : champs utiles** (limites DPF).

**Systèmes d'endiguement et zones protégées (DEAL Lizmap)** — *source candidate.* 1. DEAL Réunion. 2. `deal974.lizmap.com` couche « systèmes d'endiguement et zones protégées » WFS EPSG:2975. 3. Vecteur. 4. Selon actualisation. 5. Licence à clarifier. 6. 974. 7. Digue, zone protégée, niveau de protection. 8. Ouvrage/zone. 9. WFS. 10. **Verdict : nouvelle source à intégrer** (risque inondation résiduel derrière digues).

**Carte hypsométrique du littoral (DEAL)** — *source candidate.* 1. DEAL Réunion. 2. `deal974.lizmap.com` couche « carte hypsométrique du littoral de La Réunion » WFS. 3. Raster/vecteur. 4. Selon actualisation. 5. Licence à clarifier. 6. Littoral 974. 7. Classes d'altitude littorale. 8. Maille. 9. WFS. 10. **Verdict : nouvelle source à intégrer** (submersion marine).

**Conservatoire du littoral.** 1. Conservatoire du littoral. 2. data.gouv/`conservatoire-du-littoral.fr` (périmètres). 3. Shapefile. 4. Périodique. 5. **Licence à établir textuellement — non vérifiée.** 6. Sites du 974. 7. Site, statut foncier. 8. Zone. 9. Jeu daté. 10. **Verdict : licence à clarifier** (usage commercial non confirmé).

**Office de l'eau Réunion — Chroniques de l'eau.** 1. Office de l'eau Réunion. 2. `eaureunion.fr`. 3. PDF (bulletins) + données via SANDRE/Hub'Eau. 4. Périodique. 5. Publication publique. 6. 974. 7. N/A structuré (bulletins). 8. Masse d'eau/commune. 9. Publication datée. 10. **Verdict : trou vectoriel** (PDF) ; pour données structurées passer par SANDRE/Hub'Eau.

### FAMILLE ATTRACTIVITÉ

**BPE INSEE.** 1. INSEE. 2. `insee.fr` BPE + outil cartographie infracommunale (BPE 2025 géolocalisée, MàJ 09/07/2026). 3. CSV. 4. Annuelle. 5. Licence Ouverte. 6. 974. 7. Type d'équipement, géolocalisation. 8. Équipement/carreau. 9. Millésime annuel. 10. **Verdict : rien de plus** ; utiliser la version géolocalisée 2025.

**FRR ex-ZRR.** 1. ANCT/DGCL. 2. data.gouv « France Ruralités Revitalisation ». 3. CSV. 4. Selon classement. 5. Licence Ouverte. 6. Communes classées 974. 7. Commune, statut FRR. 8. Commune. 9. Arrêté. 10. **Verdict : rien de plus.**

**ZFANG.** 1. DGFiP/ministère Outre-mer. 2. Publication réglementaire/data.gouv. 3. CSV/texte. 4. Selon dispositif. 5. Public. 6. 974 (dispositif DOM). 7. Secteurs éligibles. 8. Commune/secteur. 9. Texte. 10. **Verdict : rien de plus.**

### FAMILLE ÉNERGIE / RÉSEAUX

**DPE ADEME** — *approfondi.* 1. ADEME. 2. `data.ademe.fr/datasets/dpe03existant` (existants) ; jeux logements neufs et tertiaire distincts ; API Koumoul + dump PostgreSQL ; référencé sur data.gouv. 3. CSV/API JSON. 4. Mensuelle. 5. Licence Ouverte (données brutes des diagnostiqueurs, non redressées). 6. **974 : filtre géographique défaillant** — la sélection « 974 » remonte majoritairement un code postal métropolitain. 7. Classe énergie/GES, surface, consommation, adresse, année. 8. Logement/adresse. 9. Date de MàJ en tête de page. 10. **Verdict : meilleur filtre à construire** — requêter par code INSEE commune (974xx), pas par code postal, et croiser avec BAN/RNB. *Volume réel 974 à confirmer* (bien supérieur aux ~17 lignes authentiques évoquées si filtré correctement).

**EDF Réunion lignes HTA (open data).** 1. EDF Réunion/SEI. 2. Portail open data EDF SEI. 3. CSV/GeoJSON. 4. Périodique. 5. **Licence à confirmer.** 6. 974. 7. Tracé HTA, poste. 8. Linéaire. 9. Portail daté. 10. **Verdict : licence à confirmer.**

**PVGIS.** 1. Commission européenne (JRC). 2. `re.jrc.ec.europa.eu/pvg_tools/`. 3. API/CSV. 4. Stable (bases climatiques). 5. Réutilisation autorisée avec attribution. 6. Mondiale (974 inclus). 7. Irradiation, productible PV. 8. Point (lat/lon). 9. Versions PVGIS. 10. **Verdict : rien de plus.**

### FAMILLE RÉGLEMENTAIRE

**ABF / Monuments historiques (Mérimée).** 1. Ministère Culture. 2. `data.culture.gouv.fr` (base Mérimée/POP) + SUP AC1 au GPU. 3. CSV/API + GeoJSON (assiette SUP). 4. Périodique. 5. Licence Ouverte. 6. MH du 974. 7. Édifice, protection, périmètre. 8. Édifice/périmètre. 9. Base datée. 10. **Verdict : champs supplémentaires utiles** (assiette SUP AC1 via API Carto).

**SITADEL.** 1. SDES. 2. `statistiques.developpement-durable.gouv.fr`/data.gouv. 3. CSV. 4. Mensuelle. 5. Licence Ouverte. 6. 974. 7. Permis, logements, surfaces, commune. 8. Commune/opération. 9. Millésime mensuel. 10. **Verdict : rien de plus.**

**Base Adresse Nationale (BAN).** 1. DINUM/IGN/ANCT. 2. `adresse.data.gouv.fr/outils/telechargements` (national + départemental, `latest` quotidien) + API + WMS/WFS. 3. CSV/BAL/addok. 4. **Quotidienne** (dernière modif 12/09/2026). 5. Licence Ouverte Etalab 2.0 (version IGN) ; version OSM France (BANO) en ODbL. 6. 974. 7. Id adresse, voie, numéro, coordonnées, code INSEE ; **BAN PLUS** ajoute le lien adresse-bâti (surface, hauteur, nature) — **non calculé hors PCI vecteur**. 8. Adresse/bâti. 9. Archivage hebdo/mensuel, `latest` quotidien. 10. **Verdict : champs supplémentaires utiles via BAN PLUS** (lien adresse↔bâtiment).

**Radar (pige d'annonces) et VRD/SPANC** — sources manuelles internes LABUSE, hors périmètre producteur officiel. **Verdict : trou de nature** (pas de producteur public unique) ; le SPANC relève des EPCI (cf. zonages d'assainissement) et n'est pas ouvert.

---

## Tableau récapitulatif (source · endpoint · millésime · licence · couverture 974 · verdict)

| Source | Endpoint recommandé | Millésime | Licence | Couv. 974 | Verdict |
|---|---|---|---|---|---|
| Annuaire admin (DILA) | api-lannuaire.service-public.fr | continu | L. Ouverte | entière | rien de plus |
| BAN | adresse.data.gouv.fr (latest) | 12/09/2026 | L.O. 2.0 / ODbL(BANO) | entière | + BAN PLUS |
| EDF HTA | open data EDF SEI | n.v. | à confirmer | entière | licence à confirmer |
| OSM transport/parkings/TCSP | Overpass/Geofabrik | continu | ODbL | entière | ODbL share-alike |
| GTFS (PAN, 7 réseaux) | transport.data.gouv.fr/region/04 | continu | L. Ouverte | réseaux 974 | meilleur endpoint |
| RPG | Géoplateforme | annuel | L.O. 2.0 | entière | rien de plus |
| INSEE RP détail (EGOUL) | insee.fr | glissant | L. Ouverte | entière | rien de plus |
| Office de l'eau | eaureunion.fr / SANDRE | périodique | publique | entière | trou vectoriel (PDF) |
| BPE | insee.fr (géoloc 2025) | 2025 | L. Ouverte | entière | rien de plus |
| Contours IRIS | Géoplateforme | annuel | L. Ouverte | entière | rien de plus |
| Filosofi 200 m | insee.fr/statistiques/8735162 | 2021 | L. Ouverte | entière | rien de plus |
| INSEE bases IRIS | insee.fr | glissant | L. Ouverte | entière | rien de plus |
| Cadastre PCI | apicarto.ign.fr/api/cadastre | juin 2026 | L. Ouverte | entière | rien de plus |
| DFI filiation | data.gouv | annuel | open data | entière | + historique |
| ACV/PVD/ORT | data.gouv/ANCT | ponctuel | L. Ouverte | conventionnées | rien de plus |
| SITADEL | SDES/data.gouv | mensuel | L. Ouverte | entière | rien de plus |
| BODACC | bodacc.fr/ODS | quotidien | L. Ouverte | entière | rien de plus |
| INPI RNE | data.inpi.fr | continu | conditions INPI | entière | + dirigeants |
| Recherche entreprises | recherche-entreprises.api.gouv.fr | continu | L. Ouverte | entière | meilleur agrégat |
| SIRENE (+ géoloc) | api.insee.fr / data.insee.fr | quotidien | L. Ouverte | entière | rien de plus |
| Trafic RN | data.regionreunion.com | périodique | à confirmer | RN 974 | + TMJA |
| DPE ADEME | data.ademe.fr/dpe03existant | mensuel | L. Ouverte | filtre cassé | meilleur filtre INSEE |
| PVGIS | re.jrc.ec.europa.eu | stable | attribution | inclus | rien de plus |
| Espaces protégés compl. (DEAL) | deal974.lizmap.com WFS | n.v. | à clarifier | entière | + couche ENS |
| Forêts publiques (ONF) | data.gouv/Géoplateforme | périodique | à confirmer | entière | licence à clarifier |
| INPN espaces protégés / ZNIEFF | inpn.mnhn.fr / Géoplateforme | n.v. | L.O./Etalab | entière | rien de plus |
| Parc National Réunion | lizmap.ofb.fr/pnrun | n.v. | à confirmer | cœur+adhésion | rien de plus |
| Zones humides DEAL | deal974.lizmap.com WFS | n.v. | à clarifier | entière | meilleur endpoint |
| FRR ex-ZRR | data.gouv | selon classement | L. Ouverte | classées | rien de plus |
| QPV 2024 | sig.ville.gouv.fr | 2024 | L. Ouverte | QPV 974 | rien de plus |
| ZFANG | data.gouv/OM | selon dispositif | publique | entière | rien de plus |
| Coût construction (SDES) | statistiques.dev.-durable | périodique | L. Ouverte | rég. | rien de plus |
| Taxe foncière REI | data.gouv | annuel | open data | entière | rien de plus |
| Taxe aménagement | data.gouv/bulletins | annuel | publique | entière | rien de plus |
| Cartofriches | cartofriches.cerema.fr | continu | L. Ouverte | 974 | + avancement |
| BD ORTHO 20 cm / IRC | Géoplateforme | par campagne | L.O. 2.0 | entière | rien de plus |
| INSEE RP Logement 2023 | insee.fr | 2023 | L. Ouverte | entière | rien de plus |
| Inventaire SRU | data.gouv | annuel | L. Ouverte | soumises | rien de plus |
| NPNRU | data.gouv/ANRU | ponctuel | L. Ouverte | conventionnés | rien de plus |
| PLH 5 EPCI | sites EPCI/GPU | ~6 ans | variable | selon EPCI | trou vectoriel |
| RNIC copropriétés | data.gouv (RNIC) | trimestriel | L.O. / conv.(CoproFF) | entière | + CoproFF sous conv. |
| RPLS | data.gouv / SDES | annuel | L.O. / conv.(détail) | entière | accès sous convention |
| Zonage ABC | zonage-abc.din... | selon arrêtés | L. Ouverte | entière | rien de plus |
| DVF (Etalab) | data.gouv | 07/04/2026 | L.O. (restrictions) | entière | commercial à surveiller |
| DVF Réunion (Région) | data.regionreunion.com | selon reprise | à vérifier | entière | source amont DGFiP |
| Loyers DHUP | data.gouv | annuel | L. Ouverte | à confirmer | à confirmer |
| Loyers OLL | ADIL/AGORAH | annuel | convention | 974 | sous convention |
| CoSIA | Géoplateforme | déploiement | L.O. 2.0 | à confirmer | à confirmer |
| BD CARTO V5 OCS | Géoplateforme | périodique | L.O. 2.0 | entière | rien de plus |
| ABF/MH (Mérimée) | data.culture.gouv.fr + GPU | périodique | L. Ouverte | MH 974 | + assiette SUP AC1 |
| Potentiel foncier (Région ODS) | data.regionreunion.com | n.v. | à vérifier | 974 | à instruire |
| DGFiP parcelles pers. morales | data.gouv | annuel | open data | entière | + lien SIREN |
| 50 pas géométriques (DEAL) | deal974.lizmap.com WFS | n.v. | à clarifier | littoral | meilleur endpoint |
| Classement sonore ITT | Lizmap DEAL | périodique | L.O. présumée | entière | + catégorie voie |
| SUP assiettes GPU | apicarto.ign.fr/api/gpu | selon dépôts | L. Ouverte | selon catégories | + acte/générateur |
| RTAA DOM | reunion.dev.-durable | selon arrêtés | réglementation | entière | trou de nature |
| Fibre Arcep | cartefibre.arcep.fr | trimestriel | L. Ouverte | entière | rien de plus |
| AZI/TRI (GASPAR) | Géorisques/data.gouv | v2 2020 | L. Ouverte | TRI désignés | + scénarios |
| CatNat | georisques...gaspar/catnat | continu | L. Ouverte | entière | meilleur endpoint (recouper) |
| GéoLittoral érosion | geolittoral.dev.-durable | périodique | L. Ouverte | à confirmer | à confirmer |
| DEAL PPR/aléas | deal974.lizmap.com WFS | selon PPR | à clarifier | entière | meilleur endpoint |
| DEAL cartes de bruit | reunion.dev.-durable / Lizmap | 28/03/2023 | L.O. présumée | axes >3M véh | + isophones |
| Géorisques (général) | georisques.gouv.fr/api | variable | L. Ouverte | entière | rien de plus |
| Géorisques CASIAS | georisques.gouv.fr | régulier | L. Ouverte | entière | rien de plus |
| ICPE | georisques + installationsclassees | régulier | L. Ouverte | entière | rien de plus |
| Cavités souterraines | georisques.gouv.fr | régulier | L. Ouverte | entière | rien de plus |
| Mouvements de terrain | georisques.gouv.fr | régulier | L. Ouverte | entière | rien de plus |
| SIS | reunion.gouv.fr / georisques | Ouest 2023; N-E/Sud projet | L. Ouverte | partielle | trou temporaire |
| Sites/sols pollués | georisques.gouv.fr | régulier | L. Ouverte | entière | rien de plus |
| PEB Pierrefonds | reunion.gouv.fr | 29/03/2017 | réglementation | St-Pierre | trou vectoriel |
| Ravines DPF (DEAL) | Lizmap/Carmen DEAL WFS | n.v. | à clarifier | entière | + limites DPF |
| OSM/Overpass | overpass-api.de | continu | ODbL | entière | ODbL share-alike |
| LiDAR HD MNH | cartes.gouv.fr + WFS TA | 1er DROM couvert | L.O. 2.0 | entière | meilleur endpoint |
| BD TOPO | Géoplateforme | trimestriel | L.O. 2.0 | entière | rien de plus |
| Cadastre d'époque | cadastre.data.gouv.fr | trimestriel+archives | L. Ouverte | entière | rien de plus |
| RGE ALTI | Géoplateforme | selon recampagne | L.O. 2.0 | entière | rien de plus |
| Conso espaces NAF | artificialisation.dev.-durable | annuel | L. Ouverte | entière | rien de plus |
| DEAL WMS/WFS | deal974.lizmap.com | continu | à clarifier | entière | meilleur endpoint |
| GPU DPU | apicarto.ign.fr/api/gpu info-surf | selon dépôts | L. Ouverte | ~2-4 communes carto. | trou structurel |
| GPU emplacements réservés | apicarto.ign.fr/api/gpu prescription | selon dépôts | L. Ouverte | selon PLU | meilleur endpoint |
| GPU EBC | apicarto.ign.fr/api/gpu prescription | selon dépôts | L. Ouverte | selon PLU | rien de plus |
| GPU zonages assainissement | EPCI / GPU typeinf 19 | n.v. | L.O. si au GPU | partielle/n.v. | trou producteur |
| Potentiel foncier Région | data.regionreunion.com | n.v. | à vérifier | 974 | à instruire |
| Sudocuh | data.gouv/DGALN | annuel | L. Ouverte | entière | rien de plus |
| Urbanisme PLU/GPU (API Carto) | apicarto.ign.fr/api/gpu | continu | L. Ouverte | selon docs | meilleur endpoint |
| RNB | rnb.beta.gouv.fr | continu | L. Ouverte | à confirmer | + ID-RNB (clé jointure) |
| OCS GE | Géoplateforme | déploiement | L.O. 2.0 | à confirmer | à confirmer |
| Radar (manuelle) | interne LABUSE | n/a | n/a | n/a | trou de nature |
| VRD/SPANC (manuelle) | EPCI | n/a | non ouvert | n/a | trou producteur |

*(n.v. = non vérifié)*

## Liste des sources où un MEILLEUR endpoint ou une MEILLEURE source existe
- **CatNat / AZI-TRI / PPR** → passer aux flux **API GASPAR versionnée** et **WFS DEAL** plutôt qu'à des exports datés.
- **Tout l'urbanisme (DPU, EBC, emplacements réservés, SUP, PLU)** → **API Carto GPU** (`apicarto.ign.fr/api/gpu`).
- **LiDAR HD** → **WFS tableau d'assemblage** + téléchargement Géoplateforme (au lieu de dalles manuelles).
- **Transport** → flux **PAN + GTFS-RT** (temps réel) directement.
- **DVF Réunion (Région)** → préférer la **source amont DVF Etalab/DGFiP** (plus fraîche, millésime 07/04/2026).
- **DPE ADEME** → construire un **filtre par code INSEE 974xx** au lieu du filtre département/code postal.
- **Aléas/zones humides/ENS/50 pas/ravines/endiguement/hypsométrie** → **WFS DEAL EPSG:2975** au lieu de PDF.
- **Recherche d'entreprises DINUM** → meilleur agrégateur pour recouper SIRENE/RNE.
- **BAN** → **BAN PLUS** pour le lien adresse↔bâtiment.

## Liste des CHAMPS supplémentaires utiles, source par source
- **AZI/TRI** : scénarios d'inondation fréquent/moyen/extrême.
- **Cartes de bruit / classement sonore** : isophones Lden/Ln vectorielles ; catégorie sonore (1-5) et largeur du secteur affecté.
- **SUP GPU** : acte + générateur de servitude (en plus de l'assiette).
- **Emplacements réservés GPU** : bénéficiaire.
- **Cartofriches** : état d'avancement de la reconversion.
- **RNIC/CoproFF** : copropriétés non immatriculées et indicateurs de fragilité (sous convention).
- **RPLS** : date et classe DPE du logement social.
- **DGFiP parcelles personnes morales** : lien parcelle↔SIREN.
- **DFI** : filiation parcellaire (mère/fille), historique.
- **BAN PLUS** : lien adresse↔bâtiment (surface, hauteur, nature).
- **RNB** : ID-RNB comme clé de jointure inter-bases (DPE, RPLS, BAN).
- **BD TOPO** : hauteur des bâtiments.
- **INPI RNE** : dirigeants (selon droits d'accès).
- **Trafic RN** : TMJA par tronçon.
- **Ravines DPF** : limites du Domaine Public Fluvial.
- **DEAL ENS** : couche `ms:ENS` (espaces naturels sensibles du Département).
- **ABF/MH** : assiette SUP AC1 (périmètre de protection) via API Carto.

## Liste des TROUS indépassables chez le producteur (avec phrase honnête à afficher)
- **DPU (20+ communes)** : « Droit de préemption urbain : le périmètre exact n'est cartographié que pour Saint-Pierre et Saint-Benoît ; ailleurs, un DPU s'applique très probablement en zones U/AU (l'EPF Réunion en est délégataire pour plus de 80 % des communes) mais son périmètre n'est pas publié — vérifier en mairie ou auprès de l'EPF Réunion. »
- **SIS Nord-Est et Sud** : « Secteurs d'information sur les sols : arrêtés pour l'Ouest (2023) ; Nord-Est et Sud en projet, non opposables (consultation close le 7 mai 2026). »
- **Zonages d'assainissement** : « Zonage d'assainissement : détenu par l'intercommunalité compétente depuis 2020, non disponible en open data — se référer à l'EPCI. »
- **PEB Pierrefonds** : « PEB de Pierrefonds : arrêté du 29/03/2017, disponible en plan PDF ; contour vectoriel à vérifier via l'annexe SUP du PLU de Saint-Pierre. »
- **PLH des 5 EPCI / OLL loyers / Chroniques de l'eau** : « Donnée disponible uniquement en document PDF chez le producteur ; pas de version structurée exploitable. »
- **RTAA DOM / VRD-SPANC / Radar** : « Élément réglementaire ou source sans producteur de données public unique — pas de jeu de données à exploiter. »

## Liste des sources dont la réutilisation commerciale est INCERTAINE ou INTERDITE/CONDITIONNÉE
- **DVF** : commercial autorisé mais **interdiction de ré-identification indirecte et d'indexation par moteurs de recherche externes** (R112 A-3 LPF).
- **OSM / Overpass / BANO** : **ODbL** — commercial autorisé mais **partage à l'identique + attribution** (risque de contamination de licence).
- **Couches DEAL Lizmap** (PPR/aléas, zones humides, ENS, 50 pas, ravines, endiguement, hypsométrie, bruit) : **licence non écrite explicitement — à faire confirmer par la DEAL**.
- **Conservatoire du littoral** : **licence à établir textuellement — non vérifiée**.
- **ONF (forêts publiques)**, **EDF Réunion HTA**, **Parc national** : **licences à confirmer**.
- **RPLS détaillé, CoproFF, OLL loyers** : **accès sous convention/ayants droit** (usage encadré).
- **INPI RNE** : conditions INPI spécifiques selon les données (bénéficiaires effectifs restreints).
- **Trafic RN Région, DVF Région, Potentiel foncier Région, Loyers DHUP, CoSIA, OCS GE 974** : licence/couverture **à vérifier** avant usage commercial.

## Points d'attention spécifiques — traités en profondeur
- **DPU commune par commune** : voir fiche « GPU DPU ». Confirmés : Saint-Pierre (simple + renforcé, délégation EPF, conv. 16 24 01, 21/10/2024) et Saint-Benoît (périmètre ajusté au PLU 2020, portage EPF). PLU au GPU (annexe présumée) : Saint-Paul, Saint-Leu. 20 communes non vérifiées individuellement, mais **l'EPF Réunion détient la délégation du DPU pour plus de 80 % des communes (10 000 ha sur 26 000 ha urbains)** — le DPU existe donc quasi partout sans être cartographié. Source la plus efficace pour recenser : délibérations du conseil d'administration de l'EPF Réunion (`epf.re`). Endpoint technique : API Carto `info-surf`, `TYPEINF=04` (03 pour anciens dépôts).
- **SIS** : Ouest arrêté (2023) ; Nord-Est et Sud en projet (arrêté n°2026-218 du 19/02/2026, modifié le 02/04/2026 ; consultation 7 avril–7 mai 2026) sur Le Port, Saint-Paul, Saint-Louis, Saint-Pierre, La Plaine-des-Palmistes. Fichiers ZIP sur reunion.gouv.fr ; Géorisques ne publie que le définitif (CSV quotidien).
- **PEB Pierrefonds** : arrêté du 29/03/2017, PDF au 1/25 000 ; communes/EPCI concernés Saint-Pierre, CIVIS, CASUD ; vectoriel à chercher via Géoportail PEB ou annexe SUP T5 du PLU de Saint-Pierre au GPU.
- **Zonages d'assainissement** : détenus par les 5 EPCI depuis 2020 ; aucune publication open data confirmée (ni Opendatasoft régional, ni PEIGEO, ni GPU typeinf 19) ; la CINOR a un zonage EU (avis MRAe) mais non ouvert.
- **GPU état des 24 communes** : Saint-Paul (PLU exécutoire depuis 2012, au GPU), Saint-Leu (PLU au GPU, **révision en enquête publique 1er sept–9 oct 2026**), Saint-Benoît (PLU 06/02/2020), Saint-Pierre (PLU + SUP). Saint-André et Saint-Leu signalés comme ayant connu des difficultés de publication ; **quand le GPU ne sert pas le règlement opposable, la version opposable reste celle détenue en mairie/EPCI** — récupérer via l'endpoint `download-by-partition` du GPU ou directement en mairie. Détection de procédure : module `procedure` de l'API GPU.
- **DPE ADEME** : filtre 974 défaillant ; corriger par code INSEE commune ; volume réel à confirmer.
- **LiDAR HD** : La Réunion premier DROM couvert ; MNT/MNS/MNH disponibles, nuages ajoutés ; date de survol exacte à confirmer (dalles datées 2025) ; licence Etalab 2.0.
- **SUP GPU** : documenter catégorie par catégorie ce que chaque gestionnaire a déposé (I4, PT, AC1, T5…) et ce qui manque.
- **Cartes de bruit 4e échéance** (28/03/2023) et **classement sonore** : servis sur Lizmap DEAL, à consommer en WFS quand disponible.
- **Zones humides / ENS (`ms:ENS`) / Conservatoire du littoral** : couches DEAL/Département à récupérer en WFS ; licences à faire écrire par les producteurs.
- **Sources candidates** : systèmes d'endiguement et zones protégées (DEAL Lizmap), carte hypsométrique du littoral (DEAL), révision du PLU de Saint-Leu — toutes trois instruites ci-dessus et recommandées à l'intégration.

## Caveats
- Sources marquées **« à confirmer / non vérifié »** faute de vérification directe aboutie : couverture 974 de GéoLittoral érosion, Loyers DHUP, CoSIA, OCS GE (millésime/dispo 974), complétude RNB 974, date de survol LiDAR HD exacte, licences DEAL/Conservatoire/ONF/EDF/Parc national/Trafic RN Région/DVF Région/Potentiel foncier Région, volume réel DPE 974 après filtrage correct. À instruire avant mise en production.
- **Risque d'homonymie majeur** (Saint-Denis 974 vs 93 ; Saint-André, Saint-Leu, Saint-Louis, Saint-Priest métropolitains) : toute automatisation de collecte de délibérations doit filtrer sur le code INSEE 974xx.
- Pour le **DPU**, l'absence de périmètre au GPU **ne signifie jamais** absence de DPU : ne jamais afficher « pas de DPU » mais « périmètre non publié ».
- **Bug de complétude de l'API CatNat** : recouper systématiquement avec l'export CSV national.
- Les **codes INSEE communaux** issus du travail de recherche sont indicatifs (ex. Bras-Panon à revérifier).
- **Aucune donnée n'a été obtenue par scraping** : toutes les recommandations reposent sur API, fichiers officiels, flux WFS/WMS/WMTS et téléchargements officiels, conformément à la contrainte du fondateur.
- Recommandation de gouvernance : mettre en place un registre interne « source → endpoint → licence confirmée → date de dernière ingestion → méthode de détection de version » pour tenir l'objectif « impeccable » dans le temps.