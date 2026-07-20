# CARTO_API — Domaine API, Socle IA & Flash

Cartographie factuelle (lecture seule) de `src/labuse/api/**`, `src/labuse/ai/**` et
`src/labuse/flash/**`. Aucun jugement — faits bruts, chemins cliquables, `wc -l` mesurés.

Périmètre : 30 fichiers `api/` + 5 fichiers `ai/` (+ `__init__`) + 3 fichiers `flash/`
(+ `__init__`). **174 routes** au total (66 sur `app`, 108 sur des routers inclus).

---

## 1. Rôle de la couche API & assemblage de l'app

`src/labuse/api/app.py` construit l'unique instance `FastAPI` (`app`, titre « LA BUSE —
radar foncier », v0.1.0). La couche API expose : parcelles/fiches, carte (GeoJSON + tuiles
MVT), scoring v2, modules-outils (Vagues 1-5), copilote IA, projets, événements/veille,
segments Habitat, solaire, ortho, protection anti-abus, exports PDF/CSV, CRM pipeline.

### Assemblage (`app.py`)

- **Lifespan** (`_lifespan`, `app.py:61`) : auto-réconciliation LÉGÈRE du schéma au
  démarrage (`models.ensure_schema`) + appel des `ensure_tables()` des routers
  (`modules`, `ia`, `events`, `partners`, `projets`, `segments`, `protection`, `courrier`).
  Remplace un ancien `@app.on_event("startup")` mort sous lifespan. Best-effort : DB
  injoignable → l'app démarre quand même, `/readyz` dit la vérité.
- **Routers inclus** (`app.py:2936-2951`, dans cet ordre) :
  `fiche_ask`, `score_v2`, `modules`, `courrier`, `dossier`, `pre_dossier`, `protection`,
  `tiles`, `ia`, `events`, `moteurs`, `partners`, `projets`, `segments`, `solaire`, `ortho`.
  Les routes restantes sont déclarées directement sur `app` dans `app.py` (66 routes).
- **Middlewares** (ordre d'enregistrement ; Starlette : dernier enregistré = plus externe) :
  1. `CORSMiddleware` (`app.py:121`) — origines `*` en local, sinon `public_url` si défini.
  2. `GZipMiddleware(minimum_size=1024)` (`app.py:127`) — compresse les couches carte
     (`/map/*.geojson` ~20-30 Mo → /9) ; n'affecte ni DB ni scoring ni verdicts.
  3. `_fix_double_encoded_query` (`app.py:130`) — répare les query-strings double-encodées
     par certains tunnels d'aperçu (`%2520` → `%20`).
  4. `garde_protection` (importé de `protection.py`, `app.py:151`) — anti-scraping/quota/rate-limit.
  5. `_auth_guard` (`app.py:154`) — garde d'auth pilote (routes métier protégées ; publiques :
     `/healthz`, `/health`, `/readyz`, `/login`, `/logout`).
  6. `_no_cache_html` (`app.py:2962`) — `Cache-Control: no-store` sur le HTML du Socle.
- **Front monté** :
  - `/socle` → `frontend/dist` (Socle V1, React+MapLibre/Vite) si présent (`app.py:2983`).
  - `/app` → `api/web` (UI Vue historique, transition) si présent (`app.py:2972`).
  - `GET /` (`app.py:2975`) redirige vers `/socle/` (sinon `/app/`, sinon `/docs`).

### Caches en mémoire (process, `app.py`)

`_mem_cached` (TTL générique, single-flight par clé) et `_geojson_cached` (GeoJSON commune,
LRU borné à ~220 Mo, TTL 600 s) — résultat identique au calcul, jamais en DB.

---

## 2. Inventaire des endpoints (174)

Chemins avec préfixe du router inclus. Groupés par fichier.

