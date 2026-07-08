# DERIVATIONS — Socle V1 (front)

Décisions de design **dérivées** de la maquette (`docs/design/mockups/dashboard_v2_exploration_1.html`)
et des 9 exigences. En cas de conflit **l'exigence gagne**. Les points marqués **⚠ décision Vic**
attendent son arbitrage (revue Brique 1).

## Design system (extrait de la maquette, → `tailwind.config.js`)

**Couleurs**
| token | hex | usage |
|---|---|---|
| `bg` (noir) | `#060A08` | fond carte / app |
| `surface-1` | `#0B100D` | rail, panneau gauche |
| `surface-2` | `#0D120F` | boîtes carte (zoom, légende, outils) |
| `surface-3` | `#111814` | cartes résultat, omnibox, chips |
| `line` | `#1B2620` / `#1E2A23` | séparateurs / bordures |
| `mint` (menthe) | `#5CE6A1` | accent primaire, scores hauts, actif |
| `mint-ink` | `#06130C` | texte sur menthe |
| `txt-hi` | `#ECF5EF` | titres |
| `txt` | `#C9DCD1` | corps clair |
| `txt-mut` | `#8FA69A` | secondaire |
| `txt-dim` | `#5C7268` | tertiaire / labels mono |

**Statuts matrice** (couleurs maquette « VERDICT ») — l'exigence #3 impose 5 statuts ; la maquette
en montre 5 mais nomme « Opportunité » et **omet « à surveiller »**. Résolution (exigence gagne) :
| statut (SCHEMA scoring) | libellé UI | couleur |
|---|---|---|
| `chaude` | **Chaude** | `#5CE6A1` (menthe vive — statut hero) |
| `a_surveiller` | À surveiller | `#4ADE96` (vert, un cran sous chaude — **dérivé**, absent de la maquette) |
| `a_creuser` | À creuser | `#E8B44C` |
| `ecartee` | Écartée | `#E8695A` |
| `exclue` (hard-exclude) | Exclue | `#6B7A72` |
| (hors q_v2) | Non évaluée | `#39463F` |

> **Décision Vic (1) — TRANCHÉE (Brique 1)** : libellé `chaude` = **« Chaude »** (Vic : « 42 CHAUDES »,
> nomenclature matrice). Couleurs : **chaude = menthe vive `#5CE6A1`** (statut hero), **à surveiller =
> vert `#4ADE96`** (un cran en dessous) — échelle descendante lisible. « Exclue » repliée dans « écartée »
> au niveau matrice (Vic : « les 4 statuts »).

**Typo** : Space Grotesk (500/700) → scores & titres display · JetBrains Mono (400/500/600) → IDU,
labels de section, valeurs · Inter (400/500) → corps.

## Structure (mode Cartes)

