# M42 — PHASE 0 · CONSTAT (voisinage hyper-local & historique permis du site)

**Branche** `m42-voisinage-historique` · base `main` 65f5f314 (M41 mergé). **Nature : LECTURE
SEULE** (seuls fichiers nouveaux `qa/m42/*`). Pas de découverte hors cadre → **pas de STOP** ;
je propose la maille chiffrée et j'enchaîne la Phase 1. Golden/re-mesures/M37 intacts par construction.

Tout est **vérifié sur pièces** (base `labuse`, run servi `q_v8_calibre`).

---

## 1. Sort des branches antérieures `feat/algo3-voisinage` (+ `-v2`)

Les deux branches sont le **même travail « ALGO-3 »** (v2 = reprise sur base saine) : un builder de
voisinage hyper-local explorée comme **FEATURE DE SCORING** (challenger ML). Méthode (lue sur
pièces, `scripts/algo3_voisinage.py`) : centroïde-à-centroïde EPSG:2975, rayons 50/100/200 m, cible
**exclue à deux niveaux** (anti-fuite : soi-même + mutations multi-parcelles où la cible participe),
`as-of` strict pour l'entraînement. Sources : `sitadel_permits` (geom + `idu_codes`) et
`p_model_ext_mut_l2` (DVF). **Verdict final (v2, `ALGO3_RAPPORT.md`) : « NE PAS PROMOUVOIR »** — le
bloc apporte une information nouvelle (colinéarité faible) mais ne justifiait pas un signal de score.

**Conséquence pour M42** : le verdict ne s'applique PAS — M42 n'est **pas** une feature de scoring,
c'est du **contexte fiche** (0 tier). Ce qui est REPRENABLE = la **technique de requête** (linkage
`idu_codes`, buffer centroïde 2975). Ce qui NE l'est PAS = le cadrage ML (as-of, anti-fuite,
exclusion de la cible) — la sémantique fiche est INVERSE : l'historique INCLUT le site, le voisinage
regarde le RÉCENT (36 mois), pas l'as-of. → **on emprunte la méthode, on ne merge pas les branches.**

⚠ **Résidu à consigner** : la branche a laissé **7 tables `algo3_*`** en base
(`algo3_c, algo3_dens, algo3_mut, algo3_pairs_mut, algo3_pairs_permis, algo3_touch, algo3_voisinage`)
— résidu d'une branche non mergée. `algo3_c` (431 663 centroïdes 2975, gist) est commode mais je ne
m'appuierai PAS sur du résidu non mergé en code servi (je calcule proprement). **Recommandé : nettoyage**
(hors périmètre servi).

## 2. Historique des permis du site — riche et rattaché

`sitadel_permits` : **50 292 permis**, `idu_codes` = **tableau jsonb d'IDU** (`["974..."]`), geom sur
39 526 (78 %). Profondeur : **autorisations 2013→2026**, **dépôts 2004→2026** (datation M38, plus
profonde). `pc_caducs` est **rattaché PARCELLE** (`idu`) : 2 164 parcelles, PC 2013-2022.

**Parcelles servies portant ≥1 permis SUR elles** (`idu_codes` contient l'IDU) — le bloc est très
pertinent en tête de classement (`qa/m42/historique_permis_par_tier_p0.csv`) :

| tier | avec permis | total | % |
|---|---|---|---|
| **brûlante** | 116 | 119 | **97,5 %** |
| **chaude** | 563 | 1 041 | **54,1 %** |
| à creuser | 3 348 | 29 974 | 11,2 % |
| réserve foncière | 298 | 2 964 | 10,1 % |

**Caducs sur tiers actifs : 565 parcelles.** Le bloc « Sur cette parcelle » a de la substance
(97 % des brûlantes). Un permis caduc sera **dit caduc, pas masqué** (Phase 2). Sitadel étant
**autorisations-seules** (doctrine M38 : refus/abandons absents de l'open-data), l'historique servi
est « déposé / autorisé / caduc » — jamais « refusé » (on ne le sait pas).

## 3. Voisinage <100 m — maille faisable & coût

**Faisable proprement par buffer métrique centroïde** (EPSG:2975) : DVF via
`dvf_mutations_parcelle` (join centroïde), permis via `sitadel_permits.geom`. Le rattachement par
SECTION serait grossier (sections hétérogènes) ; le buffer centroïde est la bonne maille fine.

**Coût mesuré (mono-parcelle, dense)** : voisinage DVF+permis <100 m sur 36 mois = **~48 ms** ;
historique `idu_codes` = **~10 ms**. Total ajouté ≈ **~58 ms/fiche**. Le goulot = `ST_Transform(geom,2975)`
des permis à chaque requête (pas d'index 2975) + pas de **GIN sur `idu_codes`**. **Optimisations
Phase 1** : GIN(`idu_codes`) → historique <1 ms ; index/precompute geom_2975 des permis → voisinage
plus rapide. Pas de table de pré-calcul lourde nécessaire ; à comparer avant/après (mandat).

## 4. Le piège nommé — distribution dense vs rural

Distribution du nombre de voisins <100 m sur 36 mois (échantillon 800 parcelles servies) :

| | DVF (ventes) | Permis |
|---|---|---|
| moyenne | 3,6 | 0,9 |
| médiane | 2 | 0 |
| max | **125** | 20 |

**22 % des parcelles n'ont AUCUN voisin** (0 vente + 0 permis <100 m/36 mois). Contraste dense/rural
mesuré : **urbain dense 4,4 DVF / 1,1 permis** vs **rural 1,2 / 0,4** (≈ ×3-4). Le piège est réel
(max 125 en poche dense) mais **pas cassant** à 100 m.

**Maille proposée : 100 m FIXE.** Justification chiffrée :
- Le libellé reste **exact et honnête** (« à moins de 100 m »), pas un rayon flou variable.
- Le contraste dense/rural EST une information vraie (un tissu actif vs un secteur calme) — on ne le
  masque pas par un rayon adaptatif.
- **Rural / 22 % vides** : doctrine M38 — **aucun bloc affiché** (« pas de bloc vide »).
- **Poches denses (max 125)** : afficher le COMPTE + prix médian si n≥3 ; ne pas lister 125 lignes
  (compte + médiane, échantillon borné). Écarté : rayon adaptatif (libellé confus), N-plus-proches
  (change la distance, moins honnête pour « à moins de 100 m »).

---

## Ce que fait la Phase 1 (enchaînée)

- Deux blocs DISTINCTS, jamais fusionnés : **« Sur cette parcelle »** (historique permis, INCLUT le
  site) et **« Autour, à moins de 100 m »** (voisinage DVF+permis, 36 mois, EXCLUT le site).
- Point de calcul unique chacun, réutilisant M38 (dépôts datés) + DVF ; GIN(`idu_codes`) + geom_2975
  permis pour la perf ; mesure avant/après au bilan.
- 0 tier, 0 verdict — contexte pur. Parcelles sans voisinage exploitable : rien (doctrine M38).

## Annexes
- `qa/m42/historique_permis_par_tier_p0.csv` · `qa/m42/voisinage_distribution_p0.csv` · `_global.txt`.
- Recommandation hors périmètre : nettoyer les 7 tables `algo3_*` (résidu branche non mergée).
