# REPARATIONS-1 lot 3 — Couverture incomplète : le trou est chez qui, et l'app le dit

13 sources « PARTIELLE — couverture incomplète » (SOURCES-AUDIT-1), instruites une à une.
La note client est SERVIE (colonne `data_sources.couverture_note`, page Sources).

## 15 — data.regionreunion.com — Potentiel foncier (`potentiel_foncier_ods`)
- **Trou : chez NOUS** — Écart non mesuré (objets producteur « non vérifié », 2 453 en base vs 4 906 sur les couches potentiel_foncier+sar), millésime absent, doublon id 9 non tranché : c'est l'instruction côté LABUSE qui est incomplète, rien n'indique que le producteur retienne des données.
- **Note servie** : Couche d'orientation issue du jeu « potentiel foncier » de la Région Réunion, à la maille îlot/zone (pas à la parcelle). Le millésime et l'exhaustivité de notre copie sont en cours de vérification.
- **Réingestion possible** : Rejouer l'ingestion ODS (endpoint /catalog/datasets/potentiel-foncier/records) vers spatial_layers avec millésime, après avoir tranché le doublon avec id 9.

## 44 — SUP — assiettes GPU (API Carto) (`sup_gpu`)
- **Trou : chez le PRODUCTEUR** — La fiche le dit : « Couverture bornée par la publication GPU, pas par nous » — 9 catégories en vigueur, T5/PT1/PT2 restreintes, AS1 (captages) non publiée au GPU.
- **Note servie** : Servitudes d'utilité publique telles que publiées au Géoportail de l'urbanisme : 9 catégories en vigueur à La Réunion, certaines restreintes (T5, PT1, PT2). Les périmètres de protection de captage (AS1) ne sont pas publiés au GPU et n'apparaissent donc pas ici.

## 45 — Recherche d'entreprises (DINUM) (`recherche_entreprises_dinum`)
- **Trou : chez NOUS** — L'API producteur couvre toutes les personnes morales ; notre couverture est un cache d'enrichissement partiel (9 730 enrichissements, 2 650 dénominations) rempli au fil des consultations.
- **Note servie** : Identification des propriétaires personnes morales via l'API Recherche d'entreprises (Sirene/RNE). L'enrichissement se fait au fil de l'eau : environ 9 700 propriétaires déjà enrichis, les autres sont complétés à la demande.
- **Réingestion possible** : Batch d'enrichissement sur les propriétaires non couverts via https://recherche-entreprises.api.gouv.fr/search vers owner_enrichment/owner_denom_lookup (sous réserve du retrait en attente, lecteurs score_v/facettes/scan encore branchés).

## 63 — GPU — zonages d'assainissement (`gpu_zonage_assainissement`)
- **Trou : chez le PRODUCTEUR** — Seules 4 communes sur 24 ont téléversé leur zonage d'assainissement au format SIG sur le GPU (constat du 11/07/2026) ; les 20 autres sont « à demander » aux collectivités (id 134).
- **Note servie** : Zonages d'assainissement issus du Géoportail de l'urbanisme : seules 4 communes sur 24 y ont publié leur plan au format SIG (juillet 2026). Pour les 20 autres, l'information n'est pas disponible auprès du producteur et doit être demandée aux collectivités.

