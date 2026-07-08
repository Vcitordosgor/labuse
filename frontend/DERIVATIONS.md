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

## Revue Vic n°2 (08/07)
- **R1 paliers de tuiles** : TOUT dès z9 (le cadastre d'abord) — le poids venait des PROPRIÉTÉS
  (idu uniques ×100k = 15 Mo/tuile), pas de la géométrie → tuiles MAIGRES sous z12 (status +
  commune seulement, valeurs dédupliquées par l'encodage MVT) : z9 ≈ 4,5 Mo + 1,7 Mo (~6 Mo à
  l'ouverture, cache serveur LRU + navigateur 1 h), z10 4,7 Mo, z11 375 Ko, z12+ complet 850 Ko.
  Le clic sous z12 passe par /parcels/at, le ping vole à z16 — l'absence d'idu n'ampute rien.
- **R1 bouton signature** : hero dans le panneau gauche (oiseau + « LABUSE a trié pour vous »,
  glow menthe) remplaçant la liste quand le verdict est éteint ; « ✓ Tri actif · éteindre »
  quand allumé. Marqueurs communes NEUTRES verdict éteint (nom seul), comptes quand allumé ;
  chevauchements Nord réglés par offsets pixels manuels (SD/SM/SS/Le Port/Possession).
- **R2 secteurs** : nouveau filtre `communes` (multi) de bout en bout (schéma IA, SQL, carte,
  hash `cs=`) — Nord/Ouest/Sud/Est = microrégions figées dans SECTEURS (ia.py). Le cadrage
  est UNE réponse (reformulation + ≤2 questions à chips) ; le suivi part seul quand toutes
  les questions sont répondues ; après cadrage le modèle répond TOUJOURS en filtres (jamais
  programme). Le copilote ALLUME le verdict (mise en scène cohérente avec R1). Stub : jamais
  de questions (direct ou refus documenté) — inchangé.
- **R4** : dark_nolabels à tous les zooms — les noms de rues partent aussi (assumé).
- **R8** : deep-link cadastre = Géoportail IGN PCI Express (permalien centré) — le site DGFiP
  n'a pas de deep-link stable sans session.
- **Stabilisation QA finale (micro-choix)** : `temperature=0` sur l'appel NL (les suites
  testent le COMPORTEMENT du copilote en réel — la variance créative ne l'améliore pas et
  rend la QA non reproductible) ; flags gravés dans le prompt comme FILTRABLES (monument →
  abf, usine → icpe…) avec interdit explicite d'out_of_scope sur ces cas. Suites : jamais
  renvoyer un objet MapLibre par le pont playwright (`() => void map.jumpTo(...)` — l'objet
  Map sérialisé avec les tuiles « tout » dépasse 512 Mo) ; pingState lit la couche ping
  ACTIVE (opacité > 0) parmi parcels-ping/ile-ping — un ancien ping éteint peut subsister ;
  l'IDU attendu d'une notification vient de l'API /events (les événements sont île entière,
  plus de préfixe commune fabriqué).
