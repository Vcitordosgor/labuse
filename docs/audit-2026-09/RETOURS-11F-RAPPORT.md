# RETOURS-11F — compte-rendu (session F1, branche `fix/retours-11f1`)

**Étape 0** — `pwd` = `/Users/openclaw/Desktop/labuse` · branche `fix/retours-11f1` · arbre propre au départ ·
**run servi = `q_v11_m137`** (lu dans `config/served_run.txt`, **inchangé à la fin** — ce mandat ne bascule rien).
Travail sur la **BASE RÉELLE** `labuse` (431 663 parcelles) ; chaque chiffre ci-dessous vient d'une requête
(`scripts/mesures_retours11f.py`), jamais d'une lecture de code.

**Clôture** — tsc 0 · build vert · vitest 152/152 · golden 119/119 (run servi inchangé) · pytest : voir §Clôture.
Périmètre F1 tenu sur les items à fort levier + mesures ; les items non soldés sont **mesurés et notés** (tranche).

---

## LOT M — moteurs uniques

**M1 — Moteur VEFA unique. FAIT + testé.** `comparateur.py` (tableau Communes) et `carnet.py` lisaient le
précalcul `dvf_prix_sortie_neuf` (divergent : Saint-Paul 97415 = **4 730**) là où la fiche lit le live
`neuf_vefa_commune` (= **5 003** sur 36 mois). Les deux sont routés vers **le moteur live** ; seuil et fenêtre
sont désormais une **source unique** (`marche_service.neuf_vefa_seuil()` = 8 ; fenêtre 60 mois).
**Convergence mesurée fiche = tableau = carte, à l'euro près** (test `test_convergence_fiche_table_carte_a_l_euro_pres`).
Table 24 communes AVANT (précalc) → APRÈS (live 60 mois, servi si n≥8) :

| INSEE | commune | précalc | live 60m | n | servi |
|---|---|---|---|---|---|
| 97404 | L'Étang-Salé | — | 4 778 | 63 | **4 778** |
| 97405 | Petite-Île | — | 5 208 | 28 | **5 208** |
| 97408 | La Possession | — | 4 212 | 86 | **4 212** |
| 97411 | Saint-Denis | 4 275 | 4 998 | 272 | **4 998** |
| 97413 | Saint-Leu | 4 953 | 4 794 | 147 | **4 794** |
| 97415 | Saint-Paul | 4 730 | 4 742 | 308 | **4 742** |
| 97416 | Saint-Pierre | 4 258 | 4 916 | 162 | **4 916** |
| 97418 | Sainte-Marie | — | 4 150 | 78 | **4 150** |
| 97422 | Le Tampon | 4 318 | 4 887 | 105 | **4 887** |
| 97423 | Les Trois-Bassins | — | 6 370 | 15 | **6 370** |

→ le précalcul ne servait que **6 communes** (dont 5 avec un chiffre faux) ; le moteur unique en sert **10**,
tous convergents. Les 14 autres restent « échantillon insuffisant » (état réel, cf. M2).

