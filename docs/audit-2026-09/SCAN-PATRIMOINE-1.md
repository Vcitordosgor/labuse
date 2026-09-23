# SCAN-PATRIMOINE-1 — L'outil « Scan patrimoine » écoute-t-il la bonne donnée ?

**Mandat :** audit court, lecture seule. L'outil Scan patrimoine (onglet **Possession** — les parcelles
d'une personne morale) lit-il les bonnes sources, complètes et à jour, et affiche-t-il ce qu'il y a
réellement en base ?
**Branche** `audit/scan-patrimoine-1` · worktree `~/Desktop/labuse-scan` (base main `b1f06a1c`) · aucune
modif code. **Verdict global : OUI — la source est la bonne, le compte affiché = le compte en base, à la
parcelle près. Trois écarts de conception (pas des bugs) à connaître ; aucun ne fausse le chiffre servi.**

Périmètre : l'onglet **Possession** uniquement (« ce qu'il possède »). L'onglet **Construction**
(Sitadel + sites promoteurs) est une autre donnée, hors mandat.

---

## 1. Le fil de la donnée

### Chaîne de code
- **Front** `frontend/src/components/outils/ScanPatrimoine.tsx` → onglet Possession = `<M02 sirenProp=… />`
  (`ModulePanel.tsx:168`).
- **Recherche** (nom/SIREN → société) : `GET /modules/patrimoine/search`
  (`src/labuse/api/modules.py:197`).
- **Portefeuille** (société → parcelles) : `GET /modules/patrimoine`
  (`src/labuse/api/modules.py:268`).

### Source, table, jointure, millésime

| Élément | Valeur constatée en base |
|---|---|
| **Table lue** | `parcelle_personne_morale` (PK = `idu`) |
| **Source** | DGFiP — « parcelles des personnes morales », open data data.economie.gouv.fr |
| **Fichier** | `fichier_des_parcelles_situation_2025_dpts_57_a_976` |
| **Millésime (colonne `millesime`)** | **`2025`, uniforme sur les 82 701 lignes** |
| **Import en base** | `date_import` max = **2026-07-05** |
| **Jointure société → parcelles** | `parcelle_personne_morale.siren = :siren` puis `JOIN parcels p ON p.idu = pm.idu` |
| **Identité affichée** | `denomination` (raison sociale MAJIC) — **pas de jointure SIRENE pour le nom** ; SIRENE/INPI ne servent que les signaux secondaires (état société, dirigeants, dépôt de comptes) |
| **Volumétrie** | 82 701 lignes · **12 605 sirens distincts** · 82 066 lignes rattachées à `parcels` |

Le compte servi (`n_parcelles`) est décrit noir sur blanc par la fiche de règle
`src/labuse/regles/n_parcelles_pm.py` : « assiette = parcelles du SIREN **présentes dans la base servie**
(jointure `parcels`) — pas le fichier DGFiP brut ».

### Points tranchés par le mandat

**a) La jointure société ↔ parcelles se fait sur quoi ?**
Sur le **SIREN** (clé forte), pas sur la dénomination. Le texte n'intervient qu'à *une seule étape* : la
**recherche** nom → SIREN (`patrimoine/search`, `ILIKE` désaccentué sur `denomination`). Une fois le SIREN
choisi, **tout est keyé sur `pm.siren`** — le portefeuille, le CSV, le compteur `n` de l'autocomplétion
(GB-007 : le `n` du search fait le MÊME `JOIN parcels` que le scan, pour ne pas sur-compter).

- *Risque « raison sociale écrite autrement » (rater des parcelles) :* **structurellement neutralisé** —
  MAJIC range toutes les parcelles d'une même société sous **un seul SIREN**, et chaque SIREN témoin ne
  porte **qu'une seule dénomination** (vérifié §2). Le texte ne sert qu'à *trouver* le SIREN ; il ne
  segmente pas le portefeuille. Reste le cas du **sigle d'usage** (« SHLMR » ≠ nom légal) : géré par une
  table d'alias explicite (`patrimoine_alias.py`, 3 entrées : SHLMR/SAFER/SEDRE).
