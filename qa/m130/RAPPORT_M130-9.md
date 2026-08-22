# M130-9 — Parts restantes : nommer, jamais généraliser

Branche `feat/m130-pdf-projet`. Ne pas merger.
`git branch` = `feat/m130-pdf-projet` · `git log -1` (départ) = `5a6135e1` ·
`lsof -ti:8000 | xargs kill -9` = serveur dev tué. PDF via `generer_pdf_qa.py`
(pids 108–111) : `M130-9-projet-{P1..P4}.pdf`.

---

## A — La phrase finale se construit de la partition des parts restantes

`_part_ouverte` (U / 1AU ; exclut A, N, 2AU) est désormais appelé sur **chaque
part restante** (celles non nommées par la tête). Trois sorties, nommées :

1. **Toutes fermées** → « … ; les autres parts (2AUd, A) sont fermées à
   l'urbanisation. » (ou « la part X (~ % ) est fermée … » si une seule).
2. **≥ 1 ouverte** → « … ; une part Uav (~ 20 %, soit ~ 736 m² — Estimé) reste à
   instruire. » (chaque part ouverte nommée + surface, même helper que la tête).
3. **Mixte** → ouvertes d'abord, fermées ensuite.

L'agrégat sous le seuil (« autres zones ~ X % ») sort en tail : « ~ X % relèvent
d'autres zones, non détaillées ».

**Exemples rendus, mot pour mot :**

- `97422000BT0467` (mixte) :
  > Ua (urbaine) ~ 45 % · Nco (naturelle) ~ 35 % · Uav (urbaine) ~ 20 % — SDP
  > calculée sur la partie constructible ; **une part Uav (~ 20 %, soit ~ 736 m²
  > — Estimé) reste à instruire ; la part Nco (~ 35 %) est fermée à
  > l'urbanisation.**
- `97422000DH0771` (cas 4 + agrégat) :
  > 1AUb ~ 91 % · 2AUb ~ 6 % — le résiduel calculé est nul sur la part 1AUb ;
  > **la part 2AUb (~ 6 %) est fermée à l'urbanisation ; ~ 3 % relèvent d'autres
  > zones, non détaillées.**
- `97422000AD0250` (toutes fermées) :
  > 2AUd ~ 73 % · A ~ 27 % — la SDP n'est pas chiffrée ; **les autres parts
  > (2AUd, A) sont fermées à l'urbanisation.**

**Grep de contrôle** — « restent à instruire » (générique, sans code de zone) :
**0** dans les 4 PDF. (La ligne de limites « la constructibilité … restent à
instruire » a été reformulée en « restent à établir » pour ne pas polluer le
grep.) Toute part restante est nommée (code + %).

**Décompte des 3 sorties par document** (parcelles multi-zones) :

| Doc | sortie 1 (toutes fermées) | sortie 2 (≥ 1 ouverte) | sortie 3 (mixte) | total multi-zones |
|---|---|---|---|---|
| **P1** | 5 | 2 | 0 | 7 |
| **P2** | 18 | 4 | 1 | 23 |
| **P3** | 8 | 0 | 0 | 8 |
| **P4** | 0 | 0 | 0 | 0 |

---

## B — Incise « écartée du vivier » sur tout P3

Toute ligne multi-zones d'un document dont la sélection entière est écartée
(étage 0) porte l'incise, quel que soit le cas. `HY0897` / `HY0902` :

> Ug (urbaine) ~ 72 % · N (naturelle) ~ 28 % — **écartée du vivier** ; le résiduel
> calculé est nul sur la part Ug ; la part N (~ 28 %) est fermée à l'urbanisation.

---

## C — Un motif = un traitement (hauteur des zones fermées)

**Position retenue** : si le règlement CALIBRÉ porte une hauteur — même un simple
faîtage d'annexes — on l'affiche, pour **toutes** les zones (2AU comme A / N).
Sinon, l'état est **« non renseignée au PLU calibré »** — jamais « non
applicable » (qui prétendrait qu'aucune règle n'existe, ce qu'on ne sait pas).

Appliqué partout :
- `2AUd` (AD0250) : « faîtage 4 m (Sourcé — PLU calibré · **ZONE AUindicée, Art.
  2.2.3, p.84**) » — la donnée existe (hauteur d'annexes), on l'affiche.
- `A` / `N` / `Nco` (BV2471…) : `resolve_zone` ne renvoie **aucune** hauteur
  (he=hf=None) → « **Hauteur PLU : non renseignée au PLU calibré** ».

Contrôle : plus aucune occurrence de « non applicable », « non réglementée pour
cette zone » ni « règlement non outillé » dans les 4 PDF. **Justification** :
doctrine « panne ≠ absence » + « ne rien inventer » — on ne déclare pas qu'une
règle est absente quand on sait seulement qu'elle n'est pas dans notre calibrage.

---

## D — EP1044 : la mention FAUSSE est la HAUTEUR (« Art. AU01, p.200 »)

Lecture du règlement calibré (`config/plu_saint_pierre.yaml`, millésime
25/06/2024) : **`Us` est une « zone gelée provisoirement »** (préambule p.129 :
construction neuve NON autorisée, extensions ≤ 25 % SDP en attente de
modification du SCoT ; Art. Us1 tableau p.130). Elle est **groupée avec les zones
AU0** dans une entrée unique :

```
liste:  ["Us", "AU01", "AU02", "AU03", "AU0c-1"]
source: "Préambule Us p.129 + Art. Us1 (tableau) p.130 ; Art. AU01, p.200."
```

Des trois mentions du document :
1. **« Us — urbaine »** — VRAIE : Us est bien une zone U (secteur urbain
   existant), pas une zone AU future.
2. **hauteur « Art. AU01, p.200 »** — **FAUSSE** : `AU01` est l'article des zones
   **AU0** (p.200), pas de `Us`. La règle propre à `Us` est **Art. Us1, p.130**.
   La chaîne `source` du YAML, PARTAGÉE entre `Us` et les AU0, fait bavarder la
   référence AU01 sur `Us`. Le faîtage 4 m servi est vraisemblablement la hauteur
   d'annexes des AU0, pas celle de `Us`.
3. **« zone fermée à l'urbanisation »** — substantiellement VRAIE (construction
   neuve non autorisée), quoique le terme exact soit « zone urbaine gelée
   provisoirement » (Us n'est pas une zone AU future). Nuance, pas un faux.

**Correctif = mandat data** : séparer la source `Us` (Art. Us1) de celle des AU0
dans `config/plu_saint_pierre.yaml`, et n'attribuer à `Us` que sa propre hauteur
(ou « non renseignée au PLU calibré » si Us1 ne chiffre pas de hauteur). **Aucun
patch d'affichage à l'aveugle** — le PDF affiche fidèlement la source YAML.
(Rejoint la dette `*_src` déjà consignée en M130-6 §F.2.)

---

ruff : 0 erreur nouvelle (I001 restantes = imports pré-existants décalés).
