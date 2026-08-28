# MANDAT — RETOURS VISUELS 1 : CORRECTIONS APRÈS VÉRIFICATION DE VIC
Régime AUTONOME. Commits par lot (R1→R9). RÈGLES COMMUNES. Findings RT-001→.
Vic a vérifié de ses yeux les 11 mandats de la soirée du 27/08, en local. Ce mandat corrige ce qu'il a relevé. C'est SA liste : chaque point est une décision produit déjà prise — tu exécutes, tu ne rediscutes pas le bien-fondé. Quand un point demande une enquête, l'enquête sert à trouver la cause, pas à remettre la décision en question.
Pour chaque lot visuel : capture avant/après au rapport.

## R1 — MENU « MON COMPTE »
Le menu affiche encore l'ère pilote : « Accès pilote — l'abonnement par compte (facturation) arrive. » et « Session pilote ». C'est périmé — la facturation existe.
- Affiche le vrai statut du compte, depuis la source de vérité des offres (offres.py) : le plan réel du compte connecté et l'e-mail du compte. Un compte interne/admin affiche « Compte interne », jamais un prix.
- Chasse exhaustive : grep « pilote » (et variantes de casse) dans tout le front — plus AUCUNE mention de l'ère pilote nulle part. Liste les occurrences trouvées au rapport.
- Retire « Proposer une amélioration » : doublon du bouton Signaler déjà présent dans la barre.

## R2 — PANNEAU DE RECHERCHE
- **Retire la section de filtres « Propriétaire »** (SIREN, APE, forme juridique...) du panneau de recherche. FRONT SEULEMENT : les endpoints, les données et les tests back restent en place — c'est réversible. Aucune régression sur les autres filtres.
- **Sélecteur de commune : restaure l'ancien comportement** — les codes postaux affichés, et le nom entier de la commune au survol. Retrouve dans l'historique git quel mandat l'a changé, dis-le au rapport, et restaure.

## R3 — OUTIL COMMUNES RESTRUCTURÉ
Quand on clique sur « Communes », un écran d'entrée à TROIS boutons :
1. **Comparaison communes** — le tableau comparatif actuel, ouvert en grand.
2. **Évolution du marché** — ce qui existe actuellement.
3. **Acquisitions récentes** — NOUVEAU : un sélecteur de commune, puis le listing des changements de propriétaire PM récents de cette commune (le contenu du bloc « Acquisitions PM récentes » actuellement en fiche commune). Un clic sur une ligne mène à la parcelle. Le constat reste brut (« changement de millésime, n'affirme pas une vente »), hors scoring.
Le bloc « Acquisitions PM récentes » QUITTE la fiche commune — il vit désormais ici, uniquement.

## R4 — FUSION DES DEUX FICHES COMMUNE
Il existe aujourd'hui deux fiches commune : celle de l'outil et celle du contexte (écran principal). Vic n'en veut qu'UNE : celle du contexte.
- Fais l'inventaire écrit de ce que porte chacune des deux fiches (liste au rapport).
- Transfère vers la fiche de contexte tout ce que la fiche-outil a d'important et qu'elle n'a pas (contacts mairie inclus s'ils n'y sont que d'un côté). AUCUNE donnée perdue — l'union des deux, ET aucun doublon après transfert.
- « Voir la fiche » dans le tableau de comparaison ouvre désormais la fiche commune de contexte, en panneau à droite, comme sur l'écran principal.
- La fiche-outil disparaît. Une seule fiche commune dans toute l'app.

## R5 — TAXE D'AMÉNAGEMENT
L'outil affiche « Barème indisponible — réessayez plus tard. » : le message honnête a fait son travail, mais le barème doit charger.
- Diagnostique : le barème est-il en base (seed/migration manquante en local ? en prod ?) ou l'endpoint est-il cassé ? La réparation doit marcher en local ET survivre au déploiement (si c'est un seed, il doit être rejouable).
- Vérifie les calculs contre le barème officiel applicable au 974 (taux communaux, part départementale, valeur forfaitaire, abattements) — source citée dans le code, jamais un taux inventé. Si une commune n'a pas de taux fiable, l'outil le dit pour CETTE commune, sans bloquer les autres.
- **Accès depuis la fiche parcelle** : un bouton vers l'outil, la commune de la parcelle pré-remplie (et la surface si elle est disponible).

## R6 — HISTORIQUE PROPRIÉTAIRES PAR MILLÉSIME
Vic ne le voit pas sur la fiche parcelle. Enquête : où le composant ProprietaireHistorique est-il monté, sous quelle condition s'affiche-t-il, pourquoi est-il invisible sur les parcelles testées ? Dis la cause au rapport.
Cible, quelle que soit la cause : dans l'onglet Propriétaire de la fiche parcelle, un bouton « Voir les anciens propriétaires » (ou un libellé meilleur — propose) qui déplie l'historique par millésime. Toujours le constat brut, hors scoring.

## R7 — INTAKE ADMIN RADAR : LE DÉPÔT DOIT MARCHER POUR DE VRAI
Vic a ajouté une capture et n'a pas réussi à déposer : il n'a pas trouvé où coller le lien. Le champ existe dans le code — mais un champ qu'on ne voit pas ou qu'on ne peut pas remplir n'existe pas.
- Diagnostique le geste réel : le champ est-il focusable ? La dropzone capte-t-elle les clics ? La validation est-elle muette ?
- Corrige : dès qu'une capture est ajoutée, le champ lien prend le focus automatiquement ; label visible au-dessus du champ (pas seulement un placeholder gris) ; bordure d'erreur + message clair si on clique Déposer sans lien ; le bouton Déposer réagit visiblement.
- PREUVE : un test navigateur (Playwright) du geste complet — ajouter une image, coller un lien, cliquer Déposer, voir la fiche apparaître dans la file d'extraction. Pas seulement des tests unitaires : le geste.

## R8 — CARTE ET NAVIGATION
- Retire la pastille « Carte à jour au JJ/MM/AAAA » de la carte.
- Retire le bouton « Zone — Dessinez un polygone » de la barre d'outils de la carte (celui dont l'infobulle dit « les résultats sont filtrés à la zone »). Le back peut rester. Ne touche pas aux autres boutons du groupe.
- BUG : deux catégories du rail peuvent être ouvertes en même temps (Veille restée ouverte derrière Sources). Ouvrir une catégorie FERME la précédente — une seule ouverte à la fois. Vérifie sur toutes les paires.

## R9 — ENQUÊTE : L'ONGLET MARCHÉ BLOQUÉ EN « CHARGEMENT... »
L'onglet Marché du Radar reste sur « Chargement... » au lieu de l'état de démarrage digne exigé. L'UI de cet onglet va être refondue (maquette en cours) — NE refais PAS l'écran. Mais diagnostique et corrige l'endpoint : pourquoi ne répond-il pas (crash ? promesse jamais résolue ? erreur avalée) ? L'endpoint doit répondre proprement même à zéro donnée, et l'écran actuel doit au minimum sortir du chargement infini (état vide honnête). La cause au rapport — si elle peut frapper d'autres endpoints, dis-le.

## FIN
Critères : chaque point de la liste de Vic traité ou documenté · captures avant/après pour R1-R8 · inventaire de fusion R4 au rapport · test Playwright R7 vert · gardées vertes · tsc/build verts · suite au niveau de la base (prouvé par worktree) · aucune donnée de test résiduelle.
Compte-rendu « Demandé → traité » par lot + commande de merge en dernier élément isolé (git merge --no-ff fix/retours-visuels-1). Tu ne merges pas.
