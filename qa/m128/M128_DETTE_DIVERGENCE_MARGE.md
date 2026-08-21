# M128 — DETTE : divergence de méthode « marge foncière » documents ↔ score_e

> **Créée le** 2026-08-21 par le commit **d36746b2** (M128-3 : SDP document = vendable ÷ rendement).
> **Statut : NON RÉCONCILIÉE — arbitrage Vic (M128-4 §1) : `score_e` reste sur sa méthode, aucune
> bascule.** La réconciliation attend le mandat de fond sur les hypothèses de bilan.
> **Ne pas corriger sans ce mandat.** Une divergence non écrite est une divergence qu'on
> redécouvre dans six mois — d'où ce registre.

## Le fait

Deux calculs différents portent le même libellé (« marge foncière estimée » / « charge foncière
supportable ») selon la SURFACE qui les affiche :

| | Méthode **documents** (banquier, dossier, fiche premium via `compute_bilan`) | Méthode **score_e** (marge servie — table `score_e`, `ingestion/score_e.py`) |
|---|---|---|
| SDP | `vendable ÷ coef_rendement` (0,80) | `sdp_residuelle_m2` (résiduel bâti) |
| habitable | = vendable (par construction) | `sdp_residuelle ÷ coef_plancher` (1,15) |
| coef CA (marge+frais déduits) | ≈ 0,76 (fourchette secteur) | 0,79 (constante) |
| coût construction | fourchette 2300–2800 €/m² | 2550 €/m² (valeur unique) |
| VRD | inclus | 0 |
| prix probable du foncier | médiane terrain sectorielle × surface | **identique** |

`prix_probable` est identique des deux côtés : **toute la divergence est dans la CHARGE.**

## La mesure (3 parcelles mandatées, 2026-08-21)

| Parcelle | charge score_e | charge document | marge score_e | marge document | écart marge (abs) |
|---|---:|---:|---:|---:|---:|
| 97420000AB0479 | 44 k€ | −16 k€ | **−17 k€** | **−77 k€** | 60 k€ (×3,6) |
| 97422000EM0120 | 244 k€ | 20 k€ | **+31 k€** | **−192 k€** | 223 k€ — **signe opposé** |
| 97413000DA0319 | 362 k€ | 126 k€ | **+240 k€** | **+4 k€** | 236 k€ (−98 %) |

La divergence n'est pas marginale : jusqu'au **signe opposé** (EM0120 : +31 k€ servi vs −192 k€
document). Elle vient entièrement de la charge (SDP + coef CA + coût différents).

## Surfaces d'exposition du chiffre `score_e` à un tiers

- **Scoreur d'adresse** (`api/scoreur.py`, router `/scoreur`) : renvoie `score_e.libelle_court`
  = `« Marge estimée : −17 k€ · Estimé »` (AB0479). Un tiers qui interroge une adresse voit ce
  chiffre.
- **Fiche premium / écran** (`app.py:3820`, `score_e_block`) : `libelle_court` + `detail`
  (« Marge estimée −17 k€ = charge foncière supportable 44 k€ − prix probable 61 k€… »).

**Collision de libellé** : le scoreur affiche « Marge estimée : **−17 k€** » et le dossier
banquier « Marge foncière estimée **−77 k€** » — POUR LA MÊME PARCELLE. Même vocabulaire
(« marge … estimée », « charge foncière supportable »), deux nombres. Constat remonté, **non
corrigé** (M128-4 §1.2).

> Effet de bord noté : `score_e.detail` (stocké) contient encore « ± 12 %, validée sur cette
> commune » — le fix M128-2-C10 a changé la FONCTION `niveau_label`, pas la colonne `detail`
> figée au dernier build de `score_e`. Se résorbe au prochain rebuild de la table (relève du
> mandat de fond, pas du chantier PDF).

## Résolution attendue

Réconcilier `score_e` sur la méthode `vendable ÷ 0,8` **changerait la marge SERVIE** → bascule +
mandat scoring dédié. Hors périmètre du chantier PDF (M128). Voir aussi la dette ouverte
« vendable > gabarit × rendement » (M128-4 §2, en attente d'arbitrage).
