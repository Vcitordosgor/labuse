# PLU-VEILLE-FIX-1 — un nouveau PLU est vu, appliqué en entier, et le client prévenu

**Mandat** : corriger les trois trous GRAVES de l'audit `docs/audit-2026-11/plu-veille-1/RAPPORT.md` —
(1) la sonde aveugle au remplacement de version (1→1), (2) la mise à jour partielle des couches
(zonage sans prescriptions), (3) l'absence de signal client pendant la latence.
**Branche** `fix/plu-veille-fix-1` · worktree `~/Desktop/labuse-pluveille-fix` · ports 10070/7270.
**Prod** : lue en lecture seule (la ré-ingestion Saint-Denis est faite EN LOCAL ; la procédure prod
est documentée au §6). **Pas de merge.** Date : 10/11/2026 (heure serveur Indian/Reunion).

---

## 0. Ce qui change, en une phrase par trou

| Trou de l'audit | Avant | Après (ce fix) |
|---|---|---|
| **Détection aveugle 1→1** | la sonde lit `totalFeatures` (un COMPTE) — ne bouge pas quand une révision remplace un PLU existant | job quotidien `plu-veille-nuit` : compare l'**identifiant** (idurba) servi par le Géoportail à l'ingéré, **couche par couche** → tout remplacement vu le jour même, 1→1 compris |
| **Mise à jour partielle** | zonage ré-ingéré sans prescriptions (Saint-Denis : zones 05/08, prescriptions 23/04) | **geste unique** `labuse plu appliquer` : zonage + prescriptions + informations + drapeau « règles à recalibrer » d'un seul tenant ; « à jour » exige que **toutes** les couches portent le même document |
| **Aucun signal client** | les anciennes règles servies pendant des semaines, sans un mot | pendant le décalage : bandeau fiche + mention documents « PLU modifié le jj/mm/aaaa — règles en cours de mise à jour », et les parcelles passent **« À vérifier »** dans l'Analyse LABUSE, jusqu'à la validation des règles |
| **Exploitation non prévenue** | — | le remplacement remonte chez **John** (onglet veille) et à la **page Données** (incident), avec commune, ancien/nouveau document et liste des gestes ; **rappel sous 7 jours** ; rappel **trimestriel** des procédures en cours |

---

## 1. La détection — par identifiant, couche par couche (`src/labuse/controle_plu.py`)

Pour chacune des 24 communes, on tranche par **preuve** :

- **Document publié** : l'idurba servi par le Géoportail, lu sur `/document?partition=DU_<insee>`
  (champ `name`, ex. `97411_PLU_20260805`). Repli sur le catalogue `config/plu_millesimes.yaml`
  (confronté aux pièces en M40) si l'API est injoignable.
- **Document ingéré, par couche** : `zonage` (`spatial_layers kind='plu_gpu_zone'`), `prescriptions`
  (`plu_gpu_prescription`), `informations`/DPU (`dpu`), `règles` chiffrées (`plu.destinations`).
- **Verdict** : `a_jour` **seulement** si toutes les couches **présentes** portent la référence ET les
  règles sont calibrées dessus ET aucun drapeau « à recalibrer » n'est en cours ; sinon `desync`
  (avec la liste des couches en retard et les gestes). `rnu` pour une commune sans PLU.

Le point clé : on compare l'**identifiant**, pas le compte. Une révision qui remplace un PLU existant
(même `totalFeatures = 1` avant et après) est vue le jour même. Une couche **absente** (prescriptions
jamais publiées par une commune legacy) n'est **pas** un retard — seule une couche plus **ancienne**
que la référence l'est (pas de faux positif sur Saint-André / Saint-Leu).

L'instantané nocturne est écrit dans `plu_veille_etat` (lu par la fiche, les documents, l'exploitation).

---

## 2. État des lieux immédiat — les 24 communes

Document de référence (= Géoportail / catalogue M40) face à l'ingéré par couche, **au moment de la
détection** (avant la ré-ingestion Saint-Denis du §3). `—` = couche absente (non publiée par la commune,
ce qui est normal : le DPU n'est publié que par quelques communes ; les prescriptions manquent sur les
PLU legacy). `regles` = document gravé au calibrage *destinations* servi.

