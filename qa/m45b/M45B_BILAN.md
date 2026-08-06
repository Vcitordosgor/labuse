# M45-B — BILAN · Finition filtres (les 3 restes de M45)

**Branche** `m45b-finition-filtres`, socle = tip M45 (`66c415c8`). **Câblage sur données EXISTANTES,
aucun sourcing.** 0 tier, 0 poids. Pas de merge.

> ⚠ Note de socle : `origin/main` était encore à `71b088b9` (Merge M43) au démarrage — il ne
> contenait PAS M45. La branche a donc été basée sur le tip `m45-filtres-recherche` (= main + M45),
> pas sur main. Signalé avant de coder (constater avant présumer).

## Lot 1 — Tiroir Économie complet
Facettes SQL-exactes sur `/filtre` (`_q_v2_where` + `FiltreCriteres`), étiquetées :
| Facette | Source | Étiquette | Vérif base réelle |
|---|---|---|---|
| Prix d'achat max ≤ budget | `score_e.charge_supportable` (M22-A) | Estimé | ≤150k → 28 075 |
| Charge foncière (tranches) | `score_e.charge_supportable` | Estimé | 100-250k → 13 920 |
| Prix marché DVF €/m² | `v_parcel_dvf_last.prix_m2_terrain` | Sourcé | ≤200 → 9 794 |
| Fiabilité marché (n≥3) | `dvf_secteur_medianes.n_ventes` | — | 419 486 |
| Bilan CA (≥N) | `dvf_prix_sortie_neuf × SDP` | Estimé | ≥500k → 2 058 |
| Mode B rentable au paramètre | `parcel_residuel × score_e` (forme fiche M44) | Estimé | 33 919 → 40 785 (params) |

Le preset **« Mon budget » est FONCTIONNEL** (charge foncière ≤ 200 k€). Compteur < 500 ms (barre
niveau 1 ; les facettes score_e/DVF sont des probes indexés par idu).

## Lot 2 — Curseur mode B partagé (le reliquat M44→M45)
Une **valeur de session UNIQUE** `modeB {travauxM2, loyerM2, rendementPct}` (store `useApp`, rien
persisté). Partagée **fiche ↔ filtre** :
- Le **curseur** du tiroir Économie écrit la session ; le filtre `mode_b_rentable` lit ces params
  (le compteur BOUGE avec le curseur : 33 919 → 40 785).
- La **fiche** (`ModeBDrawer`) lit/écrit le MÊME `modeB.travauxM2` (le slider travaux devient la
  session) → régler le curseur au filtre recalcule la fiche, et inversement. Point de calcul mode B
  inchangé (même forme que M44 : achat_max = loyer_annuel/rendement − travaux).

## Lot 3 — Unification ResultsSection → /filtre
`getStats` (cartouches) ET `getResults` (liste) passent désormais par **`/filtre`** (qui renvoie le
stats complet + la page). La liste et les cartouches portent EXACTEMENT les mêmes facettes que le
compteur. **Vérifié** : preset « Mon budget » appliqué → compteur FiltreLabuse **32 491** = « parcelles
analysées » de ResultsSection **32 491** (alignés). **Plus jamais un compteur filtré et une liste qui
ignore les filtres.**

## Vérification (Phase 3)
| Garde | Résultat |
|---|---|
| Golden | **117/117** |
| Suite pytest | **1339 passed** (5 échecs PRÉEXISTANTS residuel/au_ouverture db=None, hors sujet) |
| SHA256 vigilances M37 | `482da6f6…` **IDENTIQUE** (0 vigilance touchée) |
| tiers / poids | **0** (aucun fichier config/ · scoring/) |
| tsc frontend | rc=0 |
| Alignement liste↔compteur | **OK** (32 491 = 32 491, preset Mon budget) |

## Restes mineurs tracés
- **CSV export** (`/parcels/export.csv`) porte encore l'ancien jeu de params (pas les 15+ facettes
  M45/M45-B) — la liste À L'ÉCRAN est unifiée ; l'export CSV reste à router sur `FiltreCriteres`.
- **Vues utilisateur sauvegardées** (compte) : infra `segment_presets` présente ; les 6 presets
  nommés sont livrés (client), la sauvegarde compte reste à câbler (héritée de M45).

## Annexes
`screens/l1_economie_plein.png` · `screens/l3_mon_budget_liste_alignee.png` · `vig_check_global.txt`.
Commits `[M45B-L1]` → `[M45B-L3]`. **Pas de merge — le geste revient à Vic.**
