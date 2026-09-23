# RAPPORT DA-AUDIT-1 — audit de cohérence DA de toute l'app

**Branche** `audit/da-1` · worktree `~/Desktop/labuse-da` · **lecture seule** (aucune écriture dans `src/`).
**App auditée** front `:5325` → API `:8125` (`LABUSE_API_DEV`), navigateur réel cadré à 1440 px.
**Référentiel** `CHARTE-DA-1.md` (v1, validée Vic 23/09/2026). On audite CONTRE la charte.
**Méthode** — la capture fait foi pour la grille (A) et les écarts (B) ; le code fait foi pour l'inventaire (C) et le décompte des rayons (D). Captures dans `captures/`. Les greps de C portent sur **tout `frontend/src`** (147 `.tsx`), pas sur `primitives.tsx` seul.

---

## D. Cinq chiffres en tête

| # | Chiffre | Valeur |
|---|---------|--------|
| 1 | **Écrans audités** | **34** (17 outils + accueil, menu Outils, fiche parcelle, fiche commune, panneaux Couches / Filtres / Analyse, contrôles carte, Radar, Veille, cloche, Projets, CRM, Copilote, Compte, menu latéral) |
| 2 | **Écarts au total** | **42** (DA-001 → DA-042) |
| 3 | **Les 5 règles les plus violées** | Règle 4 *entrée d'outil* : **10** · Règle 3 *retour* : **6** · Règle 5 *filtres/tris/cases* : **5** · Règle 1 *couleurs d'état* : **5** · Règle 2 *boutons* : **5** (Règle 7 : 4) |
| 4 | **Familles de composants à ≥ 2 variantes** | **11 sur 14** (bouton, chip, case, tri, retour, omnibox, badge, accordéon/chevron, état-vide, état-erreur, état-chargement ; conformes : scrollbar, ligne de liste, carte cliquable) |
| 5 | **Rayons distincts dans le CSS** | **16** valeurs, pour **3** autorisées (4 / 6 / 999). Détail ci-dessous. |

### Rayons — valeur → occurrences (grep exhaustif CSS + Tailwind + inline)

| Rayon | Occ. (ordre de grandeur) | Où | Charte |
|------:|---:|----|:---:|
| **8 px** | ~375 | `rounded-lg` (355×), token `--r-sm` (`.field/.ico`), `.seg` interne, inline `borderRadius:8` (btnPlein Projets/Financier) | ✗ |
| **6 px** | ~175 | `rounded-md` (165×), `.chip`, `.sk`, `.hover-jaune`, inline `borderRadius:6` | ✓ |
| **9999 px** | ~175 | `rounded-full` (168×), inline `borderRadius:999` | ✓ |
| **4 px** | ~108 | `rounded` (105×), `.b` badge, scrollbar-thumb, `:focus-visible` | ✓ |
| **12 px** | ~80 | `rounded-xl` (60×), token `--r-card`, `.tiroir/.exports/.head` fiche, inline `borderRadius:12` | ✗ |
| **10 px** | ~11 | token `--r-ctl` / `rounded-ctl` (`.btn/.cta/.act`, `.seg`, `.tab`, `.porte-outil`) | ✗ |
| **9 px** | ~8 | `.acc-tile`, `.itile`, `.ia-btn`, `.t-ico`, inline | ✗ |
| **20 px** | ~8 | token `--r-pill` (`.pill/.tag/.pill-mint/-amber/-neutre`) — **la « pilule » LABUSE est 20 px, pas 999** | ✗ |
| **16 px** | ~5 | `rounded-2xl` (3×), `rounded-t-2xl`, `rounded-r-xl` | ✗ |
| **2 px** | ~14 | `rounded-sm` (10×), `::highlight(fiche-search)`, `.reglette` | ✗ |
| **11 px** | ~4 | token `--r-g`, `.head` fiche | ✗ |
| **3 px** | ~5 | `.bar`, inline barres de progression | ✗ |
| **5 px** | ~3 | `.cbx`, `span` repli synthèse | ✗ |
| **7 px** | ~3 | `.hbtn`, bouton Replier synthèse | ✗ |
| **13 px** | ~2 | `data-analyse-labuse-card`, `data-verdict-card` (Fiche) | ✗ |
| **50 %** | ~2 | `.dot`, `.f-status > .dot` | ✗ (pastille ronde) |

> Tokens (`styles/index.css:36`) : `--r-card:12 · --r-g:11 · --r-ctl:10 · --r-sm:8 · --r-pill:20`. Override Tailwind (`tailwind.config.js:100`) : `g:11 · ctl:10 · pill:20`. Les rayons Tailwind par défaut restent actifs (`rounded=4 · sm=2 · md=6 · lg=8 · xl=12 · 2xl=16 · full=9999`). **Seuls 4/6/9999 sont dans la charte ; les 13 autres valeurs sont hors charte, et le token « pilule » lui-même (20 px) n'est pas 999.**

---

## A. Grille écran × règle

**Légende cellules** : ✓ conforme · ✗ écart (→ DA-xxx) · — sans objet.
**Colonnes** (sous-règles de la charte, 1.1 → 8.2) :

