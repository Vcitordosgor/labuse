# TEST-R2-CHARGE — rapport

Branche `fix/test-r2-charge` (base `main`). Aucun merge, aucune modification de code de production :
le seul fichier changé est `tests/test_etude_fiable_1.py`.

**Symptôme.** `tests/test_etude_fiable_1.py::test_r2_deux_analyses_memes_saisies_meme_resultat` échoue
quand la machine est chargée : deux analyses aux saisies IDENTIQUES rendent deux résultats DIFFÉRENTS.
Il a bloqué cinq envois aujourd'hui sur des branches sans rapport.

---

## 1. Cause confirmée (lecture du code + reproduction)

Le moteur d'implantation examine une grille de candidats dans un ordre fixe et s'arrête sur un **compteur
déterministe** `etude_grille_max_candidats` (= 150). C'est ce compteur qui décide du résultat — pas le
temps. Mais il subsiste un **filet de temps**, `etude_grille_garde_fou_s` (variable d'env
`LABUSE_ETUDE_GRILLE_GARDE_FOU_S`, défaut 100 s) :

`src/labuse/implantation/moteur.py:361-376`
```
if (time.monotonic() - t0) > garde_fou_s:
    coupe = True
    garde_fou = True
    break
...
terrain.grille_candidats_examines = examines
if garde_fou:
    terrain.grille_garde_fou_temps = True   # → recherche « partielle » (non reproductible)
```

Quand la machine est chargée, la grille N=150 du témoin le plus lourd (Saint-André) dépasse le filet
AVANT d'avoir examiné les 150 candidats prévus. Le filet coupe à un **instant différent à chaque appel**
→ `candidats_examines` diffère d'un appel à l'autre → les sorties qui en dérivent (ex. « N candidats
écartés » dans les limitations) diffèrent → `p1 != p2`. Le test tombe. C'est bien le garde-fou de temps,
pas une autre cause.

**Reproduction (avant correctif), machine chargée (load avg ≈ 13) :**
```
assert json.dumps(p1,...) == json.dumps(p2,...)
E  ... - mesure: "6 candidats écartés" ...   (p1 ≠ p2)
1 failed in 373.54s
```
Chaque appel a duré ~186 s, loin au-delà du filet de 100 s : le filet a bien coupé les deux recherches, à
des nombres de candidats différents. Diff localisée sur les compteurs « candidats écartés » — exactement
la signature d'une recherche coupée au temps.

---

## 2. Correctif — DANS CE SEUL TEST, deux entrées machine neutralisées

`test_r2` vérifie le **déterminisme** (mêmes saisies → même résultat), pas le filet temps (ça, c'est le
rôle de `test_r3_garde_fou_force_recherche_partielle`, qui force le filet à 1 s). On neutralise donc,
**uniquement dans ce test**, les deux entrées qui faisaient dépendre le résultat de l'état de la machine :

```python
monkeypatch.setenv("LABUSE_ETUDE_GRILLE_GARDE_FOU_S", "86400")   # (1) le temps n'arbitre plus
monkeypatch.setattr(profil_altimetrique, "_completer_ign", lambda pts: None)  # (2) zéro réseau IGN
config.get_settings.cache_clear()
try:
    p1 = etudier_payload(session_reelle, _cfg_andre())
    p2 = etudier_payload(session_reelle, _cfg_andre())
finally:
    config.get_settings.cache_clear()
```

**(1) Le filet temps.** Même mécanisme que `test_r3`/`test_etude_plafond_1`, à l'inverse (eux forcent le
filet à 1 s / 0,01 s pour PROUVER la coupe ; ici on l'ouvre). La grille examine alors TOUJOURS les N=150
candidats prévus → `candidats_examines` reproductible.

