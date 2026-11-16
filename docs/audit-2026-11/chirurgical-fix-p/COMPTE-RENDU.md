# CHIRURGICAL-FIX-1 — LOT P (9ᵉ passage du relecteur)

**Branche** `fix/chirurgical-p` (depuis `origin/main`, qui porte désormais LOT O). **Pas de merge.**
Hook pré-push **VERT sans `--no-verify`**. Livraison : `~/Desktop/chasse-1/_lot-final-9/` + `_saisies.json`.

> « Le rejet des saisies invalides est validé sur les 212 cases, les comparaisons de surface aussi.
> Il reste un seul point. » Les deux alertes de surface doivent afficher **leurs deux valeurs**, avec
> assez de décimales pour voir le dépassement, dans le PDF **comme** dans le classeur.

---

## Le point — les deux alertes citent leurs deux valeurs, avec assez de décimales — **REMPLI**

**Constat.** Avec 595,01 m² de plancher et 595,02 m² vendables sur AD0887, le PDF écrivait « 595 m²
contre 595 m² » dans les deux messages. Dans le classeur, l'alerte sur la surface vendable ne donnait
**aucun chiffre**, et les surfaces de la synthèse s'affichaient arrondies au m².

**Correctif — une règle d'affichage UNIQUE, partagée par le PDF et l'Excel**
(`moteur.fmt_surfaces_paire`) : *autant de décimales que nécessaire pour **distinguer** les deux
valeurs, **au moins deux** quand elles diffèrent de moins d'un m²*, virgule française, zéros inutiles
retirés.

- **PDF** — garde-fou (`garde_fou_bilan`) et vraisemblance (moteur). Les **deux** contrôles affichent
  **leurs deux valeurs** :
  - surface à retenir : « La surface de plancher saisie (**595,01** m²) dépasse la surface à retenir
    du Dossier (**595** m²). »
  - surface vendable : « Surface vendable (**595,02** m²) supérieure à la surface de plancher
    (**595,01** m²) … »
- **Excel** — l'alerte sur la surface vendable **cite désormais les deux valeurs** (plus « aucun
  chiffre ») ; l'alerte surface à retenir cite la **SDP ET** la surface à retenir ; les surfaces de la
  synthèse ne s'affichent plus arrondies au m² (`_M2 = '#,##0.## "m²"'` → « 595,01 m² », entier sinon).

**Preuve — les trois cas, dans les deux formats** (`tests/test_chirurgical_fix_p.py`, 10 tests) :

| Cas | Attendu | PDF | Excel |
|---|---|---|---|
| AD0887 · surface à retenir | **595,01** contre **595** | `test_p_cas1_…_pdf` | `test_p_cas1_…_excel` |
| AD0887 · surface vendable | **595,02** contre **595,01** | `test_p_cas2_…_pdf` / `…_moteur` | `test_p_cas2_…_excel` |
| IS0448 | **85,01** contre **85** | `test_p_cas3_…_pdf` | `test_p_cas3_…_excel` |

`test_p_regle_affichage_unique` fige la règle (`fmt_surfaces_paire`), `test_p_pdf_et_excel_memes_valeurs`
vérifie que les deux formats citent **les mêmes** valeurs, `test_p_excel_surfaces_montrent_les_decimales`
vérifie le format décimal de la synthèse.

> Les trois cas utilisent les **valeurs exactes du relecteur** (saisies décimales). Les Bilans livrés
> partent, eux, du scénario réel (surfaces entières) : ils portent la **capacité** (format décimal de
> la synthèse, alertes qui citent leurs deux valeurs — vérifié : l'Excel d'AD0887 écrit « surface de
> plancher (555 m²) dépasse la surface à retenir (555 m²) »). Le comportement décimal est donc prouvé
> par les tests, sur les valeurs mêmes du relecteur.

---

## Livrables

`~/Desktop/chasse-1/_lot-final-9/` : 4 Bilans (PDF + Excel), 4 Dossiers, 4 Apporteurs, 4 Estimer,
3 pré-dossiers (AM0838 refusé), 1 Comparatif, `_saisies.json`. Toutes les pièces par routes HTTP.
Gardes : `tests/test_chirurgical_fix_p.py` (10) + les guards L/M/N/O ajustés au nouveau libellé des
alertes. Commits sur `fix/chirurgical-p`.
