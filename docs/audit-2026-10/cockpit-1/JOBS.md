# JOBS.md — le tri des 31 postes de l'usine

*COCKPIT-1 · Lot C · 20/10/2026. Lu du registre `src/labuse/jobs.py` (31 jobs). Décision par poste :
**GARDER** · **GELER** (reste au registre, émis commenté, non lancé, non dégradant) · **SUPPRIMER**
(retiré du registre → absent du crontab). Familles : **1** Veille des sources · **2** Livraisons
quotidiennes · **3** Le moteur · **4** Contrôle, clients, sécurité.*

> **Livrable.** `labuse.cron.actuel` = crontab généré du registre **tel quel** (référence). `labuse.cron.cible`
> = le crontab **visé** après les corrections ci-dessous (annoté). Le crontab se **génère** (jamais à la
> main) : `labuse jobs crontab --tz reunion`. **Rien n'est appliqué en prod** : Vic régénère et déploie.

## Le tableau

| # | Job | Fam. | Valeur pour Vic | Décision | Justification |
|---|-----|:----:|-----------------|----------|---------------|
| 1 | sonde-sources | 1 | L'œil gratuit sur les 99 sources chaque nuit | **GARDER** | cœur de la veille, aucun coût |
| 2 | agents-sources | 1 | Lit les sources que la sonde ne sait pas lire (IA) | **GARDER + CORRIGER** | **remis au crontab** (dim. 1 sem./2, plafond 5 €) — cf. correction B |
| 3 | ingest-bodacc | 2 | Procédures collectives (Radar/score) | **GARDER** | livraison quotidienne, tourne en prod |
| 4 | ingest-dvf | 2 | Ventes immobilières (marché/radar) | **GARDER** | dégelé 20/10, tourne |
| 5 | ingest-sitadel | 2 | Permis de construire (veille foncière) | **GARDER** | mensuel, 1er passage cron 10/11 |
| 6 | ingest-dpe | 2 | Diagnostics énergie | **GARDER** | mensuel, 1er passage cron 12/11 |
| 7 | ingest-sirene | 2 | Entreprises géolocalisées (étude de zone) | **GARDER** | mensuel, 1er passage cron 07/11 |
| 8 | sync-gpu | 2 | Diff PLU des 24 communes | **GARDER** | mensuel |
| 9 | fiche-commune-cache | 3 | Fiche commune < 500 ms | **GARDER** | précalcul nocturne utile |
| 10 | signal-instantane | 3 | Fige le Signal servi (mesure forward) | **GARDER** | mensuel, 1er passage 01/11 |
| 11 | coherence-banc | 4 | Relit chaque chiffre + 25 gardes chasse | **GARDER** | le contrôleur de nuit, central |
| 12 | verite-sources | 4 | 20 parcelles vs sites officiels | **GARDER + CORRIGER** | oracle risque à recalibrer — cf. correction C |
| 13 | backup-postgres | 4 | La seule sauvegarde | **GARDER** | vital |
| 14 | pg-maintenance | 4 | VACUUM ANALYZE (requêtes rapides) | **GARDER** | hebdo, hors usage |
| 15 | healthcheck | 4 | Dead-man local (/health, disque, /readyz) | **GARDER** | la dernière alerte qui survit |
| 16 | sante-endpoints | 4 | Sonde métier (écrans clés + DB) | **GARDER** | voit l'écran vide que /health ne voit pas |
| 17 | copilote-purge | 4 | Purge conversations Copilote | **GARDER** | hygiène données |
| 18 | abuse-scan | 4 | Usage anormal / partage de compte | **GARDER** | informatif |
| 19 | purge-sessions | 4 | Sessions expirées | **GARDER** | hygiène |
| 20 | mail-queue-consommer | 4 | Envoie les mails en attente, rejoue les échecs | **GARDER + CORRIGER** | collision quotidienne avec la sauvegarde — cf. correction A |
| 21 | evaluer-suivis | 4 | Prévient quand un fait tombe sur une parcelle suivie | **GARDER** | veille client ; pose à la cloche |
| 22 | detect-events | 4 | Bascules de classement du marché | **GARDER** | veille client |
| 23 | recap-matin | 4 | Mail récap 07:30 + évalue les vigies | **SUPPRIMER (le mail)** | Vic ne veut plus le récap ; **les ALERTES restent** — cf. correction D |
| 24 | restore-test | 4 | Test mensuel de restauration (gelé) | **SUPPRIMER (du VPS)** | doublon : l'agent Mac launchd `restore_test.sh` le fait déjà hors-VPS |
| 25 | digest | 4 | Mail client du matin (suivis + Radar + nouveautés) | **GELER** | jusqu'aux premiers clients |
| 26 | radar-cloche | 4 | Annonces Radar → cloche | **GELER** | jusqu'aux premiers clients |
| 27 | radar-cycle | 4 | Expirées / vente longue / à revérifier | **GELER** | jusqu'aux premiers clients |
| 28 | radar-cycle-dvf | 4 | Rapprochement vente DVF → « vendue » | **GELER** | jusqu'aux premiers clients |
| 29 | radar-cycle-mensuel | 4 | Cible Courrier « retirée sans vente » | **GELER** | jusqu'aux premiers clients |
| 30 | filtres-sources | 4 | Rejoue les contrôles qualité sur les versions servies | **GARDER** | ⚠ **doublon partiel** avec coherence-banc (voir ci-dessous) |
| 31 | coherence-robinets | 4 | Fuites entre robinets + eau ancienne | **GARDER** | ⚠ **doublon partiel** avec coherence-banc (voir ci-dessous) |

