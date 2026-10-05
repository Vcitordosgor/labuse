# PRIX-SORTIE-1 — un seul prix de sortie, partout

**Branche** `fix/prix-sortie-1` (worktree `~/Desktop/labuse-prixsortie1`, base `origin/main`) ·
**Phase 1 — inventaire lecture seule.** Aucun run, aucun recalcul, aucune écriture. 0 transaction
idle, ports 8707/5907 libres.

Valeurs témoins mesurées en direct par les **vraies fonctions serveur** (`sector_price`,
`resolve_prix_sortie_servi`, `neuf_vefa_commune`) sur la base de dev, le 2026-10-05.

---

## 1. Le constat : non pas deux, mais QUATRE prix de sortie

Le mandat partait d'un écart à 2 (Marché 4 848 vs bilan 4 375 sur AM0097). L'inventaire en trouve
**quatre sources distinctes** qu'un client peut rencontrer pour une même parcelle, et l'écart
constaté sur AM0097 est en réalité le plus PETIT des trois sur les témoins.

| # | Source (fonction / table) | Nature | Qui l'affiche |
|---|---|---|---|
| **S1** | `sector_price()` → `marche.median` (`faisabilite/bilan.py:257`) | **ANCIEN / existant** — DVF ventes actées (appart.+maison), rayon adaptatif 500→1500 m, trim Tukey 5 %, récence 5 ans, n≥8 | Fiche **Marché** ; fiche **Simulation** « Prix de sortie retenu » ; **Dossier PDF §8** ; **pré-remplissage du Financier** |
| **S2** | `resolve_prix_sortie_servi()` → `resolve_prix_neuf_marche()` / table `dvf_prix_sortie_neuf` (`bilan.py:347`, `ingestion/dvf_prix_neuf.py`) | **NEUF servi** — appartements vendus ≤ 3 ans après un PC (proxy VEFA), hors bailleurs sociaux, n≥10, replis secteur→commune→île | Fiche **bilan / charge foncière** ; **Calculette** (web + PDF) ; **Copilote / scoreur** ; **Assemblage** |
| **S3** | `neuf_vefa_commune()` (`ingestion/dvf_marche.py:187`) | **NEUF VEFA** — médiane €/m² des ventes « en l'état futur d'achèvement » de la commune, fenêtre 3 ans, grain commune, n≥8 ; **ni exclusion social, ni cascade de repli** | **Comparer** ; **Contexte** « Neuf VEFA (prix de sortie) » ; **fiche commune** ; `robinet_fiche._c_vefa` |
| **S4** | `prix_sortie_saisi_eur_m2` **pré-rempli depuis S1** (`financier_questionnaire.py:296-300`) | **SAISI** — défaut = prix ANCIEN du secteur (S1), modifiable | **Financier Excel/PDF** = *le* bilan promoteur |

> Adjacent, hors périmètre mais même étiquette (à surveiller) : `reference_locale()` →
> « **Prix de sortie (revente)** » du produit **réhabilitation-revente** (`constructibilite.tsx:866`,
> `api/export.py:102/239`). C'est un autre produit (revente en l'état, médiane mono-type), pas le
> bilan neuf — mais il porte le même mot « prix de sortie » et peut ajouter à la confusion.

### Valeurs sur les 3 témoins (€/m², mesurées)

| Témoin | Commune | Zone | **S1** ancien (Marché + Simul. « retenu » + Dossier §8 + prefill Financier) | **S2** neuf servi (bilan + Calculette + Copilote + Assemblage) | **S3** neuf VEFA (Comparer + Contexte + fiche commune) |
|---|---|---|---|---|---|
| `97415000AM0097` | Saint-Paul | **N** | **4 848** (appart., n=1269, 1500 m, *fragile*) | **4 730** (commune, n=54) | **4 745** (n=326) |
| `97411000BZ1065` | Saint-Denis | Uh | **2 365** (appart., n=34, 1000 m, fiable) | **4 275** (commune, n=77) | **4 878** (n=355) |
| `97416000ES0266` | Saint-Pierre | Ug | **2 975** (appart., n=26, 1000 m, fiable) | **4 258** (commune, n=76) | **4 931** (n=158) |

**Lecture.** Sur Saint-Denis, un même bien affiche **2 365 €/m²** en Simulation (« Prix de sortie
retenu »), **4 275 €/m²** réellement utilisés par le bilan de charge foncière juste en dessous, et
**4 878 €/m²** dans Comparer sous le libellé « Neuf VEFA (prix de sortie) ». Trois chiffres, trois
écrans, un seul bien.

