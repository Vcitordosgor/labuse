# PLU-STDENIS-1 — Aligner Saint-Denis sur le millésime 20260805 (les 2 îlots en retard)

**Mandat** : Saint-Denis (97411) était déjà sur le nouveau millésime 20260805 partout (zonage, fiche,
capacité, exports, Copilote), SAUF deux endroits restés sur 20260423 — (1) l'outil PLU (ZIP + recherche
verbatim + millésime affiché, alimentés par `plu_reglement_extrait`) et (2) le catalogue
`config/plu_millesimes.yaml`. On corrige **uniquement** ces deux-là. Aucun recalibrage, aucun recalcul.
Branche `fix/plu-stdenis-1` · worktree `~/Desktop/labuse-stdenis` · base main `d288600e` · API `:8145` / front `:5345`.

---

## 0. Étape 0 — état de départ (vérifié)
Arbre propre sur `main` (`d288600e`), worktree créé propre. **Résiduel et scoring servis INCHANGÉS** :
`served_run.txt` = `q_v11_m137` ; `parcel_residuel` = 431 663 lignes, `computed_at` 21-22/09 (non touché
par ce mandat — on ne réingère QUE le règlement-texte).

## 1. Périmètre confirmé avant écriture (lecture seule)
- **Récupérabilité** : le règlement 20260805 est disponible au GPU par le chemin d'ingestion existant
  (`plu_corpus.fetch_reglement`) — garde d'identité OK, `idurba_gpu = 97411_PLU_20260805`, une entrée
  `97411_reglement_20260805.pdf` (5,9 Mo, sha `35ee9bbd…`), pack `PACK_DU_97411_eee143…`. Gate franchi.
- **Qui lit encore l'ancien 20260423** : `plu_reglement_extrait` (base) + `config/plu_millesimes.yaml`.
  Les fichiers `config/calibrage/*saint_denis*` citent aussi 20260423 mais **ne sont lus par aucun code**
  (le calibrage actif est `config/plu_zonage.yaml` + `config/plu_destinations/97411_saint_denis.yaml`,
  déjà `document_gpu = 20260805`) — artefacts périmés, laissés tels quels (recalibrage hors mandat).

## 2. Ré-ingestion du règlement-texte (chemin existant)
Script ciblé `reports/plu-stdenis-1/reingest_97411.py` — utilise les fonctions du pipeline existant
(`plu_corpus.fetch_reglement` + `plu_ingest.ingest_reglement`), borné à `insee='97411'` (garde-fou 974) :

| Étape | Résultat |
|---|---|
| AVANT | idurba `97411_PLU_20260423`, **241 extraits**, doc `97411_reglement_20260423.pdf` |
| Fetch GPU 20260805 | garde_ok=True, `97411_reglement_20260805.pdf` |
| Suppression | **241** extraits 97411 supprimés (le nom de doc change → l'ancien ne survivrait pas au seul `DELETE by insee+document` d'`ingest_reglement` ; nettoyage explicite) |
| Ingestion | **241** extraits pour `97411_PLU_20260805` |
| APRÈS | idurba `97411_PLU_20260805`, millésime `2026-08-05`, `source_url` = pack `…PACK_DU_97411_eee143…/97411_PLU_20260805.zip`, doc `97411_reglement_20260805.pdf` |

**Aucun autre INSEE touché** : 20 autres communes / 3 017 extraits inchangés (corpus = 21 communes, comme avant).
L'ancien millésime n'est plus servi (0 ligne 20260423 restante).

## 3. Catalogue corrigé
`config/plu_millesimes.yaml`, ligne 97411 (seul fichier versionné modifié) :
```
- "97411": {commune: "Saint-Denis", idurba: "97411_PLU_20260423", date_mairie: "2026-04-23", statut: a_jour}
+ "97411": {commune: "Saint-Denis", idurba: "97411_PLU_20260805", date_mairie: "2026-08-05", statut: a_jour,
+           note: "[PLU-STDENIS-1] catalogue aligné 20260423 → 20260805 (Modification simplifiée n°8, …)"}
```

