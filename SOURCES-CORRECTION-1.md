# SOURCES-CORRECTION-1 — Les 8 de l'audit

**Branche** `feat/sources-audit-1` — étape 0 : `0f8b2240` (HEAD après SOURCES-AUDIT-1). Un commit par lot,
branche poussée, aucun merge. Gates : `tsc -b` vert, `labuse circuit verrous -w G8` vert.

---

## Lot 1 — `dpe_ademe` à son plein potentiel — **16 → 1123**

### Diagnostic : ce n'était PAS « le job saute les communes peuplées » — c'était un filtre à l'envers

L'ingestion tournait et ne ramenait que 16 lignes. Le connecteur DPE l'expliquait (note datée 13/09) par
un **trou producteur** : « l'ADEME rabat ~900 logements de métropole sur des INSEE 974 ; on tranche donc
sur le **CP brut** (fiable), jamais sur le géocodage BAN (faux à 98 %) ». **Vérifié live le 19/09 contre
l'API ADEME, c'est l'INVERSE** :

- Au **CP brut 974** : 16 existants + 75 neufs + 2 tertiaires = 93 candidats. C'est ce que l'ancien filtre
  moissonnait → 16 gardés après corroboration.
- Au **géocodage BAN 974** (`code_insee_ban:974*`) : **914 existants + 179 neufs + 30 tertiaires**. L'ancien
  filtre les **jetait** en les croyant « métropolitains ». Preuves qu'ils sont **réunionnais authentiques** :
  - leur `identifiant_ban` est en **974xx (300/300)** échantillonnés ;
  - il correspond **EXACTEMENT** à la table `adresses` locale (BAN Réunion) pour **150/300** ;
  - l'`adresse_ban` géocodée est une adresse réunionnaise réelle : « **RN 5 Petit Serre, Saint-Louis** »
    (score 0,88), « **Chemin de la Plaine, Saint-Louis** » (0,88), « 38 Rue Saint Louis, Saint-Paul » (0,89).
  - Ce qui est faux chez ces ~900, c'est le **CP brut** (62200 Boulogne, 66000 Perpignan…) : un champ **saisi**
    par le diagnostiqueur (souvent son propre CP) — du **bruit**, pas la vérité.

Les **vrais** homonymes existent et devaient rester rejetés : les **75 « neufs ST LEU 97436 »** géocodent
en INSEE **95563** (Saint-Leu-la-**Forêt**, Val-d'Oise) — donc **hors** `code_insee_ban:974*` — et les 2
« existants 97490/97434 » sont Montpellier / Lille. Le garde-fou est bien maintenu (cf. ci-dessous).

### Le correctif (backend seulement)

- **`connectors/dpe.py`** — `fetch_reunion_authentiques()` moissonne désormais l'**UNION**
  `code_insee_ban:974*` **∪** CP brut 974 (dédup `numero_dpe`) : la vérité = le géocodage BAN 974,
  le CP brut ne servant plus qu'à rattraper les orphelins (BAN≠974).
- **`ingestion/dpe.py`** — `is_reunion_authentic()` accepte une ligne si **BAN a géocodé en 974** OU si le
  CP brut est réunionnais ; ne rejette que si **aucun des deux** ne dit Réunion. La **corroboration locale**
  de `ingest_jeu` (rattachement `adresses` + garde-fou coordonnées `verifier_974`) reste **seul juge de
  l'homonymie** — inchangée. Docstrings des deux modules corrigées (l'hypothèse « BAN faux à 98 % » était fausse).
- **`tests/test_dpe.py`** — `test_is_reunion_authentic` et `test_ban974_cp_brut_metropolitain_garde`
  (ex-`test_contamination_metropole_ecartee`) reflètent la sémantique corrigée : un DPE BAN-974 corroboré
  localement est **gardé** même si son CP brut est métropolitain. Les tests d'homonymie et de garde-fou
  coordonnées (`test_garde_974`, `test_ingest_jeu_homonymie_et_miroir`) passent **inchangés**.

### Preuve

- **Comptes avant/après par commune** : `qa/out/dpe_avant.txt` (16 sur 8 communes) → `qa/out/dpe_apres.txt`
  (**1123 sur 20 communes**, 1109 rattachées à leur parcelle). Détail moisson :
  `existant 914 (rejetés homonymie 2), neuf 179 (rejetés 75 = Saint-Leu-la-Forêt), tertiaire 30 (0 rejeté)`.
- **Capture d'une fiche parcelle témoin avec le DPE affiché** :
  `captures/sources-correction/dpe_fiche_97401000AR1495_*.png` (parcelle absente des 16 d'avant ; bloc
  « DPE du bâtiment », étiquette **D** / GES **B**, appartement, source DPE ADEME — payload backend vérifié).
