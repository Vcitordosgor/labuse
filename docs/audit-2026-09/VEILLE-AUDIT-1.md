# VEILLE-AUDIT-1 — Ce qui déclenche, ce qui arrive, à qui

**Branche** `feat/veille-audit-1` · **hash de départ** `9b6a4cb11080e1ec986c26400b5dea8224a0c04c` (main à jour) ·
**worktree** `~/Desktop/labuse-veille` · **session** API :8145 / statique :8146 · **date** 22/09/2026 ·
**modèle** Opus · **lecture seule** (objets `[AUDIT-TEST]` créés puis purgés ; transport mail neutralisé —
aucun mail réel).

---

## Les trois chiffres

> **N = 6 types de veille** · **M = 3 ont un job du registre qui les évalue** · **K = 0 job du registre n'a jamais tourné en prod**

- **N = 6** déclencheurs : suivi de parcelle · secteur (zone dessinée) · recherche sauvegardée · veille
  Copilote « permis » · veille annonces Radar · sentinelle des sources amont. (5 orientés client + 1 pilote.)
- **M = 3** ont un job **du registre CRON-1** qui les évalue : Radar (`radar-digests`, quotidien) · veille
  Copilote permis (`ingest-sitadel` + `sync-gpu`, **mensuels**) · sentinelle (`sonde-sources`, quotidien).
  **3 n'ont AUCUN job du registre** : suivi de parcelle, secteur, recherche sauvegardée.
- **K = 0** : le **registre CRON-1 (jeu B) n'a JAMAIS été posé en prod** (`CRON-1-LOT0.md`, observé 18/09 —
  `/etc/cron.d/labuse` absent). ⚠️ **Nuance capitale** : les **crons LEGACY (jeu A)**, eux, tournaient —
  dont un job `0 7 * * *` qui lançait `evaluer-suivis` / `evaluer-veilles` / `digest quotidien` (dernier
  passage observé 18/09 07:00) et `radar-sources` hebdo. Donc la veille A ÉTÉ évaluée en prod par le legacy,
  **pas** par le registre neuf. Voir §7.

> **Méthode & limites.** L'inventaire (§ tableaux) est établi par lecture du code (file:line). Le **circuit
> joué** (§Circuit) l'a été **en local sur la base réelle `labuse`** (431 663 parcelles), transport
> neutralisé (`BREVO_API_KEY`/SMTP absents → `mail_configured()=False`, `brevo._api_key()=None`), via des
> comptes `[AUDIT-TEST]` purgés à la fin. **Le serveur web n'a pas pu rester debout** : son lifespan
> (`api/app.py:104`, migrations `ALTER TABLE parcels/parcel_zone_plu`) est entré en **famine de verrou**
> derrière un gros batch résiduel d'une AUTRE instance sur la base **partagée** ; j'ai donc joué le circuit
> en CLI (sessions courtes) + appels directs aux fonctions de service, et rendu les payloads/mails en
> fichiers (captures). **L'état prod du VPS n'a pas été observé** (hors périmètre, pas d'accès SSH) : le §7
> s'appuie sur `CRON-1-LOT0.md` + l'assertion du mandat.

---

## 1 · Tableau des déclencheurs

| # | Veille | Ce qui est surveillé | Moteur (file:line) | Quand (job registre · cadence) | Produit |
|---|--------|----------------------|--------------------|-------------------------------|---------|
| 1 | **Suivi de parcelle** | Mutation DVF / permis / BODACC / zonage **SUR** une parcelle suivie (`watched_parcels`) | `evaluer_suivis` `api/events.py:380` | **AUCUN job du registre.** CLI `evaluer-suivis` `cli.py:2886`. (Legacy : quotidien 07:00) | `event_log` kind `parcelle_suivie` → cloche + digest matin |
| 2 | **Secteur (zone dessinée)** | Vente DVF / permis / BODACC / **changement de zonage** dans un polygone `watch_zones` | `compute_alertes` `alertes.py:169` ; job-façade `evaluer_tous_secteurs` `alertes.py:299` | **AUCUN job du registre.** À la demande : endpoints `api/app.py:6979`, `:7026` (ouverture du panneau) ; CLI `evaluer-secteurs` `cli.py:2845` | table `alertes` (panneau) **+** `event_log` kind `veille_zone` → cloche + digest |
| 3 | **Recherche sauvegardée** | Parcelle qui **monte** en tier (bascule ▲) **et** matche les critères d'un filtre nommé (`saved_searches`) | `_veilles_match` `api/events.py:582`, via `detect_events` `api/events.py:454` | **AUCUN job du registre** ; `detect_events` n'est appelé par aucun job (`cli.py:2758`, seed démo `events.py:660`) | `event_log` kind `veille` → cloche + digest |
| 4 | **Veille Copilote « permis »** | Nouveaux permis d'une **commune** (`m10_permit_delais`) depuis le watermark | `evaluer_toutes` `copilote_v2/veilles.py:140` → `evaluer` `:111` | `ingest-sitadel` (**mensuel le 10**) `jobs_impl.py:365` + `sync-gpu` (**mensuel le 15**) `jobs_impl.py:388` | `event_log` kind `veille` → cloche + digest |
| 5 | **Veille annonces Radar** | Annonces immobilières validées **du jour** (`pige_biens`/`pige_faits`) matchant les critères d'une veille `type='radar'` | match `pige/veille.py:59` ; envoi `pige/digests.py:278` | **`radar-digests` (quotidien 18:00)** `jobs.py:369` → `jobs_impl.py:168` | **Mail Brevo** (digest tmpl 12 + alerte tmpl 13). **Pas de cloche** (sauf `systeme` en cas d'échec) |
| 6 | **Sentinelle sources amont** | Nouvelle version amont d'une source (`source_veille` : api/page/entête/témoin) | `sentinelle.passer` `sentinelle.py:281` | **`sonde-sources` (quotidien 07:00)** `jobs.py:289` + `agents-sources` (dim) | `event_log` kind `systeme` → **cloche pilote seulement** (compte_id NULL, hors marché) |

