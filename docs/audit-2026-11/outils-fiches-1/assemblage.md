# Assemblage

Clé interne : `assemblage` (num M16) · composant : `frontend/src/components/outils/moteurs.tsx` (`function M16`, ligne 138) · endpoint(s) : `POST /moteurs/assemblage` (principal), `GET /moteurs/assemblage/voisines`, `GET /assemblage/study`, `GET /assemblages`, `GET /moteurs/config`.

---

## 1. À quoi il sert, et pour qui

L'outil répond à la question : « si je réunis ces parcelles contiguës en une seule assiette, qu'est-ce que je peux construire dessus, et combien ça pèse ? ». Il s'adresse à un opérateur foncier (promoteur, aménageur) qui veut savoir si plusieurs parcelles mitoyennes, réunies, débloquent une opération qu'aucune ne porte seule — et qui sont les propriétaires à démarcher.

## 2. Le parcours

Un seul chemin (l'outil est linéaire, pas d'onglets) :

1. **Choisir les parcelles** (étape 1, `moteurs.tsx:214-234`). L'utilisateur ajoute des parcelles soit par l'adresse/omnibox (`EntreeParcelle`, l.215), soit en cliquant la carte en mode assemblage (la couche viole `ile-pick` affiche tous les contours). Chaque parcelle retenue devient une puce retirable (× pour l'enlever). **8 maximum à l'écran** (`ASM_MAX`, servi par `/moteurs/config` → `assemblage_max_ecran=8`). Au-delà, message « 8 parcelles maximum » et la 9ᵉ est refusée (jamais coupée en silence). Bouton « Vérifier l'assemblage (N) » actif dès 2 parcelles.
2. **Résultat** (étape 2). L'appel `POST /moteurs/assemblage` renvoie :
   - **Si non contiguës** (`moteurs.tsx:239-253`) : bandeau rouge « Pas d'assemblage possible : ces parcelles ne se touchent pas » + la liste des parcelles isolées (hors du bloc d'un seul tenant de la 1ʳᵉ). **Rien d'autre** — pas de bilan.
   - **Si contiguës** (`moteurs.tsx:256-449`) : en-tête « N parcelles contiguës », puis deux tuiles (Surface d'assiette ; Bâti conservé + Reconstruction), un accordéon « Bilan » ouvert (charge foncière, prix de sortie, marché de la zone, « prix connu pour N parcelle sur M »), un bloc « approche propriétaire » (personnes morales nommées, particuliers masqués), la liste des parcelles (surface · bâti conservé · reconstruction · propriétaire), et en pied un bouton « Étude de faisabilité de cet assemblage → » qui bascule vers l'outil Étude sur la même sélection.
   - Deux garde-fous affichés : « N parcelles sans droits à bâtir estimés » (si des parcelles n'apportent aucune SDP → bouton « Retirer »), et « Assiette sans capacité » si `sans_potentiel`.

Note : la sélection `msel` ne survit pas à la fermeture de l'outil (purge au démontage, `moteurs.tsx:197`). L'endpoint `GET /assemblage/voisines` (voisines contiguës proposées) **n'est plus appelé par M16** : la section « parcelles voisines » a été retirée (commentaire `moteurs.tsx:150`). `/assemblages` et `/assemblage/study` existent mais ne sont pas consommés par cet écran (study est rejoué par l'outil Étude).

## 3. Les données lues

L'outil ne persiste rien (recalcul à blanc en mémoire). Les tables réellement interrogées par `POST /moteurs/assemblage` et sa chaîne (`src/labuse/api/moteurs.py:203-342`, `src/labuse/assemblage.py`) :

| Donnée | Source (catalogue) | Table SQL lue | Millésime servi | Cadence |
|---|---|---|---|---|
| Géométrie + surface/contenance des parcelles | Cadastre (API Carto PCI) / Cadastre Etalab | `parcels` (`geom_2975`, `surface_m2`, `contenance_m2`) | PCI/Etalab « latest » | — (latest) |
| Contiguïté (contact cadastral 0,5 m) | idem cadastre | `parcels` via `ST_DWithin` (`moteurs.py:220-223`) | idem | — |
| Statut / rang de la parcelle (tier v2) | scoring interne LABUSE (run servi) | `parcel_p_score_v2`, `dryrun_parcel_evaluations` (`moteurs.py:211-212`) | run servi | par run |
| Propriétaire personne morale | DGFiP — parcelles des personnes morales | `parcelle_personne_morale` (`denomination`, `siren`, `groupe_label`) (`moteurs.py:213`) | Panel 2019→2025 (sit. 1ᵉʳ janv.) | annuelle |
| Zonage PLU (U/AU, grèves ER/EBC/PPR/PEB/ravine/DPF/50 pas) | Urbanisme PLU/GPU + prescriptions GPU | `spatial_layers` (kinds `plu_gpu_zone`, `plu_gpu_prescription`, `ppr`, `peb`, `dpf`, `ravine`, `cinquante_pas`) (`assemblage.py:129-172`) | GPU par commune (révisions) | par commune |
| Capacité (SDP) de l'union | moteur de faisabilité interne (`estimate_capacity`) | via `fiche_payload` / `parcel_faisabilite` (`assemblage.py:272, 191`) | calcul live | — |
| Prix de sortie neuf (bilan) | référentiel interne `compute_bilan_servi` | — (dérivé, `assemblage.py:245, 261`) | live | — |
| Prix du terrain nu de la zone (« marché de la zone ») | DVF / valeurs foncières | `dvf_mutations_parcelle` × `parcel_zone_plu` (`marche_commune.py:109-127`) | géo-DVF Etalab 2026-S1 (mesuré : millésime max = 2025 en base) | semestriel |
| SDP résiduelle des voisines (endpoint `voisines`, non affiché par M16) | feature store interne | `p_model_ext_dataset` (année max = 2026) | année de scoring | — |

## 4. Les calculs

Tout le calcul lourd est dans `aggregate_assiette` (`src/labuse/assemblage.py:265-340`) et `_capacite_union` (`:175-262`). **Principe clé** : la capacité n'est PAS la somme des parcelles, mais UN seul calcul sur l'UNION des géométries (une assiette, un moteur, une VRD) — pour ne pas doubler les reculs internes ni multiplier la VRD.

- **Contiguïté** (`moteurs.py:217-234`) : graphe des adjacences (`ST_DWithin` ≤ `ADJ_BUFFER_M`), parcours en profondeur depuis la 1ʳᵉ parcelle ; `contigu = (toutes atteintes)`. L'endpoint `study` utilise une variante : `ST_NumGeometries(ST_Union(ST_Buffer(geom, 0,25))) = 1` (`app.py:8460-8462`).
- **Surface d'assiette** (`assemblage.py:275`) : somme des **contenances cadastrales** (`contenance_m2`) si présentes, sinon surface de dessin. Arrondi à l'entier.
- **Emprise constructible de l'union** (`_EMPRISE_UNION`, `assemblage.py:129-172`) : union des géométries → inset du recul → clip aux zones U/AU → soustraction des grèves (ER, EBC, PPR interdiction, PEB a/b, DPF+3,25 m, ravine+10 m, 50 pas).
- **Part constructible** (`assemblage.py:233-235`) : `part = inset_U/AU ÷ inset_total` ; `pct_hors_zone = round(100·(1−part))`. La surface passée au moteur de capacité est `surface_union × part` (une assiette 40 % hors zone voit son plafond CES réduit d'autant).
- **SDP « terrain libéré »** (`_capacite_union`, `:237, 256`) : capacité BRUTE de l'union (table rase supposée), via `estimate_capacity` (même moteur que la fiche).
- **SDP « bâti conservé » (= valeur par défaut affichée)** (`assemblage.py:315`) : `max(0, sdp_terrain_libere − sdp_existante_totale)`. `sdp_existante_totale` = somme du bâti déjà debout lu par parcelle dans `fiche_payload.residuel` (`:293-302`). **Conséquence importante** : si le bâti existant total dépasse la capacité brute de l'union, le bâti conservé tombe à **0** (observé témoin 1).
- **Gain par défaut** (`moteurs.py:262-267`) : `gain_pct = round((sdp_bati_conserve ÷ meilleure_seule_conservée − 1)·100)`, où `meilleure_seule_conservée = max` des SDP résiduelles par parcelle. Arrondi entier ; ratio à 2 décimales.
- **Bilan** (`_capacite_union:245, 257-261`) : charge foncière et CA via `compute_bilan_servi` (VRD une fois sur l'emprise de l'ensemble) ; prix de sortie via `resolve_prix_sortie_servi`. Servis **uniquement si** le bilan est `fiable`, sinon `None`. `par_m2_terrain = round(charge_foncière_centrale ÷ surface)` (`assemblage.py:317`).
- **Marché de la zone** (`prix_terrain_nu_zone`, `marche_commune.py:80-97`) : médiane €/m² du terrain nu sur la zone **dominante** de l'assiette (la plus fréquente, `moteurs.py:272-278`). `None` hors U/AU ou si `n < SEUIL_TERRAIN_CELLULE_N`.
- **Score d'assemblage** (`moteurs.py:284-286`) : calculé mais **DORMANT** — jamais affiché (doctrine « pas de note /100 »). Sert uniquement `sans_potentiel`.

**Constantes** :

| Constante | Valeur | Fichier:ligne | Origine |
|---|---|---|---|
| `ADJ_BUFFER_M` | 0,5 m | `assemblage.py:17` | Codée en dur (contact cadastral) |
| `assemblage_max_ecran` | 8 | `moteurs.py:57` (défaut), servi par config | `config/moteurs.yaml` (servie) |
| `assemblage_max_parcelles` | 30 | `moteurs.py:58, 195` | `config/moteurs.yaml` (servie) ; plafond API |
| grèves DPF / ravine | +3,25 m / +10 m | `assemblage.py:218-219` | `_layer_params` (config couches) |
| `SEUIL_TERRAIN_CELLULE_N` | (seuil n mini ventes) | `marche_commune.py:43` | Config / codé |
| `min_surface_m2` / `individuel_max_m2` | 1000 / 1000 (**PLACEHOLDER**) | `assemblage.py:25-26` | Hypothèses `plu_zonage.yaml`, marqués PLACEHOLDER ; servent `find_assemblages` (liste `/assemblages`), PAS le calcul SDP de M16 |

Le commentaire « SHAB vendable × rendement 0,8 » (`moteurs.tsx:309`) décrit ce que la SDP **n'est PAS** : aucun rendement 0,8 n'est appliqué ici.

## 5. Chaque chiffre affiché

| Libellé à l'écran | D'où il vient | Sourcé ou estimé |
|---|---|---|
| « N parcelles contiguës » | `n` + `contigu` (graphe adjacence `ST_DWithin`) | sourcé (géométrie cadastre) |
| « Surface d'assiette … m² » | `surface_totale_m2` = Σ contenances cadastrales | sourcé |
| « dont … m² en zone constructible · X % hors zone » | `surface_constructible_m2`, `pct_hors_zone` (clip U/AU) | sourcé (zonage) × géométrie |
| « Bâti conservé : … m² » | `sdp_bati_conserve_m2` = brute − bâti existant | **estimé** (moteur capacité + hypothèse bâti) |
| « Reconstruction : … m² » | `sdp_terrain_libere_m2` (capacité brute, table rase) | **estimé** |
| « * SDP bâti conservé estimée » | `sdp_conserve_estimation` (hypothèse de niveaux) | estimé (signalé) |
| « Charge foncière estimée » + « … €/m² » | `charge_fonciere.central` / `par_m2_terrain` | **estimé** (bilan à rebours) |
| « Prix de sortie … €/m² » | `prix_sortie_eur_m2` (`resolve_prix_sortie_servi`) | **estimé** |
| « Marché de la zone … €/m² · DVF · fiab. X » | `terrain_zone_eur_m2`, `terrain_zone_fiabilite` (médiane DVF) | sourcé (DVF) mais médiane → semi-estimé |
| « Prix connu pour N parcelle sur M » | `n_chiffrables` vs `n` | sourcé (comptage) |
| « ✓ Approche simplifiée — N personnes morales » / « N particuliers » | `n_personnes_morales`, `n_particuliers`, `proprietaires_pm` | sourcé (DGFiP PM) ; particuliers = absence de PM |
| ligne parcelle « surface · bâti conservé · reconstruction » | `items[].surface_m2`, `sdp_residuelle_m2`, `sdp_m2` | surface sourcée ; SDP estimées |
| « N parcelles sans droits à bâtir estimés » | items dont `sdp_m2 ≤ 0` | estimé |
| « Assiette sans capacité » | `sans_potentiel` | estimé |

La tuile « gain / vs meilleure seule » (`gain_pct`, `gain_ratio`) est **calculée mais plus affichée** (retirée RETOURS-25, `moteurs.tsx:202, 326`). Le « nombre de logements » n'est plus servi (LOGEMENTS-SOURCE-UNIQUE : il ne vit que dans l'Étude de faisabilité).

## 6. Les limites

- **Pas de calcul propre** : M16 réutilise intégralement le moteur de faisabilité/gabarit (`estimate_capacity`, `compute_bilan_servi`). Toute erreur du moteur de capacité se propage ici.
- **Bâti conservé = 0 trompeur** : quand le bâti existant total dépasse la capacité brute de l'union, le bâti conservé affiché est 0 et le gain devient −100 % (témoin 1), alors que la « Reconstruction » (table rase) montre une capacité positive. L'écran garde les deux, mais le chiffre de tête peut surprendre.
- **Zone dominante seule pour le marché** : le « marché de la zone » est pris sur la zone la plus fréquente de l'assiette ; une assiette mixte (`zones_mixtes=true`, témoin 3) affiche un seul prix qui ne couvre pas toutes les zones.
- **Contiguïté = contact cadastral uniquement** : le domaine public non cadastré (une route > 0,5 m) coupe l'anneau par construction (`moteurs.py:347-348`). Deux parcelles séparées par une rue sont déclarées non contiguës même si l'opération est réaliste.
- **Indivision non détectable** : `indivision_detectable` toujours `False` (`moteurs.py:332`) — aucune structure de propriété physique en open data ; les particuliers ne sont jamais nommés ni regroupés.
- **Aucun accord ni faisabilité réglementaire vérifiés** : la `note_sdp` le dit (« Accords, propriétaires et faisabilité restent à vérifier »).
- **Plafond 8 à l'écran / 30 API** : au-delà de 30, assiette tronquée (dit à l'écran, `tronquee`).

