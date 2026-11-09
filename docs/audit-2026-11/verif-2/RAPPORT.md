# VERIF-2 — Audit de vérité (lecture seule)

**Branche** `audit/verif-2` · worktree `~/Desktop/labuse-verif2` · base locale `labuse` (run servi **q_v20**) · Opus · **aucune correction, aucune écriture (code ni base)**. Date : **2026-11-09**.

Quatre questions, quatre verdicts. Méthode : lecture du code + requêtes `psql` en lecture seule + sondes HTTP réelles contre la Géoplateforme IGN (`GetCapabilities` / `GetTile`). L'environnement Python du projet est cassé (`sqlalchemy` absent) ; tout passe donc par `psql` direct et lecture de fichiers, jamais par le boot de l'app.

---

## 1 · « Comprendre l'analyse » — chaque phrase est-elle encore vraie ?

Le panneau client est le bloc `comprendre` de `frontend/src/lib/strings.ts:314-340` (ANALYSE-2, « le panneau UNIQUE »). Je l'ai confronté au code **réellement servi** du Score (`src/labuse/scoring/score_labuse*.py`, `config/score_labuse.yaml`) et du Signal (`src/labuse/scoring/signal_mutation.py`, `p_v2/qv15.py` → `qv14.py` → `qv12.py`) et au tri de l'Analyse (`src/labuse/api/app.py`).

### Verdict phrase par phrase

| Phrase du panneau | Code de référence | Verdict |
|---|---|---|
| « La bande dit le potentiel constructible RÉEL… ce que le PLU autorise encore à bâtir, une fois retirées les contraintes (zonage, risques, accès, terrain) et vérifiée la faisabilité. » | `score = clip(barème_capacité(SDP résiduelle) × coef_faisabilité, 0, 100)` (`config/score_labuse.yaml:17`) | **Vrai**, avec une imprécision (voir écart ①) |
| Bandes : Excellente / Bonne / À étudier / Faible / Non retenue / Analyse incomplète | `vocabulaire_client` A/B/C/D/0/NC (`config/score_labuse.yaml:64-71`) | **Vrai — libellés identiques au mot près** |
| « Non retenue = aucun droit à bâtir résiduel identifié » | bande `"0"` = score == 0 exactement ; faisabilité a un plancher 0,4 > 0 ⇒ score 0 ⟺ capacité 0 ⟺ SDP résiduelle ≤ 0 | **Vrai au sens littéral** (voir écart ②) |
| « Analyse incomplète = une donnée manque pour conclure — la cause est indiquée sur la parcelle » | NC ⇒ score None, cause lisible `_cause_nc` ; « NC n'est jamais 0 » (`config/score_labuse.yaml:57`) | **Vrai** |
| Monte : droits restants importants, terrain praticable, accès identifié / Descend : pente forte, bâti proche du max, accès non identifié | facteurs `faisabilite` : `pente_pct`, `bati.emprise_pct`, `acces_non_identifie` (`config/score_labuse.yaml:31-54`) | **Vrai** |
| Signal « résumés en Fort, Moyen ou Faible » | `signal_niveau(p)` : fort ≥ 0,20 · moyen 0,10–0,20 · faible < 0,10 (`signal_mutation.py:7`) ; servi comme `signal_niveau` à l'Analyse (`app.py:3325,3395`) | **Vrai** |
| « des signes que la parcelle pourrait bouger dans les 12 mois » | `signal_p` = **P(vente L2-F dans les 12 mois suivant la date du score)** (`signal_mutation.py:3-4`) | **Vrai (horizon 12 mois exact)** |
| « (mise en vente, succession, société en difficulté…) » | features réelles du modèle q_v15 (voir ci-dessous) | **ÉCART ③ — exemples non représentatifs** |
| « il ne change JAMAIS la bande : une parcelle Excellente à signal Faible reste Excellente. Il sert seulement à départager les parcelles d'une même bande. » | tri `labuse` = `_BANDE_RANG_SQL ASC, sl.signal_p DESC` (`app.py:4049-4057`) : bande d'abord, signal **à l'intérieur** de la bande | **Vrai — garanti par le tri** |
| « LABUSE rend une liste unique, classée par bande (Excellente d'abord), et par signal à l'intérieur de chaque bande » | `_BANDE_RANG_SQL` : A→0, B→1, C→2, D→3, NC→4, 0→5 (`app.py:4042-4044`) puis `signal_p DESC`, puis SDP résiduelle, puis IDU | **Vrai** |

### Écarts relevés

**① (mineur, imprécision) — « retirées les contraintes (zonage, risques, accès, terrain) ».**
Seuls **zonage et risques** sont retranchés en amont pour produire la SDP résiduelle. **Accès et terrain (pente, forme)** ne sont *pas* retirés de l'enveloppe constructible : ce sont des **coefficients multiplicateurs** de la faisabilité (`acces_non_identifie = 0,85`, `pente_au_dela = 0,6`, `forme.facteur = 0,8`). La phrase les range à tort parmi les contraintes « retirées » alors qu'ils relèvent du « et vérifiée la faisabilité » qui suit. Sens global juste, mécanique décrite imprécise.

**② (nuance importante) — « Non retenue = aucun droit à bâtir résiduel identifié ».**
Littéralement vrai (bande 0 ⟺ SDP résiduelle ≤ 0). Mais ce 0 **hérite d'un résiduel qui comporte un faux négatif connu** : le test `terrain_exigu` juge le contour *après reculs* et non la surface, ce qui classe en « trop étroites / SDP 0 » des parcelles >1000 m² (cf. audit ALGO-LECTURE-1 : 166 parcelles, l'une de 11 ha). La **phrase** est vraie ; la **valeur** sous-jacente ne l'est pas toujours. À l'échelle parcelle, un « Non retenue » peut donc être un faux « aucun droit à bâtir ».

