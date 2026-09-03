# COMPTE-RENDU RETOURS-11 — SESSION A (branche `fix/retours-11a`)

Lots **T** (règles transversales), **C** (carte & couches), **A** (Copilote, notifications, compte, veille, sources).
Base : `main` (e0d423ca, scoring-3 inclus). Étape 0 : arbre remis propre sur `main` (le worktree portait un doublon staging de scoring-3, déjà committé sur `feat/scoring-3` et dans `main` — écarté sans perte, autorisé par Vic).

Statut par ID : **FAIT** / **FAIT AUTREMENT** (pourquoi) / **NON FAIT** (pourquoi) / **DÉCISION VIC** (question précise).

---

## LOT T — Règles transversales

| ID | Statut | Détail |
|---|---|---|
| T1 | **FAIT** | Les classes réutilisables `.hover-fill` / `.hover-fill-ia` / `.hover-fill-amber` existaient déjà (RETOURS-4). Appliquées aux surfaces manquantes : cases + lien + bouton de l'annuaire PLU, lignes d'acquisitions (Communes), suggestions Scan patrimoine, lignes tables O6 (blocB), lignes Densifier, items des menus « + CRM » (vert) et « + Projet » (ambre). Utilitaire unique, pas de CSS local. |
| T2 | **FAIT AUTREMENT** | Comportement de survol inversé selon la décision 03/09 : la tuile passe en FOND SOMBRE, glyphe + contour VERTS (mauve sur l'IA) — appliqué à l'accueil (`.acc-tile`) et aux en-têtes de section de la fiche (`.t-ico`). Composant unique `IconTile` + classe `.itile` créés et prêts ; le câblage sur les tuiles d'outils/Copilote se fait en A1 (Copilote) pour éviter les copies. |
| T3 | **FAIT** | (a) bouton opaque tant que le menu est ouvert (`act-cmp` / `act-amber-on`) ; (b) items du menu en survol plein vert (CRM) / ambre (Projet) ; (c) fermeture au clic ailleurs + Échap (mousedown + keydown, borné à `open`). |
| T4 | **FAIT** (1 sous-item reporté) | Modèle « Voir plus — N / M chargés » par 200 câblé : Scan patrimoine « possède » (M02, vraie pagination serveur limit/offset — l'endpoint `/patrimoine` la supporte déjà, GB-018), Permis (300→200), Point mort (1000→200), Densifier (400→200, `RENOUV_PAGE`). M22/simulPlu l'utilisaient déjà. **Reporté** : « Acquisitions récentes » (50/773) — l'endpoint `/communes/{c}/acquisitions-pm` est codé en dur `limit=50` SANS `offset` ; brancher un bouton donnerait un « Voir plus » sans page à charger. Nécessite une passe backend (param `offset`) → à faire en **O16** (session C, qui possède déjà cet outil). Notifications et Veille : traités en A5/A7. |
| T5 | **FAIT** | 4 boutons d'action/bascule passés de `rounded-full` à `rounded-ctl` (LeftPanel : Retour, algo, scoring ; ProjetKanban : filtre tier). Chips d'état, badges, points, cercles « i », pastilles de commune : gardés ronds (DA). Les pilules « Toutes 64 » / « Filtrer par thème » sont dans Sources → traitées avec A8. |
| T6 | **FAIT** | Cause trouvée : la pastille de carte élidait l'article de TOUTES les communes (`MapView` : `replace(/^(Les\|Le\|La\|L')/)`). Référentiel unique `lib/communes.ts` : `communePastille` garde l'article pour Le Port / Le Tampon / La Possession, l'élide pour les 21 autres (inchangé) ; `trierCommunes`/`communeSortKey` trient sans article (« Le Port » → P). `MU_COMMUNES` (moteurs, doublon codé en dur) dérivé de `CP_COMMUNES` ; tris des listes commune (Veille, Radar) passés au tri sans article. Test `communes.test.ts` (5). |
| T7 | **FAIT** | Pastilles de commune uniformes sur toutes les couches/fonds : fond vert `#0E7A43` (blanc lisible, contraste ~4,8), liseré noir, nom blanc. Le hot (opinion) garde une lueur menthe. |
| T8 | **FAIT** | Police et padding des pastilles +20 % (`size*1.2`, padding `2.4px 10.8px`). |
| T9 | **FAIT** | (a) `title` du bouton « Synthèse IA » retiré (Fiche) ; (b) entrée `veille` retirée de `RAIL_TITLE` (Rail). Rien d'autre touché. |

## LOT C — Carte et couches

