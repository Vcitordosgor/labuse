# FRONT-CHIFFRES-2 — reclassements « présentation pure »

Familles que FRONT-CHIFFRES-1 avait classées `remonter_back` (prudence) mais qui, à la lecture,
ne DÉCIDENT aucun chiffre / seuil / plafond / conversion / libellé : elles ne font que colorer ou
graduer une valeur DÉJÀ SERVIE. Une couleur ou un cran de jauge n'est pas un chiffre hors registre
(le verrou front FC-1 ne les vise pas). → reclassées `legitime` (règle « présentation pure : rien à
faire, listé comme tel »).

| famille | ligne(s) | ce que fait le front | pourquoi présentation |
|---|---|---|---|
| F11 | risques.tsx:22/24 | niveau d'aléa (catégoriel **servi**) → cran 0..3 de Jauge3 | le code le dit déjà : « présentation, aucun seuil inventé » ; `rédhibitoire` est un flag servi |
| F15 | RadarMarcheColonne.tsx:19/181 | couleur ambre/menthe selon le SIGNE de l'écart servi ; gris si `niveau === 'indicatif'` (**servi**) | couleur d'un signe, gris d'un niveau servi — aucun libellé décidé |
| F17 | Ia.tsx:165 | teinte rouge si `depense_eur >= budget_eur` (deux valeurs **servies**) | comparaison de deux servis → couleur seule (admin) |
| F22 | formes.tsx:99 | couleur des crans de Jauge3 selon le `niveau` (**prop servie**) | couleur d'un cran servi ; le nombre de crans vient de la donnée |

## ~~Arrêté pour décision~~ → REMONTÉ (décision Vic : servir la DA avec le tier)

| famille | ligne(s) | raison |
|---|---|---|
| F13 | ProjetKanban.tsx:37 | mapping `tier` (sortie du **scoring** brûlante/chaude/…) → couleur de pastille |
| F29 | TierBadge.tsx:9 | mapping hex→ton du badge de **verdict tier** (scoring) |

**Résolu (F13/F29 remontés).** Décision Vic : le back sert, à côté du tier, sa couleur (jeton DA)
et son libellé (`/vocabulaire/paliers`, source `scoring/tiers_client`). Pastille et badge lisent la
même carte ; à q_v15 (bandes A/B/C/D) un seul endroit change. La pastille F13 est corrigée au
passage (elle colorait `brulante` en « Priorité » alors que PRIORITE_SERVIE=false le résout en « À
suivre » — cf. CHANGEMENTS.csv).