**Note transversale.** Le producteur unique de notification est `creer_notification` `api/events.py:165` : il
**refuse tout `kind` non déclaré au registre** (`notif_registry.py`, `est_declare`), déduplique par `dedup`
(fenêtre jour, ou `permanent=True` pour un fait unique) et **plafonne à 50/kind/compte/jour**
(`NOTIF_CAP_JOUR`, `events.py:162`), le débordement étant agrégé en « +N autres » (`_debordement` `:209`).

---

## 2 · Tableau des événements de la cloche

Endpoint `GET /events` → `list_events` `api/events.py:698`. Visibilité = `_visible` `:680` (`compte_id = :cid`
**OU** marché public `compte_id NULL` sur un kind de `_MARKET_KINDS`) ; lu/non-lu = `_seen` `:688` (colonne
`lu` pour le perso, table `event_seen` pour le marché). `_MARKET_KINDS = ("bascule","bodacc","match")`
`events.py:673`.

| kind (event_log) | → type registre | Affiché client ? | Texte (exemple réel) | Lien au clic | Lu/non-lu |
|------------------|-----------------|------------------|----------------------|--------------|-----------|
| `parcelle_suivie` | parcelle_suivie | **oui** (perso) | « Vente : votre parcelle CY0018 a changé de mains » ; « Nouveau permis sur votre parcelle … » ; « Changement de zonage … » | `/socle/#parcelle={idu}` | `lu` (perso) |
| `veille_zone` | veille_zone | **oui** (perso) | « Vente DVF dans « Secteur A » » ; « Permis déposé dans … » | `/socle/#surveillance=secteurs` | `lu` (perso) |
| `veille` | veille_zone | **oui** (perso) | « 🔭 Veille « … » : {idu} correspond » ; « N nouveaux permis à {commune} » | `/copilote?veille={id}` ou `/socle/#parcelle={idu}` | `lu` (perso) |
| `bascule` | parcelle_suivie | **oui** (**marché, broadcast**) | « ▲ EH0140 : Neutre → À suivre » | fiche (idu) | `event_seen` |
| `bodacc` | parcelle_suivie | **oui** (**marché, broadcast**) | « ● BODACC : procédure ouverte sur AH0065 » | fiche (idu) | `event_seen` |
| `match` | veille_zone | oui (marché) | « Correspondance de veille » | généré | `event_seen` |
| `annonce_produit` / `maintenance` | idem | **oui** (perso, saisi par le pilote) | titre libre (ex. « Maintenance prévue ») | lien saisi | `lu` |
| `systeme` / `systeme_pilote` | systeme_pilote | **NON au client** (compte_id NULL, **hors** marché) | « Source en retard : … », « Verrous cassés : … », « Endpoints métier en échec » | `/sources` ou `/admin` | pilote |
| `pige.*` (`pige.nouvelle`, `pige.depot_html`, `pige.a_qualifier`, `pige.statut_change`, `pige.baisse_prix`, `pige.digest_envoye`) | — | **NON** (journal interne Radar, écrit par `pige/tables.py::journaliser`, **hors** `creer_notification`/registre, compte_id NULL non-marché) | trace interne | — | — |

