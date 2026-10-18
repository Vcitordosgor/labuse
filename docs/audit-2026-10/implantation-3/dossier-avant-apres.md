# IMPLANTATION-3 LOT B — Dossier §Potentiel : capacité AVANT / APRÈS

Ligne du §Potentiel (« Façons de construire ici ») sur 5 parcelles constructibles.
**AVANT** = miroir pré-LOT-B (commit `fe7a78a0`). **APRÈS** = HEAD (`d4466ddf`).
Le Flash EST le Dossier (alias builder) → il porte le MÊME renvoi (vérifié).

| Parcelle | AVANT (ancien moteur) | APRÈS (LOT B) | Flash (= Dossier) |
|---|---|---|---|
| 97404000AW0099 (L'Étang-Salé) | `Capacité (logements) 4–6 logements` | `Nombre de logements · voir l'Étude de faisabilité` | idem (renvoi) |
| 97409000AX0255 (Saint-André) | `Capacité (logements) 24–28 logements` | `Nombre de logements · voir l'Étude de faisabilité` | idem (renvoi) |
| 97411000DL0247 (Saint-Denis) | `Capacité (logements) 7–10 logements` | `Nombre de logements · voir l'Étude de faisabilité` | idem (renvoi) |
| 97422000BX1106 (Le Tampon) | `Capacité (logements) 5–8 logements` | `Nombre de logements · voir l'Étude de faisabilité` | idem (renvoi) |
| 97411000AT0427 (Saint-Denis) | `Capacité (logements) 10–13 logements` | `Nombre de logements · voir l'Étude de faisabilité` | idem (renvoi) |

- Le NOMBRE de logements (tiré de l'ancien moteur) **disparaît** ; la ligne renvoie à l'Étude de faisabilité, **sans chiffre**.
- La partie réglementaire du §Potentiel (SDP résiduelle, marge de surélévation) **reste inchangée** (extracteurs
  `sdp_residuelle_m2` / `marge_surelevation_m` non touchés).
- L'ancien libellé « Capacité (logements) » n'apparaît plus (vérifié par `test_a05_1`).
