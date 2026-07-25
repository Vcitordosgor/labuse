# M18 — LOT A : parcours INTÉGRAL (abonnement)

**Branche** `feat/m18-a-integral` (base `main`). Prouvé, **non mergé**. Stripe et envoi e-mail **hors
périmètre** (pages prêtes au branchement, jamais de paiement/e-mail simulé).

Tunnel : `/invitation` (arrivée + compte + CGV) → `/onboarding/paiement` → `/onboarding/retour`
(post-paiement) → `/login`. Reset : `/reset`.

## RG-FAV — favicon LABUSE partout
`coffre_ui.page()` (le shell de TOUTES les pages du tunnel) reçoit désormais un **favicon SVG inline =
logo buse LABUSE** (prioritaire, indépendant du service statique ; les PNG restent en repli). Garanti
sur chaque page des deux tunnels.

## A1 — Écran d'arrivée
`/invitation` : offre affichée « licence Intégral · 349 €/mois · **engagement 12 mois** » + phrase de
valeur (« Votre e-mail est déjà validé par l'invitation. Choisissez un mot de passe et vous entrez dans
le radar foncier de La Réunion. »). Placeholder e-mail (page de connexion) : `vous@cabinet.re` →
**`prenom.nom@cabinet.re`** (exemple B2B plus crédible).

## A2 — Bug CGV (PRIORITAIRE) : plus de cul-de-sac
- **Client** : le bouton « Continuer vers le paiement » est **désactivé** tant que les CGV ne sont pas
  cochées (JS `labCgv`), avec le message explicite « Vous devez d'abord accepter les conditions générales
  pour continuer. » Un style `:disabled` (grisé) rend l'inactivité visible. Cocher → bouton actif, message
  masqué.
- **Serveur (repli JS-off)** : la page « Conditions requises » (POST sans CGV) porte maintenant un
  **bouton « ← Revenir »** vers `/invitation?token=…`. **Le cul-de-sac est fermé** dans les deux cas.

## A3 — Page paiement
Offre corrigée : « **349 € /mois** · **Engagement 12 mois**, facturé mensuellement » + ligne de confiance
« 349 €/mois pendant 12 mois, puis reconduction mensuelle. » **« en toute sécurité » retiré** du bouton →
« Payer 349 € ».
⚠ **À arbitrer (voir §Décisions)** : la page CGV légale (`onboarding.py:~308`) dit encore « résiliable à
tout moment » — **contradiction** avec l'engagement 12 mois affiché. Je n'ai **pas** touché au texte légal
(ressort de Vic) ; à réconcilier.

## A4 — Post-paiement
`/onboarding/retour` refait : « **Bienvenue chez LABUSE** · votre abonnement Intégral est actif » + copie
valorisante (ce à quoi il accède) + **gros bouton vert « Entrer dans LABUSE → »** (rempli, ombré, mis en
avant).

## A5 — Phrase retirée
« les analyses LABUSE sont une pré-analyse sur données publiques, jamais un conseil » **retirée** du bloc
consentement CGV (`/invitation`). Consentement épuré : « J'ai lu et j'accepte les conditions générales. »

## A6 — Mot de passe oublié (self-service, mécanique complète)
- `/reset` (sans token) = **vrai formulaire e-mail** (« Recevoir le lien → ») + retour connexion, à la
  place de « écrivez à votre contact LABUSE ».
- `POST /reset-demande` : génère le **token + lien (1 h)** via `demander_reset` (anti-énumération : même
  réponse que le compte existe ou non), câblé au **point d'envoi `_envoyer_reset_email()`**.
- **État HONNÊTE** : on n'affiche **jamais** « e-mail envoyé ». La page dit « Demande enregistrée · un lien
  valable 1 h a été généré · **l'envoi automatique par e-mail est en cours d'activation** — en attendant,
  votre contact LABUSE peut vous le transmettre. »
- **Point d'envoi identifié** : `_envoyer_reset_email(email, lien)` TRACE le lien dans le log serveur
  (= file d'attente consultable). **Dès que l'e-mail sera branché, ce corps de fonction est remplacé, sans
  toucher aux appelants.** La page `/reset?token=` (nouveau mot de passe) est fonctionnelle et testable.

## Preuve (`:8060`, `qa/m18/A/prove.mjs`)
CGV : CTA **désactivé** + message quand décochées → **actif** + message masqué une fois cochées ✓ ;
paiement « Engagement 12 mois » + « en toute sécurité » retiré + « Payer 349 € » ✓ ; post-paiement
« BIENVENUE CHEZ LABUSE » + bouton d'accès ✓ ; reset formulaire e-mail + page nouveau mot de passe ✓ ;
favicon SVG présent ✓. Captures : `a1_arrivee_cgv_bloque`, `a2_cgv_cochees_cta_actif`, `a3_paiement`,
`a4_bienvenue`, `a6_oublie_formulaire`, `a6_nouveau_mdp`.

## Golden
**116/116 PASS** (`LABUSE_DEV_MODE=1`, `:8060`). Zéro touche scoring.

## Textes produits (relecture Vic — sa voix commerciale)
- Offre : « licence Intégral · 349 €/mois · engagement 12 mois » · « Engagement 12 mois, facturé mensuellement »
- Message CGV bloquée : « Vous devez d'abord accepter les conditions générales pour continuer. »
- Post-paiement : « Bienvenue chez LABUSE · votre abonnement Intégral est actif » + « Vous avez désormais
  accès à tout le radar foncier de La Réunion… »
- Reset : « Demande enregistrée · un lien valable 1 h a été généré · l'envoi automatique par e-mail est en
  cours d'activation… »
- Placeholder e-mail : `prenom.nom@cabinet.re`

## Décisions ouvertes / états externes
- **CGV vs engagement 12 mois** : réconcilier le texte légal CGV (« résiliable à tout moment ») avec
  l'offre affichée (engagement 12 mois). **Décision + rédaction légale = Vic.**
- **Stripe** : le paiement reste non branché (hors périmètre) — pages prêtes.
- **Envoi e-mail reset** : mécanique complète, **envoi réel inactif** jusqu'au branchement d'un service
  e-mail (point `_envoyer_reset_email`).
