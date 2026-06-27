# QA application LABUSE — post-homogénéisation totale (24/24) — ⏸️ **en attente de validation**

> QA **fonctionnelle complète** de l'app après la re-cascade des 24 communes au code courant `fb6a5478b2bf`.
> **Lecture seule** : aucune modif DB / code / config / backup, aucun commit. App démarrée pour les tests.
> **Conclusion : 🟢 GO (avec 2 points d'attention non bloquants)** — détails en fin de rapport.

## 1. Environnement

| Élément | État |
|---|---|
| `main` / `origin/main` | **`1ed56f5`** = origin ✅ · working tree clean |
| DB | accessible (`postgresql://labuse@localhost:5432/labuse`) |
| Disque | 3,0 G libres (93 %) |
| App | **non lancée → démarrée** (`labuse api`, `127.0.0.1:8000`) ; `env=local`, **auth désactivée**, `schéma=ok` |
| Démarrage | ~90 s (réconciliation `ensure_schema` au boot sur grosse DB — idempotente, sans modif data) |

## 2. Endpoints testés (~20, tous **HTTP 200**)

| Catégorie | Endpoints | Résultat |
|---|---|---|
| Santé | `/healthz`, `/health`, `/readyz`, `/demo-status` | OK — `/readyz` **ready=true** (schema ok, data ok) |
| Données | `/stats`, `/stats?commune=X`, `/communes/status`, `/coverage` | OK (cf. §3) |
| Carte | `/map/parcels.geojson`, `/map/bati`, `/map/permits.geojson` | OK — geojson + bâti (1,1 Mo) + permis |
| Parcelle | `/parcels`, `/parcels/{idu}`, `/parcels/{idu}/explain`, `/parcels/{idu}/export` | OK — fiche riche, export onepager |
| Métier | `/shortlist`, `/pipeline`, `/pipeline/meta`, `/demo` | OK |

## 3. Données globales — **cohérence DB confirmée**

| Indicateur | App (`/stats`) | DB | OK |
|---|---:|---:|:-:|
| Parcelles | **431 663** | 431 663 | ✅ |
| Opportunités | **9 103** | 9 103 | ✅ |
| Communes | 24 | 24 | ✅ |
| Gold / non-gold | 17 / 7 | 17 / 7 | ✅ |
| Parcelles *stale* (vieilles règles) | — | **0** | ✅ |
| `rules_version` (fiche parcelle) | **`fb6a5478b2bf`** | fb6a5478b2bf | ✅ |

## 4. Contrôles ciblés — communes sensibles (API `/stats?commune` ↔ DB)

| Commune | Statut | Opp API | Opp DB | Total API | Total DB | OK |
|---|---|---:|---:|---:|---:|:-:|
| Saint-Denis | gold | 70 | 70 | 38 138 | 38 138 | ✅ |
| Saint-André | gold | 56 | 56 | 22 600 | 22 600 | ✅ |
| Le Port | gold | 236 | 236 | 10 195 | 10 195 | ✅ |
| Saint-Pierre | gold | 1 380 | 1 380 | 42 425 | 42 425 | ✅ |
| Saint-Paul | gold (pilote) | 1 905 | 1 905 | 51 129 | 51 129 | ✅ |
| La Plaine-des-Palmistes | **non-gold** | 0 | 0 | 6 450 | 6 450 | ✅ |
| Sainte-Rose | **non-gold** | 9 | 9 | 6 287 | 6 287 | ✅ |

- ✅ **Tous les chiffres affichés = DB**, à l'identique.
- ✅ **Non-gold jamais présentées comme gold** (La Plaine = `partiel_evalue`, Sainte-Rose = `absent` ; les 5 gold = `gold`).
- ✅ **Cohérence verdict/score/PPR** (DB, sur 9 103 opportunités) : **0 opportunité avec score < 65**, **0 opportunité avec PPR fort** (toutes PASS/faible).
- ✅ Fiche parcelle Saint-Denis (`97411000AC0215`) : verdict `opportunité`, score 65, complétude 84, raisons PPR présentes, `rules_version=fb6a5478b2bf`, `evaluated_at` = 27/06 (re-cascade).

## 5. Vérification visuelle / fonctionnelle (screenshot)

**Screenshot capturé** : `qa_app_home.png` (Playwright/Chromium, `/app/`).
- App **rend parfaitement** : carte Leaflet (parcelles colorées par verdict, légende), **vue d'ensemble Saint-Paul = 51 129 parcelles · 1 905 opportunités · 15 397 à creuser · 1 537 exclues** (= exactement DB/API), filtres (Tout/Opportunité/À creuser/Écartée/Exclue), **shortlist promoteur** avec cartes parcelles (IDU, badge OPPORTUNITÉ, score, surface), actions (Auditer, Dessiner, Pipeline 4 suivis, Démo 8 cas), bandeau disclaimer.
- ⚠️ **L'app est verrouillée sur la commune pilote Saint-Paul** (`const COMMUNE = "Saint-Paul"`, app.js) — pas de sélecteur multi-commune. Les 23 autres communes (dont les re-cascadées) sont **accessibles via l'API** mais **non affichées dans le SPA**. La validation « visuelle » porte donc sur Saint-Paul (conforme) ; les autres sont validées par API (§4).

## 6. Anomalies

### 🔴 Bloquantes
**Aucune.** L'app et les données sont fonctionnelles et cohérentes post-homogénéisation.

### 🟠 Importantes (non bloquantes — surfaces auxiliaires, pas la donnée cœur)

1. **`/communes/status` périmé pour 4 communes non-gold.** Cilaos, Les Trois-Bassins, Sainte-Rose, Salazie y apparaissent **`etat=absent`, `parcelles=0`** alors qu'elles sont importées + évaluées en DB (Δ total 25 196 parcelles).
   - **Cause racine** : l'endpoint lit le **config statique `config/communes_gold_standard.yaml`** (`communes.status_list()`), **pas la DB live** — config jamais mis à jour après l'import de ces communes.
   - **Impact réel = FAIBLE** : cet endpoint **n'est pas utilisé par le SPA** (absent des routes fetchées ; panneau admin/monitoring seulement). L'app utilisateur s'appuie sur `/stats` (DB-live), correct. Données pleinement accessibles : `/parcels?commune=Sainte-Rose` → 6 287, `/map/parcels.geojson` → 6 283 features.
   - **Correctif suggéré (hors QA)** : mettre à jour `communes_gold_standard.yaml` (etat `absent`→`partiel_evalue`, `parcelles_en_base` réels) pour ces 4 communes.

2. **Conformité démo dégradée (2/8 parcelles vitrines Saint-Paul).** `/demo-status` → `ready_for_demo=False`. Le healthcheck est OK et le cache chaud (8/8), mais 2 parcelles de la démo guidée ne correspondent plus à leur scénario :
   - `97415000BV0912` : attendu `à creuser` (ER 81 + accès) → **`opportunité`** (score 67).
   - `97415000BH0283` : attendu `à creuser` (SAR compatible) → **`opportunité`** (score 70).
   - **Cause** : évolution du scoring (Saint-Paul re-cascadée au code courant) — ces 2 parcelles franchissent désormais le seuil 65. Pas une corruption : le scoring est cohérent ; c'est le **script de démo qui est figé** sur d'anciens verdicts.
   - **Correctif suggéré (hors QA)** : `labuse rebuild-demo --commune 97415` (régénère les attendus), ou revue produit de ces 2 cas.

### 🟢 Améliorations mineures
- Démarrage app lent (~90 s) : `ensure_schema` au boot sur la grosse DB. Acceptable ; pourrait être journalisé/optimisé.
- SPA mono-commune (pilote Saint-Paul) : si l'exposition multi-commune est souhaitée (les 24 sont prêtes en DB), câbler un sélecteur de commune (l'API `?commune=` et le bandeau de fiabilité non-gold existent déjà).

## 7. Conclusion — 🟢 **GO**

**L'homogénéisation totale n'a rien cassé.** L'app est fonctionnelle ; **toutes les données affichées sont cohérentes avec la DB** (global + 7 communes sensibles + cohérence verdict/score/PPR), sur les règles courantes `fb6a5478b2bf`. **Aucune anomalie bloquante.**

Deux points d'attention **non bloquants**, tous deux sur des **surfaces auxiliaires** (endpoint admin + démo guidée), **sans impact sur la donnée cœur ni l'app pilote**, et **fixables sans toucher la DB** (maj config + `rebuild-demo`).

> **Recommandation** : GO. Traiter les 2 points d'attention (config 4 communes + rebuild-demo) avant toute démo commerciale ou exposition multi-commune — sous décision/GO séparé.

---

### Provenance (lecture seule)
- Endpoints testés via `curl` sur `127.0.0.1:8000` (app démarrée pour la QA). Comparaisons DB via `psql` (read-only).
- Screenshot via `playwright screenshot` (Chromium `/opt/pw-browsers`). Aucune modif DB / code / config / backup. Rapport non commité.