### `app.py` (montées sur `app`, sans préfixe) — 66 routes

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 183 | GET `/health` | ping produit |
| 188 | GET `/healthz` | niveau 1 : le process répond (zéro DB) |
| 197 | GET `/login` | page de connexion pilote (HTML) |
| 210 | POST `/login` | soumission connexion (form/JSON, anti-brute) |
| 241 | GET `/logout` | déconnexion (purge cookie) |
| 251 | GET `/readyz` | niveau 2/3 : schéma + données critiques (503 sinon) |
| 370 | GET `/demo-status` | niveau 4 : état complet de la démo (healthcheck 13 pts) |
| 381 | GET `/coverage` | couverture des couches excluantes/flaggantes |
| 405 | GET `/demo` | panneau « démo guidée » (parcelles conformes) |
| 433 | GET `/sources` | page « sources de données » (statut connecteurs + fraîcheur) |
| 480 | POST `/sources/{source_id}/test` | bouton « tester la connexion » d'une source |
| 665 | GET `/parcels` | liste paginée + dernier verdict (v2 pilote) |
| 719 | GET `/parcels/export.csv` | export CSV de la liste filtrée |
| 795 | GET `/communes` | 24 communes pour le sélecteur (volumétrie, chaudes, bbox) |
| 833 | GET `/communes/{commune}/contexte` | contexte commune (SRU/ANRU/PLH/marché INSEE) |
| 867 | GET `/parcels/at` | résolution point (lon/lat) → IDU |
| 878 | GET `/parcels/search` | recherche IDU/section (omnibox île) |
| 922 | GET `/stats/entonnoir` | entonnoir par motif d'écartement (SQL-exact) |
| 945 | GET `/stats` | cartouches dashboard (volumétrie + tiers v2) |
| 1012 | GET `/map/parcels.geojson` | parcelles + verdict pour la carte colorée |
| 1730 | GET `/parcels/{idu}` | FICHE parcelle (verdict + double score + cascade + sources + IA) |
| 1738 | GET `/parcels/{idu}/export.pdf` | export PDF fiche premium (design system) |
| 1784 | GET `/map/layers.geojson` | couches carte (zonage/PPR/parc/ANRU/aménité/50 pas) |
| 1804 | GET `/map/bati` | taux de bâti par parcelle (mode « mutabilité ») |
| 1823 | GET `/assemblages` | liste des assemblages fonciers (paires contiguës) |
| 1835 | GET `/assemblage/study` | faisabilité sur un ensemble de parcelles regroupées |
| 1900 | GET `/shortlist` | « les N sujets à traiter aujourd'hui » (priorisation promoteur) |
| 1976 | GET `/mutation/{idu}` | Score Mutation d'une parcelle (lecture seule) |
| 1990 | GET `/mutation` | top Radar Mutation d'une commune |
| 2010 | GET `/map/mutation.geojson` | calque carte Radar Mutation |
| 2041 | GET `/map/permits.geojson` | marqueurs SITADEL géolocalisés |
| 2242 | GET `/parcels/{idu}/enrichment` | bloc promoteur (altimétrie/façade/PLU/proprio/réseaux), lazy |
| 2266 | GET `/assistant/status` | l'assistant IA est-il configuré (clé) ? |
| 2273 | GET `/communes/status` | état & fiabilité des 24 communes (gold standard) |
| 2284 | GET `/parcels/{idu}/explain` | explication NL de la fiche (assistant IA) |
| 2295 | GET `/parcels/{idu}/export` | export fiche (md / html / onepager A4) |
| 2316 | GET `/parcels/{idu}/spf-letter` | courrier demande SPF pré-rempli |
| 2367 | GET `/filters` | filtres de recherche sauvegardés |
| 2375 | POST `/filters` | enregistre un filtre |
| 2385 | DELETE `/filters/{filter_id}` | supprime un filtre |
| 2405 | POST `/signalements` | ticket de QA humaine (erreur de donnée) |
| 2425 | GET `/signalements` | liste des signalements |
| 2440 | GET `/signalements/export.csv` | export CSV des signalements |
| 2473 | GET `/bilan/params` | paramètres de la calculette de bilan |
| 2483 | POST `/bilan/params` | met à jour les paramètres de bilan |
| 2494 | GET `/compare` | comparateur 2-3 parcelles côte à côte |
| 2509 | POST `/parcels/{idu}/evaluate` | relance la cascade (option `?ai=true`) |
| 2544 | POST `/audit/reference` | auditer un terrain par référence cadastrale |
| 2552 | POST `/audit/adresse` | auditer par adresse (géocodage BAN) |
| 2559 | POST `/audit/polygone` | auditer par polygone dessiné |
| 2568 | GET `/discover` | vue Découverte : survivantes classées |
| 2608 | GET `/signals` | signaux de veille récents (offre C) |
| 2638 | GET `/watch-zones` | zones de veille définies |
| 2646 | POST `/watch-zones` | crée une zone de veille (+ détection nouveautés) |
| 2658 | DELETE `/watch-zones/{zone_id}` | supprime une zone de veille |
| 2667 | GET `/alertes` | nouveautés (ventes DVF + permis près d'une cible) |
| 2676 | POST `/alertes/refresh` | re-détecte les nouveautés du scope |
| 2684 | POST `/alertes/ack` | accuse réception d'une (ou toutes) nouveauté(s) |
| 2702 | POST `/feedback` | boucle de feedback (§10) |
| 2810 | GET `/pipeline/meta` | colonnes/priorités du Kanban CRM (config) |
| 2818 | GET `/pipeline` | liste des entrées du pipeline |
| 2826 | GET `/pipeline/parcel/{idu}` | l'entrée pipeline d'une parcelle |
| 2838 | POST `/pipeline` | ajoute une parcelle au pipeline |
| 2873 | PATCH `/pipeline/{entry_id}` | met à jour une entrée (statut/priorité/notes/rappel) |
| 2906 | DELETE `/pipeline/{entry_id}` | retire une entrée du pipeline |
| 2975 | GET `/` | redirige vers le front (`/socle/`) |

### `fiche_ask.py` (sans préfixe) — 1 route

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 219 | POST `/parcels/{idu}/ask` | barre de fiche : question libre → réponse sourcée (grounding + cache + quota 20/j) |

### `score_v2.py` (préfixe `/v2`) — 5 routes

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 67 | GET `/v2/score/{idu}` | score P v2 (×N, percentile, rang, tier, badges) |
| 84 | GET `/v2/liste` | liste triée par rang P (filtres tier/commune, toggle copro) |
| 114 | GET `/v2/brulantes` | vue Brûlantes v2 |
| 122 | GET `/v2/reserve-fonciere` | réserve foncière (C fort, P faible) — vitrine capacité |
| 134 | GET `/v2/modele` | sources & fraîcheur du modèle (version, gel, censure) |

### `modules.py` (préfixe `/modules`) — 17 routes

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 69 | POST `/modules/division/compute` | M01 : pré-calcul des candidats division (C1-C5) |
| 139 | GET `/modules/division` | M01 : liste des candidats division (hors étage 0) |
| 174 | GET `/modules/patrimoine/search` | M02 : recherche PM par dénomination/SIREN |
| 187 | GET `/modules/patrimoine` | M02 : patrimoine d'une PM (tier v2, BODACC) |
| 224 | GET `/modules/permis` | M03 : radar permis SITADEL (fenêtre glissante) |
| 267 | GET `/modules/permis/{permit_id}` | M03 : fiche permis cliquable |
| 306 | GET `/modules/parcelle-permis` | M10 : permis sur/à proximité d'une parcelle |
| 347 | GET `/modules/promesses` | M04 : promesses mortes (PC ancien sans DAACT, non bâti) |
| 408 | GET `/modules/velocite` | M05 : vélocité admin (délai médian dépôt→autorisation) |
| 485 | GET `/modules/fantome` | M07 : foncier fantôme (PM introuvable/dirigeant inactif RNE) |
| 543 | GET `/modules/bailleur` | M06 : mode bailleur (QPV + contexte SRU) |
| 610 | POST `/modules/courriers` | M09 : génère des courriers propriétaire (3 contextes) |
| 664 | POST `/modules/duediligence` | M10 : dossier de diligence notaire (checklist + risque) |
| 737 | GET `/modules/faisabilite/{idu}` | M22 sens 1 : que peut accueillir ce terrain + bilan |
| 805 | POST `/modules/faisabilite/{idu}/charge` | M22 : charge foncière selon hypothèses saisies |
| 913 | GET `/modules/faisabilite/{idu}/explain` | M11-C : explication IA de la faisabilité (ancrée sur les steps) |
| 959 | POST `/modules/programme` | M22 sens 2 : parc → terrains compatibles |

### `courrier.py` (préfixe `/courrier`) — 4 routes

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 27 | GET `/courrier/statut` | disponibilité + tarif (bouton masqué si stub) |
| 43 | POST `/courrier/envois` | envoie un courrier (case responsabilité obligatoire) |
| 62 | POST `/courrier/demande` | enregistre une demande d'envoi (traitée par l'équipe) |
| 81 | GET `/courrier/envois` | suivi des envois du sujet courant |

