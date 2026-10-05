# PARCOURS-CLIENT-1 — liste numérotée des étapes (écrite AVANT de jouer)

Environnement : worktree `~/Desktop/labuse-parcours`, base = origin/main `56cc27ea` (HEAD), API single-origin
`http://127.0.0.1:5995` (sert le front buildé sous `/socle`, les pages serveur, et l'API), DRY-RUN mail
(SMTP vidé), auth active (pilote = admin sans TOTP ; client = email+mot de passe). Captures Playwright Node
`chromium` 1440×900 (desktop) + 390×844 (mobile). Comptes de test `[CT-PARCOURS]` @labuse.test (masqués),
purgés en fin de session.

> Choix d'architecture assumé : single-origin (front buildé servi par FastAPI) plutôt que vite+proxy, pour
> jouer l'expérience RÉELLE du client (prod = même origine via Caddy) et ne pas prendre un trou de proxy dev
> pour un bug produit. Port unique 5995 (le « 8795 » du mandat = slot front, ici fusionné).

## Déjà prouvé (COMPTE-2/AUDIT-2/3 + CLOISONNEMENT-1) — non rejoué, cité
- Cycle de vie : `creer-essai` (actif + échéance), `creer` (invitation), `activer_par_invitation` (mdp+CGV
  argon2id), login email, prolonger/suspendre/rétablir/déconnecter, `effacer_compte_rgpd`.
- 16 templates Brevo (IDs 4→19), registre `brevo.py`, vérifiés 16/16 actifs par API (COMPTE-2 Lot 1).
- Dry-run : SMTP vide → `mail_queue` `en_attente`, jamais « envoyé » par optimisme (RV-013).
- RGPD : cascade FK + DELETE explicites `mail_queue`/`contact_etiquette_log` ; 4 tables prouvées à 0.
- Cloisonnement : projets/CRM/veilles/zones 404 cross-tenant ; fuites connues pilot-masquées
  (signalements/saved_filters/event_log/watched_parcels) — à re-confirmer post-merges.

## Section A — les mails (avant le parcours)
- A. Pour chacun des 16 templates : déclencheur, rendu (params de test), vérif variables/objet/expéditeur/
  reply-to/dates Réunion/lien prod vs 127.0.0.1 (bandeau)/signature/mentions/désabo/orthographe/vouvoiement/
  mobile. Templates jamais déclenchés signalés. → MAILS.csv + mails/NN-*.png

## Section B — côté Vic (dashboard)
1. `#admin=1` : Comptes → « Ouvrir un essai » : formulaire vide, validations (mail invalide, doublon,
   champ vide, accents), création, ligne dans la liste (statut/échéance/licence), fiche.
2. File `mail_queue` : invitation en attente → « parti » (dry-run) → échec simulé (Brevo en panne) :
   statut, relance, message à Vic.
3. Prolonger (48h→7j), suspendre, réactiver, renvoyer invitation, réinit mot de passe depuis l'admin :
   geste → effet base → écran → mail éventuel.

## Section C — côté client
4. Lien d'invitation : page mot de passe (règles, faible refusé, confirmation ≠ refusée, succès) ;
   2e clic refusé ; lien expiré (message + sortie).
5. Connexion : login (mauvais mdp, suspendu, expiré) ; « se souvenir » ; durée session ; déconnexion.
6. Première entrée : chaque écran d'un nouveau (accueil, bandeaux, aide, 1er geste). Verdict « comprend ? ».
7. 20 gestes promoteur (compte client) : adresse · fiche · potentiel+bande · filtre commune · Faisabilité ·
   Gabarit 2D/3D · Taxe aménagement · Assemblage 2 parcelles · Dossier PDF · Pré-dossier · Veille · alerte ·
   Copilote (1 question + plafond IA) · Mes documents · Radar · Signaler erreur · Comparer communes ·
   Remonter le temps · Mes vues · partage fiche. + 5 URL admin → 403 propre.
8. Mon compte : infos, échéance, changement mdp (ancien refusé ensuite), déconnexion, « mdp oublié »
   (reset dry-run → lien → nouveau mdp → connexion), pages légales (CGU, mentions, confidentialité, contact).
9. Fin d'essai : forcer l'expiration (compte test) → écran client login + in-app, données intactes,
   chemin clair ; mails J-1/J0/après déclenchés par jobs ? (dry-run).
10. Deux clients A/B : 3 gestes croisés (Veille, Mes documents, Copilote) : chacun ne voit que ses données.
11. Navigateurs : parcours 4→8 rejoué sous Safari (webkit) en plus de Chrome (login, fiche, PDF, Copilote).

## Section D — retour côté Vic
12. Dashboard : activité du client (connexions, usage, plafond IA, Journal, Comptes) juste et à jour.
13. Suppression RGPD : tout disparaît ; requête 0 ligne orpheline par table à compte_id.

## Livrables
RAPPORT.md · PARCOURS.csv · MAILS.csv · captures/desktop · captures/mobile · mails · script Playwright.
Purge `[CT-PARCOURS]` vérifiée (0 ligne). Commit + push `audit/parcours-client-1`. Pas de merge.
