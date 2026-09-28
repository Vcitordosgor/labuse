# TESTS TOLÉRÉS — la liste courte, jamais un tapis

Chaque échec de la suite DOIT avoir sa ligne ici — raison, date d'entrée, échéance — sinon
`labuse circuit suite` (et donc `deploy.sh`) REFUSE. Une échéance passée refuse aussi : une
tolérance n'est jamais éternelle. Une ligne dont le test repasse au vert est morte — la retirer.

Règle gravée au mandat TESTS-1 (14/09/2026) : **un mandat ne se déclare pas livré avec un test
rouge qu'il n'a pas nommé, daté et justifié.**

| test | raison | depuis | échéance |
|---|---|---|---|
| tests/verrous/test_lot2_sources.py::test_v2a_68_partout_sur_la_base_reelle | Base réelle mi-opération : source « Population légale (INSEE via geo.api.gouv) » ajoutée par COHERENCE-FIX-1 mais pas encore câblée au pont NOM_VERS_SLUG. LEVÉE par COHERENCE-FIX-1 (câblage source → réservoir). Hors périmètre PRE-DEPLOY-1. | 2026-09-29 | 2026-10-20 |
| tests/verrous/test_garanties.py::test_g4_vert_et_vide_jamais_a_jour | Base réelle : la même source « Population légale (INSEE) » n'a ni sonde de fraîcheur ni raison de non-vérifiabilité (ajoutée par COHERENCE-FIX-1). LEVÉE par COHERENCE-FIX-1 (sonde/raison de la source). Hors périmètre PRE-DEPLOY-1. | 2026-09-29 | 2026-10-20 |
| tests/verrous/test_lot1_tables.py::test_verrous_lot1_passent_sur_la_base_reelle | Base réelle : `parcel_couche_intersection_build` orphelin = `labuse build-intersections` de Vic EN COURS (cf. PRE-DEPLOY-1 lot D). LEVÉE quand Vic termine build-intersections (bascule staging → table finale). À revérifier après. | 2026-09-29 | 2026-10-20 |

*PRE-DEPLOY-1 (29/09/2026) — trois tolérances de BASE RÉELLE, chacune levée par le mandat nommé
(COHERENCE-FIX-1 pour le câblage « Population légale » ; build-intersections de Vic pour l'orphelin).
Ce sont des `@pytest.mark.local` (base servie réelle), hors CI. Les autres échecs de l'étape 0
(les_24/V6b, f4/fuite inter-fichiers, verrou VEFA-à-l'acte périmé) ont été CORRIGÉS en code.*
