# CRON-1 · Lot 3 — la garde : deploy.sh génère le crontab du registre

**Branche** `feat/cron-1` · un commit. Aucun job posé en prod.

## Le crontab est GÉNÉRÉ du registre

Nouvelle commande **`labuse jobs crontab [--tz utc|reunion]`** : une ligne par job du registre
(`labuse.jobs.JOBS`, 16 jobs), jamais écrite à la main. En-tête « GÉNÉRÉ — NE PAS ÉDITER ». Le
registre porte les heures en UTC ; `--tz reunion` convertit **+4 h (modulo 24)** — sûr, les jobs
concernés sont quotidiens (aucun décalage de date ni de jour). Extrait (UTC) :

```
# quotidien · 13:30 Réunion · exploitation — Sauvegarde PostgreSQL (dump + rotation, 7 conservés)
30 9 * * *   labuse  sh -c '. /etc/labuse/labuse.env; exec labuse jobs run backup-postgres'
# quotidien · 07:00 Réunion · eau — Sonde des sources amont — détecte une nouvelle version, n'ingère pas
0 3 * * *   labuse  sh -c '. /etc/labuse/labuse.env; exec labuse jobs run sonde-sources'
…
```
`--tz reunion` : `30 9` → `30 13` (backup), `0 3` → `0 7` (sonde), `*/15`/`7,37` intacts (heure `*`).

## deploy.sh — la garde

1. **Verrous** (`labuse circuit verrous --par deploy -w G8`) : un verrou OU une garantie **bloquante**
   cassée → refus. **G8 est NON BLOQUANT** (`-w G8`) : il s'affiche (`⚠ G8`, sources nommées) mais
   n'empêche pas. *Raison :* G8 mesure la **fraîcheur de la veille** (sources hors sonde, agent à 0 €),
   pas la santé du code — déployer n'aggrave jamais ce que G8 signale, et le bloquer empêcherait de
   poser les horloges (dont l'agent du dimanche) qui le feraient passer au vert. Les autres verrous
   restent **bloquants**.
2. **Suite** de tests (`labuse circuit suite`) : bloquante (inchangée).
3. **Pose du crontab généré** (`labuse jobs crontab --tz <serveur> > /etc/cron.d/labuse`) — **AVANT** le
   retrait des legacy → **backup sans trou** (le nouveau backup, à l'horaire exact du legacy, est déjà
   posé quand on retire l'ancien).
4. **Refuse tout écart** : `labuse jobs crontab --tz <serveur> --verifier /etc/cron.d/labuse` — le fichier
   posé DOIT être le registre régénéré, sinon REFUS (un crontab édité à la main est rejeté).
5. **Retrait des legacy** `/etc/cron.d/labuse-*` (hors registre), sauvegardés dans `/root/crons-legacy-…/`
   puis supprimés, **après** la pose du neuf (aucun trou). `cron` rechargé.

## La page Horloge lit le registre

L'endpoint `/admin/cron` (ops.py) rend `labuse.jobs.liste()` — **le registre** : chaque job avec sa
cadence, son heure Réunion, sa **raison** + ce qu'il **touche** (eau/exploitation, ajoutés au lot 3),
et son **dernier passage** (fichier d'état JSON). La page Horloge (`Cron.tsx`) affiche cette liste et se
rafraîchit toutes les 5 s → elle reflète automatiquement le registre (16 jobs) avec le dernier passage
de chacun. (Front non modifié : il lit déjà l'endpoint du registre.)

## Preuves
- `labuse jobs crontab --tz utc|reunion` : 16 lignes générées, backup `30 9`→`30 13`, `--verifier` round-trip identique (aucun écart).
- `labuse circuit verrous -w G8` : **exit 0**, `⚠ G8` en avertissement (15 sources nommées), « tout va bien · 1 en avertissement (G8) » — les 25 autres verts, G8 signalé sans bloquer.
- `tests/test_cron1_lot3.py` (5) : une ligne par job, backup sans trou, conversion tz, écart détecté, deploy.sh porte `-w G8` + génération + `--verifier` + retrait legacy.

`tsc -b` : le front n'est pas modifié (l'Horloge lit déjà l'endpoint du registre) → inchangé. pytest verts.