- *Risque « homonyme » (attribuer à tort) :* nul **au niveau du portefeuille** (SIREN unique) ; il ne
  subsiste qu'à **la résolution du nom**. La recherche renvoie jusqu'à 12 sirens triés `n DESC`, et
  `ScanPatrimoine.resoudre()` **auto-sélectionne le premier** (le plus gros) sur Entrée/« Chercher ». Un
  nom ambigu tapé sans regarder le typeahead retient donc la plus grosse société homonyme, **sans
  demande de confirmation**. (Le copilote, lui, garde un garde-fou d'ambiguïté — voir §3.)

**b) Filiales / groupes.**
L'outil lit `WHERE pm.siren = :s`, SIREN **exact**. Une société mère voit **ses seules** parcelles, jamais
celles de ses filiales (sirens distincts). Constat, pas un jugement : il n'y a aucune remontée de groupe.
(La colonne `groupe`/`groupe_label` de la table est le regroupement *MAJIC « personnes morales
remarquables »*, ré-étiqueté « Personne morale — fichier DGFiP » à l'écran ; ce n'est pas un lien
mère-fille.)

**c) Millésime servi.**
Le fichier servi est **« situation 2025 »** (le plus récent publié par la DGFiP), importé le 2026-07-05, et
l'onglet **le dit au client** : *« Fichiers fonciers DGFiP · situation 2025 »* (`ModulePanel.tsx:252`,
champ `millesime_majic`). ⚠ Nuance vs les audits scoring qui parlaient de « PM arrêtés à 2024 » : ce sont
**deux tables différentes**. La série **historique** `pm_proprietaires_millesimes` (utilisée par
« Acquisitions récentes ») s'arrête à **2024** ; le **snapshot servi** `parcelle_personne_morale` est bien
**2025**, et « Acquisitions récentes » le greffe comme couche « 2025 » (`_MILLESIME_SERVI = 2025`) au-dessus
de 2019→2024. Le Scan patrimoine sert donc **la donnée la plus fraîche disponible** et la nomme.

---

## 2. Test sur 3 sociétés témoins (données réelles)

Méthode : compte **affiché par l'outil** = réponse live de `GET /modules/patrimoine` (API bootée sur
`:8265`, base réelle) · compte **en base sur la même clé** = `parcelle_personne_morale JOIN parcels` par
SIREN (psql). Grosse / moyenne / petite.

| Société | SIREN (clé) | Affiché (`n_parcelles`) | En base (JOIN parcels) | MAJIC brut | OK/écart |
|---|---|---|---|---|---|
| CBO TERRITORIA (grosse) | `452038805` | **1 833** | **1 833** | 1 871 | ✅ = |
| OCEAN INDIEN PARTICIPATIONS (moyenne) | `310850870` | **83** | **83** | 87 | ✅ = |
| ADPR (petite) | `523348928` | **4** | **4** | 4 | ✅ = |

**Compte affiché = compte en base sur la même clé, aux trois échelles.** L'écart avec le « MAJIC brut »
(1871→1833, 87→83) n'est **pas** une perte silencieuse : ce sont les droits MAJIC sur des parcelles **hors
périmètre cadastral ingéré** (`parcels`) — 635 lignes sur 82 701 à l'échelle île (0,8 %) — exactement le
choix documenté par la fiche de règle. Le millésime servi est `2025` pour les trois.

**5 parcelles au hasard (CBO, `ORDER BY md5(idu)`) — propriété réelle, pas d'homonyme :**

| IDU | SIREN en base | Dénomination | Commune | Surface m² |
|---|---|---|---|---|
| 97420000AB0002 | 452038805 | CBO TERRITORIA | Sainte-Suzanne | 1 632 |
| 97413000CX2535 | 452038805 | CBO TERRITORIA | Saint-Leu | 53 |
| 97418000AC1322 | 452038805 | CBO TERRITORIA | Sainte-Marie | 148 |
| 97415000DO0271 | 452038805 | CBO TERRITORIA | Saint-Paul | 827 |
| 97413000DA0171 | 452038805 | CBO TERRITORIA | Saint-Leu | 199 325 |

Les 5 portent le bon SIREN et la bonne dénomination. Contrôle homonyme inverse : « CBO TERRITORIA » n'existe
**que** sous le siren 452038805 (1 siren). Chaque siren témoin ne porte **qu'une** dénomination.

