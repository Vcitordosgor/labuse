# RAPPORT-FIX-2 — correctifs des écarts CHASSE-INVARIANTS-2

> Branche `fix/chasse-invariants-2` depuis main (audit mergé, HEAD de départ `2da4e98f`), worktree
> `labuse-fix-ci2`, API locale 8793. Base servie **q_v18 / run_seq 15**. 15/10/2026. **Ne pas merger :
> prêt à merger.** 4 commits (3 points du mandat + le recadrage du banc). Lecture seule côté données
> (aucune réécriture des sources brutes ; seule une fonction SQL idempotente est ajoutée).

## Les 3 points, un par un

### (1) Hauteurs LiDAR « dalle » — une seule borne à la source, lue partout
Une mesure `faitage_m`/`egout_m` (table `batiment_hauteur_lidar`) **≤ 0** (MNT au-dessus du bâti :
remblai/débord/glitch vertical) ou **au-delà d'un plafond réaliste pour La Réunion** n'est jamais une
hauteur : elle n'est **plus jamais servie** ni utilisée par le calcul.
- **La borne, une seule fois** : fonction SQL `labuse_hauteur_lidar_m(real)` (`models.py`, câblée dans
  `create_all`, idempotente, `CREATE OR REPLACE` sans verrou). Ramène à **NULL** toute valeur ≤ 0 ou
  > **60 m**.
- **Le plafond, justifié** : le plus haut bâtiment de l'île est un R+15 (~45–50 m) ; la plus haute
  mesure LiDAR plausible observée est **55 m** ; entre 60 m et l'infini : **0 bâti réel**, seulement les
  **2** aberrations de coordonnée à **53 401 m**. 60 m laisse donc toute hauteur réelle passer et ne
  coupe que les artefacts (58 faîtages : 56 ≤ 0 + 2 > 60 ; 1 507 égouts ≤ 0).
- **Lue partout** : la fiche (`hauteur_lidar_servie`), l'outil Gabarit (`gabarit.py`), l'extrusion 3D
  et le **filtre hauteur** (`app.py`), et le **CALCUL** — scoring `_f_bati` (`score_labuse.py`) et
  résiduel surélévation (`residuel.py`). Plus aucune lecture brute de `faitage_m`/`egout_m`.
- **Rendu** : la fiche sert `hauteur_faitage_lidar_m = null` / `hauteur_egout_lidar_m = null`
  (« hauteur non mesurée ») ; le Gabarit retombe sur la hauteur BD TOPO ou « non mesurée » ; l'extrusion
  3D ne sert jamais 53 km.

**(1) change-t-il le calcul servi ?** — **Le score et la SDP SERVIS (q_v18, précalculés) sont
INCHANGÉS** : ce run est figé, la borne n'y touche pas. Changent : (a) **immédiatement**, le rendu live
(fiche/Gabarit/3D/filtre hauteur) — l'aberrant devient « non mesurée » ; (b) **au prochain run (q_v19)**,
le calcul cessera d'ingérer les hauteurs aberrantes — **≤ 58 parcelles** (faîtage → scoring `_f_bati`)
et **≤ 1 507** (égout → résiduel surélévation) — repli BD TOPO, **strictement une amélioration** (on
remplace du bruit par une mesure absente, jamais l'inverse).

### (2) DPE à année de construction aberrante → « année inconnue »
Une `annee_construction` ADEME **< 1800 ou future** (1 DPE à **1761**) n'est jamais servie comme année.
- **Borne à la source** (le seul lecteur qui sert cette donnée) : le builder `parcel_filtre_bati`
  (`filtre_bati.py`) retire du `max(annee_construction)` les années hors `[1800, année courante]` via un
  `FILTER` ⇒ **NULL** ⇒ étiquette « Absent » / motif « d'année Absente » = « année inconnue » (le chemin
  NULL était déjà géré en aval).
- **Garde au service** (`_m28_badges`, `app.py`) : la même borne au rendu, pour que l'aberrant ne soit
  pas servi même **avant** la reconstruction nocturne du cache.
- La source brute `dpe_records` n'est **pas** réécrite (donnée ADEME ; anomalie amont documentée).
- **Preuve** (`97418000AW0434`) : `dpe_records.annee_construction = 1761` → fiche
  `filtre_bati.annee_construction = null`, `annee_etiquette = "Absent"`.

### (3) banc2 au job de nuit `coherence-banc` (+ `--tout` hebdomadaire)
Le banc des **1 000+ invariants générés** (vague 2) rejoint la garde de nuit :
`jobs_impl.coherence_banc` appelle désormais `banc2.executer()` **après** la cohérence et les gardes
CHASSE-DONNÉES — le sous-ensemble rapide **`--nuit`** chaque nuit (SQL île + moteur, ~4 min, sans les
deux boucles API cadencées F2/F5), l'intégrale **`--tout`** le **dimanche** (~18 min). Le résultat entre
dans `ctx.compte` (`banc2_ok/ecart/skip/regles/duree`) ; **0 règle = passage non probant** (échec
bruyant). `banc2` refactoré : `executer(mode, api, base)` rend un bilan réutilisable, `main()` est un
mince emballage CLI. `jobs.py` : la raison de `coherence-banc` est mise à jour.

## Le banc rejoué (recadrage « vérité servie »)
Comme FIX-1, les gardes F1 qui mordaient sur les colonnes **brutes** visent désormais la valeur
**SERVIE** (les sources ne sont pas réécrites) : hauteurs via `labuse_hauteur_lidar_m(col)`, année DPE
via un contrôle de la fiche servie (`_check_dpe_annee_servie`). Les **3 écarts FAUX-CLIENT LiDAR**
passent au **vert** ; l'anomalie source ADEME n'est plus servie.

**banc2 `--tout` AVANT le fix** : base 36 OK · **3 ECART** (E-09/E-03/E-13, q_v19-pending) + **4 ECART F1**
(LiDAR ×3 + DPE 1761) = 7 ECART.
**banc2 `--tout` APRÈS le fix** : **1071 OK · 3 ECART · 0 SKIP** (1 074 règles, ~17 min). F1 passe à
**238 OK · 0 ECART** (les 4 écarts LiDAR/DPE éliminés) ; F2 59 · F2b 253 · F3 72 · F4 218 · F5 162 ·
F6 33 — **tous 0 ECART**. Les **3 ECART** restants sont **uniquement** la BASE vague-1 (E-09/E-03/E-13,
q_v19-pending). Le banc est passé de **7 → 3 écarts**, les 3 restants hors périmètre de ce fix.

Les 3 écarts BASE restants (E-09 `surface_terrain_m2` NULL, E-03/E-11 union PPR, E-13 sous-densité) sont
les correctifs **« calcul »** de FIX-1 qui n'entrent au vert qu'au **run final q_v19** — attendus,
documentés (`RAPPORT-FIX.md`), **hors du périmètre de ce fix**.

## Vérifications
- **Tests unitaires** (hook, sans base) : **2474 passed · 48 skipped · 0 échec** — dont
  `tests/test_filtres_bati.py` recadré sur le filtre hauteur borné.
- **Front** : `tsc -b` **0** · `vitest` **256/256**.
- **Captures** `captures/chasse-inv-fix2/` : `avant_apres.json` (LiDAR + DPE, brut → servi) et
  `banc2_apres.txt` (le banc rejoué).
- **Lecture seule données** : aucune écriture ni réécriture de source ; seule `labuse_hauteur_lidar_m`
  (fonction SQL, additive, idempotente) est posée. Rien sur le VPS. **Ne pas merger.**