> Note sur le mandat : il citait **4 375** (repli île) pour AM0097. La valeur servie aujourd'hui est
> **4 730** (médiane **commune** locale 97415, n=54, qui prime sur le repli île). 4 375 reste la
> médiane du repli île (`dvf_prix_sortie_neuf` niveau `ile`, n=315) — appliquée uniquement aux
> communes de marché SANS prix local. AM0097 est en zone **N** (non constructible) : son bilan est
> donc non calculable, mais la Simulation et le Marché affichent quand même « Prix de sortie retenu
> 4 848 ».

---

## 2. Le mensonge au cœur : « Prix de sortie retenu » ≠ prix utilisé par le bilan

Deux surfaces de la fiche **affirment** que le prix affiché EST la base du bilan, alors que le bilan
utilise S2 (neuf), pas S1 (ancien) :

- **`frontend/src/components/fiche/Fiche.tsx:1905`** — onglet Simulation, en-tête du verdict :
  `Prix de sortie retenu {prix} €/m²` où `prix = faisa.data.marche.median` (= **S1 ancien**),
  tooltip : *« C'est le prix affiché dans Marché … il sert de base au bilan de charge foncière
  ci-dessous. »* → **FAUX** : le bilan ci-dessous utilise S2.
- **`frontend/src/components/fiche/constructibilite.tsx:740-741`** — bloc « Prix de sortie retenu
  (bilan) », FactNote : *« Le prix de sortie bâti retenu pour la charge foncière est le prix du
  secteur affiché dans Marché. »* → **FAUX**, même raison.
- **`frontend/src/components/fiche/marche.tsx:130`** — commentaire « Même moteur que le bilan
  (`marche.median`) » → **périmé** : le bilan ne lit plus `marche.median` depuis la décision Vic
  28/07/2026.

Le moteur, lui, est correct : `compute_bilan` écrase q1=med=q3 par le prix neuf dès qu'il est résolu
(`bilan.py:517-518`), et `sector_price` « redevient purement documentaire » (`bilan.py:478-483`).
Le défaut est **d'affichage et de pré-remplissage**, pas de calcul.

---

## 3. Inventaire complet par surface

Légende source : **S1** ancien · **S2** neuf servi · **S3** neuf VEFA · **S4** saisi (prefill S1).

| Surface | Fichier:ligne | Source | Définition servie | AM0097 / BZ1065 / ES0266 |
|---|---|---|---|---|
| **Fiche — Marché** « Prix de sortie — bâti secteur » | `frontend/.../fiche/marche.tsx:136` | **S1** | `marche.median` (ancien, rayon adaptatif, trim 5 %) | 4 848 / 2 365 / 2 975 |
| **Fiche — Simulation** « Prix de sortie retenu » (en-tête verdict) | `frontend/.../fiche/Fiche.tsx:1905` | **S1** | `faisa.data.marche.median` | 4 848 / 2 365 / 2 975 |
| **Fiche — Simulation** « Prix de sortie retenu (bilan) » (FactNote) | `frontend/.../fiche/constructibilite.tsx:740` | **S1** | renvoie au prix Marché | 4 848 / 2 365 / 2 975 |
| **Fiche — bilan / charge foncière** (le calcul réel) | `faisabilite/bilan.py:395,408,517` | **S2** | `resolve_prix_sortie_servi` → `bp.prix_m2_neuf`, écrase q1=med=q3 | 4 730 / 4 275 / 4 258 |
| **Calculette foncière (web)** | `api/modules.py:1995-2002` ; front `constructibilite.tsx:282` (`d.prix_sortie_median`) | **S2** | `resolve_prix_sortie_servi` → `median` écrasé | 4 730 / 4 275 / 4 258 |
| **Calculette — ligne « au mieux » si non calculable** | `constructibilite.tsx:269` (`d.marche.median`) | **S1** | prix ancien au mieux | 4 848 / 2 365 / 2 975 |
| **Calculette (PDF)** | `api/app.py:6373-6377` | **S2** | `resolve_prix_sortie_servi`, `median=ps.prix` | 4 730 / 4 275 / 4 258 |
| **Faisabilité / Copilote / scoreur** | `faisabilite/bilan.py:373` `compute_bilan_servi` ; `api/scoreur.py` ; `sonde_circuit.py:340` | **S2** | source unique du bilan servi | 4 730 / 4 275 / 4 258 |
| **Assemblage (union multi-parcelle)** | `assemblage.py` (`compute_bilan_servi`) | **S2** | même résolveur sur la parcelle dominante | selon union |
| **Comparer** « €/m² neuf » | `api/comparateur.py` + `ingestion/dvf_marche.py:187` ; front `outils/blocB.tsx:172,282`, `moteurs.tsx:668` | **S3** | `neuf_vefa_commune` (VEFA acté, 3 ans, grain commune) | 4 745 / 4 878 / 4 931 |
| **Contexte** « Neuf VEFA (prix de sortie) » | `frontend/.../contexte/ContextePanel.tsx:497` | **S3** | `comparable.neuf_eur_m2` ← `neuf_vefa_commune` | 4 745 / 4 878 / 4 931 |
| **Fiche commune** | `api/fiche_commune.py` (`neuf_eur_m2`) | **S3** | `neuf_vefa_commune` | 4 745 / 4 878 / 4 931 |
| **Dossier PDF §8 Marché** (note « prix de sortie du programme reconstruit ») | `exports/blocs/marche.py:17,68,115-120` ; `exports/miroir.py` | **S1** | `prix_sortie_bati_eur_m2` = ancien, **nommé** « prix de sortie du programme reconstruit » | 4 848 / 2 365 / 2 975 |
| **Financier Excel/PDF** (le bilan promoteur) — hypothèse « Prix de vente prévu » | `financier_questionnaire.py:296-300` (prefill) ; `exports/builder.py:202` ; `exports/blocs/financier.py` ; `exports/financier_bilan.py` | **S4 = S1** | `prix_sortie_saisi_eur_m2` **pré-rempli depuis l'ancien** `prix_ancien.median` ; modifiable | 4 848 / 2 365 / 2 975 (défaut) |
| *(adjacent)* **Réhab-revente** « Prix de sortie (revente) » | `constructibilite.tsx:866` ; `api/export.py:102,239` ; `exports/robinet_fiche.py:544` | `reference_locale` | médiane mono-type secteur→commune (autre produit) | hors bilan neuf |

