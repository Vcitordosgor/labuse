# CHIRURGICAL-FIX-1 — LOT R (11ᵉ passage du relecteur)

**Branche** `fix/chirurgical-r` (depuis `origin/main`, qui porte LOT Q). **Pas de merge.**
Hook pré-push **VERT sans `--no-verify`**. Livraison : `~/Desktop/chasse-1/_lot-final-11/` + `_saisies.json`.

> « Les trois cas passent, les alertes suivent les cellules. Il reste un point : avec 595,002 m²
> vendables contre 595,001 m² de plancher, ou 85,001 contre 85 sur IS0448, l'alerte se déclenche mais
> affiche la même valeur des deux côtés, parce que l'affichage s'arrête à deux décimales. »

---

## Le point — la précision d'une surface est le centième de m² — **REMPLI**

**Correctif — une règle UNIQUE (PDF, Excel, moteur).** La **précision d'une surface est le centième de
m²**. Les deux contrôles **comparent les valeurs arrondies au centième** et **affichent ces mêmes
valeurs à deux décimales au plus**. Un écart **inférieur à 0,01 m²** n'est donc **pas un dépassement**
→ **aucune alerte**, dans aucun format ; toute alerte affichée montre **deux valeurs distinctes**.

- Moteur / garde-fou / vraisemblance : `surface_depasse(a, b) = _round2(a) > _round2(b)`, avec
  `_round2` = arrondi au centième **moitié vers le haut** (`Decimal(str(x))` + `ROUND_HALF_UP`, comme
  la fonction **ROUND d'Excel** — pas `round()` de Python, qui arrondit au pair : 595,005 → **595,01**).
  Affichage : `fmt_surface_seule` rend la valeur **arrondie au centième**, 2 décimales au plus.
- Excel : les deux formules d'alerte comparent **`ROUND(cell,2) > ROUND(cell,2)`** et citent
  **`ROUND(cell,2)`** (`_xl_m2`). La comparaison arrondie **tient même sur une valeur collée** à trois
  décimales (elle ne dépend pas de la validation de saisie). Les surfaces de la synthèse gardent leur
  format décimal (`#,##0.## "m²"`).

**Preuve — les cas du relecteur, dans les deux formats** (`tests/test_chirurgical_fix_r.py`, 5 tests) :

| Saisie | Attendu | Mesuré (PDF & Excel) |
|---|---|---|
| 595,002 contre 595,001 | **pas d'alerte** | `surface_depasse` False ; Excel : alerte vide |
| 85,001 contre 85 | **pas d'alerte** | `surface_depasse` False ; Excel : alerte vide |
| 595,01 contre 595 | alerte, **distinctes** | « 595,01 m² … 595 m² » (PDF + Excel) |
| 595,006 contre 595 | alerte, **« 595,01 contre 595 »** | arrondi au centième affiché des deux côtés |

`test_r_egalite_pdf_excel_serie` : pour une **série** de surfaces autour du seuil
(Δ = 0 / 0,001 / 0,004 / **0,005** / 0,006 / 0,009 / 0,01 / 0,011 / 0,02 / 0,5 / 1), le **déclenchement
est strictement identique** PDF (`surface_depasse`) et Excel (`formulas`) — y compris au demi-centième
0,005, où `Decimal(HALF_UP)` reproduit `ROUND` d'Excel (595,005 → 595,01) ; et toute alerte affichée
porte bien **deux valeurs distinctes**. `test_r_regle_au_centieme_code` fige la règle (`PRECISION_
SURFACE_M2`, `surface_depasse` via `_round2`, `ROUND(.,2)` en Excel).

> Vérifié **dans le fichier livré** (`_lot-final-11/bilan_AD0887…xlsx`) : les deux formules d'alerte
> comparent `ROUND(cell,2)`.

---

## Livrables

`~/Desktop/chasse-1/_lot-final-11/` : 4 Bilans (PDF + Excel), 4 Dossiers, 4 Apporteurs, 4 Estimer,
3 pré-dossiers (AM0838 refusé), 1 Comparatif, `_saisies.json`. Toutes les pièces par routes HTTP.
Gardes : `tests/test_chirurgical_fix_r.py` (5) + les gardes m3/o2 ajustées (comparaison au centième).
Commits sur `fix/chirurgical-r`.
