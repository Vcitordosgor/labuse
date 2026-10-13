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

## Alternative sans Mac allumé

Si le Mac n'est pas toujours allumé, un service de veille **gratuit** (UptimeRobot, BetterStack free…)
qui sonde `https://app.labuse.immo/readyz` toutes les 5 min et mail Vic au rouge fait le même office.
À régler par Vic côté fournisseur — rien à poser sur le VPS.

> ⚠️ Cette garde **n'est pas déployée automatiquement** : c'est un geste sur le poste de Vic (chemins et
> clé Brevo personnels). Elle est prête ; Vic l'installe quand il veut.