**Synthèse de cohérence :** les consommateurs du **bilan** (S2) sont cohérents entre eux — le
travail de la décision Vic 28/07/2026 tient. Les fuites sont sur **trois surfaces qui court-circuitent
S2** : la **fiche (Marché + Simulation, S1)**, le **Comparer / Contexte / fiche commune (S3)**, et le
**Financier + Dossier §8 (S1/S4)** — ce dernier étant le plus grave puisque le Financier EST le bilan
promoteur imprimé.

---

## 4. Recommandation (quelle source unique, et pourquoi)

1. **Retenir S2** (`resolve_prix_sortie_servi` / `dvf_prix_sortie_neuf`) comme **unique** prix de
   sortie, partout. C'est le seul vraiment NEUF (appartements ≤ 3 ans après PC, **hors social**),
   le seul déjà utilisé par le bilan servi, et le seul doté d'un repli explicite + d'un mode honnête
   « non calculable ». **4 848 est un prix de l'ANCIEN** (`sector_price` = reventes du bâti existant) :
   il ne doit jamais être le prix de sortie d'un bilan NEUF.
2. **Ordre de repli (S2) :** override bassin *sourcé* (observatoire) → **secteur** (préfixe IDU 10,
   n≥10) → **commune** (INSEE 5, n≥10) → **repli île** (médiane marché non indexée, ~4 375) →
   **non calculable** (8 communes social-dominantes). Garde-fou fragilité : n<20 **et** médiane<3 859 €/m²
   → écarté.
3. **S3 (`neuf_vefa_commune`) n'est pas un 2ᵉ prix de sortie** : c'est un comparable VEFA observé,
   sans exclusion social ni cascade. À **relibeller** « marché VEFA observé (commune) » dans Comparer /
   Contexte / fiche commune, ou à aligner sur S2 — jamais sous l'étiquette « prix de sortie ».
4. **Financier (S4) + Dossier §8 :** remplacer le pré-remplissage ancien par **S2** ; le texte des `i`
   et les notes doivent dire la règle S2, sans contredire Marché.
5. **Marché (S1) reste légitime comme fait de marché ancien**, mais renommé « **Prix du bâti ancien
   (secteur)** » — plus « prix de sortie » ; la Simulation lit S2 et son `i` dit la vraie règle.

**→ Arrêt Phase 1. Vic tranche la source unique et le sort de S3/Marché avant la Phase 2.**

---

## 5. Phase 2 — décision de Vic (05/10/2026) et mise en œuvre

**Arbitrage Vic :**
1. **Source unique = S2** (`resolve_prix_sortie_servi`, prix NEUF). C'est le seul « prix de sortie »
   de l'app : fiche (Simulation), Faisabilité, Calculette, Assemblage, Comparer, bilan Excel/PDF,
   Dossier, Copilote.
