# PAU CoSIA — Phase 2 : BLOCAGE source canonique (STOP avant construction)

**Exigence #1 (Vic) : « pointe la couche CoSIA CANONIQUE, jamais qa_cosia_bati. Si la couche
canonique n'existe pas en base, dis-le AVANT de construire — on l'ingérera au standard
plutôt que de servir un proxy de mesure. »**

## Constat : la couche CoSIA canonique EN GÉOMÉTRIE n'existe pas.

Le recalcul PAU (`build_pau`, `rnu.py:149-158`) clusterise des **géométries de bâtiments**
(`ST_ClusterDBSCAN(ST_Centroid(geom))`). Il lui faut donc une couche de **footprints CoSIA**.
État mesuré en base :

| objet | contenu | géométrie ? | statut | verdict |
|-------|---------|-------------|--------|---------|
| `qa_cosia_bati` | 445 190 polygones (24 communes) | **oui** | écrit uniquement par `qa/dette4/*` et `qa/cosia/*` | **QA — interdit** (préfixe `qa_`) |
| `p_model_bati_cosia` | 321 314 lignes, `emprise_cosia_m2` par idu | **non** (aire seule) | canonique (lu par `bati_revele.py`, `verdict_servi.py`, `p_model/sql.py`, faisabilité) | **canonique mais inclusterisable** |
| `spatial_layers kind='batiment_cosia'` | — | — | n'existe pas | absent |
| `src/labuse/ingestion/cosia.py` | — | — | **n'existe pas** | absent |

- **Aucun module d'ingestion CoSIA** dans `src/labuse/ingestion/` (40 modules y sont, dont le
  patron bâtiment `layers_ingest.py:607 ingest_batiments` → `_insert_layer(…, "batiment", …)`).
- **Aucune source brute CoSIA versionnée** sur disque (pas de `.gpkg/.shp/.parquet/.geojson`).
- `p_model_bati_cosia` a été peuplée **hors dépôt** (aucun INSERT/CREATE dans le code) ; seule
  survit l'aire par parcelle, pas les footprints.
- La seule géométrie CoSIA (`qa_cosia_bati`) est un **artefact de contrôle** — recoupé à 0,5 %
  près avec le canonique (valable pour CHIFFRER en Phase 1, cf. `PAU_COSIA_MESURE.md`, mais
  **pas** pour SERVIR en production).

**Conclusion : on ne peut pas faire un échange de source propre (BD TOPO → BD TOPO + CoSIA)
aujourd'hui, parce que la source CoSIA canonique en géométrie n'est pas en base.** Câbler
`build_pau` sur `qa_cosia_bati` reviendrait exactement à « servir un proxy de mesure » — ce que
l'exigence #1 interdit. Je m'arrête donc AVANT de construire, comme demandé.

## Ce qu'il faut pour lever le blocage — ingestion au STANDARD

Path recommandé (**A**) :
1. **Source brute CoSIA** (classe « bâtiment » PVA juil.-août 2025, 20 cm) fournie/re-téléchargée
   — le même jeu qui a produit `p_model_bati_cosia`.
2. Nouveau module `src/labuse/ingestion/cosia.py` au patron des autres ingestions
   (idempotent, `source_millesime`, CLI `labuse ingest-cosia`), matérialisant une couche
   canonique de footprints — au choix arbitré :
   - `spatial_layers kind='batiment_cosia'` (réutilise l'infra couches, le plus léger), **ou**
   - table dédiée `cosia_bati(geom_2975, source_millesime, computed_at)`.
3. (Optionnel, cohérence) re-dériver `p_model_bati_cosia` DEPUIS cette couche canonique, pour
   qu'aire-par-parcelle et footprints aient la même provenance tracée.

Path compromis (**B**, NON recommandé) : promouvoir les polygones déjà en base
(`qa_cosia_bati`) vers une table canonique via une ingestion propre. Rapide, mais ça
**blanchit un artefact QA** — contraire à l'esprit de l'exigence #1. À n'envisager que si la
source brute est irrécupérable.

## Ce qui est PRÊT à couler dès que la couche canonique existe (déjà spécifié, non écrit)

- `build_pau` : `src` = BD TOPO **∪** CoSIA canonique, **déduplication DANS le geste** —
  la clause `AND NOT EXISTS (SELECT 1 FROM <bdtopo> b WHERE ST_Intersects(b.geom, c.geom))`
  écarte les 2 390 footprints partagés AVANT le clustering (jamais comptés deux fois).
- **Test** prouvant la dédup : sur St-Philippe, `count(source clustering)` =
  `count(BD TOPO) + count(CoSIA nouveaux)` et **≠** `count(BD TOPO) + count(CoSIA total)` ;
  assert `footprints_partagés = 2 390` retirés.
- **Avertissement PAU inchangé** (`rnu.py:36 AVERTISSEMENT_PAU`) : la PAU gagne en qualité mais
  reste **Estimé** — nature inchangée. Test que `rnu_block` sert toujours `avertissement_pau`.
- **Vérif cible** (jeu médian, source dédupliquée) : PAU **2 655 parcelles / 47 noyaux**,
  plancher **1 145**, **0 sortant** ; golden 119/119, tsc 0, build.

## Décision attendue de Vic
- Fournir la source brute CoSIA (Path A, recommandé), **ou** autoriser le Path B (promotion de
  l'artefact), **ou** trancher le réceptacle canonique (`spatial_layers kind='batiment_cosia'`
  vs table dédiée). Rien n'est construit tant que ce n'est pas tranché.