## 7. Les tests

- **`tests/test_assemblage.py`** (Python) garantit : une paire contiguë franchit le seuil (`:20`) ; une parcelle seule déjà au-dessus du seuil ne crée pas d'assemblage (`:32`) ; parcelles non contiguës → pas de paire (`:39`) ; l'endpoint `POST /moteurs/assemblage` ne lève pas et valide ses garde-fous : 422 si < 2, 404 si < 2 trouvées, `sans_potentiel`/`score=0` sans faisabilité, présence de `note_sdp`/`UNION`, `sdp_combinee_m2 == sdp_bati_conserve_m2` (`:47-82`) ; `aggregate_assiette` calcule bien sur l'UNION (`sdp_m2 ≥ somme des parts`, assiette = « union », emprise > 0, `:87-123`).
- **`frontend/src/components/outils/Assemblage.test.tsx`** garantit : en-tête « N contiguës » sans doublon de surface + 2 KPI (`:51`) ; charge négative en rouge + bilan « marché de la zone » (`:61`) ; non contigu → « pas d'assemblage possible » + isolées, pas de bilan (`:71`) ; tuile « Bâti conservé » + « Reconstruction » (`:82`) ; plus de bouton Courrier (`:97`) ; plafond 8 (`:102`).
- **Ce qu'aucun test ne vérifie** : l'exactitude numérique de la SDP/charge foncière/prix (valeurs du moteur non assertées sur des chiffres connus) ; le cas « bâti conservé = 0 alors que reconstruction > 0 » ; la cohérence du « marché de la zone » quand `zones_mixtes=true` ; que `study` et `POST /assemblage` renvoient bien les mêmes chiffres (ils partagent `aggregate_assiette` mais aucun test croisé ne le prouve — vérifié manuellement ici, cf. §9).

