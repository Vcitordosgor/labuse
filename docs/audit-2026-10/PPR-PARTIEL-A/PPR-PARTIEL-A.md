# PPR-PARTIEL-A — la SDP se calcule sur la partie hors zone rouge

**Branche `fix/ppr-partiel-a`** (worktree `~/Desktop/labuse-ppra`, base `origin/main` `4bfd3c91`, l'étape B
est déjà mergée → lot 0 sauté). Ports réservés API **8719** / Vite **5919**. Opus.

> **ARRÊT À L'HEURE BUTOIR.** Le lot 3 (le run) ne peut pas être fini avant 14 h : le recalcul borné
> aux ~151 545 parcelles touchant du rouge est **chronométré à ≈ 5,5 h** (voir §4), bien au-delà de
> la trentaine de minutes disponibles. Conformément au mandat, **je m'arrête après le lot 2 et je le
> dis**. Les lots 1 et 2 (le code du moteur + les garde-fous) sont **écrits, testés et committés** ;
> le lot 3 (run q_v17) et le lot 4 (preuve avant/après) restent à faire — ils exigent le run. Rien
> n'a été poussé, **aucun run n'a été lancé, aucune bascule servie**.

---

## 1. La règle (lot 1) — `src/labuse/gabarit/builder.py:401-410` → commit `5cb21259`

Avant, dès qu'une parcelle **touchait** du rouge, le bloc SUP re-soustrayait l'enveloppe réglementaire
PPR entière `pm1` (**rouge + bleu**) via la clause `OR EXISTS (… subtype='INTERDICTION' … ST_Intersects)`,
alors que le **rouge seul** est déjà découpé juste au-dessus (exclusion `ppr-rouge`, `builder.py:348-365`).
Résultat : 3 888 parcelles U/AU > 500 m² hors rouge servies à 0 (588 ha, PPR-PARTIEL-1).

**Changement :** `pm1` n'est **plus jamais** re-soustraite (`sl.subtype <> 'pm1'` sans exception). Le
rouge reste déduit par l'exclusion `ppr-rouge` (qui **union**ne déjà les INTERDICTION superposés,
`ST_Union`, `:356`) ; le **bleu reste constructible** sous prescriptions, comme partout ailleurs. Le
gabarit vaut désormais > 0 sur la partie hors rouge.

**Cohérence cascade ↔ gabarit.** Le point de convergence est `parcel_faisabilite` (`faisabilite/db.py`,
chemin gabarit `:455-520`) : l'emprise est calculée sur la partie hors rouge (gabarit), et c'est **la
même géométrie** qui décide le verdict (plus de « HARD_EXCLUDE d'un côté, gabarit > 0 de l'autre »).
Le libellé client passe par `engine.py` (`_ASSIETTE_VIDE_LIB`, `_EXIGU_LIB`). *Note :* la couche cascade
`risques` (`cascade/layers/phase1.py`) n'émet `HARD_EXCLUDE` qu'à ≥ 50 % de couverture rouge ; le gisement
U/AU (AY0786 : 3 % de rouge) était rayé par la **sur-déduction `pm1`**, pas par ce HARD_EXCLUDE — c'est
bien `builder.py` qui tient la règle, et c'est là qu'elle est corrigée.

## 2. Les garde-fous (lot 2) — `faisabilite/db.py` `_hors_rouge_fragment_servable` → commit `6e5f75b4`

Les 588 ha sont du foncier **BRUT**. On ne sert la partie hors rouge **que si elle est exploitable**.
Sur le plus grand morceau d'un seul tenant de `parcelle − union(INTERDICTION)` :

| # | Garde-fou | Mise en œuvre | Si échec → motif explicite |
|---|---|---|---|
| 1 | **Tenant** | `ST_Dump` → plus grand fragment ; confettis ignorés | — (on ne garde que lui) |
| 2 | **Surface** | ce fragment ≥ 200 m² (`SEUIL_HORS_PPR_ROUGE_M2`) | `hors_rouge_trop_petit` |
| 3 | **Accès** | `classify_parcel_limits(sub_geom).has_voie` (`limites.py`) — enclavé derrière le rouge = 0 | `hors_rouge_sans_acces` |
| 4 | **Emprise** | l'emprise max PLU s'applique à la portion hors rouge via le gabarit (lot 1) | (dans le gabarit) |
| — | **Géométrie invalide** | SAVEPOINT (`begin_nested`) ; on garde 0 | `hors_rouge_invalide` |

Chaque échec **ramène l'emprise à 0 avec un motif en clair** (jamais un 0 muet) : le motif alimente
`vide_raison` → `_ASSIETTE_VIDE_LIB` / `_EXIGU_LIB` → fiche/Dossier/Copilote (« partie hors zone rouge
sans accès à la voie », « … inférieure à 200 m² », etc.).

**Exclusions FIX-1 §6 (comptées, jamais recalculées).** Le garde-fou ne s'exécute **que** pour les
parcelles dont le 0 tiendrait au **PPR rouge** (`ppr_rouge`). Une parcelle à 0 pour un **emplacement
réservé**, un **EBC**, des **contraintes certaines**, ou une **portion U/AU minuscule à cheval A/N**
(`portion_reduite`) garde **son** motif et **reste à 0** — elle n'est jamais balayée dans le gisement
hors rouge. C'est exactement la distinction que l'étape B (IR0368) réclamait.

### Compteurs mesurés (échantillon lecture seule, `harnais/compteurs.py`)
Sur **200 parcelles touchant du rouge** (les 200 premières par `id`, **toutes zones** — pas encore
filtrées U/AU, donc illustratif et **non** représentatif du gisement de 3 888) :

