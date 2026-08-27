# AUDIT COMPTES & CLOISONNEMENT — RAPPORT

> Mandat AUDIT COMPTES & CLOISONNEMENT (27/08/2026). Branche `audit/comptes-cloisonnement`
> (depuis `e0732190`, qui inclut le merge du dashboard admin). LABUSE n'avait jamais eu qu'un
> seul compte réel : ce mandat est le **premier test à deux comptes clients coexistants** —
> le dernier angle mort avant la vente.
>
> **Méthode.** L'audit empirique (A2, A5, A7) est mené sur la base de test `labuse_test` via
> un `TestClient` FastAPI in-process, **auth active** (env pilot + secret), **comptes et
> sessions réels** (mêmes tables, même code, même cloison que la prod). Arbitrage : NE PAS
> opérer sur la base servie par l'uvicorn `:8000` en route — pour ne rien polluer ni risquer
> sur le serveur vivant (règle « ne tue rien »). La purge finale est vérifiée en SQL sur
> `labuse_test`. Les objets créés sont de vraies lignes SQL, l'attaque de cloison est réelle.

## Gravités
🔴 fuite / faille exploitable (corrigée dans ce mandat) · 🟠 durcissement recommandé (risque
réel non exploité) · 🟡 constat / dette / amélioration UX-sécurité (documenté, décision Vic).

---

## A1 — INVENTAIRE DU CYCLE DE VIE (constat)

Tableau de l'état RÉEL aujourd'hui, mécanisme par mécanisme. Verdicts : ✅ existe et sain ·
⚠️ existe mais bancal · ❌ absent.

