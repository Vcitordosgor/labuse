# PREMIER EURO — auth réelle, Stripe, CGV, onboarding founding (rapport vivant)

**Branche `commerce/premier-euro` · STOP mi-course (tout prouvé en MODE TEST) → STOP final
(bascule live sur verdict) · Vic merge.** Doctrine : rien de simulé, rien en live avant preuve.

## ⟪ CURSEUR ⟫ E1 (identité) en cours

## Prérequis Vic — état

| Prérequis | État |
|---|---|
| Clé Stripe **mode TEST** | **MANQUANTE** — bloquant pour la PREUVE E2 (le code sera prêt-à-clé) |
| Clé Resend | **MANQUANTE** — le mailer a un transport dev (fichier .eml) ; liste DNS fournie dès la clé |
| Décisions 1-6 | pré-tranchées, appliquées telles quelles |

## E1 · Identité (moteur derrière la façade Coffre)
_(en cours)_

## E2 · Stripe (mode test)
_(prêt-à-clé, preuve dès la clé TEST)_

## E3 · CGV / pages légales
_(à venir — note : relecture Vic obligatoire + passage avocat recommandé avant signatures)_

## E4 · Onboarding founding
_(à venir)_

## E5 · QA / golden / filets
_(à venir — golden 116/116 avec auth active exigé)_

## Signalements (jamais un conseil)
- **TVA auto-entrepreneur** : la franchise en base a des seuils (BNC/BIC services ~36,8 k€ ;
  au MRR visé ils seront dépassés dans l'année) — vérifier le régime et poser la mention
  adaptée sur les factures Stripe DÈS le départ (champ « informations fiscales » du compte).
  À trancher avec le comptable — pas un conseil fiscal.
