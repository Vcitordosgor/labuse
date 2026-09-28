# ALGO-FIX-1 — Tout le monde lit le même run, et la bascule bascule tout

- **Branche** `fix/algo-fix-1` depuis `origin/main` `308297e4` (« Merge branch 'fix/exports-fix-1' » — vérifié mergée).
- **Worktree** `~/Desktop/labuse-algofix` · **API** 127.0.0.1:8635 · modèle Opus · base `labuse`.
- **Origine** ALGO-AUDIT-1 (`040af558`). On corrige les 4 points, rien d'autre. Un commit par point, après recette. Aucun `residuel-serve`, aucun `golden promote`, aucun run. Aucune écriture dans les tables servies (mesures en table TEMP + rollback).

## Étape 0 — état servi (relevé 28/09/2026)

| Pointeur | Valeur | Attendu |
|---|---|---|
| `residuel_runs.is_served` | **seq 10** (« q_v15 assiette gabarit ») | seq 10 ✓ |
| `served_manifest.json → residuel_run_seq` | **8** (ment vs is_served 10 = E6) | 8 ✓ |
| `served_manifest.json → scoring_run` | **q_v11_m137** | q_v11_m137 ✓ |
| `score_labuse` sous le servi | 0 ligne q_v11_m137 · 431 663 q_v15 (Score LABUSE NULL partout = E4) | — |

## Tableau des points

