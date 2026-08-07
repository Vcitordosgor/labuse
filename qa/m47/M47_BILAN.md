# M47 — BILAN · Renouvellement câblé au geste (portée réduite (d), arbitrage Vic)

**Branche** `m47-rebuild-renouvellement`. **0 tier, 0 changement de classement, pas de merge.**
Arbitrages Vic sur P0 : (a) **pas de rebuild** (table déjà q_v8, reproductible bit-à-bit) ·
(b) **définition gardée** (documentée ici) · (c) **aucune action sœur** · (d) **GO** sur le
durcissement P1. Golden/re-mesures/SHA256 M37 : intacts (preuve §5).

---

## 0. La leçon P0 (à consigner, 4ᵉ fois cette semaine)

La prémisse du backlog — « `parcel_renouvellement` morte sur q_v7 depuis la bascule v8 » —
était **fausse**. Constaté sur pièces : table déjà rejouée sur `q_v8_calibre` le 2026-08-05,
67 258 lignes, **rebuild à blanc reproductible bit-à-bit** (0 entrée / 0 sortie). Le run `q_v7`
n'existe même pas. **Le rebuild à blanc AVANT toute écriture est ce qui a évité un geste servi
inutile.** Une note de backlog est une affirmation d'agent, pas une source — vérifiée, elle
tombe. (cf. pc_caducs/M31, `doctrine-note-config-pas-source`.)

## 1. Définition du segment (arbitrage (b) : gardée, documentée)

`src/labuse/renouvellement.py`. Une parcelle entre **ssi les 5 conditions** :
1. **Exclue étage 0 par BatiLayer** (`dryrun_cascade_results`, `layer_name='bati'`,
   `result='HARD_EXCLUDE'`), motif franc ∈ {`deja_bati_probable`, `deja_bati`, `ensemble_bati`}.
2. **Zone PLU ∈ {U, AU}** (`p_model_ext_dataset`, `annee = max(annee)`).
3. **Capacité** : `sdp_residuelle_m2 > 100` **OU** `surface_m2 ≥ 600`.
4. **NON copro** (`p_model_ext_copro` rnic|dvf).
5. **NON foncier public** (cascade `foncier_public` HARD_EXCLUDE).

**Score /100 déterministe** (percent_rank intra-segment, `config/renouvellement.yaml`, Σ=100) :
potentiel résiduel 40 · assiette 25 · marché 20 · divisibilité 0|15. **Aucun modèle appris.**
Intrants **run-scopés** = cascade bati + foncier_public **uniquement** ; le reste lit le dataset
partagé → segment **quasi run-indépendant** (rebuild sur q_v7_defisc *aujourd'hui* = 67 258 aussi,
diff run-à-run **live = 0** ; le « 68 445 / Δ−1 187 » historique = drift dataset dans le temps).

## 2. Ce qui a changé (P1, portée (d))

| # | Changement | Fichier | Modèle |
|---|---|---|---|
| 1 | **Câblage au geste** `build-mvt` : `renouvellement.build()` après `parcel_flags` | `cli.py` (build_mvt_cmd) | `parcel_flags` (M45) |
| 2 | **Garde de cohérence** `check_coherence_renouvellement` (OK/PÉRIMÉE/MÉLANGÉE/ABSENTE), bruyante NON bloquante, appelée dans le geste | `bascule_gardes.py` | `check_fraicheur`/`check_coherence_idurba` (M40) |
| 3 | **Scope des 3 lectures** (fiche, `/map/renouvellement.geojson`, `/renouvellement/liste`) sur `run_label = Q_A_RUN_LABEL` (lu de `config/served_run.txt`, jamais un label en dur) | `api/app.py` | filtre `/parcels` (déjà scopé) |
| 4 | **Test** de la garde (4 statuts + non-blocage) | `tests/test_coherence_renouvellement.py` | `test_coherence_idurba` |

**Effet doctrinal** : `parcel_renouvellement` était la **seule** table run-scopée montée par une
commande **isolée** → la seule qui pouvait remourir en silence. Elle **ride désormais le geste**
et **une garde crie** si son run diverge du servi.

## 3. Temps ajouté au geste de bascule (P1.4)