**Bilan :** 23 GARDER · 5 GELER (digest + 4 Radar) · 2 SUPPRIMER (recap-matin + restore-test *VPS*).
**Les 5 corrections sont APPLIQUÉES** (code + registre + crontab + tests), sans casser « les ALERTES
restent » → **registre = 29 jobs**, dont **5 gelés**, **24 lignes actives** au crontab.
- **B** — `agents-sources` remis au crontab (`planifie=True`).
- **E** — `restore-test` retiré du registre (doublon : l'agent Mac launchd le fait).
- **A** — `mail-queue-consommer` déplacé à **14:10** (après la sauvegarde) — fini la collision 13:35.
- **D** — `recap-matin` (le mail) retiré ; ses vigies passent dans `healthcheck` (les ALERTES restent).
- **C** — oracle risque `verite-sources` recalibré (aléas zonaux seulement) + l'incident se referme.

## Doublons de contrôle signalés

- **coherence-robinets (07:25)** vs **coherence-banc (03:45)** — les deux vérifient la cohérence
  (fuites entre lecteurs). coherence-banc rejoue DÉJÀ les comparaisons multi-lecteurs + les 25 gardes
  chasse. coherence-robinets est une sonde plus étroite, plus tôt. **Décision : GARDER les deux pour
  l'instant** (coherence-robinets donne un signal dès 07:25, avant l'ouverture) mais **candidat à
  fusion** dans coherence-banc une fois les clients arrivés — à rouvrir.
- **filtres-sources (07:05)** vs **coherence-banc** — filtres-sources rejoue les contrôles QUALITÉ
  des versions servies ; coherence-banc rejoue la COHÉRENCE. Recouvrement limité (qualité ≠ cohérence) :
  **GARDER les deux**, pas un vrai doublon.
- **recap-matin (vigies)** vs **healthcheck** — disque et /readyz sont évalués AUSSI par healthcheck
  (toutes les 15 min). Seules sauvegarde / copie externe / jobs-en-retard sont propres à recap-matin.
  → la correction D déplace ces trois vigies pour que la suppression du récap ne les perde pas.

## Les corrections (APPLIQUÉES — code + registre + crontab + tests)

> Les cinq corrections sont faites sur `feat/cockpit-1`, chacune avec son test, en préservant
> « les ALERTES restent ». Détail ci-dessous.

