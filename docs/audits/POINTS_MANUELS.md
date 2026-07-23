# Ce qui n'est PAS autonome — les points manuels

> **Audit `audit/panorama` · M2 · Lecture seule · 2026-07-23**
> Tout ce qui, dans LABUSE, exige un geste humain (Vic). Classé par fréquence. Rien n'a été modifié.

**⚠ Fait transversal n°1 — l'alerte est quasi inexistante.** Le seul mécanisme qui *pousse* activement une alerte vers un humain est `watch_prod.sh` : une notification macOS sur le Mac de Vic après **2 échecs consécutifs** de la sonde `/healthz/crons` (`deploy/scripts/watch_prod.sh:24`), et seulement si le Mac est allumé. **Aucun email / SMS / Slack / webhook nulle part.** Tout le reste = codes de sortie + fichiers de log que personne ne tail. Les `admin_alertes` (gels, abus) sont une table DB / boîte in-app, jamais un envoi.

**⚠ Fait transversal n°2** — quasiment aucun point ci-dessous n'est « impossible à automatiser » : la plupart sont des **choix produit/juridiques délibérés** (liens à la main, gel humain, cascade gelée, re-train annuel). Les seuls vrais prérequis externes Vic-only : **clé Stripe LIVE + webhook dashboard, compte Merci Facteur, mentions légales (SIREN/adresse/TVA), recharge Anthropic.**

---

## A) Récurrent (à faire régulièrement)

### A1 — Recharger les crédits Anthropic
- **Quoi** : le produit dégrade en « stub » (repli déterministe) dès que l'API Anthropic échoue.
- **Quand** : à épuisement du solde (déjà survenu).
- **Pourquoi pas auto** : c'est un paiement fournisseur. Surtout, **rien ne le détecte** : `ai/core.py:379` catche toute exception en `degraded=True` ; `_note_error()` (`core.py:58`) ne classe QUE 401/403 — l'épuisement de crédits (HTTP 400 « credit balance too low ») tombe dans le `else` générique, le mot « crédit » n'apparaît jamais. Aucun monitoring de solde, aucune alerte. Vic ne l'apprend qu'en voyant le badge « mode mots-clés » dans l'UI.
- **Automatisable** : le paiement non ; **la détection oui** — brancher une branche « crédits épuisés » dans `_note_error()`.

### A2 — La grande passe Mac → VPS (`sync-run.sh`)
- **Quoi** : `deploy/scripts/sync-run.sh` — dump ciblé de ~10 tables de run/scores/dérivés → rsync (checksum) → `pg_restore --clean` sur le VPS → `build-mvt` → parité comptages + golden distant.
- **Quand** : après CHAQUE grande passe locale (gel-cascade, retrain, nouveau run servi).
- **Pourquoi pas auto** : c'est le **gate délibéré de promotion en prod** — le run n'est « servi » qu'après golden vert (`sync-run.sh:71`). Interactif. ⚠ jamais pendant le backup VPS de 3 h ; après un changement de LABEL, éditer `LABUSE_SERVED_RUN` + rebuild front.
- **Automatisable** : techniquement oui, mais **ne devrait pas** — checkpoint humain.

### A3 — Reconstruire les tuiles (`build-mvt`)
- **Quoi** : `labuse build-mvt` reconstruit `mvt_parcels`. « À relancer après CHAQUE run » (`cli.py:483`), souvent couplé à `segments-counts`.
- **Pourquoi pas auto** : oublier fait diverger carte et fiches (`test_run_serving_coherence.py` pète).
- **Automatisable** : oui, en post-hook de `score-v2` — pas fait.

### A4 — Décision de gel de compte (abuse)
- **Quoi** : cron quotidien `abuse-scan` (6 h) → `abuse_scores` + `admin_alertes`. **Le gel n'est JAMAIS automatique** (faux positifs, `protection.py:13`). Vic gèle via `/protection/admin/gel/{sujet}` ou CLI.
- **Pourquoi pas auto** : doctrine (jamais de blocage auto). L'alerte est une table DB **sans push**.
- **Automatisable** : le blocage refusé par choix ; la **notification** pourrait l'être.

### A5 — Suspendre / réactiver un compte (décision)
- **Quoi** : CLI `compte-suspend`/`compte-reactive`/`compte-supprime --oui` (`cli.py:2043`). Les webhooks Stripe pilotent déjà suspend/réactive **automatiquement** sur événement de paiement → **auto sur événement, manuel sur décision**.

### A6 — Envoyer invitations / reset à la main
- **Quoi** : `compte-invite <email>` / `compte-reset-lien <email>` (`cli.py:1997`) **affichent** le lien en terminal ; Vic l'envoie à la main. **Aucun email auto** : Resend retiré le 22/07 (`config.py:128`). `/reset-demande` affiche seulement « écrivez à votre contact LABUSE ».
- **Automatisable** : oui, mais **choix produit délibéré** de livraison à la main.

### A7 — Monitoring forward mensuel (optionnel)
- **Quoi** : `labuse monitor-forward` (`COMMANDES.md:39`) — « mensuel, manuel », sort `reports/monitoring/AAAA-MM.md`.

### A8 — Cascade gelée / radar (détection seule)
- **Quoi** : crons `radar` (lundi 2 h 40) et détection fraîcheur GPU/Géorisques **signalent** qu'une source amont a bougé mais **jamais d'auto-ingestion** (les couches gelées changeraient les scores). « Le radar SIGNALE, l'humain DÉCIDE » (`cli.py:2096`). Réingestion via la grande passe (A2).
- **Automatisable** : refusé par doctrine (gel-cascade).

### A9 — Recalibration annuelle du scoring
- **Quoi** : recalage d'intercept auto à chaque run, mais **re-train complet = décision humaine annuelle** (garde-fou `p_v2/pipeline.py`).

