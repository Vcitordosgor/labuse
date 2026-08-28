# MANDAT — RETOURS VISUELS 2 : APRÈS LE DÉPLOIEMENT
Régime AUTONOME. Commits par lot (V1→V5). RÈGLES COMMUNES. Findings RV2-001→.
Les 13 mandats sont EN LIGNE (deploy du 28/08, commit 7eea236b). Vic a vérifié en production. Ce mandat corrige ce qu'il a relevé. C'est SA liste : chaque point est une décision produit déjà prise — tu exécutes. Captures avant/après par lot visuel.

## V1 — 🔴 LE DÉPÔT DE CAPTURE ÉCHOUE EN PRODUCTION
En prod, déposer une capture avec son lien renvoie : « échec : capture non stockée (répertoire privé inaccessible) — rien enregistré ». Le refus est propre (RD-501 fait son travail, rien de faux en base) mais **la fonction est inutilisable en ligne** — donc tout le Radar l'est.
- Diagnostique : quel chemin est utilisé pour les captures, existe-t-il sur le VPS, quel utilisateur fait tourner l'app, quels sont les droits ? Le chemin doit être configurable et vivre hors du répertoire de l'application (un déploiement ne doit pas l'effacer).
- Le code doit **créer le répertoire s'il manque**, avec les bons droits, au démarrage ou au premier dépôt — et échouer avec un message qui NOMME le chemin fautif, pas un message générique.
- Si une intervention serveur reste nécessaire (création d'un répertoire système, droits, propriétaire), écris la **procédure exacte pour Vic** : les commandes à coller sur le VPS, dans l'ordre. Tu n'as pas accès au VPS, lui l'a.
- Ajoute une **vérification au démarrage** : le répertoire de captures est-il accessible en écriture ? Sinon, alerte visible côté admin (pas un crash), pour que ça se sache AVANT le premier dépôt.
- Cette même famille de défaut peut toucher d'autres écritures disque (exports, PDF, logs applicatifs) : liste-les au rapport, ne les corrige pas d'office.

## V2 — TAXE D'AMÉNAGEMENT : VÉRITÉ ET UTILITÉ
L'outil s'affiche et calcule. Vic demande une revue de fond : les calculs sont-ils justes, l'outil dit-il la vérité, est-il utile tel quel ?
- **Re-vérifie chaque valeur** contre la source officielle en vigueur pour 2026, DOM inclus : valeur forfaitaire par m² (et sa version hors Île-de-France appliquée à La Réunion), abattements 50 % (résidence principale sur les 100 premiers m², logement locatif aidé), forfaits (piscine, panneaux au sol, stationnement extérieur et sa fourchette délibérable, éoliennes), plafonds de taux, part départementale. Cite la source et sa date dans le code et à l'écran.
- **Exonérations manquantes ?** Vérifie les cas de droit commun (locaux agricoles, reconstruction à l'identique, surfaces sous 5 m², etc.) et dis lesquels manquent. Ajoute ceux qui sont incontestables et cadrés ; signale les autres en finding plutôt que d'inventer.
- **Le taux communal est le point faible** : l'outil demande à l'utilisateur de le saisir. Enquête : les taux des 24 communes sont-ils publiés en donnée ouverte exploitable ? Si oui, propose (ne fais pas) l'ingestion en finding chiffré. Si non, garde la saisie manuelle mais rends l'aide plus concrète — où trouver ce taux, sous quel intitulé dans la délibération.
- **Contrôle par cas réels** : construis 3 à 5 cas de test aux résultats calculables à la main (maison simple, maison + piscine + stationnement, logement aidé, projet sous seuil), vérifie chiffre par chiffre, et fige-les en tests. Toute divergence = finding.
- L'écran doit rester ce qu'il est : une estimation indicative, jamais un montant officiel.

## V3 — VEILLE : MÊME PATRON QUE RADAR
Aujourd'hui la Veille ouvre un panneau à DROITE. Elle doit s'ouvrir **à gauche, en catégorie plein écran, comme le Radar** (docs/PIGE/maquette-radar-v2.html pour le patron). Les deux portes (Le foncier / Les annonces) restent, dans ce nouveau cadre.
Dans **Le foncier → Parcelles** :
- Ajoute une **barre de recherche IDU + adresse** (le composant de la barre principale, comme dans l'outil Étude de zone) pour choisir la parcelle à surveiller.
- **Retire « Secteur »** : l'outil secteur a été supprimé, l'entrée n'a plus d'objet. Vérifie qu'aucune veille existante n'est de ce type ; s'il y en a, dis-le au rapport, ne les détruis pas silencieusement.
- Dans **Critères**, expose **les filtres de base de la recherche** (les mêmes que le panneau Filtres de la carte) — pas un jeu réduit inventé pour l'occasion. Liste au rapport ceux que tu exposes.
- **Retire la partie IA** de la création de veille (décision Vic : trop de risque qu'une consigne en langage libre soit mal interprétée). Le back peut rester ; c'est l'entrée qui disparaît.
**Vérification demandée** : les alertes de veille partent-elles bien vers **l'e-mail du compte client** (celui de la licence) ? Trace le chemin de bout en bout et prouve-le par un test. Si l'adresse vient d'ailleurs, c'est un finding rouge.

## V4 — RADAR : LE SÉLECTEUR DE TRI
Le sélecteur « Plus récentes » s'affiche en blanc, hors DA. Aligne-le sur les autres contrôles de l'écran (fond sombre, bordure, texte). Vérifie les autres `<select>` de l'app au passage : liste ceux qui souffrent du même défaut, corrige-les s'ils sont dans le Radar ou la Veille, signale les autres.

## V5 — RECETTE
Cas à prouver : dépôt d'une capture qui aboutit (avec la procédure serveur si nécessaire) · les 3-5 cas de taxe calculés à la main · Veille plein écran à gauche, deux portes, recherche IDU+adresse, critères étendus, sans Secteur ni IA · e-mail de veille = e-mail du compte (test) · sélecteur de tri conforme.
Captures 390 + 1440 avant/après pour V3 et V4, nombre annoncé. Données de test purgées, vérifié SQL.

## FIN
Critères : dépôt de capture fonctionnel ou procédure serveur écrite et testable · valeurs de taxe re-vérifiées et sourcées à la date, cas de test figés · Veille au patron Radar avec les 4 changements demandés · destinataire des alertes prouvé · DA du sélecteur alignée · gardées vertes · tsc/build verts · suite au niveau de la base (prouvé par worktree).
Compte-rendu « Demandé → traité » par lot + commande de merge en dernier élément isolé (git merge --no-ff fix/retours-visuels-2). Tu ne merges pas.
