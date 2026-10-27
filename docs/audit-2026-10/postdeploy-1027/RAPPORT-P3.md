# POSTDEPLOY-1027 P3 — réingestion des espaces naturels protégés (Réserve Marine)

## Pourquoi la RNMR était « perdue »

La Réserve Naturelle Marine Régionale (RNMR) n'a jamais quitté la base : ses **150 secteurs** sont
bien en `spatial_layers (kind='ens', subtype='reserve_naturelle')`. Ce qui s'est perdu au **13/09**,
c'est son **identité de nom**.

Avant le 13/09, la source était le nœud **Carmen** (MapServer/GML) qui servait la RNMR comme **une
entité** portant un nom « Réserve Naturelle Marine ». La migration du 13/09 vers **Lizmap**
(`deal974.lizmap.com`, couche `Reserve_Naturelle_Marine_Regionale__RNMR`) sert désormais la réserve
en **150 features par SECTEUR**, chacun nommé par son `Nom_zone` = `COT_*` / `DAR_*`
(« COT_Cap_Champagne », « DAR_Hermitage_Nord »…). L'ingestion (`deal_carmen.py`) prenait `Nom_zone`
tel quel → **aucun nom ne contenait « marine »**. Le seul `ens` nommé « marine » en base est un
FAUX-AMI : `Conservatoire du littoral — Marine De Vincendo` (subtype `conservatoire_du_littoral`,
toponyme), que le verrou ignore car il exige `subtype='reserve_naturelle'`.

Le verrou de quarantaine `d_enp_reserve_marine` (filtre `enp_complements`) demande « ≥ 1 entité
`reserve_naturelle` nommée « marine » » → **il ne trouvait rien → quarantaine → servi sous dérogation**.
Ce n'était ni un filtre géométrique ni un rejet de géométrie marine : **seul le nommage** était en cause.

## Correctif (dans l'ingestion, pas la donnée)

`src/labuse/ingestion/deal_carmen.py` : la couche RNMR porte désormais
`"nom_prefixe": "Réserve Naturelle Marine de La Réunion — "`, appliqué à l'ingestion. Chaque secteur
devient `Réserve Naturelle Marine de La Réunion — COT_Cap_Champagne` : self-descriptif, retrouvable
par le verrou et par l'utilisateur, le code secteur d'origine reste lisible. Aucune ligne corrigée à
la main ; la correction est rejouable (prod P4 via `deploy_donnees.sh` → `ingest-deal-carmen`).

## Réingestion sur le Mac (live Lizmap)

`labuse ingest-deal-carmen` → 3 741 entités, dont `Reserve_Naturelle_Marine_Regionale__RNMR : 150`.
Filtres rejoués : `deal_dpf : ok`, `zones_humides : ok`, **`enp_complements : ok`** (verdict structuré
`bloquants_ko=0, avertissants_ko=0`) — **plus de dérogation**.

## Avant / après (base Mac `labuse`)

| Mesure | Avant | Après |
|---|---|---|
| Total entités `ens` | 411 | **411** (inchangé) |
| dont `reserve_naturelle` (150 RNMR + 2 Étang St-Paul) | 152 | **152** |
| Features RNMR (typename) | 150 | **150** |
| Noms `ens` contenant « marine » | 1 (faux-ami Vincendo) | **151** (150 RNMR + Vincendo) |
| Noms `reserve_naturelle` « marine » (ce que vise le verrou) | 0 | **150** |
| Verrou `d_enp_reserve_marine` bloque ? | **oui** (dérogation) | **non** |
| Filtre `enp_complements` | quarantaine (sous dérogation) | **ok** |
| Parcelles intersectant la RNMR | 209 | **209** (inchangé) |

Le nombre d'entités ne change pas : la réingestion ne fait que **renommer** les 150 secteurs RNMR
(aucune création/suppression). Les **parcelles touchées restent 209** — stables et faibles au regard
de l'île : la réserve est **en mer**, seules les parcelles du trait de côte (lagon ouest, de
Boucan Canot à L'Étang-Salé) chevauchent sa frange terrestre. Liste complète des ENP : `enp_avant.txt`
/ `enp_apres.txt` (ramsar 1, sites classés/inscrits 7, réserves 152, ENS Département 178).

## Pour la prod (P4)

En prod la RNMR est aujourd'hui servie **sous la dérogation posée en DEPLOY-1027**. Après merge,
`deploy_donnees.sh` rejoue l'ingestion corrigée → la quarantaine passe **sans dérogation**, qui peut
alors être **levée et tracée** (cf. P4).
