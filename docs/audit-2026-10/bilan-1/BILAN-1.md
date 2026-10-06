# BILAN-1 — Le bilan promoteur remplace l'ancien Financier

**Branche** `feat/bilan-1` · base `origin/main` `01965f44` · worktree `~/Desktop/labuse-bilan1`.
**Modèle** Opus. **Rédigé** le 06/10/2026.

Le « Bilan » client n'est plus l'ancien Financier renommé (~13 postes, un écran
d'hypothèses). C'est désormais **le bilan promoteur du modèle de la promotrice** :
toutes ses lignes, dans ses 4 blocs, avec un moteur en Python, deux portes (fiche
et page Docs), un PDF et un Excel vivant. Doctrine tenue : **rien de faux** — on ne
pré-remplit que le Sourcé, tout le reste est vide avec un repère qui n'entre dans
le calcul que si le client le clique, et aucune marge ni export tant qu'un poste
est « À renseigner ».

---

## 1. Le modèle de la promotrice (xlsx) — ce qu'on en a tiré

Le fichier `modele-promotrice.xlsx` (feuille **BILAN**, zone `A1:G147`) **n'est jamais
commité** (gitignoré au 1ᵉʳ commit) ; seuls les libellés, l'ordre, les assiettes et
les formules en sont tirés, dans `declarations/bilan/postes.yaml`.

- Le classeur porte des **`definedNames` cassés** (`#N/A`, noms d'un vieux gabarit) qui
  font planter openpyxl à l'ouverture directe → lu via une **copie temporaire patchée**
  (dans `/tmp`), l'original n'est jamais touché.
- **45 postes de charges** en 4 blocs (règle de comptage déterministe, vérifiée par test) :
  Charge foncière 18 · Construction & honoraires 10 · Gestion 10 · Commercialisation 7.
  + **2 lignes produit** (CA) → le « Programme : une ligne par produit ».
- **Cellule cassée** non reproduite (listée, sans effet sur les totaux) : `E13`
  (coût construction / SHON) = `#DIV/0!` car la SHON `E6` est vide dans le témoin.
- **Nom de société** présent dans le modèle (« Cash flow **océanis** », lignes 122/128 ;
  + un chemin SharePoint en métadonnée) → **neutralisé** : rendu « Cash flow ».

## 2. Doctrine (gravée par Vic) — comment elle est tenue

1. **Pré-rempli = seulement le Sourcé** : surface du terrain (cadastre), zonage PLU,
   taux de TVA légaux (DOM 8,5 % / social 2,1 % / exonéré 0). Servi par
   `GET /bilan/{idu}/modele` (`sourcee` + `tva_legales`). Tout reste modifiable.
2. **Le reste est vide**, avec un **repère** cliquable à côté. Deux familles :
   `registre` (source publique : DVF neuf, coût de référence, …) et `ratio_place`
   (ratio de place, étiqueté honnêtement). **Un repère dont la source ne se résout
   pas ne s'affiche pas** : la résolution est défensive (sous SAVEPOINT, jamais un 500).
3. **Aucune marge, aucun export tant qu'un poste est « À renseigner »** : le moteur
   rend `complet=false` et `manquants`, le front masque la marge, `/generer` renvoie
   **422**.
4. **États par poste** : Sourcé · Saisi · Repère pris · Mes ratios · Sans objet · À renseigner.
5. **Aucun calcul au front** : toute saisie repart au moteur (`POST /bilan/{idu}/calcul`).
6. **Le mot « Financier » n'apparaît nulle part côté client** : tuile fiche = « Bilan »,
   code de rapport propre « BI » (jamais « FI »), l'ancien `FinancierQuestionnaire` supprimé.

## 3. Ce qui a été construit, lot par lot

| Lot | Livrable | Commit | Preuve |
|-----|----------|--------|--------|
| 1 | `declarations/bilan/postes.yaml` + chargeur typé | `bfe82e8e` | 5 tests : nb+ordre+libellés **comptés depuis le xlsx** = modèle |
| 2 | `src/labuse/bilan/moteur.py` | `e3038bff` | non-régression (voir §4) + 2 sens inverses + bilan vide sans marge |
| 3 | porte backend (`modele`/`calcul`) + écran React `BilanEcran.tsx` | `d0d2bb27`, `1e83790f` | routes testées (DB) ; tsc0 · vitest 237 · build prod vert |
| 4 | table `bilan_ratios` + routes + isolation par compte | `a1365142` | test IDOR à deux comptes (DB) |
| 5 | PDF + **Excel vivant** + `documents_generes` (saisies JSON) | `6f0edc3a`, `1e83790f` | « Excel = moteur » au centime + génération/ouverture (DB+WeasyPrint) |
| 6 | page Docs : 8ᵉ carte « Comparables DVF » (grisée, « bientôt ») | `a0fcce8b` | tsc0 |
| 7 | recette + ce rapport + captures | ce commit | « écran = PDF = Excel » au centime |

**Un moteur, deux portes.** La tuile « Bilan » de la fiche (`BanquierButton`) et le
bouton « Générer le bilan » de la page Docs ouvrent **le même écran** (`BilanEcran`),
qui remplace l'ancien `FinancierQuestionnaire` (supprimé, écran + test).

## 4. Non-régression : le moteur reproduit le bilan de la promotrice

En rejouant **ses propres valeurs saisies**, le moteur retombe sur les totaux de son
Excel **au centime sur les 45 lignes, 0 € d'écart**. Les assiettes d'assurances
composées à la main dans le tableur sont **recopiées à l'identique** (décision Vic) :

| Poste | Assiette (modèle = moteur) | HT modèle = moteur |
|-------|----------------------------|--------------------|
| Assurances D.O / C.N.R | total (2) TTC + étude de sol TTC − imprévus TTC | 91 570,06 € |
| Assurance TRC + GAREAT | total (2) HT + étude de sol HT − imprévus HT | 21 738,46 € |

Résultat net du moteur = **1 244 996,78 €** = le modèle, à l'euro. La **commission
d'apport** (3 % toutes taxes) est reproduite via `base: ttc`. Le test vérifie chaque
ligne (HT·TVA·TTC) + chaque total de bloc + le résultat net contre le xlsx.

## 5. Les deux sens, sur le même écran

- **Marge au prix saisi** : `résultat net` et `marge % du CA HT`.
- **Prix maximal du terrain** pour une **marge cible** saisie (charge foncière
  admissible), par un modèle linéaire **exact** (mesuré par deux évaluations du
  bilan). Test : à la marge rendue par le sens « marge », le sens « prix » redonne
  **exactement** le prix d'achat saisi.
- Le **prix d'achat historique DVF** est affiché **en information, hors calcul**.

## 6. Repères — tous câblés (source publique uniquement)

| Repère | Poste / champ | Source (vérifiée sur base réelle) |
|--------|---------------|-----------------------------------|
| DVF neuf | produits (prix/m²) | `resolve_prix_sortie_servi` — ex. 4 730 €/m² · n 54 |
| Outil Taxe | Taxe logements (txLog) | taxe d'aménagement, part communale × valeur forfaitaire — ex. 44,6 €/m² |
| Redevance archéo | Taxe d'archéologie (archeo) | 0,40 % × valeur forfaitaire — ex. 3,57 €/m² |
| Faisabilité | Surface taxable (= SDP) | `faisabilite_scenario` — ex. 706 m² SDP (+ 14 parkings, 7-9 logts en info) |
| Sitadel | info calendrier | médiane dépôt→PC de la commune — ex. 9 mois |
| Coût de construction | Construction yc VRD (constr) | calibrage commune (`Hypotheses.charger`) — ex. 2 550 €/m² |

Un repère **ne s'affiche que s'il se résout** (doctrine 2) : sur une parcelle zone N,
la Faisabilité ne propose rien ; sinon le client saisit. Le repère Taxe n'est posé que
sur la ligne taxe d'aménagement (jamais sur TA parkings/TRE → pas de double compte).
Les ratios de place **ne sont plus des repères** (décision Vic) ; aucun repère n'entre
dans le calcul sans clic.

## 7. Recette — « écran = PDF = Excel au centime »

- **Écran = moteur** par construction : l'écran n'affiche que le résultat de `/calcul`.
- **Excel = moteur** : l'export est **vivant** (HT/TVA/TTC et totaux en **formules**,
  pas de valeurs figées). Un évaluateur du graphe de formules (test) prouve l'égalité
  au centime, sans tableur.
- **PDF = moteur** : le PDF est bâti depuis le même résultat ; le test vérifie que le
  résultat net et le CA formatés du moteur y figurent.
- **Tests bilan : 20 verts** (`test_bilan_{catalogue,moteur,excel,recette,ratios_cloison,routes,sorties}.py`).
  Hors bilan : `test_circuit_provenance` **vert** sur base applicative réelle (l'ajout
  du code « BI » et de l'Excel ne casse pas l'audit de provenance des documents). Un
  échec **pré-existant** subsiste (`copilote_questions_plafond`, appel LLM/crédit),
  sans lien avec ce mandat.

### Captures (`captures/`)
**Documents** : `bilan-temoin.pdf` + `bilan-pdf-p1-1.png` (page 1 : Charge foncière,
badges d'état, Total 2 271 464 € TTC) + `bilan-pdf-synthese-3.png` (résultat net
1 244 997 € · 10,2 %) + `bilan-temoin.xlsx` (export vivant, formules).

**Écran vivant** (pile lancée sur 8820, base applicative réelle, compte dédié) :
- `ecran-docs-8-cartes.png` — la page Docs, grille 2×4, Comparables DVF grisée « bientôt ».
- `ecran-bilan-vide.png` — « 46 postes à renseigner · 0/45 », Sourcé (terrain, zonage),
  repères Faisabilité 14 153 m² SDP · Sitadel 9 mois · DVF 54 ventes ; **aucun ratio de place**.
- `ecran-bilan-repere-cliques.png` — Construction « Repère pris » 2 550 €/m² (le champ
  reflète la valeur adoptée).
- `ecran-bilan-mes-ratios.png` — Hono MOE + BET mémorisé → état « Mes ratios »
  (persisté dans `bilan_ratios`, scopé au compte).
- `ecran-bilan-complet.png` — 45/45 postes, résultat net calculé, « Générer le bilan »
  actif (valeurs de démonstration).

## 8. Décisions de Vic — avant merge (un commit par point)
1. **Assiettes D.O / TRC** — recopiées à l'identique du tableur → **0 € d'écart** (§4). ✓
2. **Repères « ratio de place »** — masqués (pas de source publique → pas de repère). ✓
3. **Repères câblés** — Taxe/archéo (€/m²), Faisabilité (SDP · parkings · logts), Sitadel. ✓ (§6)
4. **Captures de l'écran vivant** — prises sur la pile (8820, base réelle). ✓ (§7)

**Ancien Financier backend** (`financier_bilan.py`, `financier_questionnaire.py`, routes
`/financier/*`) **laissé en place** (no élargissement) ; seule la porte client bascule
sur le nouveau bilan. Démontage = un chantier dédié.
