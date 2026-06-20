# LOT 6 — Runbook : traiter une commune au standard Saint-Paul

> Procédure opérationnelle, **commune par commune**, pour `scripts/import_commune_gold_standard.py`.
> Le script est **DRY-RUN par défaut** : aucune écriture sans `--execute` + confirmation EXACTE.
> Référentiel d'état & de stratégie : `config/communes_gold_standard.yaml`. Plan détaillé :
> `docs/LOT6_GENERALISATION_23_COMMUNES_PLAN.md`.

## Ordre des vagues

| Vague | Communes | Stratégie |
|---|---|---|
| **0** | Saint-Paul | GOLD (fait) |
| **1 — tests** | **La Possession (97408)**, **L'Étang-Salé (97404)** | re-couches + re-cascade |
| **2 — commerciales** | Saint-Pierre, Le Tampon, Saint-Leu, Saint-Louis | re-couches + re-cascade |
| **3 — moyennes** | Saint-André, Saint-Joseph, Saint-Benoît, Le Port, Petite-Île, Les Avirons, Bras-Panon | re-couches + re-cascade |
| **4 — chef-lieu** | Saint-Denis (lourd, fenêtre dédiée) | re-couches + re-cascade |
| **5 — absentes** | Sainte-Marie, Sainte-Suzanne, Sainte-Rose | import complet + couches + cascade |
| **6 — atypiques** | Entre-Deux, La Plaine-des-Palmistes, Saint-Philippe, Les Trois-Bassins, **Salazie, Cilaos** | re-couches/import — **en dernier** |

Une commune n'avance que lorsque la **précédente de sa vague est en SUCCÈS** (rapport vert).

## Procédure DRY-RUN (toujours en premier)

```bash
python scripts/import_commune_gold_standard.py --commune "La Possession" --insee 97408
```
Le dry-run : valide la cible (référentiel officiel), mesure l'état réel (parcelles, sections, éval %,
couches), affiche l'**état détecté** (ABSENTE / PARTIELLE / GOLD), liste les **couches gold manquantes**,
et imprime le **PLAN** complet. **Aucune écriture.** À lire intégralement avant tout GO.

## Procédure GO commune (exécution réelle)

1. **Backup PRÉ-commune** (point de retour) :
   ```bash
   labuse backup-db --dir /var/backups/labuse        # → dump horodaté + .sha256
   ```
2. **Lancer** avec les DEUX garde-fous (la phrase **nomme la commune**) :
   ```bash
   python scripts/import_commune_gold_standard.py --commune "La Possession" --insee 97408 \
       --execute --confirm "IMPORT_LA_POSSESSION_COMPLET" --backup /var/backups/labuse/<dump_pré>.dump
   ```
3. Le script déroule : [B] cadastre (upsert id-préservant + compare Etalab) → [D] couches (DELETE
   **scopé commune** + ré-ingestion, SAVEPOINT/couche) → [E] index (vérifiés) → [F] cascade
   (`evaluate_commune`, **écrase** les verdicts non fiables) → [G] post-checks → [H] rapport
   `docs/communes/<commune>_RESULTS.md`.
4. **Backup POST-vague** une fois la vague terminée et verte.
5. **Lever le flag fiabilité** : passer la commune en `etat: gold` dans
   `config/communes_gold_standard.yaml` (le bandeau « non validée » disparaît automatiquement).

## Checkpoints (à chaque commune)

- [ ] Dry-run lu, état détecté cohérent avec la config.
- [ ] Backup pré-commune créé + sha256 vérifié.
- [ ] Couches **critiques** ingérées (plu_gpu_zone, **batiment**, pente, voirie) sans ERREUR.
- [ ] Couches **gold** présentes (batiment, ppr, sar, ravine, osm, prescriptions, abf).
- [ ] Post-checks verts : compte ≈ Etalab · sections · 0 géométrie invalide · **bâti > 0** ·
      **top-N sans bâti > 50 %** (anti-fausse-opportunité) · 100 % évalué · conservation pipeline/feedback/alertes.