2. **Pré-remplissage du bilan (S4) = S2**, plus l'ancien (toujours modifiable par le client).
3. **S1 (ancien) reste dans l'onglet Marché** sous le libellé « **Prix de l'ancien (secteur)** » — ne
   s'appelle plus jamais « prix de sortie » ; le texte de Simulation ne dit plus que le prix vient de Marché.
4. **S3 (`neuf_vefa_commune`) non recâblé** ; là où il s'affiche (Comparer, Contexte, fiche commune) →
   libellé « **Prix VEFA commune** », jamais « prix de sortie ».

### Une seule fonction serveur
`resolve_prix_sortie_servi()` est LA source. Elle est désormais exposée telle quelle en
`out["prix_sortie"] = {prix, niveau, n, label, non_calculable, repli_ile}` par
`faisabilite_sens1` (fiche) ET `faisabilite_charge` (calculette) — **plus aucune surface ne recalcule
un prix de sortie localement ni ne lit `marche.median` (ancien) / `neuf_vefa_commune` sous cette
étiquette.** Pré-remplissage Financier centralisé dans `financier_questionnaire.prix_sortie_neuf_servi()`.

### Changements (commit unique)
**Backend** · `api/modules.py` : `prix_sortie` exposé sur `faisabilite_sens1` + `faisabilite_charge` ·
`financier_questionnaire.py` : helper `prix_sortie_neuf_servi()` + `prefill()` pré-remplit S2 (plus l'ancien) ·
`exports/builder.py` + `api/app.py` (×2) : les 3 appelants de `prefill()` passent S2 ·
`exports/blocs/marche.py` : la note Dossier §8 ne nomme plus l'ancien « prix de sortie du programme reconstruit ».
**Frontend** · `Fiche.tsx` (Simulation) + `constructibilite.tsx` (Constructibilité + Calculette source-line) lisent `prix_sortie` (S2) ·
`marche.tsx` + `constructibilite.tsx` (ligne « au mieux ») : S1 → « Prix de l'ancien (secteur) » ·
`blocB.tsx` + `moteurs.tsx` + `ContextePanel.tsx` + `strings.ts` : S3 → « Prix VEFA commune », plus « prix de sortie ».

### Tableau APRÈS (payloads servis, mesurés le 05/10/2026 — `APRES-payloads-temoins.txt`)

| Témoin | Simulation / Constructibilité (S2) | `bilan.calc.median` servi | Calculette `prix_sortie_median` (S2) | Marché « Prix de l'ancien » (S1) |
|---|---|---|---|---|
| `97411000BZ1065` Saint-Denis | **4 275** | **4 275** | **4 275** | 2 365 |
| `97416000ES0266` Saint-Pierre | **4 258** | **4 258** | **4 258** | 2 975 |
| `97415000AM0097` Saint-Paul (zone N) | **—** (non constructible) | — | — (non calculable) | 4 848 |

→ Sur chaque témoin constructible, **toutes les surfaces du prix de sortie servent la MÊME valeur** ;
l'ancien (S1) reste visible dans Marché sous son propre nom. AM0097 (zone N, non constructible)
n'affiche plus « Prix de sortie retenu 4 848 » (le piège d'origine) : il n'affiche plus de prix de
sortie du tout, et Marché porte l'ancien 4 848 correctement nommé.

### Test de non-divergence
`tests/test_prix_sortie1_unique.py` — pour chaque témoin, compare le prix de sortie servi par toutes
les surfaces (résolveur, fiche `prix_sortie`, `bilan.calc.median`, calculette web `prix_sortie` +
`prix_sortie_median`, calculette PDF, pré-remplissage Financier) : **échoue si deux surfaces divergent**,
et vérifie que l'ANCIEN n'est jamais servi comme prix de sortie. **3 passés** (lecture seule base APP ;
skip propre si données absentes). `tsc` 0 · `vitest` 235 · pytest ciblé : échecs IDENTIQUES à la base
(1 pré-existant `test_faux_constructible_jamais`, sans lien).

### Captures
Harnais lancé (API **8707** / Vite **5907**, base APP). La carte MapLibre bloque les captures
d'écran automatisées (timeout « waiting for fonts » de Playwright). Preuve avant/après retenue =
**payloads servis** (`APRES-payloads-temoins.txt`) + test de non-divergence. Repro manuelle :
`labuse api --port 8707` ; `LABUSE_API_DEV=http://127.0.0.1:8707 vite --port 5907` ; ouvrir
`#idu=97411000BZ1065` → onglet Simulation (« Prix de sortie retenu 4 275 €/m² ») vs onglet Marché
(« Prix de l'ancien (secteur) 2 365 €/m² »).

**Arrêt propre** : SIGTERM, ports 8707/5907 libres, 0 transaction idle.
