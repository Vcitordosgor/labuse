# RAPPORT M85 — Phase 0 : l'architecture des notifications et l'existant (STOP)

Branche `feat/m85-notifications`. Mesure pure, aucun fichier produit modifié. **STOP** : le mandant
valide le schéma retenu et choisit le fournisseur e-mail. Date de mesure : 2026-08-14.

---

## Le verdict, en une phrase (leçon M84 appliquée : mesurer avant d'affirmer)

**Le maillon n'est PAS à construire de zéro — la moitié existe déjà, mûre.** Un vrai centre de
notifications in-app (`event_log`) avec son API complète, un transport e-mail honnête (`mail.py`), un
digest opt-out/List-Unsubscribe (`envoyer_digests`), une table de préférences (`notif_prefs`) et des
gabarits (`emails.py`) sont **déjà là** (M21 / M-T / M-V). Le VRAI travail de M85 : **unifier** le
store parallèle de M78 dans ce centre, **poser la cloche** (l'API existe, l'UI non), **brancher les
producteurs manquants** (Copilote-veilles, ingestion/fraîcheur M84), **étendre les préférences** au
par-type/par-canal, et **garantir dédup/regroupement/plafonds**. Beaucoup moins de neuf que prévu.

---

## 0a — L'existant à unifier (mesuré)

### Deux stores de notification COEXISTENT (le doublon à trancher)

**1) `event_log` (`src/labuse/api/events.py`) — le centre MÛR, cloisonné par compte.**
- Schéma : `id, ts, kind (bascule|bodacc|permis|veille), idu, titre, detail, run_from/to, demo, lu,
  compte_id`. Cloison multi-tenant : `compte_id NULL` = feed marché/pilote partagé ; `event_seen`
  (compte_id, event_id) = suivi « vu » PAR COMPTE des lignes partagées (anti-IDOR déjà en place).
- **API in-app COMPLÈTE** : `GET /events` (liste, `unread_only`), `/events/count` (+ `par_parcelle`),
  `POST /{id}/read`, `POST /read-all`. Sécurité IDOR déjà traitée.
- **Producteur** : `detect_events(run_from, run_to)` (diff de runs → bascule/bodacc/permis, idempotent)
  + `_veilles_match` qui matche les **`saved_searches`** (filtres sauvegardés) en `kind='veille'`.
- **Volume mesuré : 1 ligne** (kind=veille). Quasi inutilisé faute de cloche et de cron.

**2) `veille_notifications` (`src/labuse/copilote_v2/veilles.py`) — le store PARALLÈLE de M78.**
- Schéma : `id, veille_id, compte_id, titre, detail, ref, vu, created_at`. Table `veilles`
  (compte_id, type, commune, criteres, last_evaluated_at) = les triggers Copilote.
- Producteur : `evaluer_toutes(db)` (SQL pur, zéro modèle) → écrit ici. API `/api/copilote-v2/veilles`
  + `/api/copilote-v2/notifications`. **AUCUNE cloche, AUCUN digest, AUCUNE préférence.**
- **Volume mesuré : 12 notifications, 4 veilles actives.** C'est la « moitié manquante » de M78.

**Le doublon** : M78 a recréé un store au lieu de brancher `event_log`. Deux concepts de « veille »
cohabitent — `saved_searches` (filtres, matchés dans event_log) et `veilles` Copilote (commune+type,
dans veille_notifications). Il faut n'en garder qu'UN centre.

### L'entrée « Veilles » du rail (observée M78-quater, jamais arbitrée)
`Rail.tsx` porte un bouton **« Veilles »** (`data-rail-veilles`, `toggleVeilles`) qui ouvre
`VeillesPanel.tsx` = les **zones géographiques de surveillance DVF** (M54-EXPO-3), PAS une liste de
notifications. Il porte déjà une **pastille ambre** (`data-veille-event`) pilotée par
`getEvents().unread` — donc un embryon d'indicateur de notification existe, mais sans panneau qui
liste les notifications ni cloche dédiée. **Sort à trancher en 1b** (devient la cloche ? cohabite ?).

