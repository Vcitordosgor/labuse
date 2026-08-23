# M144 — Argumentaire : le bilan paie ce qu'il encaisse (`fix/m144-argumentaire-fond`)

Branché sur `origin/main` @ `5209a03c` (avance depuis M143 = M143 mergé + `prospection-solaire`,
hors périmètre — signalé). Cinq lots. CC ne merge jamais.

**Résumé : Lot 1 (le difficile) — le bilan chiffrait le scénario SILO (82 logts) sans en payer le
parking enterré, alors que la faisabilité retient l'AU SOL (64-65). Corrigé à la racine (une seule
source de scénario). CW1073 recalculé honnêtement à −3,63 M€ (toujours non équilibré, moins qu'avant),
CX1395 médiane 93 k€ → 66 k€. ZAC : aucune couche ingérée → dette. VRD saisissable. Six petites
vérités. Zéro montant négatif, deux dates intactes.**

---

## Lot 1 — Le bilan et la faisabilité racontent le même scénario

### 1.A — Le verdict (d'où venait le mélange)

**La faisabilité produit DEUX scénarios de stationnement** (`engine.py:369-385`) : *au sol* (`sol_*`,
le parking mange l'emprise → moins de logts) et *sous-sol/silo* (`sous_*` = plancher de densité, le
sol n'est plus consommé → plus de logts, mais exige un parking en ouvrage). Le scénario **retenu et
nommé** est l'au sol : `Step("Logements retenus au sol", …)` (`engine.py:445`).

**Le défaut, à la ligne** : `engine.py:462` posait `shab_vendable_m2 = round(sous_central × logt_moyen)`
— le **central du silo**, alors qu'il n'existait **pas de `sol_central`**. Le commentaire du même
bloc (`engine.py:439-441, 459-461`, M128-2-I1/M128-5-§1) disait pourtant que le vendable porté « au
bandeau ET au bilan » est celui « au sol » : **le code contredisait son intention documentée.** Le
bilan (`compute_calculette` lit `fourchette.shab_vendable_m2`) encaissait donc le CA du silo (82
logts) sans le coût de la place enterrée. C'était bien *la* cause du déséquilibre gonflé.

**« Scénario retenu » n'est PAS ambigu** (l'au sol est explicitement nommé) → **pas de STOP court.**

**Le cas nominal mélange aussi**, un peu : CX1395 a `au_sol=(4,5)` vs `sous_sol=(4,6)` — le parking
plafonne légèrement, donc ses chiffres bougent (documenté en contrôle 2, ci-dessous).

### 1.B — L'alignement (structural, une seule source)

- **Engine** (`engine.py`) : nouveau `sol_central` (plafond densité ∩ stationnement au sol, **modulé**,
  parallèle à `sol_lo/sol_hi`). `shab_vendable_m2 = round(sol_central × logt_moyen)` — **le scénario
  RETENU**. `shab_vendable_silo_m2` exposé pour la mention de prose. Une seule source, faisabilité et
  bilan alignés. La correction est **structurelle** : elle profite aussi au dossier banquier et à la
  calculette de la fiche (même moteur, même bug encaissé).
- **Argumentaire** (`argumentaire.py`) : le bilan **NOMME** son scénario quand le stationnement au sol
  plafonne réellement (silo > au sol) — « Bilan établi sur le scénario **retenu** : N logements,
  stationnement au sol (~X m²) » — et **mentionne le silo en PROSE**, jamais chiffré : « un
  stationnement en ouvrage porterait la surface vendable à ~Y m², au prix d'un coût de place enterrée
  **non estimé ici** » (doctrine : aucune constante 25-40 k€/place fabriquée).

### Les deux exemplaires (hypothèses par défaut 2500 €/m², 21 %, VRD 90 €/m²)

**CW1073 (Saint-Paul, 5469 m², AU3a) — recalculé HONNÊTEMENT :**
> « l'opération n'est pas équilibrée : le chiffre d'affaires prévisionnel (**14,43 M€**, ex-18,44 M€
> silo), une fois la marge et les frais couverts, ne suffit pas à financer la construction (14,54 M€)
> et les VRD (492 k€) — il manque **3,63 M€** (ex-4,51 M€). »
> Scénario nommé : « 64–65 logements, stationnement au sol (~4 652 m²). Un stationnement en ouvrage
> porterait la surface vendable à ~5 948 m², au prix d'un coût de place enterrée non estimé ici. »
> **Toujours non équilibré, mais moins** (le silo gonflait le déséquilibre). Zéro montant négatif.

**CX1395 (Saint-Paul, 608 m², U3c) — écart vs M143, ligne à ligne (contrôle 2) :**
> médiane **93 k€ → 66 k€**. **Cause unique = Lot 1** : `shab_vendable` 373 m² (silo) → **304 m²**
> (au sol ; le parking plafonne, `au_sol=(4,5)` < `sous_sol=(4,6)`). CA ∝ shab (×0,815), construction
> ∝ shab, VRD inchangé → charge foncière médiane 93 → 66 k€. **Aucun autre écart inexpliqué.**

---

## Lot 2 — La ZAC — **aucune couche ingérée → dette nommée**

Vérification (couches spatiales, GPU) : **aucune couche interrogeable ne porte de périmètre de ZAC**.
Le seul « ZAC » du code est un commentaire ; « ZAC Renaissance III » n'existe que sur le fond OSM (à
ne pas parser). Les `kind` de `spatial_layers` (plu_gpu_zone/prescription, sup, ppr, sar…) n'incluent
aucun secteur d'aménagement. Le GPU `info-surf` **est** appelé (`anc.py:206-234`) mais **filtré à
`typeinf='19'`** (assainissement) — les secteurs d'information type ZAC sont jetés.

