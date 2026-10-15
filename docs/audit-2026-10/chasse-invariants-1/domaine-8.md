# Domaine 8 — Communes et agrégats

## Verdict (3 lignes)
433 229 parcelles vivantes passées au crible (24 communes), + île entière recomposée par 2 bases servies (parc vivant 433 229 ; parcelles filtrables 432 350). 11 invariants vérifiés, **1 violation** (INCOHERENT : `foncier.surface_ha` inclut les parcelles disparues alors que `n_parcelles` les exclut — même carte, deux définitions du parc). Sont restés muets : les recalculs géométriques lourds déjà couverts par `checks_commune.py` (aléa/PPR en %), la véracité des sources externes (population, SRU, RPLS, prix), non rejouables sans amont.

## Invariants

| # | règle (une phrase FR) | requête/script | parcelles passées | violations |
|---|---|---|---|---|
| I1 | Les 24 communes sont présentes PARTOUT (parcels, /communes, /communes/status, contexte) et aucune parcelle n'a de commune NULL. | `SELECT count(DISTINCT commune), count(*) FILTER (WHERE commune IS NULL) FROM parcels` + `len(/communes)` + `len(/communes/status.communes)` + 24 contextes fetchés | 434 582 | 0 |
| I2 | Somme-des-communes = total île : `sum(parcels.vivant par commune)` = total parc vivant servi. | `SELECT count(*) FILTER (WHERE cadastre_disparue_le IS NULL) FROM parcels` vs `sum(c['parcelles'] for c in /communes)` | 433 229 = 433 229 | 0 |
| I3 | `/communes[c].parcelles` = compte SQL vivant de la commune, pour les 24. | `SELECT commune,count(*) FILTER (WHERE cadastre_disparue_le IS NULL) FROM parcels GROUP BY commune` vs API | 433 229 (24 com.) | 0 |
| I4 | `/communes[c].evaluees` et `.chaudes` = recompte SQL (run q_v18, tiers hauts) pour les 24. | `SELECT commune,count(s.parcelle_id) evaluees, count(*) FILTER (WHERE s.tier IN ('brulante','chaude','priorite','a_suivre')) chaudes FROM parcels p LEFT JOIN parcel_p_score_v2 s ON s.parcelle_id=p.idu AND s.run_id='q_v18' GROUP BY commune` vs API | 24 com. | 0 |
| I5 | `/stats` (île) : la ventilation par tiers SOMME au total, et la ventilation par bande AUSSI (+ bandes_signal par bande). | `/stats?source=q_v18` : `sum(tiers.values())==total`, `sum(bandes.values())==total`, `sum(bandes_signal[b])==bandes[b]` | 432 350 | 0 |
| I6 | Additivité : `sum(/stats?commune=c)` sur les 24 = `/stats` île, pour total et chaque tier. | `/tmp/d8_stats.py` (24 appels sommés vs île) | 432 350 = 432 350 ; brûlante 142, chaude 663, écartée 150 063 tous = | 0 |
| I7 | `/stats.total` (île) = recompte SQL de la base servie (dryrun_parcel_evaluations × parcels, run cascade q_v18_sources, slivers <2 m² exclus). | `SELECT count(*) FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id WHERE d.run_label='q_v18_sources' AND (p.surface_m2 IS NULL OR p.surface_m2>=2.0)` | 432 350 = 432 350 | 0 |
| I8 | Écart des deux compteurs « parcelles » servis (/communes 433 229 vs /stats 432 350 = 879) = exactement les slivers vivants <2 m² (différence de DÉFINITION documentée, pas un bug). | `SELECT count(*) FROM parcels WHERE cadastre_disparue_le IS NULL AND surface_m2<2.0` → 879 | 879 | 0 |
| I9 | Compteurs de filtres : `/filtre.compte` = `/filtre.total` = `/stats.total` = cardinal SQL réel (base servie, def. surface=contenance), sur 4 filtres (commune, commune+surface, tiers, commune). | `/filtre?…&limit=0` vs `/stats?…` vs SQL `round(COALESCE(contenance_m2,surface_m2))>=…` | ex. Saint-Paul+surf≥1000 : 16 235 = 16 235 (API=SQL) ; Saint-Denis 38 175 = 38 175 | 0 |
| I10 | `/filtre.idus` : longueur de la liste servie = `compte` quand non tronquée. | `/filtre?commune=Les Avirons&tiers=brulante,chaude&idus=1&limit=200` → compte 30, len 30, tronque False | 30 | 0 |
| I11 | Fiche commune cohérente avec elle-même / la base : `foncier.n_parcelles` = SQL vivant (24), INSEE = référentiel (24), `stock_opportunites.n` = `/communes.chaudes` = `/stats.opportunites`, `repartition_zonage` somme 100 % (24). | `/tmp/d8_contexte.py` + `/tmp/d8_cross.py` + `/tmp/d8_zon.py` | 24 com. | **1** (voir V1 : `surface_ha` incohérent) |

