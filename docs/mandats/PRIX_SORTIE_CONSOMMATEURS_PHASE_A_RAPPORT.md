# RAPPORT — Prix de sortie dans les consommateurs, PHASE A (mesure). Point d'arrêt.

**Exécuté le 28/07/2026** (exécuteur Claude Code). **LECTURE SEULE — aucune application, pas de
re-run de scoring.** Golden **116/116** et tiers du run servi `q_v7_defisc` **au bit près**
(120 / 1031 / 3587 / 72980 / 353945) avant ET après.

## 0 · Contrôle de base (leçon Vic appliquée) — le même piège a mordu phase C

Avant de mesurer, contrôle de la base : **la phase C (repli île, 16 communes) N'EST PAS sur
`origin/main`** (dernier commit `b20ab06` = application calibration, sans phase C). Elle vit
seulement sur la branche locale `feat/couverture-prix-repli-ile`. La **DB**, elle, est en état
phase C (ligne `dvf_prix_sortie_neuf niveau='ile'`, score_e 49 636 estimables). Code-main et DB
divergent — exactement la leçon gravée au mandat précédent. **J'ai donc mesuré sur `feat/couverture-
prix-repli-ile`** (code phase C, cohérent avec la DB et avec la prémisse « 16 communes » du mandat),
et non sur main. **À reporter : phase C doit être poussée/mergée sur `origin/main` avant toute
application de ce mandat** (sinon la routing s'appuierait sur un `resolve_prix_neuf_marche` à 5
communes).

## 1 · Cartographie exhaustive des appels `sector_price` (phase B, faite en lecture seule)

Méthode `constructible_neuf` — grep exhaustif, chaque site étiqueté LÉGITIME (valeur d'un bien
EXISTANT) ou FAUX (prix de sortie d'une opération NEUVE). **Correction de mon propre mandat : il y
a 6 sites faux, pas 4** — j'avais classé la calculette « hors périmètre » en supposant un prix
saisi ; la mesure montre que son prix de sortie est `sector_price`, pas une saisie utilisateur.

| Site | Usage | Verdict |
|---|---|---|
| `copilote/moteurs.py:385` | `compute_bilan` → charge (`c["marche"]`) | **FAUX — router** |
| `api/modules.py:815` (Rapport potentiel) | `compute_bilan` → `out["bilan"]` | **FAUX — router** |
| `api/modules.py:943` (Explication IA) | `compute_bilan` → facts bilan | **FAUX — router** |
| `api/briques_pdf.py:244` (Banquier + Argumentaire) | `compute_bilan` → `out["bilan"]` | **FAUX — router** |
| `api/modules.py:875` (calculette `/modules`) | `compute_calculette` prix de sortie | **FAUX — router** (était « hors périmètre ») |
| `api/app.py:2089` (calculette `app`) | `compute_calculette` prix de sortie | **FAUX — router** (était « hors périmètre ») |
| `faisabilite/db.py:380` (CŒUR fiche) | comparables DVF (charge déjà routée en override) | **LÉGITIME — ne pas toucher** |
| `api/modules.py:807` → `out["marche"]` | bloc marché / comparables | **LÉGITIME** |
| `api/briques_pdf.py:242` → `out["prix_dvf"]` | comparables DVF | **LÉGITIME** |

**Règle nette** : le prix de l'existant est juste pour DÉCRIRE un bien existant (comparables, bloc
marché, prix probable du foncier) ; il est faux comme PRIX DE SORTIE d'un bilan neuf. On ne route
que les seconds. Les sites `modules.py:807` et `briques_pdf.py:242` sont DUAL-USE (le même
`sector_price` alimente le marché — légitime — ET le bilan — faux) : le routage doit toucher
l'injection dans `compute_bilan`, pas le bloc marché.

## 2 · Écart de charge sector_price → resolve_prix_neuf_marche (16 communes couvertes)

Échantillon seedé `conso`, **1 826 parcelles calculables** dans les 16 communes. Les deux
configurations des consommateurs (A « no-bp » = Copilote + Rapport ; B « défauts calculette » =
Explication + Banquier + calculette) donnent des résultats **identiques** (coef CA 0,79 et coût
2 550 communs) :

- **Écart de charge (cible − courante), déciles €** :
  −1 441 749 · 0 · +39 986 · +91 068 · **+135 065 (médiane)** · +200 000 · +300 000 · +400 000 ·
  +585 598 · +900 000 · +7 271 119.
- **La charge MONTE massivement** (médiane +135 k€) — le sens attendu, mesuré et non présupposé.
- **Bascules de viabilité** : **NV → V : 1 333** (courante non viable → cible viable) ·
  **V → NV : 81** (reverse flips).

### 2.1 · Les reverse flips (81) — investigués, PAS un artefact

**Les 81 V → NV sont TOUS des `override_bassin`, TOUS à Saint-Paul** : Plateau Caillou 77,
La Plaine-Bois de Nèfles 4. Cause mesurée : le prix de **bassin sourcé** de ces Hauts (Plateau
Caillou 3 500, La Plaine 3 400) est **INFÉRIEUR au `sector_price` de l'existant local** (4 155 à
4 645) — vraisemblablement parce que le `sector_price` à rayon adaptatif remonte des appartements
plus chers du littoral, alors que le bassin override porte le vrai prix neuf des Hauts. **Le routage
y BAISSE la charge**, ce qui est correct SI les overrides de bassin sont justes.

**Ce que ça soulève (finding, pas artefact)** : dans les Hauts de Saint-Paul, le prix de sortie
neuf sourcé (3 400-3 500) contredit le prix de l'existant local (4 155-4 645). Deux lectures — soit
l'override de bassin est bon et le `sector_price` y est gonflé par le rayon, soit l'override est
sous-évalué. **À trancher AVANT de router ces bassins** (revue des valeurs Plateau Caillou / La
Plaine, ou de la portée du rayon en zone de Hauts). Hors de ce poste, aucune bascule inverse : le
routage est monotone (charge ↑) partout ailleurs.

## 3 · Extension du « non calculable » aux 8 communes social-dominantes

Sur les social-dominantes (où `resolve_prix_neuf_marche` renvoie « non calculable »), **358 / 358
parcelles de l'échantillon servent AUJOURD'HUI une charge** (via `sector_price` existant) dans les
consommateurs — charge qui **doit devenir « non calculable »**. C'est la même incohérence
cross-écran que la fiche corrigeait : le Copilote/Banquier affiche un chiffre là où la fiche dit
« je ne sais pas ». Le routage doit étendre les **4 étiquettes** de la fiche (médiane locale N ventes /
île validée / île sans opération / non calculable social) à ces 6 sites.

## 4 · Question bloquante — tiers et score_e

- **Tiers** : les consommateurs ne font que **LIRE** `parcel_p_score_v2` (LEFT JOIN d'affichage du
  tier) — **aucune écriture** (grep : 0 INSERT/UPDATE, 0 appel scoring). Router leur prix de sortie
  ne peut pas bouger un tier. Golden 116/116 + tiers au bit près avant/après (mesure lecture seule).
- **score_e** : n'est PAS un des consommateurs (batch séparé) et utilise DÉJÀ le bon instrument
  (repli île, phase C) — **non affecté** par ce mandat. Il faudra néanmoins le repasser en phase C
  d'application si sa cohérence l'exige, mais la routing des 6 sites ne le touche pas.

## 5 · Recommandation (phase B/C, non exécutée — point d'arrêt Vic)

1. **Router les 6 sites faux** vers `resolve_prix_neuf_marche` (injection dans `compute_bilan` /
   `compute_calculette`), en gardant intacts les blocs marché/comparables (dual-use). Idéalement via
   **un point de résolution partagé** pour qu'aucun futur consommateur ne retombe sur `sector_price`.
2. **Étendre les 4 étiquettes + le « non calculable » non filtrant** aux 6 sites (jamais un chiffre
   là où la fiche dit non calculable).
3. **Trancher les bassins des Hauts de Saint-Paul (Plateau Caillou, La Plaine) AVANT de router** :
   c'est le seul poste de reverse flip, et il pose une vraie question de valeur (override sourcé <
   existant local). Ne pas router ces bassins « à l'aveugle ».
4. **Pousser/merger phase C sur `origin/main`** avant l'application (la routing s'appuie sur le
   `resolve_prix_neuf_marche` à 16 communes, qui n'est pas encore sur main).
5. **Revue visuelle des 2 PDF** (Banquier, Argumentaire) avant merge (discipline O12/M26-B).
6. Gates habituels : golden + tiers avant/après, back-test chemin de production + E3, arrêt si un
   tier bouge.

## Artefacts

`/tmp/conso_ecart.py` (écart de charge + bascules, LECTURE SEULE). Golden 116/116 + tiers au bit
près (`/tmp/consoA_tiers_avant.txt` = `/tmp/consoA_tiers_apres.txt`). Mesuré sur la branche
`feat/couverture-prix-repli-ile` (code phase C).

---

# ANNEXE — Bassins des Hauts de Saint-Paul : les 81 reverse flips tranchés (mesure Vic)

LECTURE SEULE. Golden 116/116 + tiers au bit près. Question : sur Plateau Caillou et La Plaine,
l'override de bassin (3 400-3 500) et le `sector_price` local (4 155-4 645) ne peuvent être vrais
tous les deux. Quatre mesures.

## 1 · Provenance de l'override — LA FAMILLE DU 2100

Les 4 overrides de bassin (Saint-Gilles 5 800, La Saline 6 000, Plateau Caillou 3 500,
La Plaine-Bois de Nèfles 3 400) viennent de **`f25e8cc`, 14/06/2026** — **le même jour et la même
calibration web que le socle 2100** (`d94ff9b`, 14/06). Marqués « sourcée », mais la source est un
**OBSERVATOIRE de l'EXISTANT** (SeLoger : Plateau Caillou appart 3 417 ; consortium : La Plaine
~3 100-3 700), **pas du DVF, pas du neuf**. Le RAPPORT_CALIBRATION_WEB le dit lui-même : « Hauts,
**peu de collectif** ». C'est la famille du 4900 : observatoire, 14/06, jamais confirmé par DVF —
et en conflit avec la règle « DVF, un seul référentiel » (décision Vic, l'observatoire est une
contre-mesure documentée, pas une entrée de calcul).

## 2 · Ventes d'appartements neufs DVF dans ces bassins (mesure directe) — trop minces ET contradictoires

| Bassin | override | neuf DVF (direct) | existant DVF bassin | commune Saint-Paul DVF |
|---|---|---|---|---|
| Plateau Caillou | 3 500 | **3 585 (n=2)** ~ override | 4 016 (n=328) | 4 730 |
| La Plaine | 3 400 | **4 255 (n=3)** > override | 3 431 (n=106) | 4 730 |

Le DVF neuf direct est **sous le seuil N_MIN=10** (n=2 et n=3) et **contradictoire** : il ~confirme
Plateau Caillou (3 585) mais **infirme La Plaine** (4 255 ≫ 3 400). **Il ne peut ni confirmer ni
réfuter l'override** — il n'y a pas de marché du collectif neuf mesurable dans ces Hauts.

## 3 · Résolution SANS override + gonflement du rayon (`sector_price`)

- **Sans override** : aucun `dvf secteur` pour ces bassins → repli **commune Saint-Paul 4 730**
  (source DVF mesurée).
- **`sector_price` (rayon adaptatif)** : La Plaine 3 000-3 457 (rayon 500-1000 m, **PAS gonflé** —
  ≈ override) ; **Plateau Caillou 4 134-4 596** (rayon 500-1000 m, **plus haut** — c'est là que
  naissent les 77 reverse flips). Le gonflement du rayon est réel **à Plateau Caillou** (le rayon
  remonte des appartements plus chers), pas à La Plaine.

## 4 · Verdict et recommandation (ton inclination confirmée par la mesure)

**Trois sources sur ces bassins : l'override observatoire (3 400-3 500, existant, 14/06, non
confirmé DVF), le DVF neuf direct (n=2-3, trop mince et contradictoire), la commune DVF (4 730,
mesurée).** L'override **ne peut pas primer sur une source DVF mesurée** — il est de la famille du
2100, observatoire, jamais confirmé, et il n'y a pas assez de collectif neuf dans les Hauts pour le
confirmer un jour à court terme.

**Recommandation — les deux overrides des Hauts (Plateau Caillou, La Plaine) → `is_placeholder=true`,
HORS préséance jusqu'à confirmation DVF** (exactement le traitement du 2100 et du socle). Effet
mesuré : ces parcelles résolvent alors sur la **commune 4 730** (DVF), les **81 reverse flips
disparaissent**, le routage devient **monotone** (charge ↑ partout). L'override reste visible en
placeholder (le signal « Hauts moins chers » n'est pas perdu — il attend une confirmation DVF).

**Réserve honnête** : 4 730 peut SUR-évaluer les Hauts face au signal observatoire (~3 400-3 800).
Mais 4 730 est **mesuré** ; le DVF neuf direct est trop mince pour arbitrer ; et le défaut discipliné
(source mesurée > estimation non confirmée) est cohérent avec le 2100/socle.

**Les deux bassins balnéaires (Saint-Gilles 5 800, La Saline 6 000)** : MÊME provenance (observatoire
14/06, non confirmés DVF), mais AU-DESSUS de la commune (premium balnéaire plausible) et **aucun
reverse flip**. Aucune mesure ne force leur retrait ; les démoter perdrait un signal plausible. **À
ta décision** : la cohérence stricte (DVF seul) les démoterait aussi, mais le premium balnéaire est
réel — je recommande de les GARDER, en les flaggant « à confirmer par DVF » comme Le Guillaume.

Artefact : `/tmp/hauts_bassins.py` (LECTURE SEULE). Golden 116/116, tiers au bit près avant/après.
