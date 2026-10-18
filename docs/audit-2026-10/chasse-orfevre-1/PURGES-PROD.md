# Purges prod — FIX-ORFEVRE-1 point 5 (AUCUNE exécutée)

Rédigé le 18/10/2026. Chaque bloc = une inspection (`SELECT`) à jouer D'ABORD, puis la purge.
À jouer sur la base de PROD uniquement après lecture du résultat de l'inspection — les ids
cités par l'audit (mails 48-59, pipeline 91-132…) sont ceux de la base de dev et ne valent
rien en prod. Le code des points 2 et 4 est self-healing pour une partie (voir notes).

## 1. Les 12 mails de recette en file (ORF-07 / A-14)

Dry-run du 16/10, état `a_rejouer`, dont 3 vers le compte supprimé 111 (ids dev).

```sql
-- Inspection
SELECT id, etat, destinataire, sujet, compte_id, cree_at, prevu_at
FROM mail_queue
WHERE etat IN ('a_rejouer', 'en_attente')
ORDER BY cree_at;

-- Purge ciblée : les rejouables du dry-run de recette du 16/10
DELETE FROM mail_queue
WHERE etat = 'a_rejouer'
  AND cree_at >= '2026-10-16 00:00:00+04' AND cree_at < '2026-10-17 00:00:00+04';

-- Ceinture : tout dû vers un compte qui n'existe plus
DELETE FROM mail_queue q
WHERE q.etat IN ('a_rejouer', 'en_attente')
  AND q.compte_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM comptes c WHERE c.id = q.compte_id);
```

Note : depuis le point 4 (`f2fa133b`), `mailfile.consommer` passe de lui-même en `annule`
tout dû vers un compte supprimé ou plus vieux que `LABUSE_MAIL_FRAICHEUR_MAX_JOURS` (7 j).
La purge évite seulement d'attendre ce passage.

## 2. Les lignes consultation_log écrites par l'audit (angle C, 23 lignes)

Écrites le 18/10 entre 17:27 et 17:45 (+04) par les sondes TestClient de l'angle C
(SQL d'origine : ANGLE-C.md « Effet de bord déclaré »). L'angle G (parcours front du
18/10 au soir) a pu en écrire d'autres sur la base de DEV — l'inspection tranche.

```sql
-- Inspection
SELECT count(*), min(ts), max(ts)
FROM consultation_log
WHERE ts BETWEEN '2026-10-18 17:27:00+04' AND '2026-10-18 17:45:00+04';

-- Purge (fenêtre de l'angle C)
DELETE FROM consultation_log
WHERE ts BETWEEN '2026-10-18 17:27:00+04' AND '2026-10-18 17:45:00+04';

-- Optionnel (A-18) : les consultations à idu forgé des tests passés
DELETE FROM consultation_log
WHERE idu IN ('00000000XX0000', '97416000QA0000', '97416000QA0001', '97416000QA0002');
```

## 3. Les [GB-TEST] (K-3 / A-17, 38 lignes en dev ids 91→132)

```sql
-- Inspection
SELECT id, left(notes, 60) FROM pipeline_entries WHERE notes LIKE '%[GB-TEST]%' ORDER BY id;

-- Purge
DELETE FROM pipeline_entries WHERE notes LIKE '%[GB-TEST]%';
```

## 4. Annexe — accompagnement du déploiement des points 2-4 (préparées au point 4)

`ensure_idempotence` (ORF-09) et les gardes du worker (ORF-07) se jouent seuls au boot du
nouveau code ; ces SQL maîtrisent seulement le moment. ORF-12 : après accord Vic.

```sql
-- ORF-09 : dédoublonner la pige AVANT le premier boot (sinon le code le fait lui-même)
DELETE FROM pige_depots a USING pige_depots b
WHERE a.hash = b.hash AND a.hash <> '' AND a.id > b.id;
CREATE UNIQUE INDEX IF NOT EXISTS uq_pige_depots_hash ON pige_depots (hash) WHERE hash <> '';
DELETE FROM event_log a USING event_log b
WHERE a.dedup LIKE 'pige:%' AND b.dedup = a.dedup
  AND timezone('Indian/Reunion', a.ts)::date = timezone('Indian/Reunion', b.ts)::date
  AND a.id > b.id;
CREATE UNIQUE INDEX IF NOT EXISTS uq_event_log_pige_jour
  ON event_log (dedup, (timezone('Indian/Reunion', ts)::date)) WHERE dedup LIKE 'pige:%';

-- ORF-12 : résidus de recette (APRÈS ACCORD VIC)
UPDATE comptes SET statut = 'resilie' WHERE lower(nom) = 'recette onb' AND statut = 'actif';
UPDATE utilisateurs SET statut = 'invite' WHERE statut = 'actif' AND (hash IS NULL OR hash = '');
DELETE FROM evenements_compte e
WHERE e.compte_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM comptes c WHERE c.id = e.compte_id);

-- ORF-14 / ORF-15 / ORF-16 : rattrapage du stock (le code corrige le flux)
UPDATE piscines pi SET commune = p.commune
FROM parcels p WHERE pi.idu = p.idu AND (pi.commune IS NULL OR pi.commune = '');
UPDATE m10_permit_delais SET valide = false WHERE valide AND date_autorisation < date_depot;
UPDATE score_labuse_runs r
SET n_parcelles = (SELECT count(*) FROM score_labuse s WHERE s.run_label = r.run_label);
```
