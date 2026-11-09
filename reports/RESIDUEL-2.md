# RESIDUEL-2 — plus de repli non qualifié, plus de double retrait

**Branche** `fix/residuel-2` (worktree `~/Desktop/labuse-residuel2`). **Aucun merge, aucun accès
production.** Calcul et API seulement ; **zéro fichier du front touché**. Instantané de travail : run
servi **q_v20** (base locale, 433 229 parcelles ; `residuel_runs.is_served = run_seq 17`).

Références lues d'abord (worktree `labuse-algofix`) : `COMPTE-RENDU.md` §6-bis, `DOUBLE-RETRAIT.md`,
`AVIS-ASTRA-ALGO-FIX-1.md` §2, `AVIS-ASTRA-ALGO-FIX-1-PASSE-3.md` §4.

Ce mandat ferme trois trous laissés ouverts par ALGO-FIX-1, **au niveau du moteur** (ce qu'Astra
rangeait « hors du mandat isolé ») : (1) qualifier ou résorber le repli `residuel_legacy` ; (2)
corriger et **mesurer exactement** le double retrait ; (3) faire entrer la reconstruction
(C_rebuild/E/D_net) dans le run et **prouver qu'elle tient dans la nuit**.

---

## 1. Les 53 923 parcelles en repli — pourquoi, et quoi en faire

`assiette_source = residuel_legacy` = le moteur **gabarit** (reculs par côté, PPR rouge découpé) ne
sert pas la parcelle ; le calcul retombe sur la branche **legacy** (inset uniforme au recul
séparatif ∩ portion U/AU − contraintes certaines). Au run servi : **53 923** parcelles (42 539 avec
R > 0, 27 027 servies comme capacité).

### 1.1 Classement par cause (rejeu de `build_gabarit_input` + `compute_gabarit`, échantillon md5 2 500)

| Cause de non-service du gabarit | part éch. | ≈ île | décision RESIDUEL-2 |
|---|---:|---:|---|
| **Limites non qualifiées** (arête sans voie ni voisin : ravine / littoral / DPF non routier) | 50,0 % | ~26 983 | **repli QUALIFIÉ** — pas de voie sur l'arête → l'inset séparatif uniforme + l'union des contraintes applique les règles du cas ; marqué `residuel_legacy_qualifie`. *(Exception : si l'arête non classée est une **voie privée**, le motif reste « Limites… » mais c'est un recul deviné → NON qualifié, cf. §1.3.)* |
| **recul sur voie non réglementé** | 14,6 % | ~7 851 | **non qualifié** — recul voie deviné (souvent > séparatif) peut gonfler la capacité |
| **PLU non calibré pour la zone** (Uavap, A, N, AUS…) | 9,7 % | ~5 220 | **non qualifié** — règles CES/hauteur génériques, pas la géométrie |
| **gabarit OK aujourd'hui** (incohérence de run) | 9,2 % | ~4 982 | **gabarit** — le run q_v20 est périmé ; un recompute (q_v23) les sert en `gabarit` |
| **desserte : pas de façade sur voie** (voie privée) | 7,1 % | ~3 839 | **non qualifié** — recul voie privée non réglé |
| **multi-zones : morceau non isolable** | 4,2 % | ~2 243 | **non qualifié** — une seule CES appliquée à toute la portion U/AU |
| **emprise (CES) non réglementée** | 2,2 % | ~1 208 | **non qualifié** — CES manquant |
| **compute_gabarit incomplet** | 2,1 % | ~1 122 | **non qualifié** |
| zone sans règles d'implantation · A/N dominante · hauteur non validée | < 1 % | ~475 | **non qualifié** |

### 1.2 La règle de qualification (preuve, pas absence de contrainte)

Astra §2 : « un repli peut être recevable si l'on prouve qu'il traite correctement les règles
applicables ; l'absence de PPR rouge/EBC dans les motifs n'apporte pas cette preuve. »

