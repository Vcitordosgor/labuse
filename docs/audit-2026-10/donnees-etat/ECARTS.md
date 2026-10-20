# ECARTS.md — là où la machine à données ne dit pas tout à fait vrai

*DONNEES-ETAT-1 · 20/10/2026 · lecture seule. Gravité : **prod ment** (un client/Vic voit faux) · **rien ne tourne** (un mécanisme censé marcher ne produit pas) · **dashboard ment** (l'admin voit faux) · **cosmétique**. Chaque écart : étage · symptôme · cause `fichier:ligne` · gravité.*

## Les 5 pires

1. **`mail-queue-consommer` échoue chaque jour à 13:35** *(étage surveillance — ACTIF en prod)*. Le worker de la file mail tombe pendant le dump quotidien (`backup-postgres`, 13:30, ~18 min) : `psycopg.OperationalError: sending query failed: another command is already in progress`. Un **incident est ouvert + un mail part** à 13:40, puis « résolu » à 13:50 — **tous les jours depuis le 14/10** (vérifié : `premier_envoi_at` renseigné 7 jours de suite). → **dashboard/alerte ment** : une alerte quotidienne pour un faux problème use la confiance dans les alertes, et un passage mail est raté chaque jour (rejoué 5 min plus tard). Cause : le job réutilise une connexion DB pendant que le dump tient la base.

2. **Incident `verite-sources` ouvert depuis 5 jours, jamais trié** *(surveillance — prod)*. Le contrôle mensuel du 15/10 a flaggé 3 parcelles (`97411…AS0114`, `97407…AO1663`, `97423…AB0754`) : servi « aucune vigilance risque » vs Géorisques « Inondation, Séisme, Mouvements, Recul du trait de côte, Feu ». → **dashboard ment / à arbitrer** : l'oracle compare le risque **zonal** de LABUSE (intersection d'une zone PPR/TRI/inondation) au **rapport Géorisques « au point »** qui renvoie les aléas valables **partout à La Réunion** (séisme zone 2, feu). Résultat : **écart systématique** pour toute parcelle hors zone de risque mappée. Vérifié : ces 3 parcelles n'intersectent **aucune couche de risque** en local q_v19 non plus. Soit la doctrine zonale est juste (et l'oracle est trop strict → à calibrer), soit il manque un rattachement. Cause : `src/labuse/verite_sources.py` (oracle risques « au point »). **Un incident rouge permanent qui ne sera jamais vert tant que l'oracle n'est pas recalibré.**

3. **Aucune garde de volume (« ±20 % ») à l'ingestion** *(étage ingestion)*. Un connecteur qui livrerait une version tronquée écrirait ce qu'il trouve sans garde. La protection repose **uniquement** sur l'idempotence (UPSERT) et la sauvegarde quotidienne. → **risque latent / rien ne garde** : une ingestion anormale passe en silence ; seul le banc de nuit (coherence-banc) ou verite-sources la rattraperait *a posteriori*. Cause : les connecteurs `src/labuse/ingestion/*.py` — recherche exhaustive : **aucun seuil de volume**. *(Le « guard ±20 % » cité dans SOURCES-MAJ-1 était un garde-fou d'un script ponctuel, pas du code d'ingestion de production.)*

4. **La veille IA des sources (`agents-sources`) est éteinte deux fois** *(détection)*. Les sources que la sonde HTTP ne sait pas lire (SCOT, OCS GE, SIS… — 4 « illisibles » mesurées au Test 1) ne sont vérifiées par **personne** automatiquement. Cause : `planifie=False` (hors crontab, `src/labuse/jobs.py:372`) **ET** plafond `LABUSE_AGENT_PLAFOND_EUR=0` par défaut (passage sauté). → **détection partielle**.

5. **La prod sert un run de retard (q_v18) ; q_v19 n'est pas déployé** *(calcul/prod)*. Le Mac a calculé **et basculé q_v19 en local** (19/10) ; la prod reste à **q_v18** (13/10). Tous les correctifs des branches « poussées non mergées » (rouges-restants, logements-source-unique…) **ne sont pas chez les clients**. → **dépend de Vic** (décision de déployer). Cause : `config/served_manifest.json` prod ≠ local.

## Les autres écarts