### `dossier.py` (préfixe `/dossier`) — 2 routes

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 43 | GET `/dossier/statut` | disponibilité + quota mensuel (dépend du module Flash) |
| 64 | GET `/dossier/{idu}.pdf` | PDF brandé parcelle (template Flash allégé, abonnés) |

### `pre_dossier.py` (préfixe `/pre-dossier`) — 1 route

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 209 | GET `/pre-dossier/{idu}.zip` | pack pré-dossier PC (CERFA pré-rempli + plan + règles), Intégral |

### `protection.py` (préfixe `/protection`) — 4 routes

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 309 | POST `/protection/defi` | défi arithmétique anti-burst (répit 10 min) |
| 330 | GET `/protection/admin` | tableau de bord : alertes, scores d'abus, gels |
| 347 | POST `/protection/admin/gel/{sujet}` | gel MANUEL d'un sujet |
| 355 | POST `/protection/admin/degel/{sujet}` | dégel d'un sujet |

### `tiles.py` (sans préfixe) — 3 routes

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 172 | GET `/map/tiles/meta` | capacités des tuiles MVT servies (zonage parcelle dispo ?) |
| 184 | GET `/map/tiles/{z}/{x}/{y}.pbf` | tuile MVT couche `parcels` (cache LRU, simplification par palier) |
| 263 | GET `/map/tiles/ov/{kind}/{z}/{x}/{y}.pbf` | tuile MVT overlay (zonage PLU / PPR île) |

### `ia.py` (préfixe `/ia`) — 6 routes

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 77 | GET `/ia/status` | provider (anthropic/stub) + modèles + doctrine |
| 329 | POST `/ia/search` | recherche NL → filtres validés par schéma (+ agrégats SQL, +sémantique) |
| 421 | POST `/ia/segments-search` | question libre → filtres du moteur de segments (quota jour) |
| 596 | POST `/ia/entretien` | entretien de cadrage projet (RÉEL seulement, sinon fallback) |
| 699 | POST `/ia/synthese/{idu}` | synthèse de fiche (depuis le JSON tracé) |
| 710 | POST `/ia/pourquoi/{idu}` | « pourquoi ce score ? » (pédagogie des lignes Q/A) |

### `events.py` (préfixe `/events`) — 13 routes

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 225 | GET `/events` | flux d'événements (bascules, matchs…) |
| 240 | GET `/events/count` | compteur de non-lus (global + par parcelle) |
| 247 | POST `/events/{event_id}/read` | marque un événement lu |
| 253 | POST `/events/read-all` | marque tout lu |
| 259 | POST `/events/detect` | détecte les bascules entre deux runs |
| 264 | POST `/events/demo` | seed d'événements de démonstration (étiquetés) |
| 271 | GET `/events/watch/{idu}` | une parcelle est-elle suivie ? |
| 277 | POST `/events/watch/{idu}` | (dé)suit une parcelle |
| 295 | GET `/events/searches` | veilles (recherches sauvegardées) |
| 301 | POST `/events/searches` | ajoute une veille |
| 308 | DELETE `/events/searches/{sid}` | supprime une veille |
| 334 | GET `/events/digest` | digest hebdo « pépites » (JSON) |
| 339 | GET `/events/digest.html` | digest hebdo email-ready (HTML) |

### `moteurs.py` (préfixe `/moteurs`) — 7 routes

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 38 | GET `/moteurs/simulplu/zones` | M15 : zones AU d'une commune |
| 48 | GET `/moteurs/simulplu` | M15 : simulateur PLU (bascule AU→U, à blanc, par analogie) |
| 102 | POST `/moteurs/assemblage` | M16 : assemblage multi-parcelles (contiguïté, gain, privacy) |
| 218 | GET `/moteurs/zan/parcelle/{idu}` | M17 : signal ZAN par parcelle (sourcé) |
| 262 | GET `/moteurs/zan` | M17 : simulateur ZAN (conso ENAF observée + budget estimé) |
| 370 | GET `/moteurs/barometre` | M18 : baromètre foncier (DVF/Sitadel, île) |
| 375 | GET `/moteurs/barometre.pdf` | M18 : baromètre en PDF marketing |

