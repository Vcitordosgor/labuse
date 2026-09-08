# RECETTE-1 — rapport des correctifs (retours du 08/09/2026)

**Branche** : `feat/recette-1` (depuis `main`). **Worktree** : `~/Desktop/labuse-recette1`.
**Modèle** : mandat = Fable ; exécuté sous Opus 4.8 (signalé, sans incidence). **Aucun merge, aucune bascule, aucun rescoring.**
**Périmètre fermé** aux points R1–R41. Un commit par lot.

État possible : **corrigé** / **non reproduit** / **refusé**.

---

## LOT 1 — Bloquants  *(commit 1)*

| # | Point | État | Preuve |
|---|-------|------|--------|
| R1 | Export **Résumé** cassé (base `/socle/`) | **corrigé** | `frontend/vite.config.ts` — `/resume` ajouté au proxy dev |
| R2 | Export **Apporteur** cassé (base `/socle/`) | **corrigé** | `frontend/vite.config.ts` — `/apporteur` ajouté au proxy dev |
| R3 | **Financier** « Impossible de charger le questionnaire » | **corrigé** | `frontend/vite.config.ts` — `/financier` ajouté au proxy dev |
| R4 | **Faisabilité** — « Trouver les parcelles » ne fait rien | **non reproduit** | endpoint + câblage vérifiés (voir ci-dessous) |
| R5 | Cache carte — zoom bloqué sur la parcelle dans les outils suivants | **corrigé** | `frontend/src/store/useApp.ts:867` (`setModule` remet `focusIdu: null`) |
| R6 | Listing — « Adresse non disponible » sur **toutes** les parcelles | **non reproduit** | mesuré : 257 340/430 813 parcelles adressées, cache sain (voir ci-dessous) |
| R7 | Lenteur du chargement (Blocs fonciers, Densifier) | **corrigé** (cause dite) | `src/labuse/api/app.py:5422` — tri « score » sur index ; cause détaillée ci-dessous |

### R1 / R2 / R3 — trois documents du builder EXPORTS-2 hors du proxy dev
**Cause unique.** Les routes racine `/resume/{idu}.pdf`, `/apporteur/{idu}.pdf`, `/financier/{idu}.pdf` et le fetch `/financier/{idu}/questionnaire` (routeur `documents.py`, servi à la racine) n'étaient **pas** déclarées dans le proxy dev de `vite.config.ts`. En `npm run dev`, le lien PDF sortait donc de la base `/socle/` (message « public base URL of /socle/ ») et le fetch du questionnaire tombait sur Vite au lieu de FastAPI (« Impossible de charger le questionnaire »). Même famille exacte que `/dossier` et `/pre-dossier` (M70) qui, eux, étaient déjà proxifiés — d'où le fait que Dossier et Pré-dossier PC fonctionnaient et pas Résumé/Apporteur/Financier.
**Correctif** : ajout de `'/resume', '/apporteur', '/financier'` à `apiPaths`. Vérifié : `GET /resume/{idu}.pdf`, `/apporteur/{idu}.pdf` et `GET /financier/{idu}/questionnaire` répondent 200 sur l'API `:8000`. ⚠ **TRAIN 8** : ces mêmes préfixes doivent être routés côté Caddy en prod (comme `/argumentaire`, `/pre-dossier`).

### R4 — Faisabilité « Trouver les parcelles » : **non reproduit**
- L'outil « Faisabilité » du menu = `M22Programme.tsx` (registry `programme`), mappé sur `M22` (`ModulePanel.tsx:1670`).
- Le bouton (`M22Programme.tsx:156`) appelle `lancer()` → `setQuery(...)` → `useInfiniteQuery` POST `/modules/programme`. `/modules` **est** proxifié.
- `disabled={results.isLoading}` : en `@tanstack/react-query` v5, une requête `enabled:false` a `isLoading=false` (= `isPending && isFetching`), donc le bouton n'est **pas** figé.
- L'endpoint répond **200** : `POST /modules/programme` (commune nulle → 19 752 parcelles ; commune = nom → OK ; `CommuneScope` émet bien le **nom** de commune, attendu par `p.commune`).
- Aucune erreur de rendu (voisins `DestinationSelect`/`useDestinationsRef` sur `/outils/…`, proxifié et null-safe).
- **Conclusion** : câblage et backend sains sur la base de recette. Si le symptôme persiste chez Vic, il est d'environnement (API cold-start du worktree, ou `vite preview` — dont le proxy `server.proxy` ne s'applique pas). À noter : sous R5 (carte bloquée), les résultats se posaient bien mais la carte ne se recentrait pas dessus, ce qui pouvait donner l'impression que « rien ne se passe » — R5 corrigé.

