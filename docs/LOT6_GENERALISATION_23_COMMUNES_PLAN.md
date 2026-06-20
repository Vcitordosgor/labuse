# LOT 6 — Généralisation aux 23 autres communes (diagnostic + plan)

> **Analyse et préparation uniquement.** Aucun import lancé, aucune écriture base, aucune cascade,
> aucun verdict modifié, aucun déploiement, aucun merge. Diagnostic au **2026-06-20** (base live).
> Tous les chiffres « en base » sont issus de requêtes réelles ; les comptes Etalab attendus ne sont
> **pas inventés** (à récupérer à l'import).

> **Mise à jour — socle LOT 6 créé (toujours sans import réel).** Les 5 décisions sont validées :
> (1) communes non gold **masquées/flaggées** → garde-fou UI livré ; (2) backups par commune + vagues ;
> (3) tests **La Possession + L'Étang-Salé** ; (4) **re-couches + re-cascade** sur les 18 présentes ;
> (5) **écrasement** des verdicts non fiables accepté. Livrés : `config/communes_gold_standard.yaml`,
> `src/labuse/communes.py` (+ endpoint `/communes/status` + `commune_reliability` en fiche + bandeau UI),
> `scripts/import_commune_gold_standard.py` (**dry-run only**), `docs/LOT6_RUNBOOK.md`, tests.

---

## 0. Le constat qui change tout

La base **n'est pas vide** : **18 des 24 communes** ont déjà leur cadastre (377 194 parcelles,
`geom_2975` calculé à 100 %). **MAIS une seule commune — Saint-Paul — possède les couches critiques
complètes** (bâti, PPR, SAR, ravines, OSM, prescriptions, ABF). Les 17 autres ont été ingérées par un
**pipeline plus ancien** (voirie plafonnée à 5 000, **sans bâti / PPR / SAR**).

Conséquence directe et mesurée :

| | Saint-Paul (couches complètes) | 11 communes évaluées SANS bâti/PPR/SAR |
|---|---|---|
| Taux d'« opportunité » | **1,0 %** | **3,5 % → 11,2 %** |
| Faux positifs détectés | **29 943** | **0** |

👉 **Les verdicts des 11 communes déjà évaluées sont gonflés et NON fiables** : sans bâti, le garde-fou
R1 « déjà bâti » ne s'applique pas → des parcelles construites passent en « opportunité ». **Ces
verdicts ne doivent pas être montrés à un promoteur tant que la commune n'est pas refaite au standard.**

Le travail de généralisation n'est donc PAS « importer 23 cadastres » — c'est surtout **compléter les
couches critiques + recalculer la cascade**, commune par commune, au niveau Saint-Paul.

---

## 1. État actuel des communes (diagnostic)

Trois états réels (pas deux) :

- **GOLD (1)** — Saint-Paul : cadastre complet, toutes couches, 100 % évalué, verdicts fiables.
- **PARTIEL (17)** — cadastre + `geom_2975` + couches de base (safer, trait de côte, PLU zones, pente,
  voirie *plafonnée*), **mais sans bâti / PPR / SAR / ravines / OSM / prescriptions / ABF**. Sous-cas :
  - **PARTIEL-ÉVALUÉ (11)** : évaluées à 100 % **sur données incomplètes** → verdicts non fiables.
  - **PARTIEL-NON-ÉVALUÉ (6)** : cadastre présent, **0 % évalué** (Saint-Denis, Saint-Louis,
    Saint-Joseph, Saint-Leu, Saint-André, Saint-Philippe).
- **ABSENT (6)** — aucune donnée : Sainte-Marie, Sainte-Rose, Sainte-Suzanne, Salazie,
  Les Trois-Bassins, Cilaos.

**Couches : qui a quoi (entités, échantillon).** Seules présentes pour **toutes** : safer,
trait_de_cote, plu_gpu_zone, ocs_ge, potentiel_foncier, foret_publique, parc_national, pente (17/18),
voirie (17/18, **plafonnée à 5 000**), water, ens, + DVF (table dédiée, 18/18). **Présentes pour
Saint-Paul SEUL** : `batiment` (83 981), `ppr` (4), `sar` (303), `ravine` (1 244),
`osm_faux_positif` (808), `plu_gpu_prescription` (710), `abf` (1).

