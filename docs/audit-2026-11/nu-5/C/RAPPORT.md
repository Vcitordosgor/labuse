# NU5-C — La première heure, et tous les mails

**Audit LABUSE — 5 novembre 2026.** Branche `audit/nu5-c`, worktree `~/Desktop/labuse-nu5c`, Opus.
**Lecture seule, aucune correction.** Code local, Stripe en mode test, mails en **dry-run étanche**
(aucun envoi réel). Base locale `labuse`, prod **ni touchée ni sondée**.

---

## 0. Méthode & périmètre (ce qui est prouvé vs analysé)

| Volet | Comment | Fiabilité |
|---|---|---|
| **Catalogue des mails** | Les 16 templates du cycle de vie lus **en direct chez Brevo** (GET read-only `apercu_template` / `verifier_templates`) — sujet + HTML **réels**, substitution de params. Les 5 mails techniques (`emails.py`) rendus en `.eml` par la façade `mail` en **dry-run** (0 réseau). | Élevée (contenu réel) |
| **Déclencheurs** | Lecture des points d'appel (`facturation.py`, `comptes.py`, `pige/digests.py`, `api/onboarding.py`, `api/events.py`, `api/dashboard.py`). | Élevée |
| **Mails à ne pas envoyer** | Lecture des requêtes de destinataires + gardes du worker (`mailfile.py`, `digests.py`, `events.py`, `comptes.py`). | Élevée |
| **Pages légales** | Routes in-app rendues (fonctions pures, 0 base) ; pages externes `labuse.immo` **récupérées en direct** (WebFetch). | Élevée |
| **Parcours — écrans publics** | Pages server-rendered (login, invitation, CGV, reset, retour paiement) **rendues et capturées** (`captures/`). 0 base, 0 serveur. | Élevée (live) |
| **Parcours — app authentifiée** | **Analysé depuis la source** (carte, recherche, fiche, outils, PDF, Copilote, CRM). L'app n'a **pas** été bootée : son démarrage déclenche des heals/recalculs qui **écrivent** en base — incompatible avec « lecture seule ». Timing qualitatif (depuis le code), pas chronométré live. | Moyenne — **dette ouverte** (voir §9) |

**Pourquoi pas d'envoi réel ni de boot complet.** Le `.env` local porte une **clé Brevo de production**
(expéditeur `victor@labuse.immo`) et des identifiants SMTP live. Déclencher un envoi réel, même vers une
adresse de test, part depuis le compte live et touche sa réputation d'expéditeur. Le harnais implémente
l'envoi-test (option `--envoyer-test`) derrière une **double garde** (`LABUSE_MAIL_REEL=1` + adresse
explicite) mais **ne l'a pas tiré**. Le rendu read-only donne déjà le contenu réel de chaque mail.

---

## 1. Trouvailles classées