**Isolation (prouvée, §Circuit).** Un événement perso est cloisonné strict par `compte_id` ; un événement
marché (bascule/bodacc/match, `compte_id NULL`) est **broadcast en lecture** à tous les abonnés (M-T V2,
`events.py:668`). Les `systeme`/`pige.*` restent invisibles aux clients.

---

## 3 · Le circuit joué, étape par étape

**Montage** (`[AUDIT-TEST]`, purgé) : 2 comptes **actifs** A(70)/B(71) + titulaires ; A suit la parcelle
`97415000CY0018` (Saint-Paul, vente DVF 2025-12-31, 2,3 M€), B suit `97422000BN2939` ; une zone A autour de
CY0018 ; une veille Radar A « terrain · Saint-Paul » ; une annonce terrain validée **aujourd'hui** ; une
recherche sauvegardée A. Watermarks (`created_at`) reculés au 2025-01-01 pour que le DVF 2025 soit
postérieur au suivi. Transport neutralisé.

### 3.1 — Suivi de parcelle → événement → cloche → mail
1. **Déclenche** : `labuse evaluer-suivis` → `{'mutation': 2, 'permis': 1, ...}`.
2. **Événement en base** : `event_log` id 5377, compte 70, kind `parcelle_suivie`, source `Mutation`,
   titre « **Vente : votre parcelle CY0018 a changé de mains** », lien `/socle/#parcelle=97415000CY0018`,
   `lu=false`, dedup `suivi:mut:97415000CY0018:…`. (B(71) reçoit ses propres événements BN2939.)
3. **Cloche** (payload réel `list_events`, `captures/veille-audit1/cloche-payload.txt`) : l'événement
   apparaît **non-lu, en tête** pour le compte 70 ; le lien pointe la fiche.
4. **Mail (digest du matin)** : `envoyer_digests(dry_run)` → statut `simulé`, sujet « **LABUSE — 5
   changements sur vos suivis** », corps contenant « Vente : votre parcelle CY0018 … — Mutation du
   2025-12-31 — 2 300 000 € ». Rendu : `captures/veille-audit1/shot-digest-matin-compte70.png`.
5. **Idempotence** : ré-exécution de `evaluer-suivis` → `{mutation:0, permis:0, …}` ; le compte reste à 1
   événement suivi (dédup par `dedup`).

### 3.2 — Secteur (zone) → panneau + cloche (l'anti-bruit en action)
1. **Déclenche** : `labuse evaluer-secteurs` → « 3 scope(s), **491 alerte(s)**, **4 notification(s)** ».
2. **Panneau** : 491 lignes `alertes` (zone 34 : ventes DVF + permis historiques).
3. **Cloche** : **seulement 4** `event_log` kind `veille_zone` (ids 5380-5383) — car `_notifier_secteur`
   `alertes.py:143` **ne notifie QUE les faits datés après `zone.created_at`** ; les 487 autres restent au
   panneau, **jamais à la cloche ni au digest**. C'est la garde anti-rattrapage. Ré-exécution → 0 nouvelle.

### 3.3 — Veille annonces Radar → mail (broadcast + ciblé)
1. **Déclenche** : `digests.envoyer(dry_run)` (= job `radar-digests`) → `n_biens_du_jour=1`, `simules=7`.
2. **Résultat** : 1 annonce → **DIGEST (tmpl 12) à 6 comptes actifs** (19, 31, 63, 68, 70, 71) **quelle que
   soit leur veille** + **1 ALERTE (tmpl 13)** au seul compte 70 (dont la veille matche). Tous `simulé`,
   0 envoi. Carte rendue : `captures/veille-audit1/shot-radar-alerte-compte70.png` (« Terrain — Saint-Paul,
   185 000 €, 620 m², **Sous le marché −37,7 %** »).
3. **Vide quand rien / un par jour** : digest gated par `if biens:` (`digests.py:291`) ; dédup
   `pige:digest:{compte}:{jour}` / `pige:alerte:{compte}:{veille}:{jour}` vérifiés dans `event_log`
   (`_deja_envoye` `:228`) → jamais deux le même jour.

