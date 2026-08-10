# RAPPORT M55-B — Recherche, fiche commune, chevron, couches

Branche `feat/m55-b-recherche-fiche` (base `main` f8137638, **M55-A + bis mergé — précondition
vérifiée**). Un commit par point. tsc 0, `npm run build` vert, vitest inchangé. Captures dans
`reports/m55-b-recherche-fiche/captures/`. **CC ne merge jamais.**

| # | Objet | Commit |
|---|-------|--------|
| 1 | Autocomplétion d'adresse (mesure + fix) | `79f1e349` |
| 2 | Placeholder allégé | `abd8277e` |
| 3 | Recherche visible (spinner + vide) | `9f0d8f80` |
| 4 | Fiche commune (retrait + audit) | `b50f23a8` |
| 5 | Croix de fermeture | `53c6e56a` |
| 6 | Couches seules (mesure + fix) | `4fbaad1a` |

---

## 1. Autocomplétion d'adresse — CAUSE puis fix

**Mesure (rapportée avant tout code)** :
- Le composant `AddressAutocomplete` EST branché sur l'omnibox du header (`Header.tsx`).
- Seuil ≥3 caractères — ATTEINT pour « 3 chemin de la citerne ».
- Source = table interne `adresses` via `/adresses/autocomplete` (pas la BAN externe).
- Le **backend répond correctement** : `curl` → Le Tampon + Saint-Denis, avec `idu` (prouvé).
- **Cause réelle** (repro navigateur) : en `npm run dev`, `/adresses/autocomplete` renvoie **404** —
  le chemin `/adresses` **manquait dans le proxy vite** (`apiPaths`). `banAutocomplete` throw →
  `catch` silencieux → 0 suggestion. **Prod OK** (FastAPI même origine).

**Fix** : (a) `/adresses` ajouté au proxy dev (→ 200 / 6 features, prouvé) ; (b) état vide
**honnête** dans le composant : 0 résultat affiche « Aucune adresse trouvée — vérifiez
l'orthographe, ou tapez un IDU / une commune » au lieu du silence. Captures `p1_suggestions_after`,
`p1_empty_state`.

## 2. Placeholder — « commune » retiré
« Rechercher : IDU, adresse exacte, commune… » → « **Rechercher : IDU, adresse exacte…** ».
Vérifié : la recherche par commune **fonctionne toujours** (Entrée sur « Saint-Paul » → commune
active, via `onEnterRaw`) — allègement du placeholder seul.

## 3. Recherche visible
- **Chargement** : la loupe devient un **spinner sobre** (bouton désactivé, `cursor-wait`,
  `aria-busy`) pendant la résolution (`onEnterRaw` enveloppé try/finally). Prouvé (`aria-busy=true`,
  capture `p3_loading`).
- **Vide** : le toast honnête « Aucune commune, parcelle ni adresse trouvée pour … » (confirmé,
  capture `p3_empty_toast`) + le menu « Aucune adresse trouvée » du point 1 se complètent.

## 4. Fiche commune

**4a — retrait** : le bloc « CLASSEMENT LABUSE » (compteurs de production internes : parcelles
brûlantes/chaudes, propriétaires PM, « recalculé à chaque bascule ») est **retiré du front** de la
fiche de contexte commune (le backend le calcule encore mais aucune surface ne le rend). Capture
`p4_fiche_commune` (la fiche ouvre désormais sur SRU).

**4b — audit de véracité (Saint-Paul).** Chaque bloc restant croisé avec sa table + son script
d'ingestion :