**Anomalies détectées :**
- ⚠ **voirie plafonnée à 5 000** sur 14 communes (cap d'un ancien run ; le code actuel monte à 8 000).
  → la distance-à-la-voirie (proxy d'accès) est sous-échantillonnée pour les grandes communes.
- ⚠ **La Possession : voirie = 0** ; **Saint-Leu : pente = 0** (couches manquantes à recharger).
- ⚠ **Saint-Philippe : PLU = 19 prescriptions seulement** (couverture GPU faible — à vérifier).
- ✅ **0 anomalie cadastrale** : 0 commune NULL, 0 IDU dupliqué, 0 variante de casse, `geom_2975` à 100 %.

**Complétude cadastre vs Etalab :** le compte « en base » des 18 communes présentes **semble complet**
(ordres de grandeur cohérents), mais un ancien `--limit` a pu plafonner certains imports.
→ **À confirmer à l'import** : le script télécharge l'extrait Etalab (`cadastre.data.gouv.fr`, par INSEE)
et **compare son compte au compte en base**. C'est le seul juge de la complétude (jamais un chiffre inventé ici).

---

## 2. Tableau des 24 communes

Source INSEE↔nom : `src/labuse/ingestion/run_all.py:26-39` (`REUNION_COMMUNES`, d'après geo.api.gouv.fr).
« Attendu » = à confirmer vs Etalab à l'import. Priorité/risque/temps = estimations (cf. §4/§6).

| Commune | INSEE | Attendu | En base | Sections | Éval. | État | Priorité | Risque | Temps est. (couches+cascade) |
|---|---|---|--:|--:|:--:|---|:--:|:--:|--:|
| **Saint-Paul** | 97415 | ✓ | 51 129 | 98 | 100 % | **GOLD** | — | — | fait |
| La Possession | 97408 | confirmer | 13 338 | 30 | 100 %* | partiel | **TEST 1** | faible | ~1 h 30 |
| L'Étang-Salé | 97404 | confirmer | 9 070 | 19 | 100 %* | partiel | **TEST 2** | faible | ~1 h |
| Saint-Pierre | 97416 | confirmer | 42 425 | 66 | 100 %* | partiel | haute (comm.) | moyen | ~3 h 30 |
| Le Tampon | 97422 | confirmer | 42 756 | 79 | 100 %* | partiel | haute (comm.) | moyen | ~3 h 30 |
| Saint-Leu | 97413 | confirmer | 22 959 | 50 | 0 % | partiel | haute (balnéaire) | moyen | ~2 h 30 (pente=0 à recharger) |
| Saint-Louis | 97414 | confirmer | 29 241 | 53 | 0 % | partiel | haute | moyen | ~2 h 30 |
| Saint-André | 97409 | confirmer | 22 600 | 33 | 0 % | partiel | moyenne | moyen | ~2 h |
| Saint-Benoît | 97410 | confirmer | 21 671 | 50 | 100 %* | partiel | moyenne | moyen | ~2 h |
| Saint-Joseph | 97412 | confirmer | 28 959 | 57 | 0 % | partiel | moyenne | moyen | ~2 h 30 |
| Le Port | 97407 | confirmer | 10 195 | 26 | 100 %* | partiel | moyenne | faible | ~1 h 15 |
| Petite-Île | 97405 | confirmer | 13 137 | 25 | 100 %* | partiel | moyenne | faible | ~1 h 30 |
| Les Avirons | 97401 | confirmer | 8 611 | 15 | 100 %* | partiel | basse | faible | ~1 h |
| Bras-Panon | 97402 | confirmer | 6 041 | 14 | 100 %* | partiel | basse | faible | ~1 h |
| **Saint-Denis** | 97411 | confirmer | 38 138 | 124 | 0 % | partiel | haute (chef-lieu) | **élevé** (lourd) | ~4 h |
| Entre-Deux | 97403 | confirmer | 6 312 | 13 | 100 %* | partiel | basse | moyen (relief) | ~1 h |
| La Plaine-des-Palmistes | 97406 | confirmer | 6 450 | 18 | 100 %* | partiel | basse | moyen (relief) | ~1 h |
| Saint-Philippe | 97417 | confirmer | 4 162 | 29 | 0 % | partiel | basse | moyen (volcan/GPU faible) | ~1 h |
| Sainte-Marie | 97418 | **Etalab** | **0** | — | — | **ABSENT** | moyenne | moyen | import + ~2 h |
| Sainte-Suzanne | 97420 | **Etalab** | **0** | — | — | **ABSENT** | moyenne | moyen | import + ~1 h 30 |
| Sainte-Rose | 97419 | **Etalab** | **0** | — | — | **ABSENT** | basse | moyen (volcan) | import + ~1 h |
| Les Trois-Bassins | 97423 | **Etalab** | **0** | — | — | **ABSENT** | basse | faible | import + ~1 h |
| Salazie | 97421 | **Etalab** | **0** | — | — | **ABSENT** | basse | **élevé** (cirque) | import + ~1 h |
| Cilaos | 97424 | **Etalab** | **0** | — | — | **ABSENT** | basse | **élevé** (cirque) | import + ~1 h |

\* *« 100 % » = évalué, mais sur **couches incomplètes** → verdicts NON fiables (à refaire au standard).*

**Budget global estimé** (d'après le point Saint-Paul : cascade ≈ 0,137 s/parcelle après l'index voirie) :
- Cascade seule, 23 communes ≈ **15–18 h** cumulées (chunks de 2 000, en série).
- Couches (dominées par le **bâti WFS** paginé + la **pente** par grille API) : ~30 min–2 h/commune.
- **Total ≈ 45–55 h** de traitement non surveillé, à étaler en vagues.
- **Stockage** : 2,0 Go aujourd'hui (18 communes, 1 seule entièrement couchée) → **~5–8 Go** au standard
  complet (le bâti pour les 24 communes est la principale croissance). **Large dans 75 Go SSD.**
  RAM 8 Go OK (cascade chunkée, `session.expunge_all()` par lot).

---

## 3. Méthode de réplication « gold standard » (process générique)

Dérivée de ce qui a marché sur Saint-Paul (LOT 1→2), pour **une commune** :

1. **Backup AVANT commune** — `labuse backup-db --dir /var/backups/labuse` → dump horodaté + `.sha256`
   (hors git). Vérifié (existence + checksum) avant toute écriture. *Point de retour par commune.*
2. **Import cadastre complet** — `cadastre_bulk.download_parcelles(INSEE)` →
   `ingest_parcels(..., commune, run_id)` (**upsert ON CONFLICT (idu)** : jamais de purge des parcelles ;
   `ST_MakeValid` + surface/centroïde). **Compare le compte au fichier Etalab** (juge de complétude).
3. **`ensure_geom_2975(commune=…)`** — backfill métrique 2975 + triggers (idempotent, scope commune).
4. **Ré-ingestion ciblée des couches** — `DELETE FROM spatial_layers WHERE commune=:c` (+ `dvf_mutations`)
   **scopé commune**, puis `layers_ingest.ingest_layers(s, INSEE, commune, bbox, run_id)`. Chaque couche
   sous **SAVEPOINT** (un échec n'abîme pas les autres). Cible explicite des couches manquantes :
   **bâti, PPR, SAR, ravines, OSM, prescriptions, ABF** (+ voirie/pente rechargées à 8 000).
5. **Index nécessaires** — déjà **globaux** et idempotents (`ensure_schema` / `ensure_geom_2975`) :
   `idx_parcels_geom_2975`, `idx_spatial_layers_geom_2975`, **`idx_spatial_layers_voirie_geom2975`**
   (partiel `WHERE kind='voirie'` — indispensable, sinon cascade en heures), `idx_dvf_geom_2975`.
   *Rien à recréer par commune ; juste vérifier leur présence avant cascade.*
6. **Recalcul cascade commune** — `run_all.evaluate_commune(s, commune, chunk=2000)` (commit + purge
   mémoire par lot). Le `prime()` précharge les intersections en lot (1 requête/famille).
7. **Post-checks** (bloquants/non-bloquants) — comme LOT 2 : compte ~Etalab, sections, `geom_2975`
   valide, **couches critiques présentes** (bâti > 0, PPR/SAR en statut explicite), zonage ≥ seuil,
   **0 doublon**, **anti-fausse-opportunité** (top-N sans bâti > 50 %), 100 % évalué, **conservation**
   (pipeline/feedback/alertes non décroissants).
8. **Rapport commune** — `docs/communes/<commune>_RESULTS.md` (parcelles, sections, verdicts, couches,
   temps, anomalies, conclusion gold/à-reprendre).
9. **Backup APRÈS vague** — dump horodaté + sha256, restauration testée, documenté hors git.
10. **Rollback** — si check critique échoue ou crash : `labuse restore-db --file <backup_avant> --yes`
    (restaure l'état d'avant la commune). DELETE scopés = aucune autre commune touchée même en cas d'arrêt.

> **Réutilisable tel quel** (paramétrés commune/INSEE) : `download_parcelles`, `ingest_parcels`,
> `ingest_layers`, `evaluate_commune`, `purge_commune`, `backup-db`/`restore-db`, les index globaux.
> **Saint-Paul-spécifique (à paramétrer)** : les constantes `EXPECTED_*`, le seuil zonage, le chemin de backup.

---

## 4. Ordre stratégique des 23 communes

Logique : **valider d'abord sur 2 communes moyennes peu risquées et déjà cadastrées** (feedback rapide,
pipeline « du présent » testé), **puis les grosses communes commerciales**, en **gardant les cirques /
volcan / chef-lieu lourd pour la fin**.

**Vague 1 — TESTS (2 communes moyennes, présentes, peu risquées)**
1. **La Possession (97408, 13 338)** — *intercommunalité TCO comme Saint-Paul* → même écosystème PLU/GPU
   (la partition GPU `97408` apparaît déjà sur Saint-Paul). Cadastre présent, taille moyenne → le pipeline
   a la **plus forte chance de « juste marcher »**. Valide le flux *re-couches + re-cascade* sur une commune existante.
2. **L'Étang-Salé (97404, 9 070)** — *autre intercommunalité (sud/CIVIS)*, balnéaire, plat, taille moyenne →
   valide le pipeline sur **une source PLU/données DIFFÉRENTE**, attrape tôt les surprises commune-spécifiques.

→ *On teste ainsi « même écosystème » ET « écosystème différent » avant d'engager les grosses.*

**Vague 2 — COMMERCIALES IMPORTANTES (forte valeur promoteur, cadastre présent)**
3. Saint-Pierre (97416, 42 425) · 4. Le Tampon (97422, 42 756) · 5. Saint-Leu (97413, 22 959, balnéaire ouest)
· 6. Saint-Louis (97414, 29 241). *Gros volumes, marché actif — le cœur de cible promoteur.*

**Vague 3 — MOYENNES (cadastre présent, valeur correcte)**
7. Saint-André · 8. Saint-Joseph · 9. Saint-Benoît · 10. Le Port · 11. Petite-Île · 12. Les Avirons · 13. Bras-Panon.

**Vague 4 — CHEF-LIEU LOURD**
14. **Saint-Denis (97411, 38 138, 124 sections)** — chef-lieu, urbanisme complexe, la **plus lourde** ;
    à traiter une fois le process rodé, en fenêtre dédiée.

**Vague 5 — ABSENTES à valeur moyenne (import complet)**
15. Sainte-Marie (97418) · 16. Sainte-Suzanne (97420) · 17. Sainte-Rose (97419). *Nord/est ; nécessitent le cadastre.*

**Vague 6 — ATYPIQUES / RELIEF (en dernier)**
18. Entre-Deux · 19. La Plaine-des-Palmistes · 20. Saint-Philippe (relief/volcan, GPU faible) ·
21. Les Trois-Bassins (absente) · 22. **Salazie** · 23. **Cilaos** *(cirques : relief extrême, urbanisme
atypique, PPR lourds, peu de foncier mutable → faible valeur promoteur, forte complexité → tout à la fin).*

**Pourquoi cet ordre.** (a) On **ne commence pas par le risqué** (cirques, chef-lieu) ni par l'absent.
(b) Les 2 tests sont **déjà cadastrés** → on isole le maillon nouveau (couches+cascade) sans le risque
cadastre. (c) On rentabilise vite en traitant **les communes à forte valeur promoteur** juste après
validation. (d) Les **cirques et le volcan** (peu de foncier, urbanisme atypique) ferment la marche.

---

## 5. Script générique — analyse (NON transformé)

Transformer `scripts/lot2_import_saint_paul.py` → `scripts/import_commune_gold_standard.py`. La
machinerie existe déjà (`ingest-island`, `evaluate_commune`, `purge_commune`) ; le script ajoute les
**garde-fous gold standard par commune**.

**Paramètres à rendre variables** (aujourd'hui codés en dur pour Saint-Paul) :
- `commune`, `insee` — **obligatoires en argument**, validés contre `REUNION_COMMUNES` (run_all).
- `expected_parcels` — **déterminé à l'import** depuis le fichier Etalab (pas une constante) ; tolérance.
- `expected_sections` — **calculé**, contrôle **non bloquant**.
- Seuils QA : `zonage_min_pct`, minima couches critiques (bâti > 0, etc.), tolérance parcelles.
- Chemins : backup avant/après, rapport `docs/communes/<commune>_RESULTS.md`.
→ Externaliser dans **`config/communes_gold_standard.yaml`** (une entrée par commune, remplie au fil de l'eau).

**Garde-fous à garder STRICTS** (repris de LOT 2) :
- **Dry-run par défaut** ; mode réel = `--execute` **ET** `--confirm "IMPORT_<COMMUNE>_COMPLET"`.
- **DELETE scopés `WHERE commune=:c` UNIQUEMENT** (spatial_layers, dvf) ; **jamais** de DELETE parcels,
  **jamais** `--reset`/`--force` global.
- **Backup vérifié AVANT** (existence + sha256) ; sinon refus.
- Couches **critiques** (plu_gpu_zone, batiment, pente, voirie) en échec → **ROLLBACK** ; non critiques → **RE-FETCH**.
- Codes de sortie distincts (succès / rollback / confirm manquant / re-fetch) ; `main()` ne dit jamais « succès » à tort.
- Contrôle de **conservation** (pipeline/feedback/alertes non décroissants) avant/après.

**Comment éviter une erreur de commune :**
- INSEE **et** nom doivent **correspondre** dans `REUNION_COMMUNES` (sinon abort).
- La **phrase de confirmation nomme la commune** (`IMPORT_LA_POSSESSION_COMPLET`) → impossible de lancer
  La Possession avec un confirm copié de Saint-Paul.
- Refus si la commune cible == une commune **déjà GOLD** sans `--allow-regold` explicite (protège Saint-Paul).

**Comment empêcher une suppression accidentelle :**
- DELETE **toujours** scopés commune ; aucune requête sans `WHERE commune`.
- Parcelles en **upsert** (jamais supprimées).
- Backup obligatoire + vérifié avant ; dry-run par défaut ; double flag pour le réel.

**Backups :** `backup-db` avant chaque commune (point de retour) ; backup **après chaque vague** (jalon
restaurable). Nommage `labuse-<commune>-pre/post-<horodatage>.dump` + sha256, hors git, rétention.

**Rapport par commune :** générer `docs/communes/<commune>_RESULTS.md` (gabarit commun) : parcelles
vs Etalab, sections, verdicts (taux opp, faux positifs — **doit ressembler à Saint-Paul, pas 11 %**),
couches (présence/compte), temps, anomalies, conclusion.

**Couches critiques :** liste explicite à garantir (bâti, PPR, SAR + plu/pente/voirie) ; post-check
bloquant « bâti > 0 et top-N sans bâti > 50 % » (le garde-fou anti-fausse-opportunité de Saint-Paul).

**Éviter les doublons de couches :** modèle **delete-before-insert scopé commune** (déjà en place) —
le DELETE `WHERE commune=:c` précède toute ré-ingestion ; pas de contrainte d'unicité à ajouter.

**Reprendre si une couche WFS échoue :** chaque couche est isolée par **SAVEPOINT** (`begin_nested`) ;
l'échec est capturé en `"ERREUR …"` dans le dict de comptes. Le script : (a) **re-fetch** automatique des
non-critiques (1 réessai espacé) ; (b) **rollback** si une critique échoue ; (c) **résumabilité** via
`ingestion_runs.status` (les communes « ok » sont sautées sauf `--force`, comme `ingest-island`).

---

## 6. Risques (classés)

**🔴 BLOQUANT** (empêchent le standard / dangereux)
- **Échec WFS total d'une couche critique** (bâti / PPR / SAR) pour une commune → pas de gold standard
  possible (verdicts non fiables). *Mitigation : re-fetch + report « à reprendre », ne pas publier.*
- **Suppression inter-communes accidentelle** → *mitigée par DELETE scopés + backup avant + dry-run/double-flag.*
- **Cascade sans l'index voirie** → recalcul en heures. *Mitigée : index global, vérifié avant cascade.*
- **Publier les 11 communes « évaluées » non fiables** (opportunités gonflées, parcelles bâties) →
  risque de **crédibilité majeur** en démo. *Décision produit requise (cf. §7).*

**🟠 IMPORTANT** (ralentissent / dégradent, gérables)
- **WFS instable** (PPR, OSM Overpass, GPU prescriptions) → re-fetch nécessaire ; certaines communes
  itéreront. **PPR partiel** possible (couverture inégale selon commune).
- **Durée cascade** sur grosses communes (Saint-Denis ~4 h, Le Tampon/Saint-Pierre ~3 h 30) → fenêtres dédiées.
- **Voirie plafonnée (5 000→8 000)** : même à 8 000, les très grandes communes peuvent tronquer → accès
  sous-échantillonné. *À surveiller (post-check distance voirie).*
- **Stockage** : bâti × 24 + re-cascade → ~5–8 Go (OK 75 Go, mais à monitorer).
- **RAM VPS (8 Go)** pendant la cascade d'une grosse commune → *mitigée par les chunks de 2 000.*

**🟢 NON BLOQUANT**
- Variance du **nombre de sections** ; petites communes triviales.
- **Couverture DVF** inégale (petites communes = moins de comparables → bilans « fragiles », déjà géré honnêtement).
- **Communes à relief** (cirques, volcan) : peu de foncier mutable → **peu d'opportunités, mais c'est CORRECT**
  (la cascade exclut à raison). Faible valeur, pas un bug.

---

## 7. Recommandation finale

**Peut-on généraliser maintenant ? → OUI SOUS RÉSERVE.**
La machinerie existe et est éprouvée sur Saint-Paul (`ingest-island`, `evaluate_commune`, garde-fous LOT 2).
Réserves à lever d'abord : (1) **genericiser** les garde-fous LOT 2 en `import_commune_gold_standard.py` ;
(2) trancher le **sort des 11 communes non fiables** (les masquer/flaguer tant qu'elles ne sont pas refaites) ;
(3) **valider bâti/PPR/SAR par WFS** sur 2 communes test ; (4) cadrer **backups + budget temps/disque**.

- **1ʳᵉ commune après Saint-Paul : La Possession (97408)** — TCO (même écosystème), cadastre présent,
  taille moyenne → validation la plus sûre du flux re-couches + re-cascade.
- **2ᵉ commune : L'Étang-Salé (97404)** — autre intercommunalité, balnéaire, pour valider le pipeline sur
  une **source de données différente** avant les grosses.
- **Meilleur ordre des 23** : voir §4 (6 vagues : 2 tests → commerciales → moyennes → chef-lieu lourd →
  absentes moyennes → cirques/volcan en dernier).

**Fichiers / scripts à créer ensuite :**
- `scripts/import_commune_gold_standard.py` (générique + garde-fous, dry-run par défaut).
- `config/communes_gold_standard.yaml` (par commune : INSEE, seuils QA, attendu rempli à l'import).
- `docs/communes/<commune>_RESULTS.md` (gabarit de rapport par commune).
- `docs/LOT6_RUNBOOK.md` (runbook des vagues : commandes exactes, ordre, backups, rollback).
- *(option)* flag/colonne **`reliable_ready` par commune** pour masquer en UI les communes non encore au standard.

**À valider avec toi AVANT le premier import réel :**
1. **Les 11 communes non fiables** : on les **masque/flague** en attendant leur refonte ? (recommandé — éviter de montrer des opportunités gonflées).
2. **Stratégie de backup** par commune + **budget disque/temps** (fenêtres VPS) acceptés ?
3. **Paire de test** validée : **La Possession + L'Étang-Salé** ?
4. **Re-couches des 18 communes présentes** (ré-ingestion couches manquantes) confirmé comme la bonne approche (vs ré-import complet) ?
5. **Sort des verdicts existants** : on **recascade** (écrase) les 11 communes — OK puisque non fiables ?

---

*Diagnostic + plan, lecture seule. Aucun import, aucune écriture base, aucune cascade, aucun verdict
modifié. Prochaine étape sur ton GO : créer `import_commune_gold_standard.py` (toujours sans exécution),
puis lancer La Possession en dry-run.*
