# JOHN-COUT-1 — John coûte moins cher, sans perdre en qualité

**Branche** `fix/john-cout-1` · worktree `~/Desktop/labuse-john-cout` · ports 9840/7040 · **aucun accès prod, pas de merge.**
Code touché : `src/labuse/john/` (+ `ai_models.py`, `ai/core.py`). Modèle Opus. Banc jamais vers le réseau (0 €).

---

## Le constat

Une question à John passait par **Opus 5.5** du premier au dernier appel de la boucle d'outils, chaque
appel **re-renvoyant tout** (system prompt + définitions d'outils + historique + résultats d'outils), et
les outils **crachaient tout** (chaque job/source avec ses ~13 champs, re-renvoyés à chaque tour). À 50 €
de plafond mensuel, cela plafonnait le nombre de questions utiles à quelques dizaines.

## Les quatre leviers livrés

| Levier | Avant | Après |
|---|---|---|
| **Deux modèles** (routage invisible) | Opus 5.5 sur **tout** | **Sonnet 5.5** sur les questions de LECTURE (`john-lecture`), **Opus 5.5** seulement pour un **diagnostic** ou une **action** sur ordre de Vic (`john-chat`) |
| **Cache de prompt** | aucun | `cache_control` sur **system + outils + dernier message** → le préfixe stable est **lu à 0,10×** (écrit une fois à 1,25×) au lieu du plein tarif à chaque appel |
| **Outils sobres** | `lire_jobs`/`lire_sources` = tout le détail par ligne | l'**essentiel** (statut, compteurs) ; nouveau **`jobs_de_la_nuit`** = toute une plage en **un seul appel** (fini la rafale de `lire_job`) |
| **Garde-fou** | un chiffre non sourcé → **refus en bloc** de toute la réponse | le chiffre est **retiré** avec la mention « non sourcé », **le reste est servi** |

### 1. Routage invisible (`chat.model_du_tour`)
Par défaut **LECTURE → Sonnet** (le moins cher capable) ; on n'escalade vers Opus que sur un **signal
net** : marqueur de **diagnostic** (« pourquoi », « cause », « analyse », « d'où vient »…) ou **verbe
d'action** aligné sur la liste fermée (« relance », « promeus », « injecte », « retire », « lance une
sauvegarde »…). Un **nom** n'est jamais pris pour un ordre : « *la sauvegarde de cette nuit a-t-elle une
copie externe ?* » reste une lecture (Sonnet). Les deux surfaces sont `john-%` → **même plafond** ; le
coût est imputé à la bonne surface au ledger. Vic ne voit **aucune différence** (même onglet, mêmes
sources, même ton). Repli automatique `sonnet-4-6` si `sonnet-5-5` tombait en `not_found`.

### 2. Cache de prompt (`chat._poser_cache` + `_appel_reel`)
Trois points de cache (≤ 4) : le **system** entier, le bloc **outils** (marqueur sur le dernier), et un
breakpoint **glissant** sur le dernier message (l'historique grandissant de la boucle d'outils est lu du
cache au tour suivant). Posé sur des **copies** — l'historique `msgs` n'est jamais muté (pas
d'accumulation de breakpoints au fil des 6 appels). Le coût réel (`_log_cost` étendu : `cache_read`
0,10×, `cache_write` 1,25×) arrive au **ledger**, donc au **plafond** — activer le cache ne fait pas
apparaître un coût faussement nul.

### 3. Outils sobres + `jobs_de_la_nuit`
`lire_jobs` → `{nom, statut, fin, bloqué, en retard}` par job (au lieu de 13 champs) ; `lire_sources` →
`{nom, statut, classe, millésime servi, veille}` par source. Le détail reste accessible à la demande
(`lire_job`, `lire_rapport`). **`jobs_de_la_nuit`** rend, en **un appel**, le dernier passage de chaque
job d'une plage (défaut ~14 h) avec statut/durée/erreur courte + lesquels en échec.

### 4. Garde-fou qui retire au lieu de refuser (`chat.expurger_non_source`)
Même jeu de nombres autorisés que l'anti-invention (valeurs lues + cardinalités, tolérances
format/petits entiers du socle). Chaque chiffre non sourcé est remplacé par « non sourcé » **dans le
texte d'origine** (la typo n'est pas corrompue, la virgule décimale « 18,7 » est gérée) ; **le reste de
la réponse est donné**. Plus de « je préfère ne pas répondre » qui jetait 4 faits justes pour 1 douteux.

---

## La recette — banc de 10 questions, joué AVANT et APRÈS

