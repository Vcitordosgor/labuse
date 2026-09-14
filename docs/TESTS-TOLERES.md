# TESTS TOLÉRÉS — la liste courte, jamais un tapis

Chaque échec de la suite DOIT avoir sa ligne ici — raison, date d'entrée, échéance — sinon
`labuse circuit suite` (et donc `deploy.sh`) REFUSE. Une échéance passée refuse aussi : une
tolérance n'est jamais éternelle. Une ligne dont le test repasse au vert est morte — la retirer.

Règle gravée au mandat TESTS-1 (14/09/2026) : **un mandat ne se déclare pas livré avec un test
rouge qu'il n'a pas nommé, daté et justifié.**

| test | raison | depuis | échéance |
|---|---|---|---|
| tests/test_run_serving_coherence.py::test_tuiles_mvt_materialisees_sur_le_run_servi | Tuiles MVT matérialisées sur q_v14 alors que le run servi est q_v11_m137 (COHERENCE-RUN-1 a bâti q_v14, BASCULE-1 a ramené le servi sans re-matérialiser). Réparation = UN geste de Vic sur la base servie : `labuse build-mvt --label q_v11_m137` (~30 s, matérialisation seule, aucun re-scoring) — geste refusé au mandat TESTS-1 (écriture sur la base servie partagée hors périmètre). | 2026-09-14 | 2026-09-21 |