| INSEE | Commune | Référence | Zonage | Prescriptions | Informations (DPU) | Règles | Verdict |
|---|---|---|---|---|---|---|---|
| 97401 | Les Avirons | 97401_PLU_20241206 | ✓ | ✓ | — | ✓ | **à jour** |
| 97402 | Bras-Panon | 97402_PLU_**20260428** | ✓ | ⚠ 97402_PLU_**20211020** | — | ✓ | **desync** |
| 97403 | Entre-Deux | 97403_plu_20240924 | ✓ | ✓ | — | ✓ | **à jour** |
| 97404 | L'Étang-Salé | 97404_PLU_20250917 | ✓ | ✓ | — | ✓ | **à jour** |
| 97405 | Petite-Île | 97405_PLU_20230609 | ✓ | ✓ | — | ✓ | **à jour** |
| 97406 | La Plaine-des-Palmistes | 97406_PLU_20230527 | ✓ | ✓ | — | ✓ | **à jour** |
| 97407 | Le Port | 97407_PLU_20241209 | ✓ | ✓ | — | ✓ | **à jour** |
| 97408 | La Possession | 97408_PLU_20251217 | ✓ | ✓ | — | ✓ | **à jour** |
| 97409 | Saint-André | 97409_20190228 (legacy) | ✓ | — | — | ✓ | **à jour** |
| 97410 | Saint-Benoît | 97410_PLU_20200206 | ✓ | ✓ | — | ✓ | **à jour** |
| 97411 | **Saint-Denis** | 97411_PLU_**20260805** | ✓ | ⚠ 97411_PLU_**20260423** | ✓ | ✓ | **desync** → corrigé §3 |
| 97412 | Saint-Joseph | 97412_PLU_**20251210** | ✓ | ⚠ 97412_PLU_**20240320** | — | ✓ | **desync** |
| 97413 | Saint-Leu | 97413_20070226 (legacy) | ✓ | — | — | ✓ | **à jour** |
| 97414 | Saint-Louis | 97414_plu_20251218 | ✓ | ✓ | — | ✓ | **à jour** |
| 97415 | Saint-Paul | 97415_PLU_20251217 | ✓ | ✓ | ✓ | ✓ | **à jour** |
| 97416 | Saint-Pierre | 97416_PLU_20240625 | ✓ | ✓ | — | ✓ | **à jour** |
| 97417 | Saint-Philippe | — (RNU) | — | — | — | — | **rnu** |
| 97418 | Sainte-Marie | 97418_plu_20251126 | ✓ | ✓ | ✓ | ✓ | **à jour** |
| 97419 | Sainte-Rose | 97419_PLU_20190504 | ✓ | ✓ | — | ✓ | **à jour** |
| 97420 | Sainte-Suzanne | 97420_plu_20250929 | ✓ | ✓ | — | ✓ | **à jour** |
| 97421 | Salazie | 97421_PLU_20220524 | ✓ | ✓ | — | ✓ | **à jour** |
| 97422 | Le Tampon | 97422_PLU_20230811 | ✓ | ✓ | ✓ | ✓ | **à jour** |
| 97423 | Les Trois-Bassins | 97423_PLU_20220602 | ✓ | ✓ | — | ✓ | **à jour** |
| 97424 | Cilaos | 97424_plu_20240213 | ✓ | ✓ | — | ✓ | **à jour** |

**Trois décalages détectés** (la nouvelle sonde les voit, l'ancienne non) :

- **Saint-Denis (97411)** — le cas de l'audit : zonage 05/08/2026 servi, **prescriptions restées au
  23/04/2026**. Corrigé en local au §3.
- **Bras-Panon (97402)** — zonage 28/04/2026, **prescriptions au 20/10/2021** (décalage de ~4,5 ans que
  l'audit n'avait pas nommé — la sonde par compte ne pouvait pas le voir).
- **Saint-Joseph (97412)** — zonage 10/12/2025, **prescriptions au 20/03/2024**.

> La reproduire : `labuse plu etat` (catalogue, hors réseau) ou `labuse plu etat --live` (Géoportail).

---

## 3. Saint-Denis — prescriptions ré-ingérées (en local), preuve

Le geste unique a été joué **en local** (base `openclaw@labuse`) :

```
$ labuse plu appliquer --insee 97411
geste unique Saint-Denis (97411) : 259 zones, 2908 prescriptions, 41 informations
  → 97411_PLU_20260805 ; règles à recalibrer.
  overlay Analyse : 99856 ligne(s) « À vérifier ».
```

Avant : `plu_gpu_prescription` Saint-Denis = `97411_PLU_20260423` (2908, ingérées 29/06).
Après : `plu_gpu_prescription` Saint-Denis = **`97411_PLU_20260805`** (2908) — alignées sur le zonage.

La commune reste alors **`desync` sur `regles`** (drapeau « à recalibrer » posé par le geste) : le
client reste prévenu « règles en cours de mise à jour » et ses parcelles restent « À vérifier »
**jusqu'à la validation** des règles recalibrées :

```
$ labuse plu valider --insee 97411
✓ recalibrage validé pour 97411 — 60248 ligne(s) restaurée(s).
```

Après validation, Saint-Denis repasse **`à jour`**, le bandeau disparaît, et chaque parcelle retrouve
**exactement** son statut d'avant (vérifié : ESTIMATED/COMPUTE_PENDING/NO_MARGIN restaurés, les statuts
durs OUTSIDE_OBJECTIVE/DEFERRED jamais touchés).

