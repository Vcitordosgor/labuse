# NU4-B — Payer, renouveler, être refusé : toute la vie d'un compte

**Mandat** : jouer l'intégralité du cycle de vie d'un compte LABUSE — inscription, essai, fin
d'essai, premier paiement, renouvellement mensuel, carte refusée + 7 jours de grâce,
régularisation, résiliation, réactivation, et le rapport Flash à 79 €. À chaque étape, confronter
**quatre vues** — ce que voit le **client**, ce que dit le **mail**, ce qu'enregistre **Stripe**, ce
que montre l'**admin** — plus la **facture** (mentions, franchise de TVA, numéro, date). Chercher
tout décalage entre ces vues, tout accès qui survit à un non-paiement, toute facture fausse.

**Branche** : `audit/nu4-b` · **worktree** : `~/Desktop/labuse-nu4b` · **modèle** : Opus · **date** : 2026-11-04.
**Posture** : LECTURE SEULE du code (aucune correction), Stripe **mode TEST uniquement** (`sk_test_…`).
**Environnement** : base de dev locale `labuse` (bac à sable), API bootée en local sur `:9640`,
clés du `.env` du poste. Les comptes de test portent le préfixe `[CT-TEST]` / le domaine `@labuse.test`
(masqués des compteurs client par `comptes._MASQUE_SQL`).

**Méthode** : (1) lecture exhaustive du code de facturation/comptes/onboarding/front ; (2) **preuves
live en mode test** — factures réelles via l'API Stripe (horloges de test), cycle de vie rejoué par
webhooks **signés** sur le vrai moteur `facturation.traiter_webhook`, lecture avant/après de la table
`comptes`, et appel direct du point de contrôle d'accès `session_utilisateur`. Toutes les sorties
brutes sont dans `preuves/` (voir Annexe B). Les sondes n'écrivent jamais dans le code de l'app.

---

## 1. Résumé exécutif — trouvailles par gravité

| # | Gravité | Trouvaille | Preuve |
|---|---------|-----------|--------|
| **T1** | **🔴 CRITIQUE** | **« Régulariser » dans l'app prélève 349 € sans rétablir l'accès.** Le bouton Régulariser (bandeau / `/moi.lien_regularisation`) ouvre un **nouveau** Checkout d'abonnement. Un compte en défaut porte déjà une souscription : au webhook, la garde anti-doublon **annule la souscription neuve** (dont la 1ʳᵉ facture de 349 € vient d'être **payée**) et **garde l'ancienne, impayée**. Le compte reste `paiement_requis`/lecture seule. Argent pris, aucun service, aucun remboursement. | `regularisation.json` |
| **T2** | **🟠 MAJEUR** | **Un essai expiré qui paie est ré-suspendu dès le 1ᵉʳ accès (payé mais verrouillé).** Le webhook d'activation ne nettoie pas `essai_expire_at` ; `session_utilisateur` re-déclenche la suspension à la requête suivante et renvoie le mail « suspension ». Stripe = actif/payé, app = suspendu. | `webhooks_cycle.json` #6 + `verify_acces.json` |
| **T3** | **🟠 MAJEUR** | **La PREMIÈRE facture d'abonnement ne porte pas la mention de franchise de TVA (art. 293 B).** Le pied légal est posé sur le *client* Stripe **après** la 1ʳᵉ facture ; celle du premier euro sort `footer: null`, les renouvellements l'ont. Facture non conforme. | `factures_stripe.json` |
| **T4** | **🟠 MAJEUR** | **Ré-souscription après résiliation en fin de période : accès coupé à tort + mauvaise souscription enregistrée.** `acces_fin_at` n'est pas effacé à la réactivation (suspension future malgré un abonnement payé), et le `COALESCE` conserve l'**ancienne** souscription résiliée — la nouvelle n'est jamais enregistrée. | `webhooks_cycle.json` #7 |
| **T5** | 🟡 MOYEN | **L'admin lit Stripe en LIVE pendant que l'app facture en TEST.** `stripe_lecture.py` utilise `rk_live_…` (`.env:25`), le reste `sk_test_…` (`.env:15`). En test, l'admin ne voit **aucune** souscription de test ; MRR/CA/rapprochement orphelins = faux. (Et une clé **live** est committée en clair.) | code + `.env` |
| **T6** | 🟡 MOYEN | **Le passage en lecture seule (J+7) est silencieux.** Le mail `relance_carte` part à J0 ; la bascule en lecture seule ne déclenche **aucun** mail — le client n'est pas prévenu que son accès est réduit. | code |
| **T7** | 🟡 MOYEN | **L'accès en LECTURE au produit survit au non-paiement, potentiellement sans fin.** Après J+7, lecture seule maintenue jusqu'à un `customer.subscription.deleted` qui, selon le dunning Stripe, peut ne jamais arriver. | code |
| **T8** | 🔵 MINEUR | Hygiène de secrets : `.env` committé contient clé Stripe **live** restreinte, clés SMTP/Brevo/Anthropic/INPI en clair. | `.env` |

