# Bascule du run servi `q_v6_m8` → `q_v7_defisc` — procédure & rollback

Clôture A-1 (cycle 1). Bascule PROTOCOLÉE de la composante V « fenêtre de sortie de défiscalisation ».

## Convention de label

`q_v{N}_{tag}` — **v7** = 7ᵉ version servie ; tag **`defisc`** = composante V ajoutée. Le **modèle P
(M3.6 / m8, sha256 gelé) est INCHANGÉ** : V ne module que le **rang** (`p_raw`, +0,01 plafonné) de **131**
parcelles mono non-écartées → **0 bascule de tier** (golden 116/116, gate boussole 0/64).

## Ce que la bascule a fait (appliqué)

1. **Run matérialisé** `q_v7_defisc` = `q_v6_m8` copié VERBATIM (triplet gelé) + bump V, via
   `scripts/a1_bascule_v7.py`, sur les tables clés-run : `parcel_p_score_v2` (+V sur `p_raw`),
   `dryrun_parcel_evaluations`, `dryrun_cascade_results` (14,6 M), `p_score_v2_runs` (`computed_at`
   postérieur → q_v7_defisc devient le **champion de référence**). `ia_cache` NON copié (se régénère).
2. **Label servi CONFIGURABLE** (fin de la dette hard-code) :
   - backend `Q_A_RUN_LABEL = os.environ.get("LABUSE_SERVED_RUN", "q_v7_defisc")`
     (`src/labuse/scoring/score_v_constants.py`) ;
   - front `SOURCE = import.meta.env.VITE_RUN_LABEL ?? 'q_v7_defisc'` (`frontend/src/lib/api.ts`,
     type `frontend/src/vite-env.d.ts`).
3. **Front reconstruit** (`npm run build`) → bundle sur q_v7_defisc.
4. **Tuiles reconstruites** (`labuse build-mvt`) → `mvt_meta.run_label = q_v7_defisc`.
5. **Golden re-gelé** sur le nouveau label (34 champs `run_id`/`run_cascade`/`run_v2_servi`) — **116/116**,
   les 84 ancres inchangées (neutralité structurelle). **Baseline arène** régénérée : `BASELINE_q_v7_defisc.md`.

Les trois surfaces alignées (constante + bundle + tuiles) — `test_run_serving_coherence` vert.

## Hystérésis

**`q_v6_m8` est INTÉGRALEMENT conservé** (toutes ses lignes dans toutes les tables clés-run). Aucune
suppression. Rollback ⇒ **aucune re-matérialisation** nécessaire, juste re-pointer les surfaces.

## Rollback (retour à `q_v6_m8`)

1. **Backend** : `export LABUSE_SERVED_RUN=q_v6_m8` puis redémarrer l'API. `Q_A_RUN_LABEL` suit l'env,
   tout le backend re-sert q_v6_m8.
2. **Front** : `VITE_RUN_LABEL=q_v6_m8 npm run build` (dans `frontend/`) puis redéployer `dist/`.
3. **Tuiles** : `labuse build-mvt` (avec `LABUSE_SERVED_RUN=q_v6_m8`) — ou `labuse build-mvt --label q_v6_m8`
   — réécrit `mvt_meta.run_label = q_v6_m8`.
4. **Vérifier** : `pytest tests/test_run_serving_coherence.py` (les trois surfaces re-alignées sur q_v6_m8 ;
   `Q_A_RUN_LABEL` importe la valeur env). Golden : `LABUSE_GOLDEN_RUN_LABEL=q_v6_m8` (inchangé côté data).

**Re-bascule avant** : `unset LABUSE_SERVED_RUN` (défaut q_v7_defisc) + rebuild front (sans `VITE_RUN_LABEL`)
+ `labuse build-mvt`.

## Gel

`q_v7_defisc` est **gelé** : ne pas le recomputer (c'est la référence servie et le champion des prochains
challengers). Toute évolution = un nouveau label versionné (`q_v8_…`) et une nouvelle bascule protocolée.

## Notes

- Le challenger d'audit `q_v6_m8_Vdefisc` (garde-fou arène, volet 3) est distinct de `q_v7_defisc` et peut
  être purgé ultérieurement (il a servi de preuve boussole/ECE/churn).
- La table `defisc_fenetres` (badge) n'est PAS clé-run (globale) : inchangée par un rollback.
