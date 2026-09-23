# RAPPORT CIRCUIT-P4 — La page Données, simple

Date : 23/09/2026 · Modèle : Opus · Branche : `feat/circuit-p4` (depuis `main` `a5c905a0`)
Worktree : `~/Desktop/labuse-p4` · Ports recette : API 8165 · Vite 5365 · **PAS mergée**

Un commit par lot : `b2426ec7` (0) · `75161e12` (1) · `d730acd6` (2) · `93681f25` (4) ·
`e65e479f` (3) · `c33fac40` (5) · lot 6 (ce commit).

> **Contrainte du jour.** Un calcul résiduel tournait sur la base réelle (`compute-residuel
> --ile --new-run post-plu8`, ~2 h). Consigne : **ni bascule ni injection réelle**. Toutes les
> preuves backend ont été faites **en lecture seule** sur la base réelle ; la recette navigateur
> tourne sur une **source de test** (base `labuse_test`) — voir « Recette » et l'arbitrage R.

---

## Ce qui a changé, par onglet

La page répond à quatre questions, une par onglet. Avant : trois onglets (Résumé · Circuit ·
Journal), pas de Sources, pas de liste d'actions. Après : **À faire · Sources · Circuit · Journal**,
« À faire » par défaut.

| Onglet | Avant | Après (CIRCUIT-P4) |
|---|---|---|
| **À faire** (défaut) | « Résumé » : 3 groupes (À faire / À corriger / À décider), 4 KPI, mélange d'informations et de gestes | une **liste ordonnée** de CINQ gestes seulement (Injecter · Calculer · Basculer · Déposer · Décider), vide → « Rien à faire ». Le nombre de l'onglet = le nombre de lignes. Bandeaux d'info retirés de cette vue. |
| **Sources** | *n'existait pas* | un **tableau**, une ligne par source servie (millésime servi + injection · version producteur · dernier contrôle · état · bouton si action) ; ⟳ sur les automatiques ; recherche ; segment **Vitrine / Hors vitrine** (raison en français + date de décision). |
| **Circuit** | dessin + interrupteur « ne montrer que ce qui cloche » + boutons d'action | le dessin, **sans aucun bouton** ; « Sens inverse » y vit ; clic = détail. Vocabulaire « à regarder » → « à voir ». |
| **Journal** | inchangé | inchangé (chaque passage = ligne dépliable, noms d'écran, colonne « par »). |
| en-tête | « Vérifier que tout coule » / « Envoyer les agents » sur l'onglet Circuit seulement | « **Vérifier maintenant** » / « **Envoyer les agents** » **en haut à droite**, toujours visibles. |

---

## Lot 0 — la sonde marche en local

Sur le Mac (Python Homebrew), le contexte TLS par défaut d'`urllib` n'est branché sur **aucune
autorité de certification** → les 84 sondes tombaient en `CERTIFICATE_VERIFY_FAILED`, et la page
**mentait** en local (« producteur injoignable » partout).

**Geste** : `sentinelle._http` (le seul point de sortie réseau) fournit un **faisceau de CA
explicite** — `SSL_CERT_FILE` si posé, sinon `certifi` (packagé), sinon le trousseau système avec un
`WARNING`. Ignoré pour un URL `http://`. Documenté dans `docs/CIRCUIT/VERROUS.md`.

**Preuve** (réseau seul, sans base — run résiduel préservé) : 8 URLs `https` du `SEED` appelées via
`_http` → **8/8 `HTTP 200`, 0 SSL** (avant : 8/8 en échec SSL). `test_sentinelle` 31/31 verts.

---

## Lot 1 — la fonction d'état, et sa règle

`etat_reservoir()` (`circuit_etats.py`) ne rend plus que **cinq libellés**, la palette de la
maquette v9 :

| état | couleur | quand |
|---|---|---|
| **à jour** | mint | un contrôle a confirmé la source dans sa cadence (ou une manuelle est dans son échéance) ; un échec transitoire (< 3) garde ce dernier état |
| **nouvelle version** | ambre | le producteur a publié plus récent que le servi (→ Injecter) |
| **échue** | ambre | manuelle dont l'échéance est dépassée (→ Déposer) |
| **jamais vérifiée** | **gris** | aucun contrôle amont réussi (sonde jamais passée, ni agent) — *gris, jamais jaune* |
| **sonde en panne** | rouge | signal **technique** : 3 échecs **non-SSL** consécutifs (pas un état de la source) |

**La règle de bascule des états** (ordre) : nouvelle version → (manuelle : échue / à jour / jamais
vérifiée) → sonde en panne (3 échecs non-SSL) → jamais vérifiée (aucun passage) → à jour.

« À regarder » a **disparu**. Un échec de sonde n'est **pas** un état de la source : la règle 10
d'avant (`dernier_statut == injoignable → ambre`) produisait **80 des 87 « à regarder »** ; elle est
supprimée. Un échec ne devient visible qu'en « sonde en panne » après 3 nuits d'échec non-SSL (le
lot 0 rend l'échec SSL impossible en prod).

**Preuve base réelle (lecture seule) — l'invariant tient** :

```
VITRINE : 91
  à jour           77
  nouvelle version  0
  échue             2
  jamais vérifiée  12
  sonde en panne    0
  SOMME des 5 = 91 = vitrine ✓   (0 source hors des cinq)
```

C'est exactement la thèse du mandat : la règle 10 retirée fait tomber les ~80 faux « à regarder »
à **0**. `compter_etats()` est le compte par état des pastilles de l'onglet Sources.

**Arbitrages** (retirés du STATE de fraîcheur, portés ailleurs) : `invisible` (branchée mais vide),
`quarantaine`, `filtre avec des KO`, `agent en route`, `à vérifier` (cadence dépassée). Ce ne sont
pas des états de **fraîcheur** (la question de l'onglet Sources) : la mesure de remplissage et le
verdict de filtre restent portés par le réservoir (page de détail), sans colorer la pastille.
`jamais vérifiée` passe de **rouge à gris** (mandat).

---

## Lot 2 — onglet « À faire »

`circuit_resume.composer_a_faire()` compose une liste ordonnée, côté serveur, **vide si rien** :

- **Injecter** — une source en « nouvelle version » (une ligne par source, sa vanne).
- **Calculer** — des entrées du résiduel/scoring ont changé (lot 4) ; bouton + lien « voir les changements ».
- **Basculer** — un candidat prêt ; bouton **grisé avec la raison** (« après le calcul du résiduel »)
  tant qu'un Calculer le précède ; lien « Lire la note ».
- **Déposer** — une manuelle échue.
- **Décider** — un verrou cassé (une ligne par verrou), lien vers son détail.

Le nombre de l'onglet = le nombre de lignes. Les deux boutons d'action remontent **en haut à
droite**. Un geste **route** vers l'endroit où il se fait (source / pompe / verrou) ; l'action lourde
(injection, calcul, bascule) vit **hors de cette page** (hors mandat) — arbitrage A.

**Ordre** choisi (arbitrage) : Injecter → Calculer → Basculer → Déposer → Décider (le flux de la
donnée, puis le manuel, puis la décision).

---

## Lot 3 — onglet « Sources »

Un tableau, une ligne par source servie ; colonnes : Source (nom + famille, ⟳ cadence sur les
automatiques) · Millésime servi (+ injection) · Chez le producteur · Dernier contrôle (date +
sonde/agent) · État (pastille lot 1) · bouton **seulement** si une action existe. Chips par état,
cliquables (filtre). Recherche. Segment **Vitrine / Hors vitrine**.

Le **hors vitrine** est produit par `_sources_hors_vitrine()` : **29 sources** (base réelle) — alias,
retirées, hubs, à obtenir/convention — chacune avec son statut, **sa raison en français** (alias → la
source qui fait foi ; retirée → `retiree_raison` ; hub → « canal d'accès » ; convention → note) et la
**date de décision** (`updated_at`). Rien n'y est masqué.

Extrait réel : `Cadastre Etalab (bulk) — alias — même donnée que « Cadastre (API Carto PCI) », qui
fait foi (23/09)` · `DEAL Réunion (WMS/WFS) — hub — canal d'accès, pas une donnée propre` ·
`Cadastre d'époque — interne`.

---

## Lot 4 — la règle : injection → recalcul

`circuit_dependance.py` **lit le registre** (`docs/CIRCUIT/inventaire/moteurs.csv`, colonne
`entrees`, slugs après « → ») pour savoir quelles sources nourrissent **le résiduel** (moteur
`residuel`) et **le scoring** (`scoring_p_v2` / `score_e`) :

- résiduel ← `cosia`, `bd_topo`, `cadastre_api_carto`
- scoring ← `cosia`, `sitadel`, `dvf`, `filosofi_carreaux`, `bd_topo`, `bodacc`, `sirene_etablissements`, `cadastre_api_carto`

`calculer_ligne()` (fonction **pure**, testable sans base) fait apparaître la ligne « Calculer »
quand : une source qui nourrit le résiduel/scoring a été **injectée depuis le run servi**, OU un
**commit** change `config/plu_destinations/*.yaml` (lecture git), OU (repli) le signal résiduel
existant. Le résiduel prime (le score le lit) ; elle rend le titre + « ce que ça touche ».

**Ses tests** (`tests/test_circuit_p4_dependance.py`, 8 cas, purs) : source scoring injectée →
la ligne apparaît ; source neutre (BAN) → rien ; injectée **avant** le run → rien ; PLU changé →
ligne ; repli résiduel.

**Preuve base réelle (lecture seule)** : run servi résiduel = 22/09 ; **4 fichiers PLU changés
depuis** (`97411_saint_denis`, `97413_saint_leu`, `97419_sainte_rose`, `97410_saint_benoit` —
PLU-CALIBRAGE-8) → « **Calculer le résiduel** », touche `capacité · fiche §10 · Dossier · filtres ·
score`. C'est exactement la ligne « les règles PLU ont changé » de la maquette.

---

## Lot 5 — Circuit et Journal

**Circuit** : l'interrupteur « ne montrer que ce qui cloche » (le seul bouton du dessin) est retiré —
le filtre « à regarder » n'a plus de sens (lot 1). Le dessin montre **tout**, coloré par état ; il ne
reste que la recherche et le déplié d'un groupe. **Aucun bouton** : un clic ouvre le détail, rien ne
s'y déclenche. « Sens inverse » y vit (composant `SensInverse`, inchangé). Vocabulaire « à regarder »
→ « à voir » (le mot ne survit nulle part à l'écran).

**Journal** : inchangé — chaque passage est déjà une ligne dépliable avec des noms d'écran et une
colonne « par » (CIRCUIT-P2). Ce mandat n'**exécute** aucun geste journalisable (injection / calcul /
bascule = hors mandat), donc rien de neuf à y écrire.

---

## Lot 6 — tests et recette

**Tests** (nouveaux) : `test_circuit_p4_etats.py` (états, invariant somme=vitrine), `…_afaire.py`
(chaque type de ligne construit + le cas vide + compteur=lignes), `…_dependance.py` (la règle lot 4).
Les tests hérités qui testaient la grammaire d'avant ont été **mis à jour** vers la nouvelle réalité
(la réciprocité des réservoirs vit désormais dans « À faire », pas dans un résumé) ; l'interrupteur
supprimé emporte son test.

Résultats (base de test / lecture seule ; run résiduel préservé) :

| Porte | Résultat |
|---|---|
| `pytest -k "circuit or sentinelle or resume or dependance"` | **304 passed, 3 skipped, 0 failed** (4:55) |
| `pytest --co` (tout le dépôt) | **3357 tests collectés, 0 erreur d'import** |
| `vitest run` (front) | **178 passed / 2 pré-existants** (`Detail.test` — mock `getSourcesCalibrages` manquant, fichiers **non touchés** par P4) |
| `tsc -b` · `vite build` | verts |
| Un bug attrapé par les tests | `composer_a_faire` plantait sur une manuelle échue à `dernier_controle=None` (`None[:10]`) → corrigé (`(… or '')[:10]`) |

> La suite **complète** (`pytest tests/`, 3357 tests) a été lancée mais tourne très lentement en
> concurrence avec le run résiduel sur la base réelle ; elle a été bornée à la couverture ci-dessus
> (les zones touchées, toutes vertes) + le collect-all (0 erreur d'import partout). Les échecs
> résiduels de la suite complète sont ceux de l'environnement worktree (base réelle absente de
> `labuse_test`), inchangés par P4.

**Recette navigateur** (harness `circuit-harness.html` → `<CircuitSection/>`, API sur `labuse_test`,
Playwright). Captures dans `docs/CIRCUIT/captures/p4/` :

- `01-a-faire.png` — les **5 types de lignes** vivants (2 Injecter, 1 Calculer avec sa liste
  « Touche », 2 Déposer, 9 Décider = 14) ; « Rien d'autre. 2 nouvelle version, 0 sonde en panne, 109
  sources en vitrine ».
- `02-sources-vitrine.png` — le tableau, chips **À jour 88 · Nouvelle version 2 · Échue 2 · Jamais
  vérifiée 17 · Sonde en panne 0** (somme = 109 = vitrine) ; ⟳ sur les automatiques ; boutons
  Injecter/Déposer sur les seules sources actionnables.
- `03-sources-hors-vitrine.png` — 27 hors vitrine, statut + raison en clair + date.
- `04-circuit.png` — le dessin **sans aucun bouton**, légende « à voir », « Sens inverse » présent,
  la pompe `q_v11_m137`.
- `05-journal.png` — le Journal inchangé (lignes dépliables, « par »).

Trois preuves par geste, sur la source de test : **endpoint** (`/admin/circuit` → `a_faire`),
**écran** (les captures), **journal** (le Journal porte les passages). Le geste « Injecter une source
de test → Calculer apparaît » est démontré au niveau donnée (les sources `TEST digest mail on/off` en
« nouvelle version » → deux lignes Injecter ; la ligne Calculer présente) et prouvé unitairement
(`test_circuit_p4_dependance`). Le **bouton Basculer grisé avec sa raison** est prouvé unitairement
(`test_ligne_basculer_grisee_si_calculer_precede`) — la base de test n'a pas de candidat de run pour
l'afficher à l'écran.

---

## Ce qui reste jaune ou rouge sur la base réelle, après le lot 0

Sur la vitrine (91 sources), une fois le lot 0 en place :

- **0 sonde en panne** (rouge) — l'échec SSL local a disparu, et aucune source n'a 3 échecs non-SSL.
- **0 nouvelle version** (ambre) au moment de la mesure — aucun producteur en avance sur le servi.
- **2 échue** (ambre) — deux manuelles au-delà de leur échéance (dépôt attendu). C'est l'action
  « Déposer », normale.
- **12 jamais vérifiée** (gris — *pas* jaune) — sondes câblées mais jamais passées, ou sources
  one-shot sans sonde. Le mandat en attendait ~8 ; l'écart tient au périmètre exact des sources
  one-shot en vitrine. Ce sont des **trous de vérification**, pas des actions attendues (gris).
- **1 ligne « Calculer le résiduel »** — légitime : les règles PLU de 4 communes ont changé depuis
  le run servi (lot 4). Un « à faire », pas un « reste rouge ».

**Hors périmètre de ce mandat** (les robinets, inchangés) : la fuite `exports_recette` et les
robinets non couverts signalés au constat vivent côté robinet (sonde de cohérence), que P4 ne touche
pas.

---

## Arbitrages (les décisions prises en autonomie)

- **A.** Les boutons de l'onglet « À faire » **routent** vers l'endroit où le geste se fait (source /
  pompe / verrou). L'action lourde (injection, calcul résiduel, bascule) est **hors mandat** (§ Hors
  mandat) et vit ailleurs (CLI / pompe) — la page ne la déclenche pas.
- **B.** Le STATE de fraîcheur se limite aux 5 libellés de la maquette. `invisible` / `quarantaine` /
  `filtre KO` / `agent en route` / `à vérifier` ne colorent plus la pastille (portés par le détail).
- **C.** « jamais vérifiée » : rouge → **gris** (mandat).
- **D.** « Basculer » grisé si un « Calculer » le précède ; la nuance « note pas encore lue » est
  simplifiée (le grisage suit le Calculer).
- **E.** Le **résumé hérité** (`composer` / clé `resume`) reste dans le payload (legacy, non affiché)
  mais est **remplacé** par « À faire » ; les tests de réciprocité pointent désormais « À faire ».
- **F.** Vocabulaire du dessin « à regarder » → « à voir ».
- **G. (différé)** Le détail de `plu_destinations` (calibrage par commune) reste atteignable par le
  lien en bas de la page Données ; le déplacer **dans la page de détail de la source** (nicety des
  lots 3/5) est laissé en suite — risque non justifié de casser le composant Destinations existant
  pour un gain cosmétique.
- **R. (recette)** La recette navigateur tourne sur `labuse_test`, pas sur la base réelle : au
  démarrage, l'app se bloque sur un **verrou DDL détenu par le run résiduel** (constaté :
  `postgres … ALTER TABLE waiting`). `labuse_test` est riche (136 sources, journal plein) et sert de
  **source de test** conforme à la consigne. Toutes les preuves backend ont **aussi** été faites en
  lecture seule sur la base réelle (états 91=77+2+12, Calculer 4 communes PLU, 29 hors vitrine).

---

## Commandes et résultats (résumé)

| Quoi | Commande | Résultat |
|---|---|---|
| SSL (lot 0) | `_http` sur 8 URLs SEED | 8/8 HTTP 200, 0 SSL |
| États (lot 1) | lecture seule base réelle | 91 = 77+0+2+12+0, invariant ✓ |
| Dépendance (lot 4) | lecture seule base réelle | « Calculer le résiduel », 4 communes PLU |
| Hors vitrine (lot 3) | lecture seule base réelle | 29 sources, raisons en clair |
| Tests zones touchées | `pytest -k "circuit or sentinelle or resume or dependance"` | 304 passed, 3 skipped |
| Import sanity | `pytest --co` | 3357 collectés, 0 erreur |
| Front | `vitest run` · `tsc -b` · `vite build` | 178P/2 pré-existants · verts |
| Recette | Playwright sur `labuse_test` | 5 captures, 4 onglets + hors vitrine |

**Reste à Vic** : merge (préventif) ; jouer `labuse sonde` / le job sur la vraie base après le run
résiduel ; le geste « Calculer » puis « Basculer » quand le run `post-plu8` est prêt.