→ **Aucune entrée de vigilance ajoutée** (pas de détection approximative). **Dette nommée :** lever le
filtre `typeinf` dans `anc.py` pour ingérer les secteurs ZAC/aménagement (`kind='zac'`, même patron
`_insert_layer` + requête `ST_Intersects` de `servitudes.py:114`), ou seeder un dataset ZAC
DEAL/TCO/Saint-Paul. Quand la couche existera, une entrée vigilance conditionnelle (section 6),
sourcée, non chiffrée.

---

## Lot 3 — Le prix ancien appliqué au neuf se DIT

`argumentaire.py` (`_bilan_rebours`) — une ligne, **toujours** : « Prix de sortie retenu : ventes DVF
de l'existant (appartement, N ventes AAAA–AAAA, fiabilité …). Le neuf (VEFA) est trop rare dans DVF
pour une série fiable — prix de l'ancien retenus, hypothèse prudente pour un programme neuf. »

---

## Lot 4 — Les VRD cessent d'être une hypothèse honteuse

`compute_calculette` portait déjà le paramètre `vrd_m2` (défaut config). Exposé de bout en bout :
`vrd_m2 = Query(90.0, ge=0, le=500)` sur la route → `_build_pdf` → `_collect` → `compute_calculette` ;
`hypotheses_encadre` gagne une 3ᵉ hypothèse. L'encadré liste désormais **coût · marge · VRD** — et
« LABUSE ne les estime pas » devient vrai pour les trois (plus aucune constante de calcul ni sourcée
ni saisie). **Vérifié** : VRD 90 → charge 65 673 € ; VRD 150 → charge 29 193 € ; l'encadré affiche
la valeur saisie.

---

## Lot 5 — Les petites vérités

1. **Tendance stable ⟂ −4,2 %** : seuil resserré **±5 % → ±2 %** (`marche_commune.py:201`,
   `bilan.py:97` alignés). Sous ±2 %/an (bruit de la médiane DVF communale) = *stable* ; au-delà,
   *hausse*/*baisse*. **Vérifié : « stable −4,2 % » devient « baisse −4,2 % »** — le mot suit le signe.
2. **Fourchette dégénérée « X – X »** : `bilan.py` (coût de construction) collapse quand
   `round(cc_bas) == round(cc_haut)` → une valeur unique (CX1395 : « ~950 k€ »).
3. **« 98 à 121 » (§3) vs « 98-122 » (§4)** : ce n'était **pas** une divergence d'arrondi mais le
   **plafond de densité** (§4 = enveloppe pré-cap, §3 = retenu post-cap, « → borné à »). Séparateur
   unifié (`engine.py` : « - » → « à »), l'écart 121/122 est le cap, dit explicitement.
4. **« 1 aberrant exclu »** : la règle se dit (`bilan.py`) — « méthode de Tukey : hors
   [Q1−1,5×IQR ; Q3+1,5×IQR], bornée 100–12 000 €/m² ». **Vérifié** sur une parcelle à `n_exclus=3`.
5. **Zone AU3a « ESTIMÉ »** : vérifié. Le zonage AU3a est **sourcé** (GPU, avec son idurba) ; sa
   hauteur résout **par renvoi** à U3a, qui **porte** la source (Art. 10.2) → hauteur **Sourcé**, pas
   de mislabel sur CW1073. Reformulation ajoutée pour le cas général : quand un renvoi n'a **pas** de
   source de hauteur, une note dit « le zonage est sourcé, l'Estimé porte sur la hauteur héritée par
   renvoi, pas sur le zonage ». (L'« Estimé » que peut voir un lecteur sur CW1073 est la ligne
   *emprise*, légitimement estimée — non réglementée à Saint-Paul.)
6. **4 permis du même jour** : `briques_pdf` — note conditionnelle quand des permis partagent la date :
   « probablement une opération unique déposée en tranches, pas des projets distincts ». **Vérifié**
   sur CW1073 (4 permis du 2025-05-15).

---

## Contrôles

1. **CW1073 régénéré** : le bilan nomme son scénario (64-65, au sol), surface vendable = le retenu
   (4 652 m²), verdict **recalculé honnêtement** (−3,63 M€, non équilibré) — **0 montant négatif**. ✓
2. **CX1395 régénéré** : écart 93 k€ → 66 k€ **entièrement** expliqué par le Lot 1 (shab 373→304),
   aucun écart inexpliqué. ✓
3. **Zéro montant négatif** (régime M143 intact) ; **les deux dates** (M143 Lot 3) intactes. ✓
4. **Vigilance ZAC** : non ajoutée — aucune couche (dette). ✓
5. **VRD saisissable** : deux valeurs (90 / 150) → le bilan suit, l'encadré l'affiche. ✓
6. **ruff** : 5 fichiers touchés = 0 warning (baseline 0), aucun nouveau. **`tsc`** : aucun fichier
   front touché. Aucun golden test cassé (shab_vendable non asservi ; tendance/aberrant non golden). ✓

## Hors périmètre
F4 (posture d'exposition — dette existante). Lettre de zonage, Flash, revue de division. Tout coût
de construction enrichi (parking en ouvrage) : **dette produit**, aucune constante inventée.

*Fin. Commits sur `fix/m144-argumentaire-fond`. Vic merge en `--no-ff`. CC ne merge jamais.*
