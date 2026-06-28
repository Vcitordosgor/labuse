# Audit complet LABUSE — code + app + UI + fonctionnalités

> Audit **lecture seule** : aucune modification de code/DB, aucune correction (rapport versionné
> docs-only après validation humaine). Réalisé le 2026-06-27 sur `main = 6bf9378…145ef61`
> (HEAD `145ef61`). DB applicative **non modifiée** (vérifiée avant/après).
> Méthode par fonctionnalité : **testé réellement** · **testé en env. safe (labuse_test)** ·
> **inspecté seulement** · **non testé car risqué (écrit en DB)**.

---

## 1. Résumé exécutif

**Verdict global : ✅ GO pour une démo promoteur (Saint-Paul) · ⚠️ ATTENTION avant production / multi-commune.**

LABUSE est **stable, cohérent et démontrable**. 483 tests passent, l'UI ne produit **aucune erreur
console locale**, les invariants métier sont **tous respectés** (0 opportunité sous le seuil, 0 PPR
fort, 0 stale), Radar Mutation est solide. Aucun **bug bloquant (P0)**.

Principaux risques (aucun bloquant pour une démo Saint-Paul) :
- **Frontend mono-commune** : `COMMUNE = "Saint-Paul"` est **codé en dur** (pilote). Les 23 autres
  communes sont en base mais **invisibles dans l'UI**. (P1 produit, attendu en pilote.)
- **`GET /parcels` (liste) se bloque** sur données réelles (pas de pagination + N+1) → timeout >45 s.
  **Non utilisé par le frontend**, mais joignable sans auth en local (P2 robustesse).
- **Auth désactivée en `env=local`** (défaut) : tous les endpoints d'écriture sont joignables sans
  authentification si déployé en local. Fail-closed en prod (bon). (P2 déploiement.)
- **`GET /parcels/{idu}/enrichment` ÉCRIT** (cache + `CREATE TABLE`) malgré un docstring « lecture
  seule » mensonger (P2 cohérence/REST).
- Plusieurs **endpoints de lecture lents** (`/map/bati` 11 s, `/demo-status` 6,4 s, `/stats` 2 s) —
  atténués par chargement asynchrone / cache (P3 perf).

---

## 2. Ce qui marche (validé)

- **Démarrage app** + `healthz`/`readyz` (200, `ready:true`, schéma+data OK).
- **Carte** Leaflet + parcelles colorées par verdict ; **fiche parcelle** complète (verdict, zonage,
  occupation, capacité, charge foncière, accordéon « dossier complet », synthèse IA).
- **Radar Mutation** de bout en bout : sidebar + filtre Prioritaire/Forte, bloc fiche (violet,
  distinct du verdict), **calque carte** (toggle, légende, clic→fiche), API `/mutation*`.
- **Coexistence verdict + mutation** lisible et sans confusion.
- **Filtres** (statut/KPI), **vues** (Radar / Shortlist / Pipeline en lecture), **exports** (GET md/
  html/onepager), **SPF letter** (texte public).
- **Robustesse API** : 404 (parcelle/commune inconnue), 422 (niveau/limit invalides) **tous corrects**.
- **Données métier** : 24 communes, 9 103 opportunités, 0 stale, invariants respectés.
- **Tests** : 483 passés (suite complète) ; `node --check app.js` OK.
- **0 erreur console locale**, **0 exception JS**, responsive **390/768/1440** sans overflow.

---

## 3. Ce qui ne marche pas / à surveiller

- **Bug bloquant (P0)** : aucun.
- **Bugs importants (P1)** :
  - *Frontend mono-commune* (codé en dur) — limite produit (attendu en pilote, mais bloquant pour
    vendre le multi-commune).
- **Bugs mineurs (P2/P3)** :
  - `GET /parcels` (liste) : timeout >45 s sur données réelles (no-limit + N+1) — **P2**.
  - Auth off en local par défaut — **P2 (déploiement)**.
  - `/enrichment` : GET qui écrit + docstring faux — **P2**.
  - Endpoints lents `/map/bati` (11 s), `/demo-status` (6,4 s), `/stats` (2 s) — **P3**.

---

## 4. Fonctionnalités testées