---

## 4. Le geste unique — zonage + prescriptions + informations + drapeau, ensemble

`controle_plu.appliquer_plu(db, insee)` (CLI `labuse plu appliquer --insee <code>`) fait, dans **une
transaction** : purge + ré-ingestion du **zonage**, puis des **prescriptions**, puis des
**informations** (DPU de la commune), puis pose le drapeau **« règles à recalibrer »** (`plu_recalibrage`).

Il n'existe **aucun chemin** qui mette à jour une couche sans les autres — le statut « à jour » d'une
commune **exige** que toutes portent le même document, et le drapeau garde le client prévenu jusqu'à
la validation. Le refus est net sur une commune au RNU ou sans parcelles ingérées.

---

## 5. Le client et l'exploitation prévenus

**Client** — tant que la commune est `desync` :
- **Fiche** (`frontend/.../Fiche.tsx`, bloc Urbanisme) : bandeau ambre « 🔄 PLU modifié le jj/mm/aaaa —
  règles en cours de mise à jour », servi depuis `fiche.plu_modifie` (API `_plu_modifie`).
- **Documents de la parcelle** (Dossier PDF `pdf_premium.py`) : section « PLU MODIFIÉ — MISE À JOUR EN
  COURS » avant le reste de l'urbanisme.
- **Analyse LABUSE** : les parcelles de la commune passent **« À vérifier »** avec la cause
  `PLU_MODIFIE_RECALIBRAGE` (overlay restaurable `scenarios_v2_persist.appliquer_recalibrage` ; le moteur
  pur `scenarios_v2.evaluate` honore aussi le drapeau). **Le Signal de vente n'est jamais touché**
  (il ne dépend pas des chiffres du PLU), ni les statuts durs (Hors projet / À différer / Préétude).

**Exploitation** — le job `plu-veille-nuit` (quotidien, 08:10 Réunion, après la sonde) :
- **John** (`john/veille.py::signaler_plu_modifie`, axe « reglementaire ») : commune, ancien → nouveau
  document, liste des gestes ;
- **Page Données / admin** (`ops_alertes.signaler`, incident `plu-modifie:<insee>`, lien `/donnees`) ;
- **Rappel sous 7 jours** : si l'incident traîne ≥ 7 j, un incident distinct `plu-modifie-rappel:<insee>`
  plus pressant ;
- **Résolution** : une commune rentrée dans l'ordre referme son incident et restaure ses parcelles ;
- **Rappel trimestriel** : les procédures en cours (`veille_plu.a_reverifier`, 90 j / 30 j si radar
  actif) sont remontées à John, comme les autres sources manuelles.

---

## 6. Procédure PROD (lecture seule ici — à jouer sur `labuse-vps`)

La ré-ingestion prod d'une commune dont le PLU a bougé (ex. Saint-Denis), au clic de Vic :

1. **Geste unique (données)** — `sudo -u labuse labuse plu appliquer --insee 97411`
   (ré-ingère zonage + prescriptions + informations ; pose le drapeau « règles à recalibrer » ;
   pose l'overlay « À vérifier » ; remonte l'incident). Transaction unique, idempotente.
2. **Couche servie (zonage)** — rebâtir la table dérivée et promouvoir :
   `labuse build-mvt` puis `labuse promote` (rebâtit `parcel_zone_plu` si absente). C'est une étape de
   service, hors de la transaction de données — ~20-40 min sous charge.
3. **Recalibrer les règles chiffrées** — relire les destinations sur le nouveau document
   (`labuse plu extraire 97411` / `labuse plu revue 97411`), puis **valider** :
   `labuse plu valider --insee 97411` → la commune repasse « à jour », le bandeau client disparaît,
   les parcelles sortent de « À vérifier ».
