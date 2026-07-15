# M8a — FIX mapping ER + atterrissage ANO-1 + re-run CANDIDAT (q_v6_m8)

**Date** : 2026-07-14 · **Branche** : `feat/m8-ingestion` · **Run servi** : `q_v5_m6b` (cascade) / p_score `m36-l2f-2026-2026-07-14` — **INCHANGÉS**.
**Run candidat** : `q_v6_m8` (cascade) / `q_v6_m8` (p_score) — **NON servi**. Modèle P M3.6 GELÉ. Seed 974.

⚠️ Session mutante (config + code + re-run candidat). **Aucune bascule, aucun merge.** Vic valide le delta avant toute bascule.

---

## 0. Ce qui a été modifié (fix)

**Boussole appliquée partout** : une fausse opportunité servie = faute grave ; une opportunité ratée = acceptable → en cas de doute, **écarter**.

### Code — `src/labuse/cascade/layers/phase1.py` (`PrescriptionPluLayer`)
Garde par **libellé** en complément du mapping par code (les codes `typepsc` varient entre communes) :
- **RESCUE** : un libellé ER reconnaissable (typo-tolérant) est traité ER **même si le code n'est pas mappé**.
  → capte les 6 ER réels de Saint-Louis codés `02` (60 fausses opportunités servies) **sans** ajouter `02` globalement
  (`02` = secteur environnemental à Bras-Panon → un ajout global créerait des fausses écartées ailleurs).
- **VETO** : un libellé explicitement **non-ER** est routé hors famille ER **même codé `05`**, motif honnête, plus jamais « ER ».
  Priorité : VETO → RESCUE/code → EBC/patrimoine/… (inchangé). Le veto applique le même seuil (≥ seuil → HARD, sinon SOFT fort).

### Config — `config/cascade_rules.yaml` (`prescription_plu`)
```yaml
er_libelle_rescue: '(emp[al]{1,4}cement\s*r[ée]serv|emplacement\s*r[ée]serv|\bER\s*n?°?\s*[0-9])'
non_er_libelle_veto:
  - pattern: 'corridors?\s+[ée]cologiques?'          # Saint-Benoît → corridor écologique L.151-23
    motif: "Corridor écologique protégé (…L.151-23 CU) — emprise majoritairement grevée, incompatible…"
  - pattern: 'p[ée]rim[èe]tre\s+(d.attente|de\s+projet)|attente\s+de\s+projet|L\.?\s*151-?41'  # PAPA L.151-41
    motif: "Périmètre d'attente de projet d'aménagement (…L.151-41 CU) — constructibilité gelée temporairement…"
```
**Seuil `er_hard_exclude_pct` : INCHANGÉ (50 %)** — tranché séparément (bande 40-50 % fournie §6 pour la décision Vic).

**Non-régression prouvée** (tests + inline) : les ~5 221 ER captés en `05` restent captés — **typos** (« Empalcement réservé » ×149 Entre-Deux) et **numéros nus** (Étang-Salé) inclus = de vrais ER. EBC (`01`) et patrimoine (`07`) intacts. `tests/test_decisions_1_3.py` : 17/17 verts.

### Contrôles de sûreté (avant re-run)
- RESCUE (libellé ER sous code ≠ 05) ne capte QUE Saint-Louis `02` « Emplacement réservé » ×6 — tous de vrais ER.
- VETO ne capte QUE Saint-Benoît « Corridors écologiques protégés » + Sainte-Marie « Périmètre d'attente L.151-41 » — **aucun vrai ER happé**.
- → le fix cascade est **prouvé confiné à 3 communes** (Saint-Louis, Saint-Benoît, Sainte-Marie).

---

## 1. Décision CORRIDORS Saint-Benoît (Lot 1) — texte PLU à l'appui

**Donnée en base** : prescription « Corridors écologiques protégés », `typepsc 05`, **`stypepsc 04`** (protection au titre de
**L.151-23 CU** — continuités écologiques / TVB), champ `txt = "continuité"`. Il existe en outre une **zone `Acor`**
(sous-type A) libellée : *« Acor : corridors écologiques protégés où la poursuite de l'activité agricole doit se conjuguer
avec la protection de la biodiversité »* (idurba `97410_PLU_20200206`). Pas de PDF règlement 97410 dans le dépôt (basé sur la
donnée GPU + la zone Acor).

**Nature réelle** : protection environnementale de continuité écologique — **PAS un emplacement réservé** (le motif « ER » est faux).

