# POST-M7 · 1 — « J+2 » : LA CHAÎNE DE FRAÎCHEUR (rapport, STOP final)

Branche `postm7/j2-fraicheur`. **La promesse : jamais en retard de plus de 48 h sur la dernière
PUBLICATION de chaque source** — la cadence réelle s'affiche, elle ne se cache pas.
Liste J+2 du rapport M7 : intégrée (cochée en J6). Aucun downtime non nécessaire (le seul restart a
été automatiquement REPORTÉ car le backup tournait — leçon M7 codée dans la commande).

## J1 · La matrice des sources — l'état zéro (22/07/2026, base locale)

| Source | Cadence réelle | Dernière donnée | Dernière ingestion | Δ donnée | Voie |
|---|---|---|---|---|---|
| SITADEL (SDES/Dido) | mensuelle | 2026-05-30 | 2026-07-10 | 53 j | incrémentale (delta 3 mois) |
| BODACC | **quotidienne** | 2026-07-02 | 2026-07-05 | 20 j | batchée SIREN, upsert |
| DVF (Etalab) | semestrielle (avr./oct.) | 2025-12-31 | — | 203 j (= à jour de la dernière livraison) | reload par millésime |
| DPE ADEME | hebdo (flux continu) | 2026-07-03 | 2026-07-12 | 19 j | upsert numero_dpe |
| BAN | mensuelle | 2026-07-11 | 2026-07-11 | 11 j | full reload idempotent |
| CatNat (GASPAR) | au fil de l'eau | 2025-07-08 | — | 379 j (pas d'arrêté 974 récent ≠ retard) | upsert par arrêté |
| GPU/PLU | périodique (révisions) | 2026-07-03 | — | — | **détection seule** |
| Géorisques | périodique | 2026-07-10 | 2026-07-10 | — | **détection seule** |

Décision structurante documentée : **GPU/PLU et Géorisques ne sont JAMAIS auto-ingérés** — ces couches
nourrissent la **cascade gelée** ; les réingérer changerait les données sous le run servi. Une mise à
jour détectée = signalement (healthz/cron), la réingestion passe par la **grande passe Mac** (sync-run).
Anomalie relevée : 1 permis SITADEL daté 2026-08-17 (futur) — erreur de saisie source, exclu de la
matrice (`date <= now()`).

## J2 · Les crons incrémentaux

| Cron | Cadence | Détection de livraison | Idempotence |
|---|---|---|---|
| `bodacc` (NOUVEAU) | quotidien 4h30 | ré-interrogation batchée des 12 605 SIREN propriétaires | upsert `annonce_id` |
| `sitadel` (refondu) | **quotidien**-en-attente-du-mensuel 4h15 | delta `max(date) − 3 mois` → no-op léger hors livraison | upsert `permit_id` |
| `dvf` (NOUVEAU) | hebdo mercredi 5h | **Last-Modified HTTP par CSV annuel** vs état stocké (`fraicheur_etat`) — on ne retélécharge jamais ce qu'on a | DELETE millésime modifié + réinsertion |
| `dpe` (NOUVEAU) | hebdo mardi 5h20 | flux ADEME | upsert `numero_dpe` |
| ban / catnat / abuse / backup | inchangés (M7) | — | — |

Chaque cron d'ingestion **chaîne `fraicheur-derives`** ; le lundi, la variante `--hebdo` ajoute m10
(vélocité, re-fetch réseau). État exposé : **`/healthz/crons`** (3 nouvelles entrées + matrice sources
+ compteur DPE). CLI : `fraicheur-etat`, `ingest-bodacc`, `refresh-dvf`, `fraicheur-derives`.

## J3 · La chaîne post-ingestion — **PREUVE D'IDEMPOTENCE**

`run_derives` : `pc_caducs` (**une DAACT tardive fait SORTIR du badge** au rebuild — l'honnêteté vaut
dans les deux sens) → `defisc_fenetres` → `surface_d` (le moteur O10 se nourrit du frais) → compteur
DPE ; `--hebdo` : + m10 délais/vélocité.
- **Idempotence prouvée sur base réelle** : double run → empreinte identique (`68417cbfa37337cf`).
- **INTERDIT ABSOLU tenu et TESTÉ statiquement** (`test_garde_fou_tables_de_run_jamais_ecrites`) :
  aucun module de la chaîne n'écrit dans `parcel_p_score_v2` / `p_score_v2_runs` / `dryrun_*` /
  `parcel_evaluations`. **Désynchronisation badge/rang assumée** entre deux grandes passes : un badge
  peut apparaître/disparaître pendant que le rang servi reste gelé — c'est le contrat documenté.
- **Cas DPE** : compteur de réveil réévalué à chaque refresh — **7 / 200** au 22/07 (`F/G ∩ mono ∩
  non-écarté`, exactement le cadrage cycle 3) ; loggé, stocké (`fraicheur_etat`), exposé healthz ;
  franchissement → événement visible au cron. Le badge se réveillera tout seul.

## J4 · La fraîcheur VISIBLE

- `/sources` expose désormais **`derniere_donnee`** (la date de la donnée, ≠ date d'ingestion).
- La page Sources (qui avait déjà badge/cadence/prochaine MAJ) affiche **« données jusqu'au X · ingéré
  le Y »** — harmonisation d'une imprécision existante (elle affichait la date d'INGESTION sous le
  libellé « donnée du »). Wording sobre, les dates parlent seules.
