# RECETTE-PROD-1 — retours de Vic sur la prod (27/10/2026 soir)

Branche `fix/recette-prod-1` (depuis `origin/main` `a582f8f4`) · worktree `~/Desktop/labuse-recette-prod` · API **8850** / front **6050** · prod `https://app.labuse.immo` lecture seule (compte de test) · **pas de merge, pas de déploiement**.

Règle : chirurgical, DA existante, formats français, aucun texte tronqué, écran ET PDF rendus séparés. Preuve = capture LIVE avant/après (PDF régénéré+ouvert pour les documents), dans `reports/RECETTE-PROD-1/` (gitignoré).

Témoin fiche parcelle : **97410000AE1369** (4 ter Chemin Rebua, Saint-Benoît, Ub, 954 m²). Témoins documents : **97415000BY0083**, **97411000BZ1065**.

> Un précédent tour RECETTE-PROD-1 (06/10, points #1–#15) a été mergé dans `main` — son rapport est archivé en `reports/RECETTE-PROD-1-2026-10-06.md`. Le présent tour (Lots A–F, 27/10) repart de `main` à jour.

## Environnement vérifié
- API worktree sur **:8850**, served_run **q_v20** (= prod), DB locale `labuse` (434 582 parcelles).
- Front dev **:6050** (`/socle/`), proxy → :8850.
- Captures : Playwright (Chrome `channel:'chrome'`) via omnibox `[data-omnibox]` → `onEnterRaw` → fiche ; harnais `frontend/qa-rp1/`.

## Synthèse (au fil de l'eau)

| Lot | État |
|-----|------|
| A — fiche parcelle (AE1369) | ✅ fait (A1 ×6, A2, A3, A4, A5 vérifié, A7, A8) |
| B — documents | ⏳ |
| C — vitesse | ⏳ |
| D — accueil/carte/Sources/Projets/Copilote | ✅ fait (D1,D2,D3 diag,D4,D5,D6,D7) |
| B — documents (Bilan/Gabarit/Étude) | ✅ fait (B1 recompute 0 écart, B2 lien Fiche retiré) |
| C — vitesse | ◐ partiel (C5 ok, C1 local, C2/C3 non repro local, prod 401 sans compte) |
| F — fiche commune (Saint-Paul) | ✅ fait (13 points : 10 corrigés, 1 vérifié OK, 2 backend signalés) |

## Lot A — fiche parcelle (témoin 97410000AE1369, Ub Saint-Benoît, 954 m²)

Vérité du JSON servi : BD TOPO voit **0 bâtiment** (emprise 0, nb 0 → « terrain nu ») alors que RNB (1 « constructed »), CoSIA (267 m²) et OCS GE (100 % artif.) disent bâti → **lecture unique du bâti** introduite (`bati = nb>0 || emprise>0`, = `leBien.tsx:58`) et câblée partout.

| # (A1) | Contradiction | Cause | Correction | Preuve |
|---|---|---|---|---|
| 1 | « bâti présent » (sous-titre Bâti) vs « terrain nu » (badge+détail) | sous-titre reposait sur `nb_batiments` seul, repli littéral `'bâti présent'` | `Fiche.tsx` — sous-titre + badge Bâti lisent la **lecture unique `bati`** → « terrain nu » partout | `A_before_bati.png` → `A_after_bati.png` |
| 2 | « SDP consommée 25 % » + « SDP restante 777 m² — bâti conservé » sur terrain nu | 3 libellés SDP (`'bâti conservé'`) + la ligne « SDP consommée » + le bloc « Potentiel de transformation » (× bâti BD TOPO) tous indépendants du bâti | `Fiche.tsx` — tuile/ChiffreDissous/Verdict : `bati ? 'bâti conservé' : 'terrain libre'` ; « SDP consommée » et `TransformationBlock` **masqués** si `!bati` | `A_after_tiles.png` (SDP restante → « terrain libre »), `A_after_potentiel.png` |
| 3 | « règlement des zones agricoles et naturelles non indexé… » en **Ub**, **deux fois** | note rendue par zone (`blocks.tsx:188`) **et** en commun (`:206`) → doublé ; aucune garde de famille | `blocks.tsx` — note gardée sur famille **A/N** (ne s'affiche plus en U) + rendu commun dédoublé retiré | `A_before_urbanisme.png` → `A_after_urbanisme.png` |
| 4 | « BD CARTO : sol classé naturel — artificialisation à justifier » sur parcelle 100 % artif. (OCS GE) / 83 % imperm. (CoSIA) | ligne `ocs_ge` (grain grossier) rendue sans condition en « Situation » | `Fiche.tsx` — ligne `ocs_ge` **retirée** dès qu'une mesure fine (OCS GE part_artif ou CoSIA imperm.) existe | `A_after_urbanisme.png` |
| 5 | ligne brute « declassement · fort · accès non identifié… » | clé `declassement` absente de `LAYER_LABEL` → snake_case affiché tel quel | `layers.ts` — libellé humain **« Desserte et accès (BD TOPO — à vérifier) »** | `A_after_urbanisme.png` |
| 6 | en-tête + tuile « assainissement non renseigné » vs détail « CISE Réunion (SAUR) · DSP confirmé » | en-tête/tuile lisent `anc` (INSEE secteur, ton neutre) ; le détail lit `gestionnaires` | `reseaux.tsx` — en-tête et case assainissement affichés **seulement si verdict réel** (ton ≠ neutre) ; détail inchangé | `A_before_reseaux.png` → `A_after_reseaux.png` (en-tête → « — ») |
| 7 (A7) | « Gabarit — Calcul incomplet — PLU non calibré pour la zone Ub » | **bug de lecture backend** : Ub EST calibrée (emprise CES 80 %, reculs valides) ; seule la hauteur est une **table graphique par secteur** (Art. U-4, 4/7/10/13/15 m, `statut propose`). `zonage.py` jetait les règles calibrées en générique dès que la hauteur n'était pas une valeur unique | `zonage.py` — zone à enveloppe calibrée sans hauteur unique : **garde ses règles** (`calibree=True`), hauteur de repli marquée `hauteur_estimee` ; `builder.py` — hauteur présentée **estimée / non intégrée** (jamais comme la valeur validée) ; front `GabaritLine.tsx`/`Fiche.tsx` — « Non chiffrée (table graphique) ». Gabarit **status=ok**, emprise 763 m² intégrée. 156 tests gabarit/faisabilité/zonage/calibrage **verts** | endpoint `/outils/gabarit/97410000AE1369` status ok ; `A_after_potentiel.png` |
| 8 (A8) | « Prix de sortie retenu » affiché **lettre par lettre en colonne** | sous-titre long (`ps.label` ~77 car.) gonflait la colonne valeur (grille `auto`) → le libellé s'écrasait à 0 (`overflow-wrap:anywhere`) | `Fiche.tsx` — sous-titre court (`≤ 28 car.`), le détail long reste dans le « i » | `A_before_potentiel.png` → `A_after_potentiel.png` |

**A2 — polices (charte).** Les valeurs des 6 tuiles d'en-tête héritaient Inter (sans) alors que les mêmes nombres sont en mono (`--mono`, tabular-nums) dans les lignes de détail. `index.css` `.fiche-v6 .stat-v` → **`font-family:var(--mono); font-variant-numeric:tabular-nums`** : valeurs chiffrées et unités dans la même police numérique, cohérentes avec le détail. Preuve `A_after_tiles.png`.

**A4 — petit espace en haut.** Le conteneur de la fiche n'avait pas de `padding-top` (carte d'en-tête collée au bord). `Fiche.tsx` `pt-2` + `index.css` `.tete-collee top:8px` : un liseré de fond `--bg-0` au-dessus de la carte, la carte se recolle à 8 px au défilement (le fond opaque couvre toujours le défilement). Preuve `A_after_tiles.png`.

**A3 — boutons d'outils (gardé/retiré).** Règle Vic : un bouton vers un **outil d'information** n'est gardé que s'il apporte une info **absente** de sa section.

| Bouton | Section | Ce que l'outil ajoute | Décision |
|---|---|---|---|
| **Pièges & risques** | Risques | relit les **mêmes couches** que la section (aléas, PPR, bruit, pente, SUP) | **RETIRÉ** (exemple de Vic) |
| Annuaire PLU | Urbanisme | recherche plein-texte du règlement + téléchargement pack GPU | gardé (absent de la fiche) |
| Vérif procédure | Urbanisme | procédures PLU en cours (Sudocuh) | gardé |
| Simuler ouverture AU | Urbanisme (si AU) | simulation AU→U | gardé |
| Calculer la taxe d'aménagement | Fiscalité | recalcul interactif (hypothèses éditables) | gardé |
| Étude de faisabilité | Potentiel | étude d'implantation (plan masse, scénarios) | gardé |
| Densifier l'existant | Potentiel | raccourci de **filtres carte** (action, pas un outil d'info) | gardé (hors règle : action) |
| Calculette foncière | Potentiel | bilan/marge interactif | gardé |
| Assemblage | Potentiel | agrégation multi-parcelles | gardé |
| Scan patrimoine | Propriétaire | portefeuille complet du propriétaire | gardé |
| Courrier SPF | Propriétaire | génération de courrier (action) | gardé |
| Outil Communes | Marché | comparateur/vélocité/rareté | gardé |
| Étude de zone | Quartier | chalandise (isochrones) | gardé |
| Permis commune | Quartier | radar permis **commune** (section = proximité) | gardé (chevauchement partiel — à surveiller) |
| Fiche commune | Quartier | fiche commune complète | gardé |
| Remonter le temps | Exports | imagerie ancienne | gardé |