**Sort des 7 parcelles** (6 en zone U : Ub4/Up15 ; 1 en A) : elles sont **aujourd'hui `ecartee` (étage 0)** sous le faux motif ER.
Choix **anti-aberration** (boussole) : **restent ÉCARTÉES**, motif honnête « Corridor écologique protégé (continuité — L.151-23) ».

**⚠️ Déviation assumée et signalée à Vic** : la consigne Lot 1 proposait « soft_flag FORT (restent hors opportunités) ». Or,
mécaniquement (`status.py` + `p_v2/pipeline.py`), **seul un HARD_EXCLUDE pose `ecartee_etage0`** ; un SOFT_FLAG FORT ne fait
que plafonner à `a_creuser` et **REND la parcelle au vivier scoré** → pour 6/7 en zone U, il les **restaurerait** (chaude/
brûlante possible) = exactement l'aberration que la boussole interdit. Pour honorer l'intention « **non restaurées** » ET la
boussole, le corridor produit donc un **HARD_EXCLUDE au motif honnête** (tier inchangé : écartée → écartée). À valider par Vic.

---

## 2. Alignement `matrice-apply` / défauts `q_v2` en dur (Lot 3)

Défauts **mutants** `q_v2` supprimés (défaut `None` → source unique `Q_A_RUN_LABEL`, pattern `build-mvt`) :
`matrice-apply` (cli.py), `matrice-simulate` (cli.py), `apply_convention` + `build_entonnoir` (dryrun.py).

### Grep de contrôle (`q_v2|q_v3_datagap|q_v4_m6a` hors config/tests) — CLASSÉ
**Aucun défaut mutant exécutable ne subsiste.** Le résiduel est **sûr** :
- **Commentaires du fix** (cli.py:368/452/478, dryrun.py:244/289, pipeline.py:217) — documentent l'alignement.
- **Noms de fonctions** `_q_v2_*` (api/app.py, projets.py, ia.py, partners.py, pdf_premium.py) — cosmétiques ; leurs
  **défauts de run sont déjà `Q_A_RUN_LABEL`** (app.py:1068/1223/1311/1415). Renommer = refacto cosmétique risqué, hors scope.
- **Label démo fonctionnel** `q_v2_demo` (events.py, `detect-events`) — run de démonstration légitime (2-runs), pas un défaut mutant.
- **Historique de lignée** en commentaire (`score_v_constants.py:30-33` : q_v2→q_v3_datagap→q_v4_m6a→q_v5_m6b) — à conserver.

*(Grep brut collé en annexe §7.)*

---

## 3. DELTA ventilé (Lot 4)

