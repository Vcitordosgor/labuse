# ESTIMATION-BANC-1 — Précision de l'estimateur « Analyser une annonce »

**Audit lecture seule** · branche `audit/estimation-banc-1` · 29/10/2026 · aucun code servi modifié, rien en prod.
Base servie Mac `postgresql:///labuse` (PROD = LOCAL), lecture seule, aucune session créée.

Mesure, à la manière de Repère Immo, l'écart entre le **prix au m² estimé** par l'outil (entrée adresse,
point unique `estimation_annonce` / `GET /radar/annonce/estimation/{idu}`) et le **prix au m² réellement payé**,
sur **toutes les ventes DVF 2025 des 24 communes**, chaque estimation étant **reconstruite sans aucune vente
postérieure ni la vente jugée elle-même** (preuve au §3).

---

## Tableau de tête

Écart = `estimé / réel − 1` sur le €/m². « médian |écart| » = médiane de la valeur absolue de l'écart
(métrique comparable à celle de Repère Immo). N = ventes jugées (mutations 2025 mono-parcelle, DVF propre).

| Segment | N | Ne sait pas estimer | **Médian \|écart\|** | ±10 % | ±20 % | Biais médian signé | Repère Immo |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Toutes ventes** | 5 592 | 1,7 % | **27,9 %** | 19,6 % | 38,3 % | −3,2 % | — |
| **Appartement** | 2 076 | 1,1 % | **17,1 %** | 30,9 % | 57,9 % | −8,6 % | **16 %** |
| **Maison** | 2 292 | 0,3 % | **31,8 %** | 15,5 % | 31,6 % | −10,5 % | **19 %** (en ville) |
| **Terrain nu** | 1 224 | 5,3 % | **633 %** ⚠ | 7,5 % | 16,9 % | — | — |
| &nbsp;&nbsp;↳ terrain / parcelle **nue** (base correcte) | 404 | 14,4 % | **18,8 %** | 24,0 % | 54,3 % | −6,4 % | — |
| &nbsp;&nbsp;↳ terrain / parcelle **bâtie** (mauvaise base) | 820 | 0,9 % | **1 207 %** ⚠⚠ | 0,5 % | 1,0 % | — | — |

