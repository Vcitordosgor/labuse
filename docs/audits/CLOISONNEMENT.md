# Cloisonnement des comptes — audit d'isolation multi-tenant

> **Audit `audit/panorama` · M7 · Lecture seule · 2026-07-23**
> Prolongement de l'audit IDOR : prouver que deux comptes clients sont hermétiques. Aucune écriture code/DB. Verdict : **le socle de cloisonnement est solide et bien conçu (projets/CRM/veilles étanches), mais 5 surfaces déclarées ou de fait « données client » ignorent `compte_id` et fuiteront dès la première licence multi-comptes réelle.**

---

## 1. Modèle de tenant

**Clé de tenant : `compte_id` (int ; `NULL` = bucket pilote/démo hérité).**

| Table | Fichier | Rôle |
|---|---|---|
| `comptes` | `src/labuse/comptes.py:37` | comptes clients (`id`, `nom`, `plan`, `statut` CHECK 5 valeurs, `sieges`, `stripe_*`) |
| `utilisateurs` | `comptes.py:53` | `compte_id NOT NULL` FK cascade, `email UNIQUE`, `hash` argon2id, `role` CHECK(admin\|titulaire\|membre\|qa) |
| `sessions_auth` | `comptes.py:71` | token **haché SHA-256** (jamais en clair), FK cascade utilisateur |
| `evenements_compte` | `comptes.py:79` | journal d'audit par compte |

