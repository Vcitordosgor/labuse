# PIÈGES-RISQUES-2 — une seule source pour les deux modes

Suite de PIEGES-RISQUES-1. Avant : « Une parcelle » lisait les couches en direct (`spatial_layers`),
« Un lot » lisait la cascade pré-calculée de l'ancien scoring (`dryrun_cascade_results`, q_v11) → la
même parcelle affichait des listes différentes (BZ1065 : DPU et ANC absents en mode lot). **Décision
Vic exécutée : les deux modes — et la fiche — lisent la MÊME fonction, les couches en direct ; le lot =
l'union des parcelles.**

Branche `fix/pieges-risques-2` (worktree `labuse-pieges2`, base main `1c5fe81a`). Un commit par lot.
Point de vérité unique : **`servitudes.contraintes_parcelle(db, idu)`** (couches `spatial_layers` en
direct, filtres/libellés/dates communs), et **`servitudes.aleas_parcelle(db, idu)`** pour le risque gradué.

---

## Lot A — « Un lot » lit la même source que « Une parcelle » (commit `99f07f31`)

`/modules/duediligence` réécrit : pour chaque parcelle du lot il appelle `contraintes_parcelle` (la
fonction du mode parcelle) et en fait l'**union par contrainte** (catégorie + effet), chacune portant
le **nombre de parcelles touchées** (« N parcelles sur M »). Plus **aucune** lecture de
`dryrun_cascade_results` ni du scoring (score de risque, checklist, tier, seuils, CATNAT, propriétaire
retirés) — l'outil ne dépend plus de l'ancien run. Helpers cascade `_diligence_dossier` / `_seuils_crible`
supprimés. Frontend M10 réécrit : rend l'union (mêmes cartes que « une parcelle » + badge « N/M
parcelles »), garde barre/chips/collage/zoom (PIEGES-RISQUES-1 pt2) + pont Courrier.

**Grep prouvé** — la fonction `duediligence` ne contient plus `dryrun_cascade_results` /
`parcel_p_score_v2` / `_diligence_dossier` (garde-fou : `test_duediligence_ne_lit_plus_la_cascade`).

**Preuve (base réelle)** :
| Test | Résultat |
|---|---|
| BZ1065 seul == BZ1065 en lot d'une parcelle | 3 = 3, mêmes libellés ✓ |
| AI0090 seul == lot d'une parcelle | 6 = 6 ✓ |
| CH0318 (0 en parcelle) == lot d'une parcelle | 0 = 0 ✓ |
| Lot de 4 (BZ1065, AI0090, CH0318, AI0935) | **union exacte** : 8 contraintes distinctes, décomptes justes (SUP/PPR 3/4, 50 pas 2/4, ER 2/4, EBC 2/4, ANC/DPU/trait 1/4) ✓ |

> Le « risque 60 » que la cascade donnait à CH0318 (« vide » en mode parcelle) était un **score de
> l'ancien scoring**, pas une contrainte de couche : il recouvrait un aléa mouvement de terrain faible
> (désormais servi explicitement par le Lot B, sans note chiffrée). Il ne relève pas de cet outil.

---

## Lot B — compléter ce que le mode parcelle ne lisait pas (commit `56ba1f18`)

### É2 — PPR gradué + aléas par niveau (ajoutés aux DEUX modes)
Nouvelle fonction `aleas_parcelle` : lecture directe de `ppr` (zonage DEAL : **rouge** INTERDICTION /
**bleu** PRESCRIPTION) et `georisque_alea` (aléas par niveau), avec le **% de la parcelle touché**
(`ST_Union`), la **source DEAL** et le **millésime**. Seuils lus de la config partagée
`cascade_rules.yaml` (rouge : exclusion ≥ 50 %, vigilance forte ≥ 2 %, marginal en-dessous ; bleu :
marge < couverture min). Un seul niveau (le plus fort) par type d'aléa. Libellés nettoyés (miroir de
`risques_arbitrage.libelle_client_detail`). L'assiette SUP PM1 du PPR reste servie à part (catégorie
SUP), comme sur la fiche. Nouvelle catégorie « Risque naturel (PPR / aléa) ».

### É3 — prescriptions GPU : filtre élargi (justifié)
Le filtre `{01 EBC, 05 ER}` s'élargit aux typepsc CNIG qui **grèvent la constructibilité** :

| typepsc | ajouté ? | justification (1 ligne) |
|---|---|---|
| 01 Espace boisé classé | déjà | inconstructible |
| 05 Emplacement réservé | déjà | terrain grevé au profit d'un tiers public |
| **08** Terrain cultivé/planté à protéger (L151-23) | **+** | préservation imposée, quasi-inconstructible |
| **15** Règle d'implantation / bande de recul (graphique) | **+** | impose un recul à l'implantation |
| **17** Clause de logements aidés (mixité sociale, L151-15) | **+** | impose une part de LLS au programme |
| **18** Secteur d'OAP | **+** | le projet doit être compatible avec l'OAP (opposable) |
| **19** Secteur protégé (richesse sol/sous-sol) | **+** | constructibilité restreinte |
| **22** Linéaire commercial/services obligatoire | **+** | usage du rez-de-chaussée imposé |
| 07 patrimoine identifié | laissé | touche la démolition/modification, pas la constructibilité neuve ; volume élevé |
| 16 changement de destination autorisé | laissé | permission, pas contrainte |
| 02 secteur d'aléa inondation | laissé | déjà servi par la couche `risques` (Lot B) |
| 31 ZNIEFF | laissé | servi par le kind `znieff` |
| 04 zone tendue · 37 non réglementé · 99 renvois · 24 sentier · 03/45/48 | laissés | fiscal / informatif / régimes ponctuels |

