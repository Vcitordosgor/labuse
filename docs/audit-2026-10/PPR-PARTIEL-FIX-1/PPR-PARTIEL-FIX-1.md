# PPR-PARTIEL-FIX-1 — étape B : rendre visible la partie hors zone rouge

**Fix d'affichage, lecture seule du scoring.** Branche `fix/ppr-partiel-b`, worktree `~/Desktop/labuse-pprb`,
base `origin/main` (`31e58719`). Suite de [`PPR-PARTIEL-1`](../PPR-PARTIEL-1/PPR-PARTIEL-1.md). Ports API **8718** /
Vite **5918**. **Aucun run, aucune bascule, aucune écriture dans les tables de résultats.**

> **En une phrase.** Les parcelles U/AU qui *touchent* une zone rouge PPR et sont servies à 0 par prudence
> gardent souvent des milliers de m² **hors** rouge. L'étape B les **signale** — badge « Partie hors zone
> rouge : X m² (Y %) — à étudier » sur la fiche, le Dossier et le Copilote — et **supprime le libellé faux**
> « terrain trop étroit une fois retirée la zone rouge » là où il ment, sans toucher au score, à la bande, à
> la SDP servie ni à aucun run. Le recalcul réel reste l'étape A.

---

## 1. La fonction serveur — source unique (lot 1)

`src/labuse/faisabilite/db.py`
- **`surface_hors_ppr_rouge(session, parcel_id, *, faisa=None) -> dict | None`** (`db.py:834`)
- **`phrase_hors_ppr_rouge(hors) -> str`** (`db.py:877`) — le libellé client, source unique du texte.
- **`SEUIL_HORS_PPR_ROUGE_M2 = 200.0`** (`db.py:819`).

Elle rend `{"hors_rouge_m2": int, "pct": int}` (pct = part **de la parcelle** hors rouge) ou `None`. Calculée
**à la demande** (pas de run, pas de stockage), **servie seulement si** :
1. la parcelle **touche du rouge** ET sa **SDP servie est 0 pour ce motif** — c.-à-d. le moteur conclut
   `cause == terrain_exigu` **et** `exigu_raison == ppr_rouge` (la chaîne `builder.py:334-339 → db.py →
   engine.py → residuel.py:136` de l'audit). Tout autre 0 (bâti saturé, zone A/N, emplacement réservé) n'est
   pas ce gisement et ne reçoit **rien** ;
2. le reste hors rouge atteint **200 m²** (en deçà, rien : le terrain est réellement exigu, l'ancien libellé
   reste vrai).

Le découpage réutilise **le rouge-seul déjà calculé par le gabarit** (`builder.py:348-365` :
`ST_ClipByBox2D → ST_MakeValid → ST_Union → ST_Intersection`) — aucun calcul de masse, aucune enveloppe. C'est
du **foncier BRUT** : reculs non appliqués, ce n'est **pas** une SDP ni un certificat de constructibilité (le
libellé le dit). Le découpage est isolé dans un **SAVEPOINT** (`begin_nested`) : une géométrie invalide / des
PPR superposés pathologiques rendent `None` (rien affiché), jamais un chiffre douteux — et le cas est compté
au rapport (§4).

**Le branchement (une fonction, trois lecteurs via le payload fiche)** — `potentiel_transformation.hors_ppr_rouge` :
- **Fiche** : `app.py:_potentiel_transformation_block` appelle la fonction (`app.py:5924`), pose le champ
  (`app.py:6037`) et **remplace le libellé faux** par `phrase_hors_ppr_rouge` quand il y a ≥ 200 m²
  (`app.py:5934-5936`).
- **Dossier PDF** : le §potentiel l'imprime (`verdict_potentiel` lit `libelle`) ; le §risques ajoute la note
  (`miroir.py:1129-1136`) — même source, même chiffre.
- **Copilote** : réutilise `verdict_potentiel` (`copilote_v2/resume_fiche.py`) → même phrase, même chiffre.

---

## 2. Les témoins (mesure rejouable)

`docs/.../harnais/verif_lot1.py` sur la base `labuse`, run servi q_v16 :

