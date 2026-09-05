# COMPTE-RENDU RETOURS-13 — `fix/retours-12`

Recette navigateur sur la base réelle (backend :8000, front `/socle/` buildé), captures
avant/après dans `captures/` aux cadrages du mandat. Commits : Lot 1 `44443736` · Lot 2
`5248d253` · Lot 3 `4cfe8e48` · R31 `b3ca67a2` (commit séparé, intégration LiDAR).
Une ligne par travail : **fait** / **fait autrement** (pourquoi) / **pas fait** (motif mesuré).

---

## LOT 1 — carte, fonds et couches (commit 1)

- **R1 — mer en Ortho IGN, île entière — FAIT.** Le bounds C6 ne suffisait pas : les tuiles jpeg
  qui INTERSECTENT l'emprise sont servies quand même, et leur no-data est BLANC OPAQUE → l'escalier
  restait au cadrage de Vic (reproduit : capture `R1-ortho-ile-avant`). Correctif : **masque de
  mer** (`mer-mask`) — polygone monde troué par le contour dissous de l'île (ile974.geojson), peint
  couleur de mer sombre AU-DESSUS des rasters ortho → mer CONTINUE jusqu'aux bords, quoi qu'IGN
  serve. Visible sur les fonds ortho seuls (Plan IGN dessine sa propre mer ; Clair/Sombre sans
  raster). Vérifié au même cadrage sur les 3 fonds (captures `R1-{ortho,plan,clair}-ile-avant/apres`).
- **R2 — couche « Parcelles — classement LABUSE » : RETIRÉE (décision par la capture).** Cochée
  seule en mode neutre, elle ne montre RIEN de lisible (trame cadastrale quasi éteinte — les
  couleurs du classement n'apparaissent qu'en mode ANALYSE, indépendamment de la case) ; la
  différence avec « Limites parcelles » n'est pas évidente en 2 s (captures `R2-*-seule.png`).
  La case SORT du menu ; la clé de store est conservée (défaut true) : l'aplat d'analyse et la
  trame de fond fonctionnent comme avant (même patron que M62-P1).
- **R3 — groupe « RéseaUX » au menu Couches — FAIT.** Famille « Réseaux » : « Transport public
  (lignes de bus) », « Arrêts de transport en commun », « Transport en commun en site propre »,
  « Axes structurants », « Lignes haute tension (HTB) », « Lignes moyenne tension (HTA) » —
  chaque entrée avec son « i » (source, millésime, couverture). Capture `R3-couches-reseaux-apres`.
