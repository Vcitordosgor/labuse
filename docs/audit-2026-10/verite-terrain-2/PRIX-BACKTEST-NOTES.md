# VERITE-TERRAIN-2 · volet E — backtest PRIX (estimé vs réel, hors échantillon)

## Méthode anti-fuite

Les tables de prix SERVIES (`dvf_prix_sortie_neuf`, `dvf_secteur_medianes`) sont calculées sur **toute** la fenêtre DVF (jusqu'au 31/12/2025) : elles ont vu les ventes qu'on jugerait → fuite. On **reconstruit** donc l'estimation à une **date de coupe T = 2024-01-01** : médiane **€/m² par commune × type de bien** sur les ventes DVF **strictement antérieures à T** (69 couples commune×type estimés). On juge les **ventes postérieures à T**, prix estimé = médiane €/m² × surface de la vente. La vente jugée est après T par construction, l'estimation s'arrête à T : **elle n'entre jamais dans sa propre estimation**. Exigence : ≥ 5 comparables < T dans le couple, sinon abstention.

## Résultat global

- **N ventes jugées** : 3 581
- **Écart médian relatif (signé)** : -5.6 %
- **Écart absolu médian** : 27.4 %
- **Part à ±10 %** : 17.5 %
- **Part à ±20 %** : 36.5 %

## Par type de bien

| type | n | écart médian | écart abs. médian | ±10 % | ±20 % |
|---|--:|--:|--:|--:|--:|
| appartement | 449 | -11.3 % | 22.4 % | 20.0 % | 44.1 % |
| maison | 3 132 | -4.6 % | 28.3 % | 17.1 % | 35.4 % |

## Par commune (≥ 10 ventes jugées)

| commune | n | écart médian | ±10 % | ±20 % |
|---|--:|--:|--:|--:|
| 97411 | 619 | -4.8 % | 16.8 % | 39.3 % |
| 97422 | 445 | -2.5 % | 21.8 % | 40.2 % |
| 97416 | 412 | -11.6 % | 16.3 % | 36.9 % |
| 97415 | 347 | -6.6 % | 16.7 % | 33.4 % |
| 97414 | 247 | -8.1 % | 15.0 % | 33.6 % |
| 97412 | 209 | -10.1 % | 16.7 % | 38.8 % |
| 97409 | 169 | -4.5 % | 27.2 % | 46.2 % |
| 97408 | 140 | -1.1 % | 22.9 % | 43.6 % |
| 97410 | 139 | +10.2 % | 12.9 % | 37.4 % |
| 97413 | 127 | -7.4 % | 17.3 % | 34.6 % |
| 97418 | 120 | -6.3 % | 17.5 % | 35.0 % |
| 97407 | 113 | -5.5 % | 14.2 % | 20.4 % |
| 97405 | 71 | -3.4 % | 22.5 % | 46.5 % |
| 97420 | 62 | +16.2 % | 17.7 % | 29.0 % |
| 97406 | 60 | +2.2 % | 20.0 % | 43.3 % |
| 97404 | 51 | -19.7 % | 11.8 % | 25.5 % |
| 97403 | 48 | -9.0 % | 8.3 % | 16.7 % |
| 97401 | 44 | -3.6 % | 18.2 % | 31.8 % |
| 97417 | 38 | -19.1 % | 5.3 % | 21.1 % |
| 97402 | 34 | +12.2 % | 8.8 % | 35.3 % |
| 97424 | 34 | -6.1 % | 5.9 % | 23.5 % |
| 97419 | 24 | -2.6 % | 16.7 % | 25.0 % |
| 97421 | 14 | -22.6 % | 14.3 % | 42.9 % |
| 97423 | 14 | -22.2 % | 14.3 % | 14.3 % |

## Limites

- **Modèle d'estimation volontairement sobre** (médiane €/m² commune × type, rejouable sans fuite) : ce n'est pas l'estimateur fin servi en fiche, mais le plancher honnête que l'on peut reconstruire à une date de coupe sans voir le futur. L'écart mesuré majore donc l'erreur du produit (qui dispose de plus de contexte), il ne la minore pas.
- **Dispersion intra-commune** : une seule médiane par commune × type ignore quartier, état, étage → une part de l'écart est de l'hétérogénéité du bien, pas une erreur de niveau de marché.
- **Mono-mutation** : on ne garde que les mutations à une parcelle / un type pour un €/m² propre (les ventes composites sont écartées, pas jugées).
- **Couverture** : couples commune×type avec ≥ 5 comparables avant T seulement ; les communes/segments rares sont abstenus (comptés hors N).
- **Terrain nu non jugé** : le filtre mono-mutation (une parcelle / un type pour un €/m² propre) laisse trop peu de ventes de terrain nu pur postérieures à T pour un verdict ; le backtest prix porte donc sur maison + appartement (bâti). Terrain = 0 vente retenue.