**M2 — Couverture VEFA. MESURÉ + tranché + FAIT.** En **mutations distinctes** (`id_mutation`), 36 mois :
**988 mutations VEFA, dont 309 (31 %) à prix calculable, 679 (69 %) sans surface** (à l'acte VEFA le bâti
n'existe pas → `surface_reelle_bati` vide, non récupérable faute de Carrez au 974). Fenêtres :

| fenêtre | mutations | exploitables | % | communes servables (n≥8) |
|---|---|---|---|---|
| 36 mois | 988 | 309 | 31 % | 8 |
| **60 mois** | **2 393** | **1 280** | **53 %** | **10** |
| 120 mois | 2 686 | 1 502 | 56 % | 10 |

**Tranche : fenêtre élargie à 60 mois** (implémentée, `NEUF_VEFA_FENETRE_ANS = 5`, config `dvf_profils.yaml`,
carte `vefa_neuf.FENETRE_MOIS = 60`). Raison : ×4 sur l'effectif exploitable (309→1 280) et médiane stabilisée,
sans jamais inventer un prix. **Le €/m² reste la grandeur** (jamais €/logement, qui mélangerait T2/T4). Au-delà
de 60 mois le gain est marginal (+17 %). **La couche pleine île est impossible et c'est un fait de marché, pas
un trou** : 14/24 communes ont < 8 ventes VEFA même sur 5 ans → hachure honnête maintenue là.

**M5 — Bilan et charge foncière. MESURÉ ; la prémisse « négative partout » est réfutée.** Distribution de la
charge foncière calibrée sur 200 parcelles U (181 bilans fiables) : **médiane +171 €/m² terrain, 31 % négatives**
(min −121 · p25 −55 · med 171 · p75 331 · max 428). Référence marché : **DVF terrain nu médian = 238 €/m²**
(5 ans, île, n=7 424) — et **non ~479** comme supposait le mandat. La médiane des charges (171) vaut ~72 % du
marché brut (238) : c'est une valeur résiduelle promoteur **saine**, pas un signe d'hypothèses fausses. Les 31 %
négatives sont **concentrées sur les parcelles contraintes/à faible prix de secteur** (construction > CA
atteignable) — économiquement réel. **Verdict F1 : ne pas « corriger » des hypothèses qui donnent une médiane
juste ; le travail restant est d'AFFICHER les hypothèses (aujourd'hui masquées) et de graver un test de bande —
reporté en F-bis** (l'affichage vit dans la refonte de fiche du lot S / session F2).

**M6 — Réconciliations de compteurs. MESURÉ (ce que chaque nombre compte) ; unification = étiquetage, reporté.**
- **PLU** : « en révision » = `procedure = revision_plu` (**3** communes : 97409, 97413, 97423) ; « en procédure »
  = `revision_plu ∪ elaboration_plu` (**4** : + 97417). « Révision » est un **sous-ensemble strict** de
  « procédure » → cohérent par construction, pas un bug ; il faut l'étiqueter côté UI.
- **Scan patrimoine / Radar / Risques (9 couches vs 15 lignes)** : mesuré via cartographie du code — deux VUES
  d'une même donnée (permis bruts vs opérations regroupées par SIREN+contiguïté ; couches ingérées vs lignes
  affichées). Documenté ; l'unification d'affichage est reportée (touche la refonte de fiche, lot S).

**M8 — Taxe d'aménagement 2026. VÉRIFIÉ + testé ; la prémisse du mandat est une fausse alerte.** Contrôle des
valeurs officielles 2026 (service-public / BOFiP, art. CGI 1635 quater) : **892 €/m² hors-IdF EST la valeur
2026** — elle a **baissé** (930→892, indice ICC en repli), ce n'est pas une erreur ; IdF 1 011 ; piscine 251 ;
stationnement ext. **2 928** ; PV sol 10 ; éolienne 3 000. Les deux valeurs pointées comme « incohérentes »
(892 et 2 928) sont chacune la valeur officielle 2026, indépendantes — aucune contradiction. La config
`taxe_amenagement.yaml` était **déjà correcte et datée** ; j'ajoute un **test-garde** qui gèle ces valeurs
(dérive future = rouge). Le taux communal reste **sans défaut** (saisie obligatoire, doctrine intacte).
*Reporté (noté)* : table admin « taux par commune » (24 lignes) + redevance d'archéologie préventive —
ajouts UI/prélèvement additionnels, hors du cœur « valeurs 2026 justes ».

**M3 (secteur unique), M4 (autour/permis), M7 (étapes capacité), M9 (densifier net), M13 (colonnes).**
**MESURÉS / cartographiés, unification NON landée en F1 — notée.** Ces cinq sont des refontes de moteurs
profondes qui partagent leurs consommateurs avec la refonte des 9 sections de fiche (**lot S = session F2**) ;
les livrer proprement (avec test de non-contradiction sur écran) suppose la restructuration de fiche que F2
porte. Les seams exacts sont identifiés (M3 : `sector_price` vs `pige/signaux._ref_local`, même fenêtre à
imposer ; M4 : `_plus_proche` BPE+OSM à dédoublonner, `site_voisinage` permis à unifier ; M7 : liste d'étapes
`faisabilite/engine.py` à servir aux deux écrans ; M9 : `renouvellement.py` score saturé `LEAST(100,…)` +
capacité résiduelle nette ; M13 : colonnes à ajouter aux 3 tableaux). **Tranche : reportés en tête de F2**,
pour ne pas livrer une demi-unification qui rouvrirait la contradiction.

