# COMPTE-RENDU RETOURS-12 — `fix/retours-12`

Recette navigateur sur la base réelle (backend :8000 mode local, front `/socle/` buildé),
un commit par lot. Une ligne par travail : **fait** / **fait autrement** (pourquoi) / **pas fait** (motif).
Inventaires T1/T2/T5/T7/A1 joints dans ce dossier (`INVENTAIRE-*.md`).

Prérequis vérifiés : RETOURS-11 (11a `0eeee93f` + 11b/c/d `cf4d6052`) et DESTINATIONS-1
(`2ac9e39e`) sont mergés sur `main`. Run servi lu par pointeur (`runs.current()`), q_v12 non basculé.

---

## LOT T — transversal (commit 1)

- **T1 — recherche par référence courte `BW0917` — FAIT.** Grammaire UNIQUE dans `lib/format.ts`
  (`estSectionNumero` + `normSectionNumero` — casse, espaces, tirets, zéros de tête, LOI-3). Le champ
  partagé `ParcelInput` (≈ 12 outils : Étudier, Faisabilité, Risques, Solaire, Remonter le temps,
  Courrier, Diligence, Étude de zone, Densifier, Mon secteur…) reconnaît désormais la référence courte
  et **désambiguïse** : plusieurs communes → liste (commune + surface), l'utilisateur tranche ; la commune
  du contexte passe en tête. L'Omnibox du header alignée sur la même grammaire (plus de `remote[0]` au
  hasard : multi-communes → toast qui nomme les communes). Backend `/parcels/search` renvoie la surface
  pour la désambiguïsation. **Recette navigateur** : `BW0917` dans « Étudier un bien » → 2 candidates
  (Saint-Benoît 1 434 m² · Saint-Paul 8,17 ha) ; forme `BW 917` normalisée → même résultat. Tests
  `refCadastrale.test.ts` (3 formes × reconnaissance/normalisation). Inventaire complet : `INVENTAIRE-T1`.
  - *Réserve honnête* : `ScanPatrimoine` garde sa résolution propre (`resoudre()`, orientée propriétaire :
    nom/SIREN/IDU/adresse) — hors périmètre « référence parcelle », non rebranché. Les barres full-text
    (PLU annuaire, CRM, Sources, intra-fiche, admin Flux) restent du filtrage local, hors sujet T1.
