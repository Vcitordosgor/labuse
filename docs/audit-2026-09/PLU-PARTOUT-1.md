# PLU-PARTOUT-1 — Tous les endroits de l'app qui utilisent le PLU servent-ils le dernier millésime ?

**Mandat** : recenser TOUS les endroits qui touchent au PLU LABUSE et vérifier, pour chacun, s'il lit
le dernier millésime ou un ancien, en prenant **Saint-Denis (97411)** comme cas test (PLU-FRAICHEUR-1
l'avait trouvé « servi 20260423 vs GPU 20260805 »).
**Lecture seule** — aucune modif, aucune re-ingestion, aucun recalcul, aucun merge.
Branche `audit/plu-partout-1` · worktree `~/Desktop/labuse-plupartout` · base main `565820f8` (arbre propre).

Livrable joint : [`reports/plu-partout-1/ENDROITS.csv`](../../reports/plu-partout-1/ENDROITS.csv).

---

## 0. Le retournement — Saint-Denis n'est PAS « en retard partout »

PLU-FRAICHEUR-1 avait comparé **une seule source** : `plu_reglement_extrait` (le corpus du texte
règlement, servi par l'annuaire). En regardant TOUTES les sources PLU en base, le tableau réel est
l'inverse de l'intuition : **Saint-Denis est déjà sur le NOUVEAU millésime (20260805) presque partout.**
Le retard de 104 jours est confiné à **deux** endroits — le corpus règlement-texte et le catalogue.

Faits mesurés en base `labuse` (le 22/09/2026) :

| Source | idurba Saint-Denis | Millésime |
|---|---|---|
| `spatial_layers` kind=`plu_gpu_zone` (zonage, attrs) | **97411_PLU_20260805** (ingéré 14/09) | **NEUF** |
| `parcel_zone_plu` (matérialisé) | zones modif. n°8 (Uavap, Um, Uh, Ud, Uj…) | **NEUF** |
| calibrage `config/plu_destinations/97411_saint_denis.yaml` (`meta.document_gpu`) | **97411_PLU_20260805** (lu le 03/09) | **NEUF** |
| `parcel_residuel` (capacité) | `computed_at` 21-22/09 (postérieur au zonage neuf) | **NEUF** |
| `plu_reglement_extrait` (annuaire ZIP + recherche) | **97411_PLU_20260423** | **ANCIEN** |
| `config/plu_millesimes.yaml` (catalogue) | **97411_PLU_20260423** | **ANCIEN** |

Contrôle transversal : le **calibrage colle au zonage pour les 24 communes** (`document_gpu` ==
idurba `plu_gpu_zone` partout, Saint-Denis inclus). Et **Saint-Denis est la SEULE commune** où
`plu_gpu_zone` (20260805) diverge de `plu_reglement_extrait` (20260423) — les 22 autres servables
ont zonage == règlement-texte.

---

## 1. Le tableau des endroits (détail dans ENDROITS.csv)

### Endroits DÉJÀ sur le nouveau millésime (20260805)

| Endroit | Source lue | Dépend de |
|---|---|---|
| Couche carte « Limites officielles du PLU » | `plu_gpu_zone` brut (MVT) | lecture directe (ré-ingéré 14/09) |
| Couche « Zonage PLU par parcelle » | `parcel_zone_plu` (matérialisé) | recalcul build-mvt (fait) |
| Filtre Zonage (famille) + Zone exacte | `parcel_zone_plu.zone_fam/zone_filtre` | recalcul build-mvt (fait) |
| Fiche — zone PLU (libellé + idurba) | `plu_gpu_zone` **en direct** (`app.py:_reglement_plu_block`, ST_Intersection) | lecture directe |
| Fiche — règlement chiffré (hauteur/emprise/reculs/destinations) | calibrage `plu_destinations/97411` + `plu_zonage.yaml` | calibrage (relu 03/09) |
| Fiche — lien + millésime du règlement | `reglement_source` → destinations `meta` | calibrage |
| Fiche — §capacité / potentiel | `parcel_residuel` + `parcel_faisabilite` | recalcul résiduel (fait 21-22/09) |
| Exports Dossier / Flash | payload fiche (zonage live + calibrage + résiduel) | lecture + calibrage + recalcul |
| Export Pré-dossier PC (règles, pages règlement) | calibrage destinations (pages du doc 20260805) | calibrage |
| Exports Financier / Apporteur | payload fiche | recalcul + calibrage |
| Copilote (contexte zone + règlement) | payload fiche (`zone_plu`, `reglement_plu`) | lecture directe |

### Endroits ENCORE sur l'ancien millésime (20260423)

| Endroit | Source lue | Dépend de |
|---|---|---|
| **Outil PLU — bouton « Télécharger le PLU intégral (.zip) »** | `plu_reglement_extrait.source_url` (pack GPU) | lecture directe (à jour dès ré-ingestion du règlement) |
| **Outil PLU — recherche verbatim** | `plu_reglement_extrait` (texte/tsv/page_pdf) | lecture directe (idem) |
| **Outil PLU — millésime affiché « PLU du … »** | `plu_reglement_extrait.millesime` (corpus_status) | lecture directe |
| **Catalogue millésimes** | `config/plu_millesimes.yaml` (idurba 20260423) | **config** (édition manuelle, pas une ingestion) |

Note : le **dashboard d'état de calibrage** (X5.2, `destinations.etat_commune`) compare déjà le
catalogue (20260423) au calibrage (20260805) et affiche factuellement « calibrée sur un document GPU
plus récent que le catalogue — calibration à jour » : l'app SAIT que le catalogue est en retard et le dit.

---

## 2. Carte « si on ré-ingérait Saint-Denis »

Le mandat demande ce qui bougerait/ne bougerait pas. Comme le zonage, le calibrage et le résiduel
sont **déjà** sur 20260805, une « ré-ingestion Saint-Denis » se réduit à **ré-ingérer le corpus
règlement-texte** (`plu_reglement_extrait`, la passe `plu_ingest`).

- **Bougerait tout seul (lecture directe, immédiat après ré-ingestion du règlement)** :
  le bouton ZIP, la recherche verbatim et le millésime affiché de l'outil PLU passeraient à 20260805.
- **Ne dépend PAS d'une ingestion** : le catalogue `config/plu_millesimes.yaml` — c'est une **édition
  de config** (aligner l'idurba sur 20260805), pas une ré-ingestion.
- **Déjà à jour, ne bougerait pas (rien à faire)** : zonage (couche + filtres + `parcel_zone_plu`),
  fiche (zone, règlement chiffré, lien, capacité), tous les exports, le Copilote — tout est déjà sur
  le neuf, calibrage relu le 03/09, zonage ingéré le 14/09, résiduel recalculé les 21-22/09.

Rappel des dépendances (ce qui ne suit JAMAIS une simple ré-ingestion) : les surfaces **pré-calculées**
(`parcel_zone_plu`, `parcel_residuel`, score) suivent un **recalcul** (build-mvt / résiduel-serve), pas
l'ingestion. Ici ils se trouvent déjà recalculés sur le neuf ; mais si demain un nouveau millésime était
ingéré sans relancer ces recalculs, la couche par-parcelle, les filtres et la capacité resteraient sur
l'ancien tant que le recalcul n'aurait pas tourné. Les **règles chiffrées** suivent un **re-calibrage**
(lecture manuelle du nouveau PDF, `document_gpu`), jamais l'ingestion géométrique seule.

---

## 3. Verdict

**La donnée PLU est cohérente d'un endroit à l'autre pour 23 communes sur 24, et à jour.**
Pour **Saint-Denis**, il reste **une incohérence localisée** : le décor décisionnel (zonage, règles,
capacité, fiche, exports, copilote) est sur le **nouveau** millésime 20260805, mais l'**outil PLU**
(téléchargement ZIP + recherche verbatim + millésime affiché) et le **catalogue** sont restés sur
l'**ancien** 20260423. Concrètement : un utilisateur lit la fiche au bon millésime, mais s'il clique
« Télécharger le PLU intégral » ou cherche le verbatim, il obtient le document d'avril — et le lien
règlement de la fiche (destinations, 20260805) pointe, lui, sur le bon PDF. C'est le même écart de
104 jours que PLU-FRAICHEUR-1, ici **précisément localisé** aux 2 sources restées en arrière.

**Aucun autre endroit en retard**, aucune commune (hors Saint-Denis) en désync entre ses sources PLU,
et le calibrage aligné sur le zonage pour les 24. Le geste de veille reste le même — re-ingérer le
règlement-texte de Saint-Denis + aligner le catalogue — **hors de ce mandat** (aucune correction faite).

---

### Reproductibilité (base `labuse`, peer auth openclaw ; GPU relevé 22/09/2026)
- Zonage vs règlement-texte par commune :
  `WITH z AS (SELECT commune, min(attrs->>'idurba') i FROM spatial_layers WHERE kind='plu_gpu_zone' GROUP BY 1),
   r AS (SELECT commune, min(idurba) i FROM plu_reglement_extrait GROUP BY 1)
   SELECT z.commune, z.i AS zonage, r.i AS reglement FROM z FULL JOIN r USING(commune) ORDER BY 1;`
  → Saint-Denis seul en écart (20260805 vs 20260423).
- Calibrage vs zonage : `config/plu_destinations/974*.yaml` `meta.document_gpu` == idurba `plu_gpu_zone` pour les 24.
- Résiduel : `SELECT min(computed_at), max(computed_at) FROM parcel_residuel r JOIN parcels p ON p.id=r.parcel_id WHERE p.idu LIKE '97411%';` → 21-22/09/2026 (postérieur au zonage 14/09).
- Fiche règlement en direct : `src/labuse/api/app.py:5104` (`_reglement_plu_block`, lit `plu_gpu_zone` par ST_Intersection).
