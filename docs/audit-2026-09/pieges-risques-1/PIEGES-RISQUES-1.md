# PIÈGES-RISQUES-1 — Outil « Pièges et risques »

Branche `fix/pieges-risques-1` (worktree `labuse-pieges`, base `main` `1a6d58d0`). Vérif data lecture
seule (point 1, non corrigée) + correctif de comportement (point 2, capturé avant/après).

L'outil `risques` (ex-fusion O5 + M10) a **deux entrées** qui ne lisent PAS la même source :

| Entrée | Endpoint | Source réellement lue | Nature |
|---|---|---|---|
| **Une parcelle** (`O5Servitudes`) | `GET /servitudes-invisibles/{idu}` | `spatial_layers` **EN DIRECT** (`ST_Intersects` sur `geom_2975`), 13 *kinds* | servitudes **dormantes** — la MÊME table que les couches carte |
| **Un lot** (`M10`) | `POST /modules/duediligence` | cascade **pré-calculée** `dryrun_cascade_results` (run servi `q_v11_m137`) + backfill ZNIEFF (`spatial_layers`) + CATNAT (`catnat_arretes`, grain commune) + propriétaire (`parcelle_personne_morale`) | crible **risques** — la MÊME source que la fiche §Pièges & risques (`_aleas_block`, `layer='risques'`) |

> **Constat de tête (É1) :** les deux entrées répondent à la même question avec **deux sources
> différentes** → pour une même parcelle, les deux listes divergent (détaillé plus bas). Ni faux, mais
> non réconcilié. C'est un fait de conception à connaître, pas corrigé (hors mandat).

---

## 1. Vérif data

### 1.a « Une parcelle » — chaque contrainte, sa source

`GET /servitudes-invisibles/{idu}` lit `spatial_layers` (kind) et joint `data_sources` pour la
**source** (nom) et le **millésime** (`COALESCE(last_sync_at, updated_at)`, affiché par ligne). C'est
**la même table que les couches de la carte** (même `kind`) — le mode « Une parcelle » lit donc
exactement ce que la carte peint. La fiche parcelle, elle, éclate ces contraintes dans des blocs
distincts (ANC dans le bloc `anc`, PPR/aléas dans §Pièges & risques via la **cascade**, EBC/ER via
les prescriptions…), et **son §Pièges & risques est un bloc d'ALÉAS** (`layer='risques'`), pas la
liste de servitudes de l'outil.

| Contrainte (libellé outil) | `kind` · filtre | Source (`data_sources`) | Millésime affiché | = couche carte ? | = fiche ? | Témoin |
|---|---|---|---|---|---|---|
| Assainissement non collectif (ANC) | `zonage_assainissement` (subtype=`anc` seul) | GPU — zonages d'assainissement | par ligne (BZ1065 : 2026-08-21) | oui (même table) | fiche = bloc `anc` séparé (pas le §risques) | BZ1065 ✓ |
| Droit de préemption (DPU) | `dpu` | GPU — DPU (info-surf) | 2026-09-07 | oui | non servi au §risques fiche | BZ1065 ✓ |
| SUP / PPR (assiette) | `sup` (subtype `pm1/pm2/pm3/ac1..4/el10…`) | SUP — assiettes GPU (API Carto) | 2026-09-14 | oui | fiche §risques montre le PPR en **aléa gradué**, pas l'assiette SUP (**É2**) | BZ1065, AI0090 ✓ |
| Emplacement réservé (ER) / Espace boisé classé (EBC) | `plu_gpu_prescription` (subtype `05`/`01` **seuls**) | Urbanisme PLU/GPU (API Carto) | par ligne | oui | fiche = bloc prescriptions | AI0090 ✓ |
| 50 pas géométriques | `cinquante_pas` | (idem couche) | par ligne | oui | — | AI0090 ✓ |
| Classement sonore des voies (bruit) | `bruit_route` | (idem couche) | par ligne | oui | — | — |
| Secteur d'information sur les sols (SIS/CASIAS) | `sol_pollue` | (idem couche) | par ligne | oui | — | — |
| Recul du trait de côte | `trait_de_cote` | (idem couche) | par ligne | oui | — | AI0090 ✓ |
| Ravines / reculs (domaine public fluvial) | `dpf` | (idem couche) | par ligne | oui | — | — |
| Zone humide | `zone_humide` | (idem couche) | par ligne | oui | — | — |
| Espace naturel protégé | `ens` | (idem couche) | par ligne | oui | — | — |
| ZNIEFF | `znieff` | (idem couche) | par ligne | oui | — | — |
| Plan d'exposition au bruit (PEB aérodrome) | `peb` | (idem couche) | par ligne | oui | — | — |

