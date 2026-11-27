# OUTIL-PLU-FIX-13 — La Plaine : dossiers de modification concaténés (suite relecture-plu-9 §3)

Branche `fix/outil-plu-1`. Le PDF de La Plaine-des-Palmistes (97406, 217 p.) colle **3 dossiers de
modification** après le règlement opposable (p.1-117). FIX-12 les avait diagnostiqués sans y toucher ;
FIX-13 les **étiquette**, les **classe après** le règlement et **signale** la modification non intégrée —
sans dé-espacer (impossible sans risque) ni exclure de page (risquerait de perdre de l'opposable).
Consigne de charge : tests PLU ciblés, commit local, **pas de suite complète ni de push**.

## Les 3 dossiers (dates, objet, intégration dans le règlement de base p.1-117)

Le règlement de base (p.1-117) est l'édition « approuvé le 29 mai 2013, **modifié le 11 mars 2019** »
(CODRA 2019).

| Dossier | Pages PDF | Date | Objet | Intégré dans p.1-117 ? |
|---|---|---|---|---|
| ouverture AUs1 | 118-167 (34 extraits) | **mai 2023** | ouverture à l'urbanisation de la zone **AUs1** (parcelle AV 613, centre-ville) | **NON** — postérieur à l'édition 2019 |
| n°2 | 168-199 (11 extraits) | **2019** | reprise d'articles (UB/Ur 7, Uc…) | **OUI** — c'est la modification du 11 mars 2019 |
| « Plateau vert » (chemin Dureau) | 200-217 (10 extraits) | **2016** | UB 6/10/11 (implantation, hauteur, aspect) | **OUI** — antérieur à l'édition 2019 |

Seule la modification **mai 2023 (AUs1)** n'est pas intégrée : les 14 articles du chapitre **AUs** du
règlement de base (p.71-74) portent désormais un drapeau la nommant et la datant.

## Ce qui a été fait (code)

1. **Étiquetage.** `config/plu_dossiers.yaml` (par commune, vide ailleurs) décrit les plages de pages des
   dossiers. À l'ingestion (`_applique_dossiers`), chaque extrait des pages d'un dossier reçoit une
   étiquette `dossier` = « Dossier de modification [n°N] — <objet> (date) » ; les articles du règlement de
   base restent `dossier = NULL`. Colonnes DDL `dossier` / `modif_note`.
2. **Ordre.** `search_reglement` trie `(dossier IS NOT NULL)` en **premier** → les articles du règlement de
   base passent **toujours avant** les extraits de dossier (no-op pour les 20 communes sans dossier).
3. **Modification non intégrée.** Les articles du règlement de base dont la zone est visée par un dossier
   **non intégré** (`signale_zones`) portent `modif_note` (« …NON intégrée à ce règlement de base — voir le
   dossier de modification »).
4. **Écran** (`PluAnnuaire.tsx`) : bandeau ambre sur un extrait de dossier (« Dossier de modification … —
   texte restitué tel que publié : espaces parasites dans le document source »), et ⚠ `modif_note` sur
   l'article du règlement de base concerné.

## Preuve — la route réelle (`/modules/plu-annuaire/search`), ce que l'écran rend

**La Plaine · zone AUs1 · « hauteur »** — le règlement de base d'abord, chacun marqué modif non intégrée ;
le dossier mai 2023 ensuite, étiqueté :
```
1. [RÈGLEMENT (p.1-117)] ARTICLE AUs 10 · p.73 · zone AUS
     ⚠ Modification « ouverture à l'urbanisation de la zone AUs1 (parcelle AV 613) » (mai 2023) NON intégrée à ce règlement de base — voir le dossier de modification.
2. [RÈGLEMENT (p.1-117)] ARTICLE AUs 14 · p.74 · zone AUS   ⚠ (idem)
3. [DOSSIER] HAUTEUR MAXIMALE DES CONSTRUCTIONS · p.131 · zone AUS
     ↳ Dossier de modification — ouverture à l'urbanisation de la zone AUs1 (parcelle AV 613) (mai 2023) — texte restitué tel que publié : espaces parasites dans le document source.
```

**La Plaine · zone UB · « hauteur »** — les 3 articles du règlement (Ub 11/10/1, p.23-30) d'abord, puis les
extraits de dossier (p.144/145/168/171/201), chacun étiqueté par son dossier (mai 2023 / n°2 2019 / Plateau
vert 2016) avec la mention « texte restitué tel que publié ».

## Tests & périmètre

- 3 tests ajoutés au filet (`test_plu_fix10_lot0.py`) : étiquetage des dossiers, règlement-avant-dossier
  (UB), drapeau modif non intégrée (AUs1). Filet PLU reel **56/56** (53 + 3). `tsc` front vert.
- Réingestion de la **seule** commune 97406 ; corpus 3222 extraits / 21 communes intact.
- Commit **local**. Pas de suite complète, pas de push (machine chargée — consigne).