### 3.4 — Où le circuit CASSE : « mail_log »
Le mandat cite « mail dans **mail_log** ». **Il n'existe pas de table `mail_log`.** La file mail est
`mail_queue` (`mailfile.py:51`) — et **les mails de veille NE PASSENT PAS par elle** : le digest Radar
appelle `mail.envoyer_template` → Brevo **en direct** (`digests.py:248`), le digest du matin appelle
`send_email` → SMTP **en direct** (`events.py:1309`). Vérifié : `mail_queue` ne contient que des mails de
cycle de vie (onboarding/souscription), **0 ligne veille/radar/digest** (`captures/…/evidence-db.txt`).
La seule trace d'un mail de veille est : `event_log` kind `pige.digest_envoye` (Radar, **succès
seulement**, `digests.py:250`) et `notif_prefs.last_digest_at` (digest matin, succès seulement,
`events.py:1317`). **En dry-run, aucune de ces traces n'est écrite** → il n'y a **aucun registre d'envoi
neutralisé** : on ne peut pas prouver « le mail serait parti » autrement que par le rapport dry-run.

### 3.5 — Isolation (comptes 70 vs 71)
Cloche 70 = ses 4 `veille_zone` + sa mutation CY0018 ; cloche 71 = ses 2 événements BN2939 ; **A ne voit
aucun événement de B** (`SELECT … WHERE compte_id=70 AND idu='97422000BN2939'` → **0**). Digest 70 = 5
événements de 70 ; digest 71 = 2 événements de 71. Comptes **suspendus** (6, 7, 10) et **résiliés** :
**absents** des destinataires (`_clients_actifs` filtre `statut='actif'` `digests.py:275` ; idem
`envoyer_digests` `events.py:1241`).

---

## 4 · Les quatre listes

### 4.1 — Veilles sans job (ne se déclenchent jamais toutes seules)
- **Suivi de parcelle** (`evaluer_suivis`) — **aucun job du registre CRON-1**. N'existe qu'en CLI
  (`cli.py:2886`). En prod, portée uniquement par le **legacy** `0 7 * * *` (si encore posé).
- **Secteur / zone** (`evaluer_tous_secteurs`) — **aucun job**. Évalué **à la demande** quand un client
  ouvre le panneau (`app.py:6979/7026`) ou en CLI. Sans ouverture ni cron : **jamais** de cloche/digest de
  secteur en tâche de fond. (Sa propre docstring `alertes.py:300` se dit « le job CRONABLE » — **il n'est
  câblé nulle part**.)
- **Recherche sauvegardée** (`_veilles_match`/`detect_events`) — **aucun job** n'appelle `detect_events` ;
  elle ne se déclenche qu'à un **diff de run** lancé manuellement (`cli.py detect-events`).
- **Le digest du matin lui-même** (`envoyer_digests`, chaînes 1+2) — **n'est PAS dans le registre** : il
  n'existe qu'en CLI `labuse digest` (`cli.py:2933`). Le job `radar-digests` **n'envoie que le Radar**
  (`pige`), pas les notifications `event_log`. Donc, même registre entièrement posé, **les notifications
  cloche (suivi/secteur/recherche) ne seraient jamais e-mailées automatiquement**.
- (Adjacents, même trou :) `notifier-fraicheur` et `purge-notifications` (`events.py:238`/`:256`, « à
  appeler par le cron quotidien ») — **aucun job du registre** ne les appelle.

### 4.2 — Événements muets à la cloche
- `systeme` / `systeme_pilote` — **muets au client** par conception (compte_id NULL, hors marché) ; visibles
  au **pilote** seulement. Correct.
- `pige.*` (`pige.nouvelle`, `pige.depot_html`, `pige.a_qualifier`, `pige.statut_change`, `pige.baisse_prix`,
  `pige.digest_envoye`) — **muets à tous** : écrits par `pige/tables.py::journaliser` en INSERT direct,
  **hors** `creer_notification`/registre, compte_id NULL non-marché. Journal interne Radar. Ni bug ni
  fuite, mais **hors gouvernance du registre** (personne ne les « voit » ; ils gonflent seulement la table).
- **Aucun événement de test/admin n'atteint un client** : `notif-test` (`cli.py`) vise un compte précis ;
  la démo est `demo=true` (badgée) ; `systeme` est NULL non-marché. Vérifié.