| IDU | Commune · zone | touche rouge | parcelle m² | rouge m² | hors rouge m² / % | badge | libellé servi |
|---|---|:--:|---:|---:|---:|:--:|---|
| **97409000AY0786** | Saint-André · UC | oui | 4 877 | 145 | **4 732 / 97 %** | **OUI** | « Parcelle touchée par une zone rouge PPR — droits servis à 0 par prudence ; partie hors zone rouge : **4 732 m²**, à étudier. » |
| **97415000HL0001** | Saint-Paul | oui | 17 079 | 4 550 | **12 529 / 73 %** | **OUI** | idem · **12 529 m²** (gros stock, remplace IR0368 — voir ci-dessous) |
| **97411000IR0368** | Saint-Denis · Uma | oui | 57 554 | 1 314 | 56 241 / 98 % | **NON** | « Non retenue — terrain trop étroit une fois retiré **l'emplacement réservé**. » |
| **97409000BM0449** | Saint-André | oui | 213 | 33 | 180 / 84 % (**< 200**) | **NON** | « Non retenue — terrain trop étroit une fois retirée la zone rouge du PPR. » (vrai ici) |
| **97409000AB0010** | Saint-André | oui | 22 902 | 22 902 | **0** (100 % rouge) | **NON** | libellé rouge intégral (rien hors rouge) |
| **97411000BZ1065** | Saint-Denis | non | — | — | — | **NON** | inchangé (parcelle calculée) |

**Le cas IR0368 est une découverte, pas un échec.** L'audit l'avait listée « top stock » (56 241 m² hors rouge
par la géométrie seule). Mais le moteur la sert à 0 **pour un emplacement réservé** (chemin legacy, gabarit
incomplet : `_assiette_gabarit` rend `None` → `db.py:567` `er_a ≥ 0.9·base` → `emplacement_reserve`), **pas**
pour le PPR rouge. Sous la règle même du mandat (« SDP servie 0 **pour ce motif** »), elle ne reçoit donc pas de
badge — et c'est **honnête** : on ne colle pas « à étudier hors rouge » sur un terrain réservé à un projet
public. C'est exactement le garde-fou « accès / unité du terrain » que l'audit réclamait pour l'étape A.
`97415000HL0001` la remplace pour illustrer un **gros gisement ppr_rouge réel**.

### Portée du badge sur le gisement de l'audit
Classification d'un échantillon pseudo-aléatoire de **240 parcelles** du gisement « > 500 m² hors rouge, U/AU »
(`harnais`, moteur réel) : **234 / 240 = 97,5 % sont `terrain_exigu / ppr_rouge` → badgées** ; 5 sont
`emplacement_reserve` et 1 `reculs` (exclusions honnêtes, comme IR0368). Le badge couvre donc l'**essentiel** du
gisement de l'audit (≈ 3 790 des 3 888 parcelles > 500 m²) tout en **n'étiquetant jamais** une parcelle dont le 0
tient en réalité à un ER ou à une portion U/AU minuscule. Les ~2,5 % restants relèvent de l'étape A.

**Captures** `captures/avant/` et `captures/apres/` : `AY0786` tuile SDP + tiroir Potentiel (badge « 4 732 m²
(97 %) »), le libellé faux « avant » vs la vérité « après » ; `IR0368` (pas de badge), `BM0449` (< 200, pas de
badge), `AB0010` (100 % rouge, pas de badge).

---

## 3. Preuve « 0 écart » — l'étape B ne touche pas au scoring

`docs/.../harnais/verif_lot3_zero_ecart.py` → `preuve_zero_ecart.txt`. Sur **54 parcelles** (50 du rapport
d'audit + 6 témoins) : on DUMP l'état servi (`score_labuse` — toutes versions —, `parcel_residuel`), on
**exerce** les trois chemins qui calculent désormais le badge (`_q_v2_fiche`, `construire("dossier", fiche=…)`,
`resume_parcelle`), on re-DUMP et on exige un diff vide.

> **écarts score / bande / SDP / cause avant↔après : 0 / 54.**

Générer la fiche, le Dossier et le Copilote (qui lisent `surface_hors_ppr_rouge`) **n'écrit rien** : la fonction
est en lecture seule (SELECT + SAVEPOINT relâché). Le badge **n'apparaît ni en listing ni sur la carte** (valeur
non stockée ; `cause_libelle` de liste ne reçoit ni `exigu_raison` ni `hors_ppr_rouge`) — c'est l'étape A qui
décidera de la servir en masse.

### Verrou écran = PDF
`docs/.../harnais/verrou_ecran_pdf.py` : le chiffre du badge servi à la fiche est **le même** que celui imprimé
au Dossier. `AY0786 → 4 732 m²` et `HL0001 → 12 529 m²` figurent chacun **2 fois** dans le HTML du Dossier
(§potentiel + §risques), identiques au badge écran. **VERROU OK.**

