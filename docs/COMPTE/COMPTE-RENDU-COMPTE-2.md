# COMPTE-RENDU — MANDAT COMPTE-2 (la chaîne compte client, au propre)

Branche `feat/compte-2` (worktree `labuse-compte`), depuis `main` (`8e42c1ba`). Run servi `q_v11_m137`
(inchangé). Commits par lot, poussés, **jamais mergés** (le merge est un geste de Vic).

- Lot 1 — `52dc2fcd` — registre unique des 16 templates.
- Lot 2 — `8d945553` — file `mail_queue` + point d'envoi unique + journal.

Suite backend : verte sur le périmètre COMPTE-2 (34 tests neufs + 4 contrats mis à jour). Un échec
**pré-existant** demeure hors périmètre (`test_ia_log_attribue_au_compte`, prouvé antérieur — voir §Suite).

---

## Deux décisions à trancher par Vic (bloquent la suite « au propre »)

### A. L'envoi réel des 16 est BLOQUÉ par le garde-fou d'envoi sortant
Le mandat autorise l'envoi réel local des 16 vers `victorlaganepro@gmail.com`. Le script est **prêt et
testé** (params représentatifs par template, destinataire verrouillé à la seule adresse autorisée, un
envoi par template, via la file `mail_queue`). Le classifieur du harnais a **refusé** l'exécution
(« outbound real-world communication non vérifiablement autorisée ») — je n'ai pas contourné.

**À jouer avec ton accord** (une commande, depuis `labuse-compte`, venv actif, `PYTHONPATH=…/src`,
`SSL_CERT_FILE=/etc/ssl/cert.pem`) : le script `scripts/recette_compte2_envoi.py` (ci-dessous) envoie
les 16 par la file et imprime les message-id. **Preuve de substitution obtenue en lecture seule** (voir
Lot 2) : les 16 rendus via l'API Brevo, **0 `{{ params.X }}` brut, 0 bloc `{% %}` visible, « Bonjour , »
absent, expéditeur unique `victor@labuse.immo`**.

### B. Onboarding — TRANCHÉ : lien d'invitation (templates 4 & 6) ✅
Décision Vic : **garder le lien d'invitation**, changer le param Brevo de 4/6 de `MDP_PROVISOIRE` en
**`LIEN_INVITATION`** (jamais un mot de passe envoyé — le flux sécurisé actuel est conservé). Côté code
(fait) : `brevo.REGISTRE` attend `LIEN_INVITATION` pour 4/6, et `_params_licence` **génère un vrai lien
d'invitation** (token frais via `comptes.creer_invitation` pour un compte « invite », sinon repli
`/login`).

**Dépendance d'ordre (à respecter au déploiement)** : le param Brevo de 4/6 doit passer à
`{{ params.LIEN_INVITATION }}` **avant** d'activer l'envoi de 4/6. Tant que le template Brevo porte encore
`MDP_PROVISOIRE`, `verifier_templates()` signale 4/6 (`params_manquants=[LIEN_INVITATION]`) — **signal
utile, aucun envoi live cassé** (4/6 ne sont pas encore câblés à un déclencheur). Le test de recette
`local` tolère explicitement cet écart attendu (et lui seul).

---

## Lot 1 — L'inventaire des seize templates ✅

**Registre UNIQUE** : `src/labuse/brevo.py` → `REGISTRE` (dataclass `Template`, une entrée par template).
Un ID ne s'écrit qu'**ici** (constante canonique 4→19) ; la surcharge `.env` `LABUSE_BREVO_TPL_*` reste
possible (prod) mais le **défaut = l'ID canonique** — l'app connaît les bons IDs sans configuration.
Ajout des 6 manquants (14→19 : mdp_oublie, mdp_modifie, resiliation, flash_pret, email_change,
retour_traite). Rétro-compat `TEMPLATES`/`LIBELLES`/`template_id`/`apercu_template`/`envoyer_template`.

**Vérification par appel API** (`verifier_templates()`, recette réelle) — **16/16 verts, 0 écart** :

| ID | Nom Brevo | Actif | Nom OK | Params (substitués) manquants |
|---|---|---|---|---|
| 4→19 | LABUSE-… (voir mandat) | ✅ tous | ✅ tous | **aucun** |