| # | Fait / STOP | Preuve (test · capture) | Commit |
|---|---|---|---|
| 1 | **FAIT** — `residuel_runs.is_served` = seule vérité. `basculer()` ne lit ni n'écrit plus le résiduel (suppression du `set_served` piloté par le manifeste) ; le manifeste RECOPIE `is_served` (avant + précédent) ; `residuel-serve` fait suivre le miroir. `deploy/` ne pilote pas le résiduel (dump PG + fichier suivent la vérité) → rien à changer. | Bascule à blanc `q_v11_m137→q_v12` (base réelle, fichiers temp + rollback) partant d'un manifeste périmé (8) → **is_served reste 10**, manifeste recopie **10** (pas 8). `tests/test_algofix1_point1_residuel.py` (2, avant + retour arrière). | `8bb19080` |
| 2 | **FAIT** — `SCORE_LABUSE_RUN` (constante figée à l'import, app.py:3230) → `_score_labuse_run()` relu à la requête, propagé aux 5 sites (3538/3778/3798/5727/7524). Override admin `LABUSE_SCORE_RUN` conservé. | Process API VIVANT (PID 45683, inchangé) : fiche EO0796 `analyse_labuse` **None** (q_v11_m137) → bascule à blanc manifeste `scoring_run=q_v15` → **{bande D, signal faible}** sans redémarrage → restauré None. `captures/point2-hotswap.txt` · `tests/test_algofix1_point2_score_labuse.py` (3). | `3549330f` |
| 3 | **FAIT (backend)** — panneau Faisabilité : hors saisie, la SDP résiduelle vient du RUN SERVI `parcel_residuel` (bati_garde, et terrain_libere si terrain nu) ; le moteur live ne recalcule que sur chiffres SAISIS (overrides/test). Fiche §Potentiel, Dossier garde+§10, Copilote lisaient déjà le servi (post EXPORTS-FIX-1) → 0 correction. | Recette : EO0796 **179**, AX0990 **1619**, AO1424 **0** (voir avant/après). Saisie → live prouvé (EO0796+override 187, AX0990+test 1642). `captures/point3-sdp.txt` · `tests/test_algofix1_point3_sdp_servie.py` (4). | `9495cc60` |
| 3-bis | **FAIT (front, autorisé par Vic)** — STOP levé : l'onglet Faisabilité s'ouvre par défaut sur `bati_garde` pour les parcelles BÂTIES (première capacité vue = résiduel servi 179, pas l'enveloppe démolition 338). Parcelle NUE → backend rétrograde `terrain_libere` (UI suit `pan.scenario`) ; choix explicite prioritaire. `constructibilite.tsx:419`. | EO0796 avant (défaut terrain_libere) 338 → après (défaut bati_garde) **179** « Encore 179 m²… bâti conservé ». `captures/point3-faisa-defaut.txt` · `Faisabilite.test.tsx` maj (défaut + bascule 26↔245). tsc 0 · vitest 225. | `41ca9ab3` |
| 4 | **FAIT** — front : `SOURCE` lu à l'exécution (`/config/run` fetch au boot, plus figé au build). Tuiles : `mesurer_rebuild_commune` (table TEMP) + `planifier_reconstruction_tuiles` (< 15 min → enchaîne, sinon ligne « À faire » bloquante) câblés à la bascule ; `composer_a_faire` pose la ligne rouge « Reconstruire les tuiles » quand mvt périmé ; `MapView` bandeau « Carte pas à jour » piloté par `/map/tiles/meta.perime`. | `/config/run`=q_v11_m137 ; mesure Saint-Paul 51 129 → île ~0,1 min → **enchaine** ; `perime=true` ; ligne « À faire » bloquante présente. `captures/point4-tuiles.txt` · `tests/test_algofix1_point4_tuiles.py` (7) + `test_run_serving_coherence` maj. tsc 0 · vitest 225. | `71e57e7b` |

## Avant / après sur les 3 témoins

| Grandeur (source) | 97408000AO1424 | 97415000EO0796 | 97415000AX0990 |
|---|---|---|---|
| Vérité servie `parcel_residuel` | 0 (terrain_exigu) | **179** | **1619** |
| Fiche §Potentiel `sdp_residuelle_m2` (avant = après) | — / zone A | 179 / 179 | 1619 / 1619 |
| Dossier page de garde « SDP RESTANTE » (avant = après) | — | 179 / 179 | 1619 / 1619 |
| Dossier §10 (avant = après, post exports-fix-1) | non calculable (zone A) | défère à « la SDP ci-dessus » = 179 | défère à 179/1619 |
| **Faisabilité — scénario résiduel** (bati_garde / terrain nu) | **avant 0 → après 0** | **avant 187 → après 179** | **avant 1642 → après 1619** |
| Faisabilité — terrain_libere AVEC bâti (enveloppe démolition, live) | s.o. | 338 (inchangé — grandeur distincte) | s.o. (terrain nu) |
| Score LABUSE fiche (Point 2, à la bascule à blanc q_v15) | None→bande 0 | None→bande **D** | None→bande A |

*Zone : la fiche et le servi disent zone **A** pour AO1424 (dominante 98,6 %) ; l'onglet Faisabilité étiquette la portion constructible UA (0,0 %). La SDP est 0 des deux côtés. Résolution de zone = module zonage, hors périmètre « la SDP lit le servi » — non touché.*

## STOP (levé)

- **Point 3 — défaut de l'onglet Faisabilité pour les parcelles BÂTIES : STOP LEVÉ (autorisé par Vic, commit 3-bis).** L'onglet s'ouvrait par défaut sur `terrain_libere` (`constructibilite.tsx:419`) = l'enveloppe démolition-reconstruction (338 pour EO0796). Il s'ouvre désormais sur `bati_garde` = le résiduel servi (179), cohérent avec fiche/Dossier ; « Terrain libéré » reste à un clic. Parcelle NUE → backend rétrograde `terrain_libere` (l'UI suit `pan.scenario`, rien à masquer) ; un choix explicite (session/projet) reste prioritaire. Pour les parcelles NUES, le défaut `terrain_libere` lit déjà le servi (recette OK).

## Conclusion

**Oui** — une bascule `q_v15` fait maintenant tout basculer d'un coup, sans reculer le résiduel : le scoring, la cascade, la division et le Score LABUSE suivent le pointeur vivant à chaud (point 2) ; le résiduel a une seule vérité `is_served` que la bascule scoring ne touche plus (point 1) ; la SDP montrée au client lit le run servi partout, jusqu'au défaut d'ouverture de l'onglet Faisabilité (point 3 + 3-bis) ; et le front lit le run à l'exécution pendant que les tuiles se reconstruisent ou se signalent périmées (point 4).