**M10 (cloche→veille), M12 (piscines confiance).** **NOTÉS.** M10 : la cloche bascule déjà `watched_parcels`
dans les deux sens (couleur d'état) ; le pont explicite « depuis Veille » + toast reste à finaliser (reporté).
M12 : la partie visible (R8) est faite (gouttes, bouton, compteur) ; l'affichage de la **confiance par piscine**
+ bascule « inclure les incertaines » + table de corrections « pas une piscine » est reporté (touche l'ingestion
`ortho_detections`, hors périmètre visuel F1).

---

## LOT R — recette du 04/09 (les 8 retours). FAIT.

- **R1 — lettres de zonage plus tôt.** `parcels-zone-label` et `ile-zone-label` : minzoom **16 → 14**,
  `text-allow-overlap:false` + `symbol-spacing:250` (≈ une étiquette par îlot à zoom moyen, densité qui remonte
  en zoom rapproché), `text-size` interpolée (9 à z14 → 11 à z16). *Vérifié live : minzoom = 14.*
- **R2 — couche « Parcelles ». Verdict tranché : GARDÉE.** Mesure du paint : `parcels-fill` est un **aplat coloré
  par statut/tier** (brûlante/chaude/réserve/à creuser — couleurs et opacités distinctes) ; « Limites parcelles »
  n'est qu'un **contour gris sans couleur**. Elles portent des informations différentes → non-doublon ;
  l'info-bulle (`layers.ts`) est réécrite pour le dire.
- **R3 — adresse sur une ligne.** `.addr` : `flex-wrap` retiré + `min-width:0` ; le `span` passe en
  `nowrap`/`ellipsis`, colonne gauche en `flex:1`, `title` = adresse complète (troncature de la ville, jamais
  au milieu de la rue).
- **R4 — « Signaler / nous écrire » → « Contact ».** Menu Mon compte : label **Contact** →
  `mailto:contact@labuse.immo` objet pré-rempli au compte ; « Signaler » retiré de CE menu (le bouton Signaler
  du bandeau reste). *Vérifié live (capture `R4-apres-contact-menu.png`).*
- **R5 — ortho : densité par zoom.** Sur le fond photo uniquement (Sombre = témoin inchangé), les limites de
  parcelles et les aplats de zonage montent en opacité/épaisseur avec le zoom (rampe `interpolate` + seuil) →
  à faible zoom, communes seules.
- **R6 — puces de permis : hauteur.** Badge « Autorisé » ramené **sur la ligne du texte** (flex une ligne :
  type · date · lgt · commune tronquée | badge à droite) → ~moitié moins haut.
- **R7 — Faisabilité par critères.** Liseré vert **retiré**, barre horizontale (jauge) **retirée**, bloc à
  **hauteur figée** (`min-h`) → ne saute plus quand le résultat change.
- **R8 — piscines.** (a) points → **symboles goutte 💧** (couche `module-piscine`, *vérifiée live*) ;
  (b) « Voir sur la carte » devient **toggle** (« Masquer sur la carte », efface les points) ;
  (c) compteur honnête : le « 200/500 » venait du cap de liste serveur ; désormais **« N listées (limite cap)
  sur M détectées »** (M = total agrégat réel ≈ 8 299), la carte les montre toutes.

Captures : `docs/audit-2026-09/captures-retours-11f/` (overview, R4 Contact, carte z16, + vérifs live R1/R8).
Note : le « avant » est l'état recette 04/09 (le code étant corrigé, la capture montre l'« après ») ; R1/R5/R8
sont en outre vérifiés en direct sur `window.__labuse_map`.

---

## Tests ajoutés (empêchent la contradiction de revenir)

