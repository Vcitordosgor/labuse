# DETTE #4 — ENQUÊTE SOURCES COUCHE BATIMENT (mandat Vic 04/08)

> **POINT D'ARRÊT respecté : rien n'a été rechargé.** Un seul geste réseau hors mandat signalé
> (règle 4) : téléchargement du cadastre Etalab 974 (28,6 Mo, Licence Ouverte) pour un TEST À
> BLANC dans une table QA jetable, supprimée après mesure. Recherche externe : agent web,
> sources et dates citées.

## 1 · D'où vient la couche actuelle

| | |
|---|---|
| Source | **BD TOPO IGN**, flux WFS Géoplateforme `BDTOPO_V3:batiment` (`data.geopf.fr/wfs/ows`) |
| Ingestion | **nuit du 28-29 juin 2026** (~9 h, 817 506 bâtiments, île entière) |
| Millésime effectif | celui du WFS live fin juin 2026 ≈ **édition 2026-06-15 (v3.5)** |
| Licence | Licence Ouverte 2.0, attribution « © IGN — BD TOPO » |
| Défaut d'ingestion relevé | les attributs de DATE de la BD TOPO (`date_apparition`/`date_maj`) **ne sont pas conservés** — à garder au prochain chargement pour dater les retards |

**Conséquence immédiate : re-télécharger la BD TOPO ne corrigera presque rien** — notre couche
EST déjà le millésime courant. Le retard est chez le fournisseur, pas chez nous.

## 2 · Sources alternatives (recherche vérifiée 04/08/2026)

| Source | Millésime | Couverture 974 | Délai constructions neuves | Poids | Licence |
|---|---|---|---|---|---|
| BD TOPO IGN | 2026-06-15, trimestriel (+Express hebdo) | complète | **qq mois à 3-4 ans** (cycle PVA + cadastre) | ~183 Mo | LO 2.0 |
| **BDNB CSTB** | 2026-02.a | **AUCUNE — DOM exclus** (FAQ + test HTTP 403 sur dep974) | — | — | LO 2.0 |
| RNB | export 974 du 25/07/2026, hebdo | oui (DROM) | = BD TOPO au 974 (ses géométries en viennent, BDNB absente) — apporte l'ID pivot, PAS de bâtiments en plus | CSV dép. | LO 2.0 |
| Cadastre Etalab | 2026-06-01, trimestriel | complète, 642 344 bâtiments | **graphique : 1 à 3-4 ans** (rythme triennal DGFiP) | 28,6 Mo | LO 2.0 |
| OSM | quotidien | ~73 % du cadastre, import 2010 quasi figé (+700 bât./an) | très long | 32,6 Mo | **ODbL (share-alike, contaminante)** |
| **BD ORTHO / CoSIA** | **2025, 20 cm** (cycle 974 : 2013/2017/2022/2025) | complète | **voit les lotissements 2024-début 2025** | GPKG dép. | LO 2.0 |
| MS Building Footprints | 02/2026 (imagerie 2014-2024) | oui | variable | ~28 Mo | ODbL |

## 3 · Pourquoi les lotissements récents sont aveugles — TRANCHÉ EMPIRIQUEMENT

Deux tests à blanc sur les 38 bâties invisibles de l'échantillon (36 jointes) :

1. **Voisinage BD TOPO** : 35/36 ont des bâtiments BD TOPO à < 50 m (~36 en moyenne). La couche
   voit parfaitement le tissu ANCIEN → **pas un trou de couverture DOM**.
2. **Cadastre Etalab 2026-06 (test à blanc)** : ne voit que **1/36 (3 %)** des bâties invisibles,
   et 90/768 têtes sans indice. **Le cadastre graphique a le MÊME angle mort.**

**Réponse : la source est trop lente sur le NEUF — toutes les sources vectorielles le sont**
(BD TOPO se met à jour depuis le cadastre ; le report graphique cadastral est triennal). Nos
invisibles sont des constructions ~2023-2025. La seule famille de sources qui les voit :
**l'ortho 2025 (20 cm) et sa classification IA CoSIA 2025 (classe « Bâtiment », LO 2.0)** —
cohérent avec le fait que le scoring (permis < 2 ans) concentre les têtes exactement là.

## 4 · Coût / durée par option

| Option | Durée estimée | Gain mesuré/attendu sur NOTRE angle mort | Verdict |
|---|---|---|---|
| Re-télécharger BD TOPO (WFS) | ~9 h (mesuré 28-29/06) | ≈ nul (même millésime) | inutile seule |
| Recharger cadastre Etalab | ~10 min (28,6 Mo + chargement 2-3 min mesuré) | **3 % (1/36, mesuré)** | inutile seule |
| RNB | ~min (CSV hebdo) | 0 bâtiment en plus au 974 (géométries = BD TOPO) | ID pivot seulement |
| OSM / MS footprints | ~min | non mesuré | **écartés (ODbL share-alike)** |
| **CoSIA 2025 (classe Bâtiment) × parcelles** | pilote 1 commune (Saint-Paul) : ~1 j de dev + heures de calcul ; île : qq jours | **la seule source qui voit 2024-2025** ; à valider par pilote sur l'échantillon des 38 (vérité terrain déjà classée) | **LE correctif candidat** |

## 5 · Recommandation (arbitrage Vic)

1. **Correctif principal : CoSIA 2025** — croiser la classe « Bâtiment » (pixels 20 cm, LO 2.0)
   avec les parcelles pour produire une emprise bâtie par parcelle À JOUR. Pilote sur
   **Saint-Paul** + validation sur les 38 de l'échantillon (vérité terrain déjà établie :
   le pilote doit en voir ≳ 90 %).
2. **En complément** : rafraîchissement trimestriel BD TOPO (éditions) en conservant
   `date_apparition`/`date_maj` ; RNB comme ID pivot à terme.
3. **Écarter** : BDNB (absente DOM), OSM et MS footprints (ODbL), cadastre seul (3 % mesuré).
4. Les 90 têtes que le cadastre voit bâties (sur les 768) peuvent alimenter la revue par
   exceptions en attendant — SI Vic le demande (rien fait).

## Doctrine (consigne Vic 04/08)
**Le filet piscine/PV/DVF a lui-même des trous** (cas #079 : bassin dans le contour, non
détecté). Une détection d'indice ne prouve pas l'absence d'indice — **ne jamais conclure
« pas d'indice donc pas de bâti »**. Gravée ici et au BACKLOG.
