# CALCULS-AUDIT-1 — chaque calcul, refait par quelqu'un d'autre

**Branche** `audit/calculs-1` (worktree `labuse-calculs`, base `origin/main` post-merge FRONT-CHIFFRES-2, HEAD `2caa2728`). Lecture seule sur `src/` ; le banc gagne des tests. Run servi **`q_v11_m137`**, base `labuse` (431 663 parcelles). Échantillon gelé de COHERENCE-1 (120 parcelles, 24 communes).

## FAUX en tête

**0 FAUX-CLIENT numérique confirmé.** Chaque calcul recalculé indépendamment reconcilie avec la valeur servie : **1 185 comparaisons, 0 écart** hors tolérance sur l'échantillon gelé et les cas limites construits.

> Une suspicion a été levée en cours de route et **infirmée par vérification** : les forfaits de taxe d'aménagement codés (piscine **251 €/m²**, stationnement **2 928 €/place**) sont les **valeurs officielles 2026** (economie.gouv.fr, art. 1635 quater J) — pas une dérive. De même la valeur forfaitaire **892 €/m²** hors Île-de-France est bien la valeur 2026 (2025 = 914, révisée à la baisse par indexation ICC). Le code est **conforme**.

## Ce qui a été fait

- **Lot A — inventaire** (`CALCULS.csv`, 57 calculs cœur) : chaque fonction du back qui fabrique un chiffre servi, avec formule en français, entrées + id, constantes + origine, unités, arrondi, comportement sur entrée absente. Huit domaines : résiduel/capacité, gabarit, faisabilité/bilan/défisc, terrain (pente/hauteur/expo/solaire), taxe d'aménagement, DVF/médianes/marché, aléa/intersection/zone, score/signal/agrégats commune.
- **Lot B — recalcul indépendant** (`scripts/coherence/recalcul/`, aucune fonction de calcul de prod importée pour recalculer) rejoué sur l'échantillon gelé + cas limites. Résultat : `ECARTS-CALCUL.csv` **vide (0 écart)**.
- **Lot C — constantes** (`CONSTANTES.csv`, 31 constantes) : réglementaires vérifiées, hypothèses LABUSE documentées, et **origines inconnues** listées à part.
- **Lot D — permanence** : `tests/verrous/test_calculs1_recalcul.py` (5 tests, verts) + banc rejouable `python -m scripts.coherence.recalcul.banc_calcul`.

## Recalculs joués (tous à 0 écart)

| Calcul | Recalcul indépendant | Comparé à | Vérdict |
|---|---|---|---|
| `surface_m2` | `ST_Area(geom_2975)` | fiche/table servie | ✅ 120/120 |
| `pente_bande` | réimpl bornes degrés | fiche `terrain.pente_bande` | ✅ |
| `ppr_pct`, `mouvement_terrain_pct` | `100·intersectantes/total` (SQL indépendant) | contexte commune | ✅ |
| médiane €/m² secteur (maison, appartement) | **médiane Python** (interpolation) sur `dvf_mutations_parcelle` brut | table `dvf_secteur_medianes` **et** fiche `dvf_parcelle.secteur` | ✅ ~400 secteurs |
| marge surélévation (2 chemins), écart faîtage/BD TOPO, densité `pct_residuel=max(0,100−pct_consomme)`, niveaux `max(1,round(égout/3))` | identités reconstruites des autres chiffres servis | fiche `potentiel_transformation`/`le_bien` | ✅ |
| taxe d'aménagement : assiette, total, RAP | réimpl formule + **constantes officielles 2026** | `taxe_amenagement.calculer` sur 7 cas limites | ✅ |
| taux communal servi | table `taxe_amenagement_taux.part_communale_pct` | fiche | ✅ |
| `mult_base = round(p/taux_base, 2)` | `taux_base = AVG(p_raw hors copro)` recalculé | table `parcel_p_score_v2` | ✅ |
| frontières palier Signal (0,20/0,10) & bandes Score (80/50/30) | réimpl, cas aux bornes exactes | intention documentée | ✅ |

Méthode : forks lecture-seule pour l'inventaire (8 sous-agents, un par domaine) ; recalcul par réimplémentation Python à partir des tables **brutes**, jamais du code de calcul ; comparaison recalcul ↔ servi par ligne, cause automatique par ordre de grandeur (×100 = unité, ×10000 = ha/m², ratio≈3 = constante d'étage, petit = arrondi). **Trois « écarts » initiaux étaient des bugs du recalcul lui-même** (identité `pct_consomme+pct_residuel=100` fausse — le vrai est `pct_residuel=max(0,100−pct_consomme)` ; clamp de surélévation non appliqué ; filtre sous-type aléa manquant) — corrigés, ce qui a **validé la discipline** (le recalcul doit être aussi juste que la cible).

## Écarts d'homogénéité et risques structurels (NON FAUX — à instruire par un FIX)

Le recalcul ne produit pas de divergence numérique, mais l'inventaire a mis au jour des fragilités réelles, cohérentes donc invisibles au banc :