| Fonctionnalité | Bouton / Endpoint | Statut | Preuve | Commentaire |
|---|---|---|---|---|
| Santé | `/healthz` `/readyz` | ✅ testé réel | 200 / 200 (`ready:true`) | rapide |
| Stats dashboard | `/stats` | ✅ testé réel | 200, 1,95 s | lent (LATERAL) |
| Couverture | `/coverage` `/communes/status` | ✅ testé réel | 200 (289 ms / 106 ms) | OK |
| Carte parcelles | `/map/parcels.geojson` | ✅ testé réel | 200, 3,1 s, 28 Mo | gros payload |
| Carte bâti | `/map/bati` | ⚠️ testé réel | 200, **11,3 s** | lent (spatial, lazy) |
| Permis | `/map/permits.geojson` | ✅ testé réel | 200, 47 ms | OK |
| Fiche parcelle | `/parcels/{idu}` + clic carte | ✅ testé réel | 200, 346 ms ; fiche rendue | OK |
| Accordéon « dossier » | clic `.acc-head` | ✅ testé réel | s'ouvre | OK |
| Export | `/parcels/{idu}/export` | ✅ testé réel | 200 (md 118 ms) | lecture seule |
| Courrier SPF | `/parcels/{idu}/spf-letter` | ✅ testé réel | 200, texte public | sans nominatif |
| Shortlist | `/shortlist` + vue | ✅ testé réel | 200, 3,6 s | lent |
| Radar fiche | `/mutation/{idu}` | ✅ testé réel | 200, 25 ms | OK |
| Radar sidebar + filtre | `/mutation` + chips | ✅ testé réel | 200 ; prio 8 / forte 3 | cache chaud ~3 ms |
| Radar calque carte | `/map/mutation.geojson` + toggle | ✅ testé réel | 153 parcelles, légende, clic→fiche | froid 4,1 s / caché 8 ms |
| Filtres statut/KPI | boutons sidebar | ✅ testé réel | filtre carte+liste | OK |
| Légendes verdict + radar | — | ✅ testé réel | 2 légendes distinctes | OK |
| Vue Pipeline (lecture) | `/pipeline` `/pipeline/meta` | ✅ testé réel | 200 (16 ms / 8 ms) | lecture seule |
| Liste parcelles (API) | `/parcels` | ❌ testé réel | **timeout >45 s** | bug (cf. §6) |
| Suite de tests | pytest (labuse_test) | ✅ env. safe | **483 passed** | base de test dédiée |
| Auth/login | `/login` `/logout` | 🔍 inspecté | off en local, fail-closed prod | cf. §9 |

## 5. Fonctionnalités NON testées (et pourquoi)

| Fonctionnalité | Endpoint | Raison | Risque | Comment tester plus tard |
|---|---|---|---|---|
| Ajout pipeline / prospection | `POST/PATCH/DELETE /pipeline*` | **écrit en DB** | mutation `pipeline_entries` | env. test / transaction rollback |
| Auditer une parcelle | `POST /audit/reference|adresse|polygone` | **écrit en DB** (+ appels externes) | INSERT parcels/cascade/eval | DB de test + mocks réseau |
| Feedback | `POST /feedback` | **écrit en DB** | INSERT `parcel_feedback` | DB de test |
| Zones de veille / alertes | `POST /watch-zones`, `/alertes/*` | **écrit en DB** | INSERT `watch_zones`/`alertes` | DB de test |
| Filtres sauvegardés / bilan | `POST /filters`, `/bilan/params` | **écrit en DB** | INSERT `saved_filters`/`bilan_params` | DB de test |
| Ré-évaluation | `POST /parcels/{idu}/evaluate` | **écrit + recascade** | DELETE+INSERT cascade/eval | DB de test |
| Enrichissement « promoteur » | `GET /parcels/{idu}/enrichment` | **écrit un cache** | INSERT `parcel_enrichment` | exécuter avec `LABUSE_ENRICH_LIVE=0` |
| Explication IA | `GET /parcels/{idu}/explain` | **appel LLM externe + coût** | tokens Anthropic | clé de test / budget |
| Test connecteurs | `POST /sources/{id}/test` | **appel réseau externe** | — | env. réseau contrôlé |

> Note méthodo : la **suite de tests** couvre une partie de ces écritures en **base dédiée
> `labuse_test`** (rollback), donc le comportement est validé « en env. safe » même si non testé sur
> la base réelle.

## 6. Bugs détaillés

