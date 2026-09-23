# COMPTE-AUDIT-2 — comment on onboarde un client, aujourd'hui

**Contexte d'exécution.** Branche `audit/compte-audit-2` (worktree `~/Desktop/labuse-compte-audit`), venv emprunté `~/Desktop/labuse/.venv`, code servi depuis ce worktree (`PYTHONPATH=src`). API sur la **base locale réelle** (`.env` → `postgresql://openclaw@localhost/labuse`, 39 comptes / 21 utilisateurs au départ) sur le port libre **8055** ; front Vite sur **localhost:5385/socle/** (proxy → 8055) ; Playwright OK. `env=local` → auth désactivée (routes admin ouvertes sans mot de passe, normal en local). Clé **Brevo réelle** présente (`victor@labuse.immo`), Stripe **`sk_test_`** (mode test).

> **Méthode & permissions.** Lecture seule sur le code (aucun fichier `src/`, `frontend/`, migration ou test modifié). Le garde-fou auto de Claude Code a bloqué les clics/curl mutants (il lisait « Lecture seule » comme global) ; après autorisation explicite de Vic, les mutations d'audit ont été jouées via l'**endpoint admin documenté** (ce que fait le bouton), les écrans en lecture via l'UI. Chaque envoi réel a été confirmé nommément. Le clic **« Payer 349 € »** (Stripe test) n'a pas été déclenché (action financière) : le tunnel est prouvé jusqu'au handoff Stripe, Vic peut cliquer lui-même.

---

## 🔴 Bloquants (correctif en une ligne)

| # | Constat | Preuve | Correctif |
|---|---------|--------|-----------|
| 🔴 1 | **Impossible de prolonger un essai au-delà de 48 h depuis le dashboard.** Aucun champ « date de fin », aucun endpoint d'extension. La modale front code la durée **en dur `heures: 48`** ; l'`À faire` affiche « Prolonger l'essai ou convertir » mais **seul « Convertir » est câblé** (et il met `essai_expire_at = NULL`). | `frontend/…/Licences.tsx:240` (`heures: 48`), `:77` (libellé « Prolonger »), `dashboard.py:753` (seule écriture = `creer-essai`), `dashboard.py:770` (`convertir` → NULL) | Exposer un champ durée/date de fin dans la modale (le param API `heures` 1–720 existe déjà) **+** ajouter `PATCH /admin/licences/{id}/essai {essai_expire_at}`. Contournement SQL immédiat au §4. |
| 🔴 2 | **Les liens des mails partent en `http://127.0.0.1:8000`** dans cet environnement (base_url local). Les 2 vrais mails envoyés à Vic contiennent des liens localhost **non cliquables** pour un destinataire distant. En prod `LABUSE_PUBLIC_BASE_URL` corrige, mais rien ne le signale à l'écran. | `config.py:public_base_url` = `http://127.0.0.1:8000` ; aperçu Brevo « LIEN_INVITATION=http://127.0.0.1:8000/login » (capture `q2-02`) | Poser `LABUSE_PUBLIC_BASE_URL=https://app.labuse.immo` dans le `.env` servi, et afficher le base_url actif dans le bandeau Pilotage pour qu'un envoi depuis un env mal configuré se voie. |

*(Aucun 🔴 sur le cœur : le dry-run ne dit jamais « envoyé », les mails 4/5 partent réellement avec message-id, les 5 statuts et la colonne « À faire » sont fidèles.)*

**Réserves mineures (DOUTE, non bloquantes) :** la page d'invitation d'un **essai** affiche « Continuer vers le paiement · Intégral 349 €/mois », puis le POST atterrit sur « accès d'essai ouvert » **sans paiement** (libellé de bouton trompeur pour un essai) ; il n'y a **pas de bandeau d'essai permanent** dans l'app — l'échéance n'est visible que dans le menu « Mon compte » (le seul bandeau `App.tsx` est réservé à `paiement_requis`).

---

## 1 — Comment on onboarde un client depuis le dashboard

**Chemin :** Admin (Tour de contrôle) → rail **« Comptes »**. En-tête = 2 points d'entrée + segments `À toucher / Actifs / Essais / Invités / Suspendus / Tous` + recherche. *(captures `q1-01`, `q1-02`)*