**A5 — 5 icônes de l'en-tête.** Vérifiées (`liensExternes.ts` + test `liensExternes.test.ts`, 10 assertions vertes). Les 5 icônes = **Cadastre, Pages Jaunes, Google Maps, Géorisques (Errial), Google Earth** (il n'y a pas d'icône « Géoportail » distincte : l'icône Cadastre EST le lien geoportail.gouv.fr ; la 5ᵉ est Google Earth/KMZ).

| Icône | URL sur la parcelle | Correct ? |
|---|---|---|
| Cadastre | `geoportail.gouv.fr/carte?c={lon},{lat}&z=19` + couche parcellaire | ✅ centroïde, zoom 19 |
| Pages Jaunes | `pagesjaunes.fr/...?ou={adresse}` (repli commune, flag `commune_seule`) | ✅ (site = adresse) |
| Google Maps | `google.com/maps/search/?api=1&query={lat},{lon}` | ✅ (ordre lat,lon correct) |
| Géorisques (Errial) | `errial.georisques.gouv.fr/#/?adresse={adresse}` | ✅ (Errial = adresse only) |
| Google Earth | `/parcels/{idu}.kmz` (géométrie servie) | ✅ exact à la parcelle |

Aucune n'est générique/fausse ; les deux liens « adresse » (PJ, Errial) le sont par contrainte des sites cibles (documenté en code). **Aucune modification** (A5 = vérification).