### 4.3 — Risques de bruit
1. **Cloche : ~1 250 non-lues pour un compte NEUF.** Les événements **marché** `bascule`/`bodacc` sont
   broadcast à tous (`_MARKET_KINDS`). Mesuré : **1 204 `bascule` réels + 8 démo + 37 `bodacc`** en base →
   un compte `[AUDIT-TEST]` créé il y a 30 s affiche **non-lues = 1254** (`cloche-payload.txt`). Le badge de
   la cloche est donc massif dès l'inscription. (Non e-mailé — le marché sort du digest, `events.py:1282` —
   mais très bruyant à l'écran.)
2. **Digest Radar = broadcast à TOUS les actifs.** Le digest (tmpl 12) part à **chaque** compte actif dès
   qu'il y a **une** annonce du jour, **sans lien avec une veille** (`digests.py:293`). 1 annonce terrain a
   généré 6 mails digest. Le mail « ciblé » (tmpl 13) est le seul filtré par veille.
3. **Une veille de secteur large = panneau énorme.** 491 `alertes` pour une petite zone test. Le panneau
   n'est pas plafonné (la cloche, elle, l'est par l'anti-rattrapage + `NOTIF_CAP_JOUR`).
4. **`evaluer_suivis` sans watermark de run** : il re-scanne tout l'historique depuis `created_at` du suivi
   à chaque passage (pas de « depuis le dernier run ») — sûr grâce au `dedup`, mais coûteux et sensible à
   une régression du dedup.

### 4.4 — Ce qui partira au (re)déploiement du registre
Le **registre (jeu B) n'a jamais tourné en prod** (K=0). Ce qui « part » au premier `deploy.sh` :
- **Radar `radar-digests`** : le 1er passage n'envoie **que les annonces du jour** (`_biens_du_jour` borné à
  `date_premiere_saisie >= aujourd'hui`, `digests.py:81`) → **pas de rattrapage 3 semaines d'annonces**. ✓
- **`evaluer_toutes`** (via `ingest-sitadel`/`sync-gpu`, mensuels) : watermark `last_evaluated_at` ; 1re éval
  sans watermark = fenêtre **90 jours** (`veilles.py:119`), dédup par contenu → borné, sans rejeu. ✓
- **`detect_events`** (bascule/recherche) : idempotent par `(kind, idu, run_from, run_to)` ; les runs rejoués
  passés portent `envoi_statut='rattrapage'` → **exclus du digest e-mail** (`events.py:454`). ✓
- **`evaluer_suivis` / `evaluer_secteurs`** (si re-câblés) : émettront les faits **réellement nouveaux**
  depuis la pose du suivi/zone non encore notifiés. **Le garde-fou décisif est le digest** : 1 mail/jour/
  compte (`last_digest_at` + intervalle, `events.py:1270`) sur une **fenêtre J-1** (`events.py:1232`) →
  **jamais 30 mails**, au pire **un** digest de rattrapage par compte. La cloche, elle, peut afficher un pic
  de non-lues (voir risque 4.3-1).
