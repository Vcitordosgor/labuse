# CHIRURGICAL-FIX-1 — LOT L (5ᵉ passage du relecteur)

**Branche** `fix/chirurgical-l` (depuis `origin/main` après `git fetch`). **Pas de merge.**
Hook pré-push **VERT sans `--no-verify`** (unit `not db/local/reel/network` + front + cohérence).
Livraison : `~/Desktop/chasse-1/_lot-final-5/` + `_saisies.json`.

> « Tout est validé sauf le Bilan, qui reste bloquant. » Les cinq points portaient sur le Bilan
> (1-4) et sur quelques restes hors Bilan (5). Quatre parcelles témoins :
> **BW2635** `97422000BW2635` (Uav, Le Tampon), **AM0838** `97404000AM0838` (UE, L'Étang-Salé,
> habitat interdit), **AD0887** `97422000AD0887` (Ud, Le Tampon), **IS0448** `97411000IS0448`
> (Uh, Saint-Denis, bâti conservé → 0 m² en l'état, 85 m² en terrain libéré).

---

## 1 — Un seul calcul, deux rendus

**Constat.** Pour la même saisie, le PDF et l'Excel donnaient des **dépenses différentes**
(AM0838 : 1 181 735 € vs 21 482 500 € ; AD0887 : 2 474 553 € vs 4 103 771 €). Le PDF injectait la
contenance **après** le calcul (la ligne « achat » restait donc vide) et préremplissait la taxe
d'aménagement + l'archéologie que l'Excel laissait à zéro.

**Correctif.** Un objet calculé **UNIQUE** — `api/bilan.py::_entrees_servies(db, idu, corps)` —
assemble le terrain (cadastre) **dans** le calcul et fusionne les postes sourcés (taxe + archéologie).
Les deux routes (`/bilan/{idu}.pdf` et `.xlsx`) partent de **cet objet** ; le terrain rendu sur le
PDF est **celui entré dans le calcul** (`_prog["terrain"] = e.programme.terrain`). Un seul
`Moteur().calculer(e)`.

**Preuve permanente.** `tests/test_chirurgical_fix_l.py` :
- `test_l1_excel_recalcule_le_meme_bilan` (×4 parcelles) — le classeur, évalué par un **moteur de
  formules indépendant** (jamais le moteur Python), rend **CA, dépenses et résultat égaux à l'euro**
  (résultat « non calculable » des deux côtés quand un coût majeur manque).
- `test_l1_tableur_tiers_formulas_confirme` — vérification **croisée par le tiers `formulas`** :
  AD0887 CA 3 432 810 € / dépenses, identiques au moteur, indépendamment de notre évaluateur.
- `test_l1_un_seul_objet_calcule_dans_les_deux_routes` — `_entrees_servies` dans les **deux** routes.

---

## 2 — Le garde-fou

**Constat.** Il comparait la SDP saisie à l'**estimation haute** (AD0887 1 047, BW2635 3 317), pas à
la **« surface à retenir »** du Dossier (AD0887 795, BW2635 360). Le scénario « terrain libéré »
n'était pas annoncé en tête, et l'Excel figeait l'alerte.

**Correctif.** `bilan/reperes.py::garde_fou_bilan` compare à **`surface_a_retenir`** (le scénario
retenu du Dossier), détecte le **terrain libéré** et le **coût de démolition non chiffré**.
Dans l'Excel, l'alerte « SDP > surface à retenir » devient une **formule VIVANTE**
(`=IF(AND(SDP>0, SDP>surface_à_retenir), "⚠ …", "")`) qui réagit quand on change la surface.

**Preuve.** `test_l2_garde_fou_vise_la_surface_a_retenir`, `test_l2_avertissement_sdp_est_une_formule_vivante`.

---

## 3 — Une saisie invalide bloque tout

**Constat.** Un coût négatif (−250 000 € sur AD0887 → 128 % de marge) ou une TVA hors [0, 100 %]
ne faisait réagir qu'une ligne.

**Correctif.** Une **cellule de validité unique** (`I1`, hors zone visible) teste toutes les saisies
(`< 0`) et toutes les TVA (hors [0, 1]) ; **résultat net, cash-flow, marge ET les quatre ratios**
la lisent (`=IF(I1<>"", "saisie invalide", …)`).

**Preuve.** `test_l3_cellule_validite_unique_lue_partout` (I1 référencée par ≥ 6 formules de résultat).

---

## 4 — Des scénarios que l'outil propose lui-même

Livraison par les **vraies routes HTTP** (compte authentifié, comme l'écran), **deux régimes** :

| Parcelle | Régime | Programme | Résultat |
|---|---|---|---|
| **AD0887** | constructible — *Bilan depuis l'Étude* | 795 m² · 8 lots (scénario) · **4 318 €/m²** neuf VEFA commune (36 ventes) · reste = prefill outil | CA 3 432 810 € · **non calculable** (achat/constr non préremplis) |
| **BW2635** | constructible — *Bilan depuis l'Étude* | 360 m² · 4 lots (scénario) · **4 547 €/m²** neuf VEFA secteur (10 ventes) · reste = prefill outil | CA 1 636 920 € · **non calculable** |
| **AM0838** | sans capacité (habitat interdit) | **AUCUN** programme injecté | CA 0 · **non calculable** + garde-fou « Habitat interdit » |
| **IS0448** | sans capacité (pas d'Étude exploitable) | **AUCUN** programme injecté | CA 0 · **non calculable** + garde-fou « terrain libéré » |

- Pour les **constructibles**, seules la surface, les lots (scénario retenu de l'Étude) et le **prix
  de vente du neuf servi** pour le secteur (`resolve_prix_neuf_marche`) sont posés ; **chaque
  hypothèse est nommée dans le document** — l'en-tête du PDF porte désormais *« Programme : scénario
  de l'Étude (8 lots, 795 m²) · prix de vente = neuf VEFA commune · Prix demandé : 4 318 € »*
  (`_hypotheses_bilan` ; auparavant figé à *« aucune Étude reliée · non renseigné »*, ce qui
  contredisait le contenu). Ce que l'outil ne préremplit pas (coût d'achat, coût de construction,
  TVA de vente) **reste vide** → **« non calculable »**. Les sans-capacité gardent, à juste titre,
  *« aucune Étude reliée »* (aucun programme injecté).
- Pour les **sans capacité**, **aucun programme fabriqué** : le Bilan livré est celui que l'outil
  produit **de lui-même** (terrain + taxe + archéologie préremplis) avec **son garde-fou en tête**.
  L'export d'un Bilan sans CA n'est autorisé **que** parce qu'il porte un garde-fou
  (`_refuser_si_ca_nul(…, autorise_sans_ca=…)`) ; sinon 422.
- **Toutes les pièces** passent par des routes HTTP : `/dossier/{idu}.pdf`, `/apporteur/{idu}.pdf`,
  `/analyse-annonce/{idu}.pdf`, `/pre-dossier/{idu}.zip`, `/comparatif.pdf`, et les Bilans
  (`POST /bilan/{idu}/generer` → `GET .pdf` / `.xlsx`). AM0838 → **pré-dossier 422** (non
  constructible), ce qui est le comportement attendu.
- Le cas **« programme saisi quand même »** (ce que le fichier livré ne montre pas) est prouvé par
  **`test_l4_programme_saisi_sur_non_constructible_est_averti`**, pas par un fichier.

**Script** : `scripts/lot_l_livraison.py` — aucun programme écrit à la main, terrain pris au cadastre.
**Preuves** : `test_l4_script_livraison_deux_regimes`, `test_l4_export_sans_ca_autorise_seulement_si_garde_fou`.

---

## 5 — Restes hors Bilan

- **AD0887 §5** : plus de « aucun rédhibitoire » ; la **zone humide est nommée avec sa part** (lu
  depuis `fiche.lines` quand `contraintes_parcelle_liste` est absent).
- **IS0448 couverture** : la tuile SDP dit **« 0 m² — bâti existant saturé (potentiel en terrain
  libéré) »**, plus un « 0 m² » muet.
- **« Unité foncière »** au lieu de « parcelle » pour le sol (perméable / pleine terre).
- **Comparatif** : couverture **compacte** (`cmp-cover`, plan borné), plus de page quasi vide.

Vérifié **dans les fichiers livrés** (routes HTTP) : AD0887 nomme la zone humide + part, sans
« aucun rédhibitoire », avec « unité foncière » ; IS0448 porte « saturé » + « terrain libéré ».

---

## Livrables

`~/Desktop/chasse-1/_lot-final-5/` : 4 Bilans (PDF + Excel), 4 Dossiers, 4 Apporteurs, 4 Estimer,
3 pré-dossiers (AM0838 refusé à juste titre), 1 Comparatif, `_saisies.json` (route + saisie exacte
de chaque fichier). Gardes : `tests/test_chirurgical_fix_l.py` (12). Commits sur `fix/chirurgical-l`.
