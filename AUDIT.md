# AUDIT QUALITÉ — LA BUSE

Audit réalisé sur l'app réelle qui tourne (base Saint-Paul, sous-ensemble urbain borné :
3 000 parcelles ingérées, 27 opportunités / 2 888 à creuser / 44 exclues / 41 faux positifs).
Objectif : justesse métier d'abord, puis robustesse. **Aucune correction appliquée** — diagnostic seul.

Échelle : 🔴 Critique (verdict faux / crash en usage normal) · 🟠 Majeur · 🟡 Mineur · 🔵 Cosmétique.

---

## Verdict global

**NON « sain » pour être présenté comme FIABLE en l'état — 2 corrections de justesse métier requises avant** :
1. la couche ENS flague des parcelles terrestres avec une **réserve MARINE** (contrainte non pertinente) ;
2. les **risques (PPR/Géorisques) ne sont jamais vérifiés** et ne sont **pas signalés au bandeau**.

En revanche le **cœur du moteur est solide** : 0 violation d'invariant, règle d'or tenue, géométrie 2975/4326 saine, anti-hallucination IA OK, 47 tests verts, lint vert, 0 secret en dur.
→ **Montrable en démo** avec le cadrage « sous réserve » déjà en place, **mais pas à vendre comme verdict fiable** tant que les deux points 🟠 ci-dessous ne sont pas traités.

---

## ✅ Ce qui est sain (vérifié)

