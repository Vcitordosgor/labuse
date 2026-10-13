# MANDAT-CHASSE-NAV-1 — chaque bouton mène au bon endroit, avec le bon contexte

Rédigé le 13/10/2026. Modèle : Opus. Branche `audit/chasse-nav-1` depuis main, worktree `~/Desktop/labuse-chasse-nav`, ports 8770/5970. **Lecture seule : aucun correctif, aucune écriture en base, rien sur le VPS.** Deux autres sessions tournent en parallèle (déploiement, SOLIDITE-1) : ne touche ni aux crons, ni au VPS, ni à `~/Desktop/labuse`.

## Ce que cherche Vic

Chaque bouton, lien, tuile, raccourci et passage d'un écran à un autre (carte, fiche parcelle, fiche commune, outils, Copilote, Radar, Veille, Projets, CRM, Docs, Sources, Mon compte, dashboard admin, Flash, mails, PDF) :
mène au **bon** endroit · emporte le **bon contexte** (parcelle, commune, filtres, sélection) · permet de **revenir** sans rien perdre · a le **même** comportement et le même libellé partout où la même action apparaît.

Une chasse vide est un bon résultat, à condition de la prouver.

## Règles

- **Étape 0** : `pwd`, branche, arbre propre, API et front lancés sur 8770/5970, compte admin local.
- **Jamais d'action irréversible** pendant la chasse : pas d'envoi de mail, de courrier, de paiement, de suppression, d'invitation. Ces boutons sont relevés (destination, contexte) sans être déclenchés, ou testés sur un compte de test avec l'envoi coupé ; le dire dans le rapport.
- Chaque écart est reproductible : point de départ, clic, résultat attendu, résultat obtenu, capture, fichier:ligne.
- Pas de correctif : un écart, une cause, une preuve. Les corrections viendront dans CHASSE-NAV-FIX-1.
- Avant de rendre la main : API et navigateur arrêtés (`lsof`).

## Lot A — l'inventaire de tous les passages

À partir du code (chaque `onClick`, `href`, `navigate`, `setView`, `select`, lien de mail Brevo, lien de PDF) **et** de l'app lancée : une ligne par passage dans `NAVIGATION.csv` :
`écran de départ · élément (libellé exact) · destination attendue · contexte transmis · retour possible · fichier:ligne`.
Signaler les actions identiques présentes à plusieurs endroits (ex. « Étudier ce bien », « Ouvrir la fiche », « Ajouter au CRM ») : elles seront comparées au Lot C.

## Lot B — chaque passage, testé

Parcours réels (navigateur piloté) sur des témoins : une parcelle normale, une bizone, une disparue (ouverte depuis un projet), une surface incertaine, une commune, un projet, une alerte de veille, un mail de digest (lien suivi en local). Pour chaque ligne de l'inventaire :
- **CASSÉ** : erreur, page blanche, 404, bouton sans effet.
- **FAUX** : mauvaise destination (autre parcelle, autre commune, mauvais onglet).
- **PERTE** : le contexte ne suit pas (filtres oubliés, parcelle non présélectionnée dans l'outil, commune réinitialisée).
- **RETOUR** : impossible de revenir, ou le retour perd la position, les filtres, le défilement.
- **LIEN** : une URL partagée ou rechargée (F5) ne rouvre pas le même écran.

## Lot C — la même action, le même comportement

Toutes les occurrences d'une même action (Lot A) : même destination, même contexte, même libellé, même icône. Les raccourcis des fiches parcelle et commune, des outils et du Copilote vers les mêmes outils doivent se comporter pareil.

## Lot D — boutons morts, doublons et impasses

Boutons qui ne servent à rien ou font doublon avec un autre au même endroit, écrans sans sortie, boutons grisés sans dire pourquoi, liens vers des fonctions retirées (Street View, pages supprimées), endpoints appelés par aucun bouton et boutons qui appellent un endpoint absent.

## Lot E — hors de l'app

Liens des mails (bienvenue, réinitialisation, Flash prêt, digest, alerte Radar, veille), des PDF (Dossier, Flash, Comparatif, Étude de zone), de la page de partage et de la page /flash : chacun ouvre le bon écran, sur le bon domaine (jamais `127.0.0.1` ni un ancien domaine), avec le bon contexte, et gère un lien expiré proprement. Plus le passage site vitrine → app (bouton « Commander un Flash », connexion).

## Lot F — mobile

Les mêmes parcours en émulation iPhone pour les pages publiques (/flash, retour Flash, lien expiré, connexion, réinitialisation) : rien ne déborde, chaque bouton est atteignable.

## Livrables

`docs/audit-2026-10/chasse-nav-1/` : `NAVIGATION.csv`, `ECARTS.md` (une ligne par écart : passage · gravité · départ · clic · attendu · obtenu · cause · fichier:ligne · capture), `RAPPORT.md` (5 lignes de verdict en tête), captures, et un **banc rejouable** (`scripts/coherence/chasse_nav.py` ou harnais Playwright) qui rejoue tous les passages et sort OK/ÉCART, pour devenir une garde automatique.

Un commit par lot. Ne merge pas.