La preuve **existe par construction** pour un seul motif. Dans `build_gabarit_input`, l'étape
limites/géométrie n'est atteinte **que si** `not blocking` (PLU complet et unique) : zone
constructible **calibrée**, CES **et** hauteur **connus**. Le seul point ouvert est alors une **arête
non classable** (ravine / littoral / DPF non routier / micro-arête de numérisation). Sur une telle
arête il n'y a **pas de voie** dont le recul (souvent supérieur au séparatif) serait sous-appliqué :
l'inset uniforme au recul séparatif **+** l'union globale des contraintes certaines est une assiette
**correcte et conservatrice** (jamais gonflée). → `residuel_legacy_qualifie`.

Tout autre motif implique une **règle devinée** pouvant gonfler la capacité (recul voie, voie privée,
PLU non calibré, CES/hauteur absents, multi-zones) → **`residuel_legacy`** (non qualifié, capacité
provisoire « estimation simplifiée » — le badge client est inchangé).

Implémentation (`faisabilite/db.py`) : `_assiette_gabarit` renvoie désormais `(gab, blocages)` ; la
qualification est décidée par `_repli_qualifiable(blocages)` (True ssi **tous** les motifs sont
« Limites de la parcelle non qualifiées »). Le marquage est écrit dans `assiette_source`. Les deux
consommateurs client (`app.py`, `pige/api.py`) lisent `startswith("residuel_legacy")` → le libellé
« estimation simplifiée » reste porté par **les deux** variantes (la géométrie reste un inset
simplifié) ; la **qualification** est portée par `assiette_source` pour la couche de scoring / q_v23.

### 1.3 Répartition réelle (échantillon exact 1 500, batch ≡ fiche, `compute_residuel` live)

| `assiette_source` (code servi RESIDUEL-2) | part | ≈ île |
|---|---:|---:|
| `residuel_legacy_qualifie` (repli PROUVÉ) | 50,0 % | **~26 962** |
| `residuel_legacy` (non qualifié → provisoire) | 40,1 % | **~21 641** |
| `gabarit` (run périmé → servable au recompute) | 9,7 % | **~5 213** |
| non constructible (None) | 0,2 % | ~108 |

**Lecture.** Après RESIDUEL-2, sur les 53 923 ex-« repli », **~5 213 passent au gabarit** (simple
recompute), **~26 962 sont un repli QUALIFIÉ** (règles prouvées appliquées, source qualifiée), et il
reste **~21 641 capacités d'assiette NON qualifiées** (provisoires, « à vérifier » côté scoring —
détail §1.4). Objectif du mandat atteint : **toute capacité servie porte désormais une source
qualifiée ou le marqueur explicite de non-qualification** — plus aucune capacité servie sans source
qualifiée par défaut.

**Piège corrigé** : un repli dont l'arête non classée est une **voie privée** (`MOTIF_VOIE_PRIVEE`)
produit aussi un motif « Limites de la parcelle non qualifiées — … voie privée », mais c'est un
**recul deviné**, pas une arête naturelle. `_repli_qualifiable` exclut donc explicitement
« voie privée » (les motifs bénins ne contiennent jamais cette sous-chaîne) → ces ~1 900 parcelles
restent NON qualifiées (test `test_repli_qualifiable_*`).

### 1.4 Les ~21 641 non qualifiées — par motif, et ce qu'il faudrait (sans le faire)

Échantillon md5 de 3 500 legacy, rejeu du builder, buckets sur le 1er motif non bénin (NON qualifiés
mesurés : 1 408 / 3 500 → **≈ 21 692** île, cohérent avec le 40,1 % de §1.3) :

