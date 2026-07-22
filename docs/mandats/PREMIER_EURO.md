# PREMIER EURO — auth réelle, Stripe, CGV, onboarding founding (rapport vivant)

**Branche `commerce/premier-euro` (8c598cc, pushée) · Vic merge.** Doctrine tenue : rien de
simulé (transport dev = contenu réel en .eml), rien en live.

## ⟪ CURSEUR ⟫ **PRÊT POUR LE STOP MI-COURSE — il manque les 2 clés Vic pour la preuve finale**

Tout ce qui se prouve SANS clé est prouvé. Le parcours complet avec carte de test 4242
attend la clé Stripe TEST ; les emails réels attendent la clé Resend.

## Prérequis Vic — la liste exacte

1. **Clé Stripe mode TEST** (`sk_test_…`) → à poser en local `.env` : `STRIPE_SECRET_KEY=…`.
   Ensuite : `labuse stripe-provisionne` (crée Indé 290 €/Pro 490 €/coupon founding −50 %
   forever, affiche les `STRIPE_PRICE_*`/`STRIPE_COUPON_FOUNDING` à poser en .env), puis
   `stripe listen --forward-to 127.0.0.1:8023/stripe/webhook` (le secret `whsec_` en .env)
   — et le parcours carte 4242/échec/3DS se déroule.
2. **Clé Resend** → `RESEND_API_KEY=…` ; je sors alors la liste exacte des 3 DNS
   (SPF/DKIM/retour) du sous-domaine `notif.labuse.immo` à poser chez Cloudflare (les MX
   existants intouchés). En attendant : chaque email part en `.eml` réel sous outputs/mails/.
3. Décisions 1-6 : appliquées telles quelles (ajustables à la review).

## E1 · Identité — PROUVÉ
Tables additives comptes/utilisateurs/sessions_auth/evenements_compte · argon2id ·
tokens hachés SHA-256 (le lien détient le seul exemplaire) · verrou 5 échecs/15 min ·
reset qui révoque les sessions · effacement RGPD réel (audit anonymisé) · sièges Pro
bornés · façade Coffre inchangée, les DEUX champs lus (pilote en compat jusqu'à la
bascule) · sessions `u.*` httpOnly+Secure+SameSite, cache 60 s (révocation ≤ 60 s,
documenté) · CLI compte-invite/admin/suspend/reactive/supprime (mdp au clavier).
Preuves : tests cycle de vie 3/3 + HTTP (303/cookie/401/compat).

## E2 · Stripe — CODE COMPLET, preuve carte en attente de clé
Provisionnement idempotent (lookup_key) · Checkout hébergé founding · webhooks SIGNÉS
obligatoires (rejet sec sinon) — cycle activation/impayé/payé/résiliation TESTÉ en signé
(signature calculée, sans compte Stripe) · emails d'impayé/suspension jamais bloquants ·
sentinelle webhook au /healthz/crons.

## E3 · CGV/pages — DRAFTS SOLIDES
/cgv (10 articles : objet, clause boussole contractualisée, comptes/sièges, prix+founding
« tant que l'abonnement reste actif », résiliation, meilleurs efforts sans SLA chiffré,
données client, RGPD, plafond 12 mois de sommes payées, droit français/Saint-Denis),
/mentions-legales (**[À COMPLÉTER : adresse EI + SIREN]**), /confidentialite (cookie unique
fonctionnel → pas de bandeau, exemption documentée), /guide.
**⚠ Relecture Vic OBLIGATOIRE + passage avocat recommandé avant premières signatures.**

## E4 · Onboarding — PROUVÉ (hors écran Stripe)
invitation (email pré-rempli, plan/prix/founding visibles) → mot de passe (≥10) → CGV
horodatées + version consignée + audit → Checkout (ou page d'attente HONNÊTE sans clé) →
/onboarding/retour → login → app (bandeau paiement_requis si impayé ; lien Guide discret
au pied du copilote). Reset : boîte → .eml → nouveau mdp → login, prouvé bout à bout.

## E5 · QA — golden 116/116 AVEC AUTH ACTIVE
Prouvé via mot de passe pilote (compat) ; la voie compte QA (`LABUSE_QA_EMAIL`) est codée
dans golden_check + smoke_prod pour la bascule. Logs sans secrets (tokens jamais en clair).

## Signalements (jamais un conseil)
- TVA auto-entrepreneur : franchise en base — seuils dépassés au MRR visé ; mention fiscale
  à poser sur les factures Stripe dès le départ (à trancher avec le comptable).
- Webhook Stripe en PROD : tant que le rideau basic auth est debout, Stripe ne peut pas
  atteindre /stripe/webhook — l'activation du webhook live se fait À LA BASCULE (prévu).
- Mentions légales : adresse officielle EI + SIREN à fournir (placeholder explicite).
