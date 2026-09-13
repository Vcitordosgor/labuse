# REPARATIONS-1 — réparer ce que l'audit a trouvé, puis les deux sources qui manquent

Branche `fix/reparations-1` depuis `main` (`a4d770b8`, CIRCUIT-6 mergé). Worktree `~/Desktop/labuse-etat`.
Base locale `labuse:5432` (431 663 parcelles). Ports de preuve : API `:8032`, front `:5200`. Rien n'est mergé, rien n'est basculé, le run servi (`q_v11_m137`) n'a pas bougé.

État des verrous à l'ouverture : **V3a seul rouge** (tuiles fabriquées pour `q_v14`, manifeste sert `q_v11_m137`) — attendu, objet du lot 1.

---

## LOT 0 — La fuite aléa (prioritaire absolu)

### Ce que l'enquête a montré (différent du constat du mandat)

Le mandat disait : « le correctif dort sur `fix/retours-12`, jamais mergée ». **La réalité sur cette base est en avance sur le mandat** :

1. **Le correctif code + donnée est déjà sur `main` ET déjà exécuté ici** : commit `b5009d4f` (« RETOURS-21 A — aléa mouvement de terrain servi au bon niveau », 06/09) — `reclassifier_alea_niveau()` + CLI `alea-reclassifier` + `tests/test_retours21_lotA.py`. Il a réaligné les 484 zones le 06/09.
2. **La quarantaine `georisques_mvt` est déjà levée** : filtre rejoué le 06/09, tous contrôles `ok` (dont `d_alea_non_retrograde` bloquant = 0), `dernier_verdict` = ok.
3. **La garde pompe est déjà vide** : `filtres.garde_pompe()` → `[]` (aucune source `run` en quarantaine).

**Ce qui restait réellement ouvert** : l'écart sonde `circuit_ecarts` id=2 (`alea_inondation_couche` / `distribution`), ouvert le 06/09 à 01:20 — **avant** l'exécution du correctif le même jour à 12:48 — et **jamais soldé depuis**, alors que la sonde est repassée (13/09 18:00 : la mesure était saine). Cause : `sonde_circuit.verifier_categorielle()` **ouvre** des écarts mais n'a pas de passe de solde — contrairement à `verifier_robinets()` qui a sa passe 4.4. Un écart guéri restait donc « ouvert » à vie : ligne rouge fantôme sur la page Circuit, fuite comptée par G7, et le mot « fuite aléa ouverte » dans toutes les dettes. Le test existant (`test_distribution_aleas_attrape_retours13`) avouait la faille : son assertion de solde se terminait par `or True` (toujours vraie) avec le commentaire « la ligne reste (historique) ».

### Le correctif (celui de cette session)

- `src/labuse/sonde_circuit.py` — `verifier_categorielle()` tient désormais un jeu `verifies` (chiffre_id, clé, robinet_a, robinet_b) des couples **mesurés** à ce passage (4.1 zonage par témoin, 4.2 aléas, 4.3 permis approximatifs, 4.7 paliers), et **solde** (miroir exact de la passe 4.4 des robinets) tout écart ouvert re-mesuré sain : `statut='solde'`, `solde_le=now()`. Le compteur `soldes` entre dans le retour.
- `tests/test_circuit2_lot4.py` — l'assertion `or True` remplacée par de vraies assertions : après correction de la donnée, `res2["soldes"] >= 1`, **0** écart `ouvert` restant sur `alea_inondation_couche/distribution`, la ligne porte `statut='solde'` et un `solde_le`. C'est le test qui aurait attrapé la ligne rouge fantôme.

### Preuves sur les 484 zones — avant / après, effectifs par degré

Avant (état documenté par RETOURS-21 A, ingestion pré-correctif R6) : 360 ELEVE + 124 TRES_ELEVE servis `niveau='moyen'` = **484 zones**.

Après, mesuré sur cette base le 13/09 (`spatial_layers`, kind `georisque_alea`, 993 zones) :

| degré (DEAL brut) | niveau servi | classe | zones |
|---|---|---|---|
| ELEVE | **fort** | eleve | 360 |
| TRES_ELEVE | **fort** | tres_eleve | 124 |
| FORT / RESIDUEL_FORT / RESIDUEL_FORT_AGGRAVE | fort | fort | 29 |
| MOYEN / MODERE / MOYEN_B2U / MOYEN_SECURISABLE / RESIDUEL_MOYEN | moyen | moyen | 334 |
| FAIBLE / FAIBLE_A_MODERE / RESIDUEL_FAIBLE | faible | faible | 146 |

Idempotence prouvée : `reclassifier_alea_niveau()` rejoué → **0 zones réalignées, 0 degrés** (la donnée est alignée sur le mapping, source de vérité).