- **C6 réécrit par R5+R6** : l'assertion « toast au clic couche désactivée » n'a plus d'objet
  (aucune couche n'est bloquée en île). La suite vérifie désormais les deux remplaçants :
  « Zonage PLU » S'ACTIVE en île (ovmvt-zonage visible) et le SEUL contrôle encore bloqué
  (outil zone — le comptage client mentirait à l'échelle île) montre le hint ANCRÉ au bouton,
  auto-éteint ~2,5 s.

## Copilote-projet — V1 : l'objet PROJET (08/07)
- **Séparation fiche / recette** : `projets.fiche` (jsonb) = ce que le promoteur A DIT (validé
  par FICHE_SCHEMA côté serveur) ; `filtres` + `programme` = ce que le moteur EXÉCUTE, DÉRIVÉS
  de la fiche de façon déterministe (jamais l'IA). Ouvrir un projet = REJOUER (filtres
  réappliqués sur les données du jour), jamais un snapshot figé — `derniere_execution_at`
  horodate le rejeu.
- **La SDP besoin vient de la formule M22 EXISTANTE** (`unités × surface_unité(60) × 1,15`,
  cf. modules.faisabilite_sens2) — l'IA ne produit aucun m². `ampleur.sdp_m2` explicite prime
  sur `ampleur.logements`.
- **Contraintes rédhibitoires → exclusion SQL** : `contraintes:["eviter_ppr"…]` (fiche) →
  `flags_exclus` sur /parcels et /stats (`NOT EXISTS` sur la couche flag, même vocabulaire que
  `flags`). Preuve de cohérence : à Saint-Paul, `total = avec_risques + sans_risques`
  (51 129 = 49 219 + 1 910). Nouveau filtre front `flagsExclus` de bout en bout (chip « Sans …»,
  hash `fx=`, matchScope client).
- **Budget foncier = donnée de fiche, PAS un filtre** : aucun prix par parcelle en base → un
  filtre budget serait menteur. Affiché dans la fiche projet, jamais appliqué au moteur (consigné).
- **derive_programme** (mapping consigné) : type + logements → ProgrammeIn M22 avec 1 bâtiment,
  R+2 (défauts du formulaire), `logements_par_batiment = total` (la formule M22
  `unités = bâtiments × logements/bât` est préservée : 1 × total = total). La vérité reste le
  formulaire M22 pré-rempli, éditable (V3).
- **Lien CRM** : `pipeline_entries.projet_id` (FK ON DELETE SET NULL) — une piste ajoutée au
  kanban depuis un projet porte sa référence (`entry.projet = {id, nom}`). Matière du futur
  radar cron (rien câblé) : `filtres` est déjà le prédicat de match ; seuls les `statut='actif'`
  seront matchés.
- **Boot-heal réparé** : l'ancien `@app.on_event("startup")` était MORT depuis le passage au
  `lifespan` (FastAPI ignore `on_event` quand un lifespan est fourni) — les `ensure_tables`
  des routeurs (modules/ia/events/partners/projets) vivent désormais dans `_lifespan`, exécutés
  au démarrage. Sans ça la colonne `projet_id` n'était jamais créée au boot.
- **Chorégraphie d'application partagée** (`useApplySearch`) : le copilote R2 ET « ouvrir un
  projet » passent par le MÊME hook (périmètre → filtres → verdict allumé → vol caméra →
  restitution SQL). Zéro duplication — `IAStub.apply` en est devenu un simple appel.
- **Rail** : nouvelle entrée « Projets » (dossier + étoile) entre Outils et CRM. Vue CRUD
  sobre : liste, ouvrir/renommer/archiver, onglets Actifs/Archivés, création renvoyée à
  l'entretien copilote (« + Décrire un projet » → vue IA).

## Copilote-projet — V2 : l'entretien (08/07)
- **Deux voies d'entrée** : (1) le champ copilote détecte l'intention projet — `/ia/search`
  renvoie `{projet_intent: true}` pour une demande d'OPÉRATION sans critère filtrable
  (« je veux monter… ») ; (2) bouton explicite « Décrire mon projet ». La recherche simple
  (filtres) et « les chaudes de X » (parcours C) restent inchangées : critère filtrable présent
  → forme 1 directe.
- **La forme `cadrage` (R2) est REMPLACÉE par l'entretien** : le cadrage ≤2 questions →
  filtres jetables devient l'entretien ≤4 questions → objet PROJET persistant. `CADRAGE_SCHEMA`
  supprimé ; qa_revue2/qa_ia mises à jour (R2-b teste désormais l'entretien).
- **L'IA re-dérive la fiche ENTIÈRE chaque tour** (prev fiche + nouveau message → fiche mergée,
  validée par FICHE_SCHEMA à vocabulaire fermé). Les chips sont des raccourcis : cliquer une
  chip renvoie son LABEL comme message → l'IA re-merge. L'IA reste seule maîtresse de la
  construction de la fiche, sous garde-fou schéma. `clean_fiche` retire les null/""/vides que
  l'IA émet pour une dimension pas encore sue (hors enum → casserait le schéma).
- **Skippable + défaut honnête** : chaque question porte un `defaut` affiché (« → toute l'île »,
  « → sans contrainte rédhibitoire ») ; le skip envoie « je ne sais pas » → l'IA applique le
  défaut dans la fiche. Jauge = 4 cases (programme/ampleur/où/contraintes) remplies.
- **Arbitrages SOURCÉS ou tus** : `GET /projets/reperes?dimension=secteur|commune` sert, par
  SQL pur, nb d'opportunités (q_v2), prix médian DVF bâti (€/m² habitable), communes carencées
  SRU. Le front annote les chips d'une question `dimension:secteur`. AUCUN chiffre produit par
  l'IA. Le prix médian utilise le bâti (aucune mutation terrain-nu en base — consigné).
- **Interdit d'opinion marché non chiffrée** : gravé dans le prompt système ET vérifié par un
  garde-fou (`contient_opinion_marche` + `_neutralise_opinion`) — toute réponse portant « plus
  porteur / meilleur potentiel / je recommande… » dans un champ libre est NEUTRALISÉE
  (reformulation générique, chips fautives purgées, flag `doctrine_neutralise`).
- **Mode dégradé stub** : pas d'entretien simulé — `/ia/entretien` renvoie `fallback:true` +
  message honnête ; le front bascule sur la recherche directe. (Doctrine : jamais de questions
  fabriquées par le stub.)
- **derive vs create** : « Lancer la recherche » appelle `POST /projets/derive` (nom + filtres +
  programme + SDP besoin, SANS persister) puis applique — la restitution proposera « Enregistrer
  ce projet » (V3) qui, lui, crée l'objet. `useApplySearch` mutualise la mise en scène.

## Copilote-projet — V3 : la restitution reliée (08/07)
- **Le « pourquoi » par parcelle sort du MOTEUR** (`POST /projets/apercu`) : si un programme est
  défini, le top vient de M22 sens 2 (SDP résiduelle vs besoin, hauteur PLU vérifiée, marge de
  capacité) ; sinon du run q_v2 trié par score. Les lignes sont ASSEMBLÉES depuis les données
  (statut/score, SDP vs besoin, hauteur, carence SRU) — aucune valeur inventée. Un secteur
  restreint le balayage île de M22 aux communes du secteur (post-filtre).
- **derive vs apercu** : « Lancer la recherche » fait `deriveProjet` (filtres, carte) + `getApercu`
  (pourquoi) → la restitution enrichie ; la carte garde la chorégraphie `useApplySearch`.
- **Restitution mode PROJET** (panneau élargi) : top vertical avec pourquoi, « Enregistrer ce
  projet » (crée l'objet), puis « Exporter le PDF » + « Affiner dans M22 » + « Mes projets → ».
  Le mode recherche simple reste compact (inchangé).
- **PDF projet** (`GET /projets/{id}/export.pdf`, `pdf_projet.py`) : réutilise fontes/palette de
  `pdf_premium` (fond blanc, menthe en accents). Contenu = fiche de cadrage + top 5 parcelles
  avec pourquoi + mention « estimations indicatives / aucun chiffre produit par l'IA ». L'aperçu
  est RECALCULÉ à l'export (données du jour).
- **M22 pré-rempli** : « Affiner dans M22 » injecte le programme dérivé dans le formulaire M22
  (`setM22Prefill` + module programme) — la VÉRITÉ reste le formulaire, éditable (doctrine).
- **Rejouer = même restitution enrichie** : `ProjetsPanel` « Ouvrir » recalcule l'aperçu sur les
  données actuelles ; le projet étant déjà enregistré, le PDF est direct (pas de ré-enregistrement).

## Copilote-projet — V4 : QA + doctrine (08/07)
- **qa_projet.mjs** (parcours réels, clé posée) : A précis → entretien/fiche/M22/enregistrement/
  PDF ; B vague → ≤4 questions, skip à défaut affiché ; C « les chaudes de X » → zéro entretien
  (R2 intact) ; D rejeu → mêmes filtres. Suivi NON destructif (ensemble des ids avant/après —
  ne supprime que ses créations). SKIP propre si provider ≠ anthropic (entretien réel requis).
- **pret = périmètre déterminé** (pas type+périmètre) : un projet vague dont on passe le
  périmètre bascule sur « toute l'île » et devient lançable ; le type/l'ampleur raffinent sans
  bloquer. Sinon un skip du type (sans défaut de type) laissait `pret` faux à jamais.
- **L'entretien se referme après « Lancer »** (`onClose`) : ré-ouvrir le copilote = recherche
  fraîche (plus d'entretien fantôme).
- **DELETE /projets/{pid}** ajouté (CRUD complet + hygiène QA) — les pistes CRM rattachées
  gardent leur parcelle (FK ON DELETE SET NULL).
- **Test doctrine adversarial** : une demande piège (« quel secteur est le plus porteur… »)
  ne doit produire AUCUNE opinion marché non chiffrée dans la réponse (garde-fou neutralise).
- **Restitution allégée** : le compteur+top 3 tirait `/parcels?limit=500` — sous la contention
  réseau des tuiles « tout » (R1), la réponse mettait ~15-20 s à revenir (restitution en retard).
  La restitution ne demande plus que 20 résultats (`getResults(f, 20)`) : réponse légère, bien
  plus rapide. Amélioration UX réelle + QA stabilisée (timeouts restitution portés à 30-40 s).
- **M22 pré-remplissage défensif** : le copilote peut fournir un programme partiel (« 3 immeubles
  R+3 » sans nombre de logements → `logements_par_batiment: null`) ; le pré-remplissage ne
  remplace plus QUE les champs non-nuls (les défauts du formulaire tiennent) — sinon `null`
  écrasait le défaut et l'auto-run M22 échouait (422).

## Revue Vic n°3 — mise en valeur IA/outils + wording du tri (08/07)
Positionnement tranché : la cible est le PROMOTEUR / BAILLEUR SOCIAL / MARCHAND DE BIENS (foncier
constructible), PAS l'agent immobilier. 100 % présentation/wording/mise en page — rien au
scoring/cascade/matrice. Suite dédiée `qa_revue3.mjs` (P1+P3) verte, suites existantes vertes.

- **P1 — l'IA en DEUX PORTES** (`IAStub`) : la « recherche simple » et le « montage de projet »
  ne cohabitent plus au petit bonheur (un champ + un bouton perdu dessous) — deux TUILES à
  égalité (`data-porte-recherche` menthe · `data-porte-projet` violet). Recherche simple = « Dites
  en une phrase… » + le champ NL + exemples (chemin rapide, comportement inchangé). Montage =
  « Le copilote vous aide à cadrer votre opération » → l'entretien (chemin accompagné). L'accent
  projet violet `#B497F0` reste distinct de la menthe ; la doctrine (« l'IA ne calcule pas »)
  reste, plus discrète en pied.
- **P1.2 — entretien enrichi** (Vic : trop court) : plafond `ENTRETIEN_SCHEMA.questions`
  relevé **4 → 6** ; ids `perimetre/type/ampleur/gabarit/contrainte/budget` (type et ampleur
  DÉ-fusionnés → l'entretien pose naturellement plus de questions). **Dimension ajoutée =
  `gabarit` (hauteur souhaitée R+n)** — seule dimension neuve qui IRRIGUE : `ampleur.niveaux`
  (FICHE_SCHEMA) → `derive_programme.niveaux` de M22 (R+2 par défaut si tu). Écartées faute
  d'irrigation : « bâti à démolir » (aucun filtre présence-de-bâti) et « horizon » (aucun filtre
  temporel parcellaire) — jamais un champ qui n'irrigue rien (doctrine). Chaque question reste
  SKIPPABLE (défaut honnête « → R+2 par défaut »), jauge conservée (les 4 cases essentielles ;
  le gabarit s'affiche dans « Ampleur » : « 40 logements · R+3 »). `pret` toujours piloté par le
  périmètre → lançable tôt. Zéro question sur « les chaudes de Saint-Pierre » (inchangé : filtrable
  → `ia_search` direct, jamais `projet_intent`). Vérifié réel : 5 questions dont gabarit, R+4 →
  `niveaux:4` jusqu'à M22.
- **P2 — le tri = un AVIS argumenté, pas une décision** (Vic : « a trié pour vous » présomptueux).
  Wording retenu (une seule piste, consignée) : **« Afficher l'analyse LABUSE »** (bouton signature),
  état allumé **« ✓ Analyse LABUSE affichée » / « masquer »**, entonnoir popover **« son avis
  retient N opportunités. Le reste reste visible et cliquable — voici pourquoi il est écarté »**.
  Sous-texte : « Rien n'est masqué : le cadastre reste entier, chaque parcelle garde son verdict…
  Vous gardez la main ». Le GESTE est inchangé (cadastre → clic → couleurs/entonnoir/liste) ; seul
  le langage évolue — ton d'analyse contredictible, adapté à un pro qui refuse les boîtes noires.
- **P3 — outils désirables, sans jargon** (Vic : M01…M22 = langage d'ingénieur). Sort des codes M :
  **gardés EN INTERNE** (`ModuleDef.num` — logs, hash `#m=`, QA) mais **retirés de l'écran** (rail
  ET en-tête de module, désormais « OUTIL » + intitulé + bénéfice). Chaque outil porte une phrase
  de BÉNÉFICE métier (ex. Faisabilité programme = « Décrivez votre programme, LABUSE trouve où le
  poser »). **Curation** : regroupement par INTENTION — `Détecter le foncier` (d'abord = l'argument)
  · `Analyser & simuler` · `Passer à l'action` — et **PHARES** distingués (carte violette + ★,
  bénéfice lisible) : Faisabilité programme, Division parcellaire, Foncier fantôme, Scan patrimoine
  (Détecter) + Assemblage + Due diligence. Choix des phares = les notes « A » de `AUDIT_27_OUTILS`
  à plus fort « je paie » promoteur. Les 16 outils restent tous ouvrables (aucune perte). Les
  INTITULÉS d'origine sont conservés (déjà clairs — le jargon était le CODE et les descriptions
  sèches, tous deux corrigés) : bénéfice côté description, pas côté titre.
- **P4 — UN SEUL oiseau (3ᵉ passage, chirurgical)** : l'oiseau du RAIL est SUPPRIMÉ ; le combo
  oiseau + « LABUSE » reste dans le header (ce que Vic veut). Le doublon venait de l'oiseau du rail
  (haut-gauche) et de celui du header (à sa droite) qui se retrouvaient CÔTE À CÔTE. Le rail est
  désormais pur icônes de navigation. QA (`qa_revue3` + `qa_correctifs`) : `header svg[240 82] = 1`,
  `nav svg[240 82] = 0` — prouvé aussi panneau replié + vue Outils (captures jointes).
- **P5 — badge « J-2 » retiré → entrée « Sources » claire**. ⚠ SIGNALEMENT à Vic : le « J-2 »
  n'était PAS un reste de debug — il portait la FRAÎCHEUR des données (exigence #9), lien vers la
  page Sources. Fonction PRÉSERVÉE sous un libellé explicite (icône « base » + « Sources » en bas
  du rail) au lieu du code cryptique. Le title garde « Fraîcheur des données » ; QA : plus de
  « J-2 » à l'écran, « Sources » ouvre bien la page.
- **QA maintenue** : `qa_revue3.mjs` (2 portes + entretien enrichi + outils sans code/phares +
  1 oiseau + no J-2). Assertions périmées mises à jour : `qa_correctifs` (C2/R3→P4 « 1 oiseau »,
  C4→P2 « son avis retient »), `qa.mjs` (M01→intitulé métier), et le hook `openModule` de
  `qa_modules/qa_moteurs/qa_audit27/qa_missions_sp/qa_partners` (`text=M## · MODULE` → `aside h2`
  par intitulé, l'en-tête ne portant plus le code).