### `partners.py` (sans préfixe) — 10 routes

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 73 | GET `/partners/profiles` | M19 : profils de matching (démos étiquetés) |
| 79 | POST `/partners/profiles` | M19 : crée un profil |
| 88 | POST `/partners/match/run` | M19 : matche bascules chaude × profils → événements |
| 115 | GET `/partners/match/compatibilite/{idu}` | M19 : compatibilité décomposée d'une parcelle |
| 157 | GET `/partners/promoteurs-actifs` | M19-C : promoteurs réels actifs (SITADEL, PM) |
| 182 | POST `/partners/share/{idu}` | M20 : crée un lien de partage (pack apporteur) |
| 191 | GET `/partners/share/{idu}/list` | M20 : liens de partage d'une parcelle |
| 302 | GET `/p/{token}` | M20 : page publique pack apporteur (lecture seule, filigranée) |
| 396 | GET `/api/v1/parcels` | M21 : API partenaire B2B2C (clé + quota) |
| 417 | GET `/api/v1/docs` | M21 : doc HTML de l'API partenaire |

### `projets.py` (préfixe `/projets`) — 16 routes

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 64 | GET `/projets/reperes` | repères sourcés par secteur/commune (SQL, aucun chiffre IA) |
| 244 | POST `/projets/apercu` | aperçu relié au projet (top parcelles + « pourquoi ») |
| 308 | POST `/projets/derive` | dérive nom+filtres+programme d'une fiche (sans persister) |
| 340 | GET `/projets` | liste des projets + compteurs de tri |
| 360 | POST `/projets` | crée un projet (dédup douce) |
| 377 | GET `/projets/{pid}` | détail d'un projet |
| 385 | PATCH `/projets/{pid}` | modifie (nom/statut/fiche → re-dérive) |
| 407 | DELETE `/projets/{pid}` | supprime un projet |
| 419 | POST `/projets/{pid}/rejouer` | ouvrir = rejouer les critères sur les données actuelles |
| 502 | POST `/projets/{pid}/proposer` | propose les parcelles de la recherche (statut proposee) |
| 528 | GET `/projets/{pid}/parcelles` | état du parcours (parcelles groupées par statut) |
| 563 | GET `/projets/{pid}/carte/{idu}` | carte de décision d'une parcelle (points clés) |
| 588 | PATCH `/projets/{pid}/parcelle/{idu}` | geste Tinder (statut parcelle×projet, auto-CRM) |
| 628 | POST `/projets/{pid}/chercher-plus` | élargit la recherche (critères relâchés) |
| 660 | POST `/projets/{pid}/ajouter` | ajoute UNE parcelle (par IDU) |
| 675 | GET `/projets/{pid}/export.pdf` | dossier projet en PDF |

### `segments.py` (préfixe `/segments`) — 9 routes

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 123 | GET `/segments` | galerie : presets + disponibilité + registry + compteurs |
| 183 | POST `/segments/query` | évalue un preset (éventuellement modifié à la volée) |
| 242 | POST `/segments/export` | export CSV « à l'occupant » (RGPD, watermark) |
| 275 | POST `/segments/publipostage` | ZIP publipostage (CSV + étiquettes PDF + gabarit) |
| 325 | GET `/segments/gabarits` | gabarits de courrier par métier |
| 356 | POST `/segments/presets` | admin : créer/dupliquer un preset |
| 375 | PUT `/segments/presets/{slug}` | admin : éditer un preset |
| 388 | DELETE `/segments/presets/{slug}` | admin : supprimer un preset |
| 397 | POST `/segments/refresh-counts` | recalcule les compteurs (cache 24 h) |

### `solaire.py` (préfixe `/solaire`) — 5 routes

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 45 | GET `/solaire/fiche/{idu}` | panneau Solaire de la fiche (parcel_solar + sources) |
| 67 | GET `/solaire/parkings` | parkings assujettis APER (tri échéance, GeoJSON, CSV) |
| 123 | GET `/solaire/tertiaire` | grandes toitures × PM × bilan INPI × gisement |
| 152 | GET `/solaire/statut` | disponibilité de la mesure fine (gating bouton Lot 8) |
| 166 | POST `/solaire/mesure/{idu}` | Lot 8 CONDITIONNEL — 501 tant que clé Google absente |

### `ortho.py` (préfixe `/ortho`) — 5 routes

| Ligne | Méthode & chemin | Rôle |
|---|---|---|
| 51 | GET `/ortho/validation/api/suivante` | tire une vignette non validée (quota serveur) |
| 117 | GET `/ortho/validation/api/vignette/{det_id}.jpg` | image de la détection (crop ortho + contour) |
| 162 | GET `/ortho/equipements/{idu}` | badges fiche (piscine/PV/CES/pente, sourcés ortho) |
| 189 | POST `/ortho/validation/api/{det_id}` | enregistre un verdict humain (quota dur 409) |
| 302 | GET `/ortho/validation` | page HTML de validation (qualification commerciale) |

---

## 3. Socle IA (`src/labuse/ai/`)

Doctrine centrale (`ai/core.py:7`) : **l'IA n'accède JAMAIS à la base et ne calcule JAMAIS
un score/chiffre.** Elle reçoit un CONTEXTE AUTORISÉ (liste blanche, provenance étiquetée)
et FORMULE. Le module ne lit la base QUE pour le log de coût et le cache.