### Le canal e-mail — PAS « rien branché » : le transport existe (M21-A)
- **`src/labuse/mail.py`** : `send_email` (synchrone, résultat honnête `SendResult{sent,detail}`),
  `send_email_async`, `mail_configured`. Sans SMTP configuré → journalise + `sent=False` (jamais un
  mensonge d'UI). Échec **logué avec sa cause, jamais silencieux** (motif M84 déjà respecté). STARTTLS
  587, `List-Unsubscribe` géré, plafond Gmail 500/j détecté et refusé explicitement.
- **`src/labuse/emails.py`** : gabarits `reset_password`, `avis_echeance`, **`digest_notifications`**.
- **`envoyer_digests(db, base_url, freq, force)`** (events.py) : digest COMPLET — opt-out
  (`notif_prefs.unsubscribed`), anti-double-envoi (intervalle mini), **digest vide ne part pas**,
  `List-Unsubscribe` posé, `last_digest_at` tracé. `_digest_data` agrège événements + résumé marché.
- Appelants réels de `send_email` : reset password (onboarding), avis d'échéance Chatel (comptes),
  digest (events), `labuse mail-test`. **Configuré par `LABUSE_SMTP_*` + `LABUSE_MAIL_FROM` en .env.**
- CLI : `labuse digest`, `detect-events`, `mail-test` existent. **Aucun cron installé** (`deploy/cron.d`
  n'a ni digest ni events) — dormant, même dépendance VPS que les crons M84.

### Les préférences utilisateur — la table EXISTE
`notif_prefs (compte_id PK, unsubscribed, token, digest_freq hebdo|quotidien, last_digest_at)`.
Volume : **0 ligne** (jamais peuplée). C'est une préférence **globale** (opt-out digest + fréquence),
PAS encore par-type/par-canal comme le veut la Phase 2c.

### Les comptes (destinataires)
`utilisateurs (id, compte_id, email UNIQUE, role admin|titulaire|membre|qa, statut)` — **16 lignes**.
`comptes (id, nom, plan, statut)`. `evenements_compte (type, compte_id, utilisateur_id, detail, at)` =
journal d'audit compte (stripe/échéances). L'e-mail vit sur `utilisateurs` ; l'admin = `role='admin'`.

---

## 0b — La décision de schéma (proposition)

**Recommandation : `event_log` DEVIENT le centre unifié.** Il a déjà tout ce que la table
« notifications » du mandat demande, en mieux (cloisonnement tenant + read-tracking partagé) :

| Champ mandat | event_log | Action |
|---|---|---|
| user | `compte_id` | ✓ (déjà cloisonné) |
| type | `kind` | ✓ + ajouter valeur `systeme` (ingestion/fraîcheur) |
| titre / corps | `titre` / `detail` | ✓ |
| lien | dérivé de `idu` | **ajouter `lien text`** (une alerte ingestion pointe /sources, pas une parcelle) |
| source | — | **ajouter `source varchar`** (« Copilote · veille », « Ingestion · SITADEL »…) |
| created_at | `ts` | ✓ |
| read_at | `lu` + `event_seen` | ✓ |
| statut_envoi | `notif_prefs.last_digest_at` (par compte) | **ajouter `envoi_statut` par ligne** (trace e-mail : ok/error/na — motif M84) |

**Migration de `veille_notifications` (12 lignes) → `event_log`** : rejeu unique (INSERT SELECT,
kind='veille', source='Copilote', compte_id, titre, detail, lien vers la veille). Puis **`evaluer_toutes`
écrit désormais dans `event_log`** (au lieu de veille_notifications) — la « moitié manquante » de M78
est comblée par la cloche existante. `veille_notifications` conservée en lecture le temps de la bascule
puis retirée (ou gelée). Table `veilles` (les triggers) CONSERVÉE.

**Coût de migration : faible.** 3 colonnes ajoutées à event_log (`lien`, `source`, `envoi_statut`),
12 lignes rejouées, `evaluer_toutes` rebranché (≈ 10 lignes), l'API copilote-v2/notifications
redirigée ou dépréciée. Zéro contact avec le scoring (golden intact garanti).

*Alternative écartée* : créer une table `notifications` toute neuve + fédérer event_log dedans =
plus de code, deux centres à maintenir, on perd le read-tracking tenant déjà debuggé. Non recommandé.

---

## 0c — Le fournisseur e-mail (le mandant tranche — compte à créer, son geste)

Le transport `mail.py` est **agnostique SMTP** : n'importe quel relais marche via `LABUSE_SMTP_*`.
Le choix = quel compte SMTP créer, avec quelle délivrabilité.

| Option | Offre gratuite | Délivrabilité | RGPD | Verdict |
|---|---|---|---|---|
| **Brevo (ex-Sendinblue)** | 300 e-mails/jour | bonne (SPF/DKIM, IP mutualisées chaudes) | **EU (France)** | **RECOMMANDÉ** — gratuit couvre 16 comptes largement, EU cohérent avec le retrait de Resend |
| Gmail SMTP (compte dédié) | ~500/jour | correcte en transactionnel vers des inscrits ; médiocre en froid | US | **repli v1 zéro-friction** — c'est déjà le défaut de config ; suffit pour la démo |
| Postmark | 100/mois puis payant | excellente (transactionnel pur) | US | trop juste en gratuit pour un digest quotidien |
| SMTP OVH (VPS) | inclus | risquée (IP VPS souvent mal réputée, greylisting) | EU | à éviter pour du client |
| ~~Resend~~ | — | — | — | **PROSCRIT** : retiré volontairement des sous-traitants le 22/07 (RGPD) — ne pas réintroduire |
| sendmail local | — | nulle (finit en spam) | — | **PROSCRIT** (mandat) |

**Recommandation : Brevo** (EU, 300/j gratuit, SPF/DKIM). Repli v1 : le SMTP Gmail déjà prévu en
config, pour livrer la chaîne sans attendre un compte. **Dans les deux cas, DNS à poser sur Cloudflare
(SPF + DKIM + DMARC) — procédure détaillée fournie en Phase 2, geste du mandant.** Secrets en .env,
jamais en dur (déjà la règle de `mail.py`).

---

## Ce que M85 doit RÉELLEMENT construire (après ton arbitrage)

1. **La cloche** (Phase 1b) : l'API `/events` existe, l'UI non (juste une pastille ambre). Cloche +
   panneau listant les notifications (titre, source, date, lien), mark-read. Placement à proposer.
2. **Unifier** (Phase 0b) : migrer les 12 lignes veille_notifications → event_log, rebrancher
   `evaluer_toutes`, ajouter `lien`/`source`/`envoi_statut`.
3. **Producteur ingestion/fraîcheur** (Phase 1c) : décrochage M84 / échec `trace_ingestion` →
   `event_log kind='systeme'` pour l'admin/pilote.
4. **Préférences par-type/par-canal** (Phase 2c) : étendre `notif_prefs`.
5. **Dédup / regroupement / plafonds** : event_log a l'idempotence par (kind,idu,run) ; ajouter le
   regroupement par jour (N permis = 1 notif à N entrées) + le plafond testé (bug → 1 digest groupé).
6. **Digest** (Phase 2) : `envoyer_digests` existe ; brancher le fournisseur choisi + le cron (dormant,
   dépend du VPS — M84).
7. **Brief du matin** (Phase 3) : enrichir le digest (« depuis hier sur vos secteurs » depuis les
   points M83, zéro recalcul) + carte Copilote.

---

## Les deux décisions attendues (STOP)

1. **Schéma** : je pars sur **`event_log` comme centre unifié** + migration de veille_notifications
   dedans (recommandation 0b) ? Ou tu préfères une table `notifications` neuve ?
2. **Fournisseur e-mail** : **Brevo** (recommandé) ? Gmail SMTP en repli v1 ? Autre ? — c'est le compte
   que tu créeras.

Et une sous-question qui attendra la Phase 1b : **le sort de l'entrée « Veilles » du rail** (devient la
cloche, ou la cloche est séparée et « Veilles » reste les zones géographiques ?).

## Garde-fous (Phase 0)
Mesure pure — aucun fichier produit modifié, aucune table touchée, golden non contacté. **NE PAS
MERGER.** J'attends ton arbitrage schéma + fournisseur.

---

# PHASE 1 — Le centre et la cloche (arbitrages Vic appliqués)

Décisions actées : **event_log = centre unifié** ; **veille_notifications SUPPRIMÉE** (aucun repli) ;
**Brevo** (pas de repli Gmail) ; **trois objets démêlés**. Livré et démontré de bout en bout.

## La nomenclature retenue (les trois objets, trois noms — demandé par Vic)

| Objet | Nom retenu | Où | Rôle |
|---|---|---|---|
| Ce que le client reçoit | **Notifications** | la CLOCHE (chrome global, en-tête) | le centre unifié (event_log) |
| Les déclencheurs | **Veilles** | Copilote + recherches sauvegardées | produisent des notifications |
| Les zones géographiques DVF (M54) | **Secteurs** | entrée du rail (renommée) | surveillance cartographique |

« Veilles » couvre les DEUX chemins de création de déclencheurs (Copilote commune+type, et recherches
sauvegardées filtrées) : ce sont tous des triggers qui alimentent le centre — cohérent. La cloche est
dans l'**en-tête** (placement retenu : convention universelle, à droite, près du compte), PAS le rail.
La pastille de notification a QUITTÉ l'entrée rail « Secteurs » (elle appartient à la cloche).
**« Secteurs » est mon nom proposé** pour l'ex-« Veilles » du rail — dis si tu préfères « Zones suivies ».

## 1a — La table et l'API
- **event_log + 4 colonnes** (idempotentes) : `source` (« dit sa source »), `lien` (cible directe :
  parcelle OU /sources), `dedup` (clé de déduplication), `envoi_statut` (trace e-mail par ligne, motif M84).
- **Producteur UNIQUE** `events.creer_notification` — tout producteur passe par lui. Trois garde-fous :
  **dédup** (même clé + même jour → 1 ligne), **regroupement** (au producteur : N faits = 1 notif à N
  entrées), **plafond dur** `NOTIF_CAP_JOUR=50` par kind/compte/jour (backstop anti-inondation).
- **Migration jouée** : 12 lignes `veille_notifications` → event_log (kind=veille, source='Copilote'),
  **table DROP**. Preuve par grep : aucun producteur/écrivain ne subsiste (seuls l'outil de migration
  one-shot — SELECT+DROP, no-op ensuite, requis pour migrer la prod — et des commentaires).
- **API** (déjà mûre, complétée) : `/events` non-lues D'ABORD + paginé (offset) + `source`/`lien`/`ts`
  exposés ; `/events/count`, `/{id}/read`, `/read-all` conservés. Rétention 90 j (`purge-notifications`).

## 1b — La cloche
- **Elle existait** (NotifBell, M16) : badge, panneau, mark-read, digest. **Enrichie M85** : chaque
  notification affiche sa **source**, une **date relative** (« il y a 3 h »), et un **lien vers l'objet**
  (parcelle suivie, sinon la cible — ex. /sources pour une alerte d'ingestion).
- **DA** : grammaire LABUSE, vert/neutre. Le badge « DÉMO » était **violet** → **neutralisé** (le mauve
  est réservé à l'IA, rien ici n'en est).
- Rail « Veilles » → **« Secteurs »** (zones DVF), pastille de notif retirée (séparation nette).

## 1c — Les producteurs branchés
- **Veilles Copilote** : `evaluer_toutes` écrit désormais dans le CENTRE (event_log), avec regroupement
  et dédup par contenu (rejeu du même lot = pas de doublon). Testé de bout en bout.
- **Ingestion / fraîcheur** : deux producteurs → notif `systeme` pour le **pilote/admin** (compte_id
  NULL, hors marché → INVISIBLE aux clients) : `notifier_fraicheur` (source en retard, dédup source/jour)
  et `trace_ingestion` en échec (une notif systeme, sans jamais masquer l'échec). `lien=/sources`.

## Démo (STOP Phase 1)
- Chaîne **ingestion→cloche** en direct : `notifier-fraicheur` → notif systeme « Source en retard : DPE
  ADEME » (source « Ingestion · dpe », lien /sources), visible à la cloche du pilote.
- Chaîne **veille→cloche** testée : veille + 400 permis injectés → **1** notification groupée (jamais 400).
- Playwright : rail « Secteurs », cloche ouverte, notifs ingestion + Copilote visibles, dates relatives,
  **0 erreur console**.

## Ce qui reste dormant (en attendant le compte Brevo + les crons VPS)
- L'e-mail (Phase 2) attend **Brevo** — dis-moi quand le compte est prêt (sinon on décale, pas de Gmail).
- `evaluer_toutes` / `notifier-fraicheur` / `purge-notifications` sont **cronables** mais **aucun cron
  n'est déployé** (même dépendance VPS que M84). En local, tout est déclenchable et testé.

## Garde-fous (Phase 1)
tsc 0 · vitest 36/36 · build vert · pytest 133 passed (+5 tests M85 ; `test_pdf_premium` = échec de
collection PRÉ-EXISTANT, non touché) · **golden 119/119 PASS, diff 0** (aucun contact scoring) · console
0 erreur · chaîne veille→cloche testée · chaîne ingestion→cloche testée · dédup + plafond + regroupement
(400→1) testés. **NE PAS MERGER.** STOP — Phase 2 (e-mail) sur ton feu vert Brevo.

---

# PHASE 2 — L'e-mail (Brevo configuré par Vic)

## 2a — Le canal
- **Transport** : `mail.py` (M21) étendu — `send_email` accepte désormais un **`body_html`**
  (multipart/alternative : le texte reste le repli, meilleure délivrabilité). Secrets en `.env`
  (`LABUSE_SMTP_*`), jamais en dur. Échec **tracé** (statut ok/error dans le retour + log), jamais
  silencieux (motif M84). Brevo = relais SMTP standard, rien de spécifique dans le code.
- **Gabarit DA** (`emails.digest_html_email`) : **vert #1E9E58 sur blanc**, wordmark LABUSE, sobre.
  **Aucune image externe** (le SVG est mal supporté en e-mail → wordmark ; zéro tracking tiers, zéro
  pixel espion). Le **mauve a disparu** du digest (l'ancien `🟣 DÉMO` de l'aperçu HTML est retiré).
- **DNS Cloudflare** (SPF `include:spf.brevo.com`, 2 DKIM `brevoN._domainkey`, DMARC `p=none`) :
  procédure complète écrite dans `docs/DEPLOYMENT_OVH_VPS.md` — ton geste (déjà fait, tu me l'as dit).

## 2b — Le digest, pas le spam
- **Un digest QUOTIDIEN**, calé sur **7h00 heure Réunion**. **Fuseau UTC+4 EXPLICITE** dans le code
  (`events.REUNION_TZ = timezone(timedelta(hours=4))`) — jamais hérité de la machine. Le cron VPS tire
  à **03:00 UTC = 07:00 Réunion** ; cron et code s'accordent sans dépendre du fuseau système.
- **Anti-double-envoi** (`last_digest_at` + intervalle mini 20 h) · **digest vide ne part pas** (aucun
  événement e-mail-activé ET résumé marché vide → ignoré) · **statut d'envoi tracé** (envoyes/echecs).
- **Exception « immédiat » par type** : **aucun type ne l'utilise en v1** (tout passe par le digest) —
  conforme au cahier ; le point d'extension existe (un type pourrait un jour pousser en direct).
- **Désinscription** (obligation légale) : `List-Unsubscribe` + lien dans chaque e-mail → coupe
  l'e-mail de TOUS les types (la cloche reste). **Lien « préférences »** dans chaque e-mail aussi.

## 2c — Les préférences (par type ET par canal — remplacent l'opt-out global de notif_prefs)
- **Table `notif_canaux` (compte, pref_type, cloche, email)**. `notif_prefs` ne garde QUE la
  comptabilité d'envoi (jeton désinscription, `last_digest_at`) — l'opt-out global est remplacé par le
  par-type/par-canal.
- **3 types client** (`event_log.kind` mappé) avec défauts raisonnables :

| Type | Couvre | Cloche | E-mail |
|---|---|---|---|
| **Vos veilles** | kind `veille` (Copilote + recherches) | ✓ | ✓ |
| **Vos parcelles suivies** | `permis`/`bascule`/`bodacc` perso | ✓ | ✓ |
| **Le marché** | `bascule`/`bodacc`/`match` partagés | ✓ | ✗ (volumineux — activable) |

  *(`systeme` — la tuyauterie ingestion — est HORS préférences client : pilote/admin seulement.)*
- **Filtrage effectif** : un type dont la **cloche** est coupée ne s'affiche NI ne compte à la cloche ;
  un type dont l'**e-mail** est coupé n'entre pas au digest. Testé.
- **Deux écrans** : in-app (compact, dans la cloche : 3 types × cloche/e-mail) + page serveur
  DA (jeton, atteignable depuis l'e-mail — le client règle tout sans se connecter). *(La session
  pilote ne persiste pas — compte NULL ; un vrai compte persiste.)*

## Démo (STOP Phase 2) — **il me faut TON serveur pour l'envoi réel**
En local, tout est vérifié SAUF l'envoi SMTP (dev sans clé Brevo → mail journalisé, `sent=False`
honnête). Le gabarit HTML se génère (vert #1E9E58, zéro mauve, zéro image externe, liens désabo +
préférences), les préférences filtrent, la page de préférences rend, le digest respecte anti-double +
vide. **Quand tu veux le test réel** : lance depuis ton serveur (qui a les identifiants Brevo)
`sudo -u labuse /opt/labuse/venv/bin/labuse digest --force` (ou d'abord `labuse mail-test <ton-email>`)
et dis-moi si le mail arrive — je corrige si besoin (SPF/DKIM, rendu).

## Ce qui reste dormant
- Le **cron `notifications`** (`deploy/cron.d/notifications`, 03:00 UTC) est écrit mais **pas déployé**
  (même dépendance VPS que M84) : veilles → fraîcheur → purge → digest. À installer avec les autres.

## Garde-fous (Phase 2)
tsc 0 · vitest 36/36 · build vert · pytest 141 passed (+10 tests M85) · **golden 119/119 PASS, diff 0** ·
console 0 erreur · gabarit HTML sans mauve/tracking vérifié · préférences par type/canal testées
(défauts, override, désinscription, filtre cloche, fuseau UTC+4) · digest anti-double + vide testés.
**NE PAS MERGER.** STOP — j'attends ton test d'envoi réel avant la Phase 3 (le brief du matin).
