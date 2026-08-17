# M111 — la rupture de sujet

Livré le 17/08/2026. Corrige le 3ᵉ défaut de conversation mesuré en M108 (§3.1). 3ᵉ des
4 correctifs arbitrés.

## Le défaut, ses DEUX chemins (mesurés)

Le contexte inter-tours contaminait un tour sans rapport — deux chemins, un seul cause
(l'héritage aveugle) :

1. **brief_effectif RECHERCHE** (M107) : deux RECHERCHE de sujets différents → concaténés
   → l'interpréteur fond les deux. Mesuré : « des friches en zone U à Cilaos pour 8
   logements » après « ≥ 20000 m² à Saint-Paul pour 30 logements » → récap
   « Saint-Paul, Cilaos, **38 logements** [30+8 sommés], ≥ 20000 m² hérité ».
2. **prior_params du routeur** (le screen de Vic) : `_normalise` fusionnait les paramètres
   du tour précédent SANS condition. Mesuré : « combien de parcelles en procédure judiciaire
   à Saint-Denis » après le même T1 → surface_min=20000 hérité et **appliqué** → **7**
   servi au lieu de **126** (le compte contaminé, pas seulement le récap).

## Le critère de rupture (Phase 1)

Proposition de l'audit M108 confrontée aux quatre cas : clarification (contexte DOIT tenir),
correction (idem), même sujet (peut aider), autre sujet (DOIT tomber). Le critère qui tranche :
**le message est-il une demande AUTONOME (change de sujet) ou une CONTINUATION du fil ?**
C'est un jugement de contexte — le routeur le fait déjà (gate 45). Il produit désormais
`nouveau_sujet` (true = autonome, false = continuation). En cas de doute : hériter (false) —
un héritage DIT n'est pas une contamination, l'utilisateur corrige d'un clic.

## L'implémentation (Phase 2) — UN seul endroit, serveur

1. `router.py` : le modèle sort `nouveau_sujet` ; `_normalise` **n'hérite QUE si continuation**
   (nouveau_sujet=false). Un tour autonome part de ses seuls paramètres. Le défaut prudent
   (champ omis) = hériter (protège la clarification ; un fil neuf n'a rien à hériter).
2. **Jamais de somme** : `merged.update(tour)` — le tour courant PRIME, un paramètre a une
   valeur (la plus récente). Filet prompt (interpréteur, règle 7bis) : plusieurs valeurs d'un
   même paramètre dans une phrase recomposée → la dernière, jamais la somme.
3. `answering.py` RECHERCHE : le brief_effectif ne concatène le fil QUE si continuation.
4. **L'héritage est DIT** : `_normalise` trace `herites` (ce qui vient du fil, pas du tour) ;
   le récap `compris` le nomme (« … (repris du fil : ≥ 1000 m²) »). Règle M109/M110 étendue
   à l'héritage — jamais un paramètre hérité muet.

## Vérification (Phase 3)

Cas M108 rejoués (gate fil, oracle hand-SQL) :
- **S4** 2×RECHERCHE : « Cilaos, 8 logements, zones U » — plus de Saint-Paul, plus de 20000,
  plus de 38, « friches » n'est plus fondu.
- **S5** RECHERCHE→QUESTION procédure : **126** servi (était 7), « ≥ 20000 m² » absent du récap.
- **S6** clarification (cas témoin M107) : « Saint-Paul, 15 logements, ≥ 100000 m² » — le
  contexte tient toujours.
- Continuation « et à Saint-Benoît ? » (≥ 1000 m² hérité) → 7 009 (juste), surface nommée.

Gates toutes vertes, rien d'assoupli : fil **6/6** (S1-S3 + S4-S6 rupture), véracité **33/33**,
routeur **gate_95=true** (97,1 % — un raté borderline QUESTION/VERIFICATION sur une parcelle-risque,
sans rapport avec la rupture, variance modèle). 1573 passed · golden 0 FAIL · tsc 0 · build.
4 tests unitaires déterministes (`_normalise` : autonome, continuation+trace, jamais de somme, défaut).
AUCUN changement front (la rupture vit au serveur, jamais une heuristique front).