**③ (modéré — le plus net) — les exemples du Signal ne correspondent pas au modèle servi.**
Le panneau illustre le signal par « *mise en vente, succession, société en difficulté* ». Or `signal_p` vient du modèle **q_v15** (`features_qv15` = base `qv12` + `pc_pm_sur_parcelle_pp_36m`, `anciennete_plu_annees`, `ventes_pm_secteur_36m`). Ses variables réelles sont : **ancienneté de détention, nu/bâti et part bâtie du secteur, SDP résiduelle, ventes à 150/400 m, permis à 100 m, permis d'un pro sur une parcelle de particulier, opérations d'aménageur, volume/prix/tendance de la commune, personne morale vendeuse récente du secteur, ancienneté du PLU**.
- **« succession »** n'est **pas** une variable du signal 12 mois : la succession est traitée à part par `veille_succession` (radar patrimonial **3-7 ans**, `score_v_constants.py:170-173`), explicitement **HORS** du signal de mutation.
- **« société en difficulté »** (liquidation/redressement BODACC) appartient au **Score V legacy** (`score_v_constants.py:130-138`), **pas** aux features q_v15 — aucune variable BODACC/détresse de propriétaire n'entre dans `signal_p`.
- « mise en vente » décrit l'**issue prédite**, pas un signal observé — acceptable comme illustration.

Deux des trois exemples donnés au client décrivent donc des signaux que le modèle servi **n'utilise pas**.

**Note (pas un écart du texte).** Le panneau tait volontairement la fiabilité mesurée faible du signal (AUC ≈ 0,625, cf. ALGO-LECTURE-1), mais la couvre honnêtement par « *c'est un indice, pas une promesse* ». Non mensonger.

**Bilan Q1 :** le panneau est **globalement exact** (bandes, horizon 12 mois, seuils Fort/Moyen/Faible, « le signal ne change pas la bande », tri Excellente→signal). Trois écarts : un modéré (exemples du signal faux), une nuance importante (bande 0 adossée à un résiduel parfois faux), une imprécision mineure (accès/terrain présentés comme « contraintes retirées »).

---

## 2 · Les couches de la carte — affichage, millésime, date, et celles vides/cassées/périmées

### Combien de couches ? (résolution de l'écart 56 / 52 / 51)

Le catalogue vient de `declarations.couches_carte()` (YAML `declarations/couches/*.yaml`), servi par le tuyau MVT `src/labuse/api/couches_tuyau.py`.

