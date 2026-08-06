# M45 — BILAN · Filtres & Recherche (Train 4)

**Branche** `m45-filtres-recherche`, base `main` `71b088b9` (post-merge M43). **Cadrage**
`docs/mandats/M45_FILTRES_CADRAGE_V1.md` (fait foi). **0 tier, 0 poids modifié.** Pas de merge.

---

## P0 — Inventaire (validé, STOP levé)
Moteur centralisé `_q_v2_where` / `_q_v2_list` / `_q_v2_stats`. ~85 % du cadrage REQUÊTABLE en
base. Constats corrigés sur pièces : `capacite_estimee` BOOLÉEN (N dérivé SDP) ; AI1886 = 488 m²
aujourd'hui (pas 9 m²) → plancher 40 m² sûr. Détails : `M45_P0_INVENTAIRE.md`, `filtres_inventaire_p0.csv.gz`.

## P1 — Socle (les corrections AVANT tout ajout)

### Les 5 menteurs corrigés
| # | Menteur | Correction | Verrou |
|---|---|---|---|
| 1 | `v_signal` (Score V, RR 0,51, retiré M35) | retiré **front + API** (anti-filtre cadrage) | — |
| 2 | `/parcels` & `/stats` sans `source` (lisaient `parcel_evaluations` morte + ignoraient les filtres) | **404 « source requise »** | test `test_m45_filtres` |
| 3 | `statuts` (matrice morte M37) | retiré | — |
| 4 | `brulantes` (alias v1.3) | retiré | — |
| 5 | garde RGPD `age_dirigeant` | **refus API 400 avant tout SQL** (vaut partenaire API) | test dédié |

Piscine (M39) : types de vigilance lus dynamiquement, rien codé en dur → dispo auto à la bascule.

### Renommage « Réserve foncière » → « Potentiel long terme »
Libellé SEUL, clé `reserve_fonciere` inchangée → **golden key-based intact (117/117, pas de régén)**.
Toutes surfaces + IA/NL (nouveau libellé reconnu en entrée, anciens gardés en synonymes).

### Endpoint unifié `/filtre` + perf
`FiltreCriteres → _q_v2_where`, compte + tiers + page en un appel ; compteur = `_q_v2_stats`
(SQL exact + cache 30 s) ; **0 filtrage client GeoJSON** ; `source` requise. Perf mesurée
(`M45_P1_PERF.md`, `compteur_perf_p1.csv.gz`) : **barre niveau 1 < 500 ms tenu** (~200 ms).

## P2 — Les deux voies

### P2a — Barre niveau 1 + interrupteur + tiroir « Puis-je construire ? »
Facettes barre (backend + front) : constructibilité calibrée (tier + zone, pas la zone brute) ·
surface min/max · SDP min/max · état du sol · capacité logements ≥N (Estimé). Interrupteur
**Analyse LABUSE** (actif par défaut) : coupé = voie manuelle. Captures `screens/p2a_*`.

### P2b — Compteur réconcilié (clarification checkpoint)
L'écart 388 453 vs 431 663 relevé par Vic = les **43 210 parcelles déclassées** (declasse_*)
oubliées. Réconcilié, chaque nombre DIT son périmètre :
**431 663 (toute la trame) = 77 308 (retenues par l'analyse, déclassements inclus) + 354 355
(exclusions dures écartées).** Jamais une soustraction laissée au client.

### P2c — Dénormalisation `parcel_flags` (geste de bascule)
Vigilances non-francs dénormalisées, indexées. Exigences Vic tenues :
- **RUN-SCOPÉE, bâtie dans `labuse build-mvt`** (comme les MVT), jamais à la main.
- **GARDE DE COHÉRENCE bruyante** : compte par couche == source (dryrun_cascade_results), sinon
  rollback + RuntimeError.
- **TEMPS DE BUILD mesuré** : **15,1 s** pour 1 688 983 paires, 26 couches, cohérence OK
  (s'ajoute au coût de chaque bascule).

Perf vigilances île entière : **bruit_route 7098→888 ms · pente 4141→462 ms** · sol_pollue 157 ·
ravine 242 · cinquante_pas 169 ms. Comptes identiques à la source.

### P2d — Facettes des tiroirs éco / mutation / propriété / veille (backend)
sous_densite · mult_min (×N) · rang_max (têtes) · renouvellement (live q_v8) · division_or (O12) ·
proprietaire_type (PM/bailleur/PP) · etat_societe (M43) · copro (RNIC) · npnru (commune ANRU) ·
adresse_absente (BAN). Vérifiés sur données (comptes au commit). Renouvellement rebuild N°3
**vérifié live** (67 258 lignes sur q_v8_calibre).

### P2e — Les 4 tiroirs restants + presets + écartées (front)
Tiroirs éco / mutation / propriété / risques / veille (déclinaison du patron). **6 presets** du
cadrage (combinaisons nommées). **Écartées jamais masquées** (consultables voie manuelle, motif au
verdict). Capture `screens/p2e_tiroirs_presets.png`.

## P3 — Vérification
| Garde | Résultat |
|---|---|
| Golden | **117/117 PASS** (key-based, renommage sans impact) |
| Suite pytest | **1339 passed** (5 échecs PRÉEXISTANTS : residuel/au_ouverture, db=None, hors sujet) |
| **SHA256 vigilances (M37)** | `482da6f6…9e9abe9` **IDENTIQUE** — 0 vigilance touchée (`vigilances_m45_check_global.txt`) |
| tiers / poids | **0** (aucun fichier config/ · scoring/ · score_v_constants · p_v2 touché) |
| tsc frontend | rc=0 |
| Compteur barre niveau 1 | **< 500 ms** ; vigilances forte cardinalité < 900 ms après parcel_flags |

## ⚠ Restes tracés (honnêtement) — pour un lot de finition
1. **Curseur mode B partagé (session, travaux + loyer)** : non livré. Nécessite un état de session
   partagé fiche/filtre + le critère backend « mode B rentable au paramètre » (defisc/mode-b).
   Listé « en attente » dans le tiroir éco à l'écran.
2. **Unification liste/compteur historiques vers `/filtre`** : le composant FiltreLabuse porte déjà
   le compteur SQL-exact sur TOUTES les facettes ; la liste/cartouches historiques de ResultsSection
   (via `/stats`,`/parcels`) ne portent pas encore les 15 nouvelles facettes (params ignorés).
   À faire : router ResultsSection sur `/filtre` (ou étendre les 2 endpoints via `FiltreCriteres`).
3. **Vues utilisateur sauvegardées** (nom + combinaison, côté compte) : infra `segment_presets`
   existe ; les 6 presets nommés sont livrés (client), la sauvegarde compte reste à câbler.
4. **Filtres en attente de donnée (P0, arbitrés différés)** : plancher densité · EBC partiel ·
   emplacement réservé · sol naturel/ZAN · fraîcheur PLU · charge foncière/DVF/bilan CA. Listés et
   grisés à l'écran (« en attente de donnée M45 v1.1 »), jamais un filtre qui ment.

## Annexes
`M45_P0_INVENTAIRE.md` · `M45_P1_PERF.md` · `filtres_inventaire_p0.csv.gz` · `compteur_perf_p1.csv.gz`
· `vigilances_m45_check_global.txt` · `screens/` (p2a_1/2/3, p2a_zoom_barre, p2e_tiroirs_presets).
Commits `[M45-P0]` → `[M45-P2e]`. **Pas de merge — le geste revient à Vic.**
