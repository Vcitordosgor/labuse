# GRANDE REVUE AVANT MISE EN LIGNE — RAPPORT

> Mandat GRANDE REVUE (27/08/2026). Branche `audit/grande-revue` (depuis `19f92b86`, qui inclut la
> bascule du run servi `q_v10_m129` → **`q_v11_m137`**, re-run des 24 communes de ce midi : 431 663
> parcelles, canari/score-v2/build-mvt/purge vérifiés). Doctrine intacte : Sourcé/Estimé/Absent,
> moteur unique, jamais de faux positif — **aucun chiffre servi ne change dans ce mandat** (seule
> exception encadrée : le re-run conditionnel R10).
>
> Gravités : 🔴 bloquant / faille · 🟠 durcissement recommandé · 🟡 dette / constat documenté.
> Findings RV-001→. Base de vérification empirique : `labuse` (prod locale) en lecture + `labuse_test`
> pour les comptes de test `[REVUE-TEST]` (purgés en fin).

---
## R1 — FRAÎCHEUR DES 58 SOURCES

Méthode : inventaire `data_sources` (58 affichées) × vérification en ligne des millésimes chez les
producteurs (data.gouv, SDES, ADEME, cadastre.data.gouv, IGN, Sudocuh, DILA, INPI, BRGM) × croisement
avec les commandes d'ingestion CLI et les crons installés. Le run servi `q_v11_m137` (re-run de ce
midi) a consommé l'état actuel de la base.

### Sources cadencées / à flux vivant (vérifiées en ligne)

| Source | Ingéré | Disponible amont (vérifié) | Retard | Commande | Cascade |
|--------|--------|---------------------------|--------|----------|---------|
| **géo-DVF Etalab** | 2021–2025 (horizon déc. 2025) | `latest/csv` = 2021→2025, horizon oct. 2025 · prochain oct. 2026 | **Non** | `refresh-dvf` (cron dvf) | oui (prix) |
| **Cadastre PCI (DGFiP)** | « latest » | juin 2026 publié 01/07 · `latest` suit | **Non** | API Carto (live) | oui (parcelles) |
| **SITADEL (SDES)** | 2026-06 | fiche MàJ 25/08 ; période exacte non affichée en ligne | Inconnu | `ingest-permits` (cron sitadel) | non (événements) |
| **DPE ADEME** | horizon 03/07/2026, hebdo | flux continu vivant (data.ademe.fr) | **Non** | `ingest-dpe` (cron dpe) | non |
| **BAN** | horizon 11/07/2026 | flux quotidien vivant | **Non** | `ingest-ban` (cron ban) | non |
| **BODACC (DILA)** | horizon 02/07/2026 | flux quotidien vivant | **Non** | `ingest-bodacc` (cron bodacc) | non (features) |
| **INPI RNE** | 06/07/2026 | flux quotidien vivant | **Non** | `ingest-inpi-rne` | non (features PM) |
| **Géorisques (BRGM)** | 13/08/2026 | flux vivant par base (API) | **Non** | `ingest-georisques` | oui (spatial_layers PPR/ICPE) |
| **Sudocuh (DGALN)** | état 31/12/2024 | dernier état annuel = 31/12/2024 | **Non** | manuel | non |
| **IGN BD TOPO V3 (bâti)** | mi-2025 | **éd. avril (261) + juillet (262) 2026 publiées** | **OUI** | ⚠ pas de commande CLI simple | **oui (bâti→résiduel)** |

### Les 48 autres sources

