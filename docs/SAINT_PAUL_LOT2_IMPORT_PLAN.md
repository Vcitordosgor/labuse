# SAINT-PAUL — LOT 2 : Plan d'import cadastre complet (NON exécuté)

> **Objectif** : passer Saint-Paul de **3 000 → 51 129 parcelles**, sans casser les données
> actuelles, sans doublons, sans toucher inutilement aux autres communes, avec rollback garanti
> via le backup du LOT 1.
>
> **⚠️ CE DOCUMENT EST UN PLAN. RIEN N'EST EXÉCUTÉ.** Aucun import, aucune modification de la base,
> aucun recalcul cascade, aucune suppression, aucune autre commune touchée. L'exécution est gelée
> jusqu'à validation explicite (cf. dernière section).

Référence d'état : `docs/SAINT_PAUL_QUALITY_AUDIT.md` (diagnostic) · `docs/SAINT_PAUL_LOT1_BACKUP_SECURITY.md`
(point de retour : `/var/backups/labuse/labuse-labuse-20260620-101644.dump`).

---

## 0. Pourquoi PAS la commande « toute faite » (décision d'architecture)

| Commande | Comportement réel | Verdict |
|---|---|---|
| `ingest-real --reset` (défaut) | **VIDE `parcels` (toutes communes)** + couches | ⛔ destructif — interdit |
| `ingest-real --no-reset` | préserve les parcelles (ON CONFLICT) **MAIS** ré-ingère les couches **en append → DOUBLONS**, et calcule le bbox couches sur l'**emprise île** (faux) ; **n'évalue pas** | ⛔ duplique + bbox faux |
| `ingest-island --only 97415 --force` | re-import + ré-évaluation corrects **MAIS** `ingest_commune` fait `DELETE FROM parcels WHERE commune='Saint-Paul'` → **CASCADE** supprime évaluations + **pipeline (4) + feedback (1)** ; nouveaux `id` → liens perdus | ⛔ perd les données métier liées |

**Conclusion :** aucune commande unique n'est sûre **et** préservante. Le LOT 2 utilise une
**séquence chirurgicale id-préservante** (ci-dessous), revue avant exécution.

---

## 1. Commandes exactes prévues

> Toutes lancées dans le venv, avec `/etc/labuse/labuse.env` (ou `.env`) chargé. La séquence
> d'import est un **script d'orchestration unique** (≈ 25 lignes, à créer et **faire relire**
> avant de lancer) qui n'utilise que des primitives existantes du projet.

### 1.1 Import des parcelles — IDEMPOTENT, SANS reset (préserve les 3 000 `id`)
```python
# scripts/lot2_import_saint_paul.py  (À CRÉER — revu avant exécution)
from sqlalchemy import text
from labuse.db import session_scope, engine
from labuse.ingestion import cadastre_bulk, layers_ingest, run_all
from labuse.connectors.cadastre import ingest_parcels
from labuse import models

INSEE, NAME = "97415", "Saint-Paul"

# B) PARCELLES — ON CONFLICT (idu) DO UPDATE : 3 000 existantes conservées (mêmes id →
#    évaluations / pipeline / prospection / feedback PRÉSERVÉS), 48 129 nouvelles insérées.
with session_scope() as s:
    parcels = cadastre_bulk.parse_etalab(cadastre_bulk.download_parcelles(INSEE))   # 51 129
    run = models.IngestionRun(commune=NAME, status="running", parcels_count=len(parcels))
    s.add(run); s.flush(); run_id = run.id
    n = ingest_parcels(s, parcels, NAME, run_id)        # AUCUN reset, AUCUN DELETE parcels
    print("parcelles upsert:", n)
models.ensure_geom_2975(engine())                       # reprojection 2975 + ST_MakeValid + GIST

# D) COUCHES — d'abord PURGE CIBLÉE (commune='Saint-Paul' uniquement) pour éviter les doublons,
#    puis ré-ingestion sur le bbox de la COMMUNE COMPLÈTE (les 51 129 parcelles).
with session_scope() as s:
    s.execute(text("DELETE FROM spatial_layers WHERE commune = :c"), {"c": NAME})
    s.execute(text("DELETE FROM dvf_mutations  WHERE commune = :c"), {"c": NAME})
    bbox = run_all._commune_bbox(s, NAME)               # = emprise des 51 129 (pas l'île)
    counts = layers_ingest.ingest_layers(s, INSEE, NAME, bbox, run_id)
    print("couches:", counts)
models.ensure_geom_2975(engine())                       # re-valide/index les couches

# F) RECALCUL CASCADE — Saint-Paul UNIQUEMENT (les 51 129).
with session_scope() as s:
    nev = run_all.evaluate_commune(s, NAME)
    print("évaluées:", nev)
```

