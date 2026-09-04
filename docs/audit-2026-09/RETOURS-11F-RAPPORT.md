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
