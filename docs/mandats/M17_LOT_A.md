# M17 — LOT A : millésimes des sources

**Branche** `fix/m17-a-millesimes` (base `main`). Prouvé, **non mergé**.

Objectif : afficher le millésime RÉEL là où il est retrouvable **dans le code**, laisser « non tracé »
honnête là où il est réellement introuvable. **Jamais deviné.**

## Mécanisme (rappel)
`SourcesPage.tsx` — « Version en service » suit une cascade honnête (l.94-99) :
`données jusqu'au {derniere_donnee}` → sinon `{millésime vérifié}` → sinon `donnée du {ingestion}` →
sinon **« millésime non tracé en base »** (repli, jamais un « — » nu). Le millésime vérifié vit dans la
map **`MILLESIME_VERIFIE`** (l.18) — modèle existant (DVF, Filosofi 2021). **M17-A l'étend** avec les
millésimes retrouvés dans `seed_sources.py`, chacun sourcé.

## Tableau des millésimes (sources qui affichaient « non tracé » / date de sync seule)

| Source | Millésime trouvé ? | Où (preuve code) | Valeur affichée | Décision |
|---|---|---|---|---|
| **Parc National de La Réunion (INPN)** | ✅ oui | `seed_sources.py:94-95` jeu ODS **`pnrun_2021`** | `millésime 2021` | **affiché** |
| **QPV 2024 (ANCT)** | ✅ oui | `seed_sources.py:217` « génération 2024 · décret 2023-1314, en vigueur 01/01/2024 » | `génération 2024` | **affiché** |
| **Classement sonore ITT (Cerema)** | ✅ oui | `seed_sources.py:199` « arrêtés préfectoraux **14-15/12/2023** » | `arrêtés déc. 2023` | **affiché** |
| **50 pas géométriques — limite haute (DEAL)** | ✅ oui (lignée) | `seed_sources.py:193` « cadastre **1877** (géoréf. orthos **2012/1950**) » | `cadastre 1877 (géoréf. 2012/1950)` | **affiché** |
| **DEAL Réunion — trait de côte** | ✅ oui | `seed_sources.py:272` fichier GéoLittoral `…_epsg2975_**062018**_shape.zip` | `millésime 2018` | **affiché** |
| **BPE INSEE** | ❌ **introuvable** | `seed_sources.py:164-168` statut `A_FAIRE`, note « import millésime » **sans année** | — | **laissé « non tracé »** |
| **Zonage SAFER (DAAF)** | ❌ **introuvable** | `seed_sources.py:108-112` SAFER propre INTROUVABLE en public ; proxy **`RPG.LATEST`** (non daté) | — | **laissé « non tracé »** |

### Déjà propres, non touchés
- **DVF** (`ventes jusqu'à déc. 2025`) et **Filosofi 2021** : déjà dans la map (modèle répliqué).
- **BD ORTHO 20 cm / IRC, LiDAR HD MNH, SITADEL, BODACC, DPE, BAN…** : ont une **`derniere_donnee`**
  (date de donnée réelle) → affichent déjà « données jusqu'au … » (prioritaire), rien à ajouter.

### Écartés volontairement (années présentes mais qui ne sont PAS un millésime de donnée)
Pour éviter d'induire en erreur, on **n'affiche pas** comme millésime :
- **BAN « 2020 »**, **Géoplateforme IGN « 2021 »**, **INPI RNE « 2024 »** = dates de **licence / ouverture
  open-data**, pas la fraîcheur de la donnée (ces bases sont mises à jour en continu) → laissées à leur
  date de sync réelle.
- **DPE ADEME « depuis 2021 »** = début de couverture, pas un snapshot → inchangé.
- **INSEE RP Logement 2023** : l'année est **déjà dans le nom** ; note d'audit `RP2022_logemt.zip`
  (2022) en conflit → **doute → non modifié** (Vic tranchera le vrai millésime du fichier source).

## Preuve (`:8060`, `qa/m17/A/prove.mjs`)
Page Sources : les **5 millésimes** s'affichent (`millésime 2021`, `génération 2024`, `arrêtés déc.
2023`, `cadastre 1877 (géoréf. 2012/1950)`, `millésime 2018`) ; **19 sources** restent « non tracé en
base » (dont BPE + SAFER), **aucun « — » nu**, **aucune année inventée**. Capture `sources_millesimes.png`.

## Golden
**116/116 PASS** (`LABUSE_DEV_MODE=1`, `LABUSE_API_BASE=:8060`). Frontend seul, zéro touche back/scoring.

## À faire côté Vic (millésimes réellement introuvables)
- **BPE INSEE** : retrouver le nom du fichier BPE ingéré d'origine (INSEE nomme `bpe23…`/`bpe21…` avec
  l'année de campagne). Non présent dans le code → à vérifier dans les fichiers sources d'origine.
- **SAFER** : accès conventionné/manuel jamais daté proprement → restera « non tracé » tant qu'une date
  fiable n'est pas fournie.
- **INSEE RP Logement 2023 vs RP2022** : lever l'ambiguïté nom (2023) vs fichier (`RP2022_logemt.zip`).
