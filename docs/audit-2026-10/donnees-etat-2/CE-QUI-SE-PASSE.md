# Ce qui se passe vraiment — crons, agents, mise à jour des données

Audit **DONNEES-ETAT-2**, lecture seule, le 27/10/2026 (sur le VPS il est déjà le 28/10, 01 h du matin — le VPS vit à l'heure de la Réunion, +4 h ; le Mac est à l'heure de Paris, +1 h).

Ce document raconte, sans jargon, **qui tourne quand**, des deux côtés : le **serveur** (le VPS, la machine qui fait tourner le site) et le **Mac** (le poste de Vic, qui surveille le serveur et ramène les sauvegardes). Tout est constaté sur les vraies machines, pas sur le registre.

---

## Les deux machines, en une phrase chacune

- **Le serveur (VPS)** fait tout le travail de fond : il va chercher les données (BODACC, DVF, DPE…), recalcule, se sauvegarde, se surveille lui-même. Ses tâches sont posées dans un fichier d'horloge (`/etc/cron.d/labuse`).
- **Le Mac** ne calcule rien pour le site. Il fait trois choses : il **rapatrie les sauvegardes** du serveur chaque matin, il **surveille le serveur** toutes les 10 minutes, et il **recopie les sauvegardes sur un disque externe** le dimanche. Ces trois tâches ne sont pas dans un crontab : ce sont des « agents » macOS (launchd).

**Le run servi est le même des deux côtés : `q_v20`** (parcelles 433 229, mêmes versions de score et de signal). Le Mac l'a basculé le 21/10 ; le serveur l'a reçu le 27/10 via DEPLOY-1027. Autrement dit : plus de décalage « un run de retard » comme en ETAT-1 — **local et prod servent le même millésime**.

---

## Une journée type

### Sur le serveur (heures de la Réunion)

La nuit et le petit matin, le serveur enchaîne tout seul :

| Heure | Ce qui tourne | En clair |
|------|---------------|----------|
| 03:00 | fiche-commune-cache | Prépare les fiches des 24 communes pour la journée. |
| 03:30 | copilote-purge | Efface les vieilles conversations du copilote. |
| 03:45 | coherence-banc | Vérifie que chaque donnée raconte la même chose à tous les écrans. |
| 04:00 | (DVF le mardi, VACUUM le dimanche) | Recharge DVF / range la base. |
| 05:00 (mardi) | ingest-dvf | Regarde si Etalab a livré de nouvelles ventes. |
| 06:40 | ingest-bodacc | Récupère les procédures collectives du jour. |
| 07:00 | **sonde-sources** | L'œil de nuit : interroge ~90 sources pour voir si une version plus récente est parue. N'ingère rien, prévient seulement. |
| 07:02–07:05 | evaluer-suivis, detect-events, filtres-sources | Évalue les parcelles suivies, repère les bascules du marché, rejoue les contrôles qualité. |
| 07:25 | coherence-robinets | Cherche les fuites entre « robinets » de données. |
| 08:00 | purge-sessions | Nettoie les connexions expirées. |
| 10:00 | abuse-scan | Détecte les usages anormaux / partages de compte. |
| 13:30 | **backup-postgres** | Sauvegarde complète de la base (≈ 6,9 Go, 4 gardées). |
| toute la journée | healthcheck (×15 min), sante-endpoints (×30 min), mail-queue (×5 min) | Prend le pouls, teste les pages, envoie les mails en attente. |

Le reste de la journée, trois tâches tournent en boucle : **surveillance** (toutes les 15 min), **test des pages** (toutes les 30 min) et **file des mails** (toutes les 5 min).

### Sur le Mac (heures de Paris)

- **07:30** — `pull-backups` : va chercher le dernier dump du serveur et le pose dans `~/labuse-backups/vps`.
- **toutes les 10 min** — `watch-prod` : demande au serveur « tout va bien ? ». Si deux fois de suite la réponse n'est pas franchement « oui », une notification macOS s'affiche et une ligne tombe dans le journal.
- **au branchement du disque externe, et le dimanche 14:30** — `backup-offsite` : recopie la dernière sauvegarde sur le disque externe `MUSIQUE-VIDEO`.

---

## Une semaine type

