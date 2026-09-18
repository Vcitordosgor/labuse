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
