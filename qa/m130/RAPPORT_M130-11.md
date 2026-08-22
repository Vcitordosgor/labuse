# M130-11 — Préfixe « part X » restreint, hauteur muette si rien n'est ouvert

**⚠ Branche** : `feat/m130-9-rattrapage` reste **inexistante** dans le dépôt
(ni local, ni `origin`). Livré sur **`feat/m130-pdf-projet`** (lignée M130) — à
rebaser sur ta branche rattrapage. Ni merge, ni création de branche, ni `main`.
`lsof -ti:8000 | xargs kill -9` = serveur tué. PDF via `generer_pdf_qa.py`
(gitignorés).

---

## A — Préfixe « part X — » seulement si X ≠ zone principale

Règle : le préfixe s'affiche **ssi la zone dont la RÈGLE est servie diffère de la
zone principale** de la parcelle. **Compte total « Hauteur PLU : part … » = 5**,
sur les 4 PDF :

| IDU | doc | préfixe |
|---|---|---|
| `97422000BV2471` | P2 | part Ua — égout 21 m · faîtage 25 m (Art. Ua10.2, p.16) |
| `97422000CL1113` | P2 | part Uc — égout 9 m · faîtage 13 m (Art. Uc10.2, p.46) |
| `97422000DH0211` | P2 | part Uc — égout 9 m · faîtage 13 m (Art. Uc10.2, p.46) |
| `97416000CX1483` | P3 | part Uf — égout 6 m · faîtage 11 m (Art. Uf3.5, p.119) |
| `97416000EX0280` | P3 | part Uf — égout 6 m · faîtage 11 m (Art. Uf3.5, p.119) |

`BI1097` : la hauteur servie est celle de sa zone principale `1AUe` (via renvoi
Ue10.2) → `1AUe == principale` → **plus de préfixe** (et muette, cf. B).

---

## B — Hauteur muette quand rien n'est constructible

**Position retenue** : la ligne Hauteur ne sert un **chiffre** (égout/faîtage) que
si la parcelle a une part **à la fois ouverte ET constructible** :
- une **SDP résiduelle > 0** sur la zone ouverte (dominante), ou
- une **part ouverte minoritaire** nommée « constructible à instruire » (les 5
  lignes du §A).

Sinon — résiduel calculé **nul**, ou aucune part ouverte (zone fermée), y compris
sur une zone qui porterait une hauteur d'annexes (2AU) — la ligne écrit **l'état,
pas un chiffre** :

> Hauteur PLU : **sans objet (aucune capacité constructible en l'état)**

Les A/N sans hauteur au PLU calibré restent « non renseignée au PLU calibré »
(état de donnée, aucun chiffre à taire). `HY0897` / `HY0902` (résiduel nul sur Ug)
sont désormais **muettes** — on ne sert plus une hauteur de construction là où on
vient d'écrire « le résiduel calculé est nul ».

**Parcelles concernées (« sans objet ») par document** — la règle s'applique
**uniformément** (toute parcelle à hauteur calibrée mais sans capacité
constructible en l'état) :

| Doc | « sans objet » | dont les cas notés au mandat |
|---|---|---|
| P1 | 8 | `CW1056` (résiduel nul) |
| P2 | 31 | `AD0250` `AK0945` `AX1477` `CX0670` (2AU fermées) · `AE0619` `AP0249` `BI1097` (résiduel nul) |
| P3 | 44 | `HY0897` `HY0902` (résiduel nul) + les parcelles écartées |
| P4 | 0 | — |

(Volume élevé sur P3 : ce sont des parcelles **écartées du vivier** — leur servir
une hauteur de construction était précisément le défaut visé.)

---

## C — En-tête P3 : compté sur les lignes rendues

L'incise « — voir toutefois les parcelles multi-zones ci-dessous » est branchée
sur le **nombre de lignes qui nomment réellement une part ouverte constructible**
(cas 1 = `_nomme_part_constructible`), compté sur les parcelles telles que
rendues — plus sur `etage0_constructible` (qui comptait aussi les « résiduel
nul »).

**Nombre de lignes à part ouverte par document** : **P1 = 0 · P2 = 3 · P3 = 2 ·
P4 = 0**. P3 = 2 (`CX1483`, `EX0280`) → incise **présente** (1 occurrence).
Un document sans part ouverte (compteur 0) ne l'afficherait pas.

---

## D — BV2471 : ordre + périmètre du constat

Ordre des segments : parts ouvertes → parts fermées nommées → **agrégat en
dernier**. Et « **nommée** » borne le constat aux parts listées (l'agrégat ~ X %
n'est pas couvert). Rendu :

> Nco (naturelle) ~ 50 % · Ua (urbaine) ~ 48 % — la SDP n'est pas chiffrée ; une
> part Ua (~ 48 %, soit ~ 2 033 m² — Estimé) est constructible et reste à
> instruire ; **aucune autre part nommée n'est ouverte à l'urbanisation (Nco)** ;
> ~ 2 % relèvent d'autres zones, non détaillées.

---

## E — Explication de `projets.py`

`_shortlist_pdf` (et ses helpers) **vit dans `api/projets.py` depuis M130-2** :
c'est la **couche de DONNÉES du PDF projet** (elle lit la shortlist figée,
résout zones/hauteurs, calcule le total) — `render_projet_pdf` (dans
`pdf_projet.py`) n'est que le rendu. Résoudre une hauteur (via `resolve_zone`)
appartient donc à cette couche, pas au render. Les changements M130-10 y sont
**nécessaires au PDF projet** :

- `_part_ouverte(code)` (M130-8) : test U / 1AU — partagé entre `_shortlist_pdf`
  (calcul de `part_constructible`) et `pdf_projet` (partition des parts).
- `_hauteur_src_dezone(zone, src)` (M130-10 §C) : retire d'une source de hauteur
  la référence qui pointe une AUTRE zone (Us ← Art. AU01) ; appliqué au montage
  de `hauteur_source`. Nécessaire à C.
- bloc `hauteur_part_ouverte` dans `_shortlist_pdf` (M130-10 §A) : résout la
  hauteur de la part ouverte nommée (`resolve_zone(part, commune)`) pour que le
  render puisse servir « part Uf — … ». Nécessaire à A.

Aucun de ces éléments n'est utilisé ailleurs que par le PDF projet → **rien à
sortir** ; ils sont à leur place (couche données). Aucune autre fonction de
`projets.py` (API, cadrage, figeage) n'a été touchée.

ruff : 0 erreur nouvelle (I001 restantes = imports pré-existants décalés).
