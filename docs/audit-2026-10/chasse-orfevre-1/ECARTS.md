# CHASSE-ORFEVRE-1 — ECARTS consolidés

Audit du 18/10/2026, 8 angles (A tables · B sources · C calcul · D temps · E jobs/files · F journaux prod · G front · H code).
Chaque écart est PROUVÉ (requête, fichier:ligne ou capture — le détail est dans `brouillons/ANGLE-X.md`).
Aucune correction appliquée. Dédupliqué : un même phénomène vu par plusieurs angles = UN écart avec ses facettes.

## Compte par gravité

| Gravité | Écarts |
|---|---|
| **BLOQUANT** | **0** |
| **GÊNANT** | **22** (dont **3 ACTIFS en prod** : ORF-01, ORF-02, ORF-03) |
| **À SURVEILLER** | **21** |
| **COSMÉTIQUE** | **9 groupes** (≈ 35 constats élémentaires) |
| **DÉJÀ CONNUS** (comptés à part) | **6** |

Les incidents de prod RÉSOLUS (nuit de migration 06-07/10, chemin Mac, DVF `mutation_id`, churn du 13/10) sont dans `PROD-JOURNAUX.md`, pas ici.

---

## GÊNANTS

### ORF-01 — Prod : `mail-queue-consommer` échoue TOUS les jours à 13:35 (fenêtre pg_dump) — ACTIF
- **Angle** : F (G1). **Preuve** : 9 échecs 1/jour du 14 au 18/10, traceback `_Timeout (300s)` sur `ALTER TABLE mail_queue` puis `another command is already in progress`.
- **Cause** : `mailfile.ensure_tables()` rejoue des DDL (`ALTER TABLE … DROP/ADD CONSTRAINT`, verrou ACCESS EXCLUSIVE) à CHAQUE run de 5 min (`src/labuse/mailfile.py:95-104`) ; le backup 13:30-13:48 (pg_dump, ACCESS SHARE) bloque l'ALTER ; le timeout SIGALRM (`jobs.py:160-186`) interrompt psycopg en plein wait → connexion du pool sale.
- **Impact** : mails du créneau décalés ~10 min ; 1 incident rouge/jour ; parfois l'échec lui-même ne peut pas s'écrire.
- **Correction proposée** : ne jouer les DDL qu'une fois (sentinelle/version de schéma), `lock_timeout` court sur les DDL, et nettoyer la connexion après `_Timeout` (invalidate).

### ORF-02 — Prod : le healthcheck est AVEUGLE (deux mécanismes morts) — ACTIF
- **Angles** : F (G2) + E (E-04). Deux facettes du même constat « la vigie ne voit rien » :
  - **(a) L'alerte disque ne s'écrit jamais** : le disque franchit le seuil 85 % PENDANT la fenêtre pg_dump → `ops_alertes.signaler` rejoue un DDL (`ops_alertes.py:45-56`) bloqué par le dump → `_Timeout (120s)` → l'incident disque n'est jamais enregistré, précisément quand il sonne (1 traceback/jour 13:45, 14→18/10).
  - **(b) Le compteur « 2 échecs consécutifs » ne peut JAMAIS atteindre 2** : `jobs.exec_one` écrase l'état avec `compteurs: {}` AVANT le job (`jobs.py:154-157`) ; `healthcheck` relit CE fichier (`jobs_impl.py:359-360`) → `echecs` vaut toujours 0 ; `if echecs >= 2: raise` (`jobs_impl.py:396-397`) est du code mort → /health peut être HS des heures, job vert, **ping témoin (dead man's switch) vert**.
- **Compensations** : sonde /readyz du même job + readyz-watch launchd du Mac.
- **Correction proposée** : DDL une fois (comme ORF-01) ; passer l'ancien état au job ou persister `echecs_consecutifs` ailleurs.

### ORF-03 — Prod : le VACUUM hebdo n'a JAMAIS été exécuté, job pourtant VERT — ACTIF
- **Angles** : F (G3) + H (H4, cause élucidée). **Preuve** : « VACUUM cannot run inside a transaction block » chaque dimanche (13/09→18/10), job `fin (code 0)`.
- **Cause** : `jobs_impl.py:500-508` — `raw = engine().raw_connection()` renvoie le **proxy de pool SQLAlchemy** ; `raw.autocommit = True` pose l'attribut sur le proxy, PAS sur psycopg → transaction implicite → VACUUM refusé → `except` par table avale → vert. Recherche exhaustive des frères (H) : **aucun autre site** (les 16 autres `autocommit=` sont sur psycopg direct ; `score_v.py:585` passe par `.driver_connection`, la bonne porte).
- **Impact** : les 6 tables chaudes ne reçoivent jamais leur VACUUM ANALYZE (autovacuum = seul filet) ; faux vert permanent.
- **Correction proposée** : `raw.driver_connection.autocommit = True` (ou `execution_options(isolation_level="AUTOCOMMIT")`) + **échec du job si `faites == []`**.

