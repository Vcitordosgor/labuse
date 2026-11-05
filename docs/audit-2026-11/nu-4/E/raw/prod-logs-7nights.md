# Prod logs — 7 nights (2026-10-29 → 2026-11-05) — raw subagent report

Read-only ssh gather on labuse-vps. No writes. Source of truth: `job_runs`, `event_log`,
`pige_annonces`, `/var/backups/labuse`. Cron in Réunion local (UTC+4); job_runs ts in UTC.

## Headline findings
1. **[HIGH] calcul-nuit never finishes a full pass.** 11-03 timed out after 14341s
   (`SousProcessTimeout` → `IdleInTransactionSessionTimeout`); 11-04/11-05 "ok" are partial:
   `"abandon":"fin de fenêtre 5h atteinte…","promu":false`. Incident "Job jamais réussi :
   calcul-nuit" (11-03 23:00, 11-04 00:00 "toujours ouvert") has NO résolu line.
2. **[HIGH→resolved] backup-postgres failed 4 straight nights (10-30→11-02)** on lock
   acquisition / admin-command termination. Anti-shrink guard worked (partial dumps deleted,
   nothing corrupt kept). Fixed by manual retry 11-02 16:33. Dumps ~6.5GB, off-VPS copy +
   restore test green (11-04/11-05).
3. **[MED→resolved] coherence-banc failed 5 straight nights (10-29→11-02)**: FileNotFoundError
   `…/COHERENCE-1/ECHANT…` after a deploy. Fixed 11-02; green since (574–921s).
4. **[MED] Radar "passe de confirmation SUSPECTE" 3 nights running, escalating 32% → 43% →
   100% de retraits** (event_log 11-02/03/04). Data-quality signal to triage.
5. **[MED] Disk pressure.** "Disque à 94.6% (seuil 85%)" 11-05 00:15; now `/` 82% (78G/96G);
   `/var/backups/labuse` = 25G (4× ~6.5GB dumps). Retention near ceiling.
6. **[LOW known] verrous V1c/V6b broken, 1 source quarantined** (pre-existing, AUTONOMIE-2).
7. **[LOW known] 3 Overpass/OSM sources permanently injoignable** (mirror outage); BODACC
   non-JSON illisible; SIS/OCS GE/SCOT recovered by 11-05.
8. **[INFO] No job_runs history before 11-03** for injection/calcul/john/resume (registry
   regenerated 11-02 when q_v21 went live). API `labuse.service` NRestarts=0, readyz green.

Full per-job detail and the timeline table are reproduced in RAPPORT.md §Prod.