## 8. Les documents liés (PDF, exports)

L'écran Assemblage **n'a pas d'export PDF propre**. Le seul « document lié » est le pont « Étude de faisabilité de cet assemblage → » (`moteurs.tsx:442-446`) qui rejoue la même sélection dans l'outil Étude ; celui-ci appelle `GET /assemblage/study` qui lit **exactement le même** `aggregate_assiette` (`app.py:8463`) que `POST /moteurs/assemblage`. Vérifié (§9) : `study` renvoie `surface_cumulee_m2`, `pct_hors_zone`, `ca`, `charge_fonciere` identiques ; son `capacite.sdp_m2` expose la SDP brute (terrain libéré), tandis que l'écran M16 affiche par défaut le bâti conservé — même source, grandeur affichée différente.

## 9. Trois cas rejoués

Serveur `http://127.0.0.1:7300`, `POST /moteurs/assemblage`. (Le port a redémarré en cours de session ; chiffres obtenus après redémarrage.)

**Cas 1 — Saint-Denis, parcelle témoin `97411000BZ1065` + voisines `BZ1066` + `BZ1288`** (voisines trouvées via `GET /moteurs/assemblage/voisines?idu=97411000BZ1065`, 5 voisines, 0 même propriétaire, toutes « particulier », zone Uh) :
- Entrée : `{"idus":["97411000BZ1065","97411000BZ1066","97411000BZ1288"]}`
- Sortie : `n=3, contigu=true, surface_totale_m2=2768, pct_hors_zone=0`, `sdp_bati_conserve_m2=0`, `sdp_terrain_libere_m2=372`, `sdp_existante_totale_m2=571`, `gain_pct=-100`, `ca.central=889200`, `charge_fonciere.central=-57516` (−21 €/m²), `prix_sortie_eur_m2=4275`, `terrain_zone_eur_m2=482` (fiab. moyenne, n=1254), `n_particuliers=3`, `score=61`. **Le bâti conservé est 0** (terrain libéré 372 < existant 571) alors que la reconstruction vaut 372.

