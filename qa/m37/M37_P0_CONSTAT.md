# M37 — Phase 0 : RECENSEMENT rail legacy + vigilances + matrice — STOP arbitrage Vic

**Branche `m37-extinction-rail-legacy` · base main 89baeaf1 · LECTURE SEULE** (recensement +
dump ; aucune extinction avant feu vert). Cartes de départ : `qa/m34/M34_P0_CONSTAT.md` +
inventaire matrice du bilan M34, re-vérifiées (code bougé M35/M36/M33). Deux agents Explore +
vérification manuelle de leurs affirmations load-bearing.

## Lot 0.2 — Audit « Confiance et données » (90 %/100 %) : c'est l'ICD, à GARDER

Le tiroir sert `f.icd.score` — l'**Indice de Confiance Données** (`scoring/icd.py`, 9 groupes
nullables), PAS la Complétude retirée en M36. Distribution mesurée sur le run servi :
**19 valeurs distinctes de 5 à 100, médiane 90, moyenne 80,4** (90 → 186 537 parcelles, 70 →
89 837, 100 → 45 740, 60 → 23 889, …). C'est une grandeur RÉELLEMENT informative (contraste
avec les 3 valeurs de la Complétude). **Reco : GARDER** — c'est précisément le remplaçant que
M36 a préservé. Aucune implémentation (audit-only, conforme au mandat).

## 1 · Vigilances — SÛRES : elles ne dépendent PAS de `parcel_evaluations.status`

Chaîne tracée (2 agents + DB) : `apply_declassement` (`scoring/declassement.py`) retourne
`(status, motif)`. Le **motif** (accès/pente/surface/OSM/bâti partiel) devient un
`soft_flag("declassement", …)` persisté dans **`cascade_results.detail`** (live) et
**`dryrun_cascade_results.detail`** (run servi) — `pipeline.py:117-124`. Le **status** (l'autre
valeur de retour) va dans `parcel_evaluations.status` (mort) — SÉPARÉ du motif.

`resume._vigilance` agrège 6 sources, AUCUNE n'est `parcel_evaluations.status` :
downgrade_reason (= cascade_results.declassement), bâti peu_bati (bati.py), couches
HARD_EXCLUDE/SOFT_FLAG (cascade), SAR divergent (cascade), bilan fragile (faisabilité),
propriétaire (dérivé). **Vérifié DB** : AT2542 porte le même libellé de vigilance dans les
DEUX tables cascade — indépendant de `status`.

→ **Éteindre `parcel_evaluations.status` ne perd/modifie/invente AUCUNE vigilance servie.**
Corollaire : la Phase 1 étape 1 (« re-sourcer les vigilances ») est un **quasi no-op** — elles
sont déjà correctement sourcées depuis cascade_results, hors du rail éteint.

**Dump exhaustif AVANT (addendum)** : `qa/m37/dump_vigilances.py` → **4 344 938 lignes de
vigilance sur 431 632 parcelles** (couche declassement + tout HARD_EXCLUDE/SOFT_FLAG, DEUX
tables cascade). Artefacts versionnés : `vigilances_avant_digest.csv.gz` (sha256 par parcelle)
+ `vigilances_avant_global.txt` (**sha256 global
`482da6f6848989b34aac7cbafcddc413079c5c2e1a9bd1b4bf186b1689e9abe9`**). Le re-dump APRÈS doit
donner le même sha global — sinon STOP.

## 2 · Lecteurs/writers de `parcel_evaluations.status` — cut list

### Writers (chaîne cascade `_persist`, pipeline.py:183)
| Point | Servi client ? | Extinction |
|---|---|---|
| `POST /parcels/{idu}/evaluate` (app.py:3050) | **NON** (pas appelé par le front — vérifié grep ; endpoint admin/ops) | passer en dry-run OU ne pas persister `status` |
| `signals.py` veille (offre C), `cli.py`, `ingestion/run_all.py`, `audit.py` | NON (CLI/batch/interne) | idem — geler l'écriture de `status` |

Le writer central = `_persist` (pipeline.py). Extinction = cesser d'écrire la colonne `status`
(garder le reste de la ligne : opportunity_score/completeness_score/evaluated_at et surtout la
ligne cascade_results de vigilance, INCHANGÉE).