## 4. Vérifications

### 4.1 Outil PLU Saint-Denis — avant / après (navigateur, `:5345`)
Captures : `reports/plu-stdenis-1/captures/stdenis-AVANT.png` et `…-APRES.png`.

| | AVANT | APRÈS |
|---|---|---|
| Fil / millésime affiché | « Saint-Denis · **PLU du 2026-04-23** » | « Saint-Denis · **PLU du 2026-08-05** » |
| Bouton ZIP (href) | `…/PACK_DU_97411_c82625…/97411_PLU_**20260423**.zip` | `…/PACK_DU_97411_eee143…/97411_PLU_**20260805**.zip` |
| Sous-titre | « contient `97411_reglement_20260423.pdf` » | « contient `97411_reglement_20260805.pdf` » |
| Recherche verbatim (API) | idurba/millésime/doc = **20260423** | idurba/millésime/doc = **20260805** |

### 4.2 Zonage == règlement (l'écart PLU-PARTOUT-1 refermé)
`plu_gpu_zone` (`97411_PLU_20260805`) == `plu_reglement_extrait` (`97411_PLU_20260805`) → **ALIGNÉ ✓**.
Saint-Denis n'est plus la commune en désync.

### 4.3 Dashboard X5.2 (état de calibrage)
`destinations.etat_commune('Saint-Denis')` → `etat=calibree`, catalogue `document_gpu_servi=20260805` ==
calibrage `document_gpu=20260805`, **`note=None`** : plus de mention « catalogue en retard ».

### 4.4 Tests
`pytest tests/` (labuse_test) : **30 failed / 3155 passed / 67 skipped** = **baseline identique** (RACINE-1).
Les 30 échecs sont les verrous « sur la base réelle » / provenance (base applicative absente de
`labuse_test`) — **aucun test PLU/millésime/annuaire/zonage/destinations en échec** (les 203 tests PLU
ciblés passent). Aucune nouvelle rupture.

## 5. Ce qui a été fait / ce qui reste au geste de Vic
- **Fait par CC** : ré-ingestion du règlement-texte 97411 dans la base `labuse` (via le chemin existant)
  + correction du catalogue `plu_millesimes.yaml`. L'outil PLU sert le 20260805, l'écart zonage/règlement
  est refermé, X5.2 propre.
- **Reste à Vic** :
  1. **Le merge** de `fix/plu-stdenis-1` (le seul diff versionné = la ligne catalogue 97411 ;
     `reports/plu-stdenis-1/` = livrable). La ré-ingestion est un geste de **base de données**, pas un
     commit — elle est déjà appliquée sur la base `labuse` locale.
  2. **Si d'autres environnements** (prod / autre base) doivent recevoir le nouveau règlement : y rejouer
     l'ingestion. Commande équivalente ciblée :
     `PYTHONPATH=src LABUSE_DATABASE_URL=<cible> .venv/bin/python reports/plu-stdenis-1/reingest_97411.py`
     (⚠ **gotcha à connaître** : les scripts canoniques `m51_fetch_corpus.py` / `m51_ingest_corpus.py`
     réingèrent TOUTES les communes et `ingest_reglement` supprime par `insee+document` — un **changement
     de millésime change le nom de document**, donc les vieilles lignes survivraient sans le `DELETE WHERE
     insee` explicite qu'ajoute le script ciblé. À intégrer au pipeline si un geste générique est voulu.)

## 6. Hors mandat (non touché)
Aucune autre commune · pas de recalibrage `plu_destinations`/`plu_zonage` · pas de recalcul
`parcel_residuel` ni du score (déjà à jour) · pas d'autre outil · pas de merge.
Artefacts périmés `config/calibrage/*saint_denis*` (20260423, non lus) laissés en l'état.