**Cas 2 — Saint-André, témoin `97409000AK0804` + voisines `AK0907` + `AK0908`** :
- Entrée : `{"idus":["97409000AK0804","97409000AK0907","97409000AK0908"]}`
- Sortie : `n=3, contigu=true, surface_totale_m2=28736, pct_hors_zone=0`, `sdp_bati_conserve_m2=36101`, `sdp_terrain_libere_m2=36669`, `gain_pct=5`, `ca.central=110771000`, `charge_fonciere.central=207000` (+7 €/m²), `prix_sortie_eur_m2=4375`, `terrain_zone_eur_m2=264`, `n_personnes_morales=1` (COMMUNE DE SAINT ANDRE, SIREN 219740099), `n_particuliers=2`, `score=83`. Assiette dominée par la grande parcelle communale (27 862 m²).

**Cas 3 — Saint-Pierre, témoin `97415000DH0076` + voisines `DH0119` + `DH0120`** :
- Entrée : `{"idus":["97415000DH0076","97415000DH0119","97415000DH0120"]}`
- Sortie : `n=3, contigu=true, surface_totale_m2=21832, pct_hors_zone=0`, **`zones_mixtes=true`**, `sdp_bati_conserve_m2=29635`, `sdp_terrain_libere_m2=34110`, `sdp_existante_totale_m2=4475`, `gain_pct=13`, `ca.central=60014074`, `charge_fonciere.central=-2420680` (−111 €/m²), `prix_sortie_eur_m2=4730`, `terrain_zone_eur_m2=479`, `n_personnes_morales=2` (ETAT PAR DIRECTION DE L IMMOBILIER DE L ETAT ; SOCIETE D'EQUIPEMENT DU DEPARTEMENT DE LA REUNION), `n_particuliers=1`, `score=83`. Illustre `zones_mixtes=true` **avec** `pct_hors_zone=0` (mixité U/sous-zones, pas de hors-zone).

**Contrôle non contigu** : `{"idus":["97411000BZ1065","97415000DH0120"]}` (communes différentes) → `contigu=false, isolees=["97415000DH0120"]`, pas de bilan.

**Contrôle study (parité PDF)** : `GET /assemblage/study?idus=97411000BZ1065,97411000BZ1066,97411000BZ1288` → `surface_cumulee_m2=2768`, `pct_hors_zone=0`, `capacite.sdp_m2=372`, `ca.central=889200`, `charge_fonciere.central=-57516` — **identiques** à `POST /moteurs/assemblage` du cas 1 (même `aggregate_assiette`).

## 10. Tes doutes

1. **(grave) « Bâti conservé = 0 » peut faire conclure à tort « rien à faire ».** Quand le bâti existant total dépasse la capacité brute (témoin 1 : existant 571 > brute 372), la grandeur de tête affiche 0 m² et un gain de −100 %, alors qu'une reconstruction (table rase) libère 372 m². Le chiffre le plus visible est le plus pessimiste, et le `sdp_existante_totale` qui l'explique n'est pas montré à l'écran. Aucun test ne couvre ce cas.
2. **(moyen) « Marché de la zone » sur la zone dominante seule, même en assiette mixte.** Témoin 3 : `zones_mixtes=true` mais un seul prix (479 €/m²) est affiché, couvrant la seule zone majoritaire. L'utilisateur peut croire que ce prix vaut pour toute l'assiette.
3. **(moyen) SDP et charge foncière ne sont testées sur aucune valeur connue.** Les tests prouvent la plomberie (union, garde-fous, présence de champs) mais pas l'exactitude des chiffres centraux. Une dérive du moteur de capacité passerait inaperçue.
4. **(moyen) Médiane DVF présentée comme « sourcée ».** `terrain_zone_eur_m2` vient de DVF (sourcé) mais c'est une médiane par zone sur n ventes (n=1254, 522, 1531 dans les témoins) ; la fiabilité « moyenne » est affichée, mais le chiffre reste une statistique, pas le prix de l'assiette.
5. **(mineur) `zones_mixtes=true` avec `pct_hors_zone=0`** (témoin 3) peut sembler contradictoire : la mixité est U/sous-zones constructibles, pas du hors-zone. Rien de faux, mais deux indicateurs qui méritent une lecture attentive côté utilisateur.

---

### Synthèse INDEX

- Fiche écrite : `docs/audit-2026-11/outils-fiches-1/assemblage.md`.
- Outil `assemblage` (M16) : réunit 2–8 parcelles contiguës (plafond API 30) et calcule capacité + bilan sur l'UNION des géométries (un seul passage du moteur de faisabilité, une seule VRD), jamais la somme des parcelles. Endpoint principal `POST /moteurs/assemblage` ; `aggregate_assiette` (`assemblage.py:265`) partagé avec `/assemblage/study`.
- Données sourcées : géométrie/contenance (`parcels`, cadastre PCI/Etalab latest), zonage PLU/grèves (`spatial_layers` GPU), propriétaire PM (`parcelle_personne_morale`, DGFiP 2019→2025), marché terrain nu (`dvf_mutations_parcelle`, DVF Etalab 2026-S1).
- Données estimées : toutes les SDP (bâti conservé, reconstruction), charge foncière, prix de sortie, score dormant — issues du moteur de capacité/bilan à rebours.
- Part sourcé vs estimé : surface d'assiette, contiguïté, % hors zone, propriétaires et marché DVF = **sourcés** (≈ 40 %) ; tous les chiffres de capacité et de bilan (les plus mis en avant) = **estimés** (≈ 60 %).
- 3 cas rejoués (réels, après redémarrage du serveur 7300) : témoin 1 SD (BZ1065+BZ1066+BZ1288) bâti conservé 0 / reconstruction 372 ; témoin 2 SA (AK0804…) 36 101 m² gain +5 % ; témoin 3 SP (DH0076…) 29 635 m² `zones_mixtes=true`. Parité `study` vérifiée.
- Constante `ADJ_BUFFER_M=0,5 m` (dur, `assemblage.py:17`) ; plafonds 8/30 servis par `config/moteurs.yaml`.
- Doute le plus grave : le « Bâti conservé = 0 » (quand bâti existant > capacité brute, témoin 1) met en avant le chiffre le plus pessimiste et masque le `sdp_existante` qui l'explique — risque de conclure « rien à faire » alors que la reconstruction libère de la SDP. Aucun test ne couvre ce cas.
