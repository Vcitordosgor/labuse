# ORACLE-1 — consignes sous-agent « une parcelle »

Tu audites UNE parcelle de LABUSE contre les sources publiques (Lot B) et tu la relis comme un promoteur (Lot C). Lecture seule absolue : aucune écriture en base, aucun fichier hors `docs/audit-2026-09/ORACLE-1/`. La base PostgreSQL `postgresql://openclaw@localhost:5432/labuse` n'est utilisable qu'en SELECT et uniquement pour retrouver une référence LABUSE (ex. `source_url` d'un règlement) — jamais comme « source publique ».

## Entrées
- `docs/audit-2026-09/ORACLE-1/dossiers/{SLOT}_{IDU}.json` — fiche servie (72 clés : surface_m2, adresse, coords [lon,lat], reglement_plu.zones, aleas, sols, catnat, dvf_parcelle, prix_ancien, le_bien, depots, historique_site, etablissements, proprietaire_moral, filiation, viabilisation, dispositifs, territoire_fiscal, taxe_amenagement, iris_quartier…)
- `…_enrichment.json` (altimétrie min/max/mean, exposition, pente), `…_zone.json`
- `…{SLOT}_{IDU}.txt` — texte du Dossier PDF (pdftotext -layout) ; le PDF lui-même est à côté.
- Cache DVF Etalab : `/tmp/oracle1/dvf/dvf_974_{2022..2025}.csv` (colonnes id_parcelle, date_mutation, valeur_fonciere, type_local, surface_reelle_bati, surface_terrain, latitude, longitude…)
- Règlements PLU : `/Users/openclaw/Desktop/labuse/data/plu_reglements/` (le nom du document est dans `reglement_plu.zones[].destinations.document` ou `…articles[].document` ; l'URL publique est dans la table `plu_reglement_extrait.source_url`).

## Lot B — notions à vérifier (chacune = 1 ligne CSV)
Pour CHAQUE notion ci-dessous qui apparaît dans la fiche ou le Dossier : relève la valeur LABUSE, interroge la source publique, compare avec la tolérance, tranche.

| notion | valeur LABUSE (où) | source publique (comment) | tolérance |
|---|---|---|---|
| zone_plu | reglement_plu.zones / PDF | GPU : `https://apicarto.ign.fr/api/gpu/zone-urba?geom={"type":"Point","coordinates":[lon,lat]}` (libelle, typezone) ; si à cheval, GET avec la géométrie parcelle (apicarto cadastre) | identité |
| doc_urbanisme_date | reglement_plu.zones[].approbation (nom du doc GPU, date) | GPU `document` du même appel (partition, datappro) | identité |
| prescriptions (ER/EBC/OAP) | dispositifs / PDF | GPU `https://apicarto.ign.fr/api/gpu/prescription-surf?geom=…` (+ -lin, -pct) | identité |
| sup | dispositifs / gabarit | GPU `assiette-sup-s?geom=…` (+ -l, -p) | identité |
| ppr_zonage | aleas / PDF | Géorisques `https://www.georisques.gouv.fr/api/v1/rapport_pdf` NON — utiliser `https://www.georisques.gouv.fr/api/v1/resultats_rapport_risque?latlon=lon,lat` (sections pprn : zonage, aléas, date d'approbation) | identité |
| catnat_n | catnat | `…/api/v1/gaspar/catnat?code_insee=XXXXX&page_size=100` (compte + derniers arrêtés) | 0 entier |
| icpe | sols / risques | `…/api/v1/installations_classees?latlon=lon,lat&rayon=1000` (existence + distance) | identité/50 m |
| cavites | risques | `…/api/v1/cavites?latlon=lon,lat&rayon=500` | identité |
| argiles_rga | risques / PDF | `…/api/v1/rga?latlon=lon,lat` (exposition) | identité |
| sismicite | risques / PDF | `…/api/v1/zonage_sismique?latlon=lon,lat` | identité |
| radon | risques / PDF | `…/api/v1/radon?code_insee=XXXXX` | identité |
| sis | sols | `…/api/v1/ssp?latlon=…` ou `…/api/v1/sis?latlon=lon,lat&rayon=500` | identité |
| surface_cadastre_m2 | surface_m2 | API Carto cadastre : `https://apicarto.ign.fr/api/cadastre/parcelle?code_insee=XXXXX&section=SS&numero=NNNN` → properties.contenance | 1 % |
| section_numero | idu | même appel (existence de la parcelle) | identité |
| dvf_parcelle | dvf_parcelle (liste) | grep id_parcelle dans /tmp/oracle1/dvf/*.csv (dates, valeurs, type) | identité |
| dvf_mediane_secteur | prix_ancien.median (+ radius_m, type_prix, periode) | recalcul depuis les CSV : mutations du même type dans le rayon autour de coords (haversine), €/m² médian sur la même période | 1 % (au-delà, expliquer la méthode) |
| permis_parcelle | depots / historique_site | Sitadel open data — best effort : si l'API DIDO/SDES répond, comparer par commune×mois ; sinon verdict non_verifiable (dire pourquoi) | 0 entier |
| etablissements_sirene | etablissements (siret) | `https://recherche-entreprises.api.gouv.fr/search?q=SIRET` (état, adresse) | identité |
| proprietaire_pm | proprietaire_moral (denomination, siren) | fichiers PM DGFiP data.economie.gouv (API ODS `fichier-des-parcelles-des-personnes-morales…`) — best effort, sinon croiser le SIREN via recherche-entreprises | identité |
| adresse_ban | adresse | `https://api-adresse.data.gouv.fr/reverse/?lon=…&lat=…` (label le plus proche) | identité (juger la proximité) |
| altitude | enrichment.altimetrie (min/max/mean) | `https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json?lon=…&lat=…&resource=ign_rge_alti_wld&zonly=true` sur 3-5 points de la parcelle | ±2 m (échantillonnage) |
| pente_pct | enrichment.exposition.pente_locale_pct / PDF | 2 appels alti espacés (gradient) — ordre de grandeur, ±2 points | 2 points |
| batiments_n_hauteur | le_bien (n bâtiments, hauteur) | RNB `https://rnb-api.beta.gouv.fr/api/alpha/buildings/?bb=lat_min,lon_min,lat_max,lon_max` (compte) ; hauteur : WFS IGN `https://data.geopf.fr/wfs/ows?SERVICE=WFS&REQUEST=GetFeature&TYPENAME=BDTOPO_V3:batiment&BBOX=…` (attribut hauteur) | 0 entier / 1 % |
| insee_population | contexte commune du PDF (si affiché) | INSEE Melodi `https://api.insee.fr/melodi/data/DS_POPULATIONS_REFERENCE?GEO=COM-XXXXX&maxResult=20` | 0 entier |
| regles_plu_chiffrees | reglement_plu.zones[].articles + gabarit (hauteur, emprise, reculs, pleine terre, stationnement, mixité) — TOUTES les règles chiffrées affichées | ouvrir le PDF du règlement local à la page citée (`page_pdf` via SELECT sur plu_reglement_extrait, ou page dans la fiche) et vérifier le chiffre exact ; citer page + verbatim court | identité |

Notions absentes de la fiche : ne pas inventer de ligne « absent » en Lot B (c'est le Lot C qui les capte) — sauf si le Dossier PDF affiche une valeur que le JSON n'a pas.

## Sortie Lot B
Fichier `docs/audit-2026-09/ORACLE-1/verite_parts/{SLOT}.csv`, EXACTEMENT cet en-tête :
```
idu;slot;notion;valeur_labuse;valeur_source;service;url;page;ecart;verdict;pourquoi
```
- `verdict` ∈ `vrai` / `faux` / `non_verifiable`.
- `url` = l'URL EXACTE interrogée (obligatoire pour vrai et faux ; pour non_verifiable, l'URL tentée).
- `pourquoi` obligatoire pour faux et non_verifiable. Valeurs avec `;` → remplacer par `,`.
- Un FAUX doit être béton : re-vérifie une 2e fois avant de l'écrire (une requête refaite, une relecture de la fiche — les erreurs d'attribution d'agent existent).

## Lot C — lecture promoteur
Relis le Dossier PDF (le .txt) comme un promoteur qui décide d'appeler ou non le propriétaire. Pour les 6 questions :
1. Puis-je construire, quoi, combien, à quelle hauteur — qu'est-ce qui pourrait l'interdire (PPR, SUP, AU, ER, ABF, EBC, mixité) ?
2. Puis-je accéder, raccorder, évacuer (voirie, eau, élec, assainissement) — avec quel degré de certitude ?
3. Qu'est-ce que ça vaut, se vend autour, rapporterait ?
4. À qui appartient-elle, depuis quand, signal de vente ?
5. Coûts cachés (taxes, dépollution, terrassement, archéologie, bruit) ?
6. Que dois-je aller chercher ailleurs après cette fiche ?

Fichier `docs/audit-2026-09/ORACLE-1/lecture_parts/{SLOT}.csv` :
```
idu;slot;question;statut;preuve
```
- `statut` ∈ `repondu_clair` / `repondu_incomplet` / `pas_clair` / `absent`.
- `preuve` = la phrase du Dossier qui répond (verbatim court) OU le vide constaté (« rien sur X »). Q6 : liste ce qui manque.

## Rendu final (ton dernier message)
Un JSON compact : `{"slot":"SXX","verite_rows":N,"faux":N,"non_verifiable":N,"faux_liste":["notion: résumé 1 ligne"...],"lecture":{"Q1":"statut",…},"alertes":"anomalies inattendues vues en passant"}`
