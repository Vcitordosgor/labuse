# COHERENCE-1 — Un chiffre par notion, partout pareil

**Branche** `feat/couches-tuyau` · **départ** `a41c18fb`. Lecture seule d'abord (relevé), puis une seule correction (un libellé ambigu précisé).

## Verdict

**Aucun écart de calcul.** Chaque notion affichée lit une **expression canonique unique**. Les sources vitrine (94) lisent `WHERE_AFFICHEES` partout (client + dashboard) ; les couches dérivent chacune d'une fonction unique (`registre()`, `couches_carte()`, `/sources/couches`, filtre panneau). Deux quasi-écarts sont en fait des notions **distinctes** (ou du code mort) — détaillés plus bas. Une correction : le libellé du compteur « La carte » précisé pour ne pas confondre *kinds spatial_layers stockés* et *couches carte servies*.

---

## Le tableau

### Sources

| Endroit | Notion affichée | Chiffre | Expression lue | Cohérent |
|---|---|---|---|---|
| Client · page Sources · tuile « sources » | sources vitrine | **94** | `comptees.length` = `getSources()` (`/sources`) filtré `!doublon` → SQL `WHERE_AFFICHEES` | **oui** |
| Client · page Sources · « Toutes {n} » | sources vitrine | **94** | `nTotal` (= `comptees.length`) | **oui** |
| Client · page Sources · compteur par thème | sous-total d'un thème | Σ = 94 | `list.length` par catégorie (sous-ensemble filtré de `comptees`) | **oui** (sous-total du même ensemble) |
| Admin · Circuit · compteur « N réservoirs » | sources vitrine | **94** | serveur `_assembler_reservoirs` → `WHERE_AFFICHEES` (`compteurs.reservoirs`) | **oui** |
| Admin · Circuit · Résumé KPI « x / N » | sources vitrine (dénominateur) | **94** | `resume.kpis[0].sur` → `WHERE_AFFICHEES` | **oui** |
| Admin · Circuit · Résumé « reste » | sources vitrine | **94** | `resume.reste.reservoirs` → `WHERE_AFFICHEES` | **oui** |
| Admin · Circuit · diagramme « N réservoirs » | sources vitrine | **94** | `compteurs.reservoirs` → `WHERE_AFFICHEES` | **oui** |
| Admin · compteur · « N lignes en base non servies » | sources hors vitrine | **27** | `non_servies.length` (data_sources **hors** `WHERE_AFFICHEES`, non-réservoirs) | **oui** (complément : 94 + 27 = 121 en base) |

`WHERE_AFFICHEES` (`sources_catalog.py`) est l'unique expression ; les sept sites de comptage la lisent tous (SQL ou prédicat `est_affichee`), vérifié par le verrou **V2a** (SQL == Python == page). « Sources en base » (121) n'est **pas** affiché comme total : il n'apparaît que décomposé (94 vitrine + 27 hors).

### Couches

| Endroit | Notion affichée | Chiffre | Expression lue | Cohérent |
|---|---|---|---|---|
| Client · carte · légende du tuyau (`TuyauLegend`) | couches actives | *(aucun nombre)* | liste les couches cochées, **sans compteur** | s.o. |
| Client · panneau « Couches » (`NouvellesCouches`) | couches par famille | *(aucun total)* | liste par famille (`/map/tuyau/couches`), **sans compteur** | s.o. |
| Client · légende V1 (`Legend.tsx`) « · N couches » | couches actives | *(jamais rendu)* | `layers` (store **V1 mort**) filtré `!BASE_FOND` | **CODE MORT** — ne s'affiche jamais dans l'UI tuyau (retourne `null`, store V1 non alimenté) |
| Admin · fiche réservoir · « Couches carte alimentées · N » | couches carte **servies** par le réservoir | **8** (BD TOPO) | `couchesParSource[r.nom].length` → `/sources/couches` (résolution `registre()`) | **oui** |
| Admin · compteur « La carte » · `spatial_layers(…)` | **kinds `spatial_layers` stockés** (physique) | **11** (BD TOPO) | `r.couches` = `spatial_layers.kind` bruts | **oui** — notion **distincte** (libellé précisé, cf. correction) |

