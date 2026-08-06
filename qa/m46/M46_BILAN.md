# M46 — BILAN · Ménage post-vague 2 (avant Train 8)

**Branche** `m46-menage-post-vague2`, base `main` `6a6e0c17` (Merge M45+M45-B). **0 tier, 0 poids.**
Golden 117/117 · suite 1339 passed (5 échecs préexistants residuel/au_ouverture db=None, hors sujet)
· SHA256 vigilances M37 **inchangé** (`482da6f6…`). Pas de merge.

---

## Lot A — Chiffres périmés
Balayage exhaustif (docs/src/front/tests/fixtures). **Constat clé** : front + API DÉRIVENT déjà
tout du run servi (`/filtre`, `/communes` classement `_communes_data`) — 0 chiffre de tier figé
côté produit. `app.py:1237` « EN DUR » = prominence, pas une valeur figée. Docs de mandats (dated)
laissés (les corriger falsifierait l'histoire).
- Corrigé : BACKLOG « chiffres vitrine » 119/1041/29974 → **118/1038/29978/2964** (opportunités 1156),
  marqué « À DÉRIVER du run au build, jamais figer ».
- BACKLOG vague 2 mis à jour : header (M37→M45-B mergés, bascule M39 06/08), **dette #13 FERMÉE**
  (piscine règle produit [15;60], 4 déclassements), dette #14 déjà fermée.

### ⚠ Chiffres encore figés (pour Train 8)
**Un seul** : le repère vitrine dans `docs/BACKLOG.md` (118/1038/29978/2964) — explicitement marqué
« à dériver du run servi au build de la vitrine ». **Aucun autre chiffre de tier figé** dans le code
servi. Train 8 doit LIRE ces effectifs du run, pas les recopier.

## Lot B — Purge des runs archivés
Inventaire : `pre_pond, pre_regle, pre_m28, pre_m32, pre_m39` (parcel_p_score_v2 431 663 lignes chacun).
- **PURGÉ : `q_v8_calibre_pre_m32`** — 431 663 lignes + 6 méta. Preuve d'inutilité : aucun lecteur
  vivant (seul `bascule_m32.py` historique le cite ; absent de `lignee_tete.CHAINE_GESTES`). VACUUM
  ANALYZE → espace réutilisable (VACUUM FULL/retour OS différé : ne pas verrouiller la table servie).
- **⚠ REFUSÉ : `q_v8_calibre_pre_pond`** (que le mandat demandait) — la vérification d'usage ÉCHOUE.
  Il est **LU par `labuse/scoring/lignee_tete.py`** (CHAINE_GESTES, geste « pondération AU ») qui
  alimente le signal fiche SERVI `parcel_entree_tete` (dette #9). Le purger casserait l'entrée-en-tête
  à la prochaine bascule. Règle permanente « aucune suppression sans preuve de non-usage » → **rendu à Vic**.
  Idem `pre_regle` + `pre_m28` (mêmes lecteurs). `pre_m39` conservé (rollback M39).
- Script audité idempotent : `scripts/m46_purge_runs.py` (dry-run par défaut, refuse les protégés).

## Lot C — Objets morts en base
- **`parcel_evaluations.status_pre_m37` SUPPRIMÉ physiquement** (geste « à froid » M37). Preuve : rail
  éteint M37, toutes les mentions sont des commentaires « éteint », les lecteurs vivants lisent
  `dryrun_parcel_evaluations.status` (table distincte). `ensure_parcel_eval_status_archived` →
  `ensure_parcel_eval_status_dropped` (DROP IF EXISTS, idempotent).
- **7 tables `algo3_*` SUPPRIMÉES** (résidu `feat/algo3-voisinage` jamais mergée, signalé M42) :
  0 lecteur en code/tests/scripts. **2 814 Mo (2,8 Go) rendus à l'OS** — DB **32,16 → 29,34 Go**.
- Autres runs vus au passage (hors périmètre, non touchés) : `q_v7_defisc` (dette connue),
  `q_v12_m28`, `q_v13_m32_mesure`.

## Lot D — Reliquats produit
- **D.1 Export CSV** routé sur `FiltreCriteres` (déplacé au-dessus des endpoints ; `csvExportUrl`
  aligné sur `getFiltre`). Vérifié : **X-Rows = compteur** (71 sous budget≤100k+brûlante, vs 118 sans).
  Un export ne peut plus ignorer un filtre actif.
- **D.2 Contraintes dédupliquées** au rendu fiche (point de calcul unique) : « PPR zone rouge » ×2 sur
  `97421000AC0156` (Salazie) → **1 ligne** ; systémique : **77 734 parcelles / 121 430 groupes** de
  doublons corrigés. Rendu seul (SHA M37 intact).
- **D.3 Libellé « trame »** levé : il désignait 431 663 (barre) MAIS le sous-ensemble filtré ensuite.
  Remplacé par **« avant analyse »** (+ « Voie manuelle (sans analyse) »). Un mot = un périmètre.
  Vérifié : « trame » absent de l'UI.

## Espace disque (avant/après)
| Poste | Récupéré |
|---|---|
| 7 tables `algo3_*` (DROP TABLE, retour OS) | **2 814 Mo** |
| `pre_m32` (431 663 lignes, VACUUM → réutilisable) | ~555 Mo réutilisables (retour OS = VACUUM FULL différé) |
| **DB totale** | **32,16 Go → 29,34 Go** |

## Vérification
Golden **117/117** · suite **1339 passed** · **SHA256 M37 inchangé** · **0 tier/poids** · tsc rc=0.
Captures `qa/m46/screens/` : d2 Salazie (PPR unique), d3 libellé (« avant analyse »).

## À rendre à Vic
1. **`pre_pond`/`pre_regle`/`pre_m28`** : le mandat voulait purger `pre_pond` mais il est LU par
   lignee_tete (signal servi). Arbitrage : (a) adapter lignee_tete à ne plus lire ces archives, PUIS
   purger ; OU (b) conserver les archives. Non purgés par sécurité.
2. Chiffres vitrine (Lot A) : à dériver au build Train 8.

Commits `[M46-LotA]` → `[M46-LotD]`. **Pas de merge — le geste revient à Vic.**