| motif de non-service | part | ≈ île | exemple | pour SERVIR au gabarit / QUALIFIER (sans le faire) |
|---|---:|---:|---|---|
| **recul sur voie non réglementé** | 35,7 % | ~7 734 | `97410000AW0630` | **Donnée** : calibrer le recul sur voie de la zone au règlement (`recul_voirie_m`). Non qualifiable : l'inset uniforme applique le recul *séparatif* sur l'arête voie, souvent **< recul voie réel → emprise gonflée**. |
| **PLU non calibré pour la zone** (Uavap, A, N, AUS…) | 24,1 % | ~5 223 | `97411000AH0360` | **Donnée** : calibrer les règles de la zone (CES, hauteur, reculs). Inventer des valeurs génériques est proscrit (doctrine « jamais une valeur servie inventée »). |
| **desserte : voie privée** (recul non réglé) | 17,9 % | ~3 882 | `97412000BM1113` | **Règle** : fixer le recul sur voie privée au règlement, ou prouver que le séparatif s'y applique. Tant que c'est deviné → non qualifiable (même risque que le recul voie). |
| **multi-zones : morceau non isolable** | 10,2 % | ~2 203 | `97405000AI1185` | **Moteur** : outiller le gabarit pour isoler et calculer SÉPARÉMENT chaque morceau constructible (CES/hauteur propres) puis sommer. Aujourd'hui une seule CES sur toute la portion U/AU = faux. |
| **emprise (CES) non réglementée** | 5,2 % | ~1 125 | `97415000EI0173` | **Donnée** : renseigner le CES de la zone au règlement. |
| **compute_gabarit : incomplete** | 4,8 % | ~1 048 | `97403000AS1759` | **Moteur/Donnée** : diagnostiquer au cas par cas la donnée manquante en aval (géométrie d'implantation, hauteur, raccordement). |
| **zone sans règles d'implantation propres** (ex. UF) | 1,0 % | ~216 | `97405000AR0807` | **Règlement** : la zone ne fixe NI recul NI hauteur NI emprise (renvoi non résolu / silence) → résoudre le renvoi réglementaire. |
| **A/N dominante** (sous-zone U/AU non calibrée) | 1,0 % | ~216 | `97403000AM0438` | **Donnée** : calibrer la sous-zone U/AU minoritaire → **deviendrait qualifiable** (le repli clippe déjà à la portion). |
| **hauteur réglementaire non validée** | 0,2 % | ~46 | `97408000AN0447` | **Donnée** : valider la hauteur réglementaire de la zone. |

**Synthèse.** ~**85 %** des non qualifiées tiennent à un **CALIBRAGE PLU manquant** (recul voie, voie
privée, CES, hauteur, zone/sous-zone non calibrée, renvoi non résolu) : le projet **interdit d'inventer
la valeur** → elles restent honnêtement « estimation simplifiée, non qualifiée » jusqu'au calibrage du
règlement. Un seul groupe (**multi-zones, ~2 203**) relève d'un **développement MOTEUR** (isoler les
morceaux constructibles). **Aucune** ne peut être qualifiée par la géométrie du repli : c'est la
**règle de capacité elle-même** qui manque ou est devinée, pas l'assiette. Ce travail de calibrage/
moteur est délibérément **laissé hors de RESIDUEL-2** (le mandat marque et isole, il n'invente pas).

---

## 2. Double retrait — correction (union globale) + mesure exacte

### 2.1 Le défaut et le correctif

La branche legacy soustrayait **séparément** `union(ER, EBC)` (`greve_a`, requête `_EMPRISE`) **puis**
`union(PPR rouge, PEB A/B, DPF, ravine, 50 pas)` (`greve_cert`, `_GREVE_CERTAINE`) :

```
emprise = base − greve_a          (_EMPRISE)
emprise = emprise − greve_cert    (_GREVE_CERTAINE)   ← là où ER∪EBC ∩ cert ≠ ∅, retranché 2×
```

Correctif (`_GREVE_LEGACY_UNION`, miroir exact de `_GREVE_SUR_ASSIETTE` du chemin gabarit) : **une
seule union de TOUTES les contraintes certaines**, intersectée **une fois** avec l'assiette —
`emprise = base − greve_total`. Les composantes ER/EBC/cert restent retournées pour l'affichage (elles
peuvent se chevaucher) ; seule l'**union** est soustraite. Contraintes **hors PPR incluses** (ER, EBC,
PEB, DPF, ravine, 50 pas). Là où les ensembles sont disjoints, `greve_total = greve_a + greve_cert` à
l'octet près → **résultat identique** (zéro régression) ; là où ils se recouvrent, l'emprise **ne peut
qu'augmenter** (jamais diminuer) — propriété verrouillée par test (`test_union_jamais_moins_que_double_retrait`).

