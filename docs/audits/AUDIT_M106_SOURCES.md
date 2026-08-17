# AUDIT M106 — sourcing des nouvelles couches (Phase 2, STOP)

Vérifié le 17/08/2026 — chaque URL testée (code HTTP), chaque volume MESURÉ (téléchargement
ou requête comptée), rien d'ingéré. Quatre pistes explorées en parallèle, synthèse ici ;
verdicts : **existe / n'existe pas / existe mais en PDF / a existé, retiré**.

## 1. Réseau de transport public + pôles d'échange — EXISTE (vectoriel, licence ouverte)

Les 5 AOM urbaines + le réseau régional publient TOUS leur GTFS sur le Point d'Accès
National (transport.data.gouv.fr), **Licence Ouverte v2.0**, zips vérifiés 200 et comptés :

| réseau (AOM) | validité | lignes | arrêts (quais) | tracés (shapes) |
|---|---|---|---|---|
| Car Jaune (Région, interurbain) | 12/2025 → 08/2027 | 16 | 319 | oui |
| Citalis (CINOR) | 07/2026 → 12/2026 | 71 | 1 618 | oui |
| Téléphérique Papang (CINOR) | 12/2025 → 03/2028 | 1 | 10 (5 stations) | **non** |
| Kar'Ouest (TCO) | expire 17/08/2026 (rafraîchissement imminent) | 64 | 2 268 | oui |
| Alternéo (CIVIS) | 03/2026 → 12/2026 | 68 | 2 375 | oui |
| Carsud (CASUD) | 12/2025 → 12/2026 | 43 | 2 145 | oui |
| Estival (CIREST) | 01/2026 → 12/2026 | 37 | 1 206 | oui |

