# CHIRURGICAL-FIX-1 — LOT Q (10ᵉ passage du relecteur)

**Branche** `fix/chirurgical-q` (depuis `origin/main`, qui porte LOT P). **Pas de merge.**
Hook pré-push **VERT sans `--no-verify`**. Livraison : `~/Desktop/chasse-1/_lot-final-10/` + `_saisies.json`.

> « Les PDF sont validés, la synthèse du classeur aussi. Il reste un seul point. » Dans le classeur, le
> texte des deux alertes de surface était **figé à l'export** (valeurs écrites en dur dans la formule,
> `excel.py` ~128 et ~428) : après modification des cellules, AD0887 affichait « 555 contre 555 » pour
> 555,01 contre 555, et l'alerte sur la surface vendable gardait « 412 contre 555 ».

---

## Le point — les deux messages se construisent dans la formule, à partir des cellules — **REMPLI**

**Correctif.** Les deux alertes de surface de l'Excel ne portent **plus aucune valeur figée** : leur
texte se **construit dans la formule** à partir des cellules elles-mêmes, avec la **même règle
d'affichage que le PDF**.

- La **surface à retenir du Dossier** est posée dans une **cellule** (`I2`, libellé en `H2`). L'alerte
  « SDP > surface à retenir » compare `SDP` à `I2` et cite **les deux cellules** ; l'alerte « surface
  vendable > surface de plancher » cite la **surface vendable** et la **SDP**.
- Format d'une cellule dans la formule (`_xl_m2`) :
  `IF(cell=INT(cell), TEXT(cell,"0"), SUBSTITUTE(TEXT(cell,"0.##"),".",","))` — **entière si entière**
  (« 595 »), **sinon jusqu'à deux décimales** (« 595,01 »), **virgule française**. Même rendu que la
  règle du PDF (`fmt_surfaces_paire`) : assez de décimales pour voir le dépassement, au moins deux
  quand l'écart est inférieur à un m², pas de décimale parasite quand l'écart est large (412 / 555).
- Conséquence : si on **modifie** la SDP, la surface vendable ou la surface à retenir **sans
  régénérer**, le texte cité **suit** la nouvelle valeur.

**Preuve — le test exigé** (`tests/test_chirurgical_fix_q.py`, 4 tests) : on **exporte** le classeur,
on **modifie les cellules sans régénérer**, on **recalcule avec le moteur de tableur indépendant**
(`formulas`), et on vérifie que l'alerte cite les valeurs modifiées, **et qu'elle change encore** à une
seconde modification. Mesuré :

| Modification | SDP > surface à retenir | surface vendable > plancher |
|---|---|---|
| 595,01 / 595 · 595,02 / 595,01 | « (**595,01** m²) dépasse … (**595** m²) » | « (**595,02** m²) … (**595,01** m²) » |
| 85,01 / 85 · 700,25 / 700,1 (2ᵉ modif) | « (**85,01** m²) … (**85** m²) » | « (**700,25** m²) … (**700,1** m²) » |

`test_q_messages_construits_dans_la_formule_pas_figes` vérifie qu'**aucune** valeur d'entrée n'est écrite
en dur dans les formules (elles référencent les cellules via `TEXT`/`INT`/`SUBSTITUTE`) ;
`test_q_regle_affichage_dans_la_formule` fige la règle (écart large → entiers ; écart fin → décimales).

> Vérifié **dans le fichier livré** (`_lot-final-10/bilan_AD0887…xlsx`) : `I2` = surface à retenir
> (555, libellé « Surface à retenir (Dossier, m²) ») ; les deux formules d'alerte référencent les
> cellules (`TEXT(…)`, `I2`). Les Bilans livrés partent du scénario réel (surfaces entières) ; le
> comportement décimal et « vivant » est prouvé sur les valeurs mêmes du relecteur par le test.

---

## Livrables

`~/Desktop/chasse-1/_lot-final-10/` : 4 Bilans (PDF + Excel), 4 Dossiers, 4 Apporteurs, 4 Estimer,
3 pré-dossiers (AM0838 refusé), 1 Comparatif, `_saisies.json`. Toutes les pièces par routes HTTP.
Gardes : `tests/test_chirurgical_fix_q.py` (4) + les guards L/M/O/P ajustés (alertes désormais
construites des cellules). Commits sur `fix/chirurgical-q`.
