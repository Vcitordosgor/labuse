# PLU-FRAICHEUR-1 — Chaque commune sert-elle le DERNIER millésime du GPU ?

**Mandat** : pour les 24 communes, comparer le millésime PLU **servi** par l'outil au millésime
**EN_VIGUEUR** au Géoportail de l'Urbanisme (GPU), et sortir la liste des retards.
Suite de PLU-RACCORD-1 (qui n'avait comparé le millésime qu'à Saint-Denis).
**Lecture seule** — aucune modif, aucune re-ingestion, aucun merge.
Branche `audit/plu-fraicheur-1` · worktree `~/Desktop/labuse-plufraicheur` · base main `00106a19` (arbre propre).

Livrable joint : [`reports/plu-fraicheur-1/TABLE-24.csv`](../../reports/plu-fraicheur-1/TABLE-24.csv)
· script reproductible `fraicheur_check.py` (réutilise la logique GPU de `plu-raccord-1/gpu_pack_check.py`).

---

## 1. Méthode — ce qui est comparé, pour les 24

Par code INSEE, sans rien re-télécharger ni ré-ingérer :

- **Millésime servi** = l'idurba que l'outil sert aujourd'hui.
  - communes **servables** → `idurba` de la table ingérée `plu_reglement_extrait` (base `labuse`),
    la même source que le bouton « Télécharger le PLU intégral » (`source_url`). Contrôle : **1 seul
    idurba distinct par commune** (vérifié en base, `HAVING count(distinct idurba) > 1` → vide),
    donc le millésime servi est non ambigu.
  - communes en **révision** → l'outil sert le pack **live GPU** (composant `PackVigueur`) ; la base
    n'est pas ingérée → pas de « millésime servi » figé à comparer.
  - **RNU** → aucun PLU.
- **Millésime GPU EN_VIGUEUR** = requête live GPU `grid=insee`, document au statut `EN_VIGUEUR`
  (même appel que PLU-RACCORD-1). Date extraite de l'`originalName` (AAAAMMJJ).
- **Verdict** : à jour (idurba/date identiques) · en retard de N jours (GPU plus récent) · non comparable.

**Garde-fous respectés** : Saint-André, Saint-Leu (GPU vide → repli mairie) et Saint-Philippe (RNU)
sont mis **hors comparaison**, jamais comptés « en retard ».

---

## 2. Compte

| Verdict | Nombre | Communes |
|---|---:|---|
| **À jour** (millésime servi = GPU EN_VIGUEUR) | **20** | toutes sauf les 4 ci-dessous |
| **En retard** | **1** | Saint-Denis (97411) — **104 jours** |
| **Non comparable** | **3** | Saint-André (97409) · Saint-Leu (97413) · Saint-Philippe (97417) |

Pour les 20 « à jour », l'idurba servi est **strictement identique** à l'idurba GPU EN_VIGUEUR
(pas seulement la date). L'outil sert donc bien le dernier millésime pour 20 communes sur les 21
qui ont un règlement ingéré.

---

## 3. Tableau des 24