- **Tous les jours** : la boucle ci-dessus (nuit de récolte + sauvegarde 13:30 + surveillance continue).
- **Mardi 05:00** : DVF — on regarde si une nouvelle livraison de ventes est parue.
- **Dimanche 04:00** : VACUUM — rangement de la base (voir réserve dans ECARTS).
- **Dimanche 23:00, une semaine sur deux** : **agents-sources** — les « enquêteurs IA » devraient lire les sources que la sonde ne sait pas lire. **En réalité ils ne tournent pas** (voir ECARTS n° 2-4).
- **Dimanche 14:30** (Mac) : copie sur disque externe, **si le disque est branché**.

### Une fois par mois

- **le 7** : SIRENE (concurrents) · **le 10** : permis SITADEL · **le 12** : DPE · **le 15** : diff PLU des 24 communes **et** « vérité sources » (20 parcelles tirées au sort, confrontées aux sources officielles) · **le 1er** : instantané du Signal.

---

## Le chemin d'une donnée, de bout en bout (exemple réel : DVF, les ventes)

C'est le trajet qu'une mise à jour de données suit vraiment. Je prends **DVF** (les ventes immobilières d'Etalab), parce que c'est le circuit le plus complet et qu'il a tourné ce matin même.

1. **Détection — la machine.** Chaque mardi 05:00, `ingest-dvf` demande à Etalab « as-tu une livraison plus récente ? » (il compare la date du fichier). **Dernier passage : 27/10 05:00 → « aucune nouvelle livraison, inchangé » (no-op).** Rien à faire, le circuit s'arrête là. En parallèle, la **sonde** fait la même veille chaque nuit sur ~90 sources et, ce 27/10, a trouvé 2 nouveautés (BDNB, zones EnR) — dont BDNB qui **ne couvre pas la Réunion**, donc à ne pas injecter.
2. **La ligne au Tableau de bord — où ça se voit.** Le résultat remonte dans la page *Sources* du site : DVF y est affiché **« à jour »**. S'il y avait du neuf, la source passerait en « nouvelle version » et une cloche admin s'allumerait. **La machine prévient ; elle n'injecte jamais toute seule — Vic décide.**
3. **Injecter — Vic.** Si Vic valide, l'ingestion recharge la table DVF dans la base (c'est le seul moment où la donnée amont entre vraiment).
4. **Calculer — Vic lance, la machine tourne.** Un nouveau *run* de scoring est recalculé sur l'île entière. Exemple réel vécu : le run **`q_v20`** a été **calculé le 21/10 à 11:43** (433 229 parcelles).
5. **Basculer — Vic.** Tant qu'on n'a pas « basculé », le site continue de servir l'ancien run. La bascule réécrit un seul pointeur, `config/served_manifest.json`. Réel : **le Mac a basculé `q_v20` le 21/10 à 20:01** (« RPG en U/AU »).
6. **Propagation dans l'app — automatique.** Dès la bascule, `served_run.txt` est dérivé et toutes les pages lisent le nouveau run. En local, c'était fait le 21/10 au soir.
7. **Envoyer en prod — Vic (déploiement).** Le serveur ne reçoit le nouveau run que lors d'un déploiement. Réel : **le serveur a reçu `q_v20` le 27/10 à 14:41 via DEPLOY-1027** — soit **6 jours après le local**. C'est normal (on ne pousse pas en prod à chaud), mais ça explique pourquoi « local » a toujours un peu d'avance sur « prod » entre deux déploiements.

**Où ça casse aujourd'hui, sur ce chemin ?** Nulle part pour DVF (no-op). Mais l'étape « détection » a un trou : les sources que la sonde **ne sait pas lire** devaient être relues par les enquêteurs IA le dimanche — et ces enquêteurs ne tournent pas (voir ECARTS). Donc pour une poignée de sources, l'étape 1 n'a personne.

---

## État des lieux, côte à côte

| | **Serveur (VPS)** | **Mac (local)** |
|---|---|---|
| Run servi | **q_v20** (poussé le 27/10) | **q_v20** (basculé le 21/10) |
| Détail manifeste | scoring q_v20 · cascade q_v19_sources · division q_v19 · résiduel seq 17 | identique |
| Millésime | 433 229 parcelles | **identique** |
| Horloge des tâches | `/etc/cron.d/labuse` (29 lignes) | 3 agents launchd |
| Tâches qui tournent bien | la quasi-totalité (voir journal `job_runs`) | pull-backups, watch-prod |
| Ce qui cloche | voir **ECARTS.md** | sentinelle en alerte continue, copie externe figée |

Le détail chiffré des problèmes, du plus grave au moins grave, est dans **ECARTS.md**.
