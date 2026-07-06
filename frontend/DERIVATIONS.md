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
