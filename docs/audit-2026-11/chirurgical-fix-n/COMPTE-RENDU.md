# CHIRURGICAL-FIX-1 — LOT N (7ᵉ passage du relecteur)

**Branche** `fix/chirurgical-n` (depuis `origin/main` après `git fetch`). **Pas de merge.**
Hook pré-push **VERT sans `--no-verify`**. Livraison : `~/Desktop/chasse-1/_lot-final-7/` + `_saisies.json`.

> « Surfaces, chiffre d'affaires et TVA sont validés. Il reste sa liste fermée de trois points. »
> Parcelles témoins : **BW2635** / **AD0887** (Le Tampon), **AM0838** (L'Étang-Salé, habitat interdit),
> **IS0448** (Saint-Denis, bâti conservé → 0 m² / terrain libéré 85 m²).

---

## 1 — Aucune sortie sur une saisie rejetée — **REMPLI**

**Constat.** Un texte collé dans un coût (« n/a ») laissait le résultat chiffré avec `#VALUE!` ; un prix
de vente négatif donnait un CA négatif ; des sous-totaux restaient chiffrés après un coût négatif.

**Correctif — une règle unique.** La **cellule de validité** `I1` exige que **chaque case de saisie**
soit **vide OU un nombre dans ses bornes** : `AND(NOT(ISBLANK(c)), OR(NOT(ISNUMBER(c)), c<0))` pour un
coût, idem + `c>1` pour une TVA. Un **texte** (pas `ISNUMBER`) est donc rejeté, comme un négatif ou une
TVA hors `[0,1]`. Puis **TOUTES les cases calculées** (lignes, sous-totaux, totaux, CA TTC **et** HT,
ratios, résultat) sont **enveloppées** : `=IF(I1<>"", "saisie invalide", <calcul>)`. Excel
court-circuite le `IF` → quand une saisie est fausse, le calcul **n'est pas tenté** : **aucun nombre,
aucune erreur Excel** (`#VALUE!`), seulement « saisie invalide » partout.

**Preuve — test de robustesse permanent.** `test_n1_robustesse_toutes_les_cases` : pour **chaque case
de saisie** du classeur, on injecte tour à tour **négatif / texte / zéro / vide / décimal / valeur
énorme**, on recalcule avec le **moteur de tableur indépendant** (`formulas`), et on vérifie qu'une
saisie **invalide** ne laisse **ni nombre ni erreur** (tout « saisie invalide ») et qu'une saisie
**valide** recalcule juste. Mesuré : texte « n/a » dans un coût → toutes les sorties « saisie
invalide », **0 erreur Excel** ; prix négatif → idem ; valeur énorme (coût) → recalcule. Gardes :
`test_n1_validite_rejette_le_texte`, `test_n1_toutes_les_cases_calculees_sont_enveloppees`.

> « Vide » = une case réellement **blanche** (`ISBLANK`) : valide, traitée comme 0. Une chaîne vide
> `""` collée reste rejetée (sinon `#VALUE!` en aval).

---

## 2 — Les mêmes alertes dans le PDF et l'Excel — **REMPLI**

**Constat.** L'alerte « surface vendable > surface de plancher » n'était que dans l'Excel ; elle ne se
déclenchait pas pour une SDP nulle/vide ; le seuil était comparé après arrondi (595,1 passait côté PDF).

**Correctif.** L'alerte est portée par le **garde-fou** (`garde_fou_bilan`, nouveau `suv_saisie`), donc
affichée **dans le bandeau du PDF ET de l'Excel**. La comparaison se fait sur les **décimales, sans
arrondi** (`suv > (sdp or 0)` ; 595,1 > 595 alerte). Une **surface vendable positive avec une SDP nulle
ou vide** déclenche l'alerte des deux côtés. Côté Excel, la formule vivante à côté de la surface
vendable gère aussi `OR(SDP=0, ISBLANK(SDP), SUV>SDP)`, et le bandeau A2 ne la répète plus en texte figé.

**Preuve.** `test_n2_suv_sdp_dans_le_pdf`, `test_n2_suv_positive_sdp_vide_et_decimales`,
`test_n2_excel_formule_suv_sdp_gere_sdp_vide`, `test_n2_garde_fou_porte_suv_sdp_sur_les_decimales`.

---

## 3 — Ce que dit la couverture — **REMPLI**

**Constat.** (a) Les deux Bilans PDF du Tampon affichaient « aucune Étude reliée · Prix demandé : non
renseigné » alors que le scénario et le prix sont utilisés. (b) Sur IS0448, « aucune capacité à bâtir »
est faux : le Dossier distingue 0 m² (bâti conservé) et 85 m² (terrain libéré).

**Correctif.**
- (a) La route dérive déjà `etude_reliee` / `prix_demande` (`_hypotheses_bilan`) ; les Bilons sont
  **régénérés** et la couverture **NOMME les hypothèses** :
  - BW2635 : *« Programme : scénario de l'Étude (6 lots, 535 m²) · prix de vente = neuf VEFA secteur · Prix demandé : 4 547 € »*
  - AD0887 : *« … (7 lots, 595 m²) · prix de vente = neuf VEFA commune · Prix demandé : 4 318 € »*
- (b) Le bandeau « Aucun programme » (texte **partagé** PDF/Excel, `bandeau_sans_programme`) **reprend la
  distinction du Dossier** : IS0448 → *« Le Dossier distingue 0 m² en l'état (bâti conservé) et ~85 m²
  estimés en terrain libéré (démolition) »* ; AM0838 (habitat interdit) garde, à juste titre, *« aucune
  capacité résidentielle »*. Les capacités viennent de `parcel_residuel.sdp_residuelle_m2` (bâti
  conservé) et de `surface_a_retenir` (terrain libéré).

**Preuve** : vérifié **dans les fichiers livrés** — covers Tampon nommées (plus de « aucune Étude
reliée ») ; IS0448 PDF **et** Excel A2 portent la distinction 0 / 85 m², sans « aucune capacité à
bâtir ». Gardes : `test_n3_entete_nomme_les_hypotheses_est_cable`,
`test_n3_bandeau_reprend_la_distinction_du_dossier`, `test_n3_bandeau_pdf_et_excel_identiques`.

---

## Livrables

`~/Desktop/chasse-1/_lot-final-7/` : 4 Bilans (PDF + Excel), 4 Dossiers, 4 Apporteurs, 4 Estimer,
3 pré-dossiers (AM0838 refusé — non constructible), 1 Comparatif, `_saisies.json`. Toutes les pièces
par routes HTTP. Gardes : `tests/test_chirurgical_fix_n.py` (10, dont la robustesse `formulas`) +
`test_chirurgical_fix_k.py` / `test_bilan_moteur.py` ajustés à la validité durcie. Commits sur
`fix/chirurgical-n`.