**Non lus par « Une parcelle » (mais présents en couche carte et/ou en fiche) :**
- **É2 — aléas gradués** : `kind='ppr'` (zonage rouge/bleu, 164 lignes), `mvt`/`georisque_alea`
  (aléas mouvement/inondation) NE sont pas lus. Le PPR n'apparaît QUE via l'assiette SUP `pm1`
  (« Risques naturels (PPR) — prescriptions constructives »), **sans le % de zone rouge**. La carte
  affiche ces couches ; la fiche §risques et le mode « Un lot » chiffrent le PPR rouge (%).
- **É3 — prescriptions GPU filtrées** : seuls ER(`05`)+EBC(`01`) sont montrés ; les autres
  prescriptions présentes sur la parcelle (ex. AI0090 : `02` secteur de risque/environnement, `15`,
  `19`) ne sont **pas** affichées en « Une parcelle » (elles le sont en « Un lot » comme
  `prescription_plu`). Volontaire (filtre `_PRESCRIPTION_PIEGE`), mais = contraintes réelles muettes.

#### Témoins « Une parcelle »

- **BZ1065 (témoin Vic) — 3 servitudes = EXACT.** Intersect brut en base des 13 kinds :
  `dpu`, `plu_gpu_prescription/04` (« Périmètre zone souple » → **filtré**, ni ER ni EBC),
  `sup/pm1` (×5 doublons enveloppes → **dédupliqués en 1**), `zonage_assainissement/anc`.
  Après filtre + dédup (kind, effet) → **3** : **ANC, DPU, SUP/PPR**. Aucune des 13 couches
  n'est oubliée ; le `04` est écarté par conception (pas un piège foncier). Confirmé par l'endpoint
  live (`n:3`). La carte peint les mêmes 3 (+ la couche PPR aléa via `pm1`) ; la fiche les répartit
  (ANC bloc `anc`, PPR §risques en aléa bleu — cf. É2).
- **AI0090 Bras-Panon — très contrainte (PPR + ER + EBC).** « Une parcelle » : EBC(`01`), ER(`05`),
  50 pas, SUP/PPR `pm1` (×4→1), trait de côte. (Prescriptions `02/15/19` masquées — **É3**.)
- **97414000CH0318 Cilaos/Saint-Louis — sans rien.** « Une parcelle » : **`n:0`**, « Aucune servitude
  dormante détectée ». (Or le lot la classe « risque 60 » — cf. É1.)

### 1.b « Un lot » — définition et agrégation

**Définition du lot :** barre `ParcelInput` (adresse / IDU / référence courte `SECTION+NUMÉRO`) →
**chips retirables**, + collage multi-lignes, + clic carte. Pas de dessin. Max **60** parcelles.
`onPick` n'accepte que des références **résolues** (une adresse brute non rattachée est refusée avec
un message, jamais mise en chip). Chaque parcelle est requêtée **indépendamment**.