| # | Gravité | Titre | Preuve |
|---|---|---|---|
| **F1** | 🟠 MOYEN | **Deux expéditeurs** : cycle de vie = `victor@labuse.immo`, mails techniques = `contact@labuse.immo`. La doctrine « un seul expéditeur » est **fausse** en config réelle. | `verifier_templates()` → `expediteur_unique = victor@labuse.immo` ; harnais → 2 senders |
| **F2** | 🟠 MOYEN | **Mails à un compte résilié** : les requêtes de destinataires (Radar + digest) filtrent `statut='actif'` et `essai_expire_at` mais **pas `acces_fin_at`**. Un résilié en fin de période payée qui ne se reconnecte pas continue de recevoir. | `digests.py:295`, `events.py` (requête `_clients_actifs`) ; `comptes.py:529` (acces_fin_at honoré **au login seul**) ; 0 job ne balaie |
| **F3** | 🟡 MOYEN-FAIBLE | **`radar_alerte` sans lien de désinscription visible** dans le corps : le template Brevo ne référence pas `{{params.LIEN_DESABO}}` ; seul l'en-tête `List-Unsubscribe` est posé (OK Gmail/Outlook, rien de visible ailleurs). | Rendu harnais (0 lien désabo, 0 `{{ }}` résiduel) vs `digests.py:548` (commentaire qui suppose le contraire) |
| **F4** | 🟠 MOYEN | **Pas de bannière de consentement cookies.** Tiers non essentiels déclarés dans la politique (Google Fonts/Street View, Cloudflare). | Aucun composant consent dans `frontend/` ; politique `labuse.immo/confidentialite` |
| **F5** | 🟡 FAIBLE-MOYEN | **Suppression de compte : pas d'auto-service** (CLI + e-mail uniquement). | `comptes.py` `effacer_compte_rgpd`, `cli.py effacer-compte` ; 0 bouton front |
| **F6** | 🟡 FAIBLE-MOYEN | **Export de mes données non implémenté** alors que **promis en CGV art. 7**. | 0 endpoint export ; CGV art. 7 « peut en demander l'export » |
| **F7** | 🟡 FAIBLE | **Aucun e-mail d'avertissement de fin d'essai** : l'essai expire → directement l'e-mail de **suspension**, basculé **au login** (pas de cron). Le client ne reçoit aucun « votre essai se termine demain » ; et s'il ne revient pas, **aucun mail ne part**. | `comptes.py:505,524` (`basculer_essai_expire` au login) |
| **F8** | ⚪ INFO | **Pas de facture émise par LABUSE** (par conception : Stripe émet factures/reçus, CGV art. 4). Le mandat en attendait une — à clarifier. | pas de template « facture » ; `onboarding.py:4` « Facture émise automatiquement » (= Stripe) |
| **F9** | ⚪ INFO | **Template `radar_digest` (id 12) actif chez Brevo mais mort dans le code** (retiré VEILLE-FIX-1). À nettoyer. | `digests.py:5` « ancien template 12 RETIRÉ » ; Brevo `actif=True` |
| — | 🟢 FORCES | File `mail_queue` robuste ; gardes « compte supprimé → annulé » et « dû > 7 j → annulé » ; revendication `parti` anti-double-envoi ; `_adresse_placeholder` bloque les domaines de test ; `List-Unsubscribe` one-click ; **alertes `[URGENT]` à l'admin seul** (jamais un client). | §5 |

---

## 2. Parcours « première heure »

### 2.1 Écrans publics (capturés live — `captures/`)

| Étape | Écran | Verdict | Jargon / impasse |
|---|---|---|---|
| Arrivée | **`/login`** (`01_login.png`) | ✔ Clair, sobre. « LABUSE — Radar foncier · La Réunion », e-mail + mot de passe + « Se souvenir de moi sur cet ordinateur » + **Entrer** + « Mot de passe oublié ? ». Pied : disclaimer honnête (« Pré-analyse… jamais garanties ») + liens **CGV · mentions légales · confidentialité** (fonctionnels). | **Pas de page d'accueil marketing** : un prospect qui tape l'URL tombe sur une page de login fermée (« Accès réservé aux abonnés »). Inscription impossible sans invitation. |
| Lien invalide | **`/invitation`** sans token (`03_invitation_sans_token.png`) | ✔ Excellente gestion d'impasse : « Ce lien n'est plus valide — expiré, déjà utilisé, ou incomplet », bouton **Se connecter**, explication « les invitations expirent après 7 jours ». | Aucune. |
| CGV | **`/cgv`** (`04_cgv.png`) | ✔ Complète, versionnée, identité éditeur (SIRET/SIREN/adresse), 10 articles (prix 349 €/mois Intégral · 79 € Flash, résiliation, RGPD, responsabilité, droit français). | — |
| Mot de passe oublié | **`/reset`** (`05_reset_demande.png`) | ✔ Simple : champ e-mail, message neutre anti-énumération. | — |
| Confirmation paiement | `/onboarding/retour` (rendu) | ✔ « Bienvenue » / « Paiement interrompu » distincts. | — |

**Inscription (analysée source).** Pas d'auto-inscription publique : **invitation signée** envoyée par
l'exploitant → `/invitation?token=…` → choix du mot de passe (≥ 10 car., jauge) + case **CGV horodatée** →
**Stripe Checkout** (Intégral 349 €/mois) → webhook `/onboarding/paiement` active le compte. Il n'y a
**pas d'étape de vérification d'e-mail** : le **paiement fait foi**. Risque relevé : une **faute de frappe
dans l'e-mail** donne un paiement encaissé mais un accès inaccessible (le lien de connexion part à une
mauvaise adresse). `onboarding.py`.

### 2.2 App authentifiée (analysée source — à rejouer live, §9)

