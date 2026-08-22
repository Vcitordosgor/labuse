# M130-2 — PDF projet : rapports §1.4 et §6 (+ correctifs §1–§5)

Branche `feat/m130-pdf-projet`. Ne pas merger.

PDF joints (P1/P2/P3 + P4 pour l'état dégradé) :
`M130-2-projet-P1-large-ile.pdf`, `…-P2-etroit-tampon.pdf`,
`…-P3-ecartees-stpierre.pdf`, `…-P4-non-fige.pdf`.

---

## §1.4 — Combien de projets existants n'ont pas de shortlist figée exploitable ?

Sur **18 projets** en base (une shortlist « exploitable » = `derniere_execution_at`
renseignée **ET** au moins une ligne `projet_parcelles` non écartée) :

| Situation | Projets |
|---|---|
| **Figée exploitable** (date + parcelles) | **7 / 18** |
| Sans `derniere_execution_at` (jamais datée) | 9 / 18 |
| Sans aucune ligne `projet_parcelles` | 5 / 18 |
| Datée mais **0 parcelle** (figeage vide) | 2 (ids 17, 18) |
| Parcelles présentes mais **non datées** (figeage incomplet) | 6 (ids 25, 26, 33, 34, 37, 39) |

**Conséquence produit** : **11 projets sur 18** ne peuvent PAS être servis en
présentation aujourd'hui. Le correctif §1 les gère explicitement : le PDF affiche
« Ce projet n'a pas de shortlist figée exploitable — lancez (ou relancez) le
cadrage… » et **ne fabrique aucun run** (cf. `M130-2-projet-P4-non-fige.pdf`).
C'est un signal à remonter côté app : beaucoup de projets sont restés au stade
cadrage sans figeage, ou ont été figés avant que `projet_parcelles` soit écrite.

---

## §6 — Fraîcheur : les sources servies ont-elles un millésime amont ?

| Donnée servie | Source | Millésime amont ? | Traitement |
|---|---|---|---|
| **Zone PLU** | `spatial_layers kind='plu_gpu_zone'`, attribut `idurba` (GPU/API_CARTO) | **Oui** — la date d'approbation du PLU est portée par `idurba` (ex. `97401_PLU_20241206` → 06/12/2024) | **Affiché** : « Sourcé — GPU/PLU, millésime JJ/MM/AAAA » |
| **Hauteurs égout/faîtage** | `resolve_zone` (YAML PLU calibré) | Partiel — la **source article** est chiffrée (`Art. Ua10.2, p.16`), le millésime est celui du **même PLU** (idurba de la zone) | Article affiché ; le millésime PLU est celui de la zone (ligne au-dessus) |
| **SDP résiduelle** | `parcel_residuel.sdp_residuelle_m2` (dérivée du moteur) | **Non** — c'est un **calcul** (pas une source amont) ; `computed_at` est une date de run | Marquée **Estimé**, sans millésime (jamais de date de run affichée) |
| **Adresse** | BAN (DINUM/IGN) | millésime BAN non porté par ligne | pied de page « Base Adresse Nationale » |

**Doctrine appliquée** : on affiche la **date de la source amont** (approbation
PLU via `idurba`), **jamais une date de run**. À défaut de millésime, le document
écrit « **millésime non renseigné** » (helper `_plu_millesime`). La SDP, étant un
calcul, porte **Estimé** et aucun millésime (on ne déguise pas `computed_at` en
millésime amont). Vérifié sur les 3 packs : millésimes réels affichés (La
Plaine-des-Palmistes 27/05/2023, La Possession 17/12/2025, Le Tampon 11/08/2023,
Saint-Pierre 25/06/2024).

---

## Correctifs §1–§5 (résumé, vérifiés sur P1/P2/P3/P4)

- **§1** — l'export sert la **shortlist figée** (`projet_parcelles`, helper
  `_shortlist_pdf`), **plus aucun recalcul live** ; **deux dates nommées** en tête
  (« Cadrage figé le … · Document généré le … ») ; **pas de shortlist → état
  explicite**, aucun run fabriqué.
- **§2** — **verdict/rang/score purgés** : plus de « Priorité/À suivre/Écartée »,
  plus de numérotation 1..5 ni « MEILLEURES PARCELLES ». Titre neutre
  « PARCELLES DE LA SHORTLIST » ; **ordre géographique** (commune, section, n°).
  `_pourquoi_lignes` nettoyé du code mort (`qualité X/100`, `Probabilité`).
- **§3** — chaque parcelle porte de la **donnée** : **SDP résiduelle** (Estimé, ou
  raison honnête si non calculable — « terrain trop exigu », « zone non
  constructible »…), **hauteurs calibrées égout/faîtage** via `resolve_zone`
  (Sourcé — PLU calibré + article, ou Estimé — générique), **zone PLU + famille
  correcte** (U = urbaine, AU = à urbaniser, A = agricole — jamais le faux
  libellé M129). `_q_v2_list` **non modifié** (voir note d'arbitrage ci-dessous) ;
  `q_score` **non ajouté**. Chaque valeur porte **Sourcé** ou **Estimé**.
- **§4** — la **mention** décrit exactement ce qui est rendu (aucune promesse de
  score) ; **une seule population** (la shortlist figée) → l'incohérence P3
  « 0 correspondent + 5 parcelles » a disparu ; décompte vide → état explicite.
- **§5** — en-tête « **document de présentation** » ; section « **CE QUE CE
  DOCUMENT NE PEUT PAS DIRE** » (cadrage = jeu de filtres, shortlist datée, aucune
  parcelle validée) ; nommage **`projet-{id}-{slug}-labuse.pdf`** ; aucune
  variante copilote/kanban (inchangé).

### Note d'arbitrage sur §3.4

Le mandat demandait d'ajouter `sdp`/`hauteur`/`zone` à **`_q_v2_list`**. Or §1
fait que l'export **ne lit plus `_q_v2_list`** (chemin LIVE) mais la **shortlist
figée**. Ajouter ces champs à `_q_v2_list` serait donc du code mort pour ce
document (et alourdirait la liste ÎLE entière, chemin perf sensible). L'enrichissement
`sdp`/`hauteur`/`zone` est donc posé **au point où l'export lit la donnée** —
`_shortlist_pdf` — via la **même source auditée** que `collect_report_data`
(spatial_layers `plu_gpu_zone` + `parcel_residuel` + `resolve_zone`). À arbitrer
si tu préfères néanmoins le porter dans `_q_v2_list`.