| Commune | INSEE | Millésime servi | Date servie | Millésime GPU EN_VIGUEUR | Date GPU | Verdict |
|---|---|---|---|---|---|---|
| Les Avirons | 97401 | 97401_PLU_20241206 | 2024-12-06 | 97401_PLU_20241206 | 2024-12-06 | à jour |
| Bras-Panon | 97402 | 97402_PLU_20260428 | 2026-04-28 | 97402_PLU_20260428 | 2026-04-28 | à jour |
| Entre-Deux | 97403 | 97403_PLU_20240924 | 2024-09-24 | 97403_PLU_20240924 | 2024-09-24 | à jour |
| L'Étang-Salé | 97404 | 97404_PLU_20250917 | 2025-09-17 | 97404_PLU_20250917 | 2025-09-17 | à jour |
| Petite-Île | 97405 | 97405_PLU_20230609 | 2023-06-09 | 97405_PLU_20230609 | 2023-06-09 | à jour |
| La Plaine-des-Palmistes | 97406 | 97406_PLU_20230527 | 2023-05-27 | 97406_PLU_20230527 | 2023-05-27 | à jour |
| Le Port | 97407 | 97407_PLU_20241209 | 2024-12-09 | 97407_PLU_20241209 | 2024-12-09 | à jour |
| La Possession | 97408 | 97408_PLU_20251217 | 2025-12-17 | 97408_PLU_20251217 | 2025-12-17 | à jour |
| **Saint-André** | 97409 | pack live GPU (GPU vide) | — | — | — | **non comparable** (révision, GPU vide → mairie) |
| Saint-Benoît | 97410 | 97410_PLU_20200206 | 2020-02-06 | 97410_PLU_20200206 | 2020-02-06 | à jour |
| **Saint-Denis** | 97411 | 97411_PLU_20260423 | 2026-04-23 | **97411_PLU_20260805** | **2026-08-05** | **EN RETARD de 104 j** |
| Saint-Joseph | 97412 | 97412_PLU_20251210 | 2025-12-10 | 97412_PLU_20251210 | 2025-12-10 | à jour |
| **Saint-Leu** | 97413 | pack live GPU (GPU vide) | — | — | — | **non comparable** (révision, GPU vide → mairie) |
| Saint-Louis | 97414 | 97414_PLU_20251218 | 2025-12-18 | 97414_PLU_20251218 | 2025-12-18 | à jour |
| Saint-Paul | 97415 | 97415_PLU_20251217 | 2025-12-17 | 97415_PLU_20251217 | 2025-12-17 | à jour |
| Saint-Pierre | 97416 | 97416_PLU_20240625 | 2024-06-25 | 97416_PLU_20240625 | 2024-06-25 | à jour |
| **Saint-Philippe** | 97417 | — (RNU, aucun PLU) | — | — | — | **non comparable** (RNU) |
| Sainte-Marie | 97418 | 97418_PLU_20251126 | 2025-11-26 | 97418_PLU_20251126 | 2025-11-26 | à jour |
| Sainte-Rose | 97419 | 97419_PLU_20190504 | 2019-05-04 | 97419_PLU_20190504 | 2019-05-04 | à jour |
| Sainte-Suzanne | 97420 | 97420_PLU_20250929 | 2025-09-29 | 97420_PLU_20250929 | 2025-09-29 | à jour |
| Salazie | 97421 | 97421_PLU_20220524 | 2022-05-24 | 97421_PLU_20220524 | 2022-05-24 | à jour |
| Le Tampon | 97422 | 97422_PLU_20230811 | 2023-08-11 | 97422_PLU_20230811 | 2023-08-11 | à jour |
| Les Trois-Bassins | 97423 | 97423_PLU_20220602 | 2022-06-02 | 97423_PLU_20220602 | 2022-06-02 | à jour |
| Cilaos | 97424 | 97424_PLU_20240213 | 2024-02-13 | 97424_PLU_20240213 | 2024-02-13 | à jour |

Note : **Trois-Bassins (97423)** a une révision en cours (procédure active, cf. PLU-RACCORD-1) mais
son règlement **servi = GPU EN_VIGUEUR** → à jour côté fraîcheur. Procédure et fraîcheur sont deux
axes distincts.

---

## 4. La liste nette des retards — pour un futur geste de veille

**1 seule commune en retard :**

| Commune | INSEE | Servi | GPU EN_VIGUEUR | Écart |
|---|---|---|---|---|
| **Saint-Denis** | 97411 | `97411_PLU_20260423` (2026-04-23) | `97411_PLU_20260805` (2026-08-05) | **104 jours** |

Le GPU a republié le PLU de Saint-Denis le 05/08/2026 ; toutes les versions antérieures, dont celle
servie (23/04/2026), sont passées `ARCHIVE` (un seul EN_VIGUEUR au GPU, vérifié). L'outil sert donc
le **bon PLU de Saint-Denis**, mais un millésime en retard d'une révision — sur le bouton de
téléchargement, le corpus de recherche et la date affichée.
**Geste de veille suggéré (hors mandat)** : re-ingérer `97411_PLU_20260805` (M40/M41). Rien d'autre à faire.

**3 non comparables (attendu, pas des retards) :**
- Saint-André (97409) et Saint-Leu (97413) : en révision, le GPU `grid=insee` renvoie `[]` → l'outil
  bascule sur le pack live et, à défaut, la mairie de la commune. Pas de millésime figé à comparer.
- Saint-Philippe (97417) : RNU, aucun PLU.

---

## 5. Verdict

**20 communes sur 24 servent le dernier millésime EN_VIGUEUR du GPU (idurba identique).**
**1 est en retard : Saint-Denis, de 104 jours.** **3 sont non comparables** (2 en révision hors GPU,
1 RNU) — conformément aux garde-fous, non comptées comme retard.

Aucune correction, aucune re-ingestion effectuée : ce rapport ne fait que constater l'écart pour
alimenter la veille.

---

### Reproductibilité
- `reports/plu-fraicheur-1/fraicheur_check.py` → `TABLE-24.csv` (base `labuse`.plu_reglement_extrait pour le servi + GPU live EN_VIGUEUR pour la référence ; réutilise la logique de `plu-raccord-1/gpu_pack_check.py`).
- Base `labuse` : peer auth openclaw (`psql -d labuse`). GPU : `https://www.geoportail-urbanisme.gouv.fr/api/document?grid={insee}`.
- Relevé GPU du 2026-09-22.
