# CLOISONNEMENT-1 — deux comptes, rien ne fuit

**Branche** `fix/cloisonnement-1` (base `origin/main` `4c9a094b`) · worktree `~/Desktop/labuse-cloison` · ports **8585 / 5785** · env=pilot, auth active · Brevo/SMTP en dry-run (hôte + clé vidés au lancement).

**But** — prouver, à deux comptes, que tout ce qu'un client crée ou règle reste à lui, avant d'ouvrir un accès à une testeuse externe.

## Verdict

**La cloison tient partout où le mandat l'exige.** Sur 16 cas rejoués à deux comptes (API directe + job digest, DB réelle + auth active), **aucune fuite en lecture/écriture entre comptes**. Une seule faiblesse trouvée, et elle est **à la SUPPRESSION** d'un compte, pas à l'usage courant : deux tables à `compte_id` (`mail_queue`, `contact_etiquette_log`) n'avaient **pas de FK cascade** → l'effacement RGPD les laissait orphelines. **Corrigé** (1 commit), test rouge→vert.

- Épreuve à deux comptes : `tests/test_cloisonnement_1.py` — **16 tests, tous verts**.
- Correctif : `src/labuse/comptes.py` — `effacer_compte_rgpd` efface explicitement ces 2 tables.
- Comptes d'essai `[CT-TEST-A]` / `[CT-TEST-B]` créés puis **supprimés** sur le serveur live (0 reste).

---

## Lot A — la carte

### 1. Tables à données client et colonne de rattachement

Toutes portent `compte_id` (NULL = bucket pilote/legacy hérité). Mécanique : `tenant.py` — lecture `compte_id IS NOT DISTINCT FROM :cid`, écriture pose `:cid`, FK `ON DELETE CASCADE` pour l'effacement RGPD.

| Table | Rattachement | Déclaration | Domaine | FK cascade |
|---|---|---|---|---|
| `projets` | `compte_id` | models.py | projets | ✅ (SCOPED) |
| `projet_parcelles` | via `projet_id` | models.py | parcelles de projet | ✅ via projet |
| `pipeline_entries` | `compte_id` | models.py | CRM (piste, notes, statut) | ✅ (SCOPED) |
| `contact_etiquette_log` | `compte_id` | models.py | retour terrain (CRM) | ❌ (effacé explicitement — voir Lot C) |
| `saved_searches` | `compte_id` | api/events.py | Mes vues | ✅ (SCOPED) |
| `saved_filters` | `compte_id` | models/app | filtres sauvés | ✅ (SCOPED) |
| `signalements` | `compte_id` | app.py | signalements QA | ✅ (SCOPED) |
| `courrier_demandes` | `compte_id` | courrier.py | courriers demandés | ✅ (SCOPED) |
| `event_log` | `compte_id` | api/events.py | cloche (notifications) | ✅ (SCOPED) |
| `event_seen` | `compte_id` | api/events.py | vus de marché par compte | ✅ (R9) |
| `watched_parcels` | `compte_id` | api/events.py | parcelles suivies | ✅ (SCOPED) |
| `watch_zones` | `compte_id` | alertes.py | zones de veille | ✅ (SCOPED) |
| `alertes` | `compte_id` | alertes.py | nouveautés DVF/permis | ✅ (SCOPED) |
| `veilles` | `compte_id` | pige/copilote | veilles Radar/permis | ✅ (R9) |
| `veille_reprise` | `compte_id` | api/events.py | archivage veille | ✅ (R9) |
| `copilote_conversations` | `compte_id` | copilote_v2 | questions Copilote | ✅ (R9) |
| `ia_log` / `usage_events` | `compte_id` | dashboard.py | plafond / usage IA | ✅ (R9) |
| `notif_prefs` | `compte_id` (PK) | api/events.py | **digest_freq**, réglages | ✅ (R9) |
| `notif_canaux` | `compte_id` | api/events.py | canaux cloche/mail | ✅ (R9) |
| `share_links` | `compte_id` | partners.py | liens de partage | ✅ (R9) |
| `retours`, `licence_mails`, `lettre_zonage_refs` | `compte_id` | dashboard/onboarding | feedback/onboarding | ✅ (R9) |
| `prefs_carte` | `compte_id` (PK) | comptes.py | préférences carte | ✅ (DDL propre) |
| `mail_queue` | `compte_id` | mailfile.py | file d'envoi mails | ❌ (effacé explicitement — voir Lot C) |