| # | Étage | Symptôme | Cause (`fichier:ligne`) | Gravité |
|---|---|---|---|---|
| 6 | À faire / ingestion | La tuile **« Déposer un fichier »** laisse croire à un upload ; au clic elle **navigue vers la source**, aucun upload n'existe (le dépôt réel est un geste CLI). | `circuit_resume.py:398` (commentaire « le dépôt de fichier existe ») + `frontend/.../Circuit.tsx:127` (`gesteAFaire` ne fait que naviguer) | dashboard ment (cosmétique/UX) |
| 7 | Surveillance | **`digest` gelé** (Phase 8) alors que `evaluer-suivis`/`detect-events` tournent : les événements seraient posés à la cloche mais **jamais e-mailés**. | gel volontaire `jobs.py` (digest `gel="Phase 8 Stéphanie"`) | **sans effet actuel** (0 événement en 3 j, pré-lancement, `mail_queue` vide) — à surveiller au lancement |
| 8 | Surveillance | **`restore-test` gelé** (Phase 8) : le test mensuel de restauration de dump **ne tourne pas** en prod. | gel volontaire `jobs.py` | surveillance réduite (mitigé si l'agent Mac launchd `restore_test.sh` est installé) |
| 9 | Ingestion mensuelle | **Sitadel / DPE / SIRENE / signal-instantané jamais tournés via cron** (registre posé le 13/10, après leur date du mois). 1er passage réel en novembre. | `/etc/cron.d/labuse` posé 13/10 ; data présente (injectée à la main) | **non prouvé** (pas un bug, mais exécution cron prod jamais vérifiée) |
| 10 | Bootstrap | **`init-db` ne crée pas `event_log`** (créée par `api.events.ensure_tables`) → un job plante avant d'écrire sur une base neuve. | `init-db` vs `src/labuse/api/events.py` (`ensure_tables`) | cosmétique / dev |
| 11 | Exploitation (Mac) | **`labuse jobs run <job>` refuse toujours sur Mac** : verrou dans `/run/lock` absent de macOS. | `scripts/jobs/run-job.sh:23` (`LOCK_DIR=/run/lock`) | cosmétique / dev (prod Linux non concernée) |
| 12 | Disque (prod) | Disque **84 %** (16 Go libres), remonté de 76 % en une semaine. Un q_v19 déployé ajoutera plusieurs Go. | — (tendance) | à surveiller |

## Ce qui ne dépend que de Vic

| Geste | Pourquoi | Rattache |
|---|---|---|
| **Déployer q_v19 en prod** (`deploy_donnees.sh --run-label q_v19 --residuel-seq 16`) | la prod a un run de retard ; les correctifs locaux ne sont pas chez les clients | écart 5 |
| **Trancher l'incident `verite-sources`** (doctrine risque zonal vs rattachement) | un incident rouge restera permanent tant que l'oracle n'est pas recalibré | écart 2 |
| **Régler la collision `mail-queue` × `backup`** (décaler l'un des deux, ou isoler la connexion du worker) | arrête une fausse alerte quotidienne | écart 1 |
| **Dégeler Phase 8** au lancement (`digest`, `radar-*`, `restore-test`) | la veille client et le test de restauration sont volontairement éteints | écarts 7, 8 |
| **Poser `LABUSE_AGENT_PLAFOND_EUR` + crédit API + planifier `agents-sources`** | sinon la veille IA des sources « illisibles » ne tourne jamais | écart 4 |
| **Laisser tourner novembre** puis vérifier Sitadel/DPE/SIRENE/signal au journal | 1ʳᵉ exécution cron réelle de ces mensuels | écart 9 |
| **Surveiller / agrandir le disque OVH** | tendance montante, un run ajoute des Go | écart 12 |

## Ce qui tient (prouvé, pas déclaré)

- Le **registre de jobs tourne en prod** depuis le 13/10 : 20 jobs distincts ont laissé 3 007 lignes dans `job_runs`, tous `ok` (sauf la collision mail-queue). Le crontab `/etc/cron.d/labuse` est généré du registre, sans dérive.
- Le **banc de nuit mord et passe** : `coherence-banc` 20/10 → 135 écarts connus mais **0 faux-client** ; `chasse_runs` → **25 gardes, 21 ok, 0 écart, 4 skip**, stable depuis le 18/10.
- Les **millésimes servis local/prod concordent** sur ~115 sources ; les seuls écarts sont les tables **quotidiennes** (DVF/BODACC) où la prod est légitimement en avance (prod fait foi).
- **Sauvegardes** : dump quotidien 6,5 Go (4 + 1 hebdo), copie externe chiffrée sur le Mac le 19/10 — les deux marchent.
- La **détection marche** (Test 1 : une vraie nouvelle version amont détectée) ; le **dépôt manuel marche** et **filtre les homonymes métropole** (Test 3 : 75056 rejeté, 974 ingéré).