| # | Mécanisme | État | Chemin de code | Comment ça marche / défaut |
|---|-----------|------|----------------|----------------------------|
| 1 | **Création de compte** | ✅ (invitation only) | `comptes.py:118` `creer_invitation` · endpoint `dashboard.py` `admin_licence_creer` · UI `onboarding.py:41` | Par INVITATION admin uniquement (pas de self-service). Crée `comptes` (statut `invite`) + `utilisateurs` (rôle `titulaire`, statut `invite`). Token SHA-256 en base, **7 jours**, usage unique. Lien envoyé à la main. |
| 2 | **Première connexion** | ✅ | `onboarding.py:79` `invitation_submit` · `comptes.py:163` `activer_par_invitation` | L'invité pose SON mot de passe (min 10 c.) + accepte CGV horodatées. Token consommé, utilisateur → `actif`. Le compte reste `invite` jusqu'au paiement Stripe. Pas de mot de passe provisoire (l'invité le choisit d'emblée). |
| 3 | **Changer son mot de passe (connecté)** | ❌ **ABSENT** | — (aucun endpoint) | Un utilisateur connecté **ne peut pas** changer son mot de passe : il doit passer par le flux « oublié » (reset), qui tue toutes ses sessions. Lacune UX-sécurité. → **AC-010 🟡** |
| 4 | **Mot de passe oublié (reset)** | ✅ (anti-énumération) | `comptes.py:282` `demander_reset` / `299` `appliquer_reset` · `onboarding.py:237/274` | POST `/reset-demande` (email). Token SHA-256, **60 min**, usage unique. Réponse identique que l'email existe ou non (anti-énumération). Application : nouveau mdp (min 10 c.), **toutes** les sessions du compte révoquées, compteur d'échecs remis à 0. Pas d'e-mail de confirmation post-reset. |
| 5 | **Durée / expiration de session** | ⚠️ | `comptes.py:230` `creer_session` · `config.py:51` `session_hours=12.0` | Token SHA-256 en base, `expire_at = now()+12 h` (config `LABUSE_SESSION_HOURS`). Cookie httpOnly/SameSite=Lax/Secure. Vérifié à CHAQUE requête (`expire_at > now()`). **Pas de renouvellement glissant** ; **pas de purge des sessions expirées** (lignes mortes en base). → **AC-011 🟡** |
| 6 | **Déconnexion** | ✅ | `app.py` `logout` · `comptes.py:275` `detruire_session` | `/logout` fait `DELETE FROM sessions_auth WHERE token_hash` — **révocation serveur immédiate**, pas seulement le cookie (un cookie rejoué ne rouvre pas l'accès). |
| 7 | **Verrouillage après échecs** | ✅ | `comptes.py:186` `verifier_login` · `config.py:188` `login_echecs_max=5`, `login_verrou_minutes=15` | 5 échecs → verrou 15 min (`verrouille_jusqu_a`). Message JAMAIS différencié (« e-mail ou mot de passe incorrect »). Pas de déverrouillage admin manuel (attendre 15 min ou SQL). → **AC-012 🟡** |
| 8 | **Suppression de compte** | ✅ (RGPD réel) | `comptes.py:422` `supprimer_utilisateur` / `443` `effacer_compte_rgpd` · CLI `effacement-rgpd` | Deux niveaux : suppression d'un utilisateur (anonymise l'audit, DELETE utilisateur, compte → `resilie` s'il devient vide) ; effacement compte entier (`DELETE FROM comptes` → CASCADE sur les 10 tables scopées). Pas d'auto-suppression client, pas de délai de grâce, pas de confirmation 2 temps. → détaillé en **A6**. |
| 9 | **Hachage du mot de passe** | ✅ | `comptes.py:20` `PasswordHasher()` (argon2-cffi) | **argon2id** (OWASP), paramètres lib par défaut (time_cost=3, 64 MiB, parallelism=4). Rehash automatique au login si les paramètres changent (`check_needs_rehash`). |
| 10 | **Robustesse du mot de passe** | ⚠️ | `comptes.py:174` / `305` (`len < 10`) | Contrainte serveur = **longueur ≥ 10 uniquement**. Aucune complexité exigée (`aaaaaaaaaa` passe). Le front conseille « mélangez lettres, chiffres, symboles » mais ce n'est pas validé serveur. Acceptable (verrou anti-brute-force) mais non optimal. → **AC-013 🟡** |
| 11 | **Mot de passe admin** | ⚠️ (double nature) | `config.py:45` `auth_password` · `auth.py:196` `password_ok` · `auth.py:168` `exiger_admin` | Deux mondes : (a) PILOTE — mot de passe partagé `LABUSE_AUTH_PASSWORD` (clair ou `sha256:…`), session **signée HMAC sans état en base**, admin de fait ; (b) MULTI-COMPTE — utilisateur `role='admin'`. Le pilote n'a **ni verrou d'échecs ni traçabilité d'identité**. → détaillé en **A4** (**AC-020/021/022**). |

**Synthèse config** (défauts) : session 12 h · verrou 5 échecs / 15 min · token reset 60 min ·
token invitation 7 j · essai 48 h. `reset` et `invitation` sont **codés en dur** (non config).

**Verdict A1.** Authentification de fond solide (argon2id, tokens hachés en base, anti-énumération,
révocation immédiate, RGPD réel). Angles morts, tous **non bloquants** et documentés :
changer-son-mdp absent (AC-010), sessions non purgées (AC-011), pas de déverrouillage admin
(AC-012), complexité mdp non exigée (AC-013), double-nature du mdp pilote (A4). Aucune de ces
lignes n'est une fuite de cloisonnement — le cœur du mandat (A2) est traité séparément.

---

## A2 — CLOISONNEMENT À DEUX COMPTES RÉELS (cœur du mandat)

**Méthode.** Deux comptes clients réels `[AUDIT-TEST]` — **Stéphanie** et **Caroline** — créés
par le mécanisme officiel (invitation → activation → statut `actif`), sessions réelles. Chacune
a créé un objet de **chaque type propre au compte** (projet, entrée CRM, colonne CRM, filtre
sauvé, recherche sauvée, zone de veille, parcelle suivie, signalement, demande de courrier,
conversation Copilote, veille Copilote, événement). Puis, **session de Stéphanie en main**,
attaque des objets de Caroline sur les **80 routes `{param}` de `openapi.json`** (harnais
`qa/comptes/audit_a2.py`), suivie d'une levée d'ambiguïté ciblée (`audit_a2_cible.py`,
`audit_a2_cible2.py`) sur les cas non tranchés par le seul code HTTP.

**Résultat : AUCUNE FUITE.** Aucun objet d'un compte n'est atteignable depuis l'autre — par id
direct, id deviné, filtre, export, recherche, deep-link, Copilote ou notifications. Les objets
attaqués **survivent** intacts. Symétriquement, **aucun sur-filtrage** : chaque compte retrouve
l'intégralité de ses propres objets.

### Matrice de cloisonnement (routes d'objet, attaque cross-compte)

| Route | Objet | Attaque de Stéphanie sur l'objet de Caroline | Verdict |
|-------|-------|----------------------------------------------|---------|
| GET/PATCH/DELETE `/projets/{pid}` | projet | 404 | ✅ cloisonné |
| POST `/projets/{pid}/{rejouer,proposer,ajouter,chercher-plus}` | projet | 404 (payload valide) | ✅ |
| GET `/projets/{pid}/{parcelles,carte,export.pdf,export.csv}` | projet | 404 | ✅ |
| PATCH `/projets/{pid}/parcelle/{idu}` | projet | 404 (payload valide) | ✅ |
| PATCH/DELETE/restore `/pipeline/{entry_id}` | CRM | 404 | ✅ |
| PATCH/DELETE `/pipeline/columns/{col_id}` | CRM colonne | 404 (`_own_column` IDOR) | ✅ |
| DELETE `/filters/{filter_id}` | filtre | 404 | ✅ |
| PATCH/DELETE `/events/searches/{sid}` | recherche | 200 idempotent — objet **survit** (cloison SQL `AND compte_id IS NOT DISTINCT FROM`) | ✅ |
| PATCH/DELETE `/watch-zones/{zone_id}` | zone veille | 404 (payload valide) | ✅ |
| POST `/events/{event_id}/read` | événement | 200 idempotent — `lu` reste false, event **non visible** de Stéphanie | ✅ |
| GET `/api/copilote-v2/missions/{conversation_id}` | conversation | 404 | ✅ |
| DELETE `/api/copilote-v2/veilles/{veille_id}` | veille | 200 idempotent — veille **survit** (`actif` reste true) | ✅ |
| POST `/courrier/admin/demandes/{demande_id}/statut` | courrier | **403** (route admin) — demande intacte | ✅ |

**Balayage brut** : 80 routes `{param}`, dont 20 portent un id d'objet propre au compte —
**16 renvoient 404**, 4 renvoient 200/idempotent **prouvés non destructifs** (recherche, veille,
event, + les 422 de payload rejoués valides → 404). La seule « FUITE » signalée par le balayage
automatique (`DELETE veilles → 200`) était un **faux positif** : réponse `{ok:false}`, cloison SQL
vérifiée (l'objet ne bouge pas). Levé en test ciblé.

**Distinction 404 vs 403.** Les objets propres au compte renvoient **404** (« n'existe pas pour
toi » — ne révèle pas l'existence chez l'autre, correct). Les routes `/*/admin/*` renvoient **403**
(« réservé admin »). Les deux sont sains.

**Non-sur-filtrage prouvé.** Stéphanie voit son projet/CRM/filtre/zone ; Caroline voit son
projet/veille/event/courrier. Aucun objet légitime masqué à son propriétaire.

### Findings A2

- **AC-001 — RAS cloisonnement.** Aucune fuite inter-comptes sur les 20 routes d'objet. La
  cloison `tenant.py` (`compte_id IS NOT DISTINCT FROM :cid`, `SCOPED_TABLES` + FK cascade) tient
  à deux comptes réels, y compris sur les surfaces récentes (Copilote v2, colonnes CRM, courrier)
  **non couvertes** par les tests d'isolation existants. → **Régression gelée** :
  `tests/test_audit_comptes.py` (4 tests : veilles v2, conversations v2, colonnes CRM, courrier).

---

## A3 — PROPRE vs COMMUN

**Méthode.** Inventaire du schéma réel (lecture seule `information_schema` + `pg_constraint`) :
quelles tables portent `compte_id` (données propres), lesquelles ne l'ont pas (commun).

### Ce qui est PROPRE à un compte (26 tables portant `compte_id`)

| Domaine | Tables |
|---------|--------|
| Identité / accès | `comptes`, `utilisateurs`, `evenements_compte`, `licence_mails` |
| Prospection | `projets`, `pipeline_entries`, `crm_columns`, `saved_searches`, `saved_filters`, `signalements` |
| Veille / notifs | `watched_parcels`, `watch_zones`, `alertes`, `veilles`, `veille_reprise`, `event_log`, `event_seen`, `notif_prefs`, `notif_canaux` |
| Copilote / IA | `copilote_conversations` (+ `copilote_messages` via FK), `agent_runs`, `ia_log`, `usage_events` |
| Services | `courrier_demandes`, `lettre_zonage_refs`, `share_links`, `retours` |

### Ce qui est COMMUN à tous (aucun `compte_id`)

Vérifié sur les tables porteuses : `parcels`, `parcel_p_score_v2`, `parcel_residuel`,
`parcel_terrain`, `dryrun_parcel_evaluations`, `dvf_mutations`, `m10_permit_delais`, `zone_plu`,
`data_sources`, `copilote_messages` (cloisonné via `conversation_id`), `bilan_params`. **Aucune
donnée commune n'est dupliquée par compte** (aucune table commune ne porte `compte_id`), **aucune
donnée de compte ne réside hors des 26 tables scopées**. La ligne de partage est nette : la
donnée publique (parcelles, scores, prix, sources, run) est **partagée**, l'intention commerciale
(projets, CRM, veilles, conversations) est **cloisonnée**.

### Findings A3

- **AC-002 — Carte propre/commun saine.** ✅ Séparation nette, sans fuite ni duplication.
- **AC-003 🟠 — Effacement RGPD incomplet : 12 tables à `compte_id` SANS FK cascade.**
  `effacer_compte_rgpd` (`comptes.py:443`) fait `DELETE FROM comptes` et **compte sur la cascade
  FK** — son commentaire affirme « toutes portent `compte_id ON DELETE CASCADE` ». C'est vrai pour
  14 tables, **FAUX pour 12** ajoutées depuis :
  `copilote_conversations` (+`copilote_messages`), `veilles`, `veille_reprise`, `ia_log`,
  `usage_events`, `retours`, `licence_mails`, `notif_prefs`, `notif_canaux`, `share_links`,
  `lettre_zonage_refs`, `evenements_compte` (celui-ci est anonymisé exprès — légitime).
  À un effacement réel, ces lignes deviennent des **orphelins** (`compte_id` pointant vers un
  compte disparu ; les `serial` ne recyclent pas les id → invisibles à tout compte vivant, donc
  **pas une fuite de cloisonnement**). Mais c'est un **défaut de conformité** : du contenu
  potentiellement personnel survit à la demande d'effacement — surtout `copilote_conversations`
  /`copilote_messages` (le texte des échanges) et `share_links` (des liens de partage `/p/{token}`
  encore résolvables). Incohérence interne notable : `agent_runs` a la FK cascade, sa jumelle
  `copilote_conversations` ne l'a pas.
  → **NON corrigé dans ce mandat** (A6 = « constat + proposition, n'implémente pas »). Traité en
  détail et proposé dans `SUPPRESSION-SPEC.md`.

---

## A4 — RÔLES ET ACCÈS ADMIN

**Le 403 tient (vérifié après merges).** Balayage des **22 routes `/admin/*`** (`qa/comptes/audit_a4.py`)
depuis un compte **client** et un **non-connecté** :

- Client (rôle `titulaire`) → **403 sur les 22 routes** (16 immédiatement ; 6 POST renvoyaient
  d'abord 422 sur payload vide — **rejouées avec un payload valide, elles renvoient bien 403**).
- Non-connecté → **401 partout** (jamais 200). La garde `exiger_admin` (`auth.py:168`) tient sur
  toutes les surfaces admin, y compris celles ajoutées par le dashboard.
- **Régression gelée** : `tests/test_audit_comptes.py::test_a4_403_admin_sur_toutes_les_routes`
  (client 403 + anonyme non-200 sur les 22 routes, payloads valides).

### Durcissement (audité — findings)

- **AC-020 🟠 — Login PILOTE (mot de passe admin partagé) sans verrou ni rate-limit.** Le login
  utilisateur a le verrou 5 échecs / 15 min (`verifier_login`). Le login **pilote** (`identifiant`
  vide, mot de passe partagé `LABUSE_AUTH_PASSWORD` = **admin de fait**) n'a **que** `slow_failure()`
  (sleep 0,4 s) : **aucun verrou de compteur**, et `/login` **n'est pas** dans `PREFIXES_PROTEGES`
  → **pas de rate-limit applicatif** non plus. Brute-force du mot de passe admin partagé ralenti
  mais non borné (un reverse-proxy amont peut aider, hors app). **Recommandation** (non implémentée) :
  soit rate-limit/verrou par IP sur `/login`, soit **migrer Vic vers un compte `role='admin'`
  nominatif** (déjà couvert par le verrou 5/15 min) et retirer le mode pilote avant la vente.
- **AC-021 🟡 — 6 routes admin valident le corps AVANT la garde.** `/admin/degeler`,
  `/admin/licences/creer`, `/creer-essai`, `/{id}/mail`, `/admin/retours/{id}/statut`,
  `/courrier/admin/demandes/{id}/statut` : Pydantic répond 422 sur corps invalide **avant**
  `exiger_admin`. **Non exploitable** (403 avec payload valide, aucun accès), mais un non-admin
  peut inférer la forme du payload. Fix propre : `Depends(exiger_admin)` en dépendance de route
  (s'exécute avant la validation du corps).
- **AC-022 🟡 — Session pilote non révocable.** La session pilote est un **token HMAC signé sans
  état en base** (12 h) : `/logout` ne peut pas la révoquer côté serveur (contrairement à une
  session `role='admin'`, ligne en base supprimable). Un cookie pilote volé reste valide jusqu'à
  expiration. Autre raison de migrer l'admin vers un compte nominatif.
- **AC-023 🟡 — Journalisation admin partielle.** Les actions admin d'**écriture** sont tracées
  (notifications `event_log` : dégel, transition courrier, suspension). Les **consultations** admin
  (`GET /admin/pilotage|licences|stripe|ia|produit`) **ne sont pas** journalisées, et le login
  pilote n'écrit que dans le log fichier (`auth.log_event`), pas dans `event_log`. Recommandation :
  un **journal d'accès admin** (qui, quand, quelle route) — d'autant plus utile que le mot de passe
  pilote est partagé (aujourd'hui, impossible de dire *qui* s'est connecté en admin).
- **AC-024 🟡 — Rôle exposé au front.** `GET /moi` renvoie `role` au client ; le front s'en sert
  pour afficher/cacher l'entrée « Tour de contrôle ». **Sain** : la vraie garde est backend
  (`exiger_admin` re-vérifie à chaque route, prouvé ci-dessus) — le front ne fait que cacher l'UI.
  Aucune action admin n'est atteignable en forçant l'affichage côté client.

### Proposition — double authentification (demandée par le mandat)

Avant mise en ligne, **AC-025 🟠 (proposition, non implémentée)** : ajouter une **2FA TOTP sur le
seul compte admin**. Le plus propre : (1) retirer le mode pilote partagé, (2) créer un compte
`role='admin'` **nominatif** pour Vic (verrou d'échecs + session révocable déjà acquis), (3) exiger
un code TOTP (RFC 6238, ex. `pyotp`) à la connexion de ce compte. Surface minimale (un seul
compte), gain majeur : le point d'entrée le plus sensible (accès à tout le pilotage, aux licences,
à la suspension de comptes) passe de « un secret » à « un secret + un appareil ». À trancher par Vic.

---

## A5 — PARTAGE DE COMPTE

**Observable AVANT ce mandat.** `sessions_auth` = `(token_hash, utilisateur_id, created_at,
expire_at)` — **ni IP ni empreinte**. Aucun moyen de repérer qu'un compte est utilisé depuis
plusieurs postes. Les sessions concurrentes étaient comptables (une ligne par session) mais
indistinctes.

**Rate-limit par compte sur routes coûteuses : DÉJÀ EN PLACE** (constat, rien ajouté). Les quotas
JOURNALIERS sont épinglés au compte (`sujet_quota → c:<compte_id>`) : exports 30/j (Intégral) ou
200/j (Illimité) via `PLAFONDS_JOUR` ; Copilote runs 10/j (`copilote_quota_jour`) ; Copilote v2
40/j/compte (`copilote_v2_missions_jour`) ; dossiers 20/mois ; questions NL 80/j/licence. L'ingestion
est admin-only (pas de surface client). Le rate-limit par compte demandé « si absent » n'était pas
absent.

### Implémenté — mesure PROPORTIONNÉE et NON BLOQUANTE

- **Empreinte hachée de session** (`comptes.py` + `app.py` `/login`) : `ip_hash`, `ua_hash`
  (SHA-256 tronqué — **jamais l'IP/UA en clair**, RGPD) posés à la création de session.
- **Agrégat** `comptes.sessions_actives_par_compte()` : par compte, nombre de sessions actives
  (non expirées) et surtout **nombre d'IP distinctes simultanées**. Plusieurs IP actives sur la
  fenêtre de session (12 h) = plusieurs postes = **partage probable ET durable** (par construction :
  une session dure 12 h, ce n'est pas un pic instantané).
- **Seuil config** `sessions_signal_seuil = 3` (1 licence = 1 accès ; 3 postes = partage probable).
- **Endpoint** `GET /admin/partage` (admin) + **signal** dans `GET /admin/licences` (`partage`) :
  chip ambre « ⚠ Partage probable · N postes actifs » sur la fiche client du dashboard.
- **NON bloquant, prouvé** : aucune session n'est coupée, aucune connexion refusée. Vic voit,
  Vic décide. RGPD : seuls des **nombres** sont servis (les empreintes restent hachées en base).
- **Régression gelée** : `tests/test_audit_comptes.py::test_a5_signal_partage_sessions_multiples`
  (3 IP → signal ; 1 IP → pas de signal ; les sessions survivent).

### Finding A5

- **AC-004 — Partage de compte observable, mesure livrée.** ✅ Signal de partage (sessions/IP
  distinctes) posé et exposé au dashboard admin, non bloquant. Rate-limit par compte déjà en place
  sur toutes les routes coûteuses. Limite honnête : l'`ip_hash` distingue des **réseaux**, pas des
  personnes (3 collègues derrière un même NAT d'entreprise = 1 IP → non signalés ; c'est un choix
  conservateur qui évite les faux positifs, au prix de rater le partage intra-réseau — acceptable
  pour un signal informatif). Le `ua_hash` est collecté en complément (V2 : signal affiné
  navigateurs distincts). Historisation fine (time-series) laissée en V2.
