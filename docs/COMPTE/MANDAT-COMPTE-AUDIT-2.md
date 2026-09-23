# MANDAT COMPTE-AUDIT-2 — comment on onboarde un client, aujourd'hui

**Lecture seule.** Aucun fichier de `src/`, `frontend/`, migrations ou tests n'est modifié. Livrable : `docs/COMPTE/COMPTE-AUDIT-2.md` + captures dans `docs/COMPTE/captures-audit-2/`.
Branche `audit/compte-audit-2` depuis `main`. Autonomie : aucune question, on tranche et on note. Commit du rapport avant le compte-rendu. Merge = Vic.

## Étape 0
`pwd` = `~/Desktop/labuse-compte-audit` (worktree dédié, créé par Vic), branche `audit/compte-audit-2` propre depuis `main`, venv emprunté (`. ~/Desktop/labuse/.venv/bin/activate && pip install -e . -q`), API sur la base locale réelle (`DATABASE_URL` du `.env`) sur un port libre (pas 8000 si une autre session tourne), front lancé, Playwright disponible. Sinon stop.

## Règles
- Comptes créés pour l'audit préfixés `[CT-TEST]`, emails `@labuse.test`. Inventaire de purge en fin de rapport.
- Mails réels **uniquement** vers `victorlaganepro@gmail.com`, un par template au maximum, avec la vraie clé Brevo du `.env`.
- Chaque réponse porte une preuve : `fichier:ligne`, capture nommée, ligne de `mail_queue`, statut HTTP. Pas de « je pense ».
- Verdicts : OK · KO · ABSENT · DOUTE. 🔴 = bloque l'onboarding ou fait croire à Vic qu'un mail est parti.

## Les quatre questions de Vic

### 1 — Comment on onboarde un client depuis le dashboard
Depuis la page Comptes réelle sur `main` : lister les entrées existantes (« Créer un client », « Ouvrir un essai 48 h », autre). Pour chacune, le parcours écran par écran avec captures : ce que Vic saisit, ce qui est créé en base (statut, échéance, token), ce qui part ou non. Vérifier que les cinq statuts (Invité · Invitation envoyée · Actif · Suspendu · Expiré) sont ceux réellement servis, et que la colonne « À faire » suit l'état.

### 2 — Est-ce bien relié aux mails
Pour chaque bouton de la fiche client qui envoie un mail : template Brevo appelé (ID du registre `brevo.REGISTRE`), entrée dans `mail_queue` avec ses params, état après retour Brevo, écran daté. Tableau bouton → template → preuve. Prouver le dry-run (clé retirée → l'écran ne dit **pas** « envoyé »). Envoyer réellement l'invitation essai (4) et l'invitation souscription (5) à `victorlaganepro@gmail.com` et donner les message-id. Signaler tout bouton qui ne passe pas par la file.

### 3 — Comment le client crée son compte
Depuis le lien reçu dans le mail : la liste numérotée de toutes les pages jusqu'à l'arrivée dans l'app, pour l'essai et pour l'intégral (Stripe en mode test), captures à chaque page. Vérifier : GET non consommant du token, token réutilisé → page « lien plus valide », mot de passe oublié bout en bout (14 puis 15), première arrivée dans l'app (bandeau d'essai, échéance visible), console sans erreur.

### 4 — Comment Vic crée un compte de test pour quelqu'un
Livrer une **procédure en cinq à dix lignes**, telle que Vic peut la suivre demain sans ouvrir le code : créer le compte, choisir essai ou intégral, prolonger l'essai au-delà de 48 h (existe-t-il un champ « date de fin » ? sinon ABSENT 🔴 avec le geste SQL de contournement), envoyer l'invitation, vérifier qu'elle est partie, renvoyer si besoin, suspendre / supprimer à la fin. Dire ce qui manque pour que ce soit propre.

## Livrable
`COMPTE-AUDIT-2.md` : les quatre réponses dans l'ordre, en français lisible, une ligne par contrôle avec verdict et preuve ; la liste des 🔴 en tête avec le correctif proposé en une ligne ; la procédure du point 4 ; l'inventaire de purge. Rien d'autre — pas d'audit collatéral (IDOR, mémoire du compte, prod).
