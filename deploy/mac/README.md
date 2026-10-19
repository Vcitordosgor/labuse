# Agents launchd du Mac — installation HORS DU BUREAU (`install_agents.sh`)

> ⚠️ **Ne jamais ranger les scripts d'agent sous `~/Desktop`.** macOS (TCC) interdit à launchd d'y
> LIRE un fichier : l'agent échoue alors en **code 126 « Operation not permitted »**. On installe
> les scripts dans **`~/.labuse/ops`** (non protégé) et on repointe les `.plist` vers ce dossier.

Les 3 agents de sauvegarde/veille (`com.labuse.backup-offsite`, `immo.labuse.pull-backups`,
`immo.labuse.watch-prod`) s'installent/réparent en une commande, **depuis un clone à jour de `main`
(pas depuis un checkout en HEAD détachée)** :

```sh
bash deploy/mac/install_agents.sh
```

Le script : copie les 3 scripts (et leurs dépendances) dans `~/.labuse/ops`, vérifie qu'aucun ne lit
plus `~/Desktop`, installe les `.plist` dans `~/Library/LaunchAgents` (en substituant `/Users/VIC` →
`$HOME`), décharge/recharge chaque agent, puis les `kickstart` et pointe vers leurs journaux. Rejouable
à volonté. Dépendances externes (hors `~/Desktop`) : `pg_restore` ≥ majeure du VPS dans
`$HOME/miniforge3/envs/labusedb/bin`, alias ssh `labuse-vps`, secrets watch-prod dans
`~/labuse-backups/M7_SECRETS.txt`. Les scripts sont du bash autonome : **aucun venv de projet requis**.
Le VPS n'est jamais modifié (lecture des dumps par ssh uniquement).

Retirer un agent : `launchctl bootout gui/$(id -u)/<label>` puis supprimer son `.plist`.

### Seconde garde macOS pour la copie sur disque externe (Accès complet au disque)

Sortir les scripts de `~/Desktop` lève le `126` de **lecture** du script. Mais **écrire sur un volume
amovible** (`/Volumes/…`) depuis un contexte launchd réclame en plus **« Accès complet au disque »**
pour l'interpréteur `/bin/bash` — sinon `rsync` échoue en `mkstemp … Operation not permitted`. C'est un
réglage macOS **qui ne peut pas être posé en ligne de commande** ; il se fait une fois, à la main :

> Réglages Système ▸ Confidentialité et sécurité ▸ **Accès complet au disque** ▸ `+` → ajouter **`/bin/bash`**
> (dans le sélecteur : `⌘⇧.` pour voir les fichiers cachés, `⌘⇧G` puis coller `/bin/bash`).
> Volet direct : `open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"`

Puis relancer la copie : `launchctl kickstart -k gui/$(id -u)/com.labuse.backup-offsite`.
`pull-backups` et `watch-prod` n'écrivent que sous `~/` : eux n'ont besoin de rien de plus.

---

# Garde externe `/readyz` (SOLIDITE-1 Lot 1.5)

**Pourquoi.** L'alerte in-app (mail Brevo + cloche) part _depuis le VPS_. Si le VPS tombe en entier,
elle ne peut plus partir. Cette garde tourne **sur le Mac de Vic**, hors du VPS : toutes les 15 min elle
sonde `https://app.labuse.immo/readyz` et prévient Vic si le serveur ne répond plus — même mort complète.

Elle ne remplace pas l'alerte in-app (qui, elle, voit le détail : quel job, quelle source). Elle est le
dernier filet : « le serveur répond-il, oui ou non ».

## Ce que ça fait

- Sonde `/readyz` (HTTP 200 attendu).
- Alerte au **passage en panne** (après 2 échecs consécutifs, pour amortir un redémarrage), puis **un
  rappel par jour** tant que c'est en panne, et un mail **« rétabli »** au retour. Pas de déluge.
- Canaux : mail **Brevo** (si la clé est posée) + **notification macOS** + une ligne dans
  `~/.labuse/readyz_watch.log`.

## Installation (sur le Mac)

1. Éditer `com.labuse.readyz.plist` :
   - remplacer `/Users/VIC/...` par le vrai chemin du dépôt et du home ;
   - renseigner `LABUSE_BREVO_API_KEY` (clé SMTP/API Brevo de Vic) et `LABUSE_ALERT_TO`. Laisser la clé
     vide = notification macOS + log seuls (pas de mail).