## Violations

### V1 — `foncier.surface_ha` inclut les parcelles disparues, `n_parcelles` les exclut (même carte)
- **Gravité : INCOHERENT** (deux lecteurs du « parc de la commune » se contredisent dans le MÊME payload ; frôle le FAUX-CLIENT — surface qui compte des parcelles que le produit déclare disparues).
- **Objet** : les 24 fiches communes (effet non nul sur 22/24 ; pire cas Saint-Paul et Saint-André).
- **Attendu** : la surface de la commune porte sur le MÊME parc que `n_parcelles` (parc vivant, `cadastre_disparue_le IS NULL`), comme la carte / l'accueil / le run servi (règle CHASSE-DONNEES-FIX-1 Lot 2).
- **Obtenu** : `surface_ha` somme TOUTES les parcelles, disparues comprises.
  - Saint-Paul : `surface_ha`=23 080 ha servi, vivant=22 927 ha → **+153 ha fantômes (238 parcelles disparues)**.
  - Saint-André : 5 198 servi vs 5 078 vivant → **+120 ha (64 disparues, ~2,3 %)**.
  - L'Étang-Salé +44 ha, Le Tampon +40, Saint-Philippe +38, Sainte-Suzanne +34, Saint-Denis +34… (22 communes touchées ; Cilaos/Salazie ≤1 ha, sous le seuil d'affichage).
- **Preuve** : `/communes/{c}/contexte → foncier.surface_ha` = `SELECT round(sum(surface_m2)/10000.0) FROM parcels WHERE commune=:c` (SANS filtre vivant), byte-pour-byte, sur les 4 témoins recomposés. Le parc vivant donne systématiquement moins.
- **Cause probable** : `app.py:2161-2163` — le `surface_ha` de `_foncier_commune` fait `sum(surface_m2) FROM parcels WHERE commune=:c` **sans** le `filtre_vivant_sql`, alors que juste au-dessus `n_parcelles = compte_parcelles_commune(db, commune)` (`src/labuse/registre/moteurs/commune.py:102-114`) applique `filtre_vivant_sql` (exclut `cadastre_disparue_le`). Les deux lignes du même dict divergent donc par construction.
- **Fichier:ligne** : `src/labuse/api/app.py:2161-2163` (surface sans vivant) vs `src/labuse/registre/moteurs/commune.py:102-114` (compte avec vivant).

> Note : `repartition_zonage` (moteur zonage.py) et `stock_opportunites` ne souffrent pas du même problème (ils joignent `parcel_zone_plu`/`parcel_p_score_v2`, qui ne contiennent pas les disparues). Seul `surface_ha` est hors règle.

