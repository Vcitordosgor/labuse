# CHIRURGICAL-FIX-1 — LOT I (2ᵉ contre-audit du relecteur indépendant, 4 parcelles)

**Branche** `fix/chirurgical-i` (créée depuis `origin/main` = `9058a8f55`, qui contient le LOT H mergé).
**Modèle** Opus 4.8. **Dépôt** `~/Desktop/labuse-chasse-ecrans`. Documents régénérés dans
`~/Desktop/chasse-1/_lot-final-2/` (anciens témoins figés retirés). Les parcelles : **BW2635**
`97422000BW2635` (Uav), **AM0838** `97404000AM0838` (UE), **AD0887** `97422000AD0887` (Ud),
**IS0448** `97411000IS0448`. Un commit par point/groupe, gardes dans `tests/test_chirurgical_fix_i.py`.
Règle de régénération : **vider `fiche_cache`** des parcelles d'abord (le cache L2 servait l'ancien texte).

---

## 1 — Bilan Excel

### 1a — « non calculable » tant qu'un coût requis manque (OU, pas ET)
`bilan/moteur.py`, `bilan/excel.py`. La formule disait « non calculable » seulement si **les deux**
coûts étaient à 0 (ET), d'où ~60 % de marge avec le seul achat. Désormais c'est un **OU** : il faut
l'achat du terrain **ET** la construction. Moteur : `couts_requis = achat>0 ET constr>0`. Excel :
`=IF(OR(D{achat}<=0,D{constr}<=0),"non calculable…",CA−dép)` (marge et cash-flow idem).

### 1b — marge sans `#DIV/0!` ; coût négatif refusé à la saisie
Marge/renta : `=IF(OR(coût manquant, CA=0),"",…)` — plus jamais de `#DIV/0!` quand les ventes sont à
zéro. `api/bilan.py` : un coût négatif (taux/montant ou assiette) est refusé à la saisie
(`_valider_non_negatif`).

### 1c — valeurs calculées écrites EN PLUS des formules (aperçu non vide)
openpyxl écrivait `<f>…</f><v/>` (cache VIDE) → un aperçu (Finder, téléphone, pièce jointe) montrait
du blanc. `_valeurs_calculees` évalue le graphe (SUM, refs, `+−*/`, IF/AND/OR, comparateurs) et
`_injecter_valeurs` remplit le cache `<v>`. Le classeur reste vivant (`fullCalcOnLoad=1`). **Relu
SANS recalcul** (`data_only`) il donne les mêmes chiffres que le moteur. Preuve AD0887 :
CA HT en cache **238 785,40 €**, Résultat net **55 835,40 €** (une plage SUM vide — AM0838 sans
produit — vaut **0**, plus « () »).

### 1e — AM0838 : pas de produit « Logements »/CA si habitat interdit
`frontend/.../BilanEcran.tsx` : quand `sourcee.non_constructible_motif` est servi (habitat interdit),
le programme reste à blanc même si une Étude était reliée. Preuve : bilan AM0838 régénéré → **CA HT = 0**,
Résultat net « non calculable ».

### 1f — IS0448 : SATURATION ≠ INTERDICTION
`bilan/reperes.py`. `sources_parcelle` passait à **100 % non constructible SANS motif** dès que
`rien_a_batir` était vrai — y compris IS0448, CONSTRUCTIBLE mais sans surface résiduelle (SDP 0).
Désormais seul le verdict RÉEL (`constructible=False`) ferme la parcelle. Preuve : IS0448 → **34,4 %**
(part zone rouge), motif None ; AM0838 → **100 %**, motif « Habitat interdit dans cette zone ».

---

