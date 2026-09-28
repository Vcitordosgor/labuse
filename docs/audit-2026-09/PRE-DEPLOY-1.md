# PRE-DEPLOY-1 — ce qui doit être vrai avant la mise en ligne

**Branche** `fix/pre-deploy-1` (depuis `origin/main` post-merge COHERENCE-FIX-1) · worktree `~/Desktop/labuse-predeploy` · ports 8655/5855 · base de test dédiée `labuse_pd1` (clone de `labuse_test`, isolée des autres worktrees).

Périmètre strict : les quatre lots ci-dessous. Aucun run île. Aucun relancement de `build-intersections` (geste de Vic).

---

## Étape 0 — baseline

- `pwd` = `/Users/openclaw/Desktop/labuse-predeploy`, branche `fix/pre-deploy-1`, arbre propre, `.env` présent.
- `pytest tests/` complet (base `labuse_pd1`) : **7 échecs, 3507 passés, 69 skips** — conforme à l'attendu (~7). Détail et triage au Lot B.

Les 7 échecs de départ :

| # | Test | Famille |
|---|------|---------|
| 1 | `test_circuit2_lot6.py::test_prix_neuf_des_pdf_jamais_l_acte` | test périmé (produit) |
| 2 | `test_retours11f3.py::test_f4_reglement_valeurs_de_zone_pas_seulement_references` | fragile (fuite inter-fichiers) |
| 3 | `test_retours11f3.py::test_f4_zone_non_outillee_pas_de_valeurs_fabriquees` | fragile (fuite inter-fichiers) |
| 4 | `verrous/test_garanties.py::test_les_24_se_jouent_toujours_tous` | merge du jour (COHERENCE-FIX-1) |
| 5 | `verrous/test_garanties.py::test_g4_vert_et_vide_jamais_a_jour` | environnement (base réelle) |
| 6 | `verrous/test_lot1_tables.py::test_verrous_lot1_passent_sur_la_base_reelle` | environnement (base réelle) |
| 7 | `verrous/test_lot2_sources.py::test_v2a_68_partout_sur_la_base_reelle` | environnement (base réelle) |

---

## Lot A — le banc nocturne ne passe JAMAIS par l'API publique

### Constat (preuve)
Le job `coherence-banc` (03:45, `jobs.py` / `jobs_impl.coherence_banc`) lançait **un sous-processus HTTP** :
`python -m scripts.coherence.banc --ile` contre `LABUSE_COHERENCE_API` (défaut `http://127.0.0.1:8000`), via `urllib.request.urlopen(f"{API}/parcels/{idu}")`. Or `/parcels` est un préfixe **protégé** (`protection.PREFIXES_PROTEGES`) : rate-limit 60/min + quota fiches. Le banc martèle des centaines de fiches ⇒ il ne pouvait passer QUE si l'API tournait sans protection (c.-à-d. `LABUSE_DEV_MODE=1`). Dépendance à un flag de dev en ligne = trou anti-scraping.