| Décompte | Valeur |
|---|---|
| `kind` distincts déclarés `categorie: couche` | **57** |
| − `scot`, exclu du plan carte (`couches_tuyau.py:816 : if k == "scot": continue`) | −1 |
| **= couches servies par le tuyau** | **56** ← c'est le « 56 » de `api.ts:942` (le bon chiffre) |
| + hors-registre (`tuyau_hors_registre.yaml`, source `mvt_parcels/communes`) : limites parcelles, zonage parcelle, limites communes | +3 |
| + raster front-only codés en dur (`CouchesTuyau.tsx`) : courbes de niveau, EnR habitations (WMTS IGN) | +2 |
| **Total proposé au panneau** | **61** (60 toggles hors Bâti 3D, qui part dans le bouton 3D) |

Les nombres **51** (`declarations.py:43`), **52** (`couches_tuyau.py:21`, `app.py:10044`) et **55** (`app.py:7928`) sont des **commentaires périmés jamais recomptés**, chacun figé à une étape de développement différente. **56** est le décompte correct des couches servies à la carte.

### Couches vides / cassées

**Aucune couche EMPTY (0 ligne).** Toutes les résolutions virtuelles ont des données (er 2250, ebc 1782, sis 10, casias 521, alea_inondation 176, alea_mvt 917, enp/ens 411, tcsp 135). Les plus maigres sont réelles et assumées (enr_exclue_hors_toiture 3, parc_national 3, bruit_carte 6, telepherique 7, peb 8, anru 8).

**CASSÉES :**
- **`scot`** — déclarée mais **jamais servie à la carte** (exclue par `continue`). 3 lignes en base, servie en fiche seulement. Retrait volontaire (RECETTE-1 C3) mais formellement c'est une couche déclarée qui ne s'affiche pas.
- **`vefa_neuf`** (Prix logement neuf) — **orpheline de source** : 24 lignes, `data_source_id` NULL sur toutes, aucune `data_source` VEFA au catalogue (vérifié : `select count(*), count(data_source_id) → 24, 0`). **Millésime et date NULL.** La donnée s'affiche sans aucune traçabilité.
- **`pole_echange`** (mineur) — le YAML déclare `filtre subtype=osm`, mais le tuyau n'applique que `_RESOLUTION_OVERRIDE` (où `pole_echange` est absent) : il sert les 61 lignes (osm 42 **+** gtfs 19), pas les 42 attendues. Filtre inopérant.
- **`courbes_niveau`** et **`enr_habitation`** (raster front, WMTS IGN) — ne passent pas par `/map/couches-info` : **aucun millésime ni date** suivis ; le seul « millésime » est une chaîne en dur dans le texte du « i ».

### Couches périmées / millésime notablement daté (données OK en base, mais ancienneté masquée)

| Couche | Millésime réel | Dernier sync | Remarque |
|---|---|---|---|
| `trait_de_cote` (érosion côtière) | **2018** | jamais | 24 168 lignes, jamais re-synchronisé |
| `dpf` (ravines/reculs) | arrêté **2006** | jamais | donnée opposable mais ancienne |
| `ligne_mt` (HTA) | géométrie EDF **~02/2020** | 09-14 | publiée 10/2025 |
| `parc_national` | **2021** | jamais | |
| `bruit_carte` (CBS) | **2022** | jamais | |
| `cinquante_pas` | cadastre **1877** (géoréf. 2012/1950) | jamais | donnée de référence, présentée telle quelle |
| `sar` + socle `potentiel_foncier` | **`source_millesime` vide** | jamais | s'affiche sans aucun millésime |

**Machinerie de fraîcheur inerte.** Toutes les sources des couches carte sont `fraicheur_statut = sans_echeance` (66 kinds) ou vide (3) — vérifié : `select ds.fraicheur_statut, count(distinct sl.kind) … → sans_echeance 66, (vide) 3`. **Aucune** n'est marquée « périmé », aucune n'a `prochain_millesime_at`, aucune `affichage_desactive` ni `retiree_le`. Les 4 sources retirées/désactivées du catalogue (BDNB, EDF SEI, MOBPRO, ODRÉ) **n'alimentent aucune couche carte**. Conséquence : l'obsolescence (2006, 2018, 2020, 2021, 2022) **n'est jamais signalée** par le statut.

### Le constat central : le millésime et la date ne sont PAS affichés à l'utilisateur

