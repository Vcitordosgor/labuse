# M13 — LOT A : Filtres, audit et vérité (BLOQUANT)

**Branche** : `fix/m13-a-filtres` · **Base** : `main` (M12 mergée).
**Golden** : 116/116 PASS (`LABUSE_DEV_MODE=1`, run `q_v7_defisc`). **Build** : 0 erreur.
**Preuves** : `qa/m13/A/*.png` (script reproductible `qa/m13/cap_A.mjs`).

## A1 — Diagnostic « Procédure collective » : CAUSE RACINE TROUVÉE

**Requête du filtre** : `EXISTS parcel_v_score.signals` avec `code IN` du groupe `pcl`. En M12, le groupe = `[BODACC_LJ, BODACC_LJ_CLOT, BODACC_RJ, BODACC_SAUVEGARDE, BODACC_RADIATION]`.

**Le bug** : `BODACC_RADIATION` **n'est pas une procédure collective**. C'est une **famille distincte** (`radiation`, cf. `models.py:739`), pondérée **0 point** — « anti-signal Phase 0 » (`score_v_constants.py:82`, label « Radiation < 36 mois »). Une parcelle « radiation seule » a `v_score = 0`, `v_band` absent → **sa fiche n'affiche AUCUNE procédure**. Elle était pourtant servie par le filtre → **faux positif** (le péché mortel de la boussole).

**Chiffres (run servi, vérifiés en base) :**
- `pcl` AVEC radiation (M12) = **314 retournés**, dont **92 « radiation seule » = faux positifs**.
- `pcl` SANS radiation (corrigé) = **222 parcelles**, toutes avec une vraie procédure (LJ 91 / LJ clôturée 76 / RJ 52 / sauvegarde 3, pondérées 20-35, **affichées** sur la fiche).
- **5 parcelles retournées vérifiées à la fiche** (échantillon seed 974) : `…1214`, `…0377`, `…1246` (SANS radiation) → **3/3 montrent la procédure**. Les faux positifs radiation-seule (`97401000AL0823`, …) → fiche `v_band` None, **0 procédure**.

## A2 — Correction

`frontend/src/lib/filters.ts` : **`BODACC_RADIATION` retiré du groupe `pcl`**. Codes conservés = les vraies procédures collectives, toutes pondérées > 0 et affichées sur la fiche → **toute parcelle retournée porte réellement le signal**.

**Sous-couverture (rattachement)** : la base `bodacc_procedures` compte **662** procédures ; **222** sont rattachées à une parcelle du run servi (**~34 %**). L'écart = propriétaires non rattachés à une parcelle (société sans foncier, ou match SIREN↔parcelle absent) — **pas une jointure cassée**. Conformément au mandat, **on n'élargit pas le filtre pour faire du volume** : 222 justes valent mieux que 314 douteuses.

## A3 — Audit des 14 filtres (compte + 3 fiches vérifiées + verdict)

| Filtre | Retour (run servi) | 3 fiches vérifiées | Verdict |
|---|---|---|---|
| **Procédure collective** | 314 → **222** (corrigé) | 3/3 montrent la procédure (après fix) | **corrigé** (était sur-inclusif) |
| Avec événement (BODACC) | 40 | 3/3 montrent l'événement | juste |
| Veille succession | 7 092 | badge liste / radar patrimonial (hors signaux V fiche) | juste (nature différente) |
| Masquer les copropriétés | (toggle de masquage, 3 424 copros) | n/a (pas un signal) | juste |
| Pollution (`sol_pollue`) | 10 333 | **8/8** montrent le flag (re-vérifié) | **juste** |
| ABF | 60 618 | 3/3 | juste |
| ICPE | 66 820 | 3/3 | juste |
| Risques (PPR/aléa) | 403 865 | 3/3 | juste mais **quasi-universel (93,6 %)** → discriminant faible (signalé, non masqué) |
| Prescription PLU | 127 513 | 3/3 | juste |
| Friche | 1 526 | 3/3 | juste |
| Propriétaire hors île | 944 | 3/3 | juste |
| DPE F-G | 27 | 3/3 | juste (data mince) |
| Détention longue | 10 814 | 3/3 | juste |
| **Dirigeant 65+** | **0** | — | **mort** — codes `RNE_DIRIGEANT_*` absents des données ET pondérés 0. **Déjà masqué** (M12-E1, `Header.tsx`) — reste masqué. |

**Fausse alerte écartée honnêtement** : un premier passage automatique a marqué `sol_pollue` « sur-inclusif (1/3) ». Re-vérification à 8 fiches (timeout élargi) : **8/8 montrent le flag, 0 vrai manque** — les 2 « manques » initiaux étaient des **timeouts de fetch de fiche**, pas des faux positifs. Le filtre est **juste** ; je ne fabrique pas un problème inexistant.

## Verdict du lot

**Un seul filtre était réellement faux : « Procédure collective » (radiation).** Corrigé. Tous les autres sont justes (fiche vérifiée) ou déjà masqués (Dirigeant 65+). Aucun filtre douteux ne reste servi.

## Preuves (`qa/m13/A/`)
- `01_resultats_procedure_collective.png` — 79 résultats du filtre pcl corrigé (deep-link `#f=1&vs=pcl&v=1`).
- `02_panneau_filtre.png` — panneau « + Filtre », « Procédure collective » actif.
- `03_fiche_montre_procedure.png` — fiche d'un résultat **affichant la procédure** (jugement de liquidation).
- Reproduire : app servie sur `:8020/socle/`, `node qa/m13/cap_A.mjs`.