### Correctif — EN-PROCESS, sans HTTP, sans DEV_MODE
- `scripts/coherence/lib.py::client_en_process()` : construit un **TestClient FastAPI** (hôte réservé `protection.HOTE_INTERNE = "labuse-inproc"`), s'authentifie proprement par une **session pilote mintée en interne** (`auth.make_token()` — l'auth reste ACTIVE comme en prod, aucun contournement). `Contexte(fetch=…, client=…)` route fiches, contexte commune ET tuiles PBF en-process.
- `scripts/coherence/banc.py::run(ile, en_process=True)` : nouveau point d'entrée ; `passe_determinisme` prend un `refetch` en-process (plus d'`urllib`).
- `jobs_impl.coherence_banc` : appelle `banc.run(ile=True, en_process=True)` **en-process** — plus de sous-processus, plus de `LABUSE_COHERENCE_API`, plus de dépendance au port servi.
- `protection.garde_protection` : exemption **sûre** du trafic en-process (`request.client.host == HOTE_INTERNE`), placée AVANT tout le reste. Sûre car `client.host` est posé par le transport ASGI, jamais par un en-tête : une vraie requête réseau arrive avec une IP (ou l'IP extraite de X-Forwarded-For), **jamais** ce littéral. Ce n'est PAS un second `dev_mode` (il n'ouvre rien sur l'API publique).

**Preuve mesurée** (config prod : `LABUSE_ENV=production`, secret posé, `DEV_MODE` absent, rate-limit actif) :
- 130 appels `/parcels/…` via l'hôte réservé → **404×130, aucun 429** (jamais rate-limité).
- 130 appels via un TestClient ORDINAIRE → **60×404 puis 70×429** (la garde mord bien).

### Garde de démarrage
`auth.exiger_pas_de_dev_mode_deploiement()` (appelée au `lifespan`, à côté de `exiger_secret_prod` / `exiger_env_deploiement`) : hors `local` (pilot|production), `LABUSE_DEV_MODE=1` **refuse le démarrage** (fail-closed). Test : `test_audit_secu.py::test_dev_mode_refuse_hors_local` (+ `::test_banc_coherence_en_process_hote_reserve_exempte_rate_limit`). Preuve : `production`+dev → REFUS, `pilot`+dev → REFUS, `local`+dev → OK, `production` sans dev → OK.

### Ligne de cron du VPS
Le crontab est GÉNÉRÉ du registre (`labuse jobs crontab`), jamais écrit à la main. La ligne (heure Réunion, +4 h de l'UTC `45 23 * * *`) :

```
45 3 * * *  labuse  cd /opt/labuse/app && /opt/labuse/venv/bin/labuse jobs run coherence-banc >> /var/log/labuse/coherence-banc.log 2>&1
```

Aucune variable `LABUSE_COHERENCE_API` ni `LABUSE_DEV_MODE` n'est requise. (Le job tourne en-process ; l'API publique peut rester protégée.)

---

## Lot B — la suite au vert

Un commit par famille. Résultat visé : `labuse circuit suite` **vert** (0 refus), les échecs de base réelle documentés dans `docs/TESTS-TOLERES.md`.

1. **`test_les_24` (merge du jour)** — COHERENCE-FIX-1 a ajouté **V6b** au registre (`VERROUS`) mais la liste figée du test ne l'avait pas. Correctif : V6b ajouté à la liste attendue (entre V6a et V7a), 24 verrous + 8 garanties = 32.
2. **`test_f4_*` ×2 (fragile — fuite inter-fichiers)** — CAUSE RACINE trouvée : `plu_reglement` faisait `from .faisabilite.zonage import resolve_zone, reglement_source, est_outillee` (COPIES à l'import). Quand `test_faisabilite3_scenarios` monkeypatche `zonage.resolve_zone` PUIS déclenche le 1ᵉʳ import de `plu_reglement`, celui-ci **capture les stubs** ; `monkeypatch` ne restaure que `zonage.*`, pas les copies ⇒ `resolve_reglement` rend « calibré » pour des zones non outillées dans les fichiers suivants (ordre alphabétique : `faisabilite3` < `retours11f3`). Correctif RACINE : `plu_reglement` référence les fonctions **via le module** (`_zonage.resolve_zone(…)`) — tout patch/restauration de `zonage.*` est désormais vu. Vérifié : `faisa3 + f4` → 15 passés.
3. **`test_prix_neuf_des_pdf_jamais_l_acte` (test périmé — décision produit confirmée par Vic)** — le verrou Q3 « aucun export ne lit `neuf_vefa_commune` » a été **supersédé par EXPORTS-FIX-1 C5**, qui a délibérément SCINDÉ la notion : le VEFA à l'acte est servi comme donnée DISTINCTE, DÉCLARÉE au registre et LABELLISÉE « Prix du neuf — VEFA à l'acte » (`prix_neuf_vefa_acte_eur_m2`, Comparateur communes, sonde de scission). Verrou réécrit à l'invariant RÉEL : le moteur de l'acte (`neuf_vefa_commune`) n'est lu QUE sous l'extracteur de sa notion labellisée, **jamais** confondu avec le neuf observé (`prix_neuf_observe_eur_m2`). Test renommé `test_prix_neuf_vefa_a_l_acte_seulement_sous_sa_notion_labellisee`.
4. **`test_v2a`, `test_g4`, `test_lot1` (environnement — base réelle, `@pytest.mark.local`)** — voir « Ce qui reste toléré » ci-dessous. **Tolérés** dans `docs/TESTS-TOLERES.md` (décision Vic), chaque ligne nommant le mandat qui la lèvera + échéance. Hors périmètre PRE-DEPLOY-1.

Vérifs : `tsc -b` = 0 · `vitest` = 225 passés · `test_front_chiffres_orphelins` = 3 passés · V6b vert.

**Certification `pytest tests/` sur base FRAÎCHE (clone neuf de `labuse_test`)** : **3 échecs (les 3 tolérés ci-dessous) · 3517 passés · 69 skips · 0 erreur** (17 min). `labuse circuit suite` confronte les 3 échecs à `TESTS-TOLERES.md` → **0 refus** (vert). Les 4 fixés à l'étape 0 (les_24, f4×2, VEFA-à-l'acte) passent.

> Hygiène base de test : les 4 « erreurs » vues lors de runs intermédiaires (`UniqueViolation utilisateurs_email` dans `test_dashboard.py`) étaient un ARTEFACT de POLLUTION de ma base `labuse_pd1` (5 000+ `utilisateurs` accumulés par mes runs ciblés répétés) — PAS une régression : `test_dashboard.py` passe isolé, et la certification sur clone NEUF donne 0 erreur. Sur le VPS, `circuit suite` part d'une base `labuse_test` (re)créée — mais si elle est partagée/polluée, TRUNCATE avant recette.

### Ce qui reste TOLÉRÉ (à revérifier après les merges, demande de Vic)

Trois échecs de **base réelle** (`@pytest.mark.local`, hors CI) restent tolérés dans `docs/TESTS-TOLERES.md` (échéance 2026-10-20) :

| Test | Cause | Levé par |
|------|-------|----------|
| `test_lot2_sources::test_v2a_68_…` | source « Population légale (INSEE via geo.api.gouv) » servie mais absente du pont `NOM_VERS_SLUG` | **COHERENCE-FIX-1** (câblage source → réservoir) |
| `test_garanties::test_g4_…` | même source sans sonde de fraîcheur ni raison de non-vérifiabilité | **COHERENCE-FIX-1** (sonde/raison de la source) |
| `test_lot1_tables::…base_reelle` (V1c) | `parcel_couche_intersection_build` orphelin | **build-intersections de Vic** (bascule staging → table finale, Lot D) |

> Observation annexe (non bloquante, hors périmètre) : le verrou V1c signale aussi, sur la base réelle, un écart de comptes CatNat « carte risques · 97410 : servi 15 ≠ producteur 17 ; 97418 : 20 ≠ 22 ». À porter à COHERENCE-FIX-1 / la chaîne CatNat.

---

## Lot C — le manifeste servi ne peut plus mentir

`config/served_manifest.json` avait pointé le résiduel run 8 alors que run 10 est servi (corrigé à la main, `7ae2c2b7`). Rendu impossible :

1. **Réécriture + rappel « à commiter »** : `residuel-serve` réécrit le miroir (et le POSE via bootstrap s'il manque) puis affiche `⚠ manifeste modifié : à commiter (…)`. `golden promote` (→ `bascule_flux.basculer`) affiche déjà le chemin du manifeste + ajoute `⚠ manifeste modifié : à commiter`.
2. **`/sante/fraicheur` + le banc comparent le manifeste au servi en base** : nouveau contrôle `fraicheur_caches._etat_manifeste(db)` — compare `residuel_run_seq` (miroir) vs `residuel_runs.is_served` (LA vérité), et `scoring_run` vs la vue dérivée `served_run.txt`. Écart ⇒ **rouge** page Données + **PÉRIMÉ** dans `labuse rebuild --dry-run` (fumée déploiement). Garde base de test : on ne compare le résiduel QUE si le run du manifeste EXISTE dans cette base (sinon = poste de test, rien à comparer) — le vrai bug (8↔10, les deux présents) est attrapé. Ajouté aussi comme **5ᵉ mâchoire de V6b** (le banc). Preuves : manifeste menteur (seq existant ≠ is_served) → PÉRIMÉ ; run absent (999) → pas de faux positif ; live actuel (10==10) → aligné.
3. **Fumée du déploiement** : `deploy.sh` (via `labuse rebuild --dry-run` qui lit `etat()`) refuse si le manifeste ment ; `deploy/scripts/smoke_test.sh` ajoute un contrôle explicite `residuel_run_seq` commité vs `is_served` (BLOQUANT).

---

## Lot D — les intersections

État de `parcel_couche_intersection` sur la base servie (`labuse`), au 2026-09-29 :

- Table **finale `parcel_couche_intersection` : ABSENTE**.
- Table de staging `parcel_couche_intersection_build` : présente mais **VIDE (0 ligne)**, sans index, sans `_meta`.
- Aucun build en cours (`pg_stat_activity`).

**Diagnostic** : `labuse build-intersections` a été **amorcé mais NON terminé** — la table de staging a été (re)créée vide, la population par tranches puis la bascule (RENAME → table finale) n'ont pas eu lieu. Les servitudes matérialisées sont donc **absentes** : les lecteurs (fiche, Gabarit) repassent au **calcul au vol** — résultat IDENTIQUE, mais lent. **Ce n'est pas une erreur de correction, c'est un cache de vitesse manquant.** Conformément au périmètre, je n'ai PAS relancé le build (geste de Vic).

Intégration :
- `/sante/fraicheur` (et page Données, et `rebuild --dry-run`) : nouveau `fraicheur_caches._etat_intersections(db)` — **complète / partielle / vide / absente** + nombre de lignes, couches, parcelles, date. **NON bloquant** (`perime=False`) : un manque n'est pas une erreur (repli au vol correct), mais il est DIT. État actuel affiché : « table absente — jamais construite (calcul au vol) ».
- `deploy/scripts/smoke_test.sh` : ligne informative intersections (lignes/couches/parcelles/date) — non bloquante.

---

## Checklist du jour J (ordre des gestes sur le VPS)

1. **Sauvegarde** : `labuse jobs run backup-postgres` (ou vérifier le dernier dump `≥ 1 Mo`).
2. **Pull** : `git fetch && git checkout main && git pull` (le checkout servi).
3. **Migrations / schéma** : `labuse` s'auto-répare au boot (schema-heal) ; pas de migration manuelle attendue. Vérifier au boot suivant `env=… · schéma=ok`.
4. **`labuse rebuild`** : régénère les caches à clé de fraîcheur (spatial_layers_sub, tuiles, fiche commune, **intersections servitudes** — léger). Régénère aussi les intersections servitudes si `fraiche()` False.
5. **`labuse build-intersections`** (si besoin — GESTE DE VIC) : la table finale étant absente aujourd'hui, la (re)lancer à COMPLÉTION (servitudes ; `--with-zone` = fenêtre de maintenance, multi-heures). Vérifier ensuite `/sante/fraicheur` → intersections « complète ».
6. **Manifeste** : vérifier que `config/served_manifest.json` COMMITÉ = servi en base (`residuel_run_seq` == `residuel_runs.is_served`). S'il a été réécrit par un geste (`residuel-serve`/`golden promote`), **le committer**.
7. **Fumée** : `deploy.sh` enchaîne `circuit verrous -w G8` → `circuit suite` (confronté à `TESTS-TOLERES.md`) → `labuse rebuild` → `labuse rebuild --dry-run` (échoue si un cache est périmé OU si le manifeste ment) → `deploy/scripts/smoke_test.sh` (healthz/readyz/DB/PostGIS/parcels + manifeste + intersections).
8. **Bascule du trafic** : une fois la fumée verte, basculer Caddy/nginx vers la nouvelle version.
9. **Après** : lever les tolérances de `TESTS-TOLERES.md` dès que COHERENCE-FIX-1 (câblage « Population légale ») et le `build-intersections` de Vic sont terminés — puis rejouer `labuse circuit suite` (les lignes mortes se signalent seules).

---

*Livrable PRE-DEPLOY-1. Lots A/C/D faits et prouvés ; Lot B au vert (`circuit suite` 0 refus, 3 tolérances de base réelle datées). Pas de merge. API et front arrêtés.*