| ID | Statut | Détail |
|---|---|---|
| C1 | **FAIT** (🔴 corrigé + test) | Cause EXACTE trouvée : régression SECTEUR-2 (`07d16986`, « PLU brut → sous-option »). `parcels-fill` (porteur de l'aplat par famille) n'était visible que si `layers.parcelles` était coché — donc « Zonage PLU par parcelle » SANS « Limites parcelles » = lettres sans aplat, légende vide. Fix : `parcels-fill`/`ile-fill` visibles dès que `layers.parcelles OU zonageFill` ; le flag de légende `peint.zonage` ne dépend plus de `layers.parcelles`. Test `zonage-regression.test.ts` (4) : garde les 3 calques (fill/line/symbol) + entrées couleur de légende. |
| C2 | **FAIT** (audit) | Décompte réel : **38 calques actifs** (pas 22 — Vic sous-comptait), inventoriés (voir audit ci-dessous). Contrôle lettres PLU : `parcel_zone_plu` couvre 427 419/431 663 parcelles, `zone_lib` non nul partout ; échantillon 4 communes cohérent (Nerl→N, AU1st→AU, A→A, Npnr→N, Uavap→U) ; carte ET fiche lisent la MÊME table dérivée (cohérence structurelle) ; ~1 % (4 225) de codes `zone_lib` dont la lettre ne colle pas à `zone_fam` = codes spéciaux, à surveiller. **(g) équipements OSM/BPE sortis de « Risques et protections »** → famille « Équipements ». Millésime « édition non enregistrée » : documenté, à relier au catalogue sentinelle (report — cf. audit). |
| C3 | **FAIT** (diagnostic mesuré + honnêteté) ; unification **reportée** | Diagnostic MESURÉ (pas deviné) : 988 mutations VEFA/36 mois, mais **seules 315 (32 %) portent `surface_reelle_bati`** — le filtre `bati>0` élimine 68 %, exactement l'hypothèse Vic (à l'acte VEFA le bâti n'existe pas). **MAIS** DVF au 974 (tel qu'ingéré) NE porte AUCUNE surface Carrez/lot (vérifié : colonnes = `surface_reelle_bati`, `surface_terrain` seules) → impossible de récupérer le prix des 673 restantes sans l'inventer. Fix livré : hachure HONNÊTE — le moteur expose le volume RÉEL (`n_total`) ; ex. 97418 (Sainte-Marie) passe de « moins de 10 ventes (5) » à « 27 ventes VEFA · prix calculable sur 5 (surface bâtie souvent absente à l'acte) ». **Moteur unique reporté** : cause des « 3 chiffres » identifiée — carte+fiche lisent le LIVE `neuf_vefa_commune` (Saint-Paul = 5003), table Communes + Évolution lisent la table PRÉCALCULÉE `dvf_prix_sortie_neuf` (= 4730). Unifier = router `build_prix_neuf`/comparateur/carnet sur `neuf_vefa_commune` — passe backend à part, désignée mais non faite (risque de régression hors périmètre carte). |
| C4 | **NON FAIT** (reporté) | Lisibilité sur Ortho/Plan (casing des traits, aplats plus opaques, halo des lettres via `styleFor(basemap)`). Le mode Clair porte déjà un casing (M105-B) mais pas le fond Ortho. Non traité faute de budget dans cette session ; demande une passe dédiée sur `MapView.applyClairMode` + variantes par fond, avec captures témoin Sombre inchangé. |
| C5 | **FAIT** | Décision 03/09 (REMPLACE 31/08) appliquée : `zonage` (GPU brut) redevient une couche de PREMIER NIVEAU, libellée « Limites officielles PLU (GPU brut) », dans la famille « Les zonages », bascule indépendante (sous-option + couplage retirés). Légende dédiée ajoutée. |
| C6 | **NON FAIT** (reporté) | Audit GetCapabilities Géoplateforme (Plan v2 / Ortho courante / millésimes historiques présents à La Réunion). Nécessite des appels réseau live à la Géoplateforme + audit de `basemaps.ts` — non réalisé dans cette session (hors budget), à faire en passe dédiée. |
| C7 | **FAIT AUTREMENT** | Audit des outils de dessin (règle/distance, surface/polygone, altitude) : chacun produit sa mesure, état vide et Échap OK ; double-clic déjà neutralisé. L'édition de points par glisser reste à implémenter (cf. C8). Pas de bug bloquant trouvé de bout en bout. |
| C8 | **FAIT** (édition points reportée) | Déjà en place (ZONE-RECETTE) : Entrée valide (≥ 3 points) pour la zone, Échap annule, double-clic NEUTRALISÉ (ne valide plus). Libellé mis au texte EXACT du mandat : « Cliquez pour placer les points · Entrée pour valider · Échap pour annuler ». Le glisser-déplacer des points (édition) reste un vrai chantier (débounce click/dblclick + poignées) — commenté, reporté. |
| C9 | **FAIT** | « Remonter le temps » : l'étiquette IDU se pose désormais AU-DESSUS DU CONTOUR (ancre = centroïde en X, latitude MAX de la géométrie en Y, ancrée par le bas), plus jamais sur la parcelle. |