- **R4 — moyenne tension : la source EXISTE, ingérée — FAIT.** Recherche URL par URL ci-dessous.
  Le portail EDF Réunion a été REFONDU (Opendatasoft → Koumoul/data-fair : les anciennes URLs
  répondent 404/410, d'où le constat erroné de C1). Les jeux HTA sont TOUJOURS publiés →
  ingestion `kind='ligne_mt'` : **4 211 tronçons aériens + 15 269 souterrains** (LO 2.0,
  géométrie ~02/2020, republiée 16/10/2025), CLI `labuse reseaux-mt`, catalogue + sentinelle
  (en-tête du data-file). `i` honnête : tracé indicatif, sécurité publique, jamais une DT-DICT.
  **Postes sources : jeu VIDÉ par EDF (0 enregistrement au 24/12/2025, « sécurité publique »)**
  → pas de couche postes, l'absence est dite (point 4 non réalisable, mesuré).
- **R5 — BAOBAB retiré ; vraie couche TCSP — FAIT.** (a) BAOBAB retiré partout : couche carte,
  kind synthétique `tcsp_axe`, fait fiche « distance à l'axe / 500 m » — aucun vestige.
  (b) Recherche de source (détail URL par URL ci-dessous) : AUCUNE source SIG publique d'axe TCSP
  au 974 — la seule géométrie traçable des tronçons EN SERVICE est OSM. Ingéré :
  `tcsp_troncon` = **89 voies en site propre** (`highway=busway` — boulevard sud St-Denis,
  tronçons CIVIS…) + **53 couloirs bus** (distinction DITE : un couloir n'est PAS un site propre
  L151-36) + **44 stations dérivées** (`tcsp_station` = grappes d'arrêts GTFS ≤ 60 m d'un site
  propre). EN TRAVAUX (Rico Carpaye, ESTI+) et EN PROJET (Réunion Express) : aucune géométrie
  publique → dits au « i » et à la légende, JAMAIS dessinés à la main ; Réunion Express inscrit
  au catalogue + sentinelle (le tracé bougera après le débat, clôture 26/11/2026).
  (c) **Base légale relue sur Légifrance le 05/09** : art. L151-36 en vigueur = « moins de HUIT
  CENTS mètres d'une gare ou d'une station de transport public guidé ou de transport collectif en
  site propre », plafond « plus d'une aire de stationnement par logement », condition « dès lors
  que la qualité de la desserte le permet » — **modifié par la loi n° 2025-1129 du 26/11/2025
  (art. 20), en vigueur 28/11/2025** (la référence « loi 2026-103 du 19/02/2026 » du mandat ne
  correspond pas à ce que Légifrance affiche : c'est la 2025-1129 qui porte le 800 m — cité tel
  quel). L151-35 : 0,5 place pour le 1° de L151-34 (logement locatif aidé) à < 800 m ; 0,5
  partout pour personnes âgées / résidences universitaires (2°-3°).
  (d) Fait fiche : distance à la STATION en service la plus proche (à vol d'oiseau — CE 2022,
  jamais au tracé), drapeau < 800 m, formulation du mandat (plafond qui S'IMPOSE au PLU, reste à
  instruire la qualité de la desserte) ; les couloirs ne déclenchent jamais le drapeau (les
  stations ne sont dérivées que des voies en site propre). Tests `test_retours12_c2_tcsp.py`
  réécrits (5) : distinction site_propre/couloir · tcsp_axe retiré · drapeau 800 m · libellé légal
  · pas de faux positif.
- **R6 — mouvement de terrain : le rouge existait, il était ÉCRASÉ — FAIT.** Table des classes
  réelles du flux DEAL (mesurée) : inondation FAIBLE 19 · MOYEN 28 · FORT 29 (+ variantes
  RESIDUEL_*) ; mouvement de terrain FAIBLE 96 · FAIBLE_A_MODERE 31 · MODERE 2 · MOYEN 299 ·
  MOYEN_B2U 3 · MOYEN_SECURISABLE 2 · **ELEVE 360 · TRES_ELEVE 124**. Le repli d'ingestion
  envoyait ELEVE/TRES_ELEVE sur « moyen » (aucun mot-clé reconnu) → les 484 zones LES PLUS GRAVES
  étaient marron, jamais de rouge. Correctif : classe d'AFFICHAGE 4 teintes (faible beige · moyen
  marron · élevé orange · **très élevé ROUGE**) posée à l'ingestion + backfillée ; la légende suit
  les classes RÉELLEMENT SERVIES (dérivées des données à l'écran, jamais promises d'avance) ;
  inondation garde son triptyque officiel (fort = rouge). Captures avec légende. NOTE séparée :
  le `niveau` de CASCADE (scoring) reste le triptyque servi par le run gelé — la correction
  ELEVE/TRES_ELEVE→fort de l'ingestion ne s'appliquera qu'à la prochaine ré-ingestion + run
  (avec régénération du golden) : rien n'est changé en silence sur le scoring servi.
- **R7 — hachures d'aléas retirées — FAIT.** Aplats pleins semi-transparents seuls, opacité
  calibrée par fond (sombre 0,45 · clair 0,55 · ortho/IGN 0,45). Une capture par fond
  (`R7-alea-mvt-zoom-{sombre,clair,ortho,plan}-avant/apres`).
- **R8 — contours d'aléas au zoom, même règle sur les 4 fonds — FAIT.** Expressions PARTAGÉES
  (`ALEA_LINE_W/OP`) : contour absent < z13, apparaît vers z14, plein à z16 — appliquées à la
  création, en Clair, en Sombre ET dans le variant photo (qui ne garde que sa couleur sombre).
  Captures 2 zooms × ortho/IGN/sombre (`R8-alea-*-z12/z15-avant/apres`).
- **R9 — arrêts cliquables — FAIT.** Bulle MINIMALE au clic : nom de l'arrêt · ligne(s) ·
  réseau, rien d'autre (recette : « Félix Guyon · Lignes 10 · 12 · 21 · 22 · 22a · Citalis »,
  capture `R9-arret-bulle-apres`). Les NOMS de lignes (`route_short_name` de routes.txt) sont
  posés à l'ingestion (attrs.lignes_noms) ET backfillés sur les 9 956 arrêts en base ; l'entrée
  « Arrêts de transport en commun » est dédiée (les tracés restent dans « Transport public »).

## LOT 2 — tableaux, listes et survols (commit 2)