### 2.2 Mesure d'impact RÉELLE — sur l'assiette exacte, avec les filtres du moteur

Méthode exacte (seam de mesure `legacy_union=False`, qui rejoue l'ancien double retrait avec les
MÊMES rules/plafonds/hypothèses) : pour chaque parcelle, `parcel_faisabilite` OLD vs NEW →
`compute_residuel` → emprise, C (sdp_max), E (inchangé), R OLD/NEW. On sépare **augmentation
géométrique** / **capacité inchangée après plafonds** / **résiduel redevenu positif**.

*Premier passage* — échantillon aléatoire md5 de 1 500 legacy : emprise augmentée = **6 / 1 500
(0,4 %, ≈216 île)**, 0 verdict changé. Un tirage aléatoire ne touche que ~199 des 7 160 candidates et
**manque les cas rares** (les 13 faux zéros) : d'où la mesure exhaustive ci-dessous, qui est
l'autorité.

**Population touchable complète (AUTORITÉ)** — toutes les **7 160** legacy porteuses d'ER/EBC
(surensemble strict de l'ensemble touché : le double retrait exige ER/EBC **et** une contrainte
certaine qui se recouvrent sur l'assiette), mesurées **exactement** (pas d'échantillon, 1 209 s) :

| effet (île entière, exact) | parcelles |
|---|---:|
| emprise augmentée (double retrait levé) | **211** |
| C (sdp_max) augmentée | 221 |
| **R (capacité servie) change** | **172** (toutes en hausse, jamais baisse) |
| **R redevenu POSITIF (faux zéro corrigé)** | **13** |
| surface doublement soustraite (somme) | 79 120 m² (moy/touchée 375 m²) |

**Les 13 parcelles dont le VERDICT change** (R : 0 → positif) :
`97404000AZ0147`, `97404000AZ0155`, `97404000AZ0169`, `97408000BN0088`, `97410000AB0242`,
`97411000BZ0021`, `97411000BZ0922`, `97411000CL0273`, `97411000CR0250`, `97411000DK0047`,
`97411000DK0395`, `97411000DK0458`, `97412000BP0225`. Script : `scripts/residuel2_double_retrait_exact.py`.

**Conclusion.** L'exposition « 8,7 % → ≈4 709 parcelles touchées, ≈1 078 faux zéros » de
`DOUBLE-RETRAIT.md` était un **majorant grossier** (parcelle entière, sans reculs, toutes
prescriptions — critiqué par Astra §4). Mesuré **exactement sur l'assiette clippée avec les filtres du
moteur**, l'impact réel est **deux ordres de grandeur plus petit** : **172** parcelles voient leur
capacité **augmenter** (jamais baisser), dont **13 vrais faux zéros corrigés** (≈1 078 estimés → **13
réels**). Le correctif est **juste** (fin du double compte) et son effet servi est **ciblé et
honnête** — le double retrait ne vidait presque aucune assiette réelle, mais les 13 faux zéros qu'il
créait sont désormais rétablis.

---

## 3. Reconstruction île entière (C_rebuild, E, D_net) dans le run — et la nuit

### 3.1 Le calcul entre dans le run, et est PERSISTÉ

`compute_residuel` produit déjà, par parcelle, **C = sdp_max** (capacité sur terrain libéré =
C_rebuild), **E = sdp_existante** et donc **D_net = C − E SIGNÉ** (négatif quand la démolition perd de
la SDP). Jusqu'ici seul **R** était persisté (l'algo-fix V2 en souffrait : reconstruction « Calcul à
compléter » partout sauf 2 communes enrichies). RESIDUEL-2 **persiste** C/E/D_net : trois colonnes
**additives** `sdp_max_m2, sdp_existante_m2, d_net_m2` sur `parcel_residuel_runs` (même garde
catalogue « ALTER seulement si la colonne manque » que `surface_terrain_m2` → aucun ACCESS EXCLUSIVE
no-op au boot) + la vue `parcel_residuel` (ajout en fin de liste, `CREATE OR REPLACE`). Écrites par
`compute_residuel_batch`. Vérifié sur témoins (scratch run purgé) : AM0314 **D_net = −27**, AM0473
**D_net = −248** (saturées, gain signé négatif) ; EH0043 **D_net = +44 117**.