### BUG-1 — `GET /parcels` (liste) se bloque sur données réelles · **P2**
- **Repro** : `curl '/parcels?commune=Saint-Paul&limit=5'` → **timeout >45 s** (HTTP 000).
- **Attendu** : réponse rapide, paginée.
- **Observé** : ne répond pas (chargé toutes les parcelles de la commune).
- **Fichier** : `src/labuse/api/app.py:327-342` (`list_parcels`).
- **Cause** : (a) **aucune clause LIMIT** — le paramètre `limit` n'existe pas (mon `?limit=5` est
  ignoré) ; (b) **N+1** : `_latest_eval(db, p.id)` (`app.py:318`) appelé pour **chaque** parcelle →
  51 129 requêtes pour Saint-Paul, 431 663 sans filtre.
- **Impact** : **non utilisé par le frontend** (qui utilise `/map/parcels.geojson` + `/parcels/{idu}`),
  donc **aucun impact UI**. Mais joignable (sans auth en local) → peut **bloquer un worker** (mini-DoS).
- **Reco** : ajouter `LIMIT`/pagination + remplacer le N+1 par un `LEFT JOIN LATERAL` (comme `/stats`).

### BUG-2 — `GET /parcels/{idu}/enrichment` écrit en base (docstring faux) · **P2**
- **Observé** : un **GET** déclenche `CREATE TABLE IF NOT EXISTS` + UPSERT `parcel_enrichment` (et
  `parcel_vue_mer`). Le module `api/enrichment.py:9` affirme « Lecture seule, n'écrit rien » — **faux**.
- **Fichiers** : `api/enrichment.py:610-613` (CREATE TABLE), `:625-629` (INSERT cache), `:268-275`.
- **Cause** : cache-on-read ; `get_db()` (`app.py:131`) auto-commit via `session_scope` (`db.py:48`).
- **Impact** : un GET avec effet de bord (anti-pattern REST) ; un crawler/preview qui suit les liens
  écrit en base. Sans danger pour les données métier (table de cache séparée), mais **trompeur**.
- **Reco** : corriger le docstring ; idéalement isoler l'écriture (verrou/`ON CONFLICT`), ou exposer
  un flag lecture-seule.

### BUG-3 — Endpoints de lecture lents · **P3**
- `/map/bati` **11,3 s** (1,1 Mo, spatial), `/demo-status` **6,4 s**, `/stats` **2,0 s**,
  `/shortlist` 3,6 s, `/discover` 3,3 s, `/mutation` (froid) 4,1 s.
- **Impact** : la plupart sont **chargés en asynchrone** (carte/sidebar) ou **mémorisés** (mutation),
  donc tolérables. `/demo-status` et `/stats` sur le chemin du dashboard méritent un cache.
- **Reco** : cf. `RADAR_MUTATION_PERF_PLAN.md` (cache/index) ; idem pour `/stats` (déjà un LATERAL).

## 7. Performance

| Endpoint | Temps | Classe | Note |
|---|---|---|---|
| `/healthz` `/health` | 2–6 ms | rapide | — |
| `/readyz` | 0,8–4,4 s | acceptable | check data complet |
| `/parcels/{idu}` (fiche) | 346 ms | acceptable | — |
| `/mutation/{idu}` | 25 ms | rapide | — |
| `/mutation` (liste) | 4,1 s froid / ~3 ms caché | lent→rapide | cache TTL |
| `/map/mutation.geojson` | 4,1 s froid / 8 ms caché | lent→rapide | cache |
| `/map/parcels.geojson` | 3,1 s (28 Mo) | lent | gros payload, lazy |
| `/shortlist` `/discover` | 3,6 / 3,3 s | lent | — |
| `/stats` | 2,0 s | lent | LATERAL |
| `/demo-status` | 6,4 s | problématique | à cacher |
| `/map/bati` | 11,3 s | problématique | spatial, lazy |
| `/parcels` (liste) | timeout | **bug** | cf. BUG-1 |

**Démarrage app** : ~12 s (chaud) à ~90 s (froid, `ensure_schema` sur la base prod). Acceptable pour
un service long-vivant ; à surveiller si redémarrages fréquents.

## 8. Responsive

- **390 px / 768 px / 1440 px** : **aucun overflow horizontal**, fiche plein écran lisible sur mobile,
  sidebar et Radar Mutation lisibles, **aucun terme interdit** dans le DOM rendu.
- Screenshots : `audit_home_1440.png`, `audit_home_768.png`, `audit_home_390.png`.

## 9. Sécurité / RGPD