- **garde-fou hors rouge** : `servable` **166** · `hors_rouge_trop_petit` **34** · `sans_acces` 0 · `invalide` 0 ;
- **cause faisabilité** : `zone_transition` 139 · `terrain_exigu` 23 · `servie` 23 · `redhibitoire` 7 ·
  `habitat_interdit` 3 · `<none>` 5 ;
  - dont `terrain_exigu` → `portion_reduite` **19**, `ppr_rouge` **3**, `contraintes` **1**.

Lecture : l'échantillon par `id` est dominé par des parcelles A/N (`zone_transition` 139) qui **ne sont
pas** le gisement ; les **19 `portion_reduite` + 1 `contraintes` restent à 0 avec leur propre motif**
(exclusions FIX-1 §6 correctement **non** recalculées) ; seules les `ppr_rouge` passent par le garde-fou.
**Les compteurs définitifs (combien des 3 888 remontent, combien restent à 0 et pourquoi) exigent le
run borné + le filtre U/AU — c'est le lot 3.**

## 3. Tests — pas de régression

- **Unitaire PPR-PARTIEL-A** `tests/test_ppr_partiel_a.py` : **7 passed** (par injection) — tenant/surface,
  **seuil 200 exact** (200 → servi, 199,9 → trop petit), accès (`has_voie=False` → `sans_acces`), hors
  rouge vide (~100 % rouge → trop petit), découpage qui lève → `invalide`, et **libellés en clair** pour
  les 3 motifs.
- **pytest ciblé** (faisabilité, gabarit, résiduel, PPR marginal, exactitude, servitudes, **FIX-1 badge**) :
  **151 passed / 1 skip** (base-app indisponible). Le badge FIX-1 reste vert.
- **tsc `-b`** : **0 erreur**. **vitest** : **243 passed** (53 fichiers) — inchangé (modifs 100 % backend).
- **Smoke-test lecture seule** sur 40 parcelles réelles : moteur OK, verdicts cohérents.

## 4. Durée du run (chronométré) — pourquoi le lot 3 ne tient pas avant 14 h

`harnais/chrono_run.py`, recalcul `parcel_faisabilite` (cœur per-parcelle du résiduel) sur un échantillon
réel : **130 ms/parcelle** (séquentiel, une connexion). Extrapolé aux **151 545** parcelles touchant du
rouge : **≈ 328 min ≈ 5,5 h** — pour le seul cœur per-parcelle, hors scoring. Même par le chemin résiduel
batché (preuve docs SCORING ≈ 15 ms/parcelle), on reste à ~40 min de résiduel + dépendances + ~8 min de
scoring. **Dans tous les cas > la trentaine de minutes avant 14 h.** Ajout : le simple comptage spatial
des parcelles rouges prend déjà plusieurs minutes. **Je n'ai donc pas lancé de run** (il ne pourrait pas
finir, et il écrirait sur une base partagée avec une autre session active).

## 5. Ce que Vic doit faire pour servir q_v17 (lot 3 + lot 4, hors fenêtre)

1. **Lister le gisement** (parcelles U/AU touchant du rouge) dans un fichier :
   ```sql
   \copy (SELECT p.id FROM parcels p WHERE EXISTS (SELECT 1 FROM spatial_layers sl
     WHERE sl.kind='ppr' AND sl.subtype='INTERDICTION' AND ST_Intersects(sl.geom_2975,p.geom_2975)))
     TO 'ppra_rouge.txt'
   ```
2. **Run résiduel non servi** (`residuel_runs` → nouveau `run_seq`, jamais `is_served`) :
   ```
   PYTHONPATH=src python -m labuse compute-residuel --new-run q_v17 \
     --parcelles-fichier ppra_rouge.txt --chunk 500
   ```
3. **Scoring** sur ce run → bandes, non servi :
   ```
   PYTHONPATH=src python -m labuse score-labuse --run q_v17
   ```
4. **Preuve (lot 4), à produire après le run** : tableau des bandes q_v16 → q_v17 (île entière) ;
   **0 écart** sur ≥ 1 000 parcelles **sans** rouge (seules les parcelles touchant du rouge peuvent
   bouger) ; les 15 cas de l'audit avec SDP/bande avant/après (AY0786 et IR0368 doivent remonter —
   AY0786 par la règle, IR0368 reste exclu si son 0 tient à l'emplacement réservé, cf. FIX-1 §6) ;
   20 parcelles où un garde-fou a déclenché (10 « sans accès », 10 « trop petit ») vérifiées à la main ;
   10 parcelles montées en bande A/B avec capture carte (rouge + zone d'implantation) ; verrou
   écran = PDF = Copilote sur AY0786.
5. **Bascule** (servir q_v17) depuis la page Données **après lecture du rapport** — pas avant.

## 6. État de la branche
- Commits : `5cb21259` (lot 1), `6e5f75b4` (lot 2). **Rien n'est poussé.**
- Aucun run lancé, aucune bascule, aucune écriture dans les tables de résultats servies.
- Harnais rejouables (lecture seule) : `harnais/chrono_run.py`, `harnais/compteurs.py`.

## Annexe — environnement
Base `labuse` (`postgresql+psycopg://openclaw@localhost:5432/labuse`), venv `~/Desktop/labuse/.venv`,
`PYTHONPATH=src`. Une autre session faisait tourner son API sur le port **8721** (connexions idle, non
touchées). Aucun calcul géométrique concurrent détecté sur la base pendant les mesures. Arrêt propre :
aucun backend démarré par cette session (8719/5919 jamais ouverts), 0 transaction idle-in-transaction.
