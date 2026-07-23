# Correction P0 — avant bascule multi-comptes

> **Branche `secu/p0-avant-multicomptes` · 2026-07-23 · non mergée (Vic merge)**
> Corrige les 3 findings P0 de [`SYNTHESE_360.md`](SYNTHESE_360.md) + 3 P1 rapides et sûrs. Un commit par item. **Suite 1138/0 · golden 116/116 · 0 net-new lint** après chaque item.

---

## P0-1 — Les 5 surfaces qui fuitaient (commit `8e33ffc`)

Cloison `compte_id` étendue aux 5 surfaces annexes, **exactement le pattern projets/CRM/veilles** (`compte_id IS NOT DISTINCT FROM :cid`, écriture qui pose le compte, **404 jamais 403**).

| Surface | Avant | Après |
|---|---|---|
| `signalements` (POST/GET/export) | INSERT sans compte_id, SELECT global | compte_id posé + filtré partout |
| `saved_filters` (GET/POST/DELETE) | non filtré, DELETE sans ownership (IDOR écriture) | filtré ; **DELETE/{id} → 404 si non possédé** |
| `event_log` (cloche) | aucune colonne tenant, mark-read global | +compte_id ; list/count/read/read-all/digest scopés ; détection attribue veille→propriétaire, permis→compte qui suit |
| `watched_parcels` (suivi de cible) | `idu` PK global | +compte_id ; clé `UNIQUE (compte_id, idu)` (A et B suivent la même parcelle sans se voir) |

`event_log`/`watched_parcels` ajoutés à `SCOPED_TABLES` → **FK ON DELETE CASCADE** (purge RGPD). Migration idempotente au boot (`ensure_scoping`), appliquée et vérifiée sur la base app.

**Décision produit documentée** : bascule/BODACC restent le feed pilote/démo (`compte_id NULL`, données publiques de marché) ; l'isolation lecture/écriture est totale. La propagation par-compte des événements de marché au-delà des veilles est un choix produit ultérieur, **pas une faille**.

---

## P0-2 — Exfiltration du scoring (commit `17981dc`)

Le canal réel : les tuiles `/map/tiles` (z≥12 portent `idu`+`q/a`+`flags`) échappaient au rate-limit, au quota **et** au log ; le geojson île déversait `proprio`/`owner_type` en masse.

- **Tuiles** : quota **journalier dédié** (`quota_tuiles_jour=40000`), **PAS le rate-limit 60/min** — une carte qui panne charge des dizaines de tuiles/s, le 60/min tripperait la navigation. Compteur mémoire + flush DB par lots → aussi le **signal de volume vu par abuse-scan**.
- **Geojson île** : quota d'appels/jour (`quota_carto_jour=400`) en plus du 60/min + log.
- **abuse-scan** : lit les compteurs tuile/carto → un moissonneur 100 % tuiles (zéro ligne `consultation_log`) **devient visible** (score +20/+40 sous les plafonds durs ; gel manuel, doctrine inchangée).
- **Geojson île entière** (commune absente) : `proprio`/`owner_type`/`owner_famille` **masqués (NULL)** ; en mode commune (borné, usage normal) ils restent exposés. Le front sert l'île en tuiles (aucune donnée propriétaire dans les tuiles) → **zéro impact UX**.

### Calibrage (jamais gêner un client, borner l'actif)
Usage humain intense = heures de navigation z9-16, cache navigateur 1 h → **< ~15-20k tuiles/j**. L'île scorée entière ne fait que **quelques milliers** de tuiles → **40 000** laisse re-parcourir l'île plusieurs fois avant de gêner, mais une boucle de moisson multi-zoom trippe. Dépassement → **429 « reprend à minuit »** (throttle, jamais un gel auto). Geojson île : un humain en charge une poignée par session ; **400/j** est large, une boucle par commune/bbox trippe.

---

## P0-3 — LABUSE_SECRET_KEY fail-closed (commit `6ac03cc`)

