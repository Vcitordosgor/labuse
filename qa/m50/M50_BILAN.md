# M50 — BILAN · Cartographie retenue/écartée + CLI isolées stampées

**Branche** `m50-cartographie-motifs` (pas de merge). Golden **117/117** · **0 tier · 0 rang**
(Lot A trace, ne réordonne pas ; Lot B n'écrit rien sur `parcel_p_score_v2`) · re-mesures
M34/M35 & SHA256 M37 intacts.

---

## LOT A — Reconstructibilité des motifs : fermée

### 1. Re-mesure (AUDIT5 rejoué sur l'état courant, 431 663 — pas 50 000)
**Motifs 100.000 % reconstructibles.** Script versionné `remesure_reconstructibilite.py`,
digest `reconstructibilite.csv.gz`.

| famille | reconstructible | source |
|---|---|---|
| écartée (354 355) | 100 % | cascade HARD_EXCLUDE (étage 0) OU q_score (matrice) |
| déclassées (45 210, 6 tiers) | 100 % | tables motif dédiées (filtre_bati / constructibilite / au_statut / bati_revele) |
| brûlante/chaude/à-creuser/réserve (34 098) | 100 % | rang+contrib_d+cutoffs persistés OU flag copro |

**Delta vs AUDIT5** expliqué : les 133 « manquants » initiaux de la re-mesure large =
**copropriétés** (rang NULL → tier par défaut) ; reconstructibles via le flag copro
(`copro_rnic/dvf`) — c'est le **« trou n°2 » d'AUDIT5, clos**. 0 non-copro parmi eux.

### 2. Paramètres de coupure persistés (artefact du run, `p_score_v2_runs.params`)
Ajout au JSON épinglé (pipeline, going forward + backfill du run servi q_v8_calibre) :
`reserve_seuil_c_sdp` + `reserve_p_median` (formules exactes de `assign_tiers` — **« pourquoi
réserve foncière et pas à creuser » a désormais une réponse datée**), `event_bypass_mois`,
`brulante_event_mois`, `n_entree_cible`, `brulante_effectif_min/max`. Recalcul de TRACE, 0 tier/rang.
*(Déjà présents avant M50 : n_entree/n_sortie/c_surface/brulante_seuil_d/top_decile_d/seed_ties.)*

### 3. Ordre intra-palier tracé + persisté (`params.departage`)
Constat **sur pièces** : l'ordre est **DÉJÀ explicite depuis M28** (pipeline.py:271) —
`rang: p desc → contrib_D desc → SDP résiduelle desc → surface desc → IDU alphabétique → seed`.
Le **« tirage seedé arbitraire » d'AUDIT5 (trou n°3) est PÉRIMÉ** : le seed n'est que le fallback
ULTIME (inatteignable, l'IDU étant unique). Le rang servi est **reproductible**. Rien réordonné —
la clé est désormais persistée en toutes lettres dans l'artefact du run.

### 4. Motif servi == motif reconstruit
Par construction : `verdict_servi.motif` (servi en fiche/IA, M49) LIT les mêmes tables motif que
la re-mesure prouve à 100 %. Le « Pourquoi pas ? » et la re-mesure coïncident (famille grille M48).

## LOT B — Stamper + câbler les CLI isolées (dette M47)

**Constaté sur pièces** (pas les notes) : `score_e` bâtie **08-06 sur q_v8_calibre** (reads
Q_A_RUN_LABEL) ; `division_or_candidates` bâtie **2026-07-28 = q_v7_defisc** (fenêtre pré-v8) →
**PÉRIMÉE**.

1. **Colonne `run_label`** ajoutée aux deux (réversible : `DROP COLUMN`) + **backfill CONSTATÉ**
   (score_e = q_v8_calibre 77 308 ; division_or = q_v7_defisc 35). Builders **stampent** le run
   désormais (score_e `_INSERT`, division_or 2× INSERT `:served AS run_label`, partiel bindé).
2. **Câblage** : `score_e` rejoint le geste unique `rebuild_mvt_servies` (**+11,4 s**, run_label
   stampé, table servie intacte après rollback) — plus la seule table full-parc montée par
   `labuse score-e`.
3. **Garde** `check_coherence_tables_run_scopees` **dans le point unique** (CLI `build-mvt` ET
   bascule la voient) : renouvellement/score_e/parcel_flags run≠servi → alerte ; `division_or` =
   **workflow de revue par commune** (toléré mais **VISIBLE**, jamais silencieux). Live : renouv/
   score_e/flags **OK**, division_or **PÉRIMÉE** (q_v7_defisc) correctement flaggée. Test 6 cas.

### 4. Assertion : plus AUCUNE table servie run-dépendante silencieusement périable

| table (run_label) | mécanisme | statut live |
|---|---|---|
| `parcel_renouvellement` | **geste** rebuild_mvt_servies (M47) | OK |
| `score_e` | **geste** rebuild_mvt_servies (M50) | OK |
| `parcel_flags` | **geste** rebuild_mvt_servies (M45) | OK |
| `division_or_candidates` | **garde** (workflow revue par commune) | PÉRIMÉE, VISIBLE |
| `dryrun_cascade_results` / `dryrun_parcel_evaluations` / `entonnoir_motifs` | **sortie du run** (montent avec le scoring) | OK |
| `ia_cache` | **cache** déclaré (miss→recalcul) | — |
| `score_snapshots` | **archive/journal** (lignee_tete) | — |

Hors classe (vérifié) : `defisc_fenetres` = signal **run-AGNOSTIQUE** (ref_year, app.py:891
« aucun lien avec le run servi »). **Conclusion : toute table servie run-dépendante est soit dans
le geste, soit couverte par une garde bruyante — aucune ne peut plus périmer en silence.**

## VÉRIFICATION
Golden **117/117** · **0 tier · 0 rang** · re-mesures M34/M35 & SHA256 M37 intacts · tests
(garde M50 6/6 + péremption/coherence/renouv/mvt/division 83 verts) · temps geste +11,4 s (score_e).

## Reste (à ta main)
- `division_or_candidates` est PÉRIMÉE (q_v7_defisc) : la garde le crie ; un **`labuse division-or`
  par commune** (ta main, workflow revue) la rebâtira sur q_v8_calibre quand tu voudras.
- Prochain `build-mvt`/bascule : score_e sera rebâti + stampé dans le geste (déjà à jour aujourd'hui).

## Annexes (.csv.gz)
- `reconstructibilite.csv.gz` — re-mesure par tier (100 %).
- `remesure_reconstructibilite.py` — script rejouable.