### 3.2 Temps mesuré → tient dans la nuit

`compute_residuel` chronométré (avec le correctif union) sur échantillon réglier de 3 communes :

| commune | ms / parcelle | débit mono |
|---|---:|---:|
| Entre-Deux (contraintes lourdes) | 72 ms | 13,8 p/s |
| Le Port (urbain) | 73 ms | 13,8 p/s |
| Saint-Denis (grande, mixte) | 92 ms | 10,9 p/s |

**Extrapolation île (433 229), pire cas ~85 ms/parcelle** : mono-cœur ≈ **8,7 h** ; **4 shards**
(mécanique existante `residuel_shard.sh`, communes disjointes, rendement DB-bound ~76 %) ≈ **2,9–3,6 h
→ TIENT** dans la nuit (budget 8 h). Même 2 shards (~5 h) tiennent. Le correctif union est
**neutre en coût** : il **remplace** l'appel `_greve_certaine_m2` par `_GREVE_LEGACY_UNION` (même
ordre de grandeur), il n'en ajoute pas.

---

## 4. Témoins — batch ≡ fiche (base réelle q_v20)

`parcel_faisabilite` (NEW, union servie) vs OLD (double retrait), `compute_residuel` ; emprise, C, E,
R ; `assiette_source` RESIDUEL-2.

| IDU | source (NEW) | emp_old | emp_new | C | E | R | note |
|---|---|---:|---:|---:|---:|---:|---|
| 97411000EH0043 | gabarit | 49 026 | 49 026 | 44 123 | 6 | 44 117 | gabarit (double retrait sans effet) |
| 97411000EI0085 | **residuel_legacy** | 14 417 | 14 417 | 12 976 | 1 608 | 11 368 | multi-zones (AUm,Um) → non qualifié (sous-découpe connue) |
| 97403000AL0258 | — (non constr.) | — | — | — | — | 0 | contour très découpé (compacité 0,11) |
| 97415000DH0076 | gabarit | 13 659 | 13 659 | 30 733 | 4 475 | 26 258 | Saint-Paul, PPR rouge partiel 2 % — constructible hors rouge (Étude ~48 logts) |
| 97411000BZ1065 | gabarit | 470 | 470 | 212 | 177 | 35 | Uh bâtie |
| 97409000AK0804 | gabarit | 19 024 | 19 024 | 34 243 | 20 | 34 223 | Saint-André, nue en zone U |
| 97403000AM0314 | **residuel_legacy_qualifie** | 105 | 105 | 142 | 169 | 0 | saturée, **D_net −27** |
| 97403000AM0473 | **residuel_legacy_qualifie** | 122 | 122 | 109 | 357 | 0 | saturée, **D_net −248** |
| 97403000AM0561 | **residuel_legacy** | 165 | 165 | 148 | 289 | 0 | PLU non calibré zone N → non qualifié |

La qualification distingue **correctement** : AM0314/AM0473 (arête naturelle seule) **qualifiés** ;
AM0561 (PLU N non calibré), EI0085 (multi-zones) **non qualifiés** ; EH0043/DH0076/BZ1065/AK0804
servis par le **gabarit** (le double retrait est sans effet sur eux : emp_old = emp_new). `batch ≡
fiche` sur les 9 témoins (test `test_batch_egale_fiche_sur_temoins`). Témoins nommés : DH0076 =
`97415000DH0076` (Saint-Paul, PPR rouge partiel 2 %, Étude ~48 logts), AK0804 = `97409000AK0804`
(Saint-André, nue en zone U).

---