**Agrégation = juste.** Par parcelle : lecture cascade `dryrun_cascade_results`, **dédup des lignes
strictement identiques** (`layer+severity+result+detail`) DANS la parcelle (anti-double-compte des
fragments d'aléa), + ZNIEFF en repli si absente de la cascade, + CATNAT (commune), + propriétaire.
**Pas de fusion inter-parcelles** : chaque parcelle = une entrée, sa propre checklist. Donc une
contrainte est **comptée une fois par parcelle touchée**, jamais dupliquée entre parcelles, jamais
perdue.

**Test union exacte — lot `[BZ1065, AI0090, CH0318]` :** `n_demandes:3 / n_trouvees:3`, 3 entrées,
chacune identique à sa checklist individuelle (`duediligence` mono). L'union du lot = la
concaténation exacte des listes par parcelle. ✓

### 1.c Écart central (É1) — les deux modes divergent pour la MÊME parcelle

| Parcelle | « Une parcelle » (spatial_layers) | « Un lot » (cascade `q_v11_m137`) |
|---|---|---|
| **BZ1065** | 3 : **ANC, DPU, SUP/PPR** | risque 80 : PPR **zone bleue** (risques, fort), prescription « zone souple », SUP `pm1`, résiduel — **ni DPU ni ANC** |
| **AI0090** | EBC, ER, 50 pas, SUP/PPR, trait de côte | risque 100 : HARD zone A PLU + **PPR rouge 51 %/26 %**, EBC, ER, aléas inondation/mvt, ICPE 148 m, RPG, trait de côte… |
| **CH0318** | **0 (vide)** | **risque 60** : Parc National (aire d'adhésion), aléa mvt faible |

Le PPR apparaît dans les deux mais **représenté différemment** (assiette SUP vs aléa rouge %). ANC/DPU
(servitudes) ne sont **pas** au crible ; les aléas gradués/ICPE/RPG ne sont **pas** en « Une parcelle ».
**Écarts data — aucun corrigé (hors mandat) :** É1 (divergence de source), É2 (aléas PPR gradués non
lus en single), É3 (prescriptions GPU filtrées), É4 (mineur : le lot affiche une ligne `UNKNOWN
proprietaire` pour un particulier — bruit de présentation, `age_dirigeant` déjà masqué au front).

---

## 2. Comportement — la saisie amène sur la parcelle (corrigé)

**Avant.** Taper « 3 Chemin de la Citerne » / `97411000BZ1065` listait bien les contraintes, mais **la
carte ne bougeait pas** : `O5Servitudes.onPick` faisait seulement `setIdu(id)` (déclenche la requête),
sans toucher la carte. Idem à l'ajout au lot. Prouvé : centre/zoom **inchangés** après la recherche
(île `55.5267 / −21.1305`, z 9.18 → 9.18) — capture `avant-2-parcelle-recherche.png`.

**Après.** La saisie (adresse / IDU / réf. courte) résout la parcelle, la carte **zoome dessus (z 18)
avec son contour surligné**, le panneau affiche ses contraintes, et un lien **« Ouvrir la fiche → »**
(jaune permanent `#E0A94F`, `data-o5-fiche`) apparaît sous la référence — **la fiche ne s'ouvre QUE
sur ce clic** (l'ouvrir d'office fermerait l'outil ; vérifié : le clic pose `idu=…` dans l'URL et
monte la fiche). Même geste en « Un lot » : chaque ajout zoome sur la **dernière** parcelle ajoutée.

Mécanique réutilisée de **PERMIS-CHECK-2** : `select(null)` **avant** `focusParcelle(idu)` (la carte
cible `selectedIdu ?? focusIdu` ; une sélection périmée masquerait sinon le focus posé par la barre).

Mesures live (`window.__labuse_map`) :

| Étape | Avant (code d'origine) | Après (correctif) |
|---|---|---|
| Île (départ) | 55.5267 / −21.1305 · z 9.18 | 55.5267 / −21.1305 · z 9.18 |
| « Une parcelle » → BZ1065 | **55.5267 / −21.1305 · z 9.18** (inchangé) | **55.4295 / −20.8852 · z 18** (St-Denis, contour surligné) |
| « Un lot » +AI0090 | inchangé | **55.6989 / −20.9918 · z 16.5** (Bras-Panon) |
| « Un lot » +BZ1065 | inchangé | **55.4295 / −20.8852 · z 18** (dernière ajoutée) |

**Captures** (`captures/`) : `avant-2-parcelle-recherche.png` (bug : île + panneau rempli),
`apres-2-parcelle-recherche.png` (fix : parcelle zoomée + contour + panneau + lien « Ouvrir la fiche →
» jaune), `apres-3-lot-ajout.png` (lot : zoom + contour sur la parcelle ajoutée),
`apres-1-parcelle-initial.png` (contexte).

### Fichiers touchés
- `frontend/src/components/outils/blocB.tsx` — `O5Servitudes` : `onPick`→`allerA` (`select(null)` +
  `focusParcelle`), ligne référence + lien permanent « Ouvrir la fiche → ».
- `frontend/src/components/outils/ModulePanel.tsx` — `M10.ajouter` : `select(null)` + `focusParcelle`
  sur la dernière parcelle ajoutée.

Portes : `tsc -b` + `vite build` verts ; `PiegesLot.test.tsx` 3/3 ; vitest **176 P / 2 échecs
`admin/circuit/Detail.test.tsx` PRÉ-EXISTANTS** (aucun lien avec l'outil, n'importent pas les fichiers
touchés).
