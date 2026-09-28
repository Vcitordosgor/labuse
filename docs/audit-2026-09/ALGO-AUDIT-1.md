# ALGO-AUDIT-1 — Qui écoute quelle version de l'algo

- **Branche** `audit/algo-1` · worktree `~/Desktop/labuse-algo` · base `origin/main` `c4c5eafe` (« Merge origin/fix/tests-1 »)
- **Modèle** Opus · **lecture seule** (aucune écriture base, aucun run, aucune bascule, aucun correctif de code)
- **API de mesure** : servi sur `127.0.0.1:8625` (état réel) · bascule à blanc sur `127.0.0.1:8626` (`LABUSE_SERVED_RUN=q_v15`, process jetable)
- **Périmètre** : qui lit quelle version. Pas d'audit des valeurs (banc de cohérence), ni des sources, ni du modèle.

---

## 0. État servi réel (relevé le 28/09/2026)

| Brique | Pointeur (point de vérité) | Valeur servie aujourd'hui |
|---|---|---|
| Scoring / ancien classement (tier, rang) | `config/served_manifest.json → scoring_run`, lu vivant par `runs.current()` (`src/labuse/runs.py:49`) | **q_v11_m137** |
| Cascade / étage 0 (exclusions, motifs) | `manifeste.cascade_run()` (`src/labuse/manifeste.py:115`) — **le manifeste ne porte AUCUN champ `cascade_run`** → repli `runs.current()` | **q_v11_m137** |
| Division (candidats) | `manifeste.division_run()` (`src/labuse/manifeste.py:101`) | **q_v11_m137** |
| Score LABUSE (bandes A/B/C/D/0/NC + Signal) | `SCORE_LABUSE_RUN = os.environ.get("LABUSE_SCORE_RUN") or runs.current()` (`src/labuse/api/app.py:3230`, **figé à l'import**) | **q_v11_m137** |
| Résiduel / SDP / capacité | vue `parcel_residuel` → `WHERE run_seq = (SELECT run_seq FROM residuel_runs WHERE is_served)` | **run_seq 10** = « q_v15 assiette gabarit » |
| Tuiles carte | table matérialisée `mvt_parcels` (`mvt_meta.run_label`), bâtie par `tiles.build_mvt_table` | **q_v11_m137** (bâtie le 14/09/2026) |
| Front (bundle) | `SOURCE = VITE_RUN_LABEL`, injecté au **build** depuis `config/served_run.txt` (`frontend/vite.config.ts:8`) | **q_v11_m137** |

### Runs présents en base (ce qui est calculé, pas ce qui est servi)

- `parcel_p_score_v2` (tier/rang) : `q_v8_calibre*, q_v10_m129, q_v11_m137, q_v12, q_v13_sources1, q_v14, **q_v15**` — chacun 431 663 lignes.
- `dryrun_parcel_evaluations` (cascade) : jusqu'à `q_v13_sources1` — **PAS de q_v14 ni q_v15**.
- `score_labuse` (bandes/Signal) : **`q_v15` UNIQUEMENT** (431 663 lignes) + variantes dryrun. **Aucune ligne q_v11_m137.**
- `residuel_runs` : run_seq 1→10 ; `is_served = TRUE` sur **seq 10** seul.

### ⚠️ Divergence de pointeur constatée d'emblée

Le **manifeste** dit `residuel_run_seq: 8` (posé le 05/09/2026), mais la vue `parcel_residuel` sert **seq 10** (`is_served`, posée le 25/09/2026 par un `labuse residuel-serve` direct — `cli.py:2309` → `residuel_runs.set_served`, qui court-circuite le manifeste). Le point de vérité (manifeste) **ment** sur le résiduel réellement servi. Détail en §Écarts (E6).

---

## 1. Trois parcelles témoins

| Témoin | IDU | Rôle | tier servi (q_v11_m137) | tier candidat (q_v15) | score_labuse (q_v15) |
|---|---|---|---|---|---|
| W1 | `97408000AO1424` | reste écartée | `ecartee` (rang 302 316) | `ecartee` (rang 372 072) | bande 0, sdp 0, signal faible |
| W2 | `97415000EO0796` | la parcelle du Dossier (179 vs non-calculable) | `a_creuser` → « Sans signal » (rang 118 163) | `sans_signal` (rang 23 033) | bande **D**, score 23, **sdp 179**, signal faible |
| W3 | `97415000AX0990` | Priorité-équivalent au servi, bande A au candidat (choisie) | `chaude` → « À suivre » (rang 826) | `sans_signal` (rang 3 532) | bande **A**, score 81, sdp 1 619, signal faible |

*(q_v11_m137 stocke l'ANCIEN vocabulaire `brulante/chaude/a_creuser` ; `tiers_client.py` mappe pour l'écran : `chaude→À suivre`, `a_creuser→Sans signal`.)*

---

## 2. Tableau des consommateurs

Colonnes : **consommateur · écran/route · brique · ce qu'il lit · pointeur (fichier:ligne) · run lu aujourd'hui · bouge à la bascule à blanc · verdict.**
Bascule à blanc = process avec `LABUSE_SERVED_RUN=q_v15` (déplace `runs.current()`/`cascade()`/`division()` **et** `SCORE_LABUSE_RUN` puisque recalculé à l'import du process). Ne touche **PAS** la base (`residuel_runs.is_served`, `mvt_parcels`) ni le bundle front.

### Carte / tuiles / filtres

| Consommateur | Écran/route | Brique | Ce qu'il lit | Pointeur (fichier:ligne) | Run aujourd'hui | Bouge à blanc | Verdict |
|---|---|---|---|---|---|---|---|
| Tuiles vecteur parcelles | `/map/tiles/*` | ancien classement + résiduel (baked) | `mvt_parcels` (matérialisée) | `tiles.py:135` `runs.current()` **au build** ; le service lit la table telle quelle | q_v11_m137 (14/09) | **NON** (matérialisée — rebuild `build-mvt` requis) | suit le servi *(instantané figé)* |
| GeoJSON carte | `/map/parcels.geojson` | cascade + tier v2 | `dryrun_parcel_evaluations` + `parcel_p_score_v2` | `app.py:2855` `runs.cascade()` ; `_score_v2_run_id` (`app.py:2874` = `runs.current()`) | q_v11_m137 | OUI (serveur) / front épingle via `source=` | suit le servi |
| Filtre carte+liste / count | `/filtre`, `/filtre?idus=1` | cascade + tier v2 + Score LABUSE (filtre « classement ») | `dryrun` + `parcel_p_score_v2` + `score_labuse` | `app.py:2635-2705` (`source` param OU `runs.cascade()`) ; bandes via `SCORE_LABUSE_RUN` | q_v11_m137 | OUI (serveur) / front épingle | suit le servi |
| **Filtre Capacité (SDP)** | panneau Capacité | résiduel | `parcel_residuel` (`is_served`) | `app.py:1456,1581,2785` (lit la vue, aucun run_id) | **seq 10 (q_v15 assiette)** | **NON** (drapeau base, hors env) | résiduel servi par `is_served` (**hors pointeur scoring**) |
| Couches PLU/risques/etc. | `/map/tuyau/*` | — | `spatial_layers` (géométrie source) | `couches_tuyau.py:36` | — (sans run) | — | hors périmètre (aucune version d'algo) |
| Filtres sauvegardés | filtres/ | — | critères, pas un run | `filtres/` | — | — | hors périmètre (stocke des critères) |

### Fiche / Analyse / Copilote

| Consommateur | Écran/route | Brique | Ce qu'il lit | Pointeur (fichier:ligne) | Run aujourd'hui | Bouge à blanc | Verdict |
|---|---|---|---|---|---|---|---|
| Fiche — verdict/tier/rang | `/parcels/{idu}` | ancien classement | `parcel_p_score_v2` (via `verdict_servi`/`_q_v2_fiche`) | `app.py:5711` (`source` param sinon `runs.current()`) ; `_score_v2_run_id` | q_v11_m137 | **OUI** (W2 118 163→23 033, W3 826→3 532) | suit le servi |
| Fiche — carte « Analyse LABUSE » | `/parcels/{idu}` | Score LABUSE | `score_labuse` (bande/Signal/contributions) | `app.py:5716-5719` via `SCORE_LABUSE_RUN` (`app.py:3230`) | q_v11_m137 → **NULL** (table n'a que q_v15) | **OUI** (None → bande A/D/0) | suit le servi *(invisible tant que servi absent de `score_labuse`)* |
| Fiche — cascade servie (motifs/§sources) | `/parcels/{idu}` | cascade | `dryrun_parcel_evaluations` | `served_cascade.py:36` `runs.cascade()` | q_v11_m137 | OUI | suit le servi |
| Fiche — Potentiel (SDP résiduelle) | `/parcels/{idu}` | résiduel | `parcel_residuel` (`is_served`) | `app.py:3120` (vue) | **seq 10 (q_v15)** | **NON** | résiduel servi par `is_served` |
| Fiche — §10 « plancher/vendable créé » | `/parcels/{idu}` | moteur live | `surface_plancher_m2` (recalcul) | `faisabilite/engine.py:estimate_capacity` via `potentiel.py:bloc_potentiel` | — (sans run) | **NON** | **calcul parallèle** (moteur live, hors run) |
| Écran Analyse (ventilation bandes + Signal) | `/analyse` (agrégat) | Score LABUSE + cascade + tier | `score_labuse` + `dryrun` + `parcel_p_score_v2` | `app.py:3754-3790` `SCORE_LABUSE_RUN` ; `runs.cascade()` ; `_score_v2_run_id` | q_v11_m137 → bandes **NULL** | OUI | suit le servi |
| Recherche IA / NL aggregate | `nl_aggregate` | tier + cascade | `parcel_p_score_v2` + `dryrun` | `nl_aggregate.py:74,82` `runs.current()`/`cascade()` | q_v11_m137 | OUI | suit le servi |
| Score V2 API | `/v2/score`,`/v2/liste`,`/v2/modele` | ancien classement | `parcel_p_score_v2`/`p_score_v2_runs` | `score_v2.py:64` `_served_run()`=`runs.current()` | q_v11_m137 | OUI | suit le servi |
| Scoreur d'adresse | `/scoreur-adresse` | ancien classement | `parcel_p_score_v2` | `scoreur.py:106,112` `runs.current()` | q_v11_m137 | OUI | suit le servi |
| Comparateur | `/comparateur` | ancien classement | agrégats commune | `comparateur.py:56` `runs.current()` | q_v11_m137 | OUI | suit le servi |
| Copilote / assistant / fiche-ask | `/parcels/{idu}/ask`, copilote_v2 | ancien classement | `verdict_servi` | `fiche_ask.py:268,338` `runs.current()` | q_v11_m137 | OUI | suit le servi |
| Anti-fiche | interne | cascade | `dryrun` | `anti_fiche.py:55` `runs.cascade()` | q_v11_m137 | OUI | suit le servi |

### Projets & outils

| Consommateur | Écran/route | Brique | Ce qu'il lit | Pointeur (fichier:ligne) | Run aujourd'hui | Bouge à blanc | Verdict |
|---|---|---|---|---|---|---|---|
| **Projets — compteur communes** | `/projets` | ancien classement | `parcel_p_score_v2.tier` | `projets.py:153` `runs.current()` | q_v11_m137 | **OUI** | **suit le servi** |
| **Projets — liste de cadrage** | `/projets` (list) | cascade + tier v2 | `dryrun` + `parcel_p_score_v2` | `projets.py:265,288-292,321` `runs.cascade()` + `_score_v2_run_id` | q_v11_m137 | **OUI** | **suit le servi** |
| Blocs fonciers | Blocs | ancien classement + résiduel | `parcel_p_score_v2` + `parcel_residuel` | `blocs.py`/`blocs_documents.py` `runs.current()` + vue | q_v11_m137 / seq 10 | tier OUI / SDP NON | mixte (tier suit servi ; SDP par `is_served`) |
| Scan patrimoine / rareté | rareté | ancien classement | `parcel_p_score_v2` | `rarete.py:69` `runs.current()` | q_v11_m137 | OUI | suit le servi |
| Étude de zone / mon secteur | mon_secteur | tier + résiduel + DVF | `parcel_p_score_v2` + `parcel_residuel` | `mon_secteur.py` `runs.current()` + vue | q_v11_m137 / seq 10 | tier OUI / SDP NON | mixte (suit le servi + résiduel `is_served`) |
| Gabarit | gabarit | moteur live | recalcul enveloppe | `gabarit/`, `faisabilite/engine.py` | — | NON | calcul parallèle (moteur live) |
| Densifier / renouvellement | renouvellement | cascade | `dryrun` | `renouvellement.py:280` `runs.current()`/param | q_v11_m137 | OUI | suit le servi |
| Modules (faisabilité/scoreur) | `/modules/*` | cascade | `dryrun` | `modules.py` `runs.cascade()` | q_v11_m137 | OUI | suit le servi |
| Carnet | carnet | ancien classement | `parcel_p_score_v2` | `carnet.py:75,98` `runs.current()` | q_v11_m137 | OUI | suit le servi |

### Exports

| Consommateur | Route | Brique | Ce qu'il lit | Pointeur (fichier:ligne) | Run aujourd'hui | Bouge à blanc | Verdict |
|---|---|---|---|---|---|---|---|
| **Dossier — couverture « SDP RESTANTE »** | `/dossier/{idu}.pdf` | résiduel | `parcel_residuel.sdp_residuelle_m2` | robinet `regles/sdp_residuelle_m2.py` → `app.py:2785` (vue `is_served`) | **seq 10 (q_v15)** → **179 m²** | **NON** | résiduel servi par `is_served` |
| **Dossier — §10 « plancher/vendable créé »** | `/dossier/{idu}.pdf` | moteur live | `surface_plancher_m2` (None) → phrase d'absence | `faisabilite/engine.py:estimate_capacity` ; absence `declarations/fiche/reste_a_declarer.yaml:152` | — (sans run) → **« non calculable »** | **NON** | **calcul parallèle** (moteur live) |
| Dossier — verdict/tier (miroir fiche) | `/dossier/{idu}.pdf` | ancien classement | `parcel_p_score_v2` | miroir de la fiche (`source` sinon `runs.current()`) | q_v11_m137 | OUI | suit le servi |
| Flash | `/dossier/{idu}.pdf` (alias) | = Dossier | idem Dossier | `dossier.py:97` (redirige builder Dossier) | idem | idem | suit le servi |
| Financier / bilan | `/financier/*.pdf` | recalcul | questionnaire + `program.surface_plancher` | `exports/financier_bilan.py`, `exports/builder.py:200-210` | — | NON | calcul parallèle (bilan recalculé) |
| Apporteur / brief | `/brief-apporteur/*.pdf` | miroir fiche | payload fiche | `exports/builder.py:477` | q_v11_m137 | OUI | suit le servi |
| Pré-dossier PC | `/pre-dossier/{idu}.zip` | miroir fiche | `parcel_fiche()` | `pre_dossier.py` → `runs.current()` | q_v11_m137 | OUI | suit le servi |
| Documents / export générique | `/parcels/{idu}/export` | robinets | `registre` + robinets | `exports/archive.py`, `robinet_fiche.py` | q_v11_m137 | OUI | suit le servi |

### Veille / digests / CRON / Pilotage

| Consommateur | Route/CRON | Brique | Ce qu'il lit | Pointeur (fichier:ligne) | Run aujourd'hui | Bouge à blanc | Verdict |
|---|---|---|---|---|---|---|---|
| Veille suivis (`evaluer-suivis`) | CRON | ancien classement | `parcel_p_score_v2` | `events.py` `runs.current()` | q_v11_m137 | OUI | suit le servi |
| `detect-events` (bascule du score) | CRON | ancien classement (Δ runs) | `p_score_v2_runs` / `parcel_p_score_v2` | `jobs_impl.py:213-231` `runs.current()` (`run_to`) + run précédent lu en base (`run_from`) | q_v11_m137 vs préc. | OUI | suit le servi |
| Digest Radar | CRON | cascade | `event_log` | `events.py:1136` `runs.cascade()` | q_v11_m137 | OUI | suit le servi |
| Page Flux / Circuit | `/admin/flux`, `/admin/circuit` | pointeur servi | `p_score_v2_runs`, manifeste | `flux.py:137` `runs.current()`/`precedent()` | q_v11_m137 | OUI (affiche le pointeur vivant) | suit le servi |
| Cohérence | interne | pointeur servi | `p_score_v2_runs` | `coherence_flux.py:43` `runs.current()` | q_v11_m137 | OUI | suit le servi |
| Dashboard / Pilotage | `/admin/dashboard` | comparaison runs | runs, cascades | `dashboard.py` `runs.current()` vs `precedent()` | q_v11_m137 | OUI | suit le servi |
| Garde de bascule (baseline) | admin | ancien classement | comparaison | `bascule_gardes.py:35` `TARGET="q_v8_calibre"` **en dur** | q_v8_calibre | NON | **en dur (ancien)** |
| Tête de lignée (défaut) | admin | ancien classement | défaut | `scoring/lignee_tete.py:25` `"q_v8_calibre"` **en dur** | q_v8_calibre | NON | **en dur (ancien)** |
| Événements démo | `/events/*demo` | démo | `parcel_p_score_v2` | `events.py:644-816` `"q_v2_demo"` **en dur** | q_v2_demo | NON | **mort** (démo seulement) |
| CLI `--signal-recette` | `labuse` (CLI) | Signal | défaut | `cli.py:2219` `"q_v15"` **en dur** | q_v15 | — | **en dur (candidat)** — outil admin |
| CLI lancement de run | `/admin/flux/run/lancer` | build | préfixe label | `dashboard.py:1665` `"q_v12"` (préfixe si recette=q_v12) | — | — | admin (fabrication de run) |

---

## 3. Mesure sur les 3 témoins — servi (8625) vs bascule à blanc q_v15 (8626)

| Grandeur (route fiche) | Ce qu'elle lit | W1 `…AO1424` | W2 `…EO0796` | W3 `…AX0990` | Bouge ? |
|---|---|---|---|---|---|
| tier / label (ancien classement) | `parcel_p_score_v2` | Écartée→Écartée | Sans signal→Sans signal *(a_creuser→sans_signal)* | **À suivre→Sans signal** *(chaude→sans_signal)* | **OUI** |
| rang | `parcel_p_score_v2` | 302 316→372 072 | 118 163→**23 033** | 826→**3 532** | **OUI** |
| Score LABUSE bande | `score_labuse` | **None→0** | **None→D** | **None→A** | **OUI** (None → valeur) |
| Score LABUSE Signal | `score_labuse` | None→faible | None→faible | None→faible | **OUI** |
| SDP résiduelle (cover Dossier) | `parcel_residuel` (`is_served` seq 10) | None | **179→179** | 1 619→1 619 | **NON** |
| Surface plancher créée (§10) | moteur live `bloc_potentiel` | None | None→None | None→None | **NON** |

**Lecture** : tout ce qui passe par `runs.current()`/`runs.cascade()`/`SCORE_LABUSE_RUN` **bascule ensemble**. Le Score LABUSE, aujourd'hui **NULL partout** (le run servi q_v11_m137 n'a aucune ligne dans `score_labuse`), **s'allume d'un coup** sous q_v15. Ce qui **ne bouge pas** : la SDP résiduelle (pilotée par le drapeau base `is_served`, déjà sur seq 10 = assiette q_v15) et le moteur live §10 (recalcul indépendant de tout run).

---

## 4. Réponses nominatives

### 4.1 Que lit **Projets** ?

**Projets suit le servi.** Deux lectures, toutes deux résolues côté serveur au run servi (pas d'ancien classement figé, pas de `source=` du bundle) :

1. **Compteur d'opportunités par commune** → `parcel_p_score_v2` filtré `run_id = runs.current()` et `tier = ANY(TIERS_SERVABLES)` — `src/labuse/api/projets.py:151-153`.
2. **Liste de cadrage** → `dryrun_parcel_evaluations` à `runs.cascade()` jointe à `parcel_p_score_v2` à `_score_v2_run_id(db)` (= `runs.current()`, épinglé au label servi, `app.py:2874`) — `src/labuse/api/projets.py:265,288-292,321`.

Vérifié à la bascule à blanc : les rangs/tiers des témoins bougent (W3 826→3 532). **Le soupçon « Projets lit l'ancien classement » n'est pas confirmé dans le code actuel** : Projets lit bien le run servi et basculerait avec lui. *(La seule réserve est commune à tous les écrans front : le bundle épingle `SOURCE` au build — cf. E5 — mais les endpoints Projets résolvent le run côté serveur, ils ne dépendent pas de `source=`.)*

### 4.2 D'où viennent les deux SDP du Dossier de `97415000EO0796` (179 m² en page de garde, « non calculable » au §10) ?

**Ce sont deux grandeurs distinctes, produites par deux surfaces différentes, qui ne lisent pas le même run — et qui se contredisent.**

- **Couverture, « SDP RESTANTE » = 179 m²** = la donnée `sdp_residuelle_m2`, lue dans la **vue servie pré-calculée `parcel_residuel`** (= `parcel_residuel_runs` où `run_seq = is_served` = **seq 10**, étiqueté « q_v15 assiette gabarit », batch du 25/09). Robinet `regles/sdp_residuelle_m2.py`, requête `app.py:2785`. C'est un **instantané figé** ; `cause IS NULL` pour cette parcelle → 179 m² s'affiche. *(seq 8 donnerait 178 ; la valeur est calculée dans les deux cas.)*
- **§10, « Surface de plancher créée » = « non calculable »** = la donnée `surface_plancher_m2`, **recalculée EN DIRECT à la requête** par le moteur commun `faisabilite/engine.py:estimate_capacity` (via `potentiel.py:bloc_potentiel`). Pour cette parcelle elle renvoie `None` → la **phrase d'absence** `declarations/fiche/reste_a_declarer.yaml:152` (« Surface de plancher non calculable (zone non constructible ou capacité nulle) ») s'imprime.

En clair : la couverture affiche un **résiduel servi** (batch matérialisé, assiette du run **candidat** q_v15), pendant que le §10 affiche le verdict d'un **moteur live** qui, lui, renvoie « nul ». Les deux ne sont reliés à **aucun** des deux par le pointeur de scoring q_v11_m137. *(Aggravant, hors périmètre « versions » mais utile au banc : le moteur live se contredit même avec lui-même — la route `/modules/faisabilite/{idu}/scenario` renvoie « jusqu'à 338 m² de plancher · 2-3 logements » pour la même parcelle, là où `bloc_potentiel` de la fiche renvoie `None`.)*

---

## 5. Écarts, triés par gravité

### Visible client

- **E1 — Dossier : 179 m² (couverture) vs « non calculable » (§10) sur la même page.** Deux producteurs de SDP se contredisent (`parcel_residuel` servi seq 10 ↔ moteur live `bloc_potentiel`). *Correction : faire lire au §10 la même source servie que la couverture (`parcel_residuel`), ou marquer la couverture « estimé (run résiduel 10) » et n'exposer qu'un seul producteur de SDP.*
- **E2 — Le résiduel/SDP servi partout (carte, fiche, filtre Capacité, Dossier, outils) est calculé sur l'assiette du run CANDIDAT (`seq 10 = q_v15`), alors que le classement servi est q_v11_m137.** Mélange de runs en production, visible sur tout chiffre de SDP. *Correction : re-servir un résiduel du run servi (`residuel-serve <seq q_v11_m137>`), ou officialiser q_v15 par une bascule complète.*
- **E3 — Tuiles carte figées au 14/09 (`mvt_parcels` = q_v11_m137) avec une SDP baked antérieure à seq 10.** La SDP au survol de la carte ≠ la SDP de la fiche (seq 10). *Correction : rejouer `build-mvt` après tout `residuel-serve` ; inscrire `mvt_parcels` au périmètre de la bascule.*
- **E4 — « Classement LABUSE » (bandes A/B/C/D) invisible partout aujourd'hui** (fiche/Analyse/Comparer = NULL), car le run servi q_v11_m137 n'a aucune ligne dans `score_labuse` (seul q_v15 en a). *Correction : décision produit — soit basculer q_v15 (les bandes s'allument d'un coup), soit calculer `score_labuse` pour le run servi. Ce n'est pas un bug de câblage (le pointeur est correct), c'est un run manquant sous le run servi.*
- **E5 — Le bundle front épingle `SOURCE` au build** (`vite.config.ts:8`). Une bascule backend (`served_run.txt`) **sans `npm run build`** laisse carte/fiche/liste demander l'ancien run via `source=`. *Correction : verrouiller le rebuild front dans la procédure de bascule (déjà documenté `api.ts:16`, non automatisé).*

### Admin seulement

- **E6 — Le manifeste ment sur le résiduel servi : `residuel_run_seq=8` alors que `is_served=10`.** Pire, `bascule_flux.basculer()` réécrit `is_served` **depuis** `residuel_run_seq` du manifeste (`bascule_flux.py:311-315`) → la **prochaine bascule ferait silencieusement reculer le résiduel de seq 10 → seq 8**. *Correction : réaligner le manifeste (`residuel_run_seq=10`), et interdire `residuel-serve` direct hors bascule (ou le faire passer par le manifeste).*
- **E7 — `SCORE_LABUSE_RUN` est figé à l'import (`app.py:3230`), pas relu à chaud.** Une bascule sans redémarrage du process laisse l'Analyse/la fiche sur l'ancien run Score LABUSE (le reste du produit, lui, bascule à chaud via `runs.current()`). *Correction : le rendre dynamique (fonction lue par requête, comme `runs.current()`), et propager aux 5 sites (`app.py:3530,3770,3790,5719,7516`).*

### Code mort / résiduel

- **E8 — `bascule_gardes.py:35` `TARGET="q_v8_calibre"` et `scoring/lignee_tete.py:25` `"q_v8_calibre"` en dur** — baseline/défaut pointant un run qui n'est plus servi. *Correction : pointer `runs.current()`/paramétrer, ou retirer si mort.*
- **E9 — `events.py:644-816` `"q_v2_demo"` en dur** — chemin démo uniquement, inoffensif en prod. *Correction : aucune (ou isoler hors prod).*
- **E10 — Défauts CLI `cli.py:2219` `"q_v15"`, `cli.py:4652` `"m36"`, `dashboard.py:1665` `"q_v12"`** — outils admin de fabrication de run, jamais servis. *Correction : vérifier qu'aucun ne fuit vers une surface servie (aucun constaté).*

---

## 6. Conclusion

**Non — une bascule `q_v15` ne fait pas tout basculer d'un coup.** Le scoring (ancien classement tier/rang), la cascade, la division et le Score LABUSE basculent **ensemble** dès lors qu'ils lisent `runs.current()`/`runs.cascade()`/`SCORE_LABUSE_RUN` (à condition de redémarrer le backend — E7 — **et** de rebuilder le front — E5). Restent à la traîne, pilotés hors du pointeur de scoring : **(a)** le résiduel/SDP servi (drapeau base `residuel_runs.is_served`, aujourd'hui déjà sur `seq 10 = q_v15` par un `residuel-serve` manuel, pendant que le manifeste dit encore `8` — E2/E6) ; **(b)** les tuiles carte matérialisées (`mvt_parcels`, rebuild `build-mvt` requis — E3) ; **(c)** le moteur live §10/gabarit/bilan (recalcul indépendant de tout run — E1). Le câblage « lit le servi » est sain presque partout ; les vraies fractures sont un **résiduel servi séparément et désynchronisé du manifeste**, et un **Score LABUSE dont le run servi n'existe pas en table**.

---

*Méthode : 5 sous-agents de traçage (carte/fiche/projets-outils/exports/veille-cron) recoupés et corrigés contre la base (l'un annonçait la cascade en `q_v13_sources1` — faux : le manifeste ne porte pas de `cascade_run`, repli `runs.current()`=q_v11_m137). Mesures live sur `parcel_residuel`, `score_labuse`, `parcel_p_score_v2` (psql, `statement_timeout` 60 s) et sur deux process API (servi 8625 / `LABUSE_SERVED_RUN=q_v15` 8626). Dossier PDF de W2 réellement rendu et lu (`pdftotext`).*
