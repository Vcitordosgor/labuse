# M113 · Phase 0 — la latence du Copilote, mesurée avant de construire

Mesuré le 17/08/2026, base réelle + API réelle. Répond aux 4 points de la Phase 0. **STOP** : ces
mesures + la proposition de réaffectation attendent l'arbitrage de Vic avant toute construction.

## 0.1 — Inventaire des modèles (fichier:ligne)

`ai/core.py:34-35` — `MODEL_FACTUAL = haiku-4.5` · `MODEL_REASONING = sonnet-4.6`.
`core.complete()` défaut = **FACTUAL** (core.py:368). Mais **chaque étage du Copilote force REASONING** :

| étage | fichier:ligne | kind | modèle servi |
|---|---|---|---|
| routeur (classify) | `router.py:226,234` | copilote-route(-retry) | **sonnet** |
| sélecteur d'outil | `answering.py:203` | copilote-select | **sonnet** |
| formulation | `answering.py:267` | copilote-formule | **sonnet** |
| recherche web | `outils.py:378` (client direct, hors core.complete) | copilote-web | **sonnet** |

→ **Le routeur, qui ne fait que trier, est sur sonnet** — contrairement à ce que sa fonction
suggère. Le commentaire `router.py:8` l'assume (« le routage est un raisonnement »). La mesure
0.4 renverse cette prémisse.

## 0.2 — Chronométrage par étage (2 passes/cas, ms)

| cas | intent | total | décomposition |
|---|---|---|---|
| **maire** « Qui est le maire de La Possession ? » | QUESTION→web | **~15–16 s** | route(sonnet 1,8–6,4) + select(sonnet 5,0–8,9) + web-search(~4,7) |
| **comptage** « Combien de parcelles à Saint-Paul ? » | QUESTION | **~7–9 s** | route(sonnet 1,7–1,9) + select(sonnet 1,7–5,1) + formule(sonnet 1,8–1,9) + réseau |
| **clarification** « Je veux investir. » | QUESTION | **~3,5–4 s** | route(sonnet 3,5–4,0) seul |

Constats : (1) la latence est **entièrement LLM** (le SQL du comptage est négligeable) ; (2) le maire
paie **deux appels sonnet (route + select) AVANT** même que la recherche web démarre ; (3) une simple
clarification coûte un aller-retour sonnet complet (~4 s) pour un seul mot de tri.

## 0.3 — Le piège de config `LABUSE_ASSISTANT_MODEL`

Lu en **un seul endroit** : `api/assistant.py:346`, et seulement pour `explain_parcel` (le
« Expliquer cette parcelle » de la fiche). **Il n'écrase PAS le partage deux-modèles du Copilote** :
`copilote_v2/*` n'importe jamais `assistant.py`, et ni `ai/core` ni `copilote_v2` ne lisent cette
variable. → Pas de piège VPS pour le Copilote ; l'override est étroit et documenté.

## 0.4 — Expériences décisives (gates sous haiku, non commitées)

Pour proposer sur mesure et pas au jugé, j'ai fait tourner les gates avec `MODEL_REASONING→haiku` :

| expérience | résultat | lecture |
|---|---|---|
| **routeur sur haiku** (`qa/m78/routeur_eval.py`) | **100,0 %** clair · ambigu 5/5 · corrections 5/5 · **coût ÷3** (0,197 € vs 0,572 €) | le tri **n'a pas besoin de sonnet** — haiku fait mieux sur le gate 45 |
| **chemin QUESTION entier sur haiku** (`qa/m78/veracite.py`) | **32/33** (1 raté) | l'unique raté = Q14 « Combien de logements à Saint-Paul ? » : haiku **a posé une clarification** au lieu de servir 51 317. Échec **prudent** (aucune invention), mais échec — c'est le **sélecteur** qui perd en décision, pas l'anti-invention |

## Proposition de réaffectation (à arbitrer)

Deux leviers indépendants. **Le levier A ne touche aucun modèle** (zéro risque de gate) et porte
l'essentiel du gain ; le levier B demande l'arbitrage.

### Levier A — les chips court-circuitent le routage (cœur de M113, aucun changement de modèle)
Chip choisi ⇒ scénario connu ⇒ classify **sauté ou réduit à l'extraction de paramètres**.
- Chip « Rechercher sur le web » → **saute route + select** → direct au web. **Maire : ~15 s → ~5 s.**
- Chip « Interroger mes données » → **saute route**, extraction FACTUAL, facette + formule.
  **Comptage : ~7–9 s → ~4–5 s.**
- Gain **mesuré** contre cette base en Phase 5. Anti-invention **inchangé** (le verrou reste sur la
  voie chip : extraction vérifiée, chiffres à l'oracle, critères non appliqués dits — M109).

### Levier B — réaffecter les modèles (arbitrage requis, gates vertes obligatoires)
- **B1 — classify → FACTUAL (haiku). RECOMMANDÉ.** Preuve : routeur 100 % sur haiku, ÷3 coût,
  gagne ~2–4 s sur **chaque** message, y compris texte libre. C'est la prémisse du mandat confirmée.
- **B2 — _formuler → FACTUAL (haiku). Candidat.** Pure mise en forme sous verrou déterministe ;
  l'anti-invention a tenu partout sous haiku. À valider gate formule-seule.
- **B3 — _select_tool → garder SONNET.** L'unique raté haiku est une hésitation du sélecteur.
  De plus, sur la voie chip, le sélecteur est souvent inutile (le scénario est déjà connu).
- **B4 — recherche_web → garder SONNET** (un seul appel ; plus le goulot une fois route+select ôtés).

**Recommandation courte** : livrer le **levier A** (chips) — le gros du gain, sans risque — et
adopter **B1** (routeur→haiku, prouvé). Tenir B2 pour un second temps mesuré, garder B3/B4 sonnet.
Rien n'est changé côté modèle sans ton feu vert.