| Étape | Écran / fichier | Clarté | Jargon / impasse |
|---|---|---|---|
| Premier écran | Carte pleine île + rail gauche (`App.tsx`, `MapView.tsx`, `Rail.tsx`) | ⚠ **Aucun onboarding** : carte « vide » + légende « Couches » technique. Le nouveau venu ne sait pas qu'il faut **chercher** ou **filtrer**. | Pas de « commencez ici », pas de parcelle de démo proposée, pas de bouton Aide. |
| Recherche | Omnibox `Header.tsx` — placeholder « IDU · SIREN · Adresse … » | Adresse (autocomplétion BAN), IDU (14 car. → fiche directe), **nom de propriétaire/SIREN → Scan patrimoine**. Raccourci `/`. | **« IDU » jamais expliqué** (aucune infobulle). Un client ne devine pas le format. Recherche par **nom de commune retirée** (passer par le sélecteur). |
| Fiche | `fiche/Fiche.tsx` (≈ 11 sections) | Dense, complète (Identité, Terrain, Bâti, Urbanisme, Risques, Réseaux, Fiscalité, Marché, Quartier, Potentiel). | ⚠ **Surcharge** : 11 sections, aucune hiérarchie « lire d'abord ». **Sigles non définis** : SAR, PPR, DVF, PLU, BD TOPO. Pas d'« et ensuite ? ». |
| Premier outil | `outils/registry.ts`, `ModulePanel.tsx` (~15 outils) | Groupés par intention (Instruire/Agir/Marché/Temps). | ⚠ Il faut **d'abord ouvrir une fiche** ; sinon « Aucune parcelle sélectionnée ». Beaucoup d'outils en **affichage seul** (pas de prochaine action). |
| Premier PDF | `lib/ouvrirDocument.ts` → `/bilan/{idu}.pdf`, `/gabarit/{idu}.pdf` | Bouton « Étude PDF » / « Exporter », spinner ~3-5 s. | ⚠ Pas d'explication de ce que contient le PDF ; échec générique si donnée manquante. |
| Première question Copilote | `copilote/CopiloteView.tsx` | ✔ Accueil « Bonjour. Sur quoi on travaille ? » + **6 exemples concrets** (bon démarrage à froid). | ⚠ **Entrée enfouie** dans le rail (pas d'appel depuis la carte vide). **Quota quotidien** non annoncé → surprise au 429. |
| Ajout au CRM | `crm/Kanban.tsx`, `fiche/Fiche.tsx` (« → CRM ») | ✔ Bouton clair sur la fiche ; Kanban Prospection → Vente réalisée. | ⚠ Colonnes non expliquées ; **archives sans purge** (accumulation). |

**Synthèse parcours.** Les écrans **publics** sont soignés, honnêtes, sans impasse. L'**app
authentifiée** est puissante mais **froide pour un débutant** : pas de visite guidée, pas de glossaire
(IDU/PLU/PPR/SAR/DVF), pas de « prochaine étape » après la fiche/PDF/Copilote. Rien de **bloquant**, mais
la première heure repose entièrement sur la débrouillardise du client.

---

## 3. Catalogue des mails (21 mails rendus)

Rendu complet + contrôles automatiques dans **`CATALOGUE.md`** et **`checks.json`** ; sources HTML/EML
dans **`mails/`**. Déclencheurs ci-dessous.

### 3.1 Cycle de vie — templates Brevo (expéditeur **`victor@labuse.immo`**)

| Clé (id) | Sujet réel | Déclencheur |
|---|---|---|
| `essai` (4) | Vos accès d'essai LABUSE — 48 h pour juger sur pièces | Invitation essai |
| `souscription` (5) | LABUSE — votre lien d'abonnement | Envoi manuel (dashboard) |
| `onboarding1` (6) | Vos accès LABUSE | Bienvenue (compte activé) |
| `onboarding2` (7) | La méthode pour trouver ce que les autres ne voient pas | Relance **J+3** (programmé) si jamais connecté |
| `onboarding3` (8) | 10 jours de LABUSE — on fait le point ? | Relance **J+10** (programmé) |
| `relance_carte` (9) | LABUSE — un souci avec votre moyen de paiement | Webhook **`invoice.payment_failed`** + 2ᵉ relance à J+7 (lecture seule) |
| `suspension` (10) | LABUSE — votre accès est suspendu | **Essai échu** ou fin lecture-seule — bascule **au login** (`comptes.py:502,549`) |
| `retablissement` (11) | LABUSE — votre accès est rétabli | Webhook **`invoice.paid`** (compte redevient actif) |
| `radar_digest` (12) | Radar — N nouveauté(s) le … | **MORT** (retiré du code, F9) |
| `radar_alerte` (13) | Veille « … » — N correspondance(s) | Job nocturne `pige.digests.envoyer` **si** une veille matche (F3) |
| `mdp_oublie` (14) | Réinitialisation de votre mot de passe | `/reset-demande` (`onboarding.py:587`) |
| `mdp_modifie` (15) | Votre mot de passe LABUSE a été modifié | Changement de mot de passe |
| `resiliation` (16) | Votre abonnement LABUSE prend fin le … | Webhook **`customer.subscription.deleted`** (`facturation.py:590`) |
| `flash_pret` (17) | Votre rapport LABUSE — {IDU} | Flash payé → PDF généré (`facturation.py:267`) |
| `email_change` (18) | Votre adresse de connexion LABUSE a changé | Changement d'e-mail |
| `retour_traite` (19) | Votre retour a été traité | Réponse admin à un signalement (`dashboard.py`) |

Tous **actifs**, noms conformes, **0 paramètre manquant** chez Brevo (`verifier_templates` → `ok=True`).
Liens tous en `https://app.labuse.immo` ; **0 reste de test**, **0 `{{param}}` non substitué**, 0 mojibake.

### 3.2 Mails techniques — SMTP / Brevo-texte (expéditeur **`contact@labuse.immo`**)

| Clé | Sujet | Déclencheur | Désinscription |
|---|---|---|---|
| `smtp_reset_password` | LABUSE — réinitialisation de votre mot de passe | voie SMTP de secours du reset | — (transactionnel) |
| `smtp_digest_notifications` | LABUSE — N changements sur vos suivis | Digest quotidien J-1 (`events.py`) | ✔ lien + `List-Unsubscribe` |
| `smtp_annonce` | LABUSE — {titre} | Annonce produit (pilote) | ✔ lien |
| `smtp_maintenance` | LABUSE — maintenance programmée : {titre} | Maintenance (pilote) | — (non désactivable, par conception) |
| `smtp_mise_en_vente` | LABUSE — votre parcelle {X} est mise en vente | Parcelle **suivie** mise en vente (immédiat, `digests.py:416`) | ✔ lien |

**Version texte** : les mails techniques sont **multipart** (texte = repli, HTML = alternative) ✔.
Les templates Brevo : Brevo génère la part texte côté serveur (non vérifiable offline — à confirmer sur
un envoi test). **Expéditeur affiché** : `LABUSE <contact@labuse.immo>` côté app, mais `victor@labuse.immo`
côté Brevo → **F1**.

---

## 4. 2FA, facture : ce qui n'existe pas (et c'est normal / à clarifier)

- **2FA client : aucun e-mail.** Le 2FA est **TOTP applicatif réservé aux admins** (`totp_2fa`). Un
  client ne reçoit jamais de code 2FA par mail. ✔ conforme au produit.
- **Facture : aucun e-mail LABUSE (F8).** Stripe émet factures et reçus. La CGV art. 4 le dit
  (« Facture émise automatiquement »). **Reco** : confirmer que l'**envoi du reçu Stripe** est bien activé
  sur l'abonnement (Checkout `invoice_creation`/receipts) — sinon le client ne reçoit **aucune** trace
  comptable, ni de LABUSE ni de Stripe.

---

## 5. Les mails qui ne devraient pas partir

**Gardes en place (forces).** La file `mail_queue` est défensive :
- **Doublons** : fenêtre anti-doublon (dédup `compte:key:hash(params)`, 30 s par défaut, jusqu'à plusieurs
  jours pour la relance carte) ; double-clic = une seule entrée (`mailfile.enfiler`).
- **Compte supprimé** : le worker **annule** (motif lisible) toute entrée dont le `compte_id` n'existe
  plus (`consommer`, garde ORF-07).
- **Résidu de recette** : une entrée **due depuis > 7 jours** est **annulée**, jamais envoyée.
- **Double envoi** : revendication transactionnelle `parti` → deux consommateurs n'envoient jamais 2× (ORF-08).
- **Adresses placeholder** : `_adresse_placeholder` exclut `example.com`, `test.test`, `ton-email@…` au
  moment de l'envoi des digests (`events.py`).
- **`[URGENT]` / admin → jamais un client** : `ops_alertes._destinataire` = `admin_email or contact_email`
  (`victor@labuse.immo`), la notification est `compte_id=None`. **Impossible** qu'une alerte d'exploitation
  parte à un client. ✔

**Faille (F2) — mail à un compte résilié.** Les deux requêtes de destinataires…
```
WHERE c.statut = 'actif' AND (c.essai_expire_at IS NULL OR c.essai_expire_at > now())
```
…(`digests.py:295` pour le Radar, requête jumelle dans `events.py` pour le digest) **ne testent pas
`acces_fin_at`**. Or une résiliation en fin de période payée pose `acces_fin_at` (`facturation.py:590`) et
cette échéance **n'est honorée qu'au prochain login** (`comptes.py:529`, `suspendre_compte`), **aucun job
nocturne ne bascule le statut**. Conséquence : un client résilié dont la période est écoulée **mais qui ne
se reconnecte pas** reste `statut='actif'` et **continue de recevoir les alertes Radar et le digest
quotidien**. L'auteur a traité `essai_expire_at` par ce motif exact (« la coupure ne dépend plus d'une
bascule de statut ») mais **a oublié l'analogue `acces_fin_at`**. **Reco** : ajouter
`AND (c.acces_fin_at IS NULL OR c.acces_fin_at > now())` aux deux requêtes (ou un balayage nocturne qui
bascule le statut à l'échéance).

---

## 6. Pages légales & de compte — avant le premier client payant

| Exigence | État | Détail |
|---|---|---|
| **Mentions légales** | ✔ **Complètes** | `/mentions-legales` → 301 vers `labuse.immo/mentions-legales/` (live) : identité EI, SIRET/SIREN, RCS, directeur de publication, **hébergeurs Cloudflare/OVH/Stripe**. |
| **CGV** | ✔ **Complètes, in-app** | `/cgv` server-rendered, versionnées, acceptation horodatée. Prix 349 €/mois · Flash 79 €, résiliation, **293 B CGI**, responsabilité plafonnée, droit français. |
| **Confidentialité / RGPD** | ✔ **Complète** (externe) | `/confidentialite` → 301 vers `labuse.immo/confidentialite/` (live, datée 08/10/2026) : données, finalités, **sous-traitants Brevo/Anthropic/Stripe/Google/OVH/Cloudflare**, rétention (compta 10 ans), droits, CNIL. |
| **Bannière cookies / consentement** | ❌ **MANQUE (F4)** | Aucun mécanisme de consentement. Tiers non essentiels déclarés (Google Fonts/Street View, Cloudflare). **Exigé** (ePrivacy/CNIL) avant exploitation commerciale en France. |
| **Suppression de compte** | ⚠ **Partiel (F5)** | Backend `effacer_compte_rgpd` (hard delete + CASCADE, log anonymisé) + CLI ; **pas d'auto-service**. Satisfait « sur demande » (CGV : sous 30 j) mais pas de bouton. |
| **Export de mes données** | ❌ **MANQUE (F6)** | **Promis en CGV art. 7**, aucun endpoint. RGPD art. 20 (portabilité). Aujourd'hui : demande e-mail manuelle. |

**Avant le premier client payant** : (1) **bannière cookies** (le seul vrai manque réglementaire), puis
(2) **export auto-service** (déjà promis en CGV — écart contractuel) et (3) **bouton de suppression**.

---

## 7. Le harnais

**`harnais_mails.py`** (committé) — lecture seule, rejouable :
1. **Rend** les 16 templates Brevo (GET read-only, sujet + HTML réels, params d'exemple) → `mails/*.html`.
2. **Rend** les 5 mails techniques en `.eml` multipart via la façade `mail` en dry-run → `mails/*.eml`.
3. **Contrôles automatiques** par mail : expéditeur, **liens** (https + domaine `labuse.immo` + 0
   placeholder/localhost), **désinscription** (exigée sur les récurrents), **restes de test**
   (`{{param}}`, lorem, TODO, `example.com`), **français** (mojibake, tournures anglaises).
4. **Sortie** : `CATALOGUE.md` (tableau) + `checks.json` (code retour ≠ 0 si écart dur) → **exploitable en CI**.
5. **Envoi-test réel** : option `--envoyer-test ADRESSE`, derrière double garde `LABUSE_MAIL_REEL=1` +
   adresse explicite. **Non tiré** pendant l'audit (prudence réputation d'expéditeur).

```
PYTHONPATH=src <venv>/bin/python docs/audit-2026-11/nu-5/C/harnais_mails.py
```
Résultat de ce run : **21 mails rendus**, expéditeurs `{victor@labuse.immo, contact@labuse.immo}` (F1),
écarts durs = 2 (les 2 Radar sans désinscription visible, F3), écarts mous = 0.

**`render_public_pages.py`** (committé) — rend les écrans publics (0 base) → `captures/pages/*.html`,
capturés en `captures/*.png`.

---

## 8. Détail des trouvailles (constat · preuve · reco)

**F1 — Deux expéditeurs (MOYEN).** `verifier_templates()` renvoie `expediteur_unique =
victor@labuse.immo` pour les 16 templates ; `emails.py` / `config.mail_from` affichent
`LABUSE <contact@labuse.immo>` pour les mails techniques. Un client reçoit donc ses mails de cycle de vie
depuis l'adresse personnelle du fondateur et ses digests depuis `contact@`. Impacts : incohérence de
marque, **délivrabilité** (alignement SPF/DKIM/DMARC à vérifier pour les deux), et la doctrine écrite
« un seul expéditeur » est fausse. **Reco** : régler l'expéditeur Brevo sur `contact@labuse.immo` (alias
vérifié), ou assumer un expéditeur unique et corriger la doctrine.