- **T2 — SIREN/SIRET cliquable Pappers — FAIT.** Composant unique `shared/Siren.tsx` (SIREN 9 → lien
  `pappers.fr/entreprise/{siren}`, SIRET 14 affiché entier mais lié sur les 9 premiers, pas de lien si
  la valeur n'a pas 9/14 chiffres, `target=_blank rel=noopener`). Posé sur : fiche parcelle propriétaire
  PM (Fiche.tsx), historique propriétaire (×2), Scan patrimoine, Assemblage/Promoteurs (moteurs ×2),
  Veille promoteurs, drawer Permis (ModulePanel). Tests `Siren.test.tsx` (9/14/non-conforme/vide).
  Inventaire : `INVENTAIRE-T2`.
  - *Fait autrement* : le SIREN du **popup patrimoine** (ModulePanel `fiche` tuple `[string,string]`) et
    le badge **admin Programmes** (champ éditable) restent en texte — types/contexte non-JSX ; notés.
- **T3 — rail latéral fixe — FAIT (correctif, retest post-mandat).** Le shell fixe le rail par flexbox,
  mais le symptôme vu par Vic est réel sur **fenêtre de faible hauteur** : le rail restait fixe alors que
  son **contenu défilait en interne** et faisait sortir Admin/Sources de la vue (mesuré : `sourcesVisible:false`
  et `navScrolls:true` dès h ≤ 560 px). **Correctif** : la zone basse (Admin/Sources) sort du conteneur
  `overflow-y-auto` et s'épingle en bas du rail (`shrink-0`) ; l'oiseau reste en haut ; seul le bloc des
  catégories défile si nécessaire. Re-mesuré : Sources visible à h = 900 / 560 / 420. Capture
  `T3-rail-fenetre-basse`. (Livré en correctif Lot T, commit dédié — Lot T était déjà commité.)
- **T4 — en-têtes de tableau collants + opaques — FAIT.** Classe partagée `.thead-sticky` (fond opaque
  `--bg-3`, `z-20` — sous les overlays z-40, au-dessus des lignes). Appliquée à Densifier
  (`Renouvellement.tsx` — était sticky **sans z-index**, cause du chevauchement), Prospection solaire,
  et la table « 24 communes » (`blocB.tsx`, remontée z-10 → z-20). Admin (Courrier/Produit/Destinations)
  laissés non-sticky (tables courtes).
- **T5 — infobulles redondantes retirées — FAIT.** Pastilles de communes (MapView) : l'infobulle ne
  garde QUE le fait non affiché (nb de parcelles chaudes), plus de répétition du nom ni de
  « ouvrir la fiche » ; sans fait à ajouter → aucune infobulle. Lignes d'acquisitions (Communes) :
  « Ouvrir la parcelle {idu} » retirée (le lien est déjà sous la ligne — voir O11). Veille promoteurs :
  « Ouvrir la fiche parcelle » retirée. Inventaire : `INVENTAIRE-T5`.
- **T6 — contraste garanti au survol — FAIT.** Correctif AU COMPOSANT : `.chip` + variantes de teinte ;
  sur `.hover-fill:hover` la chip bascule en fond sombre plein (`--ink`) et reprend sa teinte via
  `--chip-fg` (contraste ≥ 4,5:1) — fin du bug racine `.hover-fill:hover * { color:--ink }` qui rendait
  le millésime `2024→2025` vert-sur-vert dans Acquisitions. Appliqué au badge millésime (Communes).
- **T7 — sortie du prisme « opération » — FAIT (règle transversale + libellés de 1er niveau).**
  Les verdicts d'opération de premier niveau ne se présentent plus comme des faits sur la parcelle :
  « L'opération ne finance pas ce foncier » → « à ces hypothèses, une opération de ce type ne dégage rien
  pour le terrain — c'est le résultat d'un scénario, pas la valeur de la parcelle » (EtudierBien) ;
  idem Assemblage M16 (moteurs) et restitution Copilote (strings). Français d'abord : « CA visé » →
  « Chiffre d'affaires visé (CA) ». Bannière « Étudier un bien » rendue descriptive/neutre. Tests
  existants mis à jour (Assemblage, etat1 Copilote) vers le nouveau libellé. Inventaire : `INVENTAIRE-T7`.
  - *Report assumé* : la **refonte structurelle deux niveaux** de l'accueil (descriptif d'abord, bilan
    d'opération derrière un geste explicite) relève d'**O2** (Faisabilité) et sera livrée dans le Lot O bloc 2.

**Vérifs Lot T** : tsc 0 · build OK · suite frontend 160/160 (dont 8 nouveaux tests) · backend
`/parcels/search` validé sur base réelle · 0 erreur page à la recette · golden intact (0 fichier scoring touché).

---

## LOT C — carte & couches (commit 2)

Investigation données faite sur la base réelle avant tout code.

- **C1 — réseaux MT / HT — FAIT AUTREMENT (HT clarifiée ; MT documentée sans couche).** La couche HAUTE
  tension existe déjà (`lignes_ht`, BD TOPO IGN) — en base : **40 lignes 63 kV + 8 lignes 90 kV**, pur
  transport. Son libellé/`i` est clarifié (« réseau de transport 63 et 90 kV »). Pour la MOYENNE tension :
  **aucune source ouverte fiable au 974** — le distributeur est **EDF SEI** (Enedis n'opère pas dans les
  DOM), qui a **retiré ses couches ouvertes le 24/12/2025**, et la BD TOPO ne porte que le transport HT
  (aucune ligne HTA ~20 kV en base). Conformément au mandat (« si aucune source fiable, on ne pose pas la
  couche : on l'écrit »), **la couche MT n'est pas posée** ; le motif est dit dans l'`i` de la couche HT.
- **C2 — TCSP + distance à l'axe structurant — FAIT (rouvert : dérivé du GTFS).** Mesure du GTFS déjà
  en base : pas de tables GTFS brutes, mais les tracés/arrêts sont dérivés dans `spatial_layers`
  (`transport_ligne` 300 lignes / 6 réseaux, `transport_arret` 9 956) ; les attrs des lignes ne portent
  que `route_id`/`route_type` (tous 3=bus), sans nom. En re-mesurant le **GTFS Citalis (CINOR)** à la
  source (routes.txt), la ligne **« BAO — BAOBAB Express »** ressort : c'est l'axe express structurant de
  la CINOR, **en base** (transport_ligne route_id=BAO, tracé aller/retour), **corridor Saint-Denis ↔
  Sainte-Marie/Sainte-Suzanne** (bbox 55,49→55,63, côte nord — cohérent avec « part de Sainte-Marie »),
  **16 arrêts**, **EN SERVICE** (calendriers GTFS actifs jusqu'à fin 2026). Piège écarté : `dist_tcsp_m`
  et `amenite/tcsp` (6 464) en base sont en réalité les **arrêts de bus OSM génériques** (mal nommés),
  pas l'axe en site propre — non réutilisés (ce serait trompeur). **Livré** : (a) couche carte dédiée
  « Axe structurant (BAOBAB Express) » — kind synthétique `tcsp_axe` dérivé du GTFS déjà tracé (aucune
  ingestion neuve), trait turquoise épais, légende, `i` honnête (en service, source GTFS Licence
  Ouverte) ; (b) fiche parcelle : **distance à l'axe** + drapeau **< 500 m** avec formulation prudente
  (« le règlement PEUT moduler l'exigence de stationnement — à vérifier dans le PLU, rien n'est promis »).
  Recette : corridor rendu en carte (capture `C2-baobab-corridor-z11`), fait fiche prouvé via API
  (parcelle au contact, sous_500m). Tests `test_retours12_c2_tcsp.py` (couche = un tracé BAOBAB ; fiche
  < 500 m ; pas de faux positif « stationnement réduit »). *Livré en réouverture Lot C, commit dédié.*
- **C3 — rampes d'aléas distinctes — FAIT.** Cause racine mesurée : les niveaux étaient rendus par
  **opacité d'une couleur unique** (le camaïeu). Désormais une **teinte par niveau** (mapTheme
  `aleaInondationRamp`/`aleaMvtRamp`, expression `aleaColorExpr` sur `niveau`, opacité constante) :
  inondation **bleu → orange → rouge**, mouvement de terrain **beige → marron → rouge** (le plus grave).
  Légende refaite en tranches nommées à teintes distinctes. Recette : aléas rendus en carte (64 mvt,
  17 inondation), rampe visible (capture `C3-mvt-force-z13`) ; le toggle déclenche bien le fetch
  (`georisque_alea`). Tests `mapThemeAleas.test.ts` (3 teintes distinctes × 2 rampes × 2 thèmes).
- **C4 — couche « parcelle » : tranchée — FAIT (décision par la mesure : garder + renommer).** Mesuré :
  `parcelles` (aplat coloré par CLASSEMENT LABUSE) et `limites` (contour cadastral) sont **distinctes et
  non redondantes** avec le fond — le contour cadastral n'est PAS toujours présent (absent sur ortho et
  sur sombre). L'impression « ne sert à rien » venait du label nu « Parcelles » (en mode neutre l'aplat
  est discret). Renommées pour rendre l'utilité évidente : « Parcelles — classement LABUSE » et
  « Limites parcelles (contour cadastral) ». Rien retiré (aucune redondance établie).
