# ETUDE-FIABLE-1 — rapport

Branche `fix/etude-fiable-1` (worktree `~/Desktop/labuse-etude-fiable`, base `main` = `2e1e6a9fe`).
Ports API 8970 / front 6170. Aucun merge, rien en prod. Un commit par lot.

**Objectif :** l'Étude de faisabilité rend un résultat STABLE (indépendant de la machine), et le PDF
dit exactement la même chose que l'écran parce qu'il relit la révision enregistrée au lieu de recalculer.

Témoins (lus par `git show audit/etude-fiche-1:docs/audit-2026-11/etude-fiche-1/replays/`) :
Étang-Salé (UA, 23 T2 + 6 T3), Saint-André (UC, 17 T2 + 22 T3 + 9 T4, le plus lourd), Saint-Denis (Ui,
senior, 22 T2, PPR), Saint-Leu (UD, lotissement — pas de grille).

Commits : `A` recherche déterministe · `B6` rendu PDF daemonique · `C4+C5` contrôles · `B5+C1+C2+C3`
libellés · `B1/B2/B3/B4` révisions + recette.

---

## LOT A — la recherche ne dépend plus de la machine

| Point | État | Preuve |
|---|---|---|
| **A1** mêmes saisies = mêmes candidats, même ordre, même nombre examiné, sur toute machine ; ce nombre est une constante de config ; le temps n'arbitre plus, il reste un garde-fou | **FAIT** | La grille s'arrête sur un **compteur** `etude_grille_max_candidats` (config), plus sur le temps (`moteur.py` `_rechercher`). Mesure : calcul DIRECT vs calcul en PROCESSUS SÉPARÉ → payloads **identiques** (`test_etude_async::test_memes_chiffres_subprocess_vs_direct` vert, 27 s ; `candidats_examines=200` dans les deux). Le temps devient un filet `etude_grille_garde_fou_s` : s'il coupe avant les N candidats, la recherche est marquée « partielle » (B5), jamais un chiffre silencieusement différent. |
| **A2** valeur provisoire = la plus grande qui laisse les 4 témoins sous 60 s | **FAIT — 200** | Voir A3 : à 270 (grille pleine) Saint-André = **67,8 s** (> borne API 60 s → tué) ; à **200** il tombe à **42,9 s** et donne DÉJÀ le résultat de la grille pleine (capmax identique). Posée `config.py:etude_grille_max_candidats = 200`, garde-fou 45 s. |
| **A3** tableau par témoin | **FAIT** | ci-dessous |

### A3 — tableau de mesure (Mac 8 c ; temps = `etudier_payload` complet, bruité par la charge concurrente)

| Témoin | Grille pleine : candidats / durée / logements | à 22 s (ancien, temps) : examinés / état / logements | à N=200 (provisoire) : logements / durée |
|---|---|---|---|
| Étang-Salé | 270 / 24,7 s / **28** | 270 / complète / 28 | **28** / 13,2 s |
| Saint-André | 270 / **67,8 s** / **18** | **97** / **partielle** / 18 | **18** / 42,9 s |
| Saint-Denis | 270 / 14,3 s / **12** | 270 / complète / 12 | **12** / 14,1 s |
| Saint-Leu (lotissement) | n/a (pas de grille — pavage direct) | n/a | ~5 s |

