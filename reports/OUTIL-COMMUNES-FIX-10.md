# OUTIL-COMMUNES-FIX-10 — réponse au recontrôle 03-COMMUNES-ASTRA-7

Branche `fix/outil-communes-1` (origin/main fusionné d'abord, merge `a160fd94b`). Base locale `labuse`
lue seulement. Pas de fusion dans `main`. Périmètre = la liste « C'est faux » (3 points) + l'effectif
vide de Comparer.

## LOT 1 — phrase de marché stockée → re-dérivée à la lecture (seuil 8)
Le bloc Marché servait la phrase STOCKÉE dans le classement (cascade `dvf`, `phase2.py`, plancher de 3) :
sur 97412000AY0082 (Saint-Joseph) « Prix médian terrain 50 €/m² — 6 ventes … Contexte de marché
favorable » alors que la section ne compte plus qu'**1 vente**.
- **Affichage** : `app._q_v2_fiche` RE-DÉRIVE la ligne `dvf` via la fonction UNIQUE
  `dvf_secteur.prix_section` (seuil 8) — `_dvf_terrain_detail_servi`. Sous le seuil : « échantillon
  insuffisant (N vente(s)) », AUCUN prix, AUCUN qualificatif. AY0082 → « échantillon insuffisant
  (1 vente) » (preuve `scripts/communes_fix10_marche.py`).
- **Calcul futur** : `cascade/layers/phase2.py` (DvfLayer) passe par `seuil_section()` (8), plus de
  plancher 3 ni de bande « fragile » 3-7 → sous 8, ni prix ni « favorable » ni bonus.
- **INTERDIT respecté** : le run q_v20 stocké n'est PAS modifié (correction à l'affichage + au calcul
  des prochains runs).
- **Le signal entre-t-il au score ?** OUI — bonus `contexte_dvf_favorable` = **8 points** (× magnitude)
  dans le score d'opportunité (`config/opportunity_weights.yaml`). **64 603** parcelles portent
  aujourd'hui un « contexte de marché favorable » STOCKÉ fondé sur une section à **moins de 8 ventes**
  (sur 257 604 « favorable » au total). Le classement étant gelé, ces points restent au score q_v20 ;
  le correctif de `phase2.py` les supprime aux PROCHAINS runs.
- **Autres phrases/chiffres servis DEPUIS LE CLASSEMENT qui peuvent contredire une valeur recalculée**
  (demandé) : (1) `dvf` terrain — CORRIGÉ ci-dessus ; (2) `vefa_neuf` (`fiche_couches4.py`) — médiane
  + nombre de ventes VEFA NEUF de la commune, stockés au build (peuvent dériver vs le live) ;
  (3) `zone_activite` (`fiche_couches2.py`) — taux de recouvrement stocké (stable sauf géométrie) ;
  (4) `amenites`/`sitadel`/`potentiel_foncier_region` — distances / comptes de permis / recouvrement
  (hors prix, `amenites`+`sitadel` déjà filtrés du bloc Marché). Seul `dvf` portait un PRIX + un
  qualificatif de marché sous le seuil → c'est le seul corrigé ici ; les autres sont SIGNALÉS.

## LOT 2 — dates au mois PARTOUT
La carte Urbanisme (`ContextePanel.tsx:691`) convertissait « 2025-05 » en « 01/05/2025 » (jour
fabriqué) via `fmtDateNum`. Correction au POINT UNIQUE : `fmtDateNum` (`format.ts`) rend désormais
« 2025-05 » → « mai 2025 » et « 2025 » → « 2025 » ; tout l'écran (bandeau, carte, « dernière pièce »)
en bénéficie. La ligne « dernière pièce » passe de « le {date} » à « : {date} » (« le mai » serait
fautif). Seule Les Trois-Bassins a une date au mois (etat_source_date `2025-05`) ; les 23 autres fiches
ont des dates au jour (inchangées). Préposition correcte conservée au bandeau (`plu.ts` : « en mai 2025 »).

## LOT 3 — La Plaine-des-Palmistes : chronologie complète
Nouveau champ `chronologie` (registre `veille_plu.yaml`, servi par `plu_statut`, rendu `ContextePanel`),
chaque pièce avec sa DATE, son LIEN et sa NATURE — **actes de procédure** vs **mentions d'avancement** :
| date | nature | pièce | lien (HTTP 200, ouvert avant citation) |
|---|---|---|---|
| 24/09/2015 | acte | Prescription de la révision générale (DCM40-240915) | ville-plainedespalmistes.fr/PLU/juillet2018/deliberations/DCM40-240915…pdf |
| 05/02/2020 | acte | Avis MRAe n° 2020AREU2 sur la révision générale (18 p.) | mrae…/IMG/pdf/avi_2020areu2__rev_generale_plu_plaine_des_palmistes.pdf |
| 13/07/2022 | acte | Retrait de la délibération d'arrêt du projet (avis MRAe 2022ACREU2) | mrae…/IMG/pdf/2022acreu2_modif_plu_la_plaine_des_palmistes.pdf |
| 27/11/2025 | avancement | Dossier DCM32-271125 (dispositifs contractuels) — ni acte ni approbation | ville-plainedespalmistes.fr/dcm/2025/27112025/Aff32-271125…PDF |

« aucune pièce postérieure retrouvée » RETIRÉ. `etat_source_date` = **2022-07-13** (dernier acte).
Chaque lien OUVERT + jeton vérifié : `scripts/communes_fix10_plaine_liens.py` (4/4).

## LOT 4 — Comparer sert l'effectif sous le seuil
`app._compare_row` filtrait les sections sur `mediane_prix_m2` (déjà None sous le seuil) → la section
était écartée → effectif vide. Corrigé : sélection par TYPE + ventes. Pour 97415000CD0003 :
`terrain_zone_eur_m2=None` (prix masqué) **·** `prix_terrain_n=1` (effectif servi, comme fiche/Carnet).
Preuve `scripts/communes_fix10_comparer.py`.

## Tests
LOT 0 filet (rouge avant correction, commit séparé) : `test_dvf_terrain.py` + `test_phase2_layers.py`
(seuil 8), `test_communes_fix6.py` (chronologie), `format.test.ts` (dates mois/année). Suite non-db :
**5053 passed** ; 5 flakes `test_retours11f2/f3` dus aux runs pytest CONCURRENTS d'autres worktrees
(verts en isolation : 23 passed). Front tsc + vitest verts. Cohérence : lancée par le hook au push.
