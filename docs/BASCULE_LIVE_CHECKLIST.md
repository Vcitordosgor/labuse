# Checklist « bascule live » Stripe — le jour J

> Pour passer LABUSE de **test** à **encaissements réels**. Le parcours de paiement est déjà prouvé en test (Flash + Intégral : nominal, impayé, résiliation, reprise) et **l'infra prod est prête** : le chemin `/stripe/webhook` est exempté du rideau Caddy (déployé le 23/07) et **fail-closed** (503) tant qu'aucun `whsec` live n'est posé. Il ne manque que la config Stripe live sur le VPS.
> Poser TOUTE valeur de secret avec un **éditeur** (`nano`), **jamais dans un chat**. Un secret vu ailleurs = à révoquer. Cf. [`RUNBOOK_ROTATION_CLES.md`](RUNBOOK_ROTATION_CLES.md), [`DEPLOIEMENT_M7_CHECKLIST.md`](DEPLOIEMENT_M7_CHECKLIST.md).

## 🚦 GATE légal — AVANT d'encaisser un seul euro réel
- [ ] **Comptable OK sur la TVA** → régime tranché ; ajuster `facture_mention` (config) si assujetti (défaut actuel = franchise 293 B).
- [ ] **SIREN/SIRET + adresse complète** posés sur `/mentions-legales` (aujourd'hui encore `[à confirmer]` + adresse sans voie).
- [ ] **CGV/CGU relues** (avocat recommandé avant les premières signatures payantes).
- [ ] **`display_name` Stripe = « LABUSE »** (Settings → Business / Public details) — ce que voit le client sur la page de paiement.

## 1. Clés live
- [ ] Dashboard Stripe → **mode Live** (toggle) → *Developers → API keys* → révéler/roll la **Secret key** (`sk_live_…`).

## 2. Produits live
- [ ] Poser temporairement `sk_live_…` dans un env, puis `labuse stripe-provisionne` → crée **Intégral 349 €/mois** + **Flash 79 €** *en live* et affiche les **price IDs live** (`price_…`).
  *(ou créer les 2 produits/prix à la main dans le dashboard live.)*

## 3. Endpoint webhook (dashboard Stripe **Live**)
- [ ] *Developers → Webhooks → Add endpoint* → URL **`https://app.labuse.immo/stripe/webhook`**.
- [ ] **Événements à cocher** (ceux que l'app traite) : `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`, `customer.subscription.deleted`.
- [ ] Copier le **Signing secret** (`whsec_…` live).
- Le rideau Caddy exempte déjà ce chemin → Stripe l'atteint (vérifié : `GET /stripe/webhook` = 405, pas 401).

## 4. Poser la config live sur le VPS
- [ ] `ssh labuse-vps 'sudo nano /etc/labuse/labuse.env'` → ajouter/renseigner :
  ```
  LABUSE_STRIPE_SECRET_KEY=sk_live_…
  LABUSE_STRIPE_WEBHOOK_SECRET=whsec_…      # le signing secret de l'endpoint ci-dessus
  LABUSE_STRIPE_PRICE_INTEGRAL=price_…      # live
  LABUSE_STRIPE_PRICE_FLASH=price_…         # live
  ```
- [ ] `ssh labuse-vps 'sudo systemctl restart labuse'`.

## 5. Vérifs AVANT le premier vrai paiement
- [ ] `curl -s -o/dev/null -w '%{http_code}' -X POST -d '{}' https://app.labuse.immo/stripe/webhook` → **400** (et non 503) = le secret webhook est posé, la **signature est exigée** (une requête non signée est refusée).
- [ ] Dashboard Stripe → l'endpoint → **Send test webhook** (`checkout.session.completed`) → **Delivered 200**.
- [ ] `/healthz/crons` : la **sentinelle webhook** ne signale pas d'anomalie.

## 6. Smoke LIVE (un vrai paiement, petit d'abord)
- [ ] **Flash 79 €** avec une **vraie carte** → retour → **PDF téléchargé** ; dashboard → paiement **succeeded** + webhook **Delivered 200**.
- [ ] (optionnel) **Intégral 349 €** réel → `actif` → accès.
- [ ] **Rembourse/annule** ensuite si c'était un test (dashboard → Refund / Cancel subscription).

## 7. Après la bascule
- Surveiller `/healthz/crons` (sentinelle webhook — un silence prolongé = webhook en panne) et les premiers vrais paiements dans le dashboard.
- Si tu ouvres l'app au **public** (chute du rideau) : appliquer d'abord les durcissements P1 de l'audit sécu (CSP, gating par plan sur `comptes.plan`, HSTS) — cf. `docs/audits/SYNTHESE_360.md`.

## ⏮ Rollback (revenir en test / fail-closed)
- Retirer les 4 variables `LABUSE_STRIPE_*` de `/etc/labuse/labuse.env` + `sudo systemctl restart labuse` → le webhook redevient **503** (aucun paiement traité). Les clés live restent révocables dans le dashboard.

---
**En bref** : le code et l'infra sont prêts (webhook exempté + signé). Le jour J = **clés+produits+endpoint live → 4 variables sur le VPS → restart → smoke live**. Le reste (TVA/SIREN/CGV/display_name) est le gate légal, à ta main.