| Code | Règle |
|------|-------|
| 1.1 | Actif = vert opaque, contenu inversé |
| 1.2 | Survol = opaque de sa couleur |
| 1.3 | Pas de bleu (SIREN excepté) |
| 1.4 | Désactivé = 40 % + curseur not-allowed (valeur unique) |
| 1.5 | Focus clavier = rendu du survol (pas d'anneau) |
| 2.1 | 3 niveaux de bouton, 1 primaire/écran max |
| 2.2 | Aucun mot cliquable sans contour ni soulignement |
| 2.3 | Hauteur 32 px (omnibox 40), padding/police uniformes |
| 2.4 | 3 rayons dans toute l'app, pas un de plus |
| 2.5 | Aucun CSV ; aucune entrée IA hors fiche/Copilote |
| 3.1 | `RetourOutil` unique, toujours au même endroit |
| 3.2 | Libellé conforme (jamais « Retour » nu ni croix pour reculer) |
| 3.3 | Échap = recule d'une étape (ne ferme pas) |
| 4.1 | Entrée = omnibox + clic carte (ou commune + dessin) |
| 4.2 | Omnibox permanente quand l'outil a un résultat |
| 5.1 | chip / case / tri = un seul composant chacun |
| 5.2 | « Tout/Tous » toujours dernier |
| 5.3 | Pagination `ListPagination` + pastille de filtre actif |
| 5.4 | Tri par défaut ≠ surface |
| 6.1 | Aucune barre horizontale ; scrollbar unique |
| 6.2 | Accordéon ▶/▼, chevron actif vert opaque |
| 6.3 | Une seule apparition (150 ms) ; survol 100 ms |
| 7.1 | Aucune infobulle au survol hors contrôles carte |
| 7.2 | Badge unique ; score seulement si analyse demandée |
| 7.3 | Table d'un panneau outil = cartes empilées |
| 8.1 | Vide/erreur/chargement = un composant chacun (squelette) |
| 8.2 | Un échec technique ne se déguise pas en absence |

### A.1 Surfaces transverses (header, carte, menu latéral, panneaux)

| Écran / étape | 1.1 | 1.2 | 1.3 | 1.4 | 1.5 | 2.1 | 2.2 | 2.3 | 2.4 | 2.5 | 3.x | 4.x | 5.1 | 5.2 | 5.3 | 5.4 | 6.1 | 6.2 | 6.3 | 7.1 | 7.2 | 7.3 | 8.1 | 8.2 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Accueil (menu latéral « Cartes ») | ✓ | ✓ | ✓ | ✗ 17 | ✗ 19 | ✓ | ✓ | ✗ 23 | ✗ 24 | ✓ | — | — | — | — | — | — | ✓ | — | ✗ 32 | ✓ | — | — | ✗ 36 | — |
| Barre / omnibox header (+ restitution recherche) | ✓ | ✓ | ✗ 39 | — | ✗ 19 | ✓ | ✓ | ✗ 23 | ✗ 24 | ✗ 40 | — | ✗ 01 | — | — | — | — | ✓ | — | ✗ 33 | ✗ 41 | — | — | ✗ 36 | ✓ |
| Contrôles carte (fond, mesures, légende) | ✓ | ✓ | ✗ 39 | — | ✗ 19 | ✓ | ✓ | ✗ 23 | ✗ 24 | ✓ | — | — | — | — | — | — | ✓ | ✗ 31 | ✗ 33 | ✓ (autorisé) | — | — | ✗ 36 | ✓ |
| Panneau **Couches** | ✓ | ✓ | ✓ | ✗ 17 | ✗ 19 | ✓ | ✓ | ✗ 23 | ✗ 24 | ✓ | — | — | ✗ 25 | — | — | — | ✓ | ✗ 31 | ✗ 33 | ✓ | — | — | ✗ 36 | ✓ |
| Panneau **Filtres** | ✓ | ✓ | ✓ | ✗ 17 | ✗ 19 | ✗ 21 | ✓ | ✗ 23 | ✗ 24 | ✓ | — | — | ✗ 25/26 | ✓ | ✓ | ✓ | ✓ | ✗ 31 | ✗ 33 | ✓ | ✓ | — | ✗ 36 | ✓ |
| Panneau **Analyse** (bandes LABUSE) | ✓ | ✓ | ✓ | — | ✗ 19 | ✓ | ✓ | ✗ 23 | ✗ 24 | ✓ | — | — | — | — | — | — | ✓ | — | ✗ 32 | ✓ | ✓ | — | ✗ 36 | ✓ |
| Menu latéral (rail) | ✓ | ✓ | ✓ | — | ✗ 19 | ✓ | ✓ | ✗ 23 | ✗ 24 | ⚠ 20 | — | — | — | — | — | — | ✓ | — | ✗ 33 | ✓ | — | — | — | — |

### A.2 Les 17 outils — en-tête commun + entrée + résultat

L'**en-tête de panneau est commun** à tous les outils (`ModulePanel.tsx`) : fil « ← Outils » (haut-gauche) **+** croix ✕ « Fermer le module » (haut-droite) ; Échap ferme. → cellules 3.1/3.2/3.3 identiques partout (✗ 11 / ✗ 15 / ✗ 12). Colonnes ci-dessous = **4.1** (entrée) · **4.2** (omnibox permanente) · **3.2** (retour d'étape interne) · **5.1** (chip/case/tri) · **6.2** (accordéon) · **8.1** (états).

