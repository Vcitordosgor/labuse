# RUNBOOK — recette Stripe en mode TEST (à exécuter par Vic)

La partie « app » des deux parcours est prouvée automatiquement (`tests/test_e2e_parcours.py` :
invitation→activation→webhook→actif, carte refusée→paiement_requis→reprise, résiliation→suspendu,
webhook forgé rejeté). Reste la partie qui exige un **vrai Checkout Stripe** — à dérouler avec les
**clés TEST** (jamais LIVE). Prérequis : `STRIPE_SECRET_KEY=sk_test_…`, `STRIPE_WEBHOOK_SECRET=whsec_…`
(endpoint TEST), `STRIPE_PRICE_INTEGRAL`/`STRIPE_PRICE_FLASH` posés.

## 0. Vérifier la cohérence des prix AVANT de tester
```
labuse stripe-verifie          # doit être tout vert (349 €/mois + 79 € unique)
```

## Cartes de test Stripe
| But | Numéro | Attendu |
|---|---|---|
| Paiement OK | `4242 4242 4242 4242` | paiement accepté |
| Carte refusée | `4000 0000 0000 0341` | refus (échec de prélèvement) |
| 3-D Secure | `4000 0027 6000 3184` | défi 3DS puis succès |
(date future quelconque, CVC 3 chiffres, code postal quelconque)

## (a) Parcours INTÉGRAL
1. Créer une invitation : `labuse compte-invite pe-test-integral@exemple.test` → ouvrir le lien.
2. Choisir un mot de passe (≥10), **cocher les CGV**, « Continuer vers le paiement ».
3. Checkout Stripe → carte **4242** → valider.
4. Retour app « bienvenue · Intégral actif » → `/login` → entrer avec l'e-mail + mot de passe → l'app s'ouvre.
5. **Cas refus** : recommencer avec la carte **4000…0341** → le paiement échoue, le compte n'ouvre pas ;
   Stripe relance ; une fois payé (4242), l'accès s'ouvre.
6. **Cas 3DS** : carte **4000…3184** → écran d'authentification 3DS → valider → accès ouvert.

## (b) Parcours FLASH
1. Aller sur `/flash` (public, sans compte) → saisir un IDU des 24 communes → « Voir ma parcelle ».
2. « Payer 79 € » → Checkout → carte **4242**.
3. Retour `/flash/retour` → l'écran passe de « votre rapport arrive… » au bouton **Télécharger mon
   rapport PDF** (lien 30 jours). Vérifier le téléchargement **sur iPhone/Safari** aussi.
4. **Cas refus / 3DS** : idem cartes ci-dessus.

## Purge des comptes de test (fin)
```sql
-- vérifier puis supprimer les comptes de recette
DELETE FROM utilisateurs WHERE email LIKE 'pe-test-%';
DELETE FROM comptes      WHERE nom   LIKE '[PE-TEST]%';
-- Flash : commandes de test
DELETE FROM flash_commandes WHERE email LIKE 'pe-test-%';
```
Côté Stripe TEST : les objets de test sont isolés du LIVE — rien à purger côté LIVE.

## ⚠ Rappels
- **Jamais** la clé LIVE pour un test. `stripe-verifie` se lance contre chaque mode séparément.
- Si un prix Stripe diffère de l'affiché, le Checkout **refuse** (garde `_garde_coherence_prix`) —
  corriger le `price_id` en `.env` ou re-`stripe-provisionne`, ne pas modifier un prix LIVE sans arbitrage.