- ⚠️ **Le vrai risque prod n'est pas le rattrapage, c'est le TROU** : si (comme l'affirme le mandat) plus
  aucun cron n'est posé depuis le 29/08, alors **depuis ~3 semaines : aucune veille évaluée, aucun digest
  parti, Radar muet**. Le premier redéploiement ne « noiera » pas les clients (garde-fous ci-dessus) mais
  **rétablira** un service actuellement à l'arrêt.

---

## 5 · La même donnée que la carte (parité veille ↔ filtre)

La **recherche sauvegardée** (#3) réévalue les mêmes prédicats que le panneau Filtre : `_veilles_match`
`api/events.py:582` appelle **`parcelles_matchant_hash`** (`api/app.py:3369`) — la **même** fonction que la
carte (`_q_v2_list` / `FiltreCriteres.where()`), sur le **même** `saved_searches.hash`, plus l'évaluation du
tier au `run_to`. Le commentaire `events.py:602` l'acte (« TOUTES les dimensions du filtre avec le MÊME
moteur que la carte », CONNEXIONS-2 Lot 5 / KO-7). Les familles de zonage (ZFANG/FRR) et les ~20 dimensions
vivent dans le hash (`_DIM_LABELS`, `app.py`), donc alignées par FILTRES-FIX-1. **Non prouvé en live** : le
déclenchement exige un diff de run (`detect_events`), non rejoué ici pour ne pas toucher le run servi ; la
parité repose sur le partage **littéral** de la fonction de matching (même code, même hash) — vérifiable par
lecture. La veille Radar (#5), elle, a son **propre** matcher léger (`pige/veille.py:59`) sur les faits
d'annonce — sans rapport avec les prédicats carte (attendu).

---

## 6 · Isolation (prouvée)

- **Par compte** : cloison stricte `compte_id` sur `event_log` (`_visible`/`_seen`), `veilles`,
  `watched_parcels`, `watch_zones`, `alertes`, `saved_searches` (clauses `compte_id IS NOT DISTINCT FROM`).
  Prouvé §3.5 : A ne voit rien de B (0 fuite), digests disjoints.
- **Marché** : `bascule`/`bodacc`/`match` (compte_id NULL) sont **volontairement** partagés en lecture — pas
  une fuite, un broadcast (mais cf. bruit 4.3-1).
- **Statut compte** : `statut='actif'` filtre les destinataires des deux digests → **suspendu/résilié ne
  reçoit plus rien** (prouvé : comptes 6/7/10 absents des envois). ⚠️ **Essai expiré** : `_clients_actifs`
  et `envoyer_digests` **ne testent PAS `essai_expire_at`** — un compte resté `statut='actif'` avec essai
  expiré recevrait encore les mails ; la coupure dépend d'une bascule de `statut` par la facturation, pas
  d'une garde à l'envoi. (Constat, non corrigé.)

---

## 7 · La prod : ce qui n'a jamais tourné, ce qui partira

Source : `CRON-1-LOT0.md` (observation VPS lecture seule 18/09) + `deploy.sh`. **Non re-observé ici** (pas
d'accès VPS).

- **Registre CRON-1 (jeu B, 23 jobs)** : **jamais posé** (`/etc/cron.d/labuse` absent). Donc **jamais tourné
  en prod** : `radar-digests`, `sonde-sources`, `ingest-sitadel`(→`evaluer_toutes`), `sync-gpu`,
  `coherence-robinets`, `filtres-sources`, `restore-test`, etc. → **K = 0**.
- **Crons LEGACY (jeu A, 13 jobs)** : **posés & actifs** (mtimes logs jusqu'au 18/09). Parmi eux, le job
  `0 7 * * *` lançait **`evaluer-suivis` / `evaluer-veilles` / `notifier-fraicheur` / `purge-notifications`
  / `digest quotidien`**, et `radar-sources` (hebdo). **Donc, tant que le legacy tourne, la veille EST
  évaluée et le digest matin EST envoyé en prod** — via le legacy, **pas** via le registre.
- **Divergence notable** : le legacy évaluait `evaluer-veilles` (Copilote permis) **quotidiennement** ; le
  registre neuf ne le câble qu'au **mensuel** (`ingest-sitadel`/`sync-gpu`). Passer legacy→registre
  **ralentit** cette veille de quotidienne à mensuelle.
- **Si le mandat dit vrai (« pas posés depuis le 29/08 »)** — c.-à-d. legacy retiré sans poser le neuf —
  alors **depuis ~3 semaines** : **aucune veille évaluée, aucun digest parti, Radar sans dépôt traité**.
  Le premier redéploiement **ne provoquera pas de tempête** (§4.4 : Radar borné au jour ; digest 1/jour/
  compte fenêtre J-1 ; `rattrapage` exclu du mail) — il **relancera** un service arrêté. Le seul débordement
  possible est **visuel** (pic de non-lues à la cloche par le broadcast marché), pas un envoi massif d'e-mails.

---

## Annexe — Preuves (`captures/veille-audit1/`)

- `shot-digest-matin-compte70.png` — digest du matin (chaînes 1+2) rendu, événement « Vente … CY0018 ».
- `shot-radar-alerte-compte70.png` — alerte Radar (tmpl 13) rendue.
- `radar-dryrun/` — HTML des 7 envois dry-run (6 digests + 1 alerte).
- `digest-matin-compte70.html`, `radar-alerte-compte70-preview.html` — sources rendues.
- `cloche-payload.txt` — payload réel `list_events` comptes 70/71 (isolation + non-lues=1254).
- `evidence-db.txt` — event_log 70/71, ventilation des 491 alertes, `mail_queue` (0 ligne veille).

**Nettoyage** : tous les objets `[AUDIT-TEST]` supprimés (comptes/utilisateurs/veilles/watched/zones/
alertes/pige/saved_searches) ; cascade des 491 alertes + snapshot zonage vérifiée à 0. Aucun run rejoué,
aucune bascule, aucune ingestion, aucun mail réel. État base identique au départ.
