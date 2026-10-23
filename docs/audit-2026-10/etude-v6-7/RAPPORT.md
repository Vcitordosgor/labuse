# ETUDE-V6-7 — recette (le rapport liste les tests, pas des phrases)

Branche `feat/etude-v6`, **pas de merge**. Méthode : chaque règle est prouvée par un test automatique qui
échouait avant le correctif et passe après. Un lot = un commit.

## Tests par item (tous `@pytest.mark.reel`, base servie q_v20, sauf vitest)

| Item | Test | Fichier | Statut |
|---|---|---|---|
| 1 — plan = typologie client, au prorata | `test_plan_respecte_la_typologie_client_en_proportion` | test_etude_v6_capacite.py | ✅ |
| 1 — « votre programme » = demande exacte quand elle tient | vérifié par le tableau (aérien 11/5/2/5 → plan 11×T1·5×T2·2×T3·5×T4) | TABLEAU-8-ENDROITS.md | ✅ |
| 2 — une seule vérité (tenus/dessinés/places/surface/mixité/dépassement) | `test_une_seule_verite_sur_le_programme_dessine` | test_etude_v6_capacite.py | ✅ |
| 3 — sous-sol 1 niveau (2 niveaux retiré) + double rangée + emprise dessinée | `test_sous_sol_un_seul_niveau_et_double_rangee`, `test_niveaux_sous_sol_un_seul_niveau_toujours` | test_etude_v6_capacite.py | ✅ |
| 3 — disponibilité (PPR / règlement / « à confirmer ») | `test_sous_sol_disponibilite_servie` | test_etude_v6_capacite.py | ✅ |
| 4 — sol libéré utilisé + phrase chiffrée si sous le plafond | `test_sous_sol_sol_libere_explique` | test_etude_v6_capacite.py | ✅ |
| 5 — jamais « aérien » dans une étude sous-sol | `test_sous_sol_jamais_aerien_dans_le_pdf` | test_etude_v6_capacite.py | ✅ |
| 6 — jauge vraie forme (bande) + capacité −1, écart ≤ 20 % (aérien ET sous-sol) | `test_jauge_logements_proche_du_calcul_mixte` | test_etude_v6_capacite.py | ✅ |
| 7 — « Hypothèses modifiables » + « Testez en sous-sol » retirés du résultat | `V6-7 (item 7) … RETIRÉS` | EtudeV6.test.tsx | ✅ |
| 8 — Retour/Continuer/Analyser colonne droite, sticky | rendu (`lg:sticky`), vitest parcours inchangé | EtudeV6.test.tsx | ✅ |
| 9 — « Lire l'article » → Géoportail de l'urbanisme (idurba) | `test_lire_article_lien_geoportail_urbanisme` | test_etude_v6_capacite.py | ✅ |

Tests V6-5/V6-6 « 2 niveaux » réécrits au modèle 1-niveau ; `test_numero_deterministe`, `test_sous_sol_libere_le_sol`, jauge mocks recalibrés.

## Commits (un lot = un commit)

- `0b9cc77d7` Lot 1 (items 1-2) — typologie client + prorata + vérité unique.
- `01f919051` Lot 2 (items 3-5) — sous-sol 1 niveau, double rangée, mode réel, sol libéré.
- `f6580d4e5` Lot 3 (item 6) — jauge « vraie forme » (bande) + capacité du −1.
- `d5ea4a3de` Lot 4 (items 7-8) — hypothèses retirées, boutons colonne droite sticky.
- `7115d694a` Lot 5 (item 9) — « Lire l'article » → Géoportail de l'urbanisme.

## Gardes finales

| Garde | Résultat |
|---|---|
| `tsc -b` | 0 |
| `vitest` | **297 / 297** |
| pytest implantation + etude_v6 | **187 passed** ; 2 `test_route_*` échecs **pré-existants** (env `labuse_test` vide) |
| `chasse_docs` | **20 OK · 0 ECART · 0 SKIP** |
| `chasse_donnees` | **23 OK · 0 ECART · 2 SKIP** |
| verrou `nombres_hors_payload` | **0** (aérien + sous-sol) |

## Recette — une seule valeur par chiffre (tableau)

`captures/TABLEAU-8-ENDROITS.md` relève, pour chaque chiffre, sa valeur UNIQUE (payload = écran = PDF, le
PDF étant rendu du même payload — verrou nombres_hors_payload = 0) :

**Étang-Salé AW99-451-624-625, étudiant, 11 T1 + 5 T2 + 2 T3 + 5 T4, aérien** :
demandés 23 · tenus = dessinés = resume.logements **23** · plan 11×T1·5×T2·2×T3·5×T4 · places (resume =
stationnement = imposées) **27** · surface tenue **1 150 m²** · mixité **5** · n° doc **EF-72cb87f9**.

**Étang-Salé, étudiant, 39 T1 + 5 T2 + 9 T3 + 20 T4, sous-sol 1 niveau** :
demandés 73 · tenus = dessinés = resume.logements = dépassement.total_tiennent **26** · plan 14×T1·6×T4·4×T2·2×T3
(proportion de la demande, réduit au prorata) · places **30** (au −1) · surface tenue **1 264 m²** · mixité
**6** · n° doc **EF-eb14911f** · aucun « aérien ».

Captures : `ecran_1_aerien_11-5-2-5.png`, `ecran_2_etape3_stationnement_jauge.png`, `ecran_3_soussol_39-5-9-20.png`
+ PDF `pdf_aerien_11-5-2-5.pdf`, `pdf_soussol1_39-5-9-20.pdf` (+ PNG couvertures).

Services arrêtés (8830/6060/8860 libres). **Aucun merge.**
