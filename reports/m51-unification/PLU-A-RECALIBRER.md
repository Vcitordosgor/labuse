# M5.1 lot 4.3 — PLU par commune : millésime en base vs GPU en ligne

Relevé du **13/07/2026** (requêtes en direct, lecture seule, aucune ingestion).
Base = `spatial_layers kind='plu_gpu_zone'`, `attrs->>'idurba'` (relevé 12/07/2026, fourni par le mandat).

## Méthode

1. **API officielle GPU** : `GET https://www.geoportail-urbanisme.gouv.fr/api/document?partition=DU_<insee>&limit=50` — renvoie TOUT l'historique (documents en `document.production`, `document.deleted`, `document.not_valid`) avec `originalName`, `legalStatus`, dates d'upload/màj. C'est la source de vérité utilisée ligne à ligne (colonne `url_verif` du CSV).
2. **Recoupement apicarto IGN** : `GET https://apicarto.ign.fr/api/gpu/document?partition=DU_<insee>` (document servi en flux) et `GET https://apicarto.ign.fr/api/gpu/municipality?insee=<insee>` (flag `is_rnu`). Résultats concordants sur les 24 communes.
3. **Contre-vérification zonage vivant** : `apicarto /gpu/zone-urba` par point dans la commune pour les cas « aucun document » (contrôle positif réussi sur Saint-Benoît).
4. **Web** (nature des procédures) uniquement pour les cas divergents : Saint-André, Saint-Leu, Saint-Louis, Saint-Philippe, Le Port.

Comparaison **insensible à la casse** : la base stocke `plu` en minuscules pour Entre-Deux, Sainte-Marie, Sainte-Suzanne, Cilaos, Saint-Louis — même document que le GPU.

## Résultat principal

**LISTE « PLU À RECALIBRER » : VIDE.**
Aucune des 24 communes n'a, au 13/07/2026, un document opposable sur le GPU **plus récent** que l'idurba en base. La base est alignée sur le GPU en ligne pour les 20 communes vérifiables, et pour les 4 autres le document opposable connu reste celui de la base (voir vigilances).

## Tableau complet

| Commune | INSEE | idurba en base | GPU en ligne (production) | Date appro. | Statut | Observation |
|---|---|---|---|---|---|---|
| Les Avirons | 97401 | 97401_PLU_20241206 | 97401_PLU_20241206 | 2024-12-06 | à jour | |
| Bras-Panon | 97402 | 97402_PLU_20260428 | 97402_PLU_20260428 | 2026-04-28 | à jour | téléversé le 22/06/2026 |
| Entre-Deux | 97403 | 97403_plu_20240924 | 97403_PLU_20240924 | 2024-09-24 | à jour | casse |
| L'Étang-Salé | 97404 | 97404_PLU_20250917 | 97404_PLU_20250917 | 2025-09-17 | à jour | |
| Petite-Île | 97405 | 97405_PLU_20230609 | 97405_PLU_20230609 | 2023-06-09 | à jour | |
| La Plaine-des-Palmistes | 97406 | 97406_PLU_20230527 | 97406_PLU_20230527 | 2023-05-27 | à jour | |
| Le Port | 97407 | 97407_PLU_20241209 | 97407_PLU_20241209 | 2024-12-09 | à jour ⚠ | `legalStatus = PARTIALLY_ANNULLED` |
| La Possession | 97408 | 97408_PLU_20251217 | 97408_PLU_20251217 | 2025-12-17 | à jour | |
| Saint-André | 97409 | 97409_20190228 | **aucun document GPU** | — | non vérifiable ⚠ | révision en cours NON approuvée ; PLU 2019 reste opposable |
| Saint-Benoît | 97410 | 97410_PLU_20200206 | 97410_PLU_20200206 | 2020-02-06 | à jour | |
| Saint-Denis | 97411 | 97411_PLU_20260423 | 97411_PLU_20260423 | 2026-04-23 | à jour | téléversé le 18/06/2026 |
| Saint-Joseph | 97412 | 97412_PLU_20251210 | 97412_PLU_20251210 | 2025-12-10 | à jour | téléversé le 02/07/2026 |
| Saint-Leu | 97413 | 97413_20070226 | **aucun document GPU** | — | non vérifiable ⚠ | révision en cours, approbation visée S2 2026 ; PLU 2007 reste opposable |
| Saint-Louis | 97414 | 97414_plu_20251218 | 97414_PLU_20251218 (retiré le 10/07/2026) | 2025-12-18 | à jour ⚠ | republication en cours, re-téléversement `not_valid` |
| Saint-Paul | 97415 | 97415_PLU_20251217 | 97415_PLU_20251217 | 2025-12-17 | à jour | |
| Saint-Pierre | 97416 | 97416_PLU_20240625 | 97416_PLU_20240625 | 2024-06-25 | à jour | |
| Saint-Philippe | 97417 | RNU (débordements voisins) | **aucun document GPU** | — | à jour (RNU confirmé) | zéro zonage au bourg ; débordements 97412/97419 confirmés |
| Sainte-Marie | 97418 | 97418_plu_20251126 | 97418_PLU_20251126 | 2025-11-26 | à jour | casse |
| Sainte-Rose | 97419 | 97419_PLU_20190504 | 97419_PLU_20190504 | 2019-05-04 | à jour | |
| Sainte-Suzanne | 97420 | 97420_plu_20250929 | 97420_PLU_20250929 | 2025-09-29 | à jour | casse |
| Salazie | 97421 | 97421_PLU_20220524 | 97421_PLU_20220524 | 2022-05-24 | à jour | |
| Le Tampon | 97422 | 97422_PLU_20230811 | 97422_PLU_20230811 | 2023-08-11 | à jour | |
| Les Trois-Bassins | 97423 | 97423_PLU_20220602 | 97423_PLU_20220602 | 2022-06-02 | à jour | |
| Cilaos | 97424 | 97424_plu_20240213 | 97424_PLU_20240213 | 2024-02-13 | à jour | casse |

