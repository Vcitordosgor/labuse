# Domaine 9 — Dates, millésimes et fraîcheur servis

## Verdict (3 lignes)
**433 229 parcelles servies (run q_v18 / run_seq 15), 99 sources vitrine, 2 tables dérivées versionnées — passées au crible.** 7 invariants vérifiés, **0 violation FAUX-CLIENT ni INCOHÉRENT**. Le run est cohérent PARTOUT (manifeste = `residuel_runs.is_served` = `mvt_meta` = `score_labuse` = `score_labuse_runs`), aucune date de source dans le futur, les 2 tables dérivées (pc_caducs, veille succession) portent la version de règle du CODE. Resté muet : la fraîcheur AMONT réelle (impossible à sonder hors cron), et le fait que `source_millesime` est un **label publié** (vérité par construction), non recalculé depuis le max de chaque table — donc non vérifiable table-par-table sauf là où une garde existe déjà (RPLS/PM/BODACC dans `chasse_donnees.py`).

## Invariants

| # | règle (une phrase FR) | requête/script | parcelles/lignes passées | violations |
|---|---|---|---|---|
| I1 | Aucune date de source servie (`source_horizon_at`, `last_sync_at`, `fraicheur_calcule_at`) n'est postérieure à aujourd'hui (2026-10-14). | `SELECT id,name FROM data_sources WHERE source_horizon_at > DATE '2026-10-14' OR last_sync_at > TIMESTAMPTZ '2026-10-14 23:59:59+00' OR fraicheur_calcule_at > TIMESTAMPTZ '2026-10-14 23:59:59+00';` | 157 sources | 0 |
| I2 | Aucun `source_millesime` affiché ne contient une année future (2027+). | `SELECT id,name,source_millesime FROM data_sources WHERE source_millesime ~ '(202[7-9]|20[3-9][0-9])';` | 157 sources | 0 |
| I3 | Le run servi est identique dans les 5 pointeurs : manifeste, `residuel_runs.is_served`, `mvt_meta.run_label`/`residuel_seq`, `score_labuse` (a q_v18), `score_labuse_runs.cascade_label` = manifeste.cascade_run. | voir « requête RUN-COHERENCE » ci-dessous | 5 pointeurs | 0 |
| I4 | `parcel_residuel` (vue servie) lit le run_seq de `residuel_runs.is_served` — jamais un run figé — et son effectif = l'effectif `score_labuse` du run servi. | `SELECT count(*) FROM parcel_residuel;` (433229) `=` `SELECT count(*) FROM score_labuse WHERE run_label='q_v18';` (433229) ; viewdef pointe `WHERE run_seq=(SELECT run_seq FROM residuel_runs WHERE is_served)`. | 433 229 parcelles | 0 |
| I5 | Chaque table DÉRIVÉE (pc_caducs, parcel_veille_succession) porte dans `fraicheur_etat` la version de règle COURANTE du code (sinon elle sert l'ancienne règle en silence — bug CHASSE-3). | `SELECT cle,valeur FROM fraicheur_etat WHERE cle LIKE 'derive:%';` comparé à `pc_caducs.RULE_VERSION` + `VEILLE_SUCCESSION_RULE_VERSION`. | 2 tables dérivées | 0 |
| I6 | Le millésime servi par l'API `/sources` = le `source_millesime` de la base passé par le producteur unique `millesime_source.composer` (pas deux vérités dans un même document). | `curl /sources` → comparé à `SELECT source_millesime FROM data_sources`. | 99 sources vitrine | 0 |
| I7 | Les millésimes à table sous-jacente datée (Sitadel, DVF) ne prétendent pas un millésime postérieur au max réel de la table. | `SELECT max(date) FROM sitadel_permits;` (2026-08-31, affiché « 2026-08 ») ; `SELECT max(date_mutation) FROM dvf_mutations;` (2026-08-10, affiché cap 2025). | 50 809 Sitadel + 29 566 DVF | 0 bloquant (1 note V-01) |

### requête RUN-COHERENCE (I3, rejouable)
```sql
SET statement_timeout='120s';
SELECT
  (SELECT run_seq FROM residuel_runs WHERE is_served)            AS served_resseq,  -- 15
  (SELECT label   FROM residuel_runs WHERE is_served)            AS served_label,   -- q_v18
  (SELECT value FROM mvt_meta WHERE key='run_label')             AS mvt_run,        -- q_v18
  (SELECT value FROM mvt_meta WHERE key='residuel_seq')          AS mvt_resseq,     -- 15
  EXISTS(SELECT 1 FROM score_labuse WHERE run_label='q_v18')     AS score_has_qv18, -- t
  (SELECT cascade_label FROM score_labuse_runs WHERE run_label='q_v18'); -- q_v18_sources
-- à comparer à config/served_manifest.json :
--   scoring_run=q_v18, cascade_run=q_v18_sources, mvt_run=q_v18, residuel_run_seq=15
```

## Violations

Aucune violation FAUX-CLIENT ni INCOHÉRENT. Deux observations de moindre gravité :

### V-01 — ROBUSTESSE (donnée, pas invariant) : 1 mutation DVF dans l'année 2026 hors millésime affiché
- **gravité** : ROBUSTESSE / qualité-donnée (pas FAUX-CLIENT systémique — 1 ligne sur 29 566).
- **obtenu** : `dvf_mutations` contient 1 ligne `id=33217`, `date_mutation=2026-08-10 03:43:00+04` (Vente, 380 000 €), alors que le millésime affiché de la source DVF est « géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020 » et `source_horizon_at=2025-12-31`.
- **attendu** : la table DVF ne dépasse pas le millésime annoncé (≤ 2025-12-31) ; répartition par année : 2021=6852, 2022=7029, 2023=5942, 2024=4840, 2025=4902, **2026=1**.
- **cause probable** : date de mutation aberrante / parasite d'ingestion (une seule occurrence, heure `03:43:00+04` suspecte d'un parse timestamptz) non filtrée au chargement. N'est PAS dans le futur (≤ 2026-10-14) donc ne casse pas I1. Si cette ligne remonte dans une fiche/timeline DVF, le client verrait une vente « 2026 » sous une source bornée à 2025.
- **fichier** : ingestion DVF (non modifiée — hors scope lecture seule) ; lecteur fiche `src/labuse/api/app.py` section DVF (~`:4246`, `ds.source_millesime`). Le millésime AFFICHÉ reste juste (label producteur) ; c'est la DONNÉE sous-jacente qui a 1 outlier.