## 5. Nombre de parcelles dont la capacité change (bilan)

| Source du changement | parcelles (île) | nature |
|---|---:|---|
| **Double retrait levé** (union globale) | **172** | R augmente légèrement ; **13 verdict change** (0 faux zéro) |
| **Run périmé → gabarit** (recompute q_v23) | **~5 213** | assiette legacy → assiette gabarit réglementaire ; capacité recalculée |
| **Qualification** (`residuel_legacy_qualifie`) | ~26 962 | **métadonnée** (source qualifiée) ; la valeur R **ne change pas** |

La capacité **numérique servie** change pour **~5 213 + 172 parcelles** (dominées par le
recompute du run périmé) ; la qualification de ~26 962 parcelles est un gain de **traçabilité**, pas
de valeur. Aucun changement client-visible sur q_v20 (le run servi reste intact) ; tout prend effet
au **recompute q_v23**.

---

## 6. Tests, banc, hook

- `tests/test_residuel2.py` — **3 unitaires** (qualification pure, contrats de structure, jouées au
  hook) + **19 `reel`** (témoins, batch ≡ fiche, qualification, propriété union ≥ double retrait).
  Tous **verts**.
- `tests/test_residuel1_chemin_unique.py` (invariant batch ≡ fiche) : **8 verts**.
- `tests/test_prospect.py` : mis à jour au nouveau contrat `_assiette_gabarit` (renvoie
  `(gab, blocages)`) + mock `_GREVE_LEGACY_UNION` → **10 verts**.
- **Suite unitaire** (`-m "not db and not local and not reel and not network"`) : **3 202 passed**,
  0 échec (2 prospect réparés).
- **Banc de cohérence** (12 témoins, run servi 17) : **6 passed, 0 écart (1 €/1 m²)**.
- Scan de secrets : rien. `py_compile` : OK. **Zéro fichier du front touché** (0 diff `frontend/`) →
  tsc/vitest intacts par construction (`node_modules` absent de ce worktree, non requis par ce mandat
  back-only). CLI `compute-residuel` validée de bout en bout (C/E/D_net persistés, scratch purgé).

---

## 7. Procédure q_v23 (recompute servi)

1. **Schéma** (idempotent, déjà posé en local) : au boot, `ensure_runs_schema` ajoute
   `sdp_max_m2, sdp_existante_m2, d_net_m2` (NULL sur les runs antérieurs) et rafraîchit la vue.
2. **Run neuf** : `labuse compute-residuel --ile --new-run q_v23` crée le run (non servi, garde-fou
   `assert_writable`). Les colonnes C/E/D_net se peuplent par `compute_residuel_batch`.
3. **4 shards** (nuit, ~3 h) — mécanique existante, communes disjointes, un seul `run_seq` :
   ```
   RS=$(… --new-run q_v23 …)   # le run_seq créé
   psql … "SELECT DISTINCT commune FROM parcels ORDER BY commune" > /tmp/communes.txt
   split -n l/4 /tmp/communes.txt /tmp/shard_
   for L in /tmp/shard_*; do caffeinate -i scripts/residuel_shard.sh $RS $L & done ; wait
   ```
   (⚠ ne pas sur-sharder si la machine swappe : le run est DB-bound.)
4. **Effets attendus** : ~5 213 ex-legacy passent `gabarit` (run frais) ; ~26 962 `residuel_legacy_qualifie` ;
   ~21 641 `residuel_legacy`. Reconstruction (C/E/D_net) servie île entière. Double retrait levé sur
   172 parcelles (R +), 0 faux zéro / 13 verdict.
5. **Vérifs avant bascule** : banc de cohérence (0 écart), comptes par `assiette_source`,
   `batch ≡ fiche` sur témoins, invariants du run.
6. **Bascule** : `labuse residuel-serve <run_seq>` (seule vérité `is_served` ; retour arrière =
   `residuel-serve <ancien>`). Le service historique n'est jamais à moitié.

---

*Fin — `fix/residuel-2`, non mergée, run servi q_v20 intact, Signal intact, zéro accès production.*
