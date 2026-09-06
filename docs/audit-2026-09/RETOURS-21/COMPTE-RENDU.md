# RETOURS-21 — COMPTE-RENDU

Branche `fix/retours-21`, partie de `origin/main` à jour (`cabaa5b7`, qui contient déjà le merge
de `fix/retours-12` = RETOURS-13→19). Un commit par lot. **Rien n'est mergé, rien n'est basculé.**

Étape 0 : l'arbre portait un fichier non suivi `frontend/retours16_shots.mjs` (script de captures
RETOURS-16, sans valeur) — supprimé sur consigne. `git fetch` puis branche depuis `origin/main`.

---

## Lot A — les 484 zones d'aléa servies au mauvais niveau

### Ce qu'on a trouvé avant de coder

Le mapping de classes est **déjà corrigé dans le code** (RETOURS-13 R6, présent sur main) :
`src/labuse/ingestion/layers_ingest.py::_ALEA_NIVEAU` mappe déjà `ELEVE`/`TRES_ELEVE → ("fort", …)`.
Le commentaire R6 (l. 357-361) le disait : « la correction ELEVE/TRES_ELEVE→fort ne s'applique
qu'à la prochaine ré-ingestion + run ». Autrement dit : **la donnée servie était périmée**, pas le
code. Mesuré en base (`spatial_layers`, kind `georisque_alea`, subtype `mouvement_terrain`) :

| degré      | niveau servi (avant) | classe (déjà bonne) | zones |
|------------|----------------------|---------------------|-------|
| ELEVE      | **moyen**            | eleve               | 360   |
| TRES_ELEVE | **moyen**            | tres_eleve          | 124   |
| MOYEN      | moyen                | moyen               | 299   |
| FAIBLE     | faible               | faible              | 96    |
| FAIBLE_A_MODERE | faible          | faible              | 31    |
| MOYEN_B2U / MODERE / MOYEN_SECURISABLE | moyen | moyen        | 7     |

La `classe` d'AFFICHAGE était déjà juste (fix R6) et l'endpoint la lit directement
(`api/app.py`, `"classe": r["classe"]`, aucune retraduction) — rien à changer côté affichage.
Seul le `niveau` de CASCADE (celui qui pilote le score) restait à « moyen » sur les **484** zones
les plus graves, d'où la quarantaine CIRCUIT-3.

### Impact mesuré (avant recalcul)

La couche de scoring `cascade/layers/phase1.py::RisquesLayer` émet, pour chaque zone d'aléa
intersectée (aucun seuil de couverture sur les aléas — `if coverage <= 0: continue`), un
`soft_flag` de sévérité tirée du `niveau`. Un flag **fort** vs **moyen** :
- coûte **−5 pts d'opportunité de plus** (moyen = −10, fort = −15, `opportunity_weights.yaml`) ;
- pose `has_fort_flag=True`, ce qui **bloque le statut « opportunité »** (forçage « à creuser »),
  et abaisse le rang → peut faire tomber une parcelle « chaude »/« brûlante ».

Rayon d'impact (croisement spatial `parcels ↔ 484 zones graves`, EPSG:2975) :

- **73 179 parcelles** intersectent au moins une zone ELEVE/TRES_ELEVE → gagnent un flag fort au
  lieu de moyen.
- **Delta de score d'opportunité** (déterministe = −5 pts × nombre de zones graves intersectées) :
  médiane **−5 pts** (1 zone), moyenne 1,19 zone, **max −145 pts** (une parcelle sur 29 zones).
- **Changement de palier** — seules les parcelles aujourd'hui dans un palier « chaud » peuvent
  descendre (une « écartée » / « à creuser » / « déclassée » est déjà au plancher). Parmi les
  73 179 : **67 chaudes + 1 brûlante** ; dont **13 chaudes sans flag fort préexistant**
  (les seules qui gagnent un `has_fort_flag` NEUF → bascule quasi certaine « chaude → à creuser »).
  Les 55 747 écartées et 10 469 à-creuser intersectantes ne changent pas de palier.

Le **nombre exact** de changements de palier se lit dans le run candidat (les tiers sont un
classement global, non calculable sans re-scorer) — voir plus bas.

### Correction à la source

`layers_ingest.py::reclassifier_alea_niveau()` (+ CLI `labuse alea-reclassifier`) : recalcule
`niveau`/`classe`/`residuel` de chaque zone `georisque_alea` **à partir de son `degre` stocké**,
avec les **mêmes fonctions de mapping** que l'ingestion (`_normalise_alea`/`_classe_alea`, source
de vérité). Résultat identique à une ré-ingestion, mais déterministe, hors réseau, idempotent, et
qui ne touche QUE les zones dont le niveau diffère du mapping (on nomme ce qui bouge). Exécuté :

```
ELEVE: moyen→fort (classe eleve→eleve) · 360 zones
TRES_ELEVE: moyen→fort (classe tres_eleve→tres_eleve) · 124 zones
✓ 484 zones réalignées.
```

Ce n'est PAS un correctif d'affichage : la donnée servie (`spatial_layers.attrs.niveau`) est
désormais juste, l'affichage la lit telle quelle. Le run servi (`q_v11_m137`) est un instantané
figé dans `parcel_p_score_v2` — il n'est PAS modifié : la correction ne se propage au score qu'à
la bascule d'un nouveau run (geste de Vic).

### Quarantaine levée

Le filtre CIRCUIT-3 rejoué sur la donnée corrigée passe au vert — le contrôle bloquant
`d_alea_non_retrograde` (« aléa fort jamais rétrogradé en moyen ») compte 0 :

```
✓ georisques_mvt [sync 2026-07-05] : ok — 0 bloquant(s) KO, 0 avertissant(s) KO (9 contrôles)
✓ garde pompe : aucune source `run` en quarantaine.
```

La quarantaine s'est levée **parce que le filtre passe**, pas par un `servir-quand-même`. Le
verdict OK est persisté dans `filtre_versions`.

### Run candidat (non servi)

Lancé `labuse flux-run --label q_v11_r21_alea` (cascade 24 communes + score-v2, sur la donnée
aléa corrigée). Débit mesuré ~33 parcelles/s → **~3,6 h** sur 431 663 parcelles ; résumable
(`--resume`), progression `/tmp/labuse-flux-run-q_v11_r21_alea.log`, écrit `dryrun_*` +
`parcel_p_score_v2` sous le label candidat. **NON servi** — la bascule reste manuelle
(`labuse golden promote q_v11_r21_alea`), après lecture de la note de version. La garde pompe
étant verte, la bascule n'est plus bloquée.
> État à la remise : run en cours (le compte-rendu sera complété du diff de tiers candidat vs
> `q_v11_m137` quand il termine ; l'impact palier attendu est petit — cf. les 13 chaudes ci-dessus).

### Golden

Le golden ne bouge PAS tant que le run candidat n'est pas servi (il se grave sur le run servi).
À la bascule seulement, `golden promote` régénère le golden sur le nouveau run ; le diff attendu
touche les parcelles chaudes qui descendent (aléa désormais fort) — évolution voulue, pas
régression. **Aucune régénération silencieuse** : le diff sera listé au moment de la bascule.

### Fichiers Lot A
- `src/labuse/ingestion/layers_ingest.py` — `reclassifier_alea_niveau()`.
- `src/labuse/cli.py` — commande `alea-reclassifier`.
- `tests/test_retours21_lotA.py` — réalignement + idempotence.
