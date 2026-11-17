# CHIRURGICAL-FIX-1 — LOT M (6ᵉ passage du relecteur)

**Branche** `fix/chirurgical-m` (depuis `origin/main` après `git fetch`). **Pas de merge.**
Hook pré-push **VERT sans `--no-verify`**. Livraison : `~/Desktop/chasse-1/_lot-final-6/` + `_saisies.json`.

> « Tout est validé sauf le Bilan, et il donne sa liste fermée : trois corrections conditionnent son
> feu vert. » Parcelles témoins : **BW2635** `97422000BW2635` (Uav, Le Tampon), **AM0838**
> `97404000AM0838` (UE, L'Étang-Salé, habitat interdit), **AD0887** `97422000AD0887` (Ud, Le Tampon),
> **IS0448** `97411000IS0448` (Uh, Saint-Denis, bâti conservé → 0 m²).

---

## 1 — Les vraies valeurs du parcours écran — **REMPLI**

**Constat.** Le script transmettait la **surface de plancher** comme surface vendable ; l'écran
(`BilanEcran.tsx:97`) reprend la **surface habitable** du scénario (`programme.shab_estimee_m2`) → le
CA était surestimé.

**Correctif.** `_programme_depuis_etude` (livraison) lit **deux surfaces DISTINCTES**, à l'identique de
l'écran : SDP = `resume.sdp_m2`, **surface vendable = `programme.shab_estimee_m2`**. Le produit porte
`suv = SHAB`, `sdp` reste le plancher. Le moteur ajoute un **contrôle de cohérence VIVANT** : une
surface vendable **> surface de plancher** (ou doublée sans rapport avec elle) déclenche l'alerte —
moteur (`_vraisemblance` cible `suv_sdp`) **et** formule Excel à côté de la surface vendable.

**Preuve.** Livré dans `_lot-final-6` (la surface vendable est bien la SHAB, strictement < SDP) :

| Parcelle | SDP (plancher) | Surface vendable (SHAB) | Prix VEFA | CA TTC |
|---|---|---|---|---|
| BW2635 | 535 m² | **364 m²** | 4 547 €/m² | 1 655 108 € |
| AD0887 | 595 m² | **444 m²** | 4 318 €/m² | 1 917 192 € |

> Le CA repose désormais sur la surface **habitable** (364 / 444 m²), pas sur le plancher (535 / 595) —
> sans la correction, le CA aurait été gonflé de 777 537 € (BW2635) et 652 018 € (AD0887). Les valeurs
> exactes diffèrent de celles citées par le relecteur (224 / 572 m²) parce que le **scénario de
> l'Étude a été recalculé depuis** (comme en LOT L) ; la MÉTHODE — surface vendable = SHAB, distincte
> de la SDP — est, elle, exactement celle de l'écran.

Gardes : `test_m1_script_livraison_utilise_la_shab`, `test_m1_coherence_suv_superieure_sdp_alerte`,
`test_m1_excel_alerte_suv_sdp_est_vivante`.

---

## 2 — Une seule convention de TVA — **REMPLI**

**Constat.** (a) Le net promoteur différait PDF/Excel (le PDF ajoutait 8,5 % forfaitaires alors que la
TVA de vente est vide). (b) Une TVA vide était traitée comme 0 %. (c) Une saisie invalide ne bloquait
que le résultat (dépenses négatives visibles, TVA 101 % → CA HT à zéro, texte → #VALUE!).

**Correctif.**
- **Net promoteur = TVA RÉELLE** des deux côtés (moteur `_ratios` : `net/SUV × (CA TTC / CA HT)`, plus
  de `× (1 + TVA DOM)`). Avec TVA 8,5 % et sans frais d'acte : **4 318 €/m² en PDF ET en Excel** (avant
  4 685 vs 4 318).
- **TVA de vente vide ≠ 0 %** : le CA HT, le net promoteur, le prix moyen HT, la marge et le résultat
  sont **« non calculable »** ; le CA TTC (surface vendable × prix) reste connu. Côté Excel, le CA HT
  par produit teste `ISBLANK(TVA)`, et le total **ADDITIONNE avec « + »** (pas `SUM`, qui IGNORE le
  texte et rendait 0 — le bug « CA HT à zéro »), enveloppé d'`IFERROR`.
- **Une saisie invalide bloque AUSSI les totaux** : `Dépenses totales` et `Chiffre d'affaires` passent
  par la cellule de validité `I1` **et** un `IFERROR` → « saisie invalide » / « non calculable »,
  jamais une dépense négative visible ni un `#VALUE!`. Les évaluateurs (aperçu + test) apprennent
  `ISBLANK` / `IFERROR` / `ISTEXT`.

**Preuve** (moteur + tiers `formulas`) : net promoteur PDF == Excel == 4 318 € ; TVA vide → CA HT /
net promoteur / marge « non calculable » (CA TTC connu) ; TVA 101 % → `Dépenses totales`, `CA HT`,
`Résultat` tous « saisie invalide ». Gardes : `test_m2_tva_vide_rend_tout_non_calculable`,
`test_m2_net_promoteur_identique_pdf_et_excel`, `test_m2_tva_vide_ca_ht_non_calculable_excel_tiers`,
`test_m2_saisie_invalide_bloque_les_totaux`, `test_m2_ca_ht_total_additionne_jamais_sum`.

---

## 3 — Le terrain sans programme — **REMPLI**

**Constat.** (a) AM0838 citait 8 125 m² de « surface à retenir du Dossier » (une ancienne simulation
enregistrée ; le Dossier ne donne aucune capacité résidentielle). (b) Le seuil d'alerte différait d'un
mètre entre PDF et Excel. (c) Un Bilan sans programme disait « programme saisi par l'utilisateur ».

**Correctif.**
- `garde_fou_bilan` : sur une parcelle **non constructible / habitat interdit**, AUCUNE « surface à
  retenir » n'est renvoyée (`sar_val = None`) ni scénario « terrain libéré » — seul le motif reste. Le
  8 125 m² a disparu des Bilans livrés (PDF et Excel).
- **Seuil identique** : le garde-fou (PDF) compare désormais `round(SDP) > round(surface à retenir)`,
  le MÊME que la formule Excel (`SDP > round(surface à retenir)`) — plus d'écart d'un mètre.
- Un Bilan livré **sans programme** (`programme_saisi=False`) affiche **« Aucun programme — parcelle
  écartée par LABUSE »**, pas « Programme saisi ». La route passe `programme_saisi` selon que le corps
  porte un produit / une SDP.

**Preuve** : dans `_lot-final-6`, AM0838 et IS0448 portent « Aucun programme » (PDF + Excel A2), aucun
« 8125 ». Gardes : `test_m3_non_constructible_pas_de_surface_a_retenir`,
`test_m3_seuil_identique_pdf_et_excel`, `test_m3_bandeau_aucun_programme`.

---

## Mineur — **PARTIEL**

- **Charge foncière nomme sa surface** : déjà le cas — le Comparatif l'écrit « €/m² **de terrain** »
  (+ note « rapporté au m² de terrain »), le Bilan « /m² **de surface vendable** ». **Rempli.**
- **Comparatif (couverture / carte seule)** : la couverture est passée **en deux colonnes** (résumé à
  gauche, carte à droite, `page-break-inside:avoid`) → la carte n'est plus seule sur sa page. Le total
  reste à 7 pages (le résumé multi-lignes et les 3 colonnes de tableau sont volumineux) : réduction
  complète du nombre de pages **non faite** (tuning de mise en page, hors des 3 points bloquants).

---

## Livrables

`~/Desktop/chasse-1/_lot-final-6/` : 4 Bilans (PDF + Excel), 4 Dossiers, 4 Apporteurs, 4 Estimer,
3 pré-dossiers (AM0838 refusé — non constructible), 1 Comparatif, `_saisies.json` (route + saisie
exacte de chaque fichier, SDP/SUV distinctes, hypothèses nommées). Toutes les pièces par routes HTTP.
Gardes : `tests/test_chirurgical_fix_m.py` (11) + `test_chirurgical_fix_l.py` mis à jour pour la
nouvelle convention TVA. Commits sur `fix/chirurgical-m`.
