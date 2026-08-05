# M27 — MESURE À BLANC : GARDES AMONT DU DÉPARTAGE (05/08/2026)

> Régime [S]. Rapport chiffré, AUCUN code servi, AUCUNE bascule. Étiquettes : **Sourcé** =
> mesuré sur les tables servies/couches sources · **Estimé** = dérivé/proxy · **Absent** =
> non calculable proprement (dit, pas approximé). Fraîcheurs = source AMONT.

## AVANT TOUT — une faute de MON deck, à dire
2 des 5 cartes rejetées **ne sont pas servies en tête** : AD1237 est `declasse_zone_fermee`
(rang brut 14, jamais montrée) et CW1056 `declasse_non_constructible` (la lanière de 4 m —
**le moteur l'avait attrapée**). Mon deck des 20 classait par p brut SANS filtrer aux tiers
servis. Le constat (a) du mandat (« des SDP=0 servies en brûlantes ») ne tient pas au sens
servi ; le constat (b) reste vrai (AR1260). Tout deck futur = tiers servis uniquement.

## M-A — SDP nulle dans le servi [Sourcé : parcel_residuel (bascule v8), scoring q_v8_calibre]
| population | SDP = 0 | SDP NULL |
|---|---:|---:|
| **117 brûlantes** | **0** | **0** |
| top 100 SERVI (tête par rang) | 0 | 0 |
| top 1000 SERVI | 35 | 3 |
| tête entière (1 160) | 42 | 4 |
| (rang brut incl. déclassées, top 100/1000) | 4 / 214 | 17 / 199 |

**Liste des brûlantes concernées : VIDE** — le plancher C fait son travail sur les brûlantes.
Les 46 concernées sont des CHAUDES servies par la branche « surface ≥ 600 m² U/AU » du
plancher. Motifs (CSV M_A, une valeur par cas) :
- **42/42 SDP=0 : « sdp_max saturée par le bâti existant » (pct_potentiel ≥ 100)** — cohérent
  avec les bâties-connues (audit 4) ;
- 3 NULL : « hors PLU outillé » (97417 Salazie, commune non calibrée — train 6) ;
- 1 NULL : **cache parcel_residuel troué d'une parcelle** (CW1553 — le moteur live la calcule ;
  re-matérialisation corrigera).

## M-B — bâti non capté [Sourcé : BD TOPO éd. 2026-06-15 (WFS) · CoSIA PVA juil.-août 2025]
| population | bâti max ≥ 20 non-declasse_bati_revele | dont bande 20-40 | dont ≥ 40 (connues) |
|---|---:|---:|---:|
| brûlantes | 10 | 2 | 8 |
| top 100 (rang) | 21 | 2 | 19 |
| top 1000 (rang) | 545 | 47 | 498 |

Aucune n'est un raté de la règle E : les ≥40 sont des bâties **CONNUES** (BD TOPO ≥ 20, hors
périmètre par construction — le filtre client bâti, spec en attente) ; les 20-40 sont la
bande d'adjudication voulue. CSV M_B avec cause par ligne.

### Les 3 parcelles nommées [Sourcé]
| idu | tier servi | BD TOPO | CoSIA | ratio | vol ortho | conclusion |
|---|---|---:|---:|---:|---|---|
| AD1237 | declasse_zone_fermee (rang brut 14) | 0 | 148 | 24,8 % | 2025-07-22 | **captée DEUX fois** (règle E bande 'regle' + zone fermée qui prime) — jamais servie |
| AR1260 | brûlante 82 | 50 | 123 | 28,1 % | 2025-07-22 | **trou de PÉRIMÈTRE voulu** : bâtie CONNUE (BD TOPO ≥ 20) → filtre client bâti |
| AT0870 | brûlante 11 | 3 | 5 | 1,1 % | 2025-07-21 | **trou de COUVERTURE ponctuel** : les DEUX couches ≈ vides sur une toiture visible (dalle CoSIA couverte : 130 polygones à <200 m) — l'angle mort résiduel de CoSIA lui-même |

**Verdict M-B.2 : ni trou de dalle, ni trou de seuil unique — trois causes distinctes.**

### M-B.3 — couverture des dalles CoSIA [Estimé : proxy « 0 polygone à <500 m »]
2 005 parcelles / 431 663 (0,5 %) sans aucun polygone CoSIA à moins de 500 m — Les Avirons
355, Saint-Benoît 276, Sainte-Rose 276… : zones de Hauts/cirques inhabitées en bord de
dalle, PAS un trou urbain. Aucune dalle urbaine manquante détectée.

## M-C — géométrie du top 1000 SERVI [Sourcé : cadastre parcels (Etalab 2026-06) ; méthodes uniques documentées]
- **Largeur inscriptible** = 2 × rayon de `ST_MaximumInscribedCircle` (PostGIS 3.6) — un seul
  point de calcul.
- **Compacité** = Polsby-Popper 4πA/P².

| métrique | valeur |
|---|---|
| sous 5 m de largeur | **0** (CW1056, 4 m, est déclassée — garde amont déjà effective) |
| sous 8 m | **17** |
| Polsby-Popper min / moyen | 0,019 / 0,628 |

Les 20 pires : CSV M_C (tête triée par largeur) — 3 en tête servie < rang 1000 réel dont
AY1587 (rang 31, 6,8 m) et CY1051 (rang 550, 7,0 m, PP 0,069 : filiforme).

### M-C.4 — % de voirie : **Absent (non calculable proprement)**
La seule couche disponible est `voirie` = **tronçons LINÉAIRES** BD TOPO (éd. 2026-06-15,
235 643 objets, largeur non stockée — seuls nb_voies). Un « % de recouvrement » exige des
polygones ; approximer par un buffer inventerait une largeur. Conformément à la contrainte :
**non calculé**. Substitut honnête possible sur demande : longueur de tronçon intersectant
la parcelle (m), étiqueté Estimé.

## Fraîcheurs amont citées
BD TOPO bâti/voirie : édition 2026-06-15 (WFS Géoplateforme) · CoSIA : PVA 2025 (vols
21-22/07/2025 sur les zones citées) · cadastre parcels : Etalab 2026-06-01 · parcel_residuel :
matérialisé bascule v8 (04/08/2026) sur règlements calibrés GPU-PILOTE · scoring : run servi
q_v8_calibre (04/08/2026).

## Synthèse pour l'arbitrage du départage
1. Le plancher C protège les brûlantes (0 SDP nulle) ; la branche « surface ≥ 600 » laisse
   46 chaudes saturées-bâties — c'est le MÊME chantier que le filtre client bâti (spec).
2. La règle E n'a pas de raté mesuré ; restent les bâties CONNUES (périmètre voulu) et un
   angle mort résiduel image (AT0870-type) que seule l'adjudication attrape.
3. Géométrie : 1 garde amont manquante mesurable — largeur inscriptible < 8 m (17 cas) et
   compacité extrême (PP < 0,1) : candidates à un SIGNAL de fiche (pas un déclassement aveugle).
4. Le départage D→SDP→surface→IDU reste mesuré et prêt ; il amplifiera les erreurs d'état
   amont TANT QUE le filtre client bâti n'existe pas (AR1260 : +62 rangs) — l'ordre
   d'implémentation logique est : filtre client bâti (spec arbitrée) PUIS départage.