**Doctrine** (documentée `src/labuse/api/tenant.py:1-26`) : les données **publiques** (parcelles, scoring, fiches, DVF, PLU) ne sont **jamais** scopées (analyse partagée, c'est le produit) ; seules les données **privées client** portent `compte_id`.
`SCOPED_TABLES = ("projets", "pipeline_entries", "saved_searches", "saved_filters", "signalements")` (`tenant.py:26`).

**Filtrage NULL-safe** : `scope_clause()` = `compte_id IS NOT DISTINCT FROM :cid` (`tenant.py:70`) — un compte ne voit que le sien ; le pilote (`NULL`) voit le bucket hérité. Un futur compte A (cid=1) ne verra jamais les lignes `NULL` ni celles de B.

**Injection du tenant** : middleware `_auth_guard` (`app.py:182`) → un lookup DB/requête (`auth.session_info` → `comptes.session_utilisateur`, `comptes.py:226`) pose `request.state.compte_id`. Chaque handler relit via `current_compte(request)` (`tenant.py:63`). Défense en profondeur : le statut du **compte** est recoupé à chaque requête → coupe si `suspendu|resilie|invite` (`comptes.py:238`).

### Vérification schéma (`\d`, psql)

| Table | `compte_id` | NOT NULL | FK cascade |
|---|:--:|:--:|---|
| `projets` | ✅ | ✅ | `fk_projets_compte` |
| `pipeline_entries` | ✅ | ✅ | + `UNIQUE (compte_id, parcel_id)` |
| `saved_searches` | ✅ | — | ✅ |
| `saved_filters` | ✅ | — | ✅ |
| `signalements` | ✅ | — | ✅ |
| `projet_parcelles` | ❌ | — | scopé **indirectement** via `projet_id → projets` |
| `event_log` | ❌ | — | **notifications non attribuées** (§2) |
| `watched_parcels` | ❌ | — | **suivi de cible non attribué** (§2) |
| `flash_commandes` | ❌ (par conception) | — | ressource à jeton, hors compte connecté |

---

## 2. Filtrage des requêtes — route par route

### ✅ Bien cloisonné (preuves file:line)

- **`projets.py` — tous les `/{pid}` passent par `_projet_or_404`** (`projets.py:509`) qui applique `_scope` (`compte_id IS NOT DISTINCT FROM cid`, `projets.py:29`) et lève **404** (jamais 403 — ne confirme pas l'existence). Couvre GET/PATCH/DELETE `/{pid}`, `/{pid}/rejouer`, `/proposer`, `/parcelles`, `/carte/{idu}`, `/parcelle/{idu}`, `/chercher-plus`, `/ajouter`, et **`/{pid}/export.pdf`** (l'export PDF est borné au compte). `/fusionner` revalide chaque id.
- **`projet_parcelles`** (sans `compte_id`) : scopé transitivement — chaque accès passe par un `projet_id` déjà validé, ou `WHERE projet_id = ANY(:ids)` avec `:ids` pré-filtré. **Isolation solide.**
- **CRM `pipeline_entries`** (`/carnet`, `app.py:3040-3142`) : chaque lecture/écriture filtre `compte_id` et vérifie l'ownership avant mutation. La contrainte `UNIQUE (compte_id, parcel_id)` (`tenant.py:49`) remplace l'ancien `UNIQUE(parcel_id)` — **corrige un SEC-IDOR profond** (une parcelle ne vivait que dans UN pipeline global).
- **Veilles `saved_searches`** (`events.py:291-311`) : GET/POST/DELETE scopés. OK.
- **Flash (jeton, hors compte)** : `/flash/telecharger` → lookup par `token_hash = sha256(token)` + `expire_at > now()` (jeton 32 octets, **non énumérable**). `/flash/statut` par `stripe_session_id`. OK.
- **Onboarding** `/onboarding/paiement` : `compte_id` dérivé d'un **jeton HMAC signé** (`compare_digest` + expiry), pas d'un query param. OK.
- **`carnet.py`** : ne lit que des tables publiques → pas de scoping requis (conforme doctrine).

### 🔴 Fuites inter-comptes confirmées (vérifiées à la main)

| # | Surface | Constat | Localisation |
|---|---|---|---|
| **1** | `signalements` (POST/GET) | `signalements ∈ SCOPED_TABLES` mais l'INSERT **ne pose pas** `compte_id` (naît `NULL`/global) et le SELECT **ne filtre pas** → un compte voit les signalements de tous | `app.py:2636`, `app.py:2645` |
| **2** | `signalements` (export CSV) | même SELECT non scopé → export CSV de tous les comptes | `app.py:2660` |
| **3** | `saved_filters` (GET/POST/DELETE) | `saved_filters ∈ SCOPED_TABLES` mais aucune route ne filtre/pose `compte_id` ; `DELETE /filters/{id}` **sans clause d'ownership** → suppression du filtre d'autrui en devinant l'`id` (**IDOR d'écriture**) | `app.py:2587-2607` |
| **4** | `event_log` (la « cloche ») | table **sans `compte_id`** ; `GET /events`, `/events/count`, `POST /events/{id}/read`, `/events/read-all` globaux ; la détection batch lit pipeline/veilles sans scope et écrit des events non attribués | `events.py:56-252` |
| **5** | `watched_parcels` | table **sans `compte_id`** ; `GET/POST /events/watch/{idu}` → une parcelle suivie par A est visible/togglable par B (**fuite d'intention commerciale**) | `events.py:267-281` |

**Nuance** : `segments/export` (`segments.py:242`) n'est **pas** une fuite — presets = templates partagés, export sur parcelles publiques. Conforme.

---

## 3. État global partagé / caches

**Aucun cache ne mélange de données client entre comptes.**
- `lru_cache` (geo, config, communes, loyers, règles PLU…) : `maxsize=1` sur données de **référence publiques**, jamais par compte.
- `_MEM_CACHE` / `_geojson_cached` (`app.py:369-456`) : clés = dimensions **publiques** (`demo-status`, `ban-ready`, `stats/commune`, geojson par `(commune,run)`). Aucune clé projet/pipeline/compte.
- `protection.py:120` (fenêtres rate-limit, gels) : clés = `sujet` (IP/fiche), anti-abus.
- `banquier.py:459 _PDF_JOBS` (clé jeton), `tiles.py:156 _CACHE` (clé géo publique).

**Verdict : aucun bleed inter-comptes par état mémoire.**

---

## 4. Admin (Vic)

- **Identification** : `role='admin'` dans `utilisateurs` (`comptes.py:59`), créé hors ligne par CLI `creer_admin` (`comptes.py:287`), `statut='actif'`, jamais suspendu par Stripe.
- **Privilèges** : le `role` remonte en session **mais aucune route HTTP ne branche sur `role`/`is_admin`** (grep : zéro occurrence dans `api/`). L'admin n'a **aucun chemin de lecture inter-comptes élevé** via l'API. Les actions admin (invitation, suspension, réactivation, effacement RGPD) sont **CLI uniquement** (`comptes.py:287-357`).
- **Traçabilité** : chaque action → `audit()` → `evenements_compte` (`comptes.py:102`). L'effacement RGPD **anonymise** l'audit avant de perdre les id (`comptes.py:347`).
- **`acces_gels`** (`protection.py:58`) : gels **anti-abus** (sujet=IP/fiche), **pas** un journal d'admin de comptes — à ne pas confondre.

---

## 5. Preuves DB (lecture seule)

| Mesure | Valeur |
|---|---|
| Comptes | **11** |
| Les 5 statuts (CHECK) | `invite, actif, paiement_requis, suspendu, resilie` — présents : `invite=5, suspendu=3, resilie=3` (comptes de test onboarding) |
| Utilisateurs | 7 (6 titulaire actif, 1 invite) — **0 `role='admin'`** en base (admin CLI non créé sur cette instance) |
| `projets` | 7 lignes, **toutes `compte_id NULL`** (bucket pilote) |
| `pipeline_entries` | 26 lignes, **toutes `compte_id NULL`** |
| `projet_parcelles` | 97 (scopées via projet) |
| `flash_commandes` | 3 (`en_attente=1, generee=2`) |
| `event_log` / `watched_parcels` | 18 / 3 — tous non attribués (attendu, tables sans compte_id) |

`NOT NULL` confirmé sur `projets.compte_id` et `pipeline_entries.compte_id` → aucune future ligne client sans tenant sur ces deux tables. **Les `NULL` actuels ne fuient pas** : ce sont le bucket pilote hérité, aucun vrai compte client n'a encore écrit.

---

## Scénario « A ne peut pas atteindre B »

- **Projets / CRM / veilles** : `A` requête `GET /projets/42` (à `B`). `_projet_or_404` exécute `... WHERE id=42 AND compte_id IS NOT DISTINCT FROM :cid_A` → 0 ligne → **HTTPException(404)**. Idem PATCH/DELETE/export/parcelles. **Isolation prouvée par le code.**
- **signalements / saved_filters / event_log / watched_parcels** : le check d'ownership est **absent** → `A` lit/écrit/supprime les données de `B` (ou du bucket global). Masqué aujourd'hui (tout `NULL`/pilote, mono-utilisateur), **fuitera dès la première licence multi-comptes**.

---

## Reliquats à trancher (pour le mandat de correction)

1. **`signalements`** — poser `compte_id=:cid` à l'INSERT + `AND compte_id IS NOT DISTINCT FROM :cid` aux SELECT/export. (`app.py:2636,2650,2671`)
2. **`saved_filters`** — scoper `GET/POST/DELETE /filters` + ownership sur le DELETE (IDOR écriture). (`app.py:2587-2607`)
3. **`event_log`** — décider le modèle par-compte (une bascule/BODACC sur une parcelle du pipeline de A ne regarde pas B) → colonne `compte_id` + refonte détection batch. (`events.py:56-252`)
4. **`watched_parcels`** — ajouter `compte_id` (le suivi de cible fuit l'intention). (`events.py:267-281`)
5. **`_counts_by_projet`** (`projets.py:334`) — lit tous les `projet_parcelles` sans scope ; re-filtré en aval (pas de fuite exploitable) mais à corriger par hygiène.
6. **Admin** — `role` remonté mais jamais utilisé pour gater une route : prévoir un contrôle explicite si un back-office admin arrive.

> Les points 1–4 concernent des tables **déclarées scopées** (`SCOPED_TABLES`) ou clairement à données d'intention client, dont les routes ignorent `compte_id`. **Ce sont les bloquants avant bascule multi-licence.**

*Fin M7.*
