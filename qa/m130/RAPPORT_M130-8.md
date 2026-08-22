# M130-8 — Faux positif : la part doit être constructible pour être annoncée

Branche `feat/m130-pdf-projet`. Ne pas merger.
`git branch` = `feat/m130-pdf-projet` · `git log -1` (départ) = `526249c4` ·
`lsof -ti:8000 | xargs kill -9` = serveur dev tué. PDF via `generer_pdf_qa.py`
(pids 88–91) : `M130-8-projet-{P1..P4}.pdf`.

---

## A — On n'annonce plus une part constructible sans l'avoir vérifiée

Nouveau test `_part_ouverte(code)` = **U ou 1AU** (et AU sans indice) ; **exclut A,
N, 2AU / 3AU…** (zones AU fermées). Il remplace tout test sur la seule famille de
la zone dominante (« à urbaniser » incluait 2AU → faux positif).

Quatre cas sur la ligne multi-zones :

| Cas | Condition | Texte |
|---|---|---|
| 3 | SDP chiffrée > 0 | « SDP calculée sur la partie constructible ; … » (E.1 si tout ouvert) |
| 4 | résiduel calculé et nul | « le résiduel calculé est nul sur la part {dominante} ; … » |
| 1 | SDP supprimée + **part ouverte** | « la SDP n'est pas chiffrée ; une part {zone} (~ {pct} %, soit ~ {m²} — Estimé) est constructible et reste à instruire. » (sous-cas étage 0 : « écartée du vivier, mais une part … ») |
| 2 | **aucune part ouverte** | « aucune des parts n'est ouverte à l'urbanisation. » |

**Les 8 IDU du mandat — texte rendu mot pour mot** (tous en **cas 2** ; ils
disaient « une partie constructible peut exister ») :

| IDU | Ligne rendue |
|---|---|
| `97416000HI0189` | A (agricole) ~ 89 % · N (naturelle) ~ 11 % — **aucune des parts n'est ouverte à l'urbanisation.** |
| `97416000HI0538` | A ~ 69 % · N ~ 31 % — aucune des parts n'est ouverte à l'urbanisation. |
| `97416000HK0078` | A ~ 69 % · N ~ 31 % — aucune des parts n'est ouverte à l'urbanisation. |
| `97416000HL0023` | N ~ 69 % · A ~ 31 % — aucune des parts n'est ouverte à l'urbanisation. |
| `97422000AD0250` | 2AUd (à urbaniser) ~ 73 % · A ~ 27 % — aucune des parts n'est ouverte à l'urbanisation. |
| `97422000AK0945` | 2AUc ~ 78 % · Nco ~ 22 % — aucune des parts n'est ouverte à l'urbanisation. |
| `97422000AX1477` | 2AUe ~ 94 % · Nco ~ 6 % — aucune des parts n'est ouverte à l'urbanisation. |
| `97422000CX0670` | 2AUc ~ 71 % · A ~ 29 % — aucune des parts n'est ouverte à l'urbanisation. |

**Décompte des 4 cas par projet** (parcelles multi-zones uniquement) :

| Projet | cas 1 (part ouverte) | cas 2 (aucune ouverte) | cas 3 (SDP > 0) | cas 4 (calculé nul) | total multi-zones |
|---|---|---|---|---|---|
| **P1** | 0 | 0 | 6 | 1 | 7 |
| **P2** | 3 | **4** | 11 | 5 | 23 |
| **P3** | 2 | **4** | 0 | 2 | 8 |

Les 8 IDU passés de « peut exister » à « aucune des parts n'est ouverte » = les 4
cas 2 de P2 + les 4 cas 2 de P3 (tableau ci-dessus).

**Confirmation : aucun bloc ne dit « peut exister »** — 0 occurrence dans les 4
PDF. Toute part constructible annoncée est désormais **nommée** (zone + %).

---

## B — Finitions

- **B.1** P3, en-tête complet après correctif :
  > Liste plafonnée : 60 parcelles figées sur ~ 10 725 retenues par le cadrage,
  > **toutes classées à l'étage 0** (à ce jour). Les figées ont été SÉLECTIONNÉES
  > par probabilité de mutation (critère interne du moteur) — un rang non visible ;
  > elles sont présentées ici par ordre géographique. Élargir la shortlist ne
  > supprime pas ce rang : seule une liste complète ou un tri explicite (surface)
  > est neutre. Cette sélection est intégralement composée de parcelles que le
  > moteur a écartées de son vivier exploitable. Elles n'ont pas vocation à être
  > instruites en l'état — voir toutefois les parcelles multi-zones ci-dessous.

  (« toutes classées à l'étage 0 » quand la part vaut le total ; virgule
  rétablie — un `.replace(',', ' ')` global la mangeait, corrigé via un helper
  `_num` qui n'espace QUE les milliers.)
- **B.2** part constructible nommée + surface : ex. `97416000CX1483` →
  « une part Uf (~ 42 %, **soit ~ 210 m² — Estimé**) est constructible : à
  instruire séparément » (surface = pct × surface parcelle, étiquetée Estimé).

---

## C — Consigné (non traité)

- **C.1** La métrique interne « parcelles étage 0 à part constructible ≥ 5 % »
  valait **51** en M130-7 parce qu'elle comptait aussi les **mono-zones
  urbaines**, alors que le document ne porte que des **lignes multi-zones**.
  Corrigée ici pour ne compter que les **multi-zones** (P3 = 4). Elle ne sert que
  de **déclencheur booléen** de l'incise d'en-tête (« voir toutefois… »), **jamais
  de base de décision** — à ne pas réutiliser comme dénombrement métier.

ruff : 0 erreur nouvelle (I001 restantes = imports pré-existants décalés).