## 68 — Office de l'eau Réunion — Chroniques de l'eau (`office_eau_chroniques`)
- **Trou : chez NOUS** — Couverture 6/24 communes : seed CSV manuel limité aux 6 communes 100 % ANC, alors que la Chronique de l'eau du producteur porte sur toute l'île (les chroniques quantitatives sont explicitement « non exploitées »).
- **Note servie** : Statut d'assainissement non collectif renseigné pour les 6 communes entièrement en ANC (Chronique de l'eau n°149, données 2023). Les 18 autres communes ne sont pas couvertes par cette source dans l'application.
- **Réingestion possible** : Étendre le seed CSV (dépôt manuel depuis la Chronique de l'eau) aux autres communes dans anc_office_eau_commune — sous réserve du retrait en attente (anc_service.py lit encore la table).

## 69 — BD ORTHO IRC (IGN) (`bd_ortho_irc`)
- **Trou : chez NOUS** — Le WMS IGN couvre l'île entière et parcel_vegetation touche bien les 431 663 parcelles, mais le dérivé est un one_shot sans millésime en base et le filtre est KO : la fraîcheur/traçabilité de notre copie est le trou, pas la publication IGN.
- **Note servie** : Végétation et ombrage dérivés de l'infrarouge IGN (BD ORTHO IRC), calculés une fois sur l'ensemble des 431 663 parcelles de l'île. Le millésime de la prise de vue servie n'est pas garanti à jour.
- **Réingestion possible** : Rejouer le calcul NDVI/canopée depuis le WMS ORTHOIMAGERY.ORTHOPHOTOS.IRC vers parcel_vegetation/vegetation_zonal_acc en embarquant le millésime, et réparer le filtre (KO).

## 70 — LiDAR HD — MNH 50 cm (IGN) (`lidar_hd_mnh`)
- **Trou : chez NOUS** — Le batch de dalles est ACHEVÉ (2 665/2 665, hauteur sur 303 452 parcelles ~70 %, le reste sans bâti mesuré) ; le vrai retard est chez nous : le verdict de toiture (toiture_lidar) n'est calculé que sur 27 parcelles et la provenance crédite bd_topo au lieu de lidar_hd_mnh.
- **Note servie** : Hauteurs de bâti mesurées au LiDAR HD de l'IGN (faîtage et égout) sur 303 452 parcelles, soit environ 70 % de l'île — le reste correspond à des parcelles sans bâti mesuré. L'analyse détaillée de la toiture (pente, forme) n'est pour l'instant calculée que sur un échantillon.
- **Réingestion possible** : Étendre le batch toiture_lidar (pente/forme) à la couverture de batiment_hauteur_lidar (303 452 parcelles) et rattacher lidar_hd_mnh à marge_surelevation_m/hauteur_bati_m dans le registre de provenance.

## 107 — GPU — droit de préemption urbain (info-surf) (`dpu_perimetres`)
- **Trou : chez le PRODUCTEUR** — Seules 4 communes sur 24 ont publié leur DPU au GPU (constat du 06/09/2026) ; les 20 autres sont à demander aux communes/EPCI (délibérations non téléversées).
- **Note servie** : Périmètres de droit de préemption urbain publiés au Géoportail de l'urbanisme par 4 communes sur 24 (septembre 2026). Pour les 20 autres, l'absence d'affichage ne signifie pas l'absence de DPU : la commune ne l'a simplement pas publié.

## 108 — PEB — plans d'exposition au bruit (DGAC via annexes GPU) (`peb_dgac`)
- **Trou : chez le PRODUCTEUR** — Le PEB de Roland-Garros (zones B/C/D) est publié via les annexes GPU, mais celui de Pierrefonds n'est pas publié par la DGAC/DEAL — trou connu au sud, à demander.
- **Note servie** : Plan d'exposition au bruit de l'aéroport Roland-Garros (zones B, C, D), via le Géoportail de l'urbanisme. Le PEB de l'aéroport de Pierrefonds n'est pas publié par la DGAC : le sud de l'île n'est pas couvert.

## 112 — Zones humides — inventaires DEAL (Carmen) (`deal_zones_humides`)
- **Trou : chez le PRODUCTEUR** — La fiche le dit : inventaires 2003/2009/2011/2019 menés par secteurs, « partiels par construction (le producteur n'a pas inventorié toute l'île) ».
- **Note servie** : Inventaires des zones humides de la DEAL Réunion (campagnes 2003, 2009, 2011 et 2019), réalisés par secteurs : toute l'île n'a pas été inventoriée. Une parcelle hors inventaire n'est donc pas garantie sans zone humide.

## 115 — Géorisques — secteurs d'information sur les sols (SIS) (`georisques_sis`)
- **Trou : chez le PRODUCTEUR** — La fiche le dit : « 4 SIS 974 seulement (c'est la réalité du producteur, pas un manque LABUSE) ».
- **Note servie** : Secteurs d'information sur les sols recensés par Géorisques : 4 secteurs existent à ce jour à La Réunion. Ce faible nombre reflète le recensement officiel, pas une donnée manquante dans l'application.

## 117 — DEAL — cartes de bruit stratégiques (CBS) (`deal_bruit_cartes`)
- **Trou : chez le PRODUCTEUR** — La fiche le dit : CBS 2022, « 6 zones de dépassement seulement (échéance 4, RN/RD/VC). Partiel par construction » — le producteur ne publie que les dépassements le long des grands axes.
- **Note servie** : Cartes de bruit stratégiques de la DEAL (2022) : seules les zones de dépassement des seuils réglementaires le long des routes nationales, départementales et voies communales sont publiées (6 zones). Ce n'est pas une carte du bruit sur toute l'île.

## 128 — ACV / PVD / ORT (DGALN — liste des communes) (`anct_ort`)
- **Trou : chez le PRODUCTEUR** — La table DGALN vivante ne publie que l'éligibilité COMMUNALE (19 communes 974, 13 ORT signées) ; le périmètre ORT infra-communal utile pour Denormandie n'est pas publié (source à part, id 138 à demander).
- **Note servie** : Éligibilité ORT / Action cœur de ville / Petites villes de demain à l'échelle de la commune : 19 communes concernées, dont 13 ORT signées (table DGALN). Les périmètres précis à l'intérieur des communes (déterminants pour Denormandie) ne sont pas publiés par la DGALN.

### Réingestions « chez nous » non faites dans ce mandat (écrites, avec leur raison)
- **45 DINUM**, **68 Office de l'eau**, **69 BD ORTHO IRC** : ces trois sources sont sous RETRAIT EN ATTENTE (REPARATIONS.md §C — le lecteur vivant doit d'abord être coupé ou la fonction assumée, mandats C1/C2/C4). Compléter leur couverture maintenant contredirait le retrait décidé : on dit la couverture réelle, on ne l'étend pas avant l'arbitrage.
- **15 Potentiel foncier Région** : doublon 9↔15 à trancher (B1, geste de Vic) et licence à confirmer — instruire la couverture d'abord, réingérer ensuite.
- **70 LiDAR HD** : la hauteur est complète (303 452 parcelles, le reste est sans bâti) ; le retard réel est le VERDICT de toiture (27 parcelles) = batch de calcul dédié, mandat à part.