### Lecteurs — verdict « bloque OUI/NON » (vérifié manuellement, agents corrigés)
| Lecteur | fichier:ligne | Servi ? | Bloque ? |
|---|---|---|---|
| **fiche web** `_build_fiche` | app.py:2541 (`_latest_eval`) | le verdict vient de `verdict_servi` (M34) ; `ev` ne fournit plus que opportunity/completeness (retirés de l'affichage M36) + evaluated_at | **NON** — `ev.status` n'est plus lu pour une valeur servie |
| **`/map/parcels.geojson` fallback** (source absent) | app.py:1320 (`e.status`) | **NON servi** : le front envoie TOUJOURS `?source=q_v8_calibre` via le helper `q()` (source: SOURCE) → branche v2 `_q_v2_geojson` (matrice). Le fallback n'est atteint QUE par les tests. **⚠ Les 2 agents l'ont cru bloquant — FAUX, ils n'ont pas lu `q()`.** | **NON** (mort pour le produit) |
| POST feedback `e.status = body.status` (app.py:3407) | endpoint de feedback | écrit status | à geler (non servi comme verdict) |
| `assemblage.py:53`, `demo.py`, `audit.py`, `ai/prompt.py:61` (cascade_status) | — | interne/démo/prompt | NON |
| `division_or.py:262` (`de.status='exclue'`) | builder | interne (signal dérivé) | NON — à re-sourcer sur tier si besoin |
| tests (`test_api`, `test_protection`, …) | tests | — | à mettre à jour au geste |

**Conclusion** : **aucun lecteur SERVI ne bloque l'extinction**. Le verdict est déjà 100 % tier
(M34). Le rail `status` est mort pour le produit ; il ne survit qu'en écriture (cascade batch)
et en lecture interne/tests.

## 3 · DIFF vs M34-P0 (nouveautés — règle d'escalade)

M34-P0 cartographiait le chemin **fiche**. Éléments qui touchent encore `parcel_evaluations.
status` et n'y figuraient pas explicitement (tous NON servis comme verdict) :
1. `/map/parcels.geojson` fallback legacy (dead-for-product, vivant pour tests/API directe) ;
2. `POST /parcels/{idu}/evaluate` (writer admin) ;
3. writers CLI/batch (veille, run_all, audit, cli) ;
4. POST feedback (`e.status = body.status`) ;
5. `division_or.py` (`de.status='exclue'`, builder de signal dérivé).

**Aucun n'est une divergence SERVIE** (contrairement à la crainte initiale des agents sur la
carte — infirmée). Pas de nouveau writer inattendu du verdict servi, pas de dépendance croisée
cachée. **Je ne préjuge pas** : si tu juges ce diff trop large pour une Phase 1 immédiate, tu
peux la reporter — mais mon évaluation est qu'il est SÛR (le verdict est tier depuis M34, les
vigilances sont hors rail).

## 4 · Inventaire `matrice_statut` à jour (dryrun_parcel_evaluations.matrice_statut)

⚠ **`matrice_statut` ≠ `parcel_evaluations.status`** : c'est l'axe Q×A du run SERVI, VIVANT,
distinct du rail éteint. M36 l'a ré-étiqueté « historique » à l'affichage. Reco par surface
(tu tranches) :

| Surface | fichier:ligne | Servi | Reco |
|---|---|---|---|
| Chip « Statut matrice (historique) » fiche | Fiche.tsx:1520 | oui (tiroir Confiance) | **SORTIE** (tier + ICD suffisent) |
| TierBadge « (matrice : X) » (outils) | TierBadge.tsx | oui (secondaire) | **SORTIE** |
| Légende carte repli | Legend.tsx | oui (repli) | maintien (déjà « Classement historique » M36) |
| Sélections modules Outils (`matrice_statut IN …`) | modules.py:599/606/1076 | oui (quels parcelles les outils renvoient) | **bascule tiers** (aligne M35 /communes) — change de comportement, arbitrage |
| Digest veille (transitions) | events.py:86… | oui (alertes) | maintien OU bascule tiers — arbitrage |
| API partenaire (payload `statut`) | partners.py:121/457 | externe | bascule tiers (mention déjà honnête M36) |
| Recherche (`matrice_statut AS status`) | app.py:1189 | oui (liste) | vérifier : le front colore par tier_v2 → probablement inerte, à confirmer |
| Tuiles MVT | tiles.py:141 | oui (île) | maintien (tuiles portent tier_v2 ; matrice = méta) |

## 5 · Plan d'extinction proposé (Phase 1, après feu vert)

1. **Vigilances** : rien à re-sourcer (déjà hors rail) — juste le dump APRÈS pour preuve.
2. **Geler le writer** : `_persist` n'écrit plus `parcel_evaluations.status` (garde le reste).
   `POST /evaluate` + feedback + CLI : ne plus persister `status`.
3. **Couper les lecteurs** un par un (tous non-servis) : `/map/parcels.geojson` fallback →
   soit défaut `source=Q_A_RUN_LABEL`, soit suppression du fallback (il ne sert que les tests) ;
   `division_or` → re-sourcer sur tier si le signal est vivant ; nettoyer `_build_fiche`
   (retirer la lecture `ev.status` résiduelle) ; tests → `verdict_servi`.
4. **Archiver la colonne par renommage** : `parcel_evaluations.status` →
   `status_pre_m37` (réversible ; rollback = renommage inverse). **Pas de suppression physique**
   (geste ultérieur Vic, à froid).
5. **matrice_statut** : appliquer TES arbitrages du §4, rien d'autre.

---
**STOP — questions d'arbitrage :**
1. **Feu vert Phase 1 ?** Mon évaluation : SÛR (verdict = tier depuis M34, vigilances hors
   rail, aucun lecteur servi bloquant). Le diff vs M34-P0 (§3) est réel mais aucun élément
   n'est une divergence servie. Tu peux reporter si tu préfères — je ne préjuge pas.
2. **`/map/parcels.geojson` fallback** : défaut `source=q_v8_calibre` (le docstring le
   prétendait déjà) OU suppression du fallback (mort pour le produit) ?
3. **matrice_statut** : valides-tu les recos du §4 (SORTIE chip fiche + TierBadge ; bascule
   tiers modules/partenaire ; maintien légende/tuiles) ? La bascule des SÉLECTIONS modules
   change le comportement des outils — à confirmer explicitement.
4. **Lot 0.2 ICD** : GARDER confirmé ?
