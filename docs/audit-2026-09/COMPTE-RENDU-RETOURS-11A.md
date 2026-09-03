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
| C1 | … | 🔴 Régression couleurs zonage PLU |
| C2 | … | Audit des couches (tableau) |
| C3 | … | Couche VEFA + moteur unique |
| C4 | … | Lisibilité couches Ortho/Plan |
| C5 | … | Limites officielles PLU (GPU brut) couche de 1er niveau |
| C6 | … | Fonds Plan/Ortho/Remonter le temps |
| C7 | … | Outils de dessin (audit) |
| C8 | … | Validation par Entrée seulement |
| C9 | … | Remonter le temps : étiquette IDU |

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

_(à compléter au fil des lots)_

---

## Clôture

- tsc : …
- build : …
- vitest : …
- pytest : …
- golden (119/119, aucun fichier scoring touché) : …
- captures avant/après : `docs/audit-2026-09/retours-11/captures/` …
