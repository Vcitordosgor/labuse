# RETOURS-15 — recette Vic du 27/09/2026 (socle S1–S5 · B1–B9 · C1–C10)

Branche `fix/retours-15` depuis `origin/main` (`e9dda49f`). Un commit par point.
Vérifs : `tsc` · `vite build` · `vitest` (198 P) · `pytest` (back touché). **Pas de merge.**

DA : `CHARTE-DA-1.md`, composants `components/ui/` (Bouton, Chip, Chevron, Retour, Case, Badge).

---

## PARTIE A — le socle (comportements partagés)

- **S1** — La suggestion cliquée remplit le champ de son **libellé complet** : `AddressAutocomplete.pick`
  recopie déjà `it.label` (adresse, IDU, propriétaire, lieu-dit) ; les 3 barres (ParcelInput, omnibox
  header, AddressAutocomplete) partagent ce chemin. Test-garde ajouté (`socle.test.tsx`).
- **S2** — `ParcelInput` : le bouton **« Utiliser la parcelle sélectionnée »** est supprimé partout ;
  l'invite « ou cliquez une parcelle sur la carte » **disparaît** dès qu'une parcelle est résolue par la
  barre (réapparaît si le champ est vidé). Grep « Utiliser la parcelle » = 0 (hors commentaires/tests).
- **S3** — `focusParcelle(idu, { fiche })` : zoom + contour surligné (liseré Ortho, `cible =
  selectedIdu ?? focusIdu`) + ouverture de la fiche quand `fiche:true`. Rétro-compatible.
- **S4** — Le clic carte agit directement : `ParcelInput` auto-consomme toute nouvelle sélection carte
  (→ Taxe, Solaire, Étude, Temps, Courrier, Pièges, Gabarit) ; Assemblage (`setMsel`) et Comparer
  (`addToCompare`) agissaient déjà au handler MapView. Plus d'étape « Utiliser… ».
- **S5** — La **« pilule vide »** = l'indicateur de chargement carte (pastille `rounded-full` de largeur
  fixe ne contenant qu'un Squelette dont le message était en aria seulement). Il affiche désormais son
  **message en clair** (« Chargement des parcelles… »), pastille dimensionnée à son contenu (194×31).

## PARTIE B — outils (1re moitié)

- **B1 Permis** — légende « Permis (par état) » retirée de la carte ; le bloc « N permis à moins de 200 m »
  devient un **accordéon** (Chevron, ouvert par défaut, repliable) ; « effacer » retiré (vider le champ
  suffit → `onClear`). Résolution → `focusParcelle` (zoom + contour), déjà en place.
- **B2 Communes comparateur** — colonne **« Parcelles à potentiel »** retirée (classement LABUSE, hors
  périmètre) ; tri par défaut → permis (5 ans). Fiche commune : ligne « N parcelles promues » retirée du
  sous-titre Foncier.
