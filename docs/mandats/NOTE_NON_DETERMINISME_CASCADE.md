# NOTE — Non-déterminisme de la cascade (risques / zonage)

> **Mandat à part (Vic, 30/07).** Tolérable aujourd'hui (n'affecte ni `matrice_statut` ni les
> tiers), **pas acceptable en principe** : entorse directe à l'argument central du produit — « chaque
> chiffre est reproductible au bit près ». S'il touche un jour une valeur SERVIE, c'est le socle de
> vérifiabilité qui tombe.

## 1. Ce qui est non déterministe, exactement (mesuré)
Deux exécutions de la MÊME méthode (mêmes 200 parcelles, même code, même données) produisent des
lignes `dryrun_cascade_results` qui diffèrent sur **1 350 lignes** :
- **`risques` : 1 322 lignes**
- **`zonage_plu_gpu` : 28 lignes**

**Ce qui NE bouge PAS** : `matrice_statut`, `q_score`, `a_score` — **0 différence** (vérifié). Donc
les tiers servis et le golden au niveau tier sont intacts. Le non-déterminisme est confiné au
DÉTAIL/ORDRE des verdicts, pas à leur agrégat.

## 2. D'où vient la dépendance à l'ordre (cause racine, par le code)
- `EvalContext.prime()` (`cascade/context.py`) charge les intersections spatiales par une requête
  **SANS `ORDER BY`** (`SELECT … GROUP BY b.id, lid …`). PostgreSQL renvoie alors les lignes dans un
  ordre **physique / dépendant du plan** (ordre du heap, parallélisme, bascule de plan) — qui **varie
  d'un run à l'autre**. Les lignes sont empilées telles quelles dans `self._inter[(pid, kind)]`.
- `ctx.intersections(parcel.id, kind)` restitue cette liste **dans l'ordre reçu** (non trié).
- `RisquesLayer.evaluate` (`cascade/layers/phase1.py:482` et `:515`) **émet un verdict PAR
  intersection, dans cet ordre** (boucle `for i in ctx.intersections(...)`). Une parcelle qui
  intersecte plusieurs périmètres PPR / aléas reçoit donc ses N verdicts **dans un ordre non
  déterministe** → à la persistance, les N lignes (mêmes contenus) reçoivent des `id`/ordre
  différents, et tout `detail` construit dans l'ordre diffère.
- `zonage_plu_gpu` (même fichier) : mêmes intersections non triées ; le détail et le départage
  (`_dominant`, ex æquo de couverture) peuvent basculer sur l'ordre → 28 lignes.

**Le CONTENU (multiset de verdicts) est déterministe** — mêmes intersections calculées (coverage
bit-identique, prouvé §cache pré-subdivisé). Seul l'**ORDRE des lignes** varie. C'est une
non-reproductibilité de FORME (ordre/`id`/`detail` ordonné), pas de FOND (agrégat stable).

## 3. Ce qu'il faudrait pour la lever
Rendre l'ordre des intersections DÉTERMINISTE, une fois, au point d'étranglement — trois options,
de la plus sûre à la plus large :
1. **`ORDER BY` dans la requête `prime`** (`context.py`) — ajouter `ORDER BY lid` (ou `subtype, lid`)
   à la requête d'intersection. Un seul point, tous les consommateurs deviennent déterministes.
   **Le plus sûr et le plus ciblé.**
2. **Trier `ctx.intersections()`** à la lecture (par `lid`/`subtype`) — équivalent, côté Python.
3. **Trier les verdicts avant persistance** (`_persist_dryrun`) par une clé stable — traite le
   symptôme pour toutes les couches multi-verdicts, sans toucher l'ordre d'évaluation.

**Vérification obligatoire après correctif** : deux runs même méthode → **0 ligne différente**
(y compris `detail`) ; golden inchangé ; `matrice_statut`/tiers inchangés (ils le sont déjà).
Attention : un `ORDER BY` ajoute un tri à `prime` (point chaud perf) — mesurer le surcoût (a priori
négligeable devant l'intersection, surtout avec le cache pré-subdivisé).

## 4. Périmètre & risque
- **Aujourd'hui** : aucune valeur servie n'est touchée (fiche affiche les verdicts risques comme un
  ensemble ; le tier/scoring lit l'agrégat). Tolérable.
- **Bascule** : si une surface servie se met un jour à dépendre de l'ORDRE (ex. « premier risque
  affiché », concaténation ordonnée dans un PDF, hash d'un run pour audit), la reproductibilité
  « au bit près » tombe **silencieusement**. D'où : mandat à traiter avant que ça n'arrive.
- **Découvert** le 30/07 en validant le cache pré-subdivisé (2 runs même méthode diffèrent pareil →
  le cache est innocent, le non-déterminisme est intrinsèque et pré-existant).

*Artefacts : mesure 2×(200 parcelles Sainte-Rose), q_det1/q_det2 (nettoyés). Cause : `context.py`
prime sans ORDER BY → `phase1.py:482/515` RisquesLayer.*
