# RECETTE-6 — retours de recette, emprise bâtie, vue mer

**Branche** `fix/recette-6` (tirée de `feat/recette-5`).
**Worktree** `~/Desktop/labuse-recette6`.
**Un commit par lot** (A→G), le lot H est cette note (lecture seule).

## Garde-fous — tenus

- **Aucun merge, aucune bascule, aucun rescoring.** Le run servi reste `q_v11_m137`, inchangé. Aucun
  fichier de scoring/cascade touché (les deux chemins `p_model_bati` corrigés au lot G sont du SQL de
  *feature store* : effet au prochain rebuild seulement, jamais au run servi).
- **Aucune ingestion, aucun batch sur l'île.** Lot H = mesures **lecture seule** (comptages, tailles de
  tables, un échantillonnage de 200 centroïdes). Rien n'a été ingéré, rien n'a été recalculé en masse.
- **API en SIGTERM.** L'API de recette (`:8020`, worktree `labuse-couches`) n'a pas été touchée ; une
  API fraîche `recette-6` a été lancée sur `:8021` pour la vérification navigateur, arrêtée proprement.
- **DA existante.** Aucun nouveau parti pris visuel : l'écran 0 du Financier et la bulle d'aide
  réutilisent les couleurs/typos en place ; le correctif PDF (F2) retire des *features* de police, il
  n'ajoute aucun style.