- **C5 — arrêts de transport grossis — FAIT.** Rayon désormais proportionné au zoom (`interpolate` :
  z11≈3 px → z18≈10 px, avant : 2,2 px constant), **contour sombre** (`#0A0F0C`, largeur croissante) pour
  tenir sur fond clair comme sur ortho, minzoom abaissé 12 → 11. Recette : 93 arrêts rendus, nettement
  lisibles (capture `C5-arrets-z17`).
- **C6 — vue ortho : bug de la mer — FAIT.** Cause : au large de l'île, IGN ne sert que des tuiles
  no-data (blanches) → escalier en vue dézoomée. Correctif : `bounds` (emprise 974) sur les 7 sources
  raster ortho → maplibre ne demande plus ces tuiles ; au large c'est le fond de carte sombre continu.
  Recette aux zooms 8/10/12 : île en ortho, mer sombre continue, plus aucun escalier blanc (captures
  `C6-ortho-mer-zoom8/10/12`). Test `basemaps.test.ts` (tout fond ortho borné, Plan IGN non borné).

**Vérifs Lot C** : tsc 0 · build OK · suite frontend 166/166 (tests C3/C6 ajoutés) · backend
`test_retours12_c2_tcsp.py` 3/3 (C2) · recette
navigateur à 3 zooms · golden intact (0 fichier scoring). PIÈGE noté : le toggle d'une couche aléa/PPR
peut ne pas re-render sur un double-clic programmatique rapide (artefact de recette headless du tiroir
repliable) — le fetch et le rendu sont corrects en clic normal (prouvé) ; PPR non modifié se comporte
pareil, donc pré-existant, hors périmètre C3.
## LOT O bloc 2 — outils (O1-O7)