Le mandat demande que chaque couche s'affiche « avec son millésime réel et sa date de dernière mise à jour ». **Ce n'est le cas d'aucune couche côté client.**
- L'endpoint `/map/couches-info` (`app.py:7926`) **calcule** bien `{source, millesime, date_controle, fabrication}` à partir du vrai `data_source_id` des lignes.
- Mais le panneau de la carte (`InfoTuyau`, `CouchesTuyau.tsx:132-145`) ne rend que **`meta.source`** + la prose YAML. Le millésime et la date sont **fetchés puis jetés** — commentaire explicite `CouchesTuyau.tsx:120` : « *PAGE-SOURCES-1 — le MILLÉSIME est retiré du « i »… lus côté admin* ».
- La page Sources client (`SourcesPage.tsx:28`) a elle aussi **retiré le millésime** (« Publié le… »).

**Donc 0 couche sur 60 affiche son millésime et sa date à l'utilisateur final.** La donnée existe en back, elle est volontairement masquée côté client (décisions PAGE-SOURCES-1). Seul l'admin la voit. C'est l'écart le plus net du mandat Q2 : la carte *affiche* les couches, mais **pas** « avec son millésime et sa date ».

### Table complète (front kind → stocké → fraîcheur → verdict)

Row counts = `spatial_layers` à l'audit ; millésime/sync = `data_sources` jointe sur le `data_source_id` réellement porté par les lignes servies.

