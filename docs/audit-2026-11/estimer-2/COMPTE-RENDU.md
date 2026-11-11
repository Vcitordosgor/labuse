# ESTIMER-2 — un prix de secteur honnête, mesuré

**Branche** `fix/estimer-2` · worktree `~/Desktop/labuse-estimer2` · ports 10050/7250 · base locale `labuse`
(DVF arrêté au 31/12/2025). **Calcul et API seulement — aucun fichier du front touché. Pas de merge,
aucun accès prod.** Date : 10/11/2026. Fait suite à l'audit [ESTIMER-AUDIT-1](../estimer-1/RAPPORT.md).

> Ce compte-rendu remplace celui de la première passe ESTIMER-2 (total maison / nature / fiabilité par
> bien, commit `ee1628baf`) : il en reprend les acquis et traite les six points du mandat de correction.

Chaque correction est **mesurée** : le rétro-test no-leak de l'audit devient un **banc permanent**
(`src/labuse/pige/banc_estimer.py`), rejoué ici pour chiffrer l'avant / après, et chaque nuit en
production pour alerter d'une régression.

---

## Le verdict en une page

| Mesure (rétro-test no-leak, ventes 2025) | AVANT (audit estimer-1) | APRÈS (estimer-2) |
|---|---|---|
| **Maison** — écart médian du total · part à ±20 % · sans prix | 29,2 % · 34 % · 0 % | **26,7 %** · **41,2 %** · 0,5 % |
| **Terrain** — écart médian · part à ±20 % · **sans prix** | 27,0 % · 40 % · **20,5 %** (41/200) | 35,1 % · 34 % · **0 %** |
| **Appartement** — écart médian · part à ±20 % · sans prix | *non mesuré* | **12,6 %** · 69 % · 0 % |

- **La maison gagne ~2,5 points d'écart médian et +7 points de « ±20 % »** grâce à la surface habitable
  déduite du **nombre de niveaux mesuré** (hauteur LiDAR) au lieu d'un ratio communal plat.
- **Le terrain ne laisse plus AUCUNE parcelle sans prix** quand la commune a des ventes (20,5 % → 0 %)
  grâce au **rayon adaptatif + repli commune**. L'écart médian **monte** (27 % → 35 %) : c'est attendu et
  honnête — on chiffre désormais aussi les **20 % de terrains les plus difficiles** (sections sans ventes,
  repli commune hétérogène) qui étaient simplement laissés vides. Leur **fourchette mesurée est large et
  leur fiabilité « Limitée »** (point 5) : on sert un repère, en disant son incertitude, plutôt que rien.
- **L'appartement est désormais mesuré** (12,6 % d'écart médian, 69 % à ±20 %) : le type le plus fiable de
  DVF (surface Carrez connue).

Les planchers d'erreur de DVF (maison ~24-27 %) **restent** : aucune méthode ne les franchit (l'audit l'a
montré, GBM compris). Le mandat ne vend donc pas une fausse précision — il **mesure** l'incertitude et la
**sert** (fourchette + fiabilité par commune/type).

---

## 1 — « Dernière vente » : le libellé dit la vérité (2014 → aujourd'hui)

**Avant** : l'outil lisait `dvf_mutations_parcelle` (géo-DVF **2021-2025 seulement**) ; une parcelle vendue
en 2017 et pas depuis était affichée **« aucune depuis 2014 »** — faux pour **37 488 parcelles** (l'audit
en annonçait 38 503) dont la vente 2014-2020 dort dans `dvf_mutations_histo` (110 477 lignes, jamais lues).

**Après** : nouveau lecteur UNIQUE `pige.api.derniere_vente_parcelle` qui **UNIONne** l'historique Etalab
2014-2020 et le géo-DVF 2021+ (les deux tables partagent les colonnes utiles), et renvoie la vente la
**plus récente** quelle que soit son époque, avec sa nature et sa surface.

- La **nature du bien** (maison / appartement / terrain) est désormais lue sur tout l'historique.
- Le libellé servi à l'écran et au PDF : la **vraie date** de la dernière vente ; « aucune depuis 2014 »
  **seulement si c'est vrai** (aucune mutation 2014→aujourd'hui). Côté fiche (lecteur partagé `app.py`),
  un **repli** ne se déclenche que si la vue géo-DVF 2021+ est vide → on n'écrase **jamais** une valeur
  déjà servie (le géo-DVF est toujours plus récent) : **zéro régression de cohérence**.
- Les **ventes groupées** (DVF porte la valeur sur la mutation entière) sont signalées `multi_parcelles`
  et leur **prix au m² supprimé** (on ne divise pas un prix multi-lots par une seule parcelle).
- La table historique peut être **absente** (base de test / déploiement sans historique) : l'UNION ne la
  joint que si `to_regclass` la trouve — jamais de 500.