- **Rail 64 px** (`surface-1`) : IA · **Cartes** (actif) · Outils · CRM ; bas : **J-2** (fraîcheur,
  exigence #9) + avatar profil. Icônes mono, actif en menthe.
- **Header 56 px** : omnibox (« Rechercher : adresse, AB 0234, lieu-dit… », raccourci `/`) · chips
  filtres (Saint-Paul ×, Zone U ×, Score ≥ 70 ×, + Filtre pointillé) · toggle **Verdict / Mutabilité** ·
  **cloche notifications** (exigence #7, absente de la maquette → ajoutée) · avatar.
- **Panneau gauche 300 px** (`surface-1`) : titre « Cartes » + chevron repli ; section **COUCHES**
  (cases : Zonage PLU, Parcelles, PPR, Vue mer, Parc national) ; section **RÉSULTATS** (« triés par
  score », compte « N opportunités · M à creuser », barre de répartition, « sur 51 129 — filtre dur
  actif ») ; **cartes résultat** (barre d'accent gauche colorée par statut, IDU mono, surface · lieu-dit,
  score Space Grotesk coloré) ; pied « N résultats · Tout voir → ».
- **Carte** : fond raster (Carto dark) + parcelles ; contrôles zoom (+/−) haut-gauche ; outils
  haut-droite ; **légende VERDICT** bas-droite ; pastille d'invite « Cliquez une parcelle… » ;
  attribution « © OSM · CARTO ». Clic parcelle → fiche (Brique 2).

> **Décision Vic (2) — retenue (Brique 1, à confirmer en revue)** : *Verdict* = coloration par
> `matrice_statut` ; *Mutabilité* = dégradé continu par **SDP résiduelle** (m² constructibles, socle q_v2)
> — plus proche de « combien peut-on bâtir » que Q, et cohérent avec l'existant `/map/bati`.

## Décisions Brique 1 (implémentées)
- **Source de vérité** : le front lit `?source=q_v2` (dryrun_parcel_evaluations), JAMAIS l'éval live.
  Compteur d'en-tête = « N chaudes · M à surveiller · K à creuser » (83/1720/3353 à Saint-Paul),
  PAS « 737 opportunités ».
- **Complétude partout** (exigence #1) : anneau sur chaque carte résultat + trio Q/A/Complétude en fiche.
- **Lieu-dit** : la table `parcels` n'a pas de lieu-dit → on affiche la **commune** (pas de mock). À
  enrichir plus tard (lookup spatial des lieux-dits).
- **Carte** : les 46k écartées sont quasi transparentes (fill 0.04, sans contour) pour que les ~5k
  promues ressortent — fidèle à l'intention « île sombre, opportunités qui brillent » de la maquette.
- **Service** : build Vite `base:/socle/` → monté par FastAPI sous `/socle` ; `/` redirige vers lui ;
  l'UI Vue historique reste sous `/app` (transition).

## Écarts assumés (exigence > maquette)
- Complétude affichée partout (exigence #1) — non visible dans ce wireframe statique ; ajoutée
  (mini-indicateur sur les cartes résultat, anneau en fiche).
- Cloche notifications (exigence #7) — ajoutée au header.

## Filtres (Brique 1 — correctif)
Système de filtres client (source unique = le geojson q_v2, partagé carte/liste/fiche) :
- **Chips de statut** (panneau gauche) : Tout / Chaude / À surveiller / À creuser, avec compteurs.
  Filtrent **carte ET liste** simultanément (store partagé `filters.statut`).
- **Omnibox** : chip « Saint-Paul » = périmètre fixe (Brique 1) ; chips dynamiques par filtre actif
  (statut, Q ≥ N, surface ≥ N) supprimables via ×. « + Filtre » ouvre un popover (statut, score, surface).
- **Compteurs** = comptage sur score+surface (indépendant du statut, pour garder le breakdown lisible) ;
  **liste + carte** = filtre complet (statut inclus). Retirer un chip met à jour les trois instantanément.

## Décisions autonomes (mandat socle complet — Vic arbitre à la revue finale)
- **Compteurs = SQL q_v2** : le mandat cite « 42 chaudes · 486 à surveiller · 13 979 à creuser » mais
  le SQL direct sur `run_label='q_v2'` (la règle QA du mandat elle-même) donne **83 · 1 720 · 3 353**.
  Les « 486 » correspondent au run *etape2*. L'UI affiche le SQL ; l'écart est consigné dans NOTES.
- **Couches COUCHES toutes réelles** : Zonage PLU / PPR / Parc national = overlays `spatial_layers`
  (endpoint `/map/layers.geojson`, géométries simplifiées) ; Vue mer = liseré cyan sur les promues à
  vue dégagée (propriété du geojson) ; Parcelles = visibilité des calques. Aucune case morte.
- **Omnibox** : recherche par IDU (filtre live de la liste ; Entrée ouvre la première fiche) ;
  raccourci `/`. L'adresse/lieu-dit attendra un géocodeur (hors V1).
- **Anti-serveur-périmé** : middleware `Cache-Control: no-store` sur le HTML (un index.html en cache
  pointait vers un vieux bundle → crash au clic parcelle constaté par Vic) + ErrorBoundary global avec
  consigne de relance.
- **CRM** : la fiche reste ouvrable par-dessus le kanban (clic IDU d'une carte → vue Cartes + fiche).
  Suppression d'une carte au survol (✕). Pas de fil événementiel (V1.1, conforme brief).
- **PDF** : fpdf2 (pur Python) + fontes OFL du design system embarquées (`api/fonts/`) — PDF sombre
  fidèle, généré serveur, bouton fiche → nouvel onglet.
- **IA** : stub propre à deux niveaux — zone rail (page vide élégante) et bouton fiche (popover
  « le narratif arrive en V1.x, le scoring reste déterministe »).
- **Icônes rail** : redessinées (20 px, trait 1.5-1.6, style contour unifié) — les précédentes
  rendaient brouillon à petite taille.

## Cycle polish (mandat amélioration continue)
- **PDF = palette IMPRESSION** : fond blanc, encre quasi-noire, menthe déclinée en encre `#0B8A5F`
  (contraste AA papier) — filet menthe en tête de page, chips pâles. Le dark reste l'écran.
- **Drawer source** (remplace la navigation) : extrait de la ligne + carte d'identité de la source
  (fournisseur/fiabilité/synchro/doc) ; ✕, clic-extérieur, Échap ; fiche conservée dessous ;
  escalade « Toutes les sources → » vers la page complète.
- **Identité** : logo buse + wordmark header (wordmark masqué < 1350 px), favicons 16/32/180
  générés (PIL, pastille sombre + buse menthe), titre « LABUSE — Radar foncier ».
- **Fonds de plan** : Carto dark / Plan IGN / Ortho IGN via WMTS Géoplateforme (libres, tuiles
  TESTÉES sur le 974). « Remonter le temps » : Actuelle / 2000-2005 / 1950-1965 — les millésimes
  2006-2015 renvoient 400 sur la zone, exclus. Pas de tuiles Google (CGU) → deep-link fiche.
- **3D** : MNT terrarium AWS (libre), exaggeration 1.35, bascule pitch 55° auto. Off par défaut.
- **Mesure** : distance/surface (clics, double-clic fige, Échap quitte), altimétrie au point
  (API geopf RGE ALTI). Étiquette = Marker HTML (les glyphes Carto sont bloqués CORS → aucun
  symbol layer). **Zone** : polygone → filtre liste+compteurs libellés « (dans la zone) » ;
  la carte affiche le tracé mais ne masque pas les parcelles hors zone (filtrage par géométrie
  côté GPU = liste d'IDU trop lourde ; choix honnête documenté).
- **Filtres v2** : statuts multi, surface min/max, SDP min, événement, vue mer, flags
  (pollution/ABF/ICPE/risques/prescription — agrégés par parcelle côté API). Compteurs SQL quand
  vierges, recalcul marqué `*` sinon. **URL partageable** (#f=…) : filtres + zone restaurés au
  chargement.
- **Chasse libre** : focus clavier menthe (:focus-visible), Échap ferme fiche/popovers/drawer,
  états vides avec action « Réinitialiser », retry sur toutes les erreurs réseau, skeletons de
  liste, code-split (app 69 Ko · vendor 184 Ko · maplibre 802 Ko parallèle).
- **Perf mesurée** (Playwright, serveur local) : DOM 103 ms · UI 329 ms · carte 409 ms (< 2 s ✓) ·
  données+liste 3,7 s (geojson 51 129 parcelles — passage MVT = prochain cycle) · filtre plein
  jeu 575 ms.

## Post-revue Vic (P0/P1)
- **P0 — leçon de QA** : un popover absolu DANS un conteneur `overflow-x-auto` est rogné
  (présent au DOM, invisible à l'humain) — et Playwright interagit avec les éléments rognés,
  d'où une QA faussement verte. Règle : les surfaces flottantes (popover/drawer) vivent HORS
  des conteneurs défilants, et la suite embarque `qa_filtres_reels.mjs` : clic souris réel,
  détection de rognage par ancêtre overflow, vérification des effets liste+compteurs+carte,
  suppression par ×. Le test était ROUGE sur le build fautif, VERT après correction.
- **P1 — identité** : buse reprise EXACTEMENT du mockup (`M16 34 Q24 24 32 32 Q40 24 48 34`,
  normalisée `M0 10 Q8 0 16 8 Q24 0 32 10`) — header, rail, favicons regénérés (pixels menthe
  vérifiés par assertion). La barre d'onglet native n'est pas capturable en headless
  (permissions macOS) : la capture 20 montre le favicon RÉELLEMENT SERVI + le titre RÉEL.

## Passe expert (IA réelle)
- **QA provider-aware** : les suites lisent `/ia/status` — stub → bannière « Mode dégradé » EXIGÉE,
  anthropic → INTERDITE. Un même test décrit les deux mondes ; plus d'assertion périmée au changement de clé.
- **Latence réelle** : tous les `waitForTimeout` post-IA remplacés par des `waitForSelector`
  (20-25 s max) — le test attend le résultat, pas une durée devinée.
- **« score > 80 »** : stub → `scoreMin: 80` (approx.), modèle réel → `81` (strict, filtre inclusif).
  Les deux fidèles → le test accepte 80|81. Non-déterminisme assumé, borné par le schéma.

## Extension île (mandat généralisation)
- **Défaut = « Toute l'île »** (mandat : compteurs île par défaut) ; la commune vit dans
  l'URL `#c=` — un lien partagé rouvre le bon périmètre.
- **Carte hybride** : mode commune = GeoJSON intact (26 Mo à SP, zéro régression) ; mode île
  = MVT matérialisé (z10-12 promues, z13+ tout — les écartées à 0,04 d'opacité n'apportent
  rien sous ~10 km d'écran). Mêmes clés de propriétés → mêmes expressions de filtre ;
  `flags` en CSV dans les tuiles (`['in', flag, ['get','flags']]` marche sur chaîne et tableau).
- **Honnêteté avant boutons morts** : en mode île, la zone dessinée et les couches
  commune-scopées (zonage/PPR/parc) sont DÉSACTIVÉES avec la marche à suivre — pas des
  toggles qui ne font rien.
- **Copilote & périmètre** : une phrase AVEC commune bascule le sélecteur ; une phrase SANS
  commune ne touche pas au périmètre courant (`commune: null` est la valeur neutre du modèle,
  pas une demande de revenir à l'île — le sélecteur est là pour ça).
- **Liste île = 500 premiers** (tri événement d'abord puis score), affiché honnêtement ;
  les compteurs restent SQL-exacts (filtres des chips traduits en SQL, mêmes clés que matchScope).
- **Suites historiques** : elles testent le MODE COMMUNE → épinglées sur `#c=Saint-Paul`.
  Piège appris : `goto` vers la même URL à hash différent = navigation fragment SANS
  rechargement → `reload()` explicite quand la suite veut une page fraîche.
- **Matrice réalignée (île)** : les statuts q_v2 de Saint-Paul dataient d'une convention
  jamais committée (dvf/sitadel en Q) ; l'invariant du mandat (base+Σ=score) échouait sur
  SP et passait sur les 23 autres. Rejoué le POST-PASS matrice de SP sur la convention
  committée (83→375 chaudes, AC0253 toujours chaude, cascade intouchée, traçabilité 20/20).
  Arbitrage seuils rendu à Vic (BILAN_ILE §2) — une île, une convention.
- **QA adaptées aux données île** : liste plafonnée à 200 cartes (« Tout voir ») → assertion
  min(n,200) ; module_division porte 24 communes → compteur SQL scoppé commune.

## Mandat mini (convention · dossiers · calibrage)
- **Convention de matrice** : pas de nouveau fichier — `config/scoring_matrice.yaml` EST
  l'objet versionné (en-tête convention: version/date/justification). Les seuils étaient
  déjà en YAML ; l'invariant anti-dérive = empreinte statut×commune identique à convention
  identique (prouvé simulate ET apply).
- **Clé dossier = SIREN** (personnes morales DGFiP). Limite : deux parcelles d'une même
  personne PHYSIQUE ne se regroupent pas (aucune identité en base, doctrine) — comptées au
  reliquat « sans identité », jamais fusionnées silencieusement.
- **Calibrage re-gravé = le zonage opposable** (ce que la DB sait). Les RÈGLES par zone
  (hauteurs/articles des règlements PDF) n'ont JAMAIS été en DB — leurs YAML perdus restent
  au backlog (re-extraction règlements). Manifestes versionnés config/calibrage/ (1,5 Mo) ;
  géométries data/calibrage/*.gz (politique du dépôt : pas de dump public en git — couvert
  backup, régénérable par export).
- **Marqueurs communes = DOM markers** (pas de couche symbol : aucune dépendance glyphes,
  cohérent avec les étiquettes de mesure) ; centroïde = centre bbox (suffisant à z<10).

## Mandat contexte-commune (roadmap promotrice)
- **Branche depuis feat/ile-entiere** (le merge île n'était pas encore dans main ; le volet
  s'appuie sur le sélecteur/marqueurs île — un merge île→main rendra celle-ci propre).
- **SRU** : au millésime 2025, les 24 communes 974 sont TOUTES soumises — le statut réel
  supplémentaire est « exemptée 2023-2025 » (5 communes), restitué tel quel au lieu du
  « non soumise » attendu par le mandat (la source prime).
- **NPNRU** : périmètres DEAL = QPV génération 2015 ; la couche QPV de la base est en
  génération 2024 → les deux coexistent, correspondance des codes portée dans attrs.
  « Adjacente » = ≤ 100 m (seuil affiché, arbitraire assumé).
- **Équipements** : catégories d'affichage (mairie/police/sport) SÉPARÉES des 4 catégories
  qui nourrissent parcel_amenites (pas de purge croisée — le signal distance du scoring ne
  dérive pas). Bbox par commune → les POI voisins débordent (voulu : l'école juste de
  l'autre côté de la limite compte) ; cercles colorés + popup (pas d'icônes symbol : pas de
  sprite dans le style), plancher z13. Câblage scoring = dette G3, non entamé.
- **Typologie logement** : l'INSEE ne publie pas le Tn strict à la commune → répartition
  par nombre de pièces (1p…5p+) affichée comme « proxy T1…T5+ », libellé explicite.
- **PLH** : périmètre « social » variable selon les documents (LLTS+LLS seul, ou avec PLS)
  → le % n'est posé QUE quand publié (TCO 47 %, CASUD 40 %) ; ailleurs l'absolu sourcé.
  Les 5 PLH sont tous en bilan/révision (CASUD échu) — affiché tel quel.
- **Entrées du volet** : ⓘ par ligne du sélecteur + bouton « ⓘ Contexte » quand une commune
  est active (le marqueur île mène à la commune, donc au bouton — pas de 3e entrée).
- **reliability_level** : enum existant (verifie/a_confirmer/sous_convention) — « officielle »
  n'y est pas ; les 4 nouvelles sources sont « verifie ».
- **POI Overpass** : miroirs capricieux (504 en rafale) → ré-ingestions avec retries ; état
  final 24/24 communes, 5 874 POI d'affichage. Lacune source consignée : la mairie de
  Bras-Panon n'est pas taguée `amenity=townhall` dans OSM (0 au compteur — honnête).
- **RTAA DOM (5bis)** : tout le contenu vient de `config/rtaa_dom.yaml`, VÉRIFIÉ Légifrance
  le 08/07/2026 (versions consolidées) — prise majeure : le cadre CCH a été réécrit au
  01/01/2025 (R.192-1 à 192-4, décret 2024-168) et l'ECS n'est plus « solaire » strict mais
  « ≥ 50 % chaleur renouvelable ». Seuils Réunion vérifiés : 400 m et 600 m — énoncés DANS
  chaque exigence ; l'altitude de la parcelle n'est PAS calculée (pas de donnée parcellaire
  d'altitude en base ; conditionner à la parcelle = backlog si le besoin se confirme).
  Réserves du vérificateur consignées en tête du YAML (arrêté « indice de confort thermique »
  introuvable, tableaux acoustiques condensés) — rien de non-vérifié n'est affiché.

## Correctifs revue Vic (08/07)
- **C2** : logo conservé = combo header (oiseau + « LABUSE ») ; le rail devient pur icônes.
- **C3** : traitement par fond — Carto sombre → variante `dark_nolabels` sous z10 en mode île
  (même fournisseur, zéro dépendance) ; ortho sans labels par nature ; Plan IGN inchangé
  (choix délibéré d'utilisateur, surtout aux zooms parcellaires).
- **C4** : chip renommé « Opportunités » ; déclencheur du popover = « pourquoi ? ▾ » sur la
  ligne de cadrage (le chip garde son rôle de filtre).
- **C7 voie technique** : trame = nos propres données (couche « limites » activée PAR DÉFAUT
  + tuiles « tout » dès z12 — tuile dense ~850 Ko mesurée) plutôt que le raster PCI IGN
  (lignes sombres illisibles sur fond sombre, pas d'inversion possible en raster). À z10-11
  les parcelles sont sub-pixel : marqueurs communes + promues seules, assumé. Clic universel
  = résolution serveur point→parcelle quand aucune feature vectorielle sous le curseur.
- **Écartées opt-in** : le filtre statut explicite ÉLARGIT le périmètre promues côté SQL
  (base_statuts) ; l'opacité 0,72 existante rend les écartées pleinement lisibles une fois
  filtrées.

## Extension cascade île (08/07)
- **Règles extraites des verdicts, pas réinventées** : formats de détail, seuils (largeur<8 m
  ET allongement>8× sur enveloppe ORIENTÉE ; groupes DGFiP 1/2/3/4/9 ; barème SDP
  100/300/800/2000/5000) et sémantique des poids (NULL ⟺ parcelle exclue) rétro-déduits des
  153 387 lignes de Saint-Paul — preuve : diff ZÉRO en régénération complète.
- **weight_override** : le barème propre de residuel_socle (−25/−10, sévérité info) ne passe
  par aucune sévérité standard → `Verdict.extra["weight_override"]` honoré par
  compute_opportunity (additif, aucune couche historique ne pose la clé).
- **Backfill set-based ≡ re-run** : couches indépendantes des autres verdicts → INSERT direct
  + nullification des poids des parcelles nouvellement exclues (sémantique weights=[0]* du
  moteur). Idempotent par commune. Les runs FUTURS passent par le moteur (couches enregistrées).