- **Périmètre fermé aux 33 travaux.** Pas d'audit collatéral. Seule exception assumée et tracée : F2 se
  corrige à la feuille de style **partagée** par les 5 documents (c'est la cause racine ; la corriger
  ailleurs qu'à la racine serait un pansement). Cf. arbitrage F2 plus bas.

**Étape 0 (arbitrage).** La branche `fix/recette-6` et son worktree n'existaient pas ; le mandat dépend
des livrables de RECETTE-5 (en-tête de fiche, documents, vue mer instruite). Branche donc tirée de
`feat/recette-5` (et non de `main`), `.env` recopié. Tracé ici, pas un arrêt.

---

## Les 33 travaux

| # | Travail | Statut | Preuve |
|---|---------|--------|--------|
| **A1** | Retirer le bouton « Adresse » du panneau de filtres (le filtrage reste actif en fond) | ✅ fait | `ResultsSection.tsx` — tri factuel réduit à `surface` ; ordre « adressées d'abord » conservé par défaut. Arbitrage ci-dessous. |
| **A2** | Retirer le voile gris en mode Analyse LABUSE (trouver le vestige, prouver à l'écran) | ✅ fait (déjà satisfait) | Voile déjà uniforme (0,72) depuis RECETTE-2 ; aucun scrim/opacité résiduel. Captures `r6-a2-analyse.png`, `r6-a2-analyse-sombre.png`. Arbitrage ci-dessous. |
| **A3** | Bâti 3D branché sur le bouton 3D existant + relief, état actif vert-opaque, pas de hauteur → pas d'extrusion | ✅ fait | `MapView.tsx` couche `fill-extrusion` `batiments-3d` (hauteur `['coalesce',['get','h'],0]`), source bbox `/map/batiments.geojson` (plafond 8000). Capture `r6-a3-3d-buildings.png` (649 bâtiments extrudés). |
| **B1** | Case « Voir tout » en dernier-droite du groupe | ✅ fait | `ResultsSection.tsx` case `data-segments-voir-tout` (coche/décoche les 4 accordéons). |
| **B2** | Les 4 accordéons fermés par défaut (chevron à droite) | ✅ fait | `openSeg` initialisé `false` pour les 4 segments. |
| **B3** | Compteur « 0 sans signal · 0 sans signal · … faible » qui se répète | ✅ fait | Compteur ramené aux **4 paliers** PALIERS-1 (`PALIER_META`), plus de répétition ni de `EPUISE_COLOR`. Capture `r6-b-segments.png`. |
| **C1** | Retirer les trois pastilles de la tête de fiche | ✅ fait | `Fiche.tsx` — bloc `head-badges` supprimé. |
| **C2** | Retirer « Le reste des faits » (liste de contrôle : où va chaque fait ; orphelins déplacés) | ✅ fait | Accordéon supprimé ; liste de contrôle ci-dessous (C2). Le seul orphelin (« dernière vente ») déplacé au Marché. |
| **C3** | Dédup transport + dernière vente | ✅ fait | `autour.tsx` filtre « Bus »/transport des équipements BPE ; dernière vente désormais à un seul endroit (Marché). |
| **C4** | Vente invraisemblable ~83 k€/300 m² (multi-lots/immeuble/rattachement ; seuil vraisemblance ; €/m² ÷ surface doublée = motif lot G) | ✅ fait | `marche.tsx` — garde C4 : `dm.multi_parcelles` → « Vente groupée … prix global non attribuable ». Enquête DB ci-dessous (C4). |
| **C5** | Exactement six tuiles (Surface·Zone·Pente / Vue mer·Taxe foncière·SDP restante), retirer Terrain nu + Bâti ancien, Vue mer toujours « — », grille à hauteur fixe | ✅ fait | `Fiche.tsx` `tuiles` = 6 fixes ; `index.css` grille `repeat(3,1fr)` `grid-auto-rows:1fr`. Capture `r6-c-6tiles.png`. |
| **D1** | Retirer le titre « Exports » | ✅ fait | `Fiche.tsx` — `<div class="sec">EXPORTS</div>` supprimé. |
| **D2** | 6ᵉ bouton « Remonter le temps » pré-rempli sur la parcelle avec fil de retour ; retirer de l'accueil | ✅ fait | `Fiche.tsx` `OutilCase data-temps-tile` (`setParcelPrefill(idu)` + `flyTo`) ; `LeftPanel.tsx` — entrée retirée de l'accueil. |
| **E1** | Les i (info) des 4 écrans du Financier n'affichent rien | ✅ fait | `FinancierQuestionnaire.tsx` — bulle d'aide au survol (popover) à la place du `title` natif. **Vérifié navigateur** : capture `recette6-E1-tooltip.png`. |
| **E2 🔴** | Bilan faux ×160 (garde de vraisemblance sur CA/charge, indice d'unité + alerte de saisie) | ✅ fait | `financier_bilan.py` `_hors_marche` (bornes €/m²) ; `blocs/financier.py` court-circuite en nommant le champ. **Vérifié PDF** : 700 000 → « hors marché », plus de verdict absurde. |
| **E3** | Formats/zéros (un seul format monétaire, pas de « 0 k€ », taxe portage en poste, « Régime retenu » une fois) | ✅ fait | `blocs/financier.py` — « < 1 k€ », poste « Taxe foncière (portage) », régime énoncé 1×. **Vérifié PDF**. |
| **E4** | Nature des libellés (CA HT → dérivé, construction pré-remplie → sourcé) | ✅ fait | `blocs/financier.py` — puce CA « dérivé », nature construction/taxe selon origine. **Vérifié PDF** (puce « dérivé » présente). |
| **E5** | Refonte questionnaire tous métiers (tableau des champs + écran 0 « Que voulez-vous chiffrer ? », pas 5 moteurs, parcours non servis grisés) | ✅ fait | `financier_questionnaire.USAGES` + endpoint + `FinancierQuestionnaire.tsx` écran 0. **Vérifié navigateur** : capture `recette6-E5-ecran0.png`. Tableau des champs ci-dessous (E5). |
| **F1** | Le titre de l'apporteur suit le contenu (bâti/nu) | ✅ fait | `blocs/apporteur.py` — « Un bien bâti à sonder » si `is_bati`, « Un terrain à sonder » sinon. |
| **F2 🔴** | Texte du PDF non extractible (police sans ToUnicode) | ✅ fait | `theme.css` — ligatures + chiffres tabulaires désactivés (cause racine). **Vérifié extraction** : dates « 09/09/2026 », prix « 60 000 € », zéro caractère parasite, sur apporteur ET Dossier. |
| **F3** | Dernière vente + voisines (blocs) absentes (verdict) | ✅ fait (verdict, sans code) | Absence = **donnée réelle** sur la parcelle de recette (0 vente DVF, 0 bloc). Plomberie prouvée saine sur d'autres parcelles. Détail ci-dessous (F3). |
| **G1** | Trouver tous les calculs d'emprise bâtie | ✅ fait | 5 lecteurs recensés (tableau lot G). |
| **G2** | Poser la garde `ST_Union` partout | ✅ fait | 4 lecteurs corrigés (`p_model/sql.py` ×2, `bati_revele.py`, `au_ouverture.py`) ; `le_bien` (bati.py) l'avait déjà (RECETTE-5). |
| **G3** | Ajouter la comparaison d'emprise à la sonde de cohérence | ✅ fait | `sonde_circuit.py` — compare l'emprise servie (`le_bien`) au recalcul `ST_Union` frais. |
| **G4** | Impact aval sur la SDP (mesure lecture seule) | ✅ fait | Mesuré : **20 440** parcelles emprise > contenance avant, **19 943** classe dure nette après recompte ST_Union (~500 parcelles cessent de dépasser), médiane SDP recalculée +210 m² là où le double-compte gonflait l'emprise. Lecture seule, aucun rebuild. |
| **H1** | Coût d'ingestion du MNT RGE ALTI 5 m | ✅ fait | Lot H ci-dessous. |
| **H2** | Usages au-delà de la vue mer | ✅ fait | Lot H ci-dessous. |
| **H3** | Temps du batch visibilité | ✅ fait | Lot H ci-dessous. |
| **H4** | Les quatre états (dégagée/partielle/aucune/« dégagée aujourd'hui, permis en cours devant ») | ✅ fait | Lot H ci-dessous. |
| **H5** | La méthode | ✅ fait | Lot H ci-dessous. |
| **H6** | Ce qu'il ne voit jamais | ✅ fait | Lot H ci-dessous. |
| **H7** | Stratégie de mise à jour | ✅ fait | Lot H ci-dessous. |
| **H8** | Rien ingéré + recommandation franche | ✅ fait | Lot H ci-dessous. |

**33 / 33 faits.** 2 étaient des verdicts (A2 déjà satisfait, F3 absence réelle) : tracés, pas éludés.

---

## Arbitrages

- **A1 — « Adresse ».** Aucune puce/bouton « Adresse » visible dans le panneau *Filtres* ; le filtre
  `adresseAbsente` n'a pas d'UI. Le seul bouton « Adresse » de la barre est le **tri factuel** ajouté en
  RECETTE-5. Interprétation retenue : c'est lui qu'on retire (le filtrage « adressées d'abord » reste,
  en fond, comme ordre par défaut). Si le retour visait un autre « Adresse », le dire — mais rien
  d'autre ne porte ce libellé.
- **A2 — voile analyse.** Recherché : scrim, `opacity`, calque gris surnuméraire. Le voile du mode
  Analyse est déjà l'aplat uniforme (0,72) posé en RECETTE-2 ; aucun vestige. Rien changé (garde-fou :
  pas de nouveau parti pris). Prouvé à l'écran (clair + sombre).
- **C2 — orphelins.** « Le reste des faits » ne contenait qu'un fait n'existant nulle part ailleurs : la
  **dernière vente**. Règle C2 (« un fait qui n'existe nulle part ailleurs est déplacé ») → rapatrié
  dans **Marché** (`marche.tsx`, `data-derniere-vente`). Tous les autres faits de l'ancien accordéon
  avaient déjà un foyer (surface, zone, pente → tuiles ; transport → Autour ; etc.).
- **C4 — vente à ~83 k€/300 m².** Enquête DB : ces ventes sont **toutes `multi_parcelles = true`**
  (15 444 / 37 868 mutations, soit 41 %) — le prix global de la mutation est attribué à tort à une
  seule parcelle. Le €/m² (264) = `valeur / surface`, **pas** de motif « surface doublée » du lot G ici.
  Verdict : on n'affiche plus ce prix comme prix de la parcelle ; on l'annonce comme **vente groupée**
  (« le prix global … n'est pas attribuable à cette seule parcelle »).
- **F2 — correctif à la racine.** La cause (ToUnicode absent pour les glyphes issus d'une substitution
  OpenType) est dans `theme.css`, **partagé par les 5 documents**. Corriger ailleurs qu'à la racine
  laisserait 4 documents cassés. Ce n'est pas un élargissement de périmètre : c'est le même bug, à sa
  source. Bénéfice collatéral (les autres docs deviennent extractibles) assumé.
- **F3 — pas de code.** La plomberie est saine (prouvé) ; l'absence constatée en recette est une donnée
  réelle. Toucher au code aurait été inventer un faux.

---

## Lot G — l'emprise bâtie, partout (tableau)

Cause : `SUM(ST_Area(ST_Intersection(bâti, parcelle)))` additionne des polygones BD TOPO qui **se
chevauchent** → emprise gonflée, parfois > la contenance. Correctif : `ST_Area(ST_Union(ST_Intersection(...)))`.

| Lecteur | Fichier | Nature | Effet | Statut |
|---------|---------|--------|-------|--------|
| `le_bien` (fiche/Dossier/Flash) | `exports/blocs/bati.py` | servi live | — | déjà `ST_Union` (RECETTE-5) |
| `p_model_bati` (CoSIA combiné) | `scoring/p_model/sql.py` | feature store, batch | au prochain rebuild | ✅ corrigé |
| `p_model_bati` (repli) | `scoring/p_model/sql.py` | feature store, batch | au prochain rebuild | ✅ corrigé |
| `parcel_bati_revele` | `faisabilite/bati_revele.py` | ingestion, batch | à la ré-ingestion | ✅ corrigé |
| ratio bâti/surface du voisin (étude d'ouverture AU) | `faisabilite/au_ouverture.py` | **live** | immédiat | ✅ corrigé |
| sonde de cohérence | `sonde_circuit.py` | garde | — | ✅ G3 ajoutée |

**G4 — impact aval (lecture seule).** 20 440 parcelles avaient une emprise > contenance (symptôme du
double-compte). Après recompte `ST_Union` : ~500 cessent de dépasser (→ 19 943), et là où l'emprise
gonflée mangeait la SDP résiduelle, la SDP recalculée remonte (médiane +210 m² sur les parcelles
concernées). **Aucun rebuild lancé** : l'effet réel n'apparaîtra qu'au prochain run de scoring / à la
ré-ingestion. Mesure indicative, pas un recalcul servi.

---

## E5 — le questionnaire du Financier

### Écran 0 « Que voulez-vous chiffrer ? »

Un seul moteur : le **bilan à rebours** (construction neuve). Les autres usages sont **grisés avec leur
raison** — jamais un formulaire qui rendrait un bilan faux. (`financier_questionnaire.USAGES`, servi par
`/financier/{idu}/questionnaire`, rendu par l'écran 0 du modal.)

| Usage | Servi ? | Raison si grisé |
|-------|---------|-----------------|
| Construction neuve | ✅ | — (le bilan à rebours : charge foncière supportable) |
| Revente en l'état | grisé | comparateur prix d'achat / revente non servi |
| Division parcellaire | grisé | valorisation lot par lot non servie |
| Rénovation-revente | grisé | poste travaux dédié non servi |
| Portage locatif | grisé | rendement locatif (loyers, charges, fiscalité) non servi |

### Tableau des champs (revue)

Les 20 champs du parcours **construction** (4 écrans). Les 4 champs retirés en RECETTE-2 (S3) le restent
(leur valeur n'apparaissait dans aucun poste du bilan) : type de stationnement, prix déjà refusé,
commission d'apporteur, apport (renvoyé au prêteur).

| Écran | Champ (client) | Rôle dans le bilan | Nature |
|-------|----------------|--------------------|--------|
| Votre projet | Scénario | choisit reconstruction/surélévation | saisi (pré-rempli du potentiel) |
| Votre projet | Logements visés | dimensionne le programme | saisi |
| Votre projet | Typologie moyenne | estime la surface vendable si le potentiel ne la donne pas | saisi |
| Votre projet | Part sociale (%) | régime TVA / prix bailleur | saisi |
| Le foncier | Prix demandé | point de départ (charge foncière testée) | saisi (pré-rempli si connu) |
| Le foncier | Frais d'acquisition (%) | poste acquisition | saisi |
| Le foncier | Démolition | poste préparation | saisi |
| Le foncier | Dépollution | poste préparation | saisi |
| Vos coûts | Coût construction (€/m²) | poste travaux central | saisi (pré-rempli **sourcé**) |
| Vos coûts | Honoraires techniques (%) | poste MOE | saisi |
| Vos coûts | VRD (€/m²) | poste viabilisation | saisi |
| Vos coûts | Coût par place de stationnement | poste stationnement | saisi |
| Vos coûts | Aléas (%) | provision | saisi |
| Vos coûts | Taxe d'aménagement | poste fiscal | saisi (pré-rempli **sourcé** du taux communal) |
| Vos conditions | Prix de sortie (€/m²) | **CA HT dérivé** (surface vendable × prix ÷ (1+TVA)) | saisi — **garde E2** |
| Vos conditions | Prix de vente bailleur (€/m²) | CA de la part sociale | saisi — **garde E2** |
| Vos conditions | Marge visée (%) | cible du promoteur | saisi |
| Vos conditions | **Régime de TVA** | décide HT/TTC — **obligatoire** | saisi (bloque le calcul si absent) |
| Vos conditions | Durée de portage (mois) | frais financiers | saisi |
| Vos conditions | Taux d'apport (%) | plan de financement (renvoyé au prêteur) | saisi |

**E2 (🔴), le fond.** Un prix de sortie saisi en **total** (ex. 700 000 pour un logement) au lieu d'un
**€/m²** produisait CA = surface × 700 000 → bilan ×160. La garde `_hors_marche` borne les €/m²
(sortie ≤ 20 000, construction ≤ 8 000, bailleur ≤ 12 000) ; hors borne, le document **n'énonce plus de
verdict** : il **nomme le champ** et rappelle l'unité attendue.

---

## Lot H — chiffrer le MNT (lecture seule)

> **Rien n'a été ingéré, aucun batch lancé.** Ce qui suit est un chiffrage appuyé sur des mesures
> lecture seule de la base : tailles de tables, comptages, un échantillonnage de 200 centroïdes.

**État des lieux mesuré.**
- Le seul raster présent est **`rgealti_pente_5m`** : la **pente** dérivée du MNT RGE ALTI 5 m
  (2 793 dalles, 111,72 M cellules, **425 Mo**, PostGIS raster SRID 2975). Le MNT d'**altitude** lui-même
  a été **calculé puis jeté** (`ingestion/ortho_pente.py` : « le raster de pente 5 m a été CONSERVÉ ») —
  il n'y a **aucune altitude en base**.
- **431 663** parcelles. **817 506** bâtiments (`spatial_layers` kind=`batiment`), dont **701 052 avec
  hauteur** (85,8 % — 14 % sans hauteur).
- La vue mer est aujourd'hui un **« — » assumé** (tuile C5). La table `parcel_vue_mer` est marquée « à
  archiver — plus aucun lecteur » ; le paramètre `bonus_vue_mer_pct` du bilan a été supprimé (orphelin,
  jamais câblé). **La vue mer ne nourrit donc ni le scoring ni le bilan** : c'est un argument client, pas
  un signal.

### H1 — coût d'ingestion du MNT RGE ALTI 5 m

- **Donnée** : gratuite (IGN / Etalab), déjà téléchargée une fois (pour la pente). Ré-obtenir l'altitude
  = même source.
- **Stockage** : l'altitude en float32 à 5 m sur les 111,72 M cellules pèse le même ordre que la pente,
  soit **~0,45 Go** en PostGIS raster (tuilé, compressé).
- **Chargement** : `raster2pgsql` des 2 793 dalles → **~15–30 min** une fois.
- **Mais** : le MNT RGE ALTI est un **MNT de sol nu** (bare earth). Pour une vue mer réaliste il faut un
  **MNS** (surface, bâti compris) : MNT + hauteurs de bâtiment (on a déjà 701 k bâtiments hautés) → un
  raster dérivé à construire, ~même poids. **Coût réel ≈ 1 Go et une demi-journée d'outillage**, pas le
  seul chargement du MNT.

### H2 — usages au-delà de la vue mer

Un vrai MNT/MNS sert bien plus que la mer :
1. **Terrassement** (déblai/remblai) — volumes → coût de construction en terrain pentu (poste du bilan).
2. **Faisabilité d'accès** — pente d'une rampe/voie d'accès (un accès à 15 % tue une opération).
3. **Masques solaires** — le relief cache le soleil : affine l'outil solaire existant.
4. **Vis-à-vis / covisibilité** — surplombs entre parcelles (argument et risque).
5. **Vue « montagne »** (Piton, cirques) — pas que la mer.
6. **Ruissellement/thalwegs** — complète les ravines déjà en base.
La pente scorée en tire déjà parti ; l'altitude débloquerait les points 1, 2, 4, 5.

### H3 — temps du batch visibilité

- **Mesure** : l'échantillonnage raster par `ST_Value` tourne à **~89 points/s** en SQL.
- Une ligne de vue vers la mer, c'est un **éventail de rayons** (l'arc de mer visible) × un point tous
  les 5 m sur plusieurs km → ~20 000–30 000 échantillons/parcelle. À 89/s, c'est **~5 min/parcelle** :
  **inutilisable en SQL**. Il faut un **moteur de viewshed** (GRASS `r.viewshed`, GDAL) travaillant le
  raster en mémoire, pas des `ST_Value` en boucle.
- Avec `r.viewshed` (~0,3 s/observateur sur une fenêtre) et en **restreignant aux parcelles candidates**
  (proches du littoral, sous ~600 m — de l'ordre de **~100 k**, pas les 431 k), sur 8 cœurs :
  **~1 h** de calcul, plus la construction du MNS. **Réaliste : une demi-journée une fois**, incrémental
  ensuite.

### H4 — les quatre états

1. **Vue mer dégagée** — les rayons vers la mer atteignent l'eau libre, aucun masque relief/bâti.
2. **Vue mer partielle** — une fraction de l'arc atteint la mer (certains rayons bloqués), ou vue
   lointaine/oblique.
3. **Aucune vue mer** — tous les rayons bloqués (relief ou bâti), ou parcelle tournée vers l'intérieur.
4. **« Dégagée aujourd'hui, mais permis en cours devant »** — vue ouverte **maintenant**, mais un permis
   (`sitadel_permits`, déjà en base) sur une parcelle **en contrebas, entre elle et la mer**, la
   masquera. On croise le viewshed avec les permis en cours : c'est **la** valeur différenciante — une
   vue qui **va** se perdre.

### H5 — la méthode

- **MNS** = MNT RGE ALTI 5 m + hauteurs de bâtiment BD TOPO rasterisées (701 k bâtiments hautés).
- **Observateur** : centroïde de la parcelle (ou toiture si bâti) + hauteur d'œil (~1,6 m / R+1).
- **Cible** : la mer (polygone littoral — trait de côte tamponné / hydro surfacique).
- **Calcul** : `r.viewshed` ou éventail de lignes de vue vers l'arc de mer ; **classement** par fraction
  de rayons « mer » qui atteignent l'eau, **pondéré par la distance** (un liseré à 500 m ≠ un panorama à
  20 km).
- **État 4** : intersection du viewshed avec les permis en cours en contrebas.

### H6 — ce qu'il ne voit jamais

- La **végétation** (le MNT est sol nu ; haies, arbres non modélisés) → faux « dégagée ».
- Les **14 % de bâtiments sans hauteur** → sous-masquage.
- Les **constructions récentes/non déclarées** pas encore en BD TOPO.
- Le **décalage de millésime** (RGE ALTI mis à jour au coup par coup) — terrassements/démolitions récents.
- La vue **par pièce/étage** — c'est un verdict à la parcelle, pas par fenêtre.
- La **météo/brume** — réelle pour l'acheteur, hors modèle.

### H7 — stratégie de mise à jour

- **RGE ALTI** : réingestion au nouveau millésime IGN (Réunion : espacé, tous les quelques ans) →
  reconstruction complète du viewshed (rare).
- **Bâtiments** (BD TOPO, déjà rafraîchis périodiquement) → reconstruire le MNS et le viewshed sur les
  **dalles changées** seulement (incrémental).
- **Permis** (`sitadel_permits`, cadence fréquente) → **ne recalculer que l'état 4** sur les candidates
  concernées (croisement peu coûteux). C'est le seul volet qui bouge souvent, et c'est le moins cher.

### H8 — rien ingéré + recommandation franche

**Rien n'a été ingéré, aucun batch, aucun calcul sur l'île** (garde tenue). Seules des mesures lecture
seule et un échantillon de 200 centroïdes.

**La vue mer vaut-elle son ingestion ? — Non en bloc, oui pour un seul volet.**

- La vue mer **ne sert pas le scoring** (paramètre supprimé, table à archiver) : c'est un argument
  commercial. Un badge statique « dégagée/partielle/aucune » **duplique ce qu'un agent voit sur place**,
  coûte une demi-journée d'outillage + ~1 Go + une **dépendance GRASS/GDAL** nouvelle, et reste
  **fragile** (angle mort végétation → faux positifs qui nous décrédibiliseraient). Valeur marginale
  moyenne, risque d'image réel.
- **En revanche, l'état 4 — « vue dégagée aujourd'hui, permis en cours devant » — est vraiment
  différenciant et devient bon marché une fois le viewshed en place** (il réutilise `sitadel_permits`
  qu'on a déjà). C'est ce qu'aucun agent ne voit, et c'est ce qui fait une décision d'achat.

**Recommandation.** Ne pas ingérer le MNT pour un simple badge de vue mer (valeur faible, fragile).
Ne l'ingérer que si l'on s'engage sur le **produit « vue menacée » (état 4)**, et alors **borné aux
candidates littorales (~100 k)**, pas à l'île. D'ici là, garder la tuile à **« — »** (honnête) plutôt que
livrer une devinette fragile. Si l'on y va, commencer par **le MNS + le viewshed sur les candidates**,
puis brancher les permis — le reste (états 1–3) tombe gratuitement et sert l'argumentaire.

---

## Tests & vérifications

- **Front** : `tsc -b` vert ; `vitest` **201 passés** (dont `FinancierQuestionnaire.test.tsx` mis à jour
  pour l'écran 0 — 4 tests).
- **Back** : `tests/test_recette6.py` **6 passés** (E2 garde, E5 usages, F1 titre, F2 feuille sans
  ligatures/chiffres tabulaires, G2 `ST_Union`).
- **Navigateur** (`:5178` → API `:8021`) : écran 0 des 5 usages (`recette6-E5-ecran0.png`), bulle d'aide
  au survol (`recette6-E1-tooltip.png`).
- **PDF** (WeasyPrint 69, rendu direct DYLD) : E2 garde hors-marché, E3/E4 formats+natures ; F2
  extraction propre (dates/prix) sur apporteur (nu ET bâti) et Dossier.
- Preuves dans `docs/audit-2026-09/RECETTE-6-preuves/`.

**Vic relit, bascule si besoin, merge.**
</content>
</invoke>