**(2) L'appel réseau IGN.** Première preuve (9/10) : une fois le filet neutralisé, il restait une
divergence RARE, apparue au pic de charge (load avg 16,8), sur le contrôle « implantation étagée » (relief
LiDAR). Traçage : dans tout le moteur d'implantation il n'y a AUCUNE autre source de non-déterminisme
(ni temps hors filet, ni aléatoire, ni fil d'exécution) ; la seule entrée variable est `pente`, remplie
par `terrain._pente_lidar` → `profil_altimetrique._completer_ign`, un appel **réseau IGN** (httpx, timeout
20 s, dégradation silencieuse) qui ne sert QUE sur les emprises dont le raster local a < 2 points (cas de
Saint-André). Sous charge l'appel aboutit pour une analyse et expire pour l'autre → `pente` diffère → le
contrôle apparaît d'un côté seulement. On le neutralise (no-op) : la pente ne dépend plus que du raster EN
BASE, déterministe. Un appel réseau vivant n'a de toute façon pas sa place dans un test de déterminisme.

- **Aucun comportement nouveau en production** : seuls l'environnement et une dépendance externe de ce test
  sont neutralisés (monkeypatch, restauré en fin de test). Le code de production est inchangé (seul
  `tests/test_etude_fiable_1.py` change).
- **Reste un vrai test** : pas de skip, pas de réessai, pas d'assertion affaiblie. Les deux assertions
  annoncées (résultat identique ; recherche `complete` avec `candidats_examines == candidats_prevus`) sont
  vérifiées de façon déterministe. La pente passe « non disponible » (raster local seul) et le contrôle de
  relief disparaît du payload — c'est un enrichissement réseau, non reproductible sans fixture enregistrée ;
  cela n'affecte ni la capacité servie ni les assertions.

---

## 3. Autres tests dépendant du même garde-fou / d'une horloge

Candidats examinés (ceux cités aujourd'hui + balayage de tout le suite sur `monotonic`/`perf_counter`/
assertions de durée) :

| Test | Dépendance | Même cause que R2 ? | Action |
|---|---|---|---|
| `test_etude_fiable_1::test_r3_garde_fou_force_recherche_partielle` | force `GARDE_FOU_S=1` | **Non** — force la coupe de façon déterministe ; la charge ne change pas le verdict | inchangé |
| `test_etude_plafond_1` (`GARDE_FOU_S=0.01`, `_ENVELOPPE_CALCUL_S=0`, et tests purs de `_etat_recherche`) | force le filet / fonction pure | **Non** — coupe forcée déterministe | inchangé |
| `test_etude_v6_capacite::test_sous_sol_etude_rapide` | `assert monotonic()-t < 30.0` | **Non** — assertion de **durée** (SLA de rapidité), pas un résultat non-déterministe | inchangé |
| `test_ops_nuit_2` (dont la « vigie » `test_vigie_ne_crie_pas_retrecie_pendant_ecriture`, « jamais réussi », etc.) | `datetime.now()` pour l'ÂGE des dumps/jobs | **Non** — horodatages injectés/relatifs, déterministes quelle que soit la charge | inchangé |
| `test_sentinelle` (veille sources, témoins, rappels) | horodatages de fraîcheur/millésime injectés | **Non** — fixtures déterministes, aucune durée d'exécution mesurée | inchangé |

**Conclusion :** un seul test relevait de la cause R2 (le filet de temps de la grille rendant un
RÉSULTAT dépendant de la charge) — `test_r2` lui-même. Les autres ou bien forcent le filet de façon
déterministe, ou bien mesurent un âge de donnée / une durée SLA : causes distinctes, non touchées.

---

## 4. Le défaut produit lui-même reste ouvert

Le fait qu'une recherche puisse rendre un résultat MOINDRE (recherche « partielle ») sur une machine
chargée — c.-à-d. un résultat servi qui dépend de la charge de la machine — n'est PAS corrigé ici et
relève du chantier « capacité maximale » ; ce correctif ne porte que sur la fiabilité du test.

---

## 5. Preuve — `test_r2` lancé 10 fois pendant qu'une suite complète tourne en parallèle

Jusqu'à trois suites complètes (7148 tests chacune) bouclées en continu en arrière-plan (xdist absent du
venv → process `pytest tests/` concurrents), plus la charge d'autres utilisateurs de la machine partagée.
`test_r2` lancé **10 fois de suite** pendant ce temps — **10/10 réussites**, sur une plage de charge de
6 à 28 (load average 1 min), c.-à-d. en incluant et en dépassant le pic de 16,8 qui faisait tomber le test
non corrigé.

| Run | Verdict | Durée | load avg (1 min) |
|---|---|---|---|
| 1 | PASS | 168 s | 6,2 |
| 2 | PASS | 265 s | 9,5 |
| 3 | PASS | 202 s | 7,6 |
| 4 | PASS | 176 s | 8,1 |
| 5 | PASS | 195 s | 7,6 |
| 6 | PASS | 191 s | 6,8 |
| 7 | PASS | 343 s | **28,0** |
| 8 | PASS | 733 s | **22,2** |
| 9 | PASS | 590 s | **24,0** |
| 10 | PASS | 808 s | **25,1** |

**10 PASS / 0 FAIL.** Les runs 7–10 tournent sous charge 22–28 (bien au-dessus du 16,8 qui déclenchait la
divergence réseau sur le test seulement corrigé du filet temps) : les deux entrées neutralisées tiennent.

Rappel de contraste : AVANT tout correctif, un seul run (deux analyses) échouait en 373 s sous charge ~13
(divergence « candidats écartés »). Après le seul correctif du filet temps, 9/10 (le 10ᵉ échec = réseau IGN
sous charge 16,8). Après neutralisation des DEUX entrées, 10/10 jusqu'à charge 28.

Base applicative `labuse` en **lecture seule** (`etudier_payload` ne commit jamais ; la session témoin
n'est jamais committée).
