# Étude de zone

Clé interne : `etude-zone` (num M27) · composant : `frontend/src/components/outils/EtudeZone.tsx` · endpoint(s) : `POST /outils/etude-zone` (lecture principale), `POST /outils/etude-zone/entreprises` (liste des entreprises à la demande), `GET /etude-zone.pdf` (export), `GET /moteurs/config` (liste des rayons).

> Note de méthode : le brief annonce un backend sur `http://127.0.0.1:7300`. Ce port ne répondait pas pendant l'audit (`curl` → code 000, aucun process). Les sorties « rejouées » ci-dessous ont été obtenues sur l'instance LABUSE réellement en marche, `http://127.0.0.1:9810` (même code, même base Postgres `labuse` locale). Les requêtes `psql` (table `data_sources`) et la lecture du code (zone.py, app.py) complètent.

---

## 1. À quoi il sert, et pour qui
L'Étude de zone décrit tout ce que la donnée publique sait d'un **périmètre autour d'une parcelle** (un cercle de rayon réglable) : qui y vit, qui y travaille, le marché immobilier, les contraintes PLU/risques, les équipements, la dynamique foncière. C'est l'outil de **chalandise / contexte de quartier** pour un porteur de projet (implanter une activité, apprécier l'environnement d'un bien) — faits sourcés et datés, **aucune prévision de chiffre d'affaires**.

## 2. Le parcours
Un seul chemin, en deux étapes dans le panneau de gauche (`EtudeZone.tsx:168-561`) :

- **Étape 1 « Définir la zone »** — l'utilisateur saisit une **parcelle** (adresse, IDU ou référence courte via `ParcelInput`, `EtudeZone.tsx:176-177`) puis choisit un **rayon** parmi les boutons servis `0,5 / 1 / 2 / 5 km` (`EtudeZone.tsx:181-190`, rayons venant de `/moteurs/config`, `:75-76`). Bouton **« Lire la zone »** (`:198-202`).
- **Étape 2 « Lire la zone »** — s'ouvre d'elle-même après le clic (le bouton disparaît, `:197-202`). Résultat en **7 sections repliables** (toutes fermées par défaut, `:160`) : **Population**, **Économie**, **Immobilier**, **Foncier**, **Contraintes**, **Équipements**, **Dynamique** (`:220-538`). Dans Économie, un sous-bouton **« Toutes les entreprises de la zone »** (`:262-266`) déclenche l'appel `…/entreprises` (groupées par famille d'activité, paginées par 200). En bas, **« Exporter en PDF »** (`:546-554`) ouvre le même document que la carte Docs « Étude de zone ».

Le menu « Activité (destination) » et la lentille « concurrents » ont été **retirés de l'UI** (RECETTE-4, `:192-194` / RECETTE-OUTILS-1 `:540-541`) ; le back les accepte encore (`naf`, `sous_destination`) mais le front ne les envoie plus (`:100`). Le centre réel du périmètre est le **centroïde** de la parcelle (`app.py:7922-7927`), pas forcément le cœur du bâti.

## 3. Les données lues
Mises à jour : nom dans `data_sources` → table SQL réellement lue → millésime servi (relevé `psql` + catalogue) → cadence.