1. **Marge de surélévation — deux chemins clampent différemment.** Chemin *estimé* (BD TOPO) : `marge = max(0, règle−bâti)` → un bâti **plus haut que la règle** affiche **0**. Chemin *sourcé* (LiDAR HD) : marge **brute**, affiche le négatif (témoin BZ1065 = **−3,3 m**). Même réalité (« déjà au-dessus »), deux rendus. Verdict `possible=False` identique → non FAUX, mais **à homogénéiser**.
2. **`zone.py:contraintes_plu` et `zone_demain` — pas de `ST_Union`.** Deux polygones PLU qui se chevauchent double-comptent : la somme des parts peut **dépasser 100 %** ; les hectares AU sont sommés sur l'aire **entière** (pas la part dans la zone). Contraste avec `risques_zone`/`assainissement_zone` qui, eux, dédoublonnent.
3. **`zone_servie.py:zone_dominante` — `GROUP BY token` SANS commune.** Une parcelle **à cheval sur deux communes** ayant le même token de zone (« U2 ») verrait leurs surfaces fusionnées → part surestimée, `a_cheval` possiblement raté. `contraintes_plu` inclut la commune, lui.
4. **`compute_bilan` (calculette) — `coef = 1 − (marge+honoraires+frais)/100` sans garde.** Une saisie libre `marge_frais > 100 %` rend le coef **négatif** → charge foncière absurde négative. `coef_rendement = 0` → repli `surf` qui **change silencieusement l'unité** (vendable traité comme plancher).
5. **`dvf_mediane.py` — bornes (1000–12000) et seuil N=5 en LITTÉRAUX** alors que `marche_service`/`filtre_params` lisent les mêmes depuis `dvf_profils.yaml` : **double source de vérité**, dérive possible. Quatre seuils d'effectif différents coexistent (5 / 8 / 10 / 30) dont deux non tracés.
6. **Convention de pente non uniforme** : `exposition`/`solaire` produisent des degrés, `profil_altimetrique` des pourcents, `pente_fmt` convertit °→%. Aucun consommateur ne les mélange aujourd'hui, mais rien ne l'empêche.

## Lot C — constantes à mettre à jour / surveiller

- **Défisc — péremption silencieuse en 2027.** `ANNEE_ACTIVE = 2026` est **figée en dur** (`defisc.py:14`) et les plafonds de loyer (12,21 / 12,71 €/m²/mois) sont sourcés BOFiP 2026 : sans mise à jour en janvier, ils serviront périmés sans alerte. **À re-millésimer / indexer.**
- **Forfait stationnement délibéré (5 857 €/place)** défini au YAML mais **jamais lu** par `calculer` : une commune qui vote le forfait majoré ne le verra pas appliqué.
- **`part_departementale_defaut = 2,5 %`** appliqué à toutes les communes (plafond) — over-estimation si une commune vote moins.
- **Origines inconnues** (à documenter ou dériver) : `VRD_VOIRIE_INTERNE_PCT = 40 %`, coefficients de `market_signal`, bandes du Score LABUSE (80/50/30), seuils de pente (10/25/40 %), `PENTE_PLATE = 3°`. Voir `CONSTANTES.csv`.
- **`prix_m2_lls = 2 900`, coût construction 2 300–2 800, prix neuf par bassin** : hypothèses « Estimé » non re-datées ; ancrent la charge foncière — à re-millésimer.
- **Score LABUSE** : barème « PROVISOIRE, à RE-CALER » (30 témoins) — **mais non servi** sur `q_v11_m137` (`score_labuse` ne contient que q_v15, cf. ALGO-AUDIT-1). Aucun impact client actuel ; à re-caler avant de le servir.

## Lot D — permanence

- `tests/verrous/test_calculs1_recalcul.py` : taxe sur cas limites, frontières palier/bande, médiane indépendante, conversion pente, **couverture des domaines** (un calcul dans un nouveau domaine sans recalcul indépendant fait échouer le test). 5 verts.
- Banc rejouable : `PYTHONPATH=src python -m scripts.coherence.recalcul.banc_calcul` (échantillon gelé, ~7 min, lecture seule). Chaque module de `recalcul/` est un recalcul indépendant réutilisable par le job nocturne sur l'échantillon et par V6b sur les témoins présents.

## Chiffres

- **57** calculs inventoriés (cœur ; l'inventaire complet des 8 domaines couvre ~90 fonctions productrices de chiffre).
- **1 185** comparaisons de recalcul · **0** écart hors tolérance.
- **0** FAUX-CLIENT numérique · **6** risques structurels instruits (non recalculables sur l'échantillon) · **~10** constantes à documenter/re-millésimer.

## Limites (dites, jamais silencieuses)

- Le recalcul couvre les calculs **parcelle/commune tractables** (surface, pente, médianes, hauteurs/surélévation, taxe, mult_base, %intersection). Les moteurs **gabarit** (enveloppe géométrique) et **bilan promoteur** (charge foncière) sont **inventoriés et audités par lecture** (formules + constantes), mais leur recalcul géométrique/financier complet dépend de coefficients de faisabilité (COS/emprise/reculs, coût construction) fabriqués dans `engine.py`/`db.py` — recalcul géométrique indépendant = chantier d'un second mandat.
- La valeur SERVIE est lue en-process (TestClient FastAPI) ou en table de résultat — jamais recalculée par le code de prod côté « recalcul ».
- Score LABUSE non servi sur le run courant → recalcul limité aux frontières (formule), pas de comparaison sur données.

## Livrables

```
docs/audit-2026-09/CALCULS-1/
  RAPPORT.md            (ce fichier)
  CALCULS.csv           (lot A — 57 calculs, pipe-délimité)
  CONSTANTES.csv        (lot C — 31 constantes, pipe-délimité)
  ECARTS-CALCUL.csv     (lot B — 0 écart : en-tête seul)
scripts/coherence/recalcul/
  socle.py  dvf.py  geometrie.py  residuel.py  taxe.py  score.py  banc_calcul.py
tests/verrous/test_calculs1_recalcul.py   (lot D — 5 tests)
```