## Non vérifié
- **Parts d'aléa / PPR en %** (`risques.*_pct`) : recalcul géométrique ~40 s/commune, DÉJÀ couvert par `scripts/coherence/checks_commune.py` (`_pct_couche`, mode `--ile`). Non redoublé (consigne BRIEF).
- **Véracité des indicateurs externes** (`population.*`, `sru.*`, `parc_social`, `catnat`, `prix_neuf/ancien`, `permis_12m`, `mutations_12m`) : relevant de la fraîcheur des sources amont, non recomposables depuis `parcels` seul ; déjà adressés par `checks_commune.py` (cohérence inter-lecteurs) — hors invariant « = somme/moyenne des parcelles ».
- **Contexte servi depuis cache vs direct** : `commune_contexte_cache` est VIDE en local (`computed_at=None`) → tous les contextes sont calculés en direct ici. Un cache périmé en prod resterait à vérifier (hors périmètre local) ; la clé de fraîcheur (`app.py:2234-2237`) est censée l'invalider.
- **bbox par commune** : non recomposée (purement cartographique, pas un agrégat chiffré servi comme valeur).

## Gardes proposées
Prêtes pour `scripts/coherence/chasse_invariants.py` (chacune rend `[OK]`/`[ECART]`, exit 1 si écart). Toutes en lecture seule, `SET statement_timeout='120s'`.

```python
RUN = "q_v18"            # residuel_runs.is_served
CASCADE = "q_v18_sources"  # _cascade_run(RUN) : label réel de dryrun_parcel_evaluations
MINSURF = 2.0

# G8-1 — 24 communes, 0 commune NULL, additivité du parc vivant.
# SELECT count(DISTINCT commune) n_com, count(*) FILTER (WHERE commune IS NULL) nulls,
#        sum(CASE WHEN cadastre_disparue_le IS NULL THEN 1 ELSE 0 END) vivant FROM parcels
# ECART si n_com != 24 OU nulls>0 OU vivant != sum(/communes[*].parcelles)

# G8-2 — /communes[c].parcelles == SQL vivant par commune, pour les 24 (zip exact).
# SELECT commune, count(*) FILTER (WHERE cadastre_disparue_le IS NULL) FROM parcels GROUP BY commune
# ECART si une seule commune diffère de l'API, ou si une commune manque d'un côté.

# G8-3 — INVARIANT CLÉ (attrape V1) : dans CHAQUE fiche commune, surface_ha et n_parcelles
# portent sur LE MÊME parc. Recompose les deux avec le filtre vivant ; compare à l'API.
#   surf_vivant_ha = SELECT round(sum(surface_m2) FILTER (WHERE cadastre_disparue_le IS NULL)/10000.0) ...
#   ECART si abs(contexte.foncier.surface_ha - surf_vivant_ha) > 1
#   (aujourd'hui l'API sert surf_ALL ; cette garde mord jusqu'au correctif app.py:2161).

# G8-4 — additivité /stats : sum(24 communes) == île, pour total + chaque tier.
#   ile = /stats?source=RUN ; acc = somme des /stats?commune=c
#   ECART si acc.total != ile.total OU un tier diffère.

# G8-5 — partitions internes de /stats somment au total (tiers, bandes, bandes_signal).
#   ECART si sum(tiers.values()) != total OU sum(bandes.values()) != total
#           OU pour une bande sum(bandes_signal[b].values()) != bandes[b].

# G8-6 — compteur de filtre == cardinal SQL réel (def. surface = contenance), sur un jeu de filtres :
#   SELECT count(*) FROM dryrun_parcel_evaluations d JOIN parcels p ON p.id=d.parcel_id
#   WHERE d.run_label=CASCADE AND (p.surface_m2 IS NULL OR p.surface_m2>=MINSURF)
#     AND <predicats du filtre : p.commune=:c / round(COALESCE(p.contenance_m2,p.surface_m2))>=:smin / ...>
#   ECART si count SQL != /filtre.compte  OU  /filtre.compte != /filtre.total != /stats.total.

# G8-7 — /filtre.idus : len(idus) == compte quand idus_tronque is False.
```

Le script existant `scripts/coherence/aggregats.py` couvre déjà G8-6/G8-7 partiellement (compteurs + prédicat=fiche) ; **à ajouter : G8-1, G8-2, G8-3 (la violation V1), G8-4, G8-5** — aucun n'existe aujourd'hui dans le banc.
