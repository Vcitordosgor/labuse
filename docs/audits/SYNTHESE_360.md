# Synthèse 360° — audit panorama de LABUSE

> **Audit `audit/panorama` · Lecture seule stricte · 2026-07-23**
> Photographie de LABUSE sous 5 angles : accès extérieurs (M1), points manuels (M2), sécurité OWASP (M3), cloisonnement des comptes (M7), chiffres (M9). Aucune ligne de code/config/DB modifiée. Golden 116/116 (état intact). Vic lit et décide des suites.

**Les 5 rapports** :
- [`ACCES_EXTERNES.md`](ACCES_EXTERNES.md) — routes, sorties, webhooks, pare-feu
- [`POINTS_MANUELS.md`](POINTS_MANUELS.md) — ce qui exige un geste de Vic
- [`SECURITE.md`](SECURITE.md) — checklist OWASP (constat + reco, sans fix)
- [`CLOISONNEMENT.md`](CLOISONNEMENT.md) — isolation inter-comptes
- [`LABUSE_EN_CHIFFRES.md`](LABUSE_EN_CHIFFRES.md) — l'inventaire quantifié

---

## Verdict global

LABUSE est **sain dans ses fondamentaux** : secrets côté serveur uniquement (bundle front propre), injections fermées (paramètres liés partout), auth argon2id + tokens CSPRNG, webhook Stripe signé et anti-rejeu, cloison projets/CRM/veilles étanche, pare-feu réduit à 22/80/443. Le socle multi-tenant et le mécanisme de paiement sont bien conçus.

**Deux angles morts se dégagent, tous deux invisibles aujourd'hui parce que masqués par l'état pilote** (rideau basic-auth Caddy global + un seul « compte » réel, tout en bucket `NULL`), mais qui **s'activeront à la bascule commerciale** : (1) l'**exfiltration en masse** du scoring via des surfaces non throttlées, et (2) la **fuite inter-comptes** sur 5 surfaces annexes qui ignorent `compte_id`. Ce sont les deux chantiers à traiter avant d'ouvrir le robinet multi-clients.

---

## Les 3 findings les plus importants (toutes sections)

### 1. 🔴 Exfiltration du scoring par les tuiles & le geojson bulk (M3-6, gravité **haute**)
Un client **authentifié** peut aspirer l'intégralité du référentiel scoré (431 663 parcelles, avec `q_score`/`a_score`/`flags`/`proprio`) via `/map/tiles/*` (z12+) et `/map/parcels.geojson` (cap 200 000, `commune=NULL` → île entière en ~3 requêtes). Ces routes sont **hors** `PREFIXES_PROTEGES` et hors `consultation_log` → l'abuse-scan, qui ne lit que la fiche unitaire, **reste aveugle** (score à 0). C'est le trou d'exfiltration réel : tout le capital-donnée sort sans alerte. *(ACCES_EXTERNES.md §2 / SECURITE.md §6)*