- [ ] Taux d'« opportunité » **revenu à un ordre de grandeur Saint-Paul (~1–3 %)**, PAS 5–11 % (signe
      que le bâti a bien filtré les faux positifs).
- [ ] Rapport `docs/communes/<commune>_RESULTS.md` écrit.
- [ ] `config/communes_gold_standard.yaml` mis à jour (`etat: gold`).

## Codes de sortie (post-checks [G] automatisés)

| Code | Sens | Action |
|:--:|---|---|
| **0** | SUCCÈS | tous les contrôles critiques + QA verts → marquer la commune `gold` |
| **1** | ROLLBACK recommandé | contrôle/couche **critique** KO ou crash → `restore-db` du backup pré |
| **2** | Confirmation absente/incorrecte | relancer avec `--confirm "IMPORT_<COMMUNE>_COMPLET"` |
| **3** | RE-FETCH ciblé | couche **non critique** KO → re-fetch cette couche, re-checker |
| **4** | **NO-GO QA** | import OK mais résultat **suspect** (ex. taux d'opportunité explosif) → **ne pas** marquer gold, investiguer |

Précédence : **1 > 4 > 3 > 0**. Le rapport `docs/communes/<commune>_RESULTS.md` est écrit dans tous les cas.

## Conditions de SUCCÈS (code 0)

Tous les contrôles **critiques** verts (parcelles ≥ attendu · 0 doublon · 0 géométrie invalide ·
100 % geom_2975 · 100 % évaluées · **bâti > 0** · zonage/pente/voirie présents · zonage ≥ 99 % ·
index GIST · verdicts cohérents · conservation) **et** le contrôle **QA** vert (taux d'opportunité
≤ 5 %, repère Saint-Paul ≈ 1 %) **et** aucune couche en échec. → commune **gold**.

## Conditions de RE-FETCH (code 3)

Seule(s) une/des **couche(s) NON critique(s)** en échec (ex. OSM Overpass, prescriptions GPU, ABF, SAR,
PPR, ravines). → relancer **uniquement** l'ingestion de cette couche (la commune reste utilisable, mais
pas encore « gold » tant que la couche manque). Re-fetch espacé (réseau), 1–2 tentatives, puis re-checker.

## Conditions de NO-GO QA (code 4)

Import techniquement réussi **mais résultat suspect** — typiquement **taux d'opportunité explosif**
(> 5 %, signe d'une cascade SANS bâti). → **ne PAS marquer gold**, investiguer (le bâti a-t-il bien
été ingéré ? la cascade a-t-elle tourné sur les bonnes couches ?). Pas de rollback automatique (données
non corrompues), mais la commune reste flaggée « non fiable » dans l'UI.

## Conditions de ROLLBACK / NO-GO avant lancement (code 1 / 2)

- **NO-GO avant lancement** si : cible hors référentiel · backup absent/corrompu · PostGIS/tables KO ·
  commune déjà gold (sans `--allow-regold`) · `--execute` sans la phrase exacte.
- **ROLLBACK après lancement** si : une **couche critique** échoue · un **contrôle critique** KO
  (compte aberrant, géométries invalides, bâti absent, conservation en baisse) · **crash** d'une étape.
  ```bash
  labuse restore-db --file /var/backups/labuse/<dump_pré>.dump --yes
  ```
  Les DELETE étant **scopés commune**, aucune autre commune n'est touchée même en cas d'arrêt brutal ;
  le rollback restaure l'état d'avant la commune.

## Garde-fous permanents (rappel)

- DELETE **toujours** `WHERE commune=:c` ; **jamais** de DELETE parcels (upsert id-préservant) ;
  **jamais** `--reset`/`--force` global.
- Confirmation **spécifique à la commune** → impossible de relancer la mauvaise commune par copier-coller.
- Tant qu'une commune n'est pas `gold`, l'UI affiche le **bandeau « Commune non validée — verdicts à ne
  pas utiliser commercialement »** (garde-fou `/communes/status` + `commune_reliability` en fiche).
