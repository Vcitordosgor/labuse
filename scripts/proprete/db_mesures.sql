-- PROPRETE-1 — Domaine 5 (base de données), LECTURE SEULE (catalogues système).
-- Rejouable : psql "$PGURL" -f scripts/proprete/db_mesures.sql

\echo == taille base & nb tables ==
SELECT count(*) AS tables,
       pg_size_pretty(sum(pg_total_relation_size(c.oid))) AS total
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind='r' AND n.nspname='public';

\echo == 20 plus grosses tables ==
SELECT relname,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total,
       pg_size_pretty(pg_indexes_size(c.oid)) AS idx,
       reltuples::bigint AS est_rows
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind='r' AND n.nspname='public'
ORDER BY pg_total_relation_size(c.oid) DESC LIMIT 20;

\echo == tables de runs / dry-runs / snapshots / doublons ==
SELECT relname, pg_size_pretty(pg_total_relation_size(c.oid)) AS total
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind='r' AND n.nspname='public'
  AND relname ~* '(dryrun|_run|run_|_old|_bak|_tmp|_backup|_v2bis|snapshot|_copy)'
ORDER BY pg_total_relation_size(c.oid) DESC;

\echo == dead tuples / bloat (>50k) ==
SELECT relname, n_live_tup, n_dead_tup,
  CASE WHEN n_live_tup>0 THEN round(100.0*n_dead_tup/n_live_tup,1) ELSE 0 END AS pct_dead,
  pg_size_pretty(pg_total_relation_size(relid)) AS sz
FROM pg_stat_user_tables WHERE n_dead_tup > 50000
ORDER BY n_dead_tup DESC LIMIT 15;

\echo == index jamais scannés (idx_scan=0, non-unique, >1MB) ==
SELECT s.relname, s.indexrelname,
       pg_size_pretty(pg_relation_size(s.indexrelid)) AS sz, s.idx_scan
FROM pg_stat_user_indexes s JOIN pg_index i ON i.indexrelid=s.indexrelid
WHERE s.idx_scan=0 AND NOT i.indisunique AND NOT i.indisprimary
  AND pg_relation_size(s.indexrelid) > 1048576
ORDER BY pg_relation_size(s.indexrelid) DESC LIMIT 25;

\echo == total index inutilises ==
SELECT count(*) AS n, pg_size_pretty(coalesce(sum(pg_relation_size(s.indexrelid)),0)) AS taille
FROM pg_stat_user_indexes s JOIN pg_index i ON i.indexrelid=s.indexrelid
WHERE s.idx_scan=0 AND NOT i.indisunique AND NOT i.indisprimary;

\echo == scans sequentiels lourds ==
SELECT relname, seq_scan, idx_scan, n_live_tup,
       pg_size_pretty(pg_total_relation_size(relid)) AS sz
FROM pg_stat_user_tables WHERE seq_scan > 1000 AND n_live_tup > 100000
ORDER BY seq_scan DESC LIMIT 12;

\echo == reglages Postgres vs taille base ==
SELECT name, setting, unit FROM pg_settings
WHERE name IN ('shared_buffers','work_mem','maintenance_work_mem',
               'effective_cache_size','max_wal_size','max_connections');
