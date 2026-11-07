-- PROD-SUITE-1 — D-F1 seul (88 biens du 26/09 → a_reverifier). Transaction contrôlée.
BEGIN;
SELECT count(*) AS candidats_26_09
FROM pige_biens b
WHERE b.statut = 'retiree'
  AND (b.retiree_le AT TIME ZONE 'Indian/Reunion')::date = DATE '2026-09-26'
  AND NOT EXISTS (SELECT 1 FROM event_log e WHERE e.dedup = 'pige:retiree:' || b.bien_id);

UPDATE pige_biens b SET statut = 'a_reverifier'
WHERE b.statut = 'retiree'
  AND (b.retiree_le AT TIME ZONE 'Indian/Reunion')::date = DATE '2026-09-26'
  AND NOT EXISTS (SELECT 1 FROM event_log e WHERE e.dedup = 'pige:retiree:' || b.bien_id);

INSERT INTO event_log (kind, titre, detail, source, dedup)
SELECT 'pige.statut_change',
       'Radar — 88 biens du 26/09 remis en « à revérifier » (NU5-FIX-1 D-F1)',
       'Retraits du 26/09 sur passe 100 % (blocage), sans preuve logée, jamais re-vérifiés.',
       'Radar', 'nu5fix1:d-f1:reverifier-26-09'
WHERE NOT EXISTS (SELECT 1 FROM event_log WHERE dedup = 'nu5fix1:d-f1:reverifier-26-09');

SELECT count(*) AS a_reverifier_total FROM pige_biens WHERE statut = 'a_reverifier';
COMMIT;
