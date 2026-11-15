# PLU-MAJ-2 — vérification Saint-Denis avant merge : versions + pleine terre

**Question** (session précédente) : des valeurs de pleine terre « lues dans le texte en base »
(UH 50 %, UJ/UM 35 %, UI 25 %, UD/UU 10 %, Uat 15 %) ne se retrouvaient pas dans le PDF de
`data/plu_reglements/`. De quelle version est chacun des quatre éléments, et que dit le règlement en
vigueur sur ces valeurs ?

---

## 1. Version de chacun des quatre éléments

**Conclusion : les quatre sont du document approuvé le 05/08/2026 (`97411_PLU_20260805`) et mutuellement
cohérents. Rien à mettre à niveau.**

| Élément | Version | Preuve |
|---|---|---|
| **Zonage servi** (`spatial_layers`) | `97411_PLU_20260805` | 259 zones, toutes à cet idurba |
| **Texte du règlement en base** (`plu_reglement_extrait`) | `97411_PLU_20260805` | 240 extraits ; **identiques à une extraction fraîche du PDF conservé** (même ensemble (zone, article, page) — 0 écart) |
| **PDF conservé** (`data/plu_reglements/97411_reglement_20260805.pdf`) | `97411_PLU_20260805` | md5 `43426a8faf55efcdaa2a235e95a45d2f` = **octet-pour-octet** le règlement écrit du pack officiel GPU `97411_PLU_20260805.zip` (`…/3_Reglement/97411_reglement_20260805.pdf`) ET du PDF des annexes |
| **Règles chiffrées** (`config/plu_destinations/97411_saint_denis.yaml`) | `97411_PLU_20260805` | md5 `43426a8…` ; les `page_pdf` cités tombent juste dans le PDF conservé (sondage PLU-MAJ-2, 10/10) |

**Nuance sur le document lui-même (côté Géoportail, pas côté LABUSE).** Le pack officiel de l'idurba
`97411_PLU_20260805` contient un **règlement écrit dont l'en-tête est « Modification simplifiée n°8 —
Règlement approuvé — Février 2024 »** et une **procédure horodatée du 24/04/2026** (accusé préfecture
`974-…-20260423-…`). Autrement dit, le règlement ÉCRIT porté par le document en vigueur est le texte
consolidé de la modification n°8. LABUSE sert fidèlement ce que le Géoportail publie pour cet idurba — il
n'y a **pas** de décalage de version interne à LABUSE.

---

## 2. Les valeurs de pleine terre citées ne sont PAS dans le règlement en vigueur

Recherche plein-texte du PDF opposable **et** du texte en base : les valeurs citées sont à **0
occurrence** (ni « UH 50 % », ni « UI 25 % », ni « Uat 15 % », etc. ; `Uat` existe comme secteur de la
ZAC Triangle, **sans** minimum de pleine terre). Ce que le règlement en vigueur dit RÉELLEMENT, zone par
zone, image de la ligne/section à l'appui (`images/saint-denis-pleine-terre/`) :

| Zone | Valeur citée (autre session) | Règlement en vigueur `20260805` | Page | Image |
|---|---|---|---|---|
| **UD** | 10 % | **30 % minimum** en pleine terre | p46 | `UD_p46.png` |
| **UI** | 25 % | **40 % minimum** en pleine terre | p58 | `UI_p58.png` |
| **UH** | 50 % | **aucun minimum de pleine terre** (art. Uh.13 « espaces libres… » : 1 arbre/100 m²) | p75 | `UH_p75.png` |
| **UJ** | 35 % | **aucun minimum de pleine terre** (art. Uj.13) | p64 | `UJ_p64.png` |
| **UM** | 35 % | **aucun minimum de pleine terre** (art. Um.13) | p70 | `UM_p70.png` |
| **UU** | 10 % | **aucun minimum de pleine terre** (art. Uu.13) | p50 | `UU_p50.png` |
| **Uat** | 15 % | **aucun minimum de pleine terre** (secteur de la zone UA — ZAC Triangle, art. Ua.13) | p80 | `Uat_p80.png` |

Seules **UD (30 %)** et **UI (40 %)** portent un minimum de pleine terre dans le règlement opposable ;
les autres zones citées n'en portent aucun. **Aucune des sept valeurs rapportées ne figure dans le
document en vigueur** — ni dans le texte en base (qui, lui, est identique au PDF). Les valeurs citées
proviennent donc d'un **autre document** que le règlement opposable de Saint-Denis (p. ex. un projet, une
version antérieure non retenue, ou une autre commune) : ce n'est pas un décalage de version de LABUSE.

> Reproduire : `PYTHONPATH=src <venv>/python scripts/plu_maj_2_saint_denis_pleine_terre.py`
> (table + images) ; le détail machine du diff versions est au §1.

---

## 3. Deux règles de pleine terre ajoutées à la configuration (validées)

Les deux seules règles de pleine terre réelles de Saint-Denis étaient **absentes** de
`config/plu_destinations/97411_saint_denis.yaml` (rubrique `pleine_terre`). Elles y sont désormais, au
statut **`valide`**, avec la citation mot pour mot et la page du règlement en vigueur (image à l'appui) —
**rien n'est ajouté pour les autres zones** (elles n'ont aucun minimum de pleine terre) :

| Zone | Règle | Citation (mot pour mot) | Article · page | Image | `plu verif` |
|---|---|---|---|---|---|
| **Ud** | pleine_terre.pct = **30** | « Minimum 30% de la parcelle doit être en pleine terre » | Article Ud.13 · p46 | `UD_p46.png` | **TROUVE** |
| **Ui** | pleine_terre.pct = **40** | « Minimum 40% de la parcelle doit être en pleine terre » | Article Ui.13 · p58 | `UI_p58.png` | AMBIGU¹ |

¹ `AMBIGU` honnête : la page porte, après la règle générale, une clause « Toutefois… » (exception de
secteur) — la valeur 40 % est bien présente et citée ; verif signale seulement l'exception voisine.
Le verrou V6a (toute règle `valide` porte article + page + citation) reste vert.

Rien d'autre à mettre à niveau (les quatre éléments sont déjà au `20260805` et cohérents). Tables de
travail locales `plu_maj2_zone_avant/apres` supprimées. Hook rejoué vert, branche poussée.
