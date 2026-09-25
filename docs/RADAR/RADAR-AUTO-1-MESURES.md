# RADAR-AUTO-1 — Lot 0 · mesures préalables

Branche `feat/radar-auto-1` (depuis `audit/radar-1`) · worktree `~/Desktop/labuse-radar` · lecture seule pour ce lot.
Mesures reproductibles : `html_next.analyser` sur les deux pages réelles de Vic (dans `docs/RADAR/`), et requêtes PostGIS sur la base `labuse` (431 663 parcelles). Rien corrigé ; décisions notées pour les lots A–F.

Fichiers :
- **riche** = `docs/RADAR/Saint-Denis_toute_la_ville_-_leboncoin.html` (page 1, 2,04 Mo)
- **dégradé** = `docs/RADAR/Saint-Denis_toute_la_ville_-_page_2_-_leboncoin.html` (page 2 par URL, 1,63 Mo)

---

## 0.1 — Page 1 riche : `html_next.analyser` → 35/35 avec position et date ✅

`analyser(riche)` → **`mode: resultats`, `provenance: json_riche`, 35 records**. Source = `__NEXT_DATA__.props.pageProps.searchData.ads` (35 entrées).

**Le `searchData` porte la pagination** — décisif pour l'extension (Lot B) :

| Clé `searchData` | Valeur |
|---|---|
| `total` / `total_all` | **5 116** annonces sur la recherche île entière |
| `max_pages` | **100** |
| `pivot.page_number` | 1 |
| `pivot.ids_to_display` | les 35 `list_id` de la page |
| `total_active` / `total_inactive` / `total_pro` / `total_private` | présents |

**Couverture des champs (sur 35)** :

| Champ | n | Champ | n |
|---|---|---|---|
| `list_id`, `url`, `subject`, `prix`, `prix_m2`, `commune`, `zipcode`, **`lat`**, **`lng`**, **`source_position`**, `owner_type`, **`first_publication_date`**, **`index_date`**, `statut_portail` | **35** | `type` | 34 |
| `surface_hab` | 34 | `surface_terrain` | 20 |
| `district` | 30 | `owner_siren` | 30 |
| `pieces` | 29 | `chambres` | 26 |
| `annee_construction` | 15 | `expiration_date` | 3 |
| `dpe_classe` | 1 | `piscine` | 1 |

- **`source_position`** : **31 `city`** (position de quartier floutée) + **4 `address`** (point rue). → la quasi-totalité est au **quartier**, ce qui borne le rattachement automatique (0.3).
- **Dates réelles** : `first_publication_date` (nouveauté, fait foi) ET `index_date` (remontée) sur 35/35. Ex. `list_id 3187081805` : publié `2026-08-16 20:13:31`, remonté `2026-09-21 13:22:37`.
- **types** : 18 maison · 11 appartement · 5 terrain · 1 `None`.
- **communes** : 11 communes (Saint-Pierre 11, Saint-Denis 8, Saint-Paul 6…) — la recherche « île entière » brasse toute l'île, pas Saint-Denis seul.

> Le parseur lit **déjà** cette page sans modification. Le chemin `json_riche` est le régime **cible** de la passe « nouvelles » (Lot B.1).

---

## 0.2 — Obtenir la variante riche des pages suivantes

**Fait mesuré (2 fichiers de Vic, à ne pas re-démontrer)** : page 1 ouverte normalement = **riche** (`searchData.ads`) ; page 2 **ouverte par son URL** = **dégradée** (`__NEXT_DATA__` présent mais `props.pageProps` = `libertyData` seul, ni `searchData` ni `ad` — 40 `aditem_container`, ni position ni date). C'est un rendu SSR A/B servi au **premier hit d'URL**.

**Mécanisme retenu pour l'extension** : ne **jamais** charger une URL `?page=N` à froid. Ouvrir la recherche **page 1** normalement (rendu riche), puis avancer par la **navigation client du site** (clic « page suivante » / lien de pagination), qui est une transition Next.js côté client : la nouvelle page hydrate son `searchData` **dans le DOM vivant** (`window.__NEXT_DATA__` puis les mises à jour du store), sans re-déclencher le SSR dégradé. L'extension lira `searchData.ads` de la page **vivante**, jamais un HTML enregistré.

