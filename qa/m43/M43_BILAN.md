# M43 — BILAN · Features propriétaire : construction & MESURE (personnes morales seulement)

**Branche** `m43-features-proprietaire` · base `main` d91189f2 (M44 mergé).
**Structure = MESURE, pas intégration** : le modèle P **ne bouge pas** — **0 tier, 0 poids** modifié.
L'intégration au scoring (re-fit) reste un geste **[S] de Vic** sur ces mesures (comme la bascule M39).

**⚠ Clôture RGPD tenue** : périmètre **PERSONNES MORALES uniquement**, au niveau **SOCIÉTÉ**
(dénomination / SIREN / état). **Aucun signal sur une personne physique** (âge, décès, succession,
patrimoine individuel). Le champ `dirigeants` de l'enrichissement (PP) **n'est pas lu**. Le badge
« gérant âgé » préexistant n'est **ni étendu, ni décliné, ni exposé en filtre** (inchangé).

---

## 1. Jointures & définitions (Phase 0 — sur pièces, lecture seule)

`pm_proprietaires_millesimes` : 461 570 lignes, 14 517 SIREN, **91 397** parcelles PM. Le **millésime
EST tracé** (2019→2024 ; dernier = 2024) — la dette #11 « millésime amont non tracé » est **inexacte**
au niveau donnée (note-vs-source). Servies actives PM (millésime 2024) : **~5 201** parcelles.

Sources **déjà en base**, **Licence Ouverte** (aucun re-téléchargement) :

| Signal société | Définition (sourcée) | Source | Résolution (SIREN servis) |
|---|---|---|---|
| **cessée** | `owner_enrichment.payload->>'etat_administratif'='C'` (+ `date_fermeture`) | recherche-entreprises / INSEE Sirene | 70 % enrichis |
| **radiée** | `bodacc_annonces_owner.famille='radiation'` | BODACC Etalab | 7 % (à événement) |
| **procédure collective** | `bodacc_annonces_owner.famille='pcl'` | BODACC Etalab | idem |

« Dormance » **mesurable et sourcée** — aucun proxy flou (« pas de site web » rejeté). Volumétrie :
signal **rare**, concentré sur *à creuser*, **absent des têtes** (brûlante 0). → petits effectifs, IC larges.

## 2. Mesure à blanc du pouvoir prédictif (Phase 1 — harnais gelé RR M36, `p_model_ext_dataset` fold 2025)

### Lift BRUT + résiduel tenure (Mantel-Haenszel) — `lifts_signaux_p1.csv`
| Signal | n | mutés | RR brut [IC95] | RR \| tenure (MH) |
|---|---|---|---|---|
| cessée | 1 143 | 48 | **2,49 [1,88 ; 3,30]** | 2,54 [1,92 ; 3,36] |
| radiée | 467 | 36 | **4,57 [3,33 ; 6,29]** | 4,49 [3,27 ; 6,17] |
| procédure coll. | 749 | 23 | **1,82 [1,21 ; 2,73]** | 1,88 [1,25 ; 2,82] |

Les trois RR bruts excluent 1 et survivent à la tenure → **à première vue, tous intégrables**.

### ⚠ Le piège éprouvé : causalité inverse (constater avant présumer)
Un signal société n'est prédictif que s'il **PRÉCÈDE** la mutation. Test temporel (parcelles mutées) :

| Signal | signal AVANT mutation | APRÈS (rétro-causal) |
|---|---|---|
| cessée | 10 % | **90 %** |
| radiée | 23 % | **77 %** |
| pcl | **52 %** | 48 % |

→ cessée/radiée sont majoritairement « dissolution SUIT la vente » : leur RR brut est **rétro-causal**.

### Lift honnête AS-OF (signal daté AVANT le fold → mutation dans le fold) — `lifts_asof_p1.csv`
| Signal | n | mutés | RR AS-OF [IC95] | verdict |
|---|---|---|---|---|
| cessée | 785 | 9 | **0,67 [0,35 ; 1,28]** | **NON prédictif** (sous la base) |
| radiée | 385 | 5 | **0,76 [0,32 ; 1,81]** | **NON prédictif** (n faible) |
| **procédure coll.** | 687 | 22 | **1,86 [1,23 ; 2,82]** | **CONCLUANT** — lift réel |

