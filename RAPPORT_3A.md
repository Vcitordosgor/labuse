# RAPPORT — 3.A Assistant de fiche en langage naturel ★

> Cercle 3. Bouton « Expliquer cette parcelle » → synthèse en prose, **API Anthropic**.
> Construit ENTIÈREMENT (prêt à l'emploi dès la clé posée) ; sans clé, dégrade proprement.
> 288 tests verts, ruff clean.

## Clé API — variable d'environnement (à fournir par Vic)
- **`ANTHROPIC_API_KEY`** : clé API Anthropic. **Jamais en clair dans le code, jamais commitée** —
  lue dans l'environnement du serveur (documentée aussi dans `DEPLOY_RUNBOOK.md`).
- **`LABUSE_ASSISTANT_MODEL`** (optionnel) : modèle à utiliser. Défaut : `claude-sonnet-4-6`.
- **Tant que la clé n'est pas posée** : le bouton affiche un message clair (« Assistant IA non
  configuré — définissez ANTHROPIC_API_KEY… ») et reste inactif. **Aucun crash, aucune 500.**

## Ce qui est livré
- **Module** `api/assistant.py` : `assistant_facts(fiche)` + `explain_parcel(fiche)`.
- **Endpoint** `GET /parcels/{idu}/explain` : construit la fiche, appelle l'assistant, renvoie la
  prose (ou le message d'indisponibilité). Isolé — ne casse jamais la fiche.
- **Fiche** : bouton « ✨ Expliquer cette parcelle » sous le résumé → prose + pied de page
  « rédigée par IA à partir des seules données de la fiche — à vérifier, aucune garantie ».
- **Appel API** via `httpx` (timeout 25 s) — **aucune nouvelle dépendance**. Gère proprement :
  **clé absente**, **timeout**, **erreur réseau/API**, **réponse vide** → message clair à chaque fois.

## Garde-fou anti-hallucination (cœur de l'item)
Le prompt envoyé au modèle ne contient **QUE** une **liste blanche** de faits structurés extraits
de la fiche (`assistant_facts`) — statut, scores, zone PLU, capacité (niveaux/SDP/hauteur/volume),
bilan, contraintes/signaux de la cascade (HARD_EXCLUDE / SOFT_FLAG / POSITIVE), complétude
(sources muettes), résumé métier. **Rien d'autre** n'est transmis (le centroïde, par ex., est
exclu). Le *system prompt* impose : « n'invente AUCUN chiffre, AUCUN verdict ; si une donnée
manque, dis-le ; aucune garantie ». **Le modèle reformule, il n'ajoute pas de fait.**

## Recette
`pytest tests/test_assistant.py` (**4 verts**, sans clé) :
- la **liste blanche** est stricte (7 sections, rien d'autre ne part au modèle) ;
- seules les contraintes **HARD/SOFT/POSITIVE** sont transmises (UNKNOWN/PASS exclus) ;
- une donnée absente reste **nulle** (jamais inventée) ;
- **sans clé** → `available=false`, `reason="no_key"`, message nommant la variable, **pas de crash**.

**Recette live (dès la clé posée)** — à exécuter par Vic : ouvrir 2 parcelles contrastées
(1 opportunité constructible, 1 exclue), cliquer « Expliquer » → l'explication doit refléter
**fidèlement** les verdicts réels (statut, contraintes, capacité), **sans rien inventer**. Le
garde-fou ci-dessus garantit que l'entrée du modèle = uniquement les faits de la fiche.
