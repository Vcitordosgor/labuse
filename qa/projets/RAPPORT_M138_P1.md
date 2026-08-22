# M138 P1 — Le plafond des 60 (`fix/projets-plafond`)

Branché sur `origin/main` @ `81daf718`. L'avance depuis le merge M137 = **un seul
commit `.gitignore`** (hors périmètre projets), signalé. CC ne merge jamais.

**Résultat en une ligne : le plafond est au FIGEAGE, pas au rendu — et un retrait
« liste complète » explose en volume. Les DEUX garde-fous du §1.B se déclenchent.
Je n'ai retiré aucun cap ; ce rapport pose les chiffres, Vic tranche.**

---

## 1.A — Localiser (lecture seule)

### 1. Où vit le 60 ? → au **FIGEAGE** (pas au rendu, pas les deux)

- Le 60 **n'est pas en dur** : c'est `shortlist_defaut: 60` dans `config/projets.yaml`
  (avec un plafond absolu `shortlist_max: 200`). Dette M122 « cap 60 en dur » déjà morte.
- **Écriture (figeage)** — `_figer_shortlist` (`projets.py:550`) :
  `lim = max(1, min(limit or shortlist_defaut(60), shortlist_max(200)))`, puis
  `projets.py:554` `items = _search_items(db, filtres, lim)` → **seules `lim` lignes
  sont récupérées ET écrites** dans `projet_parcelles`. Le stockage est plafonné.
- **Rendu — FIDÈLE, aucune 2ᵉ troncature** : `_shortlist_pdf` (`projets.py:1091-1102`)
  lit **tout** le stocké (`WHERE pp.projet_id = :pid AND pp.statut <> 'ecartee'`,
  **pas de LIMIT**), ordre géographique. L'écran projet lit la même table. Le PDF ne
  tronque pas une liste plus large : il n'y a **rien de plus** à rendre que les 60 figées.
- **Extension sans re-figeage** : `chercher-plus` (`projets.py:974-1002`) ajoute des
  `proposee` jusqu'à `shortlist_max=200` **sans toucher `derniere_execution_at`** — donc
  un projet peut passer de 60 à ≤ 200 sans changer sa date « figé le JJ/MM », mais **200
  est un mur dur** (dette M122 « chercher-plus » rejoint le cap config, pas l'infini).
- **Le texte d'en-tête PDF est déjà conditionnel et honnête** (`pdf_projet.py:230-237`) :
  `total > n` → « Liste plafonnée : {n} figées sur ~ {total}… un rang non visible » ;
  `total <= n` → « Liste complète… Aucune sélection, aucun rang ». Il décrit **exactement
  le figeage actuel** — il ne promet pas un mécanisme qui n'existe pas.

### 2. Volumes réels (4 projets QA — P1/P2/P3 ; P4 non figé = 0 stocké)

| QA | Cadrage | Stocké | Retenues par cadrage | Étage 0 |
|----|---------|-------:|---------------------:|--------:|
| **P1** large île (P132/P181) | toute l'île | **60** | **285 781** | 0 |
| **P2** étroit Tampon (P133/P182) | commune serrée | **60** | **839** | 0 |
| **P3** écartées St-Pierre (P134/P183) | écartées | **60** | **10 725** | **10 725 (tout)** |

Tous les projets figés récents portent **exactement 60 lignes** (le défaut config).
Le « ~ 839 » et le « 10 725 » du mandat = P2 et P3. P3 est intégralement à l'étage 0
(vivier figeable = 0 : que des parcelles écartées du vivier exploitable).

### 3. Sémantique du figé

Le plafond étant **au figeage**, un projet existant **ne porte physiquement que 60
lignes**. L'élargir au-delà du déjà-stocké suppose :
- soit `chercher-plus` (≤ 200, **ne change pas** la date de figeage) ;
- soit un **re-figeage** (repose `derniere_execution_at` → **contredit « cadrage figé le
  JJ/MM »**).

« Liste complète » est **impossible** sans lever aussi `shortlist_max`, et alors le
volume explose (§1.B).

---

## 1.B — Retrait : **DEUX STOP se déclenchent, je ne retire rien**

### STOP 1 — plafond au figeage (STOP court du mandat)

Retirer le défaut de 60 **ne vaut que pour les figeages FUTURS**. Les 19 projets figés
existants restent à 60 (ou moins) sauf **re-figeage**, qui **change leur date**. La
rétroactivité (re-figer en masse ? laisser tel quel ? migrer via chercher-plus jusqu'à
200 sans re-dater ?) est un **arbitrage Vic**, pas une évidence technique.

### STOP 2 — volume (garde-fou chiffré du mandat)

Mesure réelle (PDF générés à 1/14/60 lignes → régression, **aucun gigaoctet généré**) :
modèle `pages ≈ 0,9 + 0,119·n`, `poids ≈ 38 Ko + 525 o/parcelle`.

| Rendu complet | Parcelles | Pages | Poids |
|---|---:|---:|---:|
| P2 (839) | 839 | **~100** | ~0,5 Mo |
| **P3 complet** (10 725) | 10 725 | **~1 273** | ~5,7 Mo |
| **P1 « toute l'île » complet** | 285 781 | **~33 907** | **~150 Mo** |

Dès ~839 parcelles on atteint le seuil des ~100 pages ; P3 = **1 273 pages**, P1 =
**33 907 pages / 150 Mo**. Un rendu « liste complète » **dépasse le raisonnable** pour
tout cadrage large. **STOP avec les chiffres**, comme le mandat l'exige.

### Ce que je n'ai pas fait, et pourquoi

Je **n'ai pas** modifié `config/projets.yaml`, `_figer_shortlist`, ni le texte d'en-tête.
Le texte est **déjà honnête** (conditionnel) et le décrire faux exigerait d'abord de
retirer le mécanisme — ce que les deux STOP interdisent sans arbitrage.

---

## Options pour Vic (l'arbitrage)

1. **Liste complète assumée** — lever `shortlist_defaut` **et** `shortlist_max`.
   Conséquence : P1 = 33 907 pages / 150 Mo. À réserver éventuellement aux cadrages
   étroits, jamais « toute l'île ». Nécessite une borne de sécurité de toute façon.
2. **Plafond paramétrable** — exposer `limit` au figeage (déjà supporté par `ProjetIn.limit`
   et `chercher-plus`), défaut relevé (ex. 200), l'en-tête dit toujours « top N sur M ».
   Borné, sûr (~24 pages max), mais **ce n'est pas « le 60 saute »** — juste « 60 → 200 ».
3. **Plafond haut + en-tête honnête** — relever `shortlist_defaut` (ex. 120/200) sous
   `shortlist_max`, garder le texte conditionnel. Idem : plafond déplacé, pas supprimé.

Et, transversal à 1/2/3 : **rétroactivité des projets déjà figés** — re-figer (change la
date) vs. `chercher-plus` jusqu'à 200 (garde la date) vs. laisser à 60.

---

*Fin P1. Aucun cap retiré (deux STOP). Commit + push `fix/projets-plafond`. CC ne merge
jamais — Vic tranche l'option, la Partie 2 (audit `audit/projets`) suit.*