Vérification unitaire : remplacer l'INSEE dans
`https://www.geoportail-urbanisme.gouv.fr/api/document?partition=DU_<insee>` (le document opposable est celui en `document.production`).

## Vigilances (à surveiller, PAS à recalibrer aujourd'hui)

1. **Saint-Louis (97414)** — le 10/07/2026 (il y a 3 jours), le document `97414_PLU_20251218` a été **retiré de production** et son re-téléversement est en `document.not_valid` : au moment du relevé, le GPU ne sert AUCUN zonage pour Saint-Louis. Même millésime (republication technique probable), mais **re-vérifier d'ici quelques jours** si un nouveau millésime sort. Historique récent dense : 20140311 → 20250709 → 20250926 → 20251218. Seule procédure documentée côté API : modification n°1 approuvée le 09/04/2024 (`/api/97414/procedures`).
2. **Saint-Leu (97413)** — PLU jamais publié sur le GPU (partition `DU_97413` vide de tout historique) ; l'opposable reste le PLU de 2007 (= base). **Révision générale en approbation imminente** : projet adopté le 11/12/2025, avis MRAe du 12/03/2026, enquête publique reportée au S1 2026, approbation visée début S2 2026 → candidat n°1 au prochain recalibrage. Sources : [imazpress](https://imazpress.com/toute-l-actu/urbanisme-a-saint-leu-l-enquete-publique-est-reportee-au-1er-semestre-2026), [saintleu.re](https://www.saintleu.re/plan-local-d-urbanisme-plu), [zinfos974](https://www.zinfos974.com/plu-de-saint-leu-des-progres-mais-des-alertes-persistantes/).
3. **Saint-André (97409)** — PLU jamais publié sur le GPU (partition `DU_97409` vide) ; l'opposable reste le PLU 2019 (= base). Révision générale en cours mais **non approuvée** (arrêt déc. 2024, 2e arrêt juil. 2025 après réserves de l'État, avis CDPENAF défavorable, avis MRAe 2025AREU7, Cirest défavorable). Sources : [zinfos974](https://www.zinfos974.com/plu-la-mairie-de-saint-andre-doit-revoir-sa-copie/), [MRAe 2025AREU7](https://www.mrae.developpement-durable.gouv.fr/IMG/pdf/2025areu7_rev_plu_saint_andre.pdf), [zinfos974 Cirest](https://www.zinfos974.com/la-cirest-retoque-le-plu-de-saint-andre/).
4. **Le Port (97407)** — millésime identique, mais le GPU marque le document `legalStatus = PARTIALLY_ANNULLED` (**annulation partielle** contentieuse). Le détail du jugement (zones concernées) n'a pas été trouvé sur le web — à creuser au recalibrage (greffe TA de La Réunion). Source : API GPU `partition=DU_97407`.
5. **Saint-Philippe (97417)** — **RNU confirmé** : aucun document sous `DU_97417`, aucun zonage GPU au point bourg (55.767, -21.358 → 0 zone), PLU en élaboration (DEAL). Les idurba `97412_PLU_20240320` / `97419_PLU_20190504` vus en base sous Saint-Philippe sont bien des **débordements géométriques** de Saint-Joseph et Sainte-Rose (hypothèse du mandat confirmée). NB : le flag `rnu` du GPU/apicarto vaut `false` (métadonnée Sudocuh en retard), mais l'absence totale de document fait foi. Sources : API GPU, [plu-immo](https://plu-immo.fr/saint-philippe-97442/), [DEAL Réunion](https://www.reunion.developpement-durable.gouv.fr/plan-local-d-urbanisme-plu-r78.html).

## Notes de méthode / honnêteté

- « à jour » = l'`originalName` du document en `document.production` sur le GPU est identique (casse ignorée) à l'idurba en base.
- « non vérifiable » (Saint-André, Saint-Leu) = le GPU en ligne n'a **jamais** hébergé de document pour ces communes : la comparaison GPU↔base est impossible par construction ; le web confirme cependant qu'aucune version plus récente n'est opposable → pas de recalibrage requis.
- `documentFamily`/`gridName` de l'API GPU ne filtrent pas correctement ; seul `partition=` est fiable (constaté le 13/07/2026).
- L'idurba en base pour Saint-André/Saint-Leu (`97409_20190228`, `97413_20070226`, sans segment « PLU ») ne provient donc pas du flux GPU actuel — probablement d'une autre source ou d'un dépôt disparu ; sans impact sur la conclusion.
- Aucune écriture en base, aucune ingestion : requêtes HTTP GET uniquement.