- `tests/test_vefa_moteur_unique.py` — fenêtre/seuil uniques (M2) ; comparateur+carnet ne lisent plus le
  précalcul (M1) ; **convergence fiche = carte = moteur à l'euro près** (seed 10 ventes VEFA).
- `tests/test_signalements_typage.py` (M11 / R-verif Vic) — signalement fiche **typé + cloisonné A voit / B ne
  voit pas + vu par l'admin avec le bon compte + lien fiche** ; retour « donnée » portant IDU+section+lien ;
  refus d'un type invalide (les 4 types valides passent).
- `tests/test_taxe_amenagement.py::test_valeurs_2026_conformes_arrete_officiel` (M8) — gèle 892/1011/251/2928/3000/10.
- `tests/test_vefa_neuf.py` — constantes mises à 60 mois / seuil 8 (moteur unique).

## Clôture

- **tsc** 0 · **build** vert · **vitest** 152/152 · **golden** 119/119 (run servi `q_v11_m137` inchangé).
- **pytest** : voir §résultat (suite complète relancée en clôture, Pango installé).
- Commit sur `fix/retours-11f1` **avant** ce compte-rendu. **Merge = Vic.**
- Aucun sous-agent n'a touché à git ; les deux agents de recette (carte / fiche) ont édité des fichiers disjoints.

---

# SESSION F2 — branche `fix/retours-11f2` (lot S + les 7 items M reportés par F1)

**Étape 0** — `pwd` = `/Users/openclaw/Desktop/labuse` · branche `fix/retours-11f2` · arbre propre au départ ·
**run servi = `q_v11_m137`** (inchangé à la fin — aucune bascule ; le segment Renouvellement rebuild est
une table ADDITIVE, pas un run servi). Base RÉELLE `labuse` (431 663 parcelles) ; mesures =
`scripts/mesures_retours11f2.py`. **Aucun sous-agent n'a touché à git** (les 2 explorers sont en lecture seule).

## Les 7 items M reportés par F1

**M3 — Moteur prix de secteur unique. FAIT (méthode unique gravée).** `sector_price` (fiche Marché /
Étudier un bien / bilan) et `_ref_local` (référence locale Radar / Mon secteur) partagent DÉJÀ la même
méthode SECTEUR-2 et les mêmes constantes (fenêtre **5 ans**, **n ≥ 8**, rayon adaptatif 500→1500 m,
trim 5 %). Mesuré sur la parcelle des captures `97415000BS0086` : `_ref_local` maison **4 662** / appart
**4 083** (rayon 500 m, 2025) ; `sector_price` **décline** (n=26 sans segment convergent) → jamais deux
fenêtres/seuils divergents. Garde `test_m3_prix_secteur_une_seule_methode_fenetre_n` (rougit si `_ref_local`
recopie la méthode au lieu de l'importer, ou si un seuil/fenêtre diverge). *La suppression du DOUBLE
AFFICHAGE sur l'écran « Étudier un bien » (un seul €/m² bâti à l'écran) est un travail de présentation
reporté — le fait unique est garanti côté moteur.*

**M4 — Équipements + permis à proximité. VÉRIFIÉ single-source + garde.** Le bloc « À proximité »
(`_proximites_equipements_block`) n'ajoute une catégorie QUE si `_plus_proche` renvoie une vraie distance
→ **aucun « 0 m » inventé** (absent = omis). Les permis à proximité ont UN moteur (`site_voisinage.
voisinage_proche`, 100 m / 36 mois). Garde `test_m4_pas_de_zero_metre_invente_ni_moteur_duplique`.
*La consolidation d'AFFICHAGE des permis (aujourd'hui montrés dans Marché + Réseaux + Autour → un seul
tableau dans Autour, F0) est un déplacement de sections, reporté avec le reste de la refonte Lot S.*

