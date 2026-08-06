# M40 — BILAN (confrontation de sources n°1 : GPU vs millésime mairie)

**Branche `m40-confrontation-gpu-mairie`** · base `main` c982f46d (M39 mergé) · commits atomiques
`[M40-Px]`. **Aucun changement de tier, aucune bascule, aucun merge.** Le mandat construit la
confrontation durable (garde), corrige la config sur pièces, et expose honnêtement la source qui
fait foi. Aucune parcelle candidate au geste groupé côté zonage.

---

## Le fil (constat P0 → arbitrages Vic → repli)

Prémisse du backlog : « le GPU est en retard sur les mairies ». **Infirmée sur pièces au P0** : la
campagne de ré-extraction M32 avait déjà aligné les documents. Confrontation idurba GPU
(`spatial_layers`) vs idurba mairie (`plu_millesimes.yaml`) : **23/24 identiques, 1 RNU, 0 document
divergent** (`qa/m40/M40_P0_CONSTAT.md`). Arbitrage Vic : pas de comparaison parcellaire creuse →
**repli (a) garde idurba · (b) corrections config · (c) exposition fiche**.

---

## PHASE 1

### P1.1 · Garde de cohérence idurba — le livrable central — commit `[M40-P1]`
`check_coherence_idurba()` dans `bascule_gardes.py` (modèle `check_fraicheur`) : oppose par commune
l'idurba MAIRIE à l'idurba GPU ingéré. Deux divergences chiffrées (ampleur en jours) :
- **MANQUANT** : document mairie absent du GPU = **vrai retard GPU-derrière-mairie** — la raison
  d'être de la garde : une comparaison ponctuelle dit l'état d'un jour, la garde attrape le jour où
  le retard apparaît ;
- **RESIDU** : document superseded conservé au GPU (hygiène).

**Bruyante NON bloquante** (régime `check_fraicheur`). Tourne **au geste de bascule groupé** (importée
depuis `bascule_gardes`, comme les 6 gardes) **ET en autonome** (`scripts/check_coherence_idurba.py`,
sortie lisible, exit 0). Cœur pur `_confronter_idurba()` testable sans DB. **Test d'acceptation Vic :
signale Saint-Joseph aujourd'hui** (RESIDU, ampleur 630 j) ✓ — puis, après archivage (P1.2), la garde
est **clean** (0 divergence). 6 tests verts (dont un MANQUANT synthétique qui prouve la détection du
vrai retard).

### P1.2 · Corrections config sur pièces + archive réversible — commit `[M40-P1]`
Chaque correction **justifiée par sa pièce** :

| Commune | Correction | Pièce |
|---|---|---|
| Saint-André / Saint-Leu | note M32 « AUCUN document GPU » **retirée** — le doc opposable EST sur GPU et fait foi ; révision en cours non servie | `spatial_layers` : 97409_20190228 = 142 zones, 97413_20070226 = 368 zones (ingérées 2026-06) |
| Saint-Benoît | incertitude **consignée** (modifs postérieures éventuelles non intégrées, à confirmer mairie) | aucune pièce des modifs → non fabriqué (arbitrage D) |
| en-tête | doctrine ajoutée : « une note de config est une affirmation d'agent, pas une source » | le cas SA/SL lui-même |

**Résidu Saint-Joseph ARCHIVÉ (réversible, doctrine M32/M37)** : 3 zones stale `97412_PLU_20240320`
(A/N) → `kind = plu_gpu_zone__archive_m40` (renommage, **pas de DELETE** ; rollback documenté dans le
script). Retrait **tier-neutre** (run gelé ; le subtype stale est déjà présent au document courant sur
1670/1671 parcelles — vérifié P0). `scripts/m40_archive_residu_sj.py`, idempotent.

### P1.3 · Exposition « source qui fait foi » — 3 choses distinctes — commit `[M40-P1]`
`_plu_fraicheur` expose les **trois choses, jamais mélangées** — exigence Vic :
1. **document_servi** — quel document LABUSE sert ;
2. **fait_foi** — qu'il est bien celui qui fait foi à ce jour ;
3. **en_cours** — ce qui est en cours et **non servi** (révision / annulation / modifs), formulé
   sans jamais répéter (1)/(2) ; le `note` config détaillé reste servi à part (traçabilité).

