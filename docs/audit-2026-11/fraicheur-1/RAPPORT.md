# FRAICHEUR-1 — Chaque donnée est-elle à jour ?

**Mandat** : audit lecture seule de la fraîcheur des sources servies aux clients.
**Branche** `audit/fraicheur-1` · worktree `~/Desktop/labuse-fraicheur` · base de code `7d4f9f0ec`.
**Prod** : lue en ssh (`labuse-vps`), lecture seule, requêtes légères (`statement_timeout=30 s`, index) — un calcul lourd (`calcul-nuit`, lignée q_v21) tournait pendant l'audit. **Aucune écriture, aucune correction.**
**Date** : 10/11/2026 (heure serveur = Indian/Reunion, UTC+4).

---

## 0. Résumé exécutif

- **99 sources** en vitrine client (`data_sources` filtrées par `WHERE_AFFICHEES`). La sonde quotidienne `sonde-sources` a tourné ce matin (07:00) : **85 sondées, 1 nouvelle version, 3 injoignables, 1 illisible, 0 rappel en retard** (de son propre point de vue).
- **La sonde se trompe par omission sur 3 sources majeures** : DVF, SITADEL et le recensement (RP). Elles passent « à jour » côté LABUSE alors que l'amont a publié plus récent. La sonde regarde le mauvais signal (Last-Modified d'un fichier legacy, `last_update` d'un dataset dont le job d'ingestion ne tourne pas, mtime au lieu du millésime).
- **5 vrais retards amont**, classés §4 : **DVF** (sert jusqu'au 31/12/2025, amont au 30/06/2026), **SITADEL** (figé au 31/08, le job d'ingestion n'a **jamais** tourné), **recensement RP** (sert RP2022, RP2023 publié), **INPI RNE / dirigeants** (batch unique du 05/07/2026, amont quotidien, ni job ni sentinelle — outil Successions), **OSM/Overpass** (3 couches, sonde injoignable depuis 16-18 passages).
- **Le Radar va BIEN** : contrairement à la prémisse du mandat (« dernière collecte 27/10 »), la collecte automatique tourne **chaque soir** jusqu'au **09/11 23:45** (voir §3.2). Le 27/10 marquait la fin d'un **trou réel du 07 au 27/10**, désormais résorbé.
- **Artefact du jour** : un déploiement ce matin (crontab réécrit à 05:08, env à 05:45) a **sauté les crons de 00:00 à 05:08**, dont la livraison DVF du mardi (05:00) et le passage SITADEL mensuel (04:30 le 10). Ce sont des manques d'un jour, pas une panne — sauf SITADEL qui n'avait de toute façon jamais tourné.
- **9 couches carte** dépassent leur fenêtre de revue de 24 mois (mécanisme `echeances_couches`, admin « à vérifier ») : pour l'essentiel des référentiels lents/archivés, faible impact client — sauf DVF qui s'y trouve à juste titre.

---

## 1. Méthode & ce que signifient les colonnes

- **Cadence amont** : rythme réel de publication du producteur (vérifié en ligne pour les sources principales).
- **MAJ en prod** : date lue dans les **données** (`data_sources.source_horizon_at` = millésime de la donnée, `last_sync_at` = journal d'ingestion) ou dans le **journal des jobs** (`job_runs`, `/var/lib/labuse/state/jobs/*.json`), jamais dans la configuration. « vu » = dernier signal amont lu par la sentinelle (`source_veille.dernier_vu`) ce matin.
- **Millésime amont (en ligne)** : dernier millésime réellement publié par le producteur, vérifié sur ses pages (URL de preuve dans les notes). Vérifié en ligne pour les **sources principales** ; pour la longue traîne (§5) on reporte le millésime servi.
- **Mécanisme** : tâche planifiée (nom + dernière **exécution réussie** dans `job_runs`), sentinelle (méthode de sonde), ou manuel/rappel.
- **Verdict** : à jour / en retard / jamais automatisé.

Registre des jobs : `src/labuse/jobs.py` (crontab généré, `/etc/cron.d/labuse`, heures Réunion). Fraîcheur : `etats_sources.py` (état à la lecture), `echeances_couches.py` (fenêtre de revue 24 mois des couches carte), `millesime_source.py` (composition du millésime affiché).

---

## 2. Tableau — les sources principales (vérifiées en ligne)

| Source | Cadence amont réelle | MAJ en prod | Dernier millésime amont (vérifié en ligne) | Mécanisme (+ dernière exéc. réussie) | Verdict |
|---|---|---|---|---|---|
| **Cadastre PCI** (API Carto / Parcellaire Express) | Trimestrielle (mars/juin/sept/déc) | `last_sync` 11/10/2026 ; sonde vu 09/09/2026 | Édition **2026-09** (PCI Express) | Sonde `api` quotidienne (ok 10/11) + ingestion structurante (classe B, clic). Pas de job dédié planifié | **À jour** (édition 2026-09 ingérée le 11/10) |
| **PLU / GPU** (API Carto GPU + prescriptions/zonages témoin) | Continue, **par document** (pas de millésime) | Sondes témoin ok 10/11 ; `sync-gpu` dernière réussite **15/10/2026** | Continu. 974 : 24 communes, 21 publiées, **86,9 % surface**, 0 RNU | Job `sync-gpu` mensuel (le 15) + sondes témoin quotidiennes | **À jour** (continu par nature) |
| **DVF / valeurs foncières** | **Semestrielle** (avr. → 31/12 N-1 ; **oct. → 30/06 N**) | `last_sync` 20/10/2026 ; horizon **31/12/2025** ; sonde vu « 2025 » | Millésime **2026-06** (S1 2026, jusqu'au 30/06/2026), publié **oct. 2026** | Job `ingest-dvf` hebdo (mardi) — dernière réussite **03/11** (no-op) ; détection par Last-Modified | **EN RETARD** — sert jusqu'au 31/12/2025 ; voir §4.1 |
| **SITADEL** (permis) | **Mensuelle** (~4 sem. après le mois) | `last_sync` 13/10/2026 ; horizon **31/08/2026** ; sonde DiDo vu `last_update` 30/10/2026 | Dernier mois publié = **septembre 2026** (publié 28/10) | Sonde `api` DiDo (ok 10/11) **mais** job `ingest-sitadel` mensuel (le 10) **JAMAIS exécuté** | **EN RETARD** — voir §3.1 |
| **SIRENE** établissements géolocalisés | Mensuelle (stock au 1er) | `last_sync` 07/11/2026 ; millésime **2026-10** ; sonde vu 21/10 | Stock **01/11/2026** (registre au 31/10) ; GéoSirene = oct. 2026 | Job `ingest-sirene` mensuel (le 7) — dernière réussite **07/11** | **À jour** |
| **DGFiP — parcelles des personnes morales** | Annuelle (situation 1er janvier) | `last_sync` 12/07/2026 ; millésime 2019→**2025** (1/1/2025) | Millésime **2025** (livré 12/01/2026) | Sonde `entete` (hash) quotidienne + ingestion structurante (classe B) | **À jour** (prochain = 2026, janv. 2027) |
| **INPI RNE — dirigeants** (outil Successions) | **Quotidienne** (flux différentiel entreprises) | `pm_dirigeants` : **batch unique 05/07/2026** (27 146 lignes, 9 337 SIREN) ; source touchée 06/07 | Flux **quotidien** (stock + CMC), accès token/SFTP | **Manuel** (login live API INPI, `INPI_API_*`) — **aucun job, aucune sentinelle** | **EN RETARD / jamais automatisé** — voir §3.3 |
| **INSEE — Population légale** | Annuelle (déc., en vigueur 1/1) | Millésime **2023** ; `last_sync` 04/11/2026 | **2023** en vigueur (2024 = **année blanche** ; 2025 attendu déc. 2026) | Agent IA bimensuel (dernière passe réelle **01/11**) + `api` geo.api.gouv | **À jour** |
| **INSEE RP — fichier détail Logements (EGOUL)** | Annuelle décalée (~juin N+2.5) | « publié 16/10/2025 » ; sonde vu 12/02/2025 | **RP2023** — fichiers détail publiés **25/06/2026** | Sonde `api` (lit le mtime du dataset, **pas** le millésime) ; ingestion manuelle | **EN RETARD** (RP2023 dispo) — §4.3 |
| **INSEE RP — bases IRIS** (logement, population) | Annuelle décalée (automne N+2.5) | « parution 16/10/2025 » ; sonde vu « 2022 » | **RP2023** — bases IRIS publiées **10/11/2026** | Sonde `page` (lit l'année, pas le millésime servi) ; ingestion manuelle | **EN RETARD** (RP2023 dispo) — §4.3 |
| **BPE INSEE** (équipements) | Annuelle (paru H2 N+1) | Millésime **2025** ; `last_sync` 14/09/2026 ; sonde vu 30/03 | **BPE 2025** (paru 09/07/2026) | Sonde `api` quotidienne + ingestion | **À jour** (prod sur insee.fr 2025, pas le miroir data.gouv resté à 2023) |
| **Filosofi INSEE** (revenus, carreaux 200 m) | Annuelle, ~3-4 ans de décalage | Millésime **2021** | **2021** (y.c. carroyées 200 m, parues 12/02/2026) | Sonde `api` quotidienne + ingestion | **À jour** (2022 sauté, 2023 = rupture méthodo incomparable) |
| **PPR / aléas** (DEAL Réunion) | Continue, par arrêté communal (GASPAR) | Sonde témoin ok 10/11 ; « PPR/PPRL approuvés 2011–2026 » | Continu (ex. Saint-André PPRN approuvé **16/04/2026**) | Sonde `temoin` (hash) quotidienne | **À jour** (continu par nature) |
| **LiDAR HD — MNH 50 cm** (IGN) | Acquisition unique ; **974 survolé 2023, aucun nouveau vol 974 programmé** | « Survol 11/08–11/10/2023 » ; sonde vu 13/03/2025 | **2023** = dernier **et seul** pour 974 (plan IGN 2026) | Sonde `temoin` quotidienne | **À jour** (millésime courant = dernier disponible) |
| **BD ORTHO 20 cm** (IGN) | ~3 ans/département ; **974 volé 2025**, diffusion 2026 | Millésime **2025** ; sonde `ortho` **illisible** (1 échec) | 974 = vol **2025** (diffusion 2026) + Pléiades 2025/2026 | Sonde méthode `ortho` (GetCapabilities WMTS) — **illisible** aujourd'hui | Donnée **à jour** (2025) ; **sentinelle en panne** — §4.6 |
| **BD TOPO V3** (IGN) | Trimestrielle (mars/juin/sept/déc) | `last_sync` 26/09/2026 ; « édition non enregistrée » | Édition **2026-09** | Sonde `api` quotidienne + ingestion | **À jour** |
| **RGE ALTI** (IGN, altimétrie) | **Gelée nationalement depuis 2024** (remplacée par MNT LiDAR HD) | « édition non enregistrée » ; pas d'horizon | RGE ALTI 2.0, production **arrêtée en 2024** | Sonde `api` quotidienne | **À jour / figé** — amont ne bouge plus ; le MNT LiDAR 2023 est plus frais |
| **DPE ADEME** (logements existants) | Mensuelle (train) | `ingest-dpe` dernière réussite **02/11** ; sonde vu 04/11 | Continu (train mensuel) | Job `ingest-dpe` mensuel (le 12) | **À jour** |
| **BODACC** (procédures collectives) | Continue (~5 j/sem, J+1 matin) | `ingest-bodacc` **10/11 06:40 ok** ; sonde vu 10/11 | Live, `dateparution` **10/11/2026** | Job `ingest-bodacc` quotidien (06:40) — **27/27 réussites** | **À jour** |
| **Zonage ABC** (DHUP, arrêté) | Irrégulière (arrêtés modificatifs) | « arrêté 23/06/2026 en vigueur, 24/24 » | **Arrêté du 23/06/2026** (JORF 25/06) = dernier | Sonde `api` quotidienne | **À jour** (dernier arrêté ; refonte substantielle = 05/09/2025) |
| **Radar** (pige d'annonces) | Collecte quotidienne (extension nav., le soir) | `pige_passes` dernière **09/11 23:45** (source `auto`) ; `last_sync` 09/11 | n/a (collecte propre) | Dépôt **automatique par l'extension** (pas de cron d'ingestion) + jobs `radar-cycle*` de vieillissement | **À jour** — voir §3.2 |

---

## 3. Les deux cas à détailler

### 3.1 SITADEL — millésime 31/08, et une sentinelle qui ne sert à rien

**Ce que le mandat soupçonnait (« aucune sentinelle ») est à nuancer, et c'est pire :** une sentinelle **existe bel et bien** — `source_veille` méthode `api`, URL `data.statistiques.developpement-durable.gouv.fr/dido/api/v1/datasets/6513f0189d7d312c80ec5b5b`, sélecteur `last_update`, cadence 24 h. Elle a tourné ce matin (10/11 07:00, statut `ok`) et a bien lu la dernière mise à jour du dataset DiDo : **30/10/2026**.

**Le problème est en aval :** le job d'ingestion **`ingest-sitadel` n'a JAMAIS tourné.** Zéro ligne dans `job_runs` depuis le début de l'historique (13/10/2026), aucun fichier d'état `/var/lib/labuse/state/jobs/ingest-sitadel.json`. La donnée servie (`source_horizon_at = 31/08/2026`, `last_sync_at = 13/10/2026`) a été posée **autrement** (ingestion ponctuelle / candidat golden lors d'un déploiement), pas par le poste mensuel.

**Conséquence :**
- L'amont SDES a publié les permis **à fin septembre 2026** (note de conjoncture du 28/10/2026, 31 428 logements autorisés) ; la prod sert **août 2026**.
- La sentinelle voit `last_update = 30/10` mais reste `ok` (pas « nouvelle version ») : elle compare au dernier signal **notifié**, pas à ce que LABUSE a réellement **ingéré**. Elle ne peut donc pas déclencher le rattrapage, et le job qui le ferait ne tourne pas.
- Le passage mensuel d'aujourd'hui (le 10, 04:30) a de surcroît été **sauté par le déploiement du matin** (crontab réécrit à 05:08). Prochaine occasion : le 10/12.

**Verdict : EN RETARD.** Donnée figée au 31/08 ; au moins une livraison amont (sept.) non ingérée ; le job mensuel n'a jamais fonctionné dans la vie du registre. *(Réserve honnête : la base détaillée SITADEL retarde structurellement de ~1,5-2 mois sur la note agrégée ; « jusqu'à août » pourrait être le dernier mois **consolidé**. Mais cela n'explique pas qu'`ingest-sitadel` n'ait jamais tourné.)*

### 3.2 Radar — la collecte tourne chaque soir (prémisse du mandat périmée)

**Le mandat posait : « dernière collecte 27/10 ; l'extension tourne-t-elle le soir ? ». Réponse mesurée : OUI, elle tourne chaque soir.**

`pige_passes` (source `auto`) montre une cadence nocturne régulière, trois passes par jour (`confirmation` à 00:00, puis `nouvelles` + `relecture` ~21:00-23:45) :

| Jour | Passes | Nouvelles | MAJ | Source |
|---|---|---|---|---|
| 09/11 | 3 | 36 | 1238 | auto |
| 08/11 | 3 | 32 | 1242 | auto |
| 07/11 | 3 | 40 | 1282 | auto |
| 06/11 | 1 | 31 | 39 | auto |
| 05/11 | 3 | 31 | 1243 | auto |
| 04/11 | 3 | 57 | 1217 | auto |
| 03/11 | 3 | 41 | 1233 | auto |
| 02/11 | 5 | 436 | 2088 | auto + manuel |
| 30/10 | 1 | 27 | 8 | auto |
| 29/10 | 2 | 95 | 5 | auto |
| 28/10 | 2 | 33 | 1367 | auto + manuel |
| **06/10 → 28/10** | — | — | — | **TROU (aucune passe)** |

- **Dernière passe : 09/11 23:45** (relecture 20 pages). `pige_annonces` : max `date_saisie` = `index_date` = **09/11/2026**, 1 306 annonces actives. Aujourd'hui 10/11, pas encore de passe à l'heure de l'audit (19:40) — les passes tombent le soir, ce n'est pas anormal.
- **Le « 27/10 » du mandat** correspond à la **fin d'un trou réel du 07 au 27/10** (21 jours sans collecte auto, reprise le 28/10). Ce trou est **résorbé** : collecte continue depuis.
- **Ce dont la collecte a besoin :** l'**extension navigateur** côté Mac/poste, qui pousse les captures via l'API (`LABUSE_RADAR_TOKEN`). Il n'y a **aucun cron d'ingestion** côté serveur (choix assumé CRON-1 : « Radar — pas de job », traitement déclenché au dépôt). Le serveur ne fait que **vieillir** les annonces la nuit (`radar-cycle` 04:00, `radar-cycle-dvf` 04:30, `radar-cycle-mensuel` le 1er).
- **Échéance de dépôt :** `source_veille` méthode `rappel`, `cadence_attendue_jours = 7` ; verrou G8 tolère 14 j (`LABUSE_RADAR_DEPOT_ECHEANCE_JOURS`). Dernier dépôt 09/11 < 14 j → **à jour** du point de vue du verrou.

**Un bémol à surveiller :** les jobs `radar-cycle*` (vieillissement) sont lacunaires — `radar-cycle` : dernière réussite **08/11** (11 exécutions seulement sur ~28 jours), les passages du 09 et du 10/11 manquent (10/11 sauté par le déploiement). Ça ne touche pas la **collecte** mais le **cycle de vie** (annonces expirées/en-vente-longue). À noter, pas bloquant.

**Verdict Radar : à jour** (collecte nocturne active, dernier dépôt 09/11). Le trou 07-27/10 est de l'histoire ; l'extension tourne.

### 3.3 INPI RNE (dirigeants) — un batch unique de juillet, ni job ni sentinelle

**Rôle :** le Registre National des Entreprises de l'INPI alimente l'outil **Successions** (dirigeants, âge via `date_naissance`, dates de prise de fonction, rapprochement avec les parcelles de personnes morales). Table servie : **`pm_dirigeants`**.

**Cadence amont (vérifiée en ligne) :** l'INPI publie le RNE **quotidiennement** pour les entreprises — un **flux différentiel quotidien** (créations/modifications/cessations, dont les représentants) qui s'ajoute à un stock rejouable. Accès par **token** (`POST /api/sso/login`) sur l'API, ou **SFTP** pour le bulk (le HTTPS de masse n'existe pas). Pas de SLA chiffré dépôt→open data. *(À distinguer de l'API publique `recherche-entreprises.api.gouv.fr`, agrégée Sirene+RNE, rafraîchie plutôt à l'hebdomadaire.)*

**Dernière ingestion réelle en prod (lue dans les données) :** **UN SEUL batch, le 05/07/2026.** `pm_dirigeants` = 27 146 lignes / 9 337 SIREN, toutes avec `ingested_at = 05/07/2026` (min = max). La ligne `data_sources` a été touchée le **06/07/2026 13:46** (`last_sync_at`), statut `connecte`, `mode_remplissage = sans_millesime`, notes : *« ✓ login live 05/07/2026 (schéma vérifié, siren 913037362 SCI ALOE)… SFTP abandonné = firewall IP »*. **Rien n'a bougé depuis ~4 mois.**

**Mécanisme :** **100 % manuel.** 
- **Aucune tâche planifiée** : rien dans le registre `jobs.py`, **zéro ligne** dans `job_runs` pour `inpi`/`dirigeant`/`rne`/`succession`. 
- **Aucune sentinelle** : pas de ligne `source_veille` pour cette source (confirmé) → la sonde quotidienne `sonde-sources` **ne la regarde pas** ; elle figure parmi les sources « sans contrôle » du verrou G8 (cf. CRON-1-LOT2). L'ingestion se fait à la main, par login live sur l'API INPI (identifiants `INPI_API_*` en env), quand un humain la relance.

**Sur le « au 06/10/2026 » affiché dans l'outil :** je ne trouve **aucune date du 06/10** sur l'enregistrement de la source — `last_sync_at` = 06/07/2026, `fraicheur_calcule_at` = 19/09/2026, pas de millésime, pas d'échéance (`sans_echeance`). La donnée en base date du **05/07/2026** et n'a pas changé. Si l'écran Successions montre « au 06/10/2026 », **cette date ne correspond à aucune ingestion ni vérification stockée** pour INPI RNE — à vérifier côté affichage de l'outil (date possiblement calculée/codée, non adossée au journal d'ingestion). *(Le chemin live « Recherche d'entreprises » (DINUM, RNE/Sirene via api.gouv.fr) est, lui, sondé `temoin` et vert au 10/11 — mais c'est la recherche unitaire d'une entreprise, pas le stock des dirigeants.)*

**Verdict : EN RETARD et jamais automatisé.** Amont quotidien ; prod figée sur un batch du 05/07/2026 ; ni job, ni sentinelle pour le détecter. Impact : l'outil Successions travaille sur des dirigeants/âges/fonctions vieux de ~4 mois (décès, changements de gérant, radiations non vus), sans aucune alerte de péremption.

---

## 4. Sources en retard ou manuelles — classées par impact client

### 4.1 — DVF · **EN RETARD** · impact **ÉLEVÉ** (marché, prix secteur, Signal, Radar↔ventes)
L'amont a publié **millésime 2026-06** (S1 2026, mutations jusqu'au **30/06/2026**) en octobre 2026, avec un **changement de format Etalab** (un fichier par période pour toute la France : `full-2026-s1`, au lieu des fichiers par département/année). **La prod sert encore jusqu'au 31/12/2025.** Preuve : le dernier vrai rechargement (`ingest-dvf`, 20/10 01:16) a tiré les fichiers **par année 2021→2025**, `Last-Modified "Mon, 18 May 2026"` ; depuis, chaque passage hebdo est un **no-op** (« Last-Modified inchangés ») car le détecteur interroge l'**ancienne arborescence**, inchangée depuis mai. Le nouveau `full-2026-s1` n'est jamais vu. La sentinelle `vu = "2025"` confirme qu'elle ne voit que l'année 2025. Le mécanisme `echeances_couches` l'a d'ailleurs flaggé « à vérifier » (`prochain_millesime_at = 01/10/2026`, dépassé). *(La livraison du mardi 10/11 a aussi été sautée par le déploiement, mais ce n'est pas la cause : même en tournant, elle ferait no-op sur le format legacy.)*

### 4.2 — SITADEL · **EN RETARD** · impact **MOYEN-ÉLEVÉ** (veille foncière, candidat golden)
Voir §3.1. Données figées au 31/08/2026 ; job d'ingestion jamais exécuté ; sentinelle aveugle au décalage.

### 4.3 — Recensement RP (2 sources : EGOUL + bases IRIS) · **EN RETARD** · impact **MOYEN** (fiche commune, contexte logement/population)
L'amont INSEE a publié **RP2023** : fichiers détail le **25/06/2026**, bases infra-communales/IRIS le **10/11/2026**. La prod sert **RP2022** (« publié 16/10/2025 »). Les sentinelles lisent le **mtime du dataset** (EGOUL vu 12/02/2025) ou l'**année** (IRIS vu « 2022 »), jamais le millésime réellement servi → elles ne déclenchent pas. *(« INSEE RP Logement 2023 » existe aussi en source `rappel` manuelle — à distinguer ; voir 4.6.)*

### 4.4 — INPI RNE (dirigeants) · **EN RETARD / jamais automatisé** · impact **MOYEN** (outil Successions)
Voir §3.3. Batch unique du 05/07/2026 (27 146 lignes), amont **quotidien**, ni job ni sentinelle. L'outil Successions raisonne sur des dirigeants/âges/fonctions de ~4 mois. La date « au 06/10/2026 » affichée ne correspond à aucune ingestion/vérification stockée en prod.

### 4.5 — OSM / Overpass (3 couches : TCSP voies bus, pôles d'échange/téléphérique, parkings APER) · **sonde EN PANNE** · impact **MOYEN** (transport, stationnement loi APER)
Sentinelle `temoin` **injoignable** avec **16 à 18 échecs consécutifs** (Overpass inaccessible depuis le serveur). La donnée servie est une **extraction figée** (TCSP vu 05/09/2026, parkings vu 11/07/2026) : elle ne tombe pas, mais elle **ne se rafraîchit plus** et personne n'est alerté d'un amont qui aurait bougé. Overpass est « non sondable par nature » (interrogée en direct, pas de snapshot comparable — cf. CRON-1), mais 16-18 échecs méritent qu'on tranche : soit on accepte l'extraction figée (et on retire la sonde), soit on répare l'accès Overpass.

### 4.6 — BD ORTHO · donnée à jour, **sentinelle de fraîcheur en panne** · impact **FAIBLE** (monitoring aveugle)
La donnée est la bonne (vol 2025, dernier dispo pour 974). Mais la sonde méthode `ortho` (GetCapabilities WMTS) est **illisible** aujourd'hui (`dernier_statut = illisible`, 1 échec). On ne verrait pas passer une édition 2026. À réparer, sans urgence donnée.

### 4.7 — Sources manuelles (méthode `rappel`, jamais automatisées par construction) · impact variable
Chargées à la main, sans job d'ingestion. Toutes **dans leur cadence** du point de vue de LABUSE (`rappels_en_retard = 0`), mais **jamais automatisées** :

| Source | Cadence attendue | Dernier « au » | Impact client | Note |
|---|---|---|---|---|
| **Coût de construction** (EPTB SDES + choix LABUSE) | 365 j | — | Moyen (estimation, score) | Choix de promotion LABUSE 2300-2800 €/m² ; EPTB 2024 contexte |
| **INSEE RP Logement 2023** (rappel) | 365 j | 08/07/2026 | Faible-moyen | Doublonne partiellement RP ci-dessus |
| **NPNRU** (DEAL/ANCT) | 365 j | 08/07/2026 | Faible | Périmètres rénovation urbaine |
| **PLH des 5 EPCI** | 365 j | 08/07/2026 | Faible | Extraction documentaire |
| **PVGIS** (CE/JRC) | 365 j | 23/08/2026 | Faible | Interrogée **en direct** au build solaire (snapshot non applicable) |
| **RTAA DOM** (Légifrance) | 365 j | 08/07/2026 | Faible | Réglementaire statique (CCH) |
| **VRD / assainissement (SPANC)** | 91 j | — | Faible | Aucune URL de publication amont renseignée |

Plus **3 sources sans aucune surveillance** (méthode nulle) : **EduGéo 1980** (archive figée, OK), **INPI RNE (dirigeants)** (manuel non surveillé — **traité en détail §3.3 / §4.4**), **OpenStreetMap/Overpass** (entrée générique, live non sondable).

### 4.8 — Couches carte dépassant la fenêtre de revue 24 mois (`echeances_couches`, admin « à vérifier ») · impact **FAIBLE** (hors DVF)
Signalées à l'admin/John, **jamais au client** (décision PAGE-SOURCES-1). Ce sont pour l'essentiel des référentiels lents ou quasi-figés :

| Couche | Millésime donnée | Échéance dépassée | Nature |
|---|---|---|---|
| Ravines — domaine public fluvial (DEAL) | 21/08/2006 | 2008 | Arrêté 2006, quasi-figé |
| GéoLittoral — érosion côtière (Cerema) | 2018 | 2020 | Lent |
| Zones humides — inventaires DEAL | 2019 | 2020 | Inventaires partiels |
| EDF Réunion — lignes HTA | 02/2020 | 2022 | Géométrie 2020 (≠ publication 2025) |
| Parc National de La Réunion | 2021 | 2023 | Lent |
| DEAL — cartes de bruit stratégiques (CBS) | 2022 | 2024 | Échéance 5 (2027) |
| OCS GE (IGN) — occupation du sol | 2022 | 2024 | Édition 2022 (+ diff 2025) |
| Classement sonore ITT (Cerema) | 12/2023 | 11/2025 | Arrêtés déc. 2023 |
| **DVF** | 31/12/2025 | 01/10/2026 | **Vrai retard — voir §4.1** |

---

## 5. Les autres sources servies (longue traîne) — vue compacte

Toutes sondées ce matin (10/11) statut `ok` sauf mention. Millésime = celui servi en prod (vérification en ligne concentrée sur les principales du §2).

**Sondées `api` quotidiennement, verdict à jour :** ABF/Monuments historiques · ACV/PVD/ORT (DGALN, 19 communes 974) · BAN PLUS (maj 27/08, moisson 13/09) · BD NYME lieux-dits · BD ORTHO IRC (vu 04/11) · Base Adresse Nationale · Cartofriches (Cerema) · Classement sonore ITT *(voir §4.7)* · CoSIA 2025 · Conso ENAF 2021-2024 · Contours IRIS 2024 · DFI filiation DGFiP (409 623 liens, vu 09/11) · Fibre Arcep 2026_T1 · Forêts publiques ONF · Géorisques (vu 07/11) · Géorisques ICPE · IGN BD CARTO V5 · Inventaire SRU (DHUP) · Loyers DHUP carte 2025 · Loyers OLL 2024 · Parc National 2021 *(§4.7)* · QPV 2024 · RNIC copropriétés (Anah) · RPG agricoles 2024 · RPLS 01/01/2025 · Sudocuh (état 31/12/2024) · Taux TF REI DGFiP 2025 (24/24) · Trafic RN Région · Transport GTFS PAN (7 réseaux, maj → 10/10/2026) · ZNIEFF (maj 29/08/2025) · data.regionreunion Potentiel foncier.

**Sondées `entete` (hash fichier) quotidiennement, à jour :** 50 pas géométriques (cadastre 1877, figé) · GéoLittoral *(§4.7)* · EDF HTA *(§4.7)* · Espaces protégés complémentaires (Ramsar/sites, 13/09/2026) · Géorisques SIS (4 SIS 974) · Ravines DPF *(§4.7)* · Systèmes d'endiguement (EDD déc. 2024) · Zones humides DEAL *(§4.7)*.

**Sondées `temoin` quotidiennement, à jour :** AZI/TRI inondation (GASPAR 07/09) · Annuaire administration (24 mairies) · CatNat GASPAR · GPU DPU / emplacements réservés / EBC / zonages assainissement · GéoMCE (vu 26/09) · Géorisques CASIAS (453 sites) · Géorisques cavités / mouvements de terrain / sites pollués (vu 07/11) · OCS GE *(§4.7)* · PEB bruit aérien (Roland-Garros) · RNB (flux continu, 13/09) · Recherche d'entreprises DINUM · SCOT GPU (vu 26/09) · SUP assiettes GPU (vu 09/11) · Taxe aménagement DGFiP (24/24, 08/09) · **Zones exclues EnR sauf toiture (OFB/APER)** → **`nouvelle_version` détectée** (injectée par `injection-nuit` le 09/11 ; ré-signalée 10/11 — l'amont OFB a probablement rebougé ; sera reprise à la prochaine injection de nuit).
**Injoignables (voir §4.5) :** OSM transport · Parkings OSM · TCSP OSM.

**Agent IA bimensuel (dernière passe réelle 01/11 ; 08/11 = semaine « off »), à jour :** Communes contours (ADMIN EXPRESS, seed) · Contraintes EnR près habitations (APER) · DEAL CBS bruit *(§4.7)* · FRR ex-ZRR (Légifrance) · INPN/patrinat espaces protégés · SCAN 50 (1950, archive) · ZFANG (décret 29/05/2026). *Plafond agent `LABUSE_AGENT_PLAFOND_EUR` — à vérifier qu'il est > 0 en prod, sinon ces 7 sources ne sont vérifiées par personne (verrou G8).*

---

## 6. Annexe — faits d'exploitation du jour (10/11/2026)

- **Déploiement ce matin** : `/opt/labuse/app` 02:05, crontab `/etc/cron.d/labuse` **05:08**, `/etc/labuse/labuse.env` **05:45**. **Aucun cron n'a tourné entre 00:00 et 05:08** (confirmé : premier job du jour à 05:15). Sauts du jour : `injection-nuit` (01:00), `calcul-nuit` (02:00), `radar-cycle` (04:00), `radar-cycle-dvf` (04:30), **`ingest-sitadel`** (04:30 le 10), **`ingest-dvf`** (05:00 mardi). Reprise normale ensuite (bodacc 06:40 ok, sonde 07:00 ok, etc.).
- **Calcul lourd en cours** pendant l'audit : `calcul-nuit` (lignée q_v21), processus `multiprocessing` actifs, démarré ~14-35 min avant l'audit. `verite-permanente` a échoué 2× tôt (05:23, 05:34) puis est repassée verte (05:37) — transitoire de déploiement.
- **`job_runs`** : historique depuis 13/10/2026, 11 949 lignes. `ingest-bodacc` 27/27, `sonde-sources` 27/27, `ingest-sitadel` **0/0**, `calcul-nuit` 5 ok / 2 échecs (03/11, 06/11), `sync-gpu` 1 (15/10, mensuel), `ingest-dpe` 1 (02/11).

## 7. Ce que la sonde ne voit pas (thème transversal)

Les trois retards amont les plus importants (**DVF, SITADEL, RP**) passent tous « à jour » dans le décompte LABUSE. Raison commune : **la sentinelle lit un signal qui n'est pas le millésime réellement servi** —
- DVF : Last-Modified d'une **arborescence legacy** inchangée (le nouveau format Etalab par période n'est pas regardé) ;
- SITADEL : `last_update` du dataset DiDo **comparé au dernier notifié**, pas à ce qui est ingéré — et le job d'ingestion ne tourne pas ;
- RP : **mtime/année** du dataset, jamais le millésime (RP2022 vs RP2023).

Le mécanisme `etats_sources` projette d'ailleurs **« à jour » côté client pour tout ce qui n'est pas explicitement `nouvelle_version`** (règle R2) : un retard non détecté par la sonde est donc **invisible** au client comme à l'admin. C'est la faille de fraîcheur à corriger en priorité (hors mandat lecture seule : aucune correction ici).

---

*Fin du rapport. Lecture seule — aucune donnée ni configuration prod modifiée.*
