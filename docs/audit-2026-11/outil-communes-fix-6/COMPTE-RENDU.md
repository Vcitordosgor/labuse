# OUTIL-COMMUNES-FIX-6 — réponse au recontrôle `03-COMMUNES-ASTRA-4.md`

Périmètre = les 3 points « C'est faux » + les 2 remarques éditoriales (LOT 4). Tout ce que le rapport
déclare clos (8 médianes communales, 24 compteurs CatNat principaux, 24 trimestriels) est INCHANGÉ.
`main` fusionné (déjà à jour). SEULE la table `dvf_secteur_medianes` est écrite (rebuild autorisé par
Vic, mêmes règles que FIX-5) + sa sauvegarde datée. Chiffres par script committé, sortie brute dans
`docs/audit-2026-11/outil-communes-fix-6/`.

---

## LOT 0 — filet (commit séparé `1791c57d5`)
`tests/test_communes_fix6.py` (pytest) + `frontend/src/lib/catnat.test.ts` (vitest). AVANT correction :
- pytest : **3 failed** — IZ effectif 18≠14 ; CD (13≥8 servait un prix au lieu d'aucun) ; Plaine
  `etat_source_date` '2023-05-27'≠'2025-11-27'. (`LOT0-pytest-rouge.txt`)
- vitest : **2 failed** — `catnatReste(24,12,6)`→6≠18 ; `(21,12,6)`→6≠15. (`LOT0-vitest-rouge.txt`)

---

## LOT 1 — effectif/seuil du prix de section = ventes DANS les bornes

**Cause** (confirmée) : `ingestion/dvf_marche.py:189` comptait `n_ventes = count(*)` (TOUS les actes),
alors que la médiane `mediane_prix_m2` est filtrée aux bornes `[50 ; 20 000] €/m²`. L'effectif affiché ET
le seuil de diffusion (Comparer, `api/app.py`) portaient donc sur des actes qui n'entrent pas dans la
médiane. Témoins : IZ 18/284 (4 actes hors bornes : 5,08 / 7,62 / 7,62 / 36 000) ; CD 133/13 (1 seule
vente dans les bornes → le seuil de 8 franchi à tort).

**Correctif** : `n_ventes` (et `mediane_valeur`, pour la cohérence de la ligne) comptent désormais
`FILTER (WHERE ratio BETWEEN 50 AND 20000)` — les ventes qui fondent la médiane. Le seuil de Comparer
(`app.py`) lit ce `n_ventes` corrigé → une section à 1 vente dans les bornes n'est plus diffusée.

**Audit des autres lecteurs de prix** (décalage « ventes comptées » vs « ventes utilisées ») :

| Lecteur | Verdict |
|---|---|
| tableau (`ligne2_terrain_zone`) | **sain** — pas de borne ; médiane et `n` sur la MÊME population (ratios non nuls). Les 8 médianes communales sont inchangées. |
| fiche commune — prix acté (`prix_ancien_communes`) | **sain** — `n` = `count(*)` du MÊME filtre `_BAROMETRE_RETENUE` (bornes incluses) que la médiane. |
| fiche parcelle / Estimer (`comparateur_terrain`) | **sain** — le pool est déjà borné en SQL `[50 ; 20 000]` ; `n` servi = effectif retenu (trimé), même population. |
| Assemblage (« marché de la zone ») | **sain** — lit `ligne2_terrain_zone`. |
| Étude de zone (`zone.py::prix_par_type_zone`) | **sain** — `n` et médiane tous deux `FILTER (bornes)`. |
| Radar (`pige/signaux.py`) | **sain** — `n = count(*)` et médiane sur la même population (pas de borne). |
| **Bilan mode B** (`faisabilite/bilan.py::_prix_terrain_local`) | **lisait le cache contaminé** → corrigé par le rebuild (seuil sur `n_ventes` désormais in-bornes). |
| **Comparer / fiche §8** (cache `dvf_secteur_medianes`) | **le défaut** — corrigé (builder + rebuild). |

### Reconstruction du cache (autorisée, cette table seule)
- **a.** Sauvegarde `dvf_secteur_medianes_bak__20261124_fix6` · EMPREINTE_AVANT = lignes 2354 ·
  checksum -25299229330 (Σ hashtext colonnes métier, hors `computed_at`).
- **b.** `compute_medianes_secteur` lancé à **19 h 40 (Indian/Reunion)**, hors 13 h 30–14 h →
  {lignes 2354, secteurs 848, ventes 38097}. EMPREINTE_APRÈS = 2354 · -19351249823.
- **c.** (`scripts/communes_fix6_cache_after.py`, `LOT1-cache-apres.txt`) :
  - 97411000IZ terrain = **284 €/m² · 14 ventes** (était 18) ;
  - 97415000CD terrain = **n=1 → NON servi par Comparer** (1 < 8) ;
  - `n_ventes` du cache == ventes dans les bornes recalculées par `ACTE_TERRAIN_NU_CTE` : **0 divergence**
    sur 786 sections (l'effectif = exactement les ventes utilisées, aucun local / multi-commune ne
    subsiste puisque le CTE unique les exclut déjà) ;
  - sections qui **PERDENT leur prix servi** (med non nulle, n≥8 → n_bornes<8) = **76** (exactement l'attendu) ;
  - plus gros écarts d'effectif : 97424000AM 52→21, 97412000CE 55→25, 97423000AK 70→45, … CD 13→1.
- **d.** Cohérence (base reconstruite, `LOT1-coherence.txt`) : **87 passed · aucun écart (1 €/1 m²) sur
  les témoins.** AUCUN témoin du Bilan ne bouge (tous les lecteurs lisent le même cache reconstruit → ils
  restent cohérents). Rien à arrêter, aucun témoin modifié. (Si un témoin avait bougé, je me serais arrêté
  ici avec témoin / ancien / nouveau / acte retiré.)
- **e.** RETOUR ARRIÈRE (testé sur copie TEMP → revient à 2354 · -25299229330) :

```sql
BEGIN;
TRUNCATE dvf_secteur_medianes;
INSERT INTO dvf_secteur_medianes
       (secteur, type_bien, n_ventes, mediane_valeur, mediane_prix_m2, fenetre, computed_at, millesime_dvf)
SELECT  secteur, type_bien, n_ventes, mediane_valeur, mediane_prix_m2, fenetre, computed_at, millesime_dvf
FROM    dvf_secteur_medianes_bak__20261124_fix6;
COMMIT;
-- contrôle : lignes=2354, checksum=-25299229330
```
Aucune autre table de `labuse` écrite.

---

## LOT 2 — révision datée de la dernière pièce
- **La Plaine-des-Palmistes** (`config/veille_plu.yaml` 97406) : `etat_source_date` 2023-05-27 → **2025-11-27**
  (pièce municipale confirmant la révision en cours) ; `source` nettoyée (plus de note interne).
- Front (`ContextePanel.tsx`) : pour une commune **« en révision »**, le bandeau ET le détail portent la
  date de la DERNIÈRE PIÈCE (`etat_au`), pas la prescription. Vérifié servi : Plaine « pièce la plus
  récente au 27/11/2025 » (était 24/09/2015/2023-05-27) ; Saint-Denis 23/04/2026.

---

## LOT 3 — CatNat « et N autres » sur le total source
`frontend/src/lib/catnat.ts` : `catnatReste(totalPerils, detailLen, montres)` = `(totalPerils ?? detailLen)
− montres`. Le détail reste tronqué (6 affichées) mais le reste se calcule sur le TOTAL (`catnat_perils`,
servi) : Saint-Paul 24−6 = **18**, Saint-Denis 21−6 = **15**. vitest 4/4 vert.

---

## LOT 4 — éditorial
- **Carte Urbanisme** : la ligne de source affiche `plu_statut.source_citation` (collectivité + date de
  la pièce) + le lien `source_url`, PLUS la note interne « OUTIL-COMMUNES-FIX-… » (chaîne `source` brute,
  conservée pour l'admin mais jamais affichée). Ex. « Ville de La Plaine-des-Palmistes — en révision,
  pièce la plus récente au 27/11/2025 ». `normDatesFr` (bricolage d'affichage) retiré.
- **Compteurs techniques** (`fiche_commune.py` `outils_counters` + `_FALLBACK["outils"]`) : None =
  **indisponible** quand la source échoue, jamais 0 (le `or 0` transformait un échec en faux zéro). Types
  TS passés `number | null`.

---

## Vérifications finales
- Filet : `tests/test_communes_fix6.py` + `tests/test_communes_cas_externes.py` = **16 passed** (base
  reconstruite) ; vitest `catnat.test.ts` = **4 passed**.
- Front `tsc -b` : OK.
- Cohérence (12 témoins, base reconstruite) : **87 passed, aucun écart**.
- Cache `dvf_secteur_medianes` reconstruit ; sauvegarde `dvf_secteur_medianes_bak__20261124_fix6`
  conservée ; rollback testé sur copie TEMP. Aucune autre table de `labuse` écrite.
- Clos par le rapport (8 médianes communales, 24 compteurs CatNat, 24 trimestriels) : inchangé.
- Pas de fusion dans `main`.