## 2 — Zone rouge (partout pareil)
`cascade/phase1.py` (source, runs futurs) + `api/risques_arbitrage.py` (`libelle_client_detail`,
reformule les libellés STOCKÉS — point unique lu par la fiche et les 4 documents) +
`api/pre_dossier.py` (PCMI4). La zone rouge marginale (< 50 %) disait « vigilance forte ; … pas
d'exclusion automatique » ; elle dit désormais, partout : « **PPR zone rouge sur N % de la surface —
cette partie est inconstructible (exclue de l'implantation) ; les prescriptions du règlement PPR ne
s'appliquent qu'en zone bleue** ». Le PCMI4 distingue le ROUGE (inconstructible, pas de prescription)
du BLEU (prescriptions à intégrer). L'Apporteur (f.lines) dit alors comme le Dossier. La zone humide
d'AD0887 garde sa portée pour l'instruction (inchangée). Preuves : IS0448 Dossier + Apporteur + PCMI4.

---

## 3 — Dossier

### 3a — BW2635 : plus de « peu réaliste en copropriété » quand la copro n'est que voisine
`exports/robinet_fiche.py` : le drapeau copro (feeding `surface_a_retenir`) ne compte QUE les copros
SUR la parcelle (`rattachement ≠ proche_20m`), plus `score_v2.copro` (vrai à tort sur les voisines).
Preuve BW2635 : Dossier « **Copropriétés : aucune copropriété immatriculée sur la parcelle.** ».

### 3b — IS0448 : « bâti non déterminé » faux (le Dossier donne 128 m² bâtis)
`exports/miroir.py` (`_absence_une_raison`) : quand l'emprise bâtie est connue, l'absence de marge de
hauteur n'est plus « bâti non déterminé » mais « **hauteur du bâti non mesurée** ». Preuve IS0448 :
« Marge de surélévation non calculable (**hauteur du bâti non mesurée**). ».

### 3c — Le Tampon : DEUX obligations de sol + stationnement avec sa portée
`faisabilite/zonage.py` (champ `permeabilite_pct`), `plu_reglement.py`, `traducteur.py`. Le règlement
de sol (art. 13) porte DEUX obligations : la **surface perméable** (enveloppe) ET la **pleine terre**
(noyau). Les deux sont servies : AD0887 (Ud) **30 % pleine terre + 40 % perméable** ; BW2635 (Uav)
**20 % + 30 %**. Stationnement : barème vérifié au règlement Ua 12.2 (« **1 place / logement ; 1,5
place / logement pour une opération de plus de 5 lots ou logements** ») servi via la feuille `bareme`
(la capacité lit toujours 1 place/logement). Preuve AD0887 Dossier : les deux lignes de sol + le barème.

### 3d — comparables : « 8 plus proches » ≠ échantillon de la médiane + doublons par mutation
`pige/estimer3.py` : le pool joignait `dvf_mutation_detail` sans dédoublonner → jusqu'à **162 lignes**
pour une même vente. `DISTINCT ON (id_mutation, id_parcelle)` → une ligne par mutation (BW2635 : 2198
comparables, **0 doublon**). `exports/blocs/annonce.py` : le tableau des 8 ventes les plus proches dit
en clair qu'il **n'est pas l'échantillon du prix médian** (calculé sur tout le secteur).

### 3e — AM0838 : chaque PPR porte son nom et sa date
`exports/miroir.py` (`_r_aleas`) : listait le seul premier PPR. AM0838 relève du **PPR** (mouvement/
inondation, **26/01/2016**) ET du **PPR littoral — PPRL** (**16/03/2017**) : les deux sont nommés et
datés. Preuve : Dossier AM0838 porte les deux dates.

---

## 4 — Numéros de documents
`exports/numeros.py` (`discriminant`), `exports/builder.py`, `bilan/pdf.py`. Le numéro
`PRÉFIXE-AAAAMMJJ-IDU` recevait le même numéro pour deux versions le même jour. Ajout d'une **clé de
contenu** stable (4 hex) : deux versions (données/saisies différentes) → numéros DIFFÉRENTS, une
génération à l'identique garde le même numéro. Le **Comparatif** numérote sur **toutes ses parcelles**
(pas la seule première). Le Bilan numérote sur sa saisie (CA/dépenses/résultat).

## 5 — Mineur
« **Version du PLU servie, approuvée le …** » au lieu de « PLU approuvé le … » (Apporteur + miroir).
Plus de **doubles points** (« .. ») dans la notice PCMI4 (un détail finissant par « . » suivi d'une
phrase « . … » en produisait) : on replie les suites de points. Preuve : PCMI4 IS0448 → 0 « .. ».

---

## Recette
`tests/test_chirurgical_fix_i.py` (1a OU, 1b div0+coût négatif, 1c cache=moteur, pt2 zone rouge, 3a/3b,
3c deux obligations+barème, 3d note+DISTINCT, 3e PPR datés, pt4 numéros). Tests existants alignés
(test_bilan_moteur, test_bilan_excel évaluateur OR/`=`, test_apporteur_plu_date, test_exports2_lot2).
Famille unitaire du hook rejouée. Hook pré-push complet vert **sans `--no-verify`**, branche poussée,
**pas de merge**.