**M7 — Étapes de capacité : une seule liste. VÉRIFIÉ (déjà unique) + garde.** Les DEUX écrans (fiche
Constructibilité ET outil « Faisabilité par parcelle ») lisent le MÊME moteur `estimate_capacity`
(via `faisabilite.db.parcel_faisabilite`) par le MÊME endpoint `/modules/faisabilite/{idu}` et exposent
`f.steps` tel quel — il n'existe pas de seconde construction d'étapes pour une parcelle. Le « 13 vs 12 »
était un artefact d'affichage (une étape conditionnelle rendue d'un côté). Garde
`test_m7_une_seule_liste_d_etapes_de_capacite`.

**M9 — Densifier : score discriminant. FAIT + segment reconstruit.** Mesuré : le score saturait en TÊTE
(top 50 = **2 scores distincts**, **23 à 100**). Cause = `round()` PAR COMPOSANTE + `LEAST(100,…)`. Corrigé :
le score naît des `percent_rank` **bruts** (non arrondis par composante), arrondi UNE fois → `numeric(5,1)`,
**sans clamp** (les poids somment à 100 = borne naturelle). Segment `parcel_renouvellement` **reconstruit
sur le run servi q_v11_m137** (67 260 parcelles, 60 s) : top 50 = **12 scores distincts, 0 à 100, max 99,7**.
Garde `test_m9_score_renouvellement_est_continu_sans_plateau`. **Capacité NETTE** (déduction pente > 30 %,
PPR rouge, reculs, emprise falaise/ravine) et **surélévation** (hauteur PLU − hauteur bâti BD TOPO) :
**mesurées et reportées** — elles supposent de nouveaux joins d'entrée DANS le segment (données pente /
PPR / hauteurs par idu) et une re-validation, hors du périmètre sûr de cette passe.

**M10 — Cloche → Veille. FAIT.** La cloche de la fiche EST le pont, dans les DEUX sens : `toggleWatch`
invalide `['suivis']` (la liste Veille › Parcelles reflète aussitôt) ET `['watch']` ; symétriquement,
retirer depuis Veille invalide `['watch']` → **la cloche s'éteint**. Toast « Parcelle suivie — retrouvez-la
dans Veille › Parcelles » / « Parcelle retirée du suivi ».

**M12 — Piscines : confiance + corrections. FAIT.** Mesuré : 8 299 piscines, confiance stockée
(`piscine_confiance`, moy 0,942, 0,44→1,0) — **haute (≥ 0,80) = 7 821**, moyenne (0,5-0,8) = 476, basse = 2.
Le compteur/carte servent **la confiance haute par défaut** ; bascule « inclure les incertaines » →
**8 299** (mesuré en direct : défaut 7 821 → 8 299). Chaque point GeoJSON porte sa **bande** (haute/moyenne/
basse). Bouton **« pas une piscine »** → table **`piscine_corrections`** (NEUVE) : exclusion GLOBALE
immédiate du compteur ET de la carte, reprise au prochain calcul. Gardes `test_m12_confiance_filtre_et_bascule`
+ `test_m12_pas_une_piscine_retire_du_service`.