**F2 — Mail à un compte résilié (MOYEN).** Voir §5. `digests.py:295` + jumelle `events.py` ;
`comptes.py:529` ; aucun job sur `acces_fin_at`.

**F3 — `radar_alerte` sans opt-out visible (MOYEN-FAIBLE).** Le send passe bien `LIEN_DESABO`
(`digests.py:548`) → en-tête `List-Unsubscribe` posé par `brevo.envoyer_template`. Mais le **template
Brevo ne référence pas** `{{params.LIEN_DESABO}}` dans son HTML (prouvé : le rendu substitué ne contient
aucun lien de désinscription et aucun `{{ }}` résiduel). Donc **aucun lien visible** dans le corps. Pour un
mail récurrent de prospection, la CNIL/LCEN attend un **opt-out visible et facile**. **Reco** : ajouter
`{{ params.LIEN_DESABO }}` au pied du template Brevo `radar_alerte` (et `radar_digest` s'il est ré-activé).

**F4 — Pas de bannière cookies (MOYEN).** Voir §6.
**F5 — Suppression de compte sans auto-service (FAIBLE-MOYEN).** Voir §6.
**F6 — Export de données non implémenté, promis en CGV (FAIBLE-MOYEN).** Voir §6.
**F7 — Pas d'avertissement de fin d'essai (FAIBLE).** `basculer_essai_expire` est appelé **au login**
(`comptes.py:505,524`) et envoie directement la **suspension**. Aucun « votre essai se termine demain »,
et si le client ne se reconnecte pas, **aucun mail de fin d'essai ne part** (la bascule n'a pas lieu).
**Reco** : un job nocturne « essai → J-1 » (mail d'avertissement) + bascule à l'échéance, indépendante du login.
**F8 — Pas de facture LABUSE (INFO).** Voir §4. **F9 — `radar_digest` mort mais actif chez Brevo (INFO).**
Désactiver le template 12 chez Brevo ou le retirer du registre.

---

## 9. Dettes & limites

- **Parcours authentifié non rejoué live** (carte/recherche/fiche/outils/PDF/Copilote/CRM) : analysé
  depuis la source pour respecter « lecture seule » (le boot de l'app écrit en base). **Dette** : si Vic
  autorise les écritures de session, rejouer la première heure en live (Playwright, compte de démo) pour
  **chronométrer** chaque étape et capturer les écrans authentifiés.
- **Part texte des templates Brevo** et **rendu Gmail/Apple Mail/Outlook** non vérifiés (exigeraient un
  envoi test réel) : le harnais est prêt (`--envoyer-test`) ; à tirer vers une boîte de test contrôlée
  quand l'expéditeur F1 sera tranché.
- **F1/F3** se corrigent **côté Brevo** (expéditeur + lien désabo dans le template), pas dans le code.

---

*Livrables : ce rapport · `CATALOGUE.md` + `checks.json` + `mails/` (21 rendus) · `captures/` (écrans) ·
`harnais_mails.py` + `render_public_pages.py`. Aucune écriture en prod, aucun mail réel envoyé, Stripe non
sollicité.*