Total mesuré : **300 lignes, ~9 941 quais** (recouvrements inter-réseaux non dédoublonnés).
URL stables = ressources des fiches PAN (les `static.data.gouv.fr` sont horodatées et
changent à chaque republication — la sonde radar doit viser l'API du PAN, pas le zip).

**Pôles d'échange : AUCUN jeu dédié n'existe.** Trois proxys mesurés :
- OSM (`public_transport=station` ∪ `amenity=bus_station`) : **42 objets**, ~25 gares
  routières/pôles nommés (Duparc, Le Port, Saint-Denis, Saint-Pierre…) + bruit (dépôts,
  points 4x4 Mafate) — ODbL ;
- registre public des gares routières (ART, xlsx Licence Ouverte, màj 13/05/2025) :
  **7 aménagements en 974** — existe mais NON vectoriel ;
- les « stations parentes » GTFS (`location_type=1`) sont des groupements de quais,
  PAS des pôles (Citalis et Carsud n'en déclarent aucune) — inutilisables tels quels.

À noter : mirror GeoJSON Région (arrêts/tracés Car Jaune) **périmé** (2020, 15 lignes vs 16).

## 2. Lignes haute tension — A EXISTÉ, RETIRÉ chez EDF ; l'IGN reste

Le réseau HTB réunionnais est opéré par **EDF SEI** (pas RTE — ODRÉ/RTE = métropole
uniquement, 0 jeu 974). Référence officielle EDF (jeu statistique, 2025) : HTB 566 km,
22 postes sources.

- **Fait majeur : les 4 couches vectorielles EDF SEI (HTB aérien, HTB souterrain,
  pylônes, postes sources) ont été VIDÉES le 24/12/2025** (fiches en ligne, 0 octet,
  motif affiché : « renforcer la sécurité publique »). Miroirs data.gouv morts (302).
  Wayback : aucune capture des exports. La BT, elle, est toujours servie (46 278 tronçons)
  — seul le HT/postes a été retiré.
- **BD TOPO IGN v3 (WFS Géoplateforme, Licence Ouverte, objets modifiés 05/2026) —
  la meilleure source restante** : `ligne_electrique` **48 tronçons / 347 km** avec
  TENSION (302 km 63 kV + 45 km 90 kV, aérien seulement), `pylone` 1 187, 
  `poste_de_transformation` 20 (vs 22 officiels).
- OSM : 199 tronçons (361 km `power=line`, tension + `location=underground` portés) —
  **ODbL** (share-alike), complétude non garantie. Divergence à trancher : BD TOPO dit
  90 kV sur 45 km, OSM tagge tout 63 kV.
- **Servitude I4 (recul) : N'EXISTE PAS en vectoriel** — 0 objet au GPU sur l'emprise
  974 (contrôle positif : 133 assiettes SUP d'autres catégories présentes), 0 jeu
  data.gouv. Vraisemblablement en PDF dans les annexes SUP des PLU. Conséquence pour la
  Phase 4 : on peut servir la PROXIMITÉ à la ligne (BD TOPO), PAS le périmètre exact de
  la servitude — le libellé devra le dire.

## 3. Téléphérique — EN SERVICE (Papang) ; ligne 2 EN PROJET sans tracé publié

- **Papang** (CINOR, Chaudron ↔ Bois-de-Nèfles, ouvert 2022) : le SEUL tracé vectoriel
  est **OSM** (2 ways `gondola` ~2,7 km, 5 stations, 29 pylônes — ODbL). Le GTFS Papang
  (Licence Ouverte, 12/2025, calendrier → 2028) donne les 5 stations géolocalisées
  mais **aucun linéaire** (pas de shapes.txt). Aucune couche SIG publiée par la CINOR.
- **Ligne 2 « Zèl La Montagne »** (ex-Payenke, Bellepierre ↔ La Vigie) : marché attribué
  (MND/Sogea), travaux ~2027, **mise en service annoncée 2029**. Tracé officiel NON
  publié ; le way OSM `proposed` (1,3 km) est un tracé ANTICIPÉ PAR UN CONTRIBUTEUR,
  tag déjà périmé (`name=Pyenke`) — à ne JAMAIS servir comme tracé réglementaire ni
  comme chantier constaté.

## 4. Assainissement collectif CINOR — le zonage réglementaire existe pour SAINT-DENIS seul

**Distinction du mandat tenue partout** : (a) desserte technique (le réseau passe) ≠
(b) zonage d'assainissement réglementaire (décision L.2224-10 CGCT annexée au PLU).

- **La seule source vectorielle ouverte de ZONAGE (b) est le GPU** (couche `info_surf`,
  code CNIG 19, Licence Ouverte) : **4 communes / 24** — Saint-Denis (119 polygones,
  PLU 23/04/2026, phasage actuel/court/moyen/long terme), Le Port (92), Saint-Paul (27),
  L'Étang-Salé (20 + 22 captages MAL CODÉS en type 19, bruit à filtrer sur libellé).
  **Cette donnée est DÉJÀ ingérée chez nous** (kind=`zonage_assainissement`, 258 objets,
  source « GPU — zonages d'assainissement », M86-B) et consommée par `anc_service`.
- **Effet sur la dette ANC (le signalement demandé)** : sur les 3 communes CINOR,
  **Saint-Denis est DÉJÀ en Sourcé parcellaire** (GPU). **Sainte-Marie et Sainte-Suzanne
  ne peuvent PAS y passer** : leurs PLU en vigueur au GPU (11/2025 et 09/2025) n'ont
  AUCUNE annexe assainissement — ni vecteur NI PDF (balayage des archives). Le zonage
  CINOR existe juridiquement (décision cas-par-cas AE du 17/09/2015) mais n'est publié
  nulle part en ouvert. Seule voie : demande directe CINOR/mairies.
- **Desserte (a) eaux usées : AUCUNE donnée ouverte sur toute l'île** (0 tronçon EU
  vectoriel ; plans PDF isolés : Saint-Benoît 2020, Saint-Pierre 2024, schéma Saint-Denis).
  Contraste : le réseau AEP de Saint-Denis est intégralement vectorisé au GPU
  (12 274 tronçons — eau potable, pas eaux usées). SUP A5 : 0 objet en 974.
- **Élargissement EPCI** : TCO (PDF SCOT 2014), CIVIS (page + règlements PDF, pas de
  carte), CIREST/CASUD (rien trouvé) — aucune intercommunalité ne publie de zonage
  vectoriel en propre ; le canal réel est le GPU via les annexes de PLU communaux.
  `sig.cinor.re` n'existe pas (NXDOMAIN) ; peigeo.re en refonte, catalogue GeoNetwork
  injoignable au 17/08/2026 ; Géo-IDE DEAL derrière connexion (fin de vie).
- Ouvrages (ni (a) ni (b)) : STEU Office de l'eau (CSV sans géométrie, licence non
  affichée), SANDRE WFS (15 points, LO 2.0) — hors sujet parcelle mais notés.

## 5. Synthèse pour l'arbitrage

| couche | verdict | source d'ingestion candidate | licence | réserve principale |
|---|---|---|---|---|
| Transport (lignes+arrêts) | **existe** | 7 GTFS du PAN | LO 2.0 | URLs horodatées → sonder l'API PAN ; dédoublonnage inter-réseaux |
| Pôles d'échange | n'existe pas en propre | proxy OSM (42 stations) ± registre ART (7, xlsx) | ODbL / LO | définir « pôle » nous-mêmes = risque d'inventer une typologie |
| Lignes HT | **existe (IGN)** — l'officiel EDF a été retiré | BD TOPO `ligne_electrique` + `poste_de_transformation` | LO 2.0 | aérien seul ; servitude I4 non vectorielle → PROXIMITÉ, pas servitude ; divergence 63/90 kV |
| Téléphérique en service | existe (OSM seul) | OSM `aerialway` + stations GTFS | ODbL / LO | tracé ODbL ; ligne 2 = projet SANS tracé publié (ne pas servir l'OSM `proposed`) |
| Assainissement CINOR | **déjà servi pour ce qui est publiable** | GPU (déjà ingéré, 4/24) | LO | Sainte-Marie/Sainte-Suzanne : non publié (même pas PDF) — demande directe CINOR |

**STOP — Vic arbitre quelles couches ingérer au vu de ce qui existe.** Points qui
commandent l'arbitrage : (1) ODbL (OSM) = share-alike, à trancher juridiquement avant
toute ingestion (téléphérique et pôles d'échange n'ont pas d'alternative) ; (2) les
lignes HT servies porteront une CONTRAINTE en proximité (le recul réglementaire I4
n'étant pas vectorisé, on ne peut pas servir la servitude elle-même) ; (3) la couche
CINOR demandée est, pour sa part publiable, déjà en base — le reste est un courrier à
la CINOR, pas une ingestion.