| Rubrique | Source (catalogue) | Table SQL lue | Millésime servi | Cadence |
|---|---|---|---|---|
| Habitants, ménages, niveau de vie | Filosofi INSEE (carreaux 200 m) | `filosofi_carreaux_200m` (`zone.py:176`) | millésime 2021 | (non renseignée) |
| Structure d'âge, vacance/âge bâti | INSEE RP2022 — bases IRIS | `iris_rp` + `spatial_layers` (iris) (`zone.py:206-208`, `age_structure_zone`) | RP2022, parution 16/10/2025 (géo 01/01/2024) | — |
| Emplois (fourchette) + toutes entreprises | SIRENE établissements géolocalisés | `sirene_etablissements` (`zone.py:254`, `entreprises_zone`) | SIRENE géolocalisé **2026-09** (millésime réel renvoyé, `app.py:1087-1090`) | mensuelle |
| Ventes 12 mois + médian €/m² bâti | DVF / valeurs foncières | `dvf_mutations` + `dvf_mediane.mediane_bati` (`zone.py:454-463`) | Etalab millésime 2026-S1 | semestriel |
| Permis 36 mois | SITADEL | `sitadel_permits` (`zone.py:469-473`) | 2026-08 | mensuelle |
| Annonces actives | Radar (pige d'annonces) | `pige_biens` ⨝ `parcels` (`zone.py:464-468`) | collecte manuelle, **partielle** | quotidien |
| Équipements par domaine A→G | BPE INSEE | `spatial_layers` (kind=`amenite_bpe`) (`zone.py:886-892`) | millésime 2025 | — |
| Trafic routes nationales | Trafic RN (Région Réunion) | `trafic_rn` (`zone.py:491-497`) | millésime porté par tronçon | — |
| Fibre FttH | Fibre Arcep | `arcep_immeubles` (`app.py:2008-2015`) | 2026_T1 | — |
| Zones PLU / risques / assainissement / espaces | PLU GPU · DEAL · INPN/ANCT | couches `spatial_layers` et tables dédiées (`zone.py:505-868`) | variés (non détaillés ici) | — |
| Propriétaires PM, acquisitions PM | DGFiP (fichiers fonciers) | tables `parcelle_personne_morale`/foncier (`zone.py:725-958`) | — | — |
| Loyer, dispositif ORT | OLL 2024 · DGALN/ANCT | `commune_contexte_zone` (`zone.py:959`) | OLL 2024 | — |
| Isochrone (si aucun rayon) | isochrones IGN | API IGN + cache `zone_isochrone_cache` (`zone.py:90-126`) | TTL 30 j | — |

En **mode rayon** (le seul proposé par l'UI), l'isochrone IGN n'est **pas** appelée : le back fabrique un **cercle exact** par `ST_Buffer(...::geography, rayon×1000)` (`app.py:7957-7961`) et le passe comme polygone. L'isochrone ne sert que si aucun rayon n'est fourni.

## 4. Les calculs
Toutes les couches filtrent par **appartenance géométrique à la zone**, chacune avec sa règle d'inclusion :

- **Population** (`zone.py:167-230`) : somme des carreaux 200 m **dont le centroïde est dans la zone** (`ST_Contains(zone, ST_Centroid(f.geom))`, `:177`). `habitants = round(sum(ind))`, `menages = round(sum(men))`. **« Niveau de vie moyen / an » = `round(sum(ind_snv)/sum(ind))`** (`:171`) — c'est une moyenne par individu, **ni un revenu ni une médiane** malgré l'alias SQL `revenu_median_eur` (le code le dit, `EtudeZone.tsx:231-236`). Badge **« approché »** si la majorité des carreaux (à revenu) sont imputés depuis la maille 1 km (`i_est_200='1'`, `:187-194`).
- **Emplois** (`zone.py:246-278`) : on **somme les bornes des tranches d'effectif SIRENE** des établissements actifs de la zone → une **fourchette** `postes_min / postes_max`. Constante `TRANCHE_BORNES` (`zone.py:239-243`, codée en dur, barème INSEE des tranches ; 53 = « 10 000+ » → borne haute ouverte). Les établissements **sans tranche** renseignée sont comptés à part (`n_sans_tranche`), jamais additionnés. Ce n'est **pas** l'emploi localisé (MOBPRO abandonné, `:233-235`).
- **Marché** (`zone.py:428-482`) : `ventes_12m` = compte DVF sur une **fenêtre ancrée sur la dernière date servie** (`max(date_mutation) − 12 mois`, `:457-459`), pas sur `now()`. `prix_m2_median_bati` = `mediane_bati` (point de calcul unique, 36 mois, `:463`) ; **mais** quand l'entrée est une parcelle, l'endpoint **écrase** ce prix par `marche_dvf(idu)` = médiane du **secteur de la fiche** (`app.py:7982-7989`), pour coïncider avec Dossier/Comparatif. `annonces_actives` = compte `pige_biens` (minimum, pas un total). `permis_36m` = compte SITADEL 36 mois.
- **BPE** (`zone.py:874-918`) : par domaine A→G, liste **complète dédoublonnée par nom** (`:900-913`) ; `n` = taille de la liste dédoublonnée. Filtre anti-coquille INSEE (`_bpe_nom_dement_sdom`, `:909`). Tri stable distance-puis-nom.
- **Fibre** (`app.py:2004-2016`) : `pct_ftth = round(100×n_ftth/n_immeubles, 1)` sur les immeubles Arcep intersectant la zone.
- **Habitants par concurrent** (`app.py:7993-7996`) : `round(habitants/n_concurrents)` — seulement si une activité NAF est fournie (jamais via l'UI actuelle).
- **Rayon validé** : un rayon hors `{0,5 ; 1 ; 2 ; 5}` est **refusé (422)**, pas silencieusement remplacé (`app.py:7949-7955`) — confirmé en live (voir §9).

Arrondis : populations à l'entier, pct à l'entier ou 1 décimale, €/m² à l'entier.

## 5. Chaque chiffre affiché
| Libellé à l'écran | D'où il vient | Sourcé ou estimé |
|---|---|---|
| « habitants » / « ménages » | `sum(ind)` / `sum(men)` carreaux Filosofi 2021 | **sourcé** |
| « niveau de vie moyen / an » (badge *sourcé*/*approché*) | `sum(ind_snv)/sum(ind)` Filosofi 2021 | **sourcé** (donnée INSEE winsorisée ; *approché* si majorité imputée) |
| Structure d'âge (%) | IRIS RP2022 pondéré surface | **sourcé** (agrégé) |
| « postes salariés déclarés dans la zone » (fourchette) | somme bornes tranches SIRENE | **estimé** (fourchette, pas un décompte) |
| « Toutes les entreprises … (N) » + familles | compte `sirene_etablissements` par section NAF | **sourcé** |
| « ventes / 12 mois » | compte `dvf_mutations` fenêtre ancrée | **sourcé** |
| « médian €/m² bâti » | `marche_dvf(idu)` secteur fiche (écrase la médiane de zone) | **sourcé** (mais secteur fiche, ≠ cercle) |
| « annonces actives » | compte `pige_biens` | **sourcé mais partiel** (pige manuelle) |
| « permis / 36 mois » | compte `sitadel_permits` | **sourcé** |
| « prix par type (36 mois) » | DVF par type, seuil 5 ventes (`zone.py:646-688`) | **sourcé** (« — » sous 5 ventes) |
| « N établissement(s) » par domaine BPE | compte liste BPE dédoublonnée | **sourcé** |
| « % de la zone » (PPR, aléas, assainissement, espaces) | part de surface recouverte | **sourcé** (calculé) |
| « % FttH (n/N) » | Arcep immeubles | **sourcé** |
| « véh./j » trafic RN | `trafic_rn` dernier millésime | **sourcé** |
| Top propriétaires / acquisitions PM (ha, parc.) | fichiers fonciers DGFiP | **sourcé** |
| « loyer médian … €/m² » | OLL 2024, échelle commune | **sourcé** (commune, pas la zone) |

## 6. Les limites
- **Centre = centroïde de la parcelle**, et le périmètre est un **cercle géométrique**, pas une isochrone de temps de trajet (sauf si aucun rayon n'est envoyé — impossible depuis l'UI). « Chalandise » ici = distance à vol d'oiseau.
- La **lentille concurrents / activité NAF** (cœur annoncé d'un outil de chalandise) existe côté back mais n'est **plus accessible** depuis l'écran. Pas de comptage de concurrents ni de « habitants par concurrent » via l'UI.
- **« Niveau de vie moyen »** est souvent lu comme « revenu médian » : c'est un ratio moyen par individu, pas une médiane — libellé corrigé mais ambigu.
- **Prix médian €/m²** affiché = celui du **secteur de la fiche** (parcelle), pas la médiane des ventes du cercle : deux périmètres différents sous un même écran.
- **Annonces Radar** = pige manuelle partielle (12/24 communes à l'origine) → un **minimum**, jamais un marché.
- Plusieurs chiffres sont à **l'échelle de la commune** (loyer OLL, dispositif ORT), pas de la zone — l'écran le dit mais c'est facile à manquer.
- Si l'IGN échoue en mode isochrone, dégradé honnête (« Zone atteignable indisponible », pas de cercle inventé) — mais ce cas ne survient pas en mode rayon.

## 7. Les tests
Backend (`tests/`) :
- `test_zone_moteur.py` : Filosofi = point de calcul unique (`test_population_zone_point_unique_filosofi:66`), zone inhabitée « digne » (`:93`), échec isochrone sans cercle inventé (`:54`), cache isochrone (`:39`), couverture SIRENE non-couverte sans faux zéro (`:184`).
- `test_zone_donnees.py` : fourchette emplois + sans-tranche (`:77`), imputation Filosofi pilotée par `i_est_200` (`:102`), zone de demain (`:121`), contraintes PLU (`:144`), trafic RN dernier millésime (`:169`), coquille BPE écartée (`:192`).
- `test_etude_zone_determinisme.py` : fenêtres **ancrées sur la donnée** (`:25`) et deux appels **identiques** (`:43`, mémoïsation).
- `test_docs1_ecran_egale_pdf.py:111` : **l'écran = le PDF** (verrou 7 sections, pas de fuite).

**Non vérifié par aucun test** : **aucun test front** pour `EtudeZone.tsx` (0 `*.test.tsx` trouvé) — l'UI (rayons, accordéons, bouton PDF, retrait du menu Activité) n'est pas testée ; l'**écrasement du prix €/m² par `marche_dvf(idu)`** (`app.py:7982-7989`) ; le libellé « niveau de vie moyen » n'est pas contrôlé par un test de cohérence.

## 8. Les documents liés (PDF, exports)
`GET /etude-zone.pdf` (`documents.py:266-305`) appelle **la même fonction** `etude_zone(EtudeZoneIn(idu, rayon_km))` que l'écran (`:286-287`), puis `builder.construire_etude_zone` rend les mêmes 7 sections (`exports/blocs/etude_zone.py`). **Mêmes valeurs que l'écran** : le PDF ne recalcule rien. Une légère divergence volontaire : le PDF ajoute `marche.prix_ancien` (médiane de la fiche avec n + rayon) en plus (`documents.py:291-296`). Le libellé « Niveau de vie moyen / an » du PDF (`etude_zone.py:40-42`) est aligné sur l'écran. Le test `test_docs1_ecran_egale_pdf.py:111` verrouille cette égalité. Rayon par défaut du PDF = **2 km** si non précisé (`documents.py:267`), alors que l'UI envoie le rayon choisi.

## 9. Trois cas rejoués
Entrée exacte : `POST /outils/etude-zone` avec `{"idu":"<IDU>","rayon_km":1,"minutes":10,"mode":"voiture"}` (le centre est le **centroïde** de la parcelle ; `minutes`/`mode` sont neutres et ignorés en mode rayon). Instance `:9810` (voir note de méthode).

**97411000BZ1065 (Saint-Denis)** — adresse résolue « 3 Chemin de la Citerne, 97417 Saint-Denis », surface 312 ha (cercle 1 km).
- Population : **3 604 habitants**, 1 283 ménages, niveau de vie **30 813 €/an** (non imputé), Filosofi 2021.
- Emplois : couverture servie, **246–461 postes**, 650 établissements dont 576 sans tranche.
- Marché : **31 ventes/12 mois**, **2 365 €/m² bâti**, 0 annonce, 22 permis/36 mois.
- BPE : A=38, B=11, C=3, D=40, E=2, F=13. Fibre : 96,9 % (1 204/1 243).

**97409000AK0804 (Saint-André)** — « 524 Rue Jean Jacques Rousseau, 97440 Saint-André », 312 ha.
- Population : **7 374 habitants**, 2 277 ménages, niveau de vie **17 259 €/an**.
- Emplois : **357–693 postes**, 681 établissements (597 sans tranche).
- Marché : 17 ventes/12 mois, **1 520 €/m²**, 0 annonce, 47 permis/36 mois.
- BPE : A=112, B=12, C=6, D=19, E=7, F=6. Fibre : 99,4 % (1 763/1 774).

**97415000DH0076 (Saint-Pierre/-Joseph secteur sud, d'après le brief)** — **l'adresse BAN du centroïde est renvoyée « 104 Avenue de Bourbon, 97434 Saint-Paul »** (à signaler : le libellé d'en-tête de l'outil contredit la localisation attendue du témoin ; à vérifier si l'IDU ou la résolution d'adresse est en cause), 312 ha.
- Population : **1 829 habitants**, 896 ménages, niveau de vie **30 776 €/an**.
- Emplois : **652–1 292 postes**, 691 établissements (585 sans tranche).
- Marché : 21 ventes/12 mois, **6 250 €/m²**, 0 annonce, 11 permis/36 mois.
- BPE : A=57, B=30, C=3, D=17, F=16, G=9. Fibre : 95,5 % (463/485).

Contrôles complémentaires (BZ1065) : rayon **3 km → HTTP 422** (refus propre, valeurs acceptées 0,5/1/2/5) ; rayon **2 km → surface 1 249 ha** (≈ π×2², cohérent) et **15 060 habitants**. Entreprises (BZ1065) : millésime **« SIRENE géolocalisé 2026-09 »**, 17 familles (L immobilier 167, M 79, Q santé 71…), chaque famille plafonnée à `charges=40` établissements détaillés.

## 10. Tes doutes (par gravité)
1. **Le périmètre réel n'est pas celui d'une « chalandise »** : centre = centroïde de parcelle + **cercle à vol d'oiseau**, et la **lentille concurrents/NAF a été retirée de l'UI**. L'outil annonce « chalandise » mais ne compte plus les concurrents et ignore le temps de trajet — c'est devenu un profil de quartier.
2. **Deux périmètres sous un même écran** : le « médian €/m² bâti » affiché vient du **secteur de la fiche** (`marche_dvf(idu)`, `app.py:7982-7989`), alors que « ventes/12 mois » et « prix par type » viennent du **cercle**. Un lecteur croit lire le même périmètre.
3. **Témoin DH0076 résolu à Saint-Paul** (« 104 Avenue de Bourbon, 97434 Saint-Paul ») alors que le brief le situe à Saint-Pierre/-Joseph sud. Soit l'IDU pointe ailleurs, soit la résolution BAN dérive — l'en-tête « depuis {adresse} » pourrait afficher une commune fausse.
4. **« Niveau de vie moyen »** est un ratio `sum(ind_snv)/sum(ind)` étiqueté dans le code par l'alias trompeur `revenu_median_eur` ; même corrigé à l'écran, la nuance (moyenne ≠ médiane, Filosofi winsorisé) est facile à sur-interpréter en « revenu ».
5. **Zéro test front** et aucun test sur l'écrasement du prix : la couche UI (rayons servis, accordéons, bouton PDF, retrait du menu Activité) et la substitution de prix ne sont couvertes par aucun test automatisé.
