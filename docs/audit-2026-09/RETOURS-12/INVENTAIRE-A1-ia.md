# INVENTAIRE A1 — surfaces IA de l'app (RETOURS-12)

> Livrable du mandat, travail A1. Inventaire exhaustif AVANT rebranchement. Point d'entrée unique,
> source du modèle, source de la clé, version du client, dégradé, verrou anti-invention.

## 1. Surfaces IA (toutes passent par `core.complete()`)

| Fichier:ligne | Surface (kind) | Modèle | Source du modèle | Source clé |
|---|---|---|---|---|
| copilote/interpreteur.py:69 | copilote_mission (v1) | sonnet-4-6 | `ai_models.model_for` | `ANTHROPIC_API_KEY` |
| copilote_v2/router.py:259,267 | copilote-route (+retry) | haiku-4-5 | `ai_models.model_for` | idem |
| copilote_v2/answering.py:232 | copilote-select | sonnet-4-6 | `ai_models.model_for` | idem |
| copilote_v2/answering.py:364 | copilote-formule | sonnet-4-6 | idem | idem |
| copilote_v2/answering.py:736 | copilote-general | sonnet-4-6 | idem | idem |
| copilote_v2/answering.py:1128 | copilote-prepare | sonnet-4-6 | idem | idem |
| copilote_v2/heros.py:61 | copilote-heros | sonnet-4-6 | idem | idem |
| pige/extraction.py:98 | vision_pige (image) | haiku-4-5 (vision) | idem | idem |
| api/ia.py:364,676 | search / (par kind) | haiku-4-5 | idem | idem |
| api/nl_aggregate.py:133 | ia-aggregate | haiku-4-5 | idem | idem |
| api/traducteur.py:98 | traducteur-plu | sonnet-4-6 | idem | idem |
| api/assistant.py:343 | explain (synthèse fiche) | sonnet-4-6 | `model_for` **ou override env** (voir A1) | idem |
| api/banquier.py:173 | synthese-banquier | sonnet-4-6 | idem | idem |
| api/fiche_ask.py:298 | fiche_ask (AskBar) | haiku/sonnet routé | idem | idem |
| api/modules.py:1596 | explain-faisa | sonnet-4-6 | idem | idem |
| promo/collecte.py:129 | promo_collecte (programmes) | haiku-4-5 | idem | idem |

## 2. Point d'entrée UNIQUE
`src/labuse/ai/core.py::complete()` (ligne 425). Aucune instanciation `anthropic.Anthropic()` ailleurs.
Le modèle circule par `core.model_for(kind)` (→ `ai_models`), la clé par `has_key()` → `ANTHROPIC_API_KEY`
(source unique). `temperature=0.0` (stable), envoyée telle quelle (valide en 0.116.0).

## 3. Version client — DÉJÀ correcte
`anthropic==0.116.0` épinglé EXACT (pyproject.toml:60), installé en conda ET .venv. Le mandat visait le
piège « 1.1.0 refuse temperature → dégradé muet » : c'était le VPS (H1 27/08), corrigé par le pin +
`tests/test_anthropic_pin.py` + vérif post-install `deploy_vps.sh`. Localement : `/ia/status` = provider
anthropic, raison null (l'IA fonctionne).

## 4. Source du modèle — DÉJÀ fail-closed
`src/labuse/ai_models.py` : `MODEL_FACTUAL`/`MODEL_REASONING`/`MODEL_VISION` + registre `SURFACES` par
usage. `RETIRED_MODELS` + `check_model()` refusent BRUYAMMENT un modèle retiré (au boot via le validateur
config ET à chaque appel via `model_for`). Visible au dashboard admin (`surfaces_table`).

## 5. Dégradé — DÉJÀ journalisé, message client rendu HONNÊTE (A1)
`core.complete` : échec → `log.error(model, kind, exc)` + `_note_error` (clé invalide / permissions /
modèle retiré nommé / erreur API). `provider_status()` (→ /ia/status, admin) sert la raison structurelle.
**Correction A1** : le message CLIENT du Copilote (`copilote_v2/answering.py`) disait « Réessayez dans un
instant » même pour une cause STRUCTURELLE → remplacé par `erreur_infra()` : structurel → nomme la cause,
dit « l'équipe est alertée », n'invite plus à réessayer ; passager → « réessayez » reste.

## 6. Verrou anti-invention — INTACT (on rebranche, on n'assouplit pas)
Deux couches dans `core.py` : (a) grounding par LISTE BLANCHE (`build_context`, tout champ hors liste
refusé) ; (b) `validate_output` — marqueurs de source obligatoires (`⟨src:champ⟩` pointant un champ réel)
+ chiffres vérifiés contre le contexte (`strict_numbers` pour les comptes). Un chiffre/une source inventé
→ rejet, jamais servi. Inchangé par A1.

## 7. Corrections A1 apportées
- Message client honnête (`erreur_infra()`) branché sur les 4 replis du Copilote v2.
- Override d'env `LABUSE_ASSISTANT_MODEL` (assistant.py) passé par `check_model` : il contournait la
  garde (un modèle retiré y serait passé en dégradé muet) — désormais refusé bruyamment (A1.3, plus de
  modèle env-seul hors source unique).
- Le reste de l'infrastructure (point d'entrée unique, ai_models fail-closed, pin 0.116.0, dégradé
  journalisé, anti-invention) était DÉJÀ conforme (SECTEUR-1 S6 + HYGIÈNE H1) — vérifié, documenté.
- **Reste côté exploitation (hors code)** : la clé Anthropic LIVE du VPS (VP-003, notée invalide) — à
  poser par Vic ; le code, lui, la lit d'une source unique et dit honnêtement quand elle est refusée.
