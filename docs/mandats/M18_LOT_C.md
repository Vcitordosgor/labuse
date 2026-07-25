# M18 — LOT C : vérification post-merge + clause CGV corrigée

**Sur `main`** (M18-A + M18-B mergés). Merges + correctif CGV committés, **non poussés** (Vic valide + pousse).

## Merges
| Merge | Commit | Conflit |
|---|---|---|
| `feat/m18-a-integral` | 3f7cb3b | aucun (1er merge) |
| `feat/m18-b-flash` | 99ac7d6 | **aucun** — A et B éditent `onboarding.py` sur des routes **différentes** (A: /invitation, /onboarding/*, /reset ; B: /flash*) → auto-mergé proprement. `coffre_ui.py` (favicon + `:disabled`) vient de A, partagé. |

Toutes les intentions présentes (marqueurs A + B vérifiés, aucun marqueur de conflit).

## Correctif clause CGV (contradiction levée) — commit a308581
`onboarding.py` §5 « Durée, reconduction et résiliation » : « résiliable à tout moment » **remplacé** par :
- **durée ferme de 12 mois**, facturé mensuellement ;
- **reconduction tacite par périodes successives de 12 mois**, sauf **dénonciation ≤ 1 mois avant la date
  anniversaire** ;
- **loi Chatel (art. L. 215-1)** : LABUSE **informe le client 3→1 mois avant chaque terme** de sa faculté de
  non-reconduction ; à défaut, résiliation gratuite de la reconduction + remboursement.
- Page paiement alignée : « reconduction par périodes de 12 mois — dénonçable avant chaque échéance (vous
  êtes prévenu à l'avance) ».

### Obligation d'avis d'échéance → déclencheur câblé (envoi e-mail NON simulé)
Comme le reset (A6) : point d'envoi **identifié**, envoi réel **inactif** jusqu'au branchement e-mail.
- **Point d'envoi** : `comptes._envoyer_avis_echeance(email, échéance, lien)` → trace le rappel dans le log
  (= file d'attente). Corps remplacé par le vrai envoi dès qu'un service e-mail sera câblé.
- **Déclencheur cronable** : `comptes.declencher_avis_echeance()` — sélectionne les comptes actifs dont une
  échéance annuelle tombe dans la **fenêtre Chatel [~3 mois, ~1 mois]**, appelle le point d'envoi, dédup par
  terme (via `evenements_compte`). CLI **`labuse avis-echeance`** (mensuel).
- **Prouvé** : compte créé il y a 11 mois → détecté (échéance 2026-08-25), 1er passage envoie+enregistre,
  2e passage **dédup → 0**. Jamais « e-mail envoyé » affiché.

## Recapture sur main mergée (`:8060`, `qa/m18/{A,B}/`)
- [x] **Favicon** LABUSE sur toutes les pages des deux tunnels (SVG inline, coffre_ui)
- [x] **A1** arrivée soignée + offre « 349 €/mois · engagement 12 mois »
- [x] **A2** CGV décochées → CTA désactivé + message ; page serveur « ← Revenir » (aucun cul-de-sac)
- [x] **A3** « Engagement 12 mois » + « en toute sécurité » retiré (« Payer 349 € »)
- [x] **A4** post-paiement « BIENVENUE CHEZ LABUSE » + bouton d'accès proéminent
- [x] **A5** phrase « pré-analyse sur données publiques » retirée du consentement
- [x] **A6** reset self-service (formulaire e-mail + page nouveau mot de passe), envoi honnête
- [x] **B1** arrivée « Voir ma parcelle » + valeur PDF explicitée
- [x] **B2** pré-paiement attractif (« Dans votre PDF » + réassurances + « recevoir mon rapport »)
- [x] **B3** post-paiement « VOTRE RAPPORT EST PRÊT » en vedette + bouton PDF proéminent
- [x] **B4** PDF inventorié (8 sections, aucune identité de personne physique) — cf. M18_LOT_B.md
- [x] **CGV** : durée ferme 12 mois · reconduction tacite 12 mois · loi Chatel ; « résiliable à tout moment » = **0**
- [x] **Golden 116/116**

## État
`main` local prêt pour validation (2 merges + correctif CGV/Chatel), **non poussé**. Stripe et envoi
e-mail restent hors périmètre (pages + mécaniques prêtes au branchement).
