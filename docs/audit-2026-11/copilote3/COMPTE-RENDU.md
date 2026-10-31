# COPILOTE-3 — compte-rendu

- **Branche** : `fix/copilote-3` · worktree `~/Desktop/labuse-copilote` · ports 9150/6350.
- **Portée** : `copilote_v2/` et son écran UNIQUEMENT. Pas de merge, aucun accès prod. Merge = geste de Vic.
- **Registre lu avant correction** : `docs/audit-2026-11/nu-1/E/RAPPORT.md` (NU-E-046 à 049, commit
  `914fff1d7` — lu, non mergé) et `docs/audit-2026-11/urgence-1/COMPTE-RENDU.md`.

## Règle gravée

> **Le Copilote n'affirme que ce qu'un outil porte.** Sans champ pour répondre, il dit « je n'ai pas
> cette donnée » et propose l'outil ou la fiche qui l'a.

Appliquée en deux temps : (1) la **réponse déterministe** sert chaque fait qualitatif depuis l'outil
qui le porte, sourcé au bon producteur, avant tout LLM ; (2) le **verrou qualitatif** refuse, sur le
chemin LLM résiduel, toute affirmation oui/non que la donnée d'outil ne porte pas.

## Les quatre points traités

### NU-E-046 — faux verdict de copropriété inventé par le LLM
- **L'outil de fiche PORTE désormais la copropriété** : `fiche_parcelle` (`outils.py`) lit le drapeau
  fiable `score_v2.copro` (CHASSE-4 : `p_model_ext_copro` = TOUTES les parcelles, faux signal) et le
  **confirme** par le répertoire RNIC (`coproprietes`). Ni l'un ni l'autre servi → `None` (« inconnu »,
  **jamais « non » par défaut**).
- **Réponse OUI/NON déterministe, sans LLM** : une question copropriété sur une parcelle nommée est
  routée (`answering.answer`) vers `resume_fiche.reponse_copro` **avant** `classify`. Sur
  `97404000AV0167` : *« Oui, la parcelle est en copropriété (9 lots recensés au répertoire des
  copropriétés). »* — là où le LLM affirmait *« Non, … pas en copropriété »*.
- **Autres faits qualitatifs vérifiés et leur source** :

  | Fait | Porté par | Voie de réponse | Source servie |
  |---|---|---|---|
  | copropriété | `score_v2.copro` + RNIC | déterministe (`reponse_copro`) | **RNIC — répertoire des copropriétés** |
  | zone PLU | `reglement_plu` | déterministe (champ `zone`) | **PLU — zonage (règlement communal)** |
  | PPR (rouge/bleue/hors) | couche aléas servie | déterministe (`statut_ppr`) | **DEAL Réunion — PPR / aléas** |
  | constructibilité | *aucun verdict binaire* | zone + PPR factuels, renvoi règlement | **PLU** (+ **DEAL** si PPR) |
  | propriétaire personne morale | `proprietaire_moral` (DGFiP) | déterministe (champ `type_proprietaire`) | **DGFiP — SIREN public** |

### NU-E-047 — le verrou anti-invention était aveugle au qualitatif
- `_anti_invention` (`answering.py`) ne gardait que les **nombres**. Ajout de `_verdicts_coherents` :
  toute affirmation OUI/NON de la prose (copropriété, constructibilité, PPR, propriétaire personne
  morale) doit correspondre à un **champ présent** dans le résultat d'outil (`data`/`faits`) **et en
  respecter la polarité** — sinon la prose est **refusée** et bascule sur le gabarit de repli
  déterministe (`_repli_lisible`). Branché dans `_formuler` à côté d'`_anti_invention`.
