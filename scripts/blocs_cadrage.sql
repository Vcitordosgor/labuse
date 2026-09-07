-- Cadrage Blocs fonciers (lecture seule) — composantes connexes de parcelles
-- contiguës (ST_DWithin 0,5 m sur geom_2975) appartenant au même SIREN.
-- L'union-find final est fait hors SQL (les arêtes sont exportées) — cf. A-cadrage.md.

-- Parcelles PM des SIREN possédant >= 2 parcelles sur l'île
DROP TABLE IF EXISTS _pm_parc;
CREATE TEMP TABLE _pm_parc AS
SELECT pa.id AS pid, pa.idu, p.siren, pa.geom_2975, pa.surface_m2, pa.commune
FROM parcelle_personne_morale p
JOIN parcels pa ON pa.idu = p.idu
WHERE p.siren IS NOT NULL AND p.siren <> ''
  AND p.siren IN (
    SELECT p2.siren FROM parcelle_personne_morale p2
    JOIN parcels pa2 ON pa2.idu = p2.idu
    WHERE p2.siren IS NOT NULL AND p2.siren <> ''
    GROUP BY p2.siren HAVING count(*) >= 2);
CREATE INDEX ON _pm_parc USING gist(geom_2975);
CREATE INDEX ON _pm_parc(siren);

-- Arêtes de contiguïté (même SIREN, à moins de 0,5 m)
DROP TABLE IF EXISTS _blocs_edges;
CREATE TEMP TABLE _blocs_edges AS
SELECT a.pid AS a, b.pid AS b
FROM _pm_parc a JOIN _pm_parc b
  ON a.siren = b.siren AND a.pid < b.pid
 AND ST_DWithin(a.geom_2975, b.geom_2975, 0.5);

SELECT count(*) AS nb_parcelles_pm_multi FROM _pm_parc;
SELECT count(*) AS nb_aretes FROM _blocs_edges;
-- Distribution SIREN par nombre de parcelles possédées (contiguës ou non)
SELECT CASE WHEN n=1 THEN '1' WHEN n BETWEEN 2 AND 5 THEN '2-5'
            WHEN n BETWEEN 6 AND 10 THEN '6-10' ELSE '10+' END AS taille,
       count(*) AS nb_siren, sum(n) AS nb_parcelles
FROM (SELECT p.siren, count(*) n FROM parcelle_personne_morale p
      JOIN parcels pa ON pa.idu=p.idu
      WHERE p.siren IS NOT NULL AND p.siren<>'' GROUP BY p.siren) s
GROUP BY 1 ORDER BY min(n);
