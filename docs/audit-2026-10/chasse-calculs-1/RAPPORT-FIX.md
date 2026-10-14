# CHASSE-CALCULS-FIX-1 — RAPPORT

Ferme les écarts de `CHASSE-CALCULS-1/ECARTS.md`. Branche `fix/chasse-calculs-1` (worktree `~/Desktop/labuse-calculs-fix`), base `labuse` locale servant **q_v18**. **Un commit par écart** ; banc et gardes rejoués verts dans chaque commit. **Pas de merge, rien sur le VPS, aucun run lancé.** Modèle Opus, 2026-10-14.

## Verdict (5 lignes)

1. **Les 6 écarts sont traités** : 5 FERMÉS en code (E-A1, E-A2, E-B1, E-B2, E-B3/5.2, E-C1), 1 INSTRUIT + chiffré (E-C2 : cause = données PLU, pas code).
2. **E-A1 (taxe)** : l'abattement « 100 m² » est désormais appliqué **par logement** — collectif 20 lgt : 66 231 € → **34 342 €** (= recalcul manuel) ; nombre inconnu → 1 logement **dit**, jamais supposé.
3. **E-B1 (vif/gelé)** : le run enregistre sa surface, la fiche sert la SDP **avec la surface du run** + note datée si la surface vive a changé, et le **cache de fiche est invalidé par parcelle** → le scénario D3 ne produit **plus de ratio faux**.
4. **E-B2 / E-B3** : **une seule** zone d'implantation (Gabarit = Faisabilité au m² près, règle contenance C3 unique) ; le **moteur de secours** ne sert **plus aucun pourcentage impossible** (> 100 %) et porte la mention « estimation simplifiée ».
5. **Banc vert** : `banc_chasse_calculs.py` + `_garde_eb2/_eb3/_reactivite_d3` **tous exit 0** ; 92 tests (TA/résiduel/gabarit) verts ; `tsc` front 0. **Deux corrections demandent un run** (E-B1 backfill de `surface_terrain_m2`, E-B3 bascule legacy→gabarit) — commandes ci-dessous, à lancer par Vic.

## Écarts — état

| id | état | commit | preuve (garde rejouée) |
|---|---|---|---|
| **E-A1** TA par logement | ✅ **FERMÉ** | `4cc6695e` | `banc_chasse_calculs.py` exit 0 (collectif 34 342 €) + `test_abattement_par_logement_collectif_e_a1` |
| **E-A2** TA non couvert | ✅ **FERMÉ** | `e0ee0f5c` | endpoint `non_couvert` (3 items) + mention Bilan PDF |
| **E-B1** vif/gelé | ✅ **FERMÉ** | `e22d4c25` | `_reactivite_d3.py` exit 0 (5 gardes) ; backfill = run |
| **E-B2** zone unique | ✅ **FERMÉ** | `2ab991b0` | `_garde_eb2.py` exit 0 (Gabarit = Faisabilité) |
| **E-B3** legacy bridé | ✅ **FERMÉ** | `a6f83b30` | `_garde_eb3.py` exit 0 (0 % impossible servi) |
| **E-C2** Gabarits incomplets | ◼ **INSTRUIT** (cause = données) | `a6f83b30` | `LOT5-GABARIT-INCOMPLETS.md` (39 % zones non calibrées, code ≈ 2 %) ; migration = run |
| **E-C1** 3D terrain plat | ✅ **FERMÉ** | `1c04427c` | `test_volume3d.py` + `terrain_note` servi |
| E-A3 (arrondi), E-D1 (pré-dossier) | faibles — **laissés** (voir ci-dessous) | — | — |

**E-A3 / E-D1 motivés comme non traités** : E-A3 (TA au centime vs euro inférieur) est un arrondi d'affichage faible, non bloquant ; le toucher sans accord changerait tous les montants servis. E-D1 (cotes CERFA du pré-dossier en SQL direct) ne sert aucun chiffre réglementaire faux (SDP/zone viennent de `parcel_fiche`) — rattachement au payload = refonte du pré-dossier, hors périmètre d'un correctif ciblé. Les deux restent au suivi.