| # | Outil | Entrée réelle | 4.1 | 4.2 | 3.2 | 5.1 | 6.2 | 8.1 |
|---|-------|---------------|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 | PLU | hub 2 portes → Annuaire / Procédure | ✗ 09 | ✓ | ✗ 15 | ✗ 25 | ✗ 31 | ✗ 36 |
| 2 | Permis | barre unique + `<select>` commune | ✗ 08 | ✓ | — | ✗ 26 | ✗ 31 | ✗ 37 |
| 3 | Communes | hub 4 portes → `<select>` / table | ✗ 08 | — | ✗ 15 | ✗ 27 | ✗ 31 | ✗ 37 |
| 4 | Faisabilité | onglets, défaut **Par critères** | ✗ 05 | ✓ | ✗ 16 | ✗ 26 | — | ✗ 37 |
| 5 | Scan patrimoine | recherche seule | ✗ 02 | ✗ 03 | ✗ 16 | ✗ 26 | ✗ 31 | ✗ 37 |
| 6 | Assemblage | omnibox + clic carte | ✓ | ✓ | — | ✗ 26 | — | ✗ 37 |
| 7 | Comparer | stepper omnibox + clic carte | ✓ | ✓ | — | ✗ 25 | — | ✗ 37 |
| 8 | Pièges et risques | omnibox (clic capté, sans bouton) | ✗ 09 | ✓ | — | — | ✗ 31 | ✗ 37 |
| 9 | Étude de zone | 2 portes → point / dessin | ✓ | ✓ | ✗ 15 | ✗ 26 | ✗ 31 | ✗ 37 |
| 10 | Remonter le temps | omnibox → bandeau idu étape 2 | ✗ 02 | ✗ 04 | ✗ 14 | — | — | ✗ 37 |
| 11 | Faisabilité *(cf. 4)* | — | — | — | — | — | — | — |
| — | Gabarit | omnibox + clic carte (par texte) | ✗ 02 | ✓ | — | — | ✗ 31 | ✗ 37 |
| 12 | Taxe d'aménagement | omnibox + clic carte (par texte) | ✗ 02 | ✓ | — | ✗ 26 | ✗ 31 | ✗ 37 |
| 13 | Prospection solaire | choix de mode (Piscines/Ensoleillt) | ✗ 07 | ✓ | ✗ 15 | — | — | ✗ 38 |
| 14 | Densifier l'existant | omnibox lookup + table île | ✗ 06 | ✓ | ✗ 16 | ✗ 26 | ✗ 31 | ✗ 37 |
| 15 | Blocs fonciers | `<select>` commune + filtres | ✗ 08 | ✓ | — | ✗ 26 | ✗ 31 | ✗ 37 |
| 16 | Successions à venir | `<select>` commune + filtres | ✗ 08 | ✓ | — | ✗ 26 | ✗ 31 | ✗ 37 |
| 17 | Courrier propriétaire | liste destinataires (ponts) | ✗ 10 | — | ✗ 13 | ✗ 26 | — | ✗ 37 |

> Les colonnes 1.x / 2.x / 7.x des outils suivent les surfaces transverses (mêmes composants) : désactivé multi-opacité ✗ 17, focus ✗ 19, rayons ✗ 24, hauteurs ✗ 23. Badge de score : conforme (présent seulement après « Demander à LABUSE »).

### A.3 Fiches et surfaces produit