## LOT A — Copilote, notifications, compte, veille, sources

| ID | Statut | Détail |
|---|---|---|
| A1 | … | Accueil Copilote 3 niveaux |
| A2 | … | « Reprendre » → « Mémoire » |
| A3 | … | Boîtes de conversations (trait mauve) |
| A4 | … | Signaler global (type en base + filtre + compteur) |
| A5 | … | Notifications (audit + refonte) |
| A6 | … | Mon compte |
| A7 | … | Veille (ergonomie) |
| A8 | … | Sources client (retirer 3e colonne) |

---

## Audits détaillés (faux / retiré / ajouté / fusionné)

### C2 — Audit des couches (le vrai décompte : 38, pas 22)

Registre des calques : `MapView.tsx` (init, ~lignes 620-900). 38 calques actifs (fill/line/symbol/circle), regroupés dans le panneau « Couches » (`LeftPanel.tsx`) en familles.

**Familles (après RETOURS-11) :** Le fond (parcelles, limites, communes) · **Les zonages** (zonage par parcelle calibré, **+ Limites officielles PLU (GPU brut) — remonté en 1er niveau, C5**) · Risques et protections (PPR, aléa inondation, aléa mvt, parc national, ZNIEFF, 50 pas) · **Équipements (OSM, INSEE BPE) — SORTIS de « Risques », C2-g** · Accès et réseaux (transport GTFS, axes BD TOPO, lignes HT) · Dispositifs et périmètres (QPV, TVA primo, NPNRU/ANRU, ZFANG, FRR) · Le marché (VEFA neuf).

**Vérifs nommées :**
- **Lettres PLU** : `parcel_zone_plu` (427 419 lignes, `zone_lib` non nul partout) sert À LA FOIS la carte (symbole `parcels-zone-label`) et la fiche → cohérence par construction ; échantillon 4 communes coherent ; 1 % de codes atypiques signalés.
- **Équipements OSM** : rangés à tort sous « Risques » → déplacés (C2-g). La date d'extraction OSM reste à afficher (report).
- **« édition non enregistrée »** : certains millésimes de couche ne sont pas résolus depuis le catalogue sentinelle → à relier (report, non bloquant).
- PPR/aléas, QPV 2024, ZFANG/FRR, transport GTFS, VEFA : sources et calques présents (cf. registre). Le millésime-par-couche lu du catalogue = chantier commun avec la sentinelle (report).

### C3 — Couche VEFA : diagnostic MESURÉ (base réelle, 36 mois)

| Étape (filtre) | Mutations VEFA restantes |
|---|---|
| Brutes (distinct `id_mutation`, 36 mois) | **988** |
| Après `bati>0` (surface réelle bâtie sommée par mutation) | **315** (−68 %) |
| Après bande de prix (`valeur>1000`, 50 ≤ €/m² ≤ 20 000) | **309** |

**Le tueur = la surface** (comme pressenti). Mais DVF au 974 (`dvf_mutations_parcelle`) ne porte QUE `surface_reelle_bati` / `surface_terrain` — **aucune surface Carrez/lot** (vérifié sur tout le schéma) → les 673 mutations sans surface ne sont PAS récupérables (pas de prix inventé). Exemples communes (insee | VEFA | à prix) : 97411 | 318 | 112 · 97415 (St-Paul) | 194 | 80 · **97418 (Ste-Marie) | 27 | 5** · 97402 | 1 | 1.

**Retiré (mensonge)** : la hachure « moins de 10 ventes (5) » pour une commune à 27 ventes VEFA. **Ajouté** : `n_total` au moteur `neuf_vefa_commune` + libellé honnête « 27 ventes VEFA · prix calculable sur 5 (surface bâtie souvent absente à l'acte) ».
**« Trois chiffres pour un fait » (Saint-Paul)** : carte + fiche = LIVE `neuf_vefa_commune` → **5003** ; table Communes (`comparateur.py`) + Évolution (`carnet.py`) = table PRÉCALCULÉE `dvf_prix_sortie_neuf` → **4730**. Un seul moteur = router ces call-sites sur `neuf_vefa_commune` : désigné, **reporté** (passe backend hors périmètre carte de cette session).

---

## Clôture

- tsc : …
- build : …
- vitest : …
- pytest : …
- golden (119/119, aucun fichier scoring touché) : …
- captures avant/après : `docs/audit-2026-09/retours-11/captures/` …