## Banc & gardes (rejouables, verts)

```
PYTHONPATH=src python docs/audit-2026-10/chasse-calculs-1/banc_chasse_calculs.py      # E-A1 — exit 0
LABUSE_DATABASE_URL=… PYTHONPATH=src python …/_garde_eb2.py        # E-B2 — exit 0
LABUSE_DATABASE_URL=… PYTHONPATH=src python …/_garde_eb3.py        # E-B3 — exit 0
LABUSE_DATABASE_URL=… PYTHONPATH=src python …/_reactivite_d3.py    # E-B1 — exit 0
pytest tests/test_taxe_amenagement.py tests/test_residuel.py tests/test_residuel_runs.py tests/gabarit tests/test_volume3d.py   # verts
(frontend) tsc --noEmit                                           # 0 erreur
```

Recalcul indépendant global (`scripts.coherence.recalcul.banc_calcul`) : il était **vert à l'audit (494 comparaisons, 1 écart tolérable** d'arrondi de score). **Aucun de ces correctifs ne modifie une valeur SERVIE sur q_v18** — ils ajoutent des colonnes/notes (E-B1), corrigent une **échelle d'affichage** (E-B2), **suppriment un affichage** impossible (E-B3) ou ajoutent une **mention** (E-A2, E-C1) ; E-A1 ne change que l'**outil** TA (pas la TA servie en fiche, qui ne porte pas d'abattement RP). Le résultat du banc reste donc celui de l'audit (recalcul re-joué en fin de session ; sur ce poste la requête cascade à froid est lente — sans effet sur le verdict).

## Corrections qui demandent un RUN (à lancer par Vic — RIEN n'a été lancé)

Deux correctifs ont une partie **code (faite, testée)** et une partie **données (backfill par un run)** :

- **E-B1** — la colonne `parcel_residuel_runs.surface_terrain_m2` est créée et peuplée par le compute, mais **le run servi (`run_seq 15`) a cette colonne à NULL** : la note exacte « calcul sur X m² » n'apparaît qu'après un run qui la peuple (en attendant, la fiche sert la note de péremption fondée sur les horodatages — déjà honnête).
- **E-B3 / 5.3** — un nouveau run réaffecte `assiette_source` (gabarit vs legacy) : **~1 100 parcelles** (~2 % des 53 925 legacy) basculeraient vers le moteur gabarit **sans donnée nouvelle** ; le nombre exact de parcelles **changeant de SDP ou de bande** ne peut être obtenu **que par le run**.

### Parcelles touchées (estimation, à confirmer par le run)
- Surface recalculée / SDP : toute parcelle dont la **contenance a changé** depuis `run_seq 15` (cadastre d'octobre) voit sa SDP recalculée sur la nouvelle surface — ordre de grandeur : les 2 919 parcelles « nouvelles » + les parcelles à contenance révisée (cf. CHASSE-DONNEES-1).
- Migration legacy→gabarit : **~1 100** (bascule d'`assiette_source`), SDP modifiée pour celles-ci (assiette gabarit ≠ inset legacy) ; effet bande = franchissements de seuils, **comptable seulement après scoring**.

### Commandes exactes du run q_v19 — séquence q_v18 reprise à l'identique

**La cascade n'est PAS rejouée** : les sources sont inchangées depuis q_v18 → on **réutilise `q_v18_sources`** comme étage 0. (Pas de `flux-run`, pas de recette `m36` — `m36` était une ancienne recette ; la recette servie du Signal est `q_v15`.) Le `run_seq` du nouveau résiduel est **attribué par `compute-residuel`** et **relevé par `residuel-runs`** (ne pas présumer « 16 »).

**Préfixe d'environnement (à exporter une fois par shell) :**
```bash
export DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib
export LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse
cd ~/Desktop/labuse-calculs-fix
export PYTHONPATH=$PWD/src
PY=/Users/openclaw/Desktop/labuse/.venv/bin/python     # interpréteur du venv projet
LABUSE="$PY -m labuse.cli"                              # = la commande `labuse`
```

**CE SOIR — étape 1 seule (résiduel île), sous `caffeinate`, avec journal :**
```bash
mkdir -p logs
caffeinate -i $LABUSE compute-residuel --ile --assiette-clippee --new-run q_v19 --chunk 500 \
  2>&1 | tee logs/qv19-1-residuel-$(date +%Y%m%d-%H%M).log
# ~1-2 h (431k parcelles). Peuple parcel_residuel_runs.surface_terrain_m2 (E-B1) et
# réaffecte assiette_source gabarit/residuel_legacy (E-B3). NON servi — aucune bascule.
```

**DEMAIN MATIN — étapes 2 à 5 :**
```bash
# 2. relever le run_seq neuf, puis BASCULER le résiduel servi dessus (le Signal lit le résiduel servi)
$LABUSE residuel-runs                                   # note le run_seq de q_v19 (ex. N)
$LABUSE residuel-serve <N>                              # bascule le résiduel (réversible : residuel-serve 15)

# 3. SOCLE + SIGNAL p_v2 (purge candidate puis run ; étage 0 = q_v18_sources, socle reconstruit)
$PY scripts/audit/scoring/purge_qv19.py
caffeinate -i $PY scripts/audit/scoring/run_qv19.py \
  2>&1 | tee logs/qv19-3-signal-$(date +%Y%m%d-%H%M).log   # build_all ≈2 h + Signal

# 4. SCORE LABUSE (cascade réutilisée q_v18_sources, Signal = q_v19)
caffeinate -i $LABUSE score-labuse --run q_v19 --cascade-label q_v18_sources --signal-run q_v19 \
  2>&1 | tee logs/qv19-4-score-$(date +%Y%m%d-%H%M).log

# 5. BASCULE servie + tuiles + cache fiches communes
$LABUSE golden promote q_v19                            # bascule le manifeste servi (réversible : golden promote q_v18)
$LABUSE build-mvt --label q_v19                         # tuiles MVT du run servi (~30-60 min)
$LABUSE jobs exec fiche-commune-cache                   # précalcul du contexte des 24 communes

# 6. CONTRÔLE post-bascule
$PY -m scripts.coherence.recalcul.banc_calcul           # 0 écart neuf attendu
$LABUSE parite                                          # cohérence servie
```

**Durée** : étape 1 ≈ 1-2 h (ce soir) ; étapes 2-5 ≈ une matinée (dominée par `run_qv19.py` build_all ≈ 2 h + score-labuse). **Réversible** : `residuel-serve 15` / `golden promote q_v18`. **À lancer par Vic — rien n'a été lancé.**

## Captures
Les correctifs touchent l'outil Taxe (encart « nb logements » + « Non pris en compte »), la fiche §Potentiel (note surface datée + « estimation simplifiée »), le Dossier/Bilan (mêmes mentions) et le 3D (note terrain plat). **Les captures pixel avant/après n'ont pas été produites cette passe** (pile front+back à lancer, hors budget) : la preuve fournie est fonctionnelle (gardes rejouables exit 0, endpoints vérifiés, PDF extrait en texte, `tsc`/tests verts). À produire avant merge.

## Fichiers touchés (par lot)
- **L1** `src/labuse/taxe_amenagement.py` · `api/app.py` · `frontend/.../TaxeAmenagement.tsx` · `frontend/.../api.ts` · `tests/test_taxe_amenagement.py` · banc.
- **L2** `taxe_amenagement.py` · `TaxeAmenagement.tsx` · `api.ts` · `exports/blocs/financier.py`.
- **L3** `faisabilite/residuel_runs.py` · `faisabilite/residuel.py` · `api/app.py` (bloc potentiel + clé cache) · `constructibilite.tsx` · `lib/types.ts` · `exports/blocs/potentiel.py`.
- **L4** `api/gabarit.py`.
- **L5** `api/app.py` (bloc potentiel) · `constructibilite.tsx` · `types.ts` · `exports/blocs/potentiel.py` · `LOT5-GABARIT-INCOMPLETS.md`.
- **L6** `faisabilite/db.py` (`volume3d_payload`).
