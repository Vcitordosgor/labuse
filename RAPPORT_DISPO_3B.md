# RAPPORT — 3.B Photos aériennes historiques (dispo + livraison)

> Cercle 3, quick win. Rapport de dispo (§7) AVANT d'ajouter des couches carte, puis livraison.
> Aucune donnée fabriquée : on branche des couches IGN publiques et un lien de navigation.

## La donnée recherchée
**Orthophotographies historiques** sur Saint-Paul, pour lire l'évolution d'une parcelle (bâti
apparu/disparu, défrichement, urbanisation du voisinage) — un signal de prospection puissant.

## Sondage de disponibilité (2026-06-14)
Source : **Géoplateforme IGN** (`data.geopf.fr`, WMTS/PM) — capabilities WMTS lues (2,8 Mo).

| Couche | Millésime | Couvre Saint-Paul ? | Tuile testée (z15, centre-ville) |
|---|---|---|---|
| `ORTHOIMAGERY.EDUGEO.LA-REUNION1961` | ~1961 | ✅ (bbox 55.258→55.583) | HTTP 200 PNG **860 o** ⚠️ bord ouest |
| `ORTHOIMAGERY.EDUGEO.LA-REUNION1980` | ~1980 | ✅ | HTTP 200 PNG 94 ko |
| `ORTHOIMAGERY.EDUGEO.LA-REUNION1989` | ~1989 | ✅ | HTTP 200 PNG 54 ko |
| `ORTHOIMAGERY.EDUGEO.LA-REUNION2010` | ~2010 | ✅ | HTTP 200 PNG 152 ko |
| `ORTHOIMAGERY.ORTHOPHOTOS.1950-1965` | ~1950-1965 (national) | ✅ (bbox jusqu'à 55.846 / -21.401) | HTTP 200 PNG 50 ko |
| `ORTHOIMAGERY.ORTHOPHOTOS` | actuelle (BD ORTHO) | ✅ | HTTP 200 JPEG (référence) |

**Nuances documentées (pas masquées)** : les couches EduGéo La Réunion sont en **PNG**, **zoom natif
≤ 16** (au-delà, Leaflet ré-échantillonne — `maxNativeZoom: 16`). Le millésime **1961** est plus
**étroit** : au centre-ville (bord ouest de son emprise) la tuile est quasi vide (860 o) ; 1980/1989/
2010 couvrent largement la commune. ✅ `remonterletemps.ign.fr/comparer` joignable (HTTP 200).

## Livraison
1. **Lien « Remonter le temps » sur chaque fiche** (le cœur du 3.B) — paramétré sur le **centroïde
   réel** de la parcelle, ouvre le comparateur IGN **ortho actuelle ↔ ~1950-1965** (millésime qui
   couvre La Réunion). Helper pur `remonter_le_temps(lon, lat)` **testé**, injecté **hors cache**
   dans `GET /parcels/{idu}/enrichment` (jamais périmé) + **repli client** + lien sur le **one-pager**.
2. **Bonus — millésimes historiques SUR la carte** : 4 fonds sélectionnables (radar / vue du ciel /
   **2010 / 1989 / 1980 / 1961**) dans le sélecteur de couches (coin haut-droit). « Remonter le
   temps » sans quitter l'app.

## Recette
- `pytest tests/test_remonter_le_temps.py` (3 verts) : l'URL porte la bonne localisation
  (lon/lat ±1e-6), un millésime couvrant La Réunion, et n'invente rien si le centroïde manque.
- Carte : basculer « Ciel · 1980 » → l'orthophoto 1980 s'affiche sur Saint-Paul ; revenir à
  « Vue du ciel (IGN) » → ortho actuelle. Fiche : bouton « 📜 Remonter le temps (IGN) » ouvre
  le comparateur centré sur la parcelle.
