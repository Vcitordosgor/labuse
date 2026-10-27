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
| F — fiche commune | ⏳ |

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

## Journal — lots suivants

_(B, C, F — rempli lot par lot)_