## Lot P1 (suite) — reclassements présentation
| famille | ligne(s) | pourquoi présentation |
|---|---|---|
| F07 | ContextePanel:27/465/498 | SRU_META mappe le `statut` SERVI (carencée/déficitaire) → couleur+label+lecture ; :465/:498 = couleur selon le SIGNE d'une valeur servie (tendance/écart). Aucun chiffre décidé. |
| F20 | ProprietaireHistorique:25 | `n_millesimes < 2` : il faut AU MOINS deux millésimes pour tracer une frise / un changement — minimum inhérent, pas un seuil métier. `n_millesimes` est servi. |
| F24 | MapView:344 | `> 20 000` = plafond de RENDU (le front ne peut peindre 20k+ features à la parcelle) — contrainte technique d'affichage, pas une donnée que le client lit. *(Servable si Vic veut le rendre réglable.)* |
| F19 | PermitsProximityBlock:42 | `distance_m <= 100` ne décide QU'UNE couleur (violet) d'emphase pour les permis proches — tous les permis sont affichés, la distance est servie & affichée en clair. Aucune donnée ni libellé décidé. |
| F30 | TimeMachine:84 | `periodAn >= 2016` GÈRE la disponibilité d'une surcouche viewer (le cadastre d'époque n'existe qu'à partir de 2017 ; 2016-2020 le recouvre). Fait historique FIXE de couverture de données, pas un chiffre que le client lit — plomberie du comparateur d'orthos. *(Servable si la couverture cadastre devient dynamique.)* |
| F06 | moteurs:346/353/716 (+303) | glyphe de signe (« + », flèche ↑/↓/→) et couleur selon le SIGNE d'une valeur servie (pct, charge cumulée) = présentation ; le compte « N parcelles sans droits à bâtir » (moteurs:303) est une AGRÉGATION UI des items servis par `sdp_m2 > 0` (sens inhérent de la SDP), pour l'action « retirer les vides ». |
| F08 (part) | status.ts:229 + 298-303 | `completudeColor` (couleur selon ≥ 50 %) et `ageSignal` (couleur par bande d'âge + TEMPS RELATIF « il y a N mois » calculé au front, comme `ilYA` de format.ts) = présentation. |
| F16 | FiltreLabuse:820 | note descriptive « Terrain nu = aucune emprise bâtie ≥ 5 % » : le front ne DÉCIDE pas nu/bâti (la partition est une clause SQL back, seuil 5 % fixe et documenté) ; il la DÉCRIT. *(Servable si le seuil devient configurable.)* |
| F01 (reste) | Fiche.tsx:~890/1045/1522/1819/1826/1841 | présentation/inhérent : libellé d'orientation (`orient === 'plat'`, valeur **servie**), position de réglette (`reglette_pct` **servi**), passe-plat `au_ouverture.motif`, phrase de verdict SDP + repli du panneau gouvernés par `reglesSdp > 0` (sens inhérent de la SDP résiduelle), montage de `FaisabiliteTab`. Le **push filtre densifiables** (`setFilter('sdpMin', …)`) est un DÉFAUT de paramètre de requête (éditable, jamais affiché comme valeur/verdict) = contrôle de filtre. F01a/b/e sont remontés. |
| F05 | Licences.tsx:154/350/583 | écran **admin** de gestion des licences (hors surface client) : fenêtres de statut invitation/essai, conversion ms→heures d'un compte à rebours admin, budget IA défaut. Monitoring interne, pas un chiffre lu par le client. |
| F09 | AdminView.tsx:239/284 | écran **admin** (hors surface client) : seuils de supervision ops (backlog Courrier « > 5 j ouvrés » rouge, âge de sauvegarde « > 1 j » rouge). Tableaux de bord internes, pas des verdicts client. |

## Arrêté pour décision (touche le scoring)
| F01 (part) | Fiche.tsx:566 + libellé « signal fort/au-dessus » | `signalEcarte` (`mult_base >= 2`) et le libellé « signal fort » vs « au-dessus de la moyenne » (`mult_base >= 4`) sont des SEUILS SUR LE MULTIPLICATEUR DE SCORING (`score_v2.mult_base`). **TRANCHÉ (Vic) : laissé tel quel, NON servi — HORS PÉRIMÈTRE FC-2** (même réponse que PRIORITE_SERVIE) ; à traiter AVEC la bascule q_v15 (DONNEES-FIX-1 + run 11). |
| F08 (part) | status.ts:33 | `PRIORITE_SERVIE = false` = DRAPEAU DE POLITIQUE du scoring (miroir de `tiers_client.PRIORITE_SERVIE`, égalité garantie par un test anti-dérive). **TRANCHÉ (Vic) : laissé tel quel, NON servi — HORS PÉRIMÈTRE FC-2** (pas un chiffre client ; la bascule q_v15 est déjà conditionnée à DONNEES-FIX-1 + run 11). Sera traité AVEC la bascule. |
| F02 (reste) | constructibilite: 196/198/815/929/947/994 | présentation/inhérent : `coutDepasse` (garde relationnelle input>servi, pas de seuil codé), `negatif` (charge `<= 0` = sens inhérent), `step={50}` (pas d'un champ de saisie), couleur ER `>= 50 %` + PEB `['A','B']` (couleur d'un seuil/classe servie), `capaciteNulle` (`logMax <= 0` inhérent). Seul le VERDICT charge↔marché est remonté (`charge_couvre_marche`). |

## P2 — lot 1 (F33–F50, familles `calcul`)
Tout `calcul` front qui ne fait que **re-exprimer / agréger / formater des valeurs DÉJÀ SERVIES** (somme, différence, ratio, max/min, complément à 100, conversion d'unité, temps relatif, position de jauge, couleur d'un signe) = **présentation** (reclassé légitime). Les écrans **admin** (rendus sous `App.tsx:395` `view==='admin'`, hors surface client) = **admin interne**. Un seul `remonter` dans le lot (**F46**, valeur affichée inchangée).

| famille | fichier | verdict | pourquoi |
|---|---|---|---|
| F33 | fiche/constructibilite.tsx | présentation | `abs`/`max(0,…)`/`sort`/`round`/`fmtEurCompact` de valeurs **servies** ; verdicts (`sens`, `supportable`, `nonConstructible`) déjà servis ; `dispositifsCount` = somme UI de listes servies ; `capaciteNulle`/`negatif` = sens inhérent (`<= 0`). |
| F34 | panel/ContextePanel.tsx | présentation | Map « top acquéreurs » (group-by/count/max/slice de `acquisitions` servies) ; `fmt`/`fmtDec` de champs servis ; `autres = max(0, 100−loc−prop)` (complément inhérent) ; `sdp/1e6` (conversion d'unité) ; gate « sous le seuil » **servie**. |
| F35 | admin/Licences.tsx | admin interne | écran admin (hors surface client) : `fmtDuree` min→h, compte à rebours essai ms→h, `mrr` = filtre de statuts Stripe servis, budget IA défaut. |
| F36 | outils/ModulePanel.tsx | présentation | pastille = état **servi** (`lib/permisEtats`), badge = `etat_libelle` servi, `max(total, loaded)` garde de pagination, coût courrier = `tarif_unitaire_eur × n` (produit de servis). |
| F37 | admin/AdminView.tsx | admin interne | tableau de bord ops (hors surface client) : différences/agrégations de métriques servies (`ca_mois`, `verrous`, `horloge`, âge sauvegarde, `signalements`). |
| F38 | projets/ProjetKanban.tsx | présentation | scoring **servi** ; le front ne fait que `toLocaleString`/sommes/différences de compteurs servis (`analyse.*`). |
| F39 | fiche/Fiche.tsx | présentation | somme des 4 compteurs de cascade servis ; passe-plats (`reglesGabarit`, `au_ouverture.motif`) ; pente bande **servie** (F01b). |
| F40 | sources/SourcesPage.tsx | présentation | comptes/group-by de sources servies ; `dvfMaxAnnee` lit `derniere_donnee` **servie** ; différence `parcelles − parcelles_filtrables` (deux servis). |
| F41 | outils/VeillePromoteurs.tsx | présentation | somme/`min`/group-by de valeurs **servies** par opération (`n_permis`, `nb_logements`, `date_min`) ; aucun chiffre neuf. |
| F42 | panel/ResultsSection.tsx | présentation | `filtreCount`/`bandeSignalCount`/`encartTotal` = sommes sur le **crosstab servi** (unique GROUP BY) ; les bandes A/B/C/D sont du scoring mais les comptes sont servis, le front ne fait que les additionner. |
| F43 | compare/ComparePanel.tsx | présentation | chaque colonne lit un champ **servi** de la ligne compare ; seul formatage + convention `R+${max(0,niv−1)}` + highlight max/min. |
| F44 | admin/Courrier.tsx | admin interne | écran admin : comptes d'items servis (`nMasques`, `nADeposer`). |
| F45 | admin/Produit.tsx | admin interne | écran admin : comptes/somme d'usage par outil (valeurs servies). |
| F46 | fiche/marche.tsx | **remonter** (1 ligne) + présentation | `:129` **« Valeur au prix du secteur »** (`surface × médiane terrain`) = produit calculé au front ALORS que le back le calcule déjà (`score_e` « prix probable ») → **remonté** `dvf_parcelle.valeur_terrain_secteur_eur` (valeur affichée **inchangée**, vérifié). `:103` réglette + `:177` format = présentation. |
| F47 | outils/blocB.tsx | présentation | `max/min` best-of-colonne, largeur de barre ZAN clampée sur valeurs **servies**, horizon **servi** (F31). |
| F48 | radar/RadarEcran.tsx | présentation | `joursDepuis` = temps relatif (comme `ilYA`) ; verdicts `enVenteLongue`/`de_retour` **servis** ; €/m² = ratio de deux servis (`prix`/`surface`) pour affichage. |
| F49 | lib/geo.ts | présentation/inhérent | géométrie carte côté client (haversine, aire shoelace, point-in-polygon, `fmtDistance`/`fmtArea`) sur géométrie servie/dessinée — approximations planes locales pour mesures de zone, pas des nombres du registre (cohérent F19/F24). |
| F50 | outils/Gabarit.tsx | **REMONTER** (révisé au lot 2) + présentation | bbox `fitBounds` = présentation ; `pctPortion` (`surfaceParcelleM2 / cadastre × 100`) était classé présentation au lot 1, MAIS le lot 2 a trouvé que **F57 (`GabaritLine.tsx`) recalcule la MÊME formule** → deux sites divergents. **Remonté** `pctPortionZone` (servi une fois par `gabarit.py`), les deux le lisent. Valeur inchangée. *(cf. § P2 lot 2)* |

## P2 — lot 2 (F51–F68, familles `calcul`)
Même règle qu'au lot 1. Classification confirmée par un **test de divergence explicite** par ligne (inputs = champs servis ? le résultat pourrait-il différer d'un calcul back de la même notion ? tout doute → remonter). **2 remonters** trouvés (F57/F50, F58) — tous deux valeur inchangée, tous deux étaient des formules DUPLIQUÉES (deux sites, ou front↔back).

| famille | fichier | verdict | pourquoi (inputs servis ? divergence ?) |
|---|---|---|---|
| F51 | outils/TaxeAmenagement.tsx | présentation | `zoneA = prefill.zone_famille === 'A'` lit `zone_famille` **servi** (F28) ; la taxe est calculée par le back. Aucun calcul de taxe au front. Pas de divergence. |
| F52 | projets/ParcoursTinder.tsx | présentation | `total`/`decided` = somme de compteurs **servis** (`etat.counts`) pour une barre de progression. Pas de divergence. |
| F53 | radar/RadarMarcheColonne.tsx | présentation | pied de colonne = `seuil_indicatif_n`/`seuil_ecart_n` **servis** ; `EcartInline` lit `cmp.niveau`/`median`/`ecart_pct`/`n` **servis** (RADAR-FIX-3, calculés back). Format/couleur seuls. Pas de divergence. |
| F54 | panel/FiltreLabuse.tsx | présentation | `o.n` facettes **servies** ; `bandeTotalReveal` = somme de comptes de bandes **servis** (« comptes bruts, aucun quota/rang »). Bandes = scoring mais comptes servis, le front somme. Pas de divergence. |
| F55 | admin/Radar.tsx | admin interne | écran admin : temps relatif (jours depuis `iso` servi). Pas de divergence. |
| F56 | admin/circuit/CircuitDiagram.tsx | admin interne | schéma circuit dev/admin : `size` d'un Set de `moteur` **servis**. Pas de divergence. |
| **F57** | **fiche/GabaritLine.tsx** | **REMONTER** (valeur inchangée) | `pctChev = round(surfaceParcelleM2 / cadM2 × 100)` — **MÊME formule qu'à F50 (`Gabarit.tsx`)**, deux sites front. Divergence possible si l'un change. **Remonté** `pctPortionZone` (une fois, `gabarit.py`). |
| **F58** | **fiche/MarcheSecteurBlock.tsx** | **REMONTER** (valeur inchangée) | `partProp = round(100 × men_prop / men)` — la **MÊME formule vit au back** (`solaire.py:328`, pour le scoring). Deux sites de calcul (front↔back) → divergence possible. **Remonté** `part_proprietaires_pct` sur le bloc filosofi_200m. |
| F59 | fiche/ProprietaireHistorique.tsx | présentation | `.filter(!c.non_identifiable).length` : compte des `changements` **servis** par flag **servi** (DONNEES-FIX-1 décide au back). Pas de divergence. |
| F60 | fiche/autour.tsx | présentation | chaînes à partir de `nivvie_moyen_eur`/`taux_pauvrete_pct`/`distance_m` **servis** ; `fmtDist` m→km. Pas de divergence. |
| F61 | fiche/blocks.tsx | présentation | `aCheval = rp.a_cheval ?? …` (**servi**, F21) ; `pct = round(p×100)` formate une part **servie**. Pas de divergence. |
| F62 | fiche/leBien.tsx | présentation | `abs(ecart_egout_bdtopo_m)` **servi** + flags `hauteur_discordante`/`_motif` **servis** (DONNEES-FIX-1) ; `abs` = sens inhérent. Pas de divergence. |
| F63 | fiche/risques.tsx | présentation | `evaluees = vigilances + sansObjet + inconnues` : comptes de `f.lines` **servies** par `result` **servi**. Pas de divergence. |
| F64 | outils/EtudeZone.tsx | présentation | `surface_m2 / 10000` (m²→ha) + `n_parcelles` **servis**. Pas de divergence. |
| F65 | outils/moteurs.tsx | présentation | `.length` de `zan_compatibles` **servi** (conso/budget/pct/depasse servis verbatim autour). Pas de divergence. |
| F66 | projets/ProjetsPanel.tsx | présentation | somme + ratio de compteurs **servis** (`p.counts`) pour un % de progression (comme F52). Pas de divergence. |
| F67 | header/Header.tsx | présentation | plomberie de pagination « Voir plus » sur `items.length` **servi** (le back ne renvoie pas de total ; `+PAGE_SIZE` = artefact de pied, pas un total revendiqué). Pas un chiffre client. |
| F68 | lib/useApplySearch.ts | présentation | somme de 4 buckets de tiers **servis** (`getStats().tiers.*`) = « univers filtré hors écartées » ; sommer exactement ces 4 buckets ne peut pas diverger de leur total (comme F42). Pas de divergence. |