- **O2 — « Faisabilité / Étudier un bien » retapée — FAIT (commit dédié).** Diagnostic écrit AVANT le
  code (`DIAGNOSTIC-O2-faisabilite.md`, ancré sur une parcelle réelle) : les −219 123 € = charge foncière
  du bilan à rebours `CA×coef − construction − VRD` (négative car la VRD, proportionnelle au terrain,
  mange le solde) ; −135 €/m² = charge/terrain ; 526 k€ = shab_vendable × prix_sortie ; 123 m² =
  shab_vendable (faisabilité). **Hypothèse du mandat CONFIRMÉE** : le prix saisi était SOUSTRAIT d'une
  charge déjà négative (`marge_a_ce_prix = charge − prix` = −219 − 500 = **−719 k€**), exact mais illisible.
  **Refonte livrée** (`EtudierBien.tsx`) : (1) premier niveau DESCRIPTIF (« Ce que porte la parcelle » :
  SDP constructible, terrain) + repères de marché (prix de sortie, terrain nu de zone) — **aucun nombre
  négatif, aucun verdict d'opération à l'accueil** ; (2) le raisonnement d'opération (bilan, charge,
  marge, calculette) derrière un geste explicite **« Analyser une opération sur cette parcelle → »** ;
  (3) chiffre de tête = ce qu'une opération **pourrait payer, plancher 0** (jamais négatif) ; (4) prix
  **COMPARÉ jamais additionné** : « Prix demandé 500 000 € · une opération pourrait en payer 0 € · écart
  500 k€ ». **Point 8 (123 vs 127)** : mesuré — tous les consommateurs (écran, Flash, PDF) lisent le
  MÊME `shab_vendable_m2` de la fourchette faisabilité, **aucun recalcul en double** (le 127 = variante
  `shab_vendable_silo`, métrique distincte, ou deux parcelles). **Point 7** : moteur unique déjà partagé
  (`bilan.py` `compute_bilan`/`compute_calculette` pour l'écran ET les PDF via `compute_bilan_servi`).
  Recette navigateur : premier niveau sans verdict (vérifié), second niveau charge « 0 € » + écart
  comparé (captures `O2-premier-niveau`, `O2-second-niveau-prix`). Tests `EtudierBien.test.tsx` réécrits
  (2 niveaux · charge plancher 0 · écart comparé sans « 719 » · bascule · alerte résiduel), 5/5.

- **O1 — « Étudier un bien » zoome et délimite la parcelle — FAIT.** Primitive COMMUNE `focusParcelle(idu)`
  (store) : zoome (flyTo zoom 16) + met en surbrillance (filtre `parcels-sel`/`ile-sel` + ping) SANS
  ouvrir la fiche — réutilise l'effet carte existant (généralisé à `selectedIdu ?? focusIdu`), pas un
  second mécanisme. « Étudier un bien » l'appelle au résultat. Recette : zoom 9,9 → 16, parcelle
  surlignée (distincte des voisines), fiche NON ouverte (capture `O1-etudier-zoom`). Réutilisable par
  O12 (Permis) et J1 (œil ambre, option ortho).
- **O3 — « Pièges & risques » : encadré « non couvert » retiré de la vue client — FAIT.** L'encadré
  « NON COUVERT PAR LA BASE — À VÉRIFIER AILLEURS » quitte l'accueil ; son contenu vit désormais dans un
  « Méthode & limites » **replié** (`<details>`, fermé par défaut). Bandeau d'intro rendu descriptif
  (plus d'aveu d'ignorance en tête). Renvoi discret à l'outil PLU pour les procédures ; réserve SUP en
  phrase courte (le CU reste la référence). Recette : ancien encadré absent (0), méthode repliée présente
  et fermée (capture `O3-pieges-methode`). Trancher les 4 lignes : PEB aérodrome & canalisations TMD →
  pas de jeu ouvert ingéré (limite descend en méthode, ingestion Géorisques/DEAL à chiffrer hors mandat) ;
  procédures PLU en cours → servies par l'outil PLU (renvoi) ; SUP hors GPU → 417 SUP décodées, réserve
  en méthode. *(Le contenu `non_couvert` vient du backend inchangé ; seule la présentation change.)*
- **O5 — « Scan patrimoine » : la liste des parcelles s'ouvre — FAIT.** Bug : la liste était noyée sous
  le bandeau (nom + 3 chiffres + détail + bouton). Correctif : bouton **« Voir ses parcelles → »** (en
  fusion) qui **replie le bandeau en accordéon** (barre compacte rouvrable « nom · N parcelles · détail ▾ »)
  → la liste prend toute la hauteur. Les opérations restent dans l'onglet « Construction » (le pont
  redondant `onVoirOperations` retiré en mode fusion ; conservé hors fusion). Pagination par 200 déjà en
  place (« 200 / 1833 · Voir 200 de plus »). Recette : clic → bandeau replié + liste visible (capture
  `O5-scan-parcelles`).
