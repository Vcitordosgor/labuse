# MANDAT FRAICHEUR-PROD-1 — chaque donnée est-elle la dernière version, partout, en prod ?

Branche `audit/fraicheur-prod-1` · worktree `~/Desktop/labuse-fraicheur` · ports 8810 / 6010 · **lecture seule** · Opus.

## Étape 0

Vérifie `pwd`, la branche (`audit/fraicheur-prod-1`) et que l'arbre est propre. Si l'un des trois ne va pas, arrête-toi et signale-le sans rien écrire.

## L'objectif

Vic veut être sûr que, partout où l'app affiche une donnée, c'est la dernière version publiée par le producteur. Il veut cette preuve **en production**, et pour chaque écran.

## Pour chaque source affichée (vitrine de `data_sources`, flux quotidiens compris)

| Colonne | Ce qu'il faut relever |
|---|---|
| A — Producteur | La dernière version publiée. Pars de `source_veille` (sentinelle) et vérifie-la sur la page ou l'API du producteur. |
| B — Base prod | La version réellement présente dans la base du VPS : date max, millésime, nombre de lignes. |
| C — Base Mac | La même chose en local. Le Mac fait foi pour les sources de fond. |
| D — Lecteurs | Chaque écran, PDF, cache, tuile ou fiche commune qui affiche la donnée lit-il bien la version B ? Cherche les caches sans clé de fraîcheur, `mvt_tile_cache`, les tables figées sur un ancien run. |
| E — Tenue à jour | Le job qui la rafraîchit, sa cadence, son dernier succès réel (dans le journal, pas dans l'état déclaré), et s'il est gelé (`# GELÉ` dans `/etc/cron.d/labuse`). |

Chaque source reçoit un verdict, et un seul :
- **À JOUR** : A = B = ce que lisent les lecteurs ;
- **EN RETARD** : le producteur a publié une version plus récente ;
- **DÉCALÉ** : la base est à jour, mais un lecteur affiche encore l'ancienne version ;
- **GELÉ** : le job existe mais il est commenté ;
- **NON SURVEILLÉ** : ni job ni sentinelle ;
- **MAC ≠ PROD** : écart entre les deux bases, en précisant laquelle doit faire foi.

## Cas déjà connus à confirmer

- **DVF.** La dernière publication date du 7 avril 2026 (données jusqu'à décembre 2025). Celle d'octobre est attendue. `ingest-dvf` est gelé en prod. Indique ce qui se passera à la sortie d'octobre, et quel geste fera arriver cette version en prod.
- **Date affichée au client.** La fiche affiche « DVF — jusqu'à déc. 2025 », alors que Vic a décidé le 18/09 qu'aucune date de source n'est montrée au client. Liste tous les endroits côté client qui affichent encore une date ou un millésime de source.

## Livrables (dans `docs/audit-2026-10/FRAICHEUR-PROD-1/`)

1. `FRAICHEUR.csv` : une ligne par source, colonnes A à E, verdict, preuve (requête ou fichier:ligne).
2. `RAPPORT.md` : il **commence** par la courte liste de ce qui n'est pas à jour, avec pour chaque ligne le geste exact qui la corrige et qui doit le faire (Vic ou une session CC).
3. `scripts/coherence/fraicheur.py` : rejoue l'audit en lecture seule. Il sert de verrou : il sort en erreur dès qu'une source est EN RETARD, DÉCALÉ ou GELÉ sans motif déclaré.
4. La ligne de crontab et l'alerte proposées pour faire tourner ce verrou chaque nuit avec le mécanisme d'alerte existant de SOLIDITE-1. **Proposées seulement, pas posées.**

## Interdits

- Aucune écriture en base, ni en prod ni sur le Mac.
- Aucune ingestion, aucun job lancé.
- Ni `deploy.sh` ni `deploy_app.sh`, aucun changement de crontab.
- Aucune clé ni aucun mot de passe dans un fichier ou un commit.
- En prod, charge l'environnement avec `set -a; . /etc/labuse/labuse.env; set +a` et pose `SET statement_timeout = '60s'` sur chaque requête. Pas de requête lourde pendant qu'un job tourne.
- Si une vérification exige de se connecter à l'app en ligne, demande à Vic au lieu de créer un compte.
- Ne corrige rien : tu constates, tu prouves, tu proposes. La correction sera faite par un mandat suivant.
- Reste sur ce périmètre : pas d'audit collatéral.

## Avant de rendre la main

Commit sur la branche, sans merge. Arrête ton API et ton navigateur, puis vérifie avec `lsof -ti :8810` et `lsof -ti :6010` que plus rien n'écoute.