| Donnée | Valeur servie | Source | Millésime | Verdict |
|--------|---------------|--------|-----------|---------|
| **SRU** | 18,33 % / obj 25 % / **déficitaire** / 7 499 LLS / prélèvement 0 € | DHUP « Communes et inventaire SRU » (data.gouv, `scripts/ingest_sru.py`) | inventaire **01/01/2024** · périmètre 01/01/2025 · prélèvement 2025 (fichier **v2 du 18/12/2025**) | **EXACT** — dataset DHUP le plus récent |
| **NPNRU** | Aucun périmètre à SP ; « 8 quartiers d'intérêt national à La Réunion, aucun régional » | DEAL Réunion WFS Carmen + ANCT (`scripts/ingest_npnru.py`) | arrêté 29/04/2015 (périmètres QPV 2015, mappés vers QPV 2024) | **EXACT** — base = 8 national / 0 régional / 6 communes (vérifié en base) |
| **PLH TCO** | 1 800 log/an · 47 % social | 3e PLH TCO (Éohs, nov. 2019) + délib. PLH 4 2025 (`config/plh_tco.yaml` → `plh_epci`) | **PLH 3 : 2019-2025** (adopté) · **PLH 4 lancé** 25/06/2025 | **EXACT en transition** — le PLH 3 (2019) est le SEUL PLH adopté ; le lancement du PLH 4 est DIT. La réf. 2019 reste la bonne. *Constat : réingérer quand le PLH 4 sera adopté.* |
| **Marché INSEE** | 51 317 log · 4 840 vacants (9,4 %) · prop 61 / loc 35 · maisons 71,8 / apparts 27,4 | INSEE RP 2023 base comparateur (`scripts/ingest_insee_logement.py`) | **RP 2023** (publié 25/06/2026 — dernier millésime) | **EXACT / RP le plus récent**. **Cohérence** : loc+prop = 96 % → les **4 % = « logés gratuitement »** (3e statut INSEE) n'étaient pas nommés → **CORRIGÉ** (résiduel dérivé nommé). *Constat : la valeur EXACTE du 3e statut n'est pas ingérée (colonnes prop/loc seules) → réingestion pour la servir telle quelle.* |
| **QPV** | 11 QPV nominatifs (Barrage-Cinq heures, Centre Ville St-Charles, …) | ANCT data.gouv (`src/labuse/ingestion/qpv.py`) | **génération 2024** (décret 2023-1314, en vigueur 01/01/2024) | **EXACT** — génération QPV en vigueur (11 à SP) |

**Corrigé dans le périmètre** : le graphe d'occupation INSEE somme désormais à 100 % avec le
segment « logés gratuitement » (dérivé 100−loc−prop, arrondi, honnête).
**Constats à rapporter** (réingestion, hors périmètre) : (1) PLH 4 à réingérer une fois adopté ;
(2) valeur exacte des « logés gratuitement » à ingérer (colonne INSEE dédiée) — le résiduel dérivé
est un relais fidèle en attendant.

## 5. Croix de fermeture
Le panneau « Cartes » fermait avec un chevron « ‹ » (seul cas). Remplacé par une **croix « ✕ »**
(« Fermer le panneau »). Cohérence vérifiée : fiche parcelle (SVG ×) et contexte commune (✕)
fermaient **déjà** avec une croix. La languette « › » (ré-affichage) reste un chevron : c'est une
ouverture. Capture `p5_cartes_croix`.

## 6. Chaque couche seule ?

Protocole : chaque couche activée SEULE, sur une commune où elle a des objets (table de couverture
M55-A). Analyse code (visibilité) + repro navigateur.

| Couche | Verdict | Dépendance | Action |
|--------|---------|-----------|--------|
| Parcelles | **AUTONOME** | — | — |
| Limites parcelles | **AUTONOME** | `parcels-limites`, toggle propre | — |
| **Zonage PLU par parcelle** | **DÉPENDANTE** | **Parcelles** (repeint `parcels-fill`, masqué si Parcelles off → rien ne se peignait) | **Dépendance auto-activée** au clic (`toggleLayer`) + dite dans le « i ». Prouvé : Parcelles OFF → clic → Parcelles ré-activée, 44 314 parcelles peintes |
| Zones du PLU officiel (brut) | **AUTONOME** | `ov-zonage`/`ovmvt-zonage`, toggle propre | — |
| PPR multirisque | **AUTONOME** | `ov-ppr`/`ovmvt-ppr` | — |
| **Équipements** | **DÉPENDANTE (zoom)** | zoom ≥ 12 (`minzoom`, sinon 15 000 icônes) | **Toast sobre « Zoomez pour afficher les équipements »** au lieu du silence. Prouvé à z≈9,8 |
| Limites communes | **AUTONOME** | `communes-bounds` | — |
| Parc national | **AUTONOME** | `ov-parc` | — |
| ANRU (NPNRU) | **AUTONOME** | `ov-anru` (6 communes) | — |
| 50 pas géométriques | **AUTONOME** | `ov-50pas` (littoral) | — |
| Renouvellement | **AUTONOME** | `ov-renouv` | — |

Captures `p6_zonage_autonome`, `p6_equip_zoom_msg`. Aucune couche **CASSÉE** trouvée.

---

## Périmètre & garde-fous
Barre de recherche, fiche commune (front + données servies), chevrons, panneau couches. **Aucune
touche au scoring ni aux exports.** Fichiers : `vite.config.ts`, `AddressAutocomplete.tsx`,
`Header.tsx`, `ContextePanel.tsx`, `LeftPanel.tsx`, `store/useApp.ts`, `MapView.tsx`, `layers.ts`.
CC ne merge jamais.
