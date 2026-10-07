# BILAN-2 — le Bilan se comporte comme l'Excel de la promotrice

Branche `fix/bilan-2` · ports 8840 / 6040 · pas de merge · captures avant/après dans
`captures/BILAN-2/`. Référence de mise en page : `docs/audit-2026-10/bilan-1/modele-vierge.xlsx`
(non commité, ajouté au `.gitignore` ; la structure est identique à `modele-promotrice.xlsx`).

## Ce qui change

### 1. Calcul en continu (fin de la règle « aucune marge tant qu'un poste est à renseigner »)
- `src/labuse/bilan/moteur.py` : **une case vide vaut 0** (valeur, assiette ou taux de TVA
  non posés comptent pour 0), comme dans l'Excel. La marge, les ratios et les totaux se
  calculent **dès la première saisie** ; `depenses_*`, `resultat_net`, `marge_pct`, le prix
  max du terrain et les ratios ne sont plus conditionnés à un bilan « complet ».
- Les lignes vides ne sont plus bloquantes : elles sont **comptées** (`lignes_vides`,
  information discrète). `complet` subsiste (= 0 ligne vide) mais ne gouverne plus rien.
- Une ligne « Sans objet » vaut toujours 0 volontaire (jamais comptée comme vide).
- L'alerte de vraisemblance « marge élevée » reste gardée par « 0 ligne vide » (un bilan
  partiel affiche naturellement ~100 % de marge) ; les autres alertes (coût de construction,
  surface taxable) restent pilotées par la saisie. **Toutes les alertes restent.**
- `POST /bilan/{idu}/generer`, `GET /bilan/{idu}.pdf` et `.xlsx` : **plus de 422** « bilan
  incomplet » — le PDF et l'Excel se génèrent à tout moment.

### 2. Mise en page calée sur l'Excel (`frontend/src/components/fiche/BilanEcran.tsx`)
- **Un seul tableau aligné**, colonnes fixes `Libellé · Assiette · Taux · HT · TVA · TTC`
  (chiffres calés à droite, largeurs partagées en-tête/lignes, `table-fixed`), un **sous-total
  par bloc « TOTAL (1) … (4) »**, puis le **CA et la marge en bas** (Dépenses, CA, TVA
  résiduelle, Résultat net, Cash flow).
- **En haut**, dans l'ordre de l'Excel : le bloc **Ratios & programme** (Terrain · Surface de
  plancher · Surface taxable · SUV · Coût const. m² SUV HT · Prix moyen m² SUV HT · Net
  promoteur m² SUV TTC · CA TTC · Renta nette / CA HT · Nombre de lots) et le **Calendrier
  prévisionnel** (Compromis → Livraison en J+n, saisissable, pré-rempli, repère Sitadel sur
  Obtention PC).
- Les **états** deviennent une simple pastille (Sourcé / Saisi / Repère pris / Mes ratios /
  Sans objet) ; **plus d'« À renseigner » orange** par ligne. Un compteur discret
  **« N lignes vides »** dans l'en-tête (jamais bloquant).
- Le **repère LABUSE reste cliquable à droite de la case** (Taux, SDP, Surface taxable, prix
  produit) et n'entre dans le calcul qu'au clic.
- Lisible sur un portable 1440 px, **aucun défilement horizontal**, DA de l'app.

### 3. PDF & Excel reflètent l'écran
- `pdf.py` : bloc de tête (ratios + calendrier), `TOTAL (n)`, lignes vides à blanc,
  pastilles sans « À renseigner », génération à tout moment.
- `excel.py` : haut de feuille (ratios en formules + calendrier), toujours **vivant**
  (formules, pas de valeurs figées) ; ajoute la ligne « Surface de plancher ».
- `declarations/bilan/postes.yaml` + `catalogue.py` : nouvelle section `calendrier`
  (9 étapes, décalages du modèle, repère Sitadel).

## Tests
- **Non-régression au centime** : le bilan de la promotrice ressaisi donne toujours son
  résultat exact (`test_bilan_moteur::test_non_regression_*`, `test_bilan_recette`,
  `test_bilan_excel`).
- **Bilan à moitié rempli** : calcule et s'exporte — `test_calcul_en_continu_moitie_rempli`
  (moteur + route) et `test_generer_moitie_rempli_puis_exports` (génère, PDF `%PDF`, Excel `PK`).
- **Bilan à blanc** vaut 0 partout (`test_bilan_totalement_vide_vaut_zero`).
- 52 tests bilan verts (socket DB) · tsc 0 · vitest 237 · build prod vert.
- Pré-existant hors scope : `test_simulplu` (2 échecs de seeding DVF/Sitadel en base de test,
  identiques sans ce travail).

## Captures (`captures/BILAN-2/`)
- `avant.png` — écran d'origine : sidebar, « Aucun chiffre n'est calculé sur un bilan
  incomplet », « À renseigner » orange sur chaque ligne.
- `apres-vierge.png` — nouveau, à blanc : tableau unique, bloc ratios + calendrier en haut,
  Résultat net 0 €, « 45 lignes vides ».
- `apres-moitie-rempli.png` — nouveau, à moitié rempli : la marge (2 363 064 € / 20,9 %)
  s'affiche, « 41 lignes vides », repères cliquables, pastilles simplifiées.
- Méthode : le vrai composant `BilanEcran` monté dans un harnais Vite à `fetch` bouchonné
  (modèle + calcul bâtis par le moteur réel), sans base. Le harnais n'est pas commité ; le
  composant de prod n'a aucun point d'entrée de test.

## Décisions
- Le **calendrier est informatif** (comme dans l'Excel où les frais financiers sont un ratio
  forfaitaire du CA) : saisissable et persisté (il part dans les hypothèses du document), mais
  il n'entre pas dans le calcul.
- La pastille d'une ligne vide est **absente** (plus de badge orange) ; l'information « il
  reste N lignes » vit une seule fois, en haut.