- **Auth** : `config.py:33` `env="local"` par défaut → `auth.enabled()` **False en local** sans mot de
  passe (`auth.py:40-44`). En `env!=local`, **fail-closed** (503 sans mot de passe, `app.py:123`).
  Session = cookie HMAC-SHA256 httpOnly/SameSite. **Risque** : déployé en local, tous les endpoints
  d'écriture sont **ouverts sans auth**. ⚠️ **vérifier `LABUSE_ENV` en déploiement.**
- **RGPD** : **conforme par conception**. Seules des **personnes morales** (DGFiP, Licence Ouverte) sont
  stockées (`parcelle_personne_morale`) — jamais de personne physique nominative. Les personnes
  physiques sont routées vers un **courrier SPF non nominatif** (`proprietaire_type.py`). `owner_name`
  (raison sociale, donnée publique) exposé via `/enrichment` uniquement ; carte/shortlist n'exposent
  que la **famille** (public/privé/inconnu).
- **Secrets** : **aucun en dur**. Uniquement lecture d'env (`LABUSE_AUTH_PASSWORD`, `LABUSE_SECRET_KEY`,
  `ANTHROPIC_API_KEY`) + fichiers `.example` à placeholders. URL DB par défaut = creds dev local.
- **Erreurs propres** : 404/422 corrects, pas de stacktrace exposée.
- **Exports** : `/export` et `/spf-letter` n'exposent **aucune** donnée nominative privée.
- **Point d'attention** : génération HTML d'export par f-strings (`api/export.py`) — risque XSS
  théorique si une note/valeur non échappée y était injectée (actuellement données contrôlées). P3.

## 10. Dette technique

- **`app.py` monolithique (1 434 lignes, ~49 endpoints)** sans séparation en routers. **HIGH**.
- **`cascade/layers/phase1.py` (660 lignes)** — 30+ règles de couches dans un fichier. **MED**.
- **`app.js` (2 942 lignes)** vanilla, template-literals, **`COMMUNE` codé en dur**. **HIGH (produit)**.
- **Poids Radar Mutation codés en dur** (`mutation.py:22-40`, « PLACEHOLDER à caler terrain »). **MED**.
- **`_clamp()` dupliqué** (`mutation.py` / `scoring/opportunity.py`). **LOW**.
- **Génération HTML par f-strings** (`export.py`) sans échappement systématique. **MED**.
- **Tests manquants** : exports HTML/SPF, écritures pipeline isolées, TTL d'enrichissement, perf.
- **0 marqueur TODO/FIXME** explicite (dette implicite documentée ci-dessus).

## 11. Plan d'action recommandé

- **P0 (immédiat)** : *aucun* — rien ne bloque.
- **P1 (avant démo large / client multi-commune)** :
  - Lever le **mono-commune frontend** (sélecteur de commune + config runtime) — sinon ne montrer que
    Saint-Paul.
  - Décider de la **perf froide** Radar Mutation (cf. perf plan : single-pass / index).
- **P2 (avant mise en ligne)** :
  - Corriger **BUG-1** (`/parcels` : LIMIT + suppression N+1) **ou** retirer l'endpoint s'il est mort.
  - **Forcer `LABUSE_ENV`/auth** en déploiement (jamais `local` exposé).
  - Corriger **BUG-2** (docstring + isolation de l'écriture du cache `/enrichment`).
- **P3 (amélioration)** :
  - Cacher `/demo-status` et `/stats` ; échapper le HTML d'export (`html.escape`/Jinja2) ;
    découper `app.py` en routers ; externaliser les poids mutation en YAML.

## 12. Conclusion

- **Montrable à un promoteur ?** **Oui** — sur **Saint-Paul**, l'app est stable, lisible, cohérente
  et prudente. Le pack démo + la QA démo sont prêts.
- **Radar Mutation montrable ?** **Oui** — fiche, sidebar, calque carte, légende, wording prudent,
  0 erreur console. Solide.
- **App stable ?** **Oui** — 483 tests verts, invariants métier respectés, UI sans erreur, données
  intactes.
- **À corriger avant une vraie vente** : (1) le **mono-commune** (si on vend au-delà de Saint-Paul),
  (2) **l'auth de déploiement** (ne pas exposer `env=local`), (3) **BUG-1 `/parcels`** (ou le retirer),
  (4) le **docstring/écriture `/enrichment`**, (5) la **perf froide** + cache des endpoints lents.

> **Verdict : GO démo Saint-Paul · ATTENTION avant production/multi-commune.** Aucun P0.