**Badge de fiabilité affiché** (sur les cas où l'estimateur vise la bonne base — cf. §5) :

| Badge | N | Médian \|écart\| | ±20 % | Ordre respecté ? |
|---|---:|---:|---:|---|
| **Élevée** | 3 887 | **21,9 %** | 46,4 % | ✔ le plus précis |
| **Moyenne** | 738 | **26,4 %** | 39,3 % | ✔ au milieu |
| **Limitée** | 23 | **58,8 %** | 17,4 % | ✔ le moins précis |

> Le badge **ne ment pas sur le classement** : « Élevée » est réellement plus précis que « Limitée ».
> Mais « Élevée » ≠ « juste » : **un bien sur deux classé Élevée reste à plus de 20 % du prix réel**, et le
> badge ne dit rien de l'erreur de *nature* (un terrain peut porter « Élevée » sur un prix de bâti, cf. §5-①).

---

## 1. Verdict en cinq lignes

1. **Appartement : au niveau de Repère Immo** (17,1 % vs 16 %). C'est le seul segment où l'outil tient la comparaison.
2. **Maison : ~1,7× moins précis** que Repère Immo (31,8 % vs 19 %), à cause du comparateur qui **price les maisons avec des appartements** (§5-②).
3. **Terrain nu : à prendre avec des pinces.** Correct quand la parcelle est réellement nue (18,8 %), mais **2 ventes de terrain sur 3 (67 %) tombent sur une parcelle que l'outil croit bâtie** → il affiche un €/m² de bâti pour un terrain (écart médian 1 207 %, §5-①).
4. **L'outil affiche presque toujours un chiffre** (1,7 % de « ne sait pas estimer » seulement) — mais *afficher un chiffre n'est pas savoir estimer* : le non-dit est concentré sur le terrain (14,4 % des parcelles nues).
5. **Le badge de fiabilité est honnête sur l'ordre** mais **sur-vend la précision absolue** et ignore l'erreur de nature.

## 2. Ce que mesure (et ne mesure pas) l'estimateur

`estimation_annonce(db, idu, fiche)` (`src/labuse/pige/api.py:1268`) choisit **la nature depuis la PARCELLE, pas depuis la vente** :
`_nature_parcelle` lit `parcel_residuel.taux_emprise_pct` (part bâtie BD TOPO) — `< 5 %` → **nue**, `≥ 5 %` ou non mesuré → **bâtie**.

- **Parcelle nue** → repère €/m² de **terrain** du secteur cadastral (`mon_secteur._terrain_section`, table pré-agrégée `dvf_secteur_medianes`, seuil n ≥ 8).
- **Parcelle bâtie / non mesurée** → **`prix_ancien`** de la fiche = `marche_service.marche_dvf(profil=DVF_BANQUIER_ADAPTATIF)` = **`faisabilite.bilan.sector_price`** : médiane €/m² bâti, **plans APPARTEMENT d'abord**, puis mixte appart+maison, rayons 500→1000→1500 m, puis commune entière ; trim `[1000 ; 12000] €/m²` + 5 % extrêmes ; seuil n ≥ 8.
- **Badge** (`AnalyserAnnonce.tsx` `_badge`) : `commune_fallback → Limitée` ; sinon `fiable → Élevée` ; sinon `Moyenne`.

Conséquence structurelle : **l'estimateur ne regarde jamais le type du bien vendu.** Il n'y a ni ajustement de
surface, ni correction maison/appartement, ni modèle hédonique — c'est une **médiane de secteur**, pas un AVM.

## 3. Preuve de NON-FUITE (le point le plus important)

Pour chaque vente jugée, l'estimation est **reconstruite** avec, et seulement avec, les ventes **de date
strictement antérieure**, **la mutation jugée étant exclue par son `id_mutation`**. Trois garanties :

1. **On n'appelle jamais l'estimateur de prod tel quel** : il lirait `dvf_secteur_medianes` (pré-agrégée sur
   TOUTE la fenêtre 2021-2025, donc du futur) et `sector_price` (fenêtre ancrée sur *aujourd'hui*). On
   **ré-implémente** leur logique avec un filtre `date_mutation < date_vente` (année de référence = année de la vente).
2. **Garde-fou automatique par vente** : la date du comparable le plus récent utilisé est vérifiée `< date de la
   vente`. Résultat du run : **0 violation sur 5 592** (`METRIQUES.json → fuite.toutes_ok = true`).
3. **Fidélité du réplica prouvée** (`fidelite_replica.py`, `FIDELITE.txt`) — en exécutant le réplica **sans coupe
   de date** (fenêtre pleine), il **reproduit la production** :
   - **Terrain** : médiane recalculée == `dvf_secteur_medianes` servie → **693/693 secteurs identiques (±1 €, 100 %)**.
   - **Bâti** : `estime_bati` == `sector_price` appelée en direct → **57/60 parcelles identiques (±1 €)**, les 3
     restantes **même plan retenu**, écart de médiane < 4 % (bruit de bord du trim 5 %).

   → Le banc = **production + coupe de date, rien d'autre**. La seule différence entre le chiffre mesuré et le
   chiffre servi est précisément ce qui supprime la fuite.

**Univers.** Mutations DVF **2025** (`nature IN 'Vente', 'Vente terrain à bâtir'`), agrégées au grain mutation,
**une seule parcelle** (valeur attribuable), prix réel = `valeur/bâti` (maison/appart) ou `valeur/terrain` (terrain).
Garde-fous de vraisemblance du prix réel (artefacts DVF) : bâti `[100 ; 20 000]`, terrain `[1 ; 10 000] €/m²`.
Multi-parcelles exclues (valeur non attribuable). **5 592 ventes** jugées (2 292 maisons, 2 076 apparts, 1 224 terrains).

## 4. Résultats par commune (extrait)

Les communes **urbaines** (comparables denses) tiennent le mieux ; les communes **rurales / des Hauts** décrochent,
surtout à cause du terrain sur parcelle bâtie et des secteurs trop maigres (repli commune).

| Commune | N | Médian \|écart\| | ±20 % |
|---|---:|---:|---:|
| Saint-Denis | 1 330 | 20,8 % | 48,7 % |
| Bras-Panon | 65 | 18,8 % | 53,1 % |
| La Possession | 250 | 22,7 % | 46,8 % |
| Saint-Pierre | 590 | 24,4 % | 42,5 % |
| Saint-Paul | 626 | 25,4 % | 40,2 % |
| … | | | |
| Saint-Joseph | 281 | 47,9 % | 25,3 % |
| Saint-Philippe | 37 | 49,9 % | 16,2 % |
| Sainte-Rose | 31 | 275 % | 13,8 % |
| Cilaos | 87 | 286 % | 9,2 % |
| Les Trois-Bassins | 37 | 639 % | 10,8 % |

(détail complet des 24 communes dans `RESULTATS.txt` / `METRIQUES.json`.)

## 5. Les trois plus grosses sources d'erreur

### ① Nature décidée sur la parcelle, pas sur la vente — « un terrain au prix du bâti » (la pire)
L'outil tranche nue/bâtie depuis l'emprise bâtie *actuelle* de la parcelle. Or **67 % des ventes de terrain 2025
(820 / 1 224)** portent sur une parcelle dont l'emprise ≥ 5 % (ou non mesurée) → l'outil la croit bâtie et affiche
un **€/m² de bâti pour une vente de terrain** : écart médian **1 207 %**, 0,5 % seulement à ±10 %.
Exemple : `97412000BH0733` (Saint-Joseph), terrain payé **188,7 €/m²**, estimé **2 465 €/m² (bâti, badge Moyenne)**.
C'est ce seul mécanisme qui fait exploser la ligne « terrain nu » du tableau de tête (633 % globale vs 18,8 % quand
la base est correcte). *Le badge n'alerte pas : l'erreur est dans le choix de nature, en amont du comparateur.*

### ② La maison comparée à des prix d'appartement (attendu, confirmé, chiffré)
`sector_price` essaie **les appartements seuls en premier**. Comme la plupart des secteurs urbains ont ≥ 8
appartements à moins de 500 m, **72 % des maisons (1 644 / 2 272) sont estimées sur des comparables
APPARTEMENT PURS**. Ce sous-groupe est **nettement moins bon** que les maisons estimées sur un échantillon mixte :

| Maison estimée via… | N | Médian \|écart\| | Biais médian signé | ±20 % |
|---|---:|---:|---:|---:|
| **appartements purs** | 1 644 | **33,2 %** | **−15,4 %** | 29,3 % |
| mixte appart+maison | 628 | 27,1 % | +4,4 % | 38,2 % |

À La Réunion le €/m² bâti d'appartement est *inférieur* à celui des maisons qui se vendent → la maison est
**sous-estimée** (biais −15,4 %). Direction inverse de l'intuition métropolitaine, mais **même cause** : mauvais
type de comparable. C'est le principal responsable de l'écart maison (31,8 %) vs Repère Immo (19 %).

### ③ Secteurs maigres & repli commune — « un prix moyen pour toute la ville »
- **Terrain** : 14,4 % des parcelles nues n'ont pas 8 ventes de terrain dans leur section → **pas d'estimation**.
- **Bâti** : quand les comparables proches manquent, l'outil élargit à la **commune entière** (badge Limitée) :
  médiane d'écart **58,8 %**, 17,4 % à ±20 %. Les communes rurales (Cilaos, Les Trois-Bassins, Sainte-Rose,
  Saint-Philippe, Entre-Deux) concentrent ces cas : une médiane communale unique écrase la réalité locale.