Millésimées statiques au dernier état publié (INSEE RP2022/2023, Filosofi 2021, IRIS 2024, ZNIEFF
29/08/2025, QPV 2024, ZFANG décret 05/2026, FRR 07/2024, Cartofriches, 50 pas, classement sonore
2023, INPN 2021/2025, LiDAR HD 25/06/2025, etc.) ou flux/proxy live (API Carto GPU/PLU, SUP, SIRENE,
Recherche d'entreprises, OSM/Overpass, GTFS PAN màj 08/2026). **Aucun retard ingérable détecté** :
soit au dernier millésime publié, soit flux vivant déjà ingéré (juillet–août 2026), soit source
manuelle/licence en attente (Fichiers fonciers Cerema, VRD/SPANC) → constat seulement.

### Décision R1 (arbitrages)

- **Aucune ingestion lancée.** Les sources cascade au sens strict (DVF, cadastre, zonage PLU/GPU,
  Géorisques) sont **à jour** ; les flux vivants (DPE/BAN/BODACC/INPI) sont frais (ingérés mi-août par
  les crons) et **non cascade** — les relancer créerait un delta de données non re-scoré, contraire à
  « aucun chiffre servi ne change ». → constat.
- **RV-001 🟡 — BD TOPO en retard (édition juillet 2026 vs bâti ingéré mi-2025).** C'est la seule
  source **cascade** ayant bougé (le bâti alimente `parcel_residuel` → SDP → score de cascade, cf.
  `residuel.py:35` `kind='batiment'`). **Mais** il n'existe **pas de commande d'ingestion BD TOPO
  simple/libre** au CLI (le bâti vit dans `spatial_layers` via un pipeline WFS non trivial ; la seule
  commande bâti est `ingest-cosia`, autre source). Ré-ingérer le bâti de toute l'île + recalculer le
  résiduel + re-scorer, juste avant mise en ligne, est un **chantier DONNÉE dédié** hors périmètre
  d'une revue. → **Constat documenté, pas d'ingestion.**
- **Conséquence pour R10 : aucune source cascade n'a été ré-ingérée → R10 ne se déclenche pas** (le
  bâti actuel est cohérent avec le résiduel recalculé ce midi). Détaillé en R10.

---
## R2 — CRON & FUSEAUX

### Bug de fuseau (consigné) — CORRIGÉ

**Cause racine** : machine en CEST, PostgreSQL en `Indian/Reunion` (+2). Le SQL (`CURRENT_DATE`,
`now()`) était en heure Réunion, mais le Python (`date.today()`, `datetime.now()`) en CEST. Entre
20 h et minuit CEST il est déjà « demain » à la Réunion → le jour Python (J) diverge du jour SQL
(J+1). La porte quota partenaires comparait `date.today()` (CEST) au `jour` stocké par `current_date`
(Réunion) → **réinitialisait le quota au lieu de le lever** (RV-002).