**Surface totale / communes affichées.** À signaler honnêtement : **le bandeau de synthèse n'affiche
NI surface totale du portefeuille NI nombre de communes** — il sert 3-4 chiffres : `parcelles`,
`actionnables`, `m² SDP résiduelle`, `valorisation foncier nu` (Estimé). Les surfaces et communes
n'apparaissent qu'**à la parcelle**, dans la liste, et sortent tout droit de `parcels` (validé sur les 5
échantillons). Sommes réelles en base pour référence : CBO 25 599 823 m² / 9 communes · OCEAN INDIEN
1 106 291 m² / 4 communes · ADPR 4 248 m² / 1 commune — non contredites par l'écran (l'écran ne les
prétend pas).

---

## 3. Cohérence avec le reste de l'app

Quatre endroits touchent au « foncier d'une PM ». **Tous lisent la même table `parcelle_personne_morale`
par `siren`** — la SOURCE est unique. Ce qui diffère, c'est le **sens du compte**, et c'est voulu :

| Endroit | Endpoint / code | Ce que compte le nombre | = Scan patrimoine ? |
|---|---|---|---|
| **Scan patrimoine** (Possession) | `/modules/patrimoine` | Portefeuille **complet** du SIREN (île entière, snapshot 2025) | référence |
| **Copilote** « parcelles par entreprise » | `copilote_v2/outils.py:283` → **appelle `patrimoine()`** | **Identique** (même fonction, même `n_parcelles`) | ✅ même chiffre |
| **Acquisitions récentes** (Communes, accordéon « SOCIÉTÉ · N parcelles ») | `/communes/{c}/acquisitions-pm` → `acquisitions_recentes()` | Parcelles **acquises récemment dans CETTE commune** (changement de siren entre millésimes ≥2022, source `pm_proprietaires_millesimes`) | ❌ **différent par nature** (sous-ensemble récent + 1 commune) |
| **Fiche / carte** — badge « SOCIÉTÉ · N parcelles » (cluster même propriétaire) | `app.py:2971` / `3331` (`cl.n`) | Parcelles du même SIREN **actionnables** (tiers `brûlante/chaude/priorité/à suivre`), île entière, `HAVING n>1` | ❌ **différent** (sous-ensemble actionnable ; 4 tiers) |

**Verdict §3.** Le compte du Scan patrimoine **n'est pas censé** égaler l'accordéon Acquisitions ni le badge
cluster, et ne l'égale pas : Acquisitions = *flux récent d'achats dans une commune*, cluster = *stock
actionnable*. Ces deux nombres sont plus petits **par construction**, pas par divergence de source. Les deux
consommateurs qui **prétendent** au même sens que le Scan (Scan lui-même et le Copilote) servent le **même
chiffre** (même fonction `patrimoine()`).

Deux nuances de traçabilité :
- **La fiche parcelle (§1 Identité, propriétaire moral)** lit `parcelle_personne_morale` par `idu`
  (`app.py:3789`) et sert `denomination` + `siren` — **même identité** que celle que le Scan résout. Elle
  n'affiche **pas** de compte de portefeuille ; elle offre la porte « Voir son patrimoine » qui rouvre le
  Scan sur ce SIREN. Cohérent.
- **Résolution nom → SIREN divergente** : le Scan (`patrimoine/search`, substring `ILIKE OR` + alias,
  auto-pick du plus gros) et le Copilote (`outils.py`, matcher par **tokens** `AND` + référentiel
  d'acronymes + **garde-fou d'ambiguïté** qui *demande* si deux sociétés se valent) n'utilisent **pas le
  même** résolveur de nom. Sur un nom ambigu, ils peuvent atterrir sur des sirens différents ; une fois le
  siren fixé, le compte est identique.

---

## 4. Verdict

### Récapitulatif source · jointure · millésime

