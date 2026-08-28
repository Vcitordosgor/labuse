# ÉTUDE DE ZONE · Z5 — Recette

Chaque cas du mandat, son résultat et sa **preuve** (test gelé). Suite dédiée :
`tests/test_zone_ingestion.py`, `tests/test_zone_moteur.py`, `tests/test_zone_recette.py` (17 tests, 0 échec).

## Scénarios nominaux

| Scénario | Résultat | Preuve |
|---|---|---|
| Parcelle centre-ville (isochrone à pied 15 / voiture 5) | Zone tracée, population + équipements avec temps | `test_endpoint_parcelle_zone_revenu_source_unique` |
| Parcelle des hauts / adresse / point | Même moteur, entrée point (lon/lat) ou idu | endpoint `POST /outils/etude-zone` (idu \| lon/lat \| geom) |
| Polygone dessiné | Court-circuite l'isochrone, compte dans le polygone | `etude_de_zone(geom_geojson=…)` — statut `polygone` |
| Deux activités (boulangerie 1071C, coiffure 9602A) | Concurrents SIRENE par NAF, chacun avec son temps | `test_endpoint_etude_zone_concurrents_et_ratio`, `test_naf_sans_concurrent_reste_digne` |
| Export PDF (écran 3) | A4 sourcé, revenu ESTIMÉ, aucune prévision de CA | `test_pdf_rendu_depuis_l_agregat` + artefact `captures/etude-zone-exemple.pdf` |

## Cas limites (doctrine)

| Cas | Comportement | Preuve |
|---|---|---|
| Zone océan / inhabitée | « Zone peu ou pas habitée », aucun chiffre inventé | `test_population_zone_inhabitee_reste_digne` |
| Carreaux imputés | Revenu **toujours** marqué ESTIMÉ (INSEE lissé) | `test_population_zone_point_unique_filosofi` (`revenu_estime=True`) |
| Échec API IGN | Statut `indisponible`, **aucune géométrie** — jamais un cercle | `test_isochrone_echec_api_degrade_honnete_jamais_un_cercle`, `test_endpoint_parcelle_zone_degrade_honnete` |
| PDF sur zone indisponible | 422, pas de rapport vide | `test_pdf_zone_indisponible_pas_de_rapport` |
| NAF sans concurrent | `n=0`, pas de ratio inventé | `test_naf_sans_concurrent_reste_digne` |
| Adresse introuvable (/flash) | Message honnête, jamais un 500 | `test_flash_adresse_introuvable_dit_honnete` |
| SIRENE non diffusible | Nom et adresse masqués, NAF conservé | `test_sirene_diffusion_partielle_masque_nom_et_adresse` |

## Parcours /flash par adresse

Un commerçant a une **adresse**, pas un IDU : le formulaire `/flash` propose désormais l'adresse
(BAN → parcelle contenant le point) **et** l'IDU. Preuve : `test_flash_par_adresse_trouve_la_parcelle`.
_L'intégration de la section « zone » au PDF Flash lui-même est le **mandat suivant** (noté)._

## Choix « un seul point de calcul Filosofi »

Le tiroir fiche affiche habitants / ménages / % < 25 **de la zone**, mais le **revenu** reste la valeur
au centroïde déjà servie par la fiche (`marche_secteur.filosofi_200m`) — jamais deux revenus divergents
à l'écran. Preuve : `test_endpoint_parcelle_zone_revenu_source_unique` (`revenu_source` = « carreau au
centroïde »).

## Choix « zéro doublon » (décision 02 maquette)

Le bloc apporte les **équipements & commerces en TEMPS** (BPE). Les ventes DVF, transports et réseaux
**restent** dans leurs tiroirs « Marché » et « Réseaux » (le bloc porte le renvoi, pas une copie). Aucun
bloc « proximités en mètres » n'est dupliqué : le transport reste en distance dans « Réseaux ».

## Choix mobile 390

Le tiroir fiche (`AutourZoneBlock`) et l'outil (`EtudeZone`) sont **tous deux** utilisables à 390 px :
segments et stats en `grid-cols-2` pleine largeur, listes en colonne, aucun tableau à défilement
horizontal. Le tiroir vit dans la fiche (déjà responsive) ; l'outil dans le panneau Outils (320 px).

## Captures

- **1 capture concrète livrée** : `docs/ZONE/captures/etude-zone-exemple.pdf` — le rapport (écran 3)
  rendu par la **vraie chaîne fpdf2** (40 Ko, en-tête `%PDF`), valeurs de la maquette.
- Les captures UI des écrans 1 & 2 en **happy-path** (isochrones tracées) exigent le **réseau IGN
  Géoplateforme** (indisponible hors ligne) **et** le rideau d'authentification de l'app — elles sont
  une étape de recette **post-merge** (comme la vision LIVE de Radar P1). L'état **dégradé honnête**
  (« zone indisponible, aucun cercle ») est, lui, ce qui s'affiche sans IGN. Les comportements des trois
  écrans sont **gelés par les 17 tests** ci-dessus.
