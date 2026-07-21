# AUDIT DE CONVERGENCE DES DEUX COUCHES IA — pré-vol M7 · P7 (LECTURE SEULE)

Document d'audit + plan de migration par étapes. **RIEN n'est migré ici** (post-M7). État au 21/07/2026.

## 1 · Les deux couches

| | **LEGACY** (`ai/agent.py` + `ai/prompt.py`) | **SOCLE** (`ai/core.py`, M11) |
|---|---|---|
| Entrée | `provider.analyze(payload)` (monolithique) | `complete(db, kind=…, system=…, context=…)` (composable) |
| Usage | **UNE seule chaîne** : le pipeline cascade (`cascade/pipeline.py:_apply_ai`, l.140-152) → `parcel_evaluations.ai_payload` (narratif post-cascade ; `opportunity_adjustment` **volontairement à 0** — « IA = NARRATIF ONLY ») | **11 usages** : search, ia-aggregate, entretien, synthese, pourquoi, fiche_ask, explain-faisa, segments-search, traducteur-plu, synthese-banquier, explain (assistant) |
| Grounding | Implicite (structure du payload) | Explicite : `Fact(value, provenance)` + `build_context` whitelist |
| Validation | Schéma JSON (AI_OUTPUT_SCHEMA, 12 champs) | Hybride : sources `⟨src:…⟩` + `strict_numbers` + rejet honnête |
| Cache | Aucun | `ia_cache` versionné **CONTEXT_VERSION=4** |
| Historique conv. | Aucun | `history[]` |
| Modèles | `config.ai_provider/ai_model` (défaut stub / sonnet) | Codés en dur : haiku (factuel) / sonnet (raisonnement), routage par usage |
| Coût | `ia_log` (partagé) | `ia_log` (partagé, automatique dans `complete`) |

**Appelants du LEGACY** (les seuls) : `cli.py evaluate --ai`, `api/app.py POST /parcels` (évaluation),
`ingestion/run_all.py` — tous via `evaluate_parcels(ai_provider=get_provider())`. En pratique le
provider par défaut est **stub** (déterministe) ; l'IA legacy « réelle » ne tourne que sur `--ai anthropic`
explicite. `ai/__init__.py` ré-exporte encore `StubProvider/analyze/get_provider` (l.6-8).

## 2 · Partagé

`ia_log` (coûts, deux couches) · `ANTHROPIC_API_KEY` (`core.has_key` vs provider legacy) ·
`config.ai_provider/ai_model` = **legacy uniquement** (le socle les ignore — source de confusion documentée).
`nl_semantics` = garde déterministe, aucune couche IA. Tables socle-only : `ia_cache`, `ia_ask_quota`, `nl_query_log`.

## 3 · Divergences comportementales à connaître avant migration

1. **Batch vs requête** : legacy traite des lots de parcelles à l'évaluation (pipeline) ; le socle est
   optimisé requête/réponse avec cache. Une migration doit soit accepter N appels `complete` (coût), soit
   ajouter un mode batch au socle.
2. **Impact scoring** : l'ajustement legacy est neutralisé (0) — le narratif est le SEUL produit. Le socle
   n'a par conception AUCUNE intégration scoring : la migration est donc sans risque de dérive de score.
3. **Config provider** : `LABUSE_AI_PROVIDER/AI_MODEL` ne pilotent QUE le legacy ; l'env.example le dit.
   Après migration, ces deux settings meurent (nettoyage config).
4. **Validation** : le schéma 12-champs legacy disparaîtrait au profit du grounding socle (Fact +
   validation) — le payload `ai_payload` stocké devrait garder un format compatible fiche (`fiche["ai"]`).

## 4 · Plan de migration par étapes (post-M7, chaque étape ≤ une session)

| Étape | Contenu | Risque |
|---|---|---|
| **C1** | Écrire `kind="narratif-evaluation"` dans le socle : un `complete()` groundé sur les faits de l'`EvaluationOutcome` (verdicts cascade, scores, complétude — mêmes champs que `payload_from_outcome`), sortie = même shape `ai_payload`. Test A/B stub legacy vs socle sur 20 parcelles (diff de payload). | faible (additive) |
| **C2** | Brancher `_apply_ai` sur le socle DERRIÈRE un flag (`LABUSE_AI_PROVIDER=socle`), legacy par défaut. Golden 116 + suite complète (le payload est hors triplets gelés — vérifier que `fiche["ai"]` reste servie). | moyen (chemin pipeline) |
| **C3** | Basculer le défaut sur le socle ; legacy en repli un cycle ; puis retirer `agent.py`/`prompt.py`/`get_provider` + settings `ai_provider/ai_model` + ré-exports `ai/__init__`. | faible après C2 |
| **C4** (option) | Unifier le routage modèle : sortir haiku/sonnet du dur de `core.py` vers la config (les 11 kinds gardent leurs défauts) — prépare un futur multi-provider. | faible |

**Pré-requis d'aucune étape : M7.** Rien dans ce plan ne touche scoring/runs servis/golden ; le narratif
est le seul livrable des deux couches. Estimation totale : 2-3 sessions.

## 5 · Détail des 11 kinds socle (référence)

`search` (haiku, NL→filtres) · `ia-aggregate` (haiku, strict_numbers, COUNT/rang SQL) · `entretien`
(haiku, cadrage projet, history) · `synthese` / `pourquoi` (sonnet, prose fiche) · `fiche_ask` (routage
haiku/sonnet par mots-clés, validate+sources, cache (idu,run,question), quota 20/j) · `explain-faisa`
(sonnet, validate+sources, cache) · `segments-search` (haiku, filtres registre) · `traducteur-plu` (sonnet,
strict_numbers, O4) · `synthese-banquier` (sonnet, strict_numbers, O1) · `explain` (sonnet, assistant 3.A,
repli rules_summary).

⚠ Rappel opérationnel : tout changement de `_ask_context`/`_SYSTEM` ⇒ **bump CONTEXT_VERSION** (v4 actuel)
— sinon bugfix masqué par le cache (incident zonage du 15/07).
