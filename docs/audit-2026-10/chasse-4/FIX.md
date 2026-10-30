# CHASSE-4-FIX — correctifs des bugs du registre CHASSE-4

**Branche** `fix/chasse-4` · worktree `~/Desktop/labuse-chasse4fix` · API `127.0.0.1:8995` + front `127.0.0.1:6195` (base du Mac, run **q_v20**).
**Base** : `docs/audit-2026-10/chasse-4/RAPPORT.md`. Quatre bugs traités (**C4-001, C4-002, C4-003, C4-005**), rien d'autre.
**C4-004 écarté** (table `parcel_cadastre_remplacement` absente de la base Mac seulement ; présente en prod → pas de bug produit).
Pas de merge (geste de Vic). Aucun accès prod. **Hook vert**, commit sur la branche.

---

## Principe commun : une seule source, affichée telle quelle

Les quatre correctifs suppriment une **divergence écran ≠ PDF** en faisant décider la valeur **une seule fois côté backend** (point unique `/radar/annonce/estimation` + liste dédupliquée `_risques_rows`), l'écran et le PDF l'**affichant tels quels** — plus de table de traduction au front qui puisse diverger.

---

## C4-001 — Badge de fiabilité (écran affichait « Moyenne » pour un `limitee`)

**Avant** : `fiab()` dans `AnalyserAnnonce.tsx` ne connaissait que `'fiable'` et le repli commune ; la valeur backend `'limitee'` tombait au défaut « Moyenne » → l'écran sur-vendait la fiabilité et contredisait le PDF (« Limitée »).

**Fix — le mot vient du backend, affiché tel quel** :
- `src/labuse/pige/api.py` — nouveau `_fiabilite_mot(niveau, commune_fallback)` : **seul endroit** qui décide le mot (`fiable→Élevée`, `moyen→Moyenne`, `limitee→Limitée`, repli commune → `Limitée`). `estimation_annonce` sert désormais `fiabilite_mot` dans chaque retour chiffré.
- `frontend/src/components/outils/AnalyserAnnonce.tsx` — `fiab(mot)` **affiche `e.fiabilite_mot` tel quel** (seule la couleur est dérivée du mot) ; appel `fiab(e?.fiabilite_mot)`.
- `src/labuse/exports/blocs/annonce.py` — `_fiab_niveau(est)` lit `est["fiabilite_mot"]` (repli de compat sur l'ancien mapping si absent).

**Recette** : BZ1065 → **« Limitée » à l'écran comme sur le PDF** (`fix-captures/fix_bz1065_ecran.png`, `fix_97411000BZ1065.pdf`). API `fiabilite_mot:"Limitée"`.

## C4-002 — Nombre d'aléas (écran ≠ PDF : 1≠2, 4≠2)

**Avant** : la tuile « Risques » lisait `aleas.n` brut de `/parcels` (compte les aléas Géorisques ET les zones PPR séparément), le PDF comptait `len(risques)` (liste dédupliquée `_risques_rows`, une ligne par aléa).

**Fix — une seule liste, celle du PDF** :
- `src/labuse/pige/api.py` — l'endpoint `/radar/annonce/estimation` sert `n_aleas = len(_risques_rows(fiche, commune))`, **la même fonction** que le PDF.
- `frontend/src/components/outils/AnalyserAnnonce.tsx` — la tuile lit `estim.data?.n_aleas` (repli sur `aleas.n` seulement le temps du chargement).

**Recette** : BZ1065 → **2 aléas** écran == PDF ; CX0800 → **2 aléas** écran == PDF.

## C4-003 — Copropriété analysée comme une maison

**Avant** : une parcelle en copropriété était traitée en « Maison » avec un ordre de grandeur sur l'emprise totale du bâti, sans mention « copropriété ». *(À noter : la parcelle citée au RAPPORT, AR0420, n'était en fait PAS une copropriété — mon audit l'avait identifiée via `p_model_ext_copro`, une table présente pour toutes les parcelles ; le vrai drapeau est `parcel_p_score_v2.copro` = fiche `score_v2.copro`. Le correctif est posé sur ce VRAI drapeau et testé sur une vraie copro, 97422000BV2257 Le Tampon.)*

**Fix** (`src/labuse/pige/api.py`, `estimation_annonce`) : si `score_v2.copro` →
- `nature = "copropriete"`, label **« Copropriété »** (`rapport_parcelle`) ;
- comparateur **APPARTEMENTS** (`comparateur_bien(type_bien="appartement")`, segment précision 17 %) ;
- **pas** de `valeur_indicative` (aucun bien unique à valoriser sur l'emprise totale) ;
- la **lecture foncière reste**.
- Rendu miroir écran (`AnalyserAnnonce.tsx`, branche copro) et PDF (`annonce.py`, note « Copropriété — comparée aux ventes d'appartements… »). Élision « d'appartements » corrigée (`_de` / `dePl`).

**Recette** : BV2257 → **« Copropriété »**, comparée aux **appartements**, **pas** d'ordre de grandeur, lecture foncière 16 000 € — **écran == PDF** (`fix_copro_bv2257_ecran.png`, `fix_copro_pg-1.png`).

## C4-005 — Deux comptes de ventes sur le terrain nu (78 vs 118)

**Avant** : l'estimation disait « 78 ventes … secteur cadastral » et l'accordéon « (118) » sans périmètre → confusion.

**Fix — chaque périmètre porte son étiquette, avec le rayon réel** :
- `src/labuse/pige/api.py` — l'estimation terrain sert `comparables_radius_m` (rayon réel du comparateur, p. ex. 1000 m).
- `AnalyserAnnonce.tsx` + `annonce.py` — l'accordéon / le tableau disent **« à moins de 1 km »** (rayon réel) ; l'estimation garde **« secteur cadastral »**.

**Recette** : CX0800 → estimation « 78 … secteur cadastral » / accordéon « **Les ventes de terrain nu à moins de 1 km (118)** » — les deux périmètres sont distincts et explicites, écran == PDF.

---

## Fichiers touchés

| Fichier | Bugs |
|---|---|
| `src/labuse/pige/api.py` | C4-001 (`_fiabilite_mot`, `fiabilite_mot`), C4-002 (`n_aleas`), C4-003 (copro), C4-005 (`comparables_radius_m`), `rapport_parcelle` label |
| `src/labuse/exports/blocs/annonce.py` | C4-001 (`_fiab_niveau`), C4-003 (note copro, `_de`), C4-005 (`_rayon_txt`, footnote) |
| `frontend/src/components/outils/AnalyserAnnonce.tsx` | C4-001 (`fiab`), C4-002 (`n_aleas`), C4-003 (note copro, `dePl`), C4-005 (rayon) |
| `frontend/src/lib/api.ts` | types `fiabilite_mot`, `n_aleas`, `comparables_radius_m` |
| `tests/test_annonce_pdf.py` | assertion C4-005 mise à jour + 2 tests neufs (copro, `fiabilite_mot` tel quel) |

## Recette & tests

- **Navigateur + API en direct** (8995/6195), écran == PDF sur **fiabilité, aléas, nature** pour BZ1065, CX0800, BV2257 (copro). Console navigateur : **0 erreur**. Captures : `fix-captures/`.
- **Hook vert** : `scripts/git-hooks/pre-push` → secrets + front (`tsc -b` + `vitest`) + unitaires Python → **2739 passed, 0 failed** ; `test_annonce_pdf.py` **17 passed** (dont `test_parcelle_copropriete` et `test_fiabilite_mot_est_servi_tel_quel`).

**Merge = geste de Vic.**