- **O7 — « Prospection solaire » : simple/double pente + photo du toit — FAIT (partiel assumé).** Mesuré :
  `parcel_solar` porte l'azimut du bâti (Estimé) mais **aucune donnée de pente de toit ni de nombre de
  pans / type de toiture** — la distinction **simple/double pente n'est PAS dérivable**. Conformément au
  mandat, on ne l'invente pas : on le DIT et on affiche l'azimut + la pente MOYENNE. Ajouté : **photo
  aérienne du toit** (ortho IGN, WMS GetMap centré sur le centroïde parcelle — lon/lat ajoutés à
  l'endpoint) surmontée d'une **rosace d'orientation** (N/S/E/O, aiguille verte alignée sur l'azimut réel
  du bâti). Libellé « Pente du terrain » clarifié (RGE ALTI, pas la pente du toit). Recette : photo +
  rosace (azimut 140°) rendues (capture `O7-solaire-photo-rosace`).
- **O6 — « Scan patrimoine » / constructions : doublons supprimés — FAIT.** Mesuré : la cause n'est PAS
  deux SIREN (CBO TERRITORIA = un seul siren 452038805, une dénomination) — c'était le LISTING qui servait
  une carte **par OPÉRATION**, si bien qu'un promoteur à plusieurs opérations apparaissait plusieurs fois,
  chaque carte répétant la même frise. Correctif : **regroupement par SIREN → une carte par promoteur**,
  compteurs (opérations, permis, logements) = somme de SES opérations (même périmètre que la frise), ses
  opérations listées dessous une fois chacune, ses programmes publiés dédoublonnés (par nom+url). Le
  rattachement programme↔opération (par coordonnées SIREN+commune+année) n'est pas touché (pas cassé).
  Recette : « Explorer toutes les opérations » → 154 cartes promoteur, **0 SIREN dupliqué** ; CBO une
  seule carte (capture `O6-veille-regroupe`). Test `VeillePromoteurs.test.tsx` (2 opérations CBO → 1 carte,
  compteurs sommés 41 permis / 123 logements, 2 sous-opérations listées).
- **O4 — « PLU » : compteurs réconciliés + bug IDU — FAIT.** **Bug IDU** reproduit : `/verif-procedure/{idu}`
  faisait `WHERE idu = :i` sur l'IDU BRUT → 404 « Parcelle inconnue » sur un IDU VALIDE saisi en minuscules
  (`97413000cj0096`) ou collé avec un espace/retour en queue. Corrigé : **normalisation** (trim + majuscules,
  doctrine T1) avant le lookup. Recette : minuscule → 200, espace → 200 (étaient 404) ; 24/24 communes OK.
  **Compteurs** : l'annuaire disait « 2 en révision » (statut d'opposabilité GPU = règlement non servi) et
  RATAIT Les Trois-Bassins ; le radar Sudocuh (`veille_plu`, source unique de « Vérif procédure » et de la
  fiche) porte **3 révisions générales prescrites** : Saint-André (22/06/2022), Saint-Leu (17/05/2022),
  **Les Trois-Bassins (02/06/2022)**. Réconcilié : l'endpoint annuaire lit `veille_plu` → `n_procedures` = 3
  (`procedures_par_etat`), chaque commune porte sa `procedure_active` ; le bandeau affiche « 3 procédures en
  cours » (badge « révision générale » sur Trois-Bassins), le statut du RÈGLEMENT (GPU en attente / RNU)
  reste distinct (jamais confondu). **Nombre réel par état** : 3 révisions générales actives · 1 élaboration
  prescrite-dormante (non comptée active) · 7 clôturées · 13 aucune · 1 RNU (Saint-Philippe) ; côté règlement
  GPU : 21 servis, 2 en attente d'opposabilité, 1 RNU. Recette : bandeau « 21 PLU · 3 procédures · 1 RNU »
  (capture `O4-plu-annuaire`). Tests `test_retours12_o4_plu.py` (normalisation IDU · 404 si vraiment inconnu ·
  compteur réconcilié inclut Trois-Bassins).