- ✅ **`--reset` n'est PAS utilisé** : aucun `reset_demo`, aucun `TRUNCATE`, aucun
  `DELETE FROM parcels`. Les seules suppressions sont **`spatial_layers`/`dvf_mutations` WHERE
  commune='Saint-Paul'** (couches re-fetchées juste après ; jamais les parcelles).
- ✅ **Idempotence** : `ingest_parcels` = `INSERT … ON CONFLICT (idu) DO UPDATE` (contrainte
  `ix_parcels_idu UNIQUE`) → ré-exécutable sans doublon.

### 1.2 Commandes de contrôle (psql, lecture seule)
```bash
export PGPASSWORD=…   # ou ~/.pgpass
PSQL="psql -h localhost -U labuse -d labuse -X"
# AVANT
$PSQL -c "SELECT count(*) FROM parcels WHERE commune ILIKE 'saint-paul';"          # attendu 3000
# APRÈS import cadastre
$PSQL -c "SELECT count(*), count(DISTINCT idu), count(DISTINCT section) FROM parcels WHERE commune ILIKE 'saint-paul';"
$PSQL -c "SELECT count(*) FROM parcels WHERE commune ILIKE 'saint-paul' AND NOT ST_IsValid(geom);"
# APRÈS cascade
$PSQL -c "SELECT e.status, count(*) FROM parcels p JOIN LATERAL (SELECT status FROM parcel_evaluations WHERE parcel_id=p.id ORDER BY evaluated_at DESC LIMIT 1) e ON true WHERE p.commune ILIKE 'saint-paul' GROUP BY e.status;"
```

---

## 2. Gestion des couches Saint-Paul

`ingest_layers` **insère sans dédup** (append). Les couches « bbox » ont été fetchées sur l'**emprise
pilote urbaine** → elles ne couvrent **pas les Hauts**. La séquence ci-dessus traite cela **en une
passe** : purge ciblée `commune='Saint-Paul'` → ré-ingestion sur l'emprise commune complète.

| Couche | Couvre déjà tout SP ? | Re-fetch ? | Risque doublon | Anti-doublon | Vérif post-import |
|---|---|---|---|---|---|
| **PLU / zonage** (`plu_gpu_zone`, bbox) | ❌ emprise pilote | ✅ obligatoire | Oui (append) | purge ciblée avant | ≥ 99 % parcelles avec zone |
| **Prescriptions** (`plu_gpu_prescription`, bbox) | ❌ | ✅ | Oui | purge ciblée | features > 117 |
| **Bâti** (`batiment`, bbox) | ❌ (11 285 = zone urbaine) | ✅ | Oui | purge ciblée | features ≫ 11 285 (~×4-5) |
| **PPR / risques** (`ppr`, bbox) | partiel (4 entités) | ✅ | Oui | purge ciblée | features ≥ 4, couverture risques |
| **Ravines** (`ravine`, bbox) | ❌ | ✅ | Oui | purge ciblée | features > 98 |
| **ABF** (`abf`, bbox) | ❌ | ✅ | Oui | purge ciblée | features ≥ 1 |
| **Voirie / accès** (`voirie`, bbox) | ❌ | ✅ | Oui | purge ciblée | % accès < seuil cohérent |
| **Pente** (`pente`, bbox) | ❌ | ✅ | Oui | purge ciblée | ~100 % parcelles |
| **OCS GE** (`ocs_ge`, bbox) | ❌ | ✅ | Oui | purge ciblée | features > 0 |
| **Eau** (`water`, bbox) | ❌ | ✅ | Oui | purge ciblée | features > 0 |
| **Forêt publique** (`foret_publique`, commune) | ✅ (commune) | ✅ par cohérence | Oui si non purgé | purge ciblée | features ≥ 164 |
| **ENS** (`ens`, bbox) | ❌ | ✅ | Oui | purge ciblée | features ≥ 52 |
| **SAFER** (`safer`, insee) | ✅ (insee) | ✅ par cohérence | Oui si non purgé | purge ciblée | features ≈ stable |
| **SAR** (`sar`, insee) | ✅ (insee) | ✅ par cohérence | Oui si non purgé | purge ciblée | features ≈ 303 |
| **Trait de côte** (`trait_de_cote`, commune) | ✅ | ✅ cohérence | Oui si non purgé | purge ciblée | features ≈ stable |
| **Parc national** (`parc_national`, commune) | ✅ | ✅ cohérence | Oui si non purgé | purge ciblée | features ≈ 54 |
| **Potentiel foncier** (`potentiel_foncier`, insee) | ✅ | ✅ cohérence | Oui si non purgé | purge ciblée | features ≈ stable |
| **DVF** (`dvf`, insee) | ✅ (transactions) | ✅ cohérence | Oui si non purgé | purge ciblée `dvf_mutations` | mutations SP ≈ stable |