---

## B) Ponctuel / à venir (bloquant, one-time)

### B1 — Clés Stripe LIVE + webhook (bascule paiement live)
- **État** : `.env` local en clés **TEST** ; templates VPS en commentaire.
- **À faire** : (1) `labuse stripe-provisionne` (crée Intégral 349 €/mois + Flash 79 €) puis coller les price IDs — ⚠ docstring CLI périmé (`cli.py:1986` dit encore « 290/490 ») ; (2) poser la clé **LIVE** dans `/etc/labuse/labuse.env` (jamais dans git) ; (3) **enregistrer le endpoint `/stripe/webhook` dans le dashboard Stripe** et copier le `whsec_` — rien dans le code ne le crée.
- **Après** : le provisioning post-paiement est **entièrement automatique** (webhook signé → `statut='actif'` ; filet `reconcile_abonnement`).

### B2 — Mentions légales incomplètes (reliquat live en prod)
- **Quoi** : `/mentions-legales` (`onboarding.py:244`) affiche encore **`SIREN : [à confirmer par Vic]`** et une adresse **sans voie** (« 97417 Saint-Denis »). Le SIRET précédent a été RETIRÉ (origine non confirmée, commit 3d9a195).
- **À faire** : fournir SIREN/SIRET réels, adresse complète (ou domiciliation), statuer sur le **régime TVA** (CGV art. 4, non tranché). Relecture juridique CGV/CGU recommandée avant premières signatures (`onboarding.py:241`).

### B3 — Compte Merci Facteur PRO (courrier postal)
- **Quoi** : `courrier.py` en provider **stub** — aucune lettre ne part, bouton front masqué.
- **À faire** : ouvrir un compte Merci Facteur PRO (~19,95 €/mois), poser `LABUSE_COURRIER_PROVIDER=mercifacteur` + clés, valider en sandbox.

### B4 — Compte INPI RNE (dirigeants)
- **Quoi** : `INPI_API_USERNAME/PASSWORD` requis par `ingest-dirigeants`. Renseigné en local, à reposer côté VPS.

### B5 — SMTP / DNS d'envoi (si un jour email auto)
- **Quoi** : champs SMTP existent (`config.py:116`) mais **jamais consommés** ; le digest ne rend que du HTML. Nécessiterait hôte SMTP + DNS d'envoi (SPF/DKIM/DMARC). Non bloquant tant que la livraison à la main est assumée.

### B6 — Go-live VPS (checklist one-time)
- **Quoi** : `docs/VPS_GO_LIVE_CHECKLIST.md` + `PILOT_DEPLOYMENT.md` — commander VPS OVH, UFW, user `labuse`, PostgreSQL 18 + PostGIS, remplir `/etc/labuse/labuse.env` (`LABUSE_AUTH_PASSWORD`, `LABUSE_SECRET_KEY` via `openssl rand -hex 32`), DNS A/AAAA, `certbot`, HSTS après 24-48 h, cron backup + maintenance, répéter le rollback à blanc. Provisioning : `vps_setup.sh` + `deploy_app.sh` (lancés depuis le Mac — le VPS n'a aucun credential git), **manuels**.

### B7 — Bascule du run servi
- **Quoi** : changer le run servi exige d'éditer `LABUSE_SERVED_RUN` ET de recompiler le front (`VITE_RUN_LABEL` aligné) + `build-mvt`. Manuel, coordonné.

---

## C) Sur incident (intervention si ça casse)

### C1 — Prod down / cron mort
- **Détection** : `watch_prod.sh` (Mac) sonde `/healthz/crons` ; 2 échecs consécutifs → notification macOS + log. **Seul push d'alerte du projet.** Faiblesse : Mac allumé requis, pas de fallback SMS/email. `/healthz/crons` (`api/ops.py`) résume l'âge des crons + fraîcheur sources + **sentinelle webhook Stripe** — mais il faut que quelqu'un lise.

### C2 — Backup échoué / 0-octet
- **Garde** : `backup_postgres.sh` (3 h) — double filet : échec `pg_dump` → fichier supprimé + exit 1 ; dump vide/illisible → supprimé + exit 1 (fix incident 22/07). `pull_backups.sh` (Mac, ~7 h 30) re-vérifie via `pg_restore --list`.
- **Faiblesse** : bruyant vers un **log que personne ne tail**, aucun email/push. L'offload OVH Object Storage (durabilité hors VPS) est **écrit mais commenté** (`backup_postgres.sh:54`) — vrai trou. Un backup cassé ne remonte que si le cron paraît « en retard » à watch_prod.

### C3 — Restauration (drill + incident réel)
- **Quoi** : `RESTORE_DRILL.md` — procédure **testée réellement** (dump 242 Mo → 46 s → doctor OK). À rejouer avant chaque pilote (manuel). Restauration réelle : `labuse restore-db` (confirmation explicite) + `warm-demo`.

### C4 — Préparation démo
- **Quoi** : `demo_setup.sh` (projet démo idempotent) + `labuse prepare-pilot` avant chaque RDV (`PILOT_DEPLOYMENT.md:106`). Réseau du lieu à tester d'avance (CDN Leaflet/tuiles).

---

## Notes d'intégrité
- `STATUS.md` est **périmé** (2026-07-06, dit « pas d'auth » — dépassé par M7 en ligne + auth active). Ne pas s'y fier.
- Prospection propriétaire = **100 % manuelle par choix légal** (RGPD : jamais de particulier nommé), pas un manque d'automatisation.
- `LABUSE_DEV_MODE` n'est **pas** le repli IA : il ne désactive que rate-limit/quotas. Le repli IA = le provider « stub ».

*Fin M2.*