| Couche | front kind | stocké (subtype) | rows | last build | millésime | last sync | verdict |
|---|---|---|---|---|---|---|---|
| Limites PLU (GPU) | plu_gpu_zone | plu_gpu_zone | 5841 | 09-13 | GPU par commune | — | OK |
| 50 pas géométriques | cinquante_pas | cinquante_pas | 163 | 07-10 | cadastre 1877 | jamais | OK (ancien) |
| Artificialisation (OCS GE) | artificialisation | artificialisation | 12107 | 10-13 | OCS GE 2017+2022 | jamais | OK |
| DPU | dpu | dpu | 202 | 09-13 | GPU typeinf 04 (partiel) | — | OK |
| SUP | sup | sup | 417 | 09-14 | SUP assiettes GPU | 09-14 | OK |
| Emplacements réservés (ER) | er | plu_gpu_prescription(05) | 2250 | 06-29 | GPU/PLU | — | OK |
| Espaces boisés classés (EBC) | ebc | plu_gpu_prescription(01) | 1782 | 06-29 | GPU/PLU | — | OK |
| **SCOT (périmètre)** | scot | scot | 3 | 09-26 | GPU périmètres SCOT | 09-26 | **CASSÉE (exclue)** |
| PPR multirisque | ppr | ppr | 164 | 07-03 | PPR +récent 2026-04-16 | jamais | OK |
| **Ravines et reculs (DPF)** | dpf | dpf | 281 | 10-27 | arrêté 2006 | jamais | **PÉRIMÉE** |
| Systèmes d'endiguement | endiguement | endiguement | 117 | 09-14 | EDD Hydrétudes déc. 2024 | jamais | OK |
| PEB | peb | peb | 8 | 09-13 | Roland-Garros (partiel) | jamais | OK (partiel) |
| Classement sonore routier | bruit_route | bruit_route | 1004 | 09-14 | arrêtés déc. 2023 | 09-14 | OK |
| **Cartes de bruit** | bruit_carte | bruit_carte | 6 | 09-14 | CBS 2022 | jamais | **ancien** |
| Aléa inondation | alea_inondation | georisque_alea(inond.+submersion) | 176 | 09-14 | DEAL PPR/aléas | jamais | OK |
| Aléa mouvement de terrain | alea_mvt | georisque_alea(mouvement_terrain) | 917 | 09-14 | DEAL PPR/aléas | jamais | OK (Saint-Denis non cartographié) |
| SIS | sis | sol_pollue(sis) | 10 | 09-14 | Géorisques sols pollués | 09-14 | OK |
| CASIAS | casias | sol_pollue(casias,instruction) | 521 | 09-14 | Géorisques | 09-14 | OK |
| ICPE | icpe | icpe | 1268 | 09-14 | Géorisques ICPE | 09-14 | OK |
| Friches (Cartofriches) | friche | friche | 372 | 08-13 | Cartofriches Cerema | 08-13 | OK |
| Cavités souterraines | cavite | cavite | 151 | 09-14 | Géorisques cavités | 09-14 | OK |
| **Érosion côtière** | trait_de_cote | trait_de_cote | 24168 | 09-14 | 2018 | jamais | **PÉRIMÉE** |
| TRI zones inondables | tri_zone | tri_zone | 128 | 09-14 | GASPAR 2026-09-07 | jamais | OK |
| ABF / monuments | abf | abf | 200 | 07-05 | ABF/MH | 07-05 | OK |
| **SAR (proxy)** | sar | sar | 2453 | 06-29 | **(vide)** | jamais | **millésime absent** |
| Forêts publiques | foret_publique | foret_publique | 65 | 09-14 | BD TOPO forêt pub. | jamais | OK |
| Bassins versants | bassin_versant | bassin_versant | 150 | 09-14 | BD TOPO V3 | 09-26 | OK |
| Cimetières | cimetiere | cimetiere | 164 | 09-14 | BD TOPO V3 | 09-26 | OK |
| Foncier agricole RPG/SAFER | safer | safer | 38897 | 10-11 | RPG 2024 | jamais | OK |
| Zones d'activité | zone_activite | zone_activite | 9020 | 09-14 | BD TOPO V3 | 09-26 | OK |
| Murs de soutènement | construction_lineaire | construction_lineaire | 6719 | 09-14 | BD TOPO V3 | 09-26 | OK |
| Barrages/ponts/dalles | construction_surfacique | construction_surfacique | 305 | 09-14 | BD TOPO V3 | 09-26 | OK |
| Zones humides | zone_humide | zone_humide | 3122 | 10-27 | inventaires 2003–2019 | jamais | OK |
| Espaces naturels protégés | enp | ens | 411 | 10-27 | DEAL Carmen 2026-09-13 | 06-08 | OK |
| ZNIEFF | znieff | znieff | 162 | 09-14 | INPN 2025-08-29 | 09-14 | OK |
| **Parc national** | parc_national | parc_national | 3 | 09-14 | 2021 | jamais | **ancien** |
| Mesures compensatoires (ERC) | mesures_compensatoires | mesures_compensatoires | 24 | 09-26 | GéoMCE | 09-26 | OK |
| Équipements OSM | amenite | amenite (8 subtypes) | 3102/15214 | 08-10 | OSM Overpass | 07-06 | OK (sport/tcsp exclus par design) |
| Équipements INSEE (BPE) | amenite_bpe | amenite_bpe | 35544 | 09-14 | BPE 2025 | 09-14 | OK |
| Bâti 3D | batiment | batiment | 817506 | 06-29 | BD TOPO V3 | 09-26 | OK (hors panneau général) |
| **Prix logement neuf (VEFA)** | vefa_neuf | vefa_neuf | 24 | 10-05 | **aucune source** | **aucun** | **CASSÉE (orpheline)** |
| ZFANG | zfang | zfang | 24 | 08-24 | Décret 2026-421 | jamais | OK |
| FRR | frr | frr | 23 | 08-24 | FRR 2024-07-01 | jamais | OK |
| TVA primo | tva_primo | tva_primo | 13 | 08-24 | QPV 2024 (dérivée) | 07-05 | OK |
| QPV | qpv | qpv | 57 | 07-05 | 2024 | 07-05 | OK |
| ANRU/NPNRU | anru | anru | 8 | 07-08 | NPNRU | 07-08 | OK |
| EnR interdites hors toiture (APER) | enr_exclue_hors_toiture | enr_exclue_hors_toiture | 3 | 09-26 | OFB APER | 09-26 | OK |
| Axes structurants | axe_structurant | axe_structurant | 3481 | 10-11 | BD TOPO V3 | 09-26 | OK |
| Transport public lignes | transport_ligne | transport_ligne | 300 | 10-11 | GTFS PAN 2026-10 | 10-11 | OK |
| Transport public arrêts | transport_arret | transport_arret | 9954 | 10-11 | GTFS PAN | 10-11 | OK |
| Téléphérique | telepherique | telepherique | 7 | 10-11 | OSM Overpass | jamais | OK |
| **Pôles d'échange** | pole_echange | pole_echange (osm+gtfs) | 61 | 10-11 | OSM/GTFS | — | **CASSÉE-mineure (filtre non appliqué)** |
| Lignes HTB | ligne_ht | ligne_ht | 48 | 10-11 | BD TOPO V3 | 09-26 | OK |
| **Lignes HTA** | ligne_mt | ligne_mt | 19480 | 09-14 | EDF ~02/2020 | 09-14 | **ancien** |
| Pylônes | pylone | pylone | 1187 | 09-26 | BD TOPO V3 | 09-26 | OK |
| Postes de transformation | poste_transformation | poste_transformation | 20 | 09-26 | BD TOPO V3 | 09-26 | OK |
| TCSP | tcsp | tcsp_zone+troncon(site_propre)+station | 135 | 09-05 | OSM Overpass | 09-05 | OK |
| Limites parcelles | limites_parcelles | mvt_parcels (hors SL) | ~431k | — | run servi | — | OK |
| Zonage PLU par parcelle | zonage_parcelle | mvt_parcels (hors SL) | ~431k | — | run servi | — | OK |
| Limites communes | limites_communes | mvt_communes (hors SL) | 24 | — | IGN communes974 | — | OK |
| **Courbes de niveau** | courbes_niveau | WMTS IGN (front) | — | — | **non exposé** | — | **pas de millésime servi** |
| **Contraintes EnR habitations** | enr_habitation | WMTS IGN (front) | — | — | **non exposé** | — | **pas de millésime servi** |