> **Règle unique anti-doublon** : la purge `DELETE … WHERE commune='Saint-Paul'` **scoping commune**
> précède TOUTE ré-ingestion. Elle ne touche **aucune autre commune** (chaque feature porte sa
> colonne `commune`). Vérif globale : `SELECT kind, count(*) FROM spatial_layers WHERE commune='Saint-Paul' GROUP BY kind` ne doit montrer **aucune valeur anormalement doublée**.

---

## 3. Données préservées (confirmation)

La séquence **ne supprime jamais de parcelle** et **conserve les `id`** (ON CONFLICT DO UPDATE) →
tout ce qui est lié par `parcel_id` survit automatiquement.

| Donnée | Conservée ? | Mécanisme |
|---|---|---|
| Les 3 000 parcelles actuelles | ✅ | `ON CONFLICT (idu) DO UPDATE` (même `id`) |
| Leurs évaluations | ✅ | `parcel_id` inchangé ; la cascade **ajoute** la nouvelle éval (historique conservé) |
| Statuts pipeline (4) | ✅ | `pipeline_entries.parcel_id` inchangé (jamais de DELETE parcels) |
| Prospection / notes | ✅ | stockées dans `pipeline_entries.prospection`/`notes` → liées au même `parcel_id` |
| Propriétaires (12 539) | ✅ | `parcelle_personne_morale` keyed par **idu** (indépendant de `parcel_id`) |
| Feedback (1) | ✅ | `parcel_feedback.parcel_id` inchangé |
| Parcelles démo (8 réelles : BK0023…) | ✅ | présentes dans les 51 129, upsert |
| Calibration bilan (`bilan_params`, 16) | ✅ | **table jamais touchée** par l'import |
| Alertes (12) | ✅ | non liées aux parcelles supprimées (aucune ne l'est) |

> **C'est précisément pourquoi on REFUSE `ingest-island --force`** : son `DELETE FROM parcels`
> déclencherait le `ON DELETE CASCADE` sur `parcel_evaluations` **et** `pipeline_entries`.

---

## 4. Impact attendu (estimations)

| Élément | Avant | Après LOT 2 |
|---|---:|---:|
| Parcelles Saint-Paul | 3 000 | **51 129** |
| Parcelles totales (`parcels`) | 329 065 | ~377 194 (+48 129) |
| Taille `parcels` | 234 Mo | ~270 Mo |
| `cascade_results` (après recalcul) | 596 Mo / 3,47 M lignes | ~680 Mo / ~4,0 M lignes |
| `spatial_layers` (SP re-fetché sur emprise complète) | 254 Mo | ~330–360 Mo |
| `parcel_evaluations` | 31 Mo | +~50 k évaluations |
| **Base totale** | 1 153 Mo | **~1,4–1,5 Go** (disque ~1,7 Go) |
| **Temps import parcelles** | — | ~1–3 min (dl 5,6 Mo + upsert 51 129) |
| **Temps re-fetch couches (emprise complète)** | — | **~10–40 min** (WFS/IGN, dépend des quotas — *long pole n°1*) |
| **Temps recalcul cascade (51 129)** | — | **~10–30 min** (chunks de 2 000 — *long pole n°2*) |
| CPU | — | 1 cœur soutenu (cascade) ; réseau pour les couches |
| RAM | — | modérée (< 1 Go de surcroît) |
| Disque | — | +~0,3–0,4 Go ; pic WAL transitoire pendant l'insert/index |

> **Total opération : ~30–90 min**, dominé par le re-fetch des couches puis la cascade — à lancer
> **hors fenêtre de démo**. Les temps seront **mesurés** en exécution réelle (les estimations
> couches/cascade dépendent des quotas externes et de la machine).

---

## 5. Points de contrôle OBLIGATOIRES

### Avant import (A)
- [ ] Backup LOT 1 présent : `/var/backups/labuse/labuse-labuse-20260620-101644.dump`.
- [ ] Checksum OK : `sha256sum -c …dump.sha256`.
- [ ] Base principale saine : `labuse doctor` vert · `/readyz` 200.
- [ ] Saint-Paul = **3 000** parcelles.

### Après import cadastre, AVANT cascade (C)
- [ ] Saint-Paul ≈ **51 129** parcelles.
- [ ] **0 doublon IDU** (`count(*) = count(DISTINCT idu)`).
- [ ] **0 géométrie invalide** (`NOT ST_IsValid(geom)` = 0) ; `geom_2975` non nulle.
- [ ] Sections ≈ **98**.
- [ ] **Les 3 000 IDU d'origine sont toujours présents** (set d'avant ⊆ set d'après).
- [ ] Couches : aucune valeur doublée anormale ; bâti ≫ 11 285.

### Après recalcul cascade (G)
- [ ] **100 %** des parcelles Saint-Paul évaluées (51 129 / 51 129).
- [ ] Verdicts cohérents (les Hauts ajoutent surtout des « écartées » zone A/N — **pas** une
      explosion d'« opportunités »).
- [ ] **Aucune explosion de faux positifs évidente** (réexécuter `tests/test_saint_paul_quality.py`,
      dont l'anti-fausse-opportunité R1).
- [ ] Fiches parcelles fonctionnelles (échantillon urbain **+** Hauts).
- [ ] `/readyz` 200 · `/demo-status` 200 (14/14).

---

## 6. Rollback

| Question | Réponse |
|---|---|
| **Quand rollback ?** | Un point de contrôle (C) ou (G) échoue de façon non récupérable : doublons, géométries invalides massives, perte des 3 000 IDU, explosion d'opportunités, `/readyz` 503. |
| **Commande exacte** | `systemctl stop labuse` *(ou `pkill -f "labuse api"`)* puis `labuse restore-db --file /var/backups/labuse/labuse-labuse-20260620-101644.dump --yes` puis `systemctl start labuse`. |
| **Vérifier le retour à l'état initial** | `psql … -c "SELECT count(*) FROM parcels WHERE commune ILIKE 'saint-paul';"` → **3000** ; `labuse doctor` vert. |
| **Temps estimé** | **~1–2 min** (restauration mesurée à **23 s** au LOT 1 + arrêt/redémarrage + vérif). |

Le backup du LOT 1 ramène **l'état EXACT pré-import** (3 000 parcelles, pipeline/feedback/calibration
inclus). Aucune perte au-delà de ce qui aurait été tenté après le backup.

---

## 7. Plan en micro-étapes

| Étape | Action | Contrôle | Réversible ? |
|---|---|---|---|
| **A. Pré-checks** | vérifier backup + checksum + `doctor` + SP=3000 | section 5-A | — (lecture seule) |
| **B. Import cadastre** | script §1.1 partie B (upsert 51 129, sans reset) | upsert ≈ 48 129 nouvelles | ✅ rollback LOT 1 |
| **C. Vérif cadastre** | comptage, doublons, géométries, sections, 3 000 IDU présents | section 5-C | — |
| **D. Couches** | purge ciblée SP + ré-ingestion sur emprise complète | counts par couche | ✅ rollback LOT 1 |
| **E. Vérif couches** | couverture par couche (zonage ≥ 99 %, bâti ≫, pente ~100 %), aucun doublon | requêtes §2 | — |
| **F. Recalcul cascade** | `evaluate_commune("Saint-Paul")` sur les 51 129 | éval = 51 129 | ✅ rollback LOT 1 |
| **G. QA post-import** | `pytest tests/test_saint_paul_quality.py` (seuil → 51 129) + santé + échantillon fiches | section 5-G | — |
| **H. Rapport** | `docs/SAINT_PAUL_LOT2_RESULTS.md` (avant/après, temps mesurés, anomalies) | — | — |

Chaque étape B/D/F est **committée séparément** ; un arrêt entre deux laisse un état cohérent et
toujours rollback-able via le LOT 1.

---

## 8. VALIDATION UTILISATEUR REQUISE AVANT EXÉCUTION

🔒 **Rien de ce plan n'est exécuté.** Avant de lancer le LOT 2, l'utilisateur doit valider
explicitement :

- [ ] Le **chemin id-préservant** (et le refus de `ingest-island --force`).
- [ ] La **purge ciblée des couches** `WHERE commune='Saint-Paul'` (seule suppression, recoverable).
- [ ] La fenêtre d'exécution **hors démo** (30–90 min, long poles couches + cascade).
- [ ] Le script `scripts/lot2_import_saint_paul.py` (à créer puis **relire**) avant son lancement.

À la validation, l'ordre d'exécution sera **A → B → C → D → E → F → G → H**, chaque étape
contrôlée, avec arrêt immédiat + rollback LOT 1 au premier point de contrôle non satisfait.

---

## 9. Script d'exécution — `scripts/lot2_import_saint_paul.py`

Le LOT 2 est outillé par un **script unique, sécurisé par défaut**.

| Élément | Valeur |
|---|---|
| **Script** | `scripts/lot2_import_saint_paul.py` |
| **Mode par défaut** | **DRY-RUN** (lecture seule : pré-checks + affichage du plan ; n'écrit rien) |
| **Flag exécution réelle** | `--execute` |
| **Confirmation obligatoire** | `--confirm "IMPORT_SAINT_PAUL_COMPLET"` (exacte, sinon REFUS) |
| `--backup` | chemin du dump LOT 1 (défaut : `/var/backups/labuse/labuse-labuse-20260620-101644.dump`) |
| `--base-url` | URL pour la sonde `/readyz` (défaut `http://127.0.0.1:8000`) |
| **Commune** | **FIGÉE** à Saint-Paul / 97415 — aucun argument ne permet d'en viser une autre |

### Procédure DRY-RUN (sûre, à lancer autant qu'on veut)
```bash
python scripts/lot2_import_saint_paul.py
```
→ exécute les pré-checks (backup+checksum, PostGIS, tables critiques, SP=3000, 0 doublon, /readyz)
et affiche les étapes B/D/F **sans les exécuter**. Aucune donnée modifiée, aucun rapport écrit.

### Procédure RÉELLE (future — NE PAS lancer avant validation)
```bash
python scripts/lot2_import_saint_paul.py --execute --confirm "IMPORT_SAINT_PAUL_COMPLET"
```
→ enchaîne A→H : pré-checks bloquants, import parcelles (upsert id-préservant), purge ciblée +
ré-ingestion des couches, recalcul cascade, contrôles post-import, écriture de
`docs/SAINT_PAUL_LOT2_RESULTS.md`. Tout pré-check bloquant en échec ⇒ **arrêt immédiat, aucune action**.

### Garanties du script (vérifiées par `tests/test_lot2_import_script.py`)
- Dry-run par défaut ; refus de `--execute` sans la confirmation **exacte** (retour 2, avant toute connexion).
- Refus si backup absent / checksum non conforme ; refus si Saint-Paul ≠ 3 000.
- Aucune autre commune en dur ; les seules suppressions sont `… WHERE commune = 'Saint-Paul'`.
- **`DELETE FROM parcels` absent du code** ; en dry-run, les étapes mutantes ne touchent même pas la connexion.

### Rollback (rappel)
`systemctl stop labuse` → `labuse restore-db --file /var/backups/labuse/labuse-labuse-20260620-101644.dump --yes`
→ vérifier `SP=3000` → `systemctl start labuse`. ~1–2 min.

### ✍️ Phrase EXACTE à valider avant exécution
> **« Je valide l'exécution réelle du LOT 2 : importer Saint-Paul complet (3 000 → 51 129) avec le
> script `scripts/lot2_import_saint_paul.py --execute --confirm "IMPORT_SAINT_PAUL_COMPLET"`. »**

Tant que cette phrase n'est pas donnée, le script reste en dry-run et **rien n'est exécuté**.

---

## 10. Garde-fous de robustesse (durcissement audit #1–#4)

Le script ne se contente pas d'importer : il **détecte les échecs et refuse de mentir sur le résultat**.

### Codes de sortie (interprétables par l'opérateur / l'automatisation)
| Code | Signification | Action |
|---|---|---|
| **0** | SUCCÈS — Saint-Paul prêt comme modèle | rien |
| **1** | ROLLBACK RECOMMANDÉ (contrôle/couche **critique** KO) **ou** crash | restaurer le backup LOT 1 |
| **2** | `--execute` sans `--confirm` exact | relancer avec la phrase exacte |
| **3** | RE-FETCH COUCHE REQUIS (seule(s) couche(s) **non critique**(s) échouée(s)) | re-fetcher la couche, pas de rollback |

### Détection des erreurs de couches (#1)
- `ingest_layers` isole chaque couche par SAVEPOINT et écrit `"ERREUR …"` dans `counts` en cas d'échec.
- Le script **inspecte `counts`** : toute couche en `"ERREUR"` est remontée et **classée** :
  - **couche CRITIQUE** (`plu_gpu_zone`, `batiment`, `pente`, `voirie`) échouée → **ROLLBACK RECOMMANDÉ** (code 1) ;
  - **couche non critique** (PPR, ravines, prescriptions, ABF, ENS…) échouée → **RE-FETCH COUCHE REQUIS** (code 3).
- Post-checks de couverture : **zonage ≥ 99 %**, **bâti > état pilote** (le bâti doit avoir augmenté
  avec l'emprise complète), **PPR / ravines / prescriptions** affichées avec un statut explicite
  **complet / partiel / échoué**, et **aucune duplication** (groupes `(kind, géométrie)` en double = 0).

### Conservation métier vérifiée (#3)
Le script capture **avant** puis **après** les compteurs Saint-Paul de `pipeline_entries`,
`parcel_feedback`, `alertes` (liés par `parcel_id`). **Toute baisse ⇒ contrôle critique KO ⇒ code 1.**

### Crash / état partiel (#4)
Les étapes B/D/F sont sous `try/except`. Une exception (ex. timeout réseau) ⇒ message
**« ÉTAT PARTIEL POSSIBLE — ROLLBACK LOT 1 À ENVISAGER »**, écriture d'un **rapport d'échec**
(`docs/SAINT_PAUL_LOT2_RESULTS.md`) et **code 1**. L'opération n'est **jamais** présentée comme réussie.

### Différence « ROLLBACK requis » vs « RE-FETCH couche requis »
| Situation | Verdict | Pourquoi |
|---|---|---|
| Couche **critique** vide/échouée, zonage < 99 %, bâti non augmenté, perte pipeline/feedback/alertes, ou crash | **ROLLBACK RECOMMANDÉ** | Saint-Paul serait dégradé/incohérent → revenir à l'état 3 000 (LOT 1) puis recommencer |
| Couche **non critique** échouée, le reste OK | **RE-FETCH COUCHE REQUIS** | Saint-Paul est exploitable ; il suffit de **re-fetcher la seule couche manquante** (pas de rollback) |

### Procédures
- **Couche échouée (non critique)** : noter la couche listée, la re-fetcher ciblé une fois la cause
  réseau résolue, puis re-lancer les post-checks. Pas de rollback.
- **État partiel / contrôle critique KO** : `systemctl stop labuse` →
  `labuse restore-db --file /var/backups/labuse/labuse-labuse-20260620-101644.dump --yes` →
  vérifier `SP=3000` → `systemctl start labuse`. Puis diagnostiquer avant de retenter (~1–2 min).

> Tous ces garde-fous sont **verrouillés par `tests/test_lot2_import_script.py`** (détection erreurs,
> codes de sortie, conservation comparée, crash → rapport d'échec, dry-run 100 % non mutant).

---

*Plan LOT 2 — aucune exécution. Aucune donnée modifiée. Aucune autre commune touchée.*
