# Runbook — re-fetch voirie CIBLÉ + re-cascade des communes gold

> **Procédure prête, NON exécutée.** Ce document décrit comment récupérer la voirie complète
> (correctif de pagination, cf. `docs/VOIRIE_CAP_5000_AUDIT.md` §10) sur les **3 communes gold**, puis
> relancer la cascade pour corriger les faux « accès non identifié ». **Aucune commande de ce runbook
> n'a été lancée** : la base reste à l'identique (`voirie=5000` partout) tant que tu ne valides pas.
>
> **À exécuter dans une fenêtre dédiée**, sur la **base de travail** (`localhost:5432/labuse`),
> branche `claude/brave-davinci-NaRd4`, **une commune à la fois**, avec relecture du rapport entre chaque.

## 0. Pré-requis (à vérifier avant de commencer)

- [ ] Le correctif de pagination est **en place** : `ingest_bdtopo` pagine (`git log` doit montrer le
      commit « voirie pagination » ; `tests/test_voirie_pagination.py` = 9 verts).
- [ ] `pytest -q` (441 verts) et `ruff check src tests` (clean).
- [ ] Base accessible : `LABUSE_DATABASE_URL=postgresql+psycopg://labuse:labuse@localhost:5432/labuse`.
- [ ] `pg_dump` / `pg_restore` disponibles (`labuse backup-db` / `labuse restore-db`).
- [ ] Fenêtre dédiée : **ne rien faire d'autre** sur la base pendant le re-fetch (le serveur API peut
      mourir sous charge — `pkill -f "labuse api"` avant, relancer après).

> **Périmètre volontairement étroit.** On re-fetch **la voirie SEULE** (purge ciblée `kind='voirie'`),
> on **ne touche pas** aux autres couches gold déjà bonnes (bâti, PPR, SAR, ravines, prescriptions…).
> `water` partage la même fonction paginée et bénéficierait du même correctif, mais il est **hors scope
> ici** (l'impact métier mesuré porte sur l'accès = voirie). L'inclure serait une décision séparée.

## 1. Ordre de traitement (une commune à la fois)

| # | Commune | INSEE | Parcelles | voirie actuelle | Borne haute « accès seul » récupérable (§4 audit) |
|---|---|---|--:|--:|--:|
| 1 | **L'Étang-Salé** | 97404 | 9 070 | 5 000 (plafonnée) | ~400 |
| 2 | **La Possession** | 97408 | 13 338 | 5 000 (plafonnée) | ~1 080 |
| 3 | **Saint-Paul** | 97415 | 51 129 | 5 000 (plafonnée) | ~6 900 |

