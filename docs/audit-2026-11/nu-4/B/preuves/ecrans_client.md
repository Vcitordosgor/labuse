# Captures — texte client verbatim par état (rendu depuis les gabarits, `fichier:ligne`)

> Capture d'écran navigateur non réalisée (boot serveur local bloqué par la contention de verrous DB
> des autres worktrees actifs). Texte rendu **verbatim** depuis le code de rendu.

### Écran de bascule paiement — `onboarding.py:470-481`
```
Votre abonnement
dernière étape avant votre espace
349 € / mois
Licence Intégral — accès complet. Sans engagement, facturé au mois.
🔒 Paiement sécurisé par Stripe — page hébergée, chiffrée.
🛡 Aucune donnée bancaire ne transite par LABUSE.
⏱ 349 €/mois, sans engagement — reconduit au mois, résiliable à tout moment. Facture émise automatiquement.
[ 🔒 Payer 349 € ]
Vous serez redirigé vers Stripe. Rien n'est débité tant que vous n'avez pas confirmé.
```

### Retour paiement réussi — `onboarding.py:511-518`
```
✓ Bienvenue chez LABUSE
votre abonnement Intégral est actif
Vous avez accès à tout le radar foncier de La Réunion […]
[ Entrer dans LABUSE → ]  Connectez-vous avec votre e-mail et le mot de passe […]
```

### Retour paiement interrompu — `onboarding.py:522-528`
```
↺ Paiement interrompu — rien n'a été débité
Votre compte existe déjà. Connectez-vous et le paiement reprendra là où vous l'aviez laissé.
[ Reprendre le paiement → ]
Un doute avant de payer ? Écrivez à victor@labuse.immo — je peux vous ouvrir un accès d'essai de 48 h.
```

### Accès d'essai ouvert — `onboarding.py:446-451`
```
✓ Votre accès d'essai est ouvert — accès complet pendant l'essai
À l'échéance, l'accès se met en pause — vos données restent intactes — et un abonnement vous est proposé.
```

### Essai expiré / compte suspendu (écran post-login) — `app.py:974-980`
```
Abonnement à régulariser
Votre accès LABUSE est suspendu. Vos données sont intactes — projets, suivis et réglages vous attendent tels quels.
Régularisez votre abonnement pour reprendre exactement où vous en étiez :
[ Régulariser l'abonnement → ]     Une question ? contact@labuse.immo
```

### Bandeau grâce (≤ 7 j, ambre) — `App.tsx CompteBandeau`
```
▲ Paiement requis — le dernier prélèvement n'a pas abouti. Mettez à jour votre moyen de paiement sous
  7 jours ; passé ce délai, l'accès passe en lecture seule.                              [ Régulariser ]
```

### Bandeau lecture seule (> 7 j, corail) — `App.tsx CompteBandeau`
```
▲ Accès en lecture seule — votre abonnement est à régulariser. Les modifications sont suspendues
  jusqu'au paiement.                                                                     [ Régulariser ]
```
*(toute écriture → HTTP 402 `{"detail":"Abonnement à régulariser — accès en lecture seule."}`, `app.py:659-664`)*

### Menu « Mon compte » — `Header.tsx` (via `/moi`)
```
Plan Intégral · 349 €/mois        (abonné)
Essai jusqu'au {date}             (essai en cours, ambre)
```

### E-mails du cycle de vie (gabarits Brevo — sujet/corps hébergés chez Brevo)
| Déclencheur | clé | tpl | quand |
|---|---|---|---|
| essai (manuel admin) | `essai` | 4 | création d'essai |
| lien de souscription (manuel) | `souscription` | 5 | relance commerciale |
| bienvenue / J+3 / J+10 | `onboarding1/2/3` | 6/7/8 | séquence d'accueil |
| carte refusée | `relance_carte` | 9 | `invoice.payment_failed` (lien `hosted_invoice_url`) |
| suspension | `suspension` | 10 | essai expiré / suspension |
| rétablissement | `retablissement` | 11 | `invoice.paid` (reprise) |
| résiliation | `resiliation` | 16 | `customer.subscription.deleted` (+ `DATE_FIN_ACCES`) |
| Flash prêt | `flash_pret` | 17 | PDF Flash généré |

**Absents aux pas automatiques** : aucun mail au **1er paiement** (webhook activation) ; aucun mail à la
**bascule lecture seule** (J+7, cf. T6).
