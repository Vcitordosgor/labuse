# M11 · SOCLE 0 — Service IA unifié (livré, branche `feat/m11-socle-ia`, PAS de merge)

**Date** : 2026-07-15 · Mandat : `MANDAT SOCLE 0`. Fondé sur `AUDIT-EXISTANT-IA.md` + `CADRE-M11.md` §0.
**Aucune surface visible livrée** (c'est la fondation). Aucune modif scoring/cascade/étage 0/run servi. Aucun merge.

---

## Ce qui a été construit

### Le service central unique — `src/labuse/ai/core.py` (nouveau)
Point d'entrée unique de toute la couche IA. Remplace la duplication (3-4 modules avaient chacun leur clé, client, stub).

| Lot | Contenu | API |
|---|---|---|
| **1 — Client unique** | 1 seule détection de clé, 1 seul client Anthropic, routeur modèle **par tâche** (pas codé en dur chez l'appelant), timeout/retries/température centralisés, repli `degraded` **flaggé** (jamais silencieux), log de coût `ia_log` | `has_key()`, `provider_status()`, `complete(db, *, kind, system, context, model, max_tokens, …) -> IAResult` |
| **2 — Grounding (entrée)** | **Liste blanche OBLIGATOIRE** : `build_context()` refuse tout champ hors liste. Provenance `SOURCE`/`ESTIME`/`ABSENT` étiquetée sur chaque donnée | `Fact(value, provenance)`, `build_context(facts, allowed_fields)` |
| **3 — Validation de SORTIE (hybride 1+3)** | Voir ci-dessous | `validate_output(prose, context, require_sources) -> OutputCheck` |
| **4 — Cache** | Clé **`(idu, run_label, question_normalisée)`** (correction CC : pas `(idu, run)` pour une barre libre). Table `ia_cache`. Invalidation implicite au changement de run | `cache_get`, `cache_put`, `normalize_question` |

### Le contrat de modèle (routeur)
`MODEL_FACTUAL = claude-haiku-4-5` (extraction, factuel, acronymes, filtres) · `MODEL_REASONING = claude-sonnet-4-6`
(raisonnement explicite). Le modèle est un **paramètre de `complete()`**, choisi par la tâche.

### La validation de sortie — HYBRIDE 1 + 3 (le point dur)
Deux couches mécaniques (HORS IA), appliquées avant de renvoyer la prose :
- **Couche 1 — sources forcées** : chaque marqueur `⟨src:champ⟩` doit pointer un champ RÉELLEMENT présent dans le
  contexte autorisé (liste blanche). Marqueur invalide → **réponse rejetée**. Les `src` valides alimentent les
  étiquettes UI « Sourcé · … » (sortie exploitable par la Surface A).
- **Couche 2 — vérif des chiffres** : tout nombre de la réponse doit figurer (à tolérance de format : arrondis k€/M€,
  séparateurs FR) dans les valeurs du contexte. Chiffre inventé (hallucination numérique, le pire cas) → **rejet net**.
- **Comportement en cas de rejet** : `complete(validate=True)` renvoie `rejected=True` + un message honnête
  (« Je ne peux pas répondre de façon sourcée sur ce point ») — **jamais l'affirmation douteuse**. Règle : en cas de doute, on n'affiche pas.
- **Point d'extension documenté (non implémenté)** : Option 2 (2ᵉ appel IA vérificateur) pour les affirmations
  *qualitatives* que 1+3 ne couvrent pas — hook laissé propre, pas codé (décision Vic).

### Fix du 500 + rebranchement (Lot 5)
- **Fix du 500** : `core.complete` sérialise le contexte avec `json.dumps(..., default=str)` → plus de
  `TypeError: Decimal not JSON serializable`. `/ia/synthese` et `/ia/pourquoi` **répondent 200** (preuve §Preuves).
- **Rebranchement** (comportement observable inchangé, prouvé) :
  - `api/ia.py` : `_has_key`/`_note_erreur`/`_note_succes`/`_log` → délégués à `core` ; les **3 instanciations de client**
    (search, entretien, `_real_text`) → `core.complete`. `/ia/status` → `core.last_error()`.
  - `api/assistant.py` : `is_configured` → `core.has_key` ; l'appel `httpx` → `core.complete` (dégradation gracieuse conservée).
  - `ai/nl_segments.py` : clé + client → `core.complete` (usage tokens préservé pour le log segments).

---

## Preuves (§ STOP à Vic)

### 1. Un seul point d'accès clé/client (grep)
```
grep 'anthropic.Anthropic(' ia.py assistant.py nl_segments.py core.py  →  1 seul hit : core.py:317
grep 'os.environ.get("ANTHROPIC_API_KEY")' (même périmètre)             →  0 hit hors core
```
**Hors périmètre, laissés + notés** : `ai/agent.py` (narratif cascade legacy, `ai_adjustment=0`, opt-in stub — hors
score, à retirer/router dans un lot ultérieur) et `ml/juge_vlm.py` (juge VLM **image**, pas la pile IA texte).

### 2. Validation de sortie (test qui rejette un chiffre inventé)
`tests/test_ai_core.py` (13 tests, **verts**) :
- `test_liste_blanche_refuse_champ_hors_liste` ✅
- `test_source_invalide_rejetee` (couche 1) ✅
- **`test_chiffre_invente_rejete`** : `"Capacité 999 m² ⟨src:sdp_m2⟩"` avec contexte sdp_m2=183 → **rejeté** (« chiffre non sourcé 999 ») ✅
- `test_chiffre_source_accepte` / `_format_fr` / `test_arrondi_keur_tolere` ✅
- cache roundtrip + normalisation ✅

### 3. Le 500 corrigé (live, instance dev)
```
POST /ia/synthese/97423000AB1908  →  HTTP 200  (avant : 500 Decimal)  — texte réel produit
POST /ia/pourquoi/97423000AB1908  →  HTTP 200  (avant : 500)
```

### 4. Non-régression des appels existants (avant/après, live)
| Appel | Avant refonte | Après (via core) |
|---|---|---|
| `/ia/search` « brûlantes à Saint-Pierre » | `{tiers:[brulante], commune:Saint-Pierre}` | **idem** |
| `/parcels/{idu}/explain` (assistant) | prose groundée sonnet | **idem** (available:true, sonnet) |
| Tests `test_assistant.py` (16) | verts | **verts** (ENV_KEY ré-exporté depuis core) |

### 5. Zéro touche scoring
`git status` : seuls `ai/core.py` (neuf), `ai/nl_segments.py`, `api/ia.py`, `api/assistant.py`, `tests/test_ai_core.py`.
**Aucun** fichier scoring/cascade/étage 0/`score_v_constants`/`models.py`/mvt touché.

### 6. Aucun appel IA supplémentaire introduit
La validation (couches 1+2) est du **parsing/regex pur** (hors IA) ; le cache est en base. `core.complete` fait
**un** appel modèle par tâche, comme avant. Le socle n'ajoute aucun coût IA.

---

## Contrat d'interface (comment une Surface appellera le socle)
```python
from labuse.ai import core

ctx = core.build_context({
    "zone_plu":  core.Fact("1AUb", "SOURCE"),
    "sdp_resid": core.Fact(183, "ESTIME"),
    "assainissement": core.Fact(None, "ABSENT"),
}, allowed_fields={"zone_plu", "sdp_resid", "assainissement"})   # liste blanche = refus hors-liste

# cache d'abord
hit = core.cache_get(db, idu, run_label, question)
if hit: return hit

res = core.complete(db, kind="fiche_qa", model=core.MODEL_FACTUAL, system=PROMPT,
                    context=ctx, validate=True, require_sources=True)
if res.rejected:  # sortie non sourcée → on n'affiche pas l'affirmation douteuse
    ...
core.cache_put(db, idu, run_label, question, {"texte": res.text, "sources": res.sources})
```

## Schéma des tables (créées à la volée, idempotent)
- `ia_cache(idu, run_label, question_hash, kind, question, response jsonb, computed_at)` — PK `(idu, run_label, question_hash)`.
- `ia_log` — inchangée (coût), désormais alimentée par `core._log_cost`.

---

## Reste ouvert (pour les mandats suivants, pas bloquant)
- `ai/agent.py` (legacy) et `ml/juge_vlm.py` (VLM) ont encore leur propre client — à router/retirer dans un lot dédié (hors périmètre socle).
- Option 2 (vérificateur IA qualitatif) : hook prêt, non implémenté.
- Le cache n'est pas encore consommé par un endpoint (les surfaces l'utiliseront) — infra posée, pas de remplissage.

**Commit sur `feat/m11-socle-ia`, PAS de merge.** Vic valide et merge.