| | Constat |
|---|---|
| **Source** | ✅ La bonne — DGFiP « parcelles des personnes morales », fichier `situation 2025` (le plus récent publié) |
| **Jointure** | ✅ Par **SIREN** (clé forte), `JOIN parcels ON idu` ; le texte ne sert qu'à *trouver* le siren |
| **Millésime** | ✅ `2025`, uniforme, **affiché au client** (« Fichiers fonciers DGFiP · situation 2025 ») |
| **Affiché = base** | ✅ Égalité exacte aux 3 échelles (1833/83/4), à la parcelle près du périmètre ingéré |
| **Homonyme (portefeuille)** | ✅ Nul — siren unique par société, dénomination unique par siren |

### Écarts trouvés (non corrigés — hors mandat)

1. **Auto-sélection silencieuse du plus gros homonyme.** `ScanPatrimoine.resoudre()` retient
   `results[0]` (tri `n DESC`) sur Entrée/« Chercher », sans confirmation, quand un nom matche plusieurs
   sirens. Le typeahead liste bien les candidats, mais la validation directe peut coller la mauvaise
   société. *(Le Copilote, lui, DEMANDE en cas d'ambiguïté réelle — asymétrie.)*
2. **Filiales invisibles.** SIREN exact → une mère ne voit jamais le foncier de ses filiales. Fait
   produit assumé, mais non dit à l'écran (aucun « ce périmètre exclut les filiales »).
3. **Co-propriété PM collabée.** `parcelle_personne_morale` a pour **PK `idu`** → **une seule PM par
   parcelle** (0 idu multi-lignes en base). Une parcelle détenue en indivision par deux PM n'apparaît que
   dans **un** des deux portefeuilles ; l'autre co-détenteur la rate. Limite de complétude structurelle,
   héritée de la table source (non quantifiable sans le fichier DGFiP brut).
4. **~0,8 % de droits hors périmètre** (635/82 701 lignes MAJIC sans `parcels`). Assumé par la règle
   `n_parcelles_pm` (« pas le fichier brut »), non signalé à l'écran parcelle-par-parcelle.
5. **~12 % de « sirens » sont des pseudo-identifiants MAJIC** (préfixe `U…`, non-9-chiffres) : 2 872
   sirens / 10 145 lignes. Le join et le compte fonctionnent (c'est une clé comme une autre), mais ces
   entités ne résolvent pas chez SIRENE/Pappers (le lien `Siren` cliquable est alors mort) et ne portent
   pas de signaux INPI/BODACC.
6. **Perf grosses PM.** `/modules/patrimoine` sur CBO (1833 parcelles) répond en **~25 s** (boucle
   valorisation par commune + contiguïté `ST_DWithin` sur tout le portefeuille) ; pas un bug de donnée,
   mais un temps de réponse à l'échelle d'un gros bailleur.

### Ce qui mériterait un mandat de correction

- **Écart 1 (auto-pick homonyme) — prioritaire :** aligner le Scan sur le garde-fou d'ambiguïté du
  Copilote (demander quand deux sirens se valent), ou ne jamais auto-valider sur nom sans clic dans le
  typeahead. C'est le seul écart qui peut faire **afficher le patrimoine de la mauvaise société**.
- **Écart 2 (filiales) :** décision produit — au minimum une mention « périmètre = ce SIREN, hors
  filiales » à l'écran. Pas de correction data requise.
- **Écart 3 (indivision PM) :** limite de source ; à documenter, pas corrigeable côté outil sans une
  table `parcelle × (n propriétaires PM)` que la source ne fournit pas telle quelle.
- **Écarts 4–5 (périmètre / pseudo-sirens) :** cosmétique de transparence (compter/étiqueter), pas une
  erreur de calcul.
- **Écart 6 (perf) :** optimisation, hors « bonne donnée ».

**Aucun écart ne fausse le chiffre servi une fois le bon SIREN retenu.** Le seul risque de « mauvaise
donnée affichée » est en amont, à la résolution d'un **nom** ambigu (écart 1).

---

## 5. Hors mandat (non fait)
Corriger l'un des 6 écarts · toucher au Scan ou aux autres outils · merger. Audit lecture seule.

---
*Méthode : lecture de code (front + `api/modules.py` + `api/app.py` + `proprietaire_historique.py` +
`copilote_v2/outils.py`), requêtes psql sur la base réelle `labuse`, et appels live de l'endpoint
`/modules/patrimoine` (API bootée sur `:8265`, base réelle). 3 témoins réels. Aucune modification.*
