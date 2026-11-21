# CHIRURGICAL-FIX-1 — LOT O (8ᵉ passage du relecteur)

**Branche** `fix/chirurgical-o` (depuis `fix/chirurgical-n` — LOT N n'est pas encore mergé à `main`,
or LOT O étend sa validité et ses alertes). **Pas de merge.** Hook pré-push **VERT sans `--no-verify`**.
Livraison : `~/Desktop/chasse-1/_lot-final-8/` + `_saisies.json`.

> « Les couvertures sont validées. Il reste sa liste fermée de deux points. »
> Parcelles témoins : BW2635 / AD0887 (Le Tampon), AM0838 (L'Étang-Salé), IS0448 (Saint-Denis).

---

## 1 — Le rejet s'étend à toute la feuille — **REMPLI**

**Constat.** (a) Une valeur d'ERREUR Excel (#N/A dans Relevé topo) **contaminait la cellule de validité
elle-même**, puis le CA, les ratios, le résultat. (b) Sur AM0838 / IS0448, « Total produits » gardait
quatre zéros après un rejet. (c) Sur les deux Bilans du Tampon, un coût invalide déclenchait à tort
l'alerte « surface vendable supérieure à la surface de plancher ».

**Correctif.**
- (a) En vrai Excel, `#N/A < 0` **propage** l'erreur à travers `OR`/`AND`, donc la cellule de validité
  `I1` devenait `#N/A`. On enveloppe désormais **chaque test** d'un `IFERROR(…, TRUE)` : une case en
  erreur → le test échoue → **invalide**, et `I1` ne porte JAMAIS une erreur (seulement « saisie
  invalide » ou « »). Une erreur/ un booléen collé est donc une saisie invalide, et **toutes les
  sorties** affichent « saisie invalide ».
- (b) « Total produits » (0 produit) était un **0 littéral** (non calculé). Il devient une **formule
  gatée** (`=0` enveloppé) → il suit la règle et affiche « saisie invalide » après un rejet.
- (c) **TOUTE** formule de la feuille — y compris les **alertes de surface** — est enveloppée par la
  validité : une alerte ne s'affiche que sur une **saisie valide** ; sinon « saisie invalide » (plus
  d'alerte à tort). Seule la cellule de validité est épargnée.

**Preuve — test de robustesse permanent étendu.** `test_o1_robustesse_erreurs_et_booleens` : pour
**chaque case de saisie**, on injecte négatif / texte / **#N/A / #DIV/0! / #VALUE! / booléen** / zéro /
décimal / énorme, recalcul par le moteur de tableur indépendant (`formulas`), et on vérifie qu'une
saisie invalide ne laisse **ni nombre ni erreur** (tout « saisie invalide ») et qu'une valide
recalcule. `test_o1_aucune_cellule_calculee_n_echappe` : on injecte #N/A dans un coût et on **parcourt
TOUTES les formules** (pas une liste écrite à la main) — mesuré : **207 cellules formule, 0 échappe**,
`I1` = « saisie invalide ». Gardes : `test_o1_validite_resiste_aux_erreurs_structurel`,
`test_o1_total_produits_sans_produit_suit_la_regle`, `test_o1_alertes_surface_gatees`.

---

## 2 — Les mêmes décimales dans le PDF et l'Excel — **REMPLI**

**Constat.** Le PDF arrondissait la surface de plancher avant de la comparer au seuil du Dossier
(595,1 m² alerte dans l'Excel et pas dans le PDF).

**Correctif.** **Aucun arrondi avant comparaison, dans aucun des deux contrôles** (SDP > surface à
retenir **et** surface vendable > surface de plancher), côté Python (garde-fou/PDF : `sdp_saisie >
sar_val`) **et** côté Excel (`{cell_sdp}>{surface_à_retenir}`, plus de `round`). L'alerte affiche
**assez de décimales** pour voir le dépassement (`_dec_m2` partagé : **595,1 contre 595**, pas 595
contre 595) ; une surface entière reste entière (« 595 », « 85 »).

**Preuve.** `test_o2_seuil_sans_arrondi_les_deux_cotes`, `test_o2_garde_fou_decimales_visibles`
(595,1 m² dépasse 595 m² → alerte ; 595,0 → pas de dépassement), `test_o2_moteur_suv_sdp_decimales`,
`test_o2_dec_m2_format`. Vérifié : garde-fou « La surface de plancher saisie (595,1 m²) dépasse la
surface à retenir du Dossier (595 m²). » ; formule Excel `=…IF(AND(B28>0,B28>595),…)` (seuil brut).

---

## Livrables

`~/Desktop/chasse-1/_lot-final-8/` : 4 Bilans (PDF + Excel), 4 Dossiers, 4 Apporteurs, 4 Estimer,
3 pré-dossiers (AM0838 refusé — non constructible), 1 Comparatif, `_saisies.json`. Toutes les pièces
par routes HTTP. Vérifié dans les fichiers livrés : la cellule `I1` porte l'`IFERROR` (résiste aux
erreurs) ; « Total produits » d'AM0838 est gatée. Gardes : `tests/test_chirurgical_fix_o.py` (9) +
`test_chirurgical_fix_{l,m,n}.py` / `test_bilan_excel.py` ajustés à l'enveloppe totale et au seuil
sans arrondi. Commits sur `fix/chirurgical-o`.

> **Base de branche** : LOT O part de `fix/chirurgical-n` (et non de `origin/main`, resté à LOT M)
> parce qu'il étend la cellule de validité et les alertes de surface introduites en LOT N. Le contenu
> de LOT N (couvertures nommées, bandeau distinction, validité durcie) y est donc présent.
