# CAPACITÉ-1 — LOT A : d'où viennent 614 m² et 888 m², et quelle capacité retenir

**Branche** `fix/capacite-1` · **worktree** `~/Desktop/labuse-capacite` · lecture seule, aucun run île, aucune écriture base.
**Parcelle de référence** 97416000HT0538 — Saint-Pierre, zone **Ud**, 510 m². Lot relu : `~/Desktop/exports-audit-4/`.

> **ARRÊT demandé.** Ce document est le diagnostic (LOT A). La proposition de fin (§6) n'est **pas**
> implémentée — elle attend ta relecture. Les correctifs déjà faits sont le LOT B (voir `COMPTE-RENDU.md`).

---

## 1. Les deux chiffres, et ce qui les produit

| | **614 m²** (Dossier §3, fiche) | **888 m²** (Étude de faisabilité) |
|---|---|---|
| Qui le calcule | moteur **analytique** `faisabilite/engine.py` → `parcel_faisabilite` | moteur d'**implantation** `implantation/moteur.py` → `etudier` |
| Nature | SDP = `emprise × occupation × niveaux` (formule fermée) | SDP = somme des **bâtiments réellement dessinés** sur la parcelle, contrôlés un à un |
| Niveaux | 5 (R+4) | 5 (R+4) — **identiques** |
| Logements | fourchette interne 6–8 (non servie : le Dossier renvoie à l'Étude) | **10** (T3×5 + T2×5) |

**La hauteur n'explique rien.** Les deux travaillent sur 5 niveaux (R+4). Le compte-rendu précédent
qui attribuait l'écart à « 2 niveaux contre 5 » était faux : c'est confirmé parcelle par parcelle.

---

## 2. HT0538 — décomposition facteur par facteur

### 614 m² (moteur analytique) — chaque étape, sa provenance

| Étape | Valeur | Provenance | Formule servie |
|---|---|---|---|
| Emprise — zone d'implantation réglementaire | ~273 m² | **sourcé** (reculs PLU) | reculs par côté voie/limites, PPR rouge déduit |
| Emprise — % réglementé (CES) | ~273 m² | **sourcé** | `min(reculs, 510 × 60 %)` = min(273, 306) → **les reculs mordent, pas le CES** |
| Contrainte pleine terre | ~273 m² retenu | **sourcé** | `emprise ≤ 510 × (1 − 20 %) = 408 m²` (ne mord pas) |
| Niveaux constructibles | R+4 (5 niv.) | **sourcé** | `15 m égout ÷ 3 m/niveau = 5` |
| **Emprise bâtie (occupation)** | **~123 m²** | **ESTIMÉ (hypothèse)** | **`273 m² × 45 %`** |
| Surface de plancher brute | **~614 m²** | dérivé | `123 m² × 5 niveaux` |
| Surface habitable (rendement) | ~491 m² | estimé | `614 × 80 %` |
| Logements après plafond densité (≤ 8) | ~6 à 8 | estimé | `0,05 ha × 150 logts/ha (30/niveau × 5)` |

**614 = 273 (reculs, sourcé) × 45 % (occupation, hypothèse) × 5 (niveaux, sourcé).**
Le seul maillon non réglementaire est le **45 %**.

### 888 m² (moteur d'implantation) — ce qui est mesuré

| Facteur | Valeur | Provenance |
|---|---|---|
| Zone d'implantation (géométrie réelle) | 265 m² | mesuré (≈ 273 des reculs) |
| **Emprise bâtie dessinée** | **199 m² = 75 %** de la zone | **mesuré par le solveur** (contrôle CES ≤ 306 m² → Réussi) |
| Niveaux | R+4 (5 niv.) | sourcé — identique au 614 |
| Pleine terre | 310 m² (≥ 102 m² requis) | mesuré, Réussi |
| Stationnement | 0 place, « À confirmer » | règle Ud **existante au PLU, non ingérée par LABUSE** → non déduite (comme le 614) |
| **SDP du scénario** | **888 m²** | somme des planchers dessinés |

**L'écart +274 m² tient à un seul facteur : l'occupation.** Le moteur analytique
pose **45 %** par hypothèse ; le solveur en **tasse 75 %** (199 m² au lieu de 123 m²).
Même terrain, mêmes reculs, mêmes 5 niveaux ; le stationnement (règle existante au PLU, non ingérée par LABUSE) n'est déduit dans aucun des deux.

> **Correctif de vocabulaire (LOT C, décision Vic) :** à Saint-Pierre la règle de stationnement existe
> (≈ 1 place / 75 m² de logement, art. Ud6) ; LABUSE ne l'a simplement pas ingérée. Les 888 m² sont donc
> un **majorant** (stationnement non déduit), pas une capacité. On n'écrit plus « non opposable » ni
> « aucun ratio » : « **règle existante, non ingérée par LABUSE** ».

---

## 3. D'où sortent les 45 % ?

`coef_occupation = 0.45` — défini **par commune** dans `config/plu_zonage.yaml`
(entrée `'97416' → hypotheses_faisabilite → coef_occupation: 0.45`), défaut `engine.py:64`.

Phrase d'hypothèse servie, verbatim :
> « Coefficient d'occupation du gabarit supposé 45 % (on ne bâtit pas 100 % de l'emprise constructible). »