**Notes de conception (pas des fuites) :**
- **Notes de parcelle** = champ `notes` de `pipeline_entries` (pas de table séparée) → cloisonné avec la piste.
- **Scénario de faisabilité** = calcul **live** (`POST /scenario`), **jamais persisté** par compte → rien à fuiter (grep : aucun `INSERT`/`CREATE TABLE` faisabilité).
- **Historique « Analyser avec LABUSE »** = quota `ia_ask_quota` clé `sujet` (épinglé au compte) ; le **cache** de réponses est clé `(idu, run, question)` **global**, mais `_ask_context` ne bâtit le contexte que sur des **faits publics** (fiche premium, PLU, viabilisation, faisabilité, aménités OSM) — **aucune donnée scopée compte** n'y entre. Cache partagé = analyse publique partagée (doctrine tenant.py), pas une fuite.

### 2. Endpoints — filtrage sur le compte du jeton

La garde d'auth (`app.py` middleware ~L360-380) pose `request.state.compte_id` ; `current_compte(request)` le lit. Tous les endpoints d'objet vérifiés filtrent le compte du jeton ou refusent un id étranger :

| Objet | Endpoints | Garde compte |
|---|---|---|
| projets | `GET/POST /projets`, `GET/PATCH/DELETE /projets/{pid}`, `/{pid}/parcelles`, `/{pid}/ajouter` | `_projet_or_404(db, pid, cid)` → 404 si pas au compte |
| CRM | `GET /pipeline`, `/pipeline/parcel/{idu}`, `POST /pipeline`, `PATCH/DELETE /pipeline/{eid}` | `(e.compte_id or None) != (cid or None)` → 404 |
| colonnes CRM | `/pipeline/columns[/{id}]` | `_own_column(db, cid, id)` |
| vues / filtres | `/events/searches[/{sid}]`, `/filters[/{fid}]` | `WHERE compte_id IS NOT DISTINCT FROM :cid` |
| suivi | `GET/POST /events/watch/{idu}` | clé `(compte_id, idu)` |
| cloche | `GET /events`, `POST /events/{id}/read` | `_visible()` / `_seen()` scopés `:cid` |
| zones de veille | `GET/POST /watch-zones`, `PATCH/DELETE /watch-zones/{id}` | `update/delete_watch_zone(..., cid)` → 404 |
| veille Radar | `GET/POST /radar/veille`, `PATCH/DELETE /radar/veille/{id}` | `veille.supprimer/renommer(db, cid, id)` → `{ok:false}` |
| courrier | `POST /courrier/demande`, `GET /courrier/demandes`, `POST /courrier/demandes/{id}/statut` | `demandes_de(db, cid)` / `set_statut_demande(..., cid)` |
| Copilote | `POST /api/copilote-v2/ask`, `GET /api/copilote-v2/missions[/{conv}]` | `historique.charger/lister(db, cid, …)` → 404 |
| réglages | `GET /events/prefs`, `PATCH /events/prefs/frequence` | `get/set_digest_freq(db, cid)` |
| plafond IA | fiche_ask, copilote | `sujet_quota(request)` + `depassement_budget_eur(cid)` (par compte) |
| **admin** | `/admin/*`, `/courrier/admin/*`, `/protection/admin/*` | `exiger_admin(request)` — client=403, non connecté=401 |

### 3. Jobs qui produisent par compte

| Job | Cron (Réunion) | Destinataires | Données scopées | Verdict |
|---|---|---|---|---|
| digest e-mail | 07:15 | `SELECT c.id, titulaire.email, np.digest_freq FROM comptes … WHERE statut='actif' AND essai non expiré` | `_digest_data(db, cid)` → `WHERE e.compte_id IS NOT DISTINCT FROM :cid` | ✅ fréquence **lue par compte** |
| radar-cloche / mise en vente | 07:05 | boucle `_clients_actifs` → `veille.lister(db, cid)` | `creer_notification(compte_id=cid)` | ✅ notifie le suiveur seul |
| evaluer-suivis | 07:02 | `watched_parcels` (compte_id par ligne) | mutations/permis = faits publics, notif `compte_id=cid` | ✅ |
| detect-events | 07:04 | marché=broadcast (`compte_id NULL`) ; suivis=`w.compte_id` | ✅ | ✅ |
| mail-queue-consommer | */5 min | `mail_queue` (chaque ligne porte `compte_id`, `destinataire`) | anti-doublon `(compte, dedup, fenêtre)` | ✅ |
| mails d'essai (onboarding J+3/J+10) | registre | `licence_mails` par compte | ✅ | ✅ |