| Écran / étape | 1.1 | 1.2 | 1.3 | 1.4 | 1.5 | 2.1 | 2.2 | 2.3 | 2.4 | 3.x | 4.2 | 5.1 | 5.2 | 5.4 | 6.1 | 6.2 | 6.3 | 7.1 | 7.2 | 7.3 | 8.1 | 8.2 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **Fiche parcelle** | ✓ | ✓ | ✓ | ✗ 17 | ✗ 19 | ✓ | ✓ | ✗ 23 | ✗ 24 | ✓ | ✓ | — | — | — | ✓ | ✗ 31 | ✗ 32 | ✓ | ✓ | — | ✗ 36 | ✓ |
| **Fiche commune** | ✓ | ✓ | ✓ | — | ✗ 19 | ✓ | ✓ | ✗ 23 | ✗ 24 | ✓ | ✓ | — | — | — | ✓ | ✗ 31 | ✗ 32 | ✓ | ✓ | — | ✗ 36 | ✓ |
| **Radar** (biens en vente) | ✓ | ✓ | ✓ | — | ✗ 19 | ✓ | ✓ | ✗ 23 | ✗ 24 | — | — | ✗ 25 | ✓ | ✓ | ✗ 30 | — | ✗ 33 | ✓ | ✗ 34 | ✗ 42 | ✗ 37 | ✓ |
| **Veille** | ✓ | ✓ | ✓ | — | ✗ 19 | ✓ | ✓ | ✗ 23 | ✗ 24 | — | — | ✗ 26 | — | — | ✓ | ✗ 31 | ✗ 33 | ✓ | — | — | ✗ 37 | ✓ |
| **Cloche** (notifications) | ✓ | ✓ | ✓ | — | ✗ 19 | ✓ | ✓ | ✗ 23 | ✗ 24 | — | — | ✗ 25 | ✓ | — | ✓ | — | ✗ 33 | ✓ | — | — | ✗ 37 | ✓ |
| **Projets** | ✓ | ✓ | ✓ | ✗ 17 | ✗ 19 | ✓ | ✓ | ✗ 23 | ✗ 24 | — | — | ✗ 25 | — | — | ✓ | ✗ 31 | ✗ 33 | ✓ | — | — | ✗ 37 | ✓ |
| **CRM** (kanban) | ✓ | ✓ | ✓ | ✗ 17 | ✗ 19 | ✓ | ✗ 22 | ✗ 23 | ✗ 24 | — | — | ✗ 26 | — | — | ✓ | ✗ 31 | ✗ 33 | ✓ | — | — | ✗ 37 | ✓ |
| **Copilote** | ⚠ 20 | ✓ | ✓ | ✗ 17 | ✗ 19 | ⚠ 20 | ✓ | ✗ 23 | ✗ 24 | — | — | ✗ 25 | — | — | ✓ | — | ✗ 33 | ✓ | — | — | ✗ 37 | ✓ |
| **Compte** (menu) | ✓ | ✓ | ✓ | — | ✗ 19 | ✓ | ✓ | ✗ 23 | ✗ 24 | — | — | — | — | — | ✓ | — | ✗ 33 | ✓ | — | — | — | ✓ |

---

## B. Registre des écarts

Format : `DA-xxx` · écran · règle · constat (une phrase) · `fichier:ligne` · capture.