- **Invariants de cohérence** (sur dernier verdict/parcelle) — tous à **0** :
  aucune `opportunite` portant un HARD_EXCLUDE ; aucune `opportunite` avec complétude < 50 (règle d'or) ;
  aucune exclusion sans HARD_EXCLUDE tracé ; aucune `opportunite` avec opp < 65 ; aucun score NULL ;
  aucune parcelle évaluée sans lignes de cascade ; aucune `exclue` avec opp > 0.
- **Règle d'or** : complétude < 50 plafonne bien à `a_creuser` ; l'opportunité n'apparaît jamais sans la complétude (fiche : double score systématique, badge « sous réserve »).
- **Géométrie** : SRID 4326 partout, 0 géométrie invalide (`ST_IsValid`), surface stockée == `ST_Area(2975)` (aire en degrés ~1e-6, donc bien mesurée en 2975, pas en degrés), centroïde/bbox présents.
- **Trait de côte** : ne flague QUE le littoral (lon des flaggées 55.268–55.282 vs ensemble 55.265–55.315).
- **Forêt** : « Forêt Domaniale de Saint-Paul » réelle, 54 exclusions légitimes (subtype `domaniale`).
- **SAR** : correctement `UNKNOWN` sur les 3 000 parcelles + listé au bandeau « couches manquantes ».
- **Anti-hallucination IA** (provider stub) : payload 100 % PASS → `reunion_specific_flags=[]`, `blocking_or_risk_signals=[]` (rien d'inventé) ; payload avec SOFT_FLAG SAFER → signal correctement cité.
- **Robustesse API (entrées invalides)** : 404 propres (IDU inexistant/malformé, feedback/evaluate sur IDU inconnu), 422 propres (format export hors `md|html`, verdict feedback hors énum), commune inconnue → liste/`stats` vides (pas de crash).
- **Veille** : 1er run = photo de référence (0 alerte) ; **2e run sans changement → 0 delta** (pas de faux signal).
- **Feedback** : sur parcelle **exclue** → no-op correct (reste `exclue`, opp 0).
- **Tests** : 47 verts. **Lint** : ruff vert. **Secrets** : aucun en dur (clé Anthropic lue via env). **TODO/FIXME** : aucun.

---

## 🔴 Critique
Aucun verdict faux systémique ni crash en usage normal détecté dans le cœur du moteur.
(Les deux 🟠 de justesse métier ci-dessous touchent la *lecture* des verdicts ; à traiter en priorité.)

---

## 🟠 Majeur

### M1 — La couche ENS flague des parcelles terrestres avec la réserve naturelle **MARINE**
- **Où** : `src/labuse/ingestion/layers_ingest.py:330` (`_PROTECTED`, ligne 333 `patrinat_rnn:rnn`) → `ingest_espaces_proteges` (l.341) ; couche `src/labuse/cascade/layers/phase1.py` (`EnsLayer`).
- **Constat** : la seule RNN de La Réunion est la **Réserve Naturelle Marine**. Les 2 polygones ingérés en `ens` totalisent **3 996 ha**, soit plus que l'emprise étudiée (2 650 ha) → polygone essentiellement marin. Il flague **142 parcelles côtières** en `ens: SOFT_FLAG/moyen` (« Espace protégé réglementaire — restriction »), soit **−10 d'opportunité** sur du foncier terrestre où la protection marine ne s'applique pas.
- **Reproduire** : fiche d'une parcelle côtière → ligne cascade `ens: SOFT_FLAG` ; `SELECT ST_Area(ST_Transform(ST_Union(geom),2975))/10000 FROM spatial_layers WHERE kind='ens'` → 3 996 ha.
- **Gravité** : 🟠 (verdict faussé à la baisse sur ~142 parcelles ; SOFT, pas HARD).
- **Correction proposée** : restreindre les espaces protégés à leur **part terrestre** (intersection avec un masque terre, ou exclure les réserves marines `marin=1`), ou requalifier ce flag. Vérifier aussi APB/conservatoire littoral au même titre.

### M2 — Les **risques (Géorisques/PPR) ne sont jamais intégrés** à la cascade, et **absents du bandeau**
- **Où** : aucune fonction d'ingestion ne remplit les `spatial_kind` `ppr`/`georisque_alea` (cf. `layers_ingest.ingest_layers`) ; `CRITICAL_LAYERS` (`src/labuse/api/app.py:35`) ne contient pas `risques`.
- **Constat** : `risques` est `UNKNOWN` sur **100 %** des parcelles (3 000) → aucune exclusion **PPR-rouge** (inconstructible) ne peut se déclencher. Or Géorisques est marqué **`connecte`** dans la page Sources (API joignable) alors qu'il **n'alimente aucun verdict**. Le bandeau « verdicts partiels » ne liste que **SAR** — un utilisateur en déduit que les risques **ont** été vérifiés.
- **Reproduire** : toute fiche montre `risques: UNKNOWN "Risques Géorisques/PPR non ingérés"` ; `/coverage` → `missing = ["SAR …"]` (risques absent de la liste).
- **Gravité** : 🟠 (omission d'une couche excluante majeure + sur-confiance induite ; mitigée par le badge « sous réserve » présent sur chaque opportunité).
- **Correction proposée** : (a) ajouter `risques` (et idéalement `abf`) à `CRITICAL_LAYERS` pour qu'il figure au bandeau ; (b) ingérer un proxy risque exploitable (AZI/zonage Géorisques) ou afficher explicitement « risques non vérifiés » ; (c) aligner le statut `data_sources` de Géorisques (« joignable » ≠ « exploité dans la cascade »).

### M3 — 500 sur `limit` négatif (2 endpoints)
- **Où** : `src/labuse/api/app.py:183` (`parcels_geojson`, `limit:int`) et `:345-346` (`list_signals`, `limit:int`) → `LIMIT :lim` reçoit la valeur brute.
- **Reproduire** : `GET /map/parcels.geojson?limit=-5` → **500 Internal Server Error** ; `GET /signals?limit=-5` → **500**. (`LIMIT` négatif = erreur Postgres non capturée.)
- **Gravité** : 🟠 (techniquement un crash ; mais uniquement sur entrée absurde *manuelle* — l'UI n'envoie jamais de `limit` négatif).
- **Correction proposée** : `limit: int = Query(60000, ge=0, le=...)` (FastAPI → 422 propre) ou `max(0, limit)`.

### M4 — La suite de tests **détruit la base applicative**
- **Où** : `src/labuse/ingestion/demo_saint_paul.py:83-84` (`reset_demo` → `TRUNCATE … RESTART IDENTITY CASCADE`) appelé par la fixture `client` de `tests/test_api.py` ; `tests/conftest.py` (`engine`) pointe sur **la même base** que l'app.
- **Reproduire** : ingérer Saint-Paul (3 000 parcelles), lancer `pytest`, puis `GET /stats` → **tout à 0** (vérifié pendant cet audit : la base est passée de 3 000 parcelles à 0).
- **Gravité** : 🟠 (aucun verdict faux, mais piège d'exploitation : lancer les tests efface les données ; en CI il faut une base jetable).
- **Correction proposée** : base/ď schéma de test dédié (`LABUSE_TEST_DATABASE_URL`), ou rendre tous les tests `db` transactionnels avec rollback (comme `db_session`), et **ne jamais `TRUNCATE`** une base non-test.

### M5 — Les `faux_positif_probable` ne sont **jamais affichés** sur la carte
- **Où** : `src/labuse/api/web/index.html:32` (`#filter-statuses` ne propose que 3 cases : opportunite/a_creuser/exclue) ; `src/labuse/api/web/app.js:31` (`passesFilter`) ; légende `index.html:63` affiche pourtant « Faux positif ».
- **Constat** : `passesFilter` exclut tout statut non coché ; il n'existe **aucune case** pour `faux_positif_probable` → ces 41 parcelles sont invisibles sur la carte ET la liste, **même toutes cases cochées** (vérifié : `fp_passe_filtre=False`).
- **Reproduire** : ouvrir l'app, cocher les 3 cases → les 41 faux positifs n'apparaissent pas ; pourtant la légende les annonce.
- **Gravité** : 🟠 (incohérence carte/légende ; une catégorie de verdict est masquée).
- **Correction proposée** : ajouter une case « Faux positif » (et « Non évaluée ») au filtre, ou retirer l'entrée de légende.

---

## 🟡 Mineur

- **m1** — `GET /discover?limit=-5` → **200** mais `survivors[:-5]` (slice négatif) retire silencieusement les 5 dernières au lieu de valider/clamp. `app.py:317`. Corr : `Query(ge=1)`.
- **m2** — **5 parcelles « slivers » < 2 m²** (min 0,8 m²) : micro-parcelles cadastrales réelles, surface affichée, non excluantes — vérifier que l'affichage (~1 m²) n'induit pas en erreur. (donnée, pas bug)
- **m3** — **ABF `UNKNOWN` sur 100 %** (0 servitude AC1 dans l'emprise) : cohérent mais non signalé (ABF hors `CRITICAL_LAYERS`). À regrouper avec M2.
- **m4** — Nom ENS générique « Réserve naturelle nationale — Réserve naturelle nationale » (champ `nom` non récupéré dans `ingest_espaces_proteges`) → fiche peu informative.

## 🔵 Cosmétique

- **c1** — Compteur « Survivantes classées **(80)** » = plafond d'affichage (`app.js:117` `.slice(0,80)`), pas le total réel des survivantes (~2 915) → libellé trompeur.
- **c2** — Forêt domaniale classée **`faux_positif_probable`** (`phase1.py:103` `kind="faux_positif"`) plutôt que `exclue` : une forêt domaniale est du domaine public (exclue), pas un « faux positif » géométrique. Décision produit à clarifier (cohérence sémantique des statuts).
- **c3** — Identifiants base par défaut `labuse:labuse@localhost` en clair (`config.py:28`) : acceptable en dev (non-secret), à documenter comme tel.

---

## Récap par priorité de correction
1. **M2** (risques au bandeau + statut Géorisques) — impact justesse/confiance le plus fort.
2. **M1** (ENS réserve marine) — verdicts côtiers faussés.
3. **M5** (faux positifs invisibles) + **M3** (500 sur limit négatif) — robustesse/cohérence UI/API.
4. **M4** (isolation des tests) — exploitation/CI.
5. Mineurs / cosmétiques.

Aucune de ces corrections n'a été codée — à toi de prioriser.
