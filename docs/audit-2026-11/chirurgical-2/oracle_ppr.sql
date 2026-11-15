SET statement_timeout='300s';
SET max_parallel_workers_per_gather=0;

WITH sel AS (
  SELECT id, idu, commune, surface_m2, ST_MakeValid(geom_2975) AS g, ST_Area(geom_2975) AS parc_area
  FROM parcels
  WHERE idu IN ('97422000AD0887','97416000HT0538','97403000AR1517','97404000AM0838',
                '97417000AO0050','97411000IS0448','97404000AY0153','97414000CO0153',
                '97421000BN0260','97422000BW2635','97412000CV0446','97424000AO1198')
),
ppr AS (
  SELECT subtype, ST_Subdivide(ST_MakeValid(geom_2975), 256) AS g
  FROM spatial_layers
  WHERE kind='ppr' AND subtype IN ('INTERDICTION','PRESCRIPTION')
),
inter AS (
  SELECT s.idu, s.commune, s.surface_m2, s.parc_area, p.subtype,
         ST_Area(ST_Intersection(s.g, p.g)) AS a
  FROM sel s
  JOIN ppr p ON ST_Intersects(s.g, p.g)
)
SELECT s.idu, s.commune,
       round(s.surface_m2::numeric,1) AS surface_m2,
       round(s.parc_area::numeric,1)  AS parc_area_m2,
       round(COALESCE(SUM(a) FILTER (WHERE subtype='INTERDICTION'),0)::numeric,1) AS red_area_m2,
       round((100*COALESCE(SUM(a) FILTER (WHERE subtype='INTERDICTION'),0)/NULLIF(s.parc_area,0))::numeric,1) AS red_pct,
       round((100*COALESCE(SUM(a) FILTER (WHERE subtype='PRESCRIPTION'),0)/NULLIF(s.parc_area,0))::numeric,1) AS blue_pct
FROM sel s
LEFT JOIN inter i ON i.idu=s.idu
GROUP BY s.idu, s.commune, s.surface_m2, s.parc_area
ORDER BY s.idu;