### 2. 🔴 Cinq surfaces client fuitent entre comptes (M7 §2, gravité **haute** à la bascule multi-licence)
`signalements` et `saved_filters` sont **déclarées scopées** (`SCOPED_TABLES`) mais leurs routes n'écrivent ni ne filtrent `compte_id` ; `event_log` (la cloche de notifications) et `watched_parcels` (suivi de cible) n'ont **aucune colonne tenant**. Résultat : un compte A verrait/supprimerait les signalements, filtres, notifications et veilles-cibles de B (dont un **IDOR d'écriture** sur `DELETE /filters/{id}`). Masqué aujourd'hui (tout `NULL`/mono-utilisateur) ; **bloquant dès la première vraie licence multi-comptes**. *(CLOISONNEMENT.md §2)*

### 3. 🟠 Jeton de paiement forgeable si `LABUSE_SECRET_KEY` absente (M3-3, gravité **moyenne→haute**)
Le fallback en dur `"labuse-dev-secret"` (`coffre_ui.py:23`, `config.py:49`) sert de clé HMAC si la variable d'environnement n'est pas posée. Le secret n'étant **pas forcé en prod**, un attaquant qui connaîtrait ce littéral (public dans le code) pourrait **forger un jeton `/onboarding/paiement` pour n'importe quel `compte_id`**. À coupler avec le second angle mort structurel : **l'alerte est quasi inexistante** (seul `watch_prod.sh` pousse une notif macOS, Mac allumé requis ; aucun email/SMS/Slack) — une compromission ou une panne peut passer inaperçue. *(SECURITE.md §3 / POINTS_MANUELS.md, fait transversal n°1)*

---

## Liste priorisée pour un mandat de correction

### P0 — avant bascule commerciale multi-comptes
| # | Chantier | Source | Effort |
|---|---|---|---|
| 1 | Throttler + journaliser `/map/tiles` et le bulk geojson ; compter le bulk dans les quotas ; retirer `proprio`/`owner_type` du geojson bulk | M3-6 | moyen |
| 2 | Scoper `signalements` + `saved_filters` (INSERT pose `compte_id`, SELECT/DELETE filtrent + ownership) | M7 #1-3 | faible |
| 3 | Ajouter `compte_id` à `event_log` + `watched_parcels` et refondre la détection batch | M7 #4-5 | moyen |
| 4 | Forcer `LABUSE_SECRET_KEY` en prod (refus de boot) + supprimer le fallback `"labuse-dev-secret"` | M3-3 | faible |

### P1 — durcissement avant ouverture publique (chute du rideau Caddy)
| # | Chantier | Source | Effort |
|---|---|---|---|
| 5 | Brancher `plans.plan_courant()` sur `comptes.plan` du compte connecté (aujourd'hui stub global) — **avant** tout multi-plan | M3-4 | faible |
| 6 | Ajouter une CSP ; activer HSTS (nginx/Caddy) une fois HTTPS stable | M3-5 | faible |
| 7 | Révoquer la session en base au `/logout` ; rate-limit `/login` par IP ; documenter `LABUSE_TRUSTED_PROXIES=127.0.0.1` ; rate-limit de bord Caddy | M3-3/6 | faible |
| 8 | Détecter l'épuisement des crédits Anthropic (`_note_error`) + brancher une alerte réelle (email/push) sur backups & crons | M2-A1 / M3 | moyen |

### P2 — prérequis Vic non-code (business/légal)
| # | Point | Source |
|---|---|---|
| 9 | Clés Stripe **LIVE** + enregistrement webhook dashboard + price IDs | M2-B1 |
| 10 | Mentions légales : SIREN/SIRET réels, adresse complète, régime TVA ; relecture juridique CGV/CGU | M2-B2 |
| 11 | Offload backups hors VPS (OVH Object Storage — code écrit mais commenté) | M2-C2 |
| 12 | Figer les versions Python (`==`/lockfile) + `pip-audit` en CI | M3-7 |

---

## Ce qui est déjà solide (à ne pas retoucher)

- Bundle front **sans secret** ; injections **fermées** ; dépendances **npm 0 vuln**.
- Webhook Stripe **signé + dédup + fail-closed** ; aucune donnée de carte côté LABUSE.
- Cloison **projets / CRM / pipeline / veilles** étanche (404 sur ownership, `UNIQUE(compte_id, parcel_id)`).
- Pare-feu **22/80/443** seulement ; API + PostgreSQL en loopback ; Uvicorn ne fait confiance qu'à 127.0.0.1.
- Admin **sans chemin d'élévation via l'API** (actions CLI uniquement, tracées dans `evenements_compte`).
- Sauvegardes **à double filet anti-0-octet** ; restauration **drillée** (46 s).

---

## LABUSE en une ligne (chiffres-phares)

**431 663 parcelles · 24/24 communes · 100 % de couverture · 73,2 M de lignes · 21 Go · 52 sources ingérées & surveillées · 116/116 golden vert · 1 124 tests · 204 endpoints · ~63 200 lignes de code.**

*Fin de la synthèse 360°.*