### Clé / provider

- **Variable d'env : `ANTHROPIC_API_KEY`** (constante `ENV_KEY`, `core.py:38`). Jamais la
  valeur en clair. `has_key()` est le SEUL point de vérité (les modules l'importent d'ici).
- `provider_status()` → `provider = "anthropic"` si clé, sinon `"stub"`. Repli `degraded`
  flaggé (jamais silencieux). Diagnostic dans `_LAST_ERROR` / `last_error()`.

### Modèles (routeur par TÂCHE, `core.py:34`)

- `MODEL_FACTUAL = "claude-haiku-4-5-20251001"` — extraction, NL, filtres, factuel.
- `MODEL_REASONING = "claude-sonnet-4-6"` — raisonnement (faisabilité expliquée, synthèse).
- `PRICE` (`core.py:37`) : dict €/Mtoken indicatif (log, pas la tarification live).
- Alias côté surfaces : `ia.MODEL_NL = core.MODEL_FACTUAL`, `ia.MODEL_SYNTH = core.MODEL_REASONING`.
- `ai/agent.py` (pipeline legacy `analyze`) utilise `get_settings().ai_model`
  (défaut `claude-sonnet-4-6`, `config.py:63`) et `ai_provider` (défaut `stub`, `config.py:62`).

### Cache

- Table `ia_cache` (clé `(idu, run_label, question_hash)`, `core.py:296`). `cache_get` /
  `cache_put`. `ia_ask_quota` gère le quota par sujet/fiche.
- **`CONTEXT_VERSION = 4`** (`core.py:321`) — sel du hash de cache : tout changement de
  `fiche_ask._ask_context` / `_SYSTEM` DOIT le bumper, sinon un bugfix reste masqué par un
  cache périmé (garde-fou « bugfix masqué »). Historique v1→v4 documenté dans le code
  (v4 = ajout du champ `amenites`).

### Validation de sortie (hybride 1+3, `core.py:250`)

`validate_output(prose, context, ...)` — deux couches mécaniques HORS IA, avant renvoi client :
1. **Sources forcées** : chaque marqueur `⟨src:champ⟩` doit pointer un champ réellement
   présent au contexte ; sinon rejet. `require_sources` exige au moins un marqueur.
2. **Chiffres** : tout nombre de la réponse doit figurer (à tolérance de format) dans les
   valeurs du contexte ; un chiffre inventé → rejet. `strict_numbers=True` (réponses
   agrégées) lève la tolérance de taille 0-12 ; nombres de tournure (R+n, « 3 logements »,
   rang #n) tolérés par leur rôle. Garde-fou d'échelle k€/M€ borné aux valeurs ≥ 1000
   (évite le faux « 9999/1000 ≈ 10,2 »).

Grounding en entrée : `Fact` (valeur + provenance SOURCE/ESTIME/ABSENT) + `build_context`
(**liste blanche obligatoire** — tout champ hors `allowed_fields` refusé).

### Journalisation

Table **`ia_log`** (`core.py:95` ; DDL aussi dupliquée dans `ia.py`) : `kind, model, stub,
tokens_in, tokens_out, cout_eur`. `_log_cost` calcule le coût depuis `PRICE`. Table
`nl_query_log` (RGPD, anonyme) journalise les traductions NL et les out_of_scope.

### Appel unique

`complete(...)` (`core.py:367`) : routeur haiku/sonnet, `temperature=0.0` (QA stable),
timeout/retries centralisés, sérialisation SÛRE (`default=str` → plus de 500 Decimal),
`validate=`/`require_sources=`/`strict_numbers=` optionnels.

### Legacy `agent.py` / `schema.py` / `prompt.py`

Pipeline IA d'analyse de parcelle (Vague 1) : `StubProvider` (déterministe, dérive du
payload) + `AnthropicProvider` (API Messages). Sortie **validée contre `AI_OUTPUT_SCHEMA`**
(`schema.py`, jsonschema Draft2020-12, `opportunity_score_adjustment ∈ [-20, 20]`). Le stub
pose explicitement `opportunity_score_adjustment: 0` (« le stub ne corrige pas le score »).
`SYSTEM_PROMPT` (`prompt.py`) verbatim §9 — raisonne UNIQUEMENT sur le payload.

---

## 4. Arborescence commentée

### `src/labuse/api/`

