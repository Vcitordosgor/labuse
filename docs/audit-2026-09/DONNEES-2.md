# DONNEES-2 — CoSIA COMPLÈTE OCS GE (§2 Terrain)

Branche `feat/donnees-2` depuis main **5c12304e** (après merge de feat/donnees-1). Un commit.

## Pourquoi
`parcel_cosia_couverture` porte, par parcelle, la surface de chaque classe CoSIA (IGN, 20 cm).
DONNEES-1 n'en montrait que le bâti. La végétation, l'imperméabilisé et le sol nu n'étaient
nulle part. Ce n'est **pas** un doublon d'OCS GE : la part artificialisée OCS GE est une donnée
d'**îlot** ; CoSIA mesure la **parcelle elle-même** à 20 cm. Décision Vic : CoSIA complète OCS GE.

## Ce qui est ajouté
Dans **§2 Terrain** de la fiche parcelle, sous « Couverture du sol », en complément (ni
remplacement, ni doublon) des lignes OCS GE existantes — 3 lignes déclarées, id + source
**« CoSIA (IGN, détection par IA, 20 cm) »** :

| donnée (id) | libellé | classes CoSIA agrégées |
|---|---|---|
| `part_impermeabilisee_cosia_pct` | Part imperméabilisée (CoSIA) | Bâtiment · Zone imperméable · Piscine · Serre |
| `part_vegetalisee_cosia_pct` | Part végétalisée / boisée (CoSIA) | Feuillu · Conifère · Broussaille · Pelouse · Culture · Vigne |
| `part_sol_nu_cosia_pct` | Part sol nu (CoSIA) | Sol nu · Terre labourée |

Agrégation : **Σ(surface de classe) / contenance cadastrale** (`bati.py:_cosia_couverture`, garde
table-absente). Les classes **hors** des 3 (Zone perméable = minéral perméable, Surface eau,
Neige) ne sont dans aucune part — les trois pourcentages ne somment donc pas 100 %, résidu dit
honnête. `moteur=None, calcul=passe_plat, reservoirs=(cosia,), table=parcel_cosia_couverture`.
Servies par le robinet **fiche_parcelle_le_bien** (§2 Terrain). N'entrent pas dans le score.

### Aucune ne recoupe exactement une ligne OCS GE affichée
- « Part imperméabilisée » ≠ « Part artificialisée (OCS GE) » : concept distinct (imperméabilisé
  ⊄ artificialisé au sens du décret) **et** maille distincte (parcelle 20 cm vs îlot). Preuve
  chiffrée ci-dessous : 8,2 % (CoSIA) vs 12,6 % (OCS GE) sur la même parcelle.
- « Part végétalisée/boisée » et « Part sol nu » : OCS GE n'affiche **aucune** ligne de part
  végétale ni de sol nu (il donne un *usage* dominant, pas des parts). Aucun recoupement.

Donc les 3 sont ajoutées ; aucune n'est supprimée pour doublon.

## Le Dossier suit (§2) par le miroir, sans code en plus
Les 3 lignes sont déclarées dans `declarations/fiche/le_bien.yaml` (rang 62/64/66,
`fiche_section: terrain`) avec un extracteur chacune dans `exports/robinet_fiche.py`
(lecture de `le_bien.cosia_couverture`). Le miroir (`exports/miroir.py`) les rend en §2 du
Dossier sans autre code. **V5d vert** : 69 données maille parcelle déclarées, 70 lignes du
Dossier miroir déclarées.

## Preuves

### Les 3 pourcentages, face à la ligne OCS GE (base réelle)
| parcelle | OCS GE — part artificialisée (îlot) | CoSIA imperméabilisée | CoSIA végétalisée/boisée | CoSIA sol nu |
|---|---|---|---|---|
| **97410000AN0347** | 12,6 % (usage US6.3) | **8,2 %** | **89,6 %** | **0,0 %** |
| **97415000CP0167** (boisée) | 9,8 % (usage US6.3) | **11,5 %** | **86,7 %** | **0,0 %** |

Sur AN0347, CoSIA imperméabilisée (8,2 %) ≠ OCS GE artificialisée (12,6 %) : la démonstration
que les deux ne se recoupent pas. Et CoSIA ajoute la végétation (89,6 %) et le sol nu, absents
d'OCS GE.

### §2 du Dossier (pdftotext) — voir `DONNEES-2-dossier-s2.txt`
```
   2. Terrain
Couverture du sol
Part imperméabilisée (CoSIA)                      8,2 %                                       sourcé
Part végétalisée/boisée (CoSIA)                   89,6 %                                      sourcé
Part sol nu (CoSIA)                               0,0 %                                       sourcé
Sources : BD TOPO IGN · CoSIA (couverture du sol IA, IGN) · Cadastre (API Carto PCI)
```

### Capture écran §2 avant/après
La ligne React (`TerrainDuBienBlock`, `leBien.tsx`) suit le MÊME patron `FactRow` + `src` que la
ligne OCS GE existante (DA existante respectée). Capture pixel laissée à l'œil de Vic sur l'app
live (:8095 / :5295) — même contrainte de capture que les sessions précédentes ; le contenu servi
est prouvé ci-dessus (payload + pdftotext).

## Finding pré-existant (hors périmètre, signalé)
Dans le **Dossier**, les 2 lignes **OCS GE** (`part_artificialisee_pct`, `usage_sol_dominant`)
s'affichent « hors couverture OCS GE » alors que la donnée existe (12,6 % pour AN0347) : les
extracteurs `_c_artif` / `_c_usage_sol` (`robinet_fiche.py`) lisent `o.get("artif_pct")` /
`o.get("usage")` au lieu des clés réelles du payload `part_artif_pct` / `us_dominant`. Bug
**antérieur** à DONNEES-2 (la fiche React lit les bonnes clés et affiche l'OCS GE) ; non corrigé
ici (« sans code en plus » côté Dossier, périmètre CoSIA). À trancher par Vic.

## Portes de recette
- **tsc -b** vert.
- **V5d** vert (miroir : 69 parcelle + 70 Dossier, tout déclaré) ; G6 dette 0 (bati.py déclaré
  lecteur de `cosia` via `fonction`) ; registre `verifier()` = OK ; passe-plats déclarent leur
  table (`parcel_cosia_couverture`).
- **circuit verrous -w G8** vert (`docs/audit-2026-09/DONNEES-2-verrous.txt`) — 30 joués, V5a/V5b/V5d/V7a verts (V7a toujours 55 couches, carte non touchée), seul G8 en avertissement (fraîcheur veille, non bloquant).
- **pytest tests/ complet** : **3068 passés · 4 échecs**, les 4 **pré-existants** (rouges à main : `test_chaque_passe_plat_declare_sa_table` sur `exposition_versant` hors périmètre, `test_traçage_des_classes_pose`, `test_retours11f4` ×2). **0 échec nouveau** (mes 3 passe-plats déclarent leur table).