4. La veille `plu-veille-nuit` tourne de toute façon chaque nuit : elle **détecte** un nouveau document
   sans intervention, pose l'overlay et prévient John + la page Données — l'étape 1 n'a plus qu'à être
   déclenchée (ou l'incident traité sous 7 j).

> La détection (§1) et le signal client (§5) ne demandent **aucune** intervention : ils tournent seuls.
> Seule l'**application** (ré-ingestion + recalibrage) reste un geste humain (classe B — structurant).

---

## 7. Hook / tests

- **Python** : `tests/test_plu_veille_fix1.py` — 12 tests purs (détection par identifiant, 1→1,
  absence ≠ retard, drapeau recalibrage, moteur « À vérifier », Signal/statuts durs intacts, overlay
  idempotent) + 2 tests base (passage de nuit complet ; overlay posé/restauré). Registre : famille et
  `HORLOGES.csv` resynchronisés (`test_cockpit_lot_b`, `test_dashboardfix1_horloges`), `test_cron1_registre`
  vert. Suite unitaire complète verte.
- **Front** : `tsc -b` 0, `vitest` 326 verts (type `plu_modifie` + bandeau fiche).
- **Secrets** : rien trouvé. **Cohérence** : non impactée (aucun témoin €/m² touché).

---

## 8. Vérifications avant merge (demande de Vic)

### (1) Hook complet — cohérence rejouée, VERTE

L'étape de cohérence (arrêtée au premier rapport faute de base calme) a été **rejouée** :
`6 passed in 219,70 s` · « aucun écart (1 €/1 m²) sur les témoins » · exit 0 (run résiduel servi
seq 17). L'arrêt précédent **n'était pas un blocage** : la suite PROGRESSAIT (témoins validés un à un),
**aucune session en attente de verrou** (`wait_event` = CPU/`ClientRead`, jamais `Lock`) — seulement
ralentie par d'autres sessions (serveurs `uvicorn`/`labuse.cli api` d'autres worktrees, `::1`, 6
connexions depuis ~27 min, faisant des `ST_Intersection`/`ST_Union` lourds). Rejouée telle quelle sous
cette charge, elle finit en ~3 min 40 et passe. Les autres étapes du hook restent vertes
(tsc 0 · vitest 326 · pytest unitaire + scénarios/persist · secrets). → **hook complet vert.**

### (2) Les trois décalages, couche par couche (Géoportail vs ingéré, avec dates)

Confirmé **en direct** sur l'API Carto GPU (endpoint `/document` ET `/prescription-*`, features propres
`DU_<insee>`) le 11/11/2026 :

| Commune | Couche | Géoportail (publié) | Ingéré LABUSE | Verdict |
|---|---|---|---|---|
| **Saint-Denis** (97411) | zonage | `97411_PLU_20260805` | `97411_PLU_20260805` (14/09) | à jour |
| | prescriptions | `97411_PLU_20260805` (2908) | ⚠ `97411_PLU_20260423` (29/06) | **en retard** → corrigé §3 |
| | informations (DPU) | `97411_PLU_20260805` | `97411_PLU_20260805` | à jour |
| | règles chiffrées | `97411_PLU_20260805` | calibrée 03/09 sur `…20260805` | à jour |
| **Saint-Joseph** (97412) | zonage | `97412_PLU_20251210` | `97412_PLU_20251210` | à jour |
| | prescriptions | `97412_PLU_20251210` (451) | ⚠ `97412_PLU_20240320` (447) | **en retard** |
| | informations (DPU) | non publié | absent | — |
| | règles chiffrées | `97412_PLU_20251210` | calibrée sur `…20251210` | à jour |
| **Bras-Panon** (97402) | zonage | `97402_PLU_20260428` | `97402_PLU_20260428` | à jour |
| | prescriptions | `97402_PLU_20260428` (412) | ⚠ `97402_PLU_20211020` (412) | **en retard** (PLU **précédent 2021**) |
| | informations (DPU) | non publié | absent | — |
| | règles chiffrées | `97402_PLU_20260428` | calibrée sur `…20260428` | à jour |

