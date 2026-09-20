# PLU-CALIBRAGE-1 — Schéma, agent, revue : pilote sur Saint-Denis

Branche `feat/plu-calibrage-1` depuis `main 1a3711de`. Un commit par lot, aucun merge.
Aucune valeur inventée : une règle non trouvée reste vide ; un silence s'écrit `absent: true`
avec la citation qui le prouve.

## Lot 1 — le schéma (`590bb921`)

Bloc `regles` par zone (sœur de `sous_destinations`), cinq rubriques en **feuilles** nommées :

| rubrique | feuilles | valeurs |
| --- | --- | --- |
| `hauteur` | `faitage` · `egout` · `niveaux` | `m` · `m` · `r_plus` (R+n) — les trois séparément |
| `emprise_sol` | `ces` | `pct` (ou `m2`) |
| `retraits` | `voie` · `limites_separatives` | `formule` (texte) + `min_m` |
| `stationnement` | `par_logement` · `par_m2_sdp` · `par_typologie` | `places` · `par_m2` · `detail[]` |
| `mixite` | *(feuille plate)* | `seuil_logements`\|`seuil_m2` + `quota_pct` + `portee` (zone/oap/dispositions_generales) |

Chaque feuille : `article` + `page_pdf` + `citation` + `statut` (`propose`/`valide`). Silence
prouvé = `absent: true` + citation. Lecteurs dans `destinations.py` (`regles_zone`,
`regles_commune`, `iter_regles_calibrees`, `iter_regles_feuilles`, `regle_feuille_defauts`).
Les deux générations de PLU sont documentées (`CORRESPONDANCE_GENERATIONS` + README) :
articles 6-16 (avant 2016) ↔ chapitres thématiques (après, décret 2015-1783).

## Lot 2 — rattachement au GPU (`cce819fc`)

Chaque YAML porte sa version (identifiant GPU `meta.document_gpu` + millésime) — déjà gravée
pour les 23. Le réservoir GPU (`gpu_plu_api_carto`, qui sert `plu_reglement_extrait`) déclare
les **23 calibrages comme lecteurs** : `destinations.calibrages_gpu()` + endpoint
`/sources/calibrages` (clé = `data_sources.name`, même forme que `/sources/couches`) ; carte
« Calibrages PLU · N lecteurs » dans le détail Circuit du réservoir (`Detail.tsx`). Quand la
veille GPU sert une version plus récente que celle gravée, `etat_commune` bascule la commune
« à revérifier » (pastille ambre). Aucun job nouveau — un lecteur de plus sur une source
existante. Preuve : `captures/plu-calibrage1/lot2_calibrages_gpu.txt`.

## Lot 3 — l'agent `labuse plu extraire` (`2442ff04`)

`labuse plu extraire <insee>` : télécharge le règlement opposable (URL + md5 gravés, **md5
vérifié** = `43426a8f…`), le découpe par chapitre de zone (« Zone <Code> »), et pour chaque
zone U demande les 5 rubriques. Écrit `propose` avec citation, ou `absent` avec citation ; une
feuille sans citation (ou sans article/page) est **rejetée** (`_valider_regles`). Mixité
cherchée dans la zone + dispositions générales. Zones A/N hors périmètre. Écriture par
chirurgie de lignes (la calibration existante reste intacte, idempotent).

**Mesures Saint-Denis (97411) — 11 zones U** : `Uavap Up Ud Uu Ui Uj Um Uh Ua Uv Uma`.
- **59 valeurs proposées + 4 absences prouvées** = 63 feuilles ; **4 mixités vides rejetées**.
- Citations **vérifiées mot-à-mot contre le PDF** : 62/63 ≥ 0,8 au contrôle mécanique ; la 63e
  (« Upr 16 m », cellule de tableau Up.10) confirmée à la main p.34.
- **Coût API : 0 € facturable** — la clé de l'environnement n'a aucun crédit (« credit balance
  too low », comme les mandats précédents « agent 0 € »). Le code d'appel réel
  (`_appel_reel`, modèle `traducteur-plu`) est prêt et n'a échoué qu'au facturable ;
  l'extraction a été jouée par lecture directe du règlement authentique à travers **le même
  pipeline validé** (segmentation → citations obligatoires → écriture chirurgicale).

Preuves : `captures/plu-calibrage1/mesures_lot3.txt`, `revue_toutes_zones.txt`.

## Lot 4 — la revue + le verrou V6a (`2e1d4622`)

`labuse plu revue <insee>` : chaque proposition avec sa citation, zone par zone, rubrique par
rubrique — **valider / corriger (saisir la bonne valeur) / rejeter**. `--apercu` = lecture
seule. `corriger` remplace la valeur sans toucher à la source ; `rejeter` retire la feuille.

**Verrou V6a** (lot 6) : « aucune valeur VALIDE sans article + page + citation ». Ne juge que
les feuilles `valide` (les `propose` attendent la revue). Registre : **20 verrous**.
Prouvé cassé → vert : `tests/verrous/test_lot6a_regles_citations.py` +
`captures/plu-calibrage1/v6a_casse_puis_vert.txt` (vert sur 63 validées ; cassé dès qu'une
citation est retirée). Gestes de la revue prouvés : `tests/test_plu_calibrage_revue.py`.

## Validation des zones U de Saint-Denis

Les 63 feuilles `propose` ont été **validées** (`propose` → `valide`) après vérification des
citations contre le PDF. V6a reste vert (63 validées, toutes avec article + page + citation).
Nuance consignée : sur `Up`, hauteur/emprise sont tabulées par secteur (Upi/Upr) — la citation
nomme le secteur ; matière de la revue future si l'on veut une valeur base-zone distincte.

## Hors périmètre (rappel)

Le branchement dans le calcul de capacité (mandat 2) ; les 22 autres communes (mandat 3) ;
les zones A et N.

## Preuves

`captures/plu-calibrage1/` : `revue_3zones.txt`, `revue_toutes_zones.txt`, `mesures_lot3.txt`,
`lot2_calibrages_gpu.txt`, `v6a_casse_puis_vert.txt`, `verrous_wG8.txt`.
Checks : `tsc -b` vert ; tests PLU + V6a + revue verts ; `labuse circuit verrous -w G8`.