- **Filtre de la source vert** : `dpe_ademe` fraîcheur **`en_retard` → `a_jour`** (ré-ingestion du jour,
  `sources_fraicheur` recalculé : 0 `en_retard` / 0 `en_panne` sur les 94). Recouvrement des données passé
  de ~65 j à **17 j** (dernier DPE établi 2026-09-02 = le plus récent que l'ADEME publie pour l'île).
- `tests/test_dpe.py` + `tests/test_garde_974.py` : **21 passed**. `tsc -b` : aucun fichier front touché.

---

## Lot 2 — statuts

### `deal_wms_wfs` → **hub** (fait) : vitrine **94 → 93**

Décision Vic appliquée. `deal_wms_wfs` était `connecte`/`urbanisme` ; il rejoint les 3 autres hubs
hors vitrine (`status='hub'`, `category='hub'`). C'est un **canal carto** (hôte DEAL injoignable, HTTP 000,
servi par proxys, **aucune vanne d'ingestion propre**) — pas une source de première classe. Ceci **renverse
la requalification M74** (« hub→urbanisme », qui l'avait fait rentrer en vitrine).

- **Où** : `seed_sources.py` (ajouté au tuple `HUBS` → `appliquer_statuts_circuit()` pose `status='hub'`
  de façon **idempotente et durable au re-seed** ; entrée de catalogue passée `S.HUB`/`category="hub"` +
  note refaite) ; **DB** `UPDATE data_sources SET status='hub', category='hub'`.
- **Vérifié** : `V2a` **OK — 93 = 93 = 93** (vitrine SQL = prédicat Python = page) ; `V2b` OK (toute ligne
  hors vitrine dit pourquoi — `hub` est un statut de première classe) ; `V1d` OK. Le « 94 » n'est gravé
  nulle part : tout lit `WHERE_AFFICHEES`, tout est passé à 93 ensemble.
- **⚠ Trouvé, PAS corrigé (hors périmètre)** : la couche `kind='anru'` (8 emprises) reste rattachée en base
  à cette ligne (`spatial_layers.data_source_id = 13`, héritage M74) alors que le registre code
  (`RESERVOIR_TABLES`) la déclare au réservoir **`npnru`**. Un hub ne devrait rien « posséder » : la
  **ré-attribution `anru` → `npnru`** rendrait le hub vraiment vide. C'est une décision **couche-registre**
  (aucun verrou ne la contraint — V1d/V2b lisent le registre code, pas le `data_source_id`), **laissée à Vic**.

### `cadastre_epoque` — proposition (NON tranchée)

**Fait** : table `cadastre_historique` (6 526 lignes), lue **uniquement** par un fabricant d'ingestion
(`ingestion/cadastre_historique.py:rattacher_par_geometrie`, qui **géoréférence `sitadel_permits.geom`**) ;
**aucune surface client** (la fiche n'affiche qu'une prose statique). Elle *sert*, mais au **pipeline**, pas au client.

- **Option A — rester en vitrine, rôle interne déclaré** : garder `connecte`, note « référentiel
  géométrique **interne** — géoréférence les permis Sitadel, aucune donnée servie au client ». *Contre* :
  la vitrine « ne montre que ce qui SERT **au client** » (règle Vic M123) → une source interne y détonne.
- **Option B — sortir de la vitrine** : `status='dormant'` (servie nulle part **côté client**), table et rôle
  interne **conservés** dans la note. *Pour* : la vitrine reste honnête (que du client-facing) ; la donnée
  et son usage-pipeline ne bougent pas.
- **Recommandation** : **Option B** (sortir, `dormant`, rôle interne écrit) — c'est un outil de la pompe, pas
  une source cliente. À trancher par Vic.

### `sudocuh` — proposition (NON tranchée)

**Fait** : table `sudocuh_procedures` (24 lignes), lue **uniquement** par le **modèle candidat**
`scoring/p_v2/qv14.py` (feature `anciennete_plu`) ; le run **servi** en prod est `q_v11_m137`, où cette
feature **ne contribue pas** → 0 surface client aujourd'hui.

- **Option A — rester, rôle déclaré** : garder `connecte`, note « alimente le modèle candidat `q_v14`
  (`anciennete_plu`), **non encore promu** ». *Pour* : si `q_v14` est sur une trajectoire de promotion, la
  source deviendra servie ; la sortir puis la rentrer serait du yo-yo.
- **Option B — sortir** : `status='dormant'` tant que `q_v14` n'est pas le run servi. *Pour* : reflète l'état
  réel (rien de servi au client).
- **Recommandation** : **dépend de la feuille de route `q_v14`** — si sa promotion est planifiée, **Option A**
  (rester, rôle candidat déclaré) ; sinon **Option B** (`dormant`). À trancher par Vic (je m'arrête sans décider).