**Essai live** : un unique essai Playwright non-headless (3 pages, 6 s d'intervalle) est prévu, mais **il n'a PAS été lancé depuis ce worktree** — hitter leboncoin.fr depuis l'environnement d'audit déclenche quasi certainement DataDome et **contredit la doctrine « jamais de capture côté VPS »**. Conformément au mandat (« si DataDome bloque, la mesure se fait avec Vic à la recette. Ne pas insister »), **la confirmation live du clic « page suivante » = riche est reportée à la recette Lot F, sur le Mac de Vic.** La conception de l'extension (Lot B.1) repose sur l'asymétrie déjà prouvée par les deux fichiers ; si le clic-suivant s'avérait dégradé lui aussi, le repli est le même que pour toute page dégradée : accepter en `dom_degrade` (Lot A) et le dire.

---

## 0.3 — Terrains : candidates cadastrales dans le rayon du quartier

Sur les **20 annonces riches à surface de terrain**, requête = parcelles de la commune dont `surface_m2 = surface annoncée ± tol`, dans `ST_DWithin` **150 m** du point (quartier), tol ∈ {±1 %, ±3 %} (mêmes géométries que `rattachement_html`).

**Distribution du nombre de candidates :**

| candidates | 0 | 1 | 2 | 3 | 4 | 5 | 9 |
|---|---|---|---|---|---|---|---|
| **±1 %** | 12 | **3** | 3 | 2 | – | – | – |
| **±3 %** | 6 | 4 | 2 | 2 | 2 | 3 | 1 |

**3 uniques à ±1 %** (candidate unique = rattachable `probable (surface)`) :

| annonce | terrain annoncé | position | parcelle | contenance | écart |
|---|---|---|---|---|---|
| `3263159310` | 433 m² | Saint-Denis (city) | `97411000AS0747` | 437 m² | +0,9 % |
| `3136576468` | 508 m² | Saint-Paul (city) | `97415000ES0030` | 512 m² | +0,8 % |
| `3267786277` | 480 m² | Saint-Pierre (**address**) | `97416000EI1258` | 477 m² | −0,6 % |

**Décision — Lot D servi.** Des uniques plausibles existent (3 à ±1 %, écarts < 1 %). Le rattachement auto terrain utilisera **±1 %** (plus serré que le ±10 % du rattachement bâti, pour **garantir l'unicité** : à ±3 % l'ambiguïté explose — jusqu'à 9 candidates). Règle : **candidate unique à ±1 % dans 150 m → `probable (surface)` ; deux candidates ou plus → RIEN** (jamais une liste à trier). Bouton manuel « C'est cette parcelle » toujours disponible → `certain (manuel)`. La vérification ortho à l'œil des 3 uniques est reportée à la recette (Lot F) — la preuve quantitative (contenance à < 1 %) est acquise ici.

---

## 0.4 — Lecteurs des données `pige_*` : qui lit quoi, copros, libellé « demandé »

| Lecteur | Fichier | Lit | Copros `est_copro` | Libellé |
|---|---|---|---|---|
| **Onglet Marché** | `pige/marche.py:stats` | médianes €/m² **demandé** (terrain = prix/terrain ; bâti = prix/hab), comptes actives/nouvelles/retirées/vendues, délai médian, part particuliers ; `a_qualifier=false` | **INCLUS** (bâti = `maison∪appartement∪immeuble`, ligne 29) | « prix demandés (Radar) » à l'UI |
| **Fiche §annonces** | `api/app.py:_radar_annonces_block` (règle `radar_annonces_liste`) | biens validés rattachés à l'IDU, prix demandé, écart demandé/acté vs `v_parcel_dvf_last` | via `idu` (un appart rattaché apparaît) | « Prix demandés — jamais un prix LABUSE » |
| **Mon secteur** | `api/mon_secteur.py` | DVF médianes par type + annonces Radar actives rattachées dans 1 500 m, écart via `badges_pour_biens` | via rattachement | demandé/acté séparés |
| **Outil Communes (couverture)** | `registre/moteurs/commune.py:176` | `count(pige_biens)` = « radar_annonces » | tous | compteur de couverture, pas un prix |
| **Étude de zone** | `zone.py:446` | `count(pige_biens ⋈ parcels)` | tous rattachés | « annonces suivies par la pige (collecte manuelle) — jamais un compteur de marché » |
| **Veille promoteurs** | `api/veille_promoteurs.py:147` | biens `est_copro` rattachés → badge sur opérations | copros **seulement** (badge, aucun chiffre servi) | — |
| **Digests / cloche / veilles** | `pige/digests.py`, `pige/veille.py` | biens du jour matchant une veille | **EXCLUS** (`est_copro=false`, digests.py:81) | cartes mail |
| **Client (carte/liste)** | `pige/client.py` | biens servis | **EXCLUS** (`est_copro=false`, client.py:33) | pastille rattachement |
| **Exports** | `exports/{miroir,oracle_dossier,robinet_fiche}.py` | blocs fiche/dossier | via rattachement | — |
| **Signaux** | `pige/signaux.py` | `_ecart`, `badges_pour_biens`, `_dvf_bati`, `_ref_local` | — | « sous le marché » (demandé vs acté) |

**Constats pour Lot E :**
- La règle **copros = collecte totale, service filtré** est déjà propre : exclus de **carte / digests / veilles** (`client`, `digests`), **inclus** dans les **statistiques** de `marche.stats`. C'est exactement ce que demande le Lot E — pas de correction de fond nécessaire, seulement **consolidation**.
- La séparation **demandé (Radar) vs acté (DVF)** est **déjà étiquetée** partout (fiche, secteur, zone) : aucun lecteur ne « mélange » les deux aujourd'hui. Le risque à surveiller en Lot E est de **ne pas régresser** ces libellés.
- **Ce qui manque à `marche.stats`** pour couvrir la demande Lot E `radar_stats(commune, type)` : (a) une **signature paramétrée** par commune **et type** ; (b) la **part de baisses sur 30 j** (aujourd'hui absente — il y a retirées/vendues, pas le taux de baisse) ; (c) un **id de registre par chiffre**. → Lot E = extraire un cœur `radar_stats` réutilisable, l'appeler depuis `marche.stats` (écran inchangé) et l'exposer à la fiche §Marché / Communes.

---

## 0.5 — Jobs `radar-cycle` / `-dvf` / `-mensuel` : état et ce qui manque

Code présent dans `pige/cycle.py` (idempotent, zéro réseau) :

| Fonction | Fait | Wrapper `jobs_impl` | Entrée registre `jobs.py` |
|---|---|---|---|
| `run_quotidien` (`marquer_expirees` + `en_vente_longue` + `a_reverifier`) | expiration portail → `retiree` ; > 90 j → `en_vente_longue` ; > 60 j sans confirmation → `a_reverifier` | **`radar_cycle` existe** (`jobs_impl.py:159`) | **ABSENTE** |
| `run_dvf` (`matcher_dvf`) | rattaché Sourcé + mutation DVF [3;18] mois → `vendue` (+ délai, écart) | **manquant** | **ABSENTE** |
| `run_mensuel` (`qualifier_retiree_sans_vente`) | `retiree` rattaché > 12 mois sans vente DVF → `retiree_sans_vente` (cible Courrier) | **manquant** | **ABSENTE** |

**Preuve du non-branchement** : seul `_j("radar-cloche", …)` existe dans `jobs.py` (07:05). Le registre note explicitement (`jobs.py:429`) : *« Radar : PAS de job […] radar-cycle, radar-releves : retirés »*. Les commandes CLI existent (`radar-cycle-quotidien`/`-dvf`/`-mensuel`, `cli.py:3708+`) mais ne sont jamais appelées par la CRON.

**Ce qu'il manque pour planifier (Lot C)** :
1. deux wrappers `jobs_impl` (`radar_cycle_dvf`, `radar_cycle_mensuel`) sur le modèle de `radar_cycle` ;
2. trois entrées `_j(...)` au registre `jobs.py` avec cron (heure Réunion), `raison`, `test` et `touche="exploitation"` — quotidien pour `radar-cycle` (après la passe « nouvelles » du soir), après ingestion DVF pour `-dvf`, mensuel pour `-mensuel` ;
3. le déclencheur d'événements `baisse`/`hausse` (Lot C) s'ajoute à l'ingestion (comparaison de prix), pas au cycle.

---

## Décisions consolidées (entrée des lots A–F)

- **Lot A/B** : passe « nouvelles » sur la page 1 riche, avance par clic-suivant du site (0.2), s'arrête quand la dernière `index_date` de la page ≤ `derniere_capture_at − 1 h` ; `searchData.total`/`max_pages`/`page_number` servent les garde-fous et la détection « pages manquantes ». Repli `dom_degrade` accepté et **dit**.
- **Lot C** : planifier les 3 jobs cycle + événement baisse/hausse à l'ingestion ; `baisse_badge` (parsé, 11/40 sur le dégradé) cesse d'être jeté.
- **Lot D** : **servi**, rattachement terrain auto à **±1 %** unique dans 150 m, sinon rien ; bouton manuel partout ; niveau `certain`/`probable`/`quartier` affiché.
- **Lot E** : cœur `radar_stats(commune, type)`, apparts **inclus** en stats, baisses/30 j ajoutées, libellés « demandé (Radar) » / « vente (DVF) » préservés, un id de registre par chiffre.
