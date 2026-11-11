# Prospection solaire

Clé interne : `prospection-solaire` (num M26) · composant : `frontend/src/components/outils/ProspectionSolaire.tsx` · endpoints : `GET /modules/prospection-piscines` (+ `/points`, `/parcelles`, `/liste`, `POST /pas-une-piscine`) et `GET /modules/prospection-solaire/parcelle/{idu}`. L'ancien `GET /modules/prospection-solaire` (liste + CSV) existe encore côté back mais n'est PLUS appelé par le composant refondu (voir §6).

L'outil a **deux chemins** choisis sur l'écran d'entrée (`ProspectionSolaire.tsx:49-71`) : **Piscines** (métier pisciniste) et **Ensoleillement** (métier installateur PV). Les rubriques ci-dessous font une sous-section par chemin quand c'est utile.

---

## 1. À quoi il sert, et pour qui
Deux outils de prospection commerciale dans un seul menu : côté **Piscines**, un pisciniste voit combien de piscines sont détectées par commune et la liste des parcelles concernées (rénovation, couverture, entretien) ; côté **Ensoleillement**, un installateur photovoltaïque ouvre la « fiche soleil » d'une parcelle (potentiel kWh/kWc, toiture, orientation, profil mensuel). C'est de la **restitution de données gelées** — aucun recalcul au clic (en-tête du composant, lignes 8-14).

## 2. Le parcours

### Chemin Piscines (pisciniste)
- **Écran d'entrée** : deux cartes « 💧 Piscines » / « ☀️ Ensoleillement » (`ProspectionSolaire.tsx:66-67`).
- **Étape 1 · Périmètre** (`:156-188`) : liste « Toute l'île » + les 24 communes, chacune avec son compteur de piscines à côté. Chargée une fois par `getPiscinesAgregat` (`:112`).
- **Résultat** (`:193-246`) : un gros compteur « N piscines à <commune / La Réunion » (`:204`), la carte à droite peinte avec les piscines du périmètre (`getPiscinesParcelles`, `:142`), puis une liste paginée par 200 (`getPiscinesListe`, `:124-130`) — chaque ligne = `IDU · commune · « Fiche → »`, clic → fiche parcelle (`:219`). Le statut (« confirmée / à confirmer ») est volontairement masqué à l'écran : une seule catégorie « Piscines » affichée (`:148-154`).

