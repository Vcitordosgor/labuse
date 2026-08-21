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
mandat scoring dédié. Hors périmètre du chantier PDF (M128).

---

## Mise à jour M128-5 (2026-08-21)

**Arbitrage rendu (Vic)** : `score_e` reste sur sa méthode, **aucune bascule**. La divergence est
donc **permanente jusqu'au mandat de fond**. En conséquence, dans ce mandat :

1. **Marge `score_e` retirée du scoreur d'adresse** (`api/scoreur.py`) — la réponse ne sert plus
   `score_e` (ni `libelle_court` ni les montants de marge). Seuls `charge_supportable` /
   `prix_probable` restent lus en interne pour QUALIFIER un prix saisi (badge marché sur
   `prix_probable`, repère **non divergent**). *Aucun chiffre de marge auto-affiché à un tiers.*
2. **Libellé fiche premium / écran renommé** (`app.py`, `score_e_block`) — transformation
   **read-time** : « Marge estimée » → « Repère sectoriel (barème) », « charge foncière
   supportable » → « charge au barème sectoriel », « marge foncière » → « repère sectoriel ». Les
   termes « marge foncière estimée » / « charge foncière supportable » restent **réservés à la
   méthode documents**.
3. **Filet read-time sur `score_e.detail`** — « ± 12 %, validée sur cette commune » (verdict *live*,
   non fondé — cf. M128-2-C10 qui n'a corrigé que la fonction, pas la colonne figée) est **masqué au
   rendu** → « ± 12 % ». **Condition de levée** : au prochain **rebuild de la table `score_e`**
   (`build_score_e`), la colonne `detail` sera régénérée avec le libellé corrigé ; le filet read-time
   pourra alors être retiré de `app.py`.

**Exposition `_prix_verdict` — CLÔTURÉE par M128-6.** Le verdict de prix opt-in du scoreur (quand un
tiers SAISIT un prix) calculait `marge_a_ce_prix = charge − prix` avec la `charge` de `score_e`
(méthode divergente) et emettait des verdicts (« dans le marché », « rentable »…).
Corrigé (commit M128-6) :
- **Branché sur la charge de la méthode DOCUMENTS** (`compute_bilan_servi`, à la volée, 37–237 ms
  mesurés — non prohibitif, éphémère, aucune bascule). Plus aucune charge `score_e` servie à un tiers.
- **Renommé `_prix_constat`** et **vidé de tout verdict** (§1.3) : ne sert que des NOMBRES (prix saisi,
  prix probable + écart, charge documents, marge à ce prix) + méthode. Front-end (`ScoreurAdresse.tsx`)
  et harnais QA (`qa/m137s/…`) alignés.

**Balayage complet des surfaces (M128-6-§1.4)** — aucune autre route ne sert un chiffre dérivé de
`score_e` à un tiers :
- `scoreur d'adresse` → charge **documents**, constat nu (fait ci-dessus) ;
- `fiche premium / écran` (`score_e_block`) → **renommé** « barème sectoriel » (M128-5), surface
  OPÉRATEUR, jamais un verdict ;
- `radar` (`app.py`) → `score_e.marge_estimee` / `charge_supportable` en **prédicat de filtre**
  (`EXISTS … WHERE`) uniquement, le nombre n'est pas servi ; route opérateur (authentifiée) ;
- `argumentaire` → `score_e_affiche` lit la charge **documents** (`compute_bilan`), pas la table
  `score_e` — méthode documents, pas divergente.

## Dette §2 (vendable > gabarit × rendement) — CLÔTURÉE par M128-5-§1

Corrigée à la SOURCE dans `engine.py` (commit de ce mandat) : le vendable suit un **chemin central
unique** (`habitable ÷ taille moyenne`, puis plafonds), au lieu de la moyenne d'une fourchette de
comptes (qui surestimait de ~1 % par inégalité arithmético-harmonique). Sans plafond,
`vendable = habitable` par construction. Mesure : overshoot systématique **62,6 % → rien au-delà de
l'arrondi** (résidu ≤ 0,6 m² absolu = arrondi de `surface_plancher_m2` sur petites parcelles). Aucun
`min()` contre le gabarit posé. Dette close.