2. Copier et charger :
   ```sh
   cp deploy/mac/com.labuse.readyz.plist ~/Library/LaunchAgents/
   launchctl load  ~/Library/LaunchAgents/com.labuse.readyz.plist
   launchctl start com.labuse.readyz        # lance tout de suite (sinon attend 15 min)
   ```
3. Vérifier : `tail -f ~/.labuse/readyz_watch.log` doit montrer une ligne `OK (200)`.

Pour retirer : `launchctl unload ~/Library/LaunchAgents/com.labuse.readyz.plist`.

## Test de restauration mensuel (SOLIDITE-1 Lot 3.3)

**Pourquoi.** Une sauvegarde jamais restaurée n'en est pas une. Le VPS n'a pas la place de restaurer
45 Go (6,6 Go libres) — le Mac, si. `restore_test.sh` rapatrie le dernier dump, le restaure dans une base
jetable locale (`labuse_restore_test`, supprimée à la fin), compare les comptages des tables clés à la prod,
et alerte au moindre écart. Le job VPS `restore-test`, lui, ne fait plus qu'un contrôle de LISIBILITÉ
(`pg_restore --list`, sans restaurer) — safe sur le VPS plein.

Installation :
```sh
# éditer com.labuse.restore-test.plist (chemins /Users/VIC, clé Brevo), puis :
cp deploy/mac/com.labuse.restore-test.plist ~/Library/LaunchAgents/
launchctl load  ~/Library/LaunchAgents/com.labuse.restore-test.plist
launchctl start com.labuse.restore-test       # pour tester tout de suite
tail -f ~/.labuse/restore_test.log
```
Pré-requis : `pg_restore`/`psql` ≥ la majeure PostgreSQL du VPS (sinon le dump est refusé), et l'accès SSH
`labuse-vps` (le même que la garde externe).

## Copie des sauvegardes hors du VPS, sur le disque externe (DISQUE-EXTERNE-1)

**Pourquoi.** Un VPS perdu (feu, rançongiciel) ne doit pas emporter les sauvegardes. On a abandonné la
copie vers un stockage objet chiffré (ancien `deploy/scripts/backup_offsite.sh`, retiré) au profit d'une
copie sur le **disque externe de Vic** — volume `MUSIQUE-VIDEO`, dossier dédié `LABUSE-SAUVEGARDES`
(non chiffré, choix assumé). Le script tourne **sur le Mac** : il tire le dernier dump du VPS par ssh
(sens tiré), vérifie l'**empreinte sha256** (calculée sur le VPS) et la **lisibilité** (`pg_restore
--list`), puis range le dump. Jamais d'écrasement sans vérification réussie (copie dans un `.part`,
vérification, puis renommage atomique).

- **Déclencheurs** (plist) : à **chaque montage de volume** (`StartOnMount` — le script ne fait rien si
  ce n'est pas le bon disque) **et** chaque **dimanche 14:30** s'il est branché.
- **Rétention** : les **8 dernières hebdomadaires + 1 par mois sur 12 mois**, sur le seul dossier dédié.
- **Jamais** le volume Time Machine « SAUVEGARDE HD » (garde dure en tête de script, non surchargeable).
- Après chaque copie vérifiée, le Mac **inscrit la date sur le VPS** (`/var/backups/labuse/.copie-externe.json`,
  via `sudo -n -u labuse tee`). Le **récap du matin** affiche cette date, et une alerte **« branche le
  disque »** part si elle a **plus de 10 jours** (vigie `ops_alertes`).

Installation : `bash deploy/mac/install_agents.sh` (voir en tête de ce README — il installe ce
`.plist` dans `~/Library/LaunchAgents`, copie le script dans `~/.labuse/ops`, et le `kickstart`).
Pré-requis : `pg_restore` ≥ la majeure PostgreSQL du VPS, l'accès ssh `labuse-vps`, et le disque branché.
Pour retirer : `launchctl bootout gui/$(id -u)/com.labuse.backup-offsite`.

## Alternative sans Mac allumé

Si le Mac n'est pas toujours allumé, un service de veille **gratuit** (UptimeRobot, BetterStack free…)
qui sonde `https://app.labuse.immo/readyz` toutes les 5 min et mail Vic au rouge fait le même office.
À régler par Vic côté fournisseur — rien à poser sur le VPS.

> ⚠️ Cette garde **n'est pas déployée automatiquement** : c'est un geste sur le poste de Vic (chemins et
> clé Brevo personnels). Elle est prête ; Vic l'installe quand il veut.
