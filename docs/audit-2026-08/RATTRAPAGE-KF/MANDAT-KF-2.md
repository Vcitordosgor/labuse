# MANDAT — RATTRAPAGE KELFONCIER 2/2 : INGESTION
Régime AUTONOME. Commits par lot (L0→L3). RÈGLES COMMUNES. Findings KF-101→.

## AVERTISSEMENT DE MÉTHODE — L0 D'ABORD, ET IL PEUT TOUT ARRÊTER
Ce mandat repose sur des données EXTERNES dont la disponibilité pour La Réunion n'est PAS acquise. Contrairement au KF-1 (qui exposait des données déjà en base), ici tout commence par une vérification de terrain.
Le lot L0 est une ENQUÊTE, pas une implémentation. Tu ne construis rien avant de l'avoir écrite au rapport. Si une source s'avère absente, vide sur le 974, ou payante, tu le DIS et tu passes au lot suivant — tu n'inventes pas de substitut, tu ne bricoles pas une approximation, tu ne remplis pas un trou avec une estimation. Un chantier abandonné avec sa raison écrite est un meilleur résultat qu'une couche à moitié fausse.

## L0 — ENQUÊTE DE DISPONIBILITÉ (à faire en premier, rapport avant tout code)
Pour chacune des deux sources ci-dessous : établis où elle se télécharge, sous quelle licence, à quelle fréquence elle est mise à jour, quels millésimes sont réellement disponibles, ce qu'elle contient POUR LE 974 (nombre de lignes, colonnes utiles, couverture des 24 communes), et son poids. Télécharge un échantillon et regarde-le vraiment — ne conclus pas depuis une page de documentation.

**(a) Fichiers des locaux et parcelles des personnes morales (DGFiP, open data), millésimes 2019→2025.**
LABUSE a déjà ingéré un millésime (~82 701 liens parcelle↔PM, cf. K1). La question est : les millésimes ANTÉRIEURS sont-ils encore téléchargeables ? Lesquels ? Même structure de fichier d'une année sur l'autre ? Le code direction / code 97 est-il stable ?

**(b) ECLN — Enquête sur la commercialisation des logements neufs (programmes, VEFA, terrains à bâtir).**
Vérifie ce que l'ECLN publie réellement pour La Réunion : l'enquête a des seuils de diffusion et un secret statistique qui peuvent vider les mailles fines en outre-mer. Si le 974 n'est pas exploitable à la parcelle ou à la commune, dis-le — c'est une conclusion valable et utile.
Si ECLN est inexploitable, évalue en remplacement les sources déjà repérées lors de la recon KelFoncier : Cartofriches (Cerema), Orfel (foncier de l'État). Ne les ingère PAS dans ce mandat — évalue et rapporte.

## L1 — HISTORIQUE DES PROPRIÉTAIRES PAR MILLÉSIME (si L0-a est vert)
Ingère les millésimes disponibles dans une table versionnée par année, sans jamais écraser le millésime courant servi. Le millésime est une colonne, pas un écrasement.
Puis construis le DIFF ANNUEL : pour chaque parcelle, le changement de propriétaire moral d'une année sur l'autre. C'est le signal qui intéresse un promoteur — « quelle SCI achète où », un remembrement en cours, une société qui accumule dans un secteur.
Exigences :
- Le diff est un CONSTAT, jamais une interprétation. « La parcelle X est passée de la SCI A à la SCI B entre 2023 et 2024 » : oui. « La SCI B prépare une opération » : non.
- Affichage dans la fiche parcelle : l'historique par millésime, avec la date de chaque source.
- Une vue « acquisitions récentes par secteur » si le volume s'y prête — sinon, le dire et s'arrêter à la fiche.
- RGPD : ces fichiers ne portent que des personnes MORALES. Aucune personne physique n'entre ici, sous aucune forme.
- Le diff n'entre PAS dans le scoring dans ce mandat. Il s'affiche, il ne pondère rien. (Un signal qui entre au score exige une validation walk-forward — hors périmètre.)

## L2 — PROGRAMMES NEUFS / VEFA (si et seulement si L0-b est vert)
Ingère ce qui est réellement exploitable, en couche cartographique + affichage commune. Chaque valeur porte sa maille réelle (commune ? EPCI ? département ?) et son millésime. Si la donnée n'existe qu'au niveau département, elle s'affiche au niveau département et le dit — elle ne se répartit pas silencieusement sur les communes.
Si L0-b est rouge : ce lot est ANNULÉ, tu écris pourquoi, et tu passes à L3.

## L3 — FRAÎCHEUR ET EXPLOITATION
Toute source ingérée rejoint le registre des sources (cadence, date, badge « à mettre à jour ») visible au dashboard admin, et sa commande de rafraîchissement est documentée dans EXPLOITATION-CRON.md. Une source qu'on ne sait pas rafraîchir est une source qui pourrira : si le rafraîchissement n'est pas automatisable, écris la procédure manuelle.

## FIN
Critères : L0 écrit et honnête (une source absente est une conclusion, pas un échec) · aucune donnée inventée ni maille silencieusement changée · millésimes versionnés sans écraser le servi · diff propriétaire = constat sourcé, hors scoring · sources au registre avec cadence · gardées vertes · tsc/build verts · suite au niveau de la base (prouvé par worktree).
Compte-rendu « Demandé → traité » par lot + commande de merge en dernier élément isolé (git merge --no-ff feat/rattrapage-kf-2). Tu ne merges pas.