---

## 4. Robustesse du découpage

Dans l'échantillon des **234 parcelles badgées**, **0 échec de découpage** (toutes rendent une surface valide).
L'audit QV16 relevait 0 géométrie invalide sur l'île. Le mécanisme de garde est néanmoins en place : exception
PostGIS (géométrie invalide, PPR superposés) → `None` (rien affiché), jamais un chiffre douteux. Nombre de cas
où le découpage a échoué : **0 observé**.

---

## 5. Tests & non-régression

- **Unitaire** `tests/test_ppr_partiel_fix1.py` (6 tests, sans base, par injection) : parcelle ppr_rouge avec
  **2 000 m²** hors rouge → badge `{2000, 80 %}` ; même parcelle **150 m²** → rien ; **seuil 200 exact** (200→
  servi, 199→rien) ; **sans rouge** (motif ≠ ppr_rouge) → rien ; **découpage qui lève** → rien ; phrase unique
  (chiffre présent, jamais « constructible »). **6 passed.**
- **tsc** `-b` : 0 erreur. **vitest** : **243 passed**.
- **pytest ciblé** : `test_fiche_potentiel_cause`, `test_ppr`, `test_residuel`, `test_exigu_grandes`
  (17 passed, 2 skip base-app) ; `test_dossier`, `test_exports2_lot1`, `test_copilote2_fiche`
  (15 passed, 5 skip témoins absents). Aucune régression.

---

## 6. Ce que l'étape A devra trancher

1. **La règle de déduction (le fond).** Aujourd'hui, dès qu'une parcelle touche du rouge, le gabarit re-soustrait
   l'**enveloppe réglementaire entière** `pm1` (rouge **+** bleu) au lieu du **rouge seul** (`builder.py:405-407`,
   alors que le rouge-seul est déjà découpé juste au-dessus, `:348-365`). L'étape A doit **retirer cette
   sur-déduction** quand la parcelle touche du rouge, et calculer l'emprise sur la **portion hors rouge**.
2. **Cohérence cascade ↔ gabarit.** La cascade pose `HARD_EXCLUDE` « PPR zone rouge inconstructible » pendant que
   le gabarit vaudrait > 0 → l'incohérence que la décision antérieure de Vic évitait en servant **« 0 plutôt
   qu'incohérence »**. À traiter **ensemble** : en U/AU partiellement rouge, verdict **SOFT_FLAG** « constructible
   sur la partie hors zone rouge », pas `HARD_EXCLUDE`.
3. **Garde-fou accès / tenant (obligatoire avant le score).** Les 588 ha sont du **brut** : reculs non appliqués.
   Vérifier la **contiguïté** (plus grand fragment, `ST_Dump`) et l'**accès voirie** de la portion saine — un
   reste grand mais enclavé par le rouge en façade est inexploitable.
4. **Les cas que l'étape B a révélés.** Dans le gisement géométrique de l'audit, ~2,5 % des parcelles sont
   servies 0 pour un **emplacement réservé** (IR0368) ou parce que leur **portion U/AU est minuscule** (à cheval
   A/N). L'étape A doit les **distinguer** du vrai gisement PPR — ne jamais servir « hors rouge » en masse sur une
   parcelle bloquée par un ER ou majoritairement A/N.
5. **Recalcul aval.** Re-run résiduel + score/bandes (SCORING-9, bandes gravées à revérifier) + re-constitution
   des témoins (AY0786/AX0047 cessent d'être « périmés »). Le CPU du run est quasi gratuit (géométrie rouge déjà
   produite) ; le coût est la **validation aval** et le garde-fou accès.

---

## Annexe — harnais (rejouable)

Base `labuse` (`LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse`), `PYTHONPATH=src`,
venv `~/Desktop/labuse/.venv`. Lecture seule, aucune écriture.
- `harnais/verif_lot1.py` — les 6 témoins (cause · exigu · hors rouge · badge).
- `harnais/verif_lot3_zero_ecart.py` — preuve 0 écart (dump avant/après sur 54 parcelles) → `preuve_zero_ecart.txt`.
- `harnais/verrou_ecran_pdf.py` — verrou écran = PDF (chiffre fiche == chiffre Dossier).
- Un commit par lot : lot 1 (fonction `db.py`), lot 2 (branchement fiche/Dossier/Copilote + libellé), lot 3
  (preuve). **Rien n'est poussé.** Arrêt propre : ports 8718/5918 libres, 0 transaction idle-in-transaction.