| Contrôle | Verdict | Preuve |
|----------|---------|--------|
| Entrées de création présentes | OK | Boutons **« Ouvrir un essai 48 h »** et **« Créer un client »** — `Licences.tsx:362-363` ; capture `q1-01` |
| **« Créer un client »** = invitation Intégral | OK | `POST /admin/licences/creer` → `comptes.creer_invitation` (`comptes.py:253`). En base : compte `plan=integral, statut='invite', essai_expire_at=NULL, stripe=NULL` ; utilisateur `statut='invite'`, sans mot de passe, `invite_token_hash` + `invite_expire_at` (+7 j). **Aucun mail auto** (`comptes.py:256` « envoi À LA MAIN »). Vérifié : compte 75/utilisateur 74, HTTP 200, event `invitation_creee` |
| **« Ouvrir un essai 48 h »** = accès actif immédiat | OK | `POST /admin/licences/creer-essai` → `creer_invitation` **puis** `UPDATE comptes SET statut='actif', essai_expire_at=now()+48h` (`dashboard.py:733-756`). Vérifié : compte 76 `statut=actif, essai_expire_at=2026-09-25 22:30`, utilisateur 75 `statut='invite'` (n'a pas encore posé son mot de passe), HTTP 200 |
| Ce que Vic saisit | OK | Modale : **E-mail, Prénom, Nom** ; boutons « Créer et envoyer l'invitation » / « créer sans envoyer » (`Licences.tsx:255-266`) |
| Les 5 statuts réellement servis | OK | `statut5()` (`Licences.tsx:119-136`) : `invite`→**Invité** ; `invite` + `souscription`/`onboarding1` reçu →**Invitation envoyée** ; `actif`→**Actif** ; `suspendu`→**Suspendu** ; essai échu →**Expiré**. Observés en direct : **Actif** (ton-email@test.com) et **Expiré** (S. Vialard, V. Lagane) — capture `q1-02` ; segments comptés (Actifs 1 / Essais 2) — capture `q1-01`. Colonnes à part : pastille « Essai · N h » et « carte refusée » (Stripe) |
| Colonne « À faire » suit l'état | OK | `prochaineAction()` (`Licences.tsx:65-107`) dérive du statut + `licence_mails`. Observé : nouveau compte `invite` → « invitation à envoyer » ; V. Lagane → « mail de bienvenue à envoyer » ; essai expiré → « dernier rappel J+10 à envoyer » (capture `q1-02`) |
| Fiche client | OK | Vraie page à onglets (Aperçu/Activité/Facturation/IA) : identité, gestes **Renvoyer l'invitation / Transformer en client / Suspendre**, bloc **À FAIRE**, timeline **PARCOURS**, « Déconnecter partout ». Capture `q2-01` |

---

## 2 — Est-ce bien relié aux mails

**Transport unique du cycle de vie client :** bouton fiche → `POST /admin/licences/{id}/mail` → `mailfile.envoyer_mail` → table **`mail_queue`** → Brevo (`dashboard.py:911`). Trois preuves par envoi : une ligne de file (état réel), le journal qui nomme QUI (`demandeur`), l'écran qui change. `licence_mails` n'est marqué `envoye` **que si `etat='recu'`** (jamais par optimisme, `dashboard.py:913`). L'écran dit « ✓ Envoyé. » **uniquement si `r.envoye`**, sinon la raison (`Licences.tsx:341`).

**Tableau bouton → template → preuve** *(IDs du registre `brevo.REGISTRE`, `brevo.py:44-98`)* :

| Bouton fiche | Clé / Template Brevo | ID | Verdict | Preuve |
|---|---|---|---|---|
| Invitation **essai** | `essai` / LABUSE-E-ESSAI-48H | 4 | OK — **envoyé réel** | `mail_queue#8` `etat=recu`, `demandeur=vic:admin`, message-id `<202609231835.21442165962@smtp-relay.mailin.fr>` → victorlaganepro@gmail.com ; `licence_mails(63,'essai')='envoye'` ; capture `q2-03` |
| Lien **souscription** | `souscription` / LABUSE-0-SOUSCRIPTION | 5 | OK — **envoyé réel** | `mail_queue#9` `etat=recu`, message-id `<202609231835.77241514227@smtp-relay.mailin.fr>` ; `licence_mails(63,'souscription')='envoye'` ; capture `q2-03` |
| Mail de bienvenue | `onboarding1` / LABUSE-1-BIENVENUE | 6 | OK | Aperçu rendu réel (variables substituées) capture `q2-02` ; template actif |
| Relance J+3 | `onboarding2` / LABUSE-2-METHODE | 7 | OK | Timeline PARCOURS + `params_licence` `dashboard.py:873` |
| Dernier rappel J+10 | `onboarding3` / LABUSE-3-POINT-ETAPE | 8 | OK | Timeline PARCOURS `q2-01` |
| (client) Mot de passe oublié | `mdp_oublie` / LABUSE-D-MDP-OUBLIE | 14 | OK | file (voir §3, dry-run) |
| (client) Mot de passe modifié | `mdp_modifie` / LABUSE-D-MDP-MODIFIE | 15 | OK | file (voir §3, dry-run) |

| Contrôle | Verdict | Preuve |
|----------|---------|--------|
| Templates existent / actifs / bien nommés / params complets | OK | `brevo.verifier_templates()` (Brevo API, lecture) : `ok global=True`, expéditeur unique **victor@labuse.immo** ; essai/souscription/onboarding1/mdp_oublie/mdp_modifie : `existe=actif=nom_ok=True`, `params_manquants=[]` |
| Retour Brevo stocké | OK | `mail_queue.message_id` + `parti_at` posés au 2xx uniquement (`mailfile.py`) ; `etat='recu'` |
| **Dry-run** (clé retirée → l'écran ne dit pas « envoyé ») | OK | Même transport joué avec `BREVO_API_KEY=""` sur compte test 76 : retour `etat='en_attente'`, `message_id=None`, `erreur="Brevo non configuré (BREVO_API_KEY absente) — aucun envoi."` → l'écran afficherait **cette raison, jamais « ✓ Envoyé »**. La modale de création le documente aussi (`Licences.tsx:270`) |
| Bouton qui **ne passe pas** par la file | Signalé | **Tous les boutons du cycle de vie client passent par `mail_queue`** (fiche + reset client `onboarding.py:397/436`). Envois **hors file** (SMTP direct, hors périmètre onboarding) : annonces/maintenance `events.py:1407`, réponses retours `dashboard.py:162`, notif Vic courrier `courrier.py:156`, alertes jobs `jobs.py:121`/`jobs_impl.py:613` |

---

## 3 — Comment le client crée son compte

Pages du tunnel = **rendues serveur** par l'API (`onboarding.py`), pas de React (pages de confiance, CSP stricte). Liens dans les mails → base_url (cf. 🔴 2).

**Parcours ESSAI** *(compte 76, token frais)* :
1. Clic lien mail → **GET `/invitation?token=…`** → « Créer votre accès » : e-mail figé, mot de passe (≥ 10 car.), case CGV, bouton (capture `q3-01`).
2. **POST `/invitation`** (mot de passe + CGV) → `activer_par_invitation` (mdp argon2id, CGV horodatée, **token consommé**, utilisateur `actif`) → compte déjà `actif`+essai → écran **« Votre accès d'essai est ouvert »** → **/login, sans Stripe** (`onboarding.py:264-270` ; capture `q3-02`).
3. Entrée dans l'app → échéance visible.

**Parcours INTÉGRAL** *(compte 75, token frais)* :
1. GET `/invitation` (idem).
2. POST `/invitation` → compte reste `invite` → **redirect `/onboarding/paiement?t=<jeton signé>`** → page de rassurance **« Votre abonnement · 349 €/mois · Payer 349 € »** (`onboarding.py:280-300` ; capture `q3-04`).
3. POST `/onboarding/paiement` → `creer_checkout` → **Stripe Checkout `mode=subscription`** (test) → succès webhook `checkout.session.completed` → compte `actif` ; retour `/onboarding/retour` « Bienvenue ». *(clic Payer non déclenché — action financière ; handoff Stripe test vérifié par `sk_test_` + `facturation.creer_checkout`)*.

| Contrôle | Verdict | Preuve |
|----------|---------|--------|
| GET du lien **non consommant** | OK | 2 × `GET /invitation?token=…` → HTTP 200 chacun, `valider_invitation` renvoie toujours l'utilisateur après (token intact) |
| Token **réutilisé** → « lien plus valide » | OK | Après POST, re-GET même token → **HTTP 404** « **Ce lien n'est plus valide** — expiré, déjà utilisé, ou incomplet · Se connecter » (`onboarding.py:161-171` ; capture `q3-03`) |
| Essai vs Intégral (Stripe test) | OK | Essai → /login sans paiement (`q3-02`) ; Intégral → bascule paiement → Stripe `mode=subscription` (`q3-04`) ; `LABUSE_STRIPE_SECRET_KEY=sk_test_` |
| Mot de passe oublié **bout en bout (14 → 15)** | OK | Chaîne jouée (dry-run, aucun envoi réel vers @labuse.test) : `demander_reset`→ token ; **file 14** `mdp_oublie` `en_attente` ; **2 lectures non-consommantes** (token intact) ; page GET `/reset?token=` « nouveau mot de passe » (capture `q3-06`) ; `appliquer_reset`→ True (mdp changé, **sessions purgées**) ; **file 15** `mdp_modifie` ; token ensuite **consommé** (None). Pages : `q3-05` (demande), `q3-06` (nouveau mdp) |
| Première arrivée : échéance visible | OK | Session client (compte 76) → app → menu « Mon compte » : **« Plan Intégral · 349 €/mois · Essai jusqu'au 25 septembre 2026 »** (`/moi` → `essai_jusqu:"2026-09-25"` ; Header `Header.tsx:660` ; capture `q3-07`) |
| Bandeau d'essai permanent | DOUTE | Pas de bandeau plein écran ; échéance seulement dans le menu compte (le bandeau `App.tsx` ne sert que `paiement_requis`) |
| Console sans erreur (arrivée client connecté) | OK | 0 erreur / 0 warning dans la vue client connectée (les 401 `/moi/prefs-carte` et 404 vus avant venaient de la navigation d'audit non authentifiée) |

---

## 4 — Procédure : créer un compte de test pour quelqu'un (à suivre demain, sans le code)

1. **Ouvrir** la Tour de contrôle → rail **« Comptes »**.
2. **Essai** : bouton **« Ouvrir un essai 48 h »** → saisir e-mail + prénom + nom → **« Créer l'essai et envoyer l'invitation »** (ou « créer sans envoyer »). **Intégral** : bouton **« Créer un client »**, idem.
3. **Envoyer / renvoyer l'invitation** : sur la fiche, bouton **« Renvoyer l'invitation »**, ou dans le PARCOURS **« Envoyer »** en face du mail voulu (essai / souscription / bienvenue).
4. **Vérifier que c'est parti** : fiche → onglet **Activité** → « MAILS DE CE COMPTE » : la ligne doit être **« Reçu »** avec l'horodatage (état `en attente`/`échec` = pas parti — lire la raison).
5. **Prolonger l'essai au-delà de 48 h → ABSENT 🔴.** Aucun champ « date de fin » dans le dashboard. Contournement SQL (base réelle) :
   ```sql
   UPDATE comptes SET essai_expire_at = now() + interval '10 days', updated_at = now()
   WHERE id = <compte_id>;   -- allonge l'essai en place, aucune autre donnée touchée
   ```
   *(à la création, l'API accepte déjà `heures` 1–720 mais la modale est figée à 48 — non exploitable sans le code.)*
6. **Suspendre / rétablir** : fiche → **« Suspendre »** (coupe toutes les sessions, données intactes, réversible) ; **« Rétablir »** pour rouvrir. **Déconnecter partout** = ferme les sessions sans suspendre.
7. **Supprimer proprement à la fin** : effacement RGPD réel = `comptes.effacer_compte_rgpd(email)` (CLI ; supprime compte + données client par cascade, audit anonymisé). Le dashboard n'a **pas** de bouton « supprimer » (geste CLI seulement).

**Ce qui manque pour que ce soit propre :** (a) un champ durée/date-de-fin d'essai éditable (🔴 1) ; (b) un bouton « supprimer » RGPD sur la fiche (aujourd'hui CLI only) ; (c) afficher le base_url actif pour éviter d'envoyer des liens localhost (🔴 2) ; (d) aligner le libellé « Continuer vers le paiement » pour un essai.

---

## Inventaire de purge

Écritures faites par cet audit sur la base réelle :

| Objet | IDs | Nature | Purge |
|-------|-----|--------|-------|
| Comptes `[CT-TEST]` | comptes **75** (Audit Client), **76** (Audit Essai) + utilisateurs 74, 75 + 1 session (compte 76) | comptes de test | `DELETE FROM comptes WHERE id IN (75,76);` (cascade users + sessions) |
| File mail dry-run | `mail_queue` **10, 11, 12** (compte 76, `audit:dry-run`, jamais partis) | dry-run | `DELETE FROM mail_queue WHERE id IN (10,11,12);` |
| Mails **réels** à Vic | `mail_queue` **8, 9** (compte 63, `recu`) | **preuves** — à conserver | *(garder)* |
| Ledger onboarding de V. Lagane | `licence_mails(63,'essai')`, `(63,'souscription')` | trace des 2 envois réels (exacte) | *(optionnel)* `DELETE FROM licence_mails WHERE compte_id=63 AND mail_key IN ('essai','souscription');` si tu veux que sa fiche n'affiche pas ces envois |

**SQL de purge (comptes de test uniquement) :**
```sql
DELETE FROM mail_queue WHERE id IN (10,11,12);
DELETE FROM comptes    WHERE id IN (75,76);   -- cascade utilisateurs + sessions_auth
```
*(Non exécuté — laissé à Vic. Effet de bord bénin noté : l'envoi essai(4) à V. Lagane a régénéré son `invite_token` via `creer_invitation` — sans effet, son essai est expiré.)*
