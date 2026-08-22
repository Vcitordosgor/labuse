# M130-10 — Hauteur de la part ouverte, formule « autres parts », EP1044

**⚠ Branche** : le mandat vise `feat/m130-9-rattrapage` (commit `ae34b4cd`), mais
cette branche/ce commit **n'existent pas** dans le dépôt (ni local, ni
`origin` ; seul `feat/m130-pdf-projet` @ `f4eb8fd6` porte la lignée M130). Comme
il est interdit de créer une branche ou de toucher à `main`, les correctifs sont
livrés sur **`feat/m130-pdf-projet`** (qui contient M130-9, base de ce mandat) —
à **rebaser / cherry-pick** sur `feat/m130-9-rattrapage`. Rien n'est mergé.

`lsof -ti:8000 | xargs kill -9` = serveur dev tué. PDF via `generer_pdf_qa.py`
(pids 128–131) — désormais **gitignorés** (§E).

---

## A — Hauteur de la part ouverte (nommée)

Quand la ligne multi-zones nomme une part ouverte (U / 1AU), la ligne Hauteur
porte la hauteur de **cette part** (résolue sur SA zone), nommée. Les 5 lignes :

| IDU | part ouverte | Hauteur servie + source |
|---|---|---|
| `97422000BV2471` | Ua (48 %) | **part Ua — égout 21 m · faîtage 25 m** (Sourcé — PLU calibré · Art. Ua10.2, p.16) |
| `97422000CL1113` | Uc (49 %) | **part Uc — égout 9 m · faîtage 13 m** (Art. Uc10.2, p.46) |
| `97422000DH0211` | Uc (18 %) | **part Uc — égout 9 m · faîtage 13 m** (Art. Uc10.2, p.46) |
| `97416000CX1483` | Uf (42 %) | **part Uf — égout 6 m · faîtage 11 m** (Art. Uf3.5, p.119) |
| `97416000EX0280` | Uf (7 %) | **part Uf — égout 6 m · faîtage 11 m** (Art. Uf3.5, p.119) |

Si plusieurs parts ouvertes → la plus grande en surface (« part … »). Si la zone
ouverte n'est pas au PLU calibré → « part X — non renseignée au PLU calibré ».

**Contrôle A** : 0 parcelle affichant « part X — non renseignée » alors que la
hauteur de cette zone existe au PLU calibré (les 5 zones ci-dessus étaient
calibrées et sont désormais servies).

---

## B — « les autres parts » ne contient jamais la zone principale

Le libellé des parts fermées dépend de si la **principale (dominante)** est
ouverte :
- principale **ouverte** (dans la tête) → « la part Nco (~ 26 %) est fermée à
  l'urbanisation » / « les autres parts (…) sont fermées » — la principale en est
  exclue.
- principale **fermée**, aucune part ouverte → « **aucune part n'est ouverte à
  l'urbanisation (2AUd, A)** » (jamais « les autres parts »).
- principale **fermée**, une part ouverte nommée → « **aucune autre part n'est
  ouverte à l'urbanisation (A, N)** » (la principale n'est pas « autre » que la
  part nommée).

Exemples :
- `97422000AD0250` : « … — **aucune part n'est ouverte à l'urbanisation (2AUd,
  A).** »
- `97416000EX0280` : « A ~ 64 % · N ~ 29 % · Uf ~ 7 % — écartée du vivier ; une
  part Uf (~ 7 %, soit ~ 950 m² — Estimé) est constructible et reste à instruire ;
  **aucune autre part n'est ouverte à l'urbanisation (A, N).** »
- `97422000BV2471` : « … une part Ua (~ 48 %, soit ~ 2 033 m² — Estimé) …
  reste à instruire ; **aucune autre part n'est ouverte à l'urbanisation (Nco)** ;
  ~ 2 % relèvent d'autres zones, non détaillées. »

**Grep de contrôle B** — « les autres parts (…) » contenant le code de la zone
principale de la parcelle : **compte = 0** (vérifié programmatiquement sur les 4
documents). Régression « restent à instruire » (générique) : **0**.

**Décompte des 3 sorties par document** (multi-zones) :

| Doc | sortie 1 (toutes fermées) | sortie 2 (≥ 1 ouverte) | sortie 3 (mixte) |
|---|---|---|---|
| P1 | 5 | 2 | 0 |
| P2 | 18 | 4 | 1 |
| P3 | 8 | 0 | 0 |
| P4 | 0 | 0 | 0 |

---

## C — EP1044 : référence fausse retirée du PDF

La source de hauteur de `Us` est nettoyée de la référence qui désigne une AUTRE
zone (les AU0). `_hauteur_src_dezone` coupe au « ; Art. AU0… » (sauf si la zone
est elle-même une AU0). Rendu `EP1044` :

> Hauteur PLU : égout non réglementé · faîtage 4 m (Sourcé — PLU calibré ·
> **Préambule Us p.129 + Art. Us1 (tableau) p.130**)

Contrôle : **0** occurrence de « AU01 » dans P3. Une source incomplète est
acceptable ; une source qui pointe une autre zone ne l'est plus.

### Dette DATA (reste ouverte)

Le fond reste à corriger dans `config/plu_saint_pierre.yaml` : l'entrée est
**partagée** entre `Us` et les zones AU0 (`liste: ["Us","AU01","AU02","AU03",
"AU0c-1"]`, une seule `source`). Il faut **séparer** l'entrée `Us` (Art. Us1,
p.130) de celle des AU0 (Art. AU01, p.200), et vérifier que le faîtage 4 m servi
à `Us` provient bien de `Us1` (et non des annexes AU0). Rejoint la dette **F.2 de
M130-6** (`*_src`). Le nettoyage PDF ci-dessus est un garde-fou d'affichage, pas
le correctif de fond.

---

## D — En-tête P3 conditionnel

L'incise « — voir toutefois les parcelles multi-zones ci-dessous » n'est ajoutée
que si au moins une ligne du document nomme une part ouverte
(`etage0_constructible > 0`). P3 = 4 → incise présente ; un document sans part
ouverte (compteur 0) ne l'afficherait pas et s'arrêterait à « … instruites en
l'état. ».

---

## E — .gitignore

`qa/m130/*.pdf` ajouté au `.gitignore` ; les 4 PDF suivis désindexés
(`git rm --cached`). Artefacts régénérables par le script — plus de conflit
binaire au merge.

ruff : 0 erreur nouvelle (I001 restantes = imports pré-existants décalés).