| Fichier | `wc -l` | Rôle |
|---|---:|---|
| `__init__.py` | 1 | package |
| `app.py` | 2983 | **Monolithe FastAPI** : instance `app`, lifespan, 6 middlewares, montage front, 66 routes directes (parcelles, fiche, carte GeoJSON, stats, discover, shortlist, mutation, audit, filtres, signalements, alertes/veille, feedback, pipeline CRM). Assemble les fiches (`_build_fiche`, `_q_v2_fiche`, `_q_v2_where`, `_q_v2_list`, `_q_v2_stats`), les caches mémoire (`_mem_cached`, `_geojson_cached`). |
| `modules.py` | 1033 | **Modules-outils Vagues 1-4** (M01-M22) : division parcellaire (SQL PostGIS `ST_MaximumInscribedCircle`), patrimoine PM, radar/promesses/vélocité permis SITADEL, foncier fantôme, bailleur, courriers, due diligence, faisabilité M22. `division_compute`, `faisabilite_sens1`, `faisabilite_sens2`, `_diligence_dossier`. Aucun score modifié. |
| `ia.py` | 722 | **Copilote IA (Vague 2)** : recherche NL→filtres (`FILTER_SCHEMA`), entretien de cadrage projet (`ENTRETIEN_SCHEMA`), synthèse, pourquoi. Provider via `ai.core`. Stubs déterministes (`_stub_nl`, `_stub_programme`). Garde-fou opinion marché (`contient_opinion_marche`). |
| `enrichment.py` | 655 | **Bloc promoteur lazy** : altimétrie (RGE ALTI IGN), exposition, vue mer (ligne de vue 1D), profondeur de façade, PLU détaillé (GPU), propriétaire, réseaux. `altimetry`, `vue_mer`, `facade_depth`, `plu_detail`, `owner`, `networks`, `enrichment_cached`. Tout INDICATIF + SOURCÉ, jamais réglementaire. Seul module `api/` à sortir sur le réseau (httpx). |
| `export.py` | 499 | fiche → Markdown / HTML / one-pager A4 imprimable (`fiche_markdown`, `fiche_html`, `fiche_onepager`). |
| `protection.py` | 493 | anti-abus : `garde_protection` (middleware quota/rate-limit), défi arithmétique, gels MANUELS, watermarking d'export (`filigrane_export`, micro-variations de formatage). |
| `moteurs.py` | 443 | **Moteurs Vague 4** : M15 simulateur PLU, M16 assemblage, M17 ZAN (signal parcelle + conso ENAF), M18 baromètre foncier (+PDF fpdf2). Recalculs à blanc, jamais persistés. |
| `partners.py` | 440 | **Outils-à-clients Vague 5** : M19 matching terrain↔promoteur (`match_compatibilite`, `promoteurs_actifs` SITADEL), M20 pack apporteur (page publique HTML filigranée, `_points_cles`), M21 API partenaire (clé + quota). |
| `pdf_premium.py` | 408 | rendu PDF de la fiche premium (fpdf2, design system, `render_fiche_pdf`, `_LOGO_PTS`, palette MINT). |
| `segments.py` | 402 | API du moteur de segments Habitat : galerie de presets, query builder, export CSV/publipostage, admin presets. Mentions légales vérifiées Légifrance. Aucun SQL depuis texte client (registry). |
| `events.py` | 365 | événements/veille : flux, compteurs, détection de bascules, suivi de cible, veilles sauvegardées, digest hebdo (JSON + HTML email). |
| `projets.py` | 694 | **Projets (copilote-projet)** : objet persistant de l'entretien ; l'IA remplit la fiche, le serveur DÉRIVE filtres+programme (`derive_filtres`, `derive_programme`, `derive_sdp_besoin`). Parcours Tinder (statuts parcelle×projet), auto-CRM. Ouvrir = rejouer. |
| `ortho.py` | 305 | validation humaine des détections ortho (piscines/PV/végétation) : tirage de vignette, image OpenCV, verdict avec quota dur, page HTML. Badges équipements de fiche. |
| `assistant.py` | 293 | assistant « expliquer cette parcelle » : synthèse NL des forces/faiblesses. Clé `ANTHROPIC_API_KEY`, modèle surchargeable `LABUSE_ASSISTANT_MODEL` (défaut `core.MODEL_REASONING`). `is_configured`, `explain_parcel`. |
| `tiles.py` | 287 | tuiles vectorielles MVT (`ST_AsMVT`) : couche `parcels` (cache LRU, simplification par palier de zoom), overlays zonage PLU/PPR. `build_overlay_mvt`. |
| `pre_dossier.py` | 243 | pack pré-dossier PC en ZIP (CERFA 13406*17 pré-rempli, plan de situation, règles de zonage). Gating Intégral. |
| `protection` (voir ci-dessus) | | |
| `solaire.py` | 191 | Habitat Solaire : panneau fiche, parkings APER, toitures tertiaires, statut mesure fine (Google Solar en 501). `SOURCES` étiquetées, `purge_cache`. |
| `resume.py` | 180 | résumé humain d'une fiche dérivé de signaux DÉJÀ calculés (verdict/cascade/bilan/prospection). `build_resume`, `_synthese`, `_prochaine_action`. Aucune invention. |
| `auth.py` | 162 | auth pilote (mono-utilisateur) : cookie de session, `enabled`/`configured`/`token_ok`/`is_public`, page de login, anti-force-brute. Pas de route (utilisé par `_auth_guard`). |
| `pdf_projet.py` | 153 | rendu PDF du dossier projet (fpdf2, réutilise la palette de `pdf_premium`). `render_projet_pdf`. |
| `score_v2.py` | 153 | endpoints ADDITIFS lecture seule de `parcel_p_score_v2` (P95 < 200 ms) : score, liste, brûlantes, réserve, modèle. |
| `projet_schema.py` | 142 | module NEUTRE (casse le cycle `ia`↔`projets`) : `FICHE_SCHEMA`, `clean_fiche`, `derive_sdp_besoin`, `prune_to_schema`, constantes `CONTRAINTE_FLAG`/`TYPE_LABEL`/`M22_SURFACE_UNITE_M2`. |
| `nl_aggregate.py` | 137 | questions AGRÉGÉES (« combien de brûlantes à X ») → COUNT/GROUP BY SQL sourcé. `is_aggregate`, `answer_aggregate`. |
| `dossier.py` | 115 | « dossier parcelle » PDF pour abonnés (dépend du module Flash, sinon 501). Quota mensuel. |
| `nl_semantics.py` | 98 | validation SÉMANTIQUE (schéma ≠ sens) : anti-mistraduction (passoire → risques), `criteres_non_appliques`. `check_semantics`. |
| `voisinage.py` | 94 | ensembles contigus autour d'une parcelle (promoteur regarde des assiettes). `compute_voisinage`, `_zone_tokens`. |
| `courrier.py` | 89 | API courrier postal (statut/envoi/demande/suivi), délègue à `../courrier.py` (Merci Facteur PRO). |
| `export_commun.py` | 82 | primitives partagées : disclaimer réglementaire, `SOURCES_ATTRIBUTION`, `adresses_ban`/`format_adresse`, `pied_de_page_pdf`. |
| `fiche_ask.py` | 271 | barre de fiche (M11-A) : `POST /parcels/{idu}/ask` — grounding liste blanche (`_ask_context`), validation de sortie, cache déterministe, quota 20/j. |

