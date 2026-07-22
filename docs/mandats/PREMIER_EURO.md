# PREMIER EURO — auth réelle, Stripe, CGV, onboarding founding (rapport vivant)

**Branche `commerce/premier-euro` (8c598cc, pushée) · Vic merge.** Doctrine tenue : rien de
simulé (transport dev = contenu réel en .eml), rien en live.

## ⟪ CURSEUR ⟫ **STOP MI-COURSE — refonte pricing appliquée, tout prouvé en MODE TEST**

**Refonte commerciale (Vic 22/07) appliquée** : INTÉGRAL 349 €/mois (1 licence = 1 accès,
abonnement) · FLASH 79 €/rapport (paiement unique) · founding/sièges/Resend SUPPRIMÉS ·
aucun email automatique (liens affichés en CLI, envoyés à la main par Vic).

**Clé TEST posée** : `~/Desktop/labuse/.env`, variable `LABUSE_STRIPE_SECRET_KEY`
(préfixe LABUSE_ obligatoire — pydantic env_prefix). En prod : `/etc/labuse/labuse.env`.
Produits provisionnés en vrai (mode test) : `LABUSE_STRIPE_PRICE_INTEGRAL` /
`LABUSE_STRIPE_PRICE_FLASH` posés en .env.

**Preuves réelles (mode test)** :
- Checkout INTÉGRAL créé (session `cs_test_…` réelle, 349 €/mois) ;
- **parcours FLASH complet en HTTP** : /flash (IDU validé honnêtement) → confirmation
  (commune, m², contenu du rapport, clause boussole) → 303 Stripe (session réelle 79 €) →
  webhook signé → génération RÉELLE du PDF (weasyprint) → poll /flash/statut → lien
  token 30 j → téléchargement 200 application/pdf (157 Ko).

## Le parcours de test que VIC déroule (mi-course)

1. `stripe listen --forward-to 127.0.0.1:8023/stripe/webhook` (Stripe CLI) → remplacer
   `LABUSE_STRIPE_WEBHOOK_SECRET` dans `.env` par le `whsec_…` affiché, relancer le serveur.
2. **INTÉGRAL** : `labuse compte-invite <ton-email-de-test>` → copier le lien affiché
   (l'invitation ne part jamais seule) → mot de passe → CGV → Checkout **349 €** carte
   `4242 4242 4242 4242` → retour → login à la porte Coffre → l'app. Impayé : rejouer avec
   la carte `4000 0000 0000 0341`, constater le bandeau « paiement requis » ; suspension :
   annuler l'abonnement dans le dashboard Stripe test → session coupée ≤ 60 s.
3. **FLASH** : `/flash` → IDU (ex. 97423000AB1908) → confirmation → payer 79 € en 4242 →
   la page de retour affiche le lien → PDF téléchargé. 3DS : carte `4000 0027 6000 3184`.
Verdict écran par écran — RIEN ne part en live avant.

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