**Correction (deux garde-fous)** :
- **SQL** : `db.py` force le fuseau de session PG à `Indian/Reunion` (`-c timezone=Indian/Reunion`
  dans `connect_args`) → tout `CURRENT_DATE`/`now()` est en Réunion **quel que soit le serveur de
  prod** (robuste, corrige d'un coup tous les compteurs SQL : quota.py, events.py CURRENT_DATE, …).
- **Python** : nouveau module `labuse/tz.py` (`REUNION_TZ`, `today_reunion()`, `now_reunion()`).
  Fenêtres métier réalignées :

| Fichier | Fenêtre métier | Correction |
|---------|----------------|-----------|
| `partners.py:463` | **porte quota partenaires (bug consigné)** | `date.today()` → `today_reunion()` |
| `protection.py:_aujourdhui` | compteurs jour (quota fiches/tuiles/exports) | `today_reunion()` |
| `protection.py:scan_abus` | fenêtre « hier » du scan anti-scraping | `today_reunion()` |
| `ia.py`, `copilote.py`, `copilote_v2.py` | clés de quota jour (NL / agent / mission) | `today_reunion()` |
| `events.py` (dédup fraîcheur, péremption permis) | fenêtres jour métier | `today_reunion()` |

Les `CURRENT_DATE`/`now()` SQL (quota.py, events.py:512/795) sont couverts par le fuseau de session
— pas de modification ligne à ligne nécessaire. Les usages **techniques** (numéro de dossier
`DP-YYYYMMDD`, footer PDF « généré le », clés de réf) restent en heure locale : aucune fenêtre métier.

**RV-002 🟠→corrigé — porte quota partenaires.** Test de non-régression :
`test_partners_api_v1.py::test_r2_porte_quota_ne_reinitialise_pas_le_meme_jour_reunion` (au quota
+ même jour Réunion → 429 sans reset ; jour d'hier → reset). Suite protection/copilote : 17/17 verts.

### Inventaire CRON

Table complète : **`docs/EXPLOITATION-CRON.md`**. 10 jobs installés (train nocturne ordonné
radar→sitadel→bodacc→notifications→backup→abuse→fraicheur, tous sous `flock`). Cronables non
installés : `avis-echeance`, `evaluer-secteurs`. **Manquants** :
- **RV-003 🟡 — purge des sessions expirées** : `sessions_auth` n'est jamais nettoyée (dette AC-011).
  → commande `purge-sessions` créée en **R9**.
- **RV-004 🟡 — webhook Stripe absent** : paiements asynchrones non captés → détaillé en **R6**.

---
## R3 — MOTEUR UNIQUE REJOUÉ (q_v11_m137)

Protocole LOT AP rejoué sur le run servi actuel (`qa/revue/r3_moteur_unique.py`). Le run servi est
lu du point de vérité unique `config/served_run.txt` (`Q_A_RUN_LABEL`) = `q_v11_m137` ; la carte
(`mvt_meta.run_label`) = `q_v11_m137` (rebâtie ce midi). **130 parcelles** (120 tirées au sort tous
tiers + 10 cas canari) rejouées par tous les chemins servis.

### Concordance — AUCUNE DIVERGENCE

Pour chaque parcelle, les grandeurs servies concordent **exactement** entre les trois chemins :

| Grandeur | SQL (couche servie) | Fiche `/parcels/{idu}` | `/v2/score/{idu}` | Écart |
|----------|--------------------|-----------------------|-------------------|-------|
| tier (classement) | ✓ | ✓ | ✓ | **0** |
| mult_base (score) | ✓ | ✓ | ✓ | **0** |
| rang | ✓ | ✓ | ✓ | **0** |
| surface | ✓ | ✓ | — | **0** |

**130/130 concordantes, 0 divergence 🔴.** La bascule vers `q_v11_m137` est propre : aucun chemin
ne sert un vestige de l'ancien run. Moteur unique confirmé.

### Canari (score élevé → a_creuser) — POURQUOI LISIBLE ✅

Les 10 parcelles à `mult_base` élevé (13–22) classées `a_creuser` : **le pourquoi de non-opportunité
est visible et lisible sur chaque fiche** via le détail sourcé négatif. Exemple `97416000DN0012`
(mult 22,12, a_creuser) — 6 contraintes explicites servies au client :

- `[-15] risques` : Aléa inondation — niveau fort.
- `[-10] risques` : Aléa mouvement de terrain — niveau moyen.
- `[-5] icpe` : Installation classée à proximité (CBO TERRITORIA, 273 m).
- `[-5] risques` : Zone bleue PPR inondation/mouvement — constructible sous prescriptions (DEAL).
- `[-5] sol_pollue` : Site pollué recensé (CASIAS) à proximité — étude de sol (Central Téléphonique, 64 m).
- `[-5] bruit_route` : Classement sonore cat. 3 — isolement acoustique obligatoire (R.571-32 CE).

Chaque contrainte est **nommée, chiffrée, sourcée**. Le client comprend qu'une parcelle au fort
signal foncier est reléguée à cause d'un empilement de contraintes réglementaires/risques.

- **RV-005 ✅ — Canari satisfait.** Le motif de non-opportunité est lisible sur la fiche (lignes de
  détail sourcé négatives). Le champ de synthèse `score_v2.motif` reste `None` pour ces `a_creuser`
  (le motif de synthèse est réservé aux déclassements `declasse_*`), mais le détail par couche est
  complet et explicite. **Aucune modification** de l'affichage ni du classement nécessaire (conforme
  « sans changer le classement »). Arbitrage : le pourquoi étant déjà servi ligne à ligne, ajouter un
  badge de synthèse serait cosmétique et hors périmètre « aucun chiffre ne change ».