### `src/labuse/ai/`

| Fichier | `wc -l` | Rôle |
|---|---:|---|
| `__init__.py` | 8 | package (expose `get_provider`, `analyze`) |
| `core.py` | 406 | **SOCLE 0** : clé/statut, modèles, grounding (`Fact`/`build_context`), validation (`validate_output`), cache (`CONTEXT_VERSION`, `cache_get/put`), log (`ia_log`), appel unique (`complete`). |
| `nl_segments.py` | 202 | NL → filtres du moteur de segments : le LLM reçoit uniquement question + registry (aucune donnée base), retourne un JSON validé clé par clé. `traduire`. |
| `agent.py` | 162 | providers legacy `StubProvider`/`AnthropicProvider` + `analyze` (Vague 1), sortie validée `AI_OUTPUT_SCHEMA`. `_reunion_flags`. |
| `schema.py` | 73 | `AI_OUTPUT_SCHEMA` borné + `validate_ai_output` (garde-fou anti-hallucination structurel). |
| `prompt.py` | 67 | `SYSTEM_PROMPT` (verbatim §9) + `payload_from_outcome` (assemble faits + sources). |

### `src/labuse/flash/`

Module **Flash** = rapport de faisabilité PDF pour **UNE** parcelle, vendu à l'unité.
Anti-cannibalisation (mandat §2) : aucune exploration, aucun classement, aucun comparatif
multi-parcelles. **Aucune route HTTP dans `flash/`** — le générateur est appelé en
dépendance souple par `dossier.py`, `pre_dossier.py`, `partners.py`.