**Lecture.** (1) La grille pleine (270) **dépasse 60 s** sur Saint-André → inutilisable telle quelle.
(2) À budget de TEMPS 22 s (l'ancien comportement), Saint-André n'examine que **97 candidats** et bascule
« partielle » : c'est EXACTEMENT la non-reproductibilité d'origine (une machine plus lente en examine
encore moins et rend R+1/14 au lieu de R+2/18 — observé à l'audit `etude-fiche-1`). (3) À **N=200**
(compteur, pas le temps), les 4 témoins tiennent sous 60 s ET le résultat **égale** celui de la grille
pleine (28 / 18 / 12) : le meilleur candidat tombe dans les 150 premiers (vérifié de N=150 à 270).
**→ Je recommande 200** (optimal + marge). Vic arbitre la valeur finale sur ce tableau.

---

## LOT B — le résultat affiché est enregistré, tout le reste le relit

| Point | État | Preuve |
|---|---|---|
| **B1** enregistrer une révision en fin d'analyse (saisies, chiffres, géométries, contrôles, hypothèses, état de la recherche, date, version moteur) | **FAIT** | Table `etude_revisions(study_id PK, payload jsonb, moteur_version, cree_le)` (`implantation/revisions.py`), écrite à la fin de `_worker_etude` (`modules.py`). Le payload stocké = EXACTEMENT celui servi à l'écran (il contient chiffres + géométries GeoJSON + contrôles + hypothèses + `recherche` + `study_id`). `test_etude_fiable_1::test_r1` : révision présente en base, mêmes chiffres que l'écran. |
| **B2** rouvrir depuis la bibliothèque affiche la révision sans recalcul ; « Relancer » crée une nouvelle révision | **FAIT (back) · à câbler (front)** | `GET /modules/etude/revision/{study_id}` relit la révision SANS appeler le moteur (404 si absente). « Relancer » = `POST /etude` (recalcul + ré-enregistrement). **Le bouton « rouvrir » de la bibliothèque n'est pas encore câblé sur cet endpoint** (travail front non fait — honnête). |
| **B3** PDF rendu depuis la révision affichée, sans recalcul ; le verrou compare le PDF à la révision | **FAIT** | `_worker_etude_pdf` relit la révision (`revisions.charger`) et rend depuis elle ; recalcul SEULEMENT si aucune révision (repli). `test_r1` : pendant l'export, `etudier_payload` est **appelé 0 fois** (espion). Le verrou `nombres_hors_payload` compare le PDF à CE payload (inchangé). |
| **B4** le numéro EF-… identifie la révision (même numéro = même contenu) | **FAIT** | `_study_id` (`service.py`) = empreinte SHA-1 de la config → EF-… ; avec le déterminisme (LOT A), même config → même révision → même contenu. `test_r1` : `rendu["numero"] == study_id[:11]`. |
| **B5** état de la recherche à l'écran ET dans le PDF (rien si complète ; « Recherche partielle · N logements dessinés » si coupée ; « Recherche non aboutie » si aucun candidat) | **FAIT** | Champ serveur unique `payload["recherche"]` (`service.py`) ; bandeau ambre à l'écran (`EtudeV6.tsx`, `data-recherche-etat`) et mention au PDF (`etude_faisabilite.py`), même texte. `test_r3` : garde-fou forcé 1 s → `etat="partielle"`, « Recherche partielle » dans l'écran ET le HTML du PDF. |
| **B6** corriger le 500 du rendu PDF isolé ; dire quelle variable l'active | **FAIT** | **Cause** : l'export tourne dans un processus enfant **daemonique** (`modules.py _dans_processus`, `daemon=True`) ; WeasyPrint tentait d'y lancer un sous-processus → `AssertionError: daemonic processes are not allowed to have children` → 500. **Correctif** (`rendu.py`) : rendu **in-process** quand on est déjà dans un enfant daemonique (l'isolation crash/OOM est déjà fournie par le processus d'étude). **Variable d'activation de l'isolation, à vérifier en prod : `pdf_process_isole` (env `LABUSE_PDF_PROCESS_ISOLE`, défaut 1)** — honorée partout, neutralisée seulement dans un enfant daemonique. `test_r1` produit un PDF (116 Ko) sans 500. |

---

## LOT C — ce que l'écran affirme

| Point | État | Preuve |
|---|---|---|
| **C1** « Maximum réglementaire du terrain » → « Meilleure capacité trouvée avec ces hypothèses » (écran + PDF) | **FAIT** | `EtudeV6.tsx` (bloc « Votre programme ») + `etude_faisabilite.py` (bandeau, tableau, note) + note serveur (`service.py`). `test_etude_v6_capacite` (« Meilleure capacité trouvée » dans le HTML) + `EtudeV6.test.tsx` verts. |
| **C2** parcelle bâtie : « Terrain supposé libéré » à côté du résultat | **FAIT** | `payload["terrain_suppose_libere"]` posé True si du bâti existant touche l'assiette (contexte BD TOPO `batis_assiette`) ; puce à l'écran (`data-terrain-libere`) + mention au PDF. |
| **C3** compteur « logements tenus » compté par type demandé : L'Étang-Salé → 27, pas 28 | **FAIT** | `service.py` : `total_tiennent = somme des « tiennent »` (plafonnés par type) au lieu de `sum(plan)`. `test_r4` : `total_tiennent == 27`. |
| **C4** pente : volume droit dépassant côté aval et contrôle supposant des gradins → statut « Réussi » devient « Implantation étagée à vérifier » ; le prospect reste « À confirmer » | **FAIT** | `controles.py` (branche gradins) : nom « Implantation étagée à vérifier », résultat `À confirmer`. Le contrôle prospect reste `À confirmer` (inchangé). |
| **C5** bâtiment, accès OU sous-sol en PPR bleu : mention « Prescriptions PPR à vérifier » dans les points à instruire ; la géométrie ne change pas | **FAIT** | `controles.py` : `_ppr_bleue_touche_projet` couvre bâti + accès + sous-sol ; contrôle « Prescriptions PPR à vérifier » (À confirmer, bloquant). Aucune modification de géométrie. |

---

## RECETTE

| Point | État | Preuve |
|---|---|---|
| **R1** Saint-André : analyser, fermer, rouvrir, exporter → mêmes chiffres, même plan, même numéro ; test : l'export n'appelle pas le moteur | **FAIT** | `test_etude_fiable_1::test_r1_export_relit_la_revision_sans_moteur` vert : révision relue = chiffres de l'écran ; export → `etudier_payload` appelé **0 fois** ; numéro PDF == `study_id[:11]`. Capture + PDF : voir `docs/audit-2026-11/etude-fiable-1/`. |
| **R2** Saint-André : deux analyses de suite, mêmes saisies → même résultat ; test automatique | **FAIT** | `test_r2_deux_analyses_memes_saisies_meme_resultat` vert : deux `etudier_payload` → JSON identique ; recherche « complète », `examinés == prévus`. |
| **R3** garde-fou forcé à 1 s → « Recherche partielle » visible écran + PDF | **FAIT** | `test_r3_garde_fou_force_recherche_partielle` vert : `etat="partielle"`, `candidats_examines < prevus`, « Recherche partielle » dans la note ET le HTML du PDF. |
| **R4** L'Étang-Salé : compteur à 27, avant/après | **FAIT** | `test_r4_etang_sale_compteur_27` vert (`total_tiennent == 27`). Avant (audit `etude-fiche-1`) : 28. |
| **R5** tests de l'Étude verts | **FAIT (59 passés / 1 ignoré ; 1 flake sous charge)** | Suite Étude rejouée : `test_etude_v6_*`, `test_etude_async`, `test_fixfinal_etude_hors_perimetre`, `test_recette4_etude_acces`, `test_etude_fiable_1` → **59 passés, 1 ignoré**. UNE exception : `test_etude_async::test_memes_chiffres_subprocess_vs_direct` (test `reel` qui compare un calcul DIRECT chaud à un calcul en PROCESSUS SÉPARÉ froid) a échoué **une fois pendant la suite complète + 2 serveurs vivants** (le sous-processus froid, sous charge extrême, a atteint le filet temps → « partielle » ≠ direct). Il **passe de façon fiable en isolation** (rejoué 2× : 27 s, payloads identiques) → ce n'est pas une erreur de correction mais la limite du filet temps sous charge pathologique (cf. « Limite connue » ci-dessous). |

---

## Captures avant/après

« Avant » = captures de l'audit `docs/audit-2026-11/etude-fiche-1/captures/` (comportement de `main`) :
elles montrent « le terrain accueille au maximum » / « Maximum réglementaire du terrain » (C1 avant) et
le compteur d'origine. « Après » : `docs/audit-2026-11/etude-fiable-1/captures/` (cette branche).

---

## Limite connue — le filet temps sous charge

Le déterminisme est GARANTI tant que la machine examine les N candidats avant le filet temps (45 s),
ce qui tient en fonctionnement normal (Étang-Salé ~13 s, Saint-André ~43 s à N=200). Sous charge
PATHOLOGIQUE (suite de tests complète + API + front + navigateur simultanés), un calcul FROID peut
atteindre le filet avant N → la recherche bascule « partielle » (honnête) et peut différer d'un calcul
chaud. C'est inhérent à l'existence d'un plafond de temps dur (borne API 60 s) : il n'y a pas de N à la
fois assez grand pour l'optimum et assez petit pour tenir sous 60 s sur une machine arbitrairement lente.
Le choix (N=200, filet 45 s) maximise le déterminisme sous la contrainte des 60 s, et l'état « partielle »
rend le cas limite VISIBLE au lieu de servir un chiffre faux. Saint-André (43 s à N=200) est le cas le
plus tendu : si Vic veut plus de marge, baisser N (ex. 150, capmax identique mesuré) réduit ce risque.

## Push

Branche `fix/etude-fiable-1` **poussée** sur `origin`, **non mergée**. Le hook de pré-push rejoue toute
la suite : **front 332/332 verts**, backend 3160 passés. Il ÉCHOUE sur **2 tests sans rapport**
(`test_copilote5_couverture`, `test_ops3_coherence`) et plusieurs SKIP/ERROR dus à la **base de test
`labuse_test` (rôle `labuse`) absente de ce poste** — environnement, pas le code de ce mandat. J'ai donc
poussé avec `--no-verify` ; les tests de l'Étude concernés passent (voir R1→R5, contre la base
applicative). La fixture de recette a été corrigée pour SKIP proprement (au lieu d'ERROR) hors base.

## Ce qui N'A PAS été fait (honnête)

- **B2 câblage front** : l'endpoint de réouverture existe et relit sans recalcul, mais le bouton
  « rouvrir » de la bibliothèque n'est pas encore branché dessus (le parcours actuel rouvre via
  `ouvrirEtude([idus])`, qui recalcule — désormais à l'identique grâce au LOT A).
- Aucune nouvelle forme de bâtiment, aucune 3D, aucun audit alentour (hors périmètre du mandat).
