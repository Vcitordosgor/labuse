# ANGLE E — Les jobs et les files (CHASSE-ORFEVRE-1)

Audit en LECTURE SEULE (code + état réel de la base, aucun job exécuté). Worktree `~/Desktop/labuse-orfevre` (= main).
Script d'état rejouable : `docs/audit-2026-10/chasse-orfevre-1/scripts/angle_e_jobs.py` (sortie du 18/10 reprise ci-dessous).

Rappels d'architecture (lus, pas supposés) :
- **Registre unique** `src/labuse/jobs.py` (30 jobs déclarés, 29 planifiés — `agents-sources` est `planifie=False`).
  Le crontab `/etc/cron.d/labuse` est GÉNÉRÉ du registre (`cli.py:4928 _crontab_du_registre`, posé/vérifié par `deploy.sh:59-72`).
  Chaque ligne cron = `labuse jobs run <nom>` → `scripts/jobs/run-job.sh` (verrou **flock par job**, repli `mkdir` sur macOS)
  → `labuse jobs exec` → `jobs.exec_one` (timeout `signal.alarm`, état JSON atomique, `job_runs` + porte d'alerte `ops_alertes`, ping témoin).
- **Schedulers hors crontab** : 3 agents launchd sur le Mac de Vic (`deploy/mac/` : backup-offsite, restore-test mensuel, readyz-watch 15 min) ;
  déclencheurs « paresseux » à la requête (bascule essai expiré au login `comptes.py:385`, webhooks Stripe) ; rien d'autre (pas de
  scheduler interne au process : l'ancien `on_event startup` ne planifie rien).

---

## 1. Inventaire des jobs planifiés + verdict d'idempotence

Heures = Réunion (registre en UTC). « Écrit » = tables touchées. Verdicts : **IDEM** (idempotent prouvé par lecture du code),
**PARTIEL** (rejeu sans dégât client mais avec effet secondaire), **NON** (un rejeu produit un doublon visible).

| Job | Cadence (Réunion) | Écrit | Verdict | Preuve / réserve |
|---|---|---|---|---|
| sonde-sources | quotidien 07:00 | `source_veille`, 1 notif agrégée | **IDEM** | `sentinelle.py:315` : update par ligne, annonce dédupliquée par `dernier_notifie_vu` (même transaction) ; relancé le même jour → lignes plus « échues » = no-op |
| agents-sources | manuel seul (`planifie=False`) | `ia_log`, rapports | PARTIEL | plafond `LABUSE_AGENT_PLAFOND_EUR` défaut 0 → no-op ; try/except par source |
| filtres-sources | quotidien 07:05 | `filtre_resultats`/`filtre_versions`, notif dédup jour | PARTIEL | rejeu = nouvelles lignes de résultat (journal daté, voulu) ; try/except par source (`jobs_impl.py:877-881`) |
| coherence-robinets | quotidien 07:25 | `circuit_ecarts/controles/journal`, notifs dédup jour | PARTIEL | rejouable par design (bouton admin) ; journal append |
| ingest-bodacc | quotidien 06:40 | `bodacc_*` | **IDEM** | `ON CONFLICT (annonce_id) DO UPDATE` (`ingestion/bodacc.py:62/180`) |
| ingest-sitadel | mensuel le 10, 04:30 | `sitadel_permits`, `ingestion_runs`, notifs veille, mail candidat | PARTIEL | upsert `ON CONFLICT (permit_id)` + purge doublons (`permits_sdes.py:104-131`) = IDEM ; mais rejeu = 2ᵉ mail « run candidat » (`golden_ops.rapport_candidat`, aucune dédup d'envoi) |
| ingest-dpe | mensuel le 12 | `dpe_records` | PARTIEL | upsert `numero_dpe` + `DELETE … <> ALL(:gardes)` dans LA MÊME transaction (`dpe.py:333`) = rejeu sûr ; réserve E-13 (purge masse si amont tronqué en silence) |
| ingest-sirene | mensuel le 7 | `sirene_etablissements` (rebuild), `etablissement_parcelle` | **IDEM** | `DELETE FROM` + réinsertion + maj millésime dans UNE transaction (`sirene_etablissements.py:143-174`, commit par `session_scope` du sous-process) ; kill au milieu = rollback complet |
| sync-gpu | mensuel le 15 | notifs veille foncière | PARTIEL | délègue à `veilles.evaluer_toutes` (dédup notifs côté `creer_notification`) — non re-prouvé ligne à ligne |
| ingest-dvf | hebdo mardi 05:00 | tables DVF | **IDEM** | garde no-op par Last-Modified : « ne recharge QUE si nouvelle livraison » (`cli.py:4307`) |
| backup-postgres | quotidien 13:30 | fichiers `/var/backups` | PARTIEL | dump horodaté à la seconde : rejeu = 2ᵉ dump le même jour → mange un cran de la rotation KEEP=4 (perd un jour d'historique) ; garde taille mini + garde-disque |
| pg-maintenance | hebdo dim 04:00 | rien (VACUUM) | **IDEM** | autocommit, try par table (`jobs_impl.py:495-513`) |
| healthcheck | 15 min | `ops_incidents`, état JSON | **IDEM** (mais vigie CASSÉE, E-04) | signaler/resoudre dédupliqués par clé |
| sante-endpoints | 7 et 37 de chaque heure | notif dédup jour | **IDEM** | dédup `sante_endpoints:<date>` (`jobs_impl.py:458`) |
| copilote-purge | quotidien 03:30 | DELETE conversations | **IDEM** | purge par ancienneté, re-purger = no-op |
| abuse-scan | quotidien 10:00 | signalements | PARTIEL | délégué CLI, non approfondi (informatif, jamais de blocage) |
| purge-sessions | quotidien 08:00 | DELETE `sessions_auth` expirées | **IDEM** | prédicat `expire_at < now()` |
| radar-cloche | quotidien 07:05 | `event_log` (cloche client) | **IDEM** | passe par `creer_notification` dédup compte+bien+jour (vraie dédup, contrairement à E-03) |
| radar-cycle | quotidien 04:00 | `pige_biens.statut`, event_log | **IDEM** | transitions gardées par `WHERE statut='active'…` (`pige/cycle.py:50-68`) : déjà basculé = ne re-matche pas |
| radar-cycle-dvf | quotidien 04:30 | `pige_biens` → vendue | **IDEM** | `WHERE … statut <> 'vendue'` (`cycle.py:76-81`) |
| radar-cycle-mensuel | le 1ᵉʳ, 05:30 | `pige_biens` → retiree_sans_vente | **IDEM** | `WHERE statut='retiree'` ; qualifié = sort du prédicat |
| evaluer-suivis | quotidien 07:02 | `event_log` | **IDEM** | dédup PERMANENTE par fait (`suivi:mut:<idu>:<id_mutation>` etc., `api/events.py:447-484`) — « rejeu = 0 » |
| detect-events | quotidien 07:04 | `event_log` | **IDEM** | dédup `(kind, idu, run_from, run_to)` (`events.py:585`) ; aucun run précédent → exit 0 |
| digest | quotidien 07:15 | `mail_queue`, `notif_prefs.last_digest_at` | **IDEM** | DOUBLE barrière : `last_digest_at` (20 h) + dédup mail_queue `digest:<cid>:<date>` fenêtre 20 h (`events.py:1385-1446`) ; crash entre enfilage et commit couvert par la dédup |
| mail-queue-consommer | 5 min | `mail_queue`, `evenements_compte` | PARTIEL | séquentiel sûr (`recu`/`annule` jamais retentés, budget 240 s < timeout 300 s) ; MAIS course possible avec un geste admin → E-02 ; ligne poison → E-06 |
| fiche-commune-cache | quotidien 03:00 | `commune_contexte_cache` | **IDEM** | `ON CONFLICT (commune) DO UPDATE` (`api/app.py:2281+`), commit + rollback PAR commune |
| coherence-banc | quotidien 03:45 (dim : intégrale) | `coherence_runs`, `chasse_runs`, incidents | PARTIEL | journaux de passage datés (append voulu) ; gardes anti-« vert par vacuité » |
| recap-matin | quotidien 07:30 | `ops_incidents`, mail | **NON** | le mail récap lui-même n'a AUCUNE dédup (`jobs_impl.py:400-438` → `_envoyer_alerte` direct) : rejeu le même jour = 2ᵉ mail. Les rappels d'incidents, eux, sont dédupliqués (1/jour UTC) |
| verite-sources | mensuel le 15, 06:00 | `verite_sources_runs`, incidents | PARTIEL | nouveau rapport par passage (journal) ; incidents par clé dédupliqués |
| restore-test | mensuel le 1ᵉʳ, 05:00 | rien (pg_restore --list) | **IDEM** | lecture seule du dump |

**Bilan : 18 IDEMPOTENT PROUVÉ · 11 PARTIEL · 1 NON (recap-matin, doublon = un mail admin).**
Aucun job planifié ne produit de doublon CLIENT au rejeu — les deux vraies portes à doublons client sont dans la FILE (E-02) et dans le dépôt Radar hors-cron (E-03).

---

## 2. Constats détaillés

### E-01 — mail_queue : 12 mails « dus » armés, dont 3 vers un compte supprimé (approfondit A-14) — GÊNANT, PROUVÉ
- État réel (script, 18/10) : `a_rejouer` n=12 (16/10), `recu` n=5 ; **les 12 sont DUS maintenant**
  (`etat IN ('en_attente','a_rejouer') AND prevu_at <= now()`) : ids 48-59, templates mdp_oublie/onboarding1/essai/souscription/
  resiliation/suspension/retablissement, comptes 18/104/111 — **104 et 111 n'existent plus** (3 orphelins confirmés).
- Mécanique lue : en dry-run local, `mail.envoyer_mail` → `mailfile.envoyer_mail` tente quand même le départ immédiat
  (la façade `mail.py:249` ne passe PAS `dry_run`) ; le transport répond « dry-run » = échec → l'entrée passe `a_rejouer`
  avec `prevu_at` (mailfile.py:213-236). Le worker (`mail_queue_consommer`, jobs_impl.py:321-332) ne consomme RIEN en dry-run…
  mais les lignes RESTENT éligibles à jamais : `consommer()` (mailfile.py:295-328) n'a **ni garde d'âge, ni garde d'environnement**.
- Scénario concret : on pose `LABUSE_MAIL_REEL=1` (ou une clé Brevo) sur cette base pour un test → au premier passage du worker,
  les 12 mails de recette partent réellement, dont 3 vers `a07test@example.com` (compte supprimé) — réputation domaine + confusion.
- Correction proposée (non appliquée) : purger les 12 (déjà proposé A-14) **et** durcir `consommer()` : ignorer (passer `annule` avec motif)
  toute ligne due depuis plus de N jours (ex. 7) et toute ligne dont `compte_id` n'existe plus.

### E-02 — mail_queue : le verrou FOR UPDATE est relâché AVANT l'envoi → double envoi possible — GÊNANT, THÉORIQUE
- `mailfile._tenter_depart` (mailfile.py:172-236) : le `SELECT … FOR UPDATE` vit dans un premier `engine.begin()` qui se
  **commit (et relâche le verrou) avant l'appel transport** (l'I/O réseau est volontairement hors transaction, ligne 184-202) ;
  l'état n'est écrit qu'après, dans une 2ᵉ transaction. Le commentaire ligne 215-216 (« le SELECT ... FOR UPDATE sérialise,
  jamais d'envoi en double ») est donc FAUX entre processus.
- Le flock par job empêche deux workers ; mais rien n'empêche **worker ↔ geste admin** : Vic clique « rejouer » (`rejouer()`,
  mailfile.py:263-276, remet `en_attente` + tentatives=0 puis tente le départ) pendant que le worker traite la même ligne →
  les deux lisent un état envoyable, les deux appellent Brevo → **le client reçoit deux fois le mail**.
- Correction proposée : transition d'ÉTAT revendicative avant l'envoi — `UPDATE mail_queue SET etat='parti' WHERE id=:i AND etat
  IN ('en_attente','a_rejouer') RETURNING *` ; 0 ligne = quelqu'un d'autre l'a pris (l'état `parti`, aujourd'hui mort — E-09 —
  trouverait enfin son rôle de « en cours d'envoi »).

### E-03 — Radar : `journaliser` porte une clé dedup DÉCORATIVE → doublons massifs prouvés — GÊNANT, PROUVÉ
- `pige/tables.py:331-343` : INSERT DIRECT dans `event_log` avec la colonne `dedup` remplie mais **jamais vérifiée**
  (seul `creer_notification` applique la dédup ; `event_log` n'a aucune contrainte unique sur dedup).
- État réel : **31 couples (dedup, jour) dupliqués**, jusqu'à **×19** (`pige:depot:0583f724ecce…` et `f7d247a92f03…` le 10/10,
  `pige:hausse:300:450000` ×17 le 06/10) ; et `pige_depots` contient **19 fois le même hash de fichier** (238 dépôts, top 19/19/16/14/14) :
  le dépôt HTML (`pige/html_ingest.py:487-499`) n'a AUCUNE garde « hash déjà vu » — chaque re-dépôt du même fichier ré-insère
  dépôt + événement + (via `_maj_prix`, html_ingest.py:72-87) des allers-retours hausse/baisse dans `pige_prix_historique`.
- Conséquence : journal pilote pollué (le « rituel de Vic » compte 19 dépôts pour 1), compteurs de dépôt faux. Les CLIENTS sont
  protégés en aval (radar-cloche passe par `creer_notification`, dédup réelle).
- Correction proposée : garde `SELECT 1 FROM pige_depots WHERE hash=:h` (ou index unique + ON CONFLICT) avant ré-ingestion ;
  et faire passer `journaliser` par la même dédup que `creer_notification` (ou poser un index unique partiel sur
  `event_log(dedup, (ts::date))` pour les kinds pige).

### E-04 — healthcheck : le compteur « 2 échecs consécutifs » ne peut JAMAIS atteindre 2 — GÊNANT, PROUVÉ (par code)
- `jobs.exec_one` écrit l'état « en_cours » avec `compteurs: {}` AVANT d'exécuter le job (`jobs.py:154-157`) ;
  `healthcheck` relit ensuite CE fichier (`jobs_impl.py:359-360 : lire_etat("healthcheck")`) pour récupérer
  `echecs_consecutifs` → il lit toujours `{}` → `echecs` vaut toujours 0 puis au plus 1.
- Conséquence : `if not ok and echecs >= 2: raise` (`jobs_impl.py:396-397`) est du code MORT — /health peut être injoignable
  des heures : le job reste « ok », **le ping témoin externe (dead man's switch) reste VERT** (`_ping_temoin(nom, ok=True)`),
  aucun incident `job-echec:healthcheck`. Compensation partielle : la sonde /readyz du même job ouvre bien l'incident `readyz`
  (si la DB est joignable), et le readyz-watch launchd du Mac double la vigie de l'extérieur.
- Correction proposée : lire le compteur AVANT d'écraser l'état (exec_one passe l'ancien état au job), ou persister
  `echecs_consecutifs` ailleurs (table, fichier dédié).

### E-05 — `_ingest_via_cli` : sous-process sans timeout → ingestion ORPHELINE après le timeout du job — GÊNANT, THÉORIQUE
- `jobs_impl.py:555-564` : `subprocess.run(cmd, …)` SANS `timeout=` et sans kill à l'alarme. Quand `signal.alarm`
  (timeout du job, ex. ingest-dpe 3600 s) frappe, l'exception `_Timeout` remonte dans le parent… mais **l'enfant
  (`python -m labuse.cli ingest-dpe`) continue de tourner et de committer**.
- Scénario : job marqué « timeout », alerte part, Vic relance à la main → le flock du wrapper ne voit PAS l'orphelin
  (il verrouille le wrapper, pas l'enfant) → **deux ingestions concurrentes** sur la même table. Frère direct du piège
  SCORING-6 (« compteur dit une chose, la base une autre »).
- Concernés : ingest-sirene, ingest-sitadel, ingest-dpe, ingest-dvf, ingest-bodacc, abuse-scan, purge-sessions.
- Correction proposée : `subprocess.run(..., timeout=job.timeout_s - marge)` + kill du groupe de process dans le `except _Timeout`.

### E-06 — `consommer()` : pas de try/except PAR MAIL → une ligne poison bloque toute la file — À SURVEILLER, THÉORIQUE
- `mailfile.py:312-322` : la boucle appelle `_tenter_depart(engine, mid)` sans capture ; une exception (erreur DB passagère,
  params inattendus) fait échouer le job ENTIER, et comme l'ordre est stable (`ORDER BY prevu_at NULLS FIRST, id`), la même
  ligne re-plante en tête **toutes les 5 minutes** : la file entière est gelée derrière elle.
- Atténuations réelles : les transports n'élèvent pas (brevo.py:339 et mail.py retournent toujours un dict/SendResult) ;
  l'échec du job ouvre l'incident `job-echec:mail-queue-consommer` (visible le jour même).
- Correction proposée : try/except par mail (la ligne fautive passe `echec` avec la raison, la boucle continue).

### E-07 — Courrier : 28 demandes « à déposer » dont la plus vieille du 25/08, sans relance — À SURVEILLER, PROUVÉ (état)
- Automate `courrier_demandes` (courrier.py:120-136) : `demande → depose → envoye → repondu | sans_reponse` ;
  alias legacy (`tarif_confirme/imprime/poste`) normalisés À LA LECTURE seulement — la base garde encore 2 lignes `poste`.
- Toutes les transitions sont des GESTES humains (dashboard/CRM) : **aucun consommateur automatique, aucune alerte d'ancienneté**.
  État réel : 28 `demande` (plus vieille 2026-08-25, ~8 semaines), 1 `depose`, 2 `poste` ; `courrier_envois` : 3 `simule`,
  et un statut `erreur` possible SANS rejeu automatique (courrier.py:656-660).
- Risque secondaire (théorique) : `envoyer()` appelle Merci Facteur AVANT l'INSERT (courrier.py:656-664) — un crash entre les
  deux = lettre réellement partie sans trace, et un re-clic = lettre en double (le plafond/jour compte les lignes, pas l'appel).
- Correction proposée : tuile « demandes > N jours » dans le récap/dashboard ; migrer les 2 `poste` en base ; insérer la ligne
  `courrier_envois` en « en_cours » AVANT l'appel prestataire puis la mettre à jour.

### E-08 — Verrou de job : le repli `mkdir` (macOS) survit à un kill -9 → tours sautés À JAMAIS en silence — COSMÉTIQUE (dev)
- `scripts/jobs/run-job.sh` : sans flock, verrou = `mkdir` + `trap EXIT` ; un kill -9 n'exécute pas le trap → le lockdir reste →
  tous les lancements suivants sortent code 200 « déjà en cours » sans jamais expirer. Sur le VPS, flock (kernel) est sain.
- Correction proposée : au repli mkdir, poser le PID dans le lockdir et le voler si le process est mort.

### E-09 — mail_queue : l'état `parti` n'est JAMAIS produit — COSMÉTIQUE
- Vocabulaire et CHECK le déclarent (mailfile.py:55, 75), `lister('partis')`/`compteurs` le comptent (lignes 344, 370),
  mais aucune écriture `etat='parti'` n'existe dans le code (grep = 0) : transitions réelles `en_attente → recu` direct.
  État mort — ou à recycler en « en cours d'envoi » revendicatif (cf. E-02).

### E-10 — recap-matin et rapport candidat : le MAIL n'a pas de dédup jour — COSMÉTIQUE
- `recap_matin` (jobs_impl.py:400-438) envoie par `_envoyer_alerte` à CHAQUE passage : un rejeu manuel le même jour = 2ᵉ récap.
  Idem le mail « run candidat » en fin d'ingest-sitadel. Destinataire = admin uniquement. (Les rappels d'INCIDENTS, eux,
  sont bien bornés à 1/jour — `ops_alertes.signaler`, avec la réserve de fuseau D-04 : jour UTC.)

### E-11 — Chevauchements de fenêtres — À SURVEILLER, THÉORIQUE
- **detect-events (07:04, timeout 15 min) peut finir APRÈS le digest (07:15)** : les bascules posées à 07:16 manquent le digest
  du jour ; la fenêtre du digest est GLISSANTE (`ts >= now() - interval '1 day'`, events.py:1125) → rattrapées le lendemain.
  Retard d'un jour possible, jamais de perte ni doublon.
- **coherence-banc (03:45, jusqu'à 2 h) lit pendant que radar-cycle/radar-cycle-dvf (04:00/04:30) écrivent `pige_biens`** :
  verdicts calculés sur des données mouvantes → un faux écart possible un matin (auto-résolu le lendemain).
- **ingest-bodacc (06:40, timeout 30 min) peut déborder sur evaluer-suivis (07:02)** : un fait ingéré à 07:05 est notifié
  le lendemain (dédup permanente par fait → pas de doublon).
- **filtres-sources et radar-cloche partagent 07:05** : tables disjointes (`filtre_*` vs `event_log`), pas de conflit.
- Auto-chevauchement (job qui déborde sur son propre tour suivant) : IMPOSSIBLE par flock (code 200 = tour sauté, tracé au log).

### E-12 — Suite B-02 : la perte SIRENE du 18/10 n'est PAS le job `ingest-sirene` — CONTEXTE, PROUVÉ
- Le seul écrivain applicatif de `sirene_etablissements` est le rebuild complet transactionnel (`sirene_etablissements.py:143`)
  et `ingested_at` a `DEFAULT now()` (DDL ligne ~57) : si le job avait tourné le 18/10, TOUTES les lignes seraient datées du 18/10.
  Or elles datent toutes du 29/08 → la purge des 15 009 lignes est un geste HORS-JOB (SQL manuel ou worktree voisin — la base
  dev est PARTAGÉE, piège déjà documenté DASHBOARD-4).
- `job_runs` à 1 ligne n'est PAS une anomalie sur CE Mac : aucun crontab local (`crontab -l` vide, pas de `/etc/cron.d`) — les
  jobs ne tournent qu'en prod ; l'unique ligne = un passage manuel de fiche-commune-cache le 17/10. **À vérifier côté VPS** :
  `job_runs` doit y être dense (29 jobs planifiés) ; s'il est vide là-bas, c'est l'historique durable SOLIDITE-1 qui ne marche pas.
- Le fond de B-02 reste vrai : un DELETE manuel ne laisse AUCUNE trace (ni job_runs, ni event_log, ni ingestion_runs).

### E-13 — DPE : `DELETE … <> ALL(gardes)` sans garde de volume — À SURVEILLER, THÉORIQUE
- `ingestion/dpe.py:333` : tout `numero_dpe` du jeu NON revu par le passage courant est supprimé. Si l'amont (data-fair ADEME)
  tronque une pagination SANS lever d'erreur, `gardes` est court → purge de masse committée. Même transaction donc un CRASH
  est sûr (rollback) ; c'est la troncature SILENCIEUSE qui est dangereuse. Le backup a une garde « rétrécie de 30 % »
  (ops_alertes.py:329) ; la table DPE n'a pas d'équivalent.
- Correction proposée : refuser le DELETE si `len(gardes) < 0,7 × count(*)` existant du jeu.

### E-14 — `creer_notification` : dédup SELECT-puis-INSERT sans contrainte unique — COSMÉTIQUE, THÉORIQUE
- `api/events.py:198-217` : deux producteurs CONCURRENTS (ex. webhook + cron au même instant) peuvent passer la vérification
  tous les deux → doublon de cloche. En pratique les producteurs cron sont mono-thread (flock) ; la fenêtre est minuscule.

### Points SAINS vérifiés (à ne pas re-auditer)
- **Stripe webhooks** : dédup `stripe_events` (PK) posée DANS la même transaction que l'effet (`facturation.py:399-412`, P2-41) —
  exactly-once sérialisé, rollback = rejeu Stripe ré-applique. 185 events en base, dernier 25/07 (clé test). Relance carte
  dédupliquée par facture sur 30 j (`facturation.py:492`).
- **mail-queue vs SIGALRM** : budget 240 s < timeout 300 s (`mailfile.py:37-43`) — le correctif de l'incident du 14/10
  (« another command is already in progress ») est en place.
- **Sitadel** : la ligne `ingestion_runs 'running'` vit dans la MÊME transaction que l'ingestion (`permits_sdes.py:419`) —
  un kill ne laisse PAS de statut « running » fantôme. État réel : 59 runs tous `ok`, 0 coincé.
- **digest** : double barrière (last_digest_at 20 h + dédup mail_queue par compte/jour) — crash entre les deux commits couvert.
- **exec_one** : état JSON écrit atomiquement (tmp + replace, jobs.py:91-94) ; un kill -9 laisse « en_cours » au fichier
  (cosmétique) mais le détecteur de retard (`ops_alertes._jobs_en_retard`, 1,5 × cadence) rattrape le silence.

---

## 3. Les files — automates et état réel (18/10, script angle_e_jobs.py)

### mail_queue (automate lu dans mailfile.py)
```
en_attente ──départ ok──────────────► recu                (terminal)
    │   └──départ raté (tent ≤ 3)──► a_rejouer (prevu_at +5min/+1h/+24h)
    │                                   │ départ ok → recu
    │                                   └ tent > 3 → echec   (terminal sauf « rejouer » manuel → en_attente, tent=0)
    └──« annuler » (en_attente seul)─► annule              (terminal)
parti : déclaré, JAMAIS produit (E-09)
```
Consommateur : `mail-queue-consommer` (5 min, flock, budget 240 s, limite 200/passage).
État réel : `a_rejouer` 12 (toutes DUES, 16/10, tentative 1) · `recu` 5 · orphelins compte : 3 → **E-01**.
Pas de ligne `en_attente`/`echec`. Plus vieille ligne non traitée : 2 jours.

### event_log / cloche
Producteurs : jobs veille (dédup réelle via `creer_notification`) + Radar `journaliser` (dédup décorative → **E-03**).
État réel 7 j : `bascule` 54, `systeme` 1 ; **31 couples (dedup, jour) dupliqués** (tous `pige:*`).
Consommateurs : cloche (lecture), digest (fenêtre glissante 24 h/7 j), purge à 90 j — pas d'état bloquant possible (append + purge).

### ops_incidents
Automate : ouvert (mail) → rappel ≤ 1/jour (UTC — D-04) → résolu (mail) ; index unique partiel = 1 ouvert par clé.
État réel : **0 incident ouvert**. Pas de retry sans plafond (1 rappel/jour), pas d'état sans consommateur.

### Webhooks Stripe
Pas de file en base (traitement synchrone + table de dédup `stripe_events`) ; les retries sont CÔTÉ Stripe.
Filets : réconciliation « sub active sans webhook » et « Flash payé sans webhook » (facturation.py:287-378). Sain.

### Courrier
`courrier_demandes` : 28 `demande` (plus vieille 25/08) · 1 `depose` · 2 `poste` (legacy en base) → **E-07**.
`courrier_envois` : 3 `simule` ; état `erreur` possible sans consommateur de rejeu.

### Autres files de fait
- `ingestion_runs` : 59 `ok`, 0 `running` coincé.
- `source_veille` : 3 sondes à ≥ 3 échecs consécutifs ; 91 actives sans passage depuis 7 j et 13 jamais passées — NORMAL ici
  (pas de cron local) ; en prod ce chiffre doit tendre vers 0 après chaque sonde-sources.
- `pige_biens` : `retiree` 236 · `active` 116 — pas d'état orphelin de l'automate du cycle.
- `job_runs` : 1 ligne (dev sans cron — cf. E-12 ; à recompter en prod).

---

## 4. Récapitulatif des anomalies

| # | Gravité | Prouvé ? | Une ligne |
|---|---|---|---|
| E-01 | GÊNANT | prouvé (base) | 12 mails de recette DUS dans mail_queue (3 vers compte supprimé) ; `consommer()` sans garde d'âge → partiront au premier transport réel |
| E-02 | GÊNANT | théorique (code) | FOR UPDATE relâché avant l'envoi : course worker ↔ « rejouer » admin = mail client en double ; commentaire « sérialise » faux |
| E-03 | GÊNANT | prouvé (base) | dédup Radar décorative : event_log ×19 même clé/jour, pige_depots 19× le même hash — re-dépôt HTML non idempotent |
| E-04 | GÊNANT | prouvé (code) | healthcheck : compteur d'échecs écrasé avant lecture → l'alerte « /health 2 échecs » et le ping témoin ne détectent jamais rien |
| E-05 | GÊNANT | théorique (code) | timeout de job ≠ mort du sous-process d'ingestion : orphelin qui continue d'écrire + relance concurrente possible (frère SCORING-6) |
| E-06 | À SURVEILLER | théorique | pas de try/except par mail dans consommer() : une ligne poison gèle la file (mais alerte job-echec visible) |
| E-07 | À SURVEILLER | prouvé (base) | 28 courriers « à déposer » dont le plus vieux du 25/08, sans relance ; 2 statuts legacy `poste` en base ; envoi prestataire avant INSERT |
| E-08 | COSMÉTIQUE | prouvé (code, dev) | verrou mkdir (macOS) survit au kill -9 → tours sautés à jamais, en silence |
| E-09 | COSMÉTIQUE | prouvé (code) | état `parti` déclaré/compté mais jamais produit |
| E-10 | COSMÉTIQUE | prouvé (code) | mail récap du matin / rapport candidat sans dédup jour : rejeu = mail admin en double |
| E-11 | À SURVEILLER | théorique | chevauchements : detect-events peut finir après le digest (retard J+1) ; banc de nuit lit pendant que les cycles Radar écrivent |
| E-12 | CONTEXTE | prouvé (base+code) | perte SIRENE 18/10 : pas le job (rebuild transactionnel, ingested_at intact) — geste hors-job sur base partagée ; job_runs≈vide NORMAL en dev, à recompter en prod |
| E-13 | À SURVEILLER | théorique | DPE : DELETE `<> ALL(gardes)` sans garde de volume si l'amont tronque en silence |
| E-14 | COSMÉTIQUE | théorique | dédup creer_notification sans contrainte unique : course concurrente possible |

Aucune correction appliquée (mandat lecture seule). Priorités proposées : E-01 (purge + garde d'âge), E-04 (vigie morte),
E-02/E-03 (idempotence réelle de la file et du dépôt Radar), E-05 (timeout des sous-process).
