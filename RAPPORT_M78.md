# RAPPORT M78 — Copilote v2 : le client écrit, LABUSE instruit

Branche `feat/m78-copilote` (précondition OK : M-ENTREE mergé `5551103c`, main propre).
Maquettes de référence : `docs/DA-COPILOTE-ACCUEIL.html`, `docs/DA-COPILOTE-RESULTATS.html`.
Méthode : recopier les classes des maquettes et y verser les données — jamais de mémoire.

---

## DOCTRINE (gravée)

**Le modèle ne répond jamais une donnée de mémoire.** Toute affirmation factuelle provient d'un appel
d'outil exécuté contre la base. Le modèle traduit la question en appel d'outil, formule la réponse
depuis le résultat, cite l'outil. Le modèle n'écrit JAMAIS de SQL : il choisit un outil et des
paramètres typés, le serveur exécute une requête paramétrée. **Interdit** : un outil générique
`requete_libre(sql)` — c'est la porte de sortie de toute la doctrine.

**Les cinq issues d'une demande — une seule grammaire :**
1. **Couvert** → réponse chiffrée, source + millésime, états Sourcé/Estimé quand on restitue des
   données parcelle.
2. **Partiellement couvert** → ce qu'on a + ce qui manque, DIT (ex. délai Sitadel : médiane sur
   permis ACCORDÉS seulement = minimum optimiste, réserve rédigée mot pour mot du dossier banquier).
3. **Donnée structurellement inexistante** → refus SPÉCIFIQUE : pourquoi elle n'existe pas + où
   l'obtenir (propriétaire PP → demande SPF, porte Courrier ; « valeur dans 10 ans » → pas de
   projection, marché constaté proposé).
4. **Aucun outil ne correspond** → refus honnête, jamais une réponse plausible, pas de « bientôt ».
   Télémétrie (§1e). Cas connu : « cette parcelle est-elle divisible ? » (pas de score par parcelle,
   BACKLOG M-ENTREE) → répondre sur le fond (surface, zonage, règlement), AUCUN outil proposé.
5. **Hors sujet** → réponse fixe, zéro appel d'outil, zéro frais : « Je suis le copilote foncier de
   LABUSE — je réponds sur l'immobilier et le foncier de La Réunion. »

**Quand le Copilote dit « c'est fait », la chose EST faite** et visible dans la section de l'app.
Aucune confirmation sans écriture réelle préalable, par les API existantes uniquement.

**Coûts** : Sonnet par défaut partout (Opus interdit sans justification rapportée). Chaque appel
modèle journalisé (prompt, outils appelés, réponse, tokens) — c'est l'auditabilité vendue.

---

## PHASE 1 — Routeur et boîte à outils
_(en cours — 1a LIVRÉ ci-dessous ; restent : 1b outils+SQL · 1c table demande→outil · 1d test
véracité 32 questions · 1e télémétrie · 1f plafonds/coûts)_

### 1a — Routeur d'intention (LIVRÉ, gate bloquant franchi)

**Module** : `src/labuse/copilote_v2/router.py`. Un appel **Sonnet** (`core.MODEL_REASONING`, doctrine
« Sonnet partout ») classe le message en 7 intentions + extrait des paramètres typés. Sortie **JSON
strict validée par schéma** (`ROUTE_SCHEMA`, jsonschema) — motif éprouvé de `/ia/search` : parse
robuste (élague les ```json), clés hors liste blanche ÉLAGUÉES (jamais avalées ni inventées),
**une re-demande** si JSON invalide puis erreur honnête. Le routeur ne répond JAMAIS une donnée.
- **Contexte de session** : `HISTORIQUE_TOURS = 6` derniers tours passés au modèle (dimensionné :
  6 couvre les enchaînements « et à Saint-Benoît ? » sans gonfler le coût — mesuré ~1500 tok in/appel).
- **Correction / héritage** : `prior_params` fusionnés côté serveur — un paramètre déjà connu (IDU du
  tour 1) survit au re-routage du tour 2 s'il n'est pas contredit. Filet déterministe en plus du modèle.

**Test** (`qa/m78/routeur_eval.py`, 45 messages étiquetés, modèle RÉEL) — matrice de confusion :

```
attendu\obtenu  QUEST  OUTIL  RECHE  VERIF  VEILL  PROJE  HORS_
QUESTION          8
OUTIL                   6
RECHERCHE                      6
VERIFICATION                          4
VEILLE                                       4
PROJET                                              3
HORS_SUJET                                                 4
```
- **Précision intentions claires : 100 % (35/35)** — gate ≥ 95 % franchi. Diagonale parfaite.
- **Ambigus 5/5** : une clarification posée (jamais un menu) sur « Saint-Paul. », « Cette parcelle. »,
  « Je veux investir. », « Combien ça coûte ? », « Le terrain là-bas ».
- **Corrections de tour 2 : 5/5** — bon re-routage ET paramètre conservé (IDU/surface/programme/commune).
- Répartition : 7 intentions (33 clairs dont 6 OUTIL, **2 sans outil = division**, décision M-ENTREE)
  + 5 ambigus + 5 corrections = 45.
- **Deux ajustements de prompt** consignés (pas de sur-ajustement — règles de principe) : (i) « des
  parcelles [caractéristique] à [commune] » = ENSEMBLE à lister → RECHERCHE (pas QUESTION) ; (ii)
  « ajoute une parcelle à ce projet » = gestion de PROJET (flux Phase 3b réel), pas OUTIL générique.
- **Coût mesuré** : ~0,006 €/appel de routage (Sonnet, ~1500 tok in / ~90 tok out) ; journalisé dans
  `ia_log` (kind `copilote-route`). Une passe complète des 45 messages ≈ 0,27 €.