**Aucun total « N couches » n'est affiché au client.** Les quatre notions de couches ont chacune une expression canonique unique (côté serveur) :

| Notion | Expression canonique | Chiffre |
|---|---|---|
| couches **servies** (tuyau) | `registre()` (clés) — aussi `/map/couches-info`, `/map/tuyau/couches`, tuiles | **56** |
| couches **déclarées** | `couches_carte()` (= 56 − 3 hors-registre : limites_parcelles, limites_communes, batiment) | **53** |
| couches **thématiques** (panneau, hors repères + fond de plan) | 56 − 2 repères − 3 fond_de_plan | **51** |
| couches **alimentant une source** vitrine | `/sources/couches` (clés) | 48 (dont **45** sources vitrine) |

Ces nombres sont des **notions différentes**, pas des recalculs divergents d'une même notion : 56 ⊃ 53 ⊃ 51 ; 45 = sources qui nourrissent au moins une couche.

---

## Les deux quasi-écarts (ni l'un ni l'autre n'est un bug)

1. **Légende V1 « · N couches » = code mort.** `Legend.tsx` compte le store `layers` (l'ancien système V1, retiré à COUCHES-RETRAIT-1). Ce store n'est plus alimenté (le tuyau utilise `tuyauActives`), donc la légende V1 ne construit aucun groupe et **retourne `null`** — vérifié en navigateur (0 nœud `[data-legend]`, même en mode verdict). Le compteur n'est donc **jamais affiché**. *Signalé comme vestige à nettoyer un jour ; non retiré ici (hors périmètre, et éviter tout risque sur un chemin non testé).*

2. **BD TOPO : 11 vs 8 = deux notions.** Le compteur « La carte » liste **11 kinds `spatial_layers`** stockés (`batiment, voirie, water, ravine, cimetiere, construction_lineaire, construction_surfacique, zone_activite, bassin_versant, axe_structurant, ligne_ht`) ; la fiche réservoir liste **8 couches carte servies** (les 11 moins `voirie`, `water`, `ravine`, qui sont des sous-couches BD TOPO internes, **absentes de `registre()`**, jamais servies comme couche carte). Ce sont deux notions légitimes (physique en base vs servi au client). **Correction appliquée** : le libellé du compteur « La carte » est précisé (`kinds stockés` ≠ `Couches carte alimentées`) pour qu'on n'attende jamais l'égalité des deux chiffres.

---

## Question au passage — la source en statut `a_faire`

Une seule : **« Carte hypsométrique du littoral (DEAL Lizmap) »** (thème risques).

**Ce qui bloque** : le producteur ne la sert **qu'en WMS IMAGE** (raster) ; la couche vecteur (`Courbes_de_niveau_hypsometrique__en_metres`) est **REFUSÉE en WFS** (`ServiceException`, vérifié 13/09/2026) — aucun vecteur à ingérer sans convention. La donnée **réglementaire** de submersion est déjà servie à la place par les **aléas PPRL vecteur** (DEAL). Le statut `a_faire` est donc légitime (chantier nommé, pas un oubli).

*(NB : le survol de code statique peut suggérer d'anciens `a_faire` comme BDNB/PEIGEO ; en base aujourd'hui, `status='a_faire'` = **1 seule** ligne, celle ci-dessus. BDNB = `partenariat_requis`, PEIGEO = `hub`.)*

---

## Correction appliquée

`frontend/src/components/admin/circuit/Detail.tsx` — compteur « La carte » : libellé précisé pour distinguer les *kinds `spatial_layers` stockés* (physique) des *couches carte servies* (fiche réservoir). Aucune logique de comptage touchée, aucun autre fichier.

## Preuve
- Captures `captures/coherence1/` : `client_sources.png` (94), `client_map_legend.png` (légende tuyau sans compteur), `admin_resume.png`, `admin_compteur_carte.png` (94 réservoirs + « La carte »), `admin_reservoir_bdtopo.png` (Couches carte alimentées · 8). Harnais `frontend/qa/coherence1.mjs`.
- `tsc -b` vert · `labuse circuit verrous` COMPLET VERT 25/25.