---

## 3 · L'ortho IGN — millésime servi vs le plus récent disponible pour La Réunion

### Ce qui est servi
Le fond « Actuelle » de la carte = clé `bm-ortho-now` → proxy `ORTHO_PROXY('express')` (`frontend/src/components/map/basemaps.ts:50`), que le backend relaie vers la couche WMTS IGN **`ORTHOIMAGERY.ORTHOPHOTOS.ORTHO-EXPRESS.2025`** (`src/labuse/api/ortho_proxy.py:54`). C'est la **BD ORTHO / Ortho Express RVB 2025, 20 cm** (data_source id 61).
Sonde live (2026-11-09) sur une tuile Saint-Denis z16 (col 42863 / row 36657) : **HTTP 200, JPEG 256×256 valide (22 540 o)** → le millésime 2025 est bien servi et **couvre La Réunion**.

La mosaïque générique `ORTHOIMAGERY.ORTHOPHOTOS` (couche `monde` du proxy) ne sert, elle, que **2022** au 974 (constat GetTile du code daté 2026-09-04) ; la tuile Saint-Denis renvoie une image **différente** (md5 distinct) de l'Express 2025 → ce sont bien deux millésimes.

### Le plus récent disponible chez l'IGN pour La Réunion
`GetCapabilities` WMTS (récupéré aujourd'hui) : les Ortho Express annuelles s'arrêtent à **`ORTHO-EXPRESS.2023/2024/2025`** sous l'ancien nom. Un **millésime 2026 existe** mais sous un **schéma de nommage renommé** : `ORTHOIMAGERY.ORTHOPHOTOS.RVB-EXPRESS.2026` et `IRC-EXPRESS.2026` (WMTS **et** WMS).

Sonde live sur la **même tuile Saint-Denis** z16 :

| Couche | HTTP |
|---|---|
| `ORTHO-EXPRESS.2025` | **200** (22 540 o, image réelle) |
| `RVB-EXPRESS.2026` | **404** (137 o, pas de donnée) |
| `IRC-EXPRESS.2026` | **404** |

→ **Le millésime 2026 n'est pas encore publié pour La Réunion.** Il couvre la métropole mais pas (encore) l'île. Confirmé par la doc IGN/forum OSM : « La Réunion est *dans le programme 2026, couverture aérienne planifiée* » (futur) ; l'Express 2025 n'est intégrée à la BD ORTHO « *pas avant fin 2025 / début 2026* ».

**Verdict Q3 :** l'application sert **le millésime le plus récent réellement disponible pour La Réunion (Ortho Express 2025, 20 cm)**. Elle est à jour. **Un point de fragilité** : la couche est **codée en dur** (`ortho_proxy.py:54`), et l'IGN a **changé le nommage** pour 2026 (`ORTHO-EXPRESS.*` → `RVB-EXPRESS.*`). Quand le 2026 Réunion sortira, l'app ne le prendra **pas** automatiquement — et un simple « incrémenter l'année » échouera (il faudra `RVB-EXPRESS.2026`, l'ancien identifiant `ORTHO-EXPRESS.2026` renvoie 400).

---

## 4 · La 3D — pourquoi des bâtiments de l'ortho n'ont pas de volume

### Le chemin de rendu
- Front : couche MapLibre `batiments-3d`, `fill-extrusion`, hauteur = `['coalesce', ['get','h'], 0]` (`frontend/src/components/map/MapView.tsx:747-752`). Pas de `h` ⇒ hauteur 0 ⇒ aucun volume. Chargée par BBOX au zoom ≥ 15 (`MapView.tsx:1258-1272`) via `/map/batiments.geojson` (`api.ts:532`).
- Back : endpoint `map_batiments_geojson` (`src/labuse/api/app.py:8186-8223`). Requête :
  ```sql
  SELECT sl.geom, round(COALESCE(hl.faitage_m, (attrs->>'hauteur')),1) AS h, ...
  FROM spatial_layers sl
  LEFT JOIN LATERAL (... batiment_hauteur_lidar ...) hl ON true
  WHERE sl.kind='batiment' AND (sl.attrs->>'hauteur') IS NOT NULL
    AND sl.geom && ST_MakeEnvelope(...) LIMIT 8000
  ```
  Docstring assumé (`app.py:8190`) : « **Sans hauteur → EXCLU (jamais d'extrusion inventée, décision Vic)** ».

**Cause racine :** le filtre `(sl.attrs->>'hauteur') IS NOT NULL` s'applique **avant** le JOIN LiDAR. Le LiDAR ne fait que *raffiner* la hauteur des bâtiments **déjà retenus** ; il n'en récupère aucun. Un bâtiment sans hauteur BD TOPO est jeté même si son faîtage LiDAR existe.

### (1) Pourquoi des bâtiments visibles sur l'ortho n'ont pas de volume — trois causes
1. **BD TOPO sans hauteur.** 76 021 bâtiments BD TOPO distincts ont `attrs.hauteur` NULL → exclus par le filtre.
2. **BD TOPO hauteur = 0.** 3 886 lignes `hauteur='0'` passent le filtre mais s'extrudent à plat (volume nul).
3. **CoSIA jamais interrogé.** La couche `batiment_cosia` (445 190 empreintes **détectées sur l'ortho 20 cm**, PVA 2025) n'a **aucune clé de hauteur** (attrs = `classe`, `source_millesime` seulement — vérifié) et **n'est jamais lue** par l'endpoint (`kind='batiment'` uniquement). Or CoSIA *est* par définition le bâti visible sur l'ortho ; dans un échantillon dense de Saint-Denis, ~13 % des empreintes CoSIA n'intersectent **aucun** bâtiment BD TOPO (constructions récentes absentes de BD TOPO) → totalement invisibles en 3D.

### (2) Proportion sans hauteur
La table `batiment` a 24 runs d'ingestion → 817 506 lignes pour **513 930 géométries distinctes** (= bâtiments réels). Sur cette base (vérifié en direct) :

```
distinct_buildings = 513 930 | avec hauteur utilisable = 437 909 | sans = 76 021
```
→ **14,8 % des bâtiments BD TOPO rendables sont sans hauteur** (85,2 % en ont une).

Dénominateur « visible sur l'ortho » (BD TOPO ∪ CoSIA) : CoSIA ajoute ~13 % d'empreintes hors BD TOPO, **toutes sans hauteur** → **~21 % des bâtiments visibles sur l'ortho n'ont aucune hauteur et ne sont pas en 3D** (chiffre prudent ; la part CoSIA hors-BD-TOPO est extrapolée d'un échantillon urbain, à affiner commune par commune).

### (3) Ce qu'il faudrait pour couvrir les manquants
Le gisement de hauteur **existe déjà en base** — c'est surtout un problème de requête :
1. **LiDAR HD déjà ingéré (le plus rentable).** Table `batiment_hauteur_lidar` : **303 452 lignes, 303 396 avec `faitage_m > 0`** (vérifié). L'agent a mesuré que **99,6 % des 116 454 bâtiments BD TOPO sans hauteur sont sur une parcelle qui a déjà un faîtage LiDAR**. Correctif propre : sortir le LiDAR du `WHERE` → `COALESCE(faitage_m, hauteur) IS NOT NULL`. Récupère ~99 % des manquants BD TOPO, hauteur **mesurée**, sans nouvelle ingestion.
2. **CoSIA + LiDAR pour le bâti hors BD TOPO** (les ~13 % vraiment invisibles) : interroger aussi `kind='batiment_cosia'` et dériver la hauteur du MNH LiDAR (MNS−MNT, déjà exploité par `batiment_hauteur_lidar`). Clé géométrique (pas `idu`) + filtrer les slivers (133 281 empreintes <10 m²).
3. **Backfill des 3 886 `hauteur='0'`** via le même COALESCE LiDAR.
4. **Dédoublonnage de `batiment`** (24 runs → 817 506 lignes pour 513 930 géométries) : l'endpoint ne déduplique pas, le `LIMIT 8000`/BBOX est atteint plus vite et des faces se superposent.

**Verdict Q4 :** le gros du manque (cause ①) est un **bug de requête** — le filtre exclut 99,6 % de bâtiments dont la hauteur LiDAR est déjà calculée et à portée de JOIN. Les ~13 % de bâti réellement sans aucune hauteur sont les empreintes **CoSIA hors BD TOPO**, qui, elles, demandent une vraie extension d'ingestion (hauteur LiDAR dérivée par empreinte).

---

## Synthèse des écarts

| # | Question | Écart | Gravité |
|---|---|---|---|
| Q1-③ | Comprendre l'analyse | Exemples du Signal (« succession, société en difficulté ») non représentatifs du modèle q_v15 servi | Modérée |
| Q1-② | Comprendre l'analyse | « Non retenue = aucun droit à bâtir » littéralement vrai mais adossé à un résiduel au faux-négatif connu (`terrain_exigu`) | Nuance |
| Q1-① | Comprendre l'analyse | Accès/terrain présentés comme « contraintes retirées » alors qu'ils sont des coefficients de faisabilité | Mineure |
| Q2-a | Couches | **0/60 couche n'affiche millésime + date au client** (volontairement masqués, PAGE-SOURCES-1) — contraire à l'attendu du mandat | **Forte** |
| Q2-b | Couches | 4 couches cassées : `scot` (exclue), `vefa_neuf` (orpheline de source), `pole_echange` (filtre inopérant), `courbes_niveau`/`enr_habitation` (raster sans millésime) | Moyenne |
| Q2-c | Couches | Millésimes périmés jamais signalés : `dpf` 2006, `trait_de_cote` 2018, `ligne_mt` 2020, `parc_national` 2021, `bruit_carte` 2022, `sar`/`potentiel_foncier` sans millésime ; machinerie de fraîcheur inerte (tout `sans_echeance`) | Moyenne |
| Q2-d | Couches | Décomptes 51/52/55 périmés dans le code (56 est le bon) | Cosmétique |
| Q3 | Ortho | Sert bien le plus récent pour La Réunion (2025) ; couche **codée en dur** + **renommage IGN 2026** (`ORTHO-EXPRESS`→`RVB-EXPRESS`) ⇒ bascule 2026 Réunion non automatique | Faible (latent) |
| Q4 | 3D | ~21 % du bâti visible sur l'ortho sans volume ; cause principale = **bug de requête** (filtre hauteur avant le JOIN LiDAR, 99,6 % récupérables) + CoSIA jamais interrogé | Moyenne |

---

### Fichiers et requêtes de référence
- Q1 : `frontend/src/lib/strings.ts:314`, `config/score_labuse.yaml`, `src/labuse/scoring/signal_mutation.py`, `p_v2/qv15.py`/`qv14.py`/`qv12.py`, `src/labuse/api/app.py:4042-4057`.
- Q2 : `src/labuse/registre/declarations.py` (`couches_carte`), `src/labuse/api/couches_tuyau.py:816` (scot), `src/labuse/api/app.py:7926` (`/map/couches-info`), `frontend/src/components/map/CouchesTuyau.tsx:120,132` (millésime masqué), `declarations/couches/*.yaml`.
- Q3 : `frontend/src/components/map/basemaps.ts`, `src/labuse/api/ortho_proxy.py:53-60` ; sondes WMTS `data.geopf.fr`.
- Q4 : `src/labuse/api/app.py:8186-8223` (filtre fautif), `frontend/src/components/map/MapView.tsx:747-752,1258-1272`, tables `spatial_layers`, `batiment_hauteur_lidar`.

*Fin VERIF-2 — lecture seule, aucune modification de code ni de base.*