C'est **une hypothèse de modélisation (prov = estimee)**, pas une règle du PLU. Le code le dit
lui-même (`engine.py:707-716`) : « `coef_occupation` est un facteur de MODÉLISATION (occupation du
gabarit), PAS l'emprise réglementaire ». Il représente « les espaces entre bâtiments, les accès »,
posés à plat. Le solveur, lui, ne suppose rien : il place des bâtiments et mesure ce qui tient.

---

## 4. Ce que le règlement de la zone Ud (Saint-Pierre) dit réellement

Lu dans les `source` des étapes (calibrage PLU validé) :

| Sujet | Règle réelle | Article |
|---|---|---|
| **Emprise au sol (CES)** | **60 %** de l'unité foncière | Art. Ud3.4 · p. 83 |
| **Hauteur** | 15 m à l'égout / 20 m au faîtage → **R+4** | Art. Ud3.5 · p. 84 |
| **Reculs** | alignement ou **3 m** (voie) ; **3 m** séparatives | Art. Ud3.1/3.2 · p. 81-82 |
| **Stationnement** | **règle existante au PLU (≈ 1 place / 75 m², art. Ud6), non ingérée par LABUSE** → non déduite | Art. Ud6 |
| **Pleine terre** | **20 %** min. en pleine terre (biotope 30 %) pour UF > 250 m² | Art. Ud5.1 · p. 91 |

Donc : l'emprise (60 %), la hauteur et la pleine terre **sont** réglementées et sourcées.
Sur HT0538 ce ne sont pas elles qui bornent (les reculs donnent 273 < 306 du CES), et le
stationnement n'est pas opposable. **Le seul facteur libre reste l'occupation (45 %).**

---

## 5. Les onze parcelles — fiche vs Étude

| idu | commune | zone | surf. | SDP fiche (614) | SDP Étude (888) | écart | cause |
|---|---|---|---|---|---|---|---|
| 97416000HT0538 | Saint-Pierre | Ud | 510 | 614 | **888** | **+274** | solveur tasse 75 % vs 45 % supposé |
| 97422000AD0887 | Le Tampon | Ud | 1699 | 1047 | **795** | **−252** | solveur **applique le barème stationnement** (8 places) + occupe 41 % < 45 % |
| 97402000AB1139 | Bras-Panon | Ud | 1331 | 163 | — | — | solveur : aucune implantation ne passe les contrôles durs |
| 97403000AL0482 | Entre-Deux | Ub | 1535 | 206 | — | — | idem |
| 97406000AC0565 | Plaine-des-Palmistes | Ur | 1597 | 212 | — | — | idem |
| 97408000AB0312 | La Possession | UBc | 421 | 103 | — | — | idem |
| 97401000AD1006 | Les Avirons | Ud1 | 1780 | 619 | — | — | idem |
| 97405000AB0177 | Petite-Île | UC | 416 | 159 | — | — | idem |
| 97409000AB0392 | Saint-André | UC | 1528 | 20 | — | — | zone après reculs ≈ 0 m² |
| 97410000AB0815 | Saint-Benoît | AUp1 | 1122 | 13 | — | — | aucune implantation valide |
| 97412000AH0410 | Saint-Joseph | U5vi | 1649 | 73 | — | — | zone après reculs ≈ 39 m², trop étroite pour une barre |