## 6. Comparaison à Repère Immo

Repère Immo annonce **16 % (appartement)** et **19 % (maison, en ville)** d'écart sur des ventes 2025 en métropole.
En retenant la même métrique (médiane de l'écart absolu) :

- **Appartement : 17,1 % vs 16 % → à parité.** L'estimateur par médiane de secteur suffit quand le marché est
  homogène et dense (collectifs urbains, surtout Saint-Denis).
- **Maison : 31,8 % vs 19 % → ~1,7× pire.** L'écart vient de ① l'absence d'ajustement de type (maison estimée
  sur appartements) et ② l'absence de tout modèle de surface/qualité. Repère Immo sépare au moins maison et
  appartement ; l'outil, non.
- **Terrain nu : non comparable.** Repère Immo n'estime pas le foncier nu. Sur le périmètre où l'outil le fait
  *correctement* (parcelle vraiment nue), 18,8 % — honnête — mais c'est l'exception, pas la règle (§5-①).

**À ne pas vendre :** une précision « prix » générale. L'outil est un **repère €/m² comparatif** (il l'affiche
d'ailleurs en fourchette ±30 % avec la mention « estimation comparative, pas un avis de valeur »), fiable pour
l'appartement urbain, approximatif pour la maison, et piégeux pour le terrain.

## 7. Limites

- **Métrique Repère Immo supposée** = médiane de l'écart absolu €/m² ; si c'est un MAPE ou un écart sur le prix
  total, la comparaison reste directionnelle (le classement appart < maison et l'ampleur du retard maison tiennent).
- **Vérité terrain = DVF mono-parcelle** avec garde-fous d'artefacts ; les ventes multi-parcelles (valeur non
  attribuable) sont exclues. Quelques €/m² terrain très bas (1–2 €/m², grandes parcelles agricoles / ventes
  symboliques) gonflent les *moyennes* — raison pour laquelle le rapport n'utilise que des **médianes** (robustes).
- **Réplica bâti** fidèle à 95 % au €/m² près (3/60 avec < 4 % d'écart, même plan) ; sans effet sur des conclusions
  qui portent sur des écarts de 17–32 %.
- `taux_emprise_pct` reflète l'emprise bâtie *actuelle* : un terrain issu d'une démolition/division récente peut
  donc légitimement être « bâti » au moment du calcul — mais côté client le résultat reste un prix faux (§5-①).

## 8. Reproduire

```bash
# banc principal (≈ 3 min, dominé par le chargement SQL)
~/Desktop/labuse/.venv/bin/python docs/audit-2026-10/estimation-banc-1/backtest_estimation_annonce.py
# preuve de fidélité du réplica (appelle la vraie sector_price)
PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python docs/audit-2026-10/estimation-banc-1/fidelite_replica.py
```

**Livrables** (`docs/audit-2026-10/estimation-banc-1/`) :
`backtest_estimation_annonce.py` · `fidelite_replica.py` · `PAR-VENTE.csv` (5 592 lignes, une par vente, avec
`fuite_ok`) · `METRIQUES.json` · `RESULTATS.txt` · `FIDELITE.txt` · ce `RAPPORT.md`.
