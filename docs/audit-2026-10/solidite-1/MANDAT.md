# MANDAT-SOLIDITE-1 — une app qui ne casse plus en silence

Rédigé le 13/10/2026. Modèle : Opus. Branche `fix/solidite-1` depuis main, worktree `~/Desktop/labuse-solidite`, ports 8760/5960. À lancer **après** le §8bis du déploiement q_v18 (crons réparés).

## Pourquoi

La semaine du 07/10 a montré que le danger n'est pas le code mais le silence : sauvegarde cassée 6 jours, 19 tâches mortes depuis le 07/10, couches en double, disque à 96 %, sans qu'aucune alerte ne parte. Ce mandat rend chaque panne visible le jour même, garde la donnée juste dans le temps, et rend les mises à jour répétables.

## Règles

- **Étape 0** : `pwd`, branche, arbre propre. Sinon STOP.
- Code et tests sur la branche, pas de merge. Tout geste sur le VPS (cron, fichier, script posé) : **montré à Vic avant, vérifié après**, un point d'arrêt par lot.
- Tables clients jamais touchées. Aucun run, aucune bascule.
- Tout CLI en prod source `/etc/labuse/labuse.env` et appelle `labuse` par son chemin complet.
- Les identifiants externes (stockage, téléphone) sont fournis par Vic : ne rien créer à sa place, préparer et attendre.
- Un commit par lot.

## Lot 1 — plus aucune panne silencieuse

1.1 Chaque job du registre écrit son résultat (début, fin, statut, durée, erreur) dans une table `job_runs` et sa sortie dans `/var/log/labuse/jobs/<job>.log` (rotation 12 mois). Fin de `MAILTO` vers le vide.
1.2 Une seule fonction d'alerte : mail Brevo à Vic (adresse dans `labuse.env`) + cloche admin. Déclencheurs : job en échec · job en retard (dernier succès plus vieux que 1,5 × sa cadence) · disque > 85 % · `/readyz` faux · sauvegarde absente ou plus petite de 30 % que la précédente.
1.3 Pas de déluge : une alerte par incident, puis un rappel par jour tant qu'il n'est pas résolu, et un mail « résolu ».
1.4 Un récapitulatif chaque matin à 7 h 30 (Réunion), un seul mail : tout vert en une ligne, ou la liste de ce qui ne va pas.
1.5 Garde externe : un contrôle hors du VPS (le Mac via `launchd`, ou un service de veille gratuit) appelle `/readyz` toutes les 15 min, pour être alerté même si le serveur entier tombe.
1.6 Preuve : provoquer un échec (job de test qui lève) et un retard simulé, montrer les deux mails reçus, puis le mail « résolu ».

## Lot 2 — le banc chaque nuit, sur la prod

2.1 Le job `coherence-banc` joue chaque nuit `scripts.coherence.chasse_donnees` (les 25 gardes) **contre la prod**, plus le banc de cohérence existant. Résultat stocké, historique consultable dans le dashboard (page Données).
2.2 Au premier écart : alerte du Lot 1 avec la garde, la parcelle témoin et l'écart.
2.3 Toute nouvelle garde ajoutée au banc entre automatiquement dans le job.
2.4 Preuve : un passage de nuit réel, sortie jointe.

## Lot 3 — le disque et les sauvegardes

3.1 Inventaire de l'occupation du VPS (base table par table, sauvegardes, journaux, front, `/tmp`) et prévision à 3 mois. Proposition chiffrée pour agrandir le disque chez l'hébergeur (Vic décide et commande).
3.2 Copie des sauvegardes **hors du VPS**, chiffrée (clé détenue par Vic) : script prêt pour un stockage objet (Vic fournit le compte et les identifiants), rétention 4 quotidiennes locales + 8 hebdomadaires distantes. Tant que le compte n'existe pas : le script s'arrête proprement et l'alerte le dit.
3.3 Test de restauration **mensuel** sur le Mac (jamais sur le disque du VPS) : rapatrier la dernière sauvegarde, la restaurer dans une base de test, comparer les comptages des tables clés à la prod, rapport + alerte si écart. Remplace le `restore-test` commenté.
3.4 Nettoyage planifié : schéma `sauvegarde_20261006` (après accord de Vic), runs morts au-delà du servi, du précédent et d'un secours.

## Lot 4 — une routine de mise à jour toujours pareille

4.1 `deploy/scripts/deploy_donnees.sh` : un seul chemin pour envoyer des données du Mac vers la prod, qui enchaîne toujours les mêmes gardes : sauvegarde prod vérifiée → place disque → copie en `--no-owner --no-acl` (propriétaire labuse) → comptages et sommes de contrôle Mac = prod par table → intersections fraîches avant toute bascule → bascule en dernier → contrôle du manifeste → `/readyz` → banc. Il s'arrête au premier écart.
4.2 `deploy_app.sh` refuse de partir si le manifeste local ne correspond pas à des données présentes en prod, et contrôle le manifeste prod après chaque envoi.
4.3 Un contrôle de parité Mac = prod lançable à tout moment (`labuse parite`), tables clés et comptages par commune, sortie lisible.
4.4 `docs/EXPLOITATION.md` : la routine en une page (détection → clic de Vic → calcul sur le Mac → contrôle → petit déploiement), avec les leçons de q_v18 (manifeste, propriétaires, adresses depuis le Mac, verrou anti-rebuild des intersections, chemin complet des crons).

## Lot 5 — la vérité face aux sources, chaque mois

5.1 Job mensuel : 20 parcelles tirées au hasard (stratifiées par commune et par cas difficile : bizone, zone rouge, nouvelle, contenance ≠ dessin), comparées aux sources officielles en ligne (cadastre IGN, GPU, Géorisques, DVF, SIRENE).
5.2 Rapport stocké et visible dans le dashboard ; tout écart = alerte du Lot 1, avec la parcelle et les deux valeurs.
5.3 Respect des quotas des API, aucun écrit en base hors du rapport.

## Livrables

`docs/audit-2026-10/solidite-1/RAPPORT.md` : ce qui est posé, les preuves (mails reçus, passages de nuit, test de restauration), ce qui attend une action de Vic (disque, compte de stockage, clé de chiffrement).