> On commence par **la plus petite** (L'Étang-Salé) : validation rapide du correctif de bout en bout,
> moins de risque, puis on monte en taille. **STOP + relecture du rapport entre chaque commune.**

---

## 2. Procédure par commune

Pour chaque commune, remplacer `COMMUNE`/`INSEE` (voir tableau §1). Exemple ci-dessous : **L'Étang-Salé**.

### Étape A — Backup pré re-fetch (obligatoire)

```bash
labuse backup-db --dir backups
# → backups/labuse-labuse-<AAAAMMJJ-HHMMSS>.dump  (~500 Mo, ~1 à 2 min)
# Noter le chemin EXACT : c'est le point de rollback (§ Étape F).
```

`backup-db` ne génère pas de `.sha256`. Optionnel mais recommandé pour l'intégrité :

```bash
sha256sum backups/labuse-labuse-<...>.dump > backups/labuse-labuse-<...>.dump.sha256
```

### Étape B — Snapshot AVANT (lecture seule)

Mémoriser l'état de référence pour mesurer l'effet du re-fetch. **`DISTINCT ON` = dernière éval par
parcelle** (la table `parcel_evaluations` conserve l'historique).

```bash
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c "
-- (1) voirie en base (doit valoir 5000 = plafonnée AVANT)
SELECT 'voirie_avant='||count(*) FROM spatial_layers WHERE kind='voirie' AND commune='L''Étang-Salé';
-- (2) répartition des verdicts (dernière éval par parcelle)
SELECT status, count(*) FROM (
  SELECT DISTINCT ON (e.parcel_id) e.status
  FROM parcel_evaluations e JOIN parcels p ON p.id=e.parcel_id
  WHERE p.commune='L''Étang-Salé'
  ORDER BY e.parcel_id, e.evaluated_at DESC
) t GROUP BY status ORDER BY 2 DESC;"
```

Noter `voirie_avant` (= 5000) et la ligne `a_creuser` (= référence à faire baisser).

### Étape C — Re-fetch voirie CIBLÉ (purge `kind='voirie'` SEULE + ré-ingestion paginée)

> **Scopé commune + voirie uniquement.** Aucune autre couche, aucune autre commune n'est touchée.
> `ingest_bdtopo` est désormais paginé → il récupère **toute** la voirie (au-delà de 5 000).

```bash
python - <<'PY'
from sqlalchemy import text
from labuse import models
from labuse.db import engine, session_scope
from labuse.ingestion import layers_ingest, run_all

COMMUNE, INSEE = "L'Étang-Salé", "97404"
with session_scope() as s:
    n_del = s.execute(text("DELETE FROM spatial_layers WHERE kind='voirie' AND commune=:c"),
                      {"c": COMMUNE}).rowcount
    bbox = run_all._commune_bbox(s, COMMUNE)
    sids = layers_ingest._source_ids(s)
    n_ins = layers_ingest.ingest_bdtopo(s, bbox, COMMUNE, None, sids,
                                        "voirie", "BDTOPO_V3:troncon_de_route")
    print(f"voirie {COMMUNE} : -{n_del} purgées / +{n_ins} ré-ingérées (paginé)")
# index géométrique 2975 (dont idx_spatial_layers_voirie_geom2975) reconstruit hors transaction
models.ensure_geom_2975(engine(), commune=COMMUNE)
print("geom_2975 + index voirie : OK")
PY
```

**Attendu** : `+n_ins` **> 5 000** pour les communes denses (= preuve de dé-plafonnement). Les logs
`ingest_bdtopo[voirie] : N objet(s) en P page(s)` confirment la pagination (P ≥ 2). Si un WARNING
`garde-fou max_total` apparaît → la voirie réelle dépasse 60 000 (improbable à l'échelle commune) :
**ne pas valider**, augmenter `max_total` et relancer.

### Étape D — Re-cascade (recalcule les verdicts avec la voirie complète)

```bash
labuse evaluate --commune "L'Étang-Salé"
# → réécrit les verdicts ; la distance-à-la-voirie est désormais exacte.
```

### Étape E — Post-checks (lecture seule, AVANT → APRÈS)

```bash
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c "
-- (1) voirie APRÈS : doit être > 5000 (dé-plafonnée) ; sinon le re-fetch n'a rien changé
SELECT 'voirie_apres='||count(*) FROM spatial_layers WHERE kind='voirie' AND commune='L''Étang-Salé';
-- (2) verdicts APRÈS (dernière éval par parcelle) : 'a_creuser' doit BAISSER, 'opportunite' MONTER
SELECT status, count(*) FROM (
  SELECT DISTINCT ON (e.parcel_id) e.status
  FROM parcel_evaluations e JOIN parcels p ON p.id=e.parcel_id
  WHERE p.commune='L''Étang-Salé'
  ORDER BY e.parcel_id, e.evaluated_at DESC
) t GROUP BY status ORDER BY 2 DESC;
-- (3) intégrité géométrie : aucune voirie sans geom_2975
SELECT 'voirie_sans_geom2975='||count(*) FROM spatial_layers
  WHERE kind='voirie' AND commune='L''Étang-Salé' AND geom_2975 IS NULL;
-- (4) index voirie présent
SELECT 'idx_voirie='||count(*) FROM pg_indexes WHERE indexname='idx_spatial_layers_voirie_geom2975';"
```

Checklist de validation :

- [ ] **`voirie_apres` > `voirie_avant` (5000)** — dé-plafonnement effectif (sinon : re-fetch sans effet → enquêter).
- [ ] **`a_creuser` a baissé** et **`opportunite` a augmenté** (sens monotone attendu : plus de voirie ⇒ distances plus courtes ⇒ moins de faux enclavements). Le **total parcelles est inchangé**.
- [ ] **`voirie_sans_geom2975` = 0** — toutes les nouvelles géométries sont projetées.
- [ ] **`idx_voirie` = 1** — index spatial présent (perf cascade).
- [ ] **Aucune ERREUR WFS** dans les logs de l'étape C.
- [ ] **`opportunity_score` / opp% ne se dégrade pas** : le correctif ne peut **qu'ajouter** des tronçons ⇒ aucune parcelle ne doit passer d'`opportunite` à `a_creuser` **à cause** du re-fetch. Une hausse de `a_creuser` serait anormale → **NO-GO**.

### Étape F — Décision : gold MAINTENU ou NO-GO

| Cas | Condition | Action |
|---|---|---|
| ✅ **gold maintenu** | voirie > 5000 **ET** `a_creuser` baisse (ou stable) **ET** geom2975 OK **ET** 0 erreur WFS | Commune reste `gold`. Régénérer son rapport `docs/communes/<slug>_RESULTS.md` (avant→après voirie + verdicts). **STOP, faire valider, puis commune suivante.** |
| ⛔ **NO-GO / anomalie** | voirie toujours = 5000, **ou** `a_creuser` **augmente**, **ou** erreurs WFS, **ou** geom2975 manquant | **Rollback (Étape G)**. Ne pas laisser la commune dans un état intermédiaire. Diagnostiquer avant de réessayer. |

> **Le re-fetch ne change PAS l'état `gold` dans la config** : `gold` reste acquis (les couches gold sont
> intactes) ; on **améliore** seulement l'exactitude de l'accès. Aucune modification de
> `config/communes_gold_standard.yaml` n'est requise par ce re-fetch (sauf à vouloir tracer la date de
> recalibrage voirie en commentaire). **Ne pas merger `main`, ne pas déployer** sans validation séparée.

### Étape G — Rollback (si NO-GO)

```bash
labuse restore-db --file backups/labuse-labuse-<AAAAMMJJ-HHMMSS>.dump --yes
# Restaure l'état AVANT re-fetch (voirie=5000, verdicts d'origine). Idempotent.
```

Puis vérifier le retour à l'état initial :

```bash
PGPASSWORD=labuse psql "postgresql://labuse@localhost:5432/labuse" -tA -c "
SELECT 'voirie='||count(*) FROM spatial_layers WHERE kind='voirie' AND commune='L''Étang-Salé';"
# → doit ré-afficher 5000
```

---

## 3. Après les 3 communes gold

1. **Relire les 3 rapports** (`docs/communes/*_RESULTS.md`) : voirie dé-plafonnée + baisse de `a_creuser`.
2. **Commit** (branche de travail uniquement) : rapports + éventuelle note de recalibrage dans la config.
   **Pas de merge `main`, pas de déploiement** sans ta validation explicite.
3. **Vague 2 ensuite** : les grosses communes (Saint-Pierre, Le Tampon, Saint-Leu, Saint-Louis,
   Saint-Denis) seront traitées **avec le correctif déjà en place** → leur voirie sera paginée **dès le
   premier import** (pas de re-fetch a posteriori à prévoir pour elles).

## 4. Garde-fous (rappel)

- **Une commune à la fois**, backup **avant chaque**, STOP + relecture **entre chaque**.
- **Purge strictement `kind='voirie' AND commune=:c`** — jamais de purge globale.
- **Scope voirie** : ne pas re-fetch les couches déjà bonnes (bâti, PPR, SAR, ravines, prescriptions).
- **Rollback prêt** (`restore-db`) si la moindre anomalie (NO-GO).
- **Aucun merge `main`, aucun déploiement** dans ce runbook : c'est une opération de **données de travail**.

---

*Runbook prêt. Aucune commande ci-dessus n'a été exécutée à la rédaction : la base est inchangée
(18 communes / 377 194 parcelles ; voirie plafonnée à 5 000). Le re-fetch est à lancer sur validation.*
