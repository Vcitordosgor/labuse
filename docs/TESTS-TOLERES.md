# TESTS TOLÉRÉS — la liste courte, jamais un tapis

Chaque échec de la suite DOIT avoir sa ligne ici — raison, date d'entrée, échéance — sinon
`labuse circuit suite` (et donc `deploy.sh`) REFUSE. Une échéance passée refuse aussi : une
tolérance n'est jamais éternelle. Une ligne dont le test repasse au vert est morte — la retirer.

Règle gravée au mandat TESTS-1 (14/09/2026) : **un mandat ne se déclare pas livré avec un test
rouge qu'il n'a pas nommé, daté et justifié.**

| test | raison | depuis | échéance |
|---|---|---|---|

*(Aucune tolérance en cours — la table vide est l'état normal.)*

*ROUGES-RESTANTS (19/10/2026, fix/rouges-restants) — les trois tolérances PRE-DEPLOY-1 du 29/09
sont LEVÉES avant leur échéance du 20/10 : v2a et g4 étaient repassés au vert (lignes mortes —
« Population légale » câblée par COHERENCE-FIX-1) ; lot1 est ÉTEINT (V1c : 5 tables d'exploitation
déclarées au registre dont `parcel_couche_intersection_build`, + purge du staging SM1 du worktree
voisin ; V6b : dérive du re-run q_v19 du 18/10 acceptée ; V7a : le verrou rejoue la rétention
sous-pixel z < 12 du tuyau — `geom_rendue_sql`, source unique).*