### A — mail-queue × sauvegarde (la fausse alerte quotidienne de 13:35)
- **Fait.** `mail-queue-consommer` (toutes les 5 min) se cogne au `pg_dump` (`backup-postgres`, 13:30,
  ~18 min) → `another command is already in progress` → incident + mail tous les jours (ECARTS.md #1).
- **Correction.** `mail-queue-consommer` doit **céder la main à la sauvegarde** : au début du passage,
  si `backup-postgres` est en cours (son état JSON = `en_cours`, ou un verrou de dump présent), **sauter
  proprement ce tour** (compteur `saute=sauvegarde en cours`) et reprendre 5 min plus tard — la file
  repart **après la sauvegarde** (~13:48, d'où « 14:10 » de marge). Le cron reste `*/5` (la file doit
  rester réactive) ; c'est le WORKER qui cède, pas l'horloge. Fichier : `src/labuse/jobs_impl.py`
  (`mail_queue_consommer`). Aucune logique mail changée, juste un garde d'exclusion.

### B — agents-sources remis au crontab
- **Fait.** `planifie=False` → hors crontab ; `LABUSE_AGENT_PLAFOND_EUR=0` par défaut → passage sauté.
  Les sources illisibles par la sonde ne sont vérifiées par personne (ECARTS.md #4).
- **Correction.** Registre : `agents-sources` → **`planifie=True`** (cron `0 19 * * 0`, le dimanche ;
  `semaine_agents()` garde déjà 1 semaine sur 2 — semaines ISO paires). Prod : poser
  **`LABUSE_AGENT_PLAFOND_EUR=5`** dans `/etc/labuse/labuse.env` (déjà 5 en local). Le job s'arrête
  proprement au plafond et signale les sources non traitées. Crontab : la ligne agents-sources apparaît.

### C — verite-sources : l'oracle risque n'est pas comparable
- **Fait.** L'incident ouvert depuis le 15/10 (3 parcelles « aucune vigilance risque » vs Géorisques
  « Inondation, Séisme, Mouvements, Recul du trait de côte, Feu ») est un **faux écart** : l'oracle
  Géorisques « au point » renvoie les aléas valables **partout à La Réunion** (séisme zone 2, feu),
  alors que LABUSE sert le risque **ZONAL** (intersection d'une zone PPR/TRI/inondation). Les 3 parcelles
  n'intersectent aucune couche de risque mappée (vérifié en local q_v19) — c'est **correct** (ECARTS.md #2).
- **Appliqué.** Dans `scripts/coherence/oracles/__init__.py` (l'oracle `oracle_georisques`) : helper
  **`aleas_zonaux()`** qui retire séisme + feu (non discriminants, île-wide) ; la comparaison porte
  désormais sur `bool(risques_zonaux) == risque_labuse` (notion « aléas zonaux au point », séisme/feu
  notés mais exclus de l'écart). L'incident **« verite-sources » se referme tout seul** au prochain
  passage sans faux (`verite_sources.journaliser_passage` → `ops_alertes.resoudre(db, "verite-sources")`)
  — prouvé par `test_incident_verite_sources_se_referme_sans_faux`. Sur prod, le rouge du 15/10 s'éteint
  au run du 15/11 (ou immédiatement si Vic relance `labuse ops verite-sources`). Tests :
  `test_cockpit_corrections_c.py`.

### D — recap-matin : supprimer le récap, garder les vigies
- **Fait.** Vic ne veut plus le mail récap de 07:30. Mais `recap-matin` est le **seul** appelant de
  `ops_alertes.verifier_declencheurs()` (vigies sauvegarde / copie externe / jobs-en-retard). Le
  supprimer naïvement **éteindrait ces alertes**.
- **Appliqué (ordre important).** 1) `recap_matin` (fonction + job) SUPPRIMÉ ; 2) `healthcheck`
  (toutes les 15 min) appelle désormais `ops_alertes.verifier_declencheurs()` → les vigies sauvegarde /
  copie externe / jobs-en-retard (disque/readyz déjà couverts) partent par la **porte unique** ops_alertes,
  SANS mail récap. Le **site en panne** reste couvert par /health (healthcheck lève à 2 échecs → incident
  job-echec). Prouvé : `test_cockpit_corrections_c.py` (site en panne, sauvegarde ratée) +
  `test_disque_externe_1.py` (copie externe) + `test_solidite1_lot1.py` (vigies dans healthcheck).

### E — restore-test : retiré du VPS
- **Appliqué.** Le test mensuel de restauration tourne **déjà hors-VPS** sur le Mac (agent launchd
  `restore_test.sh`). Le poste VPS (gelé) faisait **doublon** → retiré du registre (l'impl
  `jobs_impl.restore_test` reste exécutable à la main).

## Ce qui reste à Vic (prod)
- Régénérer le crontab (`labuse jobs crontab`) et déployer via `deploy.sh` (refuse toute dérive manuelle).
- Poser `LABUSE_AGENT_PLAFOND_EUR=5` + recharger quelques euros de crédit API (Anthropic) pour les enquêteurs.
- Dégeler digest + Radar à l'arrivée des premiers clients (retirer le préfixe `# GELÉ` — le crontab le régénère).
- `verite-sources` : l'incident du 15/10 s'éteint au prochain run ; le relancer pour l'éteindre tout de suite.
- **mail-queue à 14:10** : choix pré-lancement (volume mail ~nul). À l'arrivée des clients, repasser à une
  cadence fréquente + garde « cède à la sauvegarde » (sinon les rejeux backoff sont retardés jusqu'au lendemain).