**Mesuré** : sur 500 parcelles « vendues 2014-2020, jamais depuis », **500/500** portent désormais leur
vraie date (au lieu de « aucune depuis 2014 »). *(test `test_derniere_vente_couvre_lhistorique_2014`)*

## 2 — La médiane PONDÉRÉE servie partout, un seul lecteur

**Avant** (audit §4-e) : la médiane pondérée par la ressemblance était **calculée puis jetée** —
`comparateur_bien` la remplaçait par la médiane **simple** de `reference_locale` pour le chiffre servi.

**Vérifié avant de servir** (condition de l'audit : « revérifier le gain hors échantillon ») — banc no-leak :

| €/m² (sans fuite) | SIMPLE | PONDÉRÉE |
|---|---|---|
| Maison — écart médian · ±20 % | 24,7 % · 44 % | **23,0 %** · **45 %** |
| Appartement — écart médian · ±20 % | 14,4 % · 66 % | **13,7 %** · **68 %** |

La pondérée **tient son gain** (jamais pire, légèrement meilleure). On la **sert** donc, par **un seul
calcul** : `faisabilite.bilan._mediane_ponderee` est appelé par `sector_price` (fiche / Dossier / bilan)
ET par `reference_locale` (Estimer / Radar), sur le **même échantillon** → une seule valeur.

- Poids = **ressemblance** (distance au centroïde, écart de surface au bien, écart de terrain pour la
  maison, ancienneté). Pas de ré-indexage de dérive : on repondère des prix **observés**.
- La surface du sujet pour pondérer est **intrinsèque** à la parcelle (sa dernière surface bâtie DVF),
  **jamais** la saisie utilisateur → le €/m² servi ne dépend pas de ce que tape l'utilisateur :
  **fiche == Estimer == PDF**.
- **Banc des documents : VERT — 0 écart** (témoins rejoués, 30 documents) ; suite de cohérence 6/6.
  *(tests `test_mediane_servie_identique_fiche_et_estimer`, `test_mediane_ponderee_est_un_vrai_quantile_pondere`)*

## 3 — Le terrain reçoit le moteur adaptatif du bâti

**Avant** (audit §4-c) : repère terrain pris sur la table pré-agrégée par **section cadastrale**,
**sans rayon ni repli** → **1 terrain sur 5 sans prix**.

**Après** : `marche_service.comparateur_terrain` applique le **même moteur que le bâti** — rayon
**500 → 1000 → 1500 m** (≥ 8 ventes), puis **repli commune**. Le repère servi porte sa **médiane**, son
**n** et son **périmètre retenu** (rayon réel ou « commune »).

**Mesuré** : chaque commune de la Réunion a ≥ 76 ventes de terrain → le repli commune garantit **0 % sans
prix**. Couverture d'un échantillon **140/150 → 150/150** ; sur le banc, **0 terrain sans prix** (contre
20,5 %). *(tests `test_terrain_rayon_adaptatif_*`)*

## 4 — Surface habitable = emprise × niveaux mesurés (hauteur LiDAR)

**Avant** (audit §4-a) : la surface du total maison était presque toujours **devinée** par `emprise ×
ratio communal` (ratio plat, identique pour un plain-pied et un R+1).

**Après** : on lit le **nombre de niveaux mesuré** par la hauteur d'égout **LiDAR**
(`batiment_hauteur_lidar`, `max(1, round(égout / 3 m))`), hypothèse servie **en clair** : *« Surface
habitable estimée : 140 m² au sol × 2 niveaux (hauteur LiDAR) »*.

**Mesuré, et honnête sur la formule** : sur 15 213 ventes de maisons (surface DVF + emprise + égout LiDAR),
la surface habitable **ne double pas** avec un 2ᵉ niveau — médiane `surface/emprise` = **0,50 à 1 niveau,
0,60 à ≥ 2**. `emprise × niveaux` **brut surestimerait ~×2**. On garde donc le **ratio communal mesuré**
comme base et on l'ajuste du seul **effet niveaux mesuré** (×0,97 à 1 niveau, ×1,17 à ≥ 2 — multiplicateurs
mesurés, recalibrables au banc). Sans LiDAR (~8 % micro-bâti) → **ratio communal seul** (le « à défaut »).

Résultat (banc) : maison, écart médian du total **29,2 % → 26,7 %**, part à ±20 % **34 % → 41,2 %**.
*(tests `test_surface_emprise_niveaux_lidar_*`)*

## 5 — La marge d'erreur MESURÉE remplace le ±30 % fixe

**Avant** : fourchette **±30 % FIXE** (`estimation_prix.py`) pour la valeur du terrain ; bandes de
fiabilité **figées par type** pour l'Estimer.

**Après** : la fourchette et la fiabilité servies viennent du **banc**, par **commune et par type** :

- la **fourchette** servie = l'**écart Q3 mesuré** (bande honnête qui enferme ~75 % des ventes) ;
- la **fiabilité** (Élevée / Moyenne / Limitée) découle de l'**écart médian mesuré + du nombre de ventes** ;
- repli commune → île du banc ; **aucune calibration** (banc jamais passé / base de test) → bande
  historique, jamais de 500.

