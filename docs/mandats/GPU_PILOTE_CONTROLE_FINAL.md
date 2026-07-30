# GPU-PILOTE — CONTRÔLE FINAL : règlement / OAP par commune

> Une ligne par commune. **`sans_objet`** = la commune n'a PAS ce document (avec PREUVE).
> **`non_extrait`** = le document EXISTE mais n'est pas encore extrait. **`extrait`** = contenu lu.
> Preuve OAP : `unzip -l` de chaque archive (présence/absence du fichier `5_Orientations_amenagement`).
> **Fait vérifié : les 10 dossiers-zip lus ont TOUS règlement + OAP → aucune n'est `sans_objet` OAP.**
> Le seul `sans_objet` total est Saint-Philippe (RNU, aucun PLU sur GPU).

| INSEE | commune | règlement | OAP | preuve / note |
|---|---|---|---|---|
| 97401 | Les Avirons | **extrait** | **non_extrait** (présente, 1 pdf) | OAP scannée densité/social (négatif), contenu non détaillé |
| 97402 | Bras-Panon | **extrait** | **extrait** | OAP : 50% social capté ; ouverture conditionnelle_etat_tiers |
| 97403 | Entre-Deux | **extrait** | **non_extrait** (présente, 1 pdf) | OAP scannée (ni densité ni social), contenu non détaillé |
| 97404 | L'Étang-Salé | **extrait** | **extrait** | pilote — 12 sites OAP, densité/social par site |
| 97405 | Petite-Île | non_extrait | non_extrait | archive GPU téléchargée (sha da9ee5a8), pas encore extraite |
| 97406 | La Plaine-des-Palmistes | **extrait** | **non_extrait** (présente, 2 pdf) | OAP à forte composante graphique — à lire |
| 97407 | Le Port | non_extrait | non_extrait | archive GPU téléchargée (sha 2f47f34b), pas encore extraite |
| 97408 | La Possession | non_extrait | non_extrait | archive GPU téléchargée (sha e7313e5d), pas encore extraite |
| 97409 | Saint-André | non_extrait | non_extrait | **BLOQUÉ** — PLU 2019 dépublié, opposabilité mairie en cours ; zonage AGORAH seul |
| 97410 | Saint-Benoît | **extrait (PROVISOIRE)** | **non_extrait** | règlement PDF fourni (version à confirmer, cross-check GPU) ; OAP non fournie |
| 97411 | Saint-Denis | **extrait** (2026, opposable) | **à_confirmer** (dossier `5_OAP` VIDE) | calibré sur 97411_PLU_20260423 (PAS le 2024 périmé pointé par Vic) ; AUx fermée ; AUm/AUh à relire. OAP : dossier présent mais vide → ni extrait ni sans_objet prouvé |
| 97412 | Saint-Joseph | non_extrait | non_extrait | archive GPU **CORROMPUE** (sha c46b3884, zip invalide) — à re-télécharger ou fournir |
| 97413 | Saint-Leu | **extrait** | **non_extrait** | règlement mairie extrait ; **OAP non fournie** (existence à confirmer sur le doc 2007/2013) |
| 97414 | Saint-Louis | non_extrait | non_extrait | archive vide (0 o) — à fournir |
| 97415 | Saint-Paul | **extrait** | **non_extrait** (présente, 1 pdf) | OAP volumineuse (règlement 413 p) — à approfondir |
| 97416 | Saint-Pierre | **extrait** | **extrait** | OAP : densités 50/60/80 log/ha + social 20-40% par site |
| 97417 | **Saint-Philippe** | **sans_objet** | **sans_objet** | **PREUVE** : RNU — GPU `?grid=97417` = `[]`, `config/rnu_communes.yaml` (DU_97417=0, AGORAH=0). Traité par branche PAU (2 373 dans_pau) |
| 97418 | Sainte-Marie | **extrait** | **non_extrait** | règlement PDF fourni (EN_VIGUEUR confirmée 26/11/2025) ; OAP séparée non fournie |
| 97419 | Sainte-Rose | **extrait** | **extrait** | OAP minimale (5 p., ni densité ni social — contenu lu) |
| 97420 | Sainte-Suzanne | non_extrait | non_extrait | archive vide (0 o) — à fournir |
| 97421 | Salazie | non_extrait | non_extrait | archive vide (0 o) — à fournir |
| 97422 | Le Tampon | non_extrait | non_extrait | archive vide (0 o) — à fournir |
| 97423 | Les Trois-Bassins | **extrait** | **extrait** | OAP : social 25/40% par RHI (densité au règlement) |
| 97424 | Cilaos | **extrait** | **non_extrait** (présente, 1 pdf) | OAP scannée densité/social (négatif), contenu non détaillé |

## Bilan chiffré
- **Règlement extrait** : 12 (dont 1 provisoire = Saint-Benoît). `sans_objet` : 1 (Saint-Philippe RNU).
- **OAP extraite** : 5 (L'Étang-Salé, Bras-Panon, Saint-Pierre, Sainte-Rose, Les Trois-Bassins).
- **OAP non_extraite mais PRÉSENTE** : 6 (Les Avirons, Entre-Deux, La Plaine, Saint-Paul, Cilaos +
  archives téléchargées non traitées). `sans_objet` OAP : 1 (Saint-Philippe).
- **Reste** : 8 communes non extraites (archives à fournir/re-télécharger/débloquer).

## Distinction demandée (sans_objet vs non_extrait) — appliquée
- **`sans_objet` prouvé** : Saint-Philippe (RNU, GPU vide + config sourcée) — ni règlement ni OAP,
  et c'est NORMAL (RNU). Aucune autre commune n'est `sans_objet` OAP : les 10 dossiers-zip lus
  contiennent tous un fichier `5_Orientations_amenagement` (preuve `unzip -l`).
- **`non_extrait`** partout ailleurs où le document existe mais n'est pas encore lu — jamais confondu
  avec « la commune n'en a pas ».

## Leçon : le nom du dossier OAP VARIE
Saint-Denis (2026) range son OAP sous **`5_OAP`** (et le dossier est VIDE dans le pack), là où les 10
autres utilisent **`5_Orientations_amenagement`**. Toute vérification de présence d'OAP doit tester
LES DEUX noms. Un dossier PRÉSENT mais VIDE = `à_confirmer` (pack réduit ?), jamais `sans_objet`
prouvé — seul Saint-Philippe (RNU, GPU `[]`) est un `sans_objet` prouvé.
