# Bascule 2026 — base commune `labuse` / prod — RUNBOOK (NON exécuté)

> OUTIL-SCAN-FIX-2 (item 6). Séquence PRÉPARÉE, **non lancée** : Vic choisit le moment (d'autres sessions
> utilisent `labuse`). Script : `scripts/bascule_2026_labuse.py` (`--dry-run` / `--go`). La base commune
> `labuse` porte encore le fichier **2025 à un seul titulaire** (`parcelle_pm_droit` absente).
> État mesuré de `labuse` (lecture seule) : `programmes`=9 (les CBO, DÉJÀ là), `sirene_etablissements`=155 505
> (DÉJÀ là), `bodacc_depots`=14 078 (à rafraîchir), `parcelle_personne_morale`=82 701 (2025).

## Séquence (ordre impératif)

```bash
export LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse"   # local commun ; prod = /etc/labuse/labuse.env

# 0. ROLLBACK SAFETY — dump des 2 tables SERVIES que le flip mute (≈ 40 Mo, quelques secondes) :
pg_dump -t parcelle_personne_morale -t pm_proprietaires_millesimes "$LABUSE_DATABASE_URL" \
  > /tmp/bascule_rollback_$(date +%F).sql

# 1-3. Données (additif → archive même règle → flip atomique). Inspecter d'abord :
.venv/bin/python scripts/bascule_2026_labuse.py --dry-run
.venv/bin/python scripts/bascule_2026_labuse.py --go

# 4. Rafraîchir les dépôts de comptes BODACC (fait daté ; corrige le retard, ex. 449090075 arrêté 2023) :
.venv/bin/labuse ingest-bodacc-depots

# 5. Recalcul V-SCORE derrière le flip (le classement lit parcelle_personne_morale) puis promotion du run :
.venv/bin/labuse p-score-v2 --label q_vXX_scan2026 --rebuild        # run neuf
#   puis promouvoir q_vXX_scan2026 comme run servi (chaîne golden-promote habituelle).
```

(programmes et sirene_etablissements sont DÉJÀ en base `labuse` → rien à recharger. Sur une base où ils
seraient vides : programmes via l'admin `/admin/programmes/collecter`+`valider` ; sirene via
`labuse ingest-sirene-etab`.)

## Ce que la bascule change pour les autres écrans

Le flip change le **titulaire principal** de ≈ **2 711 parcelles** (SIREN) et le **`groupe`** de ≈ **3 989**
(parcelles multi-titulaires uniquement, toujours vers « propriétaire plutôt que gestionnaire ») :

| Écran / moteur | Lit | Effet de la bascule |
|---|---|---|
| **Fiche parcelle** (Identité) | principal par idu | propriétaire affiché = le propriétaire (P) et non plus la 1re ligne, sur les parcelles multi-titulaires. + ligne « + N autres titulaires ». |
| **Blocs fonciers** | `parcel_blocs.siren` (bâti par `blocs-build`) | **rebâtir les blocs** (`labuse blocs-build`) après le flip : une parcelle multi-titulaire peut changer de bloc (vers le propriétaire). |
| **Successions** | principal (filtre signal) | inchangé en forme ; principal plus correct. |
| **Communes — « changements de propriétaires »** | `pm_proprietaires_millesimes` ⋈ servi | **M3** : archive 2025 par la MÊME règle → **963** vrais changements affichés, pas **2 019** (≈ 1 056 artefacts de règle supprimés). |
| **Classement / scoring V** | `score_v._load_owner_links` (siren, groupe, denom, forme) | **le V-score change** pour 2 711/3 989 parcelles → **recalcul V-score obligatoire** (étape 5), sinon le classement servi reste sur l'ancien owner. |
| **Scan patrimoine** (Possession/Construction) | nouvelles tables 2026 | millésime 2026, droits séparés, DP/annulés à part, catégorie justifiée NAF. |
| **Copilote / export** | `patrimoine()` | plus de valorisation ; comptes 2026. |

## Les 12 témoins de cohérence (hook pre-push)

Les 12 témoins contrôlent l'**accord à 1 €/1 m²** des médianes de marché (terrain/bâti) entre
fiche / outils / PDF / Docs / Copilote — **données de MARCHÉ, indépendantes du propriétaire**. Le flip est
**côté owner** (siren/groupe), pas côté €/m² ; il ne crée donc **aucun écart 1 €/1 m²** attendu.
**Néanmoins** : relancer la suite de cohérence APRÈS le flip **et** le recalcul V-score
(`bash scripts/ci/coherence_run.sh`), car un témoin dont la parcelle est multi-titulaire verra son owner
changer — il doit changer **de façon identique sur tous les écrans** (source unique `parcelle_personne_morale`)
→ 0 divergence. Si un témoin diverge, c'est un cache d'écran non invalidé, à corriger avant de servir.

## Durée (ordre de grandeur, base locale)

| Étape | Durée |
|---|---|
| 0 dump rollback (2 tables) | ~ secondes |
| 1 téléchargement 2 ZIP (149 Mo ×2) + load droits 2025+2026 | ~ 5-8 min (réseau dominant ; cache /tmp réutilisable) |
| 2 archive 2025 (même règle) | ~ secondes |
| 3 flip (swap atomique 84 k lignes, ACCESS EXCLUSIVE **bref**) | ~ secondes |
| 4 `ingest-bodacc-depots` (~12 605 SIREN, API BODACC) | ~ minutes (dépend de l'API) |
| 5 recalcul V-score île + promotion | **le poste long** — minutes à dizaines de min (run de scoring) |
| rebâtir blocs (`blocs-build`) | ~ minutes |

Coupure réelle **côté lecteurs** : seulement le SWAP (étape 3), bref (ACCESS EXCLUSIVE sur
`parcelle_personne_morale` le temps d'un `DELETE;INSERT` en transaction — les lecteurs attendent, ne voient
jamais une table vide). Le reste est additif ou sur des tables dérivées.

## Rollback

- **Flip (étape 3)** : `remplacer_servie` est transactionnel — un échec **ne touche pas** la table servie.
- **Revenir APRÈS un flip réussi** : restaurer les 2 tables depuis le dump de l'étape 0 —
  `psql "$LABUSE_DATABASE_URL" -c "TRUNCATE parcelle_personne_morale; TRUNCATE pm_proprietaires_millesimes WHERE false"` puis
  `psql "$LABUSE_DATABASE_URL" < /tmp/bascule_rollback_AAAA-MM-JJ.sql` (le dump contient les `COPY` d'origine) ;
  puis **re-servir le run V-score précédent** (la promotion est réversible : repointer le run servi sur
  l'ancien `run_label`, chaîne golden-promote / rollback q_v habituelle), et `blocs-build` pour revenir aux
  blocs d'avant. `parcelle_pm_droit` est additive : la laisser ou `DROP TABLE parcelle_pm_droit`.
- **Idempotence** : relancer `--go` refait proprement (droits = purge/réinsert par millésime ; archive =
  purge/réinsert ; flip = swap). Aucun doublon.

## ARRÊT

Rien de tout ceci n'est exécuté. Vic déclenche la fenêtre.