### R6 — « Adresse non disponible » partout : **non reproduit**
- Le texte n'existe qu'en `ResultsSection.tsx:47/127` (listing principal après « Voir les parcelles »). Il lit `p.adresse`.
- Île (défaut analyse groupé) : `getResults` → `/filtre` renvoie l'adresse (ex. « 6 Rue des Glorieuses, 97410 Saint-Pierre »).
- Commune : `/map/parcels.geojson` — mesuré sur Saint-Pierre : **25 849 / 42 304 features adressées** (pas « toutes » vides).
- Cache matérialisé `parcel_adresse` **sain** : 257 340 lignes, toutes `ban_voie` renseignée, = `count(distinct idu)` de `adresse_parcelles` → `_adresse_ready` vrai (le bug historique « moitié construit » que ce garde résout n'est pas présent).
- ~40 % des parcelles (173 473) n'ont **légitimement** aucune adresse BAN (grandes emprises, parcelles EDF/publiques…) : « Adresse non disponible » y est correct, jamais un blanc.
- **Conclusion** : non reproduit sur la base de recette (60 % adressées, cache sain). Un « tout vide » chez Vic pointerait vers un `parcel_adresse` vide/périmé au moment de la recette (état d'ingestion, pas de bug de code).

### R7 — Lenteur : **cause dite, puis corrigé**
**Cause.** Ce **n'est pas** la requête des deux outils. Mesuré bout-en-bout sur la base de recette (`:8000`) :
- `/modules/blocs` (liste) : **87 ms** ; détail d'un bloc : **10 ms** ; page profonde (offset 4000) : **37 ms**.
- `/renouvellement/liste` : **169 ms** ; page profonde (offset 6000) : **460 ms**.

Les deux outils lisent des tables **précalculées** (`parcel_blocs` 11 225 lignes, `parcel_renouvellement` 67 260) avec jointures indexées ; la sous-requête `idu_repr` des Blocs passe par la PK (Index Only Scan, pas un N+1). La carte surligne les IDU par filtre sur une couche déjà chargée (`MapView.tsx:2069`), **sans** fetch par parcelle.
La « lenteur » perçue correspond donc soit au **démarrage à froid de l'API du worktree** (1ʳᵉ requête ~70–140 s, documenté), soit au **GeoJSON commune plein** (`/map/parcels.geojson`, ~60 k features, ~11 s non caché puis caché) — indépendants de ces deux outils. Aucun de ces deux points n'est un défaut de code corrigeable ici (l'un est un cold-start d'env, l'autre déjà caché par `_geojson_cached`).

**Correctif appliqué (la seule inefficacité mesurable de requête).** Le tri par défaut « score » de Densifier lisait `renouv_score DESC, r.idu` — **sans index** → Parallel Seq Scan + top-N sort des 67 260 lignes à chaque page (18 ms de tri, croissant avec l'OFFSET). Or `rang_segment` est bâti exactement comme `rank() OVER (ORDER BY score DESC, idu)` (idu unique ⇒ bijection). Bascule du tri « score » sur `r.rang_segment` (indexé `ix_renouv_rang`) : **Index Scan**, tri 18 ms → **3,4 ms**, ordre vérifié **strictement identique** (`diff` des 20 IDU à offset 6000 = identiques). Aucun changement de schéma, aucune ligne réordonnée.

**Vérifs Lot 1** : `python -m py_compile src/labuse/api/app.py` OK ; `tsc --noEmit` (frontend) exit 0.

---

## LOT 2 — Doctrine du scoring  *(commit 2)*

| # | Point | État | Preuve |
|---|-------|------|--------|
| R8 | Le scoring ne s'affiche que sur demande | **corrigé** | pastilles retirées de 7 outils (liste ci-dessous) |

**Règle appliquée.** La pastille de palier (Priorité / À suivre / Sans signal / Écartée = `TierBadge` / `verdictMeta`) et tout classement issu de q_v14 ne restent que dans **deux** endroits :
1. le parcours « Demander à LABUSE » = la liste d'analyse (`ResultsSection.tsx:34`, affichée seulement en mode analyse ; le mode factuel était déjà neutre) ;
2. la **fiche parcelle** (`Fiche.tsx:627`, bloc verdict + `ScoreV2Block`).

**Endroits nettoyés (pastille retirée) :**
| Outil | Fichier:ligne (avant) | Ce qui a été retiré |
|-------|----------------------|---------------------|
| Étudier un bien | `EtudierBien.tsx:141` | pastille « Classement » de l'en-tête (le classement reste en fiche, au clic) |
| Faisabilité | `M22Programme.tsx:231` | `TierBadge` de chaque ligne (la marge de capacité `×N` reste — métrique de faisabilité) |
| Scan patrimoine | `ModulePanel.tsx:356` | `right={<TierBadge/>}` des lignes |
| Assemblage | `moteurs.tsx:401` | `TierBadge` des lignes de voisines |
| Simulateur ZAN | `moteurs.tsx:548` | `TierBadge` des parcelles alignées ZAN |
| Pièges & risques | `ModulePanel.tsx:1563` | `right={<TierBadge/>}` du crible |
| Densifier l'existant | `Renouvellement.tsx:228+257` | colonne **« Classement »** (en-tête + cellule) ; « Score densif. » et « Rang commune » **restent** (métriques propres à l'outil, cf. R40) |

`Row` (ModulePanel) : prop `right` rendue **facultative** (les outils ne la passent plus).

**Non touché, avec motif :**
- **Blocs fonciers** : n'affichait déjà aucune pastille (rien à retirer).
- **`ParcoursTinder.tsx:169`** : `setParcours` n'a **aucun appelant** dans le code → surface **inatteignable** (ne rend jamais rien à un client). Laissée en l'état ; à décider par Vic (parcours de tri d'un projet).
- **`ModulePanel.tsx:1025` (M06 « Mode bailleur »)** : outil **dormant**, retiré du menu le 20/08/2026 (non câblé). Pas une surface visible.

**Vérifs Lot 2** : `tsc --noEmit` exit 0 ; `vitest run` **194/194** (deux tests basculés en « la pastille est ABSENTE » : `ScanRetraits.test.tsx`, `DensifierTable.test.tsx`).

---

## LOT 3 à 10 — à faire
*(non entamés)*