La table `estimer_precision_calibration` est écrite chaque nuit par le banc et **lue au service**
(`banc_estimer.charge_calibration`). Le ±30 % fixe de `estimation_prix.fourchette` est remplacé, là où
l'appelant connaît la commune (valeur du terrain du bilan, projection Copilote), par la demi-largeur
mesurée. *(tests `test_fiabilite_servie_vient_de_la_calibration_mesuree`, `test_fourchette_mesuree_*`)*

Exemple servi : maison secteur 97416 → **± 42 %** (= Q3 mesuré de la commune), fiabilité **« Limitée »**
(écart médian mesuré 31 %), au lieu d'un ±26 % figé qui sur-promettait.

## 6 — Le rétro-test devient un banc permanent de nuit

`src/labuse/pige/banc_estimer.py` rejoue, **sans fuite**, **200 maisons + 200 terrains + 200 appartements**
(comparables strictement antérieurs, mutation jugée exclue). Il produit l'avant/après par type et **par
commune**, et **écrit la table de calibration servie** (point 5).

Le job de nuit **`estimer-banc-precision`** (registre `jobs.py`, 04:30 Réunion) le rejoue chaque nuit,
persiste la calibration, et **échoue → mail admin** si la précision se **dégrade** (écart médian +≥ 5 pts
ou part sans prix +≥ 5 pts) vs le dernier banc vert. *(tests `test_estimer2_banc.py`)*

### Après, par commune (banc 200/type)

**Maison** — écart médian · ±20 % :
`97413 11,4 %·75 %` · `97408 11,7 %·56 %` · `97422 14,6 %·59 %` · `97415 25,9 %·42 %` ·
`97414 27,4 %·33 %` · `97416 30,9 %·30 %` · `97411 31,8 %·44 %` · `97412 41,2 %·20 %`.

**Terrain** — écart médian · ±20 % (tous à 0 % sans prix) :
`97404 25,8 %·50 %` · `97415 31,6 %·29 %` · `97411 35,2 %·21 %` · `97408 36,1 %·46 %` ·
`97416 43,3 %·26 %` · `97422 51,8 %·32 %` · `97414 63,2 %·10 %`.

La dispersion commune-à-commune (du simple au triple) est **réelle** : c'est pourquoi la fourchette servie
est désormais **par commune** (point 5), pas un ±30 % unique.

---

## Ce qui est vérifié vert

- **Hook** : famille Python unitaire **3 240 passed, 0 failed** ; scan de secrets OK ; suite de
  **cohérence 6/6** ; **banc des documents VERT — 0 écart** (la médiane pondérée servie partout
  n'introduit aucune divergence inter-documents).
- **Tests ESTIMER-2** : `tests/test_estimer2.py` (11) + `tests/test_estimer2_banc.py` (6) verts (base
  réelle) ; registre des jobs, horloges, familles, graphe des lecteurs fins tous verts.
- Front **non touché** (mandat) ; les libellés servis changent par la **donnée servie** (dernière vente
  véridique, hypothèse de surface en clair), pas par le code du front.

## Fichiers

| Fichier | Rôle |
|---|---|
| `src/labuse/pige/api.py` | `derniere_vente_parcelle` (union 2014→), `_niveaux_lidar_parcelle`, surface niveaux, fiabilité/fourchette mesurées, repère terrain adaptatif |
| `src/labuse/marche_service.py` | `comparateur_terrain` adaptatif (médiane + n + périmètre) |
| `src/labuse/faisabilite/bilan.py` | `_mediane_ponderee` (lecteur unique pondéré) ; `sector_price` / `reference_locale` servent la pondérée |
| `src/labuse/estimation_prix.py` | `fourchette()` accepte la demi-largeur **mesurée** (remplace ±30 % fixe) |
| `src/labuse/pige/banc_estimer.py` | **banc permanent** no-leak + persistance de la calibration + lecteur servi |
| `src/labuse/jobs.py` · `jobs_impl.py` | job de nuit `estimer-banc-precision` + alerte régression |
| `src/labuse/api/app.py` · `copilote_v2/missions_lourdes.py` | repli « dernière vente » historique ; fourchette terrain mesurée |
| `src/labuse/registre/lectures.py` | déclaration fine des nouvelles lectures (graphe des lecteurs) |
| `tests/test_estimer2.py` · `tests/test_estimer2_banc.py` | recette des 6 points |
| `docs/audit-2026-11/estimer-2/METRIQUES.json` | mesures du banc (global / type / commune / calibration) |

**Rejouer le banc** :
`LABUSE_DATABASE_URL=postgresql+psycopg:///labuse ~/Desktop/labuse/.venv/bin/python -m labuse.pige.banc_estimer`
(PYTHONPATH=src).