- **B3 Évolution du marché** — voir « cause des trimestres vides » ci-dessous. Pied « … +N %/an » retiré.
- **B4 Acquisitions récentes** — clic parcelle → `focusParcelle(idu, {fiche})`. Voir « deux chiffres » ci-dessous.
- **B5 Scan patrimoine** — **deux portes** (Un propriétaire · Toutes les opérations de l'île) ; 4 chiffres
  factuels (Parcelles · Surface totale ha · Terrains nus / bâtis · En zone U ou AU) ; « actionnables » et
  « valorisation » retirés du titre ; accordéon « Détail et méthode » retiré ; onglet Construction : le
  badge = les opérations servies (plus opérations+programmes). **Compte réconcilié** : la suggestion
  propriétaire comptait 1871 (lignes MAJIC) vs 1833 à l'outil → `autocomplete` JOIN parcels TOUJOURS →
  **un seul chiffre 1833** (CBO TERRITORIA : 1833 parcelles · 2560 ha · 994 nus / 839 bâtis · 952 en U/AU).
- **B6 Assemblage** — clic carte = ajout direct (S4) ; cases à cocher des voisines + « ses voisines → »
  retirées ; liste des voisines en lecture (pastille « dans l'assiette »).
- **B7 Comparer** — tableau élargi (880 → 1240 px) ; libellés et valeurs sur une ligne (whitespace-nowrap).
- **B8 Pièges et risques** — mode « Un lot » retiré (une parcelle seulement) ; « Ouvrir la fiche → » retiré
  (la fiche s'ouvre au clic carte) ; clic carte analyse directement.
- **B9 Étude de zone** — **ampleur par RAYON en km par défaut** (0,5 · 1 · 2 · 5, cercle exact ST_Buffer
  server-side), option secondaire « ou en temps de trajet » (5/10/15 min à pied/voiture). Vérifié : rayon
  1 km = 312 ha, `entree='rayon'`.

## PARTIE C — outils (2e moitié)

- **C1 PLU** — bouton « ← Voies » retiré. Audit PLU ci-dessous.
- **C2 Remonter le temps** — parcellaire + contours de l'accueil Ortho (tuiles `parcels-ile`) sur les deux
  fonds ; millésimes en **Chip** (1950 · 1980 · 2000 · 2006 · 2011 · 2016 · 2021 · Aujourd'hui) ; frise du
  bas retirée ; comparateur à poignée conservé.
- **C3 Faisabilité** — 3 vraies hypothèses seulement (occupation · rendement · surface/logt) ; hauteur de
  niveau, densité, places (fixées par le PLU) retirées des champs éditables. Sources ci-dessous.
- **C4 Gabarit** — SUP au catalogue (1 ligne). Cause ci-dessous.
- **C5 Taxe** — bloc « SDP restante au gabarit » retiré ; résolution → `focusParcelle(fiche)`. Calcul vérifié ci-dessous.
- **C6 Piscines** — parcours refondu (encart · commune · « Voir les piscines » → liste + points goutte,
  clic ligne → fiche) ; courrier/surface/propriétaire retirés. Données ci-dessous.
- **C7 Ensoleillement** — socle S2 en place. Sources ci-dessous.
- **C8 Successions** — filtre « Résiduel minimum (SDP) » retiré ; clic ligne → `focusParcelle(fiche)`. 3 témoins ci-dessous.
- **C9 Blocs ↔ Scan** — deux ponts : Blocs → Scan (déjà en place) ; Scan Possession → « Blocs contigus : N »
  (même moteur `parcel_blocs`, CBO = 209 blocs).
- **C10 Fiche commune** — tuile « Densifier » retirée ; sections fermées par défaut ; « Voir ses parcelles » retiré.

---

## Audit PLU (C1) — le dernier PLU approuvé est bien servi

Les 3 communes « en révision » sont code_etat Sudocuh **33 = PLU approuvé, révision de PLU en cours
(compétence commune)**. Le **zonage ET le règlement servis** sont ceux du **dernier PLU APPROUVÉ**, jamais
la révision (prescrite en 2022, non approuvée). « Révision en cours » ne remplace nulle part la règle en vigueur.

| Commune | INSEE | PLU servi (approuvé) | Procédure en cours (prescription) | Source |
|---|---|---|---|---|
| Trois-Bassins | 97423 | **21/02/2017** (règlement 112 extraits, millésime 2017-02-21 ; zonage 5314/5314) | révision **02/06/2022** | GPU pack `97423_PLU_20220602.zip` (data.geopf.fr) + Sudocuh |
| Saint-Leu | 97413 | **26/02/2007** (zonage 22868/22959 ; règlement verbatim non ingéré, zonage seul) | révision **17/05/2022** | Sudocuh + GPU |
| Saint-André | 97409 | **28/02/2019** (zonage 22600/22600) | révision **22/06/2022** | Sudocuh + GPU |

## Cause des trimestres vides (B3, P5)

DVF et permis prenaient CHACUN leurs 8 trimestres les plus récents **indépendamment**. Le flux **Sitadel
est en AVANCE sur DVF** (permis jusqu'à 2026T2, DVF publié jusqu'à 2025T4) → fenêtre permis 2024T3..2026T2
vs fenêtre DVF (axe de référence) 2024T1..2025T4 : l'union affichait 2024T1/T2 avec un permis vide (hors
fenêtre permis). **Correctif** : la série permis est bornée au dernier trimestre DVF → les deux séries
couvrent les MÊMES 8 trimestres pleins. Vérifié live : 2024T1 = 710, 2024T2 = 626 permis, tableau à 8 lignes.

## Les deux chiffres des acquisitions (B4, P9) — Le Tampon

- **Outil (DGFiP fichiers fonciers)** : **302 changements** de propriétaire PM · **82 acquéreurs** distincts
  depuis 2022 (parcelles PM, millésimes annuels).
- **Recoupement DVF (même période)** : **2064 ventes** DVF à Le Tampon, tous acquéreurs — l'open data DVF
  **n'identifie pas** le PM (pas de compte PM direct). Les 302 changements PM ≈ **15 %** du flux DVF, cohérent.
Le sous-titre dit déjà « Personnes morales uniquement — fichier DGFiP ».

## Sources de Faisabilité (C3) — 3 témoins

Le « rien ne se recalcule » **n'est pas reproduit** : le recalcul fonctionne (endpoint
`/modules/faisabilite/{idu}/recalcul` + effet front debounce → `cap`). Prouvé LIVE sur BZ1065 (3 Chemin de
la Citerne, Saint-Denis) : occupation 45→100 % fait passer le verdict de « au sol ~0-1 » à « ~3-4 logts »
(SHAB 123→247 m²) ; logement_m2 40 → logements 3-4. Aucune valeur du bloc 3 ne reste figée.

**Correctif** : les valeurs FIXÉES par le PLU (hauteur d'un niveau, densité, surface d'une place) ne sont
plus éditables — restent les 3 vraies hypothèses (occupation · rendement · surface moyenne/logement).

Bloc 2 (ce que le PLU permet) — tout **Sourcé** (`prov='sourcee'`, moteur) :

| Témoin | Zone | Calibrée | Lignes bloc 2 (source) |
|---|---|---|---|
| BZ1065 (Saint-Denis) | Uh | oui | emprise reculs (géométrie réelle), emprise % réglementé (CES), niveaux constructibles, stationnement (scénario au sol), LLS imposés (mixité au seuil) ; résiduel servi via `parcel_residuel` |
| CM1799 (Saint-Paul) | U6b | oui | idem, verdict R+2 |
| BW0102 (Saint-Denis) | — | non | hors périmètre analysé (pas de faisabilité) |

## Cause du Gabarit (C4, P19)

La source SUP (`sup_src`) était référencée par l'exclusion ET la règle applicable mais **JAMAIS ajoutée au
catalogue** (`sources.append(sup_src)` manquant, régression RETOUCHES-1 D.15) → `validate` levait
« exclusion[sup] : source absente du catalogue » → gabarit=incomplete → repli legacy sur toute parcelle
intersectée par un SUP (dont 97411000BZ1065). **Correctif 1 ligne.** Vérifié : `/outils/gabarit/97411000BZ1065`
→ status ok, `validationErrors []`, hauteur 7 m, plafond emprise 487,5 m² ; plus de « Calcul incomplet ».

## Taxe d'aménagement (C5, P20) — 2 témoins contre la formule publique

Forfait 2026 = **892 €/m²** (hors-IdF / DOM) ; CGI art. 1635 quater ; abattement RP 50 % sur les 100 premiers
m² ; départemental 2,5 %.

| Témoin | Surface / type | Assiette | Communal | Départemental (2,5 %) | Total |
|---|---|---|---|---|---|
| Saint-Denis (BZ1065) | 400 m² résidence principale | 312 200 € (400×892 − 100×892×50 %) | 3 % = 9 366 € | 7 805 € | **17 171 €** |
| Saint-Paul (CM1799) | 250 m² hors RP | 223 000 € | 5 % = 11 150 € | 5 575 € | **16 725 €** |

Exact au centime.

## Piscines (C6) — données

**12 576 servies** (à confirmer +11 706 ; écartées 26 234 ; détecté brut **50 516**). Par commune (servies) :
Saint-Paul 2 380 · Saint-Denis 1 766 · Saint-Pierre 1 445 · La Possession 876 · Le Tampon 765 · Saint-Louis 667.
Source = détection **FLAIR** (Ortho Express RVB 20 cm 2025, IGN) ∪ **CoSIA** (IA 20 cm 2025, IGN), dédoublonnées
à 5 m. **Millésime unique 2025** (le plus récent publié) — aucun millésime IGN 2026 disponible/à ingérer.

## Ensoleillement (C7) — 2 témoins, sources déclarées

- **BZ1065** : productible **1548 kWh/kWc/an** → **PVGIS v5.3 SARAH3** (relevé 2026-08-23), inclinaison 15°
  (paramètre PVGIS La Réunion). Azimut 65° (confiance basse), pente 13,8°, surface toit 197 m², nature
  « monopente » → **LiDAR HD IGN (MNH 50 cm)**.
- **CM1799** : productible **1348** → PVGIS ; azimut / surface toit = **null** (LiDAR toiture non résolu sur
  cette parcelle — honnête, aucune valeur inventée).

## Successions (C8) — 3 témoins

Signal 6 099 parcelles, calculé le **09/08/2026**, RNE INPI lu au 06/07/2026. Âge du dirigeant le plus âgé
(registre RNE/INPI ; foncier DGFiP) ; signal daté du CALCUL (le registre ne publie pas d'historique).

| IDU | Commune | Société (SIREN) | Dirigeant le plus âgé |
|---|---|---|---|
| 97422000BS0419 | Le Tampon | CALYPTUS (439063587) | **82 ans** |
| 97411000BL0098 | Saint-Denis | SCI C H A R (379193493) | **79 ans** |
| 97422000AW0358 | Le Tampon | RANIMAT (452543622) | **77 ans** |

## PARTIE D — recette Vic du 28/09/2026

- **D1 Faisabilité — aucun défilement horizontal** — `overflow-x-hidden` + `w-full min-w-0` sur le
  conteneur de l'outil (`M22Programme`) ET sur l'enveloppe `.fiche-v6` (`break-words`). Vérifié à 1440 px
  sur 97411000BZ1065 : à chaque niveau du panneau `scrollWidth == clientWidth` (285/285, 287/287,
  319/319) — plus aucun débordement latéral ; le verdict et les hypothèses passent à la ligne.
- **D2 Double geste partout** — toutes les barres `ParcelInput` (défaut `withCarte`) affichent déjà
  l'invite « ou cliquez une parcelle sur la carte ». **Pièges (blocB)** consommait le clic lui-même
  (`withCarte={false}`, pour garder la fiche ouverte — B8) : l'invite était donc masquée. Ajout d'une
  prop **`inviteCarte`** à `ParcelInput` qui découple l'invite de l'auto-consommation → Pièges passe
  `withCarte={false} inviteCarte`. **Remonter le temps** utilise déjà `ParcelInput` (invite présente,
  vérifiée live). Barres corrigées / vérifiées : Permis, Faisabilité (picker), Gabarit, Taxe, Étude de
  zone, Solaire (Ensoleillement), Scan patrimoine, Courrier, Diligence, Mon secteur, Assemblage (départ),
  ZAN, Vérif procédure, Veille, Calculette, **Remonter le temps**, **Pièges** (invite réaffichée). Comparer
  garde son étape 1 « Cliquez les parcelles sur la carte » (affordance équivalente).
- **D3 Gabarit — accordéon + bouton** — « Voir les règles appliquées » **ouvert par défaut**
  (`reglesOuvertes=true`) ; bouton **« Réinitialiser » retiré**. Vérifié live (règles listées d'emblée).
- **D4 Gabarit — la parcelle se voit en 2D et 3D** — **CAUSE de la régression trouvée** : sur une parcelle
  « terrain exigu » (ex. 97411000BZ1065), le moteur renvoie `status:'ok'` **mais sans zone constructible**
  (`zoneImplantationGeoJSON` null, `zoneImplantationM2` 0). L'ancien `contourOnly` ne se déclenchait que
  pour `status:'incomplete'` → ni zone ni **contour** n'étaient tracés, la parcelle disparaissait en 2D.
  Correctif (`useMapLayers`) : `contourOnly = !ok && !!contourGeoJSON` (tout statut) → le contour + le bâti
  se dessinent dès qu'on les a. Vérifié live : `gabarit-contour` présent, zoom 19, parcelle + bâti visibles.
  **Bouton « Voir en 3D » / « Revenir en 2D »** ajouté dans le panneau (`setTerrain3d`, même levier que le
  menu haut-droite) : vérifié live (pitch → 55°, bâti extrudé, libellé bascule).
- **D5 Adresse complète avec code postal** — **CAUSE trouvée** : la suggestion BAN arrive **scindée**
  (`label` = numéro + voie ; `sub` = « CP + commune » — confirmé par le back : `label:"3 Chemin de la
  Citerne"`, `sub:"97417 Saint-Denis"`). `AddressAutocomplete.pick` ne recopiait que `it.label` → la
  voie seule. Correctif : pour une adresse, on recolle **`label, sub`** dans le champ ET dans `onSelect`.
  Vérifié live : le clic affiche **« 3 Chemin de la Citerne, 97417 Saint-Denis »**. Test-garde ajouté.
- **D6 « Méthode et limites » → accordéon de la charte** — dans Pièges (`blocB`), le `<details>` texte
  « Méthode &amp; limites … (déplier) » devient l'accordéon standard (`Chevron` fermé ◀ / ouvert ▼,
  libellé « Méthode et limites », fermé par défaut). Aucune autre occurrence littérale « (déplier) »
  dans les outils ; les blocs fiche « N couches sans objet — déplier » sont un motif distinct, laissés.
- **D7 Taxe — vérification de la calculette** — recalcul manuel de 2 témoins contre `calculer()` (vf 2026
  = **892 €/m²**, abattement 50 % sur 100 premiers m² RP, part dép. 2,5 %) :
  - **Saint-Denis (97411), taux communal 3 %** — RP, surface taxable 150 m² : assiette = 50×892 + 100×892×0,5
    = **89 200 €** ; part com. 2 676 € ; part dép. 2 230 € ; **total 4 906 €** ; RAP (0,40 %) 356,80 €.
  - **Saint-Paul (97415), taux communal 5 %** — RP, 120 m² + piscine 30 m² : assiette = (20×892 + 100×892×0,5)
    + 30×251 = 62 440 + 7 530 = **69 970 €** ; part com. 3 498,50 € ; part dép. 1 749,25 € ; **total
    5 247,75 €** ; RAP 279,88 €.
  - **Écart calculette ↔ main = 0 €** sur les deux (au centime). Taux 3 % / 5 % confirmés depuis
    `taxe_amenagement_taux` (DGFiP/DELTA). **Aucune correction nécessaire.**
- **D8 Piscines — la liste remplace les communes** — au clic « Voir les piscines », l'encart total + liste
  des communes **se replie** (`<details data-piscines-encart>`, rouvrable par le chevron de la charte) et
  la liste des parcelles prend la place. Phrase technique « Statut servie (précision ≥ 85 %)… » **retirée** ;
  une seule ligne de source **« Source : IGN FLAIR et CoSIA, 2025 »**. Vérifié live : total 12 576, encart
  ouvert → replié après « Voir », 200 lignes affichées ; « précision ≥ 85 % » absent du DOM.

## Recette PARTIE D

- `tsc` 0 · `vite build` OK · `vitest` **200 passed** (48 fichiers) — dont 3 tests-gardes ajoutés :
  socle D5 (label+sub recollés → adresse entière), socle D2 (`inviteCarte`), ProspectionSolaire D8
  (encart replié + source unique). **Back non touché** (D7 = vérification seule) → pas de pytest requis.
- Vérifications live sur l'app (back 8455 / front 5655, 1440 px) : D1, D2 (Pièges + Temps), D4 (2D+3D),
  D5, D8. Captures dans `captures/` (préfixe `D…`).

## Cas non rangés

- **D4 (3D relief)** — le bouton « Voir en 3D » allume bien le relief + le bâti extrudé (pitch 55°). En
  test headless, la caméra se re-stabilise à un pitch moindre après un `moveend` (recharge du bâti par
  bbox) : purement cosmétique en capture, le mécanisme (`setTerrain3d`, partagé avec le menu) est le bon.
- **D6** — les blocs de la **fiche** « N couches sans objet — déplier » utilisent un motif d'affordance
  distinct (mot-indice, pas le cue « (déplier) ») antérieur au mandat : laissés tels quels (hors périmètre).
- **C3 Faisabilité** — la refonte visuelle complète (verdict-ligne à badges, 5 blocs nommés avec article+page,
  deux portes « Une parcelle » / « Trouver des parcelles pour un programme ») N'A PAS été refaite en entier :
  le correctif fonctionnel (recalcul vérifié + 3 hypothèses seulement) est livré ; la restructuration en 5
  blocs / 2 portes reste à faire (risque de régression élevé sur `FaisabiliteTab`). Signalé pour arbitrage.
- **C2** — les millésimes « carte » (SCAN 50, EduGéo) sont étiquetés « 1950 (carte) » / « 1980 (carte) » pour
  ne pas se confondre avec l'ortho de la même décennie (Vic listait un seul 1950 et un seul 1980).
- **B8** — le composant M10 (flux « Un lot ») reste EXPORTÉ pour son test unitaire mais n'est plus câblé à l'outil.