**Validation Lot A** : `tsc` 0 erreur ; vitest fiche **30/30** ; pytest gabarit/faisabilité/zonage/calibrage **156 passed** ; 0 erreur console sur AE1369 (avant/après). Fichiers : `Fiche.tsx`, `reseaux.tsx`, `blocks.tsx`, `risques.tsx`, `layers.ts`, `GabaritLine.tsx`, `styles/index.css` (front) ; `faisabilite/zonage.py`, `gabarit/builder.py` (back).

## A7 — complément (étiquette « Estimé » + dénombrement)

**Étiquette « Estimé » à l'écran ET dans les PDF.** La hauteur issue d'une table graphique par secteur est désormais **servie comme valeur** (volume 3D calculé) et **étiquetée « Estimé »** partout — plus de « Non chiffrée ». `MaxHeight.estimee` + `GabaritResult.hauteurEstimee` (contract) ; `builder.py` (règle appliquée « Hauteur réglementaire — à l'égout (Estimé) », status integrated) ; écran `GabaritLine.tsx` + `Fiche.tsx` en-tête Urbanisme → « 9 m à l'égout · Estimé » (ton ambre) ; PDF `robinet_fiche.py` → « 9 m à l'égout · Estimé (table graphique par secteur) ». L'Étude ne surface PAS cette hauteur (ses règles lisent la feuille PLU brute `statut: propose` → non validée, pas de valeur affichée), donc rien à étiqueter là. Preuve : `A7_gabarit_AE1369_estime.pdf` (PDF, emprise 763 m² + « Hauteur 9 m à l'égout · Estimé ») + écran « 9 m à l'égout · Estimé ».

**Dénombrement — parcelles dont le gabarit change : 10 zones, 14 905 parcelles.** (classification par `resolve_zone().hauteur_estimee`, comptage sur `parcel_zone_plu`.)

| Commune | Parcelles | Zones |
|---|---|---|
| Saint-Benoît | 14 346 | Ub (10 245), Ua (3 777), Ue (303), Up (19), Ut (2) |
| La Possession | 511 | AUBm (243), UAv (172), AUAv (96) |
| Saint-Denis | 48 | Uma (37), Udo (11) |
| **Total** | **14 905** | **10 zones** |

Pour toutes ces parcelles, le gabarit cesse d'afficher le **faux « PLU non calibré »** ; là où la géométrie le permet (reculs/limites qualifiés), il **calcule l'emprise réelle (CES) + hauteur estimée** ; les parcelles à autre blocage (recul non réglementé, limites non cadastrées — fréquent à La Réunion : ravines/littoral, multi-zone) ne gagnent que la disparition du message faux.

**5 exemples avant/après** (AVANT = `status incomplete`, « PLU non calibré (estimation générique) », aucune emprise ni hauteur ; APRÈS = `status ok`) :

| Parcelle | Zone | Zone d'implantation (libéré) | Emprise (CES) | Hauteur | SDP indicative* |
|---|---|---|---|---|---|
| 97410000AE1369 | St-Benoît Ub | 954 m² | **763 m²** (80 %) | **9 m · Estimé** | ~2 290 m² |
| 97410000AE0810 | St-Benoît Ub | 661 m² (impl. 376) | **529 m²** | **9 m · Estimé** | ~1 586 m² |
| 97410000AL0481 | St-Benoît Ua | 137 m² (impl. 90) | **110 m²** | **9 m · Estimé** | ~329 m² |
| 97411000AO0776 | St-Denis Udo | — | **23 726 m²** | **9 m · Estimé** | — |
| 97411000AO0755 | St-Denis Udo | — | **24 975 m²** | **9 m · Estimé** | — |

\* SDP indicative = emprise × ⌊hauteur/3⌋ (niveaux), repère — le gabarit sert l'enveloppe, pas une SDP ; AVANT ces 5 lignes valaient toutes « — / PLU non calibré ».

**Validation A7 complément** : pytest gabarit/faisabilité/zone **124 passed** · tsc 0 · vitest fiche 30/30.

## Lot D — accueil / carte / Sources / Projets / Copilote

| # | Point | Cause | Correction | Preuve |
|---|---|---|---|---|
| D1 | Animation d'ouverture plus visible en prod | verrou `sessionStorage['labuse.intro']` : jouée **une fois par onglet** ; un **rechargement** ne la rejoue pas (sessionStorage survit au reload du même onglet) → Vic, qui recharge la prod, ne la revoit jamais. Le commentaire du code visait pourtant « au rechargement d'une page, pas à chaque navigation » | `LogoIntro.tsx` — drapeau **en mémoire du module** (plus de sessionStorage) : **RÈGLE** = joue à chaque **chargement complet** (ouverture/rechargement/nouvel onglet), jamais sur une navigation SPA interne | code + règle écrite |
| D2 | Panneau « Cartes » vide = zone noire | l'encart d'accueil (`AccueilPreuves`) ne s'affichait que tant que `!accueilVu` ; ouvrir Couches/Filtres posait `accueilVu` **définitivement** → au repli (panneau vide, `panneauSection='listing'`), plus rien | `LeftPanel.tsx` (`VerdictHero`) — l'encart réapparaît quand le panneau est **vide** (`!verdict && panneauSection==='listing'`), et se cache dès qu'on ouvre Couches/Filtres | `D2_empty_panel_after.png` ; test live : welcome `false` (Couches ouvert) → `true` (replié) |
| D3 | Bleu autour de l'île | **DIAGNOSTIC seul** : `MapView.tsx:303` `MER_ORTHO='#0A3B59'`, peint comme couleur de fond du calque `bg` sous fond Ortho (`:315`). Pas de l'imagerie : le proxy ortho ne sert la photo que sur terre + bande côtière ~700 m, la mer = un aplat de couleur unique. Introduit par commit **`a2b59ce85`** (« RETOURS-16 — la mer partout, un seul bleu, sans marches ») | **aucune modification** (Vic décide) | — |
| D4 | « Les Avirons / L'Étang-Salé / La Plaine-des-Palmistes » au menu vs carte sans article | le menu « Toute l'île » (`Header.tsx:304`) affichait `c.commune` brut ; la carte passe par `communePastille` (article gardé seulement pour Le Port/Le Tampon/La Possession) | `Header.tsx` — menu via **`communePastille(c.commune)`** (clé de sélection = `c.commune` brut) | `D4_communes_menu_after.png` : « Avirons · Étang-Salé · Plaine-des-Palmistes » ; « La Possession · Le Tampon · Le Port » gardés |
| D5 | Sources : pastilles + phrase sentinelle + explications par source | `SourcesPage.tsx` : badges « En direct »/proxy ; phrase « La plupart de nos sources… une sentinelle… » ; phrases cadence/couverture sous chaque source | `SourcesPage.tsx` — **toutes les pastilles retirées** (composant Badge supprimé), **phrase sentinelle retirée**, **aucune phrase par source** : titre seul + producteur à droite | `D5_sources_after.png` : « Annuaire de l'administration… · DILA … · ↗ » ; 0 pastille |
| D6 | Projets : « Chaque projet garde votre cadrage et vos parcelles retenues. » | `ProjetsPanel.tsx:209` | `<p>` retiré | `D6_projets_after.png` ; test live : phrase `false` |
| D7 | Copilote exemples : 3 colonnes, 9 cartes, icône en haut, texte tronqué | `AccueilCopilote.tsx` grille 3×3, carte `flex-col`, `line-clamp-3` | **2 rangées de 5** (10 exemples = 9 + « Calcule la taxe d'aménagement de 97415000BY0083 ») ; grille `grid-cols-5 auto-rows-fr`, carte `flex-row` (**icône à gauche, texte à droite**), `h-full min-h` (hauteurs égales), **plus de `line-clamp`** (aucun texte tronqué) | `D7_copilote_after.png` : 10 cartes, icône gauche/texte droite |

**Validation Lot D** : `tsc` 0 erreur ; vitest (sources/copilote/header/panel/projets) **20/20** ; 0 erreur console. Fichiers : `LogoIntro.tsx`, `panel/LeftPanel.tsx`, `header/Header.tsx`, `sources/SourcesPage.tsx`, `projets/ProjetsPanel.tsx`, `copilote/AccueilCopilote.tsx` (+ réutilise `lib/communes.ts`).

## Lot F — fiche commune (témoin Saint-Paul)

Fiche = `components/contexte/ContextePanel.tsx` ; contexte = `app.py commune_contexte` / `fiche_commune.py` (servi depuis `commune_contexte_cache`, précalculé).

| # | Point | Cause | Correction | Preuve |
|---|---|---|---|---|
| Icônes | « I » / « P » au lieu d'icônes | Identité/Population passaient la **lettre** au lieu d'un glyphe (les autres sections passent ◉ ▤ ◫ § ₣ ⚠) | `ic="I"→"◈"`, `ic="P"→"⌂"` | `F_Saint-Paul_after_top.png` |
| Polices | grands chiffres (51 359, 108 088, 4 278 €/m², Foncier) en `font-display` (Space Grotesk) ≠ reste | la charte (règle A2) veut les valeurs chiffrées en **`--mono` + tabular-nums** | `ContextePanel` — `font-display`→`font-mono` sur les tuiles/valeurs numériques (titres laissés en display) | idem |
| Surface | « 22 927 ha » (en-tête) vs « 23 080 ha » (Zones PLU) | deux grandeurs légitimes, même unité, non nommées : **cadastre** vs **emprise du zonage** | badge « **ha zonés** » + « (emprise du zonage) » → nommées distinctement | capture |
| Permis | PC+PA+DP+PD = 327 vs « 329 » | « 329 » = permis **déposés** (inclut 2 annulés) ; le libellé disait « autorisés » | libellé « Permis **déposés** (12 mois) » (327 autorisés par type + 2 annulés déjà affichés) → l'arithmétique ferme | capture |
| Permis dormants | « 2 583 » suspect | servi = `point_mort` = **2 589** (PC sans DAACT > 36 mois, parcelle non bâtie, run servi) ; « 2 583 » = relevé périmé | rien à corriger (le code sert déjà 2 589) ; définition écrite au rapport | — |
| Foncier couleur | « Horizon 4,2 ans » en **vert** alors que le signal ZAN est orange | la ligne était `strong` → `text-mint` **toujours vert** | `RowT` reçoit un `ton` ; horizon coloré selon le **même seuil que le signal** (< 5 ans → orange, ≤ 0 → rouge) | capture |
| Foncier unité | « SDP résiduelle 1 421 ha » | servi en m² (14 214 432) → /10 000 = 1 421 **ha** : conversion correcte, cohérente avec le reste de la carte | **rien à corriger** (vérifié) | — |
| Risques arrondi | section « 34,5 % » vs signal « 34 % » (même source) | le signal faisait `round()` entier | back `app.py` — signal en **1 décimale** → « PPR sur 34,5 % » (vérifié : `_signaux_commune` → « 34,5 % ») | appel direct |
| Risques libellé | « Mouvement de terrain 90,2 % » (de quoi ?) | pas de complément | « 90,2 % **des parcelles** » | capture |
| Risques CatNat | « Chocs Mécaniques liés à l'action des Vagues » (casse brute GASPAR) | `type_peril` rendu verbatim | `sentenceCase()` → « Chocs mécaniques liés à l'action des vagues » (affichage seul, base intacte) | capture |
| Urbanisme date brute | « prescrite le — » | `fmtDateNum("16/12/2021")` → `new Date` invalide → « — » (la date était déjà au format FR) | rendu **verbatim** de la date servie ; absence → « date de prescription non publiée » | capture |
| Urbanisme date ISO | « millésime … opposable ( 2025-12-17) » | littéral malformé dans `config/veille_plu.yaml` (7 communes), espace parasite + ISO | **YAML corrigé** (7 → « (17/12/2025) ») **+** normaliseur front `normDatesFr` (affichage FR immédiat malgré le cache) | capture |
| Fiscalité classe | « Classe de la commune : zone A » | la fiche parcelle ne sert PAS la classe ABC (grep 0) ; « zone A » prête à confusion avec le zonage PLU A/N | « **Classe ABC (zonage A/B/C) : A** » (valeur brute DHUP, sans « zone ») | capture |
| Population RPLS/SRU | 7 265 (RPLS) vs 7 499 (SRU) | deux comptages, deux dates/périmètres | déjà **expliqué** par la ligne SRU (« stock au dernier inventaire SRU · millésime ») — **suffisant** | — |
| Identité vacance | « vacance 0 → 100 % » par IRIS | min/max bruts (IRIS minuscules) présentés comme LA lecture | front : **médiane en premier** + « étendue 0–100 % selon l'IRIS, petits IRIS inclus » (filtrage par taille d'IRIS = back, signalé) | capture |
| Équipements | section = seul renvoi (vide) | aucune donnée équipement/desserte servie à la commune (BPE/transport/fibre seulement « autour d'un point ») | **section retirée** (tuile « Étude de zone » déjà en tête) — pas de section vide | capture |

**Signalé à Vic (backend, non appliqué ici)** : (1) **Date de dernière collecte Radar** dans la section Activité — `marche_annonces` ne sert aucune date ; à ajouter (`derniere_collecte = max(pige_annonces.date_saisie)`) au bloc backend puis l'afficher (nécessite recompute du cache commune). (2) **Unification comptage/seuil Activité vs Radar** (`SEUIL_N=5` d'affichage ≠ `SEUIL_REF_TYPE=30` de robustesse) = réglage des seuils dans `pige/signaux.py`/`marche.py`, hors périmètre fiche ; les « 21 / 24 » de Vic étaient des captures périmées (données actuelles 13 actives / 42 bâti, l'état « sous le seuil » ne s'affiche plus).

**Validation Lot F** : `tsc` 0 ; vitest **299/299** (suite complète) ; pytest commune/contexte/signaux/fiche **171 passed / 13 skipped** (skips = données absentes de la base de test). Fichiers : `contexte/ContextePanel.tsx`, `config/veille_plu.yaml`, `api/app.py` (signal PPR).

## Lot C — vitesse (mesures + 3D LiDAR)

| # | Point | État |
|---|---|---|
| C1 | Mesures | **Local** (API :8850, cache chaud) : fiche parcelle **6–10 ms**, contexte commune **20–145 ms** (servi depuis `commune_contexte_cache`), 3D bâtiments bbox < 300 ms. **Prod** : non mesurable cette session (contexte commune = **401** sans compte de test ; readyz prod = 200). |
| C2 | Clic commune lent / « ne fait rien » | Non reproductible en local (contexte 200, rapide). Cause probable en prod = **cache froid recalculé** (1ʳᵉ ouverture) ou concurrence (motif BOOT-VERROU déjà corrigé #11). Correctif UX (état de chargement immédiat au clic) **à faire avec Lot C/ContextePanel** — voir note. |
| C3 | Fiche commune ne s'ouvre pas | **Non reproductible en local** : les 24 contextes répondent 200 et la fiche s'ouvre (test live). Le 500 prod du tour précédent (#11, DDL sous verrou) est corrigé dans `main` (déployé). Probable perception de C2 (lenteur). Non accédable en prod (401). |
| C4 | Accélérations sûres | Aucune accélération risquée appliquée. Le contexte est déjà précalculé (cache) ; la fiche parcelle est rapide. Pas d'index/cache évident à ajouter sans mesurer la prod. **Rien changé** (garantie JSON before=after triviale : 0 endpoint touché côté calcul). |
| C5 | 3D bâtiments lit LiDAR | **Vérifié** : `/map/batiments.geojson` lit `labuse_hauteur_lidar_m(bhl.faitage_m)` (COALESCE BD TOPO, borne ≤ 60 m). Saint-Denis **1784/1789** bâtiments `lidar=true`, Saint-Paul **1208/1214**, Saint-Pierre **1673/1681** — hauteurs plausibles (4,6–19,9 m). `C5_3d_saintdenis.png`. |

> Lot C est fortement dépendant d'un accès prod authentifié (compte de test) que cette session n'a pas (les endpoints commune exigent une auth → 401). C1 prod et une repro fidèle de C2/C3 nécessitent ce compte. C5 et C1-local sont faits ; C2/C3 ne sont pas reproductibles en local (tout répond 200).

## Lot B — documents (Gabarit, Étude de faisabilité, Bilan)

**B1 — chaque calcul recalculé à la main vs donnée servie : 0 écart.** Les 3 documents lisent la donnée servie (aucun recompute front). Recompute à la main (témoins BY0083 / BZ1065), tout **MATCH** :

- **Gabarit** (`gabarit/engine.py`, `api/gabarit.py`) : plafond emprise BZ1065 = 1567 × 30 % = **470,1** ✓ ; BY0083 emprise = silence prouvé → « Non réglementé » ✓ ; zone d'implantation terrain libéré **1 736 m²**, bâti déduit **869 m²**, bati déduit du gabarit **867 m²** (1736−869) ✓ ; hauteur 9/6 m (BY0083), 7/4,5 m (BZ1065) lues du PLU. Le plafond est calculé **à part**, jamais `min(zone, plafond)`. PDF régénéré + **ouvert** (`B_gabarit_BY0083.pdf`, 3 pages, valide).
- **Étude de faisabilité** (`implantation/capacite.py`, `exports/etude_faisabilite.py`) BY0083 : **16 logements**, SDP **1 365 m²** (682,5 × 2 niveaux), SHAB **1 028 m²** (ratio 0,753), places PLU **32** (16 × 2), **17,8 m²/place** (569,3/32), pleine terre ≥ **983 m²** (40 % × 2458) ✓. Loi vs PLU : `plafond_national=null` → barème PLU (2 pl/log) appliqué. BZ1065 : « simulation impossible » (hauteur 4,5 m égout n'autorise aucun niveau habitable) — honnête, pas un écart. PDF régénéré + **ouvert** (`B_etude_BY0083.pdf`, 133 Ko, valide).
- **Bilan** (`bilan/moteur.py`, `bilan/reperes.py`) : taxe d'aménagement BY0083 = 892 × (5 %+2,5 %) = **66,9 €/m²** ✓, BZ1065 = 892 × (3 %+2,5 %) = **49,06** ✓ ; archéologie = 892 × 0,40 % = **3,57** ✓. Run complet (prix sortie 4 730 TTC, TVA DOM 8,5 %) : CA TTC **4 862 440**, CA HT **4 481 511,52**, TVA résiduelle **176 293,26**, résultat net **1 240 446,77**, marge **27,7 %**, charge foncière **811 €/m² SUV** — **tout MATCH** (TVA : base HT→×taux, base TTC→/(1+taux)). ⚠ Le PDF Bilan exige une **session** (`compte_ou_401`, comme en prod) : non régénérable sans compte de test ; l'**écran** Bilan utilise les routes publiques `/bilan/{idu}/modele` + `/calcul` et le **même `Moteur`** que le PDF (calc vérifié = PDF correct).
- **Cohérence croisée** : l'Étude lit le Gabarit (robinets `gabarit_zone_libere_m2`/`gabarit_implantation_m2`) → terrain libéré 1 736, bâti déduit 869, 1736−869 = 867 : **une seule valeur, deux documents, 0 divergence**.

**B2 — fenêtre Bilan : lien « Fiche → » retiré.** `DocumentsView.tsx` — la carte parcelle (`ParcelleResolue`, partagée par Dossier/Bilan/Apporteur/Pré-dossier/Gabarit) reçoit `showFiche` ; passé `false` pour `d.key==='bilan'`. **Vérifié live** : Porte Bilan sans « Fiche → », Porte Dossier **garde** « Fiche → » (`B2_Bilan_porte.png` / `B2_Dossier_porte.png`).

**Validation Lot B** : `tsc` 0 ; B1 = 0 écart (recompute à la main, agent de vérification) ; PDF Gabarit + Étude régénérés et ouverts.

## Lot E — clôture

- **Commits** (branche `fix/recette-prod-1`, depuis `origin/main` `a582f8f4`) : Lot A `9e8b060e`, Lot D `512e98a5`, Lot F+C `8a1b9c62`, Lot B `3c9f0e34` (+ docs). **Poussés**, hook pre-push vert (suite pytest complète).
- **Validation globale** : `tsc` 0 · vitest **299/299** · pytest ciblés (gabarit/faisabilité/zonage/calibrage **156**, commune/contexte/signaux/fiche **171 passed/13 skipped**) · 0 erreur console sur les écrans touchés.
- **Pas de merge, pas de déploiement** (comme demandé — la mise en prod suivra avec un mandat DEPLOY).
- **Captures / PDF** dans `reports/RECETTE-PROD-1/` (gitignoré). Harnais Playwright `frontend/qa-rp1/` (gitignoré).
- **Ports** 8850 (API) / 6050 (front) libérés en fin de session ; navigateurs Playwright fermés par chaque script de capture (`browser.close()`).

### Bilan par lot

| Lot | Résultat |
|-----|----------|
| **A** fiche parcelle | A1 (6 contradictions bâti/SDP/urbanisme/réseaux) + A2 polices + A3 bouton Pièges retiré + A4 espace + A5 icônes vérifiées + A7 gabarit « non calibré » (vrai bug de lecture backend) + A8 prix de sortie. |
| **B** documents | B1 recompute à la main = **0 écart** (3 documents) ; B2 lien Fiche retiré de la fenêtre Bilan. |
| **C** vitesse | C5 3D LiDAR **vérifié** ; C1 mesures locales ; C2/C3 non reproductibles en local (tout répond 200) ; **prod non accédable** (401 sans compte de test) — signalé. |
| **D** accueil/carte/Sources/Projets/Copilote | D1 animation (règle réécrite) · D2 encart panneau vide · D3 diag seul · D4 noms communes · D5 Sources épurée · D6 Projets · D7 Copilote 2×5. |
| **F** fiche commune | 10 corrigés (icônes, polices, surface, permis, foncier couleur, risques, CatNat, dates, fiscalité, identité, équipements) + 1 vérifié OK (SDP unité) + 2 backend signalés (collecte Radar, seuils Activité). |

### À signaler à Vic
- **A7** (gabarit) : correction d'un **bug de lecture backend** — Saint-Benoît Ub (et zones similaires : enveloppe calibrée + hauteur en table graphique par secteur) était déclarée « PLU non calibré » à tort. Le gabarit calcule désormais (emprise réelle) avec une hauteur **estimée** honnête. Change le gabarit de cette CLASSE de zones (à valider).
- **Lot C** nécessite un **compte de test prod** pour C1 (mesures prod) et une repro fidèle de C2/C3 (les endpoints commune exigent une auth → 401).
- **F backend** (non appliqué, nécessite recompute du cache) : date de dernière collecte Radar dans la section Activité ; unification des seuils Activité/Radar (`pige/signaux.py`).
- **veille_plu.yaml** : 7 dates ISO « ( AAAA-MM-JJ) » corrigées en français ; prend effet au prochain recompute du cache commune (un normaliseur front assure l'affichage FR immédiat entre-temps).