| Fichier | `wc -l` | Rôle |
|---|---:|---|
| `__init__.py` | 9 | expose `generate_flash_report`, `TEMPLATE_VERSION` |
| `data.py` | 474 | collecte des données du rapport — sections CONDITIONNELLES (détection `information_schema`, s'omet proprement). `collect_report_data`, `_parcelle`, `_constructibilite`, `_risques`, `_marche`, `_dynamique`, `_terrain`, `_sources`. Valeurs absolues, aucun classement. |
| `report.py` | 112 | générateur HTML/CSS (Jinja2) → PDF (WeasyPrint), template versionné (`TEMPLATE_VERSION = "1.0"`), génération idempotente (< 30 s). `render_report_html`, `generate_flash_report`, `storage_dir`. |
| `carte.py` | 131 | plan de situation : fond OSM/ortho IGN (tuiles positionnées + contour SVG), cache disque. `build_situation_map`, `_fetch_tile`. |

**Stripe : ABSENT du code.** Aucune référence Stripe/checkout/paiement dans `flash/**` ni
`api/**` (grep vide) — cohérent avec l'état « Lots 2-4 stoppés, STRIPE_SECRET_KEY manquante ».
Le paiement à l'unité annoncé par le module n'est pas branché dans ce périmètre.

---

## 5. APIs / services externes appelés

| Service / domaine | Où | Détail |
|---|---|---|
| **Anthropic (Claude)** | `ai/core.py`, `ai/agent.py`, `api/assistant.py` | API Messages. Clé `ANTHROPIC_API_KEY`. Modèles haiku-4-5 / sonnet-4-6. Import paresseux du SDK `anthropic`. |
| **RGE ALTI (IGN Géoplateforme)** | `api/enrichment.py:35` | `https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json` via httpx (altimétrie, vue mer, façade). |
| **Géoplateforme IGN — WMTS/WMS** | `flash/carte.py:67`, `enrichment.py` | ortho `data.geopf.fr/wmts` (`IGN_ORTHO_URL`), `data.geopf.fr/wms-r/…`. |
| **OpenStreetMap tuiles** | `flash/carte.py:21` | `https://tile.openstreetmap.org/{z}/{x}/{y}.png` (fond du plan de situation, cache disque + User-Agent). |
| **Remonter le Temps (IGN)** | `enrichment.py:55` | `https://remonterletemps.ign.fr/comparer` (lien deep, pas d'appel). |
| **Géoportail de l'urbanisme (GPU)** | `enrichment.py` (`plu_detail`, `_gpu_geom`) | prescriptions/zonage PLU détaillé. |
| **Merci Facteur PRO** | `../courrier.py` (`_envoyer_mercifacteur`) | courrier postal ; clés `LABUSE_MERCIFACTEUR_API_KEY/SECRET`. Sans compte → provider `stub` (aucun envoi, bouton masqué). Doc `merci-facteur.com/api/1.2`. |
| **Google Solar API** | `api/solaire.py:166` | mesure fine du toit — **non implémenté** (501 tant que `solar_api_key` absente). |
| **BAN (adresses)** | `api/audit.py` (via `../audit`), `export_commun.adresses_ban` | géocodage adresse → parcelle ; adresses postales (tables `adresses`/`adresse_parcelles`, ingérées). |
| **Légifrance** (liens) | `api/segments.py`, `moteurs.py` | URLs `legifrance.gouv.fr/codes/…` dans les mentions légales (pas d'appel). |

Sources de données non-API (en base, ingérées) : DVF, SITADEL, cadastre Etalab, OCS-GE,
Cartofriches, PVGIS, DGFiP (personnes morales), INSEE/RP2022, PLU/GPU, PPR, QPV/ANRU/SRU/PLH.

---

## 6. Métriques

- **Fichiers les plus longs** : `app.py` (2983 l, monolithe), `modules.py` (1033),
  `ia.py` (722), `projets.py` (694), `enrichment.py` (655), `export.py` (499),
  `protection.py` (493), `data.py` flash (474), `moteurs.py` (443), `partners.py` (440).
- **Densité de fonctions** : `app.py` = 112 `def`/`async def` ; `modules.py` = 25 ;
  `ia.py` = 23 ; `enrichment.py` = 20.
- **Fonctions/blocs SQL notables** (longs par nature) : `modules.division_compute` (CTE
  PostGIS multi-niveaux, `modules.py:69`), `modules.velocite` (`modules.py:408`, ~72 l),
  `moteurs._barometre_data` (`moteurs.py:305`), `partners.share_public` (page HTML inline,
  `partners.py:302`, ~75 l), `app._q_v2_where`/`_q_v2_fiche` (constructeurs de requêtes).
- **TODO / FIXME / HACK / XXX / WIP** : **aucun** dans `api/`, `ai/`, `flash/` (grep vide).
  Les caveats sont exprimés en commentaires prose (« honnêteté », « à instruire ») et en
  disclaimers renvoyés au client, pas en marqueurs de dette.
- **Fichiers jamais importés** : aucun fichier `api/`/`ai/`/`flash/` n'apparaît orphelin —
  les 16 routers sont importés par `app.py` (via `from .X import router`), les helpers
  (`enrichment`, `export`, `resume`, `voisinage`, `assistant`, `export_commun`,
  `pdf_premium`, `pdf_projet`, `projet_schema`, `nl_aggregate`, `nl_semantics`) sont
  importés (souvent en import différé) par `app.py` ou entre eux ; `flash/*` par les 3
  consommateurs cités. `auth.py` n'expose pas de route mais est utilisé par le middleware.

---

## 7. Histoire (git)

| Périmètre | Dernier commit | Nb commits |
|---|---|---:|
| `src/labuse/api/` | 2026-07-20 14:40 | 244 |
| `src/labuse/ai/` | 2026-07-15 21:09 | 7 |
| `src/labuse/flash/` | 2026-07-15 21:42 | 6 |

(Repo : 877 commits au total.) `api/` est de loin le domaine le plus actif ; le socle `ai/`
et `flash/` sont plus stables (livrés mi-juillet, peu retouchés depuis).

---

## 8. Observations factuelles

- **`app.py` est un monolithe de 2983 lignes** portant 66 routes directes + tous les
  constructeurs de fiches/requêtes v2 + les caches mémoire — le plus gros fichier du domaine.
- **Deux modules PDF** : `pdf_premium.py` (fiche) et `pdf_projet.py` (dossier projet) ;
  `pdf_projet` réutilise la palette et le pied de page de `pdf_premium`. Un troisième chemin
  PDF passe par `flash/report.py` (WeasyPrint) réutilisé par `dossier.py` et `pre_dossier.py`.
- **Deux modules `nl_*`** : `nl_aggregate.py` (agrégats COUNT/GROUP BY) et `nl_semantics.py`
  (validation sens ≠ schéma), tous deux consommés par `ia.py`.
- **Deux couches IA coexistent** : le SOCLE 0 (`ai/core.py`, utilisé par `fiche_ask`, `ia`,
  `modules.faisabilite/explain`) et le pipeline legacy (`ai/agent.py` + `schema.py` +
  `prompt.py`, utilisé par `app.evaluate_one` et `assistant.py`). Deux jeux de constantes
  modèle : `core.MODEL_FACTUAL/REASONING` vs `config.ai_model`.
- **La DDL de `ia_log` est déclarée deux fois** : dans `ai/core.py:95` (`_log_cost`) et dans
  `api/ia.py:42` (`DDL_IA`), avec la même définition.
- **Aucune route dans `flash/`** : le module est une bibliothèque de génération, jamais
  montée en router ; Stripe n'y figure pas (paiement à l'unité non branché ici).
- **Import différé systématique** : les routers font `from .app import get_db as _g` et la
  plupart des dépendances lourdes sont importées dans le corps des fonctions (`from .modules
  import faisabilite_sens2`, etc.) pour casser les cycles `app ↔ modules/ia/projets`.
- **Un seul module `api/` sort sur le réseau** : `enrichment.py` (httpx vers IGN). `flash/carte.py`
  aussi (tuiles OSM/IGN). Le reste est SQL pur ou appels IA via `ai.core`.
- **Doctrine « l'IA ne touche aucun score » gravée en profondeur** : liste blanche de
  grounding, validation mécanique des chiffres, `CONTEXT_VERSION` anti-cache-périmé, stub
  qui pose `opportunity_score_adjustment: 0`, neutralisation d'opinion marché dans l'entretien.
- **Privacy récurrente** : personne morale nommée (public DGFiP/SIREN), particulier JAMAIS
  nommé — appliqué dans `modules`, `moteurs`, `partners`, `projets`, `duediligence`.
- Le middleware `_auth_guard` est enregistré APRÈS `garde_protection` mais s'exécute AVANT
  (convention Starlette « dernier enregistré = plus externe ») — commenté explicitement.