- Détails : un verdict sur un fait **non porté** = invention → refus ; une polarité **contraire** à la
  donnée servie → refus ; un fait **inconnu** (champ servi à `None`) → aucune affirmation permise ; un
  **refus honnête** (« je n'ai pas cette donnée ») n'est pas une affirmation → passe ; les mots courts
  (« ppr ») sont cherchés avec **bornes de mot** (ne se déclenchent pas dans « approprié »).
- `FORMULE_SYSTEM` durci : interdiction explicite d'un oui/non non porté ; chaque fait cite **sa**
  source (le champ `faits[].source`), jamais une source générique sur un verdict d'une autre origine.

### NU-E-048 — source falsifiée (« cadastre Etalab » sur un verdict PLU)
- `fiche_parcelle` ne tague plus TOUT son payload « cadastre ». Chaque fait porte **sa vraie source**
  via la liste `ToolResult.faits` : zone → **PLU**, copropriété → **RNIC**, propriétaire → **DGFiP**,
  surface/commune → **cadastre**.
- `resume_fiche.champ_precis` sert la source du **fait** (`_SOURCE_CHAMP`) : la zone cite le PLU, les
  aléas la DEAL, le propriétaire la DGFiP — plus jamais « fiche LABUSE »/« cadastre » sur un verdict
  réglementaire.
- Preuve d'un trou rebouché pendant la recette : *« appartient-elle à une personne morale ? »* tombait
  dans le formuler et estampillait **cadastre** sur un fait DGFiP → désormais routé en déterministe
  (DGFiP). Mesuré : plus aucune source « cadastre » sur un verdict non cadastral sur les 20 questions.

### NU-E-049 — doctrine « scoring seulement où demandé » (déjà close par URGENCE-1)
- `fiche_parcelle` n'embarque toujours pas de `verdict` de scoring (retiré par URGENCE-1, préservé).
  Un verdict de **constructibilité** demandé à la fiche est désormais *impossible* : la fiche ne le
  porte pas → le verrou le refuse, et la question est routée vers les faits (zone PLU + PPR) et renvoyée
  au règlement / à l'Étude. En **RNU** (Saint-Philippe, pas de PLU servi), le Copilote **ne tranche
  pas** et le dit (cf. NU-E-055), au lieu d'inventer une zone « UA ».

## Recette

### Test automatisé (le filet du mandat)
`tests/test_copilote3_verdicts.py` — **« échoue si une réponse affirme un fait absent du résultat
d'outil »** : `test_verrou_refuse_verdict_copro_absent_du_resultat` construit la prose hallucinée de
NU-E-046 sur la fiche *legacy* (sans champ copro) et exige `_verdicts_coherents → False`. Couvre aussi
polarité contraire, fait inconnu, PPR/constructibilité/PM non portés, refus honnête, comptage filtré,
bornes de mot, sources par fait. **14 tests déterministes (sans IA ni base)** + 5 témoins `db` (skip
propre sur la base `labuse_test` minimale du hook ; vérifiés contre la base de dev).

### 20 questions · 6 parcelles témoins (lecture seule, base de dev)
Script reproductible `docs/audit-2026-11/copilote3/recette.py` (sortie `captures/copilote3/recette.txt`).

**Témoins** : `97404000AV0167` (copro=True, PPR rouge, UC) · `97410000AN0347` (zone N, PPR rouge,
communal) · `97401000AC0575` (zone A agricole) · `97417000AT1496` (RNU) · `97411000AW0692` (Ud, PM =
SCI ALOE) · `97416000CD0448` (Us, hors PPR).

| # | question (parcelle) | AVANT | APRÈS (déterministe) | source |
|---|---|---|---|---|
| Q1 | copro ? (AV0167) | *« Non, pas en copropriété »* (inventé) | **Oui, en copropriété (9 lots)** | RNIC |
| Q2/3/4 | copro ? (AN0347 / AW0692 / AT1496) | LLM | **Non, pas répertoriée en copropriété** | RNIC |
| Q5 | zone rouge PPR ? (AV0167) | esquive | **Oui, zone rouge — 72 % inconstructible** | DEAL |
| Q6 | risque PPR ? (CD0448) | — | **Non, hors PPR** | DEAL |
| Q7 | zone rouge ? (AN0347) | — | **Oui, zone rouge — 54 %** | DEAL |
| Q8 | zone PLU ? (AC0575) | « cadastre » | **Zone A** | PLU |
| Q9 | zone ? (AW0692) | « cadastre » | **Zone Ud (famille U)** | PLU |
| Q10 | zone ? (AT1496, RNU) | — | **non renseigné (donnée absente)** | PLU |
| Q11 | constructible ? (AC0575) | oui/non inventé | **zone A : construction nouvelle non autorisée ; + zone rouge PPR** | PLU + DEAL |
| Q12 | construire ? (AT1496, RNU) | zone « UA » inventée | **RNU : je ne tranche pas (L111-3)** | PLU |
| Q13 | constructible ? (CD0448) | — | **zone Us : pas de verdict en un mot, dépend du règlement** | PLU |
| Q14 | construire ? (AV0167) | — | **zone UC + zone rouge PPR inconstructible sur la part** | PLU + DEAL |
| Q15/16 | propriétaire ? (AW0692 / AN0347) | « fiche LABUSE » | **Personne morale — SCI ALOE / COMMUNE DE SAINT BENOIT** | DGFiP |
| Q17 | surface ? (AV0167) | — | **140 m²** | cadastre |
| Q18 | hauteur max zone Us ? (CD0448) | — | **11 m (faîtage)** | PLU Saint-Pierre (calibré) |
| Q19 | dis-moi tout (AV0167) | — | résumé déterministe (bandeau + 9 verdicts) | fiche LABUSE |
| Q20 | appartient à une PM ? (AW0692) | **« cadastre »** (stamp faux) | **Personne morale — SCI ALOE** | DGFiP |

**Preuve du verrou** : sur la fiche *legacy* (sans champ copro), la prose inventée
*« Non, … pas en copropriété »* → **verrou REFUSE (invention)** ; sur la fiche *après*, copro=True est
porté et la zone est sourcée **PLU**, plus « cadastre ».

## Résultats hook

- `pytest -m "not db"` (famille complète du hook) : **2988 passed · 49 skipped · 9 failed** en 34 min.
  Les **9 échecs sont pré-existants & environnementaux** (implantation/étude/verrous « …passent sur la
  base réelle », PDF sur parcelles témoins) : ils tiennent à l'absence de la base réelle / des témoins
  dans le shell (la base est `labuse_test` via conftest), **pas au diff**. Prouvé : 4 d'entre eux
  rejouent **à l'identique sur `main` propre** (worktree `labuse-main`, même env → 4 failed), et aucun
  des fichiers en échec n'importe `copilote_v2/`.
- Zone touchée : `test_copilote3_verdicts.py` **14 passed** (déterministes) ; suite copilote+outils
  déterministe **152 passed**, **0 régression**.
- Base de dev (lecture seule) : les 5 témoins `db` passent, les 20 questions sourcées correctement,
  **0 source « cadastre » sur un verdict non cadastral**.

## Fichiers touchés (copilote_v2/ uniquement)

- `src/labuse/copilote_v2/outils.py` — `ToolResult.faits` ; `fiche_parcelle` porte copro + propriétaire
  PM + sources par fait (zone→PLU, copro→RNIC, PM→DGFiP).
- `src/labuse/copilote_v2/resume_fiche.py` — `est_question_copro`/`reponse_copro` (OUI/NON déterministe
  RNIC) ; `_SOURCE_CHAMP`/`_source_champ` (source par champ) ; mots-clés propriétaire élargis.
- `src/labuse/copilote_v2/answering.py` — verrou `_verdicts_coherents` (+ `_polarite_quali`,
  `_quali_backing`, `_mot_present`) branché dans `_formuler` ; routage déterministe copropriété +
  constructibilité (`_est_question_constructibilite`/`_reponse_constructibilite`) ; `FORMULE_SYSTEM` et
  catalogue `fiche_parcelle` durcis ; `faits` passés au formuler.
- `tests/test_copilote3_verdicts.py` (neuf) · `docs/audit-2026-11/copilote3/recette.py` (neuf).

**Écran Copilote** : aucune modification nécessaire — les réponses déterministes voyagent par la
structure de reply existante (`text` + `sources` + `voie`), déjà rendue par l'écran.

*Recette jouée le 2026-10-31. Branche `fix/copilote-3`, commit sur la branche. Pas de merge, pas de
push, aucun accès prod. Merge = geste de Vic.*