**+43,2 s** (`renouv.build(commit=False)`, 67 258 parcelles, run q_v8_calibre ; table servie
recomptée **intacte** à 67 258 après rollback). Ordre de grandeur cohérent avec `parcel_flags`
(15,1 s) : le geste `build-mvt` s'alourdit d'une minute au total, coût assumé d'une table qui ne
remeurt plus.

> Note : **je n'ai PAS relancé `build-mvt` en réel** — la table servie est déjà correcte sur
> q_v8 (reproductible bit-à-bit), un geste servi ici ne gagnerait rien et serait un risque gratuit
> (arbitrage (a)). Le câblage s'exécutera au **prochain vrai geste de bascule**.

## 4. Balayage des autres commandes CLI isolées (exigence Vic — inventaire seul)

Test appliqué : builder **run-dépendant** (lit le run servi) **+ table servie + hors geste gardé**.
Détail machine : `cli_builders_sweep.csv.gz`.

| Commande | Table | Run-dépendant | Stampée run | Dans un geste ? | Classe |
|---|---|---|---|---|---|
| `renouv` | parcel_renouvellement | oui | oui | **OUI (M47)** | **RÉSOLU** |
| **`score-e`** | score_e | **oui** (`run=Q_A_RUN_LABEL`) | **non** | **non (isolée)** | ⚠️ **MÊME CLASSE** |
| **`division-or`** | division_or_candidates | **oui** (`:served` étage 0) | **non** | **non (à la demande)** | ⚠️ **MÊME CLASSE** |
| `pc-caducs`, `defisc-fenetres`, `surface-d`, `prix-neuf`, `rnu-pau`, `viabilisation` | (leurs tables) | **non** | non | non | HORS CLASSE (run-agnostiques) |

**2 sœurs de même risque** : `score_e` (bilan CA, 16 surfaces API) et `division_or_candidates`
(filtre O12 + fiche) **lisent le run servi mais tournent isolées** ET **sans stamp run_label** —
donc elles ne peuvent même pas s'auto-détecter périmées comme le fait désormais renouvellement.
`division_or` est bâtie par commune à la demande (workflow revue, moins exposé au risque de
bascule). **Inventaire seul, aucune correction** (consigne Vic). Candidat mandat futur : stamper +
câbler ces deux-là.

## 5. Vérification

| Gate | Résultat |
|---|---|
| **Golden 117/117** | **préservé par construction** — table mono-run → scoped == unscoped (Δ=0 sur `total_segment`/`total_commune`/liste/carte) → fiche/carte/liste **byte-identiques**. Aucune écriture scoring/tier. |
| Re-mesures M34/M35 · SHA256 vigilances M37 | intacts (aucune touche scoring/vigilances/parcel_flags) |
| **0 tier modifié** | oui — segment ≠ tier ; aucune écriture hors le geste renouvellement (rollback en test) |
| Garde live | statut **OK**, servi `q_v8_calibre`, 67 258 parcelles |
| Tests | **22/22** (guard 5 · renouvellement 7 · idurba 7 · gardes 3) |

## 6. Exposition (P2) — état constaté

- **Filtre M45 « Renouvellement »** (tiroir « Ça va muter ? ») : **déjà LIVE** (chip
  `FiltreLabuse.tsx`, run-scopé côté `/parcels`). Rien à activer.
- Surfaces (fiche, carte `/map/renouvellement.geojson`, outil MR1, liste) : **lisent la table
  rebâtie**, désormais **scopées sur le run servi**.
- **Étiquette millésime/source (P2.3)** : **ABSENTE aujourd'hui** — le segment est servi sans
  libellé de run. Petit reste d'exposition ; **hors portée (d)** → laissé à l'arbitrage Vic (ajout
  cheap : le `run_label` est déjà dans la table).

## Annexes (digests machine, .csv.gz — convention QA)
- `M47_P0_CONSTAT.md` · `sister_tables_inventaire.csv.gz` · `rebuild_blanc_funnel_diff.csv.gz` (P0)
- `cli_builders_sweep.csv.gz` — balayage des builders CLI isolés (§4)
- `p1_verif_digest.csv.gz` — vérifs P1 (§2/§3/§5)

**Captures P2** (fiche segment · filtre actif+compteur · calque carte) : à produire sur l'UI
lancée — parcelle de tête du segment `97404000AZ0004` (score 85, rang 1). Non incluses ici
(pas de serveur lancé dans ce geste read-only).
