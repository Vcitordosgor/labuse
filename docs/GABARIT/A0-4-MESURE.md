# A0-4 — Silence sourcé, renvois, multi-zones : remesure de couverture

Lecture via le builder complet (`scripts/gabarit_a0_3_mesure.py`, rejoué), 170 parcelles (100 tirées +
70 d'A0-2), EPSG:2975. Seuil GABARIT-4 : **≥ 75 % servies ET 0 faux** (le script imprime encore
l'étiquette « ≥ 90 % » de GABARIT-3 ; le seuil applicable ici est 75 %).

## Résultat — avant / après GABARIT-4

| | GABARIT-3 | **GABARIT-4** |
|---|---|---|
| Servies | 80 / 170 (47 %) | **135 / 170 (79 %)** |
| FAUX servis | 0 | **0** |
| Verrou PLU/multizone hors périmètre | 75 | 11 |
| Servies parmi les « atteignables » | 84 % | **85 %** |

**Seuil ≥ 75 % ET 0 faux : ATTEINT.** +55 parcelles servies (CES absent ~48, hauteur prospect ~1,
multi-zones 6).

## Causes de blocage restantes (35)

| Cause | n | Levier |
|---|---|---|
| enclave / voie privée (E2) | 12 | citation « voies privées » (rare) ou géométrie d'accès — GABARIT-5 |
| PLU : zone non calibrée | 10 | calibrage PLU de ces zones (hors périmètre) |
| limite non qualifiée (emprise non couverte) | 9 | zone ne visant pas « emprises publiques » ou vraie ravine — surface route BD TOPO |
| recul non validé | 3 | recul voie/séparatif ni chiffré ni alignement dans la zone |
| PLU : hauteur non validée | 1 | (autre que prospect) calibrage |

## Ce que chaque lot a débloqué

- **A — CES absent** : ~48 parcelles où le règlement ne fixe pas de CES sont servies « plafond non
  réglementé » (silence prouvé = donnée sourcée). C'est le gros du gain (le mur GABARIT-3).
- **B — renvoi / silence total** : renvoi AU→U surfacé ; zone sans aucune règle d'implantation (Le Port
  Uv) bloquée avec un motif clair (au lieu du trompeur « CES non validée »).
- **C — hauteur prospect** : Saint-Denis Ud (prospect L ≥ H) servie en 2D, hauteur « non chiffrée »
  (non intégrée), 3D indisponible.
- **D — multi-zones** : 6/7 parcelles à cheval servies (le morceau constructible ; la partie A/N =
  non constructible, exclue) ; ≥ 2 zones constructibles → différé (GABARIT-5).

## Verdict

Seuil **ATTEINT** (79 % ≥ 75 %), **0 faux**. Service confirmé. Le reste (21 %) : enclaves E2 (12),
zones non calibrées (10), limites non qualifiées hors emprise publique (9) — leviers = calibrage PLU,
citation voies privées, surface de route BD TOPO (GABARIT-5).
