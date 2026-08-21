# M129-4 §2 — Rapport : l'affirmation « placées sur la voirie publique »

**Statut : rapport (avant correctif). Ne rien merger.**
Parcelles de contrôle : `97420000AB0479`, `97422000EM0120`.

## §2.1 — Quelle couche, et le point est-il CONTRAINT à la voie ?

**Couche utilisée** : `spatial_layers` `kind='voirie'` = **BD TOPO IGN**
(`layers_ingest.py:42` → source `"BD TOPO IGN"`). Géométrie =
**LineString**, l'**axe** des tronçons (centre de chaussée), **pas** le
bord ni l'emprise de la voie. 235 643 tronçons.

**Le point EST contraint à la géométrie de la voie** — ce n'est PAS
« un point dans un rayon » :

```sql
cand AS (SELECT ST_ClosestPoint(sl.geom_2975, centroïde_parcelle) AS pt,
                ST_Distance(sl.geom_2975, centroïde_parcelle)     AS d
         FROM spatial_layers sl WHERE sl.kind='voirie'
           AND ST_DWithin(sl.geom_2975, parcelle, 70))
```

`ST_ClosestPoint(voie, centroïde)` renvoie le point **posé sur la ligne**
(distance 0). Le rayon de 70 m n'est que le **filtre de recherche**
(`ST_DWithin`), il ne relâche pas la contrainte de placement. Mesuré :
sur les 6 points des 2 parcelles, **`dist_axe = 0,00 m`** partout.

Donc « le point tombe dans un rayon d'une voie » est **faux** : il tombe
**sur l'axe** de la voie. C'est l'affirmation exacte à retenir.

## §2.2 — Contrôle « le point tombe sur la voie »

**Déjà garanti** par construction (`ST_ClosestPoint` ⇒ distance 0). Aucun
contrôle supplémentaire n'est nécessaire pour cette contrainte-là — elle
est structurelle, pas empirique.

## §2.3 — Mesure sur échantillon

40 parcelles bâties, 148 points de vue générés :

| Mesure | Résultat |
|---|---|
| Points à **> 2 m** d'un axe de voie | **0 / 148** (0 %) |
| Sous-type de la voie retenue | `Route à 1 chaussée` 70 · `Sentier` 35 · `Route empierrée` 22 · `Chemin` 21 |

La contrainte « sur l'axe d'une voie » tient à **100 %**. Mais **53 %**
(78/148) des points tombent sur un **Sentier / Chemin / Route
empierrée** — c'est-à-dire un chemin ou une piste, **pas** une voie
« publique » caractérisée.

## §2.4 — L'affirmation « voirie PUBLIQUE » est-elle défendable ?

**Non, sur deux plans :**

1. **« publique »** : la BD TOPO **ne porte aucun attribut public/privé**
   dans notre schéma (`spatial_layers` = kind/subtype/name/geom). Rien ne
   permet d'affirmer qu'un tronçon est ouvert au public. Et 53 % des
   points relèvent d'un chemin/sentier, souvent privés.
2. **« sur la voirie » au sens visuel** : le point est sur l'**axe**
   (centre de chaussée). L'axe BD TOPO peut être décalé de quelques
   mètres du bitume visible sur l'ortho, et l'axe de la voie voisine
   longe des parcelles bâties — d'où l'impression, au rendu (surtout à
   l'échelle lointaine PCMI8), que la pastille « tombe sur une parcelle
   bâtie ». Ce n'est pas un point mal placé : c'est un point sur l'axe,
   à courte distance du bâti d'en face (mesuré : 6–11 m du bâti le plus
   proche — donc **jamais SUR** un bâtiment, mais visuellement contigu à
   petite échelle).

**Constat faux à retirer** : « placées sur la voirie publique ».
**Constat exact et modeste à écrire** : *« calées sur l'axe de la voie
la plus proche (BD TOPO IGN) — chemin ou route selon le lieu ; position
indicative, à confirmer accessible et à ajuster sur le terrain. »*

## Décision appliquée dans les correctifs §1

Le mandat ne liste que **§1 et §3** en correctifs (§2 est un rapport).
Mais §1 réécrit précisément les libellés de PCMI7/PCMI8, et la doctrine
LABUSE tient qu'un **constat faux est pire qu'un constat modeste**.
Réémettre « voirie publique » dans ces libellés reconduirait un énoncé
que ce rapport démontre faux. J'écris donc les libellés §1 dans leur
forme **modeste et exacte** (ci-dessus), sans « publique » et en nommant
l'axe BD TOPO. Aucun autre correctif §2 (contrôle géométrique, filtrage
public/privé) n'est engagé — il relève de l'arbitrage de Vic.