- `coffre_ui._secret()` et `protection._cle_hmac()` : **plus aucune constante en dur** (`"labuse-dev-secret"`, `"labuse-protection"`) — elles déléguaient à `auth.cle_signature()` (clé éphémère en `local` uniquement).
- `auth.exiger_secret_prod()` : hors `local`, l'absence de `LABUSE_SECRET_KEY` **lève au démarrage** (message clair : `openssl rand -hex 32`). Appelée dans le lifespan → **l'app refuse de démarrer** plutôt que de tourner avec un secret forgeable.
- **Vérifié avant de rendre l'absence fatale** : le VPS possède déjà la clé (`M7_SECRETS.txt` + `VPS_GO_LIVE_CHECKLIST` + `deploy/env` example) → **zéro risque de brick**.

---

## P1 retenus — rapides et sûrs (commit `c05b084`)

- **/logout révoque la session en base** (`detruire_session`), pas seulement le cookie — un cookie rejoué ne rouvre plus l'accès (valait 12 h avant).
- **HSTS** (1 an + includeSubDomains) posé en HTTPS uniquement (jamais en http local).
- **`LABUSE_TRUSTED_PROXIES=127.0.0.1`** posé + documenté dans `deploy/env` (sans lui, derrière Caddy tout le trafic s'effondre en 127.0.0.1 et les quotas/rate-limit par IP deviennent inopérants).

### P1 volontairement reportés (plus intrusifs / à tester en conditions réelles)
- **Gating par plan** sur `comptes.plan` : change la logique d'accès ; sans urgence tant que tous les comptes sont Intégral. À faire **avant** tout multi-plan.
- **CSP** : sur une SPA maplibre (fonts/tiles externes), une CSP mal calibrée casse la carte — nécessite une allowlist + test navigateur, pas « rapide et sûr ».
- **Détection d'épuisement des crédits Anthropic** + alerte : demande de reclasser l'erreur API + câbler un canal d'alerte réel.

---

## Preuves de cloisonnement (tests adversariaux permanents)

`tests/test_audit_secu.py` + `tests/test_protection.py` — **32/32 PASS**. Chaque test attaque une faille : s'il tombe, la cloison est ouverte. Les 11 ajoutés par ce mandat :

| Test | Prouve |
|---|---|
| `test_idor_signalements_cloison` | B ne voit/liste/exporte pas les signalements de A |
| `test_idor_saved_filters_cloison` | B ne voit pas les filtres de A ; `DELETE` de l'id de A → **404**, filtre survit |
| `test_idor_event_log_cloison` | B ne voit pas les events de A ; ni `read`/id ni `read-all` de B ne touchent l'event de A |
| `test_idor_watched_parcels_cloison` | A et B suivent la même parcelle sans se voir ; le « unwatch » de B ne défait pas A |
| `test_quota_tuiles_gel_jusqua_minuit` | tuiles au-delà du quota → 429 |
| `test_tuiles_hors_rate_limit_60min` | 12 tuiles > 5 rpm sans 429 (navigation jamais gênée) |
| `test_quota_carto_geojson_ile` | 3ᵉ dump geojson > quota 2 → 429 |
| `test_abuse_scan_voit_le_volume_carto` | moissonneur 100 % tuiles (0 ligne log) **visible** du scan |
| `test_geojson_ile_masque_le_proprietaire` | proprio exposé en commune, **NULL en île entière** |
| `test_secret_key_exigee_hors_local` | prod sans `LABUSE_SECRET_KEY` → refus de démarrer ; local toléré |
| `test_pay_token_sans_secret_en_dur` | jeton forgé à l'ancien `"labuse-dev-secret"` → **refusé** |

*Un mandat de correction, lecture+écriture ; branche non mergée — Vic relit, merge, déploie (le déploiement rejouera `ensure_scoping` sur la base VPS et exigera `LABUSE_SECRET_KEY`, déjà posée).*