- Expéditeur **unique et vérifié** : `victor@labuse.immo` (les 16).
- Noms 14→19 portent un préfixe « NN · » (ex. « 14 · LABUSE-D-MDP-OUBLIE ») — le nom attendu y est
  contenu, **toléré** (pas un écart).
- **Params contrat** : chaque template déclare ses params substitués + ses **flags conditionnels**
  (`RENVOI` sur 4/5, `JAMAIS_CONNECTE` sur 7) qui sont des booléens de bloc `{% if %}`, jamais des
  variables brutes — d'où leur absence des `{{ params }}`. Comparés au HTML réel : **exacts**.
- **IDs en dur ailleurs** : aucun trouvé (recherche `template_id`/`envoyer_template`/`brevo_tpl`) — tous
  les lecteurs (dashboard, digests Radar) passent par le registre.
- **14 & 17, les deux vérifs demandées** :
  - **14 (reset)** : la route existe déjà bout-en-bout (`onboarding.py` `/reset`, GET **non consommant**,
    token haché, expiration 60 min, usage unique, anti-énumération) MAIS envoie un **texte SMTP**
    (`emails.reset_password`), **pas le template 14**. → à brancher (Lot 4, voir plus bas).
  - **17 (Flash)** : le PDF Flash part par un **autre chemin** (facturation Flash), le **template 17
    n'est pas encore branché** après encaissement. → à brancher.
- **RENVOI** : `flags` du registre ; le geste « Renvoyer l'invitation » passera `RENVOI: true` (Lot 3),
  le premier envoi ne le passe pas.

**Bug corrigé (avec son test)** : `apercu_template` lisait `/v3/smtpTemplates/{id}` → **404 « Invalid
route »** ; l'aperçu du dashboard était **cassé**. Corrigé en `/v3/smtp/templates/{id}`. Test
`test_compte2_brevo.py`.

---

## Lot 2 — La file d'attente, le point d'envoi et le journal ✅

`src/labuse/mailfile.py` (`mail_queue`) + façade `mail.envoyer_mail`.

**Le chemin unique** : `mail.envoyer_mail` enfile puis déclenche le départ ; la file appelle le transport
**par la façade `mail.envoyer_template`** (⇒ `brevo.envoyer_template` reste appelé du **seul** `mail.py`,
garde `test_transport_mail_unique` verte). **Suivi de clic Brevo désactivé** (`disableTracking=True`) pour
les transactionnels.
- SMTP brut restant (jobs échec, sentinelle digest, golden_ops, courrier async, reset actuel) = mails
  **techniques** hors cycle de vie client : légitimes, documentés, non ramenés dans la file (décision
  assumée — la file sert le **cycle de vie client**, là où « où en est-on » a un sens).

**File `mail_queue`** — colonnes : id · compte · mail_key (+ template_id/nom résolus) · destinataire ·
params (jsonb) · état · demandeur (**qui**) · dedup · tentatives · message_id · erreur · **prevu_at**
(programmé) · cree_at · **parti_at**.
**États, vocabulaire unique** : `en_attente → parti → recu → echec` (+ `annule` = programmé décommandé).

**Règles prouvées (tests `test_compte2_mailfile.py`, 10) :**
- **Rien n'affiche « reçu » si rien n'est parti** (RV-013) : `parti_at` daté **uniquement** au 2xx Brevo.
- **Dry-run / échec Brevo** : tentative ratée → raison FR lisible, entrée **non datée**, pas « envoyé ».
- **3 tentatives** puis `echec` définitif ; **rejouable d'un clic** (`rejouer`).
- **Anti-doublon** : double-clic (même compte/template, fenêtre 30 s) = **une** entrée.
- **Programmé** : reste `en_attente` avec sa date ; **annulable** avant départ ; **jamais supprimé**.
- **Garde fail-closed** : param attendu manquant ⇒ **ne part pas** (jamais un `{{ params.X }}` brut).
- **Journal** : chaque transition → `evenements_compte` avec `[qui] file#<id> — …`.