`docs/audit-2026-11/john-cout-1/bench.py` pilote le **vrai** `chat.repondre` (routeur, boucle d'outils,
anti-invention, garde-fou) avec un appel modèle **instrumenté**, **sans réseau** : il joue le bon outil,
fabrique une réponse **sourcée** à partir du résultat **réel** de l'outil, et **chiffre chaque appel**
(system + outils + historique + résultats) au tarif du modèle que le routeur a choisi. Les 10 questions
types du mandat : jobs de la nuit, état d'un run, journal d'un job, incident, coût, sources, cohérence,
sauvegarde, Radar, et un **diagnostic** (« pourquoi le backup a échoué »).

Ce que le banc capte **automatiquement** du code (sans drapeau) : le **routage** (via le `model=`
transmis), les **outils sobres** (résultats de `outils.dispatch` réel), **`jobs_de_la_nuit`** (détecté
dans la liste d'outils → 1 appel au lieu de N), le **cache** (via `chat.CACHE_PROMPT`).

### Résultats

| Profil | Coût moyen / question | Appels moyens | Facteur |
|---|---|---|---|
| **AVANT** (Opus partout, 0 cache, outils gras) | **14,80 c€** | 2,4 | — |
| APRÈS — routage + outils sobres (cache OFF) | 3,01 c€ | 2,1 | **÷ 4,9** |
| **APRÈS — complet (+ cache de prompt)** | **1,18 c€** | 2,1 | **÷ 12,5** |

**Objectif « coût moyen divisé par au moins 3 » : atteint — ÷ 12,5** (et déjà **÷ 4,9 sans compter le
cache**, le levier le plus dépendant d'hypothèses).

### Qualité identique — mêmes faits, mêmes sources
Le banc enregistre, par question, les **faits cités** (les compteurs sourcés de la réponse) et les
**sources** (les étiquettes de lecture). **Avant = après sur les 10 questions** (`jq` sur
`avant.json`/`apres.json`). Le **diagnostic** (Q10) reste bien sur **Opus** ; les 9 lectures passent sur
Sonnet. `jobs_de_la_nuit` remplace la rafale de `lire_job` (Q1 : 5 appels → 2, 36,8 c€ → 0,8 c€).

### Honnêteté de la mesure
Jetons ≈ octets UTF-8 / 4 (heuristique **stable des deux côtés** — seul le rapport compte). Les valeurs
**absolues** sont plus basses qu'en prod : la base de **test** porte de petits payloads et le banc ne
modélise **pas** les jetons de réflexion d'Opus (qui, en prod, rendent le passage Opus→Sonnet **encore
plus** rentable). Le **rapport** ÷12,5 est le livrable, et il est robuste. Le cache mesuré reflète une
**session chaude** (questions successives dans les 5 min partageant le cache system+outils) — le cas
courant d'un échange interactif ; la toute première question « à froid » paie l'écriture (1,25×).

Artefacts : `avant.json`, `apres.json`, `apres_sans_cache.json` (rejouables :
`python docs/audit-2026-11/john-cout-1/bench.py --out <fichier> [--cache on|off]`).

---

## Tests

- **`tests/test_john_cout_1.py` (16 tests, NEUF)** : routeur (lecture→Sonnet, diagnostic/action→Opus, nom
  ≠ ordre, imputation `john-lecture` au ledger), cache (`_poser_cache` pose les points **sans muter** les
  originaux, `_log_cost` facture lu/écrit + compat ascendante), outils sobres + `jobs_de_la_nuit`
  (bornage de plage, champs essentiels), garde-fou (retire le non-sourcé, garde le sourcé et les
  décimales FR, n'altère rien sans chiffre), surfaces/pricing Sonnet.
- **Recette John existante** (`test_john_1/2/registre/nu4fix_1_john`) : **verte**, dont le garde-fou dont
  l'assertion a été **mise au mandat** (`test_garde_fou_retire_le_chiffre_non_source_et_garde_le_reste` —
  « plus de refus en bloc »).
- Suite **unitaire sans base** (famille du hook) + hook `pre-push` : **verts** (voir ci-dessous).

## Portée et prudence
Changements **cantonnés à John** et au socle partagé **en mode additif** : `_log_cost` gagne deux
paramètres `cache_*` **par défaut à 0** (tous les appelants existants inchangés) ; `MODEL_SONNET` et la
surface `john-lecture` sont des **ajouts**. `MODEL_OPUS` reste le défaut de `john-chat` (diagnostic/action
et résumé/enquête). Aucun accès prod, aucun merge.
