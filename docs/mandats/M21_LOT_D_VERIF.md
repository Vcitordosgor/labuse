# M21 — LOT D : vérification sur `main` mergée

Après merge Vic **A → B → C** (`f681b19 · 079b0bc · 8feea8b`, tip `8feea8b`) et `.env` rempli côté Vic
(`mail-test` **réellement reçu en boîte de réception**, expéditeur `contact@labuse.immo` — confirmé par Vic).
Reboot de main, revérification. **Non poussé.**

## Méthode de preuve (secret-safe)
Le `.env` de production contient désormais le vrai mot de passe d'application Gmail. Pour **ne pas exposer ce
secret ni spammer d'adresses réelles**, les mécaniques sont revérifiées **contre le serveur SMTP de capture
local** (transaction SMTP réelle), en surchargeant `LABUSE_SMTP_HOST/PORT` et en **vidant user/password**
(les vraies creds ne sont jamais utilisées ni loguées). La livraison Gmail réelle est déjà prouvée par le
`mail-test` de Vic — même transport pour les quatre mécaniques.

## Checklist du mandat

| Point | État | Preuve |
|---|:---:|---|
| `labuse mail-test` envoie, mail reçu | ✅ | Vic : reçu en Inbox Gmail, from `contact@labuse.immo`. CC sur main : `✓ Mail envoyé (expéditeur contact@labuse.immo)` |
| Reset mot de passe : mail + lien token | ✅ | envoi capturé — sujet « réinitialisation de votre mot de passe », lien token, validité 1 h |
| Avis d'échéance : CLI exécutée, mail reçu, **dédup** | ✅ | `labuse avis-echeance` → 1 puis **0** (dédup) ; mail « votre abonnement se reconduit le … » |
| Notifications : digest reçu, **désinscription présente et fonctionnelle** | ✅ | digest capturé (événement + lien parcelle) ; **List-Unsubscribe** + lien `/events/desabonner` présents ; après clic → 2ᵉ passage **0 envoyé** |
| Expéditeur = `contact@labuse.immo`, pas de spam | ✅ | `From: LABUSE <contact@labuse.immo>` sur TOUTES les captures ; inbox-vs-spam confirmé par Vic |
| **Aucun secret** dans le code, les logs, les commits | ✅ | `.env` jamais committé (histoire entière vide) ; aucune valeur `LABUSE_SMTP_PASSWORD=` dans un fichier tracké ; `smtp_password` n'apparaît qu'au `login()` (mail.py:82-84), jamais logué/print |
| **Golden 116/116** | ✅ | `Bilan: 116/116 PASS` (`LABUSE_DEV_MODE=1`) |

## Intégrité du merge
A + B + C présents sur main (mail.py, emails.py = 3 textes, events digest+`/desabonner`+notif_prefs = 13 marqueurs,
refus quota C2 = 2, route publique desabonner = 1). **0 marqueur de conflit.** `tsc` non concerné (backend) ;
import-smoke OK.

## Verdict LOT D
Merge propre, golden 116/116, les 4 mécaniques envoient de vrais e-mails (from `contact@labuse.immo`), désinscription
fonctionnelle, aucun secret exposé, livraison Gmail réelle confirmée par Vic. **M21 clos côté CC.**

**À planifier au VPS** (hors périmètre, rappel) : cron **quotidien** `labuse avis-echeance` (obligation Chatel) +
cron **hebdomadaire** `labuse digest`. Suggestions par e-mail = décision Vic (non codé).
