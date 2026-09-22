# SCORING-6 — Diagnostic run 4 (`--assiette-clippee`) ≡ run 3

Lecture seule + appel direct (aucun run île, rien de servi). Branche `feat/scoring-6`, HEAD `88a498e0`.

## (1) 97402000AB1117 dans le run 4

| run_seq | code_commit | SDP résiduelle | cause |
|---|---|---|---|
| 3 | `69bd6906` (main) | **0** | `zone_non_constructible:N` |
| 4 | `88a498e0` (lot A) | **0** | `zone_non_constructible:N` |

Zone dominante **N à 95,6 %**, portion **Uc à 4,4 %** (commune Bras-Panon, pid 63195).

## (2) Pourquoi l'option n'a pas bougé le résultat

Deux couches, l'une opératoire, l'autre de code — les deux mènent à SDP 0.

**A. Le run 4 a tourné SANS clip effectif (constat, pas hypothèse).**
`run 3 ≡ run 4` **octet pour octet** : 0 ligne différente sur 431 663 (SDP + cause). run 3
était le tout-ou-rien (code main, sans lot A). run 4 lui est identique → le clip a été **inerte**.
Preuve fine : run 4 stocke AB1117 en `cause=zone_non_constructible:N` ; si le clip avait pris,
la sous-zone Uc aurait résolu (AB1117 n'a aucun bâti) → `disponible=True, cause=NULL, SDP 81`.
Le `code_commit` stocké (`88a498e0`) vient d'un `git rev-parse HEAD` dans le worktree courant —
il **certifie le CWD, pas le module importé**. Le piège connu `.venv/bin/labuse` = mauvais code
(ou l'oubli du drapeau : le libellé `--assiette-clippee` est saisi à la main dans `--new-run`)
explique un run étiqueté « clippé » mais exécuté tout-ou-rien.

**B. Un vrai bug de code : incohérence d'assiette entre `parcel_faisabilite` et `compute_residuel`.**
Même quand le clip PREND, le résiduel reste 0 pour toute parcelle A/N **bâtie** :

- `parcel_faisabilite(assiette_clippee=True)` clippe la capacité **max** sur la seule portion U/AU
  (`surface_assiette = surface × pct_U/AU`, `emprise` clippée à l'union U/AU) → `sdp_max` petit et juste ;
- `compute_residuel` retranche le **bâti EXISTANT du contour ENTIER** (`bati_ratio × surface`, BD TOPO
  sur toute la parcelle, portion A/N comprise) : `sdp_residuelle = max(0, sdp_max − sdp_existante)`.

On soustrait donc le bâti debout sur la portion **A/N inconstructible** d'un plafond calculé sur la
**seule portion U/AU**. Pour toute parcelle A/N-dominante portant du bâti (le cas général — le bâti
est sur la partie agricole/naturelle), `sdp_existante ≫ sdp_max` → **résiduel 0**, identique au
tout-ou-rien. C'est l'« ordre des tests zone dominante / assiette » : capacité mesurée sur l'assiette
U/AU, déduction mesurée sur la zone dominante. AB1117 échappait au 0 seulement parce qu'il n'a **pas**
de bâti (0 m²) — mais reste à 0 dans le run à cause de (A).

Illustration (appel direct, avant fix) :

| idu | dom | U% | sdp_max (U/AU) | bâti retranché (contour) | résiduel |
|---|---|---|---|---|---|
| 97401000AD1444 | A | 0,4 | 73 | **759** (portion A) | 0 |
| 97401000AD0500 | A | 13,4 | 356 | **533** | 0 |
| 97401000AD1343 | A | 4,5 | 161 | **2462** | 0 |

## (3) Correctif + preuve

`src/labuse/faisabilite/residuel.py` — sous `assiette_clippee` **et** parcelle à cheval
(`0 < pct_U/AU < 100`), le bâti retranché est mesuré sur la **même portion U/AU** que la capacité
(`_emprise_batie_assiette` : `Σ ST_Area(ST_Intersection(bâtiment, contour ∩ union U/AU))`, seuils U/AU
lus de `cascade_rules.yaml` comme la cascade). Hors clip (servi) ou mono-zone : **strictement
inchangé** (bâti du contour entier + révélé CoSIA). Opt-in — le servi ne bouge pas.

**Preuve appel direct** (20 parcelles A/N à cheval Les Avirons + AB1117) : `clip=F` → tout 0/NC ;
`clip=T` après fix → **11/21 SDP > 0** (AB1117 81, AD0660 616, AD0763 468, AD0875 213, AD1271 178,
AD1494 165, AD0514 120, AD1617 97, AD1379 94, AD1444 56…). Les 0/NC restants sont **légitimes** :
portion U/AU déjà bâtie (AD0500 : 466 m² de bâti *sur* la portion U/AU > 356 m² de plafond) ou
sous-zone trop exiguë (`terrain_exigu` / `redhibitoire`). Le bâti mesuré est bien celui de la portion
U/AU (466), pas du contour (533) → clip correct, pas un bug résiduel.

**Régression** : servi (`clip=False`) identique sur parcelles U normales. `pytest` résiduel + scoring-6
+ faisa/zone/potentiel : **256 passed, 2 skipped** (skips pré-existants, environnementaux).

## Quand relancer

Le code est prêt mais **rien n'est relancé/servi**. Pour un run 5 réellement clippé :

```
source /tmp/lab6.sh
PYTHONPATH=src /Users/openclaw/Desktop/labuse/.venv/bin/python -c "from labuse.cli import app; app()" \
    compute-residuel --ile --assiette-clippee --new-run "q_v15 assiette clippée (fix bâti)"
```

⚠ Ne PAS lancer via `.venv/bin/labuse` (piège : code d'un autre worktree → clip inerte, run 4 rejoué).
Après le run : vérifier AB1117 (`SDP 81`, cause NULL) et le compte A/N `SDP>0`, avant toute bascule
`residuel-serve`. Ne pas merger.