### ORF-04 — La phrase de score « bâti existant sur 19 569 % de la parcelle » est servie telle quelle (61 555 parcelles)
- **Angles** : C (C-01, C-05) + A (A-02). **Preuve** : `score_labuse` run **q_v19 SERVI**, `contributions` JSONB : 232 371 phrases dont **61 555 > 100 %**, 9 714 > 300 %, max **19 569 %** (`97411000AY0015`) ; fabriquée sans borne (`scoring/score_labuse.py:281-283`), affichée verbatim (`ResultsSection.tsx:374-388`), prouvé servi par TestClient.
- **Facettes** : (a) en base, `parcel_residuel_runs` run servi 16 porte 61 555 `taux_emprise_pct` > 100 et 64 475 `pct_potentiel` > 100 (A-02) — sémantiquement explicable (bâti > assiette clippée confetti) ; (b) ces valeurs brutes ATTEIGNENT les JSON servis (`/compare`, `potentiel_transformation`) mais **tous les lecteurs connus les bornent** (`fmtTauxEmprise` « Saturé », `fmtPctConsomme` « > 300 ») — SEULE la phrase pré-cuite au scoring échappe aux formatteurs (C-05).
- **Cause** : texte figé au run → la doctrine « borner à la lecture » (FIX-1) ne le voit jamais.
- **Correction proposée** : borner la phrase dans `score_parcelle` (> 100 % → « au-delà du plafond d'emprise du PLU (saturé) ») — effet au prochain run, ou reprise SQL des libellés du run servi ; à terme documenter le contrat JSON (« peut dépasser 100 »).

### ORF-05 — « Part imperméabilisée : 199,3 % » : parts CoSIA servies sans clamp (11 180 parcelles)
- **Angle** : C (C-02). **Preuve** : `bati.py:212-214` divise les m² CoSIA (raster 20 cm qui déborde le dessin cadastral) par la surface dessin sans clamp ; 11 180 parcelles ≥ 1 part > 100 %, 9 151 dont la somme > 100,5 % ; servi (`97420000BH1222` → 199.3) et affiché brut (`leBien.tsx:199`).
- **Correction proposée** : dénominateur = `max(surface, Σ classes CoSIA)` au service, ou borne 100 avec mention ; ne pas réécrire la table.

### ORF-06 — 1 mutation DVF INVENTÉE toujours servie (vestige du jeu démo)
- **Angle** : B (B-01). **Preuve** : `dvf_mutations` id 33217, Saint-Paul 380 000 €, `date_mutation = 2026-08-10 03:43` (horodatage mur), `mutation_id` et `raw` NULL — seule ligne de la table dans ce cas ; vestige de `ingestion/demo_saint_paul.py`. Connue du code : `dvf_fenetre.py` la contourne (« ligne parasite ») mais tout lecteur hors helper la sert.
- **Correction proposée** : `DELETE FROM dvf_mutations WHERE mutation_id IS NULL;` (1 ligne) puis retirer le contournement.

### ORF-07 — 12 mails de recette DUS dans la file, dont 3 vers un compte supprimé
- **Angles** : A (A-14) + E (E-01). **Preuve** : `mail_queue` 12 `a_rejouer` du 16/10 (mdp_oublie, onboarding, essai, souscription, résiliation, suspension, rétablissement — comptes 18/104/111 ; **104 et 111 n'existent plus**), tous DUS (`prevu_at <= now()`). `consommer()` (`mailfile.py:295-328`) n'a **ni garde d'âge, ni garde d'existence du compte**.
- **Scénario** : on pose `LABUSE_MAIL_REEL=1` (ou une clé Brevo) pour un test → les 12 mails de recette partent réellement.
- **Correction proposée** : purger les 12 lignes ; durcir `consommer()` (annuler toute ligne due depuis > 7 j ou dont le compte n'existe plus).

### ORF-08 — File mail : le FOR UPDATE est relâché AVANT l'envoi → double envoi client possible (théorique)
- **Angle** : E (E-02). **Preuve code** : `mailfile._tenter_depart` (172-236) commit le `SELECT … FOR UPDATE` avant l'appel Brevo ; le commentaire « le FOR UPDATE sérialise, jamais d'envoi en double » (l. 215-216) est **faux** entre processus. Course réelle possible : worker ↔ bouton « rejouer » admin → le client reçoit deux fois le mail.
- **Correction proposée** : transition revendicative `UPDATE … SET etat='parti' WHERE id=:i AND etat IN (…) RETURNING *` (l'état `parti`, aujourd'hui jamais produit — cf. ORF-48 — trouverait son rôle).

### ORF-09 — Dépôt Radar non idempotent : dédup décorative, doublons massifs prouvés
- **Angle** : E (E-03). **Preuve** : `pige/tables.py:331-343` insère dans `event_log` avec une colonne `dedup` remplie mais **jamais vérifiée** ; état réel : 31 couples (dedup, jour) dupliqués jusqu'à **×19** ; `pige_depots` contient **19 fois le même hash de fichier** (`html_ingest.py:487-499`, aucune garde « hash déjà vu ») → re-dépôt = dépôt + événement + allers-retours de prix re-insérés. Clients protégés en aval (radar-cloche passe par `creer_notification`, dédup réelle) ; le journal pilote, lui, est pollué.
- **Correction proposée** : garde hash (ou index unique + ON CONFLICT) avant ré-ingestion ; `journaliser` passant par la vraie dédup.

### ORF-10 — Timeout de job ≠ mort du sous-process : ingestion ORPHELINE qui continue d'écrire (théorique)
- **Angle** : E (E-05). **Preuve code** : `jobs_impl.py:555-564` — `subprocess.run(cmd)` SANS `timeout=` ni kill à l'alarme : quand le SIGALRM du job frappe, l'enfant (`labuse.cli ingest-*`) continue de committer ; le flock du wrapper ne le voit pas → relance manuelle = **deux ingestions concurrentes**. Frère du piège SCORING-6. Concernés : ingest-sirene/sitadel/dpe/dvf/bodacc, abuse-scan, purge-sessions.
- **Correction proposée** : `subprocess.run(..., timeout=job.timeout_s - marge)` + kill du groupe de process dans le `except _Timeout`.

### ORF-11 — 15 009 lignes SIRENE disparues DANS la journée, sans AUCUNE trace
- **Angles** : B (B-02) + E (E-12, cause circonscrite). **Preuve** : 173 524 lignes le 18/10 au matin (angle A) → 158 515 l'après-midi (angle B) ; `job_runs` 1 ligne, `event_log` muet, `ingestion_runs` rien. E-12 PROUVE que ce n'est PAS le job (rebuild transactionnel + `ingested_at DEFAULT now()` intact au 29/08) → **geste manuel/worktree voisin sur la base dev PARTAGÉE**. 0 orphelin aval ; purge des fermés plausible et saine.
- **Gravité** : gênant pour la TRAÇABILITÉ, pas pour la donnée : une table servie perd 8,6 % de ses lignes sans une ligne de journal.
- **Correction proposée** : journaliser toute purge/sync SIRENE (job_runs + compteurs avant/après) ; documenter la politique « actifs seulement » ; recompter `job_runs` en prod (il doit y être dense).

### ORF-12 — Résidus de recette dans la base vivante (comptes, utilisateur sans hash, événements, logs)
- **Angle** : A (A-12, A-13, A-15, A-18). **Preuves** : comptes « recette onb » ×2 **actifs** (ids 61/62) + « compte de test vic » ×2 résiliés ; 1 utilisateur **actif sans hash** (`qa-m23@labuse.test`, id 30) ; 84/89 `evenements_compte` orphelins (comptes de recette supprimés 104/111) ; `consultation_log` : 617 idu orphelins dont idu FORGÉS (`00000000XX0000`, `97416000QA000x`).
- **Correction proposée** : étendre la purge SQL déjà fournie ([GB-TEST]) aux comptes 61/62 + utilisateur 30 + événements orphelins, après accord Vic ; vérifier qu'aucun chemin de login n'accepte un hash vide.

### ORF-13 — Ventes et propriétés PM inaccrochables : 1 128 + 601 idu orphelins (millésimes croisés)
- **Angle** : A (A-05b, A-07). **Preuves** : `dvf_mutations_parcelle` **1 128** id_parcelle absents de `parcels` (ventes récentes sur parcelles filles/remembrées, ex. `97416000HN0670` 2025, 220 775 €) ; `parcelle_personne_morale` **601** idu orphelins (millésime MAJIC 2025 plus frais que le cadastre — SIDR, SOVIPRO…). Ces ventes/propriétés n'apparaissent sur AUCUNE fiche.
- **Correction proposée** : rattacher par filiation (`dfi_filiation`/`cadastre_historique`) ou re-millésimer le cadastre.

### ORF-14 — Piscines « servies » introuvables : 15 sans idu, 6 sans commune
- **Angle** : A (A-10). **Preuve** : `piscines` 380 sans idu (dont **15 statut `servie`**, classe cosia_confirmee), 4 359 sans commune (dont **6 servies**), 28 surfaces ≤ 0 (toutes écartées).
- **Correction proposée** : rejouer le rattachement spatial pour `statut IN ('servie','a_confirmer') AND idu IS NULL` ; backfill commune par ST_Within.

### ORF-15 — `m10_permit_delais` : 7 633 délais négatifs (date_depot fausse, jusqu'à −157 mois)
- **Angle** : A (A-11). **Preuve** : `delai_mois < 0` → 7 633 (tous `valide=false`, ex. PC « 12A » de 2012 avec dépôt 2026) ; + 127 incohérences `date_autorisation < date_depot` avec `valide=true` (quelques jours, delai clampé 0).
- **Contenu** : exclus si les stats filtrent sur `valide` — à vérifier côté consommateur M10.
- **Correction proposée** : recalculer date_depot depuis Sitadel brut, ou NULLer quand autorisation < dépôt de plus d'un mois.

### ORF-16 — `score_labuse_runs.n_parcelles` faux sur 3/3 runs (métadonnée mensongère)
- **Angle** : A (A-01). **Preuve** : q_v19 (SERVI) meta 1 229 vs réel 433 229 ; cause prouvée : `score_labuse_combine.py::persister()` upsert `n_parcelles = len(lignes)` du **dernier lot**.
- **Correction proposée** : recompter en fin de run (`UPDATE … SET n_parcelles=(SELECT count(*) …)`).

### ORF-17 — Les « aujourd'hui » naïfs : sains sur la prod actuelle, faux si la branche serveur-UTC de deploy.sh est empruntée
- **Angle** : D (D-01, D-02, D-03). Trois facettes :
  - **(a) classe entière (D-01)** : 57 `date.today()` + 5 `datetime.now()` nus supposent process = Réunion, alors que `deploy.sh:52-57` ADMET un serveur UTC ;
  - **(b) D-02** : `jobs_impl.py:216` — « dimanche = intégrale banc2 » décidé en fuseau process : sur serveur UTC l'intégrale glisserait à la nuit de lundi Réunion, silencieusement ;
  - **(c) D-03** : `api/dossier.py:36` — borne du quota MENSUEL dossiers en `date.today()` LOCAL alors que les compteurs sont posés au jour RÉUNION (`protection._aujourdhui`) ; docstring fausse ; blocage à tort possible à la bascule de mois sur machine CEST/UTC.
- **Contexte positif prouvé** : base 100 % `timestamptz` (281 colonnes, 0 naïve), session SQL forcée `Indian/Reunion` (`db.py:90-92`), zéro mélange naïf/aware, mails clients en heure Réunion — le piège « computed_at » des audits passés est fermé structurellement.
- **Correction proposée** : retirer la branche UTC de deploy.sh OU migrer les sites métier vers `today_reunion()` ; test de registre « aucun datetime.now()/date.today() nu hors liste blanche ».

### ORF-18 — Deux index manquants prouvés : `sirene_etablissements(siren)` et `dvf_mutations(date_mutation)`
- **Angle** : H (H2.1, H2.2). **Preuves** (dev, indicatif) : fiche propriétaire `WHERE siren=:s` (`app.py:5944` + 2 jointures) sur 158 k lignes SANS index siren → 46 205 seq_scan / 2,44 G tuples ; l'ancre DVF `ANCRE_DVF_SQL` (`dvf_fenetre.py:15`, injectée dans CHAQUE fenêtre de ventes) → **885 231 seq_scan / 11,2 G tuples**, record de la base.
- **Correction proposée** : `CREATE INDEX ix_sirene_etab_siren ON sirene_etablissements(siren)` (+ recréation dans l'ingestion qui DELETE+reload) ; `CREATE INDEX ix_dvf_date_mutation ON dvf_mutations(date_mutation DESC)` ou mémoïser l'ancre. Indice complémentaire : `parcelle_personne_morale(siren)` (coût négligeable, bénéfice modéré).

### ORF-19 — Six familles d'exceptions avalées qui masquent des erreurs de DONNÉES
- **Angle** : H (H4 — 418 sites silencieux au total, la plupart best-effort défendables ; 6 familles dangereuses) :
  1. `faisabilite/zonage.py:478-481` : un JSON `plu_exceptions_effet.json` CORROMPU fait disparaître en silence les **81 exceptions PLU `modifie_calcul=true`** ;
  2. `faisabilite/zonage.py:821-824` : YAML d'hypothèses cassé → défauts dataclass muets ;
  3. `cascade/layers/etage0_ext.py:26-31` : seuils géométrie → repli silencieux ;
  4. `exports/robinet_fiche.py:38-41` (+ `exports/builder.py` ×5) : un extracteur qui PLANTE devient « donnée absente » dans un DOCUMENT CLIENT, sans compteur ;
  5. `registre/moteurs/commune.py:179,204`, `plateforme.py:23,40` : un chiffre déclaré devient muet sans trace ;
  6. motif « job faussement vert » : `pg_maintenance` reste vert si `faites=[]` (cf. ORF-03).
- **Correction proposée** : séparer FileNotFoundError (défendable) de ValueError (lever), compteur/log d'échec des extracteurs, échec si résultat vide.

### ORF-20 — URL `127.0.0.1:8000` codée en dur dans un lien servi
- **Angle** : H (H5). `ingestion/vegetation.py:455` : le lien de validation ortho renvoyé est `http://127.0.0.1:8000/ortho/validation?...` au lieu de `settings.public_base_url` → faux partout sauf en local.

### ORF-21 — `GET/POST /moi/prefs-carte` → 401 sur TOUS les écrans en mode local (dev)
- **Angle** : G (G-01). **Preuve** : 2 erreurs console rouges par chargement sur les 42 écrans SPA ; `onboarding.py:1252` passe par `tenant.compte_ou_401` qui 401-e même quand `/moi` répond `mode:"local"` → la mémoire fond/couches est morte en local et le bruit masque les vraies erreurs en recette.
- **Correction proposée** : en mode local, GET → 200 `{basemap:null}`, POST → 204 ; ou ne pas appeler quand `/moi` dit local.

### ORF-22 — Mairie de Saint-Denis sans email
- **Angle** : A (A-21). La plus grosse commune, seule des 24 sans email dans `mairies` — gênant si le courrier mairie/annuaire s'en sert. Correction : compléter depuis l'annuaire service-public.

---

## À SURVEILLER

### ORF-23 — Plus AUCUNE copie hors-VPS ni test de restauration planifiés (depuis le 14/10)
- **Angle** : F (G7). `backup-offsite` RETIRÉ du cron actif (l'entrée survit dans un `.bak-20261014`), `restore-test` gelé Phase 8 ; le remplacement (disque externe Mac, `feat/sauvegarde-disque`) est un WIP hors main. Sur un disque à 84 %, c'est le point de risque n° 1. **À traiter avant le déploiement.**

### ORF-24 — Disque prod à 84 % (seuil 85) + logs sans rotation
- **Angle** : F (G8). Caddy access.log 81 Mo en UN fichier depuis le 27/08, journald 321 Mo ; le seuil est franchi pendant chaque backup (→ ORF-02a).

### ORF-25 — Mort silencieuse d'un worker uvicorn (unique, 17/10)
- **Angle** : F (G9). `Child process died` sans OOM pendant la génération de tuiles → 4 × 502, respawn 13 s. À garder à l'œil si récidive.

### ORF-26 — Dérive de millésimes : fantômes et rattachements non rejoués
- **Angles** : B (B-03, B-04, B-05) + A (A-16). 266 adresses BAN fantômes à Petite-Île (base > producteur, BAL certifiée) ; 899 parcelles vivantes déjà retirées du PCI courant (dérive d'édition 0,21 %, mécanisme disparues en place) ; 2 043 adresses rattachées à une parcelle DISPARUE (rattachement non rejoué) ; 185 `parcel_signaux_vie` orphelins (calcul du 10/08). Correction : re-sync BAN 97405, rejouer les rattachements après disparitions cadastre, DELETE orphelins au prochain recalcul.

### ORF-27 — DVF : doublons structurels et euros symboliques (source DGFiP)
- **Angle** : A (A-05a, A-05c, A-06). 7 082 groupes de lignes identiques (structure du DVF open-data : un lot par ligne — ne PAS dédupliquer ; compter `distinct id_mutation`) ; 1 351 + 2 289 + 16 ventes ≤ 1 € (euro symbolique réel — vérifié : les médianes secteur sont saines). À exclure des agrégats, pas de la base.

### ORF-28 — 1 593 écarts surface géométrique / contenance fiscale (jusqu'à ×10⁴)
- **Angle** : A (A-19). Ex. `97422000BP2028` : geom 813 m² vs contenance 8 130 000 m² (erreur MAJIC évidente). La géométrie est saine ; c'est la contenance qui déraille. Correction : règle de préférence explicite + marquage `surface_incertaine`.

### ORF-29 — `/filtre` mode B : `modeb_rendement_pct=0` → division par zéro SQL réelle
- **Angle** : C (C-04). Erreur Postgres 22012 rattrapée en 422 générique ; aucune borne sur `FiltreCriteres` (`app.py:1949-1952`) ni sur le cadrage projet, alors que `/parcels/{idu}/mode-b` borne `ge=1, le=20`. Seule voie trouvée où une entrée client atteint un `/` SQL non protégé. Correction : mêmes bornes + `NULLIF`.

### ORF-30 — 2 parcelles GEOMETRYCOLLECTION (polygone + débris LINESTRING)
- **Angle** : C (C-09). `97409000BR0171`, `97411000HP0491` — tout l'aval tient aujourd'hui ; un futur code exigeant un (MULTI)POLYGON strict casserait. Correction : `ST_CollectionExtract(geom, 3)` au prochain chargement.

### ORF-31 — DEUX définitions de « famille de zone » qui divergent (0 déclencheur aujourd'hui)
- **Angle** : C (C-11). La fonction SQL `labuse_zone_famille` (`models.py:1193`) matche `'1AUb'`/`' U1'` → « autre », là où le Python `famille_normalisee` retire le phasage. Le clip d'assiette du résiduel repose sur la SQL. Si une commune publie un jour un subtype GPU hors vocabulaire → assiette fausse EN SILENCE (forme exacte du bug des « 8 communes à name littéral »). Correction : aligner la SQL + verrou « 0 zone famille=autre ».

### ORF-32 — Collation `C` : tri par octets, accents en fin de liste (théorique)
- **Angle** : C (C-14). Aucun déclencheur servi aujourd'hui (référentiels en majuscules sans accents ; « L'Étang-Salé » tombe juste). Toute future donnée triée à initiale É/À sortirait en fin. Correction : `COLLATE "fr-x-icu"` sur les ORDER BY d'affichage ou tri front.

### ORF-33 — `ANNEE_REF` figée à l'import du module bilan
- **Angle** : D (D-06). `faisabilite/bilan.py:29` : un worker démarré en décembre et vivant en janvier calcule âges et fenêtres sur N−1 jusqu'au redémarrage. Correction : fonction `annee_ref()`.

### ORF-34 — Conversion crontab +4 : deux angles morts latents
- **Angle** : D (D-11). `cli.py:4928-4941` ne décale pas dom/dow (tout futur job hebdo/mensuel à heure UTC ≥ 20 tomberait le mauvais jour) et ignore les heures en liste (resteraient en UTC silencieusement). Aucun job actuel touché (vérifié). Correction : assert au registre plutôt que convertir faux.

### ORF-35 — File mail : pas de try/except PAR mail → une ligne poison gèle la file
- **Angle** : E (E-06). `mailfile.py:312-322` : une exception fait échouer le job entier et la même ligne re-plante en tête toutes les 5 min. Atténuation : les transports n'élèvent pas ; l'incident job-echec est visible. Correction : try/except par mail.

### ORF-36 — Courrier : 28 demandes « à déposer » (plus vieille du 25/08) sans relance ; envoi prestataire AVANT l'INSERT
- **Angle** : E (E-07). Toutes les transitions sont des gestes humains, aucune alerte d'ancienneté ; 2 statuts legacy `poste` en base ; `envoyer()` appelle Merci-Facteur avant l'INSERT → crash entre les deux = lettre partie sans trace, re-clic = doublon. Correction : tuile « demandes > N jours », INSERT « en_cours » avant l'appel.

### ORF-37 — Chevauchements de fenêtres de jobs (retard J+1 possible, jamais de perte)
- **Angle** : E (E-11). detect-events (07:04, 15 min) peut finir après le digest (07:15) → bascule rattrapée le lendemain ; coherence-banc (03:45) lit pendant que les cycles Radar (04:00/04:30) écrivent `pige_biens` → faux écart possible un matin, auto-résolu.

### ORF-38 — DPE : `DELETE … <> ALL(gardes)` sans garde de volume
- **Angle** : E (E-13). Si l'amont ADEME tronque une pagination SANS erreur, purge de masse committée (transactionnel donc crash = rollback ; c'est la troncature silencieuse qui est dangereuse — le backup a une garde « rétréci de 30 % », pas la table DPE). Correction : refuser si `len(gardes) < 0,7 × existant`.

### ORF-39 — N+1 à réécrire AVANT la croissance + UPSERT unitaire des runs
- **Angle** : H (H3). `api/events.py:435` (4-5 requêtes PAR parcelle suivie — 14 aujourd'hui, 25 000 req/job à 5 000 suivis) ; `api/modules.py:1709` (60 lookups OR-concat non indexés par requête utilisateur). Batch : UPSERT unitaire ×431 663 dans `residuel.py:314` (regroupable), INSERT par ligne CSV dans permits_sdes (COPY comme `ban_adresses.py`).

### ORF-40 — Labels de runs périmés codés en dur
- **Angle** : H (H5). `verite_terrain.py:232` `run_label='q_v18'` en dur (même famille que le banc2 corrigé dans fix/chasse-invariants-2 non mergé) + bornes de dates figées ; `bascule_gardes.py:35` et `lignee_tete.py:25` défauts `q_v8_calibre` (run d'août). Vérifié au passage : `accueil.py TRAIN_ANNEES=(2017,2023)` est CORRIGÉ sur main ; sentinelle 97410 correctement libellée Saint-Benoît.

### ORF-41 — Poids BODACC servis marqués « non tranché Phase 0 »
- **Angle** : H (H6). `scoring/score_v_constants.py:130-134` : seul TODO qui qualifie une VALEUR SERVIE de provisoire (LJ 35, RJ 30…). À trancher. (Les ~35 autres TODO « étage 1/2 » sont du plan assumé, vérifié non consommé par le score.)

### ORF-42 — npm : 13 vulnérabilités DEV-ONLY (8 high)
- **Angle** : H (H7). Toolchain uniquement (braces, micromatch, chokidar, tailwindcss ≤ 3.4.19, vitest…), rien de servi — `npm audit fix` à la prochaine montée. **Prod : 0 CVE Python (77 pkgs lock) et 0 CVE npm.** 1 CVE torch [ml] locale déjà tracée, jamais en prod.

### ORF-43 — Front : double-clic recherche = 2 requêtes ; omnibox et Copilote sans maxlength
- **Angle** : G (G-11, G-12, G-13). 2 × `/parcels/search` prouvé (GET idempotent, bénin) ; collage de 10 000 caractères accepté. Correction : bouton désactivé pendant la requête (pattern existant), maxlength ~120/raisonnable.

---

## COSMÉTIQUES (groupés)

### ORF-44 — Typographie et formats du front (7 constats)
- **Angle** : G. Apostrophes mélangées `'`/`’` (3 526 vs 498, côte à côte sur le même écran — G-05) ; 0 espace insécable avant `: ; ! ?` sauf 4 `&nbsp;` isolés (G-06) ; « 1 / 1 affichées », « l'envoi de 1 courrier » (G-07) ; « 1289 commits » sans séparateur (G-08) ; téléphone brut « 0648345707 » (G-09) ; slug « etude-faisabilite » affiché (G-10) ; SIREN non groupés (G-14). Corrections : convention `’` + lint, insécables, singuliers, formatteurs.

### ORF-45 — Arrondis et micro-formats de calcul (3 constats)
- **Angle** : C. Parts de zonage commune : 9/24 somment à 99,9/100,1 alors que le docstring du moteur promet 100 % (`registre/moteurs/zonage.py:15/46` — C-03 ; plus fort reste ou corriger la promesse) ; `ratio_pct` plafond 300 en poussière flottante (10 lignes > 300, max 300.0000000064857 — C-06 ; `LEAST`) ; parcelles 0,027 m² servies `"surface_m2": 0` (zéro menteur — C-07).

### ORF-46 — Fuseaux cosmétiques (6 constats)
- **Angle** : D. Trois définitions du « jour » pour la dédup d'alertes (UTC/local/Réunion — D-04) ; « consulté le » process vs « créé le » Réunion sur la même page partenaire (D-05) ; « aujourd'hui » UTC dans score_v/permis (J−1 entre 00:00-04:00 Réunion, inoffensif — D-07) ; mois de facture Stripe en UTC (D-08, défendable) ; front en fuseau navigateur hors 9 écrans admin (D-09, juste pour un client Réunion) ; PDF « généré le » + numéros AAAAMMJJ en date process (D-13).

### ORF-47 — Files et jobs cosmétiques (4 constats)
- **Angle** : E. Verrou mkdir macOS survit au kill -9 (tours sautés à jamais en dev — E-08) ; état `parti` déclaré/compté mais jamais produit (E-09, à recycler cf. ORF-08) ; récap matin / rapport candidat sans dédup jour (rejeu = 2ᵉ mail admin — E-10, seul « NON idempotent » des 30 jobs) ; dédup `creer_notification` sans contrainte unique (fenêtre minuscule — E-14).

### ORF-48 — Données source cosmétiques (5 constats)
- **Angles** : A, B. 10 dates de création SIRENE impossibles (9 futures + 1 an « 0026 » — source INSEE, A-09/B-08) ; 734 permis Sitadel sans géométrie mais tous rattachables par idu (A-20) ; 121 siren `owner_enrichment` périmés (A-22) ; 1 dirigeant de 114 ans (RNE non mis à jour — A-23) ; GASPAR : 1 arrêté CatNat de retard à Saint-Joseph (B-07).

### ORF-49 — Poids mort : colonnes, fonctions, exports
- **Angles** : B (B-06), H (H1). ~20 colonnes chargées jamais lues + 5 colonnes 100 % NULL (dont `parcels.origine` lue-jamais-écrite, `rpls_commune.dpe_classes/pct_passoires` ni remplies ni lues, 3 col × 330 k Arcep) ; backend **41 fonctions mortes sûres** + 98 probables + 13 vars/imports ; front **122 exports jamais importés dont 69 bindings api.ts** = plusieurs features mortes BOUT-EN-BOUT (watch_zones, alertes, financier_questionnaire, scoring_backtest : front mort + endpoint correspondant). ⚠ piège de merge : `filtre_bati.py:52` mort sur main mais modifié par fix/chasse-invariants-2 non mergé.

### ORF-50 — Valeurs en dur cosmétiques
- **Angle** : H (H5). Listes INSEE hors référentiel (run_all, remplissage, sis_projets) ; adresse perso dans le User-Agent RNB (`rnb.py:95`) ; `/tmp` comme état de runs (`LABUSE_RUN_STATE_DIR` défaut — survit mal à un reboot) ; **0 secret en clair** (vérifié).

### ORF-51 — Artefacts dev du front (2 constats)
- **Angle** : G. `/login` local → Swagger page blanche (CSP bloque le CDN — G-03, complète A-07-1 de la recette) ; polices des pages serveur 404 sans dist (G-04).

### ORF-52 — Bruit de prod cosmétique
- **Angle** : F. Burst 599 × 401 `/admin/*` le 11/10 = dashboard admin à session expirée qui re-polle sans redirection login (G11) ; warnings weasyprint HarfBuzz ×85, 502 geopf amont, 1 webhook Stripe rejeté-signature (garde OK) (G12).

---

## DÉJÀ CONNUS (état en base re-signalé, comptés à part)

| # | Écart | État |
|---|---|---|
| K-1 | Hauteurs LiDAR aberrantes (56 faîtage ≤ 0, 2 > 60 m dont 53 401 m, 1 507 égout ≤ 0) | CONNU — bornées à la lecture par `labuse_hauteur_lidar_m` (CHASSE-INVARIANTS-FIX-2, poussé **non mergé** `f9d5fb01` ; la fonction EST en base ici, le précalcul q_v19 l'a utilisée) |
| K-2 | Année de construction 1761 (DPE ADEME, 1 ligne dans `dpe_records` + `parcel_filtre_bati`) | CONNU — « année inconnue » à la lecture (FIX-2) ; table volontairement non réécrite |
| K-3 | 38 lignes `[GB-TEST]` dans `pipeline_entries` (ids 91→132) | CONNU — purge SQL fournie (RECETTE-GENERALE-1), **non exécutée** |
| K-4 | 404 en rafale tuiles ortho « mer » (483 en prod, 36/écran outil Temps) | CONNU/by design (`ortho_proxy.py` répond 404 « Tuile mer ») — amélioration proposée : 204 ou PNG transparent (ORF au sens strict : non) |
| K-5 | GPU Saint-Philippe quasi vide (9 parcelles zonées), verbatims PLU à 0 pour 97409/97413/97417 | CONNU — VERITE-TERRAIN-3 (GPU vide / procédure en cours), pas une anomalie de chargement |
| K-6 | `dvf_mutations_parcelle` vieillit (refresh DVF gelé Phase 8) | CONNU — bug `mutation_id` corrigé dans main (CORRECTIFS-1 E1), cron gelé ; dernières morsures réelles 23 et 30/09 (logs prod) |

Par design, non comptés : 11 342 SIREN « U… » MAJIC (numéros personne quand le SIREN est inconnu, systématiquement filtrés par le code — A-08) ; 6 496 « orphelins » de `cadastre_historique` (c'est l'objet de la table).