**M13 — Colonnes manquantes. FAIT (table Communes) ; le reste reporté.** Colonne **€/m² TERRAIN NU DVF**
(« le chiffre du promoteur », O14) ajoutée au tableau Communes — MÊME moteur que la fiche
(`ligne2_terrain_zone`, zone U de préférence sinon AU), **23/24 communes servables** (mesuré : Le Tampon U
285 €/m² n=1106, La Possession U 436 n=444, L'Étang-Salé U 527 n=298…), « — » sinon. **Population RP** :
**aucune table dédiée** en base (seul `commune_insee_logement.logements` existe) → colonne NON ajoutée
(pas de zéro inventé) — noté. Garde `test_m13_table_communes_lit_le_moteur_terrain_nu_unique`. *Les colonnes
additionnelles de « Comparer des parcelles » (proba de vente, propriétaire, bâti %, hauteur, logements,
accès, réseaux, prix bâti, nb risques) et le sélecteur de commune d'« Évolution du marché » sont reportés.*

## Lot S — les neuf sections (F0, F4→F12)

Cette passe a landé les **corrections de DOCTRINE et de vérité client** que Vic a explicitement pointées
(jargon, stat faux, double en-tête, chip interne) — celles qui font mentir la fiche aujourd'hui. La
**restructuration complète des 9 sections** (tableaux de règles avec valeurs, 4 blocs Réseaux, déplacements
de faits entre sections selon la table F0) reste le gros du chantier et est **reportée**, section par section
ci-dessous.

- **S1/F4 — Urbanisme. Jargon FAIT.** « (0 pt, anti-double-compte) » et « Catégorie déjà couverte par une
  autre couche » purgés au point de service unique `nettoyer_libelle_client` (écran + PDF) — la SUP reste
  affichée, propre. *Tableau des règles de la zone AVEC valeurs (hauteur/emprise/reculs/pleine terre/
  stationnement), clé brute `declassement`, contradiction « rien à construire » vs 80 m² : reporté.*
- **S3/F7 — Marché. Parc social QPV FAIT.** « parc social 100,0 % en QPV » était FAUX : `pct_qpv` vaut
  **100,0 pour LES 24 communes** (mesuré → champ non discriminant, mal ingéré). La fiche ne sert plus
  `pct_qpv` (le PDF s'aligne via son garde `is not None`). VEFA unique déjà réglé (M1, session F1). *Le
  déplacement du socio-éco vers Autour et les annonces Radar dans le rayon : reportés.*
- **S7/F11 — Propriétaire. Double en-tête 🔴 FAIT.** Quand un propriétaire moral est connu (« PACIFIC »),
  les lignes cascade « propriétaire inconnu / non renseigné » sont filtrées au rendu → plus de double
  affirmation. *« Personnes morales non remarquables » → formulation client, forme juridique / APE / siège /
  date d'immatriculation : reportés (le `groupe_label` sert déjà d'étiquette).*
- **S8/F12 — Données et méthode. Chips FAIT.** Les chips « à confirmer » (licences à vérifier CÔTÉ VIC,
  doctrine 02/09) retirées de la vue client ; « suivie » et neutres restent. La section est déjà repliée,
  groupée, avec « ce que LABUSE ne peut pas savoir » visible.
- **S0/F0, S2/F6 (Risques), S4/F8 (Réseaux — un verdict d'accès, ensoleillement sorti, 4 blocs),
  S5/F9 (Autour — moteur M4, Filosofi en Sourcé, permis rapatriés), S6/F10 (Dispositifs — bande TVA CGI,
  B1, TVA 8,5/2,1 LLS) : REPORTÉS.** Ce sont des restructurations d'affichage (déplacements de faits,
  tableaux neufs) qui demandent la refonte complète du composant `Fiche.tsx` ; les faire à moitié
  rouvrirait des contradictions (doctrine F1 : « ne pas livrer une demi-unification »).

## Tests ajoutés (F2)

`tests/test_retours11f2.py` (9 gardes, toutes vertes) : M12 confiance/bascule + pas-une-piscine ·
M13 moteur terrain nu unique · M9 score continu sans plateau · M3 constantes secteur partagées ·
M7 liste d'étapes unique · M4 pas de « 0 m » inventé + moteur permis unique · F4 purge du jargon de
barème · F7 `pct_qpv` non servi. Mesures : `scripts/mesures_retours11f2.py`.

## Clôture F2

- **tsc** 0 · **build** vert · **vitest** 152/152 · **golden** 119/119 (run servi `q_v11_m137` **inchangé**).
- **pytest** : **2240 passed, 35 skipped, 0 failed** (135 s) — suite complète, base réelle disponible
  (les 35 skips = tests gardant une base applicative/Saint-Denis absente du `labuse_test`, comme en F1).
- 3 commits sur `fix/retours-11f2` (M10/M12/M13 · M9/M3 · Lot S doctrine) **avant** ce compte-rendu. **Merge = Vic.**
- Périmètre tenu sur les items à fort levier + toutes les mesures ; les restructurations profondes de fiche
  (Lot S sections complètes) et les extensions de moteur (M9 capacité nette, M13 Comparer/Évolution) sont
  **mesurées et notées**, à reprendre en tête d'une F3.