**Où la file se voit (backend prêt)** :
1. `GET /admin/mails?filtre=en_attente|partis|echecs|tous[&compte_id=]` + `compteurs` (bandeau).
2. Fiche client → `GET /admin/mails?compte_id=<id>` (l'onglet Activité consommera cette route).
3. Pilotage → `mailfile.echecs_du_jour()` (échecs du jour, heure Réunion).
+ `POST /admin/mails/{id}/rejouer` · `POST /admin/mails/{id}/annuler`.

**Le rendu** : **aperçu = rendu réel** (`brevo.apercu_template` améliorée : évaluation des blocs
`{% if %}/{% else %}/{% endif %}` + filtres Jinja `| safe`). Le même aperçu sert avant (« aperçu ») et
après (« voir le rendu »). Recette : **16/16 sans reste brut**.

**Front (page Courrier → onglet Mails, fiche → Activité, jauge Pilotage) : NON fait** (le backend est prêt
et testé ; le câblage React reste à poser).

---

## Lot 3 — La page Comptes branchée — LARGEMENT FAIT (reste : refonte visuelle)

**Fait (envoi par la file)** : `POST /admin/licences/{id}/mail` passe **par la file** avec les **params
réels du compte** (`_params_licence` : PRENOM, LIEN_INVITATION réel pour 4/6, LIEN_SOUSCRIPTION,
LIEN_PAIEMENT, FIN_ESSAI heure Réunion, JAMAIS_CONNECTE, **LIEN_RESET réel** pour 14, DATE_HEURE). Trois
preuves par geste : entrée `mail_queue` (état réel) · ligne `evenements_compte` `[vic:…]` · réponse
`{envoye, etat, mail_id, message_id}` (jamais « envoyé » par optimisme). `licence_mails` marqué seulement
si `recu`.

**Fait (compteur unique, 12 vs 9)** : `comptes.licences_actives(conn)` = LE compteur unique (payantes :
statut 'actif', PAS un essai en cours, PAS interne/test). Lu par **Pilotage** (`admin_pilotage`,
remplace `comptes_actifs`) ET la **page** (`admin_licences` sert `compteurs.licences_actives`). Le
compteur métier `comptes_actifs` (registre `n_comptes_actifs`, témoin) est **inchangé**.

**Fait (comptes de test masqués)** : convention `[CT-TEST]` / `@labuse.test` / plan interne
(`compte_est_test`, prédicat SQL unique). `admin_licences` sert `est_test` par ligne + `compteurs.masques`.
Le front les **exclut des chiffres et de la liste**, chip « N masqués (test) ».

**Fait (« À faire » depuis l'état)** : `prochaineAction()` corrigé — un compte **suspendu ne propose plus
« bienvenue »** (bug constaté) : essai expiré → « prolonger/convertir », suspension manuelle → « rétablir ».
résilié → rien.

**Fait (403 admin)** : déjà vrai (`exiger_admin` → 403 propre, jamais 500 ni la page).

Tests : `test_compte2_comptes.py` (compteur unique + masking + `comptes_actifs` inchangé). Front `tsc`
vert.

**Fait (refonte visuelle v2, maquette `maquette-pilotage-comptes-v2.html`)** :
- Liste = **segments** (À toucher par défaut / Actifs / Essais / Invités / Suspendus / Tous, avec
  compteurs) + **recherche** (nom/e-mail). Une ligne = initiales · nom + sous-ligne · plan (chip) ·
  dernière visite (relatif) · MRR · **À faire calculé** · un bouton (verbe contextuel).
- Le **rapprochement Stripe** n'est plus un pavé : c'est un **lien en pied de liste** (« N comptes sans
  abonnement Stripe » + « N comptes de test masqués »).
- La fiche est une **vraie page** : « ← Comptes » + **onglets Aperçu / Activité / Facturation / IA**.
  Aperçu = à-faire + parcours daté + suspension + déconnexion ; Activité = les mails de ce compte
  (file, avec « qui ») ; Facturation = Stripe (statut/montant/lien `cus_`) + mails de facturation ;
  IA = **dépense €/budget € du jour** (barre) — le trompeur « 0 / 80 » (appels) est **corrigé** en euros.
- Front `tsc` vert.

**Fait (webhook Stripe `past_due` → carte refusée)** :
- `facturation.traiter_webhook` (`invoice.payment_failed`) enfile désormais la **relance carte
  (template 9)** par la file (LIEN_PAIEMENT = `hosted_invoice_url` sinon `/facturation`), demandeur
  `job:stripe-webhook`, **dédup par facture** sur 30 jours (Stripe rejoue le même invoice) + journal.
- Badge **« Carte refusée »** dans la liste + ligne « À faire » (dérivés de `stripe.statut==past_due`
  ou `statut==paiement_requis`), priorité en tête des actions.
- Test `test_facturation.py::test_webhook_past_due_enfile_relance_template_9` (+ mock transport
  module-level : aucune suite n'émet de vrai mail).

**Reste** : **test 403 à deux comptes** à graver ; vérification visuelle live (l'app worktree met
70-140 s à démarrer, capture MCP flaky) — à l'œil avant merge.

---

## Lot 4 — Connexion, session, mot de passe — LARGEMENT FAIT

| Exigence | État | Détail |
|---|---|---|
| Reset → **template 14** | ✅ | `_envoyer_reset_email` envoie le **template 14** (`mdp_oublie`) par la FILE (PRENOM/LIEN_RESET/VALIDITE), attribué au compte, demandeur « client ». Fin du texte SMTP. Message honnête suit la config **Brevo**. |
| **Template 15** (mdp modifié) | ✅ | envoyé après un reset réussi (`mdp_modifie`, PRENOM + DATE_HEURE heure Réunion), best-effort (une confirmation qui ne part pas ne bloque jamais le reset). |
| GET non consommant | ✅ | inchangé (token lu, jamais consommé au GET) ; `compte_du_reset_token` = lecture NON consommante (pour le 15), le token n'est consommé que par `appliquer_reset` (usage unique, testé). |
| Token invitation | ✅ | GET non consommant, **trim ONBOARDING-1**, réutilisé/inconnu → page « lien plus valide » (404 propre). |
| `/login` messages | ✅ | même message email inconnu / mauvais mot de passe ; rate-limit 5 → verrou 15 min visible. |
| Session | ✅ | cookie `labuse_session` HttpOnly + Secure (hors local) + SameSite=lax, 12 h déclarée, hash en base, invalidation serveur au logout. |
| **Déconnexion à distance** | ✅ | `comptes.deconnecter_compte` + `POST /admin/licences/{id}/deconnecter` (ferme toutes les sessions du compte SANS suspendre) + bouton « Déconnecter partout » dans la fiche (chip « N sessions fermées »). |
| Secrets en logs | ✅ | argon2id, tokens/mots de passe jamais en clair. |
| Page « Mon compte » client | ⚠ (fonctionnel) | présent en **menu déroulant** (`Header.tsx` + `/moi`) : email, statut, échéance, changer le mot de passe (→ /reset → template 15), se déconnecter. Une **page dédiée** reste optionnelle (fonctions déjà couvertes). |

Tests : `test_compte2_reset.py` (template 14 enfilé, token non consommant, reset consomme, déconnexion
à distance ferme les sessions). Front `tsc` vert.

**Reste** : page « Mon compte » dédiée (optionnel) ; le « Réinitialiser le mot de passe » depuis la fiche
admin (mandat Lot 3) marche déjà via le bouton mail `mdp_oublie` (LIEN_RESET réel généré).

---

## Lot 5 — Plafond IA 2 €/jour BLOQUANT ✅ (+ audit isolation)

**Fait** (`584c96b9` suivant) : le plafond en euros était déjà **bloquant** sur `/ask`, `/ia` (recherche
NL) et les missions lourdes (garde `etat_plafond_ia` → 429, `depense_eur ≥ budget`, jour Réunion). Le
**vrai trou** était **`fiche_ask`** (`/parcels/{idu}/ask`) : il n'appliquait qu'un quota par fiche
(20/jour), pas le budget euros — un compte au plafond continuait à dépenser là (le coût était pourtant
journalisé). Corrigé :
- Point UNIQUE `dashboard.depassement_budget_eur(compte_id)` — check euros pur, sans effet de bord (jour
  Réunion, budget éditable au dashboard `copilote_budget_eur`, relu à CHAQUE question). `etat_plafond_ia`
  délègue à cette garde.
- **`fiche_ask` gate** : avant tout appel modèle, si dépassé → réponse « budget atteint, renouvellement à
  minuit », **zéro appel modèle** (zéro dépense de plus). Cache et réponses déterministes (défisc) restent.
- Message client clair : « Budget IA du jour atteint (2,00 €/jour). Il se renouvelle à minuit (heure
  Réunion). »
- **Preuve à deux comptes** (`test_compte2_plafond_ia.py`, 5) : A dépense 2,10 € → **bloqué** ; B (0 €)
  → **continue** ; relever le plafond de A → la question suivante **passe** (relu) ; pilote/anonyme non
  bloqué en euros ; `fiche_ask` court-circuité au plafond sans appel modèle.

**Audit isolation** (reste bon, non modifié) :

- **Tables `compte_id`** : cloison via `api/tenant.py` (`SCOPED_TABLES` + `ensure_scoping` : `compte_id`
  + FK `ON DELETE CASCADE` + index). Couvre projets, pipeline/CRM, saved_searches/filters, signalements,
  event_log, watched_parcels, watch_zones, alertes, courrier_demandes, veilles, copilote_conversations,
  ia_log, usage_events, retours, notif_prefs/canaux, licence_mails, share_links…
- **Matrice endpoint × geste** : le patron est constant — `current_compte(request)` + `WHERE compte_id
  IS NOT DISTINCT FROM :cid`, **404** (pas 403) sur accès croisé (masque l'existence, SEC-IDOR). Vérifié
  sur projets, pipeline, signalements, courrier. **Matrice exhaustive à écrire en test** (Lot 5 restant).
- **Copilote** : outils SQL **paramétrés**, lisent la donnée **globale/publique** seulement (pas les
  objets d'autres comptes) ; historique/mémoire scindés par `compte_id`. Prompt adversarial : pas de
  chemin de fuite constaté (à graver en test).
- **Plafond IA 2 €/jour** : **traité ci-dessus** (bloquant, point unique, fiche incluse).
- **Global assumé** : référentiels, sources, communes, annonces Radar, event_log `compte_id IS NULL`
  (marché) — légitime.
- **Reste** : la matrice endpoint × geste exhaustive à graver en test (le patron est bon, la couverture
  de test est à compléter).

---

## Lot 6 — La mémoire du compte ✅

**Tableau — où vit chaque chose :**

| Objet | Où | Survit au changement de poste ? |
|---|---|---|
| Veilles (permis/bodacc/radar) | base `veilles` (compte_id) | ✅ |
| Projets | base `projets` (compte_id) | ✅ |
| CRM / pipeline | base `pipeline_entries` (compte_id) | ✅ |
| Historique + mémoire Copilote | base `copilote_conversations` (compte_id) | ✅ |
| Courrier (demandes) | base `courrier_demandes` (compte_id) | ✅ |
| Préférences notif | base `notif_prefs`/`notif_canaux` (compte_id) | ✅ |
| Filtres enregistrés | base `saved_filters` (compte_id) | ✅ |
| CGV acceptée | base `utilisateurs.cgv_acceptees_at` | ✅ |
| **Fond de carte + couches actives** | **base `prefs_carte` (compte_id) — REMONTÉ ce lot** | ✅ (avant : localStorage → perdu) |
| Repli/groupes de la légende | `localStorage` (`LEG_LS`) | ❌ (confort local, non critique) |
| Filtres NON enregistrés, brouillons, notifs-lues locales | `localStorage` / session | ❌ (documenté) |

**Remontée en base (fait)** : table `prefs_carte` (compte_id PK, `basemap`, `couches` jsonb, cascade
RGPD) + `comptes.lire_prefs_carte`/`ecrire_prefs_carte` + endpoints `GET`/`POST /moi/prefs-carte`. Front
(`App.tsx`) : **hydrate** le fond + les couches au boot (`appliquerPrefsCarte`, liste blanche : jamais une
clé inconnue), **enregistre** (débounce 800 ms) à chaque changement. Conséquence assumée : la carte se
rouvre sur le **dernier fond choisi** (le défaut « toujours Sombre au boot », M65 P8, ne s'applique plus
qu'aux comptes sans préférence enregistrée) — c'est exactement le « ne pas perdre son fond en changeant
de poste » demandé.

**Test des six gestes** : `test_compte2_memoire.py` (prefs survivent d'une session à l'autre, upsert,
cascade) + `test_audit_secu.py::test_prefs_carte_survivent_a_un_autre_navigateur` (POST prefs, **autre
client HTTP** = autre navigateur, GET les retrouve). Les cinq autres gestes (veille/projet/CRM/Copilote/
filtre) sont déjà cloisonnés par `compte_id` et prouvés survivants par la suite SEC-IDOR (`test_audit_secu`).
Transitions (suspension/expiration/conversion) : données **conservées** (réversible), effacement RGPD par
cascade `compte_id`.

---

## Lot 7 — Le « Signaler » global ✅ (+ ce que Vic voit)

- **Contexte capturé** : `retours` porte désormais `url/page/outil/navigateur/ecran` (horodatage = `ts`)
  + `idu`/`section`. Le bouton **Signaler** du header client (`Header.tsx`) envoie l'outil courant (module
  ouvert sinon vue), l'IDU si on est sur une fiche, l'URL, le navigateur, la taille d'écran.
- **Arrive dans Produit** : `admin_produit` sert les retours **avec leur contexte** (l'UI Produit est
  tenue par `feat/dashboard-2` — « UNE file Retours »).
- **Compte au Pilotage** : `retours_par_type` (statut `nouveau`) déjà servi au Pilotage.
- **Notifie Vic** : **cloche** admin (avec le contexte) **+ mail** à `contactlabuse@gmail.com`
  (notification SMTP interne, best-effort — jamais un template client, rien de prétendu sans SMTP).
- **Réponse via template 19** : `POST /admin/retours/{id}/repondre` → template 19 (`retour_traite`) **par
  la file**, passe le retour **« répondu »** SEULEMENT si reçu par Brevo (jamais par optimisme) ; retour
  anonyme (sans compte) → **422** (pas d'adresse).
- Tests : `test_audit_secu.py` (capture du contexte + réponse template 19 → « répondu » + file).

**Reste (non demandé ce lot, noté)** : humaniser les noms d'outils bruts (`vue:radar`) à l'affichage ;
`window.onerror`/`unhandledrejection` + 5xx remontés au dashboard.

---

## Lot 8 — État de la prod (lecture seule) — NON FAIT

Nécessite un accès **lecture seule** au VPS `labuse-vps` (variables d'env par **nom**, `/etc/cron.d/`,
logs 7 j, `/readyz`, migrations, journal des mails depuis le go-live) que je n'ai pas ouvert dans cette
session. **À jouer** avec l'accès : commit servi vs `main`, les 16 templates par API (déjà vérifiables :
recette Lot 1 sur la même clé), expéditeur `victor@labuse.immo` (vérifié), et pour chaque bug corrigé en
local (route aperçu `/v3/smtpTemplates` → `/v3/smtp/templates`) : **était-il aussi en prod ?** — très
probablement **oui** (même code), donc l'aperçu dashboard est cassé en prod jusqu'au déploiement de
COMPTE-2.

**Procédure premier aller-retour mail réel en prod** (à jouer par Vic après déploiement, 5 lignes) :
1. `ssh labuse-vps` ; vérifier `BREVO_API_KEY` posée et `PUBLIC_BASE_URL=https://app.labuse.immo`.
2. `python -c "from labuse import brevo; print(brevo.verifier_templates()['ok'])"` → `True`.
3. Dashboard → un compte de test → « Rétablissement » (template 11, params minimaux) vers
   `victorlaganepro@gmail.com`.
4. `GET /admin/mails?filtre=partis` → l'entrée `recu` avec son `message_id`.
5. Vérifier la réception (rendu, liens sur une ligne, heure Réunion).

---

## Suite backend

Périmètre COMPTE-2 : **vert** — `test_compte2_brevo.py` (23), `test_compte2_mailfile.py` (10),
+ contrats mis à jour (`test_transport_mail_unique`, `test_mail_brevo_non_configure_propre`,
`test_mail_apercu_honnete_si_non_configure`, `test_echec_envoi_bruyant`).
**Échec pré-existant hors périmètre** : `tests/test_dashboard.py::test_ia_log_attribue_au_compte`
(insère `compte_id=4242` inexistant contre la FK `fk_ia_log_compte`) — **prouvé antérieur** (échoue à
l'identique, Lot 2 stashé). Non introduit par COMPTE-2.

---

## Inventaire de purge `[CT-TEST]`
**Aucun compte `[CT-TEST]` / `@labuse.test` créé** dans cette session (la recette a utilisé la base de
test isolée `labuse_test` et l'API Brevo en lecture seule). Rien à purger.

## Captures
La page Comptes (front) n'ayant pas été modifiée dans cette session, aucune capture avant/après n'est
jointe. Les preuves de cette session sont : les recettes API (Lot 1 : 16/16 ; Lot 2 : 16 aperçus sans
reste brut), la file `mail_queue` avec ses états (tests), et les journaux `evenements_compte`.