### Chemin Ensoleillement (installateur PV)
- **Barre unique** : l'utilisateur désigne UNE parcelle (saisie d'adresse/IDU via `EntreeParcelle`, ou clic carte adopté via `selectedIdu`, `:252-285`). Pas de liste globale ni de classement (l'onglet « Top parcelles » a été retiré, `:250-251`).
- **Fiche soleil** (`FicheSoleil`, `:346-435`) : grille de tuiles (Potentiel, Toiture, Puissance installable, Production annuelle, Orientation, Nature du toit, Pente du terrain, Pente du toit), une photo aérienne du toit (ortho IGN WMS) avec rosace d'orientation (`:385-399`), un éventuel bandeau « zone d'exclusion EnR au sol » (loi APER, `:402-408`), un éventuel bandeau « piscine détectée » (`:411-415`), et un **profil mensuel 12 barres** (`:416-427`). Chaque tuile porte une pastille **Sourcé** ou **Estimé** (`ProvTag`, `:298-303`).

## 3. Les données lues

Toutes les données solaires sont **gelées** (bâties par un run du builder, pas recalculées à la demande). Le millésime affiché est celui réellement en base (`parcel_solar.source_millesime`).

| Source (nom catalogue) | Table SQL lue | Millésime servi (data_sources / base) | Cadence |
|---|---|---|---|
| PVGIS (Commission européenne) | `parcel_solar.prod_spec_kwh_kwc`, `prod_mensuel`, `mois_optimal` (interpolées depuis `solar_grid`) | `PVGIS v5_3 · SARAH3 · relevé 2026-08-23` (en base, witnesses) ; catalogue : « PVGIS v5.3 · modèle SARAH3 (relevé au run du builder) » | aucune (gelé) |
| RGE ALTI (altimétrie) | `parcel_terrain.pente_moy_deg` (→ « Pente du terrain ») | « RGE ALTI® (IGN) — édition non enregistrée » | — |
| LiDAR HD — MNH 50 cm (IGN) | `toiture_lidar` (cache) via WMS `IGNF_LIDAR-HD_MNH_...` → nature + pente du toit | « Survol 11/08–11/10/2023 » | à la demande + cache |
| BD ORTHO 20 cm (IGN) / CoSIA | `piscines` (statut servie/à confirmer) + `parcel_equipements` | « BD ORTHO IGN 974 — millésime 2025 (piscine, 90,7 %) » ; « CoSIA 2025 (PVA juil.-août 2025, 20 cm) » | pluriannuelle |
| (bâti) spatial_layers / BD TOPO | `p_model_bati.emprise_bati_m2` (→ « Toiture (emprise) »), `spatial_layers kind='batiment'` (→ azimut) | — | — |
| Filosofi / INSEE logement | `filosofi_carreaux_200m`, `commune_insee_logement`, `dvf_mutations_parcelle` (→ proba propriétaire-occupant, non affichée dans la fiche soleil) | — | — |

Détection piscines : la fiche soleil lit la source **unique** `piscines` (statut `servie`, corrections exclues) + `parcel_equipements` (`modules.py:1033-1037`). Le compteur/liste du chemin Piscines lit **uniquement** `piscines` via `compte_piscines` (`modules.py:1327-1328`).

## 4. Les calculs

**Potentiel (kWh/kWc/an)** — SOURCÉ PVGIS, interpolé spatialement.
- Le builder appelle l'API PVGIS `PVcalc` v5.3 sur une grille carrée de pas **400 m** (`solaire.yaml grid_step_m`), avec `peakpower=1 kWc`, `loss=14 %`, `angle=15°`, `aspect=180°` (plein nord = hémisphère sud), `usehorizon=1` (`solaire.py:129-131`). Le fetch renvoie l'annuel E_y et 12 E_m (`:143-147`).
- Chaque parcelle reçoit le productible par **interpolation IDW** (pondérée par l'inverse de la distance) des **4 points de grille les plus proches** (`solaire.py:209-218`). Le profil mensuel et le mois optimal viennent du **point le plus proche** sans interpolation (`:227-238`). Arrondi affiché : entier (`round(prod_spec)::int`, `modules.py:1028`).

**Puissance installable (kWc)** — ESTIMÉ, servi par le back (`modules.py:1077-1079`) :
`kWc = emprise toit (m²) × kwc_par_m2`, avec `kwc_par_m2 = 0.2` (constante config, `config/prospection_solaire.yaml:6`, hypothèse métier codée). Arrondi 1 décimale.

**Production annuelle (kWh/an)** — ESTIMÉ (`modules.py:1080`) :
`prod_annuel = kWc × productible PVGIS`, arrondi entier. (Composition de deux estimés.)

**Orientation du bâti (azimut)** — ESTIMÉ (`solaire.py:263-292`) :
azimut du grand côté du **rectangle englobant orienté** (`ST_OrientedEnvelope`) du bâtiment principal de la parcelle (celui qui intersecte le plus), modulo 180°, arrondi 0,1°. Confiance `haute` si l'élongation L/l > 1,4 (`azimut_elongation_min`), sinon `basse` (`:289`).

**Pente du terrain** — SOURCÉ : `parcel_terrain.pente_moy_deg` (origine RGE ALTI, `circuit_garanties.py:269`), arrondi 1 décimale. NB : la fiche prévient que « pente du terrain ≠ pente du toit » (`ProspectionSolaire.tsx:396`).

**Nature + pente du toit** — Dérivé LiDAR (`solaire_toiture.py`) : pente et orientation par pixel sur l'emprise bâtie (MNH 50 cm) ; < 15 % de pixels pentus → plat, 1 pic → monopente, 2 pics opposés → double pente, 2 perpendiculaires/3+ → croupe/complexe (`:8-19`). **Seuil de confiance 0,70** (`SEUIL_CONFIANCE`, `solaire_toiture.py:41`) : sous le seuil, le verdict n'est PAS servi (« non déterminée — pans non nets ») ; un échec technique devient « non calculée — LiDAR indisponible », jamais une absence (`:47-80`). Calcul à la demande, mis en cache (table `toiture_lidar`).

**Flags** : `flag_topo_ombrage` = productible < 0,80 × médiane communale (`solaire.py:246-256`) ; `flag_ombrage_vegetal` = canopée sur bâti ≥ 40 % (`:318-323`) ; la fiche n'affiche qu'un `ombrage` booléen agrégé (OU des deux, `modules.py:1065`), mais aucune tuile « ombrage » n'est rendue dans la grille (champ servi, non peint par la V1 actuelle).

## 5. Chaque chiffre affiché (chemin Ensoleillement — fiche soleil)

| Libellé à l'écran | D'où il vient | Sourcé ou estimé |
|---|---|---|
| Potentiel (kWh/kWc/an) | `parcel_solar.prod_spec_kwh_kwc` interpolé IDW (PVGIS SARAH3) | Sourcé (pastille écran : **Estimé**, car modélisé PVGIS) |
| Toiture (emprise, m²) | `p_model_bati.emprise_bati_m2` | Sourcé |
| Puissance installable (kWc) | emprise × 0,2 kWc/m² | Estimé |
| Production annuelle (kWh/an) | kWc × potentiel | Estimé |
| Orientation du bâti (°) | `ST_OrientedEnvelope` du bâti | Estimé |
| Nature du toit | `toiture_lidar.verdict` (LiDAR MNH) si confiance ≥ 0,70 | Estimé (Dérivé) |
| Pente du terrain (°) | `parcel_terrain.pente_moy_deg` (RGE ALTI) | Sourcé |
| Pente du toit médiane (°) | `toiture_lidar.pente_mediane_deg` | Sourcé (pastille écran : **Sourcé**) |
| Profil mensuel (12 barres) | `parcel_solar.prod_mensuel` (point de grille le plus proche) | Sourcé (modélisé PVGIS) |
| « Piscine détectée » | `EXISTS` dans `piscines` statut servie, corrections exclues | Sourcé |
| Compteur piscines (chemin Piscines) | `compte_piscines` sur table `piscines` | Sourcé |

Nuance honnête : l'écran étiquette le **potentiel PVGIS** comme « Estimé » (c'est un modèle), alors que la tuile « Toiture » et les deux pentes sont « Sourcé ». La frontière suivie est : *mesuré/relevé* = Sourcé ; *modélisé* (PVGIS, dimensionnement, azimut d'enveloppe) = Estimé (`ProspectionSolaire.tsx:295-297`).

## 6. Les limites
- **Ombrage de proximité non modélisé** : PVGIS intègre l'horizon topographique (`usehorizon=1`) mais pas l'ombre du bâti/arbres voisins ; le bandeau le dit (`modules.py:986-987`). Potentiel « théorique à confirmer sur site ».
- **Maille PVGIS 400 m** : deux parcelles voisines partagent le même potentiel au mètre près ; le classement « potentiel » seul ne départage rien (commentaire `modules.py:908-914`).
- **Puissance/production = double hypothèse** : `kWc = toit × 0,2` suppose que toute l'emprise bâtie est exploitable et qu'un ratio uniforme vaut partout. Pour la parcelle témoin DH0076 (toit 5 342 m²), cela donne **1 068 kWc / 1 379 304 kWh/an**, chiffres à prendre comme ordre de grandeur, pas comme un dimensionnement de projet.
- **Azimut = forme du bâti**, pas une orientation optimale de panneaux ; l'inclinaison optimale n'est pas servie (jamais inventée, `ProspectionSolaire.tsx:367-369`). Confiance souvent « basse » (2 des 3 témoins).
- **Nature du toit rarement servie** : au seuil 0,70, ~36 % des toits seulement sont classés (docstring `solaire_toiture.py:17`) ; les autres restent « non déterminée ».
- **Détection piscines imparfaite** : statut `servie` ≈ ≥ 85 % de précision, « à confirmer » 30–60 % (`modules.py:1345-1347`) ; l'absence de piscine n'est PAS vérifiée hors zones scannées. 26 234 détections sont en statut `ecartee` (non servies).
- **Données gelées** : aucun rafraîchissement automatique ; une construction/démolition récente n'est pas vue.
- **Liste/CSV solaire orphelins** : `GET /modules/prospection-solaire` (liste triée par potentiel + export CSV de démarchage, `modules.py:894-1015`) existe toujours mais le composant refondu ne l'appelle plus — c'est du code mort côté écran.

## 7. Les tests
- **Front** `frontend/src/components/outils/ProspectionSolaire.test.tsx` (7 it dans `describe('SOLAIRE — deux modes')`) : garantit les deux cartes d'entrée sans pied de sources (`:73-78`), l'étape Périmètre avec les communes (`:81-88`), le total unique sans mention de statut (`:91-99`), la source « IGN FLAIR et CoSIA » et **zéro potentiel solaire dans le chemin Piscines** (`:104-112`), la fiche soleil avec 12 barres et unité « kWh/kWc/an » (`:115-122`), le retrait des deux paragraphes sous le graphe (`:125-134`), et que kWc/production viennent du back (`:137-142`). Tout est sur **mocks** (`mockFetch`, `:52`).
- **Back** `tests/test_solaire.py` : vérifie la config (`aspect_deg=180`, `grid_step_m=400`, millésime « PVGIS…SARAH3 », `:15-21`) et le **schéma** de `parcel_solar` (14 colonnes, proxys abandonnés absents, `:25-36`). C'est un test de contrat de schéma, pas de valeurs.
- **Ce qu'aucun test ne vérifie** : la justesse de l'interpolation IDW, le calcul `kWc = toit × 0,2` sur une vraie parcelle, l'azimut `ST_OrientedEnvelope`, le seuil toiture 0,70 sur une parcelle réelle, les endpoints `/prospection-piscines/*` (aucun test d'intégration back trouvé pour ces routes), et la cohérence écran ↔ PDF (§8).

## 8. Les documents liés (PDF, exports)
La fiche soleil de l'outil **n'a pas d'export propre** (le lien « Ouvrir la fiche complète » et le CSV de démarchage ont été retirés). Le PDF/fiche du bien affiche une **note solaire indépendante** via `faisabilite/viabilisation_build.solaire_note` (`viabilisation_build.py:130-155`), appelée par `flash/data.py:744-747`. Elle lit **la même table** `parcel_solar.prod_spec_kwh_kwc`, donc **le même productible** — mais **arrondi différemment** : le PDF arrondit à la dizaine (`~1 430 kWh/kWc/an`, `viabilisation_build.py:148`) et ajoute une qualité (« favorable / très favorable » au seuil 1500), là où l'écran de l'outil montre l'entier exact (ex. 1548). Même donnée source, présentation (arrondi + libellé) différente. Le PDF n'expose ni kWc, ni production annuelle, ni le profil mensuel. La pente/nature du toit du PDF passent par d'autres extracteurs (`oracle_dossier.py:42-43`, `le_bien.toit.*`), distincts de `toiture_lidar` de l'outil.

## 9. Trois cas rejoués (`GET /modules/prospection-solaire/parcelle/{idu}`, sorties réelles)

Les 3 témoins ont bien une fiche soleil (chemin Ensoleillement = par parcelle, adapté : le chemin Piscines est par commune, pas par parcelle). DH0076 est en commune **Saint-Paul** (pas Saint-Pierre/-Joseph comme le briefing le suppose) — je garde le témoin et le signale.

| IDU (commune) | Potentiel | Toiture | kWc / Prod. an | Azimut (conf.) | Pente terrain | Nature toit (conf.) | Piscine |
|---|---|---|---|---|---|---|---|
| 97411000BZ1065 (Saint-Denis) | 1548 kWh/kWc/an | 197 m² | 39,4 kWc / 60 991 kWh/an | 65° (basse) | 13,8° | simple pente (0,757 ≥ 0,70) | non |
| 97409000AK0804 (Saint-André) | 1571 kWh/kWc/an | 225 m² | 45,0 kWc / 70 695 kWh/an | 125° (basse) | 3,6° | non calculée — LiDAR indisponible | non |
| 97415000DH0076 (Saint-Paul) | 1291 kWh/kWc/an | 5342 m² | 1068,4 kWc / 1 379 304 kWh/an | 160° (haute) | 1,1° | non déterminée — pans non nets (0,637 < 0,70) | oui (145 m²) |

Vérif base : `parcel_solar` → les 3 portent `source_millesime = PVGIS v5_3 · SARAH3 · relevé 2026-08-23` ; productible/azimut/pente/toit correspondent exactement aux valeurs servies (ex. BZ1065 : prod 1548,4 · az 65,1 basse · pente 13,8 · toit 197). Les 3 cas illustrent les **trois états** de la nature du toit (servi / indisponible / non déterminé). Chemin Piscines rejoué : `GET /prospection-piscines` → total île **12 561** piscines, Saint-Paul 2 379 confirmées / 1 723 à confirmer (base : `piscines` servie = 12 576, a_confirmer = 11 706, ecartee = 26 234).

## 10. Tes doutes (par gravité)

1. **« Puissance installable » et « production annuelle » risquent d'être lues comme un dimensionnement crédible** alors que c'est `toit × 0,2` sans tenir compte de la part réellement exploitable, des masques ni des pans. DH0076 affiche « 1 068 kWc / 1,38 GWh/an » : impressionnant et faux comme chiffre de projet. La pastille « Estimé » et la phrase d'hypothèse (`:378-380`) atténuent, mais ne cadrent pas la grandeur.
2. **Le productible est étiqueté « Estimé » à l'écran mais décrit « Sourcé » dans l'en-tête code** (`:295-296` : « potentiel PVGIS » dans les Estimé, mais prose « productible SOURCÉ PVGIS » dans `solaire_note`). Incohérence de vocabulaire entre outil et PDF sur la même donnée — plus l'arrondi différent (entier à l'écran, dizaine au PDF).
3. **Aucun test ne couvre les endpoints piscines ni les valeurs calculées** (IDW, azimut, kWc, seuil toiture). Les seuls tests valident config + schéma. Une régression de calcul passerait inaperçue.
4. **L'azimut est souvent de confiance « basse »** (2/3 témoins) et mesure la forme du bâti, pas l'orientation des panneaux ; affiché sans l'avertissement de confiance dans la tuile (seule la rosace le montre implicitement). Peut induire en erreur sur un bâti peu allongé.
5. **Témoin DH0076 en Saint-Paul**, pas en secteur sud comme attendu, avec un toit de 5 342 m² (bâtiment atypique, pas une maison) — à garder en tête : l'outil ne distingue pas maison / grand bâti, donc la fiche « potentiel » peut porter sur un entrepôt.