---

## Lot B — l'épreuve à deux comptes

Deux comptes actifs A et B (fixture `deux_comptes`, deux jetons). A crée une de chaque ; B teste. **Job digest** rejoué en dry-run avec un événement sur la parcelle suivie de A et un autre sur celle de B. Tout dans `tests/test_cloisonnement_1.py` (16 tests verts) + confirmé **en direct** sur le serveur 8585 (base réelle) : B ne voit rien de A, tout accès par id de A → **404 / `{ok:false}`**, objets de A intacts.

| Objet | A crée | B voit (UI¹) | B accède (API directe) | Job | Verdict |
|---|---|---|---|---|---|
| Suivi de parcelle | ✅ | ✅ vide (`watched:false`) | `GET /events/watch` = false ; pas dans la liste | digest : seul A notifié | 🟢 |
| Alerte Radar (veille) | ✅ | ✅ liste vide | `DELETE/PATCH /radar/veille/{id}` → `{ok:false}`, survit | — | 🟢 |
| Zone de veille | ✅ | ✅ liste vide | `PATCH/DELETE /watch-zones/{id}` → **404**, survit | — | 🟢 |
| Projet + 2 parcelles + note | ✅ | ✅ liste vide | `GET/PATCH/DELETE /projets/{pid}`, `/{pid}/parcelles` → **404** | — | 🟢 |
| Piste CRM + retour terrain + note | ✅ | ✅ liste vide, `parcel` = `entry:null` | `PATCH/DELETE /pipeline/{eid}` → **404** ; note « VOL » jamais écrite | — | 🟢 |
| Vue sauvegardée | ✅ | ✅ liste vide | `DELETE /events/searches/{sid}` sans effet, survit au compte A | — | 🟢 |
| Filtre sauvegardé | ✅ | ✅ liste vide | `DELETE /filters/{fid}` → **404**, survit | — | 🟢 |
| Signalement | ✅ | ✅ liste vide | listé par compte seulement | — | 🟢 |
| Demande de courrier | ✅ | ✅ liste vide | route admin statut → **403** ; route client scopée (n'atteint pas A) | — | 🟢 |
| 2 questions Copilote | ✅ | ✅ missions vides | `GET /missions/{conv}` → **404** | plafond de B intact (`ia_log` B=0) | 🟢 |
| Réglage digest « hebdo » | ✅ (A=hebdo) | B reste « quotidien » | `GET /events/prefs` par compte | digest : A traité hebdo, B quotidien | 🟢 |
| Notification cloche | ✅ | ✅ absente de `items` | `POST /events/{id}/read` de B sans effet (`event_seen` B=0) | — | 🟢 |
| **Job digest (dry-run)** | événement A + événement B | — | — | corps A = évènement A **seul**, corps B = évènement B **seul**, 0 envoi réel | 🟢 |
| Symétrie (B crée, A ne voit pas) | B projet | A liste vide | A `GET/DELETE /projets/{pid}` → **404** | — | 🟢 |
| **Admin (Vic)** voit les deux | — | dashboard `/admin/licences` = 200 | (attendu, **pas** une fuite) | — | 🟢 |

¹ **UI** : le front (5785) est un rendu direct de ces endpoints ; la colonne « B voit » reflète la réponse **réelle** de la session de B (listes vides, `watched:false`, `entry:null`). Vérifié à l'API que l'UI consomme, à deux jetons distincts, sur base réelle **et** de test. La capture pixel du SPA n'a pas été jointe : en dev, `/login` n'est pas proxifié par Vite (hack révoqué, cf. RETOURS-13) et 8585 ne sert le SPA qu'avec un build — replomber ce chemin n'ajoutait aucun signal de sécurité au-delà de la preuve API/job ci-dessus.

---

## Lot C — correction

**Une fuite, à la suppression** (pas à l'usage). `effacer_compte_rgpd` (comptes.py) fait `DELETE FROM comptes` et compte sur la **cascade FK** de `compte_id`. Deux tables à `compte_id` n'avaient **aucune FK** :

- `mail_queue` — file d'envoi : `destinataire` (e-mail) + `params` (jsonb) + `compte_id`, **sans FK** → orphelin après effacement (donnée personnelle qui survit).
- `contact_etiquette_log` — journal des retours terrain (CRM) : FK sur `parcel_id` **seulement**, rien sur `compte_id` **ni** `entry_id` → **non nettoyée**, même transitivement.

C'est la classe de bug que la revue R9 (AC-003) avait corrigée pour 11 autres tables ; ces deux-là avaient été oubliées.

**Preuve rouge→vert** — `test_suppression_compte_efface_tous_ses_objets` :
```
AVANT correctif : orphelins après effacement = {'mail_queue': 1, 'contact_etiquette_log': 1,
                                                'pipeline_entries': 0, 'projets': 0}
APRÈS correctif : 1 passed (0 orphelin)
```

**Correctif** (`src/labuse/comptes.py`, `effacer_compte_rgpd`, 1 commit) — les deux tables sont **effacées explicitement** (`DELETE … WHERE compte_id = :c`) avant le `DELETE FROM comptes`. Choix assumé plutôt qu'une FK cascade R9 : `mail_queue.compte_id` est un **tag libre** du spool (des inserts légitimes existent avec un `compte_id` sans compte réel — cf. `test_compte2_mailfile`) ; une FK stricte casserait ce contrat. La suppression explicite nettoie sans imposer de contrainte, et couvre `contact_etiquette_log` que ni `compte_id` ni `entry_id` ne rattachaient par FK.

`pytest tests/` complet : **baseline conservée** (aucune régression — voir §Vérifications).

---

## Lot D — nettoyage & suppression

- **Comportement de suppression** vérifié par test (ci-dessus) : après correctif, l'effacement d'un compte emporte **toutes** ses tables à `compte_id`, y compris `mail_queue` et `contact_etiquette_log` — 0 orphelin.
- **Comptes d'essai supprimés** sur le serveur live : `[CT-TEST-A]` (compte 87) et `[CT-TEST-B]` (compte 88), via `effacer_compte_rgpd`. État après :

```
APRÈS compte 87 : comptes=0 utilisateurs=0 restes=AUCUN
APRÈS compte 88 : comptes=0 utilisateurs=0 restes=AUCUN
utilisateurs *cloison.test restants : 0
```
Les objets de A (projet, piste CRM, suivi, vue, veille) ont cascadé à 0. Ces essais n'avaient pas de ligne `mail_queue`/`contact_etiquette_log` (créés sans envoi de mail) ; le correctif garantit le cas pour les suppressions futures.

---

## Vérifications

- `tests/test_cloisonnement_1.py` — **16 tests verts** (DB réelle labuse_test, auth active, 2 jetons).
- `pytest tests/` complet — **3451 passed, 13 failed, 69 skipped** (27 min). Les **13 échecs sont
  PRÉ-EXISTANTS** (base réelle partagée) : `verrous/test_garanties.py` (g1/g4/g6/g7 — gardes de
  registre), `verrous/test_lot1_tables.py`, `test_front_reliquats.py` (×2), `test_oracle_dossier.py`,
  `test_pige_socle.py`, `test_reparations1_lot2.py`, `test_retours17_permis.py` (×2),
  `test_veille2_lot5.py`. **Aucun n'exerce `effacer_compte_rgpd`** — la seule fonction que ce mandat
  modifie (+9 lignes). Rejoués sur ma branche, ils échouent à l'identique ; `test_veille2_lot5`
  (seul du domaine mail) utilise `supprimer_utilisateur`, que le correctif ne touche pas. Baseline
  donc **conservée** (aucune régression introduite).
- Aucun envoi réel : `LABUSE_SMTP_HOST`/`BREVO_API_KEY` vidés (mail journalisé), digest testé en `dry_run=True`.
- Serveur API 8585 (env=pilot, auth active) + front 5785 lancés une fois, puis arrêtés.

## Fichiers

- `src/labuse/comptes.py` — correctif : `effacer_compte_rgpd` efface `mail_queue` + `contact_etiquette_log`.
- `tests/test_cloisonnement_1.py` — l'épreuve à deux comptes (16 tests, dont la régression de suppression).
- `docs/audit-2026-09/CLOISONNEMENT-1/RAPPORT.md` — ce rapport.