- Le bloc permis de la fiche affichait déjà ses dates par permis (vérifié) — inchangé.

## J5 · sync-run.sh — **TESTÉ À BLANC (réel)**

`deploy/scripts/sync-run.sh` : dump ciblé des 10 tables de la grande passe → transfert (checksum) →
`--dry-run` s'arrête là ; bascule réelle = restore --clean + ANALYZE + **comptages local vs VPS (le
moindre écart = arrêt)** + build-mvt + **golden distant obligatoire** avant que le run soit servi.
**Dry-run exécuté** : dump **444 MB** (comptages de référence dont p_score 2 589 978, dryrun 36 259 335),
transfert checksum OK, arrêt propre avant restore. Rappels codés : jamais pendant le backup 3h ;
bascule de LABEL ⇒ `LABUSE_SERVED_RUN` + rebuild front + restart hors backup.

## J6 · Monitoring + reliquats M7 (la liste, cochée)

- ☑ **Sentinelle de prod** : `deploy/scripts/watch_prod.sh` + LaunchAgent `immo.labuse.watch-prod`
  (10 min) — surveille `/healthz/crons` **`ok:true`** (un cron en retard alerte aussi) ; 2 échecs
  consécutifs → notification macOS + log. Choix pull-depuis-le-Mac : aucun service tiers, aucun secret
  externe. Run manuel : prod OK.
- ☑ **Badge O11 forme juridique** : `forme_juridique` + `entite_publique` sur chaque porteur
  (`FORMES_PUBLIQUES` = ETAT/DEPT/COM/COLL/EPA/EPIC/SDIS/SIVU/SYMI/SYCO/CCAS/CCAM/HOSP/GIP/**SEM/SAM**) —
  **taguées, jamais exclues** (décision Vic) ; inconnu = `null` (pas d'invention). Vérifié live : la
  SEM d'aménagement taguée publique, CBO/SNC privées. (Note d'honnêteté : l'Aéroport est en SA au
  fichier DGFiP — le tag suit la donnée, pas la structure capitalistique.)
- ☑ **Clé ANTHROPIC posée** sur le VPS (depuis le `.env` local, jamais en git). Le restart nécessaire a
  été **reporté automatiquement** (backup en cours — garde-fou) puis exécuté ; état à la vérification :
  `/ia/status` — voir addendum en fin de rapport (le passage hors « stub » dépend des crédits, action Vic).
- ☑ **Deps implicites déclarées** : `opencv-python-headless` au pyproject ; pango/gdk-pixbuf/fonts dans
  `vps_setup.sh`.

## Garde-fous du mandat — état
Tables de run : jamais touchées (test statique + preuve d'empreinte) · format source changé : la
détection Last-Modified/upsert par clé fait qu'un format cassé échoue BRUYAMMENT (exception cron →
visible healthz), jamais de données mal parsées servies en silence · échec cron : `/healthz/crons` +
sentinelle 10 min · restart : uniquement si nécessaire, jamais pendant un backup (prouvé en live).

## ADDENDUM (fin de mandat) — deux incidents attrapés, IA opérationnelle

1. **Backup 0 octet (incident réel, détecté par ce mandat)** : le cron backup de la nuit du 22/07 a
   produit un dump VIDE — échec d'auth silencieux (pas de `.pgpass` pour l'utilisateur `labuse` ; mon
   test M7 passait le mot de passe autrement). Réparé : `.pgpass` posé (600), **script durci** (un dump
   vide/illisible est SUPPRIMÉ et le script échoue bruyamment — plus jamais un 0-octet qui pollue la
   rotation), et **backup de preuve VERT par la voie exacte du cron : 3,8 GB, contrôles taille +
   `pg_restore --list` passés**. Le filet aval existait déjà (le pull Mac de 7h30 alerte sur dump
   illisible) — l'amont est maintenant bruyant aussi.
2. **3ᵉ dépendance implicite** : le SDK `anthropic` manquait au venv VPS (révélé au premier appel IA
   réel). Déclaré au `pyproject` (avec `opencv-python-headless`) + installé.
3. **IA de prod OPÉRATIONNELLE** : clé posée (depuis le `.env` local, jamais en git), restarts
   systématiquement **reportés pendant les backups** (garde-fou appliqué deux fois en live),
   `/ia/status` → `provider: anthropic`, et un appel réel `/ia/search` répond `stub: false` avec une
   traduction NL correcte validée par schéma — **les crédits répondent** (rechargés par Vic).
4. Bug de boucle d'attente (`pgrep -f` se matchait lui-même) : leçon consignée, `pgrep -x` partout.
5. **Chaîne DÉPLOYÉE et vivante sur le VPS** : code de la branche déployé (deploy_app.sh), **8 cron.d
   actifs** (bodacc/dvf/dpe nouveaux + sitadel quotidien + ban/catnat/abuse/backup), `fraicheur-etat`
   répond depuis la prod, healthz 200, smoke prod VERT. Premiers passages : sitadel 4h15, bodacc 4h30
   (heure serveur). Incident au passage : le rate-limit ufw SSH (6/30 s, posé à M7) a mordu mes propres
   rafales de déploiement → **ControlMaster ajouté à la config SSH** (une connexion multiplexée, fix
   durable pour tous les scripts).
