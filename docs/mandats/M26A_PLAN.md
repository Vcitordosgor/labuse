# M26-A — PLAN D'IMPLÉMENTATION (Point d'arrêt A)

**Branche** : `feat/m26a-copilote-socle` (base `origin/main` 18ea733). Clone dédié `labuse-m26`.
**État vérifié avant plan** : venv Python 3.12 monté (pyproj wheel indisponible en py3.13/macOS 13),
1151 tests collectés, PostGIS up, tiers du run servi `q_v7_defisc` vérifiés en base :
**120 / 1031 / 3587 / 72980 / 353945** — c'est l'invariant « au bit près ».

## Fichiers créés (aucun moteur existant modifié)

```
src/labuse/copilote/__init__.py
src/labuse/copilote/tables.py        ensure_tables() : agent_runs, agent_events, agent_run_parcels
                                     (pattern maison CREATE TABLE IF NOT EXISTS, appelé au _lifespan sous advisory lock)
src/labuse/copilote/events.py        taxonomie fermée (Enum), emit(db, run_id, kind, payload) append-only,
                                     reduce_run(events) -> status (pur, testé)
src/labuse/copilote/boussole.py      filtre payload : réutilise proprietaire_type.classify_owner_type —
                                     toute clé nominative bloquée sauf personne morale/publique (SIREN public)
src/labuse/copilote/prompts.py       prompt interpréteur versionné (PROMPT_VERSION), Factor 2
src/labuse/copilote/interpreteur.py  brief_raw -> brief_json (schéma strict) OU clarification_requested ;
                                     appel via ai/core.complete() (MODEL_REASONING=sonnet, socle M7 : ia_log, retry, stub) ;
                                     conversion logements->SDP en CODE (SDP_PAR_LOGEMENT_M2 = 70) ;
                                     verifier_adresse : regex IDU/BAN d'abord, LLM seulement en secours
src/labuse/copilote/plans.py         PLAN_INSTRUIRE / PLAN_SHORTLIST / PLAN_VERIFIER codés en dur,
                                     chaque étape déclarée bloquante ou non (module labuse.copilote.plans —
                                     pas de collision avec labuse/plans.py, plans commerciaux)
src/labuse/copilote/moteurs.py       wrappers fins (appel + chrono + étiquette + compteurs avant->après) :
                                       criblage      -> lecture seule run servi p_score_v2 (épinglé Q_A_RUN_LABEL)
                                                        + filtres commune/zones/surface/PPR (couches précalculées)
                                       faisabilite   -> faisabilite.db.parcel_faisabilite() (11 étapes, bloquant)
                                       risques       -> cascade_results précalculés (PPR/ABF), Factor 13 : pas de recalcul
                                       marche_dvf    -> faisabilite.bilan.sector_price() + compute_bilan() (non-bloquant)
                                       mutation      -> mutation.compute_mutation_score() (voir Q1)
                                       assemblage    -> logique de api/moteurs.py (fonction interne, pas l'endpoint)
                                       scoreur_unitaire -> api/scoreur.py (verifier_adresse)
src/labuse/copilote/executeur.py     déroule le plan figé dans run_started ; retry ×1 sur transitoire ;
                                     step_failed compact (≤200 car, jamais de stacktrace) ; budgets :
                                     COPILOTE_TIMEOUT_RUN_S=120, COPILOTE_MAX_APPELS_MOTEURS=12 ;
                                     zéro retenue = run done (n_retenues=0), jamais d'assouplissement
src/labuse/api/copilote.py           router /api/copilote : POST runs (quota M23 kind='agent' AVANT run_started),
                                     GET runs/{id}/events (SSE, after_seq, rejeu sans doublon), POST answer,
                                     POST cancel, GET runs, GET runs/{id} — tout dérivé de l'event log
tests/test_copilote_*.py             ~40 tests (reduce_run, interpréteur 15+ phrases dont injection,
                                     plans snapshot, retry/bloquant/non-bloquant, zéro retenue,
                                     SSE after_seq, boussole rouge si nom de personne physique)
docs/mandats/M26A_RAPPORT.md         rapport de fin de mandat
```

## Points d'accroche dans l'existant (modifications minimales, additives)

- `api/app.py` : `include_router(copilote)` + `copilote.tables.ensure_tables()` dans `_lifespan` (~3 lignes).
- `config.py` : `copilote_quota_jour: int = 10` (+ 2 constantes budget). Rien d'autre.
- `tests/conftest.py` : ajout des tables copilote dans la fixture `engine` (1 ligne).
- Quota : `api/protection.py` existant — `compteur_incr_et_lire(jour, sujet, kind='agent')`, 429 même style,
  `LABUSE_DEV_MODE=1` le désactive comme aujourd'hui.
- Propriété du run : scope `compte_id` (pattern SEC-IDOR de `tenant.py`, `IS NOT DISTINCT FROM`) — voir Q2.
- `engine_versions` : `config.rules_version()` + sha artefact P (FREEZE-scoring2026.json) + run servi + git sha.
- SSE : inexistant dans l'app → `StreamingResponse` + polling `agent_events` (~400 ms), reconnexion par `after_seq`.
  Pas de LISTEN/NOTIFY en M26-A (simplicité, même résultat).
- Exécution : thread in-process lancé au POST (budget 120 s) — pas de worker séparé en M26-A.

## Questions ouvertes (le GO peut trancher, défauts proposés)

1. **Mutation V1 est gravé « NON SERVI »** (pondérations placeholder, jamais calées). Le mandat le met dans
   PLAN_INSTRUIRE/SHORTLIST. Défaut proposé : l'appeler, étiqueter `estimé` + limites verbatim, non-bloquant —
   ou l'omettre si le statut NON SERVI doit primer.
2. Le mandat écrit `user_id fk users` ; le système réel est `comptes`/`utilisateurs`. Défaut proposé :
   `compte_id` (+ `utilisateur_id` nullable), comme les autres tables client.
3. Pas de « moteur de recherche » isolé dans le code : le criblage sera une **lecture seule** du run servi
   épinglé + couches précalculées (aucune logique métier nouvelle). Confirmer que c'est bien l'attendu.
4. Golden 116 (`qa/golden_check.py`) exige l'API branchée sur la **base applicative** — il sera passé au
   point B contre la base de ce poste (run servi `q_v7_defisc`), avant/après.

**STOP — attente du GO de Vic avant toute ligne de code.**