**Sain (contrôles vérifiés OK)** : signature des webhooks obligatoire ; idempotence (dédup par
`event_id`, rejeu ignoré) ; prix cohérents 349 €/79 € ; garde anti-divergence de prix ; aucune TVA
facturée (cohérent franchise) ; numéro + date de facture présents ; résiliation en fin de période
honore le terme déjà payé ; aucune donnée de carte ne transite par LABUSE (Checkout hébergé). Détail §4.

---

## 2. Parcours étape par étape (les quatre vues)

> Modèle commercial : **un seul** abonnement **Intégral 349 €/mois sans engagement** + un one-shot
> **Flash 79 €** (un PDF sur une parcelle). Source de prix unique : `offres.py` (`config.py:208,210`).
> États du compte (`comptes.statut`) : `invite → actif → paiement_requis → suspendu → resilie`.
> Champs horloge : `essai_expire_at`, `paiement_requis_at` (ancre de grâce), `acces_fin_at` (fin programmée).

### Étape 0 — Inscription (invitation)
- **Client** : reçoit un lien `/invitation?token=…` (envoyé **à la main** par Vic — décision produit,
  aucun mail automatique à l'invitation). Pose son mot de passe (argon2id ≥ 10 car.) + accepte les CGV
  (`cgv_version` 2026-10-09). Compte créé `invite`, utilisateur `actif`.
- **Mail** : aucun à l'étape d'invitation. L'admin peut envoyer manuellement `essai` / `onboarding1`
  (bienvenue) / `souscription` (`dashboard.py:1124`).
- **Stripe** : rien encore.
- **Admin** : le compte apparaît en segment « Invités » (`Licences.tsx`).
- `comptes.py:283` `creer_invitation`, `activer_par_invitation:346` (le compte **reste `invite`** jusqu'au paiement).

### Étape 1 — Essai (48 h, optionnel, créé par l'admin)
- **Client** : « Votre accès d'essai est ouvert — accès complet pendant l'essai » (`onboarding.py:446`).
  Menu compte : « Essai jusqu'au {date} » (`Header.tsx`). Accès complet.
- **Mail** : `essai` (template 4) — envoi manuel admin.
- **Stripe** : aucun (l'essai n'a pas de carte, pas de souscription).
- **Admin** : segment « Essais », « Essai · {h} h » (`Licences.tsx`), prolongeable/convertible.
- `dashboard.py:922` `creer-essai` (statut `actif` + `essai_expire_at = now()+48h`).

### Étape 2 — Fin d'essai
- **Client** : à l'échéance, au login ou à la requête suivante → écran « **Abonnement à régulariser** »
  + bouton « Régulariser l'abonnement » (`app.py:974`). Données conservées.
- **Mail** : `suspension` (template 10), auto (`comptes.py:456`).
- **Stripe** : aucun.
- **Admin** : « essai expiré », action « Prolonger / Convertir ».
- Bascule `basculer_essai_expire` → `suspendre_compte` (`comptes.py:449`), déclenchée paresseusement
  dans `session_utilisateur` (`comptes.py:478`). ⚠️ interagit avec **T2** ci-dessous.

### Étape 3 — Premier paiement
- **Client** : écran de bascule `/onboarding/paiement` : « Votre abonnement — 349 € / mois — Licence
  Intégral, sans engagement » → « Payer 349 € » (`onboarding.py:470-481`) → **Checkout hébergé Stripe**
  (carte jamais saisie chez LABUSE). Retour `/onboarding/retour?ok=1` : « Bienvenue chez LABUSE — votre
  abonnement Intégral est actif ».
- **Mail** : **aucun mail applicatif au paiement** (l'accueil est l'écran de retour ; un éventuel reçu
  dépend des réglages Stripe). *Observation* : pas de confirmation de paiement côté app.
- **Stripe** : `checkout.session.completed` (mode subscription) → souscription active, 1ʳᵉ facture
  **payée 349 €**. **Preuve live** : facture `X9O8EEGC-0021`, `status: paid`, `amount_paid: 34900`,
  `currency: eur`, `tax: null` (`factures_stripe.json`).
- **Admin** : passe « Payant » ; onglet Facturation montre statut + montant + lien client Stripe
  (`Licences.tsx` `FacturationTab`).
- **Webhook** (`facturation.py:437-472`) : `statut='actif'`, pose `stripe_customer_id`/`subscription_id`,
  **efface `paiement_requis_at`**, puis pose le pied de facture sur le **client**. **Preuve live** :
  `webhooks_cycle.json` #1 (`invite → actif`).
- ⚠️ **T3** (facture) : le pied légal arrivant **après** la 1ʳᵉ facture, celle-ci sort **sans mention**.

### Étape 4 — Renouvellement mensuel
- **Client** : rien à faire, prélèvement automatique.
- **Mail** : aucun côté app (reçu Stripe éventuel).
- **Stripe** : nouvelle facture mensuelle payée. **Preuve live** (horloge de test +32 j) : facture de
  cycle `X9O8EEGC-0022`, `status: paid`, **`footer` = mention 293 B présente** (`factures_stripe.json`).
- **Admin** : CA mensuel (`stripe_lecture.apercu` → héros Pilotage) — ⚠️ faussé par **T5**.
- `invoice.paid` sur un compte déjà `actif` : no-op d'état (`webhooks_cycle.json` : action `paiement_ok`).

### Étape 5 — Carte refusée
- **Client** : accès **complet** maintenu + bandeau ambre « Paiement requis — le dernier prélèvement n'a
  pas abouti. Mettez à jour votre moyen de paiement sous 7 jours ; passé ce délai, l'accès passe en
  lecture seule. » + « Régulariser » (`App.tsx` `CompteBandeau`).
- **Mail** : `relance_carte` (template 9) avec le **lien `hosted_invoice_url`** Stripe (dédup 30 j par
  facture) — `facturation.py:495-511`. ✅ bon lien (paie la facture ouverte).
- **Stripe** : `invoice.payment_failed`, souscription `past_due`, retentatives (smart retries).
- **Admin** : « carte refusée » (`Licences.tsx`), action « renvoyer le lien de paiement ».
- **Webhook** : `statut='paiement_requis'`, **ancre `paiement_requis_at = now()`** (COALESCE : repart du
  **premier** échec). **Preuve live** : `webhooks_cycle.json` #2.

### Étape 6 — Les 7 jours de grâce puis lecture seule
- **Client** : J0→J+7 accès complet (bandeau ambre) ; **à J+7** → bandeau corail « Accès en lecture
  seule — les modifications sont suspendues jusqu'au paiement » ; toute écriture → **HTTP 402**
  (`app.py:659-664`). Login et lecture restent ouverts.
- **Mail** : ⚠️ **T6** — **aucun** mail n'accompagne la bascule en lecture seule.
- **Calcul** : `session_utilisateur` (`comptes.py:496-500`) : `acces = lecture_seule` si
  `now - paiement_requis_at > 7 j` (`PAIEMENT_GRACE_JOURS = 7`).
- ⚠️ **T7** : cette lecture seule persiste tant que Stripe n'émet pas `subscription.deleted`.

### Étape 7 — Régularisation
- **Chemin mail (sain)** : clic sur le lien `relance_carte` → page Stripe `hosted_invoice_url` → paiement
  de la facture **ouverte** → `invoice.paid` → `reactiver_compte` (`statut='actif'`, `paiement_requis_at`
  effacé) + mail `retablissement` (template 11). **Preuve live** : `webhooks_cycle.json` #3.
- **Chemin in-app (CASSÉ — T1)** : clic « Régulariser » (bandeau / `/moi`) → `/onboarding/paiement` →
  `creer_checkout` → **nouvelle** souscription. **Preuve live** (`regularisation.json`) : la souscription
  neuve passe `active`, sa 1ʳᵉ facture est **payée 349 €**, puis le webhook la passe **`canceled`**
  (doublon) ; le compte **reste `paiement_requis`** et garde `sub_ANCIENNE_impayee`. ⇒ client débité,
  non régularisé, pas de remboursement.

### Étape 8 — Résiliation
- **Client** : résilie par e-mail à LABUSE (sans engagement). Deux cas :
  - **fin de période payée** (période courante future) : accès **maintenu jusqu'au terme** ; mail
    `resiliation` (template 16) avec `DATE_FIN_ACCES`. `acces_fin_at` posé, `statut` reste `actif`
    jusqu'à l'échéance. **Preuve live** : `webhooks_cycle.json` #4 (`acces_fin_at` = terme futur). ✅
  - **immédiate** : `suspendre_compte` + mail `resiliation`. **Preuve live** : #5 (`actif → suspendu`).
- **Stripe** : `customer.subscription.deleted`. **Admin** : « suspendu » puis « resilie ».

### Étape 9 — Réactivation
- **Depuis `suspendu`** (résiliation immédiate / essai expiré) : login → écran « Abonnement à
  régulariser » → Checkout → `checkout.session.completed` → `actif`.
- ⚠️ **T2** si le compte venait d'un **essai expiré** (voir §3). ⚠️ **T4** si réactivation pendant une
  période résiliée non échue (`acces_fin_at` résiduel + ancienne souscription conservée).

### Étape 10 — Flash 79 €
- **Client** : page publique `/flash` (hors authentification), accepte les CGV (case obligatoire,
  `cgv_version` horodatée) → Checkout 79 € → `/flash/retour?session_id=…` qui *poll* jusqu'au PDF, lien
  de téléchargement signé valable **30 j**, ré-ouvrable.
- **Mail** : `flash_pret` (template 17) avec lien PDF + validité (best-effort).
- **Stripe** : Checkout **mode payment**, `invoice_creation.enabled` + **pied = mention 293 B**
  (`facturation.py:189-192`). **Preuve live** : facture Flash `X9O8EEGC-0023`, 79 € (`amount_due: 7900`),
  **`footer` = mention présente**, `tax: null` (`factures_stripe.json`). ✅ facture Flash conforme (la
  mention y est, car passée dès la création — contrairement à l'abonnement, T3).
- **Admin** : mails `flash_pret` visibles dans l'onglet Facturation ; la commande vit dans
  `flash_commandes`. Filet `reconcile_flash` si le webhook est perdu (« a payé ⇒ a son rapport »).
- `charge.refunded` d'un Flash ne révoque rien (pas d'accès à révoquer) — **voulu** (`facturation.py:549`).

---

## 3. Trouvailles détaillées

### 🔴 T1 — « Régulariser » (in-app) prélève 349 € sans régulariser (double souscription)
**Chaîne** : `App.tsx CompteBandeau` → `/moi.lien_regularisation` (`onboarding.py:859-861`) →
`/onboarding/paiement` → `paiement_lancer` (`onboarding.py:484-498`) → `creer_checkout`
(`facturation.py:124-145`). `creer_checkout` crée **toujours** une Checkout `mode=subscription` **neuve** ;
il n'y a **aucune garde** contre un compte qui a déjà `stripe_subscription_id`.
Au webhook `checkout.session.completed` (`facturation.py:437-457`), la garde anti-doublon ROB-C voit
`ancien != nouveau` et exécute `Subscription.cancel(nouveau)` puis **retourne `doublon_annule`** — sans
poser `statut='actif'`. Or la 1ʳᵉ facture de la souscription neuve est **payée pendant le Checkout**.

**Preuve live** (`preuves/regularisation.json`, mode test réel) :
```
sous_neuve        : active, 1re_facture_payee_eur = 349.0
webhook_action    : doublon_annule
compte_apres      : statut = paiement_requis, stripe_subscription_id = sub_ANCIENNE_impayee
sous_neuve_apres  : canceled
```
**Conséquence** : le client qui utilise le bouton « Régulariser » de l'app est **débité de 349 €**, sa
nouvelle souscription est **immédiatement annulée**, l'ancienne reste impayée, le compte **reste en
lecture seule**. Décalage des 4 vues : Stripe (une souscription annulée + un paiement de 349 €,
+ l'ancienne `past_due`), app (`paiement_requis`), client (« j'ai payé mais c'est toujours bloqué »),
admin (« carte refusée »). Aucun remboursement automatique. Le bon chemin existe (lien `hosted_invoice_url`
du mail `relance_carte`) — mais l'app propose partout le mauvais.
*(Note : ROB-C est correct pour son but d'origine — le double-clic d'un **nouvel** invité sans
souscription : `ancien` NULL ⇒ pas d'annulation. Le défaut n'apparaît que sur la **régularisation**.)*

### 🟠 T2 — Essai expiré qui paie = ré-suspension immédiate (payé mais verrouillé)
Le webhook d'activation (`facturation.py:453-457`) met `statut='actif'` et efface `paiement_requis_at`
mais **n'efface pas `essai_expire_at`**. Or `session_utilisateur` (`comptes.py:478`) teste `_essai_echu`
= `statut actif ET essai_expire_at ≤ now` : vrai dès le 1ᵉʳ accès → `basculer_essai_expire` → `suspendu`
+ mail `suspension`.
**Preuve live** : `webhooks_cycle.json` #6 (après paiement : `statut=actif` mais `essai_expire_at` reste
au passé) puis `verify_acces.json` :
```
statut_avant = actif ; session_utilisateur → None ; statut_apres_1er_acces = suspendu
verdict : compte PAYÉ ré-suspendu dès le 1er accès
```
**Précondition** : l'essai doit s'être **éteint naturellement** (chemin self-service login→Checkout). Le
chemin admin « Convertir » (`dashboard.py:948`) efface bien `essai_expire_at` — donc ne reproduit pas le
bug. Le défaut touche le client qui paie **lui-même** après expiration. **Décalage 4 vues** : Stripe actif
+ facturé, app suspendu, mail « suspension » reçu alors qu'il vient de payer.

### 🟠 T3 — Première facture d'abonnement sans mention de franchise de TVA
Checkout `mode=subscription` ne prend pas `invoice_creation` ; le pied légal est posé **après coup** sur
le *client* via `Customer.modify(..., invoice_settings.footer=…)` dans le webhook (`facturation.py:460-471`).
Stripe finalise la 1ʳᵉ facture **pendant** le Checkout, **avant** ce `Customer.modify`. La 1ʳᵉ facture sort
donc sans la mention obligatoire « TVA non applicable, art. 293 B du CGI ».
**Preuve live** (`factures_stripe.json`) :
```
premiere_facture (X9O8EEGC-0021) : footer = null
facture cycle suivant (X9O8EEGC-0022) : footer = "TVA non applicable, art. 293 B du CGI. …"
```
**Conséquence** : la **toute première facture** de chaque abonné — la plus regardée — est **non conforme**
(mention de franchise en base manquante). Les renouvellements sont corrects. (La facture **Flash** est
conforme : la mention y est passée dès la création, T10/§4.)

### 🟠 T4 — Ré-souscription après résiliation « fin de période » : accès coupé à tort + mauvaise souscription
À la résiliation en fin de période, `acces_fin_at` est posé au terme futur et la souscription reste
enregistrée (`facturation.py:527-529`). Si le client **se ré-abonne avant le terme**, le webhook
`checkout.session.completed` met `statut='actif'` mais **n'efface pas `acces_fin_at`** et conserve
l'ancienne souscription via `stripe_subscription_id = COALESCE(ancien, nouveau)` (`facturation.py:453-455`).
**Preuve live** : `webhooks_cycle.json` #7 — après ré-souscription : `acces_fin_at` = terme futur
**conservé**, `stripe_subscription_id` = `sub_…7old` (la **nouvelle** `sub_…7new` n'est **pas** enregistrée).
**Conséquences** : (a) `session_utilisateur` (`comptes.py:483-486`) **suspendra le compte au vieux terme**
malgré un abonnement payé actif ; (b) l'app pointe une souscription **résiliée** → `stripe_lecture`/admin
et `reconcile_abonnement` raisonnent sur la mauvaise souscription. `reactiver_compte` (`comptes.py:810`)
n'efface pas non plus `acces_fin_at`.

### 🟡 T5 — Admin lit Stripe LIVE, l'app facture en TEST
`stripe_lecture.py` (Tour de contrôle admin : MRR, souscriptions, CA, rapprochement) lit
`stripe_restricted_key` = `rk_live_…` (`.env:25`) ; tout le reste (`facturation.py`) écrit avec
`sk_test_…` (`.env:15`). En mode test, **aucune** souscription/paiement de test n'apparaît à l'admin ;
le **rapprochement** (orphelins Stripe⇄comptes) signale alors tous les comptes de test comme « sans abo »
et tous les abonnés live réels comme « sans compte » → alertes fausses, MRR/CA faux. C'est aussi un
**mélange test/live** dans un même `.env`, et une **clé live committée** (hygiène, cf. T8). *En clair :
pendant cet audit, l'admin ne reflète pas les actions de test — d'où le recours à Stripe-API + DB en preuve.*

### 🟡 T6 — Bascule en lecture seule (J+7) silencieuse
`relance_carte` part à J0 ; la transition `acces=lecture_seule` est calculée paresseusement dans
`session_utilisateur` sans aucun envoi. Le client n'est averti ni que l'accès est réduit, ni du délai
restant au-delà du bandeau. Les templates `suspension`/`retablissement` existent mais ne couvrent pas ce pas.

### 🟡 T7 — L'accès en lecture au produit survit indéfiniment au non-paiement
Après J+7, le compte reste en **lecture seule** (login + consultation du radar foncier OK) jusqu'à un
`customer.subscription.deleted`. Selon le paramétrage de relance Stripe (dunning), une souscription
`past_due` peut **ne jamais être annulée** → un non-payeur consulte le produit des semaines. Point de
décision produit (volontaire côté « grâce »), mais sans borne de fin côté app.

### 🔵 T8 — Hygiène des secrets
`.env` committé dans le worktree contient : clé Stripe **restreinte LIVE** (`rk_live_…`), identifiants
SMTP Brevo, `BREVO_API_KEY`, `ANTHROPIC_API_KEY`, `INPI_API_PASSWORD` en clair. À sortir du dépôt / roter.

---

## 4. Ce qui est sain (contrôles vérifiés)
- **Signature webhook obligatoire** : `traiter_webhook` rejette un webhook non signé/mal signé
  (`facturation.py:388-390`). Les sondes signent avec le secret `whsec_…`.
- **Idempotence** : dédup par `event_id` dans la même transaction que l'effet (`facturation.py:406-412`).
  **Preuve live** : `webhooks_cycle.json` #8 — 1ᵉʳ `activation`, rejeu `rejeu_ignore`.
- **Cohérence de prix** : `verifier_prix_stripe` + garde `_garde_coherence_prix` refusent de facturer un
  montant ≠ affiché. **Preuve live** : prix Stripe test = 349 € récurrent/mois (`labuse_integral_mensuel`)
  et 79 € unique (`labuse_flash_unitaire`), conformes à `offres.py`.
- **Pas de TVA facturée** : `tax: null`, `total_tax_amounts: null` sur toutes les factures test (cohérent
  avec la franchise). **Numéro** (`X9O8EEGC-00NN`) et **date** présents (séquence + identité = réglages
  compte Stripe de Vic).
- **Carte jamais chez LABUSE** : Checkout hébergé, aucune donnée bancaire stockée.
- **Résiliation fin de période** honore le terme déjà payé (`acces_fin_at`), conforme CGV art. 5.
- **Filets « a payé ⇒ a accès »** : `reconcile_abonnement` (login) et `reconcile_flash` (poll) rattrapent
  un webhook perdu.
- **Grâce de 7 jours** calculée correctement et bornée (`PAIEMENT_GRACE_JOURS`), écritures refusées en 402.

---

## Annexe A — Récapitulatif des décalages entre vues

| Étape | Client | Mail | Stripe | Admin | Facture | Décalage |
|-------|--------|------|--------|-------|---------|----------|
| 1er paiement | « abonnement actif » | *(aucun)* | sub active, 349 € payé | « Payant » | **1ʳᵉ sans mention 293 B** | **T3** |
| Renouvellement | — | *(aucun)* | facture payée (mention OK) | CA (LIVE→faux en test) | OK | T5 |
| Grâce→J+7 | bandeau→lecture seule | `relance_carte` J0 **puis rien** | past_due | « carte refusée » | — | **T6**, T7 |
| Régularisation in-app | « toujours bloqué » | — | **sub neuve annulée + 349 € pris** | « carte refusée » | 349 € encaissés | **T1** |
| Essai expiré → paie | ré-suspendu | « suspension » (à tort) | actif/payé | varie | — | **T2** |
| Ré-abo (fin période) | coupé au vieux terme | — | nouvelle sub active | pointe l'ancienne sub | — | **T4** |

## Annexe B — Preuves (dossier `preuves/`)
- `factures_stripe.json` — factures test réelles : 1ʳᵉ abo (`footer:null`), renouvellement (mention),
  Flash (mention). Généré par `probe_factures.py` (API Stripe test + horloges de test).
- `webhooks_cycle.json` — cycle de vie complet rejoué par webhooks **signés** sur `traiter_webhook`,
  `comptes` avant/après (8 étapes). Généré par `probe_webhooks.py`.
- `verify_acces.json` — preuve de ré-suspension d'un compte payé (T2) via `session_utilisateur`.
  Généré par `verify_acces.py`.
- `regularisation.json` — preuve du double-paiement/annulation (T1) sur souscriptions test réelles.
  Généré par `probe_regularisation.py`.

**Note de méthode** : la capture d'écrans navigateur des pages gatées n'a pas été réalisée — le boot d'un
serveur local supplémentaire était bloqué par la contention de verrous DB des serveurs d'autres worktrees
tournant simultanément (heal `ACCESS EXCLUSIVE`). Les vues client sont documentées depuis les gabarits
rendus verbatim (références `fichier:ligne`) et les preuves live ci-dessus. Les comptes de test créés dans
la base de dev portent `[CT-TEST]`/`@labuse.test` (masqués des compteurs client) ; aucune écriture en prod,
aucune action Stripe en mode live.