Catégorie renommée « Prescription du PLU (constructibilité) ».

---

## Lot C — cohérence avec la fiche (commit `dda2cb9b`)

`_aleas_block` (bloc « aléas » du §Pièges & risques de la fiche) lisait la cascade
(`layer='risques'`). Il lit désormais `aleas_parcelle` (couches en direct), **comme l'outil** :
fiche et outil ne divergent plus. **Présentation inchangée** (structure `{n, liste:[nature, niveau,
part_pct, libelle, redhibitoire, source, millesime, ppr]}` conservée ; le front `risques.tsx` n'est pas
touché ; la référence d'arrêté PPR par commune reste rattachée aux lignes PPR). Les autres blocs du
§Pièges & risques (dispositifs SUP/ER/EBC/DPU/PEB, sols SIS/CASIAS, ANC) **lisaient déjà** les couches
en direct — ils sont donc déjà cohérents avec l'outil. Le « risque » chiffré éventuel de la cascade
reste du scoring, hors de cette liste (non touché).

---

## Tableau témoins — parcelle vs lot vs fiche, avant / après

| Parcelle | Mode | Avant (PIEGES-RISQUES-1) | Après (ce mandat) |
|---|---|---|---|
| **BZ1065** | Une parcelle | 3 : ANC, DPU, SUP/PPR | **4** : + « Zone bleue PPR inondation et mouvement de terrain (toute la parcelle) » |
| | Un lot | crible cascade : risque **80/100**, checklist, CATNAT, **ni DPU ni ANC** dans la même logique | **union** : ANC (1/1), DPU (1/1), SUP/PPR (1/1), Risque PPR bleu (1/1) — **= mode parcelle** |
| | Fiche §aléas | cascade : « Zone bleue PPR INONDATION_MOUVEMENT_DE_TERRAIN » | live : **même libellé nettoyé** que l'outil (fiche == outil) |
| **AI0090** | Une parcelle | EBC, ER, 50 pas, SUP/PPR, trait de côte | **15** : + PPR rouge littoral 51 % (rédhibitoire) / inondation 26 %, zones bleues, aléas inondation/mvt/submersion **fort** (%), + prescriptions 15/19 |
| | Un lot | crible cascade (HARD exclue, risque 100) | union (mêmes 15 lignes qu'en parcelle, décomptes) |
| | Fiche §aléas | cascade (PPR rouge, aléas) | live : **7 lignes risque == les 7 de l'outil** ✓ |
| **CH0318** | Une parcelle | 0 (vide) | **1** : « Aléa mouvement de terrain — niveau faible (toute la parcelle) » |
| | Un lot | crible cascade : **risque 60** (Parc National + aléa) | union : 1 contrainte (le même aléa) — plus de score |

Vérifié en base : pour chaque témoin, `outil (une parcelle)` == `outil (un lot d'une parcelle)` ==
`fiche §aléas` (mêmes libellés).

**Captures** (`captures/`) : `avant-{1,2,3}` (main : parcelle sans risque gradué, lot = crible cascade
avec « risque 80/100 » + « Comment ce score est calculé ») vs `apres-{1,2,3}` (parcelle avec « Risque
naturel (PPR / aléa) », lot = **union par contrainte « N parcelles sur M »**), pour BZ1065, AI0090 et le
lot BZ1065+AI0090.

---

## État des tests

- **Frontend** : `tsc -b` + `vite build` verts. **vitest 178/178** (dont `PiegesLot.test.tsx` mis à
  jour : rend l'union « N parcelles sur M », plus aucun vestige de crible cascade).
- **Backend** : `test_servitudes.py` 24 pass/1 skip — filtre prescriptions élargi, `duediligence` forme
  union, **test DB Lot B/C** (PPR bleu gradué + aléa par niveau dans les deux modes ET fiche == outil),
  et **`test_duediligence_ne_lit_plus_la_cascade`** (garde-fou : casse si l'outil relit la cascade).
  `test_fiche1_aleas`, `test_deal_risques`, `test_copilote2_outil`, `test_recette11`, `test_exports2_lot6`,
  `test_coherence_run_fiche` : verts. **Suite complète : 7 échecs PRÉ-EXISTANTS / hors périmètre**,
  aucun ne touche servitudes / modules / aléas / fiche §risques :
  `test_circuit_provenance` et `test_plu_destinations::test_module_unique` (base_reelle, documentés
  pré-existants) · `test_deps_declared` (matplotlib non déclaré) · `test_front_reliquats::m135` ·
  `test_protection` ×2 (quota/rate-limit horaires) · `test_reparations1_lot2`. La toute fin de suite
  (compte/courrier) se bloque sur un verrou DDL `mail_queue` d'isolation de tests (infra pré-existante,
  non liée — `mail_queue` n'est pas touché par ce mandat). Vérif ciblée retenue comme preuve de
  non-régression sur le périmètre.
