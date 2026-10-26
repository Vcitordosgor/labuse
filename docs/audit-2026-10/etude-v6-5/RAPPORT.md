# ETUDE-V6-5 — le nombre de niveaux de sous-sol est une hypothèse explicite

Branche `feat/etude-v6` (worktree `labuse-etude-v6`), **pas de merge**. Même gardes.

## Mandat

Le stationnement a désormais **trois choix** : **Aérien · Sous-sol 1 niveau** (défaut en passant au sous-sol)
**· Sous-sol 2 niveaux**. La capacité, le plan −1 (et −2 si choisi), le facteur limitant, l'écran et le PDF
**suivent ce choix**. Plus jamais de capacité qui suppose 2 niveaux sans que ce soit choisi.

## Ce qui change

- **Hypothèse explicite** (`service.etudier_payload`) : `niveaux_sous_sol` ∈ {1, 2}, 1 par défaut, sans objet
  en aérien. Entre dans le `study_id` (3 empreintes distinctes : aérien / sous-sol 1 / sous-sol 2 → 3 PDF).
- **Capacité bornée par le choix** (`geometrie.poser_sous_sol`) : un niveau enterré tient `per_niveau` places
  RÉELLES packées sur l'emprise (≈ 30 sur l'assiette Étang-Salé) ; la capacité du sous-sol est donc bornée à
  **`niveaux × per_niveau`**. Si la demande dépasse, le contrôle « Stationnement » échoue et la recherche
  réduit les logements — jamais un 2ᵉ niveau supposé. Threadé `service → etudier_complet → _rechercher →
  _evaluer → poser_sous_sol`.
- **Plan −1 et −2 dessinés** (`_dessiner_niveau`, kinds tagués `niveau`) : remplissage « niveau −1 d'abord, le
  reste au −2 ». L'écran (`PlanSousSol`) et le PDF (`_sous_sol_plan` + `_fc_niveau`) rendent **un plan par
  niveau** sur la vraie géométrie (emprise, allée, places, rampe). Aucun chevauchement −1/−2.
- **Facteur limitant suit** : en 1 niveau le stationnement plafonne (« ce qui limite : stationnement en
  sous-sol ») ; en 2 niveaux le parking ne borne plus, c'est la hauteur sur la pente qui reprend la main.
- **Écran = PDF** : libellé « sous-sol 1 niveau / 2 niveaux », ligne « LABUSE a dessiné N places au sous-sol
  (niveau −1 / niveaux −1 et −2) », cartouche hypothèses. Verrou `nombres_hors_payload` = **0** (1 et 2 niveaux).

## Recette — Étang-Salé, 23 T2 + 6 T3, résidence étudiante

| Choix | Résultat LABUSE | Face à l'architecte |
|---|---|---|
| **Sous-sol 1 niveau** | 30 logements, 30 places, **1 niveau** ; demande 29 **tient** (réserve 1) ; ce qui limite : stationnement en sous-sol | 29 logements, 31 places, 1 niveau |
| **Sous-sol 2 niveaux** | 44 logements max ; 44 places réparties **−1 : 30 · −2 : 14** ; ce qui limite : hauteur sur la pente | — |

Écart à l'architecte : **±1 logement / ±1 place** (packing géométrique du niveau vs décompte architecte ;
barème LABUSE T3 = 1,5 pl.). Le programme de 29 logements **tient sur un seul niveau**, comme l'architecte,
et passer à 2 niveaux augmente **strictement** la capacité (30 → 44) — le choix se propage de bout en bout.

## Gardes (toutes vertes)

| Garde | Résultat |
|---|---|
| `tsc -b` (front) | 0 erreur |
| `vitest` | **298 / 298** |
| pytest implantation + etude_v6 | **164 passed** ; 2 `test_route_*` échecs **pré-existants** (env `labuse_test` vide) |
| `chasse_docs` | **20 OK · 0 ECART · 0 SKIP** |
| `chasse_donnees` | **23 OK · 0 ECART · 2 SKIP** |
| verrou `nombres_hors_payload` | **0** (sous-sol 1 et 2 niveaux) |

Tests ajoutés/mis à jour : `test_niveaux_sous_sol_hypothese_explicite` (le choix borne la capacité, 2 > 1,
3 study_id distincts) ; `test_sous_sol_libere_le_sol_et_ajoute_des_logements` réécrit à la nouvelle sémantique
(1 niveau borné peut rester sous l'aérien ; 2 niveaux ≥ aérien).

## Captures (`captures/`)

- Écran : `ecran_1_soussol_1niveau_23T2_6T3.png`, `ecran_2_soussol_2niveaux_23T2_6T3.png`.
- PDF : `pdf_soussol_1niveau.pdf`, `pdf_soussol_2niveaux.pdf` (+ PNG des pages plan `pdf_1niv_plan`, `pdf_2niv_plan`).

## Réserve honnête

Le niveau enterré est packé sur la géométrie (≈ 30 places ici) : c'est la capacité d'**un** niveau, servie
telle quelle (jamais gonflée à l'emprise réglementaire brute). Services arrêtés en fin de session
(8830/6060/8860 libres). **Aucun merge.**
