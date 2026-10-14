# CHASSE-CALCULS-FIX-1 Lot 5 — moteur de secours (E-B3) & Gabarits incomplets (E-C2)

## 5.1 — Pourquoi ~21 % des parcelles à potentiel sortent en Gabarit « incomplet »

Causes classées en rejouant `build_gabarit_input` sur un échantillon de **500 parcelles servies par `residuel_legacy`** (celles où le gabarit a échoué). Rejouable : `_garde_eb3.py` / le script de classement cité au RAPPORT-FIX.

| cause (motif bloquant) | n / 500 | part | nature | corrigible en CODE ? |
|---|---|---|---|---|
| **voie / reculs non qualifiés** (limites non classées voie/séparative, recul non validé) | 234 | **47 %** | mixte géométrie + donnée | partiellement (classification `limites.py`), mais surtout parcelles enclavées / sans voie BD TOPO = **genuine** |
| **zone non calibrée** (hors calibrage PLU, règle `propose`/non validée, zone indéterminée) | 195 | **39 %** | **donnée** (calibrage PLU manquant) | **non** — relève de la calibration du règlement, pas du code |
| **voie privée non classée** (desserte par voie privée) | 36 | 7 % | genuine | non (exclusion honnête, critères voie privée) |
| **multi-zones** (géométrie du morceau constructible indisponible) | 20 | 4 % | géométrie | partiellement (calcul de la sous-zone) |
| **zone non constructible** (A/N) | 5 | 1 % | correct | non (c'est juste) |
| **gabarit OK** (migrerait vers le moteur gabarit) | 10 | **2 %** | — | déjà |

**Conclusion.** Le taux de `incomplete` n'est **pas** un défaut de code : il est **dominé par la donnée manquante** — **39 % = zones PLU non calibrées** et une grande part des 47 % « voie/reculs » = parcelles **réellement** enclavées / sans voie référencée. Le gisement **corrigible en code est faible (~2 % migrent immédiatement)**. Le vrai levier est la **calibration du règlement** (données PLU par commune) + l'enrichissement voirie — hors périmètre d'un correctif de code. **Aucune correction de code de la classification n'a donc été forcée** (risque élevé, rendement ~2 %) : le lot ferme E-B3 par la garde de service (5.2) et chiffre le gisement (5.3).

## 5.2 — Le moteur `residuel_legacy` ne sert plus d'intermédiaire impossible (E-B3) ✅

`_potentiel_transformation_block` (app.py) :
- lit `assiette_source` ; `estimation_simplifiee = (assiette_source == 'residuel_legacy')` ;
- **supprime** tout « % consommé » > 100 % du moteur simplifié (`pct_consomme = None`) — les valeurs absurdes de l'audit (BZ0007 `pct_potentiel` 640, AB0318 164 ; `taux_emprise_pct` 607/233) ne sont **plus servies** comme des faits ;
- sert `estimation_simplifiee` + `estimation_simplifiee_note` (« Estimation simplifiée — le gabarit réglementaire … n'est pas disponible pour cette parcelle »), rendu **fiche** (`constructibilite.tsx`) **et Dossier** (`blocs/potentiel.py`).

`taux_emprise_pct` n'est **jamais servi comme pourcentage** au client (uniquement des seuils booléens : nu `<5`, déjà bâtie `>0`, filtres carte) — donc aucun « taux d'emprise > 100 % » n'atteint l'écran. Garde : `_garde_eb3.py` **exit 0** (30 parcelles legacy > 100 % : plus aucun % servi, mention présente).

## 5.3 — Chiffrage de la migration legacy → Gabarit (nécessite un run)

- **Migration immédiate (code courant)** : ~**2 %** de l'échantillon legacy a un gabarit désormais `ok` → extrapolé aux **53 925** parcelles legacy ≈ **~1 100 parcelles** basculeraient de `residuel_legacy` vers `gabarit` **sans nouvelle donnée**.
- **Changement de SDP / de bande** : il ne peut être chiffré exactement **que par un run** (recalcul `compute_residuel` sur l'île, qui réaffecte `assiette_source` et recalcule la SDP). La SDP d'une parcelle qui migre change (assiette gabarit ≠ inset legacy) ; l'effet bande dépend du franchissement de seuils de score.
- **Potentiel large (avec donnée)** : la vraie réduction du taux `incomplete` passe par la **calibration PLU** des 39 % de zones non calibrées — projet de données séparé, non chiffrable ici.

→ Commandes exactes du run et périmètre au **RAPPORT-FIX.md** (Lot 7). **Rien n'est lancé.**