### La ligne rouge passe au vert, la pompe accepte — au navigateur, sans lancer de calcul

- Sonde rejouée (passage complet, 25 mesures, déclencheur `reparations-1-lot0`) : écart id=2 → `statut='solde'`, `solde_le=2026-09-13 19:04`. `circuit_controles` : `fuites_ouvertes=0` (les 4 passages précédents disaient 1).
- G7 : « dernier passage sonde 13/09 19:04 ; **0 fuite(s) ouverte(s)** ».
- **Au navigateur** (`:8032`/`:5200`, chromium) : page Circuit → bouton « Vérifier que tout coule » cliqué (un contrôle, jamais un calcul) → bandeau « **Contrôle terminé : 0 fuite(s), 0 eau ancienne, 0 écart(s) ouverts.** » (`captures/lot0-04-verifier-bandeau.png`). Détail de la pompe : bouton « **Faire tourner la pompe** » actif (vert), aucune quarantaine, « Basculer sur q_v14 » présent mais non touché (`captures/lot0-03-pompe.png`).

### Verrous après lot 0

23 joués : **22 verts**, 1 cassé = **V3a seul** (identique à l'ouverture — objet du lot 1). G7 est passé de « 1 fuite ouverte » à « 0 ».

### Noté au passage (traité au lot 1)

La LED du rail admin affiche « Run servi q_v14 » : elle lit `mvt_meta.run_label` (le run des **tuiles**) en l'étiquetant « Run servi » — c'est la même confusion candidat/servi que V3a mesure.

---

## LOT 1 — V3a ne bloque plus un candidat assumé

### Le geste

Nouveau module `src/labuse/circuit_candidat.py` + table `circuit_candidat_assume` (déclarée à la carte des tables, rôle écrit) :

- **`declarer(run_label, par, motif)`** — le marquage explicite. Motif **obligatoire** (on écrit pourquoi). **Journalisé** : geste `candidat` au `circuit_journal` (catégorie « bascule » dans la barre du journal). Idempotent (re-déclarer met à jour le motif).
- **`retirer(run_label, par)`** — le geste inverse. **Réversible et sans perte** : rien n'est supprimé, la ligne est tamponnée `retire_le`/`retire_par`, l'historique reste, on peut re-déclarer.
- CLI : `labuse circuit candidat [--assumer X --motif "…" | --retirer X] [--par …]` ; sans option, il montre l'état + l'historique.

### V3a fait la part des choses

`verrou_versions_generations` : quand les tuiles servent un autre run que le manifeste,

- **candidat déclaré et assumé** (la déclaration active porte exactement ce run) → verrou **VERT**, et la preuve **nomme** le candidat : « … ; tuiles du candidat DÉCLARÉ q_v14 (assumé par mandat REPARATIONS-1 le 2026-09-13), manifeste sert q_v11_m137 » ;
- **génération non déclarée** (le vrai danger) → **rouge**, comme avant, avec le chemin du geste dans le détail (« candidat NON déclaré (labuse circuit candidat --assumer) »). Assumer `q_v14` ne blanchit pas des tuiles `q_v15` : la déclaration est par run (testé).

### deploy.sh accepte ce cas précis — sans chemin de contournement

La porte de `deploy.sh` est inchangée : le code retour de `labuse circuit verrous` (la même commande, le même verdict). Avec la déclaration posée, la porte rend **0** (prouvé : `circuit verrous --par deploy` → « tout va bien », exit 0). Aucun bypass n'a été ajouté à `deploy.sh` : une génération non déclarée continue de refuser le déploiement.

### Exécuté sur la base

`q_v14` déclaré assumé le 13/09 (motif : « Vic refond l'algorithme — le prochain run sera q_v15 ; q_v14 reste en base comme point de comparaison, jamais basculé »). **Le candidat n'est ni purgé ni basculé** — il est en base, nommé, comparable au futur `q_v15`.

### La LED admin cesse de mentir

Le rail admin affichait « Run servi q_v14 » : `admin_pilotage` lisait `mvt_meta.run_label` (le run des **tuiles**) sous l'étiquette « Run servi ». La LED lit désormais `runs.current()` (le manifeste, la vérité de la bascule) — capture : « Run servi q_v11_m137 », « Verrous 16/16 », candidat q_v14 nommé sur le Circuit (`captures/lot1-01-led-et-candidat.png`).

### Tests et verrous

`tests/test_reparations1_lot1.py` (4 tests : non-déclaré rouge, déclaré vert et nommé, déclaration par run, journalisé + réversible) ; `tests/verrous` 99 passed. **Verrous après lot 1 : 23/23 « tout va bien » — V3a compris.**