| DA | Écran | Règle | Constat | fichier:ligne | Capture |
|----|-------|:-----:|---------|---------------|---------|
| **DA-001** | Header vs outils | 4.1 | Deux omnibox aux rendus différents : header `bg-transparent` sans bordure vs outil `rounded-lg border bg-surface-3` — pas le « même rendu ». | `components/header/Header.tsx` (input `data-omnibox`), `components/ParcelInput.tsx:26` | `00-accueil`, `03b-faisabilite-parparcelle` |
| **DA-002** | Gabarit, Taxe, Pièges, Scan | 4.1 | Le geste « clic carte » est offert différemment selon l'outil : bouton `withCarte` (Assemblage/Zone) vs simple phrase texte `withCarte={false}` (Gabarit/Taxe/Pièges) — trois rendus pour un même geste. | `outils/Gabarit.tsx:170,173` · `outils/TaxeAmenagement.tsx:151,153` · `outils/blocB.tsx:53` | `03b` |
| **DA-003** | Scan patrimoine | 4.2 | L'omnibox disparaît une fois le propriétaire trouvé (encart + « changer »), au lieu de rester en tête. | `outils/ScanPatrimoine.tsx:162-172` | `01-outils-menu` |
| **DA-004** | Remonter le temps | 4.2 | L'omnibox est remplacée par un bandeau `idu` + « changer » à l'étape 2. | `outils/ModulePanel.tsx:1180-1183` | `01-outils-menu` |
| **DA-005** | Faisabilité | 4.1 | Outil parcelle qui s'ouvre par défaut sur « Par critères » (formulaire commune) ; l'omnibox parcelle est cachée derrière l'onglet « Par parcelle ». | `outils/M22Programme.tsx:27,136,253` | `03-faisabilite-criteres`, `03b` |
| **DA-006** | Densifier l'existant | 4.1 | Outil parcelle sans aucun geste « clic carte » — seulement l'omnibox de lookup. | `outils/Renouvellement.tsx:75` | `01-outils-menu` |
| **DA-007** | Prospection solaire | 4.1 | Ne s'ouvre pas sur une entrée parcelle mais sur un choix de mode ; le sous-mode Piscines n'offre qu'un `<select>` commune. | `outils/ProspectionSolaire.tsx:52,168,323` | `01-outils-menu` |
| **DA-008** | Communes, Permis, Blocs, Successions | 4.1 | Outils commune/zone sans « ou dessinez sur la carte » (seul Étude de zone l'offre). | `outils/Blocs.tsx:176` · `outils/Successions.tsx:89` · `outils/ModulePanel.tsx:527` | `15-communes-hub` |
| **DA-009** | PLU (par parcelle), Pièges | 4.1 | Omnibox sans clic-carte proposé (`withCarte={false}`), sans phrase de repli. | `outils/VerifProcedure.tsx:29` · `outils/blocB.tsx:53` | `02-plu-hub` |
| **DA-010** | Courrier propriétaire | 4.1 | Entrée = liste de destinataires amorcée par les ponts, pas l'omnibox parcelle standard. | `outils/ModulePanel.tsx:1299` | `01-outils-menu` |
| **DA-011** | Tous les outils | 3.1 | Pas de composant `RetourOutil` unique : retour-menu (« ← Outils »), retour-post-pont (`RetourOutil`) et retours d'étape internes sont trois mécanismes distincts, à trois emplacements. | `outils/ModulePanel.tsx:1832,1880,1897` | `02-plu-hub` |
| **DA-012** | Tous les outils | 3.3 | Échap **ferme** le panneau (`setModule(null)`) au lieu de reculer d'une étape. | `outils/ModulePanel.tsx:1853-1864` | `02-plu-hub` |
| **DA-013** | Courrier (étape 2→1) | 3.2 | Libellé « Retour » nu (interdit par la charte). | `outils/ModulePanel.tsx:1445` | `01-outils-menu` |
| **DA-014** | Remonter le temps (étape 2) | 3.2 | « ✕ Quitter » = croix qui **ferme** le panneau depuis l'étape 2 au lieu de reculer à l'étape 1. | `outils/ModulePanel.tsx:1216-1217` | `01-outils-menu` |
| **DA-015** | Communes, PLU, Solaire, Courrier | 3.2 | Glyphe de retour incohérent : `←` (partagé) vs `‹` (tous les retours d'étape internes). | `outils/Communes.tsx:247` · `outils/Plu.tsx:52` · `outils/PluAnnuaire.tsx:109,163,243` · `outils/ProspectionSolaire.tsx:80,168` | `15b-communes-comparaison` |
| **DA-016** | Faisabilité, Scan, Temps, Densifier | 3.2 | Retours d'étape non standardisés : boutons « changer » sans flèche/libellé conforme, `BackBar` local, placements variables. | `outils/M22Programme.tsx:258` · `outils/ScanPatrimoine.tsx:171` · `outils/ProspectionSolaire.tsx:76` | `01-outils-menu` |
| **DA-017** | Toute l'app | 1.4 | Désactivé rendu avec **5 valeurs d'opacité** (`disabled:opacity-40` 39×, `-50` 8×, `-60` 7×, `-30` 5×, `-25` 5×) au lieu d'une seule valeur 40 %. | grep `disabled:opacity-*` (tsx) | `04-fiche-parcelle` (bouton « ✓ Dans le CRM » désactivé) |
| **DA-018** | Toute l'app | 1.4 | Curseur `not-allowed` quasi jamais posé sur les désactivés (2 fichiers seulement). | `components/shared/GrilleOutils.tsx` · `fiche/FinancierQuestionnaire.tsx` | `04-fiche-parcelle` |
| **DA-019** | Toute l'app | 1.5 | Focus clavier = anneau vert 2 px (`outline`), pas le rendu du survol. | `styles/index.css:354` | `00-accueil` |
| **DA-020** | Copilote | 1.1 / 2.1 | Surface IA en mauve : bouton primaire « Envoyer » mauve et rail actif « Copilote » mauve (et non vert). Cohérent avec l'exception IA de la charte 1, **mais** rien dans la charte ne dit qu'un onglet actif IA passe au mauve — à trancher (⚠). | `components/copilote/*`, `styles/index.css:489` (`.ia-btn`) | `08-copilote` |
| **DA-021** | Panneau Filtres | 2.1 | Deux CTA verts co-égaux empilés en bas (« Voir les 431 663 parcelles » + « Analyser avec LABUSE ») — plus d'un primaire par écran. | `components/panel/FiltreLabuse.tsx` (bloc actions) | `06c-filtres-boutons`, `07-analyse` |
| **DA-022** | Projets, CRM, Financier | 2.1 / 2.2 | Boutons réimplémentés en styles inline (`btnPlein`, boutons `<div>`/`<span onClick>`) au lieu du composant/classe partagée. | `projets/ProjetsPanel.tsx:145` · `projets/ParcoursProjet.tsx:127` · `fiche/FinancierQuestionnaire.tsx:414` | `12-projets`, `13-crm` |
| **DA-023** | Toute l'app | 2.3 | Hauteurs de contrôle non uniformes : `h-7`(28), `h-8`(32), `h-9`(36), `h-10`(40), `height:34/30` mêlés. | grep hauteurs (tsx/css) | `06-filtres` |
| **DA-024** | Toute l'app | 2.4 | **16 rayons distincts** (2/3/4/5/6/7/8/9/10/11/12/13/16/20/50%/9999) pour 3 autorisés ; `rounded-lg`=8 px dominant (355×) ; token « pilule »=20 px et non 999. | `styles/index.css:36` · `tailwind.config.js:100` · grep `rounded-*` | tableau D |
| **DA-025** | Filtres, Radar, Cloche, Sources, Comparer | 5.1 | Deux composants `Chip` concurrents (filtre vs admin) + 2 pastilles chip inline. | `panel/FiltreLabuse.tsx:90` · `admin/AdminView.tsx:54` · `sources/SourcesPage.tsx:194` · `compare/ComparePanel.tsx:119` | `06-filtres` |
| **DA-026** | Multiples outils | 5.1 | Aucun composant « case à cocher » partagé : **18 `<input type=checkbox>` bruts** répétés. | `outils/Blocs.tsx:200,245,253` · `outils/Renouvellement.tsx:220,257` · `outils/Successions.tsx:122,133` · `outils/M22Programme.tsx:178,207` · `header/Header.tsx:483-491` … | `06-filtres` |
| **DA-027** | Listes triables | 5.1 | Deux systèmes de tri : en-tête `SORTS` (flèche ↓/↑) vs boutons de tri ad-hoc. | `panel/ResultsSection.tsx:171,652` · `outils/Renouvellement.tsx:200` | `15b-communes-comparaison` |
| **DA-028** | Courrier (admin) | 5.2 | « Tous » placé **en premier** au lieu de dernier à droite. | `admin/Courrier.tsx:97` | — |
| **DA-029** | Projets, Admin, Kanban | 5.3 | 4 paginations à la main hors `ListPagination`. | `projets/ProjetsPanel.tsx:193` · `admin/AdminView.tsx:157,160,200` · `admin/Produit.tsx:126` · `crm/Kanban.tsx:421` | `12-projets` |
| **DA-030** | Radar / Marché | 6.1 | Barre de défilement horizontale (`overflow-x-auto`) sur tableaux larges — interdite « nulle part ». | `outils/RadarMarche.tsx:60` · `outils/moteurs.tsx:567` | `09-radar` |
| **DA-031** | Partout (accordéons) | 6.2 | ≥ 6 systèmes de chevron distincts ; le chevron « fermé » pointe à **gauche** (◂ `rotate-90`) au lieu de ▶ ; couleurs grises, rarement vert opaque actif ; légende carte affiche ▾ dans les deux états. | `panel/ChevronSection.tsx:30-31` · `panel/FiltreLabuse.tsx:199` · `fiche/primitives.tsx:125` · `map/CouchesTuyau.tsx:548` … | `05-couches`, `06-filtres` |
| **DA-032** | Panneaux / tiroirs / cartes | 6.3 | L'unique animation d'apparition mandatée (fondu + 4 px, 150 ms) **n'existe pas** ; à la place, 3 pulsations d'attente distinctes (`labuse-load` scale, `labuse-sk`, `animate-pulse`). | `styles/index.css:373,380` · `Loading.tsx:26` | `07-analyse` |
| **DA-033** | Toute l'app | 6.3 | Durées de survol non conformes : 150 ms (`duration-quick`, ~250 usages), 120 ms, `.15s`, `.12s` au lieu de 100 ms ; `duration-soft` 200 ms hors charte. | `tailwind.config.js:104` · `styles/index.css:94-347` · `panel/ChevronSection.tsx:31` | — |
| **DA-034** | Fiche, Radar, Copilote, Sources, Destination | 7.2 | **7 composants badge distincts** (la charte en veut un) : `TierBadge`, `DestinationBadge`, `copilote.Badge`, `SourcesPage.Badge` (4 variantes), `EquipementsBadges`, `.b`/`StepProv` (primitives), `ProvBadge` — et `DestinationBadge` emploie **4 couleurs** (mint/amber/**corail**/neutre) au lieu de 3. | `outils/TierBadge.tsx:9` · `outils/DestinationSelect.tsx:44,38-42` · `copilote/ui.tsx:23,45` · `sources/SourcesPage.tsx:22` · `fiche/reseaux.tsx:26` · `fiche/primitives.tsx:365` · `compare/ComparePanel.tsx:60` | `04-fiche-parcelle`, `09-radar` |
| **DA-035** | Comparateur communes | 7.3 | Table à **9 colonnes** (`grid repeat(7)`) — dans l'overlay « en grand », donc hors panneau 320 px ; à confirmer si tolérée (cf. « Non couvert »). | `outils/Communes.tsx` (ligne `data-o6-row`) | `15b-communes-comparaison` |
| **DA-036** | Carte, header, boot | 8.1 | Le « chargement » de référence est un **spinner** (points animés `labuse-load`), doublé de 2 spinners rotatifs + un 4ᵉ loader `MapLoading`, au lieu d'un squelette. | `Loading.tsx:4` · `App.tsx:41,45` · `header/Header.tsx:201` | `00-accueil` (« Chargement de la carte… ») |
| **DA-037** | Radar, Veille, Projets, CRM, Copilote, outils | 8.1 | États vide/erreur réécrits écran par écran : `EmptyState` 3 usages vs ~25 vides ad-hoc ; `ErrorState` ~10 vs ~15 erreurs ad-hoc. | `States.tsx:18,38` · `crm/Kanban.tsx:607,688` · `outils/RadarView.tsx:554` · `projets/ProjetsPanel.tsx:245` … | `13-crm` (« glissez-en une ici ») |
| **DA-038** | Prospection solaire | 8.2 | Un échec technique (`f.ok=false`) rend « Aucune donnée solaire » — l'échec se déguise en absence de donnée. | `outils/ProspectionSolaire.tsx:373` | `01-outils-menu` |
| **DA-039** | Liste résultats, carte | 1.3 | **Bleu hors SIREN** : token `--blue:#8FB4F0` diffusé ; badge « même proprio ×N » bleu, état carte « à revérifier » bleu, marqueur police/gendarmerie et cercles BPE bleus. Le lien SIREN (bleu souligné) reste, lui, conforme. | `styles/index.css:29` · `lib/tokens.ts:25` · `panel/ResultsSection.tsx:106` · `map/MapView.tsx:708` · `lib/status.ts:278` · `lib/mapTheme.ts:156` | `00-accueil`, `04-fiche-parcelle` |
| **DA-040** | Panneau de recherche | 2.5 | Point d'entrée IA (bouton violet « Affiner la capacité dans M22 ») **hors fiche/Copilote**, dans la restitution de recherche. | `App.tsx:237` | `00-accueil` |
| **DA-041** | Recherche / projets | 7.1 | Infobulles natives `title=` (bulle navigateur au survol) sur des boutons hors contrôles carte. | `App.tsx:112,221,227,238` | `00-accueil` |
| **DA-042** | Radar/Marché, Densifier | 7.3 | Tables à **≥ 6 colonnes dans un panneau outil 320 px** (au lieu de cartes empilées) : RadarMarche ~10 `<th>`, Renouvellement 8-9 `<th>`. | `outils/RadarMarche.tsx:62-68` · `outils/Renouvellement.tsx:216-248` | `09-radar` |

> **Non-écarts confirmés (règle 2.5)** : aucun bouton CSV vivant (tous retirés — `ComparePanel.tsx:172`, `Renouvellement.tsx:139`, `ModulePanel.tsx:1006`) ; l'IA conversationnelle (`AskBar`/`AvisIA`) est bien cantonnée à la fiche et au Copilote. **Règle 7.1** : `Tip.tsx` ne rend aucune bulle au survol hors les 3 outils de mesure (conforme) ; seuls les `title=` natifs de `App.tsx` fautent (DA-041).

---

## C. Inventaire des composants

Grep exhaustif de tout `frontend/src`. Pour chaque famille : nombre de variantes vivantes, où, et si une variante canonique existe dans `components/fiche/primitives.tsx`.

| Famille | Variantes | Dans `primitives.tsx` ? | Détail |
|---------|:---------:|:---:|--------|
| **Bouton** | ≥ 8 idiomes | non (partiel) | Classes CSS `.btn` / `.b-pri` / `.p-on` / `.cta` / `.act` / `.ia-btn` (`styles/index.css:260-586`) + inline `btnPlein` (`projets/ProjetsPanel.tsx:145`, `projets/ParcoursProjet.tsx:127`, `fiche/FinancierQuestionnaire.tsx:414`) + boutons Tailwind ad-hoc. Aucun composant `<Bouton/>` unique ; les 3 niveaux (primaire/secondaire/lien) ne sont pas matérialisés par un composant. |
| **Chip / puce de filtre** | 4 | non | `Chip/ChipGroup` filtre `panel/FiltreLabuse.tsx:90` ; `Chip` admin (tons) `admin/AdminView.tsx:54` ; pastilles inline `sources/SourcesPage.tsx:194`, `compare/ComparePanel.tsx:119`. Classe CSS `.chip` (`styles/index.css:218`). |
| **Case à cocher** | 0 partagée / **18 bruts** | non | 18 `<input type="checkbox">` natifs (`outils/Blocs.tsx`, `Renouvellement.tsx`, `Successions.tsx`, `M22Programme.tsx`, `header/Header.tsx`, `ScoringV2.tsx`, `TaxeAmenagement.tsx`, `moteurs.tsx`, `surveillance/SurveillancePanel.tsx`…). Classe CSS `.cbx/.cbx-on` existe mais peu réutilisée. |
| **Tri** | 2 | non | En-tête `SORTS` (flèche ↓/↑) `panel/ResultsSection.tsx:171,652` ; boutons de tri ad-hoc `outils/Renouvellement.tsx:200`. |
| **Retour** | 3 | non | `← Outils` (`ModulePanel.tsx:1880`), `RetourOutil` post-pont (`ModulePanel.tsx:1832`), + retours d'étape locaux (`Communes/Plu/PluAnnuaire/ProspectionSolaire/Courrier`, glyphe `‹`). |
| **Omnibox** | 2 | non | Header `data-omnibox` (`header/Header.tsx`, bg-transparent) ; `ParcelInput` outil (`ParcelInput.tsx:26`, `rounded-lg border`) enrobé par `ParcelPicker`. |
| **Ligne de liste** | ~1 (+ variantes) | partiel | `panel/ResultsSection.tsx` (ligne résultat) réutilisée ; lignes de comparateur `data-o6-row` (`Communes.tsx`) et cartes CRM/Radar sont des variantes de mise en page. Globalement cohérent → **conforme**. |
| **Carte cliquable** | ~1 | oui (`OutilCase`/tuiles) | Portes/tuiles (`.door`, `.tiroir`, `.porte-outil`) partagées ; icône inversée au survol → **conforme**. |
| **Badge** | 7 | partiel (`pill-*`) | `TierBadge` (`outils/TierBadge.tsx:9`), `DestinationBadge` **4 couleurs** (`outils/DestinationSelect.tsx:44`), `copilote.Badge`/`PillStatut` (`copilote/ui.tsx:23,45`), `SourcesPage.Badge` 4 variantes (`sources/SourcesPage.tsx:22`), `EquipementsBadges` (`fiche/reseaux.tsx:26`), `.b`/`StepProv` (`primitives.tsx:365`, `styles/index.css:550`), `ProvBadge` (`compare/ComparePanel.tsx:60`) ; + pilules `pill-mint/-amber/-neutre` (`:454,523,524`). |
| **Accordéon / chevron** | ≥ 6 | non | `ChevronSection` SVG ◂/▾ (`panel/ChevronSection.tsx:30`) ; SVG `›` rotate (`TaxeAmenagement.tsx:255`, `Gabarit.tsx:240`, `ResultsSection.tsx:435`) ; SVG `-rotate-90` (`FiltreLabuse.tsx:199`, `CouchesTuyau.tsx:548`) ; glyphes texte `▸/▾/›/▶` (`EtudeZone.tsx:512`, `blocks.tsx:35`, `ProcedureChangement.tsx:96`, `crm/Kanban.tsx:100`…). Couleurs : gris majoritaire, rarement vert opaque. |
| **Tiroir / drawer** | ~1 | oui (`.tiroir`) | Tiroirs fiche `styles/index.css:498` cohérents ; pas d'animation d'apparition (cf. DA-032). |
| **État vide** | 1 partagé + ~25 ad-hoc | oui (`EmptyState` `States.tsx:18`) | `EmptyState` utilisé 3× seulement ; ~25 rendus locaux (`crm/Kanban.tsx:607,688`, `outils/RadarView.tsx:554,563`, `projets/ProjetsPanel.tsx:245`, `outils/EtudeZone.tsx:461`…). |
| **État erreur** | 1 partagé + ~15 ad-hoc | oui (`ErrorState` `States.tsx:38`) + `RateLimit429` (`primitives.tsx:393`) | `ErrorState` ~10 importeurs ; ~15 erreurs en texte inline (`outils/Gabarit.tsx:182`, `outils/moteurs.tsx:90,217,278`, `fiche/AskBar.tsx:148`…). |
| **État chargement** | 4 idiomes | partiel | `Loading` = points animés/spinner (`Loading.tsx:4`, ~43 usages) ; `Skeleton` (`Loading.tsx:25`, 1 vrai usage) ; `MapLoading` (`App.tsx:41`) ; 2 spinners rotatifs (`App.tsx:45`, `header/Header.tsx:201`) ; ~15 « Chargement… » texte. **Aucun squelette généralisé.** |
| **Barre de défilement** | 1 (verticale) | — | Style unique, pouce vert opaque au survol (`styles/index.css:346-349`) → **conforme**. MAIS 2 barres **horizontales** parasites (DA-030). |

**Bilan C** — familles à ≥ 2 variantes : **bouton, chip, case, tri, retour, omnibox, badge, accordéon, état-vide, état-erreur, état-chargement (11)**. Familles conformes (1 variante) : **scrollbar verticale, ligne de liste, carte cliquable, tiroir**. Les trois familles les plus éclatées : **accordéon/chevron (≥ 6 systèmes)**, **badge (≥ 6)**, **case à cocher (0 partagée / 18 brutes)** — juste devant l'**état-chargement (4 idiomes, aucun squelette)**.

---

## Non couvert par la charte

- **DA-035 / Comparateur communes (table 9 colonnes)** : la charte 7.3 vise « une table dans un panneau outil (320 px) » ; le comparateur est un overlay « en grand » plein écran. La charte ne dit pas si l'overlay large échappe à la règle « jamais 6 colonnes ». À trancher par Vic.
- **Rail actif « Copilote » en mauve (DA-020)** : la charte 1.1 dit « onglet courant = vert opaque » et 1.2 « surfaces IA restent mauves ». Le cas d'un **onglet de navigation qui EST une surface IA** n'est pas arbitré. À trancher.
- **« Analyser avec LABUSE » (scoring)** vs entrée IA : la charte 2.5 interdit « tout point d'entrée IA hors fiche/Copilote » ; l'analyse LABUSE (scoring, pas la conversation) est offerte depuis le panneau Filtres. À dire si le scoring compte comme « IA » au sens de la règle.

---

## Fin

Livrable : ce rapport + 22 captures (`captures/`). Commit `docs: DA-AUDIT-1 rapport + captures` sur `audit/da-1`, poussé, **pas de merge**.

### Les 3 familles de composants les plus éclatées
1. **Bouton** — aucun composant partagé : les classes `.btn/.b-pri/.b-sec` ne servent qu'à l'admin Circuit ; ~9 familles + boutons Tailwind inline dans **39 fichiers** (hauteurs 24→40 px, rayons 4/6/8/9/10, polices 10→14 px).
2. **Accordéon / chevron** — **≥ 6 systèmes** (SVG ◂/▾, SVG `›` rotate, glyphes texte `▸/▾/›/▶`), chevron fermé pointant à gauche, couleurs grises au lieu de vert opaque actif.
3. **Badge** — **7 composants** distincts, dont un (`DestinationBadge`) à 4 couleurs alors que la charte en impose 3.

*(Familles suivantes de près : case à cocher — 0 partagée / 18 brutes ; état-chargement — 4 idiomes, aucun squelette généralisé.)*