- **R10 — liste des communes (« Toute l'île ») — FAIT.** Infobulle qui répétait le nom RETIRÉE ;
  « voir la fiche → » en **jaune opaque** au survol (classe `.hover-jaune` — l'action secondaire
  se distingue du survol vert de la ligne). Inventaire des infobulles refait ci-dessous.
  Capture `R10-communes-voir-fiche-hover-apres` (ligne verte + bouton jaune).
- **R11 — tableau des 24 communes — FAIT.** Modale élargie (1 100 → 1 240 px), marges internes
  gauche/droite posées (px-6 conteneur + px-2 en-tête/rangs, lignes arrondies — plus collées aux
  bords), infobulle du nom retirée, « Fiche → » jaune au survol. Captures survol ligne + survol
  « Fiche → ».
- **R12 — « Ouvrir le Radar → » — FAIT.** Aligné sur la ligne de base du libellé (items-baseline).
- **R13 — évolution du marché en grand — FAIT.** Même coquille plein écran que « Les 24
  communes » (`EvolutionTablePanel` : overlay, carte flottante 1 240 px, en-tête + croix), même
  moteur M18 dedans (tableau trimestriel, en-tête collant, légende sous le tableau) — aucune
  donnée nouvelle. La porte du panneau ouvre la modale. Captures côte à côte
  (`R13-24communes-modale` / `R13-evolution-modale`) : même grammaire.
- **R14 — acquisitions — FAIT.** Plafond de 50 en dur LEVÉ (limit serveur piloté, 200 par
  défaut) ; « Voir plus — N / M chargés » par 200 ; filtre par année MULTI-SÉLECTION (chips des
  années présentes dans les données) ; le compteur reflète le filtre. Recette : Saint-Paul
  773 → 200/400… chargés.
- **R15 — cartes d'entrée d'outils en vert opaque — FAIT.** Corrigées : PLU (2 voies — le
  « contour vert » vu par Vic) et Prospection solaire (2 cartes). Inventaire complet ci-dessous.
- **R16 — chips d'exemples — FAIT.** Mécanique T6 (`.chip chip-mint`) sur les libellés de type
  (nom / SIREN / IDU / adresse) : fond sombre plein + texte clair sur ligne survolée.
- **R17 — SIREN/SIRET bleu souligné — FAIT.** Le composant unique `<Siren/>` passe en
  `.lien-siren` (bleu #5AA9E8, souligné) — la SEULE exception « bleu » de la DA. Couvre les 8
  surfaces posées en T2 (fiche parcelle PM, historique ×2, Scan, Assemblage/Promoteurs ×2,
  Veille, drawer Permis). Restent en texte (comme noté en T2, contexte non-JSX) : le popup
  patrimoine de la carte (tuple HTML) et le champ éditable admin Programmes. Acquisitions et
  fiche commune n'affichent pas de SIREN brut (vérifié). Test `Siren.test.tsx` (classe).
- **R18 — Scan patrimoine : liste repliée au départ — FAIT.** En fusion, UN SEUL état visible :
  au chargement, bandeau déplié + « Voir ses parcelles → » (liste MASQUÉE) ; le clic replie le
  bandeau ET ouvre la liste (mécanique O5 conservée). Captures avant (doublon) / après.

## LOT 3 — outils (commit 3) + R31 (commit 4)

- **R19 — contour vert des blocs retiré — FAIT.** Le bloc de résultat de « Trouver les
  parcelles » (« N parcelles · unités → SDP gabarit ») passe en bordure neutre. Inventaire des
  blocs à bordure verte résiduelle ci-dessous — tous les BLOCS-conteneurs du même gabarit
  (`border-mint/40 bg-mint/[0.07]`) traités ; chips, badges et boutons verts conservés
  (affordance, pas des blocs).
- **R20 — paragraphe d'aide retiré — FAIT.** L'aide (« Décrivez votre programme… le Copilote
  peut remplir ») vit derrière un « i » à côté du périmètre.
- **R21 — annuaire PLU : le nom d'abord — FAIT.** Liste UNE colonne (la grille 2 colonnes
  écrasait « Saint-André » en « S… » dès qu'un badge s'ajoutait) ; badge « révision », UN mot, à
  droite, sur une ligne (détail — prescription, règlement non servi — dans le title).
- **R22 — compteur PLU réconcilié — FAIT.** « **23 PLU en vigueur (24 communes, 1 au RNU) · 3
  procédures en cours** ». Mesure du « 21 » : c'était le compte des règlements SERVIS par le GPU —
  Saint-André et Saint-Leu ont un PLU **en vigueur** (la révision ne l'abroge pas) mais leur
  règlement n'est pas servi par le Géoportail : ces 2 trous de SOURCE sont désormais NOMMÉS sous
  le compteur (« règlement non servi par le Géoportail — texte à consulter en mairie »), plus
  jamais cachés. Liste des 24 avec leur état réel ci-dessous. Test `test_retours13_lot3`.
- **R23 — badge sur une seule ligne — FAIT.** `whitespace-nowrap` + un seul badge par carte
  (cf. R21) : Trois-Bassins tient sur une ligne.
- **R24 — référence courte dans la vérification PLU — FAIT.** La barre passe sur le MOTEUR
  UNIQUE (`ParcelInput` : IDU, référence courte, adresse) — avant, champ IDU brut : `BZ1065`
  laissait le bouton mort (reproduit, capture avant). Re-test T1 RÉEL barre par barre ci-dessous.
- **R25 — accordéon « Attention » — FAIT.** Les deux blocs d'explication (« Périmètre : toute
  l'île… » et « Recalcul à blanc… ») passent en `<details>` repliés « Attention ▾ » ; le fait
  « commune en procédure » reste visible d'emblée (c'est un fait, pas une explication).
- **R26 — taxe d'aménagement préremplie — FAIT.** La surface taxable se préremplit avec la
  **SDP constructible au gabarit** (résiduel du run servi), étiquetée « pré-rempli par LABUSE —
  SDP au gabarit, modifiable (la surface taxable est celle de VOTRE projet) » ; terrain + zone
  déjà posés ; toute retouche efface l'étiquette ; calcul en direct. Recette : BZ1065 →
  26 m² préremplis (capture).
- **R27 — zoom franc — FAIT.** `focusParcelle` vise **18** (parcelle standard), 17 (> 2 500 m²),
  16,5 (> 1 ha) — padding inchangé, plancher au lieu du 16 fixe. Mesuré à la recette : zoom
  final 18 (était 16). Primitive PARTAGÉE (Étudier un bien, Permis, œil des Projets).
- **R28 — « Lire la zone » vert opaque — FAIT.** Bouton d'action principale (`bg-mint text-bg`),
  plus le fond terne.
- **R29 — CBO « 20 opérations ?? » : mesuré — FAIT.** La frise comptait les permis (≥ 1 logement)
  sur les parcelles que CBO **possède encore** (fichier DGFiP) : un promoteur revend après
  livraison → les opérations livrées SORTENT de ce compte, et les SCI/SNC d'opération n'y sont
  pas — d'où un chiffre bas mais pas faux. Mesures : **pétitionnaire direct CBO TERRITORIA
  (452038805) = 112 permis · 1 213 logements depuis 2013** ; filiales via le lien de gérance
  INPI (`pm_dirigeants.gerant_siren`) : 13 sociétés gérées par CBO, dont 2 avec permis — CBO
  PROPERTY (11 permis, locaux) et CBO DEVELOPPEMENT (2 permis, 78 lgt) ; le rapprochement par
  ADRESSE DE SIÈGE est documenté NON FIABLE (« La Mare » = un quartier entier — Mutualité,
  Colipays… ressortent) et N'EST PAS utilisé. L'écran dit désormais le périmètre (« permis ≥ 1
  logement sur les parcelles que la société possède encore — les opérations livrées puis
  revendues sortent de ce compte ») + la ligne pétitionnaire + filiales identifiées. Jamais un
  total gonflé sans méthode.
- **R30 — permis hôtel AX0439 : cause trouvée, corrigée — FAIT.** (1) Le permis EXISTE en base :
  **PC 97441816A0077, autorisé le 18/11/2016, destination 2 = « hôtels » (dictionnaire Sitadel3
  SDES vérifié), état 5 = « Commencé »** — chantier en cours, cohérent avec « en travaux depuis
  plus de 3 ans ». (2) Cause : rattaché à la parcelle **97418000BC0328, disparue du cadastre
  courant** (division/remembrement — ni `parcels` ni l'API Carto ne la connaissent) → geom NULL →
  invisible de la carte et des fiches. **10 799 permis sur 50 541 étaient dans ce cas.**
  (3) Correctif : l'adresse du terrain (colonnes ADR_* du flux Dido, non ingérées jusqu'ici)
  voyage dans raw + **repli adresse → parcelle en 3 passes prudentes** — BAN exacte (numéro +
  voie + commune) : 1 617 rattachés · orthographe approchée (trigram ≥ 0,8, candidat unique —
  « ROLLAND » vs « Roland ») : 438 · interpolation entre numéros ENCADRANTS de la même voie
  (le n° 50 tombe dans un trou de numérotation BAN 20→62) : 197. **2 252 permis récupérés**,
  position marquée telle quelle (raw.geoloc, servie à la fiche permis). Le reliquat (8 547) est
  un état de fait de la source, dit. La destination est désormais SERVIE avec son libellé
  (hôtels, bureaux, commerce… — plus un code muet) ; fraîcheur Sitadel : mensuelle (refresh
  documenté, dernier mois 2026-07). (4) Recette : la fiche AX0439 montre le permis à **37 m**,
  daté, sourcé, « hôtels », position « adresse interpolée (approximative) » ; viabilisation
  Sainte-Marie reconstruite (c100 4 → 5). Tests `test_retours13_lot3` (repli adresse + libellés).
- **R31 — toiture simple/double pente : DISPONIBLE, prototype 81 %, INTÉGRÉ (commit séparé) —
  FAIT.** Détail des vérifications URL par URL ci-dessous. La Géoplateforme diffuse les modèles
  LiDAR HD **sur le 974** (couches WMS GeoTIFF MNS et **MNH** en RGR92 UTM40S / EPSG:2975,
  50 cm, LO — valeurs réelles vérifiées sur Saint-Denis). Prototype
  (`qa/solaire/toiture_probe.py`) : pente+orientation par pixel du MNH sur l'emprise BD TOPO,
  pics d'orientation = pans → plat / monopente / double pente / croupe-complexe ; 20 bâtiments,
  planches CONTRÔLÉES À L'ŒIL contre l'ortho (jointes au dépôt) : **13/16 jugeables corrects
  (81 %)** — seuil du mandat atteint ; erreurs typées (croupes/toits en L lus « monopente »,
  végétation au contact). Intégration : calcul À LA DEMANDE (1 requête WMS ~1 s) + cache
  (`toiture_lidar`) — aucune ingestion de masse, run solaire gelé intact ; la fiche soleil
  affiche « Toiture : double pente · pente médiane 18,3° (Dérivé — LiDAR HD IGN) » avec
  l'INCERTITUDE DITE (~1/5 mal classé, à vérifier sur la photo affichée dessous). Recette
  navigateur OK (capture `R31-solaire-toiture-apres`).
- **R32 — l'œil des Projets zoome comme Étudier un bien — FAIT (via R27).** Même primitive
  `focusParcelle`, même réglage (aucun code propre à l'œil).

---

## Vérifications

- **tsc 0 · build OK · vitest 170/170** (verrous neufs : R11 hover-jaune, R17 lien-siren).
- **Backend — suite complète : 2 298 passed · 49 skipped · 1 failed PRÉ-EXISTANT**
  (`test_front_reliquats::test_r5_etudier_deux_marges…` attend la chaîne « la charge calibrée »
  dans EtudierBien.tsx — chaîne DÉJÀ ABSENTE à la base de branche `b222d00f`, prouvé par
  `git show` : libellés refondus par RETOURS-12 O2, test non mis à jour alors ; hors mandat,
  non corrigé en silence). Tests neufs : `test_retours13_lot1` 5/5 · `test_retours12_c2_tcsp`
  réécrit 5/5 · `test_retours13_lot3` 4/4 (+1 skip base de test sans résiduel). Dettes
  attrapées par la suite et soldées : deps `rasterio`/`scipy` déclarées (groupe `[lidar]`),
  sentinelle 65 → 68 sources classées.
- **Golden (`qa/golden_check.py`, API up, sans throttling)** : 71/119 PASS, **48 FAIL
  PRÉ-EXISTANTS et BRANCH-INDÉPENDANTS** — tous le MÊME écart d'UN champ de libellé
  (`score_v2.pourquoi` : « SDP résiduelle : donnée non disponible » attendu vs « SDP résiduelle
  nulle ou non retenue (parcelle contrainte) » servi), libellé changé par `bc142e4f`
  (RETOURS-7, 01/09, ANTÉRIEUR à la branche) sans régénération de la référence golden.
  RETOURS-13 touche **0 fichier scoring et 0 référence golden** (diff vérifié
  `git diff b222d00f..HEAD -- src/labuse/scoring qa/golden*` = vide) — même situation que
  RETOURS-12 (« golden intact, 0 fichier scoring »). La branche `fix/golden-regen` (non mergée)
  répare précisément cette classe de dérive.
- Aucun sous-agent sur git, aucun `git add -A`, aucun merge. Base réelle, aucun run recalculé.

---

## ANNEXE R4 — recherche moyenne tension, URL par URL (05/09/2026)

| URL | Constat |
|---|---|
| `opendata-reunion.edf.fr/explore/dataset/lignes-haute-tension-hta-aerien/` | **404** — l'URL Opendatasoft n'existe plus (portail refondu sous Koumoul/data-fair ; l'API ODS répond 410 Gone). C'est cette refonte qui a fait conclure « couches retirées » à C1. |
| `opendata-reunion.edf.fr` (portail actuel) | ACTIF — catalogue de ~20 jeux. `datasets/lignes-haute-tension-hta-aerien-run` : **existe, 4 211 enregistrements (860 ko), géométrie LineString réelle (geo_shape), licence Ouverte v2.0, données « mises à jour février 2020 », republication 16/10/2025, export CSV data-fair** ; `datasets/2-lignes-haute-tension-hta-souterrain` : **15 269 enregistrements (7,7 Mo), mêmes conditions**. Seuls champs servis : statut (« En exploitation ») + géométrie — contenu réduit « afin de renforcer la sécurité publique » (mention du portail) : généralisé, PAS retiré. |
| `reunion-edf-sei.opendatasoft.com` (variante souterraine) | **404** — ancien domaine ODS mort (même refonte). |
| `data.regionreunion.com/explore/dataset/lignes-haute-tension-hta-aerien/` | **Miroir vivant** : 4 211 enregistrements, modifié 2020-09-29, Licence Ouverte v2.0 (Etalab) — cohérent avec le portail EDF (géométrie identique, plus ancienne). |
| data.gouv.fr (organisation EDF SEI) | Les 4 jeux « Lignes haute tension (HTA/HTB × aérien/souterrain) - Réunion » sont **référencés** au nom d'« EDF Systèmes Energétiques Insulaires ». |
| Postes sources (`datasets/postes-sources-reunion`) | Fiche présente mais **0 enregistrement** — jeu VIDÉ le 24/12/2025 (« données de cartographie mises à jour afin de renforcer la sécurité publique »). Le point « postes sources » du mandat n'est PAS réalisable ; documenté au catalogue. |

Décision : ingestion depuis le portail EDF (source primaire, la plus fraîche), miroir Région en
repli documenté. Bonus constaté (non ingéré, hors mandat) : le portail publie aussi la **BT
aérien** (46 278 tronçons) et les pylônes HTB.

## ANNEXE R5 — recherche TCSP, URL par URL (05/09/2026)

| Piste | Constat |
|---|---|
| `debatpublic.fr/projet-train-reunion-express` | Débat public CONFIRMÉ du 19/08 au 26/11/2026. Aucun dossier du maître d'ouvrage téléchargeable sur la page ; la cartographie des hypothèses de tracé est un **viewer 3D externe** (`client.landweb3d.com/cr-reunion/Reunion-Express_PC/index_jaune.html`) sans aucun export SIG (page inspectée : aucun geojson/wms/shapefile). → PAS de tracé ingéré (on ne numérise pas une image) ; lien dans le « i », source « à venir » au catalogue, **sentinelle posée** (en-tête du viewer). |
| TCO / Le Port (Rico Carpaye) | tco.re : pages Kar'Ouest + PDU, **aucun SIG public** des voies réservées en travaux. |
| CIREST (ESTI+) | Chantiers confirmés (DUP 2018, av. Jean Jaurès Saint-Benoît, marchés publics en cours) — **aucun tracé SIG public** (cirest.fr = actualités/indemnisation). |
| CIVIS (`tcsptoutsavoir.com`, civis.re) | `tcsptoutsavoir.com` : **injoignable (ECONNREFUSED)**. civis.re publie « Données SIG d'une partie du TCSP de Saint-Pierre » (RAR, 2024) — TÉLÉCHARGÉ et OUVERT : c'est un **récolement de chantier** (couches réseaux EP/EU/EDF, signalisation, surfaces, mobilier, arbres) d'un tronçon d'~1,5 km, PAS un tracé d'axe → inutilisable sans re-dessin (interdit). 2,6 km livrés documentés par la comm' CIVIS. |
| CINOR (TCSP nord / boulevard sud) | BAOBAB = projet THNS/BHNS (comm'). `opendata-sig.saintdenis.re` (ArcGIS Ville de Saint-Denis) interrogé : **0 jeu** TCSP/BHNS/site propre/busway. |
| PEIGEO / AGORAH (`peigeo.re:8080/geonetwork`) | Recherches « TCSP » 0 · « Trans-Éco Express » 0 · « voies réservées » 0 · « BHNS » 0 · « transport commun » 0 · « bus » 1 (« Les arrêts de bus ») · « SAR » 23 fiches (destination des sols, zones préférentielles — pas d'axe TCSP en couche). |
| `data.regionreunion.com` | Recherches « TCSP », « site propre », « Trans-Éco Express », « VRTC », « voies réservées » : **0 jeu pertinent** (3 résultats hors sujet). |
| `transecoexpress.re` (Région) | **Injoignable (ECONNREFUSED)** au 05/09. |
| OSM (Overpass, 974) | **166 ways** : 89 `highway=busway` (chaussées dédiées — Saint-Denis bd sud/Maréchal Leclerc, Sainte-Marie, Saint-Pierre…), 24 `busway=lane/opposite_lane`, 28 `psv=designated`, 24 `bus=designated` + `lanes:psv`. **La seule géométrie traçable, ingérée** (étiquetée OSM/ODbL, date d'extraction au catalogue). |
| Légifrance (base légale) | L151-36 (LEGIARTI000052866917) et L151-35 relus EN VIGUEUR : 800 m depuis la gare/station, 1 place max (0,5 LLS), « qualité de la desserte », modifiés par la **loi n° 2025-1129 du 26/11/2025 art. 20** (vig. 28/11/2025). Mesure DEPUIS LA STATION à vol d'oiseau (CE 2022). |

## ANNEXE R31 — vérification LiDAR HD, URL par URL (05/09/2026)

| Piste | Constat |
|---|---|
| `data.geopf.fr/telechargement` (cartes.gouv IGNF_MNS-LIDAR-HD) | La ressource « IGNF_MNS-LIDAR-HD » **n'existe pas** dans le service de téléchargement (catalogue parcouru en entier : seuls des jeux LiDAR de TEST Oise/Isère « NUALID »). La voie « dalles 1 km à télécharger » du mandat n'est pas celle qui marche. |
| `data.geopf.fr/wms-r` (GetCapabilities) | **LA voie qui marche** : couches `IGNF_LIDAR-HD_MNS_ELEVATION.ELEVATIONGRIDCOVERAGE.RGR92UTM40S` et `IGNF_LIDAR-HD_MNH_...RGR92UTM40S` — des variantes **dans la projection de La Réunion (EPSG:2975)**. GetMap GeoTIFF 50 cm testé sur Saint-Denis : **valeurs réelles 4-70 m** (pas du no-data). Le MNH (MNS−MNT, déjà calculé par l'IGN) sert directement le modèle de hauteur du toit. |
| Méthode / prototype | 20 bâtiments (Saint-Paul, 80-600 m²) : MNH masqué à l'emprise BD TOPO, pente/orientation par pixel, pics d'orientation lissés = pans. Contrôle à l'œil planche par planche (ortho + MNH côte à côte, `qa/solaire/toiture_planches/`) : 13 ✓ / 3 ✗ / 4 injugeables (végétation, toit caché) → **81 % sur les jugeables** ; erreurs = croupes et toits en L. Seuil 80 % atteint → intégré (à la demande + cache, incertitude dite). Voie de reprise si Vic veut plus : segmentation par plans (RANSAC) + emprises par pan. |

## ANNEXE R10 — inventaire des infobulles, liste par liste (après retraits)

| Liste / surface | Infobulle | Statut |
|---|---|---|
| Menu « Toute l'île » (Header) — nom de commune | `title={commune}` (répétait le nom) | **RETIRÉE (R10)** |
| Menu « Toute l'île » — « voir la fiche → » | « SRU, ANRU, PLH, marché logement (n'affecte pas le périmètre) » | gardée (faits non affichés) |
| Tableau 24 communes — ligne | `title={commune}` (répétait le nom) | **RETIRÉE (R11)** |
| Tableau 24 communes — en-têtes de colonnes | définition de l'indicateur | gardée (fait non affiché) |
| Acquisitions — ligne parcelle | — (retirée en T5/O11) | absente ✓ |
| Acquisitions — « Scan patrimoine → » | « Scan patrimoine de {dénomination} » | gardée (dit la cible du clic) |
| Pastilles communes carte (MapView) | nb de parcelles chaudes seul | conforme T5 ✓ |
| Annuaire PLU — badge « révision » | procédure + date de prescription + PLU en vigueur + règlement | gardée (faits non affichés) |
| Densifier — colonne SDP | détail du calcul de déduction | gardée (définition) |
| Kanban Projets — ligne | « Ouvrir la fiche · glisser pour décider » | gardée (2 affordances, décision T5) |
| Radar — badge « Sous le marché » | référentiel €/m² | gardée (fait non affiché) |
| Instruction (M10) — vignette commune | rang/délai/IQR/tendance | gardée (faits non affichés) |
| ZAN (moteurs) — barre commune | % budget consommé + ha | gardée (faits non affichés) |
| Admin (Produit, Licences…) | liens techniques | hors vue client |

## ANNEXE R15 — inventaire des cartes d'entrée d'outils

| Écran d'entrée | Cartes | Survol |
|---|---|---|
| Accueil (panneau gauche) | Explorer la carte · Suivre le marché · Demander au Copilote · Ouvrir un outil | `.acc-entry` — vert opaque ✓ (mauve pour le Copilote : surface IA) |
| PLU | Annuaire PLU · Procédures & changements | **corrigé R15** : hover-fill (était contour vert) |
| Prospection solaire | Piscines · Ensoleillement | **corrigé R15** : hover-fill |
| Communes | Comparaison · Évolution · Acquisitions (Porte) | hover-fill ✓ |
| Étude de zone | Chalandise · Zone particulière | hover-fill ✓ |
| Tuiles du tiroir Outils (GrilleOutils) | 15 outils | hover-fill ✓ |
| Scan patrimoine (exemples) | 4 chips d'exemples | hover-fill ✓ (+ R16 chips) |

## ANNEXE R19 — inventaire des blocs à bordure verte (traités)

Gabarit fautif `border-mint/40 bg-mint/[0.07]` (bloc-conteneur) → bordure neutre `border-line-2`
(fond conservé, légèrement adouci) :
- M22Programme : bloc de résultat épinglé (**le bloc de Vic**) + bannière d'aide (retirée, R20) ;
- blocB (Pièges & risques / 24 communes) : bannière d'intro ;
- EtudierBien : bannière descriptive ; TaxeAmenagement : bloc d'intro ;
- ModulePanel : primitive `Banner` partagée (tous les modules) + confirmation Courrier ;
- moteurs (Assemblage/ZAN) : bannière ; EtudeZone / Renouvellement / TimeMachine / MonSecteur /
  ProprietaireHistorique : blocs du même gabarit ;
- PluAnnuaire : carte « Télécharger le PLU intégral » (bordure neutre).
CONSERVÉS (pas des blocs) : chips/badges (`Sourcé`, raison), boutons d'action verts
(« Chercher », « Vérifier », « Voir ses parcelles »), état sélectionné ScoringV2, admin.

## ANNEXE R24 — barres × référence courte (re-test RÉEL, BZ1065, navigateur)

`BZ1065` existe dans UNE commune (97411000BZ1065, Saint-Denis) → le comportement attendu est la
**résolution directe** (la désambiguïsation ne se déclenche que multi-communes, testée en T1 avec
BW0917 → 2 candidates).

| Barre | Résultat BZ1065 |
|---|---|
| Vérification PLU (VerifProcedure) | **résolu direct → résultat rendu** (AVANT : bouton mort — champ IDU brut ; corrigé R24, capture avant/après) |
| Omnibox (header) | résolu (fiche/zoom) ✓ |
| Étudier un bien | résolu direct ✓ |
| Pièges & risques | résolu direct ✓ |
| Prospection solaire | résolu direct ✓ |
| Remonter le temps | résolu direct ✓ |
| Courrier propriétaire | résolu direct ✓ |
| Étude de zone | résolu direct ✓ |
| Densifier l'existant | résolu direct ✓ |
| Diligence | fusionnée dans « Pièges & risques » (même barre, couverte ci-dessus) |
| Mon secteur | outil masqué (fusionné dans « Étudier un bien » — RETOURS-3 R5) |
| Scan patrimoine | résolution PROPRE (nom/SIREN/IDU/adresse — orientée propriétaire) : hors périmètre référence-parcelle, comme acté en T1 |
| Barres full-text (annuaire PLU, CRM, Sources, intra-fiche, admin) | filtrage local, hors sujet T1 (inchangé) |

## ANNEXE R22 — les 24 communes, état réel

Servable (règlement GPU servi) ×21 : Les Avirons, Bras-Panon, Entre-Deux, L'Étang-Salé,
Petite-Île, La Plaine-des-Palmistes, Le Port, La Possession, Saint-Benoît, Saint-Denis,
Saint-Joseph, Saint-Louis, Saint-Paul, Saint-Pierre, Sainte-Marie, Sainte-Rose, Sainte-Suzanne,
Salazie, Le Tampon, Cilaos + **Les Trois-Bassins (servable ET révision générale en cours)**.
**Saint-André** et **Saint-Leu** : PLU en vigueur, révision générale en cours, règlement NON
servi par le GPU (trou de source nommé à l'écran). **Saint-Philippe** : RNU.
→ 23 PLU en vigueur · 1 RNU · 3 procédures (révisions générales Sudocuh).