**Candidat `q_v6_m8`** (cascade île complète 431 663 + score-v2, étage 0 lu sur q_v6_m8 via override env non destructif).
Comparaison au run p_score **servi** `m36-l2f-2026-2026-07-14` (qui lit encore l'étage 0 **q_v2** = le bug ANO-1 non encore atterri).

Candidat : `ecartee 353 945 · a_creuser 72 980 · reserve 3 587 · chaude 1 031 · brûlante 120` (N_e=2 676, seuil D brûlante=1,544).

### Ventilation des 11 865 changements de tier

| Cause | n | Transitions | Statut |
|---|--:|---|---|
| **① ANO-1 — restaurées** | **58** | ecartee→a_creuser 57 · ecartee→reserve 1 | ✅ attendu (dont canary `97406000AL0563` ✓, §4) |
| **② ANO-1 — ATTERRISSAGE (nouvelles écartées)** | **11 718** | a_creuser→ec 10 671 · reserve→ec 961 · **chaude→ec 84 · brûlante→ec 2** | ⚠️ **bien plus que prévu** (voir encadré) |
| **③ St-Louis rescue (net)** | **3** | reserve→ec 3 | ✅ 55/58 déjà écartées par d'autres couches → fondues dans ② |
| **④ Churn recalibration** | **89** | a_creuser→chaude 80 · a_creuser→brûlante 6 · brûlante→chaude 3 | ✅ recalage N_e : comble les 86 fantômes partis |
| **Total** | **11 865** | | **% parc non-écarté = 13,21 %** |

> 🛑 **GARDE-FOU FRANCHI (13,21 % > 10 % ; attendu ~130). STOP — je ne prépare PAS la bascule, j'arbitre à Vic.**
>
> **Cause = ANO-1 sous-estimé, pas une régression.** A-TRAITER-EN-M8.md ne comptait que le sens **restauration** (58 :
> q_v2 exclut / q_v5 non) et oubliait le sens **exclusion** : q_v5_m6b exclut **11 715 parcelles de plus** que q_v2
> (accumulé datagap + M6 — dont A-01 emprise routière ≈1 254, A-02/A-03…). Le p_score servi, gelé sur l'étage 0 q_v2,
> **n'a jamais reflété la cascade servie q_v5_m6b** : c'est précisément l'incohérence interne qu'ANO-1 corrige. Ces
> 11 718 parcelles sont **déjà « exclues » dans leur fiche cascade servie** (q_v5_m6b) — seul leur **badge de tier**
> disait encore a_creuser/reserve/chaude/brûlante. Les **86 fantômes chaude/brûlante** (84+2) = exactement les « 86 »
> annoncés par A-TRAITER. **Aucun mouvement inexpliqué** : ①+②+③+④ = 11 865 = total. Décision d'atterrir (et à quel
> rythme : d'un coup vs par vagues) = **arbitrage Vic**, boussole respectée (tous ces mouvements vont vers ÉCARTER).

**Mon fix mapping (St-Louis/corridors/PAPA) est marginal en volume** (rescue net = 3 ; corridors 7 + PAPA 9 = tier
inchangé, **motif honnête** — vérifié dans q_v6_m8 : « Corridor écologique protégé… L.151-23 » / « Périmètre d'attente…
L.151-41 », plus aucun « emplacement réservé »). **Il supprime des fausses opportunités / faux motifs sans rien
proposer de neuf** — conforme à la boussole. L'essentiel du delta est l'atterrissage ANO-1, indépendant de mon fix.

---

## 4. ANO-1 — confirmation des 58

Les **58** parcelles écartées à tort (q_v2 les exclut, q_v6_m8 non) **retrouvent leur vrai tier** dans le candidat :
57 → `a_creuser`, 1 → `reserve_fonciere`. Le témoin explicite d'A-TRAITER **`97406000AL0563`** : `ecartee → a_creuser` ✅.
Compte exact = 58 (q_v2 étage 0 EXCEPT q_v6 étage 0), conforme.

---

## 5. Golden 32/32 + cohérence 3/3

### Cohérence — **3/3 PASS** ✅
`tests/test_run_serving_coherence.py` : les 3 ancres servies (`Q_A_RUN_LABEL`, front `SOURCE`, `mvt_meta.run_label`)
valent toujours `q_v5_m6b` — **je n'ai touché ni la constante, ni le front, ni les tuiles (pas de `build-mvt` candidat)**.

### Golden — 0/32 « PASS » brut, mais **substance = 29/32 tiers STABLES, 3 changés TOUS expliqués, 0 inexpliqué**
Le golden compare le **dernier run p_score** (donc le candidat pendant le test) à la référence figée sur le run servi.
Les fails bruts sont **2 artefacts non-substantiels + 3 vrais changements expliqués** :

1. **`run_id` metadata** (les 32) : `attendu m36-l2f-…07-14, obtenu q_v6_m8` — trivial, la référence épingle le run servi.
2. **HTTP 429** (rate-limit API fiche pendant le run) : champs `api.fiche.*` = `<absent>` — **artefact de harnais**, pas ma modif.
3. **3 vrais changements de tier** (comparaison DB propre, hors bruit), **tous = atterrissage ANO-1** (étage 0 q_v2 non-exclu → q_v6 exclu) :

   | Témoin | Commune | servi → candidat | Cause |
   |---|---|---|---|
   | 97411000AO0748 | Saint-Denis | a_creuser → ecartee | ANO-1 landing (q_v2 opportunite → q_v6 exclue) |
   | 97413000CD0729 | Saint-Leu | **brûlante** → ecartee | ANO-1 landing (fantôme brûlante ; q_v2 a_creuser → q_v6 exclue) |
   | 97416000CR1351 | Saint-Pierre | reserve → ecartee | ANO-1 landing (q_v2 a_creuser → q_v6 exclue) |

**Aucun des 32 témoins n'est un parcelle St-Louis/corridor/PAPA** → mon fix mapping ne casse aucun golden.
Conformément à la consigne : **je NE modifie PAS le golden** ; les 3 changements sont documentés pour un **re-basage
conscient** à décider par Vic (ils suivront naturellement l'atterrissage ANO-1 quand il sera acté).

---

## 6. Bande ER 40-50 % (décision seuil `er_hard_exclude_pct`, Vic)

**Seuil laissé à 50 % (inchangé).** Liste des parcelles dont la couverture max par un **ER réel** (code 05 ∪ rescue, moins
veto) est dans **[40 %, 50 %)** — **SOFT aujourd'hui, deviendraient HARD (écartées) si le seuil passait à 40 %**.
Lecture sur les données du re-run (pas de 2ᵉ re-run). **Total ≈ 476 parcelles / 19 communes** :

| Commune | n | Commune | n | Commune | n |
|---|--:|---|--:|---|--:|
| Saint-Denis | 101 | Saint-Joseph | 22 | La Plaine-des-Palmistes | 10 |
| Saint-Pierre | 87 | La Possession | 17 | Entre-Deux | 7 |
| Saint-Louis | 62 | Saint-Benoît | 14 | Les Trois-Bassins | 5 |
| Le Tampon | 52 | Salazie | 12 | Sainte-Marie | 4 |
| Saint-Paul | 44 | Cilaos / Le Port / Ste-Suzanne | 10 chacun | L'Étang-Salé | 4 |
| | | | | Bras-Panon 3 · Les Avirons 2 | |

→ Passer le seuil à 40 % **écarterait ~476 parcelles de plus** (à croiser avec la boussole : ces parcelles sont grevées
à 40-50 % par un ER — le promoteur perd 40-50 % de l'emprise). Décision seuil = Vic (Lot 4 séparé).

---

## 7. Annexe — grep `q_v2|q_v3_datagap|q_v4_m6a` hors config/tests (52 résiduels, classés)

`grep -rn 'q_v2|q_v3_datagap|q_v4_m6a' src/labuse/ | grep -v /tests/ | grep -vi test_` → **52 lignes, 0 défaut mutant** :

| Catégorie | n | Sûr ? |
|---|--:|---|
| Commentaires du fix (ANO-1 / M8a / correctif M5) | 6 | ✅ documentent l'alignement |
| **Noms de fonctions** `_q_v2_*` (app.py, projets.py, ia.py, partners.py, pdf_premium.py) | 24 | ✅ leurs **défauts de run sont déjà `Q_A_RUN_LABEL`** (app.py:1068/1223/1311/1415) ; renommer = cosmétique risqué, hors scope |
| Label démo `q_v2_demo` + `detect-events` (2-runs légitime) | 10 | ✅ run de démonstration fonctionnel |
| Historique de lignée (`score_v_constants.py:30-33`) | 3 | ✅ à conserver (q_v2→…→q_v5_m6b) |
| Docstrings/commentaires divers | ~9 | ✅ cosmétique |

**Les 4 défauts MUTANTS exécutables sont supprimés** : `matrice-apply`, `matrice-simulate` (cli.py), `apply_convention`,
`build_entonnoir` (dryrun.py) → défaut `None` → `Q_A_RUN_LABEL` (source unique).

---

## 🛑 STOP — décisions demandées à Vic (aucune bascule, aucun merge)

1. **Atterrissage ANO-1 = 11 718 écartées (pas ~130)** — garde-fou franchi (13,21 %), **tout expliqué** (aucune régression).
   C'est l'alignement du p_score sur la cascade servie q_v5_m6b, jamais fait depuis q_v2. **Décision : atterrir d'un coup,
   ou par vagues ?** (ex. isoler A-01 emprise routière). Rien ne bascule tant que tu n'as pas tranché.
2. **Corridors Saint-Benoît** : gardés **écartés** (HARD honnête, pas soft_flag — sinon restaurés = aberration). Valides-tu ?
4. **Golden** : 3 témoins changeront de tier au re-basage (tous ANO-1 landing). **Re-baser le golden** quand tu actes l'atterrissage
   (je ne l'ai pas touché). Golden pollué par HTTP 429 (rate-limit) + `q_v3_datagap` en dur (périmé) → **à moderniser** (signalé).
5. **Seuil ER** : 40 % écarterait +476 parcelles (§6). À trancher (Lot 4 séparé).

### État laissé en base
- **Run servi INCHANGÉ** : cascade `q_v5_m6b`, p_score `m36-l2f-2026-2026-07-14` (restauré comme dernier), tuiles/front intacts.
- **Candidat CONSERVÉ pour inspection** : cascade `dryrun_parcel_evaluations[q_v6_m8]` + p_score `parcel_p_score_v2[q_v6_m8]`
  (NON servi). Reproductible. Override `LABUSE_ETAGE0_RUN` = défaut `Q_A_RUN_LABEL` (aucun impact prod).