**Lecture.**
- **Le signe de l'écart n'est pas constant** : Étude > fiche (HT0538) ou Étude < fiche (Le Tampon).
  Il dépend de ce que le solveur rencontre : s'il tasse plus que 45 %, il monte ; si un **contrôle dur
  (surtout le stationnement) mord**, il descend sous la fiche.
- **8 parcelles sur 11 : le solveur ne rend aucun chiffre** (zone trop étroite après reculs, ou aucune
  emprise ne passe tous les contrôles durs dont le stationnement aérien). La fiche, elle, imprime
  toujours une petite SDP (13 à 619 m²) tirée de la seule géométrie des reculs × 45 %.
- Reculs, CES et niveaux **concordent** entre les deux moteurs. **La divergence est l'occupation**
  (hypothèse plate contre mesure), et secondairement le **stationnement** (servi côté solveur, pas côté fiche).

### Provenance de chaque facteur (synthèse)
- Reculs / zone d'implantation → **PLU sourcé** + **mesuré** (géométrie cadastrale réelle côté solveur).
- CES (emprise %) → **PLU sourcé**.
- Niveaux / hauteur → **PLU sourcé**.
- **Occupation 45 % → HYPOTHÈSE** (614) ; **emprise mesurée/tassée** (888). *← seule vraie divergence.*
- Rendement SDP→habitable 80 % → hypothèse.
- Densité 30 logts/ha/niveau → hypothèse (« filet ex-COS, le PLU ne fixe aucune densité »).
- Stationnement → **ingéré et appliqué là où le barème est chargé** (Le Tampon) ; **règle existante au PLU mais non ingérée par LABUSE** en Ud Saint-Pierre (donc non déduite).
- Pleine terre → **PLU sourcé**.

---

## 6. Proposition — une seule définition de la capacité *(à valider avant implémentation)*

**Constat.** Deux moteurs produisent deux grandeurs portant le même mot « capacité / SDP ». Ni l'un ni
l'autre n'est « la » capacité réglementaire : le 614 est une estimation à occupation forfaitaire, le 888
est la meilleure implantation que le solveur sait dessiner. Le lecteur voit deux nombres sans savoir
lequel retenir.

**Définition unique proposée.** *La capacité d'une parcelle = la SDP du meilleur scénario d'implantation
que le solveur sait placer en respectant reculs, CES, pleine terre et stationnement.* C'est la seule
grandeur qui respecte géométriquement tous les facteurs. Le forfait 45 % n'est plus une capacité
concurrente : il devient un **repli explicite**, nommé comme tel, quand le solveur ne rend rien.

Concrètement :

1. **Quand le solveur rend un scénario** (HT0538, Le Tampon) → **tous les documents citent ce chiffre**
   (888, 795) comme *la* capacité. Le 614 forfaitaire disparaît de l'affichage, ou passe en note
   « pré-estimation forfaitaire » clairement subordonnée. Jamais deux nombres pour un même concept.
2. **Quand le solveur ne rend rien** (8/11 ci-dessus) → on sert l'estimation analytique **nommée
   explicitement** « estimation forfaitaire (occupation 45 % supposée), le solveur n'a pas trouvé
   d'implantation — à confirmer », jamais « SDP maximale réglementaire ».
3. **Nom par document :**
   - **Dossier / fiche** : « Surface de plancher — estimation » (+ renvoi « capacité détaillée : Étude
     de faisabilité »). Jamais « maximale réglementaire » ni « jusqu'à » tant qu'un 45 % y entre.
   - **Étude de faisabilité** : « Surface de plancher du scénario — meilleure capacité trouvée ».
   - **Comparatif / pré-dossier** : la même valeur que le Dossier, sous le même nom.
4. **Garde-fou** : un invariant de test « le chiffre de capacité du Dossier == celui servi par la source
   unique » (étendre le contrôle de cohérence existant), pour qu'aucun document ne réinvente un nombre.

**Ce que le LOT B a déjà fait sans attendre** (cf. `COMPTE-RENDU.md`) : retirer le nom trompeur
« SDP **maximale réglementaire** » du 614 et le nommer **estimation** avec ses facteurs écrits — étape
compatible avec cette proposition et sûre à faire dès maintenant. L'unification des deux moteurs (§6.1-6.2)
reste en attente de ta décision.