### V-02 — ROBUSTESSE (environnement local, non servi) : 2 caches de fraîcheur « périmés » à la lecture `/sante/fraicheur`
- **gravité** : ROBUSTESSE, **local-only, auto-réparant** — pas de donnée fausse servie.
- **obtenu** : `/sante/fraicheur` → `perimes = ['commune_contexte_cache','spatial_layers_sub']`.
  - `commune_contexte_cache` : « 0 périmée(s), 24 manquante(s) » — cache jamais chauffé dans ce worktree ; remède noté par le code lui-même : « la fiche se régénère d'elle-même » (lazy).
  - `spatial_layers_sub` : « spatial_layers a bougé depuis la subdivision » — remède « déjà auto-réparant à la cascade ».
- **attendu** : en PROD ces caches sont chauffés (`labuse rebuild`) ; en local non-warmé, l'état « périmé/manquant » est NORMAL et NON servi faux (recalcul au vol).
- **cause probable** : environnement d'audit local sans cron de warm-up. Aucun impact client. `src/labuse/fraicheur_caches.py:_etat_commune_cache` / `_etat_spatial_sub`.

## Non vérifié
- **Fraîcheur AMONT réelle des sources surveillées** : `etats_sources.etat_source` donne « à jour » dès que l'agent a sondé sans « nouvelle_version » ; impossible de confronter au vrai état du producteur sans lancer les sondes réseau (`source_veille`, cron absent en local). Périmètre de ce domaine = dates/millésimes SERVIS, pas la véracité amont — couvert ailleurs par `source_veille` + `admin/verite-sources`.
- **`source_millesime` = max réel de CHAQUE table** : non vérifiable en général — le millésime est un **label publié par le producteur** (`millesime_source.composer` l'affiche tel quel, par design RECETTE-8 W16), pas un recalcul. Seules RPLS, PM et BODACC ont déjà une garde de dérivation (`chasse_donnees.py` g20/g11). Pour les autres sources (CoSIA, OCS GE, LiDAR, QPV…) le millésime amont n'a pas de colonne-date exploitable côté table.
- **Fiche commune `/communes/*/contexte`** parcourue uniquement via la garde g20 existante (RPLS). Pas de sweep exhaustif des 24 communes sur tous les millésimes dérivés dans ce domaine.

## Gardes proposées
Pour `scripts/coherence/chasse_invariants.py`. Les gardes « millésime dérivé » (RPLS/PM/BODACC) existent déjà dans `chasse_donnees.py` (g20/g11) — **ne pas répéter**. Celles ci-dessous sont NEUVES (dates futures + cohérence de run + version de règle).

```python
# ── D9-I1 : aucune date de source dans le futur ──────────────────────────────
def g_dates_futures_sources():
    with _db() as cx:
        n = cx.execute("SELECT count(*) FROM data_sources WHERE "
            "source_horizon_at > DATE '2026-10-14' "
            "OR last_sync_at    > TIMESTAMPTZ '2026-10-14 23:59:59+00' "
            "OR fraicheur_calcule_at > TIMESTAMPTZ '2026-10-14 23:59:59+00'").fetchone()[0]
    # borne = date du jour (à paramétrer : DATE 'now' en garde réelle)
    return ("OK", "aucune date source future") if n == 0 else \
           ("ECART", f"{n} source(s) avec une date dans le futur")

# ── D9-I2 : aucun millésime textuel d'année future ───────────────────────────
def g_millesime_annee_future():
    with _db() as cx:
        rows = cx.execute("SELECT id,name,source_millesime FROM data_sources "
            "WHERE source_millesime ~ '(202[7-9]|20[3-9][0-9])'").fetchall()
    return ("OK", "aucun millésime d'année future") if not rows else \
           ("ECART", f"millésime(s) future(s) : {[(r[0],r[2]) for r in rows]}")

# ── D9-I3 : le run servi est cohérent dans TOUS les pointeurs ────────────────
def g_run_coherent_partout():
    m = _manifest()
    with _db() as cx:
        res_seq  = cx.execute("SELECT run_seq FROM residuel_runs WHERE is_served").fetchone()[0]
        res_lbl  = cx.execute("SELECT label  FROM residuel_runs WHERE is_served").fetchone()[0]
        mvt_run  = cx.execute("SELECT value FROM mvt_meta WHERE key='run_label'").fetchone()[0]
        mvt_seq  = cx.execute("SELECT value FROM mvt_meta WHERE key='residuel_seq'").fetchone()[0]
        has_sc   = cx.execute("SELECT 1 FROM score_labuse WHERE run_label=%(r)s LIMIT 1",
                              {"r": m["scoring_run"]}).fetchone()
        casc_lbl = cx.execute("SELECT cascade_label FROM score_labuse_runs WHERE run_label=%(r)s",
                              {"r": m["scoring_run"]}).fetchone()
    ok = (res_lbl == m["scoring_run"] and int(res_seq) == int(m["residuel_run_seq"])
          and mvt_run == m["mvt_run"] and int(mvt_seq) == int(m["residuel_run_seq"])
          and has_sc is not None
          and (casc_lbl is None or casc_lbl[0] == m.get("cascade_run")))
    return ("OK", f"run servi cohérent partout ({m['scoring_run']}/seq{res_seq})") if ok else \
           ("ECART", f"manifeste={m['scoring_run']}/seq{m['residuel_run_seq']} "
                     f"résiduel={res_lbl}/{res_seq} mvt={mvt_run}/{mvt_seq} "
                     f"score_present={has_sc is not None} cascade={casc_lbl}")

# ── D9-I5 : les tables dérivées portent la version de règle du CODE ──────────
def g_regle_derivee_a_jour():
    from labuse.fraicheur_caches import _derives_regles
    from labuse.ingestion.fraicheur import _etat_get
    perimes = []
    with _db() as cx:
        for table, reg in _derives_regles().items():
            gravee = cx.execute("SELECT valeur FROM fraicheur_etat WHERE cle=%(k)s",
                                {"k": f"derive:{table}:rule_version"}).fetchone()
            gravee = gravee[0] if gravee else None
            if gravee != reg["version"]:
                perimes.append(f"{table}: gravée {gravee!r} ≠ code {reg['version']!r}")
    return ("OK", "règles dérivées = code") if not perimes else \
           ("ECART", "tables dérivées périmées : " + " ; ".join(perimes))
```