\+ **action** « vérifier en mairie » sur les statuts qui le justifient. Rendu **server-side** dans le
one-pager (`export.py`, bloc « Zonage — source qui fait foi ») → repris dans les exports ; et **front**
(`Fiche.tsx` + `types.ts`, additif, `tsc -b` exit 0). `plu_fraicheur` ajouté à `_build_fiche` (défaut
+ one-pager, pas seulement la fiche premium). **L'honnêteté comme argument commercial : on assume ce
que les autres laissent flou.**

---

## PHASE 2 — Mesure pour la bascule groupée

**Aucune parcelle candidate.** Le zonage servi = le document qui fait foi pour 23/24 communes ; il
n'y a pas de parcelle « à déclasser au vu de la source qui tranche ». Contrairement à M39, **rien ne
rejoint le dossier du geste groupé côté zonage**. Les statuts non-`a_jour` sont des VIGILANCES
(« vérifier en mairie »), pas des déclassements — le doute ne profite jamais au classement.

Exposition (têtes servies concernées, pour information) : Saint-Leu 82 têtes + 369 réserve · Saint-
André 30 + 273 · Le Port 25 + 40 · Saint-Philippe 2 (RNU). Digest : `confrontation_gpu_mairie_p0.csv`.

---

## VÉRIFICATION (2026-08-06)

| Contrôle | Résultat |
|---|---|
| **Golden** | **117/117 PASS, 0 FAIL** (plu_fraicheur ajouté à _build_fiche = golden-invisible, vérifié) |
| **Re-mesure M34/M35** (`mesure_p2`, 1071 parcelles) | **0 divergence — PASS** |
| **SHA256 vigilances M37** | `482da6f6…e9abe9` — **INCHANGÉ** (l'archive SJ ne touche pas le cascade gelé) |
| **Tiers servis** | **0 tier modifié** (119 brûlante / 1041 chaude, identiques) |
| **pytest** | **1318 verts** (+6 tests idurba), 5 échecs pré-existants (residuel×4, au_ouverture×1) |
| **tsc -b (front)** | exit 0 |

**Écritures DB, toutes hors scoring et tracées** : `spatial_layers` (archive SJ, réversible). Aucune
écriture `parcel_p_score_v2` / run / cache scoring / cascade_results.

### Captures (`qa/m40/screens/`)
1. `1_divergence_exposee_saint_leu.png` — Saint-Leu (opposabilite_en_attente) : bloc « source qui
   fait foi » en 3 temps + action « vérifier en mairie ».
2. `2_temoin_a_jour_saint_denis.png` — témoin `a_jour` : document servi + « à jour du GPU », sans
   « en cours ».
3. `3_rnu_saint_philippe.png` — commune hors-PLU-outillé (RNU) : libellé **honnête sur ce qu'on ne
   sait pas** (« Aucun PLU — RNU ; constructibilité au cas par cas »).

### Digests de preuve
- `confrontation_gpu_mairie_p0.csv` (24 communes : idurba mairie vs GPU, statut, match, résidu,
  têtes) + `_global.txt` (SHA256). **Pas de digest .csv.gz massif** : la confrontation a du sens à
  la maille COMMUNE (24 lignes), pas parcelle — il n'existe aucune divergence parcellaire à lister
  (documents alignés). Consigner un faux digest de 430 k lignes « sans divergence » serait du bruit.

---

## DOCTRINE dégagée (à resservir)

**Une NOTE de config est une affirmation d'agent précédent, PAS une source.** Elle se vérifie sur
pièces comme le reste. Le cas Saint-André/Saint-Leu l'a montré : la note M32 « aucun document GPU en
ligne » était fausse — le GPU hébergeait bien le document opposable (142/368 zones). Ajoutée à
l'en-tête de `plu_millesimes.yaml` et aux conventions.

**Corollaire M40 (confrontation de sources)** : avant de bâtir une confrontation, vérifier qu'elle a
de la SUBSTANCE. Ici la prémisse (GPU en retard) était fausse ; la valeur n'était pas une comparaison
ponctuelle (0 divergence) mais une **garde en continu** qui attrape le retard le jour où il naît, plus
le nettoyage des affirmations non vérifiées. Ne pas fabriquer une comparaison qui donne 0.