**Vérifs Lot O bloc 2** : tsc 0 · build OK · suite frontend 169/169 (+EtudierBien/VeillePromoteurs réécrits) ·
backend `test_retours12_o4_plu` 3/3 + `test_retours12_c2_tcsp` 3/3 · recette navigateur chaque outil · golden
intact (0 fichier scoring). Les 7 travaux O1-O7 sont livrés (O2 en commit dédié).
## LOT O bloc 3 — outils (O8-O13)

- **O8 — « Communes » : SRU concordant + audit des 7 indicateurs — FAIT (priorité haute).**
  **Cause racine mesurée** : la fiche commune est servie d'un **cache nocturne** (`commune_contexte_cache`,
  calculé la nuit) qui FIGEAIT les indicateurs partagés avec le tableau des 24 communes, lequel les calcule
  LIVE (`comparateur.raw_rows`) → deux chiffres divergents. **Audit empirique des 7 indicateurs × 24
  communes** (tableau vs fiche), AVANT correction :

  | Indicateur | Moteur tableau | Moteur fiche | Écarts /24 (avant) | Après |
  |---|---|---|---|---|
  | Parcelles à potentiel (stock) | `raw_rows.stock` (p_score_v2 run) | `comparable.stock` (idem) | 0 | 0 |
  | Instruction (vélocité) | `raw_rows.velocite` (m10) | `comparable.delai` (idem) | 0 | 0 |
  | Permis 5 ans | `raw_rows.permis` (SITADEL) | cache figé | **23** | 0 |
  | Déficit SRU | `commune_contexte_sru` (SQL) | cache figé + join NOM | **2** | 0 |
  | €/m² ancien | `raw_rows.prix_ancien` | `comparable` (idem) | 0 | 0 |
  | €/m² neuf | `raw_rows.prix_neuf` (live VEFA) | cache figé | **10** | 0 |
  | €/m² terrain nu | `ligne2_terrain_zone` | idem (fiche Marché) | 0 | 0 |

  **Corrections** (un seul moteur, live) : (1) l'endpoint fiche resert les indicateurs PARTAGÉS
  (`comparable` : permis/neuf/ancien/vélocité/stock + SRU) **live** via `_rafraichir_partages` (les blocs
  lourds restent cachés) → permis & neuf concordent (ex. St-Denis neuf 4 998 des deux côtés, était
  4 998/4 275). (2) **SRU** : le join se faisait par **NOM sensible à la casse** (« La Plaine-**Des**-
  Palmistes » en base SRU vs « …-**des**-… » côté parcels) → la fiche perdait le SRU d'une commune ;
  corrigé (lecture par INSEE + repli nom insensible à la casse). (3) **SRU déficit** servi par le backend
  avec la MÊME arithmétique que le tableau (`greatest(obj−taux,0)` SQL puis `round(float,1)`) — plus de
  recalcul float au front qui donnait 5,4 là où le tableau donne 5,3 (Saint-Louis). (4) **O8.1** : la fiche
  NOMME explicitement « taux de logement social (SRU) » **et** affiche « — déficit N pts » (la grandeur du
  tableau) : fini « 18 % » vs « 6,7 » qui semblaient se contredire. **Audit final : 0 écart sur les 7 × 24.**
  Les « — » restent « — » (aucun zéro inventé). Recette : fiche « taux… — déficit 5,3 pts »
  (capture `O8-fiche-commune-sru`). Tests `test_retours12_o8_sru.py` (déficit même arithmétique · join
  casse-insensible · SRU absent → None).

- **O9 — À FAIRE** · **O10 — À FAIRE** · **O11 — À FAIRE** · **O12 — À FAIRE** · **O13 — À FAIRE**
## LOT J — Projets (commit 5) — À FAIRE
## LOT A — IA + compte-rendu final (commit 6) — À FAIRE