## 3. Recommandation d'intégration — signal par signal

| Signal | Prédictif as-of | **Recommandation [S] (Vic)** |
|---|---|---|
| **procédure collective** | oui (RR ≈ 1,86) | **INTÉGRABLE** au scoring — feature « SIREN en procédure collective as-of ». +0,86 RR réel, causalement sain. L'hypothèse backlog éprouvée & **confirmée pour CE signal seul**. |
| **cessée** | non (0,67) | **NE PAS intégrer** — indicateur RETARDÉ / fuite temporelle. Reste un **fait public** (fiche). |
| **radiée** | non (0,76, n faible) | **NE PAS intégrer** — retardé + effectif faible. Fait public (fiche). |

**Lecture** : le pari backlog (+1/+2 RR) est **partiellement vrai** — seule la **procédure collective**
le porte réellement ; cessée/radiée séduisent en brut, **morts en as-of**. Les intégrer aurait injecté
du **futur dans le passé**. Éprouvé, pas présumé. Le doute n'a pas profité au chiffre.

## 4. Exposition fiche (Phase 2 — informatif, PM only, 0 déduction à l'écran)

Ligne factuelle dans le volet **Propriétaire** quand la société porte un état public — **les trois états
exposés** (c'est un fait public d'entreprise, indépendamment de la valeur prédictive) :

> **Société propriétaire : cessée le 2024-03-20 ; procédure collective (dernière annonce 2024-03-24) ;
> radiée le 2024-03-22.** *(Sourcé Sirene/INSEE / BODACC)*
> *Fait public d'entreprise (état de la société) — information de contexte, aucune déduction.*

- **Aucune vigilance, aucun badge de ciblage, aucun filtre** (le filtre attend M45 + retour avocat).
- Helper `_pm_etat_societe(db, siren)` (app.py), **SAVEPOINT** `begin_nested()` → table absente en base
  de test n'avorte pas la fiche. Clé `etat_societe` ajoutée à `proprietaire_moral` (invisible au golden).
  Front : `Fiche.tsx` (ligne sous la dénomination) + `types.ts`. Rendu écran uniquement (le one-pager
  imprime les cartouches **pondérés** — un fait non-scoré n'y a pas sa place, il y paraîtrait pondéré).
- Témoins (captures `qa/m43/screens/`) : **PM avec signal** (1) ligne présente ; **PM sain** (2, SCI ALOE)
  **0 occurrence** de la ligne ; **PP muette** (3) « privé / personne physique », rien sur la société.

## 5. Vérification mécanique (0 régression)

| Garde | Résultat |
|---|---|
| Golden | **117/117 PASS**, 0 incohérence base↔API |
| Suite pytest | 1332 passed (5 échecs **préexistants** hors sujet : `residuel`/`au_ouverture`, db=None en base de test — vérifié par stash) |
| **SHA256 vigilances (M37)** | `482da6f6…9e9abe9` **identique** (4 344 938 lignes, 431 632 parcelles) — **0 vigilance touchée** |
| tsc frontend | rc=0 |
| tiers / poids | **0** (`git status` config/ · models.py · scoring/ = vide) |

## Annexes (digests `.csv.gz` — convention preuve QA)
- `lifts_signaux_p1.csv[.gz]` · `lifts_asof_p1.csv[.gz]` · `volumetrie_signaux_par_tier_p0.csv[.gz]`
- `vigilances_m43_check_global.txt` (preuve SHA une ligne) · `screens/` (3 témoins + zooms)
- `scripts/m43_lift_signaux.py` · `shoot_m43.mjs` · `M43_P0_CONSTAT.md` · `M43_P1_MESURE.md`

**Pas de merge, pas de re-fit, pas de bascule.** Le geste [S] (intégrer la procédure collective) revient à Vic.