**Bras-Panon, clairement** : le **zonage ET les règles** servis aux clients sont ceux du **PLU EN
VIGUEUR** (2026, `97402_PLU_20260428`) — **PAS un ancien PLU**. Le seul retard est sur les
**prescriptions** (ER/EBC), ingérées du PLU **précédent** (2021, `97402_PLU_20211020`), alors que le
Géoportail sert déjà celles de 2026 (vérifié en direct : 412 features propres `DU_97402` à l'idurba
`97402_PLU_20260428`) — ce n'est donc pas un faux positif. En conséquence, **0 parcelle ne change de
zone** (le zonage servi est déjà à jour) ; le décalage ne touche que les prescriptions. Même profil
pour **Saint-Joseph** (zonage et règles à jour, seules les prescriptions en retard).

### (3) Déclencheur de l'affichage client : la DÉTECTION, pas `plu appliquer`

Le job de nuit `plu-veille-nuit` appelle `synchroniser_recalibrage(communes_desync)` : **dès qu'une
commune est `desync`**, ses parcelles passent « À vérifier » et le bandeau fiche s'allume (il lit
`plu_veille_etat`). Le signal **ne dépend pas** de `plu appliquer` — qui est le **correctif** (aligne
les couches + pose le drapeau règles), pas le déclencheur.

**Preuve en base** : **Bras-Panon (4 191 parcelles)** et **Saint-Joseph (15 613)** sont **déjà** en
overlay « À vérifier » alors qu'elles n'ont **jamais** été `plu appliquer` — seule la détection les a
basculées.

**Au premier passage de nuit en prod** (chiffres mesurés sur la base locale q_v20, prod-like) :
communes basculées = **Saint-Denis, Saint-Joseph, Bras-Panon** ; parcelles passant « À vérifier »
(statuts chiffrés éligibles) = **30 124 + 15 613 + 4 191 ≈ 49 928**. Les parcelles « Hors de ce
projet » / « À différer » restent inchangées (p. ex. Saint-Denis : 8 171 non éligibles sur 38 295).

### (4) Prescriptions Saint-Denis (ER, EBC) dans la capacité — combien changent, quels IDU recalculer

Les prescriptions **entrent bien dans la capacité** (`config/cascade_rules.yaml` → règle
`prescription_plu`, `src/labuse/cascade/layers/phase1.py`) : **ER ≥ 50 %** de la parcelle →
**rédhibitoire** (exclue) ; **EBC ≥ 80 %** → **rédhibitoire** ; en deçà, la **surface ER/EBC est
soustraite** de l'assiette constructible (pré-faisabilité). Les autres types (mixité, OAP, eaux
pluviales, patrimoine) sont des vigilances, sans effet sur la capacité.

- **Combien changent (exclusion)** : la ré-ingestion fait passer le nombre de parcelles de Saint-Denis
  **rédhibitoirement exclues par prescription de 2 743 → 2 757**, soit **14 parcelles qui DEVIENNENT
  exclues** (ER ≥ 50 % / EBC ≥ 80 % sur la nouvelle géométrie), **0 qui cessent de l'être**. Mesure
  avant/après non destructive : le run servi (`cascade_results`) porte les verdicts calculés sur les
  anciennes prescriptions (20260423) ; comparés à la couverture ER/EBC recalculée sur les nouvelles
  (20260805). Les **14 IDU** :
  `97411000AK0184, 97411000BE0025, 97411000BW0164, 97411000BX0057, 97411000CH0672, 97411000CM0226,
  97411000CP0479, 97411000CY0016, 97411000EL0164, 97411000EL0169, 97411000IC0148, 97411000IL0379,
  97411000IS0406, 97411000IV0035`.

- **Liste à recalculer pour que fiche == run** : **14 155** parcelles de Saint-Denis intersectent une
  prescription **ER (10 991)** ou **EBC (4 188)** — ce sont celles dont la capacité peut bouger (les 14
  par leur exclusion ; les autres par la part ER/EBC soustraite, à la marge). La liste complète des
  14 155 IDU est écrite dans **`reports/PLU-VEILLE-FIX-1-saint-denis-recompute.txt`**. Geste prod après
  `plu appliquer 97411` : `labuse reevaluer-cascade` sur ces IDU, puis re-persister les scénarios V2 —
  sinon la fiche (calcul live) et le run (persisté) divergent sur ces parcelles.

> Les deux autres décalages (Bras-Panon, Saint-Joseph) appellent le même geste prod (prescriptions
> ER/EBC à réingérer + recalcul des parcelles touchées) ; leur zonage et leurs règles, eux, sont déjà
> à jour (§2) — rien à refaire côté zonage.

*Fin du rapport.*